"""Validate reviewable source-time edit plans without changing any media."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

from .asr import file_hash
from .media import probe_media

_ID = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,63}$')
_HASH = re.compile(r'^[0-9a-f]{64}$')
_ROLES = {'main': 'video', 'broll': 'video', 'voice': 'audio', 'music': 'audio'}
_RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


def _identifier(value, label):
    if not isinstance(value, str) or not _ID.fullmatch(value) or value.upper() in _RESERVED:
        raise ValueError('Invalid ' + label)
    return value


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + ' must be a finite number')
    return float(value)


def _relative_file(root, value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or '\0' in value:
        raise ValueError('Source path must be a safe relative POSIX path')
    p = PurePosixPath(value)
    if p.is_absolute() or PureWindowsPath(value).is_absolute() or any(x in ('', '.', '..') for x in value.split('/')):
        raise ValueError('Unsafe source path')
    path = root.joinpath(*p.parts)
    for item in (path, *path.parents):
        if item.is_symlink() or item.is_junction():
            raise ValueError('Linked paths are not permitted')
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file() or not resolved.is_relative_to(root.resolve(strict=True)):
            raise ValueError('Source must be a file inside the designated source directory')
    except OSError as error:
        raise ValueError('Source is missing or inaccessible') from error
    return resolved


def _history(plan):
    clips = plan.get('clips')
    history = plan.get('history')
    if not isinstance(clips, list) or not clips or not isinstance(history, list):
        raise ValueError('Clips and history must be arrays')
    if type(plan.get('revision')) is not int or plan['revision'] != len(history):
        raise ValueError('Revision must equal the number of review events')
    states, stacks = {}, {}
    digest = _semantic_digest(plan)
    seen_ids = set()
    for clip in clips:
        if not isinstance(clip, dict):
            raise ValueError('Clip must be an object')
        cid = _identifier(clip.get('clip_id'), 'clip ID')
        if cid.casefold() in seen_ids:
            raise ValueError('Duplicate clip ID')
        seen_ids.add(cid.casefold())
        states[cid], stacks[cid] = 'pending', []
    for seq, event in enumerate(history, 1):
        if not isinstance(event, dict):
            raise ValueError('History event must be an object')
        cid = event.get('clip_id')
        if not isinstance(cid, str) or cid not in states or type(event.get('revision')) is not int or event['revision'] != seq or event.get('from_status') != states[cid] or event.get('plan_sha256') != digest:
            raise ValueError('Invalid history order or prior state')
        action = event.get('action')
        if action in ('accept', 'reject'):
            target = 'accepted' if action == 'accept' else 'rejected'
            if target == states[cid] or 'target_revision' in event:
                raise ValueError('Redundant or malformed review')
            stacks[cid].append(event)
        elif action == 'undo':
            if not stacks[cid] or event.get('target_revision') != stacks[cid][-1]['revision']:
                raise ValueError('Undo must reference the latest active review')
            target = stacks[cid].pop()['from_status']
        else:
            raise ValueError('Invalid review action')
        if event.get('to_status') != target:
            raise ValueError('History result does not match action')
        states[cid] = target
    if any(clip.get('review_status') != states[clip['clip_id']] for clip in clips):
        raise ValueError('Clip review status does not match its history')
    return states, stacks


def _semantic_digest(plan):
    """Bind review to all plan contents except review states and history."""
    semantic = deepcopy(plan)
    semantic.pop('revision', None)
    semantic.pop('history', None)
    clips = semantic.get('clips')
    if not isinstance(clips, list) or any(not isinstance(c, dict) for c in clips):
        raise ValueError('Invalid clips for review')
    for clip in clips:
        clip.pop('review_status', None)
    try:
        data = json.dumps(semantic, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError) as error:
        raise ValueError('Plan is not canonically serializable') from error
    return sha256(data).hexdigest()


def review_clip(plan, clip_id, action):
    """Return a new revision; review JSON itself is not proof of human identity."""
    if not isinstance(plan, dict):
        raise ValueError('Plan must be an object')
    states, stacks = _history(plan)
    if not isinstance(clip_id, str) or clip_id not in states or action not in ('accept', 'reject', 'undo'):
        raise ValueError('Unknown clip or review action')
    previous = states[clip_id]
    event = {'revision': len(plan['history']) + 1, 'clip_id': clip_id, 'action': action, 'from_status': previous, 'plan_sha256': _semantic_digest(plan)}
    if action == 'undo':
        if not stacks[clip_id]:
            raise ValueError('No review event to undo')
        original = stacks[clip_id][-1]
        event.update(to_status=original['from_status'], target_revision=original['revision'])
    else:
        event['to_status'] = 'accepted' if action == 'accept' else 'rejected'
        if previous == event['to_status']:
            raise ValueError('Review action must change the state')
    result = deepcopy(plan)
    result['history'].append(event)
    result['revision'] = event['revision']
    for clip in result['clips']:
        if clip['clip_id'] == clip_id:
            clip['review_status'] = event['to_status']
    _history(result)
    return result


def validate_clip_plan(plan, source_root, ffprobe, *, require_approved=False):
    """Check IDs, source SHA/duration, timing, audio protection and review history.

    Returns source IDs to existing resolved paths. FFprobe is mandatory. Callers
    creating projects must check hashes again during/after any asset copying.
    """
    if not isinstance(plan, dict) or type(plan.get('schema_version')) is not int or plan['schema_version'] != 1:
        raise ValueError('Unsupported ClipPlan schema')
    if type(require_approved) is not bool:
        raise ValueError('require_approved must be boolean')
    states, _ = _history(plan)
    if require_approved and any(v != 'accepted' for v in states.values()):
        raise ValueError('All included clips require accepted review before export')
    output = plan.get('output')
    if not isinstance(output, dict) or any(type(output.get(k)) is not int or output[k] <= 0 for k in ('width', 'height')):
        raise ValueError('Output dimensions must be positive integers')
    if _number(output.get('fps'), 'fps') <= 0:
        raise ValueError('Output fps must be positive')
    end_time = _number(output.get('duration'), 'output duration')
    if end_time <= 0:
        raise ValueError('Output duration must be positive')
    root = Path(source_root)
    if not root.is_dir() or root.is_symlink() or root.is_junction():
        raise ValueError('Source root must be an existing directory')
    sources = plan.get('sources')
    if not isinstance(sources, list) or not sources:
        raise ValueError('At least one source is required')
    paths, probes, used_paths, source_ids = {}, {}, set(), set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError('Source must be an object')
        sid = _identifier(source.get('source_id'), 'source ID')
        if sid.casefold() in source_ids:
            raise ValueError('Duplicate source ID')
        source_ids.add(sid.casefold())
        expected = source.get('sha256')
        if not isinstance(expected, str) or not _HASH.fullmatch(expected):
            raise ValueError('Source SHA-256 must be lowercase hexadecimal')
        path = _relative_file(root, source.get('relative_path'))
        if path in used_paths:
            raise ValueError('Duplicate source path')
        used_paths.add(path)
        if file_hash(path) != expected:
            raise ValueError('Source hash mismatch')
        try:
            info = probe_media(path, ffprobe)
        except (ValueError, OSError, RuntimeError, TypeError) as error:
            raise ValueError('Source media could not be verified') from error
        if file_hash(path) != expected:
            raise ValueError('Source changed while being probed')
        real_duration = _number(info.get('duration_seconds'), 'source duration')
        declared = _number(source.get('duration_seconds'), 'declared source duration')
        streams = info.get('streams')
        if real_duration <= 0 or abs(real_duration - declared) > .001 or not isinstance(streams, list):
            raise ValueError('Source duration or streams do not match the probe')
        kind = source.get('media_type')
        if kind not in ('video', 'audio') or not any(isinstance(s, dict) and s.get('codec_type') == kind for s in streams):
            raise ValueError('Source media type does not match the probe')
        paths[sid], probes[sid] = path, info
    tracks = plan.get('tracks')
    if not isinstance(tracks, list) or not tracks:
        raise ValueError('Tracks must be a nonempty array')
    track_map = {}
    track_ids = set()
    for track in tracks:
        if not isinstance(track, dict):
            raise ValueError('Track must be an object')
        tid = _identifier(track.get('track_id'), 'track ID')
        if tid.casefold() in track_ids:
            raise ValueError('Duplicate track ID')
        track_ids.add(tid.casefold())
        if track.get('role') not in _ROLES or track.get('media_type') != _ROLES[track['role']]:
            raise ValueError('Track role must match media type')
        track_map[tid] = track
    if track_ids.intersection(cid.casefold() for cid in states):
        raise ValueError('Track and clip element IDs must be globally unique')
    intervals = {tid: [] for tid in track_map}
    used_sources = set()
    main_video_with_audio, voice_intervals, main_intervals, broll_intervals = [], [], [], []
    for clip in plan['clips']:
        sid, tid = clip.get('source_id'), clip.get('track_id')
        if not isinstance(sid, str) or not isinstance(tid, str) or sid not in paths or tid not in track_map:
            raise ValueError('Clip references an unknown source or track')
        track = track_map[tid]
        if clip.get('role') != track['role'] or clip.get('media_type') != track['media_type']:
            raise ValueError('Clip role and media type must match its track')
        if not any(isinstance(s, dict) and s.get('codec_type') == track['media_type'] for s in probes[sid]['streams']):
            raise ValueError('Source does not contain the track media type')
        evidence = clip.get('evidence')
        if not isinstance(evidence, list) or not evidence or any(not isinstance(e, str) or not e.strip() for e in evidence):
            raise ValueError('Clip requires at least one evidence reference')
        a = _number(clip.get('source_start'), 'source start')
        b = _number(clip.get('source_end'), 'source end')
        t = _number(clip.get('timeline_start'), 'timeline start')
        d = _number(clip.get('timeline_duration'), 'timeline duration')
        ad, bd, td, dd = (Decimal(str(x)) for x in (a, b, t, d))
        if not (0 <= ad < bd <= Decimal(str(probes[sid]['duration_seconds'])) and td >= 0 and dd > 0 and td + dd <= Decimal(str(end_time))):
            raise ValueError('Clip time outside source or timeline')
        if abs((bd - ad) - dd) > Decimal('0.000000001'):
            raise ValueError('Clip duration must preserve source time at normal speed')
        if _number(clip.get('speed'), 'speed') != 1 or _number(clip.get('volume'), 'volume') != 1:
            raise ValueError('V1 does not change speed or volume')
        if type(clip.get('muted')) is not bool or clip['muted'] != (clip['role'] == 'broll'):
            raise ValueError('V1 protects source voice and mutes B-roll')
        current_interval = (td, td + dd)
        intervals[tid].append(current_interval)
        if clip['role'] == 'main':
            main_intervals.append(current_interval)
            if any(isinstance(s, dict) and s.get('codec_type') == 'audio' for s in probes[sid]['streams']):
                main_video_with_audio.append(current_interval)
        elif clip['role'] == 'voice':
            voice_intervals.append(current_interval)
        elif clip['role'] == 'broll':
            broll_intervals.append(current_interval)
        used_sources.add(sid)
    if set(paths) != used_sources or any(not values for values in intervals.values()):
        raise ValueError('Unused sources and tracks are not permitted')
    for values in intervals.values():
        values.sort()
        if any(current[0] < previous[1] for previous, current in zip(values, values[1:])):
            raise ValueError('Overlapping clips on one track are not supported')
    for role_intervals in (main_intervals, voice_intervals):
        ordered = sorted(role_intervals)
        if any(current[0] < previous[1] for previous, current in zip(ordered, ordered[1:])):
            raise ValueError('Main or voice clips cannot overlap across tracks')
    if any(a < d and c < b for a, b in main_video_with_audio for c, d in voice_intervals):
        raise ValueError('Voice track overlaps main video with embedded audio')
    coverage = []
    for start, end in sorted(main_intervals):
        if coverage and start <= coverage[-1][1]:
            coverage[-1] = (coverage[-1][0], max(coverage[-1][1], end))
        else:
            coverage.append((start, end))
    if any(not any(a <= start and end <= b for a, b in coverage) for start, end in broll_intervals):
        raise ValueError('B-roll must be covered by main video')
    return paths

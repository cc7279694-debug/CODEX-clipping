"""Create a new OpenFilm 0.2.7 project from an approved ClipPlan.

This adapter never opens or modifies an existing film and never cuts source media.
It supports exact millisecond, normal-speed clips and copies assets locally.
"""
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import html
import json
from pathlib import Path
import re

from .asr import file_hash
from .clipplan import validate_clip_plan


_PROJECT_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
_RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
_EXTENSIONS = {'video': {'.mp4', '.mov', '.mkv', '.webm'},
               'audio': {'.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg'}}


def _milliseconds(value):
    """Reject rather than round unsupported time coordinates."""
    if isinstance(value, bool):
        raise ValueError('Time must be numeric')
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError('Time must be finite') from error
    if not d.is_finite() or d < 0 or d * 1000 != (d * 1000).to_integral_value():
        raise ValueError('OpenFilm export requires non-negative exact milliseconds')
    return d


def _time(value):
    d = _milliseconds(value)
    return format(d.normalize(), 'f') if d else '0'


def _safe_parent(project_dir, source_root, allowed_output_root):
    candidate = Path(project_dir)
    if '..' in candidate.parts or not _PROJECT_NAME.fullmatch(candidate.name) or candidate.name.upper() in _RESERVED:
        raise ValueError('Unsafe new project directory name')
    destination = candidate.absolute()
    parent = destination.parent
    if not parent.is_dir():
        raise ValueError('Existing project parent directory required')
    output_root = Path(allowed_output_root)
    if '..' in output_root.parts or not output_root.is_dir():
        raise ValueError('Existing authorized output root required')
    for part in (output_root, *output_root.parents, parent, *parent.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError('Linked project paths are not permitted')
    output_root = output_root.resolve(strict=True)
    if parent.resolve(strict=True) != output_root:
        raise ValueError('Project must be a direct child of the authorized output root')
    if destination.exists() or destination.is_symlink() or destination.is_junction():
        raise FileExistsError('Project directory already exists')
    root = Path(source_root).resolve(strict=True)
    if output_root.is_relative_to(root) or root.is_relative_to(output_root):
        raise ValueError('Output and source roots must not overlap')
    return destination


def _write_exclusive(path, contents):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(contents)


def _copy_verified(source, target, expected):
    digest = sha256()
    with source.open('rb') as src, target.open('xb') as dst:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            digest.update(chunk)
            dst.write(chunk)
    if digest.hexdigest() != expected or file_hash(source) != expected or file_hash(target) != expected:
        raise ValueError('Source or copied asset changed during export')


def create_openfilm_project(plan, source_root, project_dir, ffprobe, *, allowed_output_root):
    """Create one new project after validating all source files and reviews.

    The parent must exist and the new directory must not. Partial output is left
    for review on failure; sources and previously existing projects are untouched.
    FPS remains a ClipPlan setting: film.html's 0.2.7 format does not encode it.
    """
    destination = _safe_parent(project_dir, source_root, allowed_output_root)
    sources = validate_clip_plan(plan, source_root, ffprobe, require_approved=True)
    clips, tracks = plan['clips'], plan['tracks']
    source_meta = {item['source_id']: item for item in plan['sources']}
    by_track = {track['track_id']: [] for track in tracks}
    ends = []
    for clip in clips:
        start = _milliseconds(clip['source_start'])
        end = _milliseconds(clip['source_end'])
        at = _milliseconds(clip['timeline_start'])
        duration = _milliseconds(clip['timeline_duration'])
        if end - start != duration:
            raise ValueError('Source range and timeline duration differ at millisecond precision')
        ends.append(at + duration)
        by_track[clip['track_id']].append(clip)
    target_duration = _milliseconds(plan['output']['duration'])
    if not ends or max(ends) != target_duration:
        raise ValueError('OpenFilm timeline end must match the planned duration')
    for value in by_track.values():
        times = sorted((_milliseconds(c['timeline_start']), _milliseconds(c['timeline_start']) + _milliseconds(c['timeline_duration'])) for c in value)
        if any(right[0] < left[1] for left, right in zip(times, times[1:])):
            raise ValueError('Clips cannot overlap on a track')

    # Stable project-relative asset names do not expose source file names.
    asset_map = {}
    for sid, path in sources.items():
        kind = source_meta[sid]['media_type']
        suffix = path.suffix.lower()
        if suffix not in _EXTENSIONS[kind]:
            raise ValueError('Unsupported media extension for OpenFilm export')
        asset_map[sid] = 'assets/' + sid + suffix
    if len(set(name.casefold() for name in asset_map.values())) != len(asset_map):
        raise ValueError('Asset names collide on Windows')

    # Section order is visual z-order: earlier sections are above later sections.
    priority = {'broll': 0, 'main': 1, 'voice': 2, 'music': 3}
    ordered_tracks = sorted(tracks, key=lambda t: (priority[t['role']], t['track_id']))
    rows = ['<!doctype html>', '<html lang="zh-CN">', '<head>',
            '  <meta charset="utf-8"/>',
            f'  <meta name="viewport" content="width={plan["output"]["width"]}, height={plan["output"]["height"]}"/>',
            '  <title>ClipPlan OpenFilm Project</title>', '</head>', '<body>']
    for track in ordered_tracks:
        rows.append('  <section id="' + html.escape(track['track_id'], quote=True) + '">')
        for clip in sorted(by_track[track['track_id']], key=lambda c: (_milliseconds(c['timeline_start']), c['clip_id'])):
            tag = track['media_type']
            source = asset_map[clip['source_id']] + '#t=' + _time(clip['source_start']) + ',' + _time(clip['source_end'])
            attrs = 'id="' + html.escape(clip['clip_id'], quote=True) + '" src="' + html.escape(source, quote=True)
            attrs += '" at="' + _time(clip['timeline_start']) + '"'
            if clip['muted']:
                attrs += ' muted="true"'
            rows.append('    <' + tag + ' ' + attrs + '></' + tag + '>')
        rows.append('  </section>')
    rows.extend(['</body>', '</html>', ''])
    film = '\n'.join(rows)
    mapping = {'schema_version': 1, 'note': 'fps recorded for review; film.html does not set it',
               'sources': [{'source_id': sid, 'relative_path': source_meta[sid]['relative_path'],
                            'asset_path': asset_map[sid], 'sha256': source_meta[sid]['sha256']}
                           for sid in sorted(sources)]}

    destination.mkdir(exist_ok=False)
    assets = destination / 'assets'
    assets.mkdir()
    for sid in sorted(sources):
        _copy_verified(sources[sid], destination / asset_map[sid], source_meta[sid]['sha256'])
    for sid, path in sources.items():
        if file_hash(path) != source_meta[sid]['sha256']:
            raise ValueError('Source changed before project completion')
    _write_exclusive(destination / 'film.html', film)
    _write_exclusive(destination / 'source-map.json', json.dumps(mapping, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    _write_exclusive(destination / 'clipplan.json', json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return destination

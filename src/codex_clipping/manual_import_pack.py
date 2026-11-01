"""Create an isolated manual-import media package, never a Jianying draft."""
from decimal import Decimal
import json
from pathlib import Path

from .asr import file_hash
from .clipplan import validate_clip_plan
from .openfilm_adapter import _safe_parent, _copy_verified, _write_exclusive, _EXTENSIONS


def create_manual_import_pack(plan, source_root, package_dir, ffprobe, *, allowed_output_root):
    """Copy reviewed source files and timing instructions; no media is cut or imported."""
    dest = _safe_parent(package_dir, source_root, allowed_output_root)
    paths = validate_clip_plan(plan, source_root, ffprobe, require_approved=True)
    tracks = plan['tracks']
    if (len(tracks) != 2 or sum(t['role'] == 'main' for t in tracks) != 1 or
            sum(t['role'] == 'music' for t in tracks) != 1):
        raise ValueError('Manual pack supports one main and one music track only')
    video = sorted((c for c in plan['clips'] if c['role'] == 'main'), key=lambda c: c['timeline_start'])
    audio = [c for c in plan['clips'] if c['role'] == 'music']
    if not video or len(audio) != 1 or len(video) + len(audio) != len(plan['clips']):
        raise ValueError('Unsupported clips or overlay')
    total = Decimal(str(plan['output']['duration']))
    end = Decimal(0)
    for c in video:
        start = Decimal(str(c['timeline_start']))
        if start != end:
            raise ValueError('Video timeline has a gap or overlap')
        end = start + Decimal(str(c['timeline_duration']))
    if (end != total or Decimal(str(audio[0]['timeline_start'])) != 0 or
            Decimal(str(audio[0]['timeline_duration'])) != total):
        raise ValueError('Video and audio must cover the complete timeline')
    meta = {s['source_id']: s for s in plan['sources']}
    mapping = []
    for sid in sorted(paths):
        ext=paths[sid].suffix.lower()
        if ext not in _EXTENSIONS[meta[sid]['media_type']]:
            raise ValueError('Unsupported media extension')
        mapping.append({'source_id':sid, 'relative_path':meta[sid]['relative_path'],
                        'asset_path':'assets/'+sid+ext, 'sha256':meta[sid]['sha256']})
    if len({x['asset_path'].casefold() for x in mapping}) != len(mapping):
        raise ValueError('Asset collision')
    def info(c):
        return {k:c[k] for k in ('clip_id','source_id','track_id','role','media_type','review_status',
                                  'source_start','source_end','timeline_start','timeline_duration')}
    timeline={'schema_version':1,'kind':'MANUAL_IMPORT_ONLY_NOT_A_DRAFT','duration_seconds':plan['output']['duration'],
              'sources':mapping,'video_clips':[info(c) for c in video],'audio_clips':[info(c) for c in audio]}
    asset_by_id={entry['source_id']:entry['asset_path'] for entry in mapping}
    lines=['# 手动导入素材包（不是剪映草稿）','',
           '请在剪映中新建工程，手动导入 assets 中的文件，依照以下时间裁剪及排列。',
           '这些文件是未经裁剪的原素材副本，时间以秒为单位。','',
           '## 视频轨']
    for c in video:
        lines.append(f"- {asset_by_id[c['source_id']]}：源 {c['source_start']}–{c['source_end']} 秒，放在时间线第 {c['timeline_start']} 秒。")
    lines.extend(['','## 独立音轨'])
    for c in audio:
        lines.append(f"- {asset_by_id[c['source_id']]}：源 {c['source_start']}–{c['source_end']} 秒，放在时间线第 {c['timeline_start']} 秒。")
    lines.extend(['','本包不是剪映可编辑草稿；人工导入、播放和编辑尚未验证。',''])
    dest.mkdir(exist_ok=False)
    (dest/'assets').mkdir()
    for entry in mapping:
        _copy_verified(paths[entry['source_id']],dest/entry['asset_path'],entry['sha256'])
    for entry in mapping:
        if file_hash(paths[entry['source_id']]) != entry['sha256']:
            raise ValueError('Source changed during package creation')
    _write_exclusive(dest/'timeline.json',json.dumps(timeline,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    _write_exclusive(dest/'clipplan.json',json.dumps(plan,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    _write_exclusive(dest/'README.md','\n'.join(lines))
    return dest

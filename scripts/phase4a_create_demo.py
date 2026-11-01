"""Create one non-overwriting OpenFilm project from Phase 4A synthetic fixtures."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from codex_clipping.asr import file_hash
from codex_clipping.clipplan import review_clip
from codex_clipping.openfilm_adapter import create_openfilm_project


def main():
    test_root = ROOT / 'AI-Video-Workspace' / 'tests' / 'phase4a'
    fixtures = test_root / 'fixtures'
    ffprobe = ROOT / 'OpenFilm' / 'resources' / 'runtime' / 'ffmpeg' / 'ffprobe.exe'
    sources = [
        {'source_id': 'video_a', 'relative_path': 'clip-a.mp4', 'duration_seconds': 7.5, 'media_type': 'video'},
        {'source_id': 'video_b', 'relative_path': 'clip-b.mp4', 'duration_seconds': 7.5, 'media_type': 'video'},
        {'source_id': 'bed', 'relative_path': 'bed.wav', 'duration_seconds': 15, 'media_type': 'audio'},
    ]
    for source in sources:
        source['sha256'] = file_hash(fixtures / source['relative_path'])
    tracks = [{'track_id': 'main_track', 'media_type': 'video', 'role': 'main'},
              {'track_id': 'music_track', 'media_type': 'audio', 'role': 'music'}]
    def clip(cid, sid, track, start, duration, role):
        return {'clip_id': cid, 'source_id': sid, 'track_id': track, 'media_type': 'video' if role == 'main' else 'audio',
                'source_start': 0, 'source_end': duration, 'timeline_start': start, 'timeline_duration': duration,
                'speed': 1, 'volume': 1, 'muted': False, 'role': role, 'evidence': ['synthetic_fixture'],
                'review_status': 'pending'}
    plan = {'schema_version': 1, 'revision': 0, 'history': [],
            'output': {'width': 1080, 'height': 1920, 'fps': 30, 'duration': 15},
            'sources': sources, 'tracks': tracks,
            'clips': [clip('first_clip', 'video_a', 'main_track', 0, 7.5, 'main'),
                      clip('second_clip', 'video_b', 'main_track', 7.5, 7.5, 'main'),
                      clip('bed_clip', 'bed', 'music_track', 0, 15, 'music')]}
    # These approvals apply only to the intentionally authored synthetic demo.
    for item in list(plan['clips']):
        plan = review_clip(plan, item['clip_id'], 'accept')
    projects = test_root / 'projects'
    projects.mkdir(exist_ok=False)
    project = create_openfilm_project(plan, fixtures, projects / 'openfilm-project', ffprobe,
                                      allowed_output_root=projects)
    print('PROJECT_CREATED_WAITING_STUDIO_CHECK:', project)


if __name__ == '__main__':
    main()

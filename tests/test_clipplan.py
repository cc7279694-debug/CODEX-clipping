"""ClipPlan uses source seconds and never edits input media."""
import copy
import hashlib
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ClipPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'video.mp4').write_bytes(b'synthetic video')
        (self.root / 'music.wav').write_bytes(b'synthetic audio')
        sha = lambda name: hashlib.sha256((self.root / name).read_bytes()).hexdigest()
        self.plan = {
            'schema_version': 1, 'revision': 0, 'history': [],
            'output': {'width': 1080, 'height': 1920, 'fps': 30, 'duration': 15},
            'sources': [
                {'source_id': 'v1', 'relative_path': 'video.mp4', 'sha256': sha('video.mp4'), 'duration_seconds': 15, 'media_type': 'video'},
                {'source_id': 'a1', 'relative_path': 'music.wav', 'sha256': sha('music.wav'), 'duration_seconds': 15, 'media_type': 'audio'}],
            'tracks': [{'track_id': 'v', 'media_type': 'video', 'role': 'main'},
                       {'track_id': 'a', 'media_type': 'audio', 'role': 'music'}],
            'clips': [
                {'clip_id': 'v1a', 'source_id': 'v1', 'track_id': 'v', 'media_type': 'video', 'source_start': 0, 'source_end': 7.5, 'timeline_start': 0, 'timeline_duration': 7.5, 'speed': 1, 'volume': 1, 'muted': False, 'role': 'main', 'evidence': ['fixture'], 'review_status': 'pending'},
                {'clip_id': 'v1b', 'source_id': 'v1', 'track_id': 'v', 'media_type': 'video', 'source_start': 7.5, 'source_end': 15, 'timeline_start': 7.5, 'timeline_duration': 7.5, 'speed': 1, 'volume': 1, 'muted': False, 'role': 'main', 'evidence': ['fixture'], 'review_status': 'pending'},
                {'clip_id': 'a1a', 'source_id': 'a1', 'track_id': 'a', 'media_type': 'audio', 'source_start': 0, 'source_end': 15, 'timeline_start': 0, 'timeline_duration': 15, 'speed': 1, 'volume': 1, 'muted': False, 'role': 'music', 'evidence': ['fixture'], 'review_status': 'pending'}],
        }

    def module(self):
        spec = importlib.util.find_spec('codex_clipping.clipplan')
        self.assertIsNotNone(spec, 'ClipPlan validation module is missing')
        return importlib.import_module('codex_clipping.clipplan')

    def validate(self, plan=None, approved=False):
        module = self.module()
        def probe(path, ffprobe):
            is_video = Path(path).suffix == '.mp4'
            return {'duration_seconds': 15, 'streams': [{'codec_type': 'video' if is_video else 'audio'}]}
        with patch.object(module, 'probe_media', side_effect=probe):
            return module.validate_clip_plan(plan or self.plan, self.root, 'synthetic-ffprobe', require_approved=approved)

    def test_ordered_valid_plan_uses_sources_and_preserves_file_bytes(self):
        before = (self.root / 'video.mp4').read_bytes()
        paths = self.validate()
        self.assertEqual(set(paths), {'v1', 'a1'})
        self.assertEqual(paths['v1'], (self.root / 'video.mp4').resolve())
        self.assertEqual((self.root / 'video.mp4').read_bytes(), before)

    def test_invalid_ranges_duration_and_overlapping_clips_fail(self):
        for field, value in [('source_end', 16), ('source_start', -1), ('timeline_duration', 2), ('timeline_start', 7)]:
            broken = copy.deepcopy(self.plan)
            broken['clips'][1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.validate(broken)

    def test_hash_missing_file_duplicate_id_and_path_traversal_fail(self):
        broken = copy.deepcopy(self.plan); broken['sources'][0]['sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.validate(broken)
        broken = copy.deepcopy(self.plan); broken['sources'][0]['relative_path'] = '../video.mp4'
        with self.assertRaises(ValueError): self.validate(broken)
        broken = copy.deepcopy(self.plan); broken['sources'][0]['relative_path'] = 'missing.mp4'
        with self.assertRaises(ValueError): self.validate(broken)
        broken = copy.deepcopy(self.plan); broken['clips'][1]['clip_id'] = 'v1a'
        with self.assertRaises(ValueError): self.validate(broken)

    def test_pending_rejected_for_export_and_review_undo_is_reversible(self):
        module = self.module()
        with self.assertRaises(ValueError): self.validate(approved=True)
        plan = copy.deepcopy(self.plan)
        for clip in self.plan['clips']:
            plan = module.review_clip(plan, clip['clip_id'], 'accept')
        self.validate(plan, approved=True)
        undone = module.review_clip(plan, 'v1a', 'undo')
        self.assertEqual(undone['clips'][0]['review_status'], 'pending')
        self.assertEqual(plan['clips'][0]['review_status'], 'accepted')
        with self.assertRaises(ValueError): self.validate(undone, approved=True)

    def test_unsafe_voice_or_unapproved_speed_rejected(self):
        for field, value in [('speed', 2), ('volume', 0), ('muted', True)]:
            broken = copy.deepcopy(self.plan); broken['clips'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): self.validate(broken)

    def test_voice_cannot_overlap_main_video_with_embedded_audio(self):
        module = self.module()
        plan = copy.deepcopy(self.plan)
        plan['tracks'][1]['role'] = 'voice'
        plan['clips'][2]['role'] = 'voice'
        def probe(path, ffprobe):
            streams = [{'codec_type': 'video'}, {'codec_type': 'audio'}] if Path(path).suffix == '.mp4' else [{'codec_type': 'audio'}]
            return {'duration_seconds': 15, 'streams': streams}
        with patch.object(module, 'probe_media', side_effect=probe):
            with self.assertRaises(ValueError):
                module.validate_clip_plan(plan, self.root, 'synthetic-ffprobe')

    def test_source_ids_are_unique_on_windows_case_insensitive_filesystems(self):
        broken = copy.deepcopy(self.plan)
        broken['sources'][1]['source_id'] = 'V1'
        broken['clips'][2]['source_id'] = 'V1'
        with self.assertRaises(ValueError): self.validate(broken)

    def test_review_history_cannot_approve_changed_plan(self):
        module = self.module()
        reviewed = copy.deepcopy(self.plan)
        for clip in self.plan['clips']:
            reviewed = module.review_clip(reviewed, clip['clip_id'], 'accept')
        self.validate(reviewed, approved=True)
        for change in ('source_range', 'source_path', 'volume', 'output'):
            changed = copy.deepcopy(reviewed)
            if change == 'source_range':
                changed['clips'][0]['source_start'] = 0.5
                changed['clips'][0]['source_end'] = 8
            elif change == 'source_path': changed['sources'][0]['relative_path'] = 'other.mp4'
            elif change == 'volume': changed['clips'][0]['volume'] = .5
            else: changed['output']['width'] = 720
            with self.subTest(change=change), self.assertRaises(ValueError): self.validate(changed, approved=True)

    def test_track_and_clip_element_ids_cannot_collide(self):
        broken = copy.deepcopy(self.plan)
        broken['clips'][0]['clip_id'] = 'V'
        with self.assertRaises(ValueError): self.validate(broken)

    def test_decimal_adjacent_clips_do_not_false_overlap(self):
        plan = copy.deepcopy(self.plan)
        plan['clips'][0].update(source_start=0, source_end=.2, timeline_start=.1, timeline_duration=.2)
        plan['clips'][1].update(source_start=.2, source_end=.3, timeline_start=.3, timeline_duration=.1)
        self.validate(plan)
        plan['clips'][1]['timeline_start'] = .299
        with self.assertRaises(ValueError): self.validate(plan)

    def test_broll_requires_covering_main_and_is_muted(self):
        plan = copy.deepcopy(self.plan)
        plan['tracks'].append({'track_id': 'br', 'media_type': 'video', 'role': 'broll'})
        plan['clips'].append({'clip_id':'br1', 'source_id':'v1', 'track_id':'br', 'media_type':'video', 'source_start':14,
            'source_end':15, 'timeline_start':14, 'timeline_duration':1, 'speed':1, 'volume':1,
            'muted':True, 'role':'broll', 'evidence':['fixture'], 'review_status':'pending'})
        self.validate(plan)
        plan['clips'][1].update(source_end=14, timeline_duration=6.5)
        with self.assertRaises(ValueError): self.validate(plan)

    def test_main_and_voice_tracks_cannot_overlap_same_role(self):
        for role in ('main', 'voice'):
            plan = copy.deepcopy(self.plan)
            if role == 'main':
                extra = dict(plan['clips'][0], clip_id='extra', track_id='v2')
                plan['tracks'].append({'track_id': 'v2', 'media_type':'video', 'role':'main'})
            else:
                plan['tracks'][1]['role'] = 'voice'
                plan['clips'][2]['role'] = 'voice'
                plan['tracks'].append({'track_id': 'a2', 'media_type':'audio', 'role':'voice'})
                extra = dict(plan['clips'][2], clip_id='extra', track_id='a2')
            plan['clips'].append(extra)
            with self.subTest(role=role), self.assertRaises(ValueError): self.validate(plan)

    def test_clip_media_type_is_required_and_matches_track(self):
        missing = copy.deepcopy(self.plan)
        missing['clips'][0].pop('media_type')
        with self.assertRaises(ValueError): self.validate(missing)
        broken = copy.deepcopy(self.plan)
        broken['clips'][0]['media_type'] = 'audio'
        with self.assertRaises(ValueError): self.validate(broken)


if __name__ == '__main__': unittest.main()

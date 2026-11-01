"""Offline adapter tests use disposable bytes and a stubbed ClipPlan validator."""
import hashlib
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

try:
    adapter = importlib.import_module('codex_clipping.openfilm_adapter')
except ModuleNotFoundError as error:
    if error.name != 'codex_clipping.openfilm_adapter':
        raise
    adapter = None


class OpenFilmAdapterTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(adapter, 'OpenFilm adapter is not implemented')
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = self.root / 'source'
        self.sources.mkdir()
        self.out = self.root / 'projects'
        self.out.mkdir()
        self.paths = {}
        source_items = []
        for sid, filename, body, kind, duration in (
            ('a', 'a.mp4', b'video a', 'video', 7.5),
            ('b', 'b.mp4', b'video b', 'video', 7.5),
            ('music', 'sound.wav', b'audio c', 'audio', 15.0),
        ):
            f = self.sources / filename
            f.write_bytes(body)
            self.paths[sid] = f
            source_items.append({'source_id': sid, 'relative_path': filename,
                                 'sha256': hashlib.sha256(body).hexdigest(),
                                 'duration_seconds': duration, 'media_type': kind})
        def clip(cid, sid, tid, at, duration, role):
            return {'clip_id': cid, 'source_id': sid, 'track_id': tid, 'media_type': 'audio' if role == 'music' else 'video',
                    'source_start': 0, 'source_end': duration,
                    'timeline_start': at, 'timeline_duration': duration,
                    'speed': 1, 'volume': 1, 'muted': False, 'role': role,
                    'evidence': ['synthetic fixture'], 'review_status': 'accepted'}
        self.plan = {'schema_version': 1, 'revision': 1, 'history': [],
                     'output': {'width': 1080, 'height': 1920, 'fps': 30, 'duration': 15},
                     'sources': source_items,
                     'tracks': [{'track_id': 'main', 'media_type': 'video', 'role': 'main'},
                                {'track_id': 'music', 'media_type': 'audio', 'role': 'music'}],
                     'clips': [clip('a', 'a', 'main', 0, 7.5, 'main'),
                               clip('b', 'b', 'main', 7.5, 7.5, 'main'),
                               clip('sound', 'music', 'music', 0, 15, 'music')]}

    def generate(self, name='project'):
        with patch.object(adapter, 'validate_clip_plan', return_value=self.paths) as validate:
            result = adapter.create_openfilm_project(self.plan, self.sources, self.out / name, 'ffprobe', allowed_output_root=self.out)
            self.assertTrue(validate.call_args.kwargs.get('require_approved'))
            return result

    def test_deterministic_two_video_one_audio_project_and_source_hashes(self):
        before = {k: p.read_bytes() for k, p in self.paths.items()}
        self.generate('first')
        self.generate('second')
        a = self.out / 'first'
        b = self.out / 'second'
        self.assertEqual((a / 'film.html').read_bytes(), (b / 'film.html').read_bytes())
        text = (a / 'film.html').read_text(encoding='utf-8').replace('<!doctype html>', '')
        doc = ElementTree.fromstring(text)
        tracks = doc.findall('./body/section')
        self.assertEqual(len(tracks), 2)
        self.assertEqual([x.tag for x in tracks[0]], ['video', 'video'])
        self.assertEqual([x.tag for x in tracks[1]], ['audio'])
        self.assertEqual([x.attrib['at'] for x in tracks[0]], ['0', '7.5'])
        for element in list(tracks[0]) + list(tracks[1]):
            asset = element.attrib['src'].split('#', 1)[0]
            self.assertTrue((a / asset).is_file())
        self.assertEqual({k: p.read_bytes() for k, p in self.paths.items()}, before)

    def test_existing_project_never_overwritten(self):
        project = self.out / 'existing'
        project.mkdir()
        (project / 'film.html').write_bytes(b'existing')
        with self.assertRaises((FileExistsError, ValueError)):
            self.generate('existing')
        self.assertEqual((project / 'film.html').read_bytes(), b'existing')

    def test_project_name_rejects_escape(self):
        with self.assertRaises(ValueError):
            self.generate('../escape')
        self.assertFalse((self.root / 'escape').exists())

    def test_millisecond_truncation_rejected(self):
        self.plan['clips'][0]['source_end'] = 7.5001
        with self.assertRaises(ValueError):
            self.generate()

    def test_changed_source_fails_even_if_validator_stale(self):
        self.paths['a'].write_bytes(b'changed')
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(self.paths['a'].read_bytes(), b'changed')

    def test_output_must_be_under_explicit_authorized_root(self):
        with patch.object(adapter, 'validate_clip_plan', return_value=self.paths):
            with self.assertRaises(ValueError):
                adapter.create_openfilm_project(self.plan, self.sources, self.root / 'elsewhere', 'ffprobe', allowed_output_root=self.out)
        self.assertFalse((self.root / 'elsewhere').exists())

    def test_source_and_output_roots_must_not_overlap(self):
        with patch.object(adapter, 'validate_clip_plan', return_value=self.paths):
            with self.assertRaises(ValueError):
                adapter.create_openfilm_project(self.plan, self.sources, self.sources / 'nested', 'ffprobe', allowed_output_root=self.sources)

    def test_broll_above_and_muted_without_muting_main(self):
        self.plan['tracks'].append({'track_id': 'overlay', 'media_type': 'video', 'role': 'broll'})
        self.plan['clips'].append({'clip_id': 'closeup', 'source_id': 'a', 'track_id': 'overlay', 'media_type': 'video',
                                   'source_start': 0, 'source_end': 2, 'timeline_start': 1,
                                   'timeline_duration': 2, 'speed': 1, 'volume': 1,
                                   'muted': True, 'role': 'broll', 'evidence': ['synthetic'],
                                   'review_status': 'accepted'})
        self.generate()
        text = (self.out / 'project' / 'film.html').read_text(encoding='utf-8').replace('<!doctype html>', '')
        tracks = ElementTree.fromstring(text).findall('./body/section')
        self.assertEqual(tracks[0].attrib['id'], 'overlay')
        self.assertIn('muted', tracks[0][0].attrib)
        self.assertNotIn('muted', tracks[1][0].attrib)


if __name__ == '__main__':
    unittest.main()

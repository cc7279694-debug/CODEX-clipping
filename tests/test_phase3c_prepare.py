"""Offline tests for the Phase 3C collector. No actual model or packages."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

spec = importlib.util.spec_from_file_location('collector', Path(__file__).parents[1] / 'scripts' / 'phase3c_prepare.py')
collector = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(collector)
    available = True
except ModuleNotFoundError as error:
    if error.name != 'pip':
        raise
    available = False


@unittest.skipUnless(available, 'pip vendored packaging is unavailable')
class CollectorTests(unittest.TestCase):
    def test_domain_allowlist_rejects_credentials_and_other_hosts(self):
        self.assertTrue(collector.approved('https://files.pythonhosted.org/a.whl'))
        self.assertTrue(collector.approved('https://cas-bridge.xethub.hf.co/a'))
        self.assertFalse(collector.approved('https://huggingface.co.evil.invalid/a'))
        self.assertFalse(collector.approved('https://user:secret@pypi.org/a'))
        self.assertFalse(collector.approved('http://pypi.org/a'))

    def test_git_blob_is_not_raw_sha1(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            file = Path(d) / 'file'
            file.write_bytes(b'abc')
            self.assertEqual(collector.git_blob_sha1(file), hashlib.sha1(b'blob 3\0abc').hexdigest())

    def test_model_mismatch_blocks_even_if_locally_hashed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            meta = {'sha': collector.REVISION, 'id': collector.REPO,
                    'siblings': [{'rfilename': 'model.bin', 'lfs': {'sha256': '0' * 64}}]}
            def fake_download(url, path):
                path.write_bytes(b'fake')
                return hashlib.sha256(b'fake').hexdigest()
            with mock.patch.object(collector, 'fetch_json', return_value=meta), mock.patch.object(collector, 'download', side_effect=fake_download):
                with self.assertRaises(collector.Blocked):
                    collector.collect_model(Path(d), {})

    def test_wheel_mismatch_is_blocked(self):
        name = 'faster_whisper-1.2.1-py3-none-any.whl'
        release = {'filename': name, 'url': 'https://files.pythonhosted.org/x.whl',
                   'digests': {'sha256': '0' * 64}, 'requires_python': '>=3.9'}
        responses = [{'releases': {'1.2.1': [release]}}, {'urls': [release]}]
        def fake_download(url, path):
            path.write_bytes(b'fake')
            return hashlib.sha256(b'fake').hexdigest()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            with mock.patch.object(collector, 'fetch_json', side_effect=responses), mock.patch.object(collector, 'download', side_effect=fake_download):
                with self.assertRaises(collector.Blocked):
                    collector.collect_wheels(Path(d))

    def test_valid_model_ids_checked_from_official_metadata(self):
        payloads = {'config.json': b'{}', 'tokenizer.json': b'{}', 'model.bin': b'fake'}
        records = []
        for name, data in payloads.items():
            if name == 'model.bin':
                records.append({'rfilename': name, 'lfs': {'sha256': hashlib.sha256(data).hexdigest()}})
            else:
                blob = hashlib.sha1(('blob ' + str(len(data)) + '\0').encode() + data).hexdigest()
                records.append({'rfilename': name, 'blobId': blob})
        meta = {'sha': collector.REVISION, 'id': collector.REPO, 'siblings': records}
        def fake_download(url, path):
            data = payloads[path.name]
            path.write_bytes(data)
            return hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            with mock.patch.object(collector, 'fetch_json', return_value=meta), mock.patch.object(collector, 'download', side_effect=fake_download):
                result = collector.collect_model(Path(d), {})
                self.assertEqual(result['official_file_identities']['model.bin']['type'], 'lfs-sha256')
                self.assertTrue((Path(d) / 'model' / 'model-manifest.json').is_file())

    def test_junction_blocks_before_directory_creation(self):
        with mock.patch.object(Path, 'is_junction', return_value=True), mock.patch.object(Path, 'mkdir') as mkdir:
            with self.assertRaises(collector.Blocked):
                collector.main()
            mkdir.assert_not_called()

    def test_failure_evidence_redacts_exception_message(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            with mock.patch.object(collector, 'ROOT', Path(d)), mock.patch.object(collector, 'collect_wheels', side_effect=TimeoutError('secret-token')):
                self.assertEqual(collector.main(), 1)
            result_path = next(Path(d).rglob('collection-result.json'))
            text = result_path.read_text(encoding='utf-8')
            self.assertNotIn('secret-token', text)
            result = json.loads(text)
            self.assertEqual(result['wheel_collection'], 'BLOCKED')
            self.assertEqual(result['model_collection'], 'NOT_RUN')

    def test_wheel_metadata_identity_is_checked(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            wheel = Path(d) / 'x.whl'
            with zipfile.ZipFile(wheel, 'w') as z:
                z.writestr('x-1.dist-info/METADATA', 'Name: other\nVersion: 1\n')
            with self.assertRaises(collector.Blocked):
                collector.wheel_requirements(wheel, 'x', '1')

    def test_path_names_reject_traversal(self):
        for name in ('../model.bin', 'a/b', 'C:secret', 'a\\b', ''):
            self.assertFalse(collector.safe_name(name))
        self.assertTrue(collector.safe_name('.gitattributes'))

if __name__ == '__main__':
    unittest.main()

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from codex_clipping.asr import ModelError, validate_model, offline_guard
import socket


class ModelPreflightTests(unittest.TestCase):
    def fixture(self, root):
        files = {}
        for name in ('model.bin', 'config.json', 'tokenizer.json'):
            data = b'{}' if name.endswith('.json') else b'fake weights for preflight only'
            (root / name).write_bytes(data)
            files[name] = hashlib.sha256(data).hexdigest()
        manifest = {'schema_version': 1, 'repository': 'Systran/faster-whisper-base',
                    'revision': 'a' * 40, 'model': 'base', 'files': files,
                    'packages': {'faster-whisper': '1.2.1', 'ctranslate2': '4.6.0'}}
        (root / 'model-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        return manifest

    def test_complete_hash_preflight_is_not_model_load(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root = Path(d)
            self.fixture(root)
            self.assertEqual(validate_model(root)['model'], 'base')

    def test_missing_tokenizer_fails_before_import(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root = Path(d)
            self.fixture(root)
            (root / 'tokenizer.json').unlink()
            with self.assertRaises(ModelError):
                validate_model(root)

    def test_modified_weights_fail(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root = Path(d)
            self.fixture(root)
            (root / 'model.bin').write_bytes(b'corrupt')
            with self.assertRaises(ModelError):
                validate_model(root)

    def test_unpinned_revision_and_traversal_fail(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root = Path(d)
            manifest = self.fixture(root)
            manifest['revision'] = 'main'
            (root / 'model-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ModelError):
                validate_model(root)
            manifest['revision'] = 'a' * 40
            manifest['files']['../outside'] = 'a' * 64
            (root / 'model-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ModelError):
                validate_model(root)

    def test_unlisted_file_and_invalid_json_fail(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root = Path(d)
            self.fixture(root)
            (root / 'extra.bin').write_bytes(b'unknown')
            with self.assertRaises(ModelError):
                validate_model(root)

    def test_python_offline_guard_blocks_without_making_a_connection(self):
        original = socket.socket.connect
        with offline_guard():
            with socket.socket() as client:
                with self.assertRaises(ModelError):
                    client.connect(('127.0.0.1', 1))
            with self.assertRaises(ModelError):
                socket.create_connection(('example.invalid', 443))
        self.assertIs(socket.socket.connect, original)

    def test_non_object_manifest_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root = Path(d)
            (root / 'model-manifest.json').write_text('[]')
            with self.assertRaises(ModelError):
                validate_model(root)

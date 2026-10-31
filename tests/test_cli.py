import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from codex_clipping.cli import main, propose
from codex_clipping.decisions import build_decisions


class ReviewCommandTests(unittest.TestCase):
    def test_propose_review_and_undo_new_json_files_only(self):
        # Explicit orchestration fixture. This test does not run ASR.
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            source = root / 'synthetic-fixture.bin'
            source.write_bytes(b'not audio; review integration fixture')
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            document = build_decisions({'sha256': digest, 'duration_seconds': 10},
                                       [{'start': 0., 'end': 1., 'text': '测试'}],
                                       [{'start': 3., 'end': 7.}], asr={'engine': 'faster-whisper'})
            entries = {'base.json': document,
                       'silence.json': {'source_sha256': digest, 'status': 'PASS', 'time_base': 'source_seconds', 'candidates': [{'start': 3., 'end': 7.}]},
                       'manual.json': {'schema_version': 1, 'source_sha256': digest, 'protection_reviewed': True, 'protected_intervals': [{'start': 0., 'end': 1., 'kind': 'speech'}]}}
            for name, value in entries.items():
                (root / name).write_text(json.dumps(value), encoding='utf-8')
            proposal = root / 'proposal.json'
            made = propose(root / 'base.json', root / 'silence.json', root / 'manual.json', source, proposal)
            identifier = made['suggestions'][0]['id']
            self.assertEqual(made['suggestions'][0]['status'], 'pending')
            reviewed = root / 'accepted.json'
            self.assertEqual(main(['review', '--input', str(proposal), '--source', str(source), '--id', identifier, '--action', 'accept', '--out', str(reviewed)]), 0)
            undone = root / 'undone.json'
            self.assertEqual(main(['review', '--input', str(reviewed), '--source', str(source), '--id', identifier, '--action', 'undo', '--out', str(undone)]), 0)
            final = json.loads(undone.read_text(encoding='utf-8'))
            self.assertEqual(final['suggestions'][0]['status'], 'pending')
            self.assertEqual(len(final['review_history']), 2)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)
            self.assertEqual(main(['review', '--input', str(proposal), '--source', str(source), '--id', identifier, '--action', 'reject', '--out', str(reviewed)]), 2)
            annotations = entries['manual.json']
            annotations['protected_intervals'] = [None]
            (root / 'manual.json').write_text(json.dumps(annotations))
            self.assertEqual(main(['propose', '--decisions', str(root / 'base.json'), '--silence', str(root / 'silence.json'), '--annotations', str(root / 'manual.json'), '--source', str(source), '--out', str(root / 'bad.json')]), 2)

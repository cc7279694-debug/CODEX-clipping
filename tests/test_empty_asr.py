"""Empty ASR output does not imply subtitles or absence of speech."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_clipping.pipeline import analyze


class EmptyTranscriptionTests(unittest.TestCase):
    def test_empty_asr_is_not_subtitle_success_or_proof_of_silence(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            source = Path(d) / 'fixture.bin'
            source.write_bytes(b'synthetic orchestration fixture')
            out = Path(d) / 'result'
            with patch('codex_clipping.pipeline.probe_media', return_value={
                    'duration_seconds': 6, 'streams': [{'codec_type': 'audio'}]}), \
                 patch('codex_clipping.pipeline.detect_silence', return_value=[{'start': 2., 'end': 4.}]), \
                 patch('codex_clipping.pipeline.extract_audio'), \
                 patch('codex_clipping.pipeline.transcribe_local', return_value=([], {'engine': 'fake'})):
                result = analyze(source, out, 'ffmpeg', 'ffprobe', 'fake-model')
            self.assertEqual(result['stages']['asr'], 'PASS')
            self.assertEqual(result['stages']['subtitles'], 'NOT_RUN')
            self.assertEqual(result['transcript_status'], 'ASR_NO_TEXT_REQUIRES_HUMAN_REVIEW')
            self.assertEqual((out / 'transcript.srt').read_text(encoding='utf-8'), '')
            decisions = json.loads((out / 'edit-decisions.json').read_text(encoding='utf-8'))
            self.assertEqual(decisions['suggestions'], [])
            self.assertFalse(decisions['policy']['speech_evidence_complete'])
            self.assertTrue(result['source']['sha256_unchanged'])


if __name__ == '__main__':
    unittest.main()

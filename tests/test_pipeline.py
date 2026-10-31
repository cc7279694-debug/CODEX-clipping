from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from codex_clipping.pipeline import analyze


class PipelineSafetyTests(unittest.TestCase):
    def test_orchestration_with_explicit_fake_transcriber_is_not_asr_validation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            source = Path(d) / 'fixture.bin'
            source.write_bytes(b'not speech; orchestration only')
            out = Path(d) / 'new'
            with patch('codex_clipping.pipeline.probe_media', return_value={'duration_seconds': 6, 'streams': [{'codec_type': 'audio'}]}), \
                 patch('codex_clipping.pipeline.detect_silence', return_value=[{'start': 2., 'end': 4.}]), \
                 patch('codex_clipping.pipeline.extract_audio'), \
                 patch('codex_clipping.pipeline.transcribe_local', return_value=([{'start': .5, 'end': 1.5, 'text': '明确的测试文字'}], {'engine': 'TEST_DOUBLE_NOT_ASR'})):
                result = analyze(source, out, 'ffmpeg', 'ffprobe', 'fake-model')
            self.assertEqual(result['status'], 'READY_FOR_REVIEW')
            self.assertIn('00:00:00,500 --> 00:00:01,500', (out / 'transcript.srt').read_text(encoding='utf-8'))
            self.assertTrue(result['source']['sha256_unchanged'])

    def test_changed_source_invalidates_outputs(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            source = Path(d) / 'fixture.bin'
            source.write_bytes(b'original orchestration fixture')
            out = Path(d) / 'new'
            def unexpected_source_change(*args):
                source.write_bytes(b'simulated unexpected external mutation')
            with patch('codex_clipping.pipeline.probe_media', return_value={'duration_seconds': 6, 'streams': [{'codec_type': 'audio'}]}), \
                 patch('codex_clipping.pipeline.detect_silence', return_value=[]), \
                 patch('codex_clipping.pipeline.extract_audio', side_effect=unexpected_source_change), \
                 patch('codex_clipping.pipeline.transcribe_local', return_value=([{'start': .5, 'end': 1.5, 'text': '测试文字'}], {'engine': 'TEST_DOUBLE_NOT_ASR'})):
                result = analyze(source, out, 'ffmpeg', 'ffprobe', 'fake-model')
            self.assertEqual(result['status'], 'BLOCKED')
            self.assertFalse(result['source']['sha256_unchanged'])
            self.assertEqual((out / 'transcript.srt').read_text(encoding='utf-8'), '')

    def test_existing_output_rejected_before_reading_source(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            with self.assertRaises(FileExistsError):
                analyze('not-a-source', Path(d), 'ffmpeg', 'ffprobe', 'missing-model')

    def test_no_audio_does_not_call_asr(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            source = Path(d) / 'synthetic.bin'
            source.write_bytes(b'explicit orchestration test, not audio')
            with patch('codex_clipping.pipeline.probe_media', return_value={'duration_seconds': 6, 'streams': []}), \
                 patch('codex_clipping.pipeline.transcribe_local') as asr:
                result = analyze(source, Path(d) / 'new', 'ffmpeg', 'ffprobe', 'missing-model')
                self.assertEqual(result['status'], 'BLOCKED')
                self.assertTrue(result['source']['sha256_unchanged'])
                asr.assert_not_called()

    def test_missing_model_produces_no_fabricated_transcript(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            source = Path(d) / 'synthetic.bin'
            source.write_bytes(b'explicit orchestration test, not audio')
            out = Path(d) / 'new'
            with patch('codex_clipping.pipeline.probe_media', return_value={'duration_seconds': 6, 'streams': [{'codec_type': 'audio'}]}), \
                 patch('codex_clipping.pipeline.detect_silence', return_value=[{'start': 2., 'end': 4.}]), \
                 patch('codex_clipping.pipeline.extract_audio'):
                result = analyze(source, out, 'ffmpeg', 'ffprobe', 'missing-model')
                self.assertEqual(result['status'], 'BLOCKED')
                self.assertEqual((out / 'transcript.srt').read_text(encoding='utf-8'), '')
                self.assertEqual(result['stages']['asr'], 'BLOCKED')
                self.assertTrue(result['source']['sha256_unchanged'])
                self.assertIn('"suggestions": []', (out / 'edit-decisions.json').read_text(encoding='utf-8'))

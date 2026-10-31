import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codex_clipping.subtitles import render_srt, validate_transcript_segments, write_srt


class SubtitleTests(unittest.TestCase):
    def test_chinese_content_and_source_timestamps_preserved(self):
        value = render_srt([
            {'start': 1.25, 'end': 2.5, 'text': '我是文科生。'},
            {'start': 4, 'end': 5.001, 'text': '用 AI 做 APP。'},
        ], 12)
        self.assertEqual(value, '1\n00:00:01,250 --> 00:00:02,500\n我是文科生。\n\n2\n00:00:04,000 --> 00:00:05,001\n用 AI 做 APP。\n')

    def test_empty_asr_result_remains_empty(self):
        self.assertEqual(render_srt([], 10), '')

    def test_no_time_normalization_for_overlap_or_wrong_order(self):
        for segments in [
            [{'start': 2, 'end': 4, 'text': '甲'}, {'start': 3, 'end': 5, 'text': '乙'}],
            [{'start': 5, 'end': 6, 'text': '甲'}, {'start': 1, 'end': 2, 'text': '乙'}],
        ]:
            with self.assertRaises(ValueError):
                render_srt(segments, 10)

    def test_invalid_intervals_fail_instead_of_guessing(self):
        for start, end in [(-1, 1), (1, 1), (2, 1), (9, 11), (float('nan'), 3), (True, 3)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                render_srt([{'start': start, 'end': end, 'text': '中文'}], 10)

    def test_submillisecond_zero_srt_interval_rejected(self):
        with self.assertRaises(ValueError):
            render_srt([{'start': 0.0001, 'end': 0.0002, 'text': '短'}], 1)

    def test_empty_text_and_embedded_block_separator_rejected(self):
        for text in ['', '  ', None, '一\n\n二']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                render_srt([{'start': 0, 'end': 1, 'text': text}], 2)

    def test_duplicate_segment_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate_transcript_segments([
                {'id': 's1', 'start': 0, 'end': 1, 'text': '一'},
                {'id': 's1', 'start': 1, 'end': 2, 'text': '二'},
            ], 3)

    def test_rounding_handles_minute_and_hour_carry(self):
        value = render_srt([{'start': 3599.9996, 'end': 3601, 'text': '时间'}], 3602)
        self.assertIn('01:00:00,000 --> 01:00:01,000', value)

    def test_exclusive_utf8_write_does_not_replace_existing_file(self):
        directory = Path(__file__).resolve().parent / ('.subtitle-test-' + uuid.uuid4().hex)
        directory.mkdir()
        path = directory / 'output.srt'
        try:
            write_srt(path, [{'start': 0, 'end': 1, 'text': '中文'}], 2)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_srt(path, [{'start': 0, 'end': 1, 'text': '替换'}], 2)
            self.assertEqual(path.read_bytes(), before)
            self.assertIn('中文', path.read_text(encoding='utf-8'))
        finally:
            path.unlink(missing_ok=True)
            directory.rmdir()


if __name__ == '__main__':
    unittest.main()

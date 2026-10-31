import unittest
from codex_clipping.media import parse_silence, validate_origin


class SilenceParserTests(unittest.TestCase):
    def test_known_gap_and_trailing_gap_use_source_time(self):
        result = parse_silence('silence_start: 2\nsilence_end: 4.000063 | silence_duration: 2\nsilence_start: 5\n', 6)
        self.assertEqual(result, [{'start': 2.0, 'end': 4.000063}, {'start': 5.0, 'end': 6.0}])

    def test_invalid_sequence_fails(self):
        for log in ('silence_end: 1', 'silence_start: 4\nsilence_end: 2', 'silence_start: 1\nsilence_start: 2'):
            with self.assertRaises(ValueError):
                parse_silence(log, 6)

    def test_empty_log_not_speech_evidence(self):
        self.assertEqual(parse_silence('', 6), [])

    def test_delayed_audio_and_unknown_origins_rejected(self):
        for info in ({'format': {'start_time': '0'}, 'streams': [{'codec_type': 'audio', 'start_time': '.5'}]},
                     {'format': {'format_name': 'mov'}, 'streams': []}):
            with self.assertRaises(ValueError):
                validate_origin(info)
        validate_origin({'format': {'format_name': 'wav'}, 'streams': [{'codec_type': 'audio'}]})

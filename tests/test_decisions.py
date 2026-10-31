from copy import deepcopy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codex_clipping.decisions import build_decisions, review_decision, validate_decisions

SHA = 'a' * 64
SOURCE = {'sha256': SHA, 'duration_seconds': 20, 'relative_path': 'media/test.wav'}
TRANSCRIPT = [{'start': 0, 'end': 2, 'text': '开始。'}, {'start': 10, 'end': 12, 'text': '继续。'}]


def ready_document():
    return build_decisions(SOURCE, TRANSCRIPT, [{'start': 3, 'end': 7}], speech_evidence_complete=True)


class DecisionTests(unittest.TestCase):
    def test_default_protection_gate_has_no_delete_suggestions(self):
        value = build_decisions(SOURCE, TRANSCRIPT, [{'start': 3, 'end': 7}])
        self.assertEqual(value['suggestions'], [])
        self.assertEqual(value['excluded_candidates'][0]['reason'], 'speech_protection_evidence_incomplete')
        self.assertIs(value['execution_enabled'], False)

    def test_empty_transcript_is_not_evidence_to_delete_audio(self):
        value = build_decisions(SOURCE, [], [{'start': 3, 'end': 7}], speech_evidence_complete=True)
        self.assertEqual(value['suggestions'], [])

    def test_protected_candidate_is_pending_in_source_time_with_context(self):
        value = ready_document()
        self.assertEqual(value['time_base'], 'source_seconds')
        self.assertEqual(value['suggestions'][0]['start'], 3.35)
        self.assertEqual(value['suggestions'][0]['end'], 6.65)
        self.assertEqual(value['suggestions'][0]['status'], 'pending')
        self.assertIn('manual_review', value['suggestions'][0]['risk'])

    def test_short_natural_pause_retained(self):
        value = build_decisions(SOURCE, TRANSCRIPT, [{'start': 3, 'end': 4.5}], speech_evidence_complete=True)
        self.assertEqual(value['suggestions'], [])

    def test_low_speech_laughter_and_annotated_pause_are_protected(self):
        for kind in ['quiet_speech', 'laughter', 'natural_pause']:
            value = build_decisions(SOURCE, TRANSCRIPT, [{'start': 3, 'end': 7}],
                protected_intervals=[{'start': 5, 'end': 5.2, 'kind': kind}], speech_evidence_complete=True)
            self.assertEqual(value['suggestions'], [], kind)

    def test_speech_boundary_padding_is_protected(self):
        value = build_decisions(SOURCE, TRANSCRIPT, [{'start': 2.1, 'end': 5}], speech_evidence_complete=True)
        self.assertEqual(value['suggestions'], [])

    def test_invalid_source_hash_and_external_path_rejected(self):
        for source in [dict(SOURCE, sha256='bad'), dict(SOURCE, relative_path='../private.wav'),
                       dict(SOURCE, relative_path='C:\\private.wav')]:
            with self.subTest(source=source), self.assertRaises(ValueError):
                build_decisions(source, TRANSCRIPT, [])

    def test_invalid_or_overlapping_silence_is_not_silently_merged(self):
        for intervals in [[{'start': -1, 'end': 2}], [{'start': 3, 'end': 7}, {'start': 6, 'end': 8}]]:
            with self.assertRaises(ValueError):
                build_decisions(SOURCE, TRANSCRIPT, intervals)

    def test_accept_reject_and_undo_replay_last_active_action(self):
        original = ready_document()
        first = review_decision(original, 'cut-0001', 'accept', source_sha256=SHA)
        second = review_decision(first, 'cut-0001', 'reject', source_sha256=SHA)
        third = review_decision(second, 'cut-0001', 'undo', source_sha256=SHA)
        fourth = review_decision(third, 'cut-0001', 'undo', source_sha256=SHA)
        self.assertEqual([x['suggestions'][0]['status'] for x in [original, first, second, third, fourth]],
                         ['pending', 'accepted', 'rejected', 'accepted', 'pending'])
        self.assertEqual(fourth['review_history'][:2], second['review_history'])
        self.assertEqual(len(fourth['review_history']), 4)
        self.assertEqual(original['review_history'], [])
        self.assertIs(fourth['execution_enabled'], False)

    def test_undo_without_review_and_duplicate_accept_rejected(self):
        value = ready_document()
        with self.assertRaises(ValueError):
            review_decision(value, 'cut-0001', 'undo', source_sha256=SHA)
        accepted = review_decision(value, 'cut-0001', 'accept', source_sha256=SHA)
        with self.assertRaises(ValueError):
            review_decision(accepted, 'cut-0001', 'accept', source_sha256=SHA)

    def test_different_source_hash_fails_without_mutating_document(self):
        value = ready_document()
        before = deepcopy(value)
        with self.assertRaises(ValueError):
            review_decision(value, 'cut-0001', 'accept', source_sha256='b' * 64)
        self.assertEqual(value, before)

    def test_tampered_status_or_history_rejected(self):
        value = review_decision(ready_document(), 'cut-0001', 'accept', source_sha256=SHA)
        for mutate in [lambda d: d['suggestions'][0].update(status='pending'),
                       lambda d: d['review_history'][0].update(source_sha256='b'*64),
                       lambda d: d['review_history'][0].update(to_status='rejected')]:
            broken = deepcopy(value)
            mutate(broken)
            with self.assertRaises(ValueError):
                validate_decisions(broken)

    def test_media_execution_cannot_be_enabled_by_json(self):
        value = ready_document()
        value['execution_enabled'] = True
        with self.assertRaises(ValueError):
            validate_decisions(value)

    def test_tampered_transcript_interval_rejected(self):
        value = ready_document()
        value['transcript_segments'][0]['end'] = 99
        with self.assertRaises(ValueError):
            validate_decisions(value)

    def test_non_object_suggestion_and_history_fail_with_validation_error(self):
        value = ready_document()
        value['suggestions'] = [None]
        with self.assertRaises(ValueError):
            validate_decisions(value)
        value = ready_document()
        value['review_history'] = [None]
        with self.assertRaises(ValueError):
            validate_decisions(value)


if __name__ == '__main__':
    unittest.main()

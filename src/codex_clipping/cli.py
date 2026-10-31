"""Local command line: analyze, then review JSON. No cutting command exists."""
import argparse
import json
from pathlib import Path
import sys

from .asr import file_hash, validate_model
from .decisions import build_decisions, review_decision, validate_decisions
from .pipeline import analyze, write_json


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def propose(decisions_path, silence_path, annotations_path, source, output):
    document, silence, annotations = map(read_json, (decisions_path, silence_path, annotations_path))
    validate_decisions(document)
    digest = file_hash(source)
    if digest != document['source']['sha256'] or silence.get('source_sha256') != digest or annotations.get('source_sha256') != digest:
        raise ValueError('Source hashes do not match')
    if document['review_history']:
        raise ValueError('Use the original analysis before review to create a new proposal revision')
    if not document.get('asr') or document['asr'].get('engine') != 'faster-whisper':
        raise ValueError('Successful real ASR output required; no guessed transcript fallback')
    if silence.get('status') != 'PASS' or silence.get('time_base') != 'source_seconds':
        raise ValueError('Valid source-time silence results required')
    if annotations.get('schema_version') != 1 or annotations.get('protection_reviewed') is not True:
        raise ValueError('Explicit manual speech/laughter/natural-pause review required')
    intervals = annotations.get('protected_intervals')
    if not isinstance(intervals, list) or any(not isinstance(x, dict) or x.get('kind') not in ('speech', 'laughter', 'natural_pause') for x in intervals):
        raise ValueError('Protected intervals must identify speech, laughter or natural pauses')
    result = build_decisions(document['source'], document['transcript_segments'], silence['candidates'],
                             protected_intervals=intervals, asr=document['asr'], speech_evidence_complete=True)
    result['protection_review'] = {'origin': 'manual_attestation_not_automatic_detection', 'protected_intervals': intervals}
    write_json(output, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local Chinese speech analysis; review only, never cuts media.')
    sub = parser.add_subparsers(dest='command', required=True)
    run = sub.add_parser('analyze')
    for name in ('source', 'out', 'ffmpeg', 'ffprobe', 'model'):
        run.add_argument('--' + name, required=True)
    run.add_argument('--threads', type=int, default=2, choices=range(1, 5))
    check = sub.add_parser('check-model', help='File/hash preflight only; does not load ASR')
    check.add_argument('--model', required=True)
    review = sub.add_parser('review')
    for name in ('input', 'source', 'id', 'out'):
        review.add_argument('--' + name, required=True)
    review.add_argument('--action', choices=('accept', 'reject', 'undo'), required=True)
    review.add_argument('--note', default='')
    proposal = sub.add_parser('propose', help='Manual protection review must precede conservative proposals')
    for name in ('decisions', 'silence', 'annotations', 'source', 'out'):
        proposal.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'analyze':
            result = analyze(args.source, args.out, args.ffmpeg, args.ffprobe, args.model, threads=args.threads)
            print(json.dumps({'status': result['status'], 'stages': result['stages']}, ensure_ascii=True))
            return 0 if result['status'] == 'READY_FOR_REVIEW' else 2
        if args.command == 'check-model':
            manifest = validate_model(args.model)
            print(json.dumps({'preflight': 'PASS', 'model': manifest['model'], 'revision': manifest['revision'], 'asr_load': 'NOT_RUN'}))
        elif args.command == 'review':
            document = read_json(args.input)
            result = review_decision(document, args.id, args.action, source_sha256=file_hash(args.source), note=args.note)
            write_json(args.out, result)
            print('REVIEW_SAVED_NO_MEDIA_CHANGED')
        else:
            result = propose(args.decisions, args.silence, args.annotations, args.source, args.out)
            print(json.dumps({'suggestions': len(result['suggestions']), 'execution_enabled': False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        print(json.dumps({'status': 'BLOCKED', 'error_type': type(error).__name__, 'message': str(error)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

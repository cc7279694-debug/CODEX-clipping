"""Analysis-only pipeline. Each invocation creates a new output directory."""
import ctypes
import json
from pathlib import Path
import time

from .asr import file_hash, transcribe_local
from .decisions import build_decisions
from .media import probe_media, extract_audio, detect_silence
from .subtitles import render_srt, validate_transcript_segments


def write_json(path, data):
    with Path(path).open('x', encoding='utf-8', newline='\n') as output:
        json.dump(data, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write('\n')


def peak_working_set():
    """Peak for this Python process only, including in-process ASR, not child tools."""
    if not hasattr(ctypes, 'windll'):
        return None
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    api = ctypes.windll.psapi.GetProcessMemoryInfo
    api.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    if api(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return counters.PeakWorkingSetSize
    return None


def analyze(source, output_dir, ffmpeg, ffprobe, model_dir, *, threads=2):
    """Produce review artifacts. No automatic cut execution or cloud fallback exists."""
    out = Path(output_dir).absolute()
    if out.exists():
        raise FileExistsError('Choose a new output directory; existing data is never overwritten')
    source = Path(source).absolute()
    if not source.is_file() or source.is_symlink():
        raise ValueError('A regular explicitly authorized local test source is required')
    if any(parent.is_symlink() for parent in source.parents):
        raise ValueError('Linked source path rejected')
    digest = file_hash(source)
    out.mkdir(parents=True, exist_ok=False)
    started, cpu_started = time.perf_counter(), time.process_time()
    result = {'schema_version': 1, 'status': 'BLOCKED',
              'source': {'name': source.name, 'sha256': digest},
              'stages': {'probe': 'NOT_RUN', 'silence': 'NOT_RUN', 'asr': 'NOT_RUN',
                         'subtitles': 'NOT_RUN', 'decisions': 'NOT_RUN'},
              'errors': [], 'scope': 'analysis_only; no media cutting',
              'transcript_status': 'NOT_RUN'}
    transcript, silence, asr = [], [], None
    duration = None
    try:
        media = probe_media(source, ffprobe)
        duration = media['duration_seconds']
        result['media'] = media
        result['stages']['probe'] = 'PASS'
        if not any(s.get('codec_type') == 'audio' for s in media['streams']):
            raise ValueError('No audio stream; transcription was not attempted')
        extract_audio(source, out / 'analysis-audio.wav', ffmpeg)
        silence = detect_silence(out / 'analysis-audio.wav', ffmpeg, duration)
        result['stages']['silence'] = 'PASS'
        asr_started = time.perf_counter()
        try:
            transcript, asr = transcribe_local(out / 'analysis-audio.wav', model_dir, threads)
            transcript = validate_transcript_segments(transcript, duration)
            result['stages']['asr'] = 'PASS'
            result['transcript_status'] = ('ASR_OUTPUT_REQUIRES_HUMAN_REVIEW' if transcript
                                           else 'ASR_NO_TEXT_REQUIRES_HUMAN_REVIEW')
        except Exception:
            result['stages']['asr'] = 'BLOCKED'
            raise
        finally:
            result['asr_seconds'] = time.perf_counter() - asr_started
    except Exception as error:
        result['errors'].append({'type': type(error).__name__, 'message': str(error)})
    # If inference or timestamp validation failed, never expose partial guessed text.
    if result['stages']['asr'] != 'PASS':
        transcript, asr = [], None
    try:
        after = file_hash(source)
        result['source']['sha256_after'] = after
        unchanged = after == digest
    except OSError:
        unchanged = False
    result['source']['sha256_unchanged'] = unchanged
    if not unchanged:
        transcript, silence, asr = [], [], None
        result['errors'].append({'type': 'SourceChanged', 'message': 'Source hash changed; results invalidated'})
    srt = render_srt(transcript, duration) if duration else ''
    with (out / 'transcript.srt').open('x', encoding='utf-8', newline='\n') as output:
        output.write(srt)
    result['stages']['subtitles'] = 'PASS' if result['stages']['asr'] == 'PASS' and unchanged and transcript else 'NOT_RUN'
    write_json(out / 'silence-candidates.json', {'schema_version': 1, 'time_base': 'source_seconds',
               'source_sha256': digest, 'status': result['stages']['silence'] if unchanged else 'INVALIDATED',
               'settings': {'noise_db': -35, 'minimum_seconds': 2}, 'candidates': silence,
               'note': 'Low-level intervals are not proof of absent speech, laughter or useful pauses'})
    if duration and unchanged:
        decision_source = {'sha256': digest, 'duration_seconds': duration, 'name': source.name}
        decisions = build_decisions(decision_source, transcript, silence, asr=asr,
                                    speech_evidence_complete=False)
        result['stages']['decisions'] = 'PASS'
    else:
        decisions = {'schema_version': 1, 'status': 'BLOCKED', 'source_sha256': digest,
                     'suggestions': [], 'review_history': [], 'media_execution_allowed': False}
    write_json(out / 'edit-decisions.json', decisions)
    result['asr'] = asr
    result['resources'] = {'wall_seconds': time.perf_counter() - started,
                           'cpu_seconds': time.process_time() - cpu_started,
                           'peak_working_set_bytes': peak_working_set(),
                           'scope': 'current Python process only; excludes FFmpeg child, not a model benchmark',
                           'rtf': (time.perf_counter() - started) / duration if duration else None}
    if result['stages']['asr'] == 'PASS' and unchanged and not result['errors']:
        result['status'] = 'READY_FOR_REVIEW'
    write_json(out / 'metadata.json', result)
    return result

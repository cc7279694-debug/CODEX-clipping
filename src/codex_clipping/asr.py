"""Fail-closed local faster-whisper adapter; real inference needs locked assets."""
from contextlib import contextmanager
from hashlib import sha256
from importlib import metadata
import json
import os
from pathlib import Path
import re
import socket
import wave


class ModelError(ValueError):
    pass


def read_pcm16_mono(path):
    """Read the pipeline's normalized WAV without shifting or guessing its timing."""
    import numpy as np

    try:
        with wave.open(str(path), 'rb') as source:
            if (source.getnchannels() != 1 or source.getsampwidth() != 2 or
                    source.getframerate() != 16000 or source.getcomptype() != 'NONE'):
                raise ModelError('Expected uncompressed mono 16 kHz signed 16-bit WAV')
            frame_count = source.getnframes()
            if frame_count <= 0:
                raise ModelError('Empty audio cannot be transcribed')
            data = source.readframes(frame_count)
            if len(data) != frame_count * 2:
                raise ModelError('Truncated audio cannot be transcribed')
    except (wave.Error, EOFError) as error:
        raise ModelError('Invalid WAV input') from error
    return np.frombuffer(data, dtype='<i2').astype(np.float32) / 32768.0


def file_hash(path):
    digest = sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_model(directory):
    """Validate asset integrity only; this never imports or loads an ASR engine."""
    root = Path(directory).absolute()
    if root.is_symlink() or not root.is_dir():
        raise ModelError('Local model directory is missing or is a link')
    manifest_path = root / 'model-manifest.json'
    if manifest_path.is_symlink():
        raise ModelError('Linked manifest rejected')
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest['schema_version'] != 1 or manifest['model'] not in ('base', 'small'):
            raise ModelError('Use a schema 1 multilingual base or small model')
        if manifest['repository'] != 'Systran/faster-whisper-' + manifest['model']:
            raise ModelError('Unexpected official model repository')
        if not re.fullmatch(r'[0-9a-f]{40}', manifest['revision']):
            raise ModelError('An immutable official model revision is required')
        files = manifest['files']
        if not isinstance(files, dict) or not {'model.bin', 'config.json', 'tokenizer.json'} <= files.keys():
            raise ModelError('Critical model files missing from manifest')
        packages = manifest['packages']
        if not isinstance(packages, dict) or not {'faster-whisper', 'ctranslate2'} <= packages.keys():
            raise ModelError('Pinned engine package versions required')
        for name, expected in files.items():
            rel = Path(name)
            if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name or name == 'model-manifest.json':
                raise ModelError('Unsafe manifest path')
            path = root / rel
            if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
                raise ModelError('Linked asset rejected')
            if not re.fullmatch(r'[0-9a-f]{64}', expected) or not path.is_file() or file_hash(path) != expected:
                raise ModelError('Asset missing or hash mismatch: ' + name)
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        if actual != set(files) | {'model-manifest.json'}:
            raise ModelError('Model directory contains unlisted files')
        for name in ('config.json', 'tokenizer.json'):
            if not isinstance(json.loads((root / name).read_text(encoding='utf-8')), dict):
                raise ModelError('Invalid JSON model asset')
        if any(not isinstance(v, str) or not v.strip() for v in packages.values()):
            raise ModelError('Invalid pinned package version')
        return manifest
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ModelError('Incomplete or malformed local model manifest') from error


@contextmanager
def offline_guard():
    """Process-local Python socket guard; not an OS network policy or proof of native isolation."""
    changes = {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
               'HF_HUB_DISABLE_TELEMETRY': '1', 'DO_NOT_TRACK': '1'}
    previous = {k: os.environ.get(k) for k in changes}
    saved = (socket.socket.connect, socket.socket.connect_ex, socket.create_connection)
    def blocked(*args, **kwargs):
        raise ModelError('Network access forbidden during local ASR')
    try:
        os.environ.update(changes)
        socket.socket.connect = blocked
        socket.socket.connect_ex = blocked
        socket.create_connection = blocked
        yield
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection = saved
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def transcribe_local(wav_path, model_directory, threads=2):
    if isinstance(threads, bool) or not isinstance(threads, int) or not 1 <= threads <= 4:
        raise ModelError('CPU thread limit must be 1 through 4')
    manifest = validate_model(model_directory)
    wav = Path(wav_path)
    if not wav.is_file() or wav.is_symlink():
        raise ModelError('A regular local WAV file is required')
    runtime_packages = {}
    try:
        for name, version in manifest['packages'].items():
            runtime_packages[name] = metadata.version(name)
            if runtime_packages[name] != version:
                raise ModelError('Installed package does not match lock: ' + name)
        required = {'faster-whisper', 'ctranslate2', 'tokenizers', 'av', 'huggingface-hub', 'onnxruntime', 'tqdm', 'numpy'}
        if not required <= manifest['packages'].keys():
            raise ModelError('Runtime dependency versions are not fully recorded')
        with offline_guard():
            from faster_whisper import WhisperModel
            audio = read_pcm16_mono(wav)
            model = WhisperModel(str(Path(model_directory).resolve()), device='cpu',
                                 compute_type='int8', cpu_threads=threads, num_workers=1,
                                 local_files_only=True)
            iterator, info = model.transcribe(audio, language='zh', task='transcribe',
                                             beam_size=1, vad_filter=False,
                                             condition_on_previous_text=False, word_timestamps=False)
            segments = [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in iterator]
        # ASR is evidence for review, not proof that quiet speech/laughter is absent.
        return segments, {'engine': 'faster-whisper', 'model': manifest['model'],
                          'revision': manifest['revision'], 'packages': runtime_packages,
                          'device': 'cpu', 'compute_type': 'int8', 'threads': threads,
                          'language': 'zh', 'speech_protection_complete': False}
    except (metadata.PackageNotFoundError, ImportError) as error:
        raise ModelError('Locked ASR dependencies are not installed') from error

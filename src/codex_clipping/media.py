"""Read-only local FFprobe and FFmpeg operations; never trims source media."""
import json
import math
import re
import subprocess
from pathlib import Path


def run_tool(executable, arguments):
    tool = Path(executable)
    if not tool.is_absolute() or not tool.is_file():
        raise ValueError('An existing absolute local tool path is required')
    result = subprocess.run([str(tool), *map(str, arguments)], stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, encoding='utf-8', errors='replace',
                            timeout=600, shell=False)
    if result.returncode:
        raise RuntimeError(f'{tool.name} failed with exit {result.returncode}')
    return result


def probe_media(source, ffprobe):
    result = run_tool(ffprobe, ['-v', 'error', '-protocol_whitelist', 'file,pipe',
                               '-show_streams', '-show_format', '-of', 'json', source])
    info = json.loads(result.stdout)
    duration = float(info.get('format', {}).get('duration', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Media duration must be known, finite and positive')
    validate_origin(info)
    return {'duration_seconds': duration, 'streams': info.get('streams', [])}


def validate_origin(info):
    """First release rejects delayed/unknown origins instead of guessing offsets."""
    fmt = info.get('format', {})
    zero_implicit = fmt.get('format_name') in ('wav', 'flac')
    relevant = [fmt] + [s for s in info.get('streams', []) if s.get('codec_type') in ('video', 'audio')]
    for item in relevant:
        raw = item.get('start_time', 0 if zero_implicit else None)
        try:
            start = float(raw)
        except (ValueError, TypeError) as error:
            raise ValueError('Unknown source timestamp origin is unsupported') from error
        if not math.isfinite(start) or abs(start) > .001:
            raise ValueError('Nonzero source or stream origin is unsupported; no timestamp shift guessed')


def extract_audio(source, target, ffmpeg):
    if Path(target).exists():
        raise FileExistsError('Extracted audio output already exists')
    run_tool(ffmpeg, ['-hide_banner', '-v', 'error', '-nostdin', '-n',
                      '-protocol_whitelist', 'file,pipe', '-i', source,
                      '-map', '0:a:0', '-vn', '-af', 'aresample=async=1:first_pts=0',
                      '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', target])


def parse_silence(log, duration):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Invalid source duration')
    intervals, start = [], None
    for kind, value in re.findall(r'silence_(start|end):\s*([\d.eE+\-]+)', log):
        point = float(value)
        if not math.isfinite(point) or point < 0 or point > duration + .1:
            raise ValueError('Silence timestamp outside source')
        point = min(point, duration)
        if kind == 'start':
            if start is not None:
                raise ValueError('Unclosed silence interval')
            start = point
        else:
            if start is None or point <= start:
                raise ValueError('Invalid silence interval')
            intervals.append({'start': start, 'end': point})
            start = None
    if start is not None and start < duration:
        intervals.append({'start': start, 'end': duration})
    if any(b['start'] < a['end'] for a, b in zip(intervals, intervals[1:])):
        raise ValueError('Overlapping silence intervals')
    return intervals


def detect_silence(source, ffmpeg, duration, noise_db=-35., minimum_seconds=2.):
    if not math.isfinite(noise_db) or not -100 <= noise_db <= -1 or not math.isfinite(minimum_seconds) or minimum_seconds <= 0:
        raise ValueError('Invalid silence detection settings')
    result = run_tool(ffmpeg, ['-hide_banner', '-nostdin', '-protocol_whitelist', 'file,pipe',
                               '-i', source, '-map', '0:a:0', '-vn',
                               '-af', f'silencedetect=noise={noise_db}dB:d={minimum_seconds}',
                               '-f', 'null', '-'])
    return parse_silence(result.stderr, duration)

#!/usr/bin/env python3
"""Offline, synthetic-only FFmpeg smoke test. Never opens user media."""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', required=True, help='Absolute path to ffmpeg executable')
    parser.add_argument('--ffprobe', required=True, help='Absolute path to ffprobe executable')
    args = parser.parse_args()
    paths = [Path(args.ffmpeg), Path(args.ffprobe)]
    if any(not p.is_absolute() or not p.is_file() for p in paths):
        print('BLOCKED: both --ffmpeg and --ffprobe must be absolute paths to existing files.')
        return 2

    root = Path(__file__).resolve().parent
    run = root / 'runs' / dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    run.mkdir(parents=True, exist_ok=False)
    log = run / 'test.log'
    results = {'scope': 'synthetic-only; no speech or actual translation', 'checks': {}, 'run_dir': str(run)}

    def execute(label, argv):
        with log.open('a', encoding='utf-8') as f:
            f.write('\n### ' + label + '\n' + subprocess.list2cmdline(argv) + '\n')
        proc = subprocess.run(argv, cwd=run, capture_output=True, text=True, encoding='utf-8', errors='replace')
        with log.open('a', encoding='utf-8') as f:
            f.write(proc.stdout + proc.stderr + '\nexit=' + str(proc.returncode) + '\n')
        if proc.returncode:
            raise RuntimeError(f'{label} failed (exit {proc.returncode}); see test.log')
        return proc

    ff, probe = map(str, paths)
    try:
        # SRT is intentionally authored test text; it is neither ASR nor translation.
        (run / 'captions.srt').write_text('1\n00:00:00,200 --> 00:00:01,700\n测试字幕\nTest subtitles\n\n2\n00:00:02,100 --> 00:00:03,800\n合成画面\nSynthetic footage\n', encoding='utf-8')
        timeline = {'source': 'source.mp4', 'retain_seconds': [[0, 2], [4, 6]], 'reason': 'known synthetic silence', 'output': 'final.mp4', 'note': 'editable instructions, not an NLE project'}
        (run / 'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding='utf-8')
        execute('generate synthetic input', [ff, '-hide_banner', '-loglevel', 'error', '-n', '-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=25:duration=6', '-f', 'lavfi', '-i', r'aevalsrc=if(between(t\,2\,4)\,0\,0.2*sin(2*PI*440*t)):s=48000:d=6', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', 'source.mp4'])
        results['checks']['synthetic_source'] = 'PASS'
        silence = execute('detect silence', [ff, '-hide_banner', '-i', 'source.mp4', '-af', 'silencedetect=noise=-35dB:d=1.5', '-f', 'null', '-'])
        found = re.findall(r'silence_start:\s*([\d.]+).*?silence_end:\s*([\d.]+)', silence.stderr, re.S)
        if not any(1.8 <= float(a) <= 2.2 and 3.8 <= float(b) <= 4.2 for a, b in found):
            raise RuntimeError('Expected silence at 2–4 seconds was not detected; see test.log')
        results['checks']['silence_detection'] = 'PASS (known synthetic tone gap)'
        filters = ('[0:v]trim=start=0:end=2,setpts=PTS-STARTPTS[v0];'
                   '[0:v]trim=start=4:end=6,setpts=PTS-STARTPTS[v1];'
                   '[v0][v1]concat=n=2:v=1:a=0,crop=202:360,scale=360:640,eq=contrast=1.03:saturation=0.95,subtitles=captions.srt:force_style=\'FontName=Microsoft YaHei,FontSize=14\'[v];'
                   '[0:a]atrim=start=0:end=2,asetpts=PTS-STARTPTS[a0];'
                   '[0:a]atrim=start=4:end=6,asetpts=PTS-STARTPTS[a1];'
                   '[a0][a1]concat=n=2:v=0:a=1[voice];'
                   '[1:a]volume=0.08[music];[voice][music]amix=inputs=2:duration=first:normalize=0[a]')
        execute('render vertical video', [ff, '-hide_banner', '-loglevel', 'error', '-n', '-i', 'source.mp4', '-f', 'lavfi', '-i', 'sine=frequency=220:sample_rate=48000:duration=4', '-filter_complex', filters, '-map', '[v]', '-map', '[a]', '-t', '4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', 'final.mp4'])
        results['checks']['render'] = 'PASS (trim, crop, scale, basic color, mixed synthetic tones, authored subtitles)'
        p = execute('probe output', [probe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', 'final.mp4'])
        data = json.loads(p.stdout)
        (run / 'ffprobe.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        video = next(s for s in data['streams'] if s['codec_type'] == 'video')
        audio = next(s for s in data['streams'] if s['codec_type'] == 'audio')
        duration = float(data['format']['duration'])
        if (video['width'], video['height'], video['codec_name'], audio['codec_name']) != (360, 640, 'h264', 'aac') or not 3.9 <= duration <= 4.2:
            raise RuntimeError('Unexpected dimensions, codecs, or duration; inspect ffprobe.json')
        results['checks']['metadata'] = f'PASS (360x640, h264/aac, {duration:.3f}s)'
        execute('decode output', [ff, '-hide_banner', '-loglevel', 'error', '-xerror', '-i', 'final.mp4', '-f', 'null', '-'])
        results['checks']['decode'] = 'PASS'
        results['checks']['visual_and_audio_quality'] = 'NOT_RUN: requires human viewing and listening'
        results['checks']['speech_recognition_and_translation'] = 'NOT_RUN: source has no speech; captions are authored examples'
        status = 'PASS_WITH_NOTES'
        exit_code = 0
    except (OSError, RuntimeError, KeyError, StopIteration, ValueError) as exc:
        status = 'BLOCKED_OR_FAILED'
        results['error'] = str(exc)
        exit_code = 1
    results['status'] = status
    (run / 'result.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())

"""Generate exclusively synthetic test assets; never opens or overwrites user media."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FFDIR = ROOT / 'OpenFilm' / 'resources' / 'runtime' / 'ffmpeg'
FFMPEG = FFDIR / 'ffmpeg.exe'
FFPROBE = FFDIR / 'ffprobe.exe'
OUT = HERE / 'generated'


def run(argv):
    return subprocess.run([str(x) for x in argv], check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')


def main():
    if not FFMPEG.is_file() or not FFPROBE.is_file():
        raise SystemExit('BLOCKED: bundled FFmpeg and FFprobe not found')
    OUT.mkdir(exist_ok=False)
    common = [FFMPEG, '-hide_banner', '-loglevel', 'error', '-n']
    for name, source in [('clip-a.mp4', 'testsrc2=size=360x640:rate=25:duration=3'), ('clip-b.mp4', 'smptebars=size=360x640:rate=25:duration=3')]:
        run(common + ['-f', 'lavfi', '-i', source, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', OUT / name])
    run(common + ['-f', 'lavfi', '-i', 'color=c=0x303a55:s=360x640:d=1', '-frames:v', '1', '-threads', '1', OUT / 'image.png'])
    run(common + ['-f', 'lavfi', '-i', 'sine=frequency=330:sample_rate=48000:duration=6', '-c:a', 'pcm_s16le', OUT / 'music.wav'])
    (OUT / 'captions.srt').write_text('1\n00:00:00,200 --> 00:00:01,800\n这是第一条测试字幕\n\n2\n00:00:03,200 --> 00:00:04,800\n这是第二条测试字幕\n', encoding='utf-8')
    result = {'origin': 'FFmpeg-generated; no user footage', 'assets': {}}
    for name in ['clip-a.mp4', 'clip-b.mp4', 'image.png', 'music.wav']:
        p = OUT / name
        probe = run([FFPROBE, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', p])
        result['assets'][name] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'probe': json.loads(probe.stdout)}
    srt = OUT / 'captions.srt'
    result['assets'][srt.name] = {'sha256': hashlib.sha256(srt.read_bytes()).hexdigest(), 'subtitle_cues': 2}
    for n in ['clip-a.mp4', 'clip-b.mp4']:
        v = result['assets'][n]['probe']['streams'][0]
        assert (v['width'], v['height'], v['r_frame_rate']) == (360, 640, '25/1')
        assert abs(float(result['assets'][n]['probe']['format']['duration']) - 3.0) < 0.05
    a = result['assets']['music.wav']['probe']['streams'][0]
    assert a['codec_type'] == 'audio' and a['sample_rate'] == '48000'
    assert abs(float(result['assets']['music.wav']['probe']['format']['duration']) - 6.0) < 0.05
    assert result['assets']['image.png']['probe']['streams'][0]['codec_name'] == 'png'
    (OUT / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: 2 generated 360x640/25fps 3s videos, PNG, 6s WAV and 2 authored Chinese subtitle cues')
    print('Evidence:', OUT / 'verification.json')


if __name__ == '__main__':
    main()

"""Create disposable Phase 4A fixtures with the bundled OpenFilm FFmpeg.

This script creates one new test directory and refuses to reuse it. It does
not read personal media, alter existing projects, or download anything.
"""
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / 'AI-Video-Workspace' / 'tests' / 'phase4a'
TOOLS = ROOT / 'OpenFilm' / 'resources' / 'runtime' / 'ffmpeg'


def run(tool, args):
    return subprocess.run([str(tool), *map(str, args)], check=True,
                          capture_output=True, encoding='utf-8', errors='replace',
                          stdin=subprocess.DEVNULL, timeout=300)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    for item in (TARGET, *TARGET.parents):
        if item.is_symlink() or item.is_junction():
            raise ValueError('Linked output directories are not permitted')
    if not TARGET.parent.is_dir() or TARGET.exists():
        raise FileExistsError('Expected a new, unoccupied Phase 4A test directory')
    ffmpeg, ffprobe = (TOOLS / 'ffmpeg.exe'), (TOOLS / 'ffprobe.exe')
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise FileNotFoundError('OpenFilm bundled FFmpeg / FFprobe not found')
    TARGET.mkdir(exist_ok=False)
    fixtures = TARGET / 'fixtures'
    fixtures.mkdir(exist_ok=False)
    files = []
    for name, colour in (('clip-a.mp4', '0x344451'), ('clip-b.mp4', '0xA76E53')):
        output = fixtures / name
        args = ['-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-f', 'lavfi',
                '-i', f'color=c={colour}:s=1080x1920:r=30:d=7.5', '-an', '-c:v', 'libx264',
                '-preset', 'ultrafast', '-threads', '2', '-pix_fmt', 'yuv420p',
                '-r', '30', '-t', '7.5', output]
        run(ffmpeg, args)
        files.append((output, args[:-1] + [name]))
    output = fixtures / 'bed.wav'
    args = ['-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-f', 'lavfi',
            '-i', 'sine=frequency=440:sample_rate=48000:duration=15', '-af', 'volume=0.05',
            '-ac', '1', '-c:a', 'pcm_s16le', '-t', '15', output]
    run(ffmpeg, args)
    files.append((output, args[:-1] + [output.name]))
    evidence = {'generator': 'scripts/phase4a_generate_synthetic.py',
                'ffmpeg': 'OpenFilm bundled FFmpeg', 'files': []}
    for path, command in files:
        probe = run(ffprobe, ['-v', 'error', '-show_entries',
                             'format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,duration',
                             '-of', 'json', path])
        info = json.loads(probe.stdout)
        streams, duration = info['streams'], float(info['format']['duration'])
        if path.suffix == '.mp4':
            if len(streams) != 1 or streams[0].get('codec_type') != 'video' or (
                streams[0].get('width'), streams[0].get('height'), streams[0].get('r_frame_rate')
            ) != (1080, 1920, '30/1') or abs(duration - 7.5) > 0.001:
                raise ValueError('Synthetic video metadata does not match requested specification')
        elif len(streams) != 1 or streams[0].get('codec_type') != 'audio' or abs(duration - 15) > 0.001:
            raise ValueError('Synthetic audio metadata does not match requested specification')
        evidence['files'].append({'name': path.name, 'sha256': sha256(path),
                                  'bytes': path.stat().st_size, 'ffmpeg_arguments': command,
                                  'ffprobe': info})
    with (fixtures / 'fixture-evidence.json').open('x', encoding='utf-8', newline='\n') as file:
        json.dump(evidence, file, ensure_ascii=False, indent=2)
        file.write('\n')
    print('SYNTHETIC_FIXTURES_PASS')


if __name__ == '__main__':
    main()

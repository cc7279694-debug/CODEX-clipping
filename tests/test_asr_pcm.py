"""Synthetic local PCM checks, independent of the speech model."""
import importlib.util
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from codex_clipping import asr


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'numpy unavailable')
class PcmInputTests(unittest.TestCase):
    def write_wav(self, root, *, rate=16000, channels=1, width=2, frames=None):
        path = root / 'fixture.wav'
        with wave.open(str(path), 'wb') as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(width)
            wav.setframerate(rate)
            wav.writeframes(frames if frames is not None else b'\0\0' * channels)
        return path

    def test_signed_samples_are_normalized_without_shifting_time(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            path = self.write_wav(Path(d), frames=struct.pack('<hhhh', -32768, -1, 0, 32767))
            before = path.read_bytes()
            audio = asr.read_pcm16_mono(path)
            self.assertEqual(audio.dtype.name, 'float32')
            self.assertEqual(audio.tolist(), [-1.0, -1 / 32768, 0.0, 32767 / 32768])
            self.assertEqual(len(audio), 4)
            self.assertEqual(path.read_bytes(), before)

    def test_wrong_rate_channels_or_sample_width_are_rejected(self):
        for params in ({'rate': 44100}, {'channels': 2}, {'width': 1}):
            with self.subTest(params=params), tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
                path = self.write_wav(Path(d), **params)
                with self.assertRaises(asr.ModelError):
                    asr.read_pcm16_mono(path)

    def test_truncated_pcm_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            path = self.write_wav(Path(d), frames=b'\0\0' * 12)
            data = path.read_bytes()
            path.write_bytes(data[:-4])
            with self.assertRaises(asr.ModelError):
                asr.read_pcm16_mono(path)

    def test_empty_and_invalid_wav_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as d:
            root = Path(d)
            path = self.write_wav(root, frames=b'')
            with self.assertRaises(asr.ModelError):
                asr.read_pcm16_mono(path)
            path.write_bytes(b'not-a-wav')
            with self.assertRaises(asr.ModelError):
                asr.read_pcm16_mono(path)


if __name__ == '__main__':
    unittest.main()

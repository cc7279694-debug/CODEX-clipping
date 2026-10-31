"""Generate an original 12-second instrumental test tone; never overwrites."""
import math
import struct
import wave
from pathlib import Path

RATE = 48_000
SECONDS = 12
out = Path(__file__).resolve().parent / 'assets' / 'bed.wav'
out.parent.mkdir(parents=True, exist_ok=True)
chords = ((130.81, 164.81, 196.00), (146.83, 174.61, 220.00), (130.81, 164.81, 196.00))
with out.open('xb') as raw:
    with wave.open(raw, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        frames = bytearray()
        for index in range(RATE * SECONDS):
            t = index / RATE
            freqs = chords[min(int(t // 4), 2)]
            fade = min(1.0, t / 0.8, (SECONDS - t) / 1.2)
            # Soft, low-volume tones are computed from sample time only.
            tone = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
            pulse = 0.8 + 0.2 * math.sin(2 * math.pi * 0.18 * t)
            frames += struct.pack('<h', round(32767 * 0.13 * fade * pulse * tone))
        wav.writeframes(frames)
print('Wrote original synthesized audio:', out.name)

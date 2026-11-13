"""Sons dos encantamentos do GitHub Actions (a aba de vigília dos Arautos), só stdlib.

Distintos dos sons dos sandestins (cure-wounds.wav, sending.wav):
encantamento-cumprido.wav  campainhas de cristal subindo em quintas (C6, G6, C7, G7) e um brilho final.
encantamento-desfeito.wav  um tom que despenca em trítono com batimento, vidro estilhaçado e um baque grave.
Uso: python3 sons_encantamento.py <pasta-de-saída>
"""
import math
import random
import struct
import sys
import wave
from pathlib import Path

SR = 44100
rnd = random.Random(7)


def buf(seconds):
    return [0.0] * int(SR * seconds)


def mix(dst, src, at, gain=1.0):
    o = int(at * SR)
    for i, v in enumerate(src):
        if o + i < len(dst):
            dst[o + i] += v * gain


def chime(freq, seconds, decay=4.0):
    """Glass chime: near-harmonic partials, quick attack, bright fast decay."""
    partials = [(1, 1.0), (2.0, 0.35), (3.01, 0.18), (4.17, 0.08)]
    out = []
    for i in range(int(SR * seconds)):
        t = i / SR
        v = sum(g * math.sin(2 * math.pi * freq * r * t) * math.exp(-t * decay * r ** 0.7) for r, g in partials)
        out.append(v * min(1.0, t * 400))
    return out


def sparkle(seconds):
    """Soft high glitter: sparse tiny pings."""
    out = buf(seconds)
    for _ in range(14):
        at = rnd.uniform(0, seconds * 0.6)
        mix(out, chime(rnd.uniform(3000, 5200), 0.25, decay=18), at, rnd.uniform(0.05, 0.12))
    return out


def fall(f0, f1, seconds):
    """A detuned pair gliding down from f0 to f1 (a spell coming undone)."""
    out, ph1, ph2 = [], 0.0, 0.0
    for i in range(int(SR * seconds)):
        t = i / SR
        f = f0 * (f1 / f0) ** min(1.0, t / (seconds * 0.7))
        ph1 += 2 * math.pi * f / SR
        ph2 += 2 * math.pi * f * 1.013 / SR
        v = math.sin(ph1) + 0.8 * math.sin(ph2) + 0.3 * math.sin(3 * ph1)
        env = min(1.0, t / 0.02) * math.exp(-t * 1.6)
        out.append(v * env)
    return out


def shatter(seconds):
    """Glass breaking: a noise burst through a crude high-pass, plus scattered shards."""
    out, prev, y = [], 0.0, 0.0
    for i in range(int(SR * seconds)):
        t = i / SR
        n = rnd.uniform(-1, 1)
        y = 0.6 * (y + n - prev)  # one-pole high-pass
        prev = n
        out.append(y * math.exp(-t * 9))
    for _ in range(9):
        mix(out, chime(rnd.uniform(1800, 4200), 0.3, decay=14), rnd.uniform(0.0, seconds * 0.5), 0.25)
    return out


def thud(seconds=0.5):
    out = []
    for i in range(int(SR * seconds)):
        t = i / SR
        f = 48 + 40 * math.exp(-t * 25)
        out.append(math.sin(2 * math.pi * f * t) * math.exp(-t * 8))
    return out


def write(path, data, peak=0.55):
    m = max(abs(v) for v in data) or 1
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(v / m * peak * 32767)) for v in data))


out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

done = buf(1.9)
for k, f in enumerate([1046.5, 1568.0, 2093.0, 3136.0]):
    mix(done, chime(f, 1.5), k * 0.11, 0.6 - k * 0.08)
mix(done, sparkle(1.4), 0.4, 1.0)
write(out / "encantamento-cumprido.wav", done)

undone = buf(1.8)
mix(undone, fall(659.25, 466.16, 1.3), 0.0, 0.55)  # E5 -> Bb4, a falling tritone
mix(undone, shatter(0.9), 0.32, 0.7)
mix(undone, thud(), 0.32, 0.8)
write(out / "encantamento-desfeito.wav", undone)
print("ok")

"""Synthesize the Wrath alert sounds (stdlib only).

cure-wounds.wav  (agent done): plucked harp arpeggio rising into a bell shimmer.
sending.wav      (agent needs you): two-note war horn over a low drum.
Usage: python3 sounds.py <out-dir>
"""
import math
import random
import struct
import sys
import wave
from pathlib import Path

SR = 44100
rnd = random.Random(20)


def buf(seconds):
    return [0.0] * int(SR * seconds)


def mix(dst, src, at, gain=1.0):
    o = int(at * SR)
    for i, v in enumerate(src):
        if o + i < len(dst):
            dst[o + i] += v * gain


def pluck(freq, seconds, decay=0.996):
    """Karplus-Strong plucked string (harp)."""
    n = int(SR / freq)
    ring = [rnd.uniform(-1, 1) for _ in range(n)]
    out = []
    for i in range(int(SR * seconds)):
        a = ring[i % n]
        b = ring[(i + 1) % n]
        ring[i % n] = decay * 0.5 * (a + b)
        out.append(a)
    return out


def bell(freq, seconds):
    partials = [(1, 1.0), (2.76, 0.45), (5.4, 0.25), (8.93, 0.12)]
    out = []
    for i in range(int(SR * seconds)):
        t = i / SR
        v = sum(g * math.sin(2 * math.pi * freq * r * t) * math.exp(-t * (2.2 + r)) for r, g in partials)
        out.append(v * min(1.0, t * 200))
    return out


def horn(freq, seconds):
    """Brassy tone: band-limited saw with slow attack, vibrato and a one-pole lowpass."""
    out, y = [], 0.0
    for i in range(int(SR * seconds)):
        t = i / SR
        f = freq * (1 + 0.006 * math.sin(2 * math.pi * 5.2 * t) * min(1, t * 3))
        v = sum(math.sin(2 * math.pi * f * k * t) / k for k in range(1, 9))
        env = min(1.0, t / 0.09) * (1 if t < seconds - 0.25 else max(0.0, (seconds - t) / 0.25))
        y += 0.18 * (v * env - y)
        out.append(y)
    return out


def drum(seconds=0.6):
    out = []
    for i in range(int(SR * seconds)):
        t = i / SR
        f = 55 + 70 * math.exp(-t * 30)
        out.append(math.sin(2 * math.pi * f * t) * math.exp(-t * 7) + rnd.uniform(-1, 1) * 0.15 * math.exp(-t * 40))
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

# Cure Wounds: A major arpeggio on a harp, then a bell on the high E.
cure = buf(2.4)
for k, f in enumerate([440.0, 554.37, 659.25, 880.0, 1108.73]):
    mix(cure, pluck(f, 1.6), k * 0.09, 0.55)
mix(cure, bell(1318.5, 1.9), 0.5, 0.35)
write(out / "cure-wounds.wav", cure)

# Sending: drum hit, then horn D3 -> A3.
send = buf(1.7)
mix(send, drum(), 0.0, 0.9)
mix(send, horn(146.83, 0.55), 0.05, 0.6)
mix(send, horn(220.0, 0.95), 0.6, 0.6)
mix(send, drum(), 0.6, 0.6)
write(out / "sending.wav", send)
print("ok")

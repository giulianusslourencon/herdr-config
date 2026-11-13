"""Summoning-circle art for the wrath-ritual mod (tinted via currentColor).

Usage: python3 ritual_art.py <mod-dir>
"""
import math
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

# Elder-Futhark-like strokes in a 6x10 box (x 0..6, y 0..10).
RUNES = [
    "M1 0V10M1 2l4-2M1 5l4-2",          # fehu
    "M1 10V0l4 3v7",                     # uruz
    "M1 0V10M1 3l4 2-4 2",               # thurisaz
    "M1 0V10M1 0l4 3M1 4l4 3",           # ansuz
    "M1 0V10M1 0l4 2.5-4 2.5 4 5",       # raidho
    "M5 0 1 5l4 5",                      # kaunan
    "M0 0l6 10M6 0 0 10",                # gebo
    "M1 0V10M1 0l4 3-4 3",               # wunjo
    "M1 0V10M5 0V10M1 3l4 4",            # hagalaz
    "M3 0V10M1 3l4 4",                   # naudiz
    "M3 0V10",                           # isaz
    "M3 0V10M0 4l3-2 3 2M0 6l3 2 3-2",   # algiz-ish
    "M1 0 5 5 1 10M5 0 1 5l4 5",         # dagaz-ish
    "M3 10V4M3 4 0 0M3 4l3-4",           # elhaz
    "M3 0 0 3l3 3 3-3ZM0 6l3 4M6 6l-3 4", # othala
]
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">'


def outer():
    parts = [HEAD,
             '<circle cx="100" cy="100" r="97" stroke-width="1.6"/>',
             '<circle cx="100" cy="100" r="92" stroke-width="0.6"/>',
             '<circle cx="100" cy="100" r="78" stroke-width="1.2"/>',
             '<circle cx="100" cy="100" r="74.5" stroke-width="0.5" stroke-dasharray="1.5 2.5"/>']
    n = 30
    for i in range(n):
        a = i * 360 / n
        r = RUNES[i % len(RUNES)]
        parts.append(f'<g transform="rotate({a:.2f} 100 100) translate(97 9.5) scale(0.62)"><path d="{r}" stroke-width="1.6"/></g>')
    for i in range(8):
        a = i * 45
        parts.append(f'<g transform="rotate({a} 100 100)"><path d="M100 2.5 103 6 100 9.5 97 6Z" fill="currentColor" stroke="none"/></g>')
    parts.append("</svg>")
    return "\n".join(parts)


def inner():
    parts = [HEAD, '<circle cx="100" cy="100" r="70" stroke-width="0.9"/>']
    pts = [(100 + 70 * math.sin(2 * math.pi * k / 7), 100 - 70 * math.cos(2 * math.pi * k / 7)) for k in range(7)]
    order = [(k * 3) % 7 for k in range(8)]
    parts.append('<path d="M' + " L".join(f"{pts[k][0]:.2f},{pts[k][1]:.2f}" for k in order) + '" stroke-width="1"/>')
    parts.append('<circle cx="100" cy="100" r="31" stroke-width="1"/>')
    parts.append('<circle cx="100" cy="100" r="27" stroke-width="0.5" stroke-dasharray="2 2"/>')
    for x, y in pts:
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="currentColor" stroke="none"/>')
    parts.append("</svg>")
    return "\n".join(parts)


SMALL = '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">'
SIGILS = {
    # flame: concentration
    "sigil-working": '<path d="M24 5c3 8 12 12 12 23a12 12 0 0 1-24 0c0-6 3-9 5-12 1 4 3 6 5 6-2-6 0-12 2-17Z" stroke-width="2.2"/><path d="M24 26c2 3 5 4 5 8a5 5 0 0 1-10 0c0-3 3-5 5-8Z" fill="currentColor" stroke="none"/>',
    # eye: the Sending calls you
    "sigil-blocked": '<path d="M3 24S11 11 24 11 45 24 45 24 37 37 24 37 3 24 3 24Z" stroke-width="2.4"/><circle cx="24" cy="24" r="6.5" fill="currentColor" stroke="none"/><path d="M24 2v5M24 41v5M7 8l3.5 3.5M41 8l-3.5 3.5M7 40l3.5-3.5M41 40l-3.5-3.5" stroke-width="2"/>',
    # radiant star: quest complete
    "sigil-done": '<path d="M24 3 27.5 18.5 43 24 27.5 29.5 24 45 20.5 29.5 5 24 20.5 18.5Z" fill="currentColor" stroke="none"/><path d="M24 11 32.5 15.5M24 11 15.5 15.5" stroke-width="0"/><circle cx="24" cy="24" r="18" stroke-width="1.2" stroke-dasharray="2 3"/>',
    # crescent: long rest
    "sigil-idle": '<path d="M32 8a17 17 0 1 0 8 26A14 14 0 0 1 32 8Z" stroke-width="2.2"/><path d="M36 14l1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1Z" fill="currentColor" stroke="none"/>',
    # node halo for working familiars
    "node-ring": '<circle cx="24" cy="24" r="21" stroke-width="2" stroke-dasharray="4 3"/><path d="M24 1.5a22.5 22.5 0 0 1 22.5 22.5" stroke-width="3"/>',
    # tab-bar button icon
    "icon": '<circle cx="24" cy="24" r="19" stroke-width="3"/><path d="M24 5 35 39 6 18h36L13 39Z" stroke-width="2.6"/>',
}

(OUT / "circle-outer.svg").write_text(outer())
(OUT / "circle-inner.svg").write_text(inner())
for name, body in SIGILS.items():
    (OUT / f"{name}.svg").write_text(SMALL + body + "</svg>\n")
print("ok")

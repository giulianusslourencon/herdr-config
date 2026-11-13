"""Generate Wrath-theme art: SVG scenes (rendered to PNG later) and mod icons."""
import math
import random
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
MOD = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
rnd = random.Random(1212)


def embers(n, w, h, ymin=0.0, colors=("#ff8a3d", "#ffb347", "#e8742a", "#ffd27a")):
    out = []
    for _ in range(n):
        x, y = rnd.uniform(0, w), rnd.uniform(h * ymin, h)
        r = rnd.choice([0.8, 1.0, 1.2, 1.6, 2.2]) * (w / 2560)
        o = rnd.uniform(0.25, 0.9)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 2:.2f}" fill="{rnd.choice(colors)}" opacity="{o:.2f}"/>')
    return "\n".join(out)


def stars(n, w, h):
    return "\n".join(
        f'<circle cx="{rnd.uniform(0, w):.1f}" cy="{rnd.uniform(0, h * 0.45):.1f}" r="{rnd.uniform(0.6, 1.8):.2f}" '
        f'fill="#f5ead2" opacity="{rnd.uniform(0.15, 0.6):.2f}"/>'
        for _ in range(n)
    )


def jag(x0, y0, x1, y1, steps, amp):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t + (rnd.uniform(-amp, amp) if 0 < i < steps else 0)
        y = y0 + (y1 - y0) * t
        pts.append((x, y))
    return pts


def rift_path(cx, top, bottom, width):
    left = jag(cx, top, cx - width * 0.15, bottom, 18, width * 0.35)
    right = jag(cx, bottom, cx + width * 0.1, top, 18, width * 0.35)
    # widen in the middle
    mid = (top + bottom) / 2
    def bulge(p, s):
        k = 1 - abs(p[1] - mid) / ((bottom - top) / 2)
        return (p[0] + s * width * 0.5 * k, p[1])
    pts = [bulge(p, -1) for p in left] + [bulge(p, 1) for p in right]
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"


def castle(w, h, base):
    """Ruined fortress-city silhouette along the bottom."""
    s = w / 2560
    parts = [f"M0,{h} L0,{base}"]
    x = 0
    while x < w:
        kind = rnd.random()
        if kind < 0.18:  # tower with spire
            tw = rnd.uniform(40, 70) * s
            th = rnd.uniform(160, 300) * s
            parts.append(f"L{x:.0f},{base - th * 0.6:.0f} L{x + tw * 0.5:.0f},{base - th:.0f} L{x + tw:.0f},{base - th * 0.6:.0f} L{x + tw:.0f},{base:.0f}")
            x += tw
        elif kind < 0.45:  # crenellated wall
            seg = rnd.uniform(80, 180) * s
            wh = rnd.uniform(50, 90) * s
            n = int(seg // (16 * s))
            parts.append(f"L{x:.0f},{base - wh:.0f}")
            for i in range(n):
                xx = x + i * 16 * s
                parts.append(f"L{xx:.0f},{base - wh - (10 * s if i % 2 == 0 else 0):.0f} L{xx + 16 * s:.0f},{base - wh - (10 * s if i % 2 == 0 else 0):.0f}")
            parts.append(f"L{x + seg:.0f},{base - wh:.0f} L{x + seg:.0f},{base:.0f}")
            x += seg
        elif kind < 0.6:  # broken tower (ruin)
            tw = rnd.uniform(36, 60) * s
            th = rnd.uniform(110, 200) * s
            parts.append(f"L{x:.0f},{base - th:.0f} L{x + tw * 0.4:.0f},{base - th * 0.82:.0f} L{x + tw * 0.7:.0f},{base - th * 0.95:.0f} L{x + tw:.0f},{base - th * 0.7:.0f} L{x + tw:.0f},{base:.0f}")
            x += tw
        else:  # low ground / rubble
            seg = rnd.uniform(60, 160) * s
            parts.append(f"L{x + seg * 0.5:.0f},{base - rnd.uniform(5, 25) * s:.0f} L{x + seg:.0f},{base:.0f}")
            x += seg
    parts.append(f"L{w},{base} L{w},{h}Z")
    return " ".join(parts)


def arcane_circle(cx, cy, r, color, op):
    runes = "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟ"
    out = [f'<g opacity="{op}" fill="none" stroke="{color}">',
           f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke-width="{r * 0.012:.1f}"/>',
           f'<circle cx="{cx}" cy="{cy}" r="{r * 0.86}" stroke-width="{r * 0.006:.1f}"/>',
           f'<circle cx="{cx}" cy="{cy}" r="{r * 0.55}" stroke-width="{r * 0.008:.1f}"/>']
    pts = [(cx + r * 0.86 * math.cos(math.pi / 2 + i * 2 * math.pi / 7 * 3), cy - r * 0.86 * math.sin(math.pi / 2 + i * 2 * math.pi / 7 * 3)) for i in range(8)]
    out.append(f'<path d="M{" L".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" stroke-width="{r * 0.006:.1f}"/>')
    out.append(f'<text font-family="serif" font-size="{r * 0.08:.0f}" fill="{color}" stroke="none">')
    for i, ch in enumerate(runes):
        a = i * 2 * math.pi / len(runes)
        x, y = cx + r * 0.93 * math.cos(a), cy + r * 0.93 * math.sin(a)
        out.append(f'<tspan x="{x:.1f}" y="{y + r * 0.028:.1f}" text-anchor="middle">{ch}</tspan>')
    out.append("</text></g>")
    return "\n".join(out)


def worldwound(w=2560, h=1440):
    base = h * 0.86
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#07040a"/><stop offset="0.45" stop-color="#160812"/>
    <stop offset="0.8" stop-color="#3a0d12"/><stop offset="1" stop-color="#5a1a12"/>
  </linearGradient>
  <radialGradient id="glow" cx="0.68" cy="0.42" r="0.55">
    <stop offset="0" stop-color="#ff5a2a" stop-opacity="0.55"/><stop offset="0.25" stop-color="#b3171f" stop-opacity="0.35"/>
    <stop offset="0.6" stop-color="#4a0a2a" stop-opacity="0.18"/><stop offset="1" stop-color="#000" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="holy" cx="0.12" cy="0.1" r="0.35">
    <stop offset="0" stop-color="#f0c96a" stop-opacity="0.16"/><stop offset="1" stop-color="#f0c96a" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="vig" cx="0.5" cy="0.5" r="0.75">
    <stop offset="0.55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.75"/>
  </radialGradient>
  <filter id="clouds" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.0016 0.0042" numOctaves="5" seed="7"/>
    <feColorMatrix values="0 0 0 0 0.35  0 0 0 0 0.06  0 0 0 0 0.12  0 0 0 1.4 -0.55"/>
  </filter>
  <filter id="blur40"><feGaussianBlur stdDeviation="40"/></filter>
  <filter id="blur12"><feGaussianBlur stdDeviation="12"/></filter>
  <filter id="blur3"><feGaussianBlur stdDeviation="3"/></filter>
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3"/>
    <feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.18 0"/></filter>
  <linearGradient id="riftcore" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffd27a"/><stop offset="0.5" stop-color="#ff6a2a"/><stop offset="1" stop-color="#c4302b"/>
  </linearGradient>
</defs>
<rect width="{w}" height="{h}" fill="url(#sky)"/>
{stars(220, w, h)}
<rect width="{w}" height="{h}" filter="url(#clouds)"/>
<rect width="{w}" height="{h}" fill="url(#glow)"/>
<rect width="{w}" height="{h}" fill="url(#holy)"/>
{arcane_circle(w * 0.12, h * 0.16, h * 0.2, "#d4a24c", 0.16)}
<g transform="translate(0,0)">
  <path d="{rift_path(w * 0.68, h * 0.08, h * 0.8, w * 0.07)}" fill="#ff3a1a" opacity="0.55" filter="url(#blur40)"/>
  <path d="{rift_path(w * 0.68, h * 0.12, h * 0.78, w * 0.035)}" fill="#ff7a2a" opacity="0.8" filter="url(#blur12)"/>
  <path d="{rift_path(w * 0.68, h * 0.14, h * 0.76, w * 0.012)}" fill="url(#riftcore)" filter="url(#blur3)"/>
</g>
<path d="{castle(w, h, base - h * 0.06)}" fill="#1a0a0e" opacity="0.85"/>
<path d="{castle(w, h, base)}" fill="#0a0507"/>
{embers(260, w, h, 0.35)}
<rect width="{w}" height="{h}" fill="url(#vig)"/>
<rect width="{w}" height="{h}" filter="url(#grain)"/>
</svg>'''


def filigree_column(w, h):
    """Vertical tapestry: dark leather, gold borders, heraldic sigil."""
    cx = w / 2
    vine = []
    y = 40
    side = 1
    while y < h - 40:
        x0 = 18 if side > 0 else w - 18
        vine.append(f'<path d="M{x0},{y} q{side * 14},12 0,24 q{-side * 10},10 0,20" fill="none" stroke="#a87a2e" stroke-width="1.4" opacity="0.5"/>')
        y += 46
        side = -side
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
  <linearGradient id="leather" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#22101a"/><stop offset="0.5" stop-color="#170a10"/><stop offset="1" stop-color="#0d0609"/>
  </linearGradient>
  <filter id="tex"><feTurbulence type="fractalNoise" baseFrequency="0.035 0.012" numOctaves="4" seed="11"/>
    <feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.12  0 0 0 0 0.12  0 0 0 0.2 0"/></filter>
  <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="5"/>
    <feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.22 0"/></filter>
  <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f0c96a"/><stop offset="0.5" stop-color="#a87a2e"/><stop offset="1" stop-color="#f0c96a"/>
  </linearGradient>
  <radialGradient id="sigilglow" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#d4a24c" stop-opacity="0.18"/><stop offset="1" stop-color="#d4a24c" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect width="{w}" height="{h}" fill="url(#leather)"/>
<rect width="{w}" height="{h}" filter="url(#tex)"/>
<rect x="8" y="8" width="{w - 16}" height="{h - 16}" fill="none" stroke="url(#gold)" stroke-width="2" opacity="0.55"/>
<rect x="14" y="14" width="{w - 28}" height="{h - 28}" fill="none" stroke="#a87a2e" stroke-width="0.8" opacity="0.4"/>
{"".join(vine)}
<g transform="translate({cx},{h * 0.78})" opacity="0.22">
  <circle r="{w * 0.42}" fill="url(#sigilglow)"/>
  <!-- dying red sun of the last age: a swollen disc with tired rays, half-sunk behind a horizon line -->
  <g>
    <circle r="150" fill="#b3171f" opacity="0.55"/>
    <circle r="150" fill="none" stroke="#d4a24c" stroke-width="3"/>
    <circle r="118" fill="none" stroke="#d4a24c" stroke-width="1" stroke-dasharray="6 7"/>
    <g stroke="#d4a24c" stroke-width="4" stroke-linecap="round">
      {"".join(f'<line x1="0" y1="-172" x2="0" y2="-{205 + (k % 2) * 30}" transform="rotate({k * 22.5 - 90})"/>' for k in range(9))}
    </g>
    <rect x="-240" y="40" width="480" height="140" fill="#170a10"/>
    <line x1="-230" y1="40" x2="230" y2="40" stroke="#d4a24c" stroke-width="3"/>
    <line x1="-170" y1="58" x2="170" y2="58" stroke="#d4a24c" stroke-width="1.2"/>
  </g>
  <circle r="{w * 0.36}" fill="none" stroke="#d4a24c" stroke-width="2"/>
  <circle r="{w * 0.33}" fill="none" stroke="#d4a24c" stroke-width="1"/>
</g>
{embers(40, w, h, 0.5)}
<rect width="{w}" height="{h}" filter="url(#grain)"/>
</svg>'''


def header_tex(w=1600, h=68):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#2a161b"/><stop offset="1" stop-color="#170b10"/>
  </linearGradient>
  <filter id="tex"><feTurbulence type="fractalNoise" baseFrequency="0.02 0.25" numOctaves="3" seed="21"/>
    <feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.25  0 0 0 0 0.12  0 0 0 0.22 0"/></filter>
  <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#d4a24c" stop-opacity="0"/><stop offset="0.15" stop-color="#d4a24c" stop-opacity="0.85"/>
    <stop offset="0.85" stop-color="#d4a24c" stop-opacity="0.85"/><stop offset="1" stop-color="#d4a24c" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect width="{w}" height="{h}" fill="url(#g)"/>
<rect width="{w}" height="{h}" filter="url(#tex)"/>
<rect y="{h - 4}" width="{w}" height="2" fill="url(#rule)"/>
<rect y="{h - 1}" width="{w}" height="1" fill="#000" opacity="0.6"/>
<rect y="0" width="{w}" height="1" fill="#f0c96a" opacity="0.12"/>
</svg>'''


# --- small vector pieces for the pane header (used directly as SVG) ---
FLOURISH = '''<svg xmlns="http://www.w3.org/2000/svg" width="56" height="30" viewBox="0 0 56 30">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f0c96a"/><stop offset="1" stop-color="#a87a2e" stop-opacity="0.2"/></linearGradient></defs>
<g fill="none" stroke="url(#g)" stroke-width="1.3" stroke-linecap="round">
<path d="M3,15 C10,4 22,4 26,12 C29,18 22,22 18,18 C15,15 19,11 22,13"/>
<path d="M3,15 C10,26 22,26 26,18"/>
<path d="M26,15 L54,15" stroke-width="1"/>
<path d="M34,15 C38,9 44,9 46,13" stroke-width="0.9"/>
</g>
<path d="M0,15 L3,12 L6,15 L3,18Z" fill="#f0c96a"/>
</svg>'''

STAR = '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M8,0.5 L9.6,6.4 L15.5,8 L9.6,9.6 L8,15.5 L6.4,9.6 L0.5,8 L6.4,6.4Z" fill="#f0c96a"/>
<path d="M8,4 L8.8,7.2 L12,8 L8.8,8.8 L8,12 L7.2,8.8 L4,8 L7.2,7.2Z" fill="#fff4d0"/>
</svg>'''

RUNE_RING = '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-linecap="round">
<circle cx="8" cy="8" r="6.3" stroke-width="1" stroke-dasharray="2.2 1.6"/>
<path d="M8,1.7 L8,4 M14.3,8 L12,8 M8,14.3 L8,12 M1.7,8 L4,8" stroke-width="1.3"/>
<path d="M8,5.2 L10.8,8 L8,10.8 L5.2,8Z" stroke-width="1.1"/>
</svg>'''

SWORDS = '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round">
<path d="M2,2 L11,11 M2,2 L4.5,2.4 M2,2 L2.4,4.5 M9.5,12.5 L12.5,9.5 M11,11 L14,14"/>
<path d="M14,2 L5,11 M14,2 L11.5,2.4 M14,2 L13.6,4.5 M6.5,12.5 L3.5,9.5 M5,11 L2,14"/>
</svg>'''

DIAMOND = '''<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 10 10">
<path d="M5,0.5 L9.5,5 L5,9.5 L0.5,5Z" fill="#d4a24c"/><path d="M5,3 L7,5 L5,7 L3,5Z" fill="#2a161b"/>
</svg>'''

(OUT / "worldwound.svg").write_text(worldwound())
(OUT / "sidebar.svg").write_text(filigree_column(536, 1800))
(OUT / "header.svg").write_text(header_tex())
for name, body in {"flourish.svg": FLOURISH, "star.svg": STAR, "rune-ring.svg": RUNE_RING,
                   "swords.svg": SWORDS, "diamond.svg": DIAMOND}.items():
    (MOD / name).write_text(body)
print("ok")

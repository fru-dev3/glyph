#!/usr/bin/env python3
"""Four replacement concepts for the figure in the Glyph icon family, on one comparison sheet.

Reuses the tile, palette and per-app elements from ../build.py; only the signature changes.
Writes concepts/<id>/<app>-macos.svg and concepts/figure-concepts.png. Does not touch the
shipped icons.  Run:  python3 assets/family/concepts/build_concepts.py
"""
import importlib.util, math, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("family", os.path.join(HERE, "..", "build.py"))
fam = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fam)
A_, SOFT, APPS = fam.ACCENT, fam.SOFT, fam.APPS


def arcs(cx, cy, radii=(22, 35, 48), half=32, w=6.5):
    """Dictate's three sound arcs, centred on the speaker, fading outward."""
    out = []
    for r, op in zip(radii, ("1", SOFT, ".55")):
        dx, dy = r * math.cos(math.radians(half)), r * math.sin(math.radians(half))
        out.append(f'<path d="M{cx+dx:.1f} {cy-dy:.1f}a{r} {r} 0 0 1 0 {2*dy:.1f}" '
                   f'stroke-width="{w}" stroke-opacity="{op}"/>')
    return "".join(out)


def spiral(cx, cy, s=6.25, w=6.5, op="1"):
    """The petroglyph spiral (1.5 turns of half-circles), centred like the family's."""
    return (f'<path d="M{cx} {cy}a{s} {s} 0 0 1 {2*s} 0 {2*s} {2*s} 0 0 1 {-4*s} 0 '
            f'{3*s} {3*s} 0 0 1 {6*s} 0" stroke-width="{w}" stroke-opacity="{op}"/>')


R = dict(fam.RIGHT)  # the shipped per-app elements

# A. Clean figure: perfect circle head, one even 7 stroke, symmetric, arms raised in the
# orant pose of rock art, four joints total.
A_FIG = ('<circle cx="26" cy="17" r="8" fill="#fff" stroke="none"/>'
         '<path d="M9 22v4a17 17 0 0 0 34 0v-4M26 43v21M26 64 15 89M26 64l11 25" stroke-width="7"/>')
A_RIGHT = dict(R, dictate=arcs(33, 24, radii=(20, 32, 44)))

# C. Solid silhouette: one filled white shape, no thin lines; holds at 16 px.
C_FIG = ('<circle cx="26" cy="15.5" r="9.5" fill="#fff" stroke="none"/>'
         '<path d="M6.5 22v3.5a19.5 19.5 0 0 0 39 0V22" stroke-width="11"/>'
         '<path d="M18 40h16v24l9 22.5a5 5 0 0 1-9.2 3.8L26 72l-7.8 18.3A5 5 0 0 1 9 86.5L18 64z" '
         'fill="#fff" stroke="none"/>')
C_RIGHT = dict(R, dictate=arcs(36, 24, radii=(20, 31, 42), w=7))

# B. No figure: the carved spiral is the signature, big on the left; each app's element
# sits beside it. Studio, the hub, is the spiral alone with its light-green core.
B_LEFT = spiral(20, 56, s=6, w=7)  # bbox centred on y 53, the elements' axis
B_RIGHT = dict(
    R,
    studio=spiral(41, 54.5, s=9, w=8) + f'<circle cx="41" cy="54.5" r="6.5" fill="{A_}" stroke="none"/>',
    dictate=arcs(34, 53),
)

# D. Carved G: a spiral that turns once and resolves into a G (outer bowl, bar inward,
# a small curl at the heart), drawn with the family's stroke.
D_G = ('<path d="M39.6 36.6A19 19 0 1 0 45 50H28a4.5 4.5 0 0 0-9 0 4.5 4.5 0 0 0 4.5 4.5" '
       'stroke-width="7"/>')
# Studio: the G alone, larger and centred (G beside a spiral read as the word "Go").
D_RIGHT = dict(R, dictate=arcs(30, 50),
               studio=f'<g transform="translate(11 -25) scale(1.5)">{D_G}</g>')

CONCEPTS = [
    ("now", "Now", fam.FIGURE, R),  # (id, label, signature, per-app elements)
    ("a", "A  Clean figure", A_FIG, A_RIGHT),
    ("b", "B  Spiral, no figure", B_LEFT, B_RIGHT),
    ("c", "C  Solid silhouette", C_FIG, C_RIGHT),
    ("d", "D  Carved G", D_G, D_RIGHT),
]


def macos(left, right, app):
    solo = app == "studio" and left in (B_LEFT, D_G)  # the signature IS the Studio icon
    body = right[app] if solo else left + right[app]
    mark = f'<g fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round">{body}</g>'
    return fam.macos("studio").split('<g transform')[0] + \
        f'<g transform="translate(182.4 182.4) scale(6.592)">{mark}</g>\n</svg>\n'


def main():
    col, gx = 280, 60
    small_x = gx + col * 5 + 30
    w, rowh, top = small_x + 5 * 52 + 40, 400, 90
    font = 'font-family="Helvetica Neue, Helvetica, Arial" fill="#1d1d1f"'
    parts = [f'<rect width="{w}" height="{top + rowh * len(CONCEPTS) + 20}" fill="#f5f5f7"/>']
    for i, app in enumerate(APPS):
        parts.append(f'<text x="{gx + i * col + 128}" y="62" text-anchor="middle" font-size="24" '
                     f'{font} fill-opacity=".55">{app.title()}</text>')
    parts.append(f'<text x="{small_x + 120}" y="62" text-anchor="middle" font-size="24" {font} '
                 f'fill-opacity=".55">32 px</text>')
    for r, (cid, label, left, right) in enumerate(CONCEPTS):
        os.makedirs(os.path.join(HERE, cid), exist_ok=True)
        y = top + r * rowh
        if r:
            parts.append(f'<rect x="{gx}" y="{y - 6}" width="{w - 2 * gx}" height="2" fill="#d2d2d7"/>')
        parts.append(f'<text x="{gx}" y="{y + 52}" font-size="44" font-weight="bold" {font}>{label}</text>')
        for i, app in enumerate(APPS):
            path = os.path.join(HERE, cid, f"{app}-macos.svg")
            open(path, "w").write(macos(left, right, app))
            parts.append(f'<image x="{gx + i * col}" y="{y + 80}" width="256" height="256" href="{cid}/{app}-macos.svg"/>')
            parts.append(f'<image x="{small_x + i * 52}" y="{y + 192}" width="32" height="32" href="{cid}/{app}-macos.svg"/>')
    h = top + rowh * len(CONCEPTS) + 20
    src = os.path.join(HERE, ".sheet.svg")
    open(src, "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{"".join(parts)}</svg>')
    try:
        subprocess.run(["/opt/homebrew/bin/rsvg-convert", "-o", os.path.join(HERE, "figure-concepts.png"), src], check=True)
    finally:
        os.remove(src)


if __name__ == "__main__":
    main()

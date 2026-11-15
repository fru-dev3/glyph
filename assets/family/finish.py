#!/usr/bin/env python3
"""The family's finish: the glossy, lifted look every Glyph icon shares.

Applies to a master SVG in place, and does nothing to one it has already finished.

    python3 finish.py [--flat] <master.svg> [more.svg ...]

Fru, 2026-11-15: "really make the icons have good glossy 3d effects". It is drawn ON TOP of the
tile's own flat colour rather than replacing it: every pipeline in the family recolours the icon
by swapping `fill="#008000"` for black or for a dark background, and a gradient in its place would
have left the tinted and dark icons green. White and black at low opacity read as light and depth
over any colour, so the same four lines work on the green tile, the dark one and the tinted one.

--flat is for the -small masters (32 px and below), where a blur is mud: they get the light and
the depth, but not the shadow under the figure.
"""
import re, sys

MARK = 'id="glyphTileShade"'

DEFS = (
    '<defs>'
    '<linearGradient id="glyphTileShade" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#fff" stop-opacity="0.22"/>'
    '<stop offset="0.45" stop-color="#fff" stop-opacity="0.04"/>'
    '<stop offset="0.72" stop-color="#000" stop-opacity="0.06"/>'
    '<stop offset="1" stop-color="#000" stop-opacity="0.26"/>'
    '</linearGradient>'
    '<linearGradient id="glyphGloss" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#fff" stop-opacity="0.30"/>'
    '<stop offset="1" stop-color="#fff" stop-opacity="0.03"/>'
    '</linearGradient>'
    '<linearGradient id="glyphRim" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#fff" stop-opacity="0.5"/>'
    '<stop offset="0.45" stop-color="#fff" stop-opacity="0.05"/>'
    '<stop offset="1" stop-color="#000" stop-opacity="0.22"/>'
    '</linearGradient>'
    '<filter id="glyphLift" x="-25%" y="-25%" width="150%" height="150%">'
    '<feDropShadow dx="0" dy="1.6" stdDeviation="1.2" flood-color="#001a00" flood-opacity="0.34"/>'
    '</filter>'
    '</defs>'
)
SHADE = '<rect width="100" height="100" rx="22" fill="url(#glyphTileShade)"/>'
# The sweep: the top of the tile, curving away below the middle, which is what a glossy tile does.
GLOSS = '<path d="M0 22A22 22 0 0 1 22 0H78A22 22 0 0 1 100 22V43Q50 64 0 43Z" fill="url(#glyphGloss)"/>'
RIM = '<rect x="0.8" y="0.8" width="98.4" height="98.4" rx="21.3" fill="none" stroke="url(#glyphRim)" stroke-width="1.6"/>'

TILE = re.compile(r'<rect width="100" height="100" rx="22" fill="#008000"\s*(?:/>|></rect>)')


def finish(path, flat=False):
    svg = open(path).read()
    if MARK in svg:
        return "already finished"
    m = TILE.search(svg)
    if not m:
        return "no family tile in it"
    head, tile, rest = svg[:m.start()], m.group(0), svg[m.end():]
    end = rest.rindex("</svg>")
    art, tail = rest[:end], rest[end:]
    lift = ('<g filter="url(#glyphLift)">' + art + "</g>") if not flat else art
    open(path, "w").write(head + DEFS + tile + SHADE + GLOSS + lift + RIM + tail)
    return "finished" + (" (flat)" if flat else "")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--flat"]
    flat = "--flat" in sys.argv
    for p in args:
        print(f"{p}: {finish(p, flat or p.endswith('-small.svg'))}")

#!/usr/bin/env python3
"""Writes the Glyph icon family SVGs and renders every PNG, .icns and the preview.

Run from anywhere:  python3 assets/family/build.py
Needs rsvg-convert (brew install librsvg) and macOS iconutil.
"""
import os, shutil, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GREEN = "#008000"
ACCENT = "#b9f0b0"  # the family's light-green accent
SOFT = ".78"        # opacity of the secondary white element, as in glyph-tile.svg

# The petroglyph figure, the family signature (100x100 space): a round head, one even 7 stroke,
# four joints, arms raised in the orant pose of rock art. Concept A, chosen 2026-10-25.
FIGURE = ('<circle cx="26" cy="17" r="8" fill="#fff" stroke="none"/>'
          '<path d="M9 22v4a17 17 0 0 0 34 0v-4M26 43v21M26 64 15 89M26 64l11 25" stroke-width="7"/>')
SPIRAL = "M66 53a6.25 6.25 0 0 1 12.5 0 12.5 12.5 0 0 1-25 0 18.75 18.75 0 0 1 37.5 0"

# One variation per app: the element to the right of the figure.
RIGHT = {
    # the original mark: the spiral, a sound that turns back on itself
    "glyph": f'<path d="{SPIRAL}" stroke-width="6.5" stroke-opacity="{SOFT}"/>',
    # the hub: the same spiral, full white, growing out of a light-green core
    "studio": f'<path d="{SPIRAL}" stroke-width="6.5"/>'
              f'<circle cx="66" cy="53" r="5.5" fill="{ACCENT}" stroke="none"/>',
    # speech: three arcs leaving the figure's head, fading as they travel
    "dictate": '<path d="M50 13.4a20 20 0 0 1 0 21.2" stroke-width="6.5"/>'
               f'<path d="M60.1 7a32 32 0 0 1 0 33.9" stroke-width="6.5" stroke-opacity="{SOFT}"/>'
               '<path d="M70.3 .7a44 44 0 0 1 0 46.6" stroke-width="6.5" stroke-opacity=".55"/>',
    # iPhone memos: a phone, with a short voice waveform on its screen
    "mobile": '<rect x="57" y="22" width="30" height="62" rx="8" stroke-width="6"/>'
              f'<path d="M64.5 49v8M72 43v20M79.5 49v8" stroke="{ACCENT}" stroke-width="5"/>',
    # recording: the record button, a ring around a solid dot
    "record": f'<circle cx="72" cy="53" r="17" stroke-width="6.5" stroke-opacity="{SOFT}"/>'
              f'<circle cx="72" cy="53" r="8.5" fill="{ACCENT}" stroke="none"/>',
    # screen video: a play triangle inside a screen frame, on a short stand
    "cast": f'<rect x="51" y="33" width="42" height="31" rx="6" stroke-width="6" stroke-opacity="{SOFT}"/>'
            f'<path d="M67 41.5v14l11-7z" fill="{ACCENT}" stroke="{ACCENT}" stroke-width="3"/>'
            '<path d="M64 77h16M72 64v13" stroke-width="6"/>',
    # command line: a ">_" prompt
    "code": '<path d="M53 37l15 15-15 15" stroke-width="7"/>'
            f'<path d="M74 67h16" stroke="{ACCENT}" stroke-width="7"/>',
    # the Rig: a grid of four machines, one lit, the harnesses it connects and manages
    "rig": '<rect x="52" y="34" width="16" height="16" rx="4" fill="#b9f0b0" stroke="#b9f0b0" stroke-width="5"/>'
           f'<rect x="76" y="34" width="16" height="16" rx="4" stroke-width="5"/>'
           f'<rect x="52" y="58" width="16" height="16" rx="4" stroke-width="5" stroke-opacity="{SOFT}"/>'
           f'<rect x="76" y="58" width="16" height="16" rx="4" stroke-width="5" stroke-opacity="{SOFT}"/>',
    # Arena: a podium, the winning recipe on the tall middle step in light green
    "arena": f'<rect x="51" y="58" width="13" height="23" rx="2.5" stroke-width="5.5" stroke-opacity="{SOFT}"/>'
             '<rect x="67" y="42" width="13" height="39" rx="2.5" fill="#b9f0b0" stroke="#b9f0b0" stroke-width="5.5"/>'
             f'<rect x="83" y="66" width="11" height="15" rx="2.5" stroke-width="5.5" stroke-opacity="{SOFT}"/>',
    # Knowledge: a globe, what the world knows, its equator in light green
    "knowledge": '<circle cx="72" cy="54" r="19" stroke-width="6"/>'
                 f'<path d="M72 35c-8.5 5-8.5 33 0 38M72 35c8.5 5 8.5 33 0 38" stroke-width="4.5" stroke-opacity="{SOFT}"/>'
                 f'<path d="M56 54h32" stroke="{ACCENT}" stroke-width="5"/>',
}
APPS = ["studio", "dictate", "mobile", "record", "cast", "code", "rig", "knowledge", "arena"]
LABEL = {"glyph": "Glyph", "studio": "Glyph Studio", "dictate": "Glyph Dictate",
         "mobile": "Glyph Mobile", "record": "Glyph Record", "cast": "Glyph Cast", "code": "Glyph Code",
         "rig": "Glyph Rig", "knowledge": "Glyph Knowledge", "arena": "Glyph Arena"}


def mark(name, color="#fff"):
    return (f'<g fill="none" stroke="{color}" stroke-linecap="round" stroke-linejoin="round">'
            f'{FIGURE}{RIGHT[name]}</g>')


def tile(name):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="{LABEL[name]}">\n'
            f'  <rect width="100" height="100" rx="22" fill="{GREEN}"/>\n'
            f'  <g transform="translate(10 10) scale(.8)">{mark(name)}</g>\n</svg>\n')


GRAD = ('<linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#0a8f0a"/><stop offset="1" stop-color="#007000"/></linearGradient>')


def macos(name):
    # macOS tile: 824 body at 100 offset, rx 185, soft shadow; the mark at 80% of the body.
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img" aria-label="{LABEL[name]}">\n'
            f'  <defs>{GRAD}\n'
            '    <filter id="s" x="-10%" y="-10%" width="120%" height="125%">'
            '<feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#000" flood-opacity=".22"/></filter></defs>\n'
            # shadow drawn on its own: rsvg bands a gradient fill that sits under a filter
            '  <rect x="100" y="100" width="824" height="824" rx="185" filter="url(#s)"/>\n'
            '  <rect x="100" y="100" width="824" height="824" rx="185" fill="url(#g)"/>\n'
            f'  <g transform="translate(182.4 182.4) scale(6.592)">{mark(name)}</g>\n</svg>\n')


def ios(name):
    # iOS: full-bleed square, no corners, no transparency; iOS applies its own mask.
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">\n'
            f'  <defs>{GRAD}</defs>\n  <rect width="1024" height="1024" fill="url(#g)"/>\n'
            f'  <g transform="translate(102.4 102.4) scale(8.192)">{mark(name)}</g>\n</svg>\n')


def write(path, text):
    with open(os.path.join(HERE, path), "w") as f:
        f.write(text)


def rsvg(src, out, size):
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", out, src], check=True)


def main():
    write("glyph.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" role="img" aria-label="Glyph">\n  '
          + mark("glyph", GREEN).replace('fill="#fff"', f'fill="{GREEN}"') + "\n</svg>\n")
    write("glyph-tile.svg", tile("glyph"))
    write("glyph-macos.svg", macos("glyph"))
    rsvg(f"{HERE}/glyph-macos.svg", f"{HERE}/glyph-1024.png", 1024)
    rsvg(f"{HERE}/glyph-tile.svg", f"{HERE}/glyph-512.png", 512)
    tmp = tempfile.mkdtemp()
    for app in APPS:
        write(f"{app}-tile.svg", tile(app))
        write(f"{app}-macos.svg", macos(app))
        rsvg(f"{HERE}/{app}-macos.svg", f"{HERE}/{app}-1024.png", 1024)
        rsvg(f"{HERE}/{app}-tile.svg", f"{HERE}/{app}-512.png", 512)
        if app not in ("code", "cast", "rig", "knowledge", "arena"):  # no iOS app: Cast and Arena are Mac apps, Code/Rig a command-line tool, Knowledge a website
            src = f"{tmp}/{app}-ios.svg"
            open(src, "w").write(ios(app))
            rsvg(src, f"{tmp}/{app}-ios.png", 1024)
            # App Store icons must have no alpha channel: a lossless-enough JPEG hop drops it.
            subprocess.run(["sips", "-s", "format", "jpeg", f"{tmp}/{app}-ios.png",
                            "-s", "formatOptions", "100", "--out", f"{tmp}/{app}.jpg"], check=True, capture_output=True)
            subprocess.run(["sips", "-s", "format", "png", f"{tmp}/{app}.jpg",
                            "--out", f"{HERE}/{app}-ios-1024.png"], check=True, capture_output=True)
        if app in ("studio", "dictate", "record", "cast"):
            iconset = f"{tmp}/{app}.iconset"
            os.makedirs(iconset)
            for s in (16, 32, 128, 256, 512):
                rsvg(f"{HERE}/{app}-macos.svg", f"{iconset}/icon_{s}x{s}.png", s)
                rsvg(f"{HERE}/{app}-macos.svg", f"{iconset}/icon_{s}x{s}@2x.png", s * 2)
            subprocess.run(["iconutil", "-c", "icns", iconset, "-o", f"{HERE}/{app}.icns"], check=True)
    preview(tmp)
    shutil.rmtree(tmp)


def preview(tmp):
    names = ["glyph"] + APPS
    col, pad = 300, 22
    w = pad + col * len(names)
    rows = []
    for bg, y0 in (("#f5f5f7", 0), ("#1e1e1e", 420)):
        rows.append(f'<rect y="{y0}" width="{w}" height="420" fill="{bg}"/>')
        for i, n in enumerate(names):
            x = pad + i * col
            rows.append(f'<image x="{x}" y="{y0 + 20}" width="256" height="256" href="{n}-macos.svg"/>')
            rows.append(f'<image x="{x + 40}" y="{y0 + 300}" width="64" height="64" href="{n}-tile.svg"/>')
            rows.append(f'<image x="{x + 140}" y="{y0 + 316}" width="32" height="32" href="{n}-tile.svg"/>')
            rows.append(f'<image x="{x + 200}" y="{y0 + 324}" width="16" height="16" href="{n}-tile.svg"/>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="840">{"".join(rows)}</svg>'
    src = f"{HERE}/.preview.svg"
    open(src, "w").write(svg)
    try:
        subprocess.run(["rsvg-convert", "-o", f"{HERE}/preview.png", src], check=True)
    finally:
        os.remove(src)


if __name__ == "__main__":
    main()

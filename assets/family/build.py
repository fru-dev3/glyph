#!/usr/bin/env python3
"""Renders the Glyph icon family from the SVG masters in src/.

Run from anywhere:  python3 assets/family/build.py
Needs rsvg-convert (brew install librsvg), Pillow, and macOS iconutil.

Every PNG is drawn from an SVG at its own size, never scaled down from a bigger PNG.
At 32 px and below the -small master is used (bolder head, thicker lines).
"""
import glob, io, os, shutil, struct, subprocess, tempfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
NAMES = ["glyph", "studio", "jot", "knowledge", "rig", "cast", "arena", "time"]
LABEL = {"glyph": "Glyph", "studio": "Glyph Studio", "jot": "Glyph Jot", "knowledge": "Glyph Ibis",
         "rig": "Glyph Rig", "cast": "Glyph Cast", "arena": "Glyph Arena", "time": "Glyph Time"}
IOS = ["jot", "studio"]                    # apps with an iPhone icon
ICNS = ["studio", "jot", "cast", "arena", "time"]  # Mac apps
# Old names kept so old links still show the right icon.
ALIASES = {"dictate": "jot", "record": "jot", "mobile": "jot", "code": "rig"}


def master(name, px):
    small = os.path.join(SRC, f"{name}-small.svg")
    return open(small if px <= 32 and os.path.exists(small) else os.path.join(SRC, f"{name}.svg")).read()


def png(svg, px, bg=None):
    cmd = ["rsvg-convert", "-w", str(px), "-h", str(px)] + (["-b", bg] if bg else [])
    return subprocess.run(cmd, input=svg.encode(), capture_output=True, check=True).stdout


def save(path, data):
    with open(os.path.join(HERE, path), "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode())


def macos(svg):
    # Apple grid: the tile is 824 of the 1024 canvas, centred.
    return svg.replace('viewBox="0 0 100 100"', 'viewBox="-12.136 -12.136 124.272 124.272"')


def ios(name, px):
    # Full bleed, no transparency: iOS applies its own mask.
    raw = png(master(name, px).replace(' rx="22"', ""), px, "#008000")
    out = io.BytesIO()
    Image.open(io.BytesIO(raw)).convert("RGB").save(out, "PNG")
    return out.getvalue()


def ico(name, sizes=(16, 32, 48)):
    frames = [png(master(name, s), s) for s in sizes]
    head = struct.pack("<HHH", 0, 1, len(frames))
    off = 6 + 16 * len(frames)
    for s, f in zip(sizes, frames):
        head += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(f), off)
        off += len(f)
    return head + b"".join(frames)


def labelled(name, svg):
    return svg.replace("<svg ", f'<svg role="img" aria-label="{LABEL[name]}" ', 1)


def main():
    tmp = tempfile.mkdtemp()
    for n in NAMES:
        save(f"{n}-tile.svg", labelled(n, master(n, 512)))
        save(f"{n}-small.svg", labelled(n, master(n, 16)))
        save(f"{n}-macos.svg", labelled(n, macos(master(n, 1024))))
        save(f"{n}-1024.png", png(macos(master(n, 1024)), 1024))
        for px in (512, 192):
            save(f"{n}-{px}.png", png(master(n, px), px))
        save(f"{n}-180.png", ios(n, 180))  # apple-touch-icon: iOS rounds it itself
        save(f"{n}.ico", ico(n))
        if n in IOS:
            save(f"{n}-ios-1024.png", ios(n, 1024))
        if n in ICNS:
            iconset = f"{tmp}/{n}.iconset"
            os.makedirs(iconset)
            for s in (16, 32, 128, 256, 512):
                save(f"{iconset}/icon_{s}x{s}.png", png(macos(master(n, s)), s))
                save(f"{iconset}/icon_{s}x{s}@2x.png", png(macos(master(n, s * 2)), s * 2))
            subprocess.run(["iconutil", "-c", "icns", iconset, "-o", f"{HERE}/{n}.icns"], check=True)
    for old, new in ALIASES.items():
        for f in glob.glob(f"{HERE}/{old}[-.]*"):
            os.remove(f)
        for f in glob.glob(f"{HERE}/{new}[-.]*"):
            shutil.copy(f, f.replace(f"/{new}", f"/{old}", 1))
    preview()
    shutil.rmtree(tmp)


def preview():
    # Each icon at 256 (macOS), 64, 32 and 16, on light and dark.
    col, pad = 300, 22
    im = Image.new("RGB", (pad + col * len(NAMES), 840))
    for bg, y0 in (("#f5f5f7", 0), ("#1e1e1e", 420)):
        im.paste(Image.new("RGB", (im.width, 420), bg), (0, y0))
        for i, n in enumerate(NAMES):
            x = pad + i * col
            for px, dx, dy, svg in ((256, 0, 20, macos(master(n, 256))), (64, 40, 300, None), (32, 140, 316, None), (16, 200, 324, None)):
                tile = Image.open(io.BytesIO(png(svg or master(n, px), px)))
                im.paste(tile, (x + dx, y0 + dy), tile)
    im.save(f"{HERE}/preview.png")


if __name__ == "__main__":
    main()

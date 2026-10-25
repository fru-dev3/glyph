# Glyph icon family

One tile, one palette (office green `#008000`, white, light-green accent `#b9f0b0`),
one petroglyph figure on the left of every icon. Only the element to its right changes.

The figure is the clean figure (concept A in `concepts/`): a round solid head, one even
stroke for the body, four joints (shoulders, hip, two feet) and arms raised in the orant
pose of rock art. It holds its shape down to 16 px.

| Icon | Variation |
|---|---|
| Glyph (`glyph*`) | The plain mark: the figure and its spiral, the spiral in soft white. For the family and the site. |
| Glyph Studio (`studio*`) | The full mark, the spiral in solid white growing out of a light-green core: the hub everything comes back to. |
| Glyph Dictate (`dictate*`) | Three sound arcs leaving the figure's head, fading as they go: you talk, it types. |
| Glyph Mobile (`mobile*`) | A phone beside the figure with a voice waveform on its screen: memos and the keyboard on iPhone. |
| Glyph Record (`record*`) | A record button, a ring around a solid light-green dot: meetings, calls, long talks. |
| Glyph Cast (`cast*`) | A play triangle inside a screen frame on a short stand: screen videos. Coming, not released. |
| Glyph Code (`code*`) | A `>_` prompt with a light-green cursor: the command-line tool's old icon, kept for old links. |
| Glyph Rig (`rig*`) | A grid of four machines, one lit in light green: the Rig that names, connects and manages every harness across your Macs (was Glyph Code). |
| Glyph Knowledge (`knowledge*`) | A globe with a light-green equator: what the world knows, live data from 50+ context sources (was Ibis). |

## Files

- `glyph.svg`: the mark alone, green on transparent.
- `<name>-tile.svg`, `<name>-512.png`: flat 100x100 tile for the web and favicons.
- `<name>-macos.svg`, `<name>-1024.png`: macOS app icon (824 body at 100 on a 1024 canvas, rx 185, green gradient, soft shadow).
- `<app>-ios-1024.png` (studio, dictate, mobile, record): full-bleed square, no alpha; iOS applies the mask.
- `<app>.icns` (studio, dictate, record): every size from 16 to 1024, @1x and @2x.
- `preview.png`: every icon at 256 (macOS), 64, 32 and 16 (tile), on light and dark.

## Re-render

`build.py` holds the shapes and writes everything above. Edit it, never the generated SVGs.

```sh
brew install librsvg          # rsvg-convert; ImageMagick's SVG renderer mangles strokes
python3 assets/family/build.py
```

It uses `rsvg-convert` for every PNG, `sips` to drop the alpha channel from the iOS icons,
and `iconutil` for the `.icns` files (macOS only).

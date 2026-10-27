# Glyph icon family

One tile, one figure: a white stick figure on office green `#008000`, a 100x100 tile with
corner radius 22. The figure's head shows the app's job; nothing else changes.

| Icon | Head |
|---|---|
| Glyph (`glyph*`) | A plain round head: the family mark, for the site. |
| Glyph Studio (`studio*`) | An AI sparkle, the figure on a stage line. |
| Glyph Jot (`jot*`) | A mic capsule. Also the iPhone app "Glyph" for now. |
| Glyph Ibis (`knowledge*`) | An eye: what the world knows. |
| Glyph Rig (`rig*`) | A terminal with a `>_` prompt. |
| Glyph Cast (`cast*`) | A screen with play over a timeline. |
| Glyph Arena (`arena*`) | A medal with a "1". |
| Glyph Time (`time*`) | A stopwatch, its hand at two o'clock. |

`dictate*`, `record*` and `mobile*` are copies of Jot, and `code*` of Rig, kept for old links.

## Files

- `src/<name>.svg`: the master. `src/<name>-small.svg`: the master for 32 px and below
  (bigger, simpler head, thicker lines), so every icon holds up at 16 px.
- `<name>-tile.svg`, `<name>-small.svg`: the masters, for the web.
- `<name>-512.png`, `-192.png`: the tile. `<name>-180.png`: full bleed, for apple-touch-icon.
- `<name>.ico`: 16, 32 and 48, each drawn on its own.
- `<name>-macos.svg`, `<name>-1024.png`: macOS app icon (the tile at 824 of 1024, centred).
- `<app>-ios-1024.png` (studio, jot): full-bleed square, no alpha; iOS applies the mask.
- `<app>.icns` (studio, jot, cast, arena, time): every size from 16 to 1024, @1x and @2x.
- `preview.png`: every icon at 256 (macOS), 64, 32 and 16, on light and dark.
- `concepts/`: the earlier figure studies, kept for history.

## Re-render

Edit the masters in `src/`, never the generated files. Every PNG is drawn from SVG at its own
size, never scaled down from a bigger PNG.

```sh
brew install librsvg          # rsvg-convert
python3 assets/family/build.py
```

// Regenerate every icon and the share image from the two SVG sources in assets/.
//   assets/glyph.svg       the mark, for light backgrounds
//   assets/glyph-tile.svg  the mark on its dark rounded tile (favicon, app icons, README)
// Needs playwright-core and Google Chrome. Point PLAYWRIGHT_CORE at a playwright-core
// folder if it is not installed where node can resolve it.
// Run: node scripts/icons.mjs
import { readFileSync, writeFileSync, copyFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const docs = join(root, "docs");
const assets = join(root, "assets");
const pw = process.env.PLAYWRIGHT_CORE
  ? pathToFileURL(join(process.env.PLAYWRIGHT_CORE, "index.mjs")).href
  : "playwright-core";
const { chromium } = await import(pw);

const mark = readFileSync(join(assets, "glyph.svg"), "utf8");
const tile = readFileSync(join(assets, "glyph-tile.svg"), "utf8");
const uri = (svg) => "data:image/svg+xml;base64," + Buffer.from(svg).toString("base64");

const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage();

async function png(svg, size) {
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(`<body style="margin:0"><img src="${uri(svg)}" width="${size}" height="${size}" style="display:block">`);
  return page.screenshot({ omitBackground: true });
}

// ICO holding PNG frames: 6 byte header, 16 bytes per entry, then the images.
function ico(frames) {
  const head = Buffer.alloc(6 + 16 * frames.length);
  head.writeUInt16LE(1, 2);
  head.writeUInt16LE(frames.length, 4);
  let offset = head.length;
  frames.forEach(({ size, buf }, i) => {
    const o = 6 + 16 * i;
    head[o] = head[o + 1] = size;
    head.writeUInt16LE(1, o + 4);
    head.writeUInt16LE(32, o + 6);
    head.writeUInt32LE(buf.length, o + 8);
    head.writeUInt32LE(offset, o + 12);
    offset += buf.length;
  });
  return Buffer.concat([head, ...frames.map((f) => f.buf)]);
}

copyFileSync(join(assets, "glyph-tile.svg"), join(docs, "favicon.svg"));
const frames = [];
for (const size of [16, 32, 48]) frames.push({ size, buf: await png(tile, size) });
writeFileSync(join(docs, "favicon.ico"), ico(frames));
writeFileSync(join(docs, "apple-touch-icon.png"), await png(tile, 180));
writeFileSync(join(docs, "icon-192.png"), await png(tile, 192));
writeFileSync(join(docs, "icon-512.png"), await png(tile, 512));
writeFileSync(join(assets, "glyph-512.png"), await png(tile, 512));

// 1200x630 share image: the mark, the display name, the one line, office green on the canvas.
await page.setViewportSize({ width: 1200, height: 630 });
await page.setContent(`<!doctype html>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=block">
<body style="margin:0;width:1200px;height:630px;background:#F6F7F4;color:#0B1210;
  font-family:Inter,-apple-system,'Helvetica Neue',Arial,sans-serif;display:flex;align-items:center;gap:64px;
  padding:0 90px;box-sizing:border-box;border-bottom:14px solid #008000">
  <img src="${uri(mark)}" width="300" height="300" style="flex:none">
  <div>
    <div style="font-size:84px;font-weight:600;letter-spacing:-.035em;line-height:1">Glyph <span style="color:#008000;font-weight:400">| Agent Rig</span></div>
    <div style="margin-top:28px;font-size:34px;line-height:1.3;color:#5B6660;max-width:17em">Gives every coding agent session a name you can recognise.</div>
    <div style="margin-top:40px;font-size:26px;color:#008000;font-weight:600">glyph.fru.dev</div>
  </div>
</body>`);
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: join(docs, "og-image.png") });

await browser.close();
console.log("favicon.svg, favicon.ico, apple-touch-icon.png, icon-192.png, icon-512.png, og-image.png -> docs/; glyph-512.png -> assets/");

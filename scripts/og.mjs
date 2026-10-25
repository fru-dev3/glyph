// The share image (docs/og-image.png, 1200x630): the family mark, the promise and the five
// app icons with their short names from docs/apps.json, drawn from assets/family/. Re-run whenever the icons change.
// Needs playwright-core and Google Chrome; point PLAYWRIGHT_CORE at a playwright-core folder
// if node can't resolve it. Run: node scripts/og.mjs
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const pw = process.env.PLAYWRIGHT_CORE ? pathToFileURL(join(process.env.PLAYWRIGHT_CORE, "index.mjs")).href : "playwright-core";
const { chromium } = await import(pw);
const icon = (n) => "data:image/svg+xml;base64," + readFileSync(join(root, "assets/family", `${n}-tile.svg`)).toString("base64");
const copy = JSON.parse(readFileSync(join(root, "docs/copy.json"), "utf8"));
const apps = JSON.parse(readFileSync(join(root, "docs/apps.json"), "utf8"));
const html = `<!doctype html><html><head>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,800&display=swap" rel="stylesheet">
<style>
body{margin:0;width:1200px;height:630px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:34px;font-family:-apple-system,sans-serif;color:#0B1A10;
background:radial-gradient(45% 40% at 12% 18%,#C9F7B5 0,transparent 70%),radial-gradient(40% 45% at 90% 12%,#CFE6FF 0,transparent 70%),radial-gradient(45% 45% at 85% 92%,#E4DCFF 0,transparent 70%),radial-gradient(40% 40% at 8% 95%,#FFE7C7 0,transparent 70%),#F7FBF5}
.b{display:flex;align-items:center;gap:22px}.b img{width:96px;border-radius:22%;box-shadow:0 10px 24px rgba(0,100,0,.28)}
.b b{font:800 76px/1 "Bricolage Grotesque";letter-spacing:-.03em}
h1,h2{margin:0;font:800 60px/1 "Bricolage Grotesque";letter-spacing:-.035em}h2{color:#008000;font-size:48px;margin-top:-18px}
.r{display:flex;gap:38px}.r div{display:flex;flex-direction:column;align-items:center;gap:10px;font-weight:700;font-size:24px;color:#3E5446}
.r img{width:104px;border-radius:22%;box-shadow:0 10px 24px rgba(0,100,0,.25)}
</style></head><body>
<div class="b"><img src="${icon("glyph")}"><b>Glyph</b></div>
<h1>${copy.headline}</h1><h2>${copy.green1} ${copy.green2}</h2>
<div class="r">${apps.map((a) => `<div><img src="${icon(a.icon)}">${a.short}</div>`).join("")}</div>
</body></html>`;
const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await page.setContent(html, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: join(root, "docs/og-image.png") });
await browser.close();
console.log("og-image: docs/og-image.png");

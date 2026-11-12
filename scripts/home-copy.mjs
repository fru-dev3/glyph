// The home page's words live in docs/copy.json. Edit them there, then run
//   node scripts/home-copy.mjs
// to write them into docs/index.html: the label, the headline (black, then green), the one line
// under it, and the page's descriptions. No em dashes, please.
import { readFileSync, writeFileSync } from "node:fs";
const page = new URL("../docs/index.html", import.meta.url);
const c = JSON.parse(readFileSync(new URL("../docs/copy.json", import.meta.url), "utf8"));
const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
if (/[–—]/.test(JSON.stringify(c))) throw new Error("copy.json has an em or en dash");
let s = readFileSync(page, "utf8");
const set = (id, text) => { s = s.replace(new RegExp(`(id="${id}"[^>]*>)[^<]*(<)`), `$1${esc(text)}$2`); };
set("copy-label", c.label); set("said", c.green);
// The headline may break where copy.json has a new line; the line under it sets its first sentence in ink.
const [first, ...rest] = c.sub.split(/(?<=\.)\s+/);
s = s.replace(/(id="copy-h1"[^>]*>)[\s\S]*?(<\/span>)/, `$1${esc(c.headline).replace(/\n/g, "<br>")}$2`);
s = s.replace(/(id="copy-sub"[^>]*>)[\s\S]*?(<\/p>)/, `$1<b>${esc(first)}</b>${rest.length ? " " + esc(rest.join(" ")) : ""}$2`);
s = s.replace(/data-lines='[^']*'/, `data-lines='${JSON.stringify([c.green]).replace(/'/g, "&#39;")}'`);
for (const m of ['name="description"', 'property="og:description"', 'name="twitter:description"'])
  s = s.replace(new RegExp(`(<meta ${m} content=")[^"]*(")`), `$1${esc(c.description)}$2`);
writeFileSync(page, s);
console.log("home copy written from docs/copy.json");

// Rename one Glyph app across the whole site: its name, short name, page path and "formerly"
// note. docs/apps.json is the list of record; this rewrites every page, the sitemap and the
// ship check to match, moves the page folder and redirects the old path.
//   node scripts/rename-app.mjs <icon> [--name "Glyph Jot"] [--short Jot] [--path jot] [--formerly Jot]
// <icon> is the app's icon id in assets/family/ (studio, dictate, mobile, record, code); it never changes.
import { readFileSync, writeFileSync, readdirSync, statSync, renameSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const docs = join(root, "docs"), listFile = join(docs, "apps.json");
const [icon, ...rest] = process.argv.slice(2);
const opts = {};
for (let i = 0; i < rest.length; i += 2) opts[rest[i].replace(/^--/, "")] = rest[i + 1];
const apps = JSON.parse(readFileSync(listFile, "utf8"));
const app = apps.find((a) => a.icon === icon);
if (!app || !Object.keys(opts).length) {
  console.error("usage: node scripts/rename-app.mjs <" + apps.map((a) => a.icon).join("|") + "> [--name N] [--short S] [--path P] [--formerly F]");
  process.exit(1);
}
const was = { ...app }, now = { ...app, ...opts };
const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const swaps = [];
if (now.name !== was.name) swaps.push([new RegExp(esc(was.name) + "\\b", "g"), now.name]);
if (now.short !== was.short) {
  // the short name only where it stands alone as a label: home cards, sheet nodes
  swaps.push([new RegExp(`<small>Glyph</small>${esc(was.short)}<`, "g"), `<small>Glyph</small>${now.short}<`]);
  swaps.push([new RegExp(`<b>${esc(was.short)}</b>`, "g"), `<b>${now.short}</b>`]);
}
if (now.formerly !== was.formerly) swaps.push([new RegExp(`<i>formerly ${esc(was.formerly)}</i>`, "g"), `<i>formerly ${now.formerly}</i>`]);
if (now.path !== was.path) {
  const p = esc(was.path);
  swaps.push([new RegExp(`/${p}(?=["'/<#?\\s)])`, "g"), `/${now.path}`]);
  swaps.push([new RegExp(`data-page="${p}"`, "g"), `data-page="${now.path}"`]);
}
const files = [];
const walk = (d) => { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) { if (!/^(family|stargazers|demos|agents|logos|apps)$/.test(f)) walk(p); } else if (/\.(html|xml)$/.test(f)) files.push(p); } };
walk(docs);
files.push(join(root, "scripts/ship.sh"));
let changed = 0;
for (const f of files) {
  const s = readFileSync(f, "utf8"); let t = s;
  for (const [re, to] of swaps) t = t.replace(re, to);
  if (t !== s) { writeFileSync(f, t); changed++; }
}
if (now.path !== was.path) {
  if (existsSync(join(docs, now.path))) throw new Error(`docs/${now.path} already exists`);
  renameSync(join(docs, was.path), join(docs, now.path));
  const vj = join(root, "vercel.json"), v = JSON.parse(readFileSync(vj, "utf8"));
  v.redirects = (v.redirects || []).filter((r) => r.source !== `/${now.path}`);
  v.redirects.push({ source: `/${was.path}`, destination: `/${now.path}`, permanent: true });
  for (const r of v.redirects) if (r.destination === `/${was.path}`) r.destination = `/${now.path}`;
  writeFileSync(vj, JSON.stringify(v, null, 2) + "\n");
}
Object.assign(app, now);
writeFileSync(listFile, JSON.stringify(apps, null, 2) + "\n");
console.log(`${icon}: ${JSON.stringify(was)} -> ${JSON.stringify(now)}; ${changed} files rewritten. Re-run node scripts/og.mjs for the share image.`);

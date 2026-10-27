// Build-time social proof: the real people who starred the Glyph repos. For every page it bakes
// a face stack (up to twelve avatars, newest first) and the count between the stargazers markers;
// the home page gets the whole family, de-duplicated, each app page its own repo. An app whose
// repo has fewer than three stars from other people shows the family instead, and says so.
// Avatars are saved into docs/stargazers/ so the page loads nothing from GitHub, the logins into
// docs/stargazers.json. On any failure the committed files stay as they are.
import { mkdirSync, writeFileSync, readFileSync, existsSync, readdirSync, rmSync } from "node:fs";
import { execSync } from "node:child_process";

const OWNER = "fru-dev3";
const FAMILY = ["glyph-studio", "glyph-engine", "glyph-jot", "glyph", "glyph-arena", "glyph-cast", "glyph-time"];
const PAGES = [
  { file: "index.html", repos: FAMILY, label: "Glyph" },
  { file: "studio/index.html", repos: ["glyph-studio"], label: "Glyph Studio" },
  // Glyph Record folded into Glyph Jot (2026-10-25); its repo (0 stars) is archived
  { file: "jot/index.html", repos: ["glyph-jot"], label: "Glyph Jot" },
  { file: "rig/index.html", repos: ["glyph"], label: "Glyph Rig" },
  { file: "arena/index.html", repos: ["glyph-arena"], label: "Glyph Arena" },
  { file: "cast/index.html", repos: ["glyph-cast"], label: "Glyph Cast" },
  { file: "time/index.html", repos: ["glyph-time"], label: "Glyph Time" },
  // Ibis's code is private (context.fru.dev), so its page shows the family's stargazers
  { file: "ibis/index.html", repos: [], label: "Glyph Ibis" },
];
const SHOW = 12, MIN = 3;
const DOCS = new URL("../docs/", import.meta.url);
const DIR = new URL("stargazers/", DOCS);
const headers = { Accept: "application/vnd.github.star+json" };
let token = process.env.GITHUB_TOKEN;
if (!token) try { token = execSync("gh auth token", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim(); } catch {}
if (token) headers.Authorization = `Bearer ${token}`;

// Only other people count: never the owner, never the accounts in .stargazers-exclude (git-ignored).
const skip = new Set([OWNER.toLowerCase()]);
const ex = new URL("../.stargazers-exclude", import.meta.url);
if (existsSync(ex)) for (const l of readFileSync(ex, "utf8").split("\n")) if (l.trim()) skip.add(l.trim().toLowerCase());

async function stargazers(repo) {
  const out = [];
  for (let page = 1; ; page++) {
    const r = await fetch(`https://api.github.com/repos/${OWNER}/${repo}/stargazers?per_page=100&page=${page}`, { headers });
    if (!r.ok) throw new Error(`${repo}: HTTP ${r.status}`);
    const batch = await r.json();
    out.push(...batch.filter((s) => s.user?.type === "User" && !skip.has(s.user.login.toLowerCase()))
      .map((s) => ({ login: s.user.login, avatar: s.user.avatar_url, at: s.starred_at })));
    if (batch.length < 100) return out;
  }
}
// newest star first, one entry per person
const merge = (lists) => {
  const by = new Map();
  for (const s of lists.flat()) if (!by.has(s.login) || by.get(s.login).at < s.at) by.set(s.login, s);
  return [...by.values()].sort((a, b) => (a.at < b.at ? 1 : -1));
};
const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

try {
  const per = {};
  for (const repo of FAMILY) per[repo] = await stargazers(repo);
  const family = merge(FAMILY.map((r) => per[r]));
  const plan = PAGES.map((p) => {
    const own = merge(p.repos.map((r) => per[r]));
    const mine = own.length >= MIN;
    return { ...p, people: mine ? own : family, link: mine && p.repos.length === 1 ? `https://github.com/${OWNER}/${p.repos[0]}` : `https://github.com/${OWNER}`,
      what: mine ? p.label : "Glyph" };
  });
  const need = new Map();
  for (const p of plan) for (const s of p.people.slice(0, SHOW)) need.set(s.login, s.avatar);
  mkdirSync(DIR, { recursive: true });
  const fresh = new Set();
  for (const [login, avatar] of need) {
    const img = await fetch(`${avatar}${avatar.includes("?") ? "&" : "?"}s=96`);
    if (!img.ok) continue;
    writeFileSync(new URL(`${login}.png`, DIR), Buffer.from(await img.arrayBuffer()));
    fresh.add(login);
  }
  for (const f of readdirSync(DIR)) if (!fresh.has(f.replace(/\.png$/, ""))) rmSync(new URL(f, DIR));
  writeFileSync(new URL("stargazers.json", DOCS), JSON.stringify([...fresh], null, 2) + "\n");
  for (const p of plan) {
    const shown = p.people.slice(0, SHOW).filter((s) => fresh.has(s.login));
    const n = p.people.length;
    const faces = shown.map((s) => `<a href="https://github.com/${s.login}" target="_blank" rel="noreferrer" title="${esc(s.login)}"><img src="/stargazers/${s.login}.png" width="40" height="40" alt="${esc(s.login)}" loading="lazy"></a>`).join("");
    const more = n > shown.length ? `<span class="more">+${n - shown.length}</span>` : "";
    const block = `<!-- stargazers -->\n    <div class="proof"><div class="faces">${faces}${more}</div><p><a href="${p.link}" target="_blank" rel="noreferrer"><b>${n}</b><span class="dv"> developers</span> starred ${p.what}<svg class="heart" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 21s-7.5-4.6-10-9.3C.4 8.4 2.3 4.5 6.2 4.5c2.4 0 4 1.4 5.8 3.5 1.8-2.1 3.4-3.5 5.8-3.5 3.9 0 5.8 3.9 4.2 7.2C19.5 16.4 12 21 12 21z"/></svg></a></p></div>\n    <!-- /stargazers -->`;
    const page = new URL(p.file, DOCS);
    const html = readFileSync(page, "utf8");
    if (!html.includes("<!-- stargazers -->")) { console.warn(`stargazers: no markers in ${p.file}`); continue; }
    const next = html.replace(/<!-- stargazers -->[\s\S]*?<!-- \/stargazers -->/, block);
    if (next !== html) writeFileSync(page, next);
    console.log(`stargazers: ${p.file} ${shown.length} faces, ${n} people (${p.what})`);
  }
} catch (e) {
  console.warn(`stargazers: fetch failed (${e.message}); keeping the committed faces`);
}

// Build-time social proof: the real stargazers of fru-dev3/glyph. Saves up to ten avatars into
// docs/stargazers/ (so the page loads nothing from GitHub), their logins to docs/stargazers.json,
// and bakes the faces and the count into docs/index.html between the stargazers markers.
// On any failure the committed files stay as they are.
import { mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from "node:fs";
import { execSync } from "node:child_process";

const REPO = "fru-dev3/glyph";
const DOCS = new URL("../docs/", import.meta.url);
const DIR = new URL("stargazers/", DOCS);
const headers = { Accept: "application/vnd.github+json" };
let token = process.env.GITHUB_TOKEN;
if (!token) try { token = execSync("gh auth token", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim(); } catch {}
if (token) headers.Authorization = `Bearer ${token}`;

try {
  const repo = await (await fetch(`https://api.github.com/repos/${REPO}`, { headers })).json();
  const r = await fetch(`https://api.github.com/repos/${REPO}/stargazers?per_page=100`, { headers });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  // Only other people count as social proof: never the repo's owner, and never the accounts
  // listed one per line in .stargazers-exclude (git-ignored, so no account name goes public).
  const skip = new Set([REPO.split("/")[0].toLowerCase()]);
  const ex = new URL("../.stargazers-exclude", import.meta.url);
  if (existsSync(ex)) for (const l of readFileSync(ex, "utf8").split("\n")) if (l.trim()) skip.add(l.trim().toLowerCase());
  const all = (await r.json()).filter((u) => u.type === "User");
  const others = all.filter((u) => !skip.has(u.login.toLowerCase()));
  const users = others.slice(-10).reverse(); // the newest ten
  if (!users.length) throw new Error("none");
  rmSync(DIR, { recursive: true, force: true });
  mkdirSync(DIR, { recursive: true });
  const list = [];
  for (const u of users) {
    const img = await fetch(`${u.avatar_url}${u.avatar_url.includes("?") ? "&" : "?"}s=96`);
    if (!img.ok) continue;
    writeFileSync(new URL(`${u.login}.png`, DIR), Buffer.from(await img.arrayBuffer()));
    list.push(u.login);
  }
  writeFileSync(new URL("stargazers.json", DOCS), JSON.stringify(list, null, 2) + "\n");
  const n = Math.max(others.length, list.length);
  const faces = list.map((l) => `<a href="https://github.com/${l}" target="_blank" rel="noreferrer" title="${l}"><img src="stargazers/${l}.png" width="40" height="40" alt="${l}" loading="lazy"></a>`).join("");
  const block = `<!-- stargazers -->\n    <div class="proof"><div class="faces">${faces}</div><p><a href="https://github.com/${REPO}" target="_blank" rel="noreferrer">Starred by <b id="sgn">${n}</b> developers</a></p></div>\n    <!-- /stargazers -->`;
  const page = new URL("index.html", DOCS);
  const html = readFileSync(page, "utf8");
  const next = html.replace(/<!-- stargazers -->[\s\S]*?<!-- \/stargazers -->/, block);
  if (next !== html) writeFileSync(page, next);
  console.log(`stargazers: ${list.length} faces, ${n} stars`);
} catch (e) {
  console.warn(`stargazers: fetch failed (${e.message}); keeping the committed list`);
}

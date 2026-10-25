// glyph.fru.dev: the behaviour every page shares. No build step, no dependencies.
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const wait = (ms) => new Promise((r) => setTimeout(r, still ? 0 : ms));
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

// Analytics: the GA4 property glyph.fru.dev has always used, tagged with this site and page. Only on the live host.
window.dataLayer = window.dataLayer || [];
function gtag() { dataLayer.push(arguments); }
gtag("consent", "default", { analytics_storage: "denied", ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied",
  region: ["AT","BE","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IE","IT","LV","LT","LU","MT","NL","PL","PT","RO","SK","SI","ES","SE","IS","LI","NO","GB","CH"] });
if (location.hostname === "glyph.fru.dev") addEventListener("load", () => (window.requestIdleCallback || setTimeout)(() => {
  const s = document.createElement("script"); s.async = true; s.src = "https://www.googletagmanager.com/gtag/js?id=G-1TQYNT93J1";
  document.head.appendChild(s); gtag("js", new Date());
  gtag("config", "G-1TQYNT93J1", { site_name: "glyph", content_group: "glyph-" + (document.body.dataset.page || "home") });
}));
const track = (name, params) => { try { gtag("event", name, params); } catch {} };
$$("a[data-track]").forEach((a) => a.addEventListener("click", () => track(a.dataset.track, { link_url: a.href })));

// The sheet behind the footer link: #features opens it; Esc, the X or a click outside close it.
const sheet = $("dialog.sheet");
if (sheet) {
  const open = () => { if (!sheet.open) { sheet.showModal(); track("features_open"); } };
  $$('a[href="#features"]').forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); open(); history.replaceState(null, "", "#features"); }));
  sheet.addEventListener("click", (e) => { if (e.target === sheet || e.target.closest(".fclose")) sheet.close(); });
  sheet.addEventListener("close", () => { document.activeElement?.blur(); if (location.hash === "#features") history.replaceState(null, "", location.pathname); });
  if (location.hash === "#features") open();
  addEventListener("hashchange", () => { if (location.hash === "#features") open(); });
}

// The headline types itself, line after line. Pages listen for "typing" to animate along.
const h1 = $("h1[data-lines]"), said = $("#said");
const lines = h1 ? JSON.parse(h1.dataset.lines) : [];
async function typeLoop() {
  for (let n = 0; ; n = (n + 1) % lines.length) {
    const line = lines[n];
    said.textContent = "";
    for (let k = 1; k <= line.length; k++) {
      said.textContent = line.slice(0, k);
      dispatchEvent(new CustomEvent("typing", { detail: { n, k, line, talking: true } }));
      await wait(line[k - 1] === " " ? 45 : 85);
    }
    dispatchEvent(new CustomEvent("typing", { detail: { n, k: line.length, line, talking: false } }));
    await wait(2300);
    for (let k = line.length; k >= 0; k--) { said.textContent = line.slice(0, k); await wait(26); }
    await wait(250);
  }
}

// The headline never runs past its column: try every typed line at the CSS size and shrink
// only when the widest one doesn't fit. The face changes shape with size, so refine a few times.
function fitH1() {
  if (!h1) return;
  const col = (h1.dataset.fit || ".cta").split(",").map((q) => $(q.trim())).find((el) => el && el.getBoundingClientRect().width);
  if (!col) return;
  h1.style.fontSize = "";
  const keep = said.textContent, rng = document.createRange();
  const center = getComputedStyle(h1).textAlign === "center";
  const over = () => {
    let lo = Infinity, hi = 0;
    for (const t of lines) {
      said.textContent = t; rng.selectNodeContents(h1);
      for (const r of rng.getClientRects()) { lo = Math.min(lo, r.left); hi = Math.max(hi, r.right); }
    }
    const c = col.getBoundingClientRect();
    return center ? Math.max(hi - lo - c.width, 0) : hi - c.right;
  };
  for (let k = 0, o = over(); k < 6 && o > 0; k++, o = over()) {
    const size = parseFloat(getComputedStyle(h1).fontSize);
    const room = center ? col.getBoundingClientRect().width : col.getBoundingClientRect().right - h1.getBoundingClientRect().left;
    h1.style.fontSize = (size * room / (room + o) * 0.985).toFixed(2) + "px";
  }
  said.textContent = keep;
}

// The right group is as tall as the left column allows and centred on it: the picture takes
// whatever height the rest leaves, at its own aspect ratio (data-ar, width over height).
function fitRight() {
  const right = $(".right"), left = $(".left"), fill = $(".right .fill");
  if (!right || !fill || getComputedStyle(right).display === "none") return;
  fill.style.width = ""; fill.style.height = "";
  const other = right.getBoundingClientRect().height - fill.getBoundingClientRect().height;
  const h = Math.max(140, left.getBoundingClientRect().height - other);
  const w = right.getBoundingClientRect().width, ar = parseFloat(fill.dataset.ar) || 0;
  if (ar) { const fw = Math.min(w, h * ar); fill.style.width = fw + "px"; fill.style.height = fw / ar + "px"; }
  else { fill.style.width = w + "px"; fill.style.height = Math.min(h, w * 0.78) + "px"; }
}
function fitAll() { fitH1(); fitRight(); }
fitAll(); addEventListener("resize", fitAll); addEventListener("load", fitAll);
document.fonts?.ready.then(fitAll);
if (h1 && !still && lines.length > 1) typeLoop();

// Copy a command (the install line).
$$("button[data-copy]").forEach((b) => b.addEventListener("click", () => {
  const l = $(".lbl", b), was = l.textContent;
  navigator.clipboard.writeText(b.dataset.copy).then(() => { l.textContent = b.dataset.done || "Copied"; setTimeout(() => (l.textContent = was), 2200); });
  track("copy_install");
}));

// Star counts: shields.io first (it caches GitHub, so no visitor meets GitHub's 60 an hour),
// GitHub's API if that fails, never below the number baked into the page. Several repos add up.
const starsOf = (repo) => fetch(`https://img.shields.io/github/stars/${repo}.json`).then((r) => (r.ok ? r.json() : Promise.reject()))
  .then((d) => { const n = parseInt(d.value, 10); if (!(n >= 0)) throw 0; return n; })
  .catch(() => fetch(`https://api.github.com/repos/${repo}`).then((r) => (r.ok ? r.json() : null)).then((d) => d?.stargazers_count || 0).catch(() => 0));
$$("[data-stars]").forEach((el) => {
  const floor = +el.dataset.floor || 0, out = $(".n", el) || el;
  const show = (n) => { n = Math.max(n, floor); if (n > 0) { out.textContent = n.toLocaleString("en-US"); el.hidden = false; } };
  show(0);
  Promise.all(el.dataset.stars.split(",").map(starsOf)).then((ns) => show(ns.reduce((a, b) => a + b, 0)));
});

// Download counts: what people downloaded, read from GitHub. The sum of download_count over every
// asset of every release whose name matches data-match: the installers only (.dmg, .exe, .msi).
// The auto-updater's own fetches (latest.json, .app.tar.gz, .sig) are not people downloading the
// app, so they are left out. Never below the number baked into the page (data-floor), which is a
// real count taken from the same API at the last edit; never anything invented.
$$("[data-downloads]").forEach((el) => {
  const floor = +el.dataset.floor || 0, out = $(".n", el), re = new RegExp(el.dataset.match || "\\.dmg$");
  const show = (n) => { n = Math.max(n || 0, floor); if (n > 0) { out.textContent = n.toLocaleString("en-US"); el.title = n.toLocaleString("en-US") + " downloads"; el.hidden = false; } };
  // GitHub allows 60 unsigned requests an hour per network: ask at most once an hour per browser.
  const key = "dl:" + el.dataset.downloads;
  let saved = null; try { saved = JSON.parse(localStorage.getItem(key)); } catch {}
  show(saved?.n);
  if (saved && Date.now() - saved.at < 3600e3) return;
  // Every page of releases: glyph-studio has more than 100 of them, and reading only the first
  // page undercounted it (388 where the true installer total was 511, 2026-10-25).
  const page = (n, acc) => fetch(`https://api.github.com/repos/${el.dataset.downloads}/releases?per_page=100&page=${n}`)
    .then((r) => (r.ok ? r.json() : Promise.reject())).then((rels) => (rels.length === 100 ? page(n + 1, acc.concat(rels)) : acc.concat(rels)));
  page(1, [])
    .then((rels) => { const n = rels.flatMap((r) => r.assets || []).filter((a) => re.test(a.name)).reduce((t, a) => t + (a.download_count || 0), 0);
      show(n); try { localStorage.setItem(key, JSON.stringify({ n, at: Date.now() })); } catch {} })
    .catch(() => {});
});

// The version beside an app's name: the latest release's number, asked at most once an hour per
// browser; the number baked into the page stays until an answer comes.
$$("[data-version]").forEach((el) => {
  const key = "ver:" + el.dataset.version;
  const show = (t) => { const v = (t || "").match(/\d+(\.\d+)+/); if (v) el.textContent = "v" + v[0]; };
  let saved = null; try { saved = JSON.parse(localStorage.getItem(key)); } catch {}
  show(saved?.t);
  if (saved && Date.now() - saved.at < 3600e3) return;
  // shields.io first (cached, no rate limit for visitors), GitHub's API if that fails
  fetch(`https://img.shields.io/github/v/release/${el.dataset.version}.json`).then((r) => (r.ok ? r.json() : Promise.reject()))
    .then((d) => { if (!/\d/.test(d.value || "")) throw 0; return d.value; })
    .catch(() => fetch(`https://api.github.com/repos/${el.dataset.version}/releases/latest`).then((r) => (r.ok ? r.json() : null)).then((d) => d?.tag_name))
    .then((t) => { if (!t) return; show(t); try { localStorage.setItem(key, JSON.stringify({ t, at: Date.now() })); } catch {} })
    .catch(() => {});
});

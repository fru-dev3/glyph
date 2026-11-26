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
// An Install click starts the download right here, then opens /thanks: what to do next, and the setup session (decision d-mwww6afh-e4j3fl).
if (document.body.dataset.page !== "thanks") document.addEventListener("click", (ev) => {
  const a = ev.target.closest && ev.target.closest('a[href$=".dmg"]');
  if (!a || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey || ev.button) return;
  const k = a.dataset.app || document.body.dataset.page || "";
  setTimeout(() => (location.href = "/thanks/" + (/^[a-z]+$/.test(k) && k !== "home" ? "?app=" + k : "")), 900);
});
$$("a[data-track]").forEach((a) => a.addEventListener("click", () => track(a.dataset.track, { link_url: a.href, app: a.dataset.app || document.body.dataset.page || "home", from: location.hash.slice(1) || "overview" })));

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

// Every live number (stars, downloads, versions) is one small answer from shields.io or GitHub.
// Each answer is kept in localStorage for an hour, a failed one too, so a page view asks nothing
// when a fresh answer is saved and a rate-limited visitor does not ask again (and log another
// 403) for an hour. Only the reduced answer is saved, never a whole release list. Without
// localStorage (private mode, blocked storage) the page still works: it just asks each time.
// Without any answer, the number baked into the page stays.
const HOUR = 3600e3, asked = new Map();
function cachedJson(url, reduce) {
  if (asked.has(url)) return asked.get(url);
  const key = "c1:" + url;
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(key)); } catch {}
  const p = saved && Date.now() - saved.at < HOUR
    ? (saved.ok ? Promise.resolve(saved.v) : Promise.reject(new Error("failed within the hour")))
    : fetch(url).then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))).then(reduce)
        .then((v) => { try { localStorage.setItem(key, JSON.stringify({ at: Date.now(), ok: true, v })); } catch {} return v; },
              (e) => { try { localStorage.setItem(key, JSON.stringify({ at: Date.now(), ok: false })); } catch {} throw e; });
  asked.set(url, p);
  return p;
}
const shieldsNumber = (d) => { const n = parseInt(d.value, 10); if (!(n >= 0)) throw new Error("no number"); return n; };

// Star counts: shields.io first (it caches GitHub, so no visitor meets GitHub's 60 an hour),
// GitHub's API if that fails, never below the number baked into the page. Several repos add up.
const starsOf = (repo) => cachedJson(`https://img.shields.io/github/stars/${repo}.json`, shieldsNumber)
  .catch(() => cachedJson(`https://api.github.com/repos/${repo}`, (d) => d.stargazers_count || 0)).catch(() => 0);
$$("[data-stars]").forEach((el) => {
  const floor = +el.dataset.floor || 0, out = $(".n", el) || el;
  const show = (n) => { n = Math.max(n, floor); if (n > 0) { out.textContent = n.toLocaleString("en-US"); el.hidden = false; } };
  show(0);
  Promise.all(el.dataset.stars.split(",").map(starsOf)).then((ns) => show(ns.reduce((a, b) => a + b, 0)));
});

// Download counts: what people downloaded, read from GitHub. The sum of download_count over every
// asset of every release whose name matches data-match: the installers only (.dmg, .exe, .msi;
// on the home also the engine's command-line binaries, prevail-v* and aireadyu-v* .tar.gz).
// The family total (several repos, data-match ".") counts every asset, updates included (owner's call,
// 2026-11-12); a single app's own count may still pass a narrower data-match.
// The auto-updater's own fetches (latest.json, .app.tar.gz, .sig) are not people downloading the
// app, so they are left out. Never below the number baked into the page (data-floor), which is a
// real count taken from the same API at the last edit, so it can only undercount (it keeps the
// number on screen when GitHub rate-limits a visitor); never anything invented.
// Every page of releases: glyph-studio has more than 100 of them, and reading only the first page
// undercounted it (388 where the true installer total was 511, 2026-10-25). data-downloads may
// name several repos (the home's family total): their counts add up.
const releasePage = (repo, n) => cachedJson(`https://api.github.com/repos/${repo}/releases?per_page=100&page=${n}`,
  (rels) => ({ full: rels.length === 100, assets: rels.flatMap((r) => (r.assets || []).map((a) => [a.name, a.download_count || 0])) }));
const allAssets = (repo, n = 1) => releasePage(repo, n).then((pg) => (pg.full ? allAssets(repo, n + 1).then((more) => pg.assets.concat(more)) : pg.assets));
$$("[data-downloads]").forEach((el) => {
  const floor = +el.dataset.floor || 0, out = $(".n", el), re = new RegExp(el.dataset.match || "\\.dmg$");
  const show = (n) => { n = Math.max(n || 0, floor); if (n > 0) { out.textContent = n.toLocaleString("en-US"); el.title = n.toLocaleString("en-US") + " " + (el.dataset.label || "downloads"); el.setAttribute("aria-label", el.title); el.hidden = false; } };
  show(0);
  Promise.all(el.dataset.downloads.split(",").map((repo) => allAssets(repo.trim())))
    .then((lists) => show(lists.flat().filter(([name]) => re.test(name)).reduce((t, [, c]) => t + c, 0)))
    .catch(() => {});
});

// The version beside an app's name: the latest release's number, shields.io first, GitHub's API
// if that fails; the number baked into the page stays until an answer comes.
$$("[data-version]").forEach((el) => {
  const repo = el.dataset.version;
  const show = (t) => { const v = (t || "").match(/\d+(\.\d+)+/); if (v) el.textContent = "v" + v[0]; };
  cachedJson(`https://img.shields.io/github/v/release/${repo}.json`, (d) => { if (!/\d/.test(d.value || "")) throw new Error("no version"); return d.value; })
    .catch(() => cachedJson(`https://api.github.com/repos/${repo}/releases/latest`, (d) => d.tag_name))
    .then(show).catch(() => {});
});

// The version on the Install button (Fru, 2026-11-16: "I don't really know what I'm installing").
// The latest release's number is shown beside the button, and the link is pointed at the disk image
// that carries it, so the file in Downloads is Glyph-Native-0.6.5.dmg and not a nameless one. The
// unversioned link stays until the answer comes, and whenever GitHub does not answer.
$$("a[data-dmg]").forEach((el) => {
  const repo = el.dataset.dmg, stem = el.getAttribute("href").split("/").pop().replace(/\.dmg$/, "");
  cachedJson(`https://api.github.com/repos/${repo}/releases/latest`, (d) => d.tag_name).then((tag) => {
    const v = (tag || "").match(/\d+(\.\d+)+/);
    if (!v) return;
    el.href = window.glyphDmg = `https://github.com/${repo}/releases/download/${tag}/${stem}-${v[0]}.dmg`;
    $$(".dlv").forEach((n) => { n.textContent = v[0]; n.hidden = false; });
  }).catch(() => {});
});

// The ribbon (scripts/ribbon.py): the address names the panel (#how, #compare, #open, #faq, #apps);
// no hash is the one bright screen. The panels are already in the HTML, so search engines read them.
const panels = $$(".panel");
if (panels.length) {
  const route = () => {
    const id = location.hash.slice(1), p = panels.find((x) => x.id === id);
    panels.forEach((x) => (x.hidden = x !== p));
    document.body.classList.toggle("paneled", !!p);
    $$(".ribbon a").forEach((a) => a.setAttribute("aria-current", a.dataset.tab === (p ? id : "") ? "page" : "false"));
    stepStop();
    if (p) { p.scrollTop = 0; track("ribbon_open", { tab: id }); opened(p); }
  };
  addEventListener("hashchange", route); route();
  // The way back: the close button, Esc, and the Overview tab all return to the one bright screen without a reload.
  const home = () => { history.pushState(null, "", location.pathname + location.search); route(); };
  $$(".pclose, .ribbon a[data-tab='']").forEach((a) => a.addEventListener("click", (ev) => { if (location.hash) { ev.preventDefault(); home(); } }));
  addEventListener("keydown", (ev) => { if (ev.key === "Escape" && document.body.classList.contains("paneled") && !$("dialog[open]")) home(); });
  addEventListener("popstate", route);
  // Compare: one rival at a time; the head-to-head and the rows rise in again.
  $$(".rivals button").forEach((b) => b.addEventListener("click", () => {
    $$(".rivals button").forEach((x) => x.setAttribute("aria-selected", x === b));
    $$(".rv").forEach((x) => (x.hidden = x.dataset.r !== b.dataset.r));
    track("compare_pick", { rival: b.dataset.r });
  }));
}
// How it works: the steps take turns every 5.5 seconds while the panel is open; a tap picks one, hovering holds.
var stepT = 0; // var: route() above runs before this line on a page opened at a panel
function stepStop() { clearTimeout(stepT); }
// A step with several screens shows each in turn (3.2 seconds apiece), then hands over to the next step.
function stepGo(st, n, j = 0) {
  const bs = $$(".steplist button", st), im = $$(".shots img", st), k = im.filter((x) => +x.dataset.i === n).length;
  if (!j) bs.forEach((b, i) => { b.setAttribute("aria-selected", i === n); const bar = $(".bar", b); bar.style.animation = "none"; bar.offsetWidth; bar.style.animation = ""; });
  im.forEach((x) => x.classList.toggle("on", +x.dataset.i === n && +(x.dataset.j || 0) === j));
  stepStop();
  if (!still && !st.classList.contains("hold"))
    stepT = setTimeout(() => (j + 1 < k ? stepGo(st, n, j + 1) : stepGo(st, (n + 1) % bs.length)), k > 1 ? 3200 : 5500);
  st.dataset.n = n; st.dataset.j = j;
}
$$(".stepper").forEach((st) => {
  $$(".steplist button", st).forEach((b, i) => b.addEventListener("click", () => { stepGo(st, i); track("how_step", { step: i + 1 }); }));
  st.addEventListener("mouseenter", () => { st.classList.add("hold"); stepStop(); });
  st.addEventListener("mouseleave", () => { st.classList.remove("hold"); stepGo(st, +st.dataset.n || 0, +st.dataset.j || 0); });
});
// Numbers count up from zero the first time their panel opens.
function countUp(el) {
  const to = +el.dataset.count; if (!to || still) return;
  const t0 = performance.now(), d = 1100;
  const f = (t) => { const k = Math.min(1, (t - t0) / d), v = Math.round(to * (1 - Math.pow(1 - k, 3))); el.textContent = v.toLocaleString("en-US"); if (k < 1) requestAnimationFrame(f); };
  requestAnimationFrame(f);
}
function opened(p) {
  const st = $(".stepper", p); if (st) stepGo(st, 0);
  if (p.dataset.seen) return; p.dataset.seen = 1;
  $$("[data-count]", p).forEach(countUp);
  const f = $("[data-faces]", p), src = $(".proof .faces");
  if (f && src) f.innerHTML = src.innerHTML.replace(/<span class="more">.*?<\/span>/, "");
}
// The home's calculator: tick what you pay for, see the month and the year.
const calc = $(".calc");
if (calc) {
  const sum = $("[data-sum]", calc), yr = $("[data-year]", calc);
  let shown = 0;
  const total = () => {
    const to = $$("input:checked", calc).reduce((t, i) => t + +i.value, 0), from = shown, t0 = performance.now();
    shown = to; yr.textContent = "$" + Math.round(to * 12).toLocaleString("en-US");
    const list = $("[data-drop]", calc);
    if (list) { list.textContent = ""; $$("input:checked", calc).forEach((i) => { const img = i.nextElementSibling, c = document.createElement("span"); c.append(img.cloneNode(), img.dataset.n); list.append(c); }); }
    const f = (t) => { const k = still ? 1 : Math.min(1, (t - t0) / 500); sum.textContent = "$" + (from + (to - from) * (1 - Math.pow(1 - k, 3))).toFixed(2).replace(/\.00$/, ""); if (k < 1) requestAnimationFrame(f); };
    requestAnimationFrame(f);
  };
  calc.addEventListener("change", (ev) => { total(); track("calc_toggle", { value: ev.target.value }); });
  total();
}

// The Support pill every fru.dev site shows (support.js). Pages without site.js load it themselves.
{ const s = document.createElement("script"); s.src = "/support.js"; s.defer = true; document.head.appendChild(s); }

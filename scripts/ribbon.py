#!/usr/bin/env python3
"""The ribbon on every app page and the home: Overview, How it works, Compare, In the open, FAQ.

    python3 scripts/ribbon.py              # every app in scripts/compare.json, then the home
    python3 scripts/ribbon.py jot time     # some apps
    python3 scripts/ribbon.py home         # the home only

Overview is the page as it was: one bright screen. The other tabs are panels baked into the same
HTML between <!-- ribbon --> markers, so Google and AI agents read them without running a script;
site.js opens the one the address names (#how, #compare, #open, #faq, and #apps on the home).
Each rival also gets its own page at /<app>/vs/<rival>, the page people search for.

Data: scripts/compare.json (our side: the steps, the questions, our column) and
scripts/rivals/<app>.json (their side, researched from each vendor's own pages). Every rival fact
carries its source; one nobody could find on an official page reads "Not stated", never a guess.
No quotes or testimonials: "what people say" is real stars, downloads and releases, read from GitHub.
"""
import json, re, sys, html, subprocess, urllib.request
from datetime import datetime, date
from pathlib import Path

root = Path(__file__).resolve().parent.parent
docs = root / "docs"
data = json.loads((root / "scripts/compare.json").read_text())
APPS = {a["path"]: a for a in json.loads((docs / "apps.json").read_text())}
e = html.escape
FAM = "fru-dev3/glyph-native,fru-dev3/glyph-studio,fru-dev3/glyph-jot,fru-dev3/glyph-record,fru-dev3/glyph-time,fru-dev3/glyph-arena,fru-dev3/glyph-cast,fru-dev3/glyph,fru-dev3/glyph-engine"
INSTALL = "https://github.com/fru-dev3/glyph-native/releases/latest/download/Glyph-Native.dmg"


def svg(d, cls="ic"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true"><path d="{d}"/></svg>')


# One icon per kind of row, so a table reads at a glance.
ROWICON = {
    "price": "M20.6 13.4l-7.2 7.2a2 2 0 01-2.8 0L3 13V3h10l7.6 7.6a2 2 0 010 2.8zM7.5 7.5h.01",
    "platforms": "M4 5h16v10H4zM2 19h20M15 19v2",
    "processing": "M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2M7 7h10v10H7z",
    "capture": "M12 8V4H8M4 12a8 8 0 0016 0M8 12h.01M16 12h.01M9 16h6",
    "account": "M20 21v-1a5 5 0 00-5-5H9a5 5 0 00-5 5v1M12 11a4 4 0 100-8 4 4 0 000 8",
    "source": "M8 6l-6 6 6 6M16 6l6 6-6 6",
    "storage": "M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z",
    "training": "M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9zM19 17l.9 2.1L22 20l-2.1.9L19 23l-.9-2.1L16 20l2.1-.9z",
    "offline": "M2 2l20 20M8.5 16.5a5 5 0 017 0M5 12.9a10 10 0 015.2-2.8M19 12.9a10 10 0 00-2-1.4M2 8.8a15 15 0 014.2-2.6M22 8.8A15 15 0 0010.7 5M12 20h.01",
    "export": "M12 3v12m0 0l-5-5m5 5l5-5M5 21h14",
    "bank": "M3 21h18M5 21V10M19 21V10M9 21V10M15 21V10M2 10l10-7 10 7z",
    "models": "M12 2a4 4 0 014 4v1a4 4 0 01-8 0V6a4 4 0 014-4zM4 22a8 8 0 0116 0",
    "sources": "M10 13a5 5 0 007.5.5l3-3a5 5 0 00-7-7l-1.7 1.7M14 11a5 5 0 00-7.5-.5l-3 3a5 5 0 007 7l1.7-1.7",
    "cancels": "M12 3a9 9 0 100 18 9 9 0 000-18zM9 9l6 6M15 9l-6 6",
    "input": "M12 2a3 3 0 013 3v6a3 3 0 01-6 0V5a3 3 0 013-3zM19 10a7 7 0 01-14 0M12 17v5",
    "patterns": "M3 3v18h18M7 15l4-4 3 3 6-6",
    "goals": "M12 3a9 9 0 100 18 9 9 0 000-18zM12 8a4 4 0 100 8 4 4 0 000-8zM12 12h.01",
    "agents": "M12 8V4H8M5 8h14v12H5zM2 14h2M20 14h2M9 13v2M15 13v2",
    "machines": "M3 4h18v6H3zM3 14h18v6H3zM7 7h.01M7 17h.01",
    "network": "M12 3a9 9 0 100 18 9 9 0 000-18zM3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18",
    "tasks": "M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01",
    "judging": "M12 3v18M5 21h14M3 9l3-6 3 6a3 3 0 01-6 0zM15 9l3-6 3 6a3 3 0 01-6 0zM6 3h12",
    "local": "M3 11l9-8 9 8M5 10v10h14V10",
    "output": "M14 3H6a1 1 0 00-1 1v16a1 1 0 001 1h12a1 1 0 001-1V8zM14 3v5h5M9 13h6M9 17h6",
    "runs": "M3 4h18v6H3zM3 14h18v6H3zM7 7h.01M7 17h.01",
    "perms": "M8 6h8a6 6 0 010 12H8A6 6 0 018 6zM16 15a3 3 0 100-6 3 3 0 000 6",
    "writes": "M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4z",
    "what": "M4 4h13v16H6a2 2 0 01-2-2zM17 8h3v10a2 2 0 01-2 2M8 8h5M8 12h5M8 16h3",
    "coverage": "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
    "tracking": "M12 3a9 9 0 100 18 9 9 0 000-18zM12 7v5l3 2",
    "goals2": "M4 6h16M4 12h16M4 18h10",
}
CHECK = "M20 6L9 17l-5-5"


def icon_url(k):
    ic = APPS.get(k, {}).get("icon", k)
    for ext in ("svg", "png"):
        if (docs / "family" / f"{ic}-tile.{ext}").exists():
            return f"/family/{ic}-tile.{ext}"
    return "/family/glyph-tile.svg"


def app(k):
    """Our side from compare.json, their side from rivals/<k>.json when it is not inline."""
    a = dict(data[k])
    f = root / "scripts/rivals" / f"{k}.json"
    if f.exists() and "rivals" not in a:
        r = json.loads(f.read_text())
        a["rows"], a["rivals"] = r["rows"], r["rivals"]
    for rv in a.get("rivals", []):
        rv.setdefault("logo", fetch_logo(rv))
    return a


def fetch_logo(rv):
    """A rival's own icon, saved once into docs/logos/ so the page loads nothing from their site."""
    for ext in ("webp", "png", "svg", "jpg", "ico"):
        if (docs / "logos" / f"{rv['slug']}.{ext}").exists():
            return f"/logos/{rv['slug']}.{ext}"
    url = rv.get("logo_url")
    if not url:
        return "/family/glyph-small.svg"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    body = urllib.request.urlopen(req, timeout=20).read()
    ext = "svg" if body.lstrip()[:5] in (b"<svg ", b"<?xml") else "ico" if body[:4] == b"\x00\x00\x01\x00" else "png" if body[:4] == b"\x89PNG" else "jpg" if body[:2] == b"\xff\xd8" else "webp" if body[8:12] == b"WEBP" else None
    if not ext:
        raise SystemExit(f"{rv['slug']}: {url} is not an image")
    (docs / "logos" / f"{rv['slug']}.{ext}").write_bytes(body)
    return f"/logos/{rv['slug']}.{ext}"


def price_tag(cell):
    """The paid price, short, for the head-to-head: '$15/mo'. Free when there is no paid figure."""
    t = cell[0] if isinstance(cell, list) else cell
    m = re.search(r"\$([\d,.]+)(?:\s*(?:a|per|/)\s*(?:user |seat |user a |seat a )?(month|mo|year|yr|once))?", t)
    if not m:
        return "Free" if t.lower().startswith("free") else "Paid"
    per = {"month": "/mo", "mo": "/mo", "year": "/yr", "yr": "/yr", "once": " once"}.get(m.group(2) or "", "")
    return f"${m.group(1).rstrip('.')}{per}"


# On a phone the app pages' tabs take short names, so the ribbon fits from 320px (2026-11-22).
SHORT = {"Overview": "App", "How it works": "How", "In the open": "Open", "Releases": "Builds"}


def ribbon(k, here="", base="", tabs=None):
    tabs = tabs or tabs_for(k)
    out = []
    for t, label in tabs:
        href = (base or "/" + ("" if k == "home" else k)) if not t else (f"{base}#{t}" if base else f"#{t}")
        cur = ' aria-current="page"' if t == here else ""
        sh = SHORT.get(label) if k != "home" else None
        text = f'<span class="lf">{label}</span><span class="ls">{sh}</span>' if sh else label
        out.append(f'<a href="{href}" data-tab="{t}"{cur}>{text}</a>')
    # Every page but the home starts with the way home (Fru, 2026-11-22: "how i get back to the main page").
    # Fru, 2026-11-22: "make it more prominent that somebody knows that's something you can click on to get back to the home".
    home = ('<a class="home" href="/" title="glyph.fru.dev">'
            '<img src="/family/glyph-tile.svg" width="22" height="22" alt="">Home</a>')
    return f'<nav class="ribbon" aria-label="Sections">{home}{"".join(out)}</nav>'


def tabs_for(k):
    if k == "home":
        return [("", "Overview"), ("apps", "Apps"), ("compare", "Compare"), ("open", "In the open"), ("faq", "FAQ")]
    return [("", "Overview"), ("how", "How it works"), ("compare", "Compare"),
            ("open", "In the open" if data[k].get("repo") else data[k].get("open_tab", "Releases")), ("faq", "FAQ")]


def cite(rv, cell):
    v, src = (cell + [None])[:2] if isinstance(cell, list) else (cell, None)
    if src is None:
        return f'<span class="t">{e(v)}</span>'
    return (f'<span class="t">{e(v)}<a class="cite" href="{e(rv["sources"][src - 1])}" target="_blank" '
            f'rel="noreferrer nofollow" title="{e(rv["name"])}\'s own page">{src}</a></span>')


def duel(k, a, rv):
    """The head-to-head card: our tile and price against theirs, struck through."""
    ours = a["ours"].get("price", "Free")
    big = a.get("duel_big") or ("Free" if ours.lower().startswith("free") else ours.split(",")[0])
    theirs = price_tag(rv["cells"].get("price", "Not stated"))
    # No strike where the comparison is not like for like (Bot runs on AI tools you pay for yourself).
    struck = f"<s>{e(theirs)}</s>" if theirs not in ("Free", "Paid") and not a.get("no_strike") else f"<span>{e(theirs)}</span>"
    return (f'<div class="duel"><div class="side us"><img src="{icon_url(k)}" width="72" height="72" alt=""><b>{e(a["name"])}</b>'
            f'<span class="big">{e(big)}</span></div><div class="vs">vs</div>'
            f'<div class="side"><img src="{e(rv["logo"])}" width="72" height="72" alt=""><b>{e(rv["name"])}</b>'
            f'<span class="big them">{struck}</span></div></div>')


def rows(k, a, rv):
    rs = [r for r in a["rows"] if not r.get("only") or r["only"] == rv["group"]]
    out = []
    for i, r in enumerate(rs):
        ours = a["ours"].get(r["k"], "")
        out.append(f'<div class="cr" style="--i:{i}"><div class="lab">{svg(ROWICON.get(r["k"], ROWICON["goals2"]))}{e(r["label"])}</div>'
                   f'<div class="c us">{svg(CHECK, "ok")}<span class="t">{e(ours)}</span></div>'
                   f'<div class="c">{cite(rv, rv["cells"].get(r["k"], "Not stated"))}</div></div>')
    head = (f'<div class="cr hd"><div class="lab"></div><div class="c us"><img src="{icon_url(k)}" width="26" height="26" alt="">{e(a["name"])}</div>'
            f'<div class="c"><img src="{e(rv["logo"])}" width="26" height="26" alt="">{e(rv["name"])}</div></div>')
    return f'<div class="cmp" role="table">{head}{"".join(out)}</div>'


def picks(a, rv):
    p = a["pick"].get(rv["group"], a["pick"]["default"])
    return (f'<div class="picks"><div><h3>When to pick {e(rv["name"])}</h3><p>{e(rv["pick"])}</p></div>'
            f'<div class="us"><h3>When to pick {e(a["name"])}</h3><p>{e(p)}</p></div></div>')


def asof(a):
    d = date.fromisoformat(a["as_of"])
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def ghj(path):
    out = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out.replace("]\n[", ",").replace("][", ","))


def releases(repo):
    return [(r["tag_name"], r["name"] or r["tag_name"], r["published_at"], r["html_url"]) for r in ghj(f"repos/{repo}/releases?per_page=100")]


def family():
    repos = FAM.split(",")
    return {"stars": sum(ghj(f"repos/{r}")["stargazers_count"] for r in repos),
            "downloads": sum(x["download_count"] for r in repos for rel in ghj(f"repos/{r}/releases?per_page=100") for x in rel["assets"])}


def day(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def timeline(rels):
    """Every release as a dot on one line of time: the pace, at a glance."""
    if not rels:
        return ""
    ts = [datetime.fromisoformat(r[2].replace("Z", "+00:00")).timestamp() for r in rels]
    lo, hi = min(ts), max(max(ts), datetime.now().timestamp())
    span = (hi - lo) or 1
    dots = "".join(f'<i style="left:{100 * (t - lo) / span:.2f}%;--i:{n}" title="{e(r[0])}, {day(r[2])}"></i>'
                   for n, (t, r) in enumerate(sorted(zip(ts, rels))))
    return (f'<figure class="tl"><div class="track">{dots}</div>'
            f'<figcaption><span>{day(min(rels, key=lambda r: r[2])[2])}</span><b>{len(rels)} releases</b><span>today</span></figcaption></figure>')


def stats(a=None):
    out = [f'<a class="stat" href="https://github.com/fru-dev3" target="_blank" rel="noreferrer"><b class="n" data-stars="{FAM}" data-floor="{GH["stars"]}" data-count="{GH["stars"]}">{GH["stars"]:,}</b><span>stars across Glyph</span></a>',
           f'<a class="stat" href="https://github.com/fru-dev3/glyph-native/releases" target="_blank" rel="noreferrer"><span data-downloads="{FAM}" data-match="." data-floor="{GH["downloads"]}" data-label="downloads across Glyph"><b class="n" data-count="{GH["downloads"]}">{GH["downloads"]:,}</b></span><span>downloads across Glyph</span></a>']
    return out


def close(k):
    href = "/" if k == "home" else f"/{k}"
    return (f'<a class="pclose" href="{href}" aria-label="Close, back to the overview" title="Close (Esc)">'
            f'{svg("M6 6l12 12M18 6L6 18")}</a>')


def cta(back_k=None, back_name=None):
    back = f'<a class="btn ghost" href="/{back_k}">Back to {e(back_name)}</a>' if back_k else ""
    return (f'<p class="row-btns"><a class="btn go" href="{INSTALL}" data-dmg="fru-dev3/glyph-native" data-track="file_download">'
            f'{svg("M12 3v12m0 0l-5-5m5 5l5-5M5 21h14")}Install Glyph Native</a>{back}</p>')


def panels(k):
    a = app(k)
    # How it works: a stepper. The steps on the left take turns; the picture on the right follows.
    steps = "".join(f'<li><button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" data-i="{i}">'
                    f'<span class="no">{i + 1:02d}</span><b>{e(s["title"])}</b><span class="p">{e(s["text"])}</span><i class="bar"></i></button></li>'
                    for i, s in enumerate(a["how"]))
    shots = "".join(f'<img class="{"on" if i == 0 else ""}{" tall" if s["h"] > s["w"] else ""}" data-i="{i}" src="{e(s["img"])}" width="{s["w"]}" height="{s["h"]}" alt="{e(s["alt"])}" loading="lazy">'
                    for i, s in enumerate(a["how"]))
    # Compare: a rival picker, the head-to-head, the rows.
    chips, cards = [], []
    for i, rv in enumerate(a["rivals"]):
        chips.append(f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" data-r="{rv["slug"]}">'
                     f'<img src="{e(rv["logo"])}" width="32" height="32" alt="">{e(rv["name"])}</button>')
        cards.append(f'<div class="rv" data-r="{rv["slug"]}"{"" if i == 0 else " hidden"}>{duel(k, a, rv)}<p class="thesis">{e(rv["thesis"])}</p>'
                     f'{rows(k, a, rv)}{picks(a, rv)}<p class="more"><a href="/{k}/vs/{rv["slug"]}">{e(a["name"])} vs {e(rv["name"])}: the full page, with sources {svg("M5 12h14M13 6l6 6-6 6", "arr")}</a></p></div>')
    groups = "".join(f'<div class="grp"><span>{e(g)}</span><div class="chips">' + "".join(c for c, rv in zip(chips, a["rivals"]) if rv["group"] == g) + "</div></div>"
                     for g in dict.fromkeys(rv["group"] for rv in a["rivals"]))
    faq = "".join(f'<details><summary>{e(q)}</summary><p>{e(ans)}</p></details>' for q, ans in a["faq"])
    repo = a.get("repo")
    if repo:
        rels = releases(repo)
        rel_li = "".join(f'<li style="--i:{n}"><b>{e(t)}</b><a href="{e(u)}">{e(nm)}</a><span>{day(d)}</span></li>' for n, (t, nm, d, u) in enumerate(rels[:6]))
        open_body = f'''<h2 id="open-h">Built in the open</h2><p class="pl">The code, every release and every star are public on GitHub. These numbers are read from there.</p>
  <div class="stats">{"".join(stats())}
    <a class="stat" href="https://github.com/{repo}/releases" target="_blank" rel="noreferrer"><b data-count="{len(rels)}">{len(rels)}</b><span>releases of {e(a["name"])}</span></a>
    <a class="stat" href="https://github.com/{repo}/releases/latest" target="_blank" rel="noreferrer"><b>{e(rels[0][0]) if rels else ""}</b><span>latest, {day(rels[0][2]) if rels else ""}</span></a>
  </div>
  {timeline(rels)}
  <div class="two"><div><h3>Recent releases</h3><ul class="rels">{rel_li}</ul></div>
  <div><h3>People who starred Glyph</h3><div class="faces big" data-faces></div>
  <p class="row-btns"><a class="btn go" href="https://github.com/{repo}">{svg("M8 6l-6 6 6 6M16 6l6 6-6 6")}Read the code</a><a class="btn ghost" href="https://github.com/{repo}/issues">Ask or report an issue</a></p></div></div>'''
    else:
        lede = a.get("open_lede") or f"{a['name']} is installed and kept up to date by Glyph Native, signed and notarized by Apple. Its code is private for now; the family's numbers are public on GitHub."
        link, label = a.get("open_link") or [f"https://github.com/fru-dev3/glyph-native/releases/tag/{k}", f"{a['name']} builds on GitHub"]
        open_body = f'''<h2 id="open-h">{e(a.get("open_tab", "Releases"))}</h2><p class="pl">{e(lede)}</p>
  <div class="stats">{"".join(stats())}
    <a class="stat" href="{e(link)}" target="_blank" rel="noreferrer"><b>{svg("M5 12h14M13 6l6 6-6 6", "ic big")}</b><span>{e(label)}</span></a>
  </div>
  <div class="two"><div><h3>People who starred Glyph</h3><div class="faces big" data-faces></div></div>
  {f'<div><h3>Your data stays yours</h3><p class="pl sm">{e(a["ours"]["storage"])}. Nothing is sent to fru.dev.</p></div>' if a["ours"].get("storage") else ""}</div>'''
    return f'''<!-- ribbon -->
{ribbon(k)}
<section class="panel" id="how" hidden aria-labelledby="how-h">{close(k)}<div class="pin">
  <h2 id="how-h">How it works</h2><p class="pl">{e(a["how_lede"])}</p>
  <div class="stepper"><ol class="steplist" role="tablist">{steps}</ol><div class="shots">{shots}</div></div>
  {cta(k, a["name"])}
</div></section>
<section class="panel" id="compare" hidden aria-labelledby="cmp-h">{close(k)}<div class="pin">
  <h2 id="cmp-h">{e(a["name"])} side by side</h2><p class="pl">Pick an app. Every fact about it links to its own site, as of {asof(a)}.</p>
  <div class="rivals" role="tablist" aria-label="Compare with">{groups}</div>
  {"".join(cards)}
</div></section>
<section class="panel" id="open" hidden aria-labelledby="open-h">{close(k)}<div class="pin">
  {open_body}
</div></section>
<section class="panel" id="faq" hidden aria-labelledby="faq-h">{close(k)}<div class="pin">
  <h2 id="faq-h">Questions</h2>
  <div class="faq">{faq}</div>
  {cta(k, a["name"])}
</div></section>
<!-- /ribbon -->'''


def monthly(cell):
    """A rival's cheapest paid plan as dollars a month, or None. Yearly-only plans are divided by 12."""
    t = cell[0] if isinstance(cell, list) else cell
    m = re.search(r"\$([\d,.]+)\s*(?:a |per |/)\s*(?:user |seat |member )?(?:a )?(month|mo)\b", t)
    if m:
        return float(m.group(1).replace(",", "").rstrip("."))
    m = re.search(r"\$([\d,.]+)\s*(?:a |per |/)\s*(?:user |seat |member )?(?:a )?(year|yr)\b", t)
    return round(float(m.group(1).replace(",", "").rstrip(".")) / 12, 2) if m else None


def home_panels():
    """The home: the family as a map, a calculator of what it replaces, the proof, questions."""
    h = data["home"]
    k = "home"
    # Fru, 2026-11-22: "uneven and full of text wall". The family as a home screen: even icons, a name, nothing else.
    core, tools = h["layers"][:4], h["layers"][4]
    icon = lambda p, n, sub=None: (f'<a class="ai" href="/{p}" style="--i:{n}" title="{e(data[p]["tag"])}"><img src="{icon_url(p)}" width="112" height="112" alt="">'
                                   f'<b>{e(APPS[p]["short"] if "short" in APPS[p] else APPS[p]["name"])}</b>{f"<span>{e(sub)}</span>" if sub else ""}</a>')
    layers = [f'<div class="grid core4">{"".join(icon(keys[0], n, sub) for n, (title, sub, keys) in enumerate(core))}</div>'
              f'<div class="grid tools9">{"".join(icon(p, n + 4) for n, p in enumerate(tools[2]))}</div>']
    # The calculator: the cheapest paid plan of each rival with a monthly price, ticked by default for one per app.
    rows_ = []
    for p in h["calc"]:
        a = app(p)
        tiles = []
        for n, rv in enumerate(a["rivals"]):
            m = h["monthly"][rv["slug"]] if rv["slug"] in h.get("monthly", {}) else monthly(rv["cells"].get("price", ""))
            if m:
                tiles.append(f'<label class="pt" title="{e(rv["name"])}, ${m:g} a month"><input type="checkbox" value="{m}"{" checked" if n == 0 else ""}>'
                             f'<img src="{e(rv["logo"])}" width="44" height="44" alt="{e(rv["name"])}" data-n="{e(rv["name"])}"><s>${m:g}</s></label>')
        if tiles:
            # Fru, 2026-11-22: the paid apps and Glyph must not look alike. Paid on the left, quiet; an arrow; Glyph on the right, solid green.
            # Fru, 2026-11-22: the green block installs ("make it as easy as possible to install"); Glyph Native installs every app.
            pop = '<i class="pop">Popular</i>' if p in h.get("popular", []) else ""
            rows_.append(f'<div class="prow"><div class="pts">{"".join(tiles)}</div><span class="parr" aria-hidden="true">{svg("M5 12h14M13 6l6 6-6 6")}</span>'
                         f'<a class="pa" href="{INSTALL}" data-dmg="fru-dev3/glyph-native" data-track="file_download" data-app="{p}" title="Install {e(a["name"])} with Glyph Native">'
                         f'<img src="{icon_url(p)}" width="40" height="40" alt=""><b>{e(a["short"])}{pop}</b><span>{svg("M12 3v12m0 0l-5-5m5 5l5-5M5 21h14")}Install</span></a></div>')
    faq = "".join(f'<details><summary>{e(q)}</summary><p>{e(ans)}</p></details>' for q, ans in h["faq"])
    return f'''<!-- ribbon -->
{ribbon("home")}
<section class="panel" id="apps" hidden aria-labelledby="apps-h">{close("home")}<div class="pin wide">
  <h2 id="apps-h">The Glyph family</h2>
  {"".join(layers)}
</div></section>
<section class="panel" id="compare" hidden aria-labelledby="cmp-h">{close("home")}<div class="pin wide">
  <h2 id="cmp-h">What Glyph replaces</h2><p class="pl">Tap what you pay for today. Glyph's answer to each is free.</p>
  <div class="calc"><div class="phead"><span>What you pay for today</span><span>Glyph instead</span></div><div class="clab">Your total</div>
  <div class="prows">{"".join(rows_)}</div>
  <aside class="total"><div class="tt"><span>You would stop paying</span><b class="sum" data-sum>$0</b><span>a month, or <b data-year>$0</b> a year</span></div><div class="drop" data-drop aria-live="polite"></div>
  <span class="glyph">Glyph: <b>$0</b></span></aside></div>
</div></section>
<section class="panel" id="open" hidden aria-labelledby="open-h">{close("home")}<div class="pin wide">
  <h2 id="open-h">Built in the open</h2><p class="pl">Stars, downloads and releases, read from GitHub.</p>
  <div class="stats">{"".join(stats())}<a class="stat" href="https://github.com/fru-dev3" target="_blank" rel="noreferrer"><b data-count="{len(APPS)}">{len(APPS)}</b><span>apps in the family</span></a></div>
  <h3>People who starred Glyph</h3><div class="faces big" data-faces></div>
  <p class="row-btns"><a class="btn go" href="https://github.com/fru-dev3">{svg("M8 6l-6 6 6 6M16 6l6 6-6 6")}Read the code</a></p>
</div></section>
<section class="panel" id="faq" hidden aria-labelledby="faq-h">{close(k)}<div class="pin">
  <h2 id="faq-h">Questions</h2>
  <div class="faq">{faq}</div>
  {cta()}
</div></section>
<!-- /ribbon -->'''


def vs_page(k, a, rv):
    url = f"https://glyph.fru.dev/{k}/vs/{rv['slug']}"
    title = f'{a["name"]} vs {rv["name"]} | {rv["alt_title"]}'
    desc = f'{a["name"]} and {rv["name"]} side by side, with sources: {rv["thesis"]}'
    short = "".join(f"<li>{svg(CHECK, 'ok')}<span>{e(x)}</span></li>" for x in rv["short"])
    bare = lambda u: re.sub(r"^https?://(www\.)?", "", u)
    srcs = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noreferrer nofollow">{e(bare(u))}</a></li>' for u in rv["sources"])
    others = "".join(f'<a href="/{k}/vs/{o["slug"]}"><img src="{e(o["logo"])}" width="28" height="28" alt="">{e(o["name"])}</a>' for o in a["rivals"] if o is not rv)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="icon" href="{icon_url(k)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#F7FBF5">
<meta property="og:site_name" content="Glyph Labs">
<meta property="og:type" content="article">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://glyph.fru.dev/og-image.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/site.css">
</head>
<body data-page="{k}-vs-{rv["slug"]}" class="vs">
{ribbon(k, "compare", f"/{k}")}
<main class="doc"><div class="pin">
  <p class="crumb"><a href="/{k}#compare">{e(a["name"])} side by side</a></p>
  <h1>{e(a["name"])} vs {e(rv["name"])}</h1>
  <p class="pl">{e(rv["thesis"])}</p>
  {duel(k, a, rv)}
  <h2>The short version</h2><ul class="short">{short}</ul>
  <h2>Side by side</h2><p class="fine">As of {asof(a)}. The numbers link to {e(rv["name"])}'s own pages.</p>
  {rows(k, a, rv)}
  {picks(a, rv)}
  {cta(k, a["name"])}
  <h2>Also compared</h2><div class="others">{others}</div>
  <h2>Sources</h2><ol class="srcs">{srcs}</ol>
</div></main>
<footer><div class="bar"><nav aria-label="Footer"><a class="home" href="/"><img src="/family/glyph-small.svg" width="16" height="16" alt="">Glyph</a><a href="/{k}">{e(a["name"])}</a><a class="legal-link" href="/legal">Disclaimer</a></nav></div></footer>
<script src="/site.js"></script>
</body>
</html>
'''


def bake(path, block):
    s = path.read_text()
    if "<!-- ribbon -->" in s:
        s = re.sub(r"<!-- ribbon -->.*?<!-- /ribbon -->", lambda m: block, s, flags=re.S)
    else:
        s = s.replace("<main", block + "\n<main", 1)
    path.write_text(s)


def sitemap(k, a):
    sm = docs / "sitemap.xml"
    lines = [l for l in sm.read_text().splitlines() if f"glyph.fru.dev/{k}/vs/" not in l]
    lines[-1:-1] = [f'  <url><loc>https://glyph.fru.dev/{k}/vs/{rv["slug"]}</loc><lastmod>{a["as_of"]}</lastmod>'
                    f'<changefreq>monthly</changefreq><priority>0.7</priority></url>' for rv in a["rivals"]]
    sm.write_text("\n".join(lines) + "\n")


def main(keys):
    global GH
    GH = family()
    for k in keys:
        if k == "home":
            bake(docs / "index.html", home_panels())
            print("home: ribbon")
            continue
        a = app(k)
        bake(docs / k / "index.html", panels(k))
        for rv in a["rivals"]:
            out = docs / k / "vs" / rv["slug"] / "index.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(vs_page(k, a, rv))
        sitemap(k, a)
        print(f"{k}: ribbon + {len(a['rivals'])} vs pages")


if __name__ == "__main__":
    main(sys.argv[1:] or [k for k in data if k != "home"] + ["home"])

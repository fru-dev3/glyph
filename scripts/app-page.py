#!/usr/bin/env python3
"""One page per app, stamped from docs/time/index.html.

    python3 scripts/app-page.py wealth      # writes docs/wealth/index.html from scripts/app-pages.json

Glyph Time's page is the pattern (one bright screen, the screens taking turns, Features behind
the footer link). The apps that arrived on the strip on 2026-11-19 had a tile and no page, so
/wealth answered 404. This fills in the words and the pictures and leaves the frame alone, so a
change to the frame is made once, in Time's page, and stamped again.
No rival prices here: a price nobody checked is an invented number.
"""
import json, re, sys, html
from pathlib import Path

root = Path(__file__).resolve().parent.parent
pages = json.loads((root / "scripts/app-pages.json").read_text())
t = (root / "docs/time/index.html").read_text()
e = html.escape


def between(s, a, b, new, keep_b=True):
    i = s.index(a); j = s.index(b, i)
    return s[:i] + new + s[j if keep_b else j + len(b):]


def icon(d):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true"><path d="%s"/></svg>' % d)


ICONS = {"mac": "M3 5h18v11H3zM1 20h22", "phone": "M8 2h8a2 2 0 012 2v16a2 2 0 01-2 2H8a2 2 0 01-2-2V4a2 2 0 012-2zM11 18h2",
         "chart": "M4 20V10M10 20V4M16 20v-7M22 20H2", "list": "M4 6h16M4 12h16M4 18h10",
         "clock": "M12 3a9 9 0 100 18 9 9 0 000-18zM12 7v5l3 2", "gear": "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M16 4v4M10 10v4M18 16v4",
         "tag": "M9 3L7 21M17 3l-2 18M4 9h17M3 15h17", "people": "M16 19v-1a4 4 0 00-4-4H7a4 4 0 00-4 4v1M9.5 10a3.5 3.5 0 100-7 3.5 3.5 0 000 7M21 19v-1a4 4 0 00-3-3.8",
         "heart": "M12 21s-7.5-4.6-10-9.3C.4 8.4 2.3 4.5 6.2 4.5c2.4 0 4 1.4 5.8 3.5 1.8-2.1 3.4-3.5 5.8-3.5 3.9 0 5.8 3.9 4.2 7.2C19.5 16.4 12 21 12 21z",
         "target": "M12 3a9 9 0 100 18 9 9 0 000-18zM12 8a4 4 0 100 8 4 4 0 000-8z", "plug": "M9 3v6M15 3v6M6 9h12v3a6 6 0 01-12 0zM12 18v3",
         "doc": "M14 3H6a1 1 0 00-1 1v16a1 1 0 001 1h12a1 1 0 001-1V8zM14 3v5h5"}


def page(k):
    p = pages[k]; name = p["name"]; url = "https://glyph.fru.dev/" + k
    s = t
    head = f'''<title>{e(p["title"])}</title>
<meta name="description" content="{e(p["description"])}">
<link rel="icon" href="/family/{k}-tile.svg" type="image/svg+xml">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="author" content="fru.dev">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#F7FBF5">
<meta property="og:site_name" content="Glyph Labs">
<meta property="og:type" content="website">
<meta property="og:title" content="{e(p["title"])}">
<meta property="og:description" content="{e(p["description"])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="https://glyph.fru.dev/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="The Glyph family of app icons in office green">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@fru">
<meta name="twitter:image" content="https://glyph.fru.dev/og-image.png">
'''
    s = between(s, "<title>", '<link rel="preconnect"', head)
    ld = json.dumps({"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": "https://fru.dev/#org", "name": "fru.dev", "legalName": "Inspired Nation, LLC",
         "url": "https://fru.dev", "logo": "https://fru.dev/icon-512.png", "sameAs": ["https://github.com/fru-dev3"]},
        {"@type": "SoftwareApplication", "@id": url + "#app", "name": name, "applicationCategory": p["category"],
         "operatingSystem": "macOS 26 or later (Apple silicon)", "url": url, "isAccessibleForFree": True,
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "publisher": {"@id": "https://fru.dev/#org"},
         "description": p["description"]}]}, indent=1)
    s = between(s, '<script type="application/ld+json">', "</script>", '<script type="application/ld+json">\n' + ld + "\n")
    s = s.replace('<body data-page="time">', f'<body data-page="{k}">')
    top = f'''<div class="top">
      <a class="brand" href="/{k}"><img class="icon" src="/family/{k}-tile.svg" width="72" height="72" alt=""><div><b>{e(name)}</b><span>{e(p["tagline"])}</span></div></a>
      <h1 data-lines='{e(json.dumps(p["lines"]), quote=False).replace("'", "&#39;")}'>{e(p["lead"])} <em><span id="said">{e(p["lines"][0])}</span><i class="caret" aria-hidden="true"></i></em></h1>
    </div>
    '''
    s = between(s, '<div class="top">', '<div class="cta loved">', top)
    s = re.sub(r'<p class="nat">.*?</p>', f'<p class="nat">Glyph Native installs {e(name)} and keeps it up to date.</p>', s, count=1)
    s = re.sub(r'<p class="note">.*?</p>', f'<p class="note">{e(p["note"])}</p>', s, count=1)
    # "Open source" is true of Time and not of an app whose source is private.
    s = s.replace("Open source</li>", e(p.get("badge3", "Free")) + "</li>")
    views, tabs, first = [], [], True
    for v in p["views"]:
        d = v["device"]
        imgs = "".join(
            f'<img class="{"phone" if d == "iphone" else "shot"}" src="/{k}/{i["src"]}" width="{i["w"]}" height="{i["h"]}" alt="{e(i["alt"])}" '
            + ('fetchpriority="high"' if first and n == 0 else 'loading="lazy"') + ">" for n, i in enumerate(v["imgs"]))
        views.append(f'      <figure class="view{" on" if first else ""}" data-k="{v["k"]}" data-d="{d}" style="margin:0">{imgs}</figure>')
        tabs.append(f'      <button type="button" role="tab" aria-selected="{"true" if first else "false"}" data-k="{v["k"]}" data-d="{d}"'
                    + (" hidden" if d != p["views"][0]["device"] else "") + f'>{icon(ICONS[v["icon"]])}{e(v["label"])}</button>')
        first = False
    s = between(s, '      <figure class="view on"', "    </div>\n    <div class=\"seg\" id=\"tabs\"", "\n".join(views) + "\n")
    s = between(s, '<div class="seg" id="tabs" role="tablist" aria-label="Glyph Time on screen">',
                "    </div>\n  </div>\n</main>",
                f'<div class="seg" id="tabs" role="tablist" aria-label="{e(name)} on screen">\n' + "\n".join(tabs) + "\n")
    s = s.replace("iPhone <small>testing</small>", "iPhone")
    feats = "\n".join(f'    <div class="fq"><h3>{e(h)}</h3><p>{e(b)}</p></div>' for h, b in p["features"])
    s = between(s, '<div class="fhead"><img src="/family/time-tile.svg"', '<button type="button" class="fclose"',
                f'<div class="fhead"><img src="/family/{k}-tile.svg" width="40" height="40" alt=""><h2 id="feat-h">Everything {e(name)} does</h2>')
    s = between(s, '  <div class="flist">', "  </div>\n</dialog>", '  <div class="flist">\n' + feats + "\n")
    nav = '''<a class="opt" href="/bot" title="Where your agents read it">Bot</a>
      <a class="opt" href="https://github.com/fru-dev3/glyph-native/releases" title="Every release">Releases</a>
      <a class="opt" href="https://github.com/fru-dev3/glyph/issues" title="Contact: open an issue">Contact</a>
      '''
    s = between(s, '<a class="opt" href="/bot"', '<a class="opt" href="https://fru.dev">', nav)
    s = s.replace('<a class="built" href="https://github.com/fru-dev3/glyph-time">', '<a class="built" href="https://github.com/fru-dev3/glyph">')
    s = s.replace('track("time_view"', f'track("{k}_view"').replace('track("time_device"', f'track("{k}_device"')
    # the Install button counts the whole family's downloads, Time's among them
    left = [m for m in re.findall(r"[^\n]*(?:glyph-time|Glyph Time|/time[/\"])[^\n]*", s) if "data-downloads" not in m]
    assert not left, "still says Time:\n" + "\n".join(x[:160] for x in left)
    (root / "docs" / k).mkdir(exist_ok=True)
    (root / "docs" / k / "index.html").write_text(s)
    print("wrote docs/%s/index.html" % k, len(s))


for k in sys.argv[1:] or pages:
    page(k)

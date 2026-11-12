#!/usr/bin/env python3
"""Bake the real family download total into every page's data-floor, so a visitor GitHub
rate-limits still sees the true number (as of the last ship) and not an old one. Never lowers it."""
import glob, json, re, subprocess, sys

total, pages = None, glob.glob("docs/**/index.html", recursive=True)
for path in pages:
    html = open(path).read()
    m = re.search(r'data-downloads="([^"]+)" data-match="([^"]+)" data-floor="(\d+)"', html)
    if not m or "," not in m.group(1):
        continue  # only the family total (several repos)
    if total is None:
        rx, total = re.compile(m.group(2).replace("\\\\", "\\")), 0
        for repo in m.group(1).split(","):
            out = subprocess.run(["gh", "api", f"repos/{repo.strip()}/releases", "--paginate",
                                  "-q", ".[].assets[] | [.name, .download_count] | @json"],
                                 capture_output=True, text=True)
            if out.returncode:
                sys.exit(f"could not read {repo}: floors left as they are")
            total += sum(c for n, c in map(json.loads, out.stdout.splitlines()) if rx.search(n))
    if total > int(m.group(3)):
        open(path, "w").write(html.replace(m.group(0), m.group(0).replace(f'data-floor="{m.group(3)}"', f'data-floor="{total}"')))
        print(f"{path}: {m.group(3)} -> {total}")
print("family downloads:", total)

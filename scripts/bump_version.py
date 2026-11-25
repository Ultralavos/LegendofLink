"""Bump Legend of Link's version (owner: +0.001 with every change set) everywhere it shows:
the title screen (build/lol/lol_seedcode.py), the page and its file names (web/app.js), the README, and the
?v= on the pages' own scripts and styles (so a browser never mixes a new page with old cached files).
Then rebuild the booklet (its cover shows the version): python3 manual/gen.py.

Usage: python3 scripts/bump_version.py [new version]   (default: the current one + 0.001)"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "build/lol/lol_seedcode.py"
cur = re.search(r'^VERSION = "([\d.]+)"', SEED.read_text(), re.M).group(1)
new = sys.argv[1] if len(sys.argv) > 1 else f"{float(cur) + 0.001:.3f}"


def sub(path, pattern, repl, count=1):
    p = ROOT / path
    s = p.read_text()
    t, n = re.subn(pattern, repl, s, count=count, flags=re.M)
    assert n, (path, pattern)
    p.write_text(t)


sub("build/lol/lol_seedcode.py", r'^VERSION = "[\d.]+"', f'VERSION = "{new}"')
sub("web/app.js", r'^const VERSION = "[\d.]+";   // \(owner: Beta [\d.]+,', f'const VERSION = "{new}";   // (owner: Beta {new},')
sub("README.md", r"LEGEND OF LINK / BETA [\d.]+", f"LEGEND OF LINK / BETA {new}")
for page in ("web/index.html", "web/tracker/index.html"):
    sub(page, r'((?:src|href)="[\w./-]+\.(?:js|css))(\?v=[\d.]+)?"', rf'\1?v={new}"', count=0)
print(f"{cur} -> {new}")

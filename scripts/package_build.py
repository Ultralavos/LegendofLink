"""Pack the build for the page: web/lol-build.zip holds build/ (the Legend of Link modules and data) and zora/ (the
ZORA package the build sits on). Usage: python3 scripts/package_build.py PATH_TO_ZORA_CHECKOUT"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
zora = sys.argv[1]
out = os.path.join(ROOT, "web", "lol-build.zip")
skip = ("__pycache__", ".pyc")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for base, arc in ((os.path.join(ROOT, "build"), "build"), (os.path.join(zora, "zora"), "zora/zora")):
        for d, _, files in os.walk(base):
            if "__pycache__" in d:
                continue
            for f in files:
                if f.endswith(skip):
                    continue
                p = os.path.join(d, f)
                z.write(p, os.path.join(arc, os.path.relpath(p, base)))
print(out, os.path.getsize(out), "bytes")

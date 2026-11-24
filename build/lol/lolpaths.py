"""Where the build's pieces are, relative to this checkout (no absolute paths).

build/lol      the Legend of Link modules (this folder)
build/q3/build the 3Q build the LoL build sits on (build_mock, build_q3)
ZORA           the ZORA package: $ZORA_PATH, else ../../zora next to build/, else an installed one
SOURCE_ROM     the player's clean ROM (bytes), set by lol_build before any module needs it
"""
import os
import sys

LOL = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.dirname(LOL)
Q3B = os.path.join(BUILD, "q3", "build")
ZORA = os.environ.get("ZORA_PATH", os.path.join(os.path.dirname(BUILD), "zora"))
GRID_FILE = os.path.join(LOL, "v2_grids", "grids.txt")
HINTS_FILE = os.path.join(LOL, "v2_grids", "hints.txt")
SOURCE_ROM = None

for _p in (Q3B, ZORA):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)


def source_rom():
    assert SOURCE_ROM is not None, "lol_build sets lolpaths.SOURCE_ROM first"
    return SOURCE_ROM

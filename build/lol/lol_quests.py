"""The quests' dungeon footprints (which squares are rooms), for the page's dungeon sets (docs/dungeon-sets.md).

footprints(quest) -> {level 1-9: (block, [cells])}: cells are squares (row * 16 + column) on that level's 8x16
block ("1-6" or "7-9"). 1Q and 2Q come from the player's ROM (lolpaths.source_rom, ZORA's parse); 3Q from
q3/grid_1_6.json and grid_7_9.json; 4Q from shapes/q4/q4_grids.json (level 9: its main part and the Torch wing).
"""
import json
import os

import lolpaths

BUILD = lolpaths.BUILD


def _rom_levels(second):
    from zora.rom.parse.rom_file import parse_rom
    w = parse_rom(lolpaths.source_rom())
    out = {}
    for lv in (w.levels_2q if second else w.levels):
        out[lv.level_num] = ("1-6" if lv.level_num <= 6 else "7-9", sorted(r.room_num for r in lv.rooms))
    return out


def _q3():
    out = {}
    g16 = json.load(open(os.path.join(BUILD, "q3", "grid_1_6.json")))
    for lv in range(1, 7):
        out[lv] = ("1-6", [r * 16 + c for r in range(8) for c in range(16) if g16[r][c] == lv])
    g79 = json.load(open(os.path.join(BUILD, "q3", "grid_7_9.json")))["rows"]
    for lv, ch in ((7, "r"), (8, "b"), (9, "g")):
        out[lv] = ("7-9", [r * 16 + c for r in range(8) for c in range(16) if g79[r][c] == ch])
    return out


def _q4():
    q = json.load(open(os.path.join(BUILD, "shapes", "q4", "q4_grids.json")))
    out = {}
    for key, info in q["levels"].items():
        block, letter = key.split(":")
        rows = q[block]["rows"]
        cells = [r * 16 + c for r in range(8) for c in range(16) if rows[r][c] == letter]
        lv = info["level"]
        b = "1-6" if block == "block_1_6" else "7-9"
        if lv in out:                           # (level 9's Torch wing: the same dungeon, its own piece)
            cells = sorted(set(out[lv][1]) | set(cells))
        out[lv] = (b, sorted(cells))
    return out


def footprints(quest):
    if quest == "1q":
        return _rom_levels(False)
    if quest == "2q":
        return _rom_levels(True)
    if quest == "3q":
        return _q3()
    if quest == "4q":
        return _q4()
    raise ValueError(quest)

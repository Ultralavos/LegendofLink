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
        n = lv.rom_level_num            # the number the game shows (2Q: slots 2-3, 4-5, 7-8 swapped)
        out[n] = ("1-6" if n <= 6 else "7-9", sorted(r.room_num for r in lv.rooms))
    return out


MAJOR = {"WOOD_BOOMERANG", "MAGICAL_BOOMERANG", "BOW", "SILVER_ARROWS", "BLUE_CANDLE", "RED_CANDLE", "RECORDER",
         "RAFT", "LADDER", "WAND", "BOOK", "MAGICAL_KEY", "BLUE_RING", "RED_RING", "POWER_BRACELET", "LETTER",
         "WOOD_SWORD", "WHITE_SWORD", "MAGICAL_SWORD", "MAGICAL_SHIELD"}


def _rom_rules(second):
    """{level: (item stairs, transports, walk-through share, a major item on the floor)} from the ROM's levels."""
    from zora.rom.parse.rom_file import parse_rom
    w = parse_rom(lolpaths.source_rom())
    out = {}
    for lv in (w.levels_2q if second else w.levels):
        items = sum(1 for s in lv.staircase_rooms if "ITEM" in s.room_type.name)
        cells = {r.room_num: r for r in lv.rooms}
        walk = total = 0
        for c, r in cells.items():
            for side, step in ((r.walls.east, 1), (r.walls.south, 16)):
                if (step == 1 and c % 16 == 15) or c + step not in cells:
                    continue
                total += 1
                walk += int(side.value) in (2, 3)
        floor = any(r.item is not None and r.item.name in MAJOR for r in lv.rooms)
        out[lv.rom_level_num] = (items, len(lv.staircase_rooms) - items, walk / total if total else 0.0, floor)
    return out


# 3Q (our designs, q3/level_N.json): item cellars, transports, walk-through walls / doors between its rooms, and
# whether a major item is on the floor or dropped (L1 white sword, L4 blue candle, L6 bow, L7 raft, L8 red candle)
Q3_RULES = {1: (1, 1, 4 / 24, True), 2: (1, 1, 2 / 15, False), 3: (1, 3, 2 / 10, False), 4: (1, 0, 6 / 29, True),
            5: (1, 1, 10 / 33, False), 6: (1, 2, 7 / 28, True), 7: (0, 5, 10 / 40, True), 8: (1, 6, 1 / 45, True),
            9: (1, 8, 9 / 38, False)}
# 4Q levels 1-5 (our designs: the 4Q build's rooms, walls, transports and cellars; floor: L1 bow, L2 blue candle,
# L3 the boomerangs, L5 bracelet); 6-9 aren't designed yet: 3Q's
Q4_RULES = {1: (0, 5, 4 / 24, True), 2: (0, 2, 3 / 22, True), 3: (0, 1, 0.0, True), 4: (1, 2, 2 / 21, False),
            5: (0, 2, 1 / 13, True),
            **{lv: Q3_RULES[lv] for lv in (6, 7, 8, 9)}}


def rules(quest):
    """{level 1-9: (item stairs, transports, walk-through share, floor item)}: the quest's own stair rules, its
    share of walk-through walls among the doors between rooms, and whether a major item lies on the floor there (then
    the level gets a floor badge / XP like LoL's levels 1 and 2)."""
    if quest in ("1q", "2q"):
        return _rom_rules(quest == "2q")
    return dict(Q3_RULES if quest == "3q" else Q4_RULES)


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


# The levels' nicknames (owner, 2026-11-24; 2Q by the level number the game shows), for the page and a spoiler log.
# 3Q's: the owner's picks (2026-11-24; 1-4 and 9 as proposed in q3/nicknames.json); 4Q's from the 4Q build (level 9:
# the Swiss Cheese with the Torch wing, one dungeon here).
NICKNAMES = {
    "1q": {1: "The Eagle", 2: "The Moon", 3: "The Manji", 4: "The Snake", 5: "The Lizard", 6: "The Dragon",
           7: "The Demon", 8: "The Lion", 9: "The Skull"},
    "2q": {1: "The E", 2: "The A", 3: "The L", 4: "The D", 5: "The Z", 6: "The Cap", 7: "The Flail",
           8: "The Whip", 9: "The Pig"},
    "3q": {1: "The Sword", 2: "The Kite", 3: "The Islands", 4: "The Candle", 5: "The Crane", 6: "The Dancer",
           7: "The Lock Picks", 8: "The Vire", 9: "The Serpent"},
    "4q": {1: "The Bow and Arrow", 2: "The Rabbit", 3: "The Broken Boomerang", 4: "The Whirlwind", 5: "The Hammer",
           6: "The Scorpion", 7: "The Armos", 8: "The Crown", 9: "The Swiss Cheese"},
}


def nickname(quest, level):
    return NICKNAMES.get(quest, {}).get(level, f"{quest.upper()} level {level}")

"""Legend of Link: dungeons A-F rebuilt on the user's map (the second quest's Level 1-6 block).

  A yellow   the note        entrance H15   (2Q level 1: 1Q Level 1's sprites / rooms)
  B cyan     the islands     entrance H6    (2Q level 3: 1Q Level 3's)
  C green    bird and post   entrance H10   (2Q level 2: 1Q Level 2's)
  D red      the guillotine  entrance H14   (2Q level 5: 1Q Level 5's)
  E blue     the bomb        entrance H4    (2Q level 4: 1Q Level 4's); hidden A4 / A7 behind walk-through walls
  F pink     the camel       entrance H9    (2Q level 6: 1Q Level 6's)

Sprite sets go by the level number in both quests, so each letter's rooms are copied from the first-quest level of
its number (or use that level's enemies). Each has a boss room (a blue potion) whose shutter is the only way into the
triforce room (A-F's reward); E and F have an old man's choice room; the only stairs are transports (both ends have
stairs). Walls: an open door between rooms of the same piece unless DOORS says otherwise, a wall elsewhere.

Writes the 2Q block of Levels 1-6 and those levels' LevelInfo replacement arrays (bank 6), as the 3Q/4Q builder's
q4_placeholders does.
"""
import sys

import lolpaths
B = lolpaths.Q3B
for p in (lolpaths.ZORA, B):
    if p not in sys.path:
        sys.path.insert(0, p)

GRID = ["BBwwEEwBwFCCCDCC",
        "BwwEFFEBFFFCCDCC",
        "wwEEEFFFFFFFCDCA",
        "wEEEEEwFFFFFCCCA",
        "EEEEEEEFFFFDDDDA",
        "EEEEEEEFFCFDDwDA",
        "BEEEEEBFFCFDDDAA",
        "BBEEEBBFFCFDwDAA"]
# A4 and A7 (white on the map) are E's hidden rooms
HIDDEN = {"E": {"A4", "A7"}}
LETTER_LEVEL = {"A": 1, "B": 3, "C": 2, "D": 5, "E": 4, "F": 6}   # lol_af.AF_LEVELS
ENTRANCES = {"A": "H15", "B": "H6", "C": "H10", "D": "H14", "E": "H4", "F": "H9"}
BOSS_ROOMS = {"A": "D16", "B": "A1", "C": "A12", "D": "B14", "E": "A5", "F": "B10"}
CHOICE_ROOMS_2Q = {4: "E3", 6: "G11"}          # by 2Q level (E, F)


def cell(name):
    return "ABCDEFGH".index(name[0]) * 16 + int(name[1:]) - 1


def name(n):
    return "ABCDEFGH"[n // 16] + str(n % 16 + 1)


def cells_of(letter):
    s = {r * 16 + c for r in range(8) for c in range(16) if GRID[r][c] == letter}
    return s | {cell(x) for x in HIDDEN.get(letter, ())}


# Rooms: name -> ("copy", 1Q level, 1Q room, {overrides}) or a tuple (layout, enemy, count, item, position, trigger,
# dark, push). Overrides: item, trigger, pos, enemy, count, layout, push, dark.
def C(lv, rm, **kw):
    return ("copy", lv, rm, kw)


def T(layout, enemy, count, item, pos="A", trigger="NONE", dark=False, push=False):
    return ("new", layout, enemy, count, item, pos, trigger, dark, push)


ROOMS = {
    "A": {
        "H15": T("ENTRANCE_ROOM", "NOTHING", 3, "NOTHING"),
        "H16": C(1, "E4"),                                            # five pair, gels, the map
        "G15": C(1, "D4"),                                            # stalfos, a key
        "G16": C(1, "F4"),                                            # stalfos, a key
        "F16": C(1, "E6"),                                            # wallmasters, a key
        "E16": C(1, "F5"),                                            # keese, the compass
        "D16": C(1, "D6", item="BLUE_POTION"),                        # Aquamentus
        "C16": C(1, "D7"),                                            # the triforce (reward)
    },
    "B": {
        "H6": T("ENTRANCE_ROOM", "NOTHING", 3, "NOTHING"),
        "H7": C(3, "G12"),                                            # zols, a key
        "G7": C(3, "G10", item="BOMBS"),                              # stairs -> B8
        "B8": T("SPIRAL_STAIR_ROOM", "BLUE_KEESE", 8, "MAP"),         # stairs <- G7
        "A8": T("NARROW_STAIR_ROOM", "ZOL", 5, "COMPASS", trigger="ALL_DEAD_ITEM"),   # stairs -> H2
        "H2": T("SPIRAL_STAIR_ROOM", "RED_DARKNUT", 5, "NOTHING"),   # stairs <- A8
        "H1": C(3, "E12"),                                            # zols, a key
        "G1": T("NARROW_STAIR_ROOM", "MIXED_ENEMY_GROUP_14", 8, "KEY", trigger="ALL_DEAD_ITEM"),   # stairs -> B1
        "B1": T("SPIRAL_STAIR_ROOM", "BLUE_KEESE", 5, "BOMBS", trigger="ALL_DEAD_ITEM"),   # stairs <- G1
        "A1": C(3, "E14", item="BLUE_POTION"),                        # Manhandla
        "A2": C(3, "D14"),                                            # the triforce
    },
    "C": {
        "H10": T("ENTRANCE_ROOM", "NOTHING", 3, "NOTHING"),
        "G10": C(2, "G13"),                                           # ropes, a key
        "F10": T("NARROW_STAIR_ROOM", "ROPE", 5, "NOTHING"),          # stairs -> D14
        "D14": T("SPIRAL_STAIR_ROOM", "GEL_2", 5, "NOTHING"),         # stairs <- F10
        "D13": C(2, "E15"),                                           # ropes, a key
        "C13": C(2, "F16"),                                           # gels, the map
        "B13": C(2, "B15"),                                           # red goriyas, bombs
        "A13": C(2, "D15"),                                           # moldorm, a key
        "A12": C(2, "A15", item="BLUE_POTION"),                       # Dodongo
        "A11": C(2, "A14"),                                           # the triforce
        "B12": C(2, "G16"),                                           # gels, the compass
        "D15": C(2, "C16"),                                           # gels, 5 rupees
        "C15": C(2, "F15", trigger="ALL_DEAD"),                       # red goriyas
        "B15": C(2, "C15", item="KEY", trigger="ALL_DEAD_ITEM"),     # ropes, a key
        "A15": C(2, "E16", item="KEY"),                               # blue goriyas, a key
        "A16": C(5, "F7"),                                            # extra boss: triple Dodongo, bombs
        "B16": C(2, "D16"),                                           # mixed, bombs
    },
    "D": {
        "H14": T("ENTRANCE_ROOM", "NOTHING", 3, "NOTHING"),
        "G14": C(5, "G6"),                                            # gibdos, bombs
        "G13": C(5, "C7"),                                            # gibdos, a key
        "G12": C(5, "B7"),                                            # keese, a key
        "H12": C(5, "F7"),                                            # extra boss: triple Dodongo
        "F12": C(5, "D8"),                                            # red darknuts, the compass
        "F13": C(5, "E8"),                                            # gibdos, a key
        "E12": C(5, "C6"),                                            # pols voice
        "E13": C(5, "E7"),                                            # the map
        "E14": C(5, "H8"),                                            # pols voice, a key
        "E15": C(5, "F6"),                                            # zols, a key
        "F15": T("NARROW_STAIR_ROOM", "BLUE_DARKNUT", 5, "NOTHING"),  # stairs -> C14
        "C14": T("SPIRAL_STAIR_ROOM", "ZOL", 5, "NOTHING"),           # stairs <- F15
        "B14": C(5, "C5", item="BLUE_POTION"),                        # Digdogger
        "A14": C(5, "B5"),                                            # the triforce
    },
    "E": {
        "H4": T("ENTRANCE_ROOM", "NOTHING", 3, "NOTHING"),
        "H3": C(4, "H1"),                                             # keese, a key
        "H5": C(4, "G2"),                                             # vires
        "G2": C(4, "F2"),                                             # keese, a key
        "G3": C(4, "C1"),                                             # vires
        "G4": C(4, "E1"),                                             # zols, a key (dark)
        "G5": C(4, "F1"),                                             # vires (dark)
        "G6": C(4, "D2", item="BOMBS", trigger="ALL_DEAD_ITEM"),      # vires
        "F1": C(4, "A2"),                                             # keese, a key (dark)
        "F2": C(4, "D1"),                                             # mixed (dark)
        "F3": C(4, "G3"),                                             # vires, the compass (dark)
        "F4": C(4, "B1", item="BOMBS", trigger="ALL_DEAD_ITEM"),      # extra boss: Manhandla
        "F5": C(4, "C2"),                                             # gels, the map (dark)
        "F6": C(4, "A3"),                                             # spike traps (dark)
        "F7": C(4, "B3", trigger="NONE", push=False),                 # vires
        "E1": C(4, "H1", item="NOTHING", trigger="NONE"),             # keese
        "E2": C(4, "F1", item="KEY", trigger="ALL_DEAD_ITEM"),        # vires, a key (dark)
        "E3": T("BLACK_ROOM", "ELDER", 3, "NOTHING"),                 # the old man's choice
        "E4": C(4, "E1", item="BOMBS"),                               # zols (dark)
        "E5": T("GOHMA_ROOM", "RED_GOHMA", 0, "KEY", trigger="ALL_DEAD_ITEM"),   # extra boss: Gohma, a key
        "E6": C(4, "C1"),                                             # vires
        "E7": C(4, "G2"),                                             # vires
        "D2": C(4, "F2", item="NOTHING", trigger="NONE"),             # keese
        "D3": C(4, "B2"),                                             # the money-giving old man
        "D4": C(4, "D3", item="KEY", trigger="ALL_DEAD_ITEM", push=False),   # mixed, a key
        "D5": C(4, "E1", item="NOTHING"),                             # zols (dark)
        "D6": C(4, "G3", item="NOTHING"),                             # vires (dark)
        "C3": C(4, "A2"),                                             # keese, a key (dark)
        "C4": C(4, "C2", item="NOTHING"),                             # gels (dark)
        "C5": C(4, "D1", item="BOMBS", trigger="ALL_DEAD_ITEM"),      # mixed (dark)
        "B4": C(4, "B3", trigger="NONE", push=False),                 # vires
        "A4": T("PLAIN_ROOM", "NOTHING", 3, "NOTHING", dark=True),    # hidden
        "A5": C(4, "B4", item="BLUE_POTION"),                         # Gleeok
        "A6": C(4, "A3"),                                             # spike traps (dark)
        "A7": T("PLAIN_ROOM", "NOTHING", 3, "NOTHING", dark=True),    # hidden
        "B7": C(4, "A4"),                                             # the triforce
    },
    "F": {
        "H9": T("ENTRANCE_ROOM", "NOTHING", 3, "NOTHING"),
        "H8": C(6, "H9", item="KEY", trigger="ALL_DEAD_ITEM"),        # blue wizzrobes, a key
        "G8": C(6, "G9"),                                             # zols, the compass
        "G9": C(6, "F9"),                                             # keese, a key
        "F8": C(6, "E9"),                                             # spike traps
        "F9": C(6, "C9"),                                             # mixed, 5 rupees
        "H11": C(6, "H11"),                                           # wizzrobes, a key (dark)
        "G11": T("BLACK_ROOM", "ELDER", 3, "NOTHING"),                # the old man's choice
        "F11": C(6, "B11"),                                           # wizzrobes, a key (dark)
        "E8": C(6, "D13"),                                            # mixed, bombs (dark)
        "E9": C(6, "B12"),                                            # mixed
        "E10": C(6, "D10"),                                           # vires (dark)
        "E11": C(6, "C14"),                                           # mixed, a key (dark)
        "D8": C(6, "C13"),                                            # mixed
        "D9": C(6, "B9", item="BOMBS", trigger="ALL_DEAD_ITEM"),      # extra boss: Gleeok (3 heads)
        "D10": C(6, "B10"),                                           # mixed, the map
        "D11": C(6, "A11"),                                           # mixed
        "D12": C(6, "C10"),                                           # mixed, a key (dark)
        "C6": C(6, "D9", trigger="NONE", push=False),                 # mixed
        "C7": C(6, "D11", trigger="NONE", push=False),                # mixed
        "C8": T("GOHMA_ROOM", "MANHANDLA", 0, "KEY", trigger="ALL_DEAD_ITEM"),   # extra boss: Manhandla, a key
        "C9": C(6, "A10", trigger="NONE", push=False),                # mixed
        "C10": C(6, "C9", item="BOMBS"),                              # mixed
        "C11": C(6, "F9", item="NOTHING", trigger="NONE"),            # keese
        "C12": C(6, "B12", item="FIVE_RUPEES", trigger="ALL_DEAD_ITEM"),   # mixed
        "B5": C(6, "D13", item="KEY"),                                # mixed, a key (dark)
        "B6": C(6, "C13", item="BOMBS", trigger="ALL_DEAD_ITEM"),     # mixed
        "B9": C(6, "G9", item="NOTHING", trigger="NONE"),             # zols
        "B10": C(6, "B13", item="BLUE_POTION"),                       # Gohma
        "B11": C(6, "B11", item="NOTHING"),                           # wizzrobes (dark)
        "A10": C(6, "A13"),                                           # the triforce
    },
}
# Door changes (both sides are listed where a door is shared): letter -> {room: {side: kind}}
DOORS = {
    "A": {"G16": {"N": "LOCK"}, "F16": {"S": "LOCK", "N": "LOCK"}, "E16": {"S": "LOCK", "N": "LOCK"},
          "D16": {"S": "LOCK", "N": "SHUT"}},
    "B": {"H7": {"N": "LOCK"}, "G7": {"S": "LOCK"}, "H1": {"N": "LOCK"}, "G1": {"S": "LOCK"},
          "B1": {"N": "LOCK"}, "A1": {"S": "LOCK", "E": "SHUT"}},
    "C": {"G10": {"N": "LOCK"}, "F10": {"S": "LOCK"}, "D14": {"W": "LOCK"}, "D13": {"E": "LOCK"},
          "B13": {"N": "LOCK"}, "A13": {"S": "LOCK", "W": "LOCK"}, "A12": {"E": "LOCK", "W": "SHUT", "S": "WALL"},
          "B12": {"N": "WALL"}},
    "D": {"G13": {"N": "LOCK"}, "F13": {"S": "LOCK"}, "E13": {"E": "LOCK"}, "E14": {"W": "LOCK"},
          "E15": {"S": "LOCK"}, "F15": {"N": "LOCK"}, "C14": {"N": "LOCK"}, "B14": {"S": "LOCK", "N": "SHUT"}},
    "E": {"A4": {"E": "WALK", "S": "WALK"}, "B4": {"N": "WALK"}, "A5": {"W": "WALK", "E": "SHUT"},
          "A6": {"W": "WALK", "E": "WALK"}, "A7": {"W": "WALK", "S": "WALK"}, "B7": {"N": "WALK"},
          "H3": {"N": "LOCK"}, "G3": {"S": "LOCK"},
          "G4": {"N": "LOCK"}, "F4": {"S": "LOCK"},
          "F2": {"N": "LOCK"}, "E2": {"S": "LOCK", "E": "WALL"},
          "E5": {"N": "LOCK"}, "D5": {"S": "LOCK"},
          "D3": {"N": "LOCK", "E": "WALL", "W": "WALL", "S": "WALL"}, "C3": {"S": "LOCK"},
          "D4": {"W": "WALL", "N": "LOCK"}, "C4": {"S": "LOCK"},
          "E3": {"N": "WALL", "E": "WALL", "W": "WALL"}, "D2": {"E": "WALL"}, "E4": {"W": "WALL"},
          "G5": {"N": "LOCK"}, "F5": {"S": "LOCK"}},
    "F": {"H8": {"N": "LOCK"}, "G8": {"S": "LOCK"},
          "G9": {"N": "LOCK"}, "D9": {"N": "LOCK"}, "C9": {"S": "LOCK"},
          "F9": {"N": "LOCK", "S": "LOCK"}, "E9": {"S": "LOCK"},
          "E11": {"N": "LOCK"}, "D11": {"S": "LOCK"},
          "D12": {"N": "LOCK"}, "C12": {"S": "LOCK"},
          "C8": {"N": "WALL"},
          "B10": {"N": "SHUT", "S": "LOCK"}, "C10": {"N": "LOCK"}},
}
# Transports: (letter, stairs room, other stairs room, free cell for the staircase)
TRANSPORTS = [("B", "G7", "B8", "A3"), ("B", "A8", "H2", "A9"), ("B", "G1", "B1", "B2"),
              ("C", "F10", "D14", "B3"), ("D", "F15", "C14", "C1")]


def kind(k):
    import build_q3 as q
    return {"OPEN": q.OPEN, "WALL": q.WALL, "WALK": q.WALK, "LOCK": q.LOCK, "SHUT": q.SHUT, "BOMB": q.BOMB}[k]


def plan():
    """letter -> {cell: (spec, walls dict side -> kind name)}; checks the map's shape against the room lists."""
    out = {}
    for L, rooms in ROOMS.items():
        cells = cells_of(L)
        assert {cell(r) for r in rooms} == cells, (L, sorted(name(c) for c in cells ^ {cell(r) for r in rooms}))
        # pieces (connected parts of the colour, the hidden rooms join theirs)
        piece, k = {}, 0
        for c in sorted(cells):
            if c in piece:
                continue
            stack = [c]; piece[c] = k
            while stack:
                x = stack.pop()
                for d in (-16, 16, -1, 1):
                    y = x + d
                    if 0 <= y < 128 and not (d == 1 and x % 16 == 15) and not (d == -1 and x % 16 == 0) \
                            and y in cells and y not in piece:
                        piece[y] = k; stack.append(y)
            k += 1
        res = {}
        for c in cells:
            walls = {}
            for side, d in (("N", -16), ("E", 1), ("S", 16), ("W", -1)):
                y = c + d
                edge = (side == "E" and c % 16 == 15) or (side == "W" and c % 16 == 0) or not 0 <= y < 128
                walls[side] = "OPEN" if (not edge and y in cells and piece[y] == piece[c]) else "WALL"
            if c == cell(ENTRANCES[L]):
                walls["S"] = "OPEN"
            walls.update(DOORS.get(L, {}).get(name(c), {}))
            res[c] = (rooms[name(c)], walls)
        out[L] = res
    return out


def check(p):
    """Each dungeon: the rooms reachable from the entrance with the keys found (any order of using them), the
    triforce reachable only through the boss room, locked door pairs vs keys."""
    tr = {}
    for L, a, b, _ in TRANSPORTS:
        tr.setdefault(L, []).append((cell(a), cell(b)))
    report = {}
    for L, rooms in p.items():
        # consistency: a door's two sides agree (both lock, or open/walk/shut/bomb vs wall)
        for c, (spec, w) in rooms.items():
            for side, d, opp in (("N", -16, "S"), ("E", 1, "W"), ("S", 16, "N"), ("W", -1, "E")):
                y = c + d
                if y in rooms and not ((side == "E" and c % 16 == 15) or (side == "W" and c % 16 == 0)):
                    s1, s2 = w[side], rooms[y][1][opp]
                    if (s1 == "LOCK") != (s2 == "LOCK"):
                        raise AssertionError(f"{L} {name(c)} {side}: {s1} vs {s2}")
        keys = {c for c, (spec, w) in rooms.items() if item_of(spec) == "KEY"}
        locks = {frozenset((c, c + {"N": -16, "E": 1, "S": 16, "W": -1}[s]))
                 for c, (spec, w) in rooms.items() for s, k in w.items() if k == "LOCK"}
        ent = cell(ENTRANCES[L])

        def reach(opened):
            seen, stack = {ent}, [ent]
            while stack:
                x = stack.pop()
                for s, d in (("N", -16), ("E", 1), ("S", 16), ("W", -1)):
                    y = x + d
                    k = rooms[x][1][s]
                    if y not in rooms or k == "WALL" or (side_edge(x, s)):
                        continue
                    if k == "LOCK" and frozenset((x, y)) not in opened:
                        continue
                    if y not in seen:
                        seen.add(y); stack.append(y)
                for a, b in tr.get(L, []):
                    for u, v in ((a, b), (b, a)):
                        if x == u and v not in seen:
                            seen.add(v); stack.append(v)
            return seen
        # worst case over the order of opening: every reachable state must still be able to finish
        from functools import lru_cache

        @lru_cache(None)
        def ok(opened):
            seen = reach(opened)
            if cell(BOSS_ROOMS[L]) in seen and all(c in seen for c in rooms):
                return True
            have = len([k for k in keys if k in seen]) - len(opened)
            frontier = [l for l in locks if l not in opened and (set(l) & seen)]
            if have <= 0 or not frontier:
                return False
            return all(ok(opened | {l}) for l in frontier)
        report[L] = (len(keys), len(locks), ok(frozenset()))
    return report


def side_edge(c, s):
    return (s == "E" and c % 16 == 15) or (s == "W" and c % 16 == 0)


def item_of(spec):
    if spec[0] == "copy":
        return spec[3].get("item", COPY_ITEMS.get((spec[1], spec[2])))
    return spec[4]


COPY_ITEMS = {}


def load_copies(world):
    """The first quest's rooms (Levels 1-6) by (level, name)."""
    src = {}
    for lv in world.levels[:6]:
        for rm in lv.rooms:
            if hasattr(rm, "layout_info"):
                src[(lv.level_num, name(rm.room_num))] = (rm, lv)
                COPY_ITEMS[(lv.level_num, name(rm.room_num))] = rm.item_info.item.name
    return src


def apply(rom: bytearray, notes: list) -> None:
    import build_q3 as q
    from zora.model.enums import Enemy, Item, RoomType, Direction
    from zora.model.rooms import Room, StaircaseRoom, EnemyInfo, LayoutInfo, ItemInfo, SecretInfo, WallSet
    from zora.model.levels import Level
    from zora.rom.parse.bin_files import load_bin_files_from_rom
    from zora.rom.parse.game_world import parse_game_world
    from zora.rom.serialize.levels import encode_level_block, _serialize_level_info
    from zora.rom.layout import LEVEL_1_6_DATA_ADDRESS_Q2
    world = parse_game_world(load_bin_files_from_rom(bytes(rom)), rom_bytes=bytes(rom))
    src = load_copies(world)
    p = plan()
    rep = check(p)
    for L, (k, l, good) in rep.items():
        assert good, (L, "can't be finished with its keys", k, l)
        assert abs(k - l) <= 1, (L, "keys", k, "locked doors", l)
    R, E, A, P = q.R, q.E, q.A, q.P
    block = world.blocks_2q[0]
    for n in range(128):
        p0, p1 = block.palette_bits(n)
        block[n] = Room.blank(n, p0, p1)
    pools = {}
    for L, rooms in p.items():
        lv = LETTER_LEVEL[L]
        qty = world.levels[lv - 1].qty_table
        for c, (spec, walls) in rooms.items():
            w = WallSet(*(kind(walls[s]) for s in "NESW"))
            if spec[0] == "copy":
                _, slv, srm, kw = spec
                rm, slevel = src[(slv, srm)]
                layout = R[kw["layout"]] if "layout" in kw else rm.layout_info.room_type
                push = kw.get("push", rm.layout_info.movable_block)
                enemy = E[kw["enemy"]] if "enemy" in kw else rm.enemy_info.enemy
                count_i = rm.enemy_info.count_index
                item = Item[kw["item"]] if "item" in kw else rm.item_info.item
                pos = P["POSITION_" + kw["pos"]] if "pos" in kw else rm.secret_info.item_position
                trig = A[kw["trigger"]] if "trigger" in kw else rm.secret_info.trigger
                if trig in (A.BLOCK_STAIRS, A.BLOCK_DOOR):
                    trig = A.NONE
                if trig == A.RINGLEADER:
                    trig = A.ALL_DEAD_ITEM
                dark = kw.get("dark", rm.item_info.is_dark)
                pal1 = rm.palette_1
            else:
                _, layout, enemy, count, item, pos, trig, dark, push = spec
                layout, enemy, item = R[layout], E[enemy], Item[item]
                pos, trig = P["POSITION_" + pos], A[trig]
                count_i = 0 if count == 0 else qty.index(count)
                pal1 = 3 if layout == R.ENTRANCE_ROOM else 0 if layout == R.BLACK_ROOM else 2
            room = Room(room_num=c, walls=w, enemy_info=EnemyInfo(enemy, count_i), layout_info=LayoutInfo(layout, push),
                        item_info=ItemInfo(item, rm.item_info.boss_sound if spec[0] == "copy" else q.BossSound.NONE, dark),
                        secret_info=SecretInfo(trig, pos), palette_0=2, palette_1=pal1)
            block[c] = room
        for L2, a, b, where in TRANSPORTS:
            if L2 != L:
                continue
            n = cell(where)
            assert GRID[n // 16][n % 16] == "w" and n not in {x for rr in p.values() for x in rr}, where
            block[n] = StaircaseRoom(room_num=n, room_type=RoomType.TRANSPORT_STAIRCASE, exit_x=6, exit_y=9,
                                     left_exit=cell(a), right_exit=cell(b), t5_raw=0)
            pools.setdefault(lv, []).append(n)
    rom[LEVEL_1_6_DATA_ADDRESS_Q2:LEVEL_1_6_DATA_ADDRESS_Q2 + 0x300] = encode_level_block(block)          # vanilla nothing code ($03)

    # LevelInfo replacement arrays for 2Q Levels 1-6 (7-9 keep theirs)
    bank6 = 16 + 6 * 0x4000
    sizes_at, addrs_at = SIZES_AT, SIZES_AT - 18
    old_ptrs = [rom[addrs_at + 2 * i] | rom[addrs_at + 2 * i + 1] << 8 for i in range(9)]
    info_at = 0x19310
    arrays = {}
    for L, rooms in p.items():
        lv = LETTER_LEVEL[L]
        old = world.levels[lv - 1]
        old_repl = rom[bank6 + old_ptrs[lv - 1] - 0x8000: bank6 + old_ptrs[lv - 1] - 0x8000 + rom[sizes_at + lv - 1] + 1]
        cells = sorted(rooms)
        shown = set(cells) - {cell(x) for x in HIDDEN.get(L, ())}
        map_data, commands, map_start, map_cursor = q.synthesize_minimap(shown)
        new = Level(
            level_num=lv, entrance_room=cell(ENTRANCES[L]), entrance_direction=Direction.SOUTH,
            palette_raw=old.palette_raw, fade_palette_raw=old.fade_palette_raw, staircase_room_pool=pools.get(lv, []),
            room_nums=cells, staircase_nums=sorted(pools.get(lv, [])), block=block,
            boss_room=cell(BOSS_ROOMS[L]), enemy_sprite_set=old.enemy_sprite_set,
            boss_sprite_set=old.boss_sprite_set, start_y=old.start_y,
            item_position_table=list(old.item_position_table), map_start=map_start, map_cursor_offset=map_cursor,
            map_data=map_data, map_ppu_commands=q.command_block(commands, old.map_ppu_commands),
            qty_table=list(old.qty_table),
            stairway_data_raw=bytes(pools.get(lv, [])) + b"\xFF" * (10 - len(pools.get(lv, []))),
            rom_level_num=old.rom_level_num,
            screen_status_ram_offset=(old_repl[0x31 - 0x29], old_repl[0x32 - 0x29]))
        new.triforce_room_ptr = None
        blk = bytearray(rom[info_at + lv * 0xFC:info_at + (lv + 1) * 0xFC])
        _serialize_level_info(new, blk)
        end = 0x4F + len(q.drawn_commands(bytes(blk[0x4F:0x7C])))
        arr = bytearray(blk[0x29:end])
        arr[0x33 - 0x29] = old_repl[0x33 - 0x29]          # the level number tile (lol_af makes it the letter)
        arrays[lv] = bytes(arr)
    total = sum(len(a) for a in arrays.values())
    at = bank6 + FREE6 - 0x8000
    assert all(x == 0xFF for x in rom[at:at + total]), "bank 6's free space"
    pp = at
    for lv in sorted(arrays):
        a = arrays[lv]
        rom[pp:pp + len(a)] = a
        cpu = 0x8000 + pp - bank6
        rom[addrs_at + 2 * (lv - 1):addrs_at + 2 * lv] = bytes([cpu & 0xFF, cpu >> 8])
        rom[sizes_at + lv - 1] = len(a) - 1
        pp += len(a)
    notes.append("A-F rebuilt: " + ", ".join(f"{L} {len(p[L])} rooms ({rep[L][0]} keys / {rep[L][1]} locks)" for L in p)
                 + f"; level info at ${FREE6:04X} ({total} bytes)")


SIZES_AT = 0x183C6          # file offset of the 2Q LevelInfo replacement sizes (vanilla PRG1); addresses 18 before
FREE6 = 0xAD60              # bank 6's free run (PRG1: $AD54-$BEFF)

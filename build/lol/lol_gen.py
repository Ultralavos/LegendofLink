"""Legend of Link v2: pre-built dungeon layouts ("variants") for the user's dungeon designs (generator_spec.txt).

For each design (a footprint on a grid) and each level type it can be (levels 1-3, 4, 5-7, 8; or a shrine), K
variants are generated here, following the user's rules, each checked for reachability. In the game, the first
load of a level picks one; enemies, the boss, the palette and the cellar items are rolled there (lol_genload).

A variant: {
  "cells": {cell: dict(walls=[N,E,S,W], layout=full code, item=code|None, pos=0-3, trigger=RoomAction, role=str,
                        eclass=0 none / 1 enemies / 2 enemies but no traps / 3 boss / 4 old man)},
  "stairs": [(cellar cell, kind, a, b, exit_x, exit_y)], "start", "boss", "tri", "choice", "item_stairs": [cells],
}
"""
import random
from collections import deque

ROWS = "ABCDEFGH"
N_, E_, S_, W_ = 0, 1, 2, 3
STEP = {N_: -16, E_: 1, S_: 16, W_: -1}
OPP = {N_: S_, S_: N_, E_: W_, W_: E_}
OPEN, WALL, WALK1, WALK2, BOMB, KEY, KEY2, SHUT = range(8)
T_NONE, T_ALL_DEAD, T_RINGLEADER, T_LAST_BOSS, T_BLOCK_DOOR, T_BLOCK_STAIRS, T_MOL, T_ALL_DEAD_ITEM = range(8)
I_BOMBS, I_RUPEES, I_COMPASS, I_MAP, I_KEY, I_HEART, I_TRIFORCE, I_BLUE_POTION = 0x00, 0x0F, 0x16, 0x17, 0x19, 0x1A, 0x1B, 0x1F

# the door weights (open, wall, walk1, walk2, bomb, key1, key2, shutter) of the first quest's levels (ZORA T1)
T1 = {1: [18, 0, 0, 0, 4, 12, 0, 3], 2: [25, 0, 0, 0, 10, 6, 0, 6], 3: [23, 0, 0, 0, 4, 8, 0, 8],
      4: [23, 2, 0, 0, 8, 10, 0, 6], 5: [21, 12, 0, 0, 10, 12, 0, 6], 6: [25, 8, 0, 0, 6, 10, 0, 12],
      7: [30, 26, 0, 0, 20, 10, 0, 11], 8: [21, 12, 0, 0, 12, 8, 0, 12], 9: [41, 68, 0, 0, 38, 32, 0, 14]}
# room items (bombs, nothing, five rupees, key) (ZORA T3)
T3 = {1: [0, 1, 0, 6], 2: [2, 4, 1, 4], 3: [3, 2, 1, 5], 4: [0, 8, 0, 4], 5: [2, 3, 1, 7], 6: [1, 8, 1, 5],
      7: [7, 11, 3, 4], 8: [3, 8, 3, 6], 9: [5, 29, 7, 4]}
CLASSES = {"L13": (1, 2, 3), "L4": (4,), "L57": (5, 6, 7), "L8": (8,), "SH": (1, 2, 3), "L9": (9,)}
# v2.02 test 6: a layout set per level 1-9 and per shrine A-D; each belongs to one of the rule groups above
LEVEL_CLASSES = ("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "SA", "SB", "SC", "SD")
GROUP = {"L1": "L13", "L2": "L13", "L3": "L13", "L4": "L4", "L5": "L57", "L6": "L57", "L7": "L57", "L8": "L8",
         "L9": "L9", "SA": "SH", "SB": "SH", "SC": "SH", "SD": "SH"}
LEVEL_LAYOUTS = {"L%d" % n: (n,) for n in range(1, 10)}
LEVEL_LAYOUTS.update({"SA": (1, 2, 3), "SB": (1, 2, 3), "SC": (1, 2, 3), "SD": (1, 2, 3)})
# the walls between a level's rooms (open, solid, walk1, walk2, bomb, key1, key2, shutter), counted in the vanilla
# ROM: levels 1-9 the first quest's, shrines A-D the second quest's levels 1, 3, 4, 5; no walk-through walls
WALLS = {"L1": [7, 0, 0, 0, 2, 6, 0, 3], "L2": [10, 0, 0, 0, 5, 3, 0, 5], "L3": [9, 0, 0, 0, 2, 4, 0, 6],
         "L4": [9, 1, 0, 0, 4, 5, 0, 5], "L5": [8, 6, 0, 0, 5, 6, 0, 5], "L6": [7, 4, 0, 0, 3, 5, 0, 11],
         "L7": [11, 13, 0, 0, 10, 5, 0, 9], "L8": [7, 6, 0, 0, 6, 4, 0, 9], "L9": [16, 34, 0, 0, 19, 16, 0, 11],
         "SA": [6, 2, 0, 0, 3, 2, 0, 3], "SB": [7, 5, 0, 0, 3, 4, 0, 6], "SC": [6, 6, 0, 0, 0, 2, 0, 6],
         "SD": [12, 13, 0, 0, 4, 3, 0, 9]}
TRANSPORTS = {"L57": 1, "L8": 1, "L9": 6}
ITEM_STAIRS = {"L13": 1, "L4": 1, "L57": 1, "L8": 2, "L9": 2, "SH": 0}

# layouts never drawn for ordinary rooms: turnstile, T moat, black rooms, Zelda, Ganon, triforce, entrance, lava moat,
# and the stair / boss layouts (placed on purpose)
EXCLUDED = {0x20, 0x12, 0x26, 0x27, 0x28, 0x29, 0x21, 0x0B, 0x1A, 0x1B, 0x1C}
BOSS_LAYOUTS = (0x04, 0x05, 0x06, 0x25, 0x23, 0x24)       # aquamentus, gleeok, gohma, desert, two / four shooter
# the bosses each boss layout can hold
BOSS_OF = {0x04: [0x3D], 0x05: [0x43, 0x44, 0x45], 0x06: [0x33, 0x34], 0x25: [0x3C, 0x32, 0x31],
           0x23: [0x33, 0x34, 0x3C, 0x32, 0x31, 0x38, 0x39], 0x24: [0x33, 0x34, 0x3C, 0x32, 0x31, 0x38, 0x39]}
BOSS_GROUP_A = {0x3D, 0x31, 0x32, 0x38, 0x39}               # Aquamentus, Dodongos, Digdogger (one boss graphics set)
# (owner 2026-11-26) a boss room may take any ordinary layout as ZORA allows (zora.generate.shapes.bosses'
# boss_barred: Gleeok not in circle walls, lava, chutes, T, circle moats or the fireball rooms, the four-headed one
# not in the moats either; Gohma not in lava, chutes or T; Dodongos not in circle walls, lava, chutes or T)
ALL_BOSSES = (0x3D, 0x31, 0x32, 0x33, 0x34, 0x43, 0x44, 0x45, 0x38, 0x39, 0x3C)
_GLEEOK_BAD = {0x09, 0x0B, 0x0E, 0x0F, 0x12, 0x14, 0x23, 0x24}
_GLEEOK4_BAD = {0x13, 0x15, 0x16, 0x17, 0x18, 0x19}
_GOHMA_BAD = {0x0B, 0x0E, 0x0F, 0x12}
_DODONGO_BAD = {0x09, 0x0B, 0x0E, 0x0F, 0x12}


def _seeded():
    """(owner 2026-11-26) the website's seeded builds: ZORA's boss rooms and doors; Unseeded keeps the old way."""
    import lol_fixed
    return lol_fixed.FIXED


def _shut_boss(walls, c, deg):
    """Unseeded (the old way): a boss room's doors shutters on its own side."""
    for t in deg(c):
        if walls[c][t] == OPEN:
            walls[c][t] = SHUT


def boss_of(L):
    """The bosses a boss room of layout L can hold: a boss layout's own list, else ZORA's bars."""
    L &= 0x3F
    if L in BOSS_OF:
        return BOSS_OF[L]
    out = []
    for b in ALL_BOSSES:
        if b in (0x43, 0x44, 0x45) and (L in _GLEEOK_BAD or (b == 0x45 and L in _GLEEOK4_BAD)):
            continue
        if b in (0x33, 0x34) and L in _GOHMA_BAD:
            continue
        if b in (0x31, 0x32) and L in _DODONGO_BAD:
            continue
        out.append(b)
    return out


def _quest_l2():
    import lol_sets
    return lol_sets.quest_l2()


def groups_of(bosses):
    return {1 if b in BOSS_GROUP_A else 0 for b in bosses}


NO_TRAPS = {0x15, 0x1C, 0x08}                               # pointless moat, spiral stairs, reverse C
NO_ITEM_LAYOUTS = {0x09, 0x22, 0x20}                        # circle wall, single block, turnstile (the user's list)
CHUTE_SIDES = {0x0E: {N_, S_}, 0x0F: {E_, W_}}              # a chute room: items only in the chute (the center)
# a room's item mark (the game places the items at load): $10 | 1 the center is usable | 2 standing only
MARK = 0x10
# sides joined inside a room (without the ladder); a layout fits a room when all its doorways are in one group
# (moat rooms need the ladder to cross, which is allowed; chutes can't be crossed at all)
GROUPS = {0x0E: [{N_, S_}, {E_}, {W_}], 0x0F: [{E_, W_}, {N_}, {S_}]}
MOATS = (0x13, 0x14, 0x15, 0x18, 0x19)          # their weight: the average of the two quests
# item positions each layout can seat (index into the table below; ZORA's fit), default all four
POS_TABLE = [0x89, 0xD6, 0x26, 0x2C]
USABLE = {0x00: (0, 1, 2, 3), 0x02: (0, 1, 2, 3), 0x03: (0, 1, 2, 3), 0x04: (0, 2, 3), 0x05: (0, 3), 0x06: (0, 3),
          0x08: (0, 3), 0x0A: (0, 2, 3), 0x0C: (2,), 0x0D: (1,), 0x0E: (0, 3), 0x0F: (0, 3), 0x11: (0, 2, 3),
          0x13: (0, 2, 3), 0x14: (0, 2, 3), 0x15: (0, 2, 3), 0x16: (0, 2, 3), 0x17: (0, 2, 3), 0x18: (0, 1, 2, 3),
          0x19: (0, 3), 0x1B: (0, 2, 3), 0x1C: (0, 1), 0x1D: (0, 2, 3), 0x1E: (1, 2), 0x1F: (0,), 0x23: (0, 2, 3),
          0x24: (0, 2, 3), 0x25: (0, 2, 3), 0x5A: (1,)}
OPEN_STAIRS = (0x1C, 0x1B)                                  # spiral, narrow (corridor: its east side solid)
# push-block stairs (the user's list, 2Q's rooms): single block, double block, reverse C, five pair, three rows,
# zigzag, maze, Gohma room, spike trap room, grid room
PUSH_STAIRS = (0x62, 0x4A, 0x48, 0x5F, 0x47, 0x51, 0x4C, 0x46, 0x41, 0x4D)
STAIR_EXIT = {0x1C: (6, 9), 0x1B: (6, 9), **{L: (6, 9) for L in PUSH_STAIRS}, 0x41: (6, 10)}   # (vanilla's)


def name(c):
    return f"{ROWS[c // 16]}{c % 16 + 1}"


def cell(n):
    return ROWS.index(n[0]) * 16 + int(n[1:]) - 1


def nb(c, s):
    if (s == E_ and c % 16 == 15) or (s == W_ and c % 16 == 0):
        return None
    y = c + STEP[s]
    return y if 0 <= y < 128 else None


def _probe():
    import json, os
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiles_probe.json")
    out = {}
    for k, v in json.load(open(f)).items():
        if v is None:
            continue
        out[int(k, 16)] = tuple(i for i, ts in enumerate(v) if all(t in (116, 117, 118, 119, 104, 36) for t in ts))
    return out
PROBE = _probe()


def usable_in(layout, postab):
    """(1.0) The item positions a layout allows: ZORA's (T5's base row against the level's own four positions, SH-ROOM-11)
    for a level with its own table (1Q, 2Q, Random shapes); LoL's otherwise. A push block room may hold an item
    where its plain layout would (owner 2026-11-28)."""
    if postab is None:
        return usable(layout & 0x3F if layout & 0x40 else layout)
    from zora.generate.shapes.t5_positions import T5_BASE
    row = T5_BASE.get(layout) or T5_BASE.get(layout & 0x3F, ())
    return tuple(i for i, p in enumerate(postab) if p in row)


# (1.0, owner 2026-11-28) item tiles: never a door's tile, a block, statue, water or stairs tile, a tile Link can't
# walk to from the room's ways in, nor where a staircase appears or drops Link off
DOOR_TILES = {0x76, 0x86, 0x7C, 0x8C, 0x29, 0xD9}
WALKABLE = (0x74, 0x68, 0x24)                   # floor, sand, a dark room's floor
LOL_TILE_POOL = [(c << 4) | r for c in range(2, 14) for r in range(6, 13)
                 if (c << 4) | r not in DOOR_TILES and (c << 4) | r != 0x89]
_FLOORS = {}


def floors():
    if not _FLOORS:
        import lolpaths
        from zora.rom.parse.room_layouts import underworld_floors
        _FLOORS.update(underworld_floors(bytes(lolpaths.source_rom())))
    return _FLOORS


def tile_ok(layout, tile, sides=None):
    """Whether an item may lie on tile ($XY) of a room with this layout (full code), entered by sides (N/E/S/W; None:
    any) - or, a stairs room, from its stairs."""
    if tile in DOOR_TILES:
        return False
    fl = floors()[layout & 0x3F]
    walk = lambda t: fl[(t >> 4) - 2][(t & 15) - 6] in WALKABLE
    if not walk(tile):
        return False
    exit_ = STAIR_EXIT.get(layout) or STAIR_EXIT.get(layout & 0x3F)
    if exit_ and tile == (exit_[0] << 4) | exit_[1]:
        return False
    starts = []
    fronts = {N_: (0x76, 0x86), S_: (0x7C, 0x8C), W_: (0x29,), E_: (0xD9,)}
    for t in range(4):
        if sides is None or t in sides:
            starts += [x for x in fronts[t] if walk(x)]
    if exit_:
        starts.append((exit_[0] << 4) | exit_[1])
    seen, todo = set(starts), list(starts)
    while todo:
        x = todo.pop()
        c, r = x >> 4, x & 15
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            y = ((c + dc) << 4) | (r + dr)
            if 2 <= c + dc <= 13 and 6 <= r + dr <= 12 and y not in seen and walk(y):
                seen.add(y); todo.append(y)
    return tile in seen


def spot_slots(layout, postab, sides=None):
    """(1.0) The slots (0-3) of the level's four item tiles an item may take in this room: a ZORA table's (1Q, 2Q, Random
    shapes) also only where T5 allows; the triforce room's layout only the center."""
    if (layout & 0x3F) == 0x29:
        return (postab.index(0x89),)
    t5 = None
    if not getattr(postab, "lol", False):
        from zora.generate.shapes.t5_positions import T5_BASE
        t5 = T5_BASE.get(layout) or T5_BASE.get(layout & 0x3F, ())
    return tuple(i for i, p in enumerate(postab) if (t5 is None or p in t5) and tile_ok(layout, p, sides))


class LolTab(list):
    """(1.0, owner 2026-11-28) a LoL dungeon's own four item tiles: the center and three drawn for it."""
    lol = True


def usable(layout):
    """The item positions whose tiles are floor in this layout (measured in the game), never a block or water."""
    if layout in PROBE:
        return PROBE[layout]
    return PROBE.get(layout & 0x3F, ())


def weights(cls, table):
    lv = CLASSES[cls]
    return [sum(table[x][i] for x in lv) for i in range(len(table[lv[0]]))]


def t4_weights(cls):
    from zora.generate.shapes.t4_tables import T4_FIRST_QUEST, T4_SECOND_QUEST_ADDITION
    CLASSES = {**globals()["CLASSES"], **LEVEL_LAYOUTS}
    w = [sum(T4_FIRST_QUEST[x][i] for x in CLASSES[cls]) for i in range(128)]
    for i in range(128):
        if (i & 0x3F) in MOATS:      # ladder rooms: the first and second quests' average
            w2 = sum(T4_FIRST_QUEST[x][i] + T4_SECOND_QUEST_ADDITION[x][i] for x in CLASSES[cls])
            w[i] = (w[i] + w2 + 1) // 2
    for code in range(128):
        if (code & 0x3F) in EXCLUDED or (code & 0x3F) in BOSS_LAYOUTS or (code & 0x3F) >= 0x2A:
            w[code] = 0
        if code & 0x40 and code not in (0x4A, 0x48, 0x62, 0x41):
            w[code] = 0          # push-block variants only as door pushers (no stairs outside stair rooms)
    return w


class Fail(Exception):
    pass


def pieces(cells):
    piece, k = {}, 0
    for c in sorted(cells):
        if c in piece:
            continue
        piece[c] = k; q = [c]
        while q:
            x = q.pop()
            for s in range(4):
                y = nb(x, s)
                if y in cells and y not in piece:
                    piece[y] = k; q.append(y)
        k += 1
    return piece


# boss rooms made (the most the level type can need; the game keeps 1-2 / 2-3 / 3-5 of them at load, the rest get
# ordinary enemies): levels 1-3, 4, 5-7 (5 when the design can be level 7), 8; level 9: Patra rooms (plus Ganon)
N_BOSS = {"L13": 2, "L4": 3, "L57": 5, "L8": 5, "SH": 2, "L9": 5,
          "L1": 2, "L2": 2, "L3": 2, "L5": 3, "L6": 3, "L7": 5, "SA": 2, "SB": 2, "SC": 2, "SD": 2}


def generate(cells, cls, rng, free_item_cellars, free_transport_cellars, hidden=(), n_boss=None, rule=None,
             postab=None):
    """rule: a quest's (item stairs, transports, walk-through share, floor item) in place of LoL's counts."""
    lvcls = cls                           # the level's own class (its walls, layouts, bosses)
    if cls in GROUP:
        cls = GROUP[cls]                  # the rules' group
    """One variant of the dungeon on `cells` as level type `cls`."""
    cells = set(cells)
    shrine = cls == "SH"
    if shrine and _seeded():              # (1.0: a shrine's doors are open, locked or shutters, two bomb walls at most:
        hidden = ()                       #  no hidden rooms, all bombed into)
    if _seeded() and postab is None:      # (1.0) a LoL dungeon: the center and three tiles of its own
        postab = LolTab([0x89] + rng.sample(LOL_TILE_POOL, 3))
    piece = pieces(cells)
    walls = {c: [WALL] * 4 for c in cells}
    rooms = {c: dict(layout=None, item=None, pos=0, trigger=T_NONE, role="room", eclass=1) for c in cells}
    roles = {}

    # entrance: the square below isn't this dungeon's
    ents = [c for c in cells if nb(c, S_) not in cells and c not in hidden]
    if cls == "L9":       # the triforce check room north of the entrance, and a room beyond it
        ents = [c for c in ents if nb(c, N_) in cells and nb(nb(c, N_), N_) in cells and nb(c, N_) not in hidden]
    if not ents:
        raise Fail("no entrance")
    ent = rng.choice(sorted(ents))
    roles[ent] = "entrance"

    # transports: join the pieces (each to the next), plus one for levels 5-8
    trans = []
    ks = sorted(set(piece.values()), key=lambda k: (k != piece[ent], -sum(1 for c in cells if piece[c] == k)))
    joined = {ks[0]}
    for k in ks[1:]:          # each other piece joined to one already reachable (small pieces stay leaves)
        a_opts = sorted(c for c in cells if piece[c] in joined and c not in roles and c not in hidden)
        b_opts = sorted(c for c in cells if piece[c] == k and c not in roles and c not in hidden)
        if not a_opts or not b_opts:
            raise Fail("pieces")
        a, b = rng.choice(a_opts), rng.choice(b_opts)
        trans.append((a, b)); roles[a] = roles[b] = "transport"; joined.add(k)
    reserved = {nb(ent, N_)} if cls == "L9" else set()
    n_extra = TRANSPORTS.get(cls, 0) if rule is None else max(0, rule[1] - len(trans))
    for _ in range(n_extra):
        cand = sorted(c for c in cells if c not in roles and c not in reserved and c not in hidden)
        a = rng.choice(cand)
        far = [c for c in cand if c != a and abs(c % 16 - a % 16) + abs(c // 16 - a // 16) >= 3]
        b = rng.choice(far or [c for c in cand if c != a])
        trans.append((a, b)); roles[a] = roles[b] = "transport"

    # doors between neighbours of the same piece, drawn by the level type's weights
    wts = WALLS[lvcls] if lvcls in WALLS else weights(cls, T1)    # the vanilla level's mix (no walk-through walls)
    max_walls = {"L13": 0, "L4": 1}.get(cls, 99)
    nwalls = nbombs = 0
    # (1.0, owner 2026-11-28) a shrine's doors: open, locked or shutters only, and at most two bomb walls (its hidden
    # rooms' count); no walk-through walls (its prize room keeps its sealed sides)
    sh10 = shrine and _seeded()
    nbomb = [sum(1 for c in hidden for t in range(4) if nb(c, t) in cells and piece[nb(c, t)] == piece[c])]
    SH_MAX_BOMBS = 2
    for c in sorted(cells):
        for s in (E_, S_):
            y = nb(c, s)
            if y not in cells or piece[y] != piece[c]:
                continue
            k = rng.choices(range(8), wts)[0]
            if sh10:
                k = rng.choices((OPEN, KEY, SHUT, BOMB),
                                [wts[OPEN], wts[KEY], wts[SHUT], wts[BOMB] if nbomb[0] < SH_MAX_BOMBS else 0])[0]
                nbomb[0] += k == BOMB
            elif rule is not None and rule[2] and rng.random() < rule[2]:
                k = WALK1                         # the quest's share of walk-through walls (both sides)
            elif k in (WALK1, WALK2, KEY2):
                k = {WALK1: OPEN, WALK2: OPEN, KEY2: KEY}[k]
            if k == WALL:
                if nwalls >= max_walls:
                    k = BOMB
                else:
                    nwalls += 1
            a, b = k, k
            if k == SHUT:
                a, b = (SHUT, OPEN) if rng.random() < 0.5 else (OPEN, SHUT)
            walls[c][s], walls[y][OPP[s]] = a, b
    walls[ent][S_] = OPEN                         # the way out
    for c in hidden:                              # hidden rooms: bombed into
        for s in range(4):
            y = nb(c, s)
            if y in cells and piece[y] == piece[c]:
                walls[c][s] = walls[y][OPP[s]] = BOMB

    def passable(c, s):
        return walls[c][s] != WALL and nb(c, s) in cells

    def graph(skip=None):
        g = {c: set() for c in cells}
        for c in cells:
            for s in range(4):
                y = nb(c, s)
                if y in cells and passable(c, s) and passable(y, OPP[s]) and (c, s) != skip:
                    g[c].add(y)
        for a, b in trans:
            g[a].add(b); g[b].add(a)
        return g

    def reach(g):
        seen = {ent}; q = deque([ent])
        while q:
            x = q.popleft()
            for y in g[x]:
                if y not in seen:
                    seen.add(y); q.append(y)
        return seen

    def fix_reach():
        """Walls that cut rooms off become bomb walls."""
        for _ in range(64):
            seen = reach(graph())
            if len(seen) == len(cells):
                return
            # (owner 2026-11-27) level 9's entrance keeps its east and west walls solid: it opens north only
            opts = [(c, s) for c in sorted(seen) for s in range(4)
                    if nb(c, s) in cells and nb(c, s) not in seen and piece[nb(c, s)] == piece[c]
                    and not (cls == "L9" and c == ent and s in (E_, W_))]
            if not opts:
                raise Fail("unreachable")
            c, s = rng.choice(opts)
            # a door of the level's mix (not solid): open, bomb wall, locked or shutter
            k = rng.choices((OPEN, BOMB, KEY, SHUT), [wts[OPEN], wts[BOMB] if not sh10 or nbomb[0] < SH_MAX_BOMBS
                                                      else 0, wts[KEY], wts[SHUT]])[0]
            nbomb[0] += k == BOMB
            if k == SHUT:
                a_, b_ = (SHUT, OPEN) if rng.random() < 0.5 else (OPEN, SHUT)
            else:
                a_ = b_ = k
            walls[c][s], walls[nb(c, s)][OPP[s]] = a_, b_
        raise Fail("fix_reach")
    fix_reach()

    def dist_from_ent():
        g = graph(); d = {ent: 0}; q = deque([ent])
        while q:
            x = q.popleft()
            for y in g[x]:
                if y not in d:
                    d[y] = d[x] + 1; q.append(y)
        return d
    dist = dist_from_ent()

    def deg(c):
        return [s for s in range(4) if nb(c, s) in cells and passable(c, s)]

    def seal(c, keep_side):
        """Make c a dead end opening only on keep_side (if everything stays reachable)."""
        saved = {x: list(walls[x]) for x in cells}
        for s in range(4):
            y = nb(c, s)
            if s != keep_side and y in cells:
                walls[c][s] = walls[y][OPP[s]] = WALL
        if len(reach(graph())) != len(cells):
            for x in cells:
                walls[x] = saved[x]
            return False
        return True

    free = lambda: sorted(c for c in cells if c not in roles)
    v10 = _seeded()                       # (1.0, owner 2026-11-28: ZORA's items, Ganon / Zelda; level 9's old man)

    # the old man's choice: anywhere. A north doorway (behind him: he stops Link going north) is a gate that
    # opens when he leaves - so the rooms past it are reached only through his room, never from behind first
    def behind_ok(c):
        y = nb(c, N_)
        if not (y in cells and passable(c, N_)):
            return True
        g = graph()
        g = {k: [x for x in v if x != c] for k, v in g.items() if k != c}
        seen, todo = {ent}, [ent]
        while todo:
            k = todo.pop()
            for x in g.get(k, ()):
                if x not in seen:
                    seen.add(x); todo.append(x)
        return y not in seen

    def reach_without(z):
        g = graph()
        g = {k: [x for x in v if x != z] for k, v in g.items() if k != z}
        seen, todo = {ent}, [ent]
        while todo:
            k = todo.pop()
            for x in g.get(k, ()):
                if x not in seen:
                    seen.add(x); todo.append(x)
        return seen

    def zelda_at(z):
        """(1.0) Zelda in room z: every way in a shutter on the far side, opened by the Triforce of Power (the room's
        trigger LAST_BOSS: 'zguard' rooms; Ganon's has it already); a way from another special room walled up."""
        saved = {x: list(walls[x]) for x in cells}
        guards, ways = [], 0
        for t in range(4):
            y = nb(z, t)
            if y not in cells or piece[y] != piece[z]:
                continue
            door = walls[z][t] != WALL or walls[y][OPP[t]] != WALL
            if y in roles and roles[y] != "ganon" or y in hidden:
                walls[z][t] = walls[y][OPP[t]] = WALL
            elif door:
                walls[z][t], walls[y][OPP[t]] = OPEN, SHUT
                ways += 1
                if roles.get(y) != "ganon":
                    guards.append(y)
        if not ways:
            opts = [t for t in range(4) if nb(z, t) in cells and piece[nb(z, t)] == piece[z]
                    and nb(z, t) not in roles and nb(z, t) not in hidden]
            if opts:
                t = rng.choice(opts); y = nb(z, t)
                walls[z][t], walls[y][OPP[t]] = OPEN, SHUT
                guards.append(y); ways = 1
        if not ways or len(reach_without(z)) != len(cells) - 1 or len(reach(graph())) != len(cells):
            for x in cells:
                walls[x] = saved[x]
            return False
        roles[z] = "zelda"
        for y in guards:
            roles[y] = "zguard"
        return True

    if cls == "L9" and v10:
        # the triforce check north of the entrance (as before); Ganon and Zelda in random rooms (ZORA SH-ROOM-06),
        # Ganon's ways out shutters (the Triforce of Power opens them), Zelda's ways in likewise; an old man's choice
        chk = nb(ent, N_)
        for s in (E_, W_):
            y = nb(ent, s)
            if y in cells:
                walls[ent][s] = walls[y][OPP[s]] = WALL
        walls[ent][N_] = walls[chk][S_] = OPEN
        for s in (N_, E_, W_):
            y = nb(chk, s)
            if y in cells:
                if walls[chk][s] == WALL:
                    walls[chk][s] = walls[y][OPP[s]] = OPEN
                walls[chk][s] = SHUT
                if walls[y][OPP[s]] in (WALL, SHUT):
                    walls[y][OPP[s]] = OPEN
        roles[chk] = "check"
        fix_reach()
        cand = [c for c in free() if c not in hidden]
        if not cand:
            raise Fail("no ganon")
        gan = rng.choice(cand)
        roles[gan] = "ganon"
        zs = [c for c in free() if c not in hidden]
        rng.shuffle(zs)
        for z in zs:
            if zelda_at(z):
                zel = z
                break
        else:
            raise Fail("no zelda")
        for t in range(4):
            if walls[gan][t] == OPEN and nb(gan, t) in cells:
                walls[gan][t] = SHUT
        dist = dist_from_ent()
        pool = [c for c in free() if c not in hidden and behind_ok(c)]
        if not pool:
            raise Fail("no old man room")
        choice = rng.choice(pool)
        roles[choice] = "choice"
        tri, boss = zel, gan                    # (the compass points to Zelda)
    elif cls == "L9":
        # the triforce check: his room north of the entrance, its other ways shutters (he opens them); the
        # entrance's other sides walls
        chk = nb(ent, N_)
        for s in (E_, W_):
            y = nb(ent, s)
            if y in cells:
                walls[ent][s] = walls[y][OPP[s]] = WALL
        walls[ent][N_] = walls[chk][S_] = OPEN
        for s in (N_, E_, W_):
            y = nb(chk, s)
            if y in cells:
                if walls[chk][s] == WALL:
                    walls[chk][s] = walls[y][OPP[s]] = OPEN
                walls[chk][s] = SHUT
                if walls[y][OPP[s]] in (WALL, SHUT):
                    walls[y][OPP[s]] = OPEN
        roles[chk] = "check"
        fix_reach()
        dist = dist_from_ent()
        # Ganon far away; Zelda a dead end beside him (shutters both sides); his other doors shutters on his side
        best = None
        for c in free():
            for s in deg(c):
                z = nb(c, s)
                if s != N_ or z in roles or z in hidden or c in hidden:      # Zelda: north of him (entered from
                    continue                                                  # the south)
                sc = (dist.get(c, 0) + rng.random() * 3, c, s)
                if best is None or sc > best:
                    best = sc
        if best is None:
            raise Fail("no ganon")
        _, gan, s = best
        zel = nb(gan, s)
        if not seal(zel, OPP[s]):
            raise Fail("zelda seal")
        walls[gan][s] = walls[zel][OPP[s]] = SHUT
        for t in range(4):
            if t != s and walls[gan][t] == OPEN:
                walls[gan][t] = SHUT
        roles[gan], roles[zel] = "ganon", "zelda"
        tri, boss, choice = zel, gan, None      # (owner 2026-11-24: the compass points to Zelda)
    elif shrine:
        # the prize room: a dead end, its only way in a shutter on the approach room's side (never a bomb wall: not a
        # hidden room, owner 2026-11-28)
        best = None
        for c in free():
            if c in hidden:
                continue
            for s in deg(c):
                y = nb(c, s)
                if y in roles or y == ent:
                    continue
                sc = (dist.get(c, 0) + rng.random(), c, s)
                if best is None or sc > best:
                    best = sc
        if best is None:
            raise Fail("no prize room")
        _, tri, s = best
        if not seal(tri, s):
            raise Fail("prize seal")
        app = nb(tri, s)
        walls[tri][s] = OPEN; walls[app][OPP[s]] = SHUT
        roles[tri] = "prize"; roles[app] = "boss"          # the guard: its shutter opens when the boss dies
        boss = app
        # a second boss somewhere else
        cand = [c for c in free() if c not in hidden and nb(ent, N_) != c]
        if not cand:
            raise Fail("no second boss")
        b2 = max(cand, key=lambda c: (abs(dist.get(c, 0) - dist.get(app, 0)) + rng.random() * 3, -c))
        roles[b2] = "boss"          # (owner 2026-11-26: its doors as any room's; Unseeded: shutters)
        if not _seeded():
            _shut_boss(walls, b2, deg)
    else:
        # boss room: far from the entrance (owner 2026-11-26: its doors as any room's; only a shrine's guard keeps
        # its shutter into the prize)
        cand = free()
        boss = max(cand, key=lambda c: (dist.get(c, 0) + rng.random() * 2, -c))
        roles[boss] = "boss"
        if not _seeded():
            _shut_boss(walls, boss, deg)
        tri = boss                                  # (the game picks the triforce's room at load)
        pool = [c for c in free() if behind_ok(c)]
        if not pool:
            raise Fail("no old man room")
        choice = rng.choice(pool)
        roles[choice] = "choice"
        if v10:                                 # (1.0) ZORA's triforce room (SH-ROOM-01): its own room, layout $29
            cand = [c for c in free() if c not in hidden]
            if not cand:
                raise Fail("no triforce room")
            tri = rng.choice(cand)
            roles[tri] = "triforce"
    if len(reach(graph())) != len(cells):
        raise Fail("after specials")

    # item stairs: 1 (levels 1-7), 2 (level 8); levels 1-3 always push-block (level 2 turns it into a floor item)
    item_stairs = []
    n_items = ITEM_STAIRS[cls] if rule is None or (lvcls == "L2" and not _quest_l2()) else rule[0]
    for _ in range(n_items):
        pool = [x for x in free() if x not in hidden]
        if not pool:
            raise Fail("no item stairs room")
        c = rng.choice(pool); roles[c] = "item_stairs"; item_stairs.append(c)

    # more boss rooms (level 9: the Patra rooms)
    nb_ = (N_BOSS[lvcls] if n_boss is None else n_boss) - (0 if cls == "L9" else 1)
    if not shrine:
        for _ in range(nb_):
            cand = [c for c in free() if c not in hidden and dist.get(c, 0) >= 2] or \
                   [c for c in free() if c not in hidden and c != nb(ent, N_)]
            if not cand:
                if v10:                           # (1.0: a small level's triforce room took its place)
                    break
                raise Fail("no room for a boss")
            c = rng.choice(cand)
            roles[c] = "patra" if cls == "L9" else "boss"
            if not _seeded():
                _shut_boss(walls, c, deg)

    # layouts
    w4 = t4_weights(lvcls)
    codes = list(range(128))

    def fits(layout, c):
        open_sides = {s for s in range(4) if nb(c, s) in cells and passable(c, s)}
        if c == ent:
            open_sides.add(S_)
        g = GROUPS.get(layout & 0x3F)
        if g and not any(open_sides <= grp for grp in g):
            return False
        return True

    stairs = []
    bosses_ok = None
    order = sorted(cells, key=lambda x: (x != boss, roles.get(x) != "boss", x))     # the main boss's layout first
    for c in order:
        r = rooms[c]; role = roles.get(c, "room"); r["role"] = role
        if role == "entrance":
            r.update(layout=0x21, eclass=0)
        elif role == "choice":
            r.update(layout=0x26, eclass=4)
            for s in range(4):                    # never a shutter on the old man's side
                if walls[c][s] == SHUT:
                    walls[c][s] = OPEN
        elif role == "check":
            r.update(layout=0x26, eclass=5)
        elif role == "ganon":
            r.update(layout=0x28, eclass=6)
        elif role == "zelda":
            r.update(layout=0x27, eclass=7)
        elif role == "boss":
            # every boss room's layout holds a boss of one graphics group (the game picks each room's boss at load)
            # (owner 2026-11-26) the boss layouts or any ordinary one (its share as an ordinary room's), as ZORA
            opts = [L for L in BOSS_LAYOUTS if fits(L, c)]
            wb = max(1, sum(w4) // max(1, sum(1 for x in w4 if x)))           # (a boss layout: an average room's)
            ow = [w4[L] if L not in opts else 0 for L in codes]
            cand = [(L, wb) for L in opts] + ([(L, ow[L]) for L in codes
                                               if ow[L] and not L & 0x40 and fits(L, c) and boss_of(L)]
                                              if _seeded() else [])               # (Unseeded: the boss layouts)
            if not _seeded():                       # (Unseeded: the old way, by graphics group)
                if bosses_ok is not None:
                    opts = [L for L in opts if groups_of(BOSS_OF[L]) & groups_ok] or opts
                L = rng.choice(opts)
                if bosses_ok is None:
                    bosses_ok, groups_ok = set(BOSS_OF[L]), groups_of(BOSS_OF[L])
                else:
                    groups_ok = groups_ok & groups_of(BOSS_OF[L]) or groups_ok
                    bosses_ok = {x for x in bosses_ok if groups_of([x]) & groups_ok} or bosses_ok
            else:
                if bosses_ok is not None:          # (a boss every boss room so far can hold)
                    cand = [(L, w) for L, w in cand if set(boss_of(L)) & bosses_ok] or cand
                L = rng.choices([x for x, _ in cand], [w for _, w in cand])[0]
                if bosses_ok is None:
                    bosses_ok, groups_ok = set(boss_of(L)), groups_of(boss_of(L))
                else:
                    bosses_ok = bosses_ok & set(boss_of(L)) or bosses_ok
                    groups_ok = groups_of(bosses_ok)
            r.update(layout=L, eclass=3, item=None, trigger=T_ALL_DEAD, pos=0)    # no heart container
        elif role == "patra":
            for _ in range(200):
                L = rng.choices(codes, w4)[0]
                if fits(L, c) and not L & 0x40:
                    break
            else:
                L = 0x00
            r.update(layout=L, eclass=3, trigger=T_ALL_DEAD)
        elif role == "prize":
            r.update(layout=0x29, eclass=0, trigger=T_NONE)            # the triforce room, no enemies
        elif role == "triforce" and v10:              # (1.0: ZORA's, standing; at $89)
            r.update(layout=0x29, eclass=0, trigger=T_NONE, item=I_TRIFORCE,
                     pos=0 if postab is None else postab.index(0x89))
        elif role in ("item_stairs", "transport"):
            if role == "item_stairs" and cls == "L13":
                lays = PUSH_STAIRS
            else:
                lays = OPEN_STAIRS + PUSH_STAIRS
            lays = [L for L in lays if fits(L, c) and not (sh10 and L == 0x1B)]   # (a shrine: no walled-in corridor)
            if not lays and role == "item_stairs" and cls == "L13":
                raise Fail("no push stairs")       # (level 2 turns them into a floor item)
            lays = lays or [0x1C]
            L = rng.choice(lays)
            if L == 0x1B and nb(c, E_) in cells:      # the corridor stairs: no east doorway
                y = nb(c, E_)
                saved = (walls[c][E_], walls[y][W_])
                walls[c][E_] = walls[y][W_] = WALL
                if len(reach(graph())) != len(cells):
                    walls[c][E_], walls[y][W_] = saved
                    L = 0x1C
            r.update(layout=L, eclass=2 if L == 0x1C else 1,
                     trigger=T_BLOCK_STAIRS if L in PUSH_STAIRS else T_NONE)
        else:
            for _ in range(200):
                L = rng.choices(codes, w4)[0]
                if fits(L, c) and not (role == "triforce" and L & 0x40):
                    break
            else:
                L = 0x00
            r.update(layout=L, eclass=2 if (L & 0x3F) in NO_TRAPS else 1)
            if L & 0x40:
                r["trigger"] = T_BLOCK_DOOR
            if role == "zguard":                  # (1.0) Zelda's way: opened by the Triforce of Power
                r.update(layout=L & 0x3F, trigger=T_LAST_BOSS)
    if len(reach(graph())) != len(cells):
        raise Fail("after layouts")

    # transports and cellars
    if len(trans) > len(free_transport_cellars) or len(item_stairs) > len(free_item_cellars):
        raise Fail("no cellar squares")
    for (a, b), sq in zip(trans, free_transport_cellars):
        la = rooms[a]["layout"]
        if rooms[b]["layout"] != la:            # both ends: the same stairs position
            rooms[b]["layout"] = la
            rooms[b]["trigger"] = rooms[a]["trigger"]
        if la not in STAIR_EXIT:
            raise Fail("transport layout")
        x, y = STAIR_EXIT[la]
        stairs.append((sq, "transport", a, b, x, y))
    for c, sq in zip(item_stairs, free_item_cellars):
        if rooms[c]["layout"] not in STAIR_EXIT:
            raise Fail("item stairs layout")
        x, y = STAIR_EXIT[rooms[c]["layout"]]
        stairs.append((sq, "item", c, c, x, y))

    # items: only the shrine's prize here (the game places the rest at load, from the rooms' marks below)
    if shrine:
        rooms[tri]["item"], rooms[tri]["pos"] = I_TRIFORCE, 0

    for c in cells:
        if roles.get(c) == "zguard":
            for t in range(4):
                if walls[c][t] == SHUT and roles.get(nb(c, t)) != "zelda":
                    walls[c][t] = OPEN
    # a push block that reveals stairs: never a shutter in that room
    for c in cells:
        if rooms[c]["trigger"] == T_BLOCK_STAIRS:
            walls[c] = [OPEN if x == SHUT else x for x in walls[c]]
    # shutters need a room trigger that opens them
    for c in cells:
        r = rooms[c]
        if SHUT in walls[c] and r["trigger"] == T_NONE and roles.get(c) != "check":   # (the check old man
            r["trigger"] = T_ALL_DEAD                                                    #  opens his own)
            if r["eclass"] == 0:
                for s in range(4):
                    if walls[c][s] == SHUT:
                        walls[c][s] = OPEN
                r["trigger"] = T_NONE
    for c in cells:
        r = rooms[c]
        if r["trigger"] == T_BLOCK_DOOR and SHUT not in walls[c]:
            r["layout"] &= 0x3F                       # a push block with nothing to open: a plain block
            r["trigger"] = T_NONE
        if r["layout"] & 0x40 and r["trigger"] not in (T_BLOCK_DOOR, T_BLOCK_STAIRS):
            r["layout"] &= 0x3F
    # shutters back to the level's vanilla share: drawn ones (not a boss's, Ganon's, the check room's or a push
    # block's) become open doors while there are more than its share
    pairs = [(c, t) for c in cells for t in (E_, S_) if nb(c, t) in cells and piece[nb(c, t)] == piece[c]
             and (walls[c][t] != WALL or walls[nb(c, t)][OPP[t]] != WALL or True)]
    kept = ("prize", "ganon", "check", "zelda", "zguard") if _seeded() else ("boss", "patra", "ganon", "check", "zelda")
    keep = lambda c: roles.get(c) in kept or rooms[c]["trigger"] == T_BLOCK_DOOR
    def is_shut(c, t):
        y = nb(c, t)
        return SHUT in (walls[c][t], walls[y][OPP[t]]) and not ({walls[c][t], walls[y][OPP[t]]} & {KEY, KEY2, BOMB})
    target = round(len(pairs) * wts[SHUT] / max(1, sum(wts)))
    shut = [p_ for p_ in pairs if is_shut(*p_)]
    free_s = [(c, t) for c, t in shut if not keep(c) and not keep(nb(c, t))]
    rng.shuffle(free_s)
    while len(shut) > target and free_s:
        c, t = free_s.pop(); y = nb(c, t)
        for x, side in ((c, t), (y, OPP[t])):
            if walls[x][side] == SHUT:
                walls[x][side] = OPEN
        shut.remove((c, t))
    if v10:
        _items_v10(rooms, roles, cells, cls, lvcls, rng, passable, nb_ok=lambda c, t: nb(c, t) in cells,
                   postab=postab)
    # the item marks: rooms that may hold an item, a usable spot, the center usable?, standing only?
    nmark = ncenter = 0
    for c in ([] if v10 else cells):
        r = rooms[c]
        if r["item"] is not None:
            continue
        lay = r["layout"]
        if roles.get(c) in ("entrance", "choice", "check", "zelda", "ganon", "prize") or (lay & 0x3F) in NO_ITEM_LAYOUTS:
            continue
        opts = list(usable(lay))
        if (lay & 0x3F) in CHUTE_SIDES:
            if not any(passable(c, t) and nb(c, t) in cells for t in CHUTE_SIDES[lay & 0x3F]):
                continue                            # no door into the chute
            opts = [p for p in opts if p == 0]
        if not opts:
            continue
        m = MARK | (1 if 0 in opts else 0) | (2 if r["trigger"] in (T_BLOCK_DOOR, T_BLOCK_STAIRS) or not r["eclass"] else 0)
        r["item"], r["pos"] = m, rng.choice(opts)
        nmark += 1; ncenter += m & 1
    if not shrine and cls != "L9" and not ncenter and not v10:
        raise Fail("no triforce room")
    if nmark < 6 and not v10:
        raise Fail("too few item rooms")
    # a shrine's prize room: its one way in a shutter from the guard's (boss) room; every other side solid
    if shrine:
        ways = [t for t in range(4) if nb(tri, t) in cells and (walls[tri][t] != WALL or walls[nb(tri, t)][OPP[t]] != WALL)]
        if len(ways) != 1 or walls[tri][ways[0]] != OPEN or walls[nb(tri, ways[0])][OPP[ways[0]]] != SHUT \
                or nb(tri, ways[0]) != boss:
            raise Fail("prize room ways")
    # the corridor stairs (1Q3's raft-stairs room): only with a solid east side (both sides of it)
    for c in cells:
        if rooms[c]["layout"] == 0x1B:
            y = nb(c, E_)
            if walls[c][E_] != WALL or (y in cells and walls[y][W_] != WALL):
                raise Fail("corridor stairs east")
    if sh10:                                      # (1.0) a shrine's doors (its prize room's sealed sides aside)
        for c in cells:
            for t in (E_, S_):
                y = nb(c, t)
                if y in cells and piece[y] == piece[c] and tri not in (c, y) and \
                        not {walls[c][t], walls[y][OPP[t]]} <= {OPEN, KEY, SHUT, BOMB}:
                    raise Fail("shrine door kinds")
    # (owner 2026-11-27) level 9's entrance: solid east and west (both sides), its way on north only
    if cls == "L9":
        for t in (E_, W_):
            y = nb(ent, t)
            if walls[ent][t] != WALL or (y in cells and walls[y][OPP[t]] != WALL):
                raise Fail("level 9 entrance sides")
    for c in cells:
        rooms[c]["walls"] = walls[c]
    if len(reach(graph())) != len(cells):
        raise Fail("final")
    return dict(cells=rooms, stairs=stairs, start=ent, boss=boss, tri=tri, postab=postab,
                choice=None if shrine else choice, item_stairs=item_stairs, trans=trans,
                bosses=sorted(bosses_ok) if bosses_ok else [])


DECK_MARKS = 2                            # (1.0) levels 1-8: rooms left marked for the deck's spots (the blue potion
                                          #  room, the floor item): the game places those at load


def _items_v10(rooms, roles, cells, cls, lvcls, rng, passable, nb_ok, postab=None):
    """(1.0, owner 2026-11-28) ZORA's room items (SH-ROOM-12/13, T3): each item room draws bombs / nothing / five
    rupees / a key by its level's odds (a no-item draw redrawn while the level has under four item rooms); then the
    compass and the map each take an item room's place (SH-ITEM-01). Push block rooms may hold a standing item.
    Triggers: a push block's stays (standing); no enemies: standing; else 2 in 3 dropped when all are dead.
    Levels 1-8 keep DECK_MARKS rooms without an item marked for the deck's spots."""
    lv = int(lvcls[1]) if lvcls[0] == "L" and lvcls[1:].isdigit() else None
    t3 = T3[lv] if lv else weights(cls, T3)
    elig = []
    for c in sorted(cells):
        r = rooms[c]
        lay = r["layout"]
        if r["item"] is not None or roles.get(c) in ("entrance", "choice", "check", "zelda", "ganon", "prize",
                                                       "zguard", "triforce") or (lay & 0x3F) in NO_ITEM_LAYOUTS:
            continue
        sides = {t for t in range(4) if nb_ok(c, t) and passable(c, t)}
        opts = list(spot_slots(lay, postab, sides))
        if opts:
            elig.append((c, opts))
    draw = lambda: rng.choices((I_BOMBS, None, I_RUPEES, I_KEY), t3)[0]
    held, vc = [], 0
    for c, opts in elig:
        it = draw()
        n = 0
        while it is None and vc < 4 and n < 32:
            it = draw(); n += 1
        if it is None:
            continue
        r = rooms[c]
        r["item"], r["pos"] = it, rng.choice(opts)
        vc += 1
        held.append(c)
        if r["trigger"] in (T_BLOCK_DOOR, T_BLOCK_STAIRS) or not r["eclass"]:
            continue
        r["trigger"] = T_ALL_DEAD_ITEM if rng.random() < 2 / 3 else T_ALL_DEAD
    for code in (I_COMPASS, I_MAP):
        cnt = [c for c in held if rooms[c]["item"] in (I_BOMBS, I_RUPEES, I_KEY)]
        if not cnt:
            raise Fail("no room for the map / compass")
        rooms[rng.choice(cnt)]["item"] = code
    if lvcls[0] == "L" and lv and lv <= 8:
        empty = [(c, o) for c, o in elig if rooms[c]["item"] is None]
        if len(empty) < DECK_MARKS:             # (a small level: item rooms give way, not the map or compass)
            more = [(c, o) for c, o in elig if rooms[c]["item"] in (I_BOMBS, I_RUPEES, I_KEY)]
            empty += rng.sample(more, min(len(more), DECK_MARKS - len(empty)))
        if len(empty) < DECK_MARKS:
            raise Fail("no rooms for the deck's spots")
        for c, opts in rng.sample(empty, DECK_MARKS):
            r = rooms[c]
            m = MARK | (1 if (0 if postab is None else postab.index(0x89) if 0x89 in postab else -1) in opts else 0) | (2 if r["trigger"] in (T_BLOCK_DOOR, T_BLOCK_STAIRS) or not r["eclass"] else 0)
            r["item"], r["pos"] = m, rng.choice(opts)


def make_variants(cells, cls, k, seed, free_item_cellars, free_transport_cellars, hidden=(), n_boss=None, rule=None,
                  postab=None):
    out = []
    rng = random.Random(seed)
    tries = 0
    while len(out) < k:
        tries += 1
        if tries > 400:
            raise RuntimeError(f"could not generate {cls}")
        try:
            out.append(generate(cells, cls, rng, free_item_cellars, free_transport_cellars, hidden, n_boss, rule,
                                postab=postab))
        except Fail:
            continue
    return out


def show(v):
    """A text picture of a variant (for checking by eye)."""
    sym = {"entrance": "E", "boss": "B", "triforce": "T", "prize": "P", "choice": "O", "item_stairs": "S",
           "check": "C", "ganon": "G", "zelda": "Z",
           "transport": "t", "approach": "a", "patra": "p"}
    door = {OPEN: " ", WALL: "|", BOMB: "b", KEY: "k", SHUT: "s", WALK1: "w"}
    lines = []
    cs = v["cells"]
    for r in range(8):
        top, mid = "", ""
        for c in range(16):
            x = r * 16 + c
            if x in cs:
                top += "+" + {OPEN: "  ", WALL: "--", BOMB: "bb", KEY: "kk", SHUT: "ss", WALK1: "ww"}[cs[x]["walls"][N_]]
                mid += door[cs[x]["walls"][W_]] + sym.get(cs[x]["role"], ".") + (
                    "i" if cs[x]["item"] is not None else " ")
            else:
                top += "   "; mid += "   "
        lines += [top, mid]
    return "\n".join(lines)

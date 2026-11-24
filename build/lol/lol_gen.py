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


def generate(cells, cls, rng, free_item_cellars, free_transport_cellars, hidden=(), n_boss=None, rule=None):
    """rule: a quest's (item stairs, transports, walk-through share, floor item) in place of LoL's counts."""
    lvcls = cls                           # the level's own class (its walls, layouts, bosses)
    if cls in GROUP:
        cls = GROUP[cls]                  # the rules' group
    """One variant of the dungeon on `cells` as level type `cls`."""
    cells = set(cells)
    shrine = cls == "SH"
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
    for c in sorted(cells):
        for s in (E_, S_):
            y = nb(c, s)
            if y not in cells or piece[y] != piece[c]:
                continue
            k = rng.choices(range(8), wts)[0]
            if rule is not None and rule[2] and rng.random() < rule[2]:
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
            opts = [(c, s) for c in sorted(seen) for s in range(4)
                    if nb(c, s) in cells and nb(c, s) not in seen and piece[nb(c, s)] == piece[c]]
            if not opts:
                raise Fail("unreachable")
            c, s = rng.choice(opts)
            # a door of the level's mix (not solid): open, bomb wall, locked or shutter
            k = rng.choices((OPEN, BOMB, KEY, SHUT), [wts[OPEN], wts[BOMB], wts[KEY], wts[SHUT]])[0]
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

    if cls == "L9":
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
        tri, boss, choice = gan, gan, None
    elif shrine:
        # the prize room: a dead end, its only way in a shutter on the approach room's side
        best = None
        for c in free():
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
        roles[b2] = "boss"
        for t in deg(b2):
            if walls[b2][t] == OPEN:
                walls[b2][t] = SHUT
    else:
        # boss room: far from the entrance; its doors shutters on its own side (shut until the boss dies)
        cand = free()
        boss = max(cand, key=lambda c: (dist.get(c, 0) + rng.random() * 2, -c))
        roles[boss] = "boss"
        for s in deg(boss):
            if walls[boss][s] in (OPEN,):
                walls[boss][s] = SHUT
        tri = boss                                  # (the game picks the triforce's room at load)
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
        pool = [c for c in free() if behind_ok(c)]
        if not pool:
            raise Fail("no old man room")
        choice = rng.choice(pool)
        roles[choice] = "choice"
    if len(reach(graph())) != len(cells):
        raise Fail("after specials")

    # item stairs: 1 (levels 1-7), 2 (level 8); levels 1-3 always push-block (level 2 turns it into a floor item)
    item_stairs = []
    n_items = ITEM_STAIRS[cls] if rule is None or lvcls == "L2" else rule[0]
    for _ in range(n_items):
        c = rng.choice([x for x in free() if x not in hidden]); roles[c] = "item_stairs"; item_stairs.append(c)

    # more boss rooms (level 9: the Patra rooms), shutters on their own side
    nb_ = (N_BOSS[lvcls] if n_boss is None else n_boss) - (0 if cls == "L9" else 1)
    if not shrine:
        for _ in range(nb_):
            cand = [c for c in free() if c not in hidden and dist.get(c, 0) >= 2] or \
                   [c for c in free() if c not in hidden and c != nb(ent, N_)]
            if not cand:
                raise Fail("no room for a boss")
            c = rng.choice(cand)
            roles[c] = "patra" if cls == "L9" else "boss"
            for t in deg(c):
                if walls[c][t] == OPEN:
                    walls[c][t] = SHUT

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
            opts = [L for L in BOSS_LAYOUTS if fits(L, c)]
            if bosses_ok is not None:
                opts = [L for L in opts if groups_of(BOSS_OF[L]) & groups_ok] or opts
            L = rng.choice(opts)
            if bosses_ok is None:
                bosses_ok, groups_ok = set(BOSS_OF[L]), groups_of(BOSS_OF[L])
            else:
                groups_ok = groups_ok & groups_of(BOSS_OF[L]) or groups_ok
                bosses_ok = {x for x in bosses_ok if groups_of([x]) & groups_ok} or bosses_ok
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
        elif role in ("item_stairs", "transport"):
            if role == "item_stairs" and cls == "L13":
                lays = PUSH_STAIRS
            else:
                lays = OPEN_STAIRS + PUSH_STAIRS
            lays = [L for L in lays if fits(L, c)]
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
        x, y = STAIR_EXIT[la]
        stairs.append((sq, "transport", a, b, x, y))
    for c, sq in zip(item_stairs, free_item_cellars):
        x, y = STAIR_EXIT[rooms[c]["layout"]]
        stairs.append((sq, "item", c, c, x, y))

    # items: only the shrine's prize here (the game places the rest at load, from the rooms' marks below)
    if shrine:
        rooms[tri]["item"], rooms[tri]["pos"] = I_TRIFORCE, 0

    # a push block that reveals stairs: never a shutter in that room
    for c in cells:
        if rooms[c]["trigger"] == T_BLOCK_STAIRS:
            walls[c] = [OPEN if x == SHUT else x for x in walls[c]]
    # shutters need a room trigger that opens them
    for c in cells:
        r = rooms[c]
        if SHUT in walls[c] and r["trigger"] == T_NONE:
            r["trigger"] = T_ALL_DEAD
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
    keep = lambda c: roles.get(c) in ("boss", "patra", "ganon", "check", "zelda") or rooms[c]["trigger"] == T_BLOCK_DOOR
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
    # the item marks: rooms that may hold an item, a usable spot, the center usable?, standing only?
    nmark = ncenter = 0
    for c in cells:
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
    if not shrine and cls != "L9" and not ncenter:
        raise Fail("no triforce room")
    if nmark < 6:
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
    for c in cells:
        rooms[c]["walls"] = walls[c]
    if len(reach(graph())) != len(cells):
        raise Fail("final")
    return dict(cells=rooms, stairs=stairs, start=ent, boss=boss, tri=tri,
                choice=None if shrine else choice, item_stairs=item_stairs, trans=trans,
                bosses=sorted(bosses_ok) if bosses_ok else [])


def make_variants(cells, cls, k, seed, free_item_cellars, free_transport_cellars, hidden=(), n_boss=None, rule=None):
    out = []
    rng = random.Random(seed)
    tries = 0
    while len(out) < k:
        tries += 1
        if tries > 400:
            raise RuntimeError(f"could not generate {cls}")
        try:
            out.append(generate(cells, cls, rng, free_item_cellars, free_transport_cellars, hidden, n_boss, rule))
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

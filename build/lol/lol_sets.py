"""Dungeon sets for the randomizer page (docs/dungeon-sets.md).

A set is four grids in the shape lol_genload reads from v2_grids/grids.txt: per grid (1-4) 8 rows of 16 squares,
each square '.' (free: cellars) or a letter, the letter's dungeon name, and each dungeon's level classes.

Shapes (the owner's rules, 2026-11-24): grid 4 holds 8 random shapes, grid 2 holds 6, grid 1 holds 4, grid 3 holds
3; a shape is 12-60 rooms. By room count: levels 1-3 and the shrines 12-20, levels 4-5 15-30, levels 6-8 20-45,
level 9 30-60. The sizes are drawn so every level has at least one shape (7 of 12-20 for levels 1-3 and the four
shrines, 2 of 15-30, 3 of 20-45, 1 of 30-60), and each grid keeps the free squares its shapes' cellars need.
"""
import random

ROWS, COLS = 8, 16
LETTERS = "ABCDEFGHIJKLMNOP"
COUNTS = {4: 8, 2: 6, 1: 4, 3: 3}               # shapes per grid
RANGES = {"L13": (12, 20), "SH": (12, 20), "L45": (15, 30), "L68": (20, 45), "L9": (30, 60)}
CLASSES_BY_RANGE = {"L13": ("L1", "L2", "L3"), "SH": ("SA", "SB", "SC", "SD"), "L45": ("L4", "L5"),
                    "L68": ("L6", "L7", "L8"), "L9": ("L9",)}


def classes_for(n):
    """The level classes a shape of n rooms may be."""
    out = []
    for k, (lo, hi) in RANGES.items():
        if lo <= n <= hi:
            out += CLASSES_BY_RANGE[k]
    return tuple(out)


def free_needed(sizes, pools=None):
    """Free squares a grid's shapes need: two item cellars per shape (plus two), and the transport cellars (7 on a
    grid with level 9's shape, else 3)."""
    nine = pools is not None and "L9" in pools
    return 2 * len(sizes) + 2 + (7 if nine else 3)


def plan_sizes(rng):
    """The 21 sizes per grid: grid 4 (8 shapes) 12-14 rooms, grid 2 (6) 15-22, grid 1 (4) 20-30, grid 3 (3, the
    large ones) 30-40; each grid keeps the free squares its cellars need."""
    while True:
        sizes = {4: sorted(rng.randint(12, 14) for _ in range(8)), 2: [rng.randint(15, 22) for _ in range(6)],
                 1: [rng.randint(20, 30) for _ in range(4)], 3: [rng.randint(30, 40) for _ in range(3)]}
        pools = {4: [], 2: [], 1: [], 3: ["L9"]}            # (grid 3 holds level 9: its transport cellars)
        if all(sum(sizes[g]) + free_needed(sizes[g], pools[g]) <= ROWS * COLS - 6 for g in sizes):
            return sizes, pools


# The owner's order (2026-11-24): each level takes one shape, at random among those left that it may use (its
# grids and its size range). The shrines take the four smallest of the 8-shape grid.
ORDER = (("L9", (3,)), ("L8", (1, 3)), ("L7", (1, 3)), ("L6", (2, 1, 3)), ("SH", (4,)), ("L5", (2, 1)),
         ("L4", (2, 1)), ("L1", (4, 2)), ("L2", (4, 2)), ("L3", (4, 2)))
SIZE_OF = {"L9": "L9", "L8": "L68", "L7": "L68", "L6": "L68", "L5": "L45", "L4": "L45",
           "L1": "L13", "L2": "L13", "L3": "L13"}


def assign(shapes, rng):
    """shapes: [(grid, name, rooms)] -> {name: level class}, in the owner's order."""
    left = list(shapes)
    out = {}
    for cls, grids in ORDER:
        if cls == "SH":
            small = sorted((s for s in left if s[0] == 4), key=lambda s: (s[2], s[1]))[:4]
            rng.shuffle(small)
            for sh, s in zip(("SA", "SB", "SC", "SD"), small):
                out[s[1]] = sh
                left.remove(s)
            continue
        lo, hi = RANGES[SIZE_OF[cls]]
        can = [s for s in left if s[0] in grids and lo <= s[2] <= hi]
        if not can:
            return None
        s = rng.choice(can)
        out[s[1]] = cls
        left.remove(s)
    return out


def _grow(grid, start, size, rng):
    cells = [start]
    grid[start] = -2
    frontier = set()

    def add_front(c):
        r, k = divmod(c, COLS)
        for dr, dk in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, kk = r + dr, k + dk
            if 0 <= rr < ROWS and 0 <= kk < COLS and grid[rr * COLS + kk] == -1:
                frontier.add(rr * COLS + kk)
    add_front(start)
    while len(cells) < size:
        if not frontier:
            return None
        # blobby: prefer squares touching two or more of the shape
        fl = sorted(frontier)
        w = []
        for c in fl:
            r, k = divmod(c, COLS)
            t = sum(1 for dr, dk in ((-1, 0), (1, 0), (0, -1), (0, 1))
                    if 0 <= r + dr < ROWS and 0 <= k + dk < COLS and grid[(r + dr) * COLS + k + dk] == -2)
            w.append(1 + 3 * (t - 1))
        c = rng.choices(fl, weights=w)[0]
        frontier.discard(c)
        grid[c] = -2
        cells.append(c)
        add_front(c)
    return cells


def map_ok(cells):
    """The level map (minimap) of these rooms fits the game's 45-byte drawing block."""
    import lolpaths  # noqa: F401
    from zora.generate.shapes.minimap import synthesize_minimap
    try:
        synthesize_minimap(set(cells))
        return True
    except AssertionError:
        return False


def make_grid(sizes, rng, pools=None, tries=2000):
    """Place the shapes (largest first) on an 8x16 grid; None if they don't fit."""
    for _ in range(tries):
        grid = [-1] * (ROWS * COLS)
        shapes, ok = [], True
        for i, n in sorted(enumerate(sizes), key=lambda x: -x[1]):
            empty = [c for c in range(ROWS * COLS) if grid[c] == -1]
            cells = _grow(grid, rng.choice(empty), n, rng)
            if cells is None or not map_ok(cells):
                ok = False
                break
            for c in cells:
                grid[c] = i
            shapes.append((i, cells))
        if ok and sum(1 for c in grid if c == -1) >= free_needed(sizes, pools):
            return grid
    return None


def shapes_set(seed):
    """Four grids of random shapes: {grid: {"rows": [...], "names": {letter: name}, "classes": {name: (...)}}}.
    Each level and shrine gets one shape (assign); the eight left over stay on their grids, unused."""
    rng = random.Random(seed)
    while True:
        sizes, pools = plan_sizes(rng)
        out, ok, shapes = {}, True, []
        k = 0
        for gi in (1, 2, 3, 4):
            grid = make_grid(sizes[gi], rng, pools[gi])
            if grid is None:
                ok = False
                break
            rows = ["".join("." if grid[r * COLS + c] < 0 else LETTERS[grid[r * COLS + c]] for c in range(COLS))
                    for r in range(ROWS)]
            names = {}
            for i, n in enumerate(sizes[gi]):
                k += 1
                names[LETTERS[i]] = f"Shape {k}"
                shapes.append((gi, f"Shape {k}", n))
            out[gi] = {"rows": rows, "names": names, "classes": {}}
        if not ok:
            continue
        got = assign(shapes, rng)
        if got is None:
            continue
        for gi, nm, _ in shapes:
            out[gi]["classes"][nm] = (got[nm],) if nm in got else ()
        return out


# --- quests, Random and Mixed (docs/dungeon-sets.md) ---

SOURCES = ("1q", "2q", "3q", "4q", "lol", "shapes")
# LoL's pools (v2_grids/grids.txt, 2026-11-20)
LOL_SHRINES = {"Giraffe", "Cactus", "Bat", "Face", "Pompadour", "Piranha", "Sock Puppet"}
LOL_LEVELS = {"Vice", "Anteater", "Elephant", "Robber", "Whale", "Poodle", "Unicorn", "Gecko", "Stallion", "Rook",
              "Bell"}
LOL_NINES = {"Serpent", "Balloon", "Ghost", "Hero", "Hellhound"}
LOL_LEVELS |= {"Hero", "Hellhound", "Bomb", "Candle", "Guillotine", "Bird", "Broken Reticle", "Ladle",   # (grids 7-9: their
               "Notes", "Pyramids", "Heart", "Bull", "Periscope"}                                #  classes say which)
LOL_SHRINES |= {"Guillotine", "Bird", "Broken Reticle", "Ladle", "Bull", "Notes", "Periscope", "Question Mark"}
SHRINES = ("SA", "SB", "SC", "SD")
LEVEL_RANGE = {"L1": "L13", "L2": "L13", "L3": "L13", "L4": "L45", "L5": "L45", "L6": "L68", "L7": "L68",
               "L8": "L68", "L9": "L9"}


def _rc(c):
    return divmod(c, COLS)


def _shift(cells, dr, dc):
    out = []
    for c in cells:
        r, k = _rc(c)
        r, k = r + dr, k + dc
        if not (0 <= r < ROWS and 0 <= k < COLS):
            return None
        out.append(r * COLS + k)
    return out


def _fresh_shape(n, rng):
    """One random shape of n rooms on an empty grid (its map fits)."""
    while True:
        grid = [-1] * (ROWS * COLS)
        cells = _grow(grid, rng.randrange(ROWS * COLS), n, rng)
        if cells and map_ok(cells):
            return sorted(cells)


def _lol_pool():
    """LoL's designs: [(name, cells, block, classes)] (grids 1-4, and grids 7 and 8)."""
    import lol_genload as GL
    ds, _ = GL.lol_designs()
    out = [(nm, cells, f"lol:{gi}", GL.classes_of(nm)) for gi, _, nm, cells, _ in ds]
    g = lol_grids()
    for gi in (7, 8, 9):
        out += [(nm, sorted(cs), f"lol:{gi}", EXTRA_CLASSES[nm]) for nm, cs in sorted(g[gi]["des"].items())]
    return out


def lol_alt_set(swap2, swap3):
    """The plain LoL set with grid 8 (Broken Reticle, Bomb, Candle, Guillotine, Bird, Ladle) or 9 (Notes, Question Mark,
    Pyramids, Heart, Bull, Periscope) in grid 2's place (swap2: 8 or 9, or 0) and / or grid
    7 (the Hero and the Hellhound) in grid 3's (the Ghost, the Gecko and the Balloon); the other grids as they are,
    every design with LoL's own classes."""
    import lol_genload as GL
    g = lol_grids()
    out = {}
    for slot, src in ((1, 1), (2, swap2 or 2), (3, 7 if swap3 else 3), (4, 4)):
        names = sorted(g[src]["des"])
        letters = {nm: LETTERS[i] for i, nm in enumerate(names)}
        occ = {c: nm for nm in names for c in g[src]["des"][nm]}
        rows = ["".join(letters[occ[r * COLS + c]] if r * COLS + c in occ else "." for c in range(COLS))
                for r in range(ROWS)]
        out[slot] = {"rows": rows, "names": {letters[nm]: nm for nm in names},
                     "classes": {nm: EXTRA_CLASSES.get(nm) or GL.classes_of(nm) for nm in names},
                     "hidden": dict(g[src]["hidden"])}
    return out


def quest_l2():
    """2Q, 3Q and 4Q keep their own level 2 (its item stairs and floor item as the quest has them); the other sets
    play level 2 as LoL's (its stairs block reveals nothing: a floor item)."""
    import os
    return os.environ.get("LOL_SET", "lol") in ("2q", "3q", "4q")


def quest_counts(cls, rule):
    """A quest level's (item stairs, transports) from its rule: level 2's stairs stay LoL's (a floor item), level 9
    keeps two cellars (its record's item and the red potion), at most two (the level header's)."""
    items, trans = rule[0], rule[1]
    if cls == "L9":
        items = 2
    return min(items, 2), trans


def cellar_need(cls, cells=(), rule=None):
    """(item cellars, transport cellars) a design of this level class takes on its grid: LoL's item stairs per class
    (level 2's is a floor item: its cellar shares another's; shrines none), and its transports: one per extra piece
    of its footprint plus the class's own (lol_gen.generate)."""
    import lol_gen as G
    grp = G.GROUP[cls]
    items = 0 if cls == "L2" else G.ITEM_STAIRS[grp]
    pieces = len(set(G.pieces(set(cells)).values())) if cells else 1
    if rule is not None:                  # a quest's own stair rules (lol_quests.rules)
        qi, qt = quest_counts(cls, rule)
        return (0 if cls == "L2" and not quest_l2() else qi), max(qt, pieces - 1)
    return items, G.TRANSPORTS.get(grp, 0) + pieces - 1


def need(des):
    """Free squares a grid needs for its designs' cellars: des [(name, class, cells)]."""
    return sum(sum(cellar_need(c, cs)) for _, c, cs in des) + (1 if des and all(c == "L2" for _, c, _ in des) else 0)


def pack(fps, rng, tries=300):
    """fps: [dict(name, cls, block, cells)] -> at most four grids, each design at its own place on a grid of its
    block when it fits there, else moved (whole) to wherever it fits; every grid keeps its cellars' free squares."""
    for t in range(tries):
        grids = []
        order = sorted(fps, key=lambda f: -len(f["cells"]))
        if t:
            rng.shuffle(order)
        ok = True
        for f in order:
            placed = None
            def room(g, cs):              # it fits there, and the grid keeps its cellars' squares
                return (not (set(cs) & g["occ"].keys())
                        and ROWS * COLS - len(g["occ"]) - len(cs) >= need(g["des"] + [(f["name"], f["cls"], cs)]))
            for g in grids:
                if f["block"] in g["blocks"] and room(g, f["cells"]):
                    placed = (g, f["cells"])
                    break
            if placed is None and len(grids) < 4:
                g = {"blocks": set(), "occ": {}, "des": []}
                g["blocks"].add(f["block"])
                grids.append(g)
                placed = (g, f["cells"])
            if placed is None:
                offs = [(dr, dc) for dr in range(-7, 8) for dc in range(-15, 16)]
                rng.shuffle(offs)
                offs.sort(key=lambda o: abs(o[0]) + abs(o[1]))
                for g in sorted(grids, key=lambda g: len(g["occ"])):
                    for dr, dc in offs:
                        cs = _shift(f["cells"], dr, dc)
                        if cs is not None and room(g, cs):
                            placed = (g, cs)
                            break
                    if placed:
                        break
            if placed is None:
                ok = False
                break
            g, cs = placed
            for c in cs:
                g["occ"][c] = f["name"]
            g["des"].append((f["name"], f["cls"], cs))
        if ok and all(ROWS * COLS - len(g["occ"]) >= need(g["des"]) for g in grids):
            return grids
    return None


def _grids_out(grids):
    out = {}
    for gi, g in enumerate(grids, 1):
        letters = {nm: LETTERS[i] for i, (nm, _, _) in enumerate(g["des"])}
        rows = ["".join(letters[g["occ"][r * COLS + c]] if r * COLS + c in g["occ"] else "."
                        for c in range(COLS)) for r in range(ROWS)]
        out[gi] = {"rows": rows, "names": {letters[nm]: nm for nm, _, _ in g["des"]},
                   "classes": {nm: (cls,) for nm, cls, _ in g["des"]}}
    for gi in range(len(grids) + 1, 5):                     # (unused grids: empty)
        out[gi] = {"rows": ["." * COLS] * ROWS, "names": {}, "classes": {}}
    return out


def build_set(which, seed):
    """The page's dungeon set: 1q / 2q / 3q / 4q / shapes / random (four grids) / mixed. None: LoL's own maps
    (grids.txt)."""
    rng = random.Random(seed)
    if which == "random":
        return random_grids_set(rng)
    if which == "lol":                    # grid 2's place: grid 2, 8 or 9 (a third each); grid 3's: 3 or 7 (half)
        swap2, swap3 = rng.choice((0, 8, 9)), rng.random() < 0.5     # (owner, 2026-11-24)
        return lol_alt_set(swap2, swap3) if swap2 or swap3 else None
    if which == "shapes":
        return shapes_set(seed)
    if which in ("1q", "2q", "3q", "4q"):
        return quest_set(which, rng)
    import lol_quests
    lol = _lol_pool()
    for attempt in range(50):
        fps, used = [], set()
        srcs = {lv: (rng.choice(SOURCES) if which == "mixed" else which) for lv in range(1, 10)}
        quests = {q: lol_quests.footprints(q) for q in set(srcs.values()) if q in ("1q", "2q", "3q", "4q")}
        ok = True
        for lv in range(1, 10):
            cls, src = f"L{lv}", srcs[lv]
            if src in quests:
                block, cells = quests[src][lv]
                fps.append(dict(name=f"{src.upper()} L{lv}", cls=cls, block=f"{src}:{block}", cells=cells))
            elif src == "lol":
                pool = LOL_NINES if lv == 9 else LOL_LEVELS
                can = [d for d in lol if cls in d[3] and d[0] in pool and d[0] not in used]
                if not can:
                    ok = False
                    break
                nm, cells, block, _ = rng.choice(can)
                used.add(nm)
                fps.append(dict(name=nm, cls=cls, block=block, cells=cells))
            else:
                lo, hi = RANGES[LEVEL_RANGE[cls]]
                fps.append(dict(name=f"Shape L{lv}", cls=cls, block=f"shape:{lv}",
                                cells=_fresh_shape(rng.randint(lo, min(hi, 40)), rng)))
        if not ok:
            continue
        # shrines: LoL's shrine designs, or (Shapes, or Mixed's coin) a small random shape
        for sh in SHRINES:
            if which == "mixed" and rng.random() < 0.5:
                fps.append(dict(name=f"Shape {sh}", cls=sh, block=f"shape:{sh}",
                                cells=_fresh_shape(rng.randint(12, 14), rng)))
                continue
            can = [d for d in lol if sh in d[3] and d[0] in LOL_SHRINES and d[0] not in used]
            nm, cells, block, _ = rng.choice(can)
            used.add(nm)
            fps.append(dict(name=nm, cls=sh, block=block, cells=cells))
        grids = pack(fps, rng)
        if grids is not None:
            return _grids_out(grids)
    raise RuntimeError(f"couldn't fit the {which} set's dungeons on four grids")


# --- quest sets: the quest's two blocks as they are, and two LoL grids for the shrines (owner, 2026-11-24) ---

EXTRA_NAMES = {7: {"H": "Hero", "D": "Hellhound"},
               8: {"T": "Broken Reticle", "B": "Bomb", "P": "Candle", "R": "Guillotine", "G": "Bird", "Y": "Ladle"},
               9: {"R": "Notes", "G": "Question Mark", "B": "Pyramids", "P": "Heart", "T": "Bull", "Y": "Periscope"}}
# grid 7's levels (owner, 2026-11-24): the Hero 6-9, the Hellhound 7-9
EXTRA_CLASSES = {"Hero": ("L6", "L7", "L8", "L9"), "Hellhound": ("L7", "L8", "L9")}
# grid 8's (no levels given: by size, as LoL's own designs; its 12 free squares hold the stairs this allows)
_S = ("SA", "SB", "SC", "SD")
EXTRA_CLASSES.update({"Bomb": tuple(f"L{n}" for n in range(5, 9)), "Candle": tuple(f"L{n}" for n in range(4, 9)),   # (owner)
                      "Guillotine": tuple(f"L{n}" for n in range(1, 6)) + _S,              # (owner)
                      "Bird": tuple(f"L{n}" for n in range(1, 6)) + _S,                    # (owner)
                      "Broken Reticle": ("L1", "L2", "L3") + _S, "Ladle": ("L1", "L2", "L3") + _S,   # (Broken Reticle: four
                      # pieces, too few rooms for levels 4-6's boss rooms; tried in lol_gen)
                      # grid 9's (by size too; its 13 free squares hold their stairs)
                      "Heart": tuple(f"L{n}" for n in range(1, 7)), "Pyramids": tuple(f"L{n}" for n in range(4, 9)),
                      "Bull": tuple(f"L{n}" for n in range(1, 6)) + _S,                    # (owner: Heart..Bull)
                      "Notes": tuple(f"L{n}" for n in range(1, 7)) + _S,
                      "Periscope": tuple(f"L{n}" for n in range(1, 7)) + _S,
                      "Question Mark": _S})                # (ten rooms in four pieces: only a shrine generates)
SHRINE_GRIDS = (1, 2, 3, 4, 8, 9)       # (a quest set's shrine grids: grid 7 has no shrine-sized design)


def lol_grids():
    """LoL's grids 1-4 and 7-9, whole: {grid: {"rows", "des": {name: cells}, "hidden": {name: cells}}}."""
    import os
    import lol_genload as GL
    import lolpaths
    ds, _ = GL.lol_designs()
    out = {}
    for gi, k, nm, cells, hid in ds:
        g = out.setdefault(gi, {"des": {}, "hidden": {}})
        g["des"][nm] = cells
        if hid:
            g["hidden"][nm] = hid
    for gi in out:
        occ = {c: nm for nm, cs in out[gi]["des"].items() for c in cs}
        out[gi]["occ"] = occ
    txt = open(os.path.join(lolpaths.LOL, "v2_grids", "grids_extra.txt")).read().split("\n\n")[1:]
    for gi, blk in zip((7, 8, 9), txt):
        rows = [l for l in blk.split("\n") if len(l) == COLS]
        g = {"des": {}, "hidden": {}, "occ": {}}
        for r in range(ROWS):
            for c in range(COLS):
                ch = rows[r][c]
                if ch == ".":
                    continue
                nm = EXTRA_NAMES[gi][ch.upper()]
                g["des"].setdefault(nm, []).append(r * COLS + c)
                g["occ"][r * COLS + c] = nm
                if ch.islower():
                    g["hidden"].setdefault(nm, []).append(r * COLS + c)
        out[gi] = g
    return out


def quest_set(quest, rng):
    """1Q-4Q: the quest's blocks 1-6 and 7-9 as they are (levels 1-9), and two LoL grids picked at random (of six),
    whose designs of 12-20 rooms give the four shrines (any four of them)."""
    import lol_quests
    fp = lol_quests.footprints(quest)
    qr = lol_quests.rules(quest)
    lol = lol_grids()
    lo, hi = RANGES["SH"]
    while True:
        pair = rng.sample([g for g in sorted(lol) if g in SHRINE_GRIDS], 2)
        cand = [(gi, nm) for gi in pair for nm, cs in sorted(lol[gi]["des"].items()) if lo <= len(cs) <= hi
                and map_ok(cs)]
        if len(cand) < 4:
            continue
        pick = rng.sample(cand, 4)
        break                          # (the unused designs leave their grids: room for any cellars)
    shrines = dict(zip(pick, SHRINES))
    out = {}
    for gi, (block, lvs) in enumerate((("1-6", range(1, 7)), ("7-9", range(7, 10))), 1):
        names = {LETTERS[i]: f"{quest.upper()} L{lv}" for i, lv in enumerate(lvs)}
        occ = {c: LETTERS[i] for i, lv in enumerate(lvs) for c in fp[lv][1]}
        rows = ["".join(occ.get(r * COLS + c, ".") for c in range(COLS)) for r in range(ROWS)]
        rl = {f"{quest.upper()} L{lv}": list(qr[lv]) for lv in lvs}
        # the quest's stairs, when its block can't hold them all: fewer extra transports (the most first), then items
        free = sum(ch == "." for r in rows for ch in r)
        def total():
            return sum(sum(cellar_need(f"L{lv}", fp[lv][1], rl[f"{quest.upper()} L{lv}"])) for lv in lvs)
        while total() > free:
            nm = max(rl, key=lambda n: (rl[n][1] - (len(set(__import__("lol_gen").pieces(set(fp[int(n[-1])][1]))
                                                              .values())) - 1), rl[n][0]))
            if rl[nm][1] > 0 and cellar_need(f"L{nm[-1]}", fp[int(nm[-1])][1], rl[nm])[1] > \
                    len(set(__import__("lol_gen").pieces(set(fp[int(nm[-1])][1])).values())) - 1:
                rl[nm][1] -= 1
            elif rl[nm][0] > 0 and nm[-1] != "9":
                rl[nm][0] -= 1
            else:
                raise RuntimeError(f"{quest} block {block}: no room for its stairs")
        out[gi] = {"rows": rows, "names": names,
                   "classes": {f"{quest.upper()} L{lv}": (f"L{lv}",) for lv in lvs}, "hidden": {},
                   "rules": {n: tuple(r) for n, r in rl.items()}}
    for gi, src in zip((3, 4), pair):
        g = lol[src]
        used = sorted(nm for (g2, nm) in shrines if g2 == src)       # (owner: a design not used on a grid can
        letters = {nm: LETTERS[i] for i, nm in enumerate(used)}       # give up its squares for stairs)
        rows = ["".join(letters[g["occ"][r * COLS + c]] if g["occ"].get(r * COLS + c) in letters else "."
                        for c in range(COLS)) for r in range(ROWS)]
        out[gi] = {"rows": rows, "names": {v: k for k, v in letters.items()},
                   "classes": {nm: (shrines[(src, nm)],) for nm in used},
                   "hidden": {nm: h for nm, h in g["hidden"].items() if nm in letters}}
    return out


# --- Random: any four grids (owner, 2026-11-24) ---
# The pool: LoL's grids 1-9, the quests' blocks (1Q-4Q, levels 1-6 and 7-9: 8 grids) and a grid of random shapes.
# Four are drawn; levels 1-9 and the four shrines are dealt to their designs: LoL's designs by their own classes, a
# quest's or a random shape by its size (any level its room count fits: classes_for; a quest level keeps its stair
# rules). Designs no level takes leave their grid (their squares hold cellars). A draw whose designs can't take every
# level, or whose grids can't hold their cellars, is drawn again.
NEEDED = ("L9", "L8", "L7", "L6", "L5", "L4", "L3", "L2", "L1", "SA", "SB", "SC", "SD")


def _quest_grids():
    import lol_quests
    out = []
    for q in ("1q", "2q", "3q", "4q"):
        fp, qr = lol_quests.footprints(q), lol_quests.rules(q)
        for block, lvs in (("1-6", range(1, 7)), ("7-9", range(7, 10))):
            des, rules, cls = {}, {}, {}
            for lv in lvs:
                nm = f"{q.upper()} L{lv}"
                des[nm] = sorted(fp[lv][1])
                rules[nm] = tuple(qr[lv])
                cls[nm] = classes_for(len(des[nm])) or (f"L{lv}",)
            out.append({"src": f"{q}:{block}", "des": des, "hidden": {}, "rules": rules, "cls": cls})
    return out


def _shape_grid(rng):
    """One grid of random shapes, as one of the Random shapes set's four (its sizes and count)."""
    while True:
        sizes, pools = plan_sizes(rng)
        gi = rng.choice((1, 2, 3, 4))
        grid = make_grid(sizes[gi], rng, pools[gi], tries=200)
        if grid is None:
            continue
        des = {}
        for i, n in enumerate(sizes[gi]):
            des[f"Shape {i + 1}"] = [c for c in range(ROWS * COLS) if grid[c] == i]
        return {"src": "shapes", "des": des, "hidden": {}, "rules": {},
                "cls": {nm: classes_for(len(cs)) for nm, cs in des.items()}}


def _deal(cands, rng):
    """cands: {name: classes} -> {class: name} for every NEEDED class (random order, augmenting paths), or None."""
    who = {}
    names = list(cands)

    def try_cls(cls, seen):
        opts = [nm for nm in names if cls in cands[nm] and nm not in seen]
        rng.shuffle(opts)
        for nm in opts:
            seen.add(nm)
            if nm not in who or try_cls(who[nm], seen):
                who[nm] = cls
                return True
        return False
    for cls in NEEDED:
        if not try_cls(cls, set()):
            return None
    return {cls: nm for nm, cls in who.items()}


def random_grids_set(rng):
    import lol_genload as GL
    lol = lol_grids()
    pool = []
    for gi in sorted(lol):
        g = lol[gi]
        pool.append({"src": f"lol:{gi}", "des": g["des"], "hidden": g["hidden"], "rules": {},
                     "cls": {nm: tuple(EXTRA_CLASSES.get(nm) or (GL.classes_of(nm) if gi <= 4 else
                                                                   classes_for(len(cs))))
                             for nm, cs in g["des"].items()}})
    pool += _quest_grids()
    pool.append("shapes")
    for attempt in range(500):
        pick = [p if p != "shapes" else _shape_grid(rng) for p in rng.sample(pool, 4)]
        cands = {nm: [c for c in g["cls"][nm] if c in NEEDED] for g in pick for nm in g["des"]}
        got = _deal(cands, rng)
        if got is None:
            continue
        cls_of = {nm: cls for cls, nm in got.items()}
        out, ok = {}, True
        for gi, g in enumerate(pick, 1):
            used = sorted(nm for nm in g["des"] if nm in cls_of)
            letters = {nm: LETTERS[i] for i, nm in enumerate(used)}
            occ = {c: nm for nm in used for c in g["des"][nm]}
            rows = ["".join(letters[occ[r * COLS + c]] if r * COLS + c in occ else "." for c in range(COLS))
                    for r in range(ROWS)]
            rules = {nm: list(g["rules"][nm]) for nm in used if nm in g["rules"] and cls_of[nm][0] == "L"}
            free = sum(ch == "." for r in rows for ch in r)
            def need_of(nm):
                return cellar_need(cls_of[nm], g["des"][nm], rules.get(nm))
            def total():                    # (lol_genload.cellar_alloc: item cellars each, transports shared)
                ns = [need_of(nm) for nm in used]
                return sum(i for i, t in ns) + max([t for i, t in ns] or [0])
            while total() > free:           # a quest level's stairs, as quest_set trims them
                rl = [nm for nm in rules if rules[nm][1] > 0 or (rules[nm][0] > 0 and cls_of[nm] != "L9")]
                if not rl:
                    break
                nm = max(rl, key=lambda n: (rules[n][1], rules[n][0]))
                if rules[nm][1] > 0:
                    rules[nm][1] -= 1
                else:
                    rules[nm][0] -= 1
            if total() > free:
                ok = False
                break
            out[gi] = {"rows": rows, "names": {v: k for k, v in letters.items()},
                       "classes": {nm: (cls_of[nm],) for nm in used},
                       "hidden": {nm: h for nm, h in g["hidden"].items() if nm in letters},
                       "rules": {nm: tuple(r) for nm, r in rules.items()}}
        if ok:
            return out
    raise RuntimeError("Random: no four grids took every level")

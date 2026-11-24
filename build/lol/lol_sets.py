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

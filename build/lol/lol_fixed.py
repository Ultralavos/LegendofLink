"""Legend of Link: dungeons decided by the build (owner 2026-11-24: the norm; the page's "Unseeded" option, LOL_FIXED=0,
keeps the old in-game rolls).

Without it the game rolls these itself (lol_genload): the entrance deal on a new file (DEAL), and each level's and
shrine's record the first time Link needs it (gen_make: its design, variant, enemy group, palette, boss, seed and
items). With it the build rolls them here, from the seed, with the same rules, and the ROM only copies them:
  - the deal (71 entrances): A15 never a level 1-8; among the gated screens at least one level or shrine and one
    upgrade cave;
  - the 13 records (Levels 1-9, shrines A-D): a design each that may take that slot (lol_genload's masks; no design
    twice), the variant, the enemy group (any of 3), the palette (Level 9: its own), a boss from the variant's list,
    the seed (the rooms' enemies, read by the decoder: fixed with it), and the two cellar items (old men cards S /
    D / X or XP bags, as gen_make's weights).
Still rolled in the game: Level 9's stair item (from what Link has then), the old men's choices and the shrine prizes.
A card Link already holds three of comes as an orange XP bag (lol_bombup).
"""
import os
import random

FIXED = os.environ.get("LOL_FIXED", "1") != "0"   # (the norm since 2026-11-24; LOL_FIXED=0: unseeded, the old way)
_CACHE = {}


def _rng(tag):
    s = os.environ.get("LOL_SEED") or os.environ.get("LOL_SET_SEED") or "0"
    return random.Random(f"lol fixed {tag} {s}")


def deal(info):
    """The 71 entrances' contents, lol_entrances' order (info: lol_genload.deal_info)."""
    if "deal" in _CACHE:
        return _CACHE["deal"]
    import lol_entrances as E
    cont, a15, gated = info
    rng = _rng("deal")
    dun = lambda c: 0x01 <= c <= 0x0D
    for _ in range(10000):
        d = cont[:]
        rng.shuffle(d)
        if 1 <= d[a15] <= 8:
            continue
        if not any(dun(d[g]) for g in gated) or not any(d[g] in E.UPGRADES for g in gated):
            continue
        break
    else:
        raise AssertionError("no deal")
    _CACHE["deal"] = d
    return d


def records():
    """13 records of 5 bytes (slot order: Levels 1-9, shrines A-D); Level 9's item byte 0 (rolled in the game)."""
    if "rec" in _CACHE:
        return _CACHE["rec"]
    import lol_genload as GL
    ds, out = GL.build_variants()
    nd = len(ds)
    masks = [GL.slot_mask(d[2]) for d in ds]
    rng = _rng("records")
    dests = GL.DESTS
    opts = {dst: [x for x in range(nd) if masks[x] >> dst & 1] for dst in dests}
    for dst, o in opts.items():
        assert o, f"no design for slot {dst}"

    def solve(order, used):
        if not order:
            return {}
        dst = order[0]
        cand = [x for x in opts[dst] if x not in used]
        rng.shuffle(cand)
        for x in cand:
            rest = solve(order[1:], used | {x})
            if rest is not None:
                return {dst: x, **rest}
        return None
    order = sorted(dests, key=lambda t: (len(opts[t]), rng.random()))
    pick = solve(order, frozenset())
    assert pick is not None, "no design assignment"
    recs = []
    for dst in dests:
        d = pick[dst]
        ci = GL.SLOT_CLASS[dst]
        v = rng.randrange(GL.K)
        g = rng.randrange(3)
        b1 = v | g << 2 | ((0x80) if dst == 9 else rng.randrange(9) << 4)
        bosses = tuple(out[(d, ci)][v].get("bosses", ()))
        boss = rng.choice(bosses) if bosses else 0
        seed = rng.randrange(1, 256)
        if dst == 9:
            items = 0
        else:
            cel = lambda: rng.choices(range(5), weights=(13, 13, 13, 13, 12))[0]
            items = cel() | cel() << 3
        recs.append([d + 1, b1, boss, seed, items])
    _CACHE["rec"] = recs
    return recs


def describe():
    import lol_genload as GL
    ds, _ = GL.build_variants()
    names = [f"L{i}" for i in range(1, 10)] + [f"S{c}" for c in "ABCD"]
    return ", ".join(f"{n} {ds[r[0] - 1][2]}" for n, r in zip(names, records()))

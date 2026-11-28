"""Legend of Link 1.0 (test site; seeded builds only - unseeded stays the old way, owner 2026-11-28).

Step 1: the odds and the shops.
  odds10/old_men_shops.tsv   a row per level (1-3 one level, then 4-16), a column per item, "old men-shop" odds out
                             of 100. The build rolls each level's list (weighted, without repeats: lol_odds.lines'
                             method); a level of 1-3 is one list for all three.
  shrines                    each shrine level h <= 13 rolls its own list from the old men's level h + 3, then keeps
                             only candles, swords, rings, books, arrows (as their upgrades: the top tier, which
                             gives the next tier Link lacks), the wand, the bow and the magic key; 14-16 one list
                             from odds10/shrines_14_16.csv.
  shops                      each of the four kinds (shops A-D) its own lists; a shop shows the first three on its
                             level's list Link may have now (owned: skipped; a higher tier without the lower: the
                             lower; bait only with none, bombs below 5, a key with no keys), never saved; one buy
                             closes that entrance. Prices: PRICES, each rolled +-20% per kind when the seed is built.
  the sword line             wood -> white -> magical: a white sword without the wood sword is the wood sword.
"""
import csv, os, random
import lol_fixed

HERE = os.path.dirname(os.path.abspath(__file__))
D10 = os.path.join(HERE, "odds10")
ON = lol_fixed.FIXED

from lol_choice import (SWORD, ARROWS, BOW, CANDLE, RECORDER, WAND, RAFT, BOOK, RING, LADDER, MAGIC_KEY, BRACELET,
                        BOOMERANG, MAGIC_BOOMERANG, SHIELD, MAX_BOMBS, ANY)
POTION, BAIT, KEYS, BOMBS = 0x065E, 0x065D, 0x066E, 0x0658

# (table name, item code, (addr, lo, hi), (addr, lo, hi)): offered while lo <= [addr] < hi (hi 0: no upper bound)
ITEMS = [
    ("boomerang", 0x1D, (BOOMERANG, 0, 1), (MAGIC_BOOMERANG, 0, 1)),
    ("blue candle", 0x06, (CANDLE, 0, 1), ANY),
    ("bait", 0x04, (BAIT, 0, 1), ANY),
    ("bomb upgrade", 0x24, (MAX_BOMBS, 0, 20), ANY),
    ("power bracelet", 0x14, (BRACELET, 0, 1), ANY),
    ("raft", 0x0C, (RAFT, 0, 1), ANY),
    ("white sword", 0x02, (SWORD, 1, 2), ANY),
    ("bow", 0x0A, (BOW, 0, 1), ANY),
    ("arrows", 0x08, (ARROWS, 0, 1), ANY),
    ("wand", 0x10, (WAND, 0, 1), ANY),
    ("ladder", 0x0D, (LADDER, 0, 1), ANY),
    ("recorder", 0x05, (RECORDER, 0, 1), ANY),
    ("red book", 0x11, (BOOK, 0, 1), ANY),
    ("blue ring", 0x12, (RING, 0, 1), ANY),
    ("red candle", 0x07, (CANDLE, 1, 2), ANY),
    ("magic shield", 0x1C, (SHIELD, 0, 1), ANY),
    ("key", 0x19, (KEYS, 0, 1), ANY),
    ("bomb pack", 0x00, (BOMBS, 0, 5), ANY),
    ("pity heart", 0x22, ANY, ANY),
    ("magic boomer", 0x1E, (MAGIC_BOOMERANG, 0, 1), (BOOMERANG, 1, 0)),
    ("silver arrows", 0x09, (ARROWS, 1, 2), (BOW, 1, 0)),
    ("magical sword", 0x03, (SWORD, 2, 3), ANY),
    ("red ring", 0x13, (RING, 1, 2), ANY),
    ("blue book", 0x25, (BOOK, 1, 2), ANY),
    ("magic key", 0x0B, (MAGIC_KEY, 0, 1), ANY),
    ("wood sword", 0x01, (SWORD, 0, 1), ANY),          # (no odds: the white sword's lower tier)
]
NAMES = [c[0] for c in ITEMS]
# a higher tier Link can't have yet gives its lower tier (lol_odds' down chain: magical -> white -> wood)
LOWER = {0x03: 0x02, 0x02: 0x01, 0x07: 0x06, 0x13: 0x12, 0x09: 0x08, 0x25: 0x11, 0x1E: 0x1D}
# shrines: what each kept item counts as (the upgrade: its top tier)
SHRINE_AS = {"blue candle": "red candle", "red candle": "red candle", "white sword": "magical sword",
             "magical sword": "magical sword", "blue ring": "red ring", "red ring": "red ring",
             "red book": "blue book", "blue book": "blue book", "arrows": "silver arrows",
             "silver arrows": "silver arrows", "wand": "wand", "bow": "bow", "magic key": "magic key"}
SHRINE_14 = {"ring upgrade": "red ring", "sword upgrade": "magical sword", "arrow upgrade": "silver arrows",
             "book upgrade": "blue book", "magic key": "magic key"}
SHRINE_ITEMS = ["magical sword", "white sword", "wood sword", "red candle", "blue candle", "red ring", "blue ring",
                "blue book", "red book", "silver arrows", "arrows", "wand", "bow", "magic key"]
PRICES = {"key": 20, "bomb pack": 5, "bait": 20, "pity heart": 10, "bomb upgrade": 50, "arrows": 40,
          "silver arrows": 150, "blue candle": 40, "red candle": 80, "boomerang": 40, "magic boomer": 50,
          "power bracelet": 50, "raft": 50, "ladder": 75, "recorder": 75, "bow": 80, "wand": 125,
          "white sword": 150, "magical sword": 225, "magic shield": 50, "blue ring": 150, "red ring": 225,
          "red book": 75, "blue book": 125, "magic key": 200, "wood sword": 50}
BANDS = [(1, 3)] + [(h, h) for h in range(4, 17)]


def table():
    """{level label: {item: (old men, shop)}} from odds10/old_men_shops.tsv."""
    with open(os.path.join(D10, "old_men_shops.tsv")) as f:
        rows = [line.rstrip("\n").split("\t") for line in f if line.strip()]
    head = rows[0][1:]
    assert set(head) <= set(NAMES), set(head) - set(NAMES)
    out = {}
    for r in rows[1:]:
        cells = {name: tuple(int(x) for x in c.split("-")) for name, c in zip(head, r[1:])}
        assert sum(v[0] for v in cells.values()) == 100 and sum(v[1] for v in cells.values()) == 100, r[0]
        out[r[0]] = cells
    assert list(out) == ["1-3"] + [str(h) for h in range(4, 17)], list(out)
    return out


def shrine14():
    with open(os.path.join(D10, "shrines_14_16.csv")) as f:
        rd = list(csv.reader(f))[1:]
    w = {SHRINE_14[name]: int(v) for name, v in rd if int(v)}
    assert sum(w.values()) == 100
    return w


def rng(tag):
    s = os.environ.get("LOL_SEED") or os.environ.get("LOL_SET_SEED") or "0"
    return random.Random(f"lol 1.0 {tag} {s}")


def roll(weights, r):
    """One list: every item with odds, drawn one at a time by the odds of those left (keys u^(1/w): the same)."""
    ent = [k for k, w in weights.items() if w > 0]
    return sorted(ent, key=lambda k: -r.random() ** (1 / weights[k]))


def label(h):
    return "1-3" if h <= 3 else str(h)


def _with_upgrade(w, upgrade):
    """(lol_upmix) an "upgrade" entry: each item with odds gives it one point (the old tables' rule)."""
    if not upgrade:
        return w
    w = {k: v for k, v in w.items()}
    n = sum(1 for v in w.values() if v > 0)
    w = {k: (v - 1 if v > 1 else v) for k, v in w.items()}
    w["upgrade"] = n
    return w


def old_men_lines(names, upgrade=False):
    """16 lists (per heart level) of entry names, 1-3 sharing one."""
    t, r = table(), rng("old men")
    by = {lab: roll(_with_upgrade({k: v[0] for k, v in t[lab].items()}, upgrade), r) for lab in t}
    return [[n for n in by[label(h)] if n in names] for h in range(1, 17)]


def shop_lines(kind, names):
    t, r = table(), rng(f"shop {kind}")
    by = {lab: roll({k: v[1] for k, v in t[lab].items()}, r) for lab in t}
    return [[n for n in by[label(h)] if n in names] for h in range(1, 17)]


def shrine_lines(upgrade=False):
    t, r = table(), rng("shrines")
    keep = dict(SHRINE_AS, **({"upgrade": "upgrade"} if upgrade else {}))
    out = []
    for h in range(1, 14):
        line = []
        for n in roll(_with_upgrade({k: v[0] for k, v in t[label(h + 3)].items()}, upgrade), r):
            if n in keep and keep[n] not in line:
                line.append(keep[n])
        out.append(line)
    top = roll(_with_upgrade(shrine14(), upgrade), r)
    return out + [top] * 3


def as_choice(names):
    """lol_choice's list format for these items: (name, code, fewest containers, cond, cond, most containers)."""
    by = {c[0]: c for c in ITEMS}
    return [(n, by[n][1], 1, by[n][2], by[n][3], 16) for n in names]


def prices():
    """Per shop kind (0-3: shops A-D) {item: price}: each +-20% of PRICES, 1-255."""
    out = []
    for kind in range(4):
        r = rng(f"prices {kind}")
        out.append({n: max(1, min(255, r.randint(round(p * 0.8), round(p * 1.2)))) for n, p in PRICES.items()})
    return out


# (owner 2026-11-28) the wood sword cave's shop from shop level 11: (name, item code, base price), the first three
# Link may buy (lol_choice: bombs below a full bag, arrows and the shield only if he has none)
WOOD = [("key", 0x19, 75), ("bomb pack", 0x00, 20), ("arrows", 0x08, 80), ("pity heart", 0x22, 10),
        ("magic shield", 0x1C, 90)]


def wood_prices():
    r = rng("wood shop")
    return [max(1, min(255, r.randint(round(p * 0.8), round(p * 1.2)))) for _, _, p in WOOD]


# (owner 2026-11-28) the secret caves' amounts: one roll per size when the seed is built (every cave of a size the
# same); the cave table's prices in the ROM (bank 6 $8600: 20 caves' wares, then their prices; caves $11 30, $12 100,
# $13 10)
CAVE_PRICES_FILE = 0x1864C
SECRETS = {0x13: (1, 20), 0x11: (20, 45), 0x12: (51, 150)}


def secret_amounts():
    r = rng("secrets")
    return {c: r.randint(lo, hi) for c, (lo, hi) in SECRETS.items()}


def apply_secrets(rom: bytearray, notes: list) -> None:
    if not ON:
        return
    am = secret_amounts()
    for c, v in am.items():
        at = CAVE_PRICES_FILE + 3 * c + 1
        assert rom[at] in (10, 30, 100), (hex(c), rom[at])
        rom[at] = v
    notes.append(f"1.0 secrets: small {am[0x13]}, medium {am[0x11]}, large {am[0x12]}")


# hints that 1.0 makes wrong (owner 2026-11-28): the quote (as shown) -> its 1.0 text
HINTS = {"LEVELS 1-8 ALL HAVE AN OLD MAN, SEEK THEM": "LEVELS 1-9 ALL HAVE AN OLD MAN, SEEK THEM",
         "SHOP WARES AND DUNGEON ITEMS CAN INCREASE WITH YOUR LEVEL": "SHOP WARES AND OLD MEN GIFTS IMPROVE WITH YOUR LEVEL",
         "WHITE BORDER CARDS BOOST DUNGEON AND SHRINE FINDS": "WHITE BORDER CARDS BOOST OLD MEN AND SHRINE GIFTS"}

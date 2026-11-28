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
Step 2: the item deck (below): levels 1-8's cellars / floor items and blue potion rooms, the coast, the Armos;
  level 9's red potion and rolled item cellars swapped by the seed (l9_swap).
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


def seed():
    return os.environ.get("LOL_SEED") or os.environ.get("LOL_SET_SEED") or "0"


def rng(tag):
    return random.Random(f"lol 1.0 {tag} {seed()}")


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


# ---------------- step 2: the item deck (owner 2026-11-28) ----------------
# Every item spot of levels 1-8 (its cellars / floor item room, at most two: lol_fixed.spots; and its blue potion
# room, the old heart container's), the coast's and the Armos' item take the deck's next card the first time Link
# comes to them. The deck (rolled when the seed is built): 1-7 items by DECK_ODDS (no repeats), 1-3 each of the S, D
# and X cards, the rest a blue potion, a small (+15) or a large (+25) XP bag (1 in 3 each); shuffled. Dealt in the game
# in order, a card Link can't use skipped (owned; an upgrade at its top tier gives its next tier; a fourth card of a
# kind; a potion past 2, or 4 with the potion pouch; XP at heart level 16); none left: the letter (a Race Rom, 1 seed in
# 25: has_letter), else a big XP bag.
# Kinds (the deck's bytes): 0-14 an inventory byte's next tier (KINDS), 15 bomb upgrade, 16 blue potion, 17-19 the
# S / D / X cards, 20 / 21 small / large XP; $FE (lol_upmix) the upgrade card.
KINDS = [("ring upgrade", RING, [0x12, 0x13]), ("sword upgrade", SWORD, [0x01, 0x02, 0x03]),
         ("arrow upgrade", ARROWS, [0x08, 0x09]), ("book upgrade", BOOK, [0x11, 0x25]),
         ("candle upgrade", CANDLE, [0x06, 0x07]), ("boomerang upgrade", BOOMERANG, [0x1D, 0x1E]),
         ("magic key", MAGIC_KEY, [0x0B]), ("magic shield", SHIELD, [0x1C]), ("wand", WAND, [0x10]),
         ("bow", BOW, [0x0A]), ("ladder", LADDER, [0x0D]), ("recorder", RECORDER, [0x05]),
         ("power bracelet", BRACELET, [0x14]), ("raft", RAFT, [0x0C]), ("bait", BAIT, [0x04])]
SPECIAL = ["bomb upgrade", "blue potion", "S card", "D card", "X card", "small XP", "large XP"]
KIND_NAMES = [k[0] for k in KINDS] + SPECIAL
K = {n: i for i, n in enumerate(KIND_NAMES)}
DECK_ODDS = {"ring upgrade": 1, "sword upgrade": 1, "arrow upgrade": 1, "book upgrade": 1, "candle upgrade": 1,
             "magic key": 2, "magic shield": 3, "boomerang upgrade": 5, "wand": 5, "bow": 5, "ladder": 5,
             "recorder": 5, "power bracelet": 10, "raft": 10, "bomb upgrade": 15, "bait": 15, "blue potion": 15}
assert sum(DECK_ODDS.values()) == 100
LETTER = 0x15


def has_letter():
    """(owner 2026-11-28) whether this seed has the letter (the empty deck's card): Race Roms, about 1 seed in 25."""
    return os.environ.get("LOL_RACE") == "1" and rng("letter").randrange(25) == 0
SPOT_N = 26                             # spot = (level - 1) * 3 + its index (0 / 1 the cellars / floor room, 2 the
COAST, ARMOS = 24, 25                   #  blue potion room); the coast, the Armos


def deck_spots():
    return lol_fixed.spots() + 8 + 2


def deck():
    """(kinds, upos): the 1.0 deck; upos the Upgrade mix's upgrade card's place (lol_fixed.upos)."""
    if "deck" in _C:
        return _C["deck"]
    n = deck_spots()
    r = rng("deck")
    if lol_fixed.UPMIX:
        n -= 1
    items = roll(DECK_ODDS, r)[:r.randint(1, 7)]
    cards = [K["S card"] + c for c in range(3) for _ in range(r.randint(1, 3))]
    fill = [K[("blue potion", "small XP", "large XP")[r.randint(1, 3) - 1]]
            for _ in range(n - len(items) - len(cards))]
    d = [K[x] for x in items] + cards + fill
    assert len(d) == n
    r.shuffle(d)
    _C["deck"] = (d, r.randrange(n + 1))
    return _C["deck"]


def l9_swap():
    """Level 9's two cellars: which holds the red potion (False: the first, as before; True: the second)."""
    return rng("level 9 stairs").random() < 0.5


_C = {}
GROUND = None
DEAL = None                             # bank 12: the deal (A = spot -> A = the item; X, Y kept)
_SLOTS_AT = None                        # its slot table's file offset (filled by fill_slots once the entrances are dealt)


def deal_routine(rom):
    """The deal, in bank 0 (once). Each spot keeps its item in a hint quote byte (lol_genload HINT_QS) of an entrance
    that is neither a dungeon nor a hint cave: 0 not dealt yet, else $80 | the item ($FE: the upgrade card)."""
    global DEAL, _SLOTS_AT
    if DEAL is not None:
        return DEAL
    import lol_v3core as V3
    from lol_af import Asm, BANK
    from lol_genload import HINT_QS, DECK_PTR
    import lol_uptable as UT, lol_upgrades as U
    from lol_bombup import BADGES
    dk, upos = deck()
    T, KK = 0x019C, 0x0173
    zb, sb = UT.bit("zombie link"), UT.bit("heart snubber")
    starts = [sum(len(k[2]) for k in KINDS[:i]) for i in range(len(KINDS))]

    def build(org):
        a = Asm(org)
        a.label("deal").abs(0x8D, T).b(0x8A, 0x48, 0x98, 0x48)
        a.abs(0xAE, T).abs(0xBC, "sl").abs(0xB9, HINT_QS).br(0x30, "have")
        a.label("next")
        if lol_fixed.UPMIX:
            import lol_upmix as UM
            a.b(0xA9, upos, 0x38).abs(0xED, UM.UFLAGS).b(0x29, UM.MOVES).abs(0x8D, KK)
            a.abs(0xAE, DECK_PTR).b(0xE0, len(dk) + 1).br(0xB0, "empty")
            a.abs(0xEE, DECK_PTR).abs(0xEC, KK).br(0x90, "lo").br(0xF0, "up").b(0xCA)
            a.label("lo").abs(0xBD, "deck").abs(0x20, "res").br(0xB0, "next").br(0x90, "store")
            a.label("up").b(0xA9, 0xFE).br(0xD0, "store")
        else:
            a.abs(0xAE, DECK_PTR).b(0xE0, len(dk)).br(0xB0, "empty").abs(0xBD, "deck").abs(0xEE, DECK_PTR)
            a.abs(0x20, "res").br(0xB0, "next").br(0x90, "store")
        # (owner 2026-11-28) the letter in a Race Rom only, about 1 seed in 25 (has_letter; lol_infoshop); else a big
        # (blue, +25) XP bag
        a.label("empty").b(0xA9, LETTER if has_letter() else 0x2A)
        a.label("store").b(0x09, 0x80).abs(0x99, HINT_QS)
        a.label("have").b(0xC9, 0xFE).br(0xF0, "ret").b(0x29, 0x7F)
        a.label("ret").abs(0x8D, T).b(0x68, 0xA8, 0x68, 0xAA).abs(0xAD, T).b(0x60)
        # ground (the coast's and the Armos' stubs): the deal; the upgrade card its item (lol_upmix; X, Y kept)
        a.label("ground").abs(0x20, "deal")
        if lol_fixed.UPMIX:
            import lol_upmix as UM
            a.b(0xC9, 0xFE).br(0xD0, "g_r").b(0x8A, 0x48, 0x98, 0x48).b(*V3.far(UM.BANKX, UM.UITEM, DEAL_BANK))
            a.abs(0x8D, T).b(0x68, 0xA8, 0x68, 0xAA).abs(0xAD, T)
        a.label("g_r").b(0x60)
        # res: A = a kind -> C clear: A = its item now; C set: skipped (X, T, KK used; Y kept)
        a.label("res").abs(0x8D, KK).b(0xC9, len(KINDS)).br(0xB0, "sp")
        a.b(0xC9, K["ring upgrade"]).br(0xD0, "r1").abs(0xAD, zb[0]).b(0x29, zb[1]).br(0xD0, "skip").br(0xF0, "gen")
        a.label("r1").b(0xC9, K["sword upgrade"]).br(0xD0, "r5").abs(0xAD, sb[0]).b(0x29, sb[1]).br(0xD0, "skip")
        a.abs(0xAD, 0x7FF7).br(0xF0, "gen").b(0xA9, 32).br(0xD0, "bomb")         # (swordless: a bomb upgrade)
        a.label("r5").b(0xC9, K["boomerang upgrade"]).br(0xD0, "gen").abs(0xAD, MAGIC_BOOMERANG).br(0xD0, "skip")
        a.label("gen").abs(0xAE, KK).abs(0xBD, "alo").b(0xAA).abs(0xBD, 0x0600).abs(0xAE, KK)
        a.abs(0xDD, "cnt").br(0xB0, "skip").abs(0x7D, "start").b(0xAA).abs(0xBD, "codes").b(0x18, 0x60)
        a.label("skip").b(0x38, 0x60)
        a.label("sp").b(0xC9, K["bomb upgrade"]).br(0xD0, "s16").b(0xA9, 20).abs(0xAE, 0x7FF7).br(0xF0, "bomb")
        a.b(0xA9, 32)
        a.label("bomb").abs(0x8D, T).abs(0xAD, MAX_BOMBS).abs(0xCD, T).br(0xB0, "skip").b(0xA9, 0x24, 0x18, 0x60)
        a.label("s16").b(0xC9, K["blue potion"]).br(0xD0, "s17").b(0xA9, 2).abs(0x8D, T)
        a.abs(0xAD, U.POUCH[0]).b(0x29, U.POUCH[1]).br(0xF0, "p2").b(0xA9, 4).abs(0x8D, T)
        a.label("p2").abs(0xAD, POTION).abs(0xCD, T).br(0xB0, "skip").b(0xA9, 0x1F, 0x18, 0x60)
        a.label("s17").b(0xC9, K["small XP"]).br(0xB0, "xp").b(0xE9, K["S card"] - 1, 0xAA)   # (C clear: - 17)
        a.abs(0xAD, BADGES).abs(0x3D, "mask").abs(0xDD, "mask").br(0xF0, "skip").b(0x8A, 0x18, 0x69, 0x26, 0x60)
        a.label("xp").abs(0xAD, 0x066F).b(0xC9, 0xF0).br(0xB0, "skip")
        a.abs(0xAD, KK).b(0x18, 0x69, 0x29 - K["small XP"], 0x60)
        a.label("alo").b(*[k[1] & 0xFF for k in KINDS])
        a.label("cnt").b(*[len(k[2]) for k in KINDS])
        a.label("start").b(*starts)
        a.label("codes").b(*[c for k in KINDS for c in k[2]])
        a.label("mask").b(0x03, 0x0C, 0x30)
        a.label("deck").b(*dk)
        a.label("sl").b(*_C.get("slots", [0] * SPOT_N))
        return a
    assert all(k[1] >> 8 == 0x06 for k in KINDS)
    a = build(DEAL_AT)
    assert DEAL_AT + len(a.bytes()) <= DEAL_END, hex(DEAL_AT + len(a.bytes()))
    DEAL = a.labels["deal"]
    global GROUND
    GROUND = a.labels["ground"]
    _C["build"] = build
    return DEAL


DEAL_BANK, DEAL_AT, DEAL_END = 12, 0xAF00, 0xB100   # (below lol_odds' engine: lol_genload's variants stop below it)


WS12_AT, WS12_END = 0xBA00, 0xBB60            # (1.0) bank 12, above lol_odds' engine: the triforce caves' choosers


def _chooser(a, p, lst, vec):
    """A = the prize: the first entry of lst Link may have (the wood / white sword alike; a ring none with Zombie
    Link; swords none with the heart snubber, swordless a bomb upgrade below 32 bombs; UPGRADE_ENTRY: lol_upmix's
    vec); everything: a bomb upgrade, at the most bombs an orange XP bag (owner 2026-11-28). C clear."""
    import lol_uptable as T, lol_v3core as V3
    n = len(lst)
    a.label(p).b(0xA2, 0x00)
    a.label(p + "lp")
    if any(e[0] == UPGRADE_ENTRY[0] for e in lst):
        a.abs(0xBD, p + "i").b(0xC9, UPGRADE_ENTRY[0]).br(0xD0, p + "in").b(0x8A, 0x48)
        a.b(*V3.far(14, vec, DEAL_BANK)).b(0xA8, 0x68, 0xAA, 0x98).br(0xB0, p + "nx").b(0x18, 0x60)
        a.label(p + "in")
    a.abs(0xBC, p + "a").abs(0xB9, 0x0600).abs(0xDD, p + "m").br(0xB0, p + "nx")
    a.abs(0xBD, p + "i").b(0xC9, 0x12).br(0xF0, p + "rg").b(0xC9, 0x13).br(0xD0, p + "nr")
    a.label(p + "rg").abs(0xAD, T.bit("zombie link")[0]).b(0x29, T.bit("zombie link")[1]).br(0xD0, p + "nx")
    a.br(0xF0, p + "put")
    a.label(p + "nr").b(0xC9, 0x04).br(0xB0, p + "put").b(0xC9, 0x01).br(0x90, p + "put")
    a.abs(0xAD, T.bit("heart snubber")[0]).b(0x29, T.bit("heart snubber")[1]).br(0xD0, p + "nx")
    a.abs(0xAD, 0x7FF7).br(0xF0, p + "put")
    a.abs(0xAD, 0x067C).b(0xC9, 32).br(0xB0, p + "nx").b(0xA9, 0x24, 0x18, 0x60)
    a.label(p + "nx").b(0xE8, 0xE0, n).br(0xD0, p + "lp")
    a.abs(0x4C, "full")
    a.label(p + "put").abs(0xBD, p + "i").b(0x18, 0x60)
    a.label(p + "i").b(*[e[0] for e in lst]).label(p + "a").b(*[e[1] & 0xFF for e in lst])
    a.label(p + "m").b(*[e[2] for e in lst])


def ws12(ws_list):
    """(1.0) The triforce caves' choosers (far from lol_upgrades' ws / ms, bank 1): WS12_AT the 4-triforce cave's,
    MS12 the 8-triforce cave's. Placed by late()."""
    from lol_af import Asm
    import lol_upmix as UM
    global MS12
    def build(org):
        a = Asm(org)
        _chooser(a, "w", ws_list, UM.V_U4)
        _chooser(a, "m", tri8_table(), UM.V_U8)
        a.label("full").b(0xA9, 0x14).abs(0xAC, 0x7FF7).br(0xF0, "cp").b(0xA9, 0x20)   # (lol_bombup's cap: 20 / 32)
        a.label("cp").abs(0xCD, 0x067C).br(0xF0, "fu").br(0x90, "fu").b(0xA9, 0x24, 0x18, 0x60)
        a.label("fu").b(0xA9, 0x29, 0x18, 0x60)
        return a
    a = build(WS12_AT)
    code = a.bytes()
    assert WS12_AT + len(code) <= WS12_END, len(code)
    assert a.labels["w"] == WS12_AT
    MS12 = a.labels["m"]
    _C["ws12"] = code


MS12 = None


def fill_slots(rom, dealt):
    """The spots' save bytes: entrances (lol_entrances' order) that are neither a dungeon nor a hint cave."""
    import lol_entrances as E
    free = [i for i, c in enumerate(dealt) if not 0x01 <= c <= 0x0F and c != E.HINT
            and c not in (E.WHITE, E.MAGIC)]      # (the triforce caves' bytes: the 4-triforce cave's upgrade)
    assert len(free) >= SPOT_N, len(free)
    _C["slots"] = free[:SPOT_N]
    return free[:SPOT_N]


def late(rom):
    """lol_build, after lol_genload: the deal into bank 12 (the slots known by now)."""
    if DEAL is None:
        return
    from lol_af import place
    assert "slots" in _C
    a = _C["build"](DEAL_AT)
    assert a.labels["deal"] == DEAL
    place(rom, DEAL_BANK, DEAL_AT, a.bytes())
    if "ws12" in _C:
        place(rom, DEAL_BANK, WS12_AT, _C["ws12"])


def describe_deck():
    dk, upos = deck()
    names = [KIND_NAMES[k] for k in dk]
    if lol_fixed.UPMIX:
        names.insert(upos, "upgrade card")
    return f"1.0 deck ({deck_spots()} spots): " + ", ".join(names)


# ---------------- step 3: the Armos item's screen (owner 2026-11-28; ZORA's Shuffle Armos, OW-CAVE-05) ----------------
# Bank 4's Armos tables ($8CB2: 7 screens, $8CB9: their Xs; the first the item's, the rest stairs). Each X rolled from
# the formation's choices; the item swapped with one of the five screens' entries (C5 36, B13 28, D5 52, D14 61, E15
# 78). C5 (no cave of its own) always gets the stairs' screen settings; the screen the item moves to gives C5 its cave
# and hides its own (quest visibility: neither).
ARMOS_SCREENS_FILE, ARMOS_X_FILE = 0x10CC2, 0x10CC9
ARMOS_FORMATION = ((36, (32, 80, 128, 176, 224)), (11, (48, 80, 144, 176)), (28, (112, 144, 176, 208)),
                   (34, (48, 64, 80, 160, 176, 192)), (52, (32, 64, 96)), (61, (96, 144)), (78, (80, 160)))
ARMOS_SWAP = (0, 2, 4, 5, 6)
OW = 0x18410


def armos():
    """(screens, xs): the seed's Armos tables."""
    r = rng("armos")
    screens = [s for s, _ in ARMOS_FORMATION]
    xs = [ch[r.randrange(len(ch))] for _, ch in ARMOS_FORMATION]
    sw = ARMOS_SWAP[r.randrange(len(ARMOS_SWAP))]
    for t in (screens, xs):
        t[0], t[sw] = t[sw], t[0]
    return screens, xs


def apply_armos(rom, notes):
    if not ON:
        return
    assert list(rom[ARMOS_SCREENS_FILE:ARMOS_SCREENS_FILE + 7]) == [s for s, _ in ARMOS_FORMATION]
    screens, xs = armos()
    rom[ARMOS_SCREENS_FILE:ARMOS_SCREENS_FILE + 7] = bytes(screens)
    rom[ARMOS_X_FILE:ARMOS_X_FILE + 7] = bytes(xs)
    a = screens[0]
    c5 = 36
    assert rom[OW + 0x80 + c5] >> 2 == 0
    rom[OW + c5] = 0x43                             # exit X 4, outer palette 3, no Zora, no sea sound
    rom[OW + 0x280 + c5] = 0x03                     # both quests, exit row 3
    if a != c5:
        cave = rom[OW + 0x80 + a] >> 2
        assert cave and rom[OW + 0x280 + a] >> 6 == 0, (a, hex(rom[OW + 0x80 + a]), hex(rom[OW + 0x280 + a]))
        rom[OW + 0x80 + c5] = cave << 2 | 3
        rom[OW + 0x280 + a] |= 0xC0
    nm = lambda s: "ABCDEFGH"[s // 16] + str(s % 16 + 1)
    notes.append(f"1.0 Armos: the item on {nm(a)} (X {xs[0]}); stairs " + ", ".join(f"{nm(s)} X {x}" for s, x in
                                                                                  zip(screens[1:], xs[1:])))


# ---------------- step 4: fresh dungeons (owner 2026-11-28) ----------------
# lol_gen (1.0): the dungeons drawn fresh every seed (lol_genload.vseed); ZORA's room items, triforce room and
# level 9 Ganon / Zelda (her ways in opened by the Triforce of Power); an old man's choice in level 9. Here: one
# room with Ganon's room's layout and one with Zelda's, each in a random level 1-9 (not a shrine), once a game.
GANON_LAYOUT, ZELDA_LAYOUT = 0x28, 0x27


def decor(out, chosen):
    """chosen: per slot (levels 1-9, shrines) its (design, class, variant). One ordinary room each takes Ganon's room's
    layout (its item, if any, standing) and Zelda's (no item)."""
    import lol_gen as G
    r = rng("decor")
    said = []
    used = set()
    for lay, name in ((GANON_LAYOUT, "Ganon's"), (ZELDA_LAYOUT, "Zelda's")):
        for _ in range(50):
            lv = r.randint(1, 9)
            d, ci, vi = chosen[lv - 1]
            v = out[(d, ci)][vi]
            cells = v["cells"]
            pool = [c for c, x in sorted(cells.items()) if x["role"] == "room" and c not in used
                    and x["trigger"] in (G.T_NONE, G.T_ALL_DEAD, G.T_ALL_DEAD_ITEM) and not x["layout"] & 0x40
                    and (x["layout"] & 0x3F) not in G.CHUTE_SIDES and x["eclass"] in (1, 2)
                    and (x["item"] is None or x["item"] in (G.I_BOMBS, G.I_RUPEES, G.I_KEY)
                         or (lay == GANON_LAYOUT and x["item"] == G.I_MAP))
                    and (lay == ZELDA_LAYOUT or x["item"] is None
                         or G.spot_slots(lay, v["postab"], {t for t in range(4) if x["walls"][t] != G.WALL}))]
            if pool:
                break
        else:
            continue
        c = r.choice(pool)
        used.add(c)
        x = cells[c]
        x["layout"] = lay
        if lay == ZELDA_LAYOUT:
            x["item"], x["pos"] = None, 0
            if x["trigger"] == G.T_ALL_DEAD_ITEM:
                x["trigger"] = G.T_ALL_DEAD
        elif x["item"] is not None:
            sides = {t for t in range(4) if x["walls"][t] != G.WALL}
            x["pos"] = r.choice(G.spot_slots(lay, v["postab"], sides))
            if x["trigger"] == G.T_ALL_DEAD_ITEM:
                x["trigger"] = G.T_ALL_DEAD                 # (standing)
        said.append(f"{name} room's layout in level {lv} ({G.name(c)})")
    return "1.0 dungeons: " + ", ".join(said)


# ---------------- the 4-triforce cave (owner 2026-11-28) ----------------
# Its old man asks for 3, 4 or 5 triforces (the seed's pick); with that many, the cave's prize: the first item of the
# seed's rolled list (TRI4_ODDS) Link doesn't have (a candle upgrade: his next candle; the white sword without the
# wood sword: the wood sword); everything: a bomb upgrade, or at the most bombs an orange XP bag.
TRI4_ODDS = {"blue ring": 1, "white sword": 25, "bow": 20, "wand": 15, "red book": 4, "ladder": 10, "recorder": 10,
             "power bracelet": 5, "raft": 5, "candle upgrade": 5}
assert sum(TRI4_ODDS.values()) == 100
TRI4_ENTRIES = {"blue ring": [(0x12, RING, 1)], "white sword": [(0x01, SWORD, 1), (0x02, SWORD, 2)],
                "bow": [(0x0A, BOW, 1)], "wand": [(0x10, WAND, 1)], "red book": [(0x11, BOOK, 1)],
                "ladder": [(0x0D, LADDER, 1)], "recorder": [(0x05, RECORDER, 1)],
                "power bracelet": [(0x14, BRACELET, 1)], "raft": [(0x0C, RAFT, 1)],
                "candle upgrade": [(0x06, CANDLE, 1), (0x07, CANDLE, 2)]}


def tri4_count():
    return rng("4-triforce cave count").randint(3, 5)


def tri4_list():
    """The seed's rolled list (names)."""
    return roll(TRI4_ODDS, rng("4-triforce cave"))


def tri4_table():
    """(item, inventory byte, offered while below) in the rolled order, an upgrade's tiers in a row (the Upgrade
    mix's 1 in 20: the wand's place an upgrade's, UPGRADE_ENTRY)."""
    return [e for nm in tri4_list() for e in
            ([UPGRADE_ENTRY] if nm == "wand" and tri4_upgrade() else TRI4_ENTRIES[nm])]


def tri4_upgrade():
    """(the Upgrade mix) whether the seed's 4-triforce cave has an upgrade in the wand's place (1 in 20)."""
    return lol_fixed.UPMIX and rng("4-triforce cave upgrade").randrange(20) == 0


UPGRADE_ENTRY = (0xFE, 0x00, 0x01)      # (tri4_table: the upgrade's entry, lol_upgrades' ws far-calls lol_upmix's u4)


# ---------------- the 8-triforce cave (owner 2026-11-28) ----------------
# Its old man asks for 6, 7 or 8 triforces (the seed's pick); with that many, the first item of the seed's rolled list
# (TRI8_ODDS) Link doesn't have, an upgrade's next step (arrows: wood then silver; swords: wood, white, magical; books:
# red then blue; rings: blue then red); everything: a bomb upgrade, at the most bombs an orange XP bag. Upgrade mix: 1
# in 20 seeds a tier 3 upgrade in the book upgrade's place (picked once, the first Link may have; the next prize if
# he owns three upgrades).
TRI8_ODDS = {"arrow upgrade": 20, "magic key": 5, "book upgrade": 10, "ring upgrade": 5, "sword upgrade": 30, "bow": 30}
assert sum(TRI8_ODDS.values()) == 100
TRI8_ENTRIES = {"arrow upgrade": [(0x08, ARROWS, 1), (0x09, ARROWS, 2)], "magic key": [(0x0B, MAGIC_KEY, 1)],
                "book upgrade": [(0x11, BOOK, 1), (0x25, BOOK, 2)], "ring upgrade": [(0x12, RING, 1), (0x13, RING, 2)],
                "sword upgrade": [(0x01, SWORD, 1), (0x02, SWORD, 2), (0x03, SWORD, 3)], "bow": [(0x0A, BOW, 1)]}


def tri8_count():
    return rng("8-triforce cave count").randint(6, 8)


def tri8_list():
    return roll(TRI8_ODDS, rng("8-triforce cave"))


def tri8_upgrade():
    return lol_fixed.UPMIX and rng("8-triforce cave upgrade").randrange(20) == 0


def tri8_table():
    return [e for nm in tri8_list() for e in
            ([UPGRADE_ENTRY] if nm == "book upgrade" and tri8_upgrade() else TRI8_ENTRIES[nm])]

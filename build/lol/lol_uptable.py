"""Legend of Link v3.0 stage 5: the upgrades, as one table.

Every upgrade is a row: its name, where it's saved (address, bit), price, tier, weight in its tier's roll, the
condition for being offered, its picture (lol_bombup's drawing function and any half that is a game sprite) and its
palette (the vanilla item it's drawn as). Index order is the save order (the first 15 keep test12's bits).

Items: an upgrade is no longer its own item code. Six codes stand for picture slots: $2B-$2D the upgrades Link owns
(at most three: one per upgrade cave), $2E-$30 the wares of the upgrade cave he's in. RAM says which upgrade each
slot holds (WIX for the wares; owned ones are listed in order), and lol_pictures loads the slots' pictures.
Codes $31-$3E are free for new items.

Conditions: a list of rules, all of which must hold for the upgrade to be offered: ("ge", address, n) the byte is
n or more; ("lt", address, n) below n; ("ge_or_swordless", address, n) n or more, or swordless mode (lol_modes); ("notowned", name) Link doesn't own that upgrade; ("owned", name) he does; ("rank1",) only in the second upgrade cave Link enters; ("rank0",) only in the
first upgrade cave Link enters; ("anynz", a, b) either byte is nonzero. (Addresses: page $06, the inventory.)"""
import os

OWNED_CODES = (0x2B, 0x2C, 0x2D)
WARE_CODES = (0x2E, 0x2F, 0x30)
FIRST_CODE = 0x2B
# RAM (save RAM's spare bytes, rebuilt by every load: never saved meaning)
SCONV = 0x6080                          # 6: each slot's palette item (owned 0-2, wares 3-5)
WIX = 0x6086                            # 3: the upgrade each ware slot holds
OWN_N = 0x6089                          # how many owned slots are filled

UPGRADES, UP2, UP3 = 0x066B, 0x0673, 0x606A + 19
LL_VARIANT = os.environ.get("LL_VARIANT", "b")

UP4, UP5 = 0x607E, 0x607F              # the second batch's bits (save RAM; cleared for a new file by lol_af)
POTION, BOW, ARROWS, CANDLE, BOOMERANG, MAGIC_BOOMERANG = 0x065E, 0x065A, 0x0659, 0x065B, 0x0674, 0x0675
MAX_BOMBS, HEARTS = 0x067C, 0x066F
HAS_POTION = [("ge", POTION, 1)]
HAS_BOW = [("ge", BOW, 1)]
HAS_SWORD = [("ge", 0x0657, 1)]             # (lol_modes: sword-only upgrades need a sword)
NO_SNUB = [("notowned", "heart snubber")]   # (sword upgrades leave the pool with the heart snubber)
BOMB_UPGRADE = [("ge", MAX_BOMBS, 12)]  # at least one bomb upgrade (8 -> 12)
WAND = 0x065F
RECORDER = 0x065C
TRIFORCE = 0x0671
RING = 0x0662
LINES = 0x6012                          # 8 (owner 2026-11-24): the upgrade caves' lines - 2 bits per place in a
                                        # tier's line (tier_items: 0 not taken, 1-3 the cave), the caves' "bought
                                        # here" bits 4-6 of the last byte (file 3's name; cleared for a new file)
UP6 = 0x600E                            # the third batch's bits (file 2's name, as lol_stats' clock; cleared for a
                                        # new file by lol_saveblock)
FOOD = 0x065D                           # the bait
RARE = 3                                # relative weights: 13 a normal upgrade, 3 a super rare one
# name, (address, bit), price, tier, relative weight, conditions (all must hold), picture, fixed halves {x: tile},
# palette (the item drawn as: $1A red, $00 blue, $12 the blue ring's)
ROWS = [
    ("beams",           (UPGRADES, 0x01),  50, 0, 13, HAS_SWORD + NO_SNUB, "_beam_sword", {}, 0x00),
    ("boomstick",       (UPGRADES, 0x02), 100, 1, 13, [("ge", WAND, 1), ("notowned", "divining rod")], "_boomstick",
     {0: 0x4A}, 0x00),
    ("regen",           (UPGRADES, 0x04), 125, 1, 13, [("notowned", "zombie link")], "_regen", {}, 0x1A),
    ("skull ring",      (UPGRADES, 0x10),  50, 0, 13, [], "_skull_ring", {}, 0x12),
    ("sword mastery",   (UPGRADES, 0x08), 100, 1, 13, HAS_SWORD + NO_SNUB, "_sword_plus", {0: 0x20}, 0x00),
    ("fairy bottle",    (UPGRADES, 0x40), 150, 2, 13, [], "_fairy_bottle", {0: 0x40, 8: 0x50}, 0x00),   # (owned: the
                        # bottle, $40; the fairy in it is $20, set too when bought: lol_upgrades' utbits)
    ("blue like likes", (UPGRADES, 0x80),  50, 0, 13, [], "_likelike_bomb", {}, 0x1A if LL_VARIANT == "a" else 0x00),
    ("rupee speed",     (UP2, 0x40),      100, 1, 13, [], "_rupee_speed", {}, 0x00),
    ("ganon boomerang", (UP2, 0x80),      150, 2, 13, [], "_ganon_boomerang", {}, 0x00),
    ("critter crusher", (UP3, 0x01),       50, 0, 13, [], "_critter_crusher", {}, 0x1A),
    ("statue jammer",   (UP3, 0x02),      100, 1, 13, [], "_statue_jammer", {}, 0x00),
    ("bombsmith",       (UP3, 0x04),      150, 2, 13, BOMB_UPGRADE, "_bombsmith", {}, 0x00),
    ("potion pouch",    (UP3, 0x08),       50, 0, 12, HAS_POTION, "_pouch", {}, 0x00),
    ("bat potion",      (UP3, 0x10),      125, 1, 12, HAS_POTION + [("notowned", "brain potion")], "_bat_potion", {},
     0x1A),
    ("bow mastery",     (UP3, 0x20),      150, 2, 12, HAS_BOW + [("ge", ARROWS, 1)], "_bow_mastery", {0: 0x2A}, 0x00),
    # the second batch (test14)
    ("ganon visible",   (UP4, 0x01),       25, 0, RARE, [], "_ganon_visible", {}, 0x1A),
    ("slow fireballs",  (UP4, 0x02),       50, 0, 13, [], "_slow_fireballs", {}, 0x1A),
    ("key hoarder",     (UP4, 0x04),       50, 0, 13, [], "_key_hoarder", {}, 0x1A),
    ("unlimited candle", (UP4, 0x08),      50, 0, 13, [("ge", CANDLE, 1), ("lt", CANDLE, 2)], "_unlimited_candle", {},
     0x00),
    ("misers bow",      (UP4, 0x10),       50, 0, 13, HAS_BOW + [("notowned", "bow of greed")], "_misers_bow", {0: 0x2A}, 0x00),
    ("refilling bag",   (UP4, 0x20),       50, 0, 13, [("ge_or_swordless", MAX_BOMBS, 12)], "_refill_bag", {}, 0x00),
    ("map master",      (UP4, 0x40),       50, 0, 13, [], "_map_master", {}, 0x1A),
    ("spider bomber",   (UP4, 0x80),       75, 1, 13, BOMB_UPGRADE, "_spider_bomber", {}, 0x00),
    ("bow of greed",    (UP5, 0x01),      100, 1, 13, HAS_BOW + [("notowned", "misers bow")], "_bow_of_greed", {0: 0x2A}, 0x00),
    ("holy fire",       (UP5, 0x02),      100, 1, 13, [("ge", CANDLE, 1)], "_holy_fire", {}, 0x1A),
    ("xp boost",        (UP5, 0x04),      100, 1, RARE, [("lt", HEARTS, 0x30)], "_xp_boost", {}, 0x1A),
    ("ghost hunter",    (UP5, 0x08),      125, 1, 13, [], "_ghost_hunter", {}, 0x00),
    ("healerang",       (UP5, 0x10),      150, 2, 13, [("anynz", BOOMERANG, MAGIC_BOOMERANG)], "_healerang", {0: 0x36}, 0x1A),
    ("shield breaker",  (UP5, 0x20),      150, 2, 13, [], "_shield_breaker", {}, 0x00),
    ("membership card", (UP5, 0x40),      200, 2, 13, [("rank0",)], "_membership_card", {}, 0x1A),
    # v2.02 web: needs the bait; it turns blue, lures gibdos too, drains moblins / goriyas / octoroks touching it
    # and heals gibdos (lol_newups). (Its bit, UP5's $80, is read with BIT: bit 7.)
    ("poison bait",     (UP5, 0x80),       50, 0, 13, [("ge", FOOD, 1)], "_poison_bait", {}, 0x00),
    # owner 2026-11-24 (was "attack over heart"): only in the second upgrade cave Link finds, at 3 containers or fewer
    # (lol_snubber: 3 hearts for good, the level counted on in the containers' nibble, the wood sword's attack half
    # the level, swords out of every pool). Its bit: UP3's $40.
    ("heart snubber",   (UP3, 0x40),      200, 2, 13, HAS_SWORD + [("lt", HEARTS, 0x30), ("rank1",)],
     "_heart_snubber", {}, 0x1A),
    # owner 2026-11-24 (lol_rodsong): the wand becomes a stick (Link's colors), stabs only (no shot) for 1 less, and
    # every level's and shrine's compass comes with it; never with the boomstick. Its bit: UP3's $80.
    ("divining rod",    (UP3, 0x80),      100, 1, 13, [("ge", WAND, 1), ("notowned", "boomstick")], "_divining_rod",
     {}, 0x0A),
    # owner 2026-11-24 (lol_rodsong): the recorder's whirlwind (with or without triforces) drops Link on a random
    # screen, one of those safe to land on (lol_entrances' SAFE_Y). Its bit: UP6's $01.
    ("song of chaos",   (UP6, 0x01),       25, 0, 13, [("ge", RECORDER, 1), ("ge", TRIFORCE, 1)], "_song_of_chaos",
     {}, 0x05),                         # (owner: with a triforce piece, as the whirlwind needs)
    # owner 2026-11-24 (lol_zombie; was "glass cannon"): only at exactly 3 containers, with no ring, never with regen
    ("zombie link",     (UP6, 0x02),       75, 1, RARE, [("ge", HEARTS, 0x20), ("lt", HEARTS, 0x30), ("lt", RING, 1),
                                                         ("notowned", "regen")], "_zombie", {}, 0x0A),
    # owner 2026-11-24 (lol_zombie): with Zombie Link and a potion; never with the bat potion
    ("brain potion",    (UP6, 0x04),       50, 0, 13, [("owned", "zombie link"), ("ge", POTION, 1),
                                                       ("notowned", "bat potion")], "_brain", {}, 0x1A),
    # owner 2026-11-24 (lol_xray): a dungeon's secret walls show (bombable grey, walk-through orange); always in the
    # pool of a set whose dungeons can have walk-through walls (WALK_SET); 2026-11-25: tier 3 / 200, regen's (regen
    # took its tier 2 / 125)
    ("x-ray glasses",   (UP6, 0x08),      200, 2, 13, [], "_xray_glasses", {}, 0x1A),
    # owner 2026-11-25: boomerang mastery (75, tier 2; with either boomerang): boomerang hits +1 damage ($10;
    # lol_upgrades' sword hook, weapon slot $0F)
    ("boomerang mastery", (UP6, 0x10),     75, 1, 13, [("anynz", BOOMERANG, MAGIC_BOOMERANG)], "_boomerang_mastery",
     {0: 0x36}, 0x1A),
    # owner 2026-11-25: bookworm (200, tier 3; only from level 8, 8+ containers): the red book +2, the blue +4
    # (lol_books' bonus doubled); until Link has a book, one of each dungeon old man's choices is the red book and
    # every shop sells it for 25 (lol_odds.wrappers' book)
    ("bookworm",        (UP6, 0x20),      200, 2, 13, [("ge", HEARTS, 0x70)], "_bookworm", {}, 0x1A),
    # owner 2026-11-25: heavy bracelet (75, tier 2; with the power bracelet): moves G6's and A10's new rocks
    # (lol_heavy), whose caves roll once each: the Thorn Bracelet (UP6 $80, not a row: it takes this one's picture),
    # a secret shop, 100 rupees, a secret-mode hint or a free ring / book / sword
    ("heavy bracelet",  (UP6, 0x40),       75, 1, 13, [("ge", 0x0665, 1)], "_heavy_bracelet", {}, 0x00),
]
THORN = (UP6, 0x80)                     # (owner 2026-11-25) the Thorn Bracelet (lol_heavy)
N_UP = len(ROWS)
NAME, SAVE, PRICE, TIER, WEIGHT, COND, PIC, FIXED, PAL = range(9)
POWER_ON = 9                            # the first nine have pictures in the power-on tiles (the title's legend)
assert all(r[TIER] == (0 if r[PRICE] <= 50 else 1 if r[PRICE] <= 125 else 2) for r in ROWS)
# each tier's roll walks its upgrades in this order: test12's order first, new ones after
ROLL_ORDER = [0, 3, 6, 9, 12, 4, 7, 1, 10, 13, 2, 5, 8, 11, 14] + list(range(15, N_UP))
assert sorted(ROLL_ORDER) == list(range(N_UP))

# The seed's pool (owner, 2026-11-24): the shops offer only the upgrades this seed picked, up to PER_TIER of each
# tier; first GUARANTEED of each tier's unconditional ones (always offerable: no conditions), then the rest of the
# tier at random. The same seed (LOL_SET_SEED, else LOL_SEED) picks the same pool. Unpicked upgrades are never offered,
# and their hint quotes are left out (lol_genload.hint_lines); the title still lists every upgrade (owner).
PER_TIER = (10, 10, 10)
GUARANTEED = 3


def _pool():
    import os
    import random
    seed = int(os.environ.get("LOL_SET_SEED") or os.environ.get("LOL_SEED") or 0)
    rng = random.Random(seed * 7919 + 0x7550)
    out = set()
    for t in range(3):
        tier = [k for k in range(N_UP) if ROWS[k][TIER] == t]
        free = [k for k in tier if not ROWS[k][COND]]
        got = rng.sample(free, min(GUARANTEED, len(free)))
        rest = [k for k in tier if k not in got]
        got += rng.sample(rest, max(0, min(PER_TIER[t], len(tier)) - len(got)))
        xr = next(k for k, r in enumerate(ROWS) if r[NAME] == "x-ray glasses")
        if xr in tier and xr not in got and walk_set():     # (owner: always there with walk-through walls)
            got[rng.randrange(GUARANTEED, len(got))] = xr
        out |= set(got)
    return out


def walk_set():
    """True if the page's dungeon set has designs that can get walk-through walls (a quest's levels with a share of
    them: 2Q, 3Q, 4Q; in Mixed and Random when one is dealt). LoL's designs and the shapes never get them."""
    import lol_genload
    cs = lol_genload.custom_set()
    return cs is not None and any(r[2] > 0 for g in cs.values() for r in g.get("rules", {}).values())


POOL = _pool()


def _lines():
    """Each tier's line (owner 2026-11-24): the seed's pool shuffled, weighted (a rare one tends to come later). The
    upgrade caves take from the front (lol_upgrades); the first 3 of each are hinted from the start (lol_genload)."""
    import os
    import random
    seed = int(os.environ.get("LOL_SET_SEED") or os.environ.get("LOL_SEED") or 0)
    rng = random.Random(seed * 1000003 + 0x11E5)
    out = []
    for t in range(3):
        tier = [k for k in ROLL_ORDER if ROWS[k][TIER] == t and k in POOL]
        out.append(sorted(tier, key=lambda k: -rng.random() ** (1 / ROWS[k][WEIGHT])))
    return out


TIERS = _lines()


def in_pool(name):
    return index(name) in POOL


def weights256(tier):
    """The tier's relative weights scaled to whole numbers summing to 256 (the roll is a full byte)."""
    rel = [ROWS[k][WEIGHT] for k in tier]
    raw = [w * 256 / sum(rel) for w in rel]
    out = [int(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)[:256 - sum(out)]:
        out[i] += 1
    assert sum(out) == 256 and min(out) >= 1
    return out


def index(name):
    return next(k for k, r in enumerate(ROWS) if r[NAME] == name)


def bit(name):
    return ROWS[index(name)][SAVE]

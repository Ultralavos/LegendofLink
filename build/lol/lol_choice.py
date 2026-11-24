"""Legend of Link: the old man's choice of two in dungeons 1-9 (first quest).

One hint old man per level becomes a take-any old man (person $6B, cave 1: his items vanish once one is taken and the
room's item bit remembers it) offering two items. They are picked from the items Link may get at his heart
containers that he doesn't already have (CHOICES); which two depends on the level and the containers, so the offer is
fixed for a given visit and changes as Link grows. With nothing to offer he gives a red potion.

The level's entry in InitUnderworldPerson's jump table (bank 1 $8A07 + 2 * level) goes to a stub here: in the first
quest, in the chosen room, it runs the choice; otherwise the vanilla entry.
"""
from lol_af import Asm, BANK, place

# One old man per level (the hint old men; rooms by the dungeon grid, row letter + column)
CHOICE_ROOMS = {1: "E2", 2: "B16", 3: "C12", 4: "A1", 5: "B6", 6: "G11", 7: "F12", 8: "D12", 9: "G7"}

HEARTS = 0x066F
SWORD, ARROWS, BOW, CANDLE, RECORDER, WAND, RAFT, BOOK, RING, LADDER, MAGIC_KEY, BRACELET = (
    0x0657, 0x0659, 0x065A, 0x065B, 0x065C, 0x065F, 0x0660, 0x0661, 0x0662, 0x0663, 0x0664, 0x0665)
BOOMERANG, MAGIC_BOOMERANG, SHIELD = 0x0674, 0x0675, 0x0676
MAX_BOMBS, TRIFORCE = 0x067C, 0x0671
ANY = (SWORD, 0x00, 0x00)       # a condition that always holds (hi 0: no upper bound)

# Lists in priority order: the first items Link may get are offered. (name, item code, fewest containers,
# (addr, lo, hi), (addr, lo, hi)[, most containers]): offered while lo <= [addr] < hi (hi 0: no upper bound) for
# both. Progressive: the second tier (magical sword, red candle, silver arrows, blue book, magical boomerang, red ring)
# only once Link has the first.
CHOICES = [    # (the user's v2.02 sheet: odds/old_men.csv)
    ("boomerang", 0x1D, 1, (BOOMERANG, 0, 1), (MAGIC_BOOMERANG, 0, 1)),
    ("blue candle", 0x06, 1, (CANDLE, 0, 1), ANY),
    ("raft", 0x0C, 1, (RAFT, 0, 1), ANY),
    ("recorder", 0x05, 1, (RECORDER, 0, 1), ANY),
    ("power bracelet", 0x14, 1, (BRACELET, 0, 1), ANY),
    ("ladder", 0x0D, 1, (LADDER, 0, 1), ANY),
    ("wood arrows", 0x08, 1, (ARROWS, 0, 1), ANY),
    ("bomb upgrade", 0x24, 1, (MAX_BOMBS, 0, 20), ANY),
    ("white sword", 0x02, 1, (SWORD, 0, 2), ANY),
    ("wand", 0x10, 1, (WAND, 0, 1), ANY),
    ("bow", 0x0A, 1, (BOW, 0, 1), ANY),
    ("silver arrows", 0x09, 1, (ARROWS, 1, 2), (BOW, 1, 0)),
    ("magical shield", 0x1C, 1, (SHIELD, 0, 1), ANY),
    ("red candle", 0x07, 1, (CANDLE, 1, 2), ANY),
    ("magical sword", 0x03, 1, (SWORD, 2, 3), ANY),
]

TAKE_ANY = 0x6B
INIT_CAVE = 0x85D0
WARES, PRICES = 0x6A81, 0x6ABD          # cave 1's three items and prices (RAM), as InitCave reads them
TABLE = 0x4A17                          # file offset of InitUnderworldPerson's jump table (entry = level)
FREE = 0xB770                           # bank 1's free run (after $B751-$B76F, which runs from WRAM)
SAVE_X = 0x0174                         # scratch (RAM: the stack page's unused bottom)
T0, T1, CNT, K = 0x00, 0x01, 0x02, 0x03  # zero page scratch (before InitCave)


def screen(name):
    return "ABCDEFGH".index(name[0]) * 16 + int(name[1:]) - 1


BADGES = 0x0673                         # S / D / X badges (2 bits each): + that many containers for the minimums
EFF = 0x0172                            # scratch (RAM, the stack page's unused bottom)


def picker(a: Asm, items: list, p: str, badge_shift: int = None) -> None:
    """Emit {p}elig (Y = entry: carry set if Link may get it), {p}count (CNT = how many may) and {p}nth (A = the
    K-th such item in priority order, or $3F; Y = its entry) with their tables (stored last-first: nth scans down)."""
    items = list(reversed(items))
    a.label(p + "elig")
    if badge_shift is None:
        a.b(0xA9, 0x00)
    else:
        a.abs(0xAD, BADGES).b(*([0x4A] * badge_shift), 0x29, 0x03)              # this list's badges
    a.abs(0x8D, EFF)
    a.abs(0xAD, HEARTS).b(0x4A, 0x4A, 0x4A, 0x4A).abs(0xD9, p + "t_hcx").br(0xB0, p + "e_no")  # containers - 1 < most
    a.b(0x18).abs(0x6D, EFF).abs(0xD9, p + "t_hc").br(0x90, p + "e_no")        # + badges >= min - 1
    for k in (0, 1):
        a.abs(0xBE, f"{p}t_a{k}")                                               # LDX addr low,Y (all in $06xx)
        a.abs(0xBD, 0x0600).abs(0xD9, f"{p}t_lo{k}").br(0x90, p + "e_no")       # LDA $0600,X / CMP lo,Y / BCC no
        a.abs(0xB9, f"{p}t_hi{k}").br(0xF0, f"{p}e_ok{k}")                      # hi 0: no upper bound
        a.abs(0xBD, 0x0600).abs(0xD9, f"{p}t_hi{k}").br(0xB0, p + "e_no")       # CMP hi,Y / BCS no
        a.label(f"{p}e_ok{k}")
    a.b(0x38, 0x60)                                                             # SEC / RTS
    a.label(p + "e_no").b(0x18, 0x60)
    a.label(p + "count").b(0xA9, 0x00, 0x85, CNT, 0xA0, len(items) - 1)
    a.label(p + "c_lp").abs(0x20, p + "elig").br(0x90, p + "c_nx").b(0xE6, CNT)
    a.label(p + "c_nx").b(0x88).br(0x10, p + "c_lp").b(0x60)
    a.label(p + "nth").b(0xA0, len(items) - 1)
    a.label(p + "n_lp").abs(0x20, p + "elig").br(0x90, p + "n_nx")
    a.b(0xA5, K).br(0xF0, p + "n_hit").b(0xC6, K)
    a.label(p + "n_nx").b(0x88).br(0x10, p + "n_lp").b(0xA9, 0x3F, 0x60)
    a.label(p + "n_hit").abs(0xB9, p + "t_item").b(0x60)
    a.label(p + "t_item").b(*[c[1] for c in items])
    a.label(p + "t_hc").b(*[c[2] - 1 for c in items])
    a.label(p + "t_hcx").b(*[(c[5] if len(c) > 5 else 16) for c in items])
    for k in (0, 1):
        a.label(f"{p}t_a{k}").b(*[c[3 + k][0] & 0xFF for c in items])
        a.label(f"{p}t_lo{k}").b(*[c[3 + k][1] for c in items])
        a.label(f"{p}t_hi{k}").b(*[c[3 + k][2] for c in items])


def apply(rom: bytearray, notes: list) -> None:
    a = Asm(FREE)
    vanilla = {lv: rom[TABLE + 2 * lv] | rom[TABLE + 2 * lv + 1] << 8 for lv in CHOICE_ROOMS}
    from lol_dungeons import CHOICE_ROOMS_2Q            # A-F's (by their second-quest level)
    for lv, name in CHOICE_ROOMS.items():
        q2 = CHOICE_ROOMS_2Q.get(lv)
        a.label(f"lv{lv}").b(0xA4, 0x16).abs(0xB9, 0x062D).br(0xD0, f"q{lv}" if q2 else f"v{lv}")   # which quest
        a.b(0xA5, 0xEB, 0xC9, screen(name)).br(0xD0, f"v{lv}")                    # the room
        a.label(f"ok{lv}").b(0xA9, lv).abs(0x4C, "choice")
        if q2:
            a.label(f"q{lv}").b(0xA5, 0xEB, 0xC9, screen(q2)).br(0xF0, f"ok{lv}")
        a.label(f"v{lv}").abs(0x4C, vanilla[lv])

    import lol_odds
    lol_odds.register(0, "old_men", CHOICES)

    def old_store(a):                   # the save index: Levels 1-9 0-8, the second quest's 4 (E) 9, 6 (F) 10
        a.b(0xA4, 0x16).abs(0xB9, 0x062D).br(0xD0, "os_q2").b(0xA5, T0, 0x38, 0xE9, 0x01).br(0xB0, "os_st")
        a.label("os_q2").b(0xA5, T0, 0xC9, 0x04).br(0xF0, "os_e").b(0xA9, 0x0A).br(0xD0, "os_st")
        a.label("os_e").b(0xA9, 0x09)
        a.label("os_st").abs(0x8D, lol_odds.CTX)
    lol_odds.wrappers(a, 0, CHOICES, "", 1, old_store, 2)
    # the choice: A = level
    a.label("choice").b(0x85, T0).abs(0x8E, SAVE_X)                            # (X: the caller's, kept)
    a.abs(0x20, "count").b(0xA5, CNT).br(0xD0, "ch_some")
    a.b(0xA9, 0x20, 0x48, 0xA9, 0x3F).abs(0x4C, "ch_one")                     # nothing left: a red potion
    a.label("ch_some").b(0xA9, 0x00, 0x85, K).abs(0x20, "nth").b(0x48)        # the first (pushed)
    a.b(0xA9, 0x3F).b(0xA6, CNT, 0xCA).br(0xF0, "ch_one")                       # only one: no second item
    a.b(0xA9, 0x01, 0x85, K).abs(0x20, "nth")                                   # the second
    a.label("ch_one").b(0x09, 0x40, 0x85, T1)                                   # 'show items' bit
    a.b(0x68, 0x85, T0)                                                         # first item
    a.b(0xA9, TAKE_ANY).abs(0x8D, 0x0350)                                       # the take-any person
    # save cave 1's wares / prices, put ours (no prices), InitCave, put them back
    a.b(0xA2, 0x02).label("sv").abs(0xBD, WARES).b(0x48).abs(0xBD, PRICES).b(0x48)
    a.b(0xA9, 0x00).abs(0x9D, PRICES).b(0xCA).br(0x10, "sv")
    a.b(0xA5, T0).abs(0x8D, WARES).b(0xA9, 0x3F).abs(0x8D, WARES + 1).b(0xA5, T1).abs(0x8D, WARES + 2)
    a.abs(0xAE, SAVE_X).abs(0x20, INIT_CAVE)
    a.b(0xA2, 0x00).label("rs").b(0x68).abs(0x9D, PRICES).b(0x68).abs(0x9D, WARES).b(0xE8, 0xE0, 0x03)
    a.br(0xD0, "rs").abs(0xAE, SAVE_X).b(0x60)

    a.label("vtab_lo").b(*[0] + [vanilla.get(l, 0) & 0xFF for l in range(1, 10)])
    a.label("vtab_hi").b(*[0] + [vanilla.get(l, 0) >> 8 for l in range(1, 10)])
    code = bytearray(a.bytes())
    place(rom, 1, FREE, bytes(code))
    for lv in CHOICE_ROOMS:
        t = a.labels[f"lv{lv}"]
        rom[TABLE + 2 * lv:TABLE + 2 * lv + 2] = bytes([t & 0xFF, t >> 8])
    import lol_entrances
    if lol_entrances.GEN:               # a generated dungeon: the old man's room is lol_genload's GEN_CHOICE
        from lol_genload import CUR_GEN, GEN_CHOICE
        L = a.labels
        gch = Asm(0x9EF0)
        gch.label("gen_ch").abs(0xAD, CUR_GEN).br(0x30, "gc_st")
        gch.b(0xA5, 0xEB).abs(0xCD, GEN_CHOICE).br(0xD0, "gc_van").b(0xA5, 0x10).abs(0x4C, L["choice"])
        gch.label("gc_van").b(0xA4, 0x10).abs(0xB9, L["vtab_lo"]).b(0x85, T1).abs(0xB9, L["vtab_hi"]).b(0x85, T1 + 1)
        gch.b(0x6C, T1, 0x00)
        gch.label("gc_st").b(0xA4, 0x10).abs(0xB9, "ltab_lo").b(0x85, T1).abs(0xB9, "ltab_hi").b(0x85, T1 + 1)
        gch.b(0x6C, T1, 0x00)
        gch.label("ltab_lo").b(0, *[L[f"lv{lv}"] & 0xFF for lv in range(1, 10)])
        gch.label("ltab_hi").b(0, *[L[f"lv{lv}"] >> 8 for lv in range(1, 10)])
        place(rom, 1, 0x9EF0, gch.bytes())
        g = gch.labels["gen_ch"]
        for lv in CHOICE_ROOMS:
            rom[TABLE + 2 * lv:TABLE + 2 * lv + 2] = bytes([g & 0xFF, g >> 8])
    notes.append("choices: " + ", ".join(f"L{lv} {n}" for lv, n in CHOICE_ROOMS.items()) + f" ({len(code)} bytes)")
    apply_shops(rom, notes, FREE + len(code))


# The A-F rewards in place of the triforce: one item picked the same way (by the letter and the containers)
REWARDS = [    # shrine prizes (the user's v2.02 sheet: odds/rewards.csv)
    ("blue candle", 0x06, 1, (CANDLE, 0, 1), ANY),
    ("bomb upgrade", 0x24, 1, (MAX_BOMBS, 0, 20), ANY),
    ("bow", 0x0A, 1, (BOW, 0, 1), ANY),
    ("white sword", 0x02, 1, (SWORD, 0, 2), ANY),
    ("wand", 0x10, 1, (WAND, 0, 1), ANY),
    ("blue ring", 0x12, 1, (RING, 0, 1), ANY),
    ("red book", 0x11, 1, (BOOK, 0, 1), ANY),
    ("red candle", 0x07, 1, (CANDLE, 1, 2), ANY),
    ("red ring", 0x13, 1, (RING, 1, 2), ANY),
    ("blue book", 0x25, 1, (BOOK, 1, 2), ANY),
    ("magical sword", 0x03, 1, (SWORD, 2, 3), ANY),
    ("magical shield", 0x1C, 1, (SHIELD, 0, 1), ANY),
]
# First-quest rooms (level, room, item) with items the room tables can't hold (above $1F): the old boomerang rooms
# give the orange XP potion, the item cellars the badges, the blue XP potion and Level 9's red potion
SUBS = [(1, "E5", 0x29), (2, "E16", 0x29),
        (1, "H16", 0x28), (3, "A16", 0x28), (4, "G1", 0x27), (5, "A5", 0x2A), (6, "H6", 0x26),
        (7, "E11", 0x27), (8, "A16", 0x27), (8, "G16", 0x26), (9, "A1", 0x20), (9, "E16", 0x2A)]
REWARD_NONE = 0x20                      # nothing left to give: a red potion
REWARD_HOOK = 0xB84C                    # bank 5: the room item's AND #$1F / CMP #$03 (then STA RoomItem $AB)
REWARD_FREE = 0xB8A0                    # bank 5's free run (PRG1)
INSIDE = 0x0678
REWARD_ROOM = 0x0170                    # $80 | the room whose item is A-F's reward (taking it leaves the dungeon)


def apply_rewards(rom: bytearray, notes: list) -> None:
    from lol_af import patch
    a = Asm(REWARD_FREE)
    # first: the first quest's rooms whose item is one the room tables can't hold (SUBS)
    a.label("reward").b(0x29, 0x1F, 0x48, 0x98, 0x48)                          # item, Y kept
    import lol_entrances
    if lol_entrances.GEN:               # a generated dungeon: its cellar items (lol_genload's RAM table) instead
        from lol_genload import CUR_GEN, SUB_RM, SUB_IT
        a.abs(0xAD, CUR_GEN).br(0x30, "g_static").b(0xA0, 0x01)
        a.label("g_lp").abs(0xB9, SUB_RM).b(0xC5, 0xEB).br(0xD0, "g_nx")
        a.abs(0xB9, SUB_IT).abs(0x8D, SAVE_X).b(0x68, 0xA8, 0x68).abs(0xAD, SAVE_X).abs(0x4C, "r_cmp")
        a.label("g_nx").b(0x88).br(0x10, "g_lp").abs(0x4C, "s_none")
        a.label("g_static")
    a.b(0xA4, 0x16).abs(0xB9, 0x062D).br(0xD0, "s_none").b(0xA0, len(SUBS) - 1)
    a.label("s_lp").abs(0xB9, "sub_lv").b(0xC5, 0x10).br(0xD0, "s_nx")
    a.abs(0xB9, "sub_rm").b(0xC5, 0xEB).br(0xD0, "s_nx")
    a.abs(0xB9, "sub_it").abs(0x8D, SAVE_X).b(0x68, 0xA8, 0x68).abs(0xAD, SAVE_X).abs(0x4C, "r_cmp")
    a.label("s_nx").b(0x88).br(0x10, "s_lp")
    a.label("s_none").b(0x68, 0xA8, 0x68)
    a.b(0xC9, 0x1B).br(0xD0, "r_cmp")                                           # the triforce?
    a.abs(0xAD, INSIDE).br(0xF0, "r_tri")                                       # in A-F only
    a.b(0x8A, 0x48, 0x98, 0x48)                                                 # keep X, Y
    for z in (T0, T1, CNT, K):
        a.b(0xA5, z, 0x48)                                                      # and the scratch bytes
    a.b(0xA5, 0xEB, 0x09, 0x80).abs(0x8D, REWARD_ROOM)                         # (the room, for TakeItem)
    a.abs(0x20, "r_count").b(0xA5, CNT).br(0xF0, "r_none")
    a.b(0xA9, 0x00, 0x85, K).abs(0x20, "r_nth").br(0xD0, "r_have")             # the first (an item is never 0)
    a.label("r_none").b(0xA9, REWARD_NONE)
    a.label("r_have").abs(0x8D, SAVE_X)
    for z in (K, CNT, T1, T0):
        a.b(0x68, 0x85, z)
    a.b(0x68, 0xA8, 0x68, 0xAA).abs(0xAD, SAVE_X).br(0xD0, "r_cmp")
    a.label("r_tri").b(0xA9, 0x1B)
    a.label("r_cmp").b(0xC9, 0x03, 0x60)
    import lol_odds
    from lol_af import AF_LEVELS
    lol_odds.register(1, "rewards", REWARDS)

    def rew_store(a):                   # the save index: 11 + the letter (A-F)
        a.b(0xA4, 0x10).abs(0xB9, "r_letter").abs(0x8D, lol_odds.CTX)
    lol_odds.wrappers(a, 1, REWARDS, "r_", 5, rew_store, 1)
    a.label("r_letter").b(0, *[11 + AF_LEVELS.index(lv) for lv in range(1, 7)])
    a.label("sub_lv").b(*[s_[0] for s_ in SUBS])
    a.label("sub_rm").b(*[screen(s_[1]) for s_ in SUBS])
    a.label("sub_it").b(*[s_[2] for s_ in SUBS])
    code = a.bytes()
    place(rom, 5, REWARD_FREE, code)
    patch(rom, 5, REWARD_HOOK, bytes([0x29, 0x1F, 0xC9, 0x03]), bytes([0x20, REWARD_FREE & 0xFF, REWARD_FREE >> 8]))
    # The triforce's exit (mode $12, bank 5 $A850: LDA #$1B / STA HeldItem) holds up the room's item ($AB) instead:
    # the triforce in the first quest's levels, the reward in A-F
    patch(rom, 5, 0xA850, bytes([0xA9, 0x1B, 0x8D, 0x05, 0x05]), bytes([0xA5, 0xAB, 0x8D, 0x05, 0x05]))
    notes.append(f"A-F rewards ({len(code)} bytes)")


# The shops (A-D and the potion shop): the first three items Link may buy; one purchase and the shop is gone for
# good (InitCave checks their taken flag too).
POTION, BAIT, KEYS, BOMBS = 0x065E, 0x065D, 0x066E, 0x0658
SHOP_ITEMS = [   # (name, item, fewest containers, cond, cond, most containers, price) - odds/shops.csv
    ("key", 0x19, 1, (KEYS, 0, 6), (MAGIC_KEY, 0, 1), 16, 20),         # not with the magical key or 6+ keys
    ("bombs", 0x00, 1, (BOMBS, 0, 0xFE), ANY, 16, 5),                  # not with a full bag ($FE: < max bombs)
    ("bait", 0x04, 1, (BAIT, 0, 1), ANY, 16, 20),
    ("blue candle", 0x06, 1, (CANDLE, 0, 1), ANY, 16, 50),
    ("boomerang", 0x1D, 1, (BOOMERANG, 0, 1), (MAGIC_BOOMERANG, 0, 1), 16, 50),
    ("wood arrows", 0x08, 1, (ARROWS, 0, 1), ANY, 16, 50),
    ("pity heart", 0x22, 1, ANY, ANY, 16, 10),
    ("raft", 0x0C, 1, (RAFT, 0, 1), ANY, 16, 50),
    ("recorder", 0x05, 1, (RECORDER, 0, 1), ANY, 16, 50),
    ("power bracelet", 0x14, 1, (BRACELET, 0, 1), ANY, 16, 50),
    ("bow", 0x0A, 1, (BOW, 0, 1), ANY, 16, 50),
    ("ladder", 0x0D, 1, (LADDER, 0, 1), ANY, 16, 50),
    ("red candle", 0x07, 1, (CANDLE, 1, 2), ANY, 16, 50),
    ("magical boomerang", 0x1E, 1, (MAGIC_BOOMERANG, 0, 1), (BOOMERANG, 1, 0), 16, 50),
    ("magical shield", 0x1C, 1, (SHIELD, 0, 1), ANY, 16, 50),
]
SHOP_TYPES = (0x74, 0x77, 0x78, 0x79, 0x7A)      # the potion shop, shops A-D (person $6A + cave index)
CAVE_WARES, CAVE_PRICES = 0x6A7E, 0x6ABA
J, BASE = 0x04, 0x05


def apply_shops(rom: bytearray, notes: list, cpu: int) -> int:
    from lol_af import patch
    a = Asm(cpu)
    # InitCave's taken check: also the shops
    a.label("taken").abs(0xAD, 0x0350)
    for t in (0x72, 0x71):
        a.b(0xC9, t).br(0xF0, "tk_chk")
    a.b(0xC9, 0x7B).br(0xB0, "tk_chk").b(0xC9, 0x74).br(0xF0, "tk_chk").b(0xC9, 0x75).br(0xB0, "tk_chk")   # $75-$7A: the upgrade caves and shops A-D
    a.b(0xC9, 0x6E).br(0xB0, "tk_skip")
    a.label("tk_chk").b(0x18, 0x60)
    a.label("tk_skip").b(0x38, 0x60)
    # InitCave's wares: a shop's are picked here
    a.label("fill").abs(0xAD, 0x0350).b(0xC9, 0x74).br(0xF0, "f_go")
    a.b(0xC9, 0x77).br(0x90, "f_out").b(0xC9, 0x7B).br(0xB0, "f_out")
    a.label("f_go").b(0x38, 0xE9, 0x6A, 0x85, BASE, 0x0A, 0x65, BASE, 0x85, BASE)   # BASE = cave index * 3
    a.abs(0x20, "s_count").b(0xA5, CNT, 0x85, T1)                                # n
    a.b(0xA9, 0x00, 0x85, J)
    a.label("f_lp").b(0xA5, J, 0xC5, T1).br(0x90, "f_pick")                     # J >= n: an empty place
    a.b(0xA9, 0x3F, 0x48, 0xA9, 0x00, 0x48).br(0xF0, "f_put")
    a.label("f_pick").b(0x85, K).abs(0x20, "s_nth")                             # the J-th
    a.b(0x48).abs(0xB9, "s_t_price").b(0x48)                                    # item, price
    a.label("f_put")
    a.b(0xA5, BASE, 0x18, 0x65, J, 0xAA)
    a.b(0x68).abs(0x20, "half").abs(0x9D, CAVE_PRICES)                          # (the membership card: halved)
    a.b(0x68).b(0xA4, J).b(0xC0, 0x02).br(0xD0, "f_st")
    a.b(0x85, K).abs(0xBD, CAVE_WARES).b(0x29, 0xC0, 0x05, K)                  # the third keeps its flags
    a.label("f_st").abs(0x9D, CAVE_WARES)
    a.b(0xE6, J, 0xA5, J, 0xC9, 0x03).br(0xD0, "f_lp")
    a.label("f_out").abs(0xAD, 0x0350).b(0x38, 0x60)
    # half: A = a price; with the membership card halved, rounded up (0 stays 0)
    import lol_uptable as TU
    mc = TU.bit("membership card")
    a.label("half").b(0x48).abs(0xAD, mc[0]).b(0x29, mc[1]).br(0xF0, "h_n")
    a.b(0x68, 0x4A, 0x69, 0x00, 0x60)
    a.label("h_n").b(0x68, 0x60)
    import lol_odds
    lol_odds.register(2, "shops", [c[:6] for c in SHOP_ITEMS])

    def shop_store(a):                  # not saved; the shop's kind is the hash's place (every shop 1 the same)
        a.abs(0xAD, 0x0350).abs(0x8D, lol_odds.CTX).b(0xA9, 0xFF)
    lol_odds.wrappers(a, 2, [c[:6] for c in SHOP_ITEMS], "s_", 1, shop_store, 3)
    a.label("s_t_price").b(*[c[6] for c in reversed(SHOP_ITEMS)])
    code = a.bytes()
    place(rom, 1, cpu, code)
    L = a.labels
    patch(rom, 1, 0x85D7, bytes.fromhex("ad5003c972f00cc971f008c97bb004c96eb00f"),
          bytes([0x20, L["taken"] & 0xFF, L["taken"] >> 8, 0xB0, 0x85F9 - 0x85DC, 0x4C, 0xEA, 0x85]))
    patch(rom, 1, 0x85F9, bytes([0xAD, 0x50, 0x03, 0x38]), bytes([0x20, L["fill"] & 0xFF, L["fill"] >> 8]))
    notes.append(f"shops ({len(code)} bytes)")
    shop_texts(rom, notes)
    return cpu + len(code)


SHOP_QUOTE = 0x1C                                # "BUY SOMETHIN' WILL YA!" (the cave quotes' low 6 bits)
CAVE_QUOTES = 0x45B2                             # file offset: the 20 caves' quote bytes
SHOP_CAVES = (10, 13, 14, 15, 16)                # the potion shop, shops A-D
DOOR_REPAIR, SHOP_A = 0x17, 0x1D                 # overworld destinations ($10 + cave index)


def shop_texts(rom: bytearray, notes: list) -> None:
    """Every shopkeeper says "YOU CAN ONLY BUY ONE!!" (in place of BUY SOMETHIN' WILL YA!, the same length), and the
    door repair caves are shops."""
    import lolpaths  # noqa: F401  (sys.path)
    from zora.rom.serialize.text import _encode_quote
    old, new = (bytes(_encode_quote(t)) for t in ("BUY SOMETHIN' WILL YA!", "YOU CAN ONLY BUY ONE!!"))
    assert len(old) == len(new) and rom.count(old) == 1
    at = rom.index(old); rom[at:at + len(new)] = new
    for c in SHOP_CAVES:
        rom[CAVE_QUOTES + c] = (rom[CAVE_QUOTES + c] & 0xC0) | SHOP_QUOTE
    ow, moved = 0x18410, []
    for s in range(128):
        if rom[ow + 0x80 + s] >> 2 == DOOR_REPAIR:
            rom[ow + 0x80 + s] = (SHOP_A << 2) | (rom[ow + 0x80 + s] & 0x03); moved.append(s)
    notes.append("door repairs -> shops: " + ", ".join("ABCDEFGH"[s // 16] + str(s % 16 + 1) for s in moved))

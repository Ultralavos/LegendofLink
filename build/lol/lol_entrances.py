"""Legend of Link: random entrance contents.

Every overworld entrance except H8 (the wood sword cave) and the four Any roads gets its contents the first time Link
goes in: roll 1 picks a type by his heart containers, roll 2 picks which one of that type. Each file keeps its 71
choices in save RAM $7F00 (file 1) / $7F48 (file 2), a part of the battery RAM nothing else uses ($7F00-$7FFE: the
bank-1 code copy ends at $7EFF); 0 = not rolled yet. A new file clears its 72 bytes (lol_af's new-file branch).

How it works:
- bank 6, after the overworld's level block is copied to WRAM (InitMode2_Sub0's JSR CopyBlock / RTS at $806C):
  every rolled entrance's cave value is written into LevelBlockAttrsB ($68FE + room), keeping the palette bits,
  and the whirlwind's tables ($7F90 prev rooms, $7F98 drop Ys) are rebuilt for wherever levels 1-8 now are.
- bank 5, HandleWarpOW's LDY RoomId / LDA LevelBlockAttrsB,Y ($B489, Link touching an entrance): first rolls the
  room if it hasn't been (bank 6, through a trampoline at $AF40 in banks 5 and 6), then reads the (new) value.
- bank 1: the whirlwind reads its prev room ($A06D) and drop Y ($A135) from the WRAM tables.

Rules: no content is placed more times than the game has it now (the totals are exactly 71). A pick that is used up
rerolls within the type; a type that is used up rerolls the type; "back to type" rerolls the type. A15 never gets a
level 1-9 (shrines are fine). If A15 is the last entrance and only levels are left, it gets a 10 secret.
"""
from lol_af import Asm, place, patch, BANK, screen

STORE, PER_FILE = 0x7F00, 0x48
WL, WY = 0x7F90, 0x7F98
RNG = 0x7FA0
V_IDX, V_OFF, V_D, V_CNT, V_I, V_T, V_TI, V_T2, V_D3, V_MASK, V_R = range(0x7FA2, 0x7FAD)
HEARTS = 0x066F
ROOM = 0xEB
ATTR_B = 0x68FE
SWITCH = 0xFFAC
TRAMP = 0xAF40                  # banks 5 and 6 (identical bytes)
HOOK5 = 0xAF60                  # bank 5
CODE6 = 0xAF60                  # bank 6
import os
GEN = os.environ.get("LOL_GEN") == "1"   # the v2 dungeon test: the first 8 caves are generated dungeons
CLEAR2 = 0xB900                 # bank 2: clear a new file's choices (called from lol_af's new-file branch)
EXCLUDED = ("H8",)

SECRET10, SECRET30, SECRET100 = 0x23, 0x21, 0x22
SHOPS = (0x1D, 0x1E, 0x1F)
SHOP4 = 0x20                    # v2: shop 4 (shop D's cave: its wares rolled a level higher)
UPGRADES = (0x18, 0x1B, 0x1C)
GAMBLE, WHITE, MAGIC, HINT = 0x16, 0x12, 0x13, 0x15
BACK = 0xFF

# Drop Y for the whirlwind at X=$80 per screen (whirl.txt: the first height Link isn't stuck at)
SAFE_Y = {"A2": 0x8D, "A4": 0x8D, "A5": 0x8D, "A6": 0x8D, "A8": 0x8D, "A11": 0xAD, "A12": 0x8D, "A13": 0x8D,
          "A14": 0x8D, "A15": 0x8D, "A16": 0x8D, "B1": 0x8D, "B2": 0x8D, "B3": 0x8D, "B4": 0x8D, "B5": 0x8D,
          "B7": 0x8D, "B10": 0x8D, "B11": 0x8D, "B12": 0x8D, "B13": 0x8D, "B15": 0x8D, "B16": 0x8D, "C2": 0x8D,
          "C3": 0x8D, "C6": 0x8D, "C7": 0x8D, "C8": 0x8D, "C9": 0x8D, "C13": 0xAD, "C14": 0x8D, "C16": 0x8D,
          "D4": 0x8D, "D5": 0x8D, "D8": 0x8D, "D13": 0x8D, "D14": 0x8D, "E3": 0xAD, "E5": 0x8D, "E6": 0x8D,
          "E7": 0x8D, "E8": 0x8D, "E9": 0x8D, "E11": 0x8D, "E12": 0x8D, "E14": 0x8D, "E15": 0x8D, "F2": 0x8D,
          "F7": 0x8D, "F9": 0x8D, "F12": 0x8D, "F15": 0x8D, "G3": 0x8D, "G4": 0x8D, "G5": 0x8D, "G7": 0x8D,
          "G8": 0x8D, "G9": 0x8D, "G11": 0x8D, "G12": 0x8D, "G14": 0x5D, "G16": 0x8D, "H1": 0x8D, "H2": 0x8D,
          "H5": 0x8D, "H6": 0x8D, "H7": 0x8D, "H8": 0x8D, "H9": 0x8D, "H12": 0x8D, "H13": 0x8D, "H14": 0x8D}


def rows(spec):
    """{'1-3': [...], '4': [...]} -> a list of 16 rows (containers 1..16)."""
    out = [None] * 16
    for k, v in spec.items():
        lo, hi = (int(x) for x in k.split("-")) if "-" in k else (int(k), int(k))
        for h in range(lo, hi + 1):
            out[h - 1] = v
    assert all(out), spec
    return out


# The user's tables (out of 64)
TYPE = rows({"1-3": [16, 16, 16, 8, 1, 7], "4": [14, 14, 20, 9, 1, 6], "5": [10, 10, 25, 11, 2, 6],
             "6": [5, 5, 25, 20, 2, 7], "7": [2, 5, 25, 20, 5, 7], "8": [2, 2, 25, 20, 8, 7],
             "9": [1, 1, 25, 20, 10, 7], "10": [1, 1, 25, 10, 20, 7], "11": [1, 1, 15, 5, 35, 7],
             "12": [1, 1, 5, 2, 45, 10], "13-16": [1, 1, 1, 1, 50, 10]})
SECRET = rows({"1-16": [20, 32, 12]})                                   # 10 / 30 / 100
OTHER = rows({"1-7": [40, 22, 1, 1], "8-16": [4, 20, 20, 20]})          # gamble / white / magic / hint
DUNGEON = rows({"1-3": [20, 20, 5, 3, 2, 1, 1, 1, 1, 10], "4": [15, 15, 15, 3, 2, 1, 1, 1, 1, 10],
                "5": [10, 10, 15, 10, 3, 2, 2, 1, 1, 10], "6": [5, 5, 15, 15, 5, 4, 3, 1, 1, 10],
                "7": [1, 1, 5, 10, 10, 10, 7, 7, 3, 10], "8-16": [1, 1, 1, 1, 12, 12, 12, 12, 12, 0]})
SHRINE = rows({"1-16": [8, 8, 8, 8, 8, 8, 16]})                         # A-D 32 even, E-F 16 even, back 16

TYPE_DESTS = [[SECRET10, SECRET30, SECRET100], list(SHOPS) + ([SHOP4] if GEN else []), list(range(1, 10)), list(range(0x0A, 0x10)),
              list(UPGRADES), [GAMBLE, WHITE, MAGIC, HINT]]
MAX = {SECRET10: 11, SECRET30: 10, SECRET100: 4, 0x1D: 13, 0x1E: 3, 0x1F: 4, 0x18: 1, 0x1B: 1, 0x1C: 1,
       GAMBLE: 5, WHITE: 1, MAGIC: 1, HINT: 1, **{d: 1 for d in range(1, 0x10)}}
# v2 (the dungeon test): no shrines E/F; shops 4 / 4 / 3 (+ shop 4, a copy of shop 1); secrets 100 x3, 30 x6,
# 10 x4; the rest hint caves (71 in all)
MAX_GEN = {SECRET10: 4, SECRET30: 6, SECRET100: 3, 0x1D: 4, 0x1E: 4, 0x1F: 3, SHOP4: 1, 0x18: 1, 0x1B: 1, 0x1C: 1,
           GAMBLE: 5, WHITE: 1, MAGIC: 1, **{d: 1 for d in range(1, 0x0E)}, 0x0E: 0, 0x0F: 0}
MAX_GEN[HINT] = 71 - sum(MAX_GEN.values())


def wlist(weights, outs, mask=0x3F):
    """A list: mask, then (cumulative, outcome) pairs, then 0. pick: r = rnd & mask; the first r < cum wins; past
    the end, roll again."""
    b, cum = [mask], 0
    for w, o in zip(weights, outs):
        if w:
            cum += w; b += [cum, o]
    assert mask != 0x3F or cum == 64, (weights, cum)
    return bytes(b + [0])


def apply(rom: bytearray, notes: list) -> None:
    OW = 0x18410
    ents = [s for s in range(128) if rom[OW + 0x80 + s] >> 2 and rom[OW + 0x280 + s] >> 6 != 2
            and rom[OW + 0x80 + s] >> 2 != 0x14]
    name = lambda s: "ABCDEFGH"[s // 16] + str(s % 16 + 1)
    ents = [s for s in ents if name(s) not in EXCLUDED]
    from collections import Counter
    have = Counter(rom[OW + 0x80 + s] >> 2 for s in ents)
    if not GEN:
        assert have == Counter({d: n for d, n in MAX.items()}), sorted(have.items())
    N = len(ents); assert N == 71 and N <= PER_FILE, N
    A15 = ents.index(screen("A15"))

    # the whirlwind's vanilla tables (this ROM's), the defaults for levels not placed yet
    b1 = BANK(1) - 0x8000
    assert rom[b1 + 0xA06D:b1 + 0xA070] == bytes([0xB9, 0x10, 0xA0])
    assert rom[b1 + 0xA135:b1 + 0xA138] == bytes([0xB9, 0x19, 0xA1])
    def_wl = rom[b1 + 0xA010:b1 + 0xA018]
    def_wy = rom[b1 + 0xA119:b1 + 0xA121]

    # the first quest's triforce rooms (Levels 1-8: LevelInfo + $30)
    b6 = BANK(6) - 0x8000
    tri_rooms = []
    for lv in range(1, 9):
        p = rom[b6 + 0x8014 + 2 * lv] | rom[b6 + 0x8015 + 2 * lv] << 8
        tri_rooms.append(rom[b6 + p + 0x30])
    assert tri_rooms[1] == screen("F4"), [hex(t) for t in tri_rooms]

    # --- the lists
    lists = bytearray(); offs = {}

    def add(blob):
        if blob not in offs:
            offs[blob] = len(lists); lists.extend(blob)
        return offs[blob]

    type_ptr = [add(wlist(TYPE[h], range(6))) for h in range(16)]
    sub_ptr = []
    for t in range(6):
        for h in range(16):
            if t == 0: blob = wlist(SECRET[h], [SECRET10, SECRET30, SECRET100])
            elif t == 1: blob = (wlist([4, 4, 3, 1], SHOPS + (SHOP4,), mask=0x0F) if GEN else
                                 wlist([13, 3, 4], SHOPS, mask=0x1F))
            elif t == 2: blob = wlist(DUNGEON[h], list(range(1, 10)) + [BACK])
            elif t == 3: blob = wlist(SHRINE[h], list(range(0x0A, 0x10)) + [BACK])
            elif t == 4: blob = wlist([1, 1, 1], UPGRADES, mask=0x03)
            else: blob = wlist(OTHER[h], [GAMBLE, WHITE, MAGIC, HINT])
            sub_ptr.append(add(blob))
    td = bytearray(); td_off = []
    for ds in TYPE_DESTS:
        td_off.append(len(td)); td.extend(ds + [0])

    # --- bank 6
    a = Asm(CODE6)
    # entry: roll the current room (from bank 5)
    import lol_heavy                                     # (owner 2026-11-25) G6 / A10: the Heavy Bracelet's caves
    hent = lol_heavy.entry_code(rom)
    a.label("roll_entry")
    if hent is not None:
        import lol_v3core as V3
        a.b(*V3.far(3, hent))
    a.b(0xA5, 0x00, 0x48, 0xA5, 0x01, 0x48)
    a.abs(0x20, "setoff")
    a.b(0xA2, N - 1).label("fi").abs(0xBD, "rooms").b(0xC5, ROOM).br(0xF0, "found").b(0xCA).br(0x10, "fi")
    a.abs(0x4C, "re_done")
    if GEN:                             # dealt at the start: a level or shrine gets its design the first time
        a.label("found").abs(0x20, "md_track").abs(0x8E, V_IDX).b(0x8A, 0x18).abs(0x6D, V_OFF).b(0xAA).abs(0xBD, STORE).br(0xF0, "re_done")
        a.b(0x48).abs(0x20, "seed").b(0x68).abs(0x20, "gen_need").abs(0x4C, "re_hint")
    else:
        a.label("found").abs(0x20, "md_track").abs(0x8E, V_IDX).b(0x8A, 0x18).abs(0x6D, V_OFF).b(0xAA).abs(0xBD, STORE).br(0xD0, "re_hint")
        a.abs(0x20, "seed")
        a.abs(0x20, "roll")
    a.label("re_have").b(0x48)
    a.abs(0xAD, V_IDX).b(0x18).abs(0x6D, V_OFF).b(0xAA, 0x68).abs(0x9D, STORE)
    a.abs(0x20, "apply")
    a.label("re_hint")
    if GEN:
        a.abs(0x20, "hint_chk")
    a.label("re_done").b(0x68, 0x85, 0x01, 0x68, 0x85, 0x00, 0x60)
    if GEN:
        # a hint cave: its quote (one not used yet in this game, if any left), copied to the old man's text
        from lol_genload import HINT_QS, TRAMPQ
        a.label("hint_chk").abs(0xAD, V_IDX).b(0x18).abs(0x6D, V_OFF).b(0xAA).abs(0xBD, STORE).b(0xC9, HINT)
        a.br(0xF0, "hc_go").b(0x60)
        # a quote not used yet this run whose condition Link meets (an inventory byte at least so much)
        from lol_genload import hint_conds
        conds = hint_conds(); NQ = len(conds)
        assert NQ <= 64
        a.label("hc_go").abs(0xAE, V_IDX).abs(0xBD, HINT_QS).br(0xD0, "hc_have")
        a.label("hc_r").abs(0x20, "rnd").b(0x29, 0x3F, 0xC9, NQ).br(0xB0, "hc_r").abs(0x8D, V_T)
        a.b(0xA9, NQ).abs(0x8D, V_T2)
        a.label("hc_try").abs(0xAD, V_T).b(0x18, 0x69, 0x01).abs(0x8D, V_D3)
        a.abs(0xAE, V_T).abs(0xBD, "hc_lo").b(0x85, 0x00).abs(0xBD, "hc_hi").b(0x85, 0x01, 0xA0, 0x00, 0xB1, 0x00)
        a.abs(0x3D, "hc_mask").abs(0xDD, "hc_min").br(0x90, "hc_used")     # ($00/$01: restored by re_done)
        a.b(0xA2, N - 1)
        a.label("hc_s").abs(0xBD, HINT_QS).abs(0xCD, V_D3).br(0xF0, "hc_used").b(0xCA).br(0x10, "hc_s")
        a.abs(0x4C, "hc_take")
        a.label("hc_used").abs(0xEE, V_T).abs(0xAD, V_T).b(0xC9, NQ).br(0x90, "hc_u2").b(0xA9, 0x00).abs(0x8D, V_T)
        a.label("hc_u2").abs(0xCE, V_T2).br(0xD0, "hc_try")
        a.label("hc_take").abs(0xAD, V_T).b(0x18, 0x69, 0x01).abs(0xAE, V_IDX).abs(0x9D, HINT_QS)
        a.label("hc_have").b(0x38, 0xE9, 0x01, 0x85, 0x00, 0xA9, 0x08).abs(0x20, TRAMPQ).b(0x60)
        a.label("hc_lo").b(*[c[0] & 0xFF for c in conds])
        a.label("hc_hi").b(*[c[0] >> 8 for c in conds])
        a.label("hc_mask").b(*[c[1] for c in conds])
        a.label("hc_min").b(*[c[2] for c in conds])

    # after the level block's copy
    a.label("post_copy").abs(0x20, 0x80D7).b(0xA5, 0x10).br(0xD0, "repair")
    if GEN:                             # a new file: deal every entrance now (lol_genload's DEAL, a data bank)
        from lol_genload import TRAMPD
        a.abs(0x20, "setoff").abs(0xAE, V_OFF).abs(0xBD, STORE).br(0xD0, "pc_dealt").b(0xA9, 0x08).abs(0x20, TRAMPD)
        a.label("pc_dealt")
    from lol_pictures import STUB as PICS
    from lol_save import SAVING
    a.abs(0xAD, SAVING).br(0xD0, "pc_np")  # (not for the autosave's reload: the pictures are in place, and the
    a.b(0xA2, 0x00).abs(0x20, PICS)        #  load's blanking showed as a black frame) the owned upgrades' pictures
    a.label("pc_np").abs(0x20, "apply")    #  (an overworld load)
    a.label("pc_r").b(0x60)
    # a first-quest level 1-8 whose triforce Link doesn't have: its triforce room's item isn't taken (bit $10 of
    # the room's flags: $06FF + room for Levels 1-6, $077F + room for 7-8). Mends files where A-F's rooms wrote
    # over Levels 1-6's flags.
    a.label("repair")
    if GEN:                             # (generated levels: their rooms aren't the vanilla ones)
        a.b(0x60)
    a.b(0xC9, 0x09).br(0xB0, "pc_r").b(0xA4, 0x16).abs(0xB9, 0x062D).br(0xD0, "pc_r")
    a.b(0xA6, 0x10).abs(0xAD, 0x0671).abs(0x3D, "lvmask").br(0xD0, "pc_r")
    a.abs(0xBC, "triroom").b(0xE0, 0x07).br(0xB0, "rp_hi")
    a.abs(0xB9, 0x06FF).b(0x29, 0xEF).abs(0x99, 0x06FF).b(0x60)
    a.label("rp_hi").abs(0xB9, 0x077F).b(0x29, 0xEF).abs(0x99, 0x077F).b(0x60)

    # apply: every rolled entrance into attrs B; the whirlwind's tables
    a.label("apply").abs(0x20, "setoff").b(0xA2, N - 1)
    a.label("a_l").abs(0x8E, V_I).b(0x8A, 0x18).abs(0x6D, V_OFF).b(0xA8).abs(0xB9, STORE).br(0xF0, "a_n")
    a.b(0x0A, 0x0A).abs(0x8D, V_D).abs(0xBC, "rooms").abs(0xB9, ATTR_B).b(0x29, 0x03).abs(0x0D, V_D)
    a.abs(0x99, ATTR_B)
    a.label("a_n").abs(0xAE, V_I).b(0xCA).br(0x10, "a_l")
    a.b(0xA2, 0x07).label("a_w").abs(0xBD, "def_wl").abs(0x9D, WL).abs(0xBD, "def_wy").abs(0x9D, WY)
    a.b(0xCA).br(0x10, "a_w")
    a.b(0xA2, N - 1)
    a.label("w_l").b(0x8A, 0x18).abs(0x6D, V_OFF).b(0xA8).abs(0xB9, STORE).br(0xF0, "w_n")
    a.b(0xC9, 0x09).br(0xB0, "w_n").b(0xA8, 0x88)                      # levels 1-8: Y = level - 1
    a.abs(0xBD, "rooms").b(0x38, 0xE9, 0x01).abs(0x99, WL).abs(0xBD, "safey").abs(0x99, WY)
    a.label("w_n").b(0xCA).br(0x10, "w_l")
    import lol_modes
    lol_modes.d10(a)
    a.b(0x60)
    lol_modes.track(a)

    a.label("setoff").b(0xA9, 0x00, 0xA4, 0x16).br(0xF0, "so").b(0xA9, PER_FILE)
    a.label("so").abs(0x8D, V_OFF).b(0x60)

    # random: xorshift16 (RNG, RNG+1), stirred with the game's random byte and the frame counter
    import lol_modes                                     # (a fixed seed: no stirring)
    st = (0x49, 0x00) if lol_modes.SEED_OPT is not None else (0x45, 0x18)
    st2 = (0x49, 0x00) if lol_modes.SEED_OPT is not None else (0x45, 0x15)
    a.label("seed").abs(0xAD, RNG).b(*st).abs(0x8D, RNG).abs(0xAD, RNG + 1).b(*st2)
    a.abs(0x8D, RNG + 1).abs(0x0D, RNG).br(0xD0, "sd_ok").abs(0xEE, RNG)
    a.label("sd_ok").abs(0x20, "rnd").abs(0x4C, "rnd")
    a.label("rnd").abs(0xAD, RNG + 1).b(0x4A).abs(0xAD, RNG).b(0x6A).abs(0x4D, RNG + 1).abs(0x8D, RNG + 1)
    a.b(0x6A).abs(0x4D, RNG).abs(0x8D, RNG).abs(0x4D, RNG + 1).abs(0x8D, RNG + 1).b(0x60)

    if not GEN:                         # (the v2 build deals everything at the start)
        # pick: ($00) = a list -> A = its outcome
        a.label("pick").b(0xA0, 0x00, 0xB1, 0x00).abs(0x8D, V_MASK)
        a.label("p_again").abs(0x20, "rnd").abs(0x2D, V_MASK).abs(0x8D, V_R).b(0xA0, 0x01)
        a.label("p_l").b(0xB1, 0x00).br(0xF0, "p_again").abs(0xAD, V_R).b(0xD1, 0x00).br(0x90, "p_f")
        a.b(0xC8, 0xC8).br(0xD0, "p_l")
        a.label("p_f").b(0xC8, 0xB1, 0x00, 0x60)

        # allowed: A = dest -> C = 1 if it can still be placed here
        a.label("allowed").abs(0x8D, V_D).abs(0xAE, V_IDX).b(0xE0, A15).br(0xD0, "al_c")
        a.b(0xC9, 0x0A).br(0x90, "al_no")                                    # A15: no level 1-9
        a.label("al_c").b(0xA9, 0x00).abs(0x8D, V_CNT).abs(0xAE, V_OFF).b(0xA0, N)
        a.label("al_l").abs(0xBD, STORE).abs(0xCD, V_D).br(0xD0, "al_n").abs(0xEE, V_CNT)
        a.label("al_n").b(0xE8, 0x88).br(0xD0, "al_l")
        a.abs(0xAE, V_D).abs(0xAD, V_CNT).abs(0xDD, "max").br(0xB0, "al_no").b(0x38, 0x60)
        a.label("al_no").b(0x18, 0x60)

        # type_ok: A = type -> C = 1 if any of its contents is allowed
        a.label("type_ok").b(0xAA).abs(0xBD, "td_off").abs(0x8D, V_TI)
        a.label("t_l").abs(0xAE, V_TI).abs(0xBD, "td").br(0xF0, "t_no").abs(0x20, "allowed").br(0xB0, "t_yes")
        a.abs(0xEE, V_TI).br(0xD0, "t_l")
        a.label("t_no").b(0x18)
        a.label("t_yes").b(0x60)

        # roll -> A = the dest
        a.label("roll").b(0xA9, 0x05).abs(0x8D, V_T2)
        a.label("f_l").abs(0xAD, V_T2).abs(0x20, "type_ok").br(0xB0, "r_type").abs(0xCE, V_T2).br(0x10, "f_l")
        a.b(0xA9, SECRET10, 0x60)                                            # nothing fits: a 10 secret
        a.label("r_type").abs(0xAD, HEARTS).b(0x4A, 0x4A, 0x4A, 0x29, 0x1E, 0xAA)
        a.abs(0xBD, "type_ptr").b(0x85, 0x00)
        a.abs(0xBD, "type_ptr_hi").b(0x85, 0x01)
        a.abs(0x20, "pick").abs(0x8D, V_T).abs(0x20, "type_ok").br(0x90, "r_type")
        a.label("r_sub").abs(0xAD, V_T).b(0x0A, 0x0A, 0x0A, 0x0A, 0x0A).abs(0x8D, V_R)
        a.abs(0xAD, HEARTS).b(0x4A, 0x4A, 0x4A, 0x29, 0x1E, 0x18).abs(0x6D, V_R).b(0xAA)
        a.abs(0xBD, "sub_ptr").b(0x85, 0x00).abs(0xBD, "sub_ptr_hi").b(0x85, 0x01)
        a.abs(0x20, "pick").b(0xC9, BACK).br(0xF0, "r_type").abs(0x8D, V_D3).abs(0x20, "allowed").br(0x90, "r_sub")
        a.abs(0xAD, V_D3).b(0x60)

    # data
    if GEN:
        import lol_genload
        lol_genload.gen_force(a, V_IDX, V_OFF, A15, STORE, N)
    a.label("rooms").b(*ents)
    a.labels["lvmask"] = a.cpu + len(a.code) - 1                         # (index = level, 1-8)
    a.b(*(1 << i for i in range(8)))
    a.labels["triroom"] = a.cpu + len(a.code) - 1
    a.b(*tri_rooms)
    a.label("safey").b(*(SAFE_Y[name(s)] for s in ents))
    a.label("def_wl").b(*def_wl)
    a.label("def_wy").b(*def_wy)
    if not GEN:
        a.label("max").b(*(MAX.get(d, 0) for d in range(0x24)))
        a.label("td_off").b(*td_off)
        a.label("td").b(*td)
        # pointer tables (lo at label, hi at label + 1, X = index * 2): filled after layout
        a.label("type_ptr").b(*([0] * 32))
        a.labels["type_ptr_hi"] = a.labels["type_ptr"] + 1
        a.label("sub_ptr").b(*([0] * 192))
        a.labels["sub_ptr_hi"] = a.labels["sub_ptr"] + 1
        a.label("lists").b(*lists)
    code = bytearray(a.bytes())
    if not GEN:
        base = a.labels["lists"]
        tp = a.labels["type_ptr"] - CODE6
        for h in range(16):
            p = base + type_ptr[h]; code[tp + 2 * h] = p & 0xFF; code[tp + 2 * h + 1] = p >> 8
        sp = a.labels["sub_ptr"] - CODE6
        for i, o in enumerate(sub_ptr):
            p = base + o; code[sp + 2 * i] = p & 0xFF; code[sp + 2 * i + 1] = p >> 8
    place(rom, 6, CODE6, bytes(code))
    L = a.labels
    patch(rom, 6, 0x806C, bytes([0x20, 0xD7, 0x80, 0x60]), bytes([0x4C, L["post_copy"] & 0xFF, L["post_copy"] >> 8]))

    # --- the trampoline (banks 5 and 6) and bank 5's hook
    tr = bytes([0xA9, 0x06, 0x20, SWITCH & 0xFF, SWITCH >> 8, 0x20, L["roll_entry"] & 0xFF, L["roll_entry"] >> 8,
                0xA9, 0x05, 0x4C, SWITCH & 0xFF, SWITCH >> 8])
    place(rom, 5, TRAMP, tr); place(rom, 6, TRAMP, tr)
    h = Asm(HOOK5)
    h.b(0x8A, 0x48).abs(0x20, TRAMP).b(0x68, 0xAA, 0xA4, ROOM).abs(0xB9, ATTR_B).b(0x60)
    place(rom, 5, HOOK5, h.bytes())
    patch(rom, 5, 0xB489, bytes([0xA4, ROOM, 0xB9, 0xFE, 0x68]), bytes([0x20, HOOK5 & 0xFF, HOOK5 >> 8]))

    # --- bank 1: the whirlwind reads the WRAM tables
    rom[b1 + 0xA06D:b1 + 0xA070] = bytes([0xB9, WL & 0xFF, WL >> 8])
    rom[b1 + 0xA135:b1 + 0xA138] = bytes([0xB9, WY & 0xFF, WY >> 8])
    import lol_modes                     # (its new-file part: its own routine in bank 2, called from here)
    lol_modes.install_clear(rom)
    c = Asm(CLEAR2); clear_code(c, 0x16); c.b(0x60); place(rom, 2, CLEAR2, c.bytes())
    notes.append(f"random entrances: {N} entrances, bank 6 ${CODE6:04X}-${CODE6 + len(code) - 1:04X} "
                 f"({len(code)} bytes), saved at ${STORE:04X}/${STORE + PER_FILE:04X}")


def clear_code(a: Asm, slot_zp: int) -> None:
    """For lol_af's new-file branch: clear this file's choices (keeps A = 0... returns with A = 0)."""
    import lol_modes
    lol_modes.clear(a)
    a.b(0xA9, 0x00, 0xA4, slot_zp).br(0xF0, "ec_0").b(0xA9, PER_FILE)
    a.label("ec_0").b(0xAA, 0xA0, PER_FILE, 0xA9, 0x00).label("ec_l").abs(0x9D, STORE).b(0xE8, 0x88).br(0xD0, "ec_l")
    if GEN:                               # and the generated dungeons' records (lol_genload: $7FAD, 65 bytes),
        a.b(0xA2, 64, 0xA9, 0x00).label("ec_m").abs(0x9D, 0x7FAD).b(0xCA).br(0x10, "ec_m")   # the hint quotes
                                          # (the item deck's next card is in them: lol_genload DECK_PTR)
        a.b(0xA2, 71).label("ec_q").abs(0x9D, 0x7F48).b(0xCA).br(0x10, "ec_q")
        a.b(0xA2, 0x7F).label("ec_f").abs(0x9D, 0x6292).b(0xCA).br(0x10, "ec_f")   # grid 4's second room memory

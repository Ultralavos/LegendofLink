"""Legend of Link: the Heavy Bracelet's rocks and caves (owner, 2026-11-25).

Only on seeds whose upgrade pool has the Heavy Bracelet (lol_uptable.POOL; 75, tier 2, with the power bracelet):
  - A10 gets the second quest's screen: its pushable rock (square 4, 5) and stairs (spot 2, $99) show in the first
    quest too; G6 gets the owner's 3Q screen: the middle rock of column 10 (row 5) is pushable, the stairs right of
    it (spot 3 becomes $B9: only C1, a second-quest secret, used it). Neither is one of the 71 entrances (their
    destination stays 0 in the ROM); bank 4's push check (UpdateRockOrGravestone's LDA InvBracelet, $8E4F) asks
    for the Heavy Bracelet on these two screens instead of the power bracelet.
  - the two caves: the seed decides each one's contents (out of 64; never the same option in both): 30 the Thorn
    Bracelet (free), 10 a secret shop (ring 150, sword 150, book 100), 20 a 100-rupee secret, 3 an old man's hint
    about a secret mode, 1 a free ring, book or sword (take one). Entering the stairs (lol_entrances' roll_entry,
    bank 6) far-calls ENTRY, which writes the cave's destination into LevelBlockAttrsB; InitCave's fill ($85F9)
    and TakeItem ($891E) get stubs here (bank 1) that far-call WARES / TAKE in bank 0 after the usual chain.
  - Thorn Bracelet (UP6 $80, lol_uptable.THORN): shown on the menu in the Heavy Bracelet's place (lol_pictures);
    a monster touching Link takes what Link loses (ring halving included), rounded up to whole hearts, as a sword
    hit of $10 a heart (lol_enemies2's harm sets THD, its common stub makes the hit).
  - with the Heavy Bracelet, every pushable rock on the overworld (the $26 squares a first-quest game can push)
    is drawn in the grey palette (lol_xray's fill: OW_MARK).
Items in the caves follow Link's inventory: ring blue then red (none with Zombie Link), sword white then magical
(none swordless or with the Heart Snubber), book red then blue; one he can't use leaves its place empty."""
import os
import random
from lol_af import Asm, BANK, place, patch
import lol_uptable as T

G6, A10 = 0x65, 0x09
OW = 0x18410
SPOTS = 0x19339                         # LevelInfo_ShortcutOrItemPosArray (file)
COL_DIR = 0x19D1F                       # bank 6 $9D0F (file): the column groups' addresses (bank 5)
LAYOUTS = 0x15428
B5 = 16 + 5 * 0x4000 - 0x8000
ATTR_B = 0x68FE
CAVE_WARES, CAVE_PRICES = 0x6A7E, 0x6ABA
TAKE_ANY, SHOP, SECRET100, HINT = 0x11, 0x1D, 0x22, 0x15
THD = 0x01B6                            # (stack page, unused): the thorns' hit ($10 a heart; 0: none)
HB = T.bit("heavy bracelet")
THORN = T.THORN
GREY = 0                                # the overworld's grey background palette
GREY_PAL = (0x00, 0x55, 0xAA, 0xFF)[GREY]
ACTIVE = T.index("heavy bracelet") in T.POOL

THORN_C, SHOP_C, SECRET_C, HINT_C, FREE_C = 1, 2, 3, 4, 5
ODDS = [(THORN_C, 30), (SHOP_C, 10), (SECRET_C, 20), (HINT_C, 3), (FREE_C, 1)]
DEST = {THORN_C: TAKE_ANY, SHOP_C: SHOP, SECRET_C: SECRET100, HINT_C: HINT, FREE_C: TAKE_ANY}
SPECIAL_TEXT = {THORN_C: ["WITH THIS YOU DEAL", "DAMAGE BACK WHEN", "ENEMIES TOUCH YOU"],
                "sleep": ["THIS LULLABY PUTS SOME", "ENEMIES TO SLEEP,", "AND SLOWS OTHERS"]}   # (owner 2026-11-25)
HINTS = {"swordless": ["ENTER 5 DOORS BEFORE", "YOU TAKE A SWORD, THEN", "VISIT THE SWORD CAVE"],
         "hard": ["DIE 5 TIMES BEFORE YOU", "ENTER ANY DOOR, THEN", "VISIT THE SWORD CAVE"]}


H16, E4 = 0x7F, 0x43                    # (lol_discovery's two caves: the same deal)
ACTIVE2 = T.index("song of discovery") in T.POOL


def _deal(salt, rooms):
    seed = int(os.environ.get("LOL_SET_SEED") or os.environ.get("LOL_SEED") or 0)
    rng = random.Random(seed * 6151 + salt)

    def roll():
        r = rng.randrange(64)
        for c, w in ODDS:
            if r < w:
                return c
            r -= w
    g = roll()
    a = roll()
    while a == g:                       # (owner: no option in both caves)
        a = roll()
    return {rooms[0]: g, rooms[1]: a}, rng.choice(sorted(HINTS))


DEALT, HINT_MODE = _deal(0x4EA7, (G6, A10))
DEALT2, HINT_MODE2 = _deal(0x5D15, (H16, E4))
# every cave this seed has: (room, its option, the special's item and bit, the hint's mode)
CAVES = ([(r, DEALT[r], 0x14, THORN, HINT_MODE) for r in (G6, A10)] if ACTIVE else []) + \
        ([(r, DEALT2[r], 0x05, T.SLEEP, HINT_MODE2) for r in (H16, E4)] if ACTIVE2 else [])
import lol_secret                       # (owner 2026-11-25: a rare seed's secret spot: a hint cave of its own)
CAVES += lol_secret.caves()


def describe():
    out = []
    for r, c, item, bit, mode in CAVES:
        sp = "Thorn Bracelet" if bit == THORN else "Song of Sleep"
        names = {THORN_C: sp, SHOP_C: "secret shop", SECRET_C: "100 rupees", HINT_C: f"hint ({mode})",
                 FREE_C: "free ring / book / sword"}
        out.append(f"{'ABCDEFGH'[r // 16]}{r % 16 + 1} {names[c]}")
    return ", ".join(out) or "no Heavy Bracelet / Song of Discovery this seed"


def entry_code(rom):
    """lol_entrances' roll_entry far-calls this (bank 0) first: the caves get their destinations."""
    if not CAVES:
        return None
    import lol_v3core as V

    def build(org):
        a = Asm(org)
        a.label("ent").b(0xA5, 0x10).br(0xD0, "e_r").b(0xA2, len(CAVES) - 1)
        a.label("e_l").b(0xA5, 0xEB).abs(0xDD, "e_rm").br(0xF0, "e_f").b(0xCA).br(0x10, "e_l").b(0x60)
        a.label("e_f").abs(0xBD, "e_d").b(0x0A, 0x0A).abs(0x8D, THD).b(0xA6, 0xEB).abs(0xBD, ATTR_B).b(0x29, 0x03)
        a.abs(0x0D, THD).abs(0x9D, ATTR_B)
        a.label("e_r").b(0x60)
        a.label("e_rm").b(*[c[0] for c in CAVES])
        a.label("e_d").b(*[DEST[c[1]] for c in CAVES])
        return a
    from lol_newups import put3 as put
    return put(rom, 3, build).labels["ent"]                 # (bank 3; far-called)


def marks(rom):
    """(room, PlayAreaAttrs index, quarter mask) of every pushable rock a first-quest game shows, and A10's and G6's."""
    import sys
    import lolpaths
    if lolpaths.ZORA not in sys.path:
        sys.path.insert(0, lolpaths.ZORA)
    from zora.rom.vanilla_overworld import layouts as L
    from zora.rom.vanilla_overworld.tables import ROOM_LAYOUTS_OW
    ta = bytes(rom).index(ROOM_LAYOUTS_OW.read(rom))
    heaps = L._heap_starts(rom)
    out = []
    for s in range(128):
        if rom[OW + 0x280 + s] >> 6 == 2:
            continue
        code = rom[OW + 0x180 + s] & 0x7F
        for c in range(16):
            col = L._column(rom, heaps[rom[ta + code * 16 + c] >> 4], rom[ta + code * 16 + c] & 15)
            out += [(s, c, r) for r in range(11) if col[r] == 0x26]
    out += [(A10, 4, 5), (G6, 10, 5)]
    return [(s, (r // 2) * 8 + c // 2, 3 << (2 * ((r % 2) * 2 + c % 2))) for s, c, r in out]


def ow_mark(a: Asm, rom, zr):
    """lol_xray's mark (bank 0, after FillPlayAreaAttrs; ZR the room): on the overworld with the Heavy Bracelet,
    every pushable rock's quarter in the grey palette. Ends at its own RTS; mark's code follows at "mark"."""
    m = marks(rom) if ACTIVE else []
    if not m:
        a.label("owm").b(0x60)
        return False
    a.label("owm").b(0xA5, 0x10).br(0xD0, "om_r").abs(0xAD, HB[0]).b(0x29, HB[1]).br(0xF0, "om_r")
    a.b(0xA2, len(m) - 1)
    a.label("om_l").abs(0xBD, "om_room").abs(0xCD, zr).br(0xD0, "om_n")
    a.abs(0xBC, "om_idx").abs(0xBD, "om_msk").b(0x49, 0xFF).abs(0x39, 0x0530).abs(0x99, 0x0530)
    a.abs(0xBD, "om_msk").b(0x29, GREY_PAL).abs(0x19, 0x0530).abs(0x99, 0x0530)
    a.label("om_n").b(0xCA).br(0x10, "om_l")
    a.label("om_r").b(0x60)
    a.label("om_room").b(*[s for s, _, _ in m])
    a.label("om_idx").b(*[i for _, i, _ in m])
    a.label("om_msk").b(*[k for _, _, k in m])
    return bool(m)


def _set_square(rom, screen, col, row, old, new, notes):
    """The screen's layout gets a new column (its group's heap copied to bank 5 with the column appended)."""
    from lol_newups import free_in
    lay = rom[OW + 0x180 + screen] & 0x7F
    assert sum(1 for s in range(128) if rom[OW + 0x180 + s] & 0x7F == lay) == 1, hex(screen)
    base_col = rom[LAYOUTS + 16 * lay + col]
    g = base_col >> 4
    dirp = [rom[COL_DIR + 2 * k] | rom[COL_DIR + 2 * k + 1] << 8 for k in range(16)]

    def column(p_start, i):
        p, n = p_start, -1
        while True:
            if rom[B5 + p] & 0x80:
                n += 1
                if n == i:
                    break
            p += 1
        sq, start = [], p
        while len(sq) < 11:
            b = rom[B5 + p]; sq.append(b & 0x3F)
            if b & 0x40:
                sq.append(b & 0x3F)
            p += 1
        return sq[:11], p
    lo, hi = dirp[g], dirp[g + 1]
    assert lo < hi < lo + 0x200, (hex(lo), hex(hi))
    n = sum(1 for x in rom[B5 + lo:B5 + hi] if x & 0x80)
    hi = max(column(lo, i)[1] for i in range(n))    # (the last column may run on into the next group's bytes)
    sq, _ = column(lo, base_col & 15)
    assert sq[row] == old, (hex(screen), sq)
    sq[row] = new
    enc, k = bytearray(), 0
    while k < 11:
        if k + 1 < 11 and sq[k + 1] == sq[k]:
            enc.append(sq[k] | 0x40); k += 2
        else:
            enc.append(sq[k]); k += 1
    enc[0] |= 0x80
    heap = bytes(rom[B5 + lo:B5 + hi]) + bytes(enc)
    at = free_in(rom, 5, len(heap), 0x8000, 0xBD40 - len(heap))   # (lol_snubber: $BD5E on)
    place(rom, 5, at, heap)
    rom[COL_DIR + 2 * g:COL_DIR + 2 * g + 2] = bytes([at & 0xFF, at >> 8])
    k = sum(1 for x in rom[B5 + lo:B5 + hi] if x & 0x80)   # (its index: every column start in the copy before it)
    new_code = g << 4 | k
    assert k < 16
    rom[LAYOUTS + 16 * lay + col] = new_code
    notes.append(f"heavy: {screen:02X}'s column {col} -> ${new_code:02X} (group {g:X}'s heap now bank 5 ${at:04X})")


def apply(rom: bytearray, notes: list) -> None:
    if not CAVES:
        notes.append("heavy bracelet / song of discovery: " + describe())
        return
    import lol_v3core as V
    import lol_modes
    from lol_newups import free_in
    from lol_saveblock import HINT_BUF
    import sys
    import lolpaths
    for p in (lolpaths.ZORA, lolpaths.Q3B):
        if p not in sys.path:
            sys.path.insert(0, p)
    from zora.rom.serialize.text import _encode_quote
    import build_mock as base
    if ACTIVE:
        heavy_screens(rom, notes)
    if ACTIVE2:
        import lol_discovery
        lol_discovery.apply(rom, notes)
    caves(rom, notes)


def heavy_screens(rom, notes):
    from lol_newups import free_in
    f = OW + 0x280
    assert rom[f + A10] == 0xA4 and rom[OW + 0x80 + A10] >> 2 == 0x13
    rom[f + A10] = 0x24                                         # first quest too (spot 2, exit row 4)
    rom[OW + 0x80 + A10] &= 0x03                                # (no destination in the ROM: ENTRY's)
    assert rom[SPOTS:SPOTS + 4] == bytes([0x57, 0x49, 0x99, 0x69])
    users3 = [s for s in range(128) if (rom[f + s] >> 4) & 3 == 3]
    assert users3 == [0x20] and rom[f + 0x20] >> 6 == 2, users3
    rom[SPOTS + 3] = 0xB9                                       # G6's stairs: column 11, row 5
    assert rom[f + G6] == 0x00 and rom[OW + 0x80 + G6] >> 2 == 0
    rom[f + G6] = 0x35                                          # spot 3, exit row 5
    rom[OW + G6] = 0xB0 | (rom[OW + G6] & 0x0F)                 # exit column 11
    _set_square(rom, G6, 10, 5, 0x13, 0x26, notes)

    # --- bank 4: the push check
    def bpush(o):
        a = Asm(o)
        a.b(0xA5, 0xEB, 0xC9, G6).br(0xF0, "h").b(0xC9, A10).br(0xF0, "h").abs(0xAD, 0x0665).b(0x60)
        a.label("h").abs(0xAD, HB[0]).b(0x29, HB[1]).b(0x60)
        return a
    pa = free_in(rom, 4, len(bpush(0x8000).bytes()), 0xB000, 0xBFB0)
    place(rom, 4, pa, bpush(pa).bytes())
    patch(rom, 4, 0x8E4F, bytes([0xAD, 0x65, 0x06]), bytes([0x20, pa & 0xFF, pa >> 8]))


def caves(rom, notes):
    import lol_v3core as V
    import lol_modes
    from lol_newups import free_in
    from lol_saveblock import HINT_BUF
    import sys
    import lolpaths
    for p in (lolpaths.ZORA, lolpaths.Q3B):
        if p not in sys.path:
            sys.path.insert(0, p)
    from zora.rom.serialize.text import _encode_quote
    import build_mock as base

    # --- bank 0: the wares and the take
    import lol_secret
    ALL = {**HINTS, **({"secret": lol_secret.TEXT} if lol_secret.PICK else {})}
    modes = sorted(ALL)
    texts = b""
    for m in modes:
        t = bytes(_encode_quote(base.centered(ALL[m])))
        texts += t + bytes(80 - len(t))
    stexts = b""
    for lines in (SPECIAL_TEXT[THORN_C], SPECIAL_TEXT["sleep"]):
        t = bytes(_encode_quote(base.centered(lines)))
        assert len(t) <= 80
        stexts += t + bytes(80 - len(t))
    mc = T.bit("membership card")
    zl = T.bit("zombie link")
    sn = T.bit("heart snubber")
    n = len(CAVES)

    def bwares(o):
        a = Asm(o)
        a.label("w").b(0xA5, 0x10).br(0xD0, "w_r").b(0xA2, n - 1)
        a.label("w_l").b(0xA5, 0xEB).abs(0xDD, "rm").br(0xF0, "w_f").b(0xCA).br(0x10, "w_l")
        a.label("w_r").b(0x60)
        a.label("w_f").abs(0xBD, "opt").b(0xC9, THORN_C).br(0xF0, "w_th").b(0xC9, SHOP_C).br(0xF0, "w_sh")
        a.b(0xC9, FREE_C).br(0xF0, "w_fr").b(0xC9, HINT_C).br(0xF0, "w_hi").b(0x60)
        ta = 3 * (TAKE_ANY - 0x10)
        sh = 3 * (SHOP - 0x10)
        # the special (Thorn Bracelet / Song of Sleep): the take-any's middle place, drawn as its item
        # (owner 2026-11-25) and the old man's own words for it (sel: 0 the Thorn Bracelet, 1 the Song of Sleep)
        a.label("w_th").abs(0xBD, "sel").br(0xF0, "w_t0").b(0xA9, 80)
        a.label("w_t0").b(0x48)
        a.abs(0xBD, "item").b(0x48, 0xA2, ta, 0xA9, 0x3F).abs(0x20, "put").b(0x68).abs(0x20, "put")
        a.b(0xA9, 0x3F).abs(0x20, "put")
        a.b(0x68, 0xA8, 0xA2, 0x00)
        a.label("w_tl").abs(0xB9, "stext").abs(0x9D, HINT_BUF).b(0xC8, 0xE8, 0xE0, 80).br(0xD0, "w_tl")
        a.b(0xA9, lol_modes.HINT_SEL).abs(0x8D, lol_modes.QOVR).b(0x60)
        # free: ring, book, sword (take one)
        a.label("w_fr").b(0xA2, ta).abs(0x20, "ring").abs(0x20, "put").abs(0x20, "book").abs(0x20, "put")
        a.abs(0x20, "sword").abs(0x4C, "put")
        # the shop: ring 150, sword 150, book 100 (the membership card: half, rounded up)
        a.label("w_sh").b(0xA2, sh).abs(0x20, "ring").abs(0x20, "put").abs(0x20, "sword").abs(0x20, "put")
        a.abs(0x20, "book").abs(0x20, "put")
        a.b(0xA2, 0x02)
        a.label("w_pl").abs(0xBD, "prices").b(0xA8).abs(0xAD, mc[0]).b(0x29, mc[1]).br(0xF0, "w_ps")
        a.b(0x98, 0x4A, 0x69, 0x00, 0xA8)
        a.label("w_ps").b(0x98).abs(0x9D, CAVE_PRICES + sh).b(0xCA).br(0x10, "w_pl").b(0x60)
        # the hint: the old man's text (this cave's mode)
        a.label("w_hi").abs(0xBC, "hix").b(0xA2, 0x00)
        a.label("w_hl").abs(0xB9, "text").abs(0x9D, HINT_BUF).b(0xC8, 0xE8, 0xE0, 80).br(0xD0, "w_hl")
        a.b(0xA9, lol_modes.HINT_SEL).abs(0x8D, lol_modes.QOVR).b(0x60)
        # put: item A into ware X (its flag bits kept); X + 1
        a.label("put").abs(0x8D, THD).abs(0xBD, CAVE_WARES).b(0x29, 0xC0).abs(0x0D, THD).abs(0x9D, CAVE_WARES)
        a.b(0xE8, 0xA9, 0x00).abs(0x8D, THD).b(0x60)
        # the items by inventory ($3F: none)
        a.label("ring").abs(0xAD, zl[0]).b(0x29, zl[1]).br(0xD0, "none").abs(0xAD, 0x0662).b(0xC9, 0x02)
        a.br(0xB0, "none").b(0x18, 0x69, 0x12, 0x60)
        a.label("sword").abs(0xAD, sn[0]).b(0x29, sn[1]).br(0xD0, "none").abs(0xAD, lol_modes.SWL).br(0xD0, "none")
        a.abs(0xAD, 0x0657).b(0xC9, 0x02).br(0x90, "s_w").br(0xD0, "none").b(0xA9, 0x03, 0x60)
        a.label("s_w").b(0xA9, 0x02, 0x60)
        a.label("book").abs(0xAD, 0x0661).br(0xF0, "b_r").b(0xC9, 0x01).br(0xD0, "none").b(0xA9, 0x25, 0x60)
        a.label("b_r").b(0xA9, 0x11, 0x60)
        a.label("none").b(0xA9, 0x3F, 0x60)
        a.label("prices").b(150, 150, 100)
        # the take: in a special's cave, its bit (and its picture now: the owned ones reloaded). X kept.
        import lol_pictures as PIC
        a.label("take").b(0xA5, 0x10).br(0xD0, "t_x").b(0x8A, 0x48, 0xA2, n - 1)
        a.label("t_l").b(0xA5, 0xEB).abs(0xDD, "rm").br(0xF0, "t_f").b(0xCA).br(0x10, "t_l").br(0x30, "t_r")
        a.label("t_f").abs(0xBD, "opt").b(0xC9, THORN_C).br(0xD0, "t_r").abs(0xBD, "sel").br(0xD0, "t_s")
        a.abs(0xAD, THORN[0]).b(0x09, THORN[1]).abs(0x8D, THORN[0]).br(0xD0, "t_p")
        a.label("t_s").abs(0xAD, T.SLEEP[0]).b(0x09, T.SLEEP[1]).abs(0x8D, T.SLEEP[0])
        a.label("t_p").b(0xA2, 0x00).b(*V.far(0, PIC.LOAD["load"]))
        a.label("t_r").b(0x68, 0xAA)
        a.label("t_x").b(0x60)
        a.label("rm").b(*[c[0] for c in CAVES])
        a.label("opt").b(*[c[1] for c in CAVES])
        a.label("item").b(*[c[2] for c in CAVES])
        a.label("sel").b(*[0 if c[3] == THORN else 1 for c in CAVES])
        a.label("hix").b(*[80 * modes.index(c[4]) for c in CAVES])
        a.label("text").b(*texts)
        a.label("stext").b(*stexts)
        return a
    from lol_newups import put3 as put
    W = put(rom, 3, bwares).labels                          # (bank 3: bank 0 is full)

    # --- bank 1: the stubs (InitCave's fill; TakeItem)
    f1 = BANK(1) + 0x85F9 - 0x8000
    assert rom[f1] == 0x20
    old_fill = rom[f1 + 1] | rom[f1 + 2] << 8
    t1 = BANK(1) + 0x891E - 0x8000
    assert rom[t1] == 0x20
    old_take = rom[t1 + 1] | rom[t1 + 2] << 8

    def bstub(o):
        a = Asm(o)
        a.label("fill").abs(0x20, old_fill).b(0x48).b(*V.far(3, W["w"])).b(0x68, 0x38, 0x60)   # (A $0350, C set)
        a.label("take").b(0x48).b(*V.far(3, W["take"])).b(0x68).abs(0x4C, old_take)
        return a
    sa = free_in(rom, 1, len(bstub(0x8000).bytes()), 0xB000)
    s = bstub(sa)
    place(rom, 1, sa, s.bytes())
    rom[f1 + 1:f1 + 3] = bytes([s.labels["fill"] & 0xFF, s.labels["fill"] >> 8])
    rom[t1 + 1:t1 + 3] = bytes([s.labels["take"] & 0xFF, s.labels["take"] >> 8])
    notes.append("heavy bracelet / song of discovery: " + describe())

"""Legend of Link: names (owner, 2026-11-25). On an unseeded game (the page's "Unseeded", LOL_FIXED=0) a file's
name changes things:

  ZELDA   every old man says "DID YOU ACTUALLY THINK THAT WOULD WORK" (nothing else changes)
  IDDQD   every old man says "OK YOU WANTED DOOM, YOU GOT IT!", and enemies level up as at 16 containers
  UNSEED  (lol_names' later parts) bait, poison bait and the fountains' ciphers
  !ADLEZ  (lol_names' later parts) the hero's start

The name is the file's own (NAMES $0638 + slot * 8, saved with it), read when needed: nothing else is stored.
namek (bank 3, far-called): A = 0 none, 1 UNSEED, 2 ZELDA, 3 IDDQD, 4 !ADLEZ (always 0 on a seeded game).
Old men: InitCave's fill (bank 1 $85F9, after lol_heavy's) -> for those names, an old man's ($0350 one of OLD_MEN)
words are the name's (HINT_BUF, QOVR). IDDQD's levels: unseeded, lol_build's status bar code (bank 5, every frame) sets HVE
through hve (bank 3): HeartValues + 3 containers in hard mode, $FF for a file named IDDQD."""
from lol_af import Asm, BANK, place

NAMES = 0x0638
BLANK = 0x24
WORDS = {"UNSEED": 1, "ZELDA": 2, "IDDQD": 3, "!ADLEZ": 4}
TEXT = {2: ["DID YOU ACTUALLY", "THINK THAT WOULD WORK"], 3: ["OK YOU WANTED DOOM,", "YOU GOT IT!"],
        4: ["YOU EARNED IT,", "YOU TRULY ARE A HERO!"],
        "E4": ["M-D O-A K-L J-N", "Z NEVER CHANGES"], "D10": ["H-E I-U J-N", "S STAYS THE SAME"]}   # (the font
                                        # has no "=": a dash)
E4, D10 = 0x43, 0x39
BUSH = (12, 4)                          # (owner: the bush above the right pair's lower one, both fountains)
EXIT_COL, EXIT_ROW = 7, 1               # out above the pond
EXTRA, BAIT_BOUGHT = 0x7F47, 0x04       # (lol_uptable's EXTRA: cleared for a new file) bait bought once
LASTU = 0x014F                          # (stack page, untouched) the screen last seen (UNSEED's fountains)
ATTR_B = 0x68FE
HINT_DEST = 0x15
CAVE_WARES, CAVE_PRICES = 0x6A7E, 0x6ABA
BAIT_ITEM, BAIT_PRICE = 0x04, 60
PLAY = 0x6530
WORLD_FLAGS = 0x6BAF
OLD_MEN = (0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F, 0x70, 0x72, 0x73, 0x75, 0x76)
HVE = 0x016F
# !ADLEZ (owner 2026-11-25): the hero's start (once: EXTRA's GRANTED), the wood sword cave's magical sword, a red ring
# and a book in every shop (5 rupees), full XP, and G7's cave a free upgrade cave until 3 are taken (EXTRA's AD_N)
GRANTED, AD_N = 0x08, 0x30              # (EXTRA's bits; AD_N counts by $10)
ORIG = 0x016B                           # (stack page, unused) G7's own cave value while it is the free one
G7, UPDEST = 0x66, 0x1C                 # (UPDEST: lol_upgrades' SHOPS[0] cave 12, person $76)
WOOD_MAN, MAGIC_SWORD = 0x6A, 0x03
RED_RING, BOOK, CHEAP = 0x13, 0x11, 5
START = ((0x0664, 1), (0x067C, 20), (0x0658, 20), (0x065B, 2), (0x065A, 1), (0x0659, 2), (0x0660, 1),
         (0x065C, 1), (0x0665, 1), (0x0663, 1), (0x065D, 1), (0x0674, 1))
#        magic key, most bombs, bombs, red candle, bow, silver arrows, raft, recorder, bracelet, ladder, bait, boomerang
XP_LABELS = {}                          # lol_build's XP helper's labels (set by lol_build)
TILES = {**{c: 0x0A + i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}, **{str(d): d for d in range(10)},
         " ": BLANK, "!": 0x29}


def tiles(word):
    return bytes(TILES[c] for c in word.ljust(8))


HVE_FAR_AT = [None]                     # lol_build's JSR (bank 5) to the stub that far-calls "hve": patched here


_LIB = {}
_LIB6 = {}                              # (bank 6: !ADLEZ's parts)


def put6(rom, n, lo=0x9D66, hi=0xA000):
    """Reserve n bytes in bank 6's free run (best fit, $FF margins of 2); the caller places the code."""
    base = BANK(6) - 0x8000
    best, c = None, lo
    while c < hi:
        if rom[base + c] != 0xFF:
            c += 1
            continue
        e = c
        while e < hi and rom[base + e] == 0xFF:
            e += 1
        if e - c - 4 >= n and (best is None or e - c < best[1]):
            best = (c + 2, e - c)
        c = e
    assert best, f"no {n} bytes free in bank 6"
    rom[base + best[0]:base + best[0] + n] = bytes(n)        # (taken: placed over by the caller)
    return best[0]


def lib(rom):
    """Bank 3: namek and the old men's words."""
    if "namek" in _LIB:
        return _LIB
    import lol_fixed
    from lol_newups import put3_best as put3
    from lol_saveblock import HINT_BUF
    import lol_modes
    import sys
    import lolpaths
    for p in (lolpaths.ZORA, lolpaths.Q3B):
        if p not in sys.path:
            sys.path.insert(0, p)
    from zora.rom.serialize.text import _encode_quote
    import build_mock as base
    # the words, packed (cpy pads each to 80 with zeros): 0 ZELDA, 1 IDDQD, 2 !ADLEZ, 3 E4, 4 D10
    tx, toff, tlen = b"", [], []
    for k in (2, 3, 4, "E4", "D10"):
        t = bytes(_encode_quote(base.centered(TEXT[k])))
        assert 0 < len(t) <= 80
        toff.append(len(tx)); tlen.append(len(t)); tx += t
    assert len(tx) < 256
    order = sorted(WORDS, key=WORDS.get)
    import lol_v3core as V

    def build6(o, L3):
        """Bank 6 ($9D66-, free in every finished ROM): !ADLEZ's parts (bank 3 is full)."""
        a = Asm(o)
        namek(a)
        # !ADLEZ: the hero's start, once
        a.label("a_on").abs(0xAD, EXTRA).b(0x29, GRANTED).br(0xD0, "a_r")
        for addr, v in START:
            a.b(0xA9, v).abs(0x8D, addr)
        a.abs(0xAD, EXTRA).b(0x09, GRANTED).abs(0x8D, EXTRA)
        a.label("a_r").b(0x60)
        # !ADLEZ's caves (InitCave's fill): shops: a red ring (first place) and a book (third), 5 rupees each; the
        # wood sword cave's old man: the hero's words, and the magical sword
        a.label("adl").b(0xA6, 0xEB).abs(0xBD, ATTR_B).b(0x4A, 0x4A, 0x38, 0xE9, 0x10).br(0x90, "a_x")
        a.b(0x85, 0x0E, 0x0A, 0x65, 0x0E, 0xAA)                                  # X: 3 * cave
        a.abs(0xAD, 0x0350).b(0xC9, WOOD_MAN).br(0xF0, "a_ws")
        a.b(0xA5, 0x0E, 0xC9, 0x0D).br(0x90, "a_x").b(0xC9, 0x11).br(0xB0, "a_x")   # (shops: caves $0D-$10)
        a.abs(0xBD, CAVE_WARES).b(0x29, 0xC0, 0x09, RED_RING).abs(0x9D, CAVE_WARES)
        a.abs(0xBD, CAVE_WARES + 2).b(0x29, 0xC0, 0x09, BOOK).abs(0x9D, CAVE_WARES + 2)
        a.b(0xA9, CHEAP).abs(0x9D, CAVE_PRICES).abs(0x9D, CAVE_PRICES + 2)
        a.label("a_x").abs(0x20, "adfree").br(0xF0, "a_x2").b(0xA9, 0x00)            # G7's free cave: prices 0
        for k in range(3):
            a.abs(0x8D, CAVE_PRICES + 3 * (UPDEST - 0x10) + k)
        a.label("a_x2").b(0x60)
        a.label("a_ws").abs(0xBD, CAVE_WARES + 1).b(0x29, 0xC0, 0x09, MAGIC_SWORD).abs(0x9D, CAVE_WARES + 1)
        a.b(0xA2, 2).b(*V.far(3, L3["cpy"])).b(0x60)
        # G7 (bank 5's HandleWarpOW hook, A its cave value): !ADLEZ, under 3 taken: the upgrade cave UPDEST
        a.label("g7").b(0x48).abs(0x20, "namek").b(0xC9, 0x04).br(0xD0, "g_n").b(0xA5, 0xEB, 0xC9, G7).br(0xD0, "g_n")
        a.abs(0xAD, EXTRA).b(0x29, AD_N, 0xC9, AD_N).br(0xF0, "g_rs")
        a.abs(0xAD, 0x067F + G7).b(0x29, 0xEF).abs(0x8D, 0x067F + G7)            # (never "taken": rolled anew)
        a.b(0x68, 0x48, 0x29, 0xFC, 0xC9, 0x40).br(0x90, "g_n").b(0xC9, UPDEST << 2).br(0xF0, "g_n")
        a.b(0x68).abs(0x8D, ORIG).b(0x29, 0x03, 0x09, UPDEST << 2).abs(0x8D, ATTR_B + G7).b(0x60)
        # (3 taken: G7's own cave back)
        a.label("g_rs").b(0x68, 0x48, 0x29, 0xFC, 0xC9, UPDEST << 2).br(0xD0, "g_n")
        a.abs(0xAD, ORIG).b(0x29, 0xFC, 0xC9, 0x40).br(0x90, "g_n").b(0xC9, UPDEST << 2).br(0xF0, "g_n")
        a.b(0x68).abs(0xAD, ORIG).abs(0x8D, ATTR_B + G7).b(0xA9, 0x00).abs(0x8D, ORIG).abs(0xAD, ATTR_B + G7).b(0x60)
        a.label("g_n").b(0x68, 0x60)
        # adfree: A = 1 (Z clear) in G7's free upgrade cave (!ADLEZ, under 3 taken, the overworld's cave)
        a.label("adfree").abs(0x20, "namek").b(0xC9, 0x04).br(0xD0, "af_0").b(0xA5, 0x10).br(0xD0, "af_0")
        a.b(0xA5, 0xEB, 0xC9, G7).br(0xD0, "af_0").abs(0xAD, EXTRA).b(0x29, AD_N, 0xC9, AD_N).br(0xF0, "af_0")
        a.b(0xA9, 0x01, 0x60)
        a.label("af_0").b(0xA9, 0x00, 0x60)
        a.label("adinc").abs(0xAD, EXTRA).b(0x18, 0x69, 0x10).abs(0x8D, EXTRA).b(0x60)
        # full XP (lol_build's XP helper, its STA TMP at calc): C set: !ADLEZ
        a.label("xpf").abs(0x20, "namek").b(0xC9, 0x04).br(0xF0, "x_y").b(0x18, 0x60)
        a.label("x_y").b(0x38, 0x60)
        a.label("words").b(*b"".join(tiles(w) for w in order))
        return a

    def namek(a):
        a.label("namek").b(0x8A, 0x48, 0x98, 0x48)
        if lol_fixed.FIXED:
            a.b(0xA9, 0x00).br(0xF0, "k_out")
        else:
            a.b(0xA9, len(order), 0x85, 0x0E)                   # (k, from the last)
            a.label("k_w").b(0xA5, 0x0E, 0x38, 0xE9, 0x01, 0x0A, 0x0A, 0x0A, 0xA8)   # Y: the word's tiles
            a.b(0xA5, 0x16, 0x0A, 0x0A, 0x0A, 0xAA, 0xA9, 0x08, 0x85, 0x0F)
            a.label("k_l").abs(0xBD, NAMES).abs(0xD9, "words").br(0xD0, "k_nx").b(0xE8, 0xC8, 0xC6, 0x0F)
            a.br(0xD0, "k_l").b(0xA5, 0x0E).br(0xD0, "k_out")
            a.label("k_nx").b(0xC6, 0x0E).br(0xD0, "k_w").b(0xA9, 0x00)
        a.label("k_out").b(0x85, 0x0E, 0x68, 0xA8, 0x68, 0xAA, 0xA5, 0x0E, 0x60)

    def build(o):
        a = Asm(o)
        namek(a)
        # InitCave's fill, after the others (A: $0350; C set kept by the stub): UNSEED's shops and fountains;
        # ZELDA / IDDQD old men's words
        a.label("fill").abs(0x20, "namek").b(0xC9, 0x01).br(0xD0, "f_zi").abs(0x4C, "uns")
        a.label("f_zi").b(0xC9, 0x04).br(0xD0, "f_z2").b(*V.far(6, L6["adl"])).b(0x60)
        a.label("f_z2").b(0xC9, 0x02).br(0x90, "f_r").b(0xC9, 0x04).br(0xB0, "f_r")
        a.b(0x38, 0xE9, 0x02, 0x48)
        a.abs(0xAD, 0x0350).b(0xA2, len(OLD_MEN) - 1)
        a.label("f_o").abs(0xDD, "olds").br(0xF0, "f_y").b(0xCA).br(0x10, "f_o").b(0x68, 0x60)
        a.label("f_y").b(0x68, 0xAA)
        # cpy: words X (0-4) into HINT_BUF, zeros after; the hint cave's quote
        a.label("cpy").abs(0xBC, "toff").abs(0xBD, "tlen").b(0x85, 0x0F, 0xA2, 0x00)
        a.label("c_l").abs(0xB9, "tx").abs(0x9D, HINT_BUF).b(0xC8, 0xE8, 0xC6, 0x0F).br(0xD0, "c_l")
        a.b(0xA9, 0x00)
        a.label("c_z").abs(0x9D, HINT_BUF).b(0xE8, 0xE0, 80).br(0xD0, "c_z")
        a.b(0xA9, lol_modes.HINT_SEL).abs(0x8D, lol_modes.QOVR)
        a.label("f_r").b(0x60)
        # UNSEED: a shop (its cave $1D-$20) sells bait in its third place until bait was bought once; the fountains'
        # caves (E4, D10) are hint caves with the ciphers' keys
        a.label("uns").b(0xA6, 0xEB).abs(0xBD, ATTR_B).b(0x4A, 0x4A, 0xC9, 0x1D).br(0x90, "u_ft").b(0xC9, 0x21)
        a.br(0xB0, "u_ft").abs(0xAD, EXTRA).b(0x29, BAIT_BOUGHT).br(0xD0, "u_r")
        a.abs(0xBD, ATTR_B).b(0x4A, 0x4A, 0x38, 0xE9, 0x10, 0x85, 0x0E, 0x0A, 0x65, 0x0E, 0xAA)   # X: 3 * cave
        a.abs(0xBD, CAVE_WARES + 2).b(0x29, 0xC0, 0x09, BAIT_ITEM).abs(0x9D, CAVE_WARES + 2)
        a.b(0xA9, BAIT_PRICE).abs(0x9D, CAVE_PRICES + 2)
        a.label("u_r").b(0x60)
        a.label("u_ft").b(0xA5, 0xEB, 0xA2, 3, 0xC9, E4).br(0xF0, "u_t").b(0xA2, 4, 0xC9, D10).br(0xD0, "u_r")
        a.label("u_t").abs(0x4C, "cpy")
        # every frame of play (lol_upgrades' frame hook): UNSEED's bait bought, and its fountains: in E4 / D10 the
        # cave is a hint cave; the poison bait set down by the bush (12, 4) is eaten (bait gone, as the hungry Goriya
        # eats it) and the bush is stairs, found for good (the screen's secret flag); written again on coming back
        T_PLAY = PLAY + BUSH[0] * 44 + BUSH[1] * 2
        ppu = 0x2100 + BUSH[1] * 64 + 2 * BUSH[0]
        a.label("frame").abs(0x20, "namek").b(0xC9, 0x04).br(0xD0, "fr_1").b(*V.far(6, L6["a_on"])).b(0x60)
        a.label("fr_1").b(0xC9, 0x01).br(0xD0, "fr_r").abs(0x4C, "u_on")
        a.label("fr_r").b(0x60)
        a.label("u_on").abs(0xAD, 0x065D).br(0xF0, "u_nb").abs(0xAD, EXTRA).b(0x09, BAIT_BOUGHT).abs(0x8D, EXTRA)
        a.label("u_nb").b(0xA5, 0x10).br(0xD0, "u_x0").b(0xA5, 0x12, 0xC9, 0x05).br(0xD0, "u_x0")
        a.b(0xA5, 0xEB, 0xC9, E4).br(0xF0, "u_here").b(0xC9, D10).br(0xF0, "u_here")
        a.label("u_x0").b(0xA9, 0xFF).abs(0x8D, LASTU)
        a.label("u_x").b(0x60)
        a.label("u_here").b(0xA6, 0xEB).abs(0xBD, ATTR_B).b(0x29, 0x03, 0x09, HINT_DEST << 2).abs(0x9D, ATTR_B)
        a.abs(0xAD, WORLD_FLAGS).b(0x85, 0x0C).abs(0xAD, WORLD_FLAGS + 1).b(0x85, 0x0D)
        a.b(0xA4, 0xEB, 0xB1, 0x0C, 0x29, 0x80).br(0xF0, "u_look")
        a.b(0xA5, 0xEB).abs(0xCD, LASTU).br(0xF0, "u_x").abs(0x8D, LASTU).abs(0x4C, "u_wsq")
        a.label("u_look").b(0xA5, 0xEB).abs(0x8D, LASTU)
        import lol_uptable as UT
        pb = UT.bit("poison bait")
        a.abs(0xAD, pb[0]).b(0x29, pb[1]).br(0xF0, "u_x")
        a.b(0xA5, 0xAC + 0x0F).br(0xF0, "u_x")
        a.b(0xA5, 0x70 + 0x0F, 0x38, 0xE9, BUSH[0] * 16).br(0xB0, "u_a1").b(0x49, 0xFF, 0x69, 0x01)
        a.label("u_a1").b(0xC9, 0x14).br(0xB0, "u_x")
        a.b(0xA5, 0x84 + 0x0F, 0x38, 0xE9, (0x40 + BUSH[1] * 16) & 0xFF).br(0xB0, "u_a2").b(0x49, 0xFF, 0x69, 0x01)
        a.label("u_a2").b(0xC9, 0x14).br(0xB0, "u_x")
        # eaten: the bait gone, its object gone; found; the secret sound
        a.b(0xA9, 0x00).abs(0x8D, 0x065D).b(0x85, 0xAC + 0x0F)
        a.b(0xA4, 0xEB, 0xB1, 0x0C, 0x09, 0x80, 0x91, 0x0C).b(0xA9, 0x04).abs(0x8D, 0x0602)
        a.label("u_wsq")
        for k, tile in zip((0, 1, 22, 23), (0x70, 0x71, 0x72, 0x73)):
            a.b(0xA9, tile).abs(0x8D, T_PLAY + k)
        a.abs(0xAC, 0x0301)
        a.b(0xA9, ppu >> 8).abs(0x99, 0x0302).abs(0x99, 0x0307)
        a.b(0xA9, ppu & 0xFF).abs(0x99, 0x0303).b(0xA9, (ppu + 32) & 0xFF).abs(0x99, 0x0308)
        a.b(0xA9, 0x02).abs(0x99, 0x0304).abs(0x99, 0x0309)
        a.b(0xA9, 0x70).abs(0x99, 0x0305).b(0xA9, 0x72).abs(0x99, 0x0306)
        a.b(0xA9, 0x71).abs(0x99, 0x030A).b(0xA9, 0x73).abs(0x99, 0x030B)
        a.b(0xA9, 0xFF).abs(0x99, 0x030C).b(0x98, 0x18, 0x69, 0x0A).abs(0x8D, 0x0301).b(0x60)
        # IDDQD: HVE $FF (lol_build's status bar code far-calls this every frame, after setting HVE)
        a.label("hve").abs(0xAD, 0x7FF8).br(0xF0, "h_0").b(0xA9, 0x30)          # (as lol_build's: hard + 3)
        a.label("h_0").b(0x18).abs(0x6D, 0x066F).br(0x90, "h_1").b(0xA9, 0xFF)
        a.label("h_1").abs(0x8D, HVE).abs(0x20, "namek").b(0xC9, 0x03).br(0xD0, "h_r").b(0xA9, 0xFF).abs(0x8D, HVE)
        a.label("h_r").b(0x60)
        a.label("olds").b(*OLD_MEN)
        a.label("words").b(*b"".join(tiles(w) for w in order))
        a.label("tx").b(*tx)
        a.label("toff").b(*toff)
        a.label("tlen").b(*tlen)
        return a
    d6 = build6(0x8000, {"cpy": 0x8000})
    at6 = put6(rom, len(d6.bytes()))
    L6 = {k: at6 + v - 0x8000 for k, v in d6.labels.items()}
    a = put3(rom, build)
    _LIB.update(a.labels)
    b6 = build6(at6, a.labels)
    assert len(b6.bytes()) == len(d6.bytes())
    o6 = BANK(6) + at6 - 0x8000
    rom[o6:o6 + len(b6.bytes())] = b6.bytes()
    _LIB6.update(b6.labels)
    return _LIB


def apply(rom: bytearray, notes: list) -> None:
    import lol_fixed
    if lol_fixed.FIXED:
        return
    import lol_v3core as V
    from lol_newups import free_in
    L = lib(rom)
    OW = 0x18410
    for room in (E4, D10):                                                  # out above the pond (UNSEED's caves)
        rom[OW + room] = (EXIT_COL << 4) | (rom[OW + room] & 0x0F)
        rom[OW + 0x280 + room] = (rom[OW + 0x280 + room] & 0xF8) | EXIT_ROW
    f1 = BANK(1) + 0x85F9 - 0x8000
    assert rom[f1] == 0x20
    old_fill = rom[f1 + 1] | rom[f1 + 2] << 8

    def bstub(o):
        a = Asm(o)
        a.label("fill").abs(0x20, old_fill).b(0x48).b(*V.far(3, L["fill"])).b(0x68, 0x38, 0x60)
        return a
    sa = free_in(rom, 1, len(bstub(0x8000).bytes()), 0xB000)
    place(rom, 1, sa, bstub(sa).bytes())
    rom[f1 + 1:f1 + 3] = bytes([sa & 0xFF, sa >> 8])
    at = HVE_FAR_AT[0]
    assert at is not None
    o = BANK(5) + at - 0x8000
    assert rom[o:o + 3] == bytes([0x20, 0xFF, 0xFF])
    hs = free_in(rom, 5, 8, 0xA000, 0xBE40)
    place(rom, 5, hs, V.far(3, L["hve"]) + bytes([0x60]))
    rom[o + 1:o + 3] = bytes([hs & 0xFF, hs >> 8])
    # !ADLEZ: full XP. The XP helper's STA TMP (at calc) -> JSR xpst: STA TMP; with !ADLEZ: the full value, added
    XL = XP_LABELS
    calc = BANK(4) + XL["calc"] - 0x8000
    tmp = XL["TMP"]
    assert rom[calc:calc + 3] == bytes([0x8D, tmp & 0xFF, tmp >> 8])

    def xst(o):
        a = Asm(o)
        a.label("xpst").abs(0x8D, tmp).b(*V.far(6, _LIB6["xpf"])).br(0xB0, "full").b(0x60)
        a.label("full").b(0x68, 0x68).abs(0xAD, tmp).abs(0x4C, XL["add"])
        return a
    xs = free_in(rom, 4, len(xst(0xB000).bytes()), 0xB000, 0xBE00)
    place(rom, 4, xs, xst(xs).bytes())
    rom[calc:calc + 3] = bytes([0x20, xs & 0xFF, xs >> 8])
    # !ADLEZ: G7's cave (lol_entrances' HandleWarpOW hook: ... LDY RoomId / LDA LevelBlockAttrsB,Y / RTS)
    import lol_entrances as EN
    h5 = BANK(5) + EN.HOOK5 - 0x8000
    assert rom[h5 + 7:h5 + 13] == bytes([0xA4, 0xEB, 0xB9, 0xFE, 0x68, 0x60]), rom[h5:h5 + 13].hex()

    def g5(o):
        a = Asm(o)
        a.abs(0xB9, ATTR_B).b(*V.far(6, _LIB6["g7"])).b(0xA4, 0xEB, 0x60)
        return a
    gs = free_in(rom, 5, len(g5(0xA000).bytes()), 0x8000, 0xBD50)
    place(rom, 5, gs, g5(gs).bytes())
    rom[h5 + 9:h5 + 12] = bytes([0x4C, gs & 0xFF, gs >> 8])
    notes.append(f"names (unseeded): ZELDA / IDDQD old men (bank 3 ${L['namek']:04X})")

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
TILES = {**{c: 0x0A + i for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}, **{str(d): d for d in range(10)},
         " ": BLANK, "!": 0x29}


def tiles(word):
    return bytes(TILES[c] for c in word.ljust(8))


HVE_FAR_AT = [None]                     # lol_build's JSR (bank 5) to the stub that far-calls "hve": patched here


_LIB = {}


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
    texts, ftexts = b"", b""
    for k in (2, 3):
        t = bytes(_encode_quote(base.centered(TEXT[k])))
        texts += t + bytes(80 - len(t))
    for k in ("E4", "D10"):
        t = bytes(_encode_quote(base.centered(TEXT[k])))
        ftexts += t + bytes(80 - len(t))
    order = sorted(WORDS, key=WORDS.get)

    def build(o):
        a = Asm(o)
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
        # InitCave's fill, after the others (A: $0350; C set kept by the stub): UNSEED's shops and fountains;
        # ZELDA / IDDQD old men's words
        a.label("fill").abs(0x20, "namek").b(0xC9, 0x01).br(0xD0, "f_zi").abs(0x4C, "uns")
        a.label("f_zi").b(0xC9, 0x02).br(0x90, "f_r").b(0xC9, 0x04).br(0xB0, "f_r")
        a.b(0x38, 0xE9, 0x02, 0x48)
        a.abs(0xAD, 0x0350).b(0xA2, len(OLD_MEN) - 1)
        a.label("f_o").abs(0xDD, "olds").br(0xF0, "f_y").b(0xCA).br(0x10, "f_o").b(0x68, 0x60)
        a.label("f_y").b(0x68).br(0xF0, "f_0").b(0xA0, 80).br(0xD0, "f_c")
        a.label("f_0").b(0xA0, 0x00)
        a.label("f_c")
        a.label("f_cp").b(0xA2, 0x00)
        a.label("f_l").abs(0xB9, "texts").abs(0x9D, HINT_BUF).b(0xC8, 0xE8, 0xE0, 80).br(0xD0, "f_l")
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
        a.label("u_ft").b(0xA5, 0xEB, 0xA0, 0, 0xC9, E4).br(0xF0, "u_t").b(0xA0, 80, 0xC9, D10).br(0xD0, "u_r")
        a.label("u_t").b(0xA2, 0x00)
        a.label("u_l").abs(0xB9, "ftexts").abs(0x9D, HINT_BUF).b(0xC8, 0xE8, 0xE0, 80).br(0xD0, "u_l")
        a.b(0xA9, lol_modes.HINT_SEL).abs(0x8D, lol_modes.QOVR).b(0x60)
        # every frame of play (lol_upgrades' frame hook): UNSEED's bait bought, and its fountains: in E4 / D10 the
        # cave is a hint cave; the poison bait set down by the bush (12, 4) is eaten (bait gone, as the hungry Goriya
        # eats it) and the bush is stairs, found for good (the screen's secret flag); written again on coming back
        T_PLAY = PLAY + BUSH[0] * 44 + BUSH[1] * 2
        ppu = 0x2100 + BUSH[1] * 64 + 2 * BUSH[0]
        a.label("frame").abs(0x20, "namek").b(0xC9, 0x01).br(0xF0, "u_on").b(0x60)
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
        a.label("texts").b(*texts)
        a.label("ftexts").b(*ftexts)
        return a
    a = put3(rom, build)
    _LIB.update(a.labels)
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
    notes.append(f"names (unseeded): ZELDA / IDDQD old men (bank 3 ${L['namek']:04X})")

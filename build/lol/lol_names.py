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
TEXT = {2: ["DID YOU ACTUALLY", "THINK THAT WOULD WORK"], 3: ["OK YOU WANTED DOOM,", "YOU GOT IT!"]}
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
    from lol_newups import put3
    from lol_saveblock import HINT_BUF
    import lol_modes
    import sys
    import lolpaths
    for p in (lolpaths.ZORA, lolpaths.Q3B):
        if p not in sys.path:
            sys.path.insert(0, p)
    from zora.rom.serialize.text import _encode_quote
    import build_mock as base
    texts = b""
    for k in (2, 3):
        t = bytes(_encode_quote(base.centered(TEXT[k])))
        texts += t + bytes(80 - len(t))
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
        # InitCave's fill, after the others (A: $0350; C set kept by the stub): ZELDA / IDDQD old men's words
        a.label("fill").abs(0x20, "namek").b(0xC9, 0x02).br(0x90, "f_r").b(0xC9, 0x04).br(0xB0, "f_r")
        a.b(0x38, 0xE9, 0x02, 0x48)
        a.abs(0xAD, 0x0350).b(0xA2, len(OLD_MEN) - 1)
        a.label("f_o").abs(0xDD, "olds").br(0xF0, "f_y").b(0xCA).br(0x10, "f_o").b(0x68, 0x60)
        a.label("f_y").b(0x68).br(0xF0, "f_0").b(0xA0, 80).br(0xD0, "f_c")
        a.label("f_0").b(0xA0, 0x00)
        a.label("f_c").b(0xA2, 0x00)
        a.label("f_l").abs(0xB9, "texts").abs(0x9D, HINT_BUF).b(0xC8, 0xE8, 0xE0, 80).br(0xD0, "f_l")
        a.b(0xA9, lol_modes.HINT_SEL).abs(0x8D, lol_modes.QOVR)
        a.label("f_r").b(0x60)
        # IDDQD: HVE $FF (lol_build's status bar code far-calls this every frame, after setting HVE)
        a.label("hve").abs(0xAD, 0x7FF8).br(0xF0, "h_0").b(0xA9, 0x30)          # (as lol_build's: hard + 3)
        a.label("h_0").b(0x18).abs(0x6D, 0x066F).br(0x90, "h_1").b(0xA9, 0xFF)
        a.label("h_1").abs(0x8D, HVE).abs(0x20, "namek").b(0xC9, 0x03).br(0xD0, "h_r").b(0xA9, 0xFF).abs(0x8D, HVE)
        a.label("h_r").b(0x60)
        a.label("olds").b(*OLD_MEN)
        a.label("words").b(*b"".join(tiles(w) for w in order))
        a.label("texts").b(*texts)
        return a
    a = put3(rom, 3, build)
    _LIB.update(a.labels)
    return _LIB


def apply(rom: bytearray, notes: list) -> None:
    import lol_fixed
    if lol_fixed.FIXED:
        return
    import lol_v3core as V
    from lol_newups import free_in
    L = lib(rom)
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

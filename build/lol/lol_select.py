"""v2.02: fast text, and Select steps the B item instead of pausing.

Text: the person-text delay (bank 1 $881D, LDA #$06 / STA $29) becomes 2 frames a letter, ZORA's fast text.

Select: bank 7 $EC36 toggled the pause flag ($E0) on Select. Now it far-calls SEL5 in bank 5 (lol_v3core's FAR, back
to the bank that was in). SEL5 moves the B item to the next
one Link can use with the item screen's own cursor routine (bank 5 $B7C8: A = direction 1 right, Y = the slot; it
skips empty slots, the bow, arrows without a bow, and handles the boomerangs and the letter/potion slot), silently.
"""
from lol_af import Asm, place, patch, BANK

BROWN = ("F7", "G11", "C9")     # screens whose inner bushes are brown (the inner palette: 3, the rocks' brown)
ALL_BROWN = ("F7",)             # ... and the outer ring too: every bush and rock on the screen brown
TEXT_DELAY = 0x881D             # bank 1: LDA #$06 / STA $29 (operand)
SEL5 = 0xAE40                   # bank 5 free
SWITCH = 0xFFAC
CURSOR = 0xB7C8                 # bank 5: the item screen's cursor move


def apply(rom: bytearray, notes: list) -> None:
    patch(rom, 1, TEXT_DELAY - 1, bytes([0xA9, 0x06, 0x85, 0x29]), bytes([0xA9, 0x02, 0x85, 0x29]))

    s = Asm(SEL5)
    s.b(0xA5, 0xEF, 0x48)                                               # (the menu's last direction: kept)
    s.abs(0xAC, 0x0656).b(0xC0, 0x0F).br(0xD0, "s_y").b(0xA0, 0x07)    # the letter's slot: the potion's
    s.label("s_y").b(0xA9, 0x01).abs(0x20, CURSOR)                       # (no sound)
    s.b(0x68, 0x85, 0xEF, 0x60)
    place(rom, 5, SEL5, s.bytes())

    # Select: the B item, not the pause (LDA $E0 / EOR #1 / STA $E0 / BNE / LDA #$0F / STA $4015): a far call
    from lol_v3core import far
    patch(rom, 7, 0xEC3C, bytes.fromhex("a5e0490185e0d005a90f8d1540"), far(5, SEL5) + bytes([0x4C, 0x49, 0xEC]))
    # brown bushes: F7 (6), G11 (2), C9 (4) - those screens' inner palette brown
    from lol_af import screen
    OW = 0x18410
    for n in BROWN:
        rom[OW + 0x80 + screen(n)] = (rom[OW + 0x80 + screen(n)] & 0xFC) | 3
    for n in ALL_BROWN:
        rom[OW + screen(n)] = (rom[OW + screen(n)] & 0xFC) | 3
    # the candle's fire on a secret bush (bank 4 UpdateTree's JSR CheckTileObjWeaponCollision at $8F2D, X the
    # tile object): the blue candle burns only brown bushes - the bush's palette (the screen's outer ring, 2
    # squares wide: attribute A's, else the inner: attribute B's) is 3, the brown; the red candle any. Z set: no burn.
    b4 = BANK(4) - 0x8000
    burn = next(c for c in range(0xB000, 0xBF00) if all(x == 0xFF for x in rom[b4 + c - 2:b4 + c + 64]))
    b = Asm(burn)
    b.abs(0xAD, 0x065B).b(0xC9, 0x02).br(0xB0, "bn_go").b(0x98, 0x48)
    b.b(0xB5, 0x70, 0xC9, 0x20).br(0x90, "bn_o").b(0xC9, 0xE0).br(0xB0, "bn_o")
    b.b(0xB5, 0x84, 0xC9, 0x60).br(0x90, "bn_o").b(0xC9, 0xD0).br(0xB0, "bn_o")
    b.b(0xA4, 0xEB).abs(0xB9, 0x68FE).br(0xD0, "bn_p").br(0xF0, "bn_p")
    b.label("bn_o").b(0xA4, 0xEB).abs(0xB9, 0x687E)
    b.label("bn_p").b(0x29, 0x03, 0xC9, 0x03).br(0xF0, "bn_y")
    b.b(0x68, 0xA8, 0xA9, 0x00, 0x60)
    b.label("bn_y").b(0x68, 0xA8)
    b.label("bn_go").abs(0x4C, 0x8F3F)
    assert len(b.bytes()) <= 62
    place(rom, 4, burn, b.bytes())
    patch(rom, 4, 0x8F2D, bytes([0x20, 0x3F, 0x8F]), bytes([0x20, burn & 0xFF, burn >> 8]))
    notes.append("v2.02: text 2 frames a letter (ZORA fast text); Select steps the B item (no pause)")

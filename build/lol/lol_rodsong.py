"""Legend of Link: the divining rod and the song of chaos (owner, 2026-11-24; upgrades in lol_uptable).

Divining rod (100, tier 2; needs the wand, never with the boomstick):
- the wand is drawn in Link's colors, a wooden stick: in the hand (bank 7 $F7E6, the rod's ORA #$01 palette: a hook
  keeps palette 0) and as an item (lol_books' pal: the wand's slot, 8, palette 0);
- it only stabs: the rod's shot (bank 7 $F816, CPX #$12 before making the magic shot in slot $0E) is never made;
- its stab does 1 less ($10; lol_upgrades' sword hook: weapon slot $00 = $12), never below $10;
- every level's and shrine's compass comes with it (lol_upgrades' take, as the map master's maps).

Song of chaos (25, tier 1; needs the recorder): playing the recorder on the overworld always calls the whirlwind (bank 1
$A0B1: no triforce needed, no level picked), and it sets Link down on a random screen of lol_entrances' SAFE_Y (not
in the first column: the whirlwind comes from the screen to the left): at $A06D (the screen before, from WL) a random
index (RNG $18) goes in $0523, the whirlwind's destination, and the screen comes from the list; at $A135 (the drop
height, from WY) the list's height."""
from lol_af import Asm, BANK, place, patch

COMMON = 0xBEBD                         # free in banks 0-6 (after bank 5's status-bar code)


def apply(rom: bytearray, notes: list) -> None:
    import lol_v3core as V
    import lol_uptable as T
    from lol_entrances import SAFE_Y
    from lol_af import screen
    from lol_newups import free_in
    rod, chaos = T.bit("divining rod"), T.bit("song of chaos")
    # --- the rod: its palette in the hand, no shot
    # (bank 7 is full: both hooks in the common area, the same bytes in banks 0-6: whichever bank is in)
    c = Asm(COMMON)
    c.label("pal").b(0x48).abs(0xAD, rod[0]).b(0x29, rod[1]).br(0xF0, "blue")
    c.b(0x68).abs(0x4C, 0xF7F2).label("blue").b(0x68, 0x09, 0x01).abs(0x4C, 0xF7F2)
    c.label("shot").b(0xE0, 0x12).br(0xF0, "rod").b(0x68, 0x68).abs(0x4C, 0xF85A)
    c.label("rod").abs(0xAD, rod[0]).b(0x29, rod[1]).br(0xF0, "go").b(0x68, 0x68)
    c.label("go").b(0x60)
    code = c.bytes()
    for bank in range(7):
        place(rom, bank, COMMON, code)
    pal, shot = c.labels["pal"], c.labels["shot"]
    patch(rom, 7, 0xF7E6, bytes([0x09, 0x01, 0x4C, 0xF2, 0xF7]), bytes([0x4C, pal & 0xFF, pal >> 8, 0xEA, 0xEA]))
    patch(rom, 7, 0xF816, bytes([0xE0, 0x12, 0xD0, 0x40]), bytes([0x20, shot & 0xFF, shot >> 8, 0xEA]))
    # --- the song of chaos (bank 1)
    spots = sorted((screen(n), y) for n, y in SAFE_Y.items() if screen(n) % 16)
    assert len(spots) < 128

    def build(org):
        a = Asm(org)
        a.label("call").abs(0xAD, chaos[0]).b(0x29, chaos[1]).br(0xD0, "c_go").abs(0xAD, 0x0523).b(0x60)
        a.label("c_go").b(0x68, 0x68).abs(0x4C, 0xA0E0)                       # (straight to the whirlwind)
        a.label("prev").abs(0xAD, chaos[0]).b(0x29, chaos[1]).br(0xD0, "p_go").abs(0xB9, 0x7F90).b(0x60)
        a.label("p_go").b(0xA5, 0x18)
        a.label("p_m").b(0xC9, len(spots)).br(0x90, "p_k").b(0xE9, len(spots)).br(0xB0, "p_m")
        a.label("p_k").abs(0x8D, 0x0523).b(0xA8).abs(0xB9, "s_prev").b(0x60)
        a.label("dropy").abs(0xAD, chaos[0]).b(0x29, chaos[1]).br(0xD0, "y_go").abs(0xB9, 0x7F98).b(0x60)
        a.label("y_go").abs(0xAC, 0x0523).abs(0xB9, "s_y").b(0x60)
        a.label("s_prev").b(*[s - 1 for s, y in spots])
        a.label("s_y").b(*[y for s, y in spots])
        return a
    n = len(build(0x8000).bytes())
    at = free_in(rom, 1, n, 0x8000, 0xA500)
    a = build(at)
    place(rom, 1, at, a.bytes())
    L = a.labels
    j = lambda k: bytes([0x20, L[k] & 0xFF, L[k] >> 8])
    patch(rom, 1, 0xA0B1, bytes([0xAD, 0x23, 0x05]), j("call"))
    patch(rom, 1, 0xA06D, bytes([0xB9, 0x90, 0x7F]), j("prev"))
    patch(rom, 1, 0xA135, bytes([0xB9, 0x98, 0x7F]), j("dropy"))
    notes.append(f"divining rod (common ${pal:04X} / ${shot:04X}); song of chaos: {len(spots)} screens "
                 f"(bank 1 ${at:04X}, {n} bytes)")

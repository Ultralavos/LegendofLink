"""Legend of Link: the red Gleeok (12+ heart containers as enemies see them: HVE; planned 2026-11-23, built 2026-11-24).

Red (sprite palette 3, the level's, sent turned red every 16 frames while it's on screen), the same health, its fireballs as before. Every 120-240
frames (random) two of the heads still on their necks (one: just it) each spit a candle flame straight down: it goes
16 pixels at half a pixel a frame and burns 64 frames more, as Link's candle flame does; 2 hearts to Link, nothing to
anyone else (Link's weapons go through it). Flying heads don't spit.

Bank 4:
  Gleeok's update (types $42-$45, $A4DE: JSR $A825 first) -> entry: with a red Gleeok, the timer; at 0 the heads to
      spit are picked: the necks not cut ($0511's bits clear), two at most, from a random one on
  each neck's turn (JSR $A576 at $A517, its head at slot 5) -> neck: that neck's flame, if it's picked: a new object
      of type $19 (an unused type) at the head ($82AF, as the fireball's)
  type $19's update (the object table, bank 4 $B5D0) -> flame: moves, then burns; Link's touch ($7AA7: type $19's
      damage, 2 hearts, in the WRAM damage table); drawn as the cave flame ($40's frame and flicker)
Scratch: FT / PEND (stack page $015E / $015F, the decoder's scratch, unused in play)."""
from lol_af import Asm, BANK, patch

FLAME = 0x19
FT, PEND = 0x015E, 0x015F
MOVE, BURN = 32, 64
PAL3 = 0x6B7E + 3 + 28 + 1              # LevelInfo: sprite palette 3's colors (lol_enemies2 PAL3)
DMG = 0x7A4A                            # WRAM: ObjTypeToDamagePoints
WRAM_DELTA = 0x3870
TABLE = 0xB5D0 + 3                      # bank 4: UpdateObject's table (lol_v3core TABLES4)


def apply(rom: bytearray, notes: list) -> None:
    from lol_newups import put
    from lol_enemies2 import HVE, RED_GLEEOK_AT

    def build0(org):
        a = Asm(org)
        # entry (bank 0, far-called after the Gleeok's own JSR $A825)
        a.label("entry")
        a.abs(0xAD, HVE).b(0xC9, RED_GLEEOK_AT).br(0xB0, "e_red").b(0x60)
        a.label("e_red")
        # red: every 16 frames sprite palette 3 (the level's, which the boss uses) is sent turned red (each color's
        # brightness kept; black stays), through the transfer buffer
        a.b(0x8A, 0x48)
        a.b(0xA5, 0x15, 0x29, 0x0F).br(0xD0, "e_p").abs(0xAE, 0x0301)
        a.b(0xA9, 0x3F).abs(0x9D, 0x0302).b(0xA9, 0x1D).abs(0x9D, 0x0303).b(0xA9, 0x03).abs(0x9D, 0x0304)
        a.b(0xA0, 0x00)
        a.label("e_c").abs(0xB9, PAL3).b(0x48, 0x29, 0x0F, 0xC9, 0x0D).br(0xB0, "e_k").b(0x68, 0x29, 0x30, 0x09, 0x06, 0x48)
        a.label("e_k").b(0x68).abs(0x9D, 0x0305).b(0xE8, 0xC8, 0xC0, 0x03).br(0xD0, "e_c")
        a.b(0xA9, 0xFF).abs(0x9D, 0x0305).b(0x8A, 0x38, 0xE9, 0x03, 0x18, 0x69, 0x06).abs(0x8D, 0x0301)
        a.label("e_p").b(0x68, 0xAA)
        a.b(0x8A, 0x48)
        a.abs(0xAD, FT).br(0xF0, "e_new").abs(0xCE, FT).br(0xD0, "e_r")
        # time: the heads to spit (necks not cut: the first two from a random neck on), the next wait 120-240
        a.abs(0xAD, 0x0350).b(0x38, 0xE9, 0x41, 0x85, 0x00)                  # necks: 1-4
        a.b(0xA9, 0x00).abs(0x8D, PEND).b(0x85, 0x01)                         # $01: how many picked
        a.b(0xA5, 0x18, 0x29, 0x03, 0x85, 0x02, 0xA0, 0x04)                  # $02: the neck, 4 tries
        a.label("e_lp").b(0xA5, 0x02, 0xC5, 0x00).br(0xB0, "e_nx")           # a neck it has?
        a.b(0xAA).abs(0xBD, 0xE6BE).abs(0x2C, 0x0511).br(0xD0, "e_nx")         # cut?
        a.abs(0x0D, PEND).abs(0x8D, PEND).b(0xE6, 0x01, 0xA5, 0x01, 0xC9, 0x02).br(0xB0, "e_new")
        a.label("e_nx").b(0xA5, 0x02, 0x18, 0x69, 0x01, 0x29, 0x03, 0x85, 0x02, 0x88).br(0xD0, "e_lp")
        a.label("e_new").b(0xA5, 0x19)                                       # 120 + 0-120
        a.label("e_m").b(0xC9, 121).br(0x90, "e_t").b(0xE9, 121).br(0xB0, "e_m")
        a.label("e_t").b(0x18, 0x69, 120).abs(0x8D, FT)
        a.label("e_r").b(0x68, 0xAA, 0x60)
        return a

    import lol_v3core as V
    e0 = V.put0(rom, build0).labels["entry"]

    def build(org):
        a = Asm(org)
        a.label("entry").abs(0x20, 0xA825).b(*V.far(0, e0)).b(0x60)            # (the timer and palette: bank 0)
        # neck: this neck's head (slot 5) spits if picked; then the replaced JSR $A576
        a.label("neck").abs(0xAD, PEND).br(0xF0, "n_go").abs(0xAC, 0x04D7).abs(0xB9, 0xE6BE).abs(0x2D, PEND)
        a.br(0xF0, "n_go").b(0x49, 0xFF).abs(0x2D, PEND).abs(0x8D, PEND)
        a.b(0x8A, 0x48, 0xA2, 0x05, 0xA9, FLAME).abs(0x20, 0x82AF).br(0xF0, "n_x")   # (Z: no free slot)
        a.abs(0xB9, 0x0084).b(0x18, 0x69, 0x08).abs(0x99, 0x0084)
        a.b(0xA9, 0x00).abs(0x99, 0x00AC).b(0xA9, MOVE).abs(0x99, 0x0028)
        a.b(0xA9, 0xFF).abs(0x99, 0x04B2)                                    # (Link's weapons go through it)
        a.label("n_x").b(0x68, 0xAA)
        a.label("n_go").abs(0x4C, 0xA576)
        # flame (X): 16 pixels down at half a pixel a frame, then burns; Link's touch; drawn as the cave flame
        a.label("flame").b(0xB5, 0xAC).br(0xD0, "f_b")
        a.b(0xA5, 0x15, 0x4A).br(0x90, "f_t").b(0xF6, 0x84)
        a.label("f_t").b(0xB5, 0x28).br(0xD0, "f_d").b(0xA9, 0x01, 0x95, 0xAC, 0xA9, BURN, 0x95, 0x28).br(0xD0, "f_d")
        a.label("f_b").b(0xB5, 0x28).br(0xD0, "f_d").abs(0x4C, 0xFEB1)        # burnt out: gone
        a.label("f_d").b(0xB5, 0x84, 0xC9, 0xD8).br(0x90, "f_in").abs(0x4C, 0xFEB1)
        a.label("f_in").abs(0x20, 0x7AA7)                                    # Link's touch (type $19's damage)
        a.b(0xA9, 0x02).abs(0x20, 0x7988).b(0xA9, 0x08, 0x95, 0x98).abs(0x20, 0xFA4F)
        # (2026-11-25: drawn whole, as lol_patra's flames: its "one sprite" bit $02 off for the draw, centred)
        a.abs(0xBD, 0x04BF).b(0x48, 0x29, 0xFD).abs(0x9D, 0x04BF).b(0xA5, 0x00, 0x38, 0xE9, 0x04, 0x85, 0x00)
        a.b(0xA9, 0x40).abs(0x9D, 0x034F).b(0xA9, 0x00).abs(0x20, 0x77DF)
        a.b(0x68).abs(0x9D, 0x04BF)
        a.b(0xA9, FLAME).abs(0x9D, 0x034F).b(0x60)
        return a
    a = put(rom, 4, build)
    L = a.labels
    patch(rom, 4, 0xA4DE, bytes([0x20, 0x25, 0xA8]), bytes([0x20, L["entry"] & 0xFF, L["entry"] >> 8]))
    patch(rom, 4, 0xA517, bytes([0x20, 0x76, 0xA5]), bytes([0x20, L["neck"] & 0xFF, L["neck"] >> 8]))
    t = BANK(4) + TABLE + 2 * FLAME - 0x8000
    assert rom[t:t + 2] == bytes([0x94, 0xFC]), rom[t:t + 2].hex()           # (unused: the RTS at $FC94)
    rom[t:t + 2] = bytes([L["flame"] & 0xFF, L["flame"] >> 8])
    d = BANK(1) + DMG + FLAME + WRAM_DELTA - 0x8000
    rom[d] = 2                                                               # 2 hearts
    notes.append(f"red Gleeok: flames (type ${FLAME:02X}) every 120-240 frames from two heads "
                 f"(bank 4 ${L['entry']:04X}, {len(a.bytes())} bytes)")

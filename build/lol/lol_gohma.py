"""Legend of Link: the Hydra Gohma (owner, 2026-11-25): any Gohma ($33 / $34) at 14+ heart containers (as enemies
see them: HVE $D0) that the room puts in slot 1 (a boss room's).

  - purple (sprite palette 3 sent as COLORS), with two of Gleeok's heads on necks from the north wall; the heads
    sway, bite and spit fireballs as Gleeok's; Gohma spits its own as before;
  - a head cut off flies about as Gleeok's do; while any head is on, Gohma's eye stays shut, and once both are gone
    it opens for good (arrows from below, as ever), with the blue Gohma's health.

How: at the Gohma's init (slot 1) the slot becomes a two-headed Gleeok ($43: its init runs instead; Gleeok's code
owns slots 1-6 and puts cut heads in 7-8), and the Gohma is made in slot GS (11: none of the fields Gleeok borrows),
with its own init. HYB (stack page) says so; any slot 1 init clears it first. Each frame:
  Gleeok's update (lol_gleeok's JSR at $A4DE) -> with HYB: no body drawn, no red Gleeok; the two necks' roots
      (their first segment, in Gleeok's WRAM neck tables) set on the north wall
  UpdateObject's $33 / $34 -> with HYB, slot GS: the eye's timer held shut ($78) while a Gleeok is in slot 1, else
      open ($40), then $A316
  Gohma's palette ($A419: type - $32) -> 3 for it"""
from lol_af import Asm, place, patch, BANK

HVE = 0x016F
AT = 0xD0
HYB = 0x6531                    # 0 no, 1 made (its Gohma to come), 2 on
KIND = 0x6532                   # the Gohma's type
GS = 0x0B
GLEEOK = 0x43
HP = 0x60                       # the blue Gohma's ($33)
COLORS = (0x04, 0x14, 0x30)                  # (owner: purple; green vanished in green levels)
NECK_X, NECK_Y = (0x0438, 0x0452), (0x0445, 0x045F)     # Gleeok's neck tables (bank 4 $A4C6...): x, y; segment 0
ROOT_X, ROOT_Y = (0x4C, 0xA4), 0x5E                      # the roots: the north wall, halfway from the middle to
                                                         #  each side (owner 2026-11-25: less flicker)
GOHMA_INIT = 0xA161


def apply(rom: bytearray, notes: list) -> None:
    import lol_wizzrobe as W
    import lol_v3core as V
    from lol_newups import free_in
    b4 = BANK(4) - 0x8000
    b7 = BANK(7) - 0xC000
    assert rom[b4 + 0xA4C6:b4 + 0xA4C8] == bytes([0x38, 0x52]) and rom[b4 + 0xA4CE:b4 + 0xA4D0] == bytes([0x45, 0x5F])
    ATTR = lambda t: rom[b7 + 0xFAEF + t]

    def code(o):
        a = Asm(o)
        # init (X the slot, A / [00] the type), the init chain's end
        a.label("init").b(0xE0, 0x01).br(0xD0, "i_g").b(0xA8, 0xA9, 0x00).abs(0x8D, HYB).b(0x98)
        a.label("i_g").b(0xC9, 0x33).br(0xF0, "i_go").b(0xC9, 0x34).br(0xF0, "i_go").b(0x60)
        a.label("i_go").b(0xE0, 0x01).br(0xD0, "i_r").abs(0xAD, HVE).b(0xC9, AT).br(0x90, "i_r")
        a.b(0xA5, 0x00).abs(0x8D, KIND).b(0xA9, 0x01).abs(0x8D, HYB)               # (its Gohma: Gleeok's first frame)
        # this slot: a two-headed Gleeok (InitObject goes on with [00])
        a.b(0xA9, GLEEOK, 0x85, 0x00).abs(0x9D, 0x034F).b(0xA9, ATTR(GLEEOK)).abs(0x9D, 0x04BF)
        # sprite palette 3: purple (the transfer buffer)
        a.b(0x8A, 0x48).abs(0xAE, 0x0301)
        a.b(0xA9, 0x3F).abs(0x9D, 0x0302).b(0xA9, 0x1D).abs(0x9D, 0x0303).b(0xA9, 0x03).abs(0x9D, 0x0304)
        for k, c in enumerate(COLORS):
            a.b(0xA9, c).abs(0x9D, 0x0305 + k)
        a.b(0xA9, 0xFF).abs(0x9D, 0x0308).b(0x8A, 0x18, 0x69, 0x06).abs(0x8D, 0x0301).b(0x68, 0xAA)
        a.label("i_r").b(0x60)
        return a
    def gl(o):
        a = Asm(o)
        # Gleeok's frame with HYB: no red Gleeok's flames; the necks' roots to Gohma's sides
        a.label("frame").b(0xA9, 0x00).abs(0x8D, 0x015F)                    # (lol_gleeok's PEND)
        a.abs(0xAD, 0x034F + GS).b(0xC9, 0x33).br(0xF0, "f_ok").b(0xC9, 0x34).br(0xD0, "f_r")
        a.label("f_ok")
        for n in range(2):                                                 # (owner: on the north wall)
            a.b(0xA9, ROOT_X[n]).abs(0x8D, NECK_X[n]).b(0xA9, ROOT_Y).abs(0x8D, NECK_Y[n])
        a.label("f_r").b(0x60)
        # the Gohma, in slot GS (Gleeok's first frame: the room's own objects are made by now); its init follows
        a.label("prep").abs(0xAD, KIND).abs(0x8D, 0x034F + GS).b(0xC9, 0x33).br(0xD0, "p_4").b(0xA9, ATTR(0x33))
        a.br(0xD0, "p_a")
        a.label("p_4").b(0xA9, ATTR(0x34))
        a.label("p_a").abs(0x8D, 0x04BF + GS)
        a.b(0xA9, 0x00).abs(0x8D, 0x0405 + GS).b(0xA9, GS, 0x85, 0x28 + GS).b(0xA9, 0x02).abs(0x8D, HYB).b(0x60)
        a.label("hp").b(0xA9, HP).abs(0x8D, 0x0485 + GS).b(0x60)
        # Gohma's frame (X): with HYB in slot GS, the eye shut while a Gleeok is in slot 1, else open for good
        a.label("eye").abs(0xAD, HYB).br(0xF0, "e_r").b(0xE0, GS).br(0xD0, "e_r")
        a.abs(0xAD, 0x0350).b(0x38, 0xE9, 0x42, 0xC9, 0x04, 0xA9, 0x40).br(0xB0, "e_s")
        a.b(0xA9, HP).abs(0x9D, 0x0485).b(0xA9, 0x78)                      # (heads on: the health held at HP)
        a.label("e_s").abs(0x9D, 0x0444)
        a.label("e_r").b(0x60)
        return a

    n = len(code(0x8000).bytes())
    at = free_in(rom, 2, n, 0xB940)
    c = code(at)
    place(rom, 2, at, c.bytes())
    INIT = c.labels["init"]
    n2 = len(gl(0x8000).bytes())
    at2 = free_in(rom, 2, n2, 0xB940)
    g = gl(at2)
    place(rom, 2, at2, g.bytes())

    # the init chain: lol_wizzrobe's i_nx
    nx = BANK(2) + W.LABELS["i_nx"] - 0x8000
    assert rom[nx:nx + 3] == bytes([0x60, 0xEA, 0xEA])
    rom[nx:nx + 3] = bytes([0x4C, INIT & 0xFF, INIT >> 8])

    # bank 4: Gleeok's update (lol_gleeok's JSR at $A4DE), Gohma's update entry, Gohma's palette ($A419: 9 bytes)
    old_gl = rom[b4 + 0xA4DF] | rom[b4 + 0xA4E0] << 8                     # (lol_gleeok's entry)
    assert rom[b4 + 0xA4DE] == 0x20

    def stubs(o):
        s = Asm(o)
        s.label("gl").b(*V.far(2, X["glx"])).b(0x60)
        s.label("go").b(*V.far(2, g.labels["eye"])).abs(0x4C, 0xA316)
        return s

    def glx(o):
        a = Asm(o)
        # (bank 2) Gleeok's update entry: without HYB lol_gleeok's own; with it, the Gohma first, then the necks
        a.label("glx").abs(0xAD, HYB).br(0xD0, "x_h").b(*V.far(4, old_gl)).b(0x60)
        a.label("x_h").b(0xC9, 0x01).br(0xD0, "x_f").abs(0x20, g.labels["prep"])
        a.b(0x8A, 0x48, 0xA2, GS).b(*V.far(4, GOHMA_INIT)).b(0x68, 0xAA).abs(0x20, g.labels["hp"])
        a.label("x_f").abs(0x4C, g.labels["frame"])
        # Gohma's palette (X): 3 for it, else type - $32 (as $A419)
        a.label("palx").abs(0xAD, HYB).br(0xF0, "p_o").b(0xE0, GS).br(0xD0, "p_o").b(0xA9, 0x03).abs(0x4C, 0x7988)
        a.label("p_o").abs(0xBD, 0x034F).b(0x38, 0xE9, 0x32).abs(0x4C, 0x7988)
        return a
    nx2 = len(glx(0x8000).bytes())
    ax = free_in(rom, 2, nx2, 0xB940)
    xg = glx(ax)
    place(rom, 2, ax, xg.bytes())
    X = xg.labels
    n4 = len(stubs(0xB000).bytes())
    s4 = free_in(rom, 4, n4, 0xB000, 0xBE00)                              # (not $BE00+: lol_zombie's)
    s = stubs(s4)
    place(rom, 4, s4, s.bytes())
    rom[b4 + 0xA4DE:b4 + 0xA4E1] = bytes([0x20, s.labels["gl"] & 0xFF, s.labels["gl"] >> 8])
    patch(rom, 4, 0xA419, bytes.fromhex("bd4f0338e9324c8879"), V.far(2, X["palx"]) + bytes([0x60, 0xEA]))
    for t in (0x33, 0x34):
        ut = b4 + V.TABLES4 + 3 + 2 * t
        assert rom[ut:ut + 2] == bytes([0x16, 0xA3]), rom[ut:ut + 2].hex()
        rom[ut:ut + 2] = bytes([s.labels["go"] & 0xFF, s.labels["go"] >> 8])
    notes.append(f"Hydra Gohma at 14 containers (bank 2 ${at:04X} / ${at2:04X}, stubs bank 4 ${s4:04X})")

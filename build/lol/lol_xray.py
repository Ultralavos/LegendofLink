"""Legend of Link: the X-ray glasses (owner, 2026-11-24; upgrade in lol_uptable: 125, tier 2).

With the glasses, a dungeon's (and a shrine's) secret walls show in another palette: a bombable wall not yet blown
open in palette 0 (grey / white), a walk-through wall (door types 2 and 3) in palette 1 (orange). Only the
attributes change: the door spots are whole 16x16 quarters of the play area's attribute bytes (north and south:
32 x 32 at the wall's middle; east and west: 32 x 48), all in the room's outer (wall) palette.

Bank 5 (stubs; the work: bank 0, far calls):
  FillPlayAreaAttrs ($83D7: A = the room; every room draw, scroll and level entry fills PlayAreaAttrs, $0530, from
      it) -> fill: the game's fill, then the marks (in a level, not in a cellar, with the glasses)
  a door's opening transfer ($A659: LDA #$FF / STA DynTileBuf,X, ending the door's tile records) -> opened: a
      bombable wall being blown open (TriggeredDoorCmd 6 / 7) gets the wall's palette back, its attribute bytes sent
      with the door's tiles
Scratch: $01B8-$01BC (stack page, unused)."""
from lol_af import Asm, patch

FILL = 0x83D7
OPEN_SITE = 0xA659
ATTRS = 0x0530                       # PlayAreaAttrs: 6 rows of 8 bytes from nametable 0's $23D0
ATTR_A, ATTR_B = 0x687E, 0x68FE      # LevelBlockAttrsA / B (each room: S / N doors; E / W doors)
WORLD_FLAGS = 0x6BAF                 # LevelInfo_WorldFlagsAddr
ZR, PV, DX, K, BX = 0x01B8, 0x01B9, 0x01BA, 0x01BB, 0x01BC
BOMB_PAL, WALK_PAL = 0, 1
# each direction's (E, W, S, N: the game's door index) attribute bytes and the quarters in them (4 at most)
SPOTS = [[(23, 0xFF), (31, 0x0F)],
         [(16, 0xFF), (24, 0x0F)],
         [(35, 0xC0), (36, 0x30), (43, 0x0C), (44, 0x03)],
         [(3, 0xCC), (4, 0x33)]]


def apply(rom: bytearray, notes: list) -> None:
    import lol_uptable as T
    from lol_newups import put
    xr = T.bit("x-ray glasses")
    idx, msk = [], []
    for s in SPOTS:
        s = s + [(0xFF, 0)] * (4 - len(s))
        idx += [i for i, _ in s]
        msk += [m for _, m in s]

    def build(org):
        a = Asm(org)
        # mark (ZR = the room, after the game's fill)
        a.label("mark").abs(0x20, "owm").abs(0xAD, xr[0])                     # (lol_heavy: grey rocks).b(0x29, xr[1]).br(0xF0, "f_r")
        a.b(0xA5, 0x10).br(0xF0, "f_r").b(0xA5, 0x12, 0xC9, 0x09).br(0xF0, "f_r")       # a level, not a cellar
        a.b(0xA5, 0x00, 0x48, 0xA5, 0x01, 0x48)
        a.abs(0xAD, WORLD_FLAGS).b(0x85, 0x00).abs(0xAD, WORLD_FLAGS + 1).b(0x85, 0x01)
        a.b(0xA2, 0x03)
        a.label("f_lp").abs(0x8E, DX).abs(0x20, "dtype")
        a.b(0xC9, 0x02).br(0xF0, "f_wk").b(0xC9, 0x03).br(0xF0, "f_wk").b(0xC9, 0x04).br(0xD0, "f_nx")
        a.abs(0xAC, ZR).b(0xB1, 0x00).abs(0x3D, "bits").br(0xD0, "f_nx")                 # blown open already
        a.b(0xA9, BOMB_PAL).br(0xF0, "f_p")
        a.label("f_wk").b(0xA9, WALK_PAL)
        a.label("f_p").abs(0x8D, PV).abs(0x20, "paint")
        a.label("f_nx").abs(0xAE, DX).b(0xCA).br(0x10, "f_lp")
        a.b(0x68, 0x85, 0x01, 0x68, 0x85, 0x00)
        a.label("f_r").b(0x60)
        # dtype: X = the direction (0 E, 1 W, 2 S, 3 N), ZR the room: A = its door type (X kept)
        a.label("dtype").abs(0xAC, ZR).b(0xE0, 0x02).br(0xB0, "d_a").abs(0xB9, ATTR_B).br(0xD0, "d_s")
        a.abs(0x4C, "d_s")
        a.label("d_a").abs(0xB9, ATTR_A)
        a.label("d_s").b(0x48, 0x8A, 0x29, 0x01).br(0xF0, "d_lo")                        # E / S: bits 2-4
        a.b(0x68, 0x4A, 0x4A, 0x4A, 0x48)                                                # W / N: bits 5-7
        a.label("d_lo").b(0x68, 0x4A, 0x4A, 0x29, 0x07, 0x60)
        # paint: X = the direction, PV the palette: its quarters set in PlayAreaAttrs (X kept)
        a.label("paint").b(0x8A, 0x48, 0x0A, 0x0A).abs(0x8D, K)
        a.label("p_lp").abs(0xAC, K).abs(0xB9, "idx").b(0xC9, 0xFF).br(0xF0, "p_r")
        a.b(0xAA).abs(0xB9, "msk").b(0x49, 0xFF).abs(0x3D, ATTRS).abs(0x9D, ATTRS)        # the quarters cleared
        a.abs(0xAC, PV).abs(0xB9, "pals").abs(0xAC, K).abs(0x39, "msk")
        a.abs(0x1D, ATTRS).abs(0x9D, ATTRS)
        a.abs(0xAD, K).b(0x29, 0x03, 0xC9, 0x03).br(0xF0, "p_r").abs(0xEE, K).abs(0x4C, "p_lp")
        a.label("p_r").b(0x68, 0xAA, 0x60)
        # opened (X = DynTileBuf's end): a bombable wall blown open gets the wall's palette back
        a.label("opened").abs(0xAD, xr[0]).b(0x29, xr[1]).br(0xF0, "o_r")
        a.b(0xA5, 0x10).br(0xF0, "o_r").b(0xA5, 0x54, 0xC9, 0x06).br(0x90, "o_r")
        a.abs(0x8E, BX).b(0xA5, 0xEB).abs(0x8D, ZR)
        a.b(0xA5, 0x55, 0xA2, 0x00)                                                      # the bit -> its index
        a.label("o_ix").b(0x4A).br(0xB0, "o_got").b(0xE8, 0xE0, 0x04).br(0x90, "o_ix").abs(0x4C, "o_x")
        a.label("o_got").abs(0x20, "dtype").b(0xC9, 0x04).br(0xD0, "o_x")
        a.abs(0xAC, ZR).abs(0xB9, ATTR_A).b(0x29, 0x03).abs(0x8D, PV).abs(0x20, "paint")
        a.b(0x8A, 0x0A, 0x0A).abs(0x8D, K)
        a.label("o_lp").abs(0xAC, K).abs(0xB9, "idx").b(0xC9, 0xFF).br(0xF0, "o_x")
        a.abs(0xAE, BX).b(0x48, 0xA9, 0x23).abs(0x9D, 0x0302).b(0x68, 0x48, 0x18, 0x69, 0xD0).abs(0x9D, 0x0303)
        a.b(0xA9, 0x01).abs(0x9D, 0x0304).b(0x68, 0xA8).abs(0xB9, ATTRS).abs(0x9D, 0x0305)
        a.b(0xE8, 0xE8, 0xE8, 0xE8).abs(0x8E, BX)
        a.abs(0xAD, K).b(0x29, 0x03, 0xC9, 0x03).br(0xF0, "o_x").abs(0xEE, K).abs(0x4C, "o_lp")
        a.label("o_x").abs(0xAE, BX)
        a.label("o_r").b(0x60)
        a.label("bits").b(0x01, 0x02, 0x04, 0x08)
        a.label("pals").b(0x00, 0x55, 0xAA, 0xFF)
        a.label("idx").b(*idx)
        a.label("msk").b(*msk)
        import lol_heavy
        lol_heavy.ow_mark(a, rom, ZR)
        return a
    import lol_v3core as V
    a = V.put0(rom, build)
    L = a.labels

    def stubs(org):                  # bank 5: the hooks, far calls to bank 0
        s = Asm(org)
        s.label("fill").abs(0x8D, ZR).abs(0x20, "body").b(*V.far(0, L["mark"])).b(0x60)
        s.label("body").b(0xA8).abs(0xB9, ATTR_A).abs(0x4C, FILL + 4)
        s.label("opened").b(*V.far(0, L["opened"])).b(0xA9, 0xFF).abs(0x9D, 0x0302).b(0x60)
        return s
    st = put(rom, 5, stubs)
    f, o = st.labels["fill"], st.labels["opened"]
    patch(rom, 5, FILL, bytes([0xA8, 0xB9, 0x7E, 0x68]), bytes([0x4C, f & 0xFF, f >> 8, 0xEA]))
    patch(rom, 5, OPEN_SITE, bytes([0xA9, 0xFF, 0x9D, 0x02, 0x03]), bytes([0x20, o & 0xFF, o >> 8, 0xEA, 0xEA]))
    notes.append(f"x-ray glasses: secret walls marked (bank 0 ${L['mark']:04X}, {len(a.bytes())} bytes; bank 5 stubs ${f:04X})")

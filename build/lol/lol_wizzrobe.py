"""Legend of Link: the Bomber Wizzrobe (owner, 2026-11-25): red Wizzrobes ($24, the teleporting ones) at 14+ heart
containers (as enemies see them: HVE $D0).

  - drawn with sprite palette 3 (the level's own colors; their 4 frames' palettes, WRAM, set at each init),
  - 12 health, 16 XP (lol_build's XP_EXT),
  - immune to bombs, hurt by the candles' fire: the blue candle 4 per hit, the red candle kills,
  - a few frames before one fades out (its timer $AC at DROP_AT, 4 frames before the fade) it leaves a red bomb
    where it stands (lol_dodongo's type $29: lit $30 frames, then a blast that only hurts Link, 4 hearts), so the
    blast comes shortly after it's gone; and it leaves one when it dies,
  - at most 3 red bombs on the floor, never two on one square (none within 16 px of another).

Hooks (bank 4 stubs at its tail, far-calling bank 2):
  $A035 the visible state's LDA $AC,X / CMP #$B0 -> the drop check, then the same compare
  $A052 the two bomb / fire checks (LDY #$10 / JSR $7CDC, LDY #$11 / JSR $7CDC) -> vanilla, or fire only
  the death hook (bank 7 $FCBD: JSR lol_build's XP helper) -> the helper, then a bomb for a dying one
  lol_enemies2's init chain end (i_gb) -> the palettes and health."""
from lol_af import Asm, place, patch, BANK

HVE = 0x016F
AT = 0xD0                       # 14 containers
HP = 0xC0                       # 12
TYPE, BOMB = 0x24, 0x29
DROP_AT = 0x84                  # (the fade starts at $7F)
MASK = 0xDE                     # (vanilla $F6: fire $20 now hurts; bombs $08 are skipped anyway)
BLUE_DMG, RED_DMG = 0x40, 0xFF
PALT = 0x76DF
FIND_EMPTY, SET_TYPE = 0xFEBB, 0xFEB3
CHECK_BF, COLLIDE, HIT, KNOCK = 0x7CDC, 0x7DFB, 0x7C16, 0x7E26
CANDLE = 0x065B
XP_BOMBER = 16


def apply(rom: bytearray, notes: list) -> None:
    import lol_dodongo as D
    import lol_enemies2 as E2
    import lol_v3core as V
    from lol_newups import free_in
    w1 = lambda c: rom[BANK(1) + c + 0x3870 - 0x8000]
    RF = w1(0x7594 + TYPE + 1)                                   # the red wizzrobe's first frame
    PV = [w1(PALT + RF + k) for k in range(4)]
    assert RF == 140 and all(v & 3 == 2 for v in PV), (RF, PV)
    ABS = D.LABELS["abs"]

    def code(o):
        a = Asm(o)
        # up: C set for an upgraded red wizzrobe (X)
        a.label("up").abs(0xBD, 0x034F).b(0xC9, TYPE).br(0xD0, "u_n").abs(0xAD, HVE).b(0xC9, AT).b(0x60)
        a.label("u_n").b(0x18, 0x60)
        # init (X the object, A its type): palettes both ways, the health
        a.label("init").b(0xC9, TYPE).br(0xD0, "i_r").abs(0xAD, HVE).b(0xC9, AT).br(0xB0, "i_u").b(0xA0, 0x03)
        a.label("i_v").abs(0xB9, "pv").abs(0x99, PALT + RF).b(0x88).br(0x10, "i_v")
        a.label("i_r").b(0x60)
        a.label("i_u").b(0xA9, HP).abs(0x9D, 0x0485).b(0xA0, 0x03)
        a.label("i_w").abs(0xB9, "pu").abs(0x99, PALT + RF).b(0x88).br(0x10, "i_w").b(0x60)
        a.label("pv").b(*PV)
        a.label("pu").b(*[(v & 0x80) | 3 for v in PV])
        # the bomb / fire checks (X): vanilla, or the fire only (candle damage)
        a.label("wpn").abs(0x20, "up").br(0xB0, "w_u")
        a.b(0xA0, 0x10).abs(0x20, CHECK_BF).b(0xA0, 0x11).abs(0x4C, CHECK_BF)
        a.label("w_u").b(0xA9, MASK).abs(0x9D, 0x04B2).b(0xA0, 0x10).abs(0x20, "fire").b(0xA0, 0x11)
        a.label("fire").b(0x84, 0x00).abs(0xB9, 0x00AC).b(0xC9, 0x20).br(0x90, "f_r")          # (a fire: $20+)
        a.b(0xA9, 0x20, 0x85, 0x09).abs(0xAD, CANDLE).b(0xC9, 0x02, 0xA9, BLUE_DMG).br(0x90, "f_d").b(0xA9, RED_DMG)
        a.label("f_d").b(0x85, 0x07, 0xA9, 0x0E, 0x85, 0x0D)
        a.abs(0xB9, 0x0070).b(0x18, 0x69, 0x08, 0x85, 0x04).abs(0xB9, 0x0084).b(0x18, 0x69, 0x08, 0x85, 0x05)
        a.b(0xA5, 0x0D).abs(0x20, COLLIDE).br(0xF0, "f_r").abs(0x20, HIT)
        a.abs(0xBD, 0x04B2).b(0x25, 0x09).br(0xD0, "f_r").abs(0x20, KNOCK)
        a.label("f_r").b(0x60)
        # the drop, DROP_AT frames into the end of its visible time
        a.label("drop").abs(0x20, "up").br(0x90, "d_r").b(0xB5, 0xAC, 0xC9, DROP_AT).br(0xD0, "d_r")
        # a red bomb at its feet (X the wizzrobe): at most 3 out, none within 16 px of another
        a.label("spawn").b(0xA9, 0x00, 0x85, 0x0E, 0xA0, 0x0B)
        a.label("s_lp").abs(0xB9, 0x034F).b(0xC9, BOMB).br(0xD0, "s_nx").b(0xE6, 0x0E)
        a.b(0xB5, 0x70, 0x18, 0x69, 0x04, 0x38).abs(0xF9, 0x0070).abs(0x20, ABS).b(0xC9, 0x10).br(0xB0, "s_nx")
        a.b(0xB5, 0x84, 0x38).abs(0xF9, 0x0084).abs(0x20, ABS).b(0xC9, 0x10).br(0x90, "d_r")
        a.label("s_nx").b(0x88).br(0xD0, "s_lp")
        a.b(0xA5, 0x0E, 0xC9, 0x03).br(0xB0, "d_r")
        a.abs(0x20, FIND_EMPTY).br(0xF0, "d_r")                   # (Y: an empty slot)
        a.b(0x8A, 0x48, 0x98, 0xAA, 0xA9, BOMB).abs(0x20, SET_TYPE)
        a.b(0xA9, 0x00).abs(0x9D, 0x0405)                         # (no spawn cloud)
        a.b(0x68, 0xA8, 0x98, 0x95, 0x98)                         # its owner: the wizzrobe
        a.abs(0xB9, 0x0070).b(0x18, 0x69, 0x04, 0x95, 0x70).abs(0xB9, 0x0084).b(0x95, 0x84)
        a.b(0x98, 0xAA)
        a.label("d_r").b(0x60)
        # its death (X, still its type)
        a.label("death").abs(0x20, "up").br(0xB0, "spawn").b(0x60)
        return a
    n = len(code(0x8000).bytes())
    at = free_in(rom, 2, n, 0xB940)
    c = code(at)
    place(rom, 2, at, c.bytes())
    L = c.labels

    # bank 4 stubs
    def stubs(o):
        s = Asm(o)
        s.label("wpn").b(*V.far(2, L["wpn"])).b(0x60)
        s.label("drop").b(*V.far(2, L["drop"])).b(0xB5, 0xAC, 0xC9, 0xB0, 0x60)
        s.label("death").abs(0x20, E2_XP_HELPER(rom)).b(*V.far(2, L["death"])).b(0x60)
        return s
    n4 = len(stubs(0xBE00).bytes())
    s4 = free_in(rom, 4, n4, 0xBE00, 0xBFB0)
    s = stubs(s4)
    place(rom, 4, s4, s.bytes())
    J = lambda name: bytes([0x20, s.labels[name] & 0xFF, s.labels[name] >> 8])
    patch(rom, 4, 0xA035, bytes.fromhex("b5acc9b0"), J("drop") + b"\xEA")
    patch(rom, 4, 0xA052, bytes.fromhex("a01020dc7ca01120dc7c"), J("wpn") + b"\xEA" * 7)
    hook = 0x1FCCD
    assert rom[hook] == 0x20
    rom[hook:hook + 3] = J("death")
    # lol_enemies2's init chain end
    gi = BANK(2) + E2.GO["i_gb"] - 0x8000
    assert rom[gi:gi + 3] == bytes([0x60, 0xEA, 0xEA])
    rom[gi:gi + 3] = bytes([0x4C, L["init"] & 0xFF, L["init"] >> 8])
    notes.append(f"Bomber Wizzrobes at 14 containers ({n} bytes in bank 2 at ${at:04X}, stubs bank 4 ${s4:04X})")


def E2_XP_HELPER(rom):
    """lol_build's XP helper (the death hook's JSR target, bank 4)."""
    hook = 0x1FCCD
    assert rom[hook] == 0x20
    t = rom[hook + 1] | rom[hook + 2] << 8
    assert 0x8000 <= t < 0xC000
    return t

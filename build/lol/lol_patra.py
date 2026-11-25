"""Legend of Link: the Fire Sage (owner, 2026-11-25): Patras ($47 / $48) at 15+ heart containers (as enemies see
them: HVE $E0) become an old man with 6 flames circling him (Patra's own moves and patterns).

  - the old man: drawn as the dungeons' old man ($6B's frame, palette 2), 15 health, 4 hearts on touch, a fireball
    ($56, 1 heart) every FIRE_T frames;
  - the flames: drawn as the cave flame ($40's frame, palette 2, flickering), 8 health each, 2 hearts on touch;
  - hurt as Patra is (its masks: the sword's and the wand's hits; with piercing arrows, arrows too: lol_enemies2);
    the old man only once the flames are gone (Patra's rule).
Six flames, not eight: the init's children in slots 7 and 8 are removed, and the children's start points (when the
first child's angle, 0-$1F, reaches each one's: bank 4's table at $ABCF) are read from WRAM (STARTS), so the six go
round evenly spaced.

Bank 4: Patra's init (the children's loop, $A964: 11 bytes) -> JSR cfg (each child: mask, health, the two extra
removed) ... JMP pin (the old man: health, the damage table, STARTS); its update's body draw ($AB74: LDA #2 / JSR
$8476 / LDY #8) -> a far call (the draw, the fireball, LDY #8); the child's draw ($AC71: 12 bytes) -> a far call;
the start point compare (CMP $ABCF,Y at $ABEE) -> CMP STARTS,Y.
RAM: STARTS $6533-$6539, FT $653A (battery RAM past the save files, unused)."""
from lol_af import Asm, place, patch, BANK

HVE = 0x016F
AT = 0xE0                       # 15 containers
BODY_HP, FLAME_HP = 0xF0, 0x80
BODY_DMG, FLAME_DMG = 4, 2      # (hearts; vanilla 2 / 1)
FIRE_T = 90
DMG = 0x7A4A
STARTS, FT, CSTEP = 0x6533, 0x653A, 0x653B
OLD_MAN, CAVE_FLAME = 0x6B, 0x40
VANILLA_STARTS = (0x14, 0x10, 0x0C, 0x08, 0x04, 0x00, 0x1C)
SIX_STARTS = (19, 13, 8, 3, 0, 0, 29)           # slots 3, 4, 5, 6, (7, 8 gone), 9: 32 / 6 apart


OLD_MAN_AT = 0xD20B                             # (file) the old man's tiles ($98-$99 in a cave): 32 bytes


def apply(rom: bytearray, notes: list) -> None:
    import lol_v3core as V
    from lol_newups import free_in
    b4 = BANK(4) - 0x8000
    assert tuple(rom[b4 + 0xABCF:b4 + 0xABD6]) == VANILLA_STARTS
    global OLD_MAN_TILES, MIRRORED
    OLD_MAN_TILES = bytes(rom[OLD_MAN_AT:OLD_MAN_AT + 32])
    assert OLD_MAN_TILES[:8].hex() == "000a00000c1f3c7f", OLD_MAN_TILES[:8].hex()
    MIRRORED = bytes(int(f"{b:08b}"[::-1], 2) for b in OLD_MAN_TILES)
    w1 = lambda c: rom[BANK(1) + c + 0x3870 - 0x8000]
    BF = w1(0x7594 + 0x48)                                                # Patra's body frame
    assert BF == w1(0x7594 + 0x49) == 200, BF
    BPAL = w1(0x76DF + BF)

    def code(o):
        a = Asm(o)
        a.label("up").abs(0xAD, HVE).b(0xC9, AT, 0x60)                   # C set: the Fire Sage
        # each child (Y) at Patra's init: its mask as before; upgraded: 8 health, slots 7 / 8 gone
        a.label("cfg").b(0xA9, 0xFE).abs(0x99, 0x04B2).abs(0x20, "up").br(0x90, "c_r")
        a.b(0xA9, FLAME_HP).abs(0x99, 0x0485).b(0xC0, 0x07).br(0x90, "c_r").b(0xC0, 0x09).br(0xB0, "c_r")
        a.b(0xA9, 0x00).abs(0x99, 0x034F)
        a.label("c_r").b(0x60)
        # the old man (X) at the init's end: health, damage, start points (both ways)
        a.label("pin").b(0xA0, 0x06).abs(0x20, "up").br(0xB0, "p_u")
        a.label("p_v").abs(0xB9, "vst").abs(0x99, STARTS).b(0x88).br(0x10, "p_v")
        for t, v in ((0x47, 2), (0x48, 2), (0x25, 1), (0x26, 1)):
            a.b(0xA9, v).abs(0x8D, DMG + t)
        a.b(0xA9, BPAL).abs(0x8D, 0x76DF + BF).b(0x60)
        a.label("p_u").abs(0xB9, "sst").abs(0x99, STARTS).b(0x88).br(0x10, "p_u")
        for t, v in ((0x47, BODY_DMG), (0x48, BODY_DMG), (0x25, FLAME_DMG), (0x26, FLAME_DMG)):
            a.b(0xA9, v).abs(0x8D, DMG + t)
        a.b(0xA9, BODY_HP).abs(0x9D, 0x0485).b(0xA9, FIRE_T).abs(0x8D, FT).b(0xA9, 0x00).abs(0x8D, CSTEP)
        a.b(0xA9, (BPAL & 0xFC) | 2).abs(0x8D, 0x76DF + BF)                 # (the old man's palette 2)
        a.b(0xA0, 0x09)                                                     # (and the flames' health again)
        a.label("p_f").abs(0xB9, 0x034F).b(0xC9, 0x25).br(0xF0, "p_h").b(0xC9, 0x26).br(0xD0, "p_n")
        a.label("p_h").b(0xA9, FLAME_HP).abs(0x99, 0x0485)
        a.label("p_n").b(0x88, 0xC0, 0x02).br(0xB0, "p_f").b(0x60)
        # InitObject's chain end (A the type, X the slot): an upgraded flame's health (the room inits each child)
        a.label("init").b(0xC9, 0x25).br(0xF0, "i_f").b(0xC9, 0x26).br(0xD0, "i_r")
        a.label("i_f").abs(0x20, "up").br(0x90, "i_r").b(0xA9, FLAME_HP).abs(0x9D, 0x0485)
        a.label("i_r").b(0x60)
        a.label("vst").b(*VANILLA_STARTS)
        a.label("sst").b(*SIX_STARTS)
        # the body's draw (X), as $8476 with A = 2; upgraded: the old man's frame, and his fireball; then LDY #8
        a.label("bdraw").abs(0x20, "up").br(0xB0, "b_u")
        a.b(0xA9, 0x02).abs(0x20, 0xFA89).abs(0x20, 0xFA72).b(0xA9, 0x00).abs(0x20, 0x77DF).b(0xA0, 0x08, 0x60)
        a.label("b_u").abs(0xCE, FT).br(0xD0, "b_d").b(0xA9, FIRE_T).abs(0x8D, FT)
        a.b(0xA9, 0x56).b(*V.far(4, 0x82AF))                                # (Shoot: a fireball from X)
        # his picture: Patra's body tiles ($F8-$FB) rewritten as the old man (32 bytes a frame, two frames)
        a.label("b_d").abs(0xAC, CSTEP).b(0xC0, 0x02).br(0xB0, "b_v").abs(0xEE, CSTEP)
        a.b(0x8A, 0x48).abs(0xAE, 0x0301).b(0xA9, 0x0F).abs(0x9D, 0x0302).abs(0xB9, "plo").abs(0x9D, 0x0303)
        a.b(0xA9, 0x20).abs(0x9D, 0x0304).abs(0xB9, "pof").b(0xA8, 0xA9, 0x20, 0x85, 0x0A)
        a.label("b_c").abs(0xB9, "pics").abs(0x9D, 0x0305).b(0xC8, 0xE8, 0xC6, 0x0A).br(0xD0, "b_c")
        a.b(0xA9, 0xFF).abs(0x9D, 0x0305).b(0x8A, 0x18, 0x69, 0x03).abs(0x8D, 0x0301).b(0x68, 0xAA)
        a.label("b_v").b(0xA9, 0x02).abs(0x20, 0xFA89).abs(0x20, 0xFA72).b(0xA9, 0x00).abs(0x20, 0x77DF)
        a.b(0xA0, 0x08, 0x60)
        a.label("plo").b(0x80, 0xA0)
        a.label("pof").b(0x00, 0x20)
        a.label("pics").b(*OLD_MAN_TILES, *MIRRORED)
        # a child's draw (X), as $AC71; upgraded: the cave flame, flickering (its ObjDir kept)
        a.label("cdraw").abs(0x20, "up").br(0xB0, "d_u")
        a.abs(0x20, 0x7986).abs(0x20, 0xFA89).abs(0xBD, 0x03E4).abs(0x4C, 0x77DF)
        a.label("d_u").b(0xB5, 0x98, 0x48, 0xA9, 0x02).abs(0x20, 0x7988).b(0xA9, 0x08, 0x95, 0x98).abs(0x20, 0xFA4F)
        a.abs(0xBD, 0x034F).b(0x48, 0xA9, CAVE_FLAME).abs(0x9D, 0x034F).b(0xA9, 0x00).abs(0x20, 0x77DF)
        a.b(0x68).abs(0x9D, 0x034F).b(0x68, 0x95, 0x98, 0x60)
        return a
    n = len(code(0x8000).bytes())
    at = free_in(rom, 2, n, 0xB300)                                        # (past lol_dodongo's code)
    c = code(at)
    place(rom, 2, at, c.bytes())
    L = c.labels
    import lol_gohma as G
    nx = BANK(2) + G.LABELS["i_nx"] - 0x8000
    assert rom[nx:nx + 3] == bytes([0x60, 0xEA, 0xEA])
    rom[nx:nx + 3] = bytes([0x4C, L["init"] & 0xFF, L["init"] >> 8])

    def stubs(o):
        s = Asm(o)
        s.label("cfg").b(*V.far(2, L["cfg"])).b(0x60)
        s.label("pin").b(*V.far(2, L["pin"])).b(0x60)
        return s
    n4 = len(stubs(0xB000).bytes())
    s4 = free_in(rom, 4, n4, 0xB000, 0xBE00)
    s = stubs(s4)
    place(rom, 4, s4, s.bytes())
    # the init's child loop: JSR cfg / INY / CPY #$0A / BNE $A95F / JMP pin
    i = Asm(0xA964).abs(0x20, s.labels["cfg"]).b(0xC8, 0xC0, 0x0A)
    i.b(0xD0, (0xA95F - (0xA96A + 2)) & 0xFF).abs(0x4C, s.labels["pin"])
    patch(rom, 4, 0xA964, bytes.fromhex("a9fe99b204c8c00ad0f160"), i.bytes())
    patch(rom, 4, 0xAB74, bytes.fromhex("a902207684a008"), V.far(2, L["bdraw"]))
    patch(rom, 4, 0xAC71, bytes.fromhex("2086792089fabde4034cdf77"), V.far(2, L["cdraw"]) + bytes([0x60, 0xEA, 0xEA, 0xEA, 0xEA]))
    patch(rom, 4, 0xABEE, bytes.fromhex("d9cfab"), bytes([0xD9, STARTS & 0xFF, STARTS >> 8]))
    notes.append(f"Fire Sage (Patras at 15 containers): bank 2 ${at:04X} ({n} bytes), stubs bank 4 ${s4:04X}")

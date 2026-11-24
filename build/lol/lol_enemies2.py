"""Legend of Link: brown darknuts (9+ heart containers) and blue Aquamentus (10+).

Brown darknut: every red darknut ($0B) once Link has 9 containers: 10 HP, speed $30 (red $20, blue $28: both now from SPD, set at each init), the blue
darknut's damage (2; the WRAM damage table's entry is set at each darknut's init), 14 XP (blue's 12 + 2; lol_build's
XP_EXT). Drawn with sprite palette 3, which its init loads as dark brown $17, tan $27 and Link's tunic color.
Blue Aquamentus: 8 HP, 20 XP (15 + 5), sprite palette 3 loaded with palette 1's blues; its fireballs fly as red
bombs (the dodongo's, type $29) that blast on reaching Link or the room's edge (4 hearts; the magic shield doesn't
stop them; Link's flashing after a hit stops a second).

Palette 3 is the bosses' (each boss room loads its own: bank 6's records), so nothing needs putting back.

Hooks (bank 4, through lol_dodongo's trampoline into bank 2 with Y = 2 / 3 / 4):
  InitObject's chain (lol_upgrades' j_w)            -> Y 4: the init above
  the fireball's Link check (JSR $8371 at $83FC)    -> Y 2: in a blue Aquamentus' room: touching Link? blast;
                                                       else drawn as a red bomb (the rest of the update skipped)
  the fireball leaving the room (JMP $FEB1 at $83D7) -> Y 3: blast there
  the darknut's draw (JSR $77DF at $9B76)            -> palettes from $04 / $05 = 3 (only used with the brown's
                                                       attribute bit)"""
from lol_af import Asm, place, patch, BANK

BROWN_AT, BLUE_AQ_AT = 0x80, 0x90       # HeartValues: 9 / 10 containers
BROWN_HP, BROWN_SPEED, BROWN_DMG, RED_DMG = 0xA0, 0x30, 2, 1
BLUE_AQ_HP = 0x80
DMG = 0x7A4A                            # WRAM: ObjTypeToDamagePoints
LI = 0x6B7E                             # LevelInfo: palettes from +3
TUNIC, PAL1, PAL3 = LI + 3 + 16 + 1, LI + 3 + 20 + 1, LI + 3 + 28 + 1
T1, T2, T3, FLAG = 0x01A1, 0x01A2, 0x01A3, 0x01A4   # (stack page, unused); FLAG: the frame last queued
SPD = 0x01A5                            # the darknuts' speeds ($0B, $0C), read by their first update
STUB_A, STUB_B, STUB_I, STUB_D, STUB_W = 0xBC84, 0xBC84 + 15, 0xBCF6, None, 0xBD58    # bank 4 free (STUB_W: 2 too; after the trampoline)
BOMB = 0x29
WM4 = 0xBD90                            # lol_upgrades: the red wallmaster init (the init chain's end)


def apply(rom: bytearray, notes: list) -> None:
    import lol_dodongo as D
    import lol_upgrades as U
    TR = D.TLABELS["bomb"] + 2              # the trampoline past its LDY (bank 4 -> bank 2 CODE2 -> back)
    assert rom[BANK(4) + TR - 0x8000] == 0xA9
    DL = D.LABELS
    # bank 4 stubs
    sa = Asm(STUB_A)
    sa.b(0xA0, 0x02).abs(0x20, TR).b(0xC0, 0x00).br(0xD0, "m").abs(0x4C, 0x8371)
    sa.label("m").b(0x68, 0x68, 0x60)
    sb = Asm(STUB_B)
    sb.b(0xA0, 0x03).abs(0x20, TR).b(0xC0, 0x00).br(0xD0, "r").abs(0x4C, 0xFEB1)
    sb.label("r").b(0x60)
    si = Asm(STUB_I)
    si.b(0xA0, 0x04).abs(0x20, TR).b(0xA5, 0x00).abs(0x4C, WM4)
    global STUB_D
    b4 = BANK(4) - 0x8000
    STUB_D = next(c for c in range(0xB000, 0xBF00) if all(x == 0xFF for x in rom[b4 + c - 2:b4 + c + 13]))
    sd = Asm(STUB_D)
    sd.b(0x48, 0xA9, 0x03, 0x85, 0x04, 0x85, 0x05, 0x68).abs(0x4C, 0x77DF)   # (A: the frame image, kept)
    assert len(sa.bytes()) == 15 and STUB_B + len(sb.bytes()) <= 0xBCA4
    for s, at in ((sa, STUB_A), (sb, STUB_B), (si, STUB_I), (sd, STUB_D)):
        place(rom, 4, at, s.bytes())
    assert len(si.bytes()) <= 10 and len(sd.bytes()) <= 11
    sw = Asm(STUB_W)
    sw.b(0xA0, 0x08).abs(0x4C, TR)
    place(rom, 4, STUB_W, sw.bytes())
    # wizzrobes check the sword, not arrows: their LDY #$0D / JSR $7D29 ($A05C) -> Y 9: the sword, then the arrow
    patch(rom, 4, 0xA05C, bytes.fromhex("a00d20297d"), bytes([0xA0, 0x09, 0x20, TR & 0xFF, TR >> 8]))
    patch(rom, 1, 0xB5E4, bytes.fromhex("a9048509"), bytes([0x20, STUB_W & 0xFF, STUB_W >> 8, 0xEA]))   # the arrow's
    patch(rom, 4, 0x83FC, bytes([0x20, 0x71, 0x83]), bytes([0x20, STUB_A & 0xFF, STUB_A >> 8]))
    patch(rom, 4, 0x83D7, bytes([0x4C, 0xB1, 0xFE]), bytes([0x4C, STUB_B & 0xFF, STUB_B >> 8]))
    patch(rom, 4, 0x9B76, bytes([0x20, 0xDF, 0x77]), bytes([0x20, STUB_D & 0xFF, STUB_D >> 8]))
    # the darknut's first update: LDA #$20 / LDY type / CPY #$0B / BEQ / LDA #$28 / STA $03BC,X -> from SPD
    patch(rom, 4, 0x9B25, bytes.fromhex("a920bc4f03c00bf002a9289dbc03"),
          bytes([0xBC, 0x4F, 0x03, 0xB9, (SPD - 0x0B) & 0xFF, (SPD - 0x0B) >> 8, 0x9D, 0xBC, 0x03]))
    jw = BANK(4) + U.GB_LABELS["j_w"] - 0x8000
    assert rom[jw:jw + 3] == bytes([0x4C, WM4 & 0xFF, WM4 >> 8])
    rom[jw + 1:jw + 3] = bytes([STUB_I & 0xFF, STUB_I >> 8])

    # bank 2: Y = 2, 3, 4
    a = Asm(D.MORE)
    for k, name in ((2, "fb"), (3, "edge"), (4, "init"), (6, "dodo"), (8, "arrow")):
        a.b(0xC0, k).br(0xD0, f"dn{k}").abs(0x4C, name).label(f"dn{k}")
    a.abs(0x4C, "wizz")                                                  # (9)
    # is a blue Aquamentus here? (C set: yes)
    a.label("blue").abs(0xAD, 0x066F).b(0xC9, BLUE_AQ_AT).br(0x90, "bl_r").b(0xA0, 0x0B)
    a.label("bl_lp").abs(0xB9, 0x034F).b(0xC9, 0x3D).br(0xF0, "bl_y").b(0x88).br(0xD0, "bl_lp")
    a.b(0x18)
    a.label("bl_r").b(0x60)
    a.label("bl_y").b(0x38, 0x60)
    # Y 2: the fireball X
    a.label("fb").abs(0x20, "blue").br(0xB0, "fb_m").b(0xA0, 0x00, 0x60)
    a.label("fb_m").b(0xA9, 0x00).abs(0x9D, 0x0394)                 # (as $8371 does each frame)
    a.label("fb_m2").b(0xB5, 0x70, 0xC9, 0x1C).br(0x90, "fb_b").b(0xC9, 0xDC).br(0xB0, "fb_b")
    a.b(0xB5, 0x84, 0xC9, 0x58).br(0x90, "fb_b").b(0xC9, 0xCC).br(0xB0, "fb_b")
    a.b(0xA5, 0x70, 0x18, 0x69, 0x04, 0x38, 0xF5, 0x70).abs(0x20, DL["abs"]).b(0xC9, 0x0C).br(0xB0, "fb_d")
    a.b(0xA5, 0x84, 0x38, 0xF5, 0x84).abs(0x20, DL["abs"]).b(0xC9, 0x0C).br(0xB0, "fb_d")
    a.label("fb_b").abs(0x20, "boom").b(0xA0, 0x01, 0x60)
    a.label("fb_d").b(0xB5, 0x70, 0x85, 0x00, 0xB5, 0x84, 0x85, 0x01, 0xA9, 0x00).abs(0x20, DL["draw"])
    a.b(0xA0, 0x01, 0x60)
    # Y 3: it left the room
    a.label("edge").abs(0x20, "blue").br(0xB0, "ed_m").b(0xA0, 0x00, 0x60)
    a.label("ed_m").abs(0x20, "boom").b(0xA0, 0x01, 0x60)
    # the fireball becomes a dodongo bomb, blasting
    a.label("boom").b(0xA9, BOMB).abs(0x9D, 0x034F).b(0xA9, 0x02, 0x95, 0xAC, 0xA9, 0x10, 0x95, 0x28)
    a.b(0xA9, 0xFF).abs(0x9D, 0x04B2).b(0x95, 0x98).b(0xA9, 0x10).abs(0x8D, 0x0603)
    a.abs(0xBD, 0x04BF).b(0x09, 0x20).abs(0x9D, 0x04BF).b(0x60)          # (no weapon checks: CheckMonsterCollisions)
    # Y 4: InitObject (X the object, [00] its type)
    a.label("init").b(0xA9, 0x20).abs(0x8D, SPD).b(0xA9, 0x28).abs(0x8D, SPD + 1)   # darknut speeds: red, blue
    a.b(0xA5, 0x00, 0xC9, 0x0B).br(0xD0, "i_aq")
    a.b(0xA9, RED_DMG).abs(0x8D, DMG + 0x0B)
    a.abs(0xAD, 0x066F).b(0xC9, BROWN_AT).br(0x90, "i_r")
    a.b(0xA9, BROWN_DMG).abs(0x8D, DMG + 0x0B)
    a.b(0xA9, BROWN_HP).abs(0x9D, 0x0485).b(0xA9, BROWN_SPEED).abs(0x8D, SPD)
    a.abs(0xBD, 0x04BF).b(0x09, 0x08).abs(0x9D, 0x04BF)
    a.b(0xA9, 0x17).abs(0x8D, T1).b(0xA9, 0x27).abs(0x8D, T2).abs(0xAD, TUNIC).abs(0x8D, T3)
    a.label("i_set").b(0xA5, 0x15).abs(0xCD, FLAG).br(0xF0, "i_r").abs(0x8D, FLAG)   # (once a frame)
    a.abs(0x20, "queue")
    a.label("i_r").b(0x60)
    a.label("i_aq").b(0xC9, 0x3D).br(0xD0, "i_ot")
    a.abs(0xAD, 0x066F).b(0xC9, BLUE_AQ_AT).br(0x90, "i_back")
    a.b(0xA9, BLUE_AQ_HP).abs(0x9D, 0x0485)
    for k, t in enumerate((T1, T2, T3)):
        a.abs(0xAD, PAL1 + k).abs(0x8D, t)
    a.abs(0x4C, "i_set")
    a.label("i_ot")
    a.label("i_back").b(0x60)
    # Y 6: a dodongo (X), each frame: with piercing arrows, a flying arrow (slot $12) on it stuns it
    a.label("dodo").abs(0xAD, U.PIERCING[0]).b(0x29, U.PIERCING[1]).br(0xF0, "dd_r")
    a.b(0xB5, 0xAC, 0xC9, 0x02).br(0xB0, "dd_r").b(0xA5, 0xAC + 0x12, 0x29, 0xF0, 0xC9, 0x10).br(0xD0, "dd_r")
    a.b(0xA5, 0x70 + 0x12, 0x38, 0xF5, 0x70, 0x18, 0x69, 0x08, 0xC9, 0x20).br(0xB0, "dd_r")
    a.b(0xA5, 0x84 + 0x12, 0x18, 0x69, 0x08, 0x38, 0xF5, 0x84, 0xC9, 0x14).br(0xB0, "dd_r")
    a.b(0xA9, 0x02, 0x95, 0xAC)
    a.label("dd_r").b(0x60)
    # Y 8: an arrow hit (X the monster): its damage type $04, or 0 (nothing is immune) for wizzrobes ($23 / $24),
    # Patra's eyes ($25 / $26), Gleeok and Patra ($42-$48) with piercing arrows
    a.label("arrow").b(0xA9, 0x04, 0x85, 0x09).abs(0xAD, U.PIERCING[0]).b(0x29, U.PIERCING[1]).br(0xF0, "ar_r")
    a.abs(0xBD, 0x034F).b(0x38, 0xE9, 0x23, 0xC9, 0x04).br(0x90, "ar_z").b(0xC9, 0x1F).br(0x90, "ar_r")
    a.b(0xC9, 0x26).br(0xB0, "ar_r")
    a.label("ar_z").b(0xA9, 0x00, 0x85, 0x09)
    a.label("ar_r").b(0x60)
    # Y 9: a wizzrobe's weapon checks: the sword, and with piercing arrows the arrow (WRAM routines; the arrow's
    # STUB_W has a bank 2 copy)
    a.label("wizz").b(0xA0, 0x0D).abs(0x20, 0x7D29).abs(0xAD, U.PIERCING[0]).b(0x29, U.PIERCING[1]).br(0xF0, "wz_r")
    a.b(0xA0, 0x12).abs(0x20, 0x7D5F)
    a.label("wz_r").b(0x60)
    # queue: sprite palette 3 = T1-T3 (the transfer buffer, X kept)
    a.label("queue").b(0x8A, 0x48).abs(0xAE, 0x0301)
    a.b(0xA9, 0x3F).abs(0x9D, 0x0302).b(0xA9, 0x1D).abs(0x9D, 0x0303).b(0xA9, 0x03).abs(0x9D, 0x0304)
    for k, t in enumerate((T1, T2, T3)):
        a.abs(0xAD, t).abs(0x9D, 0x0305 + k)
    a.b(0xA9, 0xFF).abs(0x9D, 0x0308).b(0x8A, 0x18, 0x69, 0x06).abs(0x8D, 0x0301)
    a.b(0x68, 0xAA, 0x60)
    code = a.bytes()
    place(rom, 2, D.MORE, code)
    s2 = Asm(STUB_W)
    s2.b(0xA0, 0x08).abs(0x4C, a.labels["arrow"])
    place(rom, 2, STUB_W, s2.bytes())
    notes.append(f"brown darknuts at 9 containers, blue Aquamentus at 10 ({len(code)} bytes in bank 2 at ${D.MORE:04X})")

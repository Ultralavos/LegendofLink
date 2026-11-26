"""Legend of Link: brown darknuts (9+ heart containers) and blue Aquamentus (10+); blue charging red moblins (8+)
and Zora-colored bomb-shooting red octoroks (10+). (Containers as enemies see them: HVE, hard mode + 3.)

Red moblin at 8+: 6 health, 2 hearts on contact, blue; when it faces Link lined up with him it charges (the rope's
speed $60), 10 XP. Red octoroks (slow and fast) at 10+: 4 health, the Zora's colors, and their rocks are red bombs
(type $54 rocks, drawn and blasting as the blue Aquamentus' bombs, on Link or a wall), 12 XP.

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
HVE = 0x016F                            # lol_build: the containers enemies level up by (HeartValues; hard mode + 3)
BROWN_HP, BROWN_SPEED, BROWN_DMG, RED_DMG = 0xA0, 0x30, 2, 1
BLUE_AQ_HP = 0x80
MOBLIN_AT, OCTOROK_AT = 0x70, 0x90      # HVE: red moblins level up at 8 containers, red octoroks at 10
RED_GLEEOK_AT = 0xB0                    # HVE: Gleeok turns red at 12 containers (lol_gleeok)
PALT = 0x76DF                           # WRAM: the sprite frames' palettes (bank 1); red moblin's 4 from 23, red octorok's 6
MOBLIN_FRAMES, OCTOROK_FRAMES = 23, 27  # from 27 (both octorok speeds share them)
OCTOROK_PAL = (0x02, 0x82, 0x02, 0x02, 0x82, 0x02)   # (vanilla: palette 2; bit 7 the vertical flip)
DMG = 0x7A4A                            # WRAM: ObjTypeToDamagePoints
LI = 0x6B7E                             # LevelInfo: palettes from +3
TUNIC, PAL1, PAL3 = LI + 3 + 16 + 1, LI + 3 + 20 + 1, LI + 3 + 28 + 1
T1, T2, T3, FLAG = 0x01A1, 0x01A2, 0x01A3, 0x01A4   # (stack page, unused); FLAG: the frame last queued
SPD = 0x01A5                            # the darknuts' speeds ($0B, $0C), read by their first update
STUB_A, STUB_B, STUB_I, STUB_D, STUB_W = 0xBC84, 0xBC84 + 15, 0xBCF6, None, 0xBD58    # bank 4 free (STUB_W: 2 too; after the trampoline)
BOMB = 0x29
# Goriya Charger: blue goriyas ($05) at 12+ (HVE $B0): Link's colors (sprite palette 0, so the ring's), 6 health,
# 4 hearts on contact, 15 XP; its boomerang doesn't hurt Link but stuns him (STUN frames of no input: lol_upgrades'
# frame hook), and DELAY frames after that the goriya charges at him (2 px a frame, straight, until a wall,
# the room's edge, 16 px past Link or MAX frames)
CHARGER_AT, CHARGER_HP, CHARGER_DMG = 0xB0, 0x60, 4
STUN, CHG, CSLOT, CTIME = 0x01B1, 0x01B2, 0x01B3, 0x01B4
THD = 0x01B6                            # lol_heavy's: the Thorn Bracelet's hit
from lol_uptable import THORN   # (stack page, unused): stun left, charge delay, the
STUN_FRAMES, CHARGE_DELAY, CHARGE_MAX = 30, 20, 64         #  goriya's slot, charge frames left
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
    # (2026-11-26, lag: this runs for every monster every frame) the arrow's damage type $04 right here; only
    # with piercing arrows the trip to bank 2 (Y 8: the types nothing is immune to)
    from lol_newups import free_in

    def fast(o):
        q = Asm(o)
        q.b(0xA9, 0x04, 0x85, 0x09).abs(0xAD, U.PIERCING[0]).b(0x29, U.PIERCING[1]).br(0xD0, "p").b(0x60)
        q.label("p").b(0xA0, 0x08).abs(0x4C, TR)
        return q
    f_at = free_in(rom, 4, len(fast(0x8000).bytes()), 0xB000, 0xBE00)
    place(rom, 4, f_at, fast(f_at).bytes())
    sw = Asm(STUB_W)
    sw.abs(0x4C, f_at)
    place(rom, 4, STUB_W, sw.bytes())
    # wizzrobes check the sword, not arrows: their LDY #$0D / JSR $7D29 ($A05C) -> Y 9: the sword, then the arrow
    patch(rom, 4, 0xA05C, bytes.fromhex("a00d20297d"), bytes([0xA0, 0x09, 0x20, TR & 0xFF, TR >> 8]))
    patch(rom, 4, 0x83FC, bytes([0x20, 0x71, 0x83]), bytes([0x20, STUB_A & 0xFF, STUB_A >> 8]))
    patch(rom, 4, 0x83D7, bytes([0x4C, 0xB1, 0xFE]), bytes([0x4C, STUB_B & 0xFF, STUB_B >> 8]))
    patch(rom, 4, 0x9B76, bytes([0x20, 0xDF, 0x77]), bytes([0x20, STUB_D & 0xFF, STUB_D >> 8]))
    # the darknut's first update: LDA #$20 / LDY type / CPY #$0B / BEQ / LDA #$28 / STA $03BC,X -> from SPD
    patch(rom, 4, 0x9B25, bytes.fromhex("a920bc4f03c00bf002a9289dbc03"),
          bytes([0xBC, 0x4F, 0x03, 0xB9, (SPD - 0x0B) & 0xFF, (SPD - 0x0B) >> 8, 0x9D, 0xBC, 0x03]))
    jw = BANK(4) + U.GB_LABELS["j_w"] - 0x8000
    assert rom[jw:jw + 3] == bytes([0x4C, WM4 & 0xFF, WM4 >> 8])
    rom[jw + 1:jw + 3] = bytes([STUB_I & 0xFF, STUB_I >> 8])

    # bank 4: the red moblin's charge, the red octorok's bomb rocks (type $54, unused: the rock code's own)
    from lol_newups import free_in
    def hooks(at):
        h = Asm(at)
        # UpdateMoblin's LDY #$5B / JMP $87D1 (the shooter, speed $20 in $01): an upgraded red moblin that faces
        # Link while lined up with him (within 8 px) charges at the rope's speed $60
        h.label("mob").abs(0xBD, 0x034F).b(0xC9, 0x04).br(0xD0, "m_n").abs(0xAD, HVE).b(0xC9, MOBLIN_AT)
        h.br(0x90, "m_n").b(0xB5, 0x98, 0x29, 0x0C).br(0xF0, "m_h")
        h.b(0xA5, 0x70, 0x38, 0xF5, 0x70).abs(0x20, 0x701F).b(0xC9, 0x08).br(0xB0, "m_n")     # |x - Link's| < 8
        h.b(0xA0, 0x04, 0xA5, 0x84, 0xD5, 0x84).br(0xB0, "m_d").b(0xA0, 0x08)                 # Link below: down
        h.label("m_d").b(0x98, 0xD5, 0x98).br(0xD0, "m_n").br(0xF0, "m_c")
        h.label("m_h").b(0xA5, 0x84, 0x38, 0xF5, 0x84).abs(0x20, 0x701F).b(0xC9, 0x08).br(0xB0, "m_n")
        h.b(0xA0, 0x01, 0xA5, 0x70, 0xD5, 0x70).br(0xB0, "m_d").b(0xA0, 0x02).br(0xD0, "m_d")  # Link right: right
        h.label("m_c").b(0xA0, 0x5B, 0xA9, 0x60, 0x85, 0x01).abs(0x4C, 0x87D5)
        h.label("m_n").b(0xA0, 0x5B).abs(0x4C, 0x87D1)
        # UpdateOctorok's LDY #$53 / JSR $87D3 (A kept): an upgraded red octorok shoots a bomb rock ($54)
        h.label("oct").b(0xA0, 0x53, 0x48).abs(0xBD, 0x034F).b(0xC9, 0x09).br(0xB0, "o_n")
        h.abs(0xAD, HVE).b(0xC9, OCTOROK_AT).br(0x90, "o_n").b(0xA0, 0x54)
        h.label("o_n").b(0x68).abs(0x4C, 0x87D3)
        # the rock's wall / edge check (JSR $6FB8 / BEQ gone): a bomb rock blasts there
        h.label("rw").abs(0x20, 0x6FB8).br(0xD0, "rw_r").abs(0xBD, 0x034F).b(0xC9, 0x54).br(0xD0, "rw_z")
        h.b(0xA0, 0x0B).abs(0x20, TR).b(0x68, 0x68, 0x60)
        h.label("rw_z").b(0xA9, 0x00)
        h.label("rw_r").b(0x60)
        # the rock's tile check (JSR $EDFA / CMP $034A / BCS gone: a solid tile): a bomb rock blasts there
        h.label("rt").abs(0x20, 0xEDFA).b(0x48).abs(0xCD, 0x034A).br(0x90, "rt_ok")
        h.abs(0xBD, 0x034F).b(0xC9, 0x54).br(0xD0, "rt_ok")
        h.b(0x68, 0xA0, 0x0B).abs(0x20, TR).b(0x68, 0x68, 0x60)
        h.label("rt_ok").b(0x68, 0x60)
        # the rock's Link check (JSR $8371): a bomb rock is the blue Aquamentus' bomb (Y 10), the rest skipped
        h.label("rl").abs(0xBD, 0x034F).b(0xC9, 0x54).br(0xF0, "rl_b").abs(0x4C, 0x8371)
        h.label("rl_b").b(0xA0, 0x0A).abs(0x20, TR).b(0x68, 0x68, 0x60)
        return h
    hat = free_in(rom, 4, len(hooks(0xB000).bytes()), 0xB000)
    h = hooks(hat)
    place(rom, 4, hat, h.bytes())
    J = lambda n, op=0x20: bytes([op, h.labels[n] & 0xFF, h.labels[n] >> 8])
    patch(rom, 4, 0x87C7, bytes.fromhex("a05b4cd187"), J("mob", 0x4C) + b"\xEA\xEA")
    patch(rom, 4, 0x8C1E, bytes.fromhex("a05320d387"), J("oct") + b"\xEA\xEA")
    patch(rom, 4, 0x82F6, bytes.fromhex("20b86f"), J("rw"))
    patch(rom, 4, 0x82EE, bytes.fromhex("20faed"), J("rt"))
    patch(rom, 4, 0x82FE, bytes.fromhex("207183"), J("rl"))
    import lol_v3core as V
    # HarmLink's start (lol_upgrades' critter crusher, WRAM: its JMP $7E26 when it lets the harm through): a Goriya
    # Charger's boomerang ($5C, its owner's slot in $042C) stuns Link instead (no harm, no flashing); the first one
    # while no charge runs sets that goriya's charge going
    def harm(o):
        g = Asm(o)
        g.abs(0xEC, CSLOT).br(0xD0, "h_0").abs(0xAD, CTIME).br(0xF0, "h_0").b(0xA9, 0x01).abs(0x8D, CTIME)
        g.label("h_0")                                                  # (the charger touched Link: its charge ends)
        g.abs(0xBD, 0x034F).b(0xC9, 0x5C).br(0xD0, "h_o").abs(0xBC, 0x042C).abs(0xB9, 0x034F).b(0xC9, 0x05)
        g.br(0xD0, "h_o").abs(0xAD, HVE).b(0xC9, CHARGER_AT).br(0x90, "h_o")
        g.abs(0xAD, STUN).br(0xD0, "h_k").b(0xA9, STUN_FRAMES).abs(0x8D, STUN)
        g.abs(0xAD, CTIME).br(0xF0, "h_s").abs(0xAC, CSLOT).abs(0xB9, 0x034F).b(0xC9, 0x05).br(0xF0, "h_k")
        g.abs(0xBC, 0x042C)
        g.label("h_s").abs(0x8C, CSLOT).b(0xA9, CHARGE_DELAY).abs(0x8D, CHG).b(0xA9, 0x00).abs(0x8D, CTIME)
        g.label("h_k").b(0x38, 0x60)                                    # (C set: no harm)
        # (owner 2026-11-25) the Thorn Bracelet: a monster's touch (not a shot) costs it what Link loses (rings
        # halving), rounded up to whole hearts, $10 a heart (THD; the common stub makes the hit)
        g.label("h_o").b(0xA9, 0x00).abs(0x8D, THD).abs(0xAD, THORN[0]).b(0x29, THORN[1]).br(0xF0, "t_x")
        g.abs(0xBC, 0x034F).b(0xC0, 0x53).br(0xB0, "t_x").abs(0xB9, DMG).b(0x48, 0x29, 0x0F, 0x85, 0x0D)
        g.b(0x68, 0x29, 0xF0, 0x85, 0x0E).abs(0xAC, 0x0662).br(0xF0, "t_n")
        g.label("t_h").b(0x46, 0x0D, 0x66, 0x0E, 0x88).br(0xD0, "t_h")
        g.label("t_n").b(0xA5, 0x0D, 0xA4, 0x0E).br(0xF0, "t_u").b(0x18, 0x69, 0x01)
        g.label("t_u").b(0xC9, 0x10).br(0x90, "t_ok").b(0xA9, 0x0F)
        g.label("t_ok").b(0x0A, 0x0A, 0x0A, 0x0A).abs(0x8D, THD)
        g.label("t_x").b(0x18, 0x60)
        return g
    hat2 = free_in(rom, 2, len(harm(0x8000).bytes()))
    place(rom, 2, hat2, harm(hat2).bytes())
    # the common stub (banks 0-6: HarmLink runs from WRAM with any bank in): the far call, then harm or out
    HS = 0xBFC0
    hs = Asm(HS).b(*V.far(2, hat2)).br(0x90, "n").b(0x68, 0x68, 0x60)
    hs.label("n").abs(0xAD, THD).br(0xF0, "j").b(0x85, 0x07, 0xA9, 0x01, 0x85, 0x09, 0xA0, 0x0D).abs(0x20, 0x7C16)
    hs.label("j").abs(0x4C, 0x7E26)                                   # (the thorns' hit first: a sword hit)
    assert HS + len(hs.bytes()) <= 0xBFE4, hex(HS + len(hs.bytes()))
    for bank in range(7):
        place(rom, bank, HS, hs.bytes())
    hc = HS
    cw = BANK(1) + 0xB751 - 0x8000                                        # (lol_upgrades' CR_W)
    k = rom.find(bytes([0x4C, 0x26, 0x7E]), cw, cw + 0x20)
    assert k > 0
    rom[k + 1:k + 3] = bytes([hc & 0xFF, hc >> 8])

    w1 = lambda c: rom[BANK(1) + c + 0x3870 - 0x8000]
    GF = w1(0x7594 + 6)                                                   # blue goriya's first frame (type + 1)
    GPAL = [w1(PALT + GF + k) for k in range(4)]
    DMG5 = w1(DMG + 0x05)
    assert GF == 92 and w1(0x7594 + 7) == GF + 4 and DMG5 == 0x01, (GF, DMG5)
    def gob(o):                                                      # (bank 2, beside: InitObject's part)
        g = Asm(o)
        # any object's init in the charging goriya's slot ends the charge
        g.label("clr").abs(0xEC, CSLOT).br(0xD0, "c_p").b(0xA9, 0x00).abs(0x8D, CSLOT).abs(0x8D, CTIME).abs(0x8D, CHG)
        # a pols voice's init (a new room): the recorder's hold on blue pols voices ends (lol_newups' FREEZE)
        g.label("c_p").b(0xA5, 0x00, 0xC9, 0x16).br(0xD0, "c_r").b(0xA9, 0x00).abs(0x8D, 0x01B5)
        g.label("c_r").b(0x60)
    # the Goriya Charger: blue goriya ($05) at 12+ (frames GF-GF+3: palette 0, else theirs)
        g.label("i_go").b(0xC9, 0x05).br(0xD0, "i_gb").abs(0xAD, HVE).b(0xC9, CHARGER_AT).br(0xB0, "go_u")
        g.b(0xA9, DMG5).abs(0x8D, DMG + 0x05).b(0xA0, 0x03)
        g.label("go_v").abs(0xB9, "gopv").abs(0x99, PALT + GF).b(0x88).br(0x10, "go_v")
        g.label("i_gb").b(0x60, 0xEA, 0xEA)                         # (lol_wizzrobe: JMP its init)
        g.label("go_u").b(0xA9, CHARGER_HP).abs(0x9D, 0x0485).b(0xA9, CHARGER_DMG).abs(0x8D, DMG + 0x05).b(0xA0, 0x03)
        g.label("go_w").abs(0xB9, "gopu").abs(0x99, PALT + GF).b(0x88).br(0x10, "go_w").b(0x60)
        g.label("gopv").b(*GPAL)
        g.label("gopu").b(*[v & 0x80 for v in GPAL])
        return g
    gat = free_in(rom, 2, len(gob(0x8000).bytes()), 0xB940)
    global GO
    GO = gob(gat).labels
    place(rom, 2, gat, gob(gat).bytes())
    # bank 2: Y = 2, 3, 4
    a = Asm(D.MORE)
    for k, name in ((2, "fb"), (3, "edge"), (4, "init"), (6, "dodo"), (8, "arrow"), (10, "rk"), (11, "ed_m")):
        a.b(0xC0, k).br(0xD0, f"dn{k}").abs(0x4C, name).label(f"dn{k}")
    a.abs(0x4C, "wizz")                                                  # (9)
    # is a blue Aquamentus here? (C set: yes)
    a.label("blue").abs(0xAD, HVE).b(0xC9, BLUE_AQ_AT).br(0x90, "bl_r").b(0xA0, 0x0B)
    a.label("bl_lp").abs(0xB9, 0x034F).b(0xC9, 0x3D).br(0xF0, "bl_y").b(0x88).br(0xD0, "bl_lp")
    a.b(0x18)
    a.label("bl_r").b(0x60)
    a.label("bl_y").b(0x38, 0x60)
    # Y 2: the fireball X
    a.label("fb").abs(0x20, "blue").br(0xB0, "fb_m").b(0xA0, 0x00, 0x60)
    a.label("fb_m").b(0xA9, 0x00).abs(0x9D, 0x0394)                 # (as $8371 does each frame)
    a.label("fb_m2").b(0xB5, 0x70, 0xC9, 0x1C).br(0x90, "fb_b").b(0xC9, 0xDC).br(0xB0, "fb_b")
    a.b(0xB5, 0x84, 0xC9, 0x58).br(0x90, "fb_b").b(0xC9, 0xCC).br(0xB0, "fb_b")
    a.label("fb_l").b(0xA5, 0x70, 0x18, 0x69, 0x04, 0x38, 0xF5, 0x70).abs(0x20, DL["abs"]).b(0xC9, 0x0C).br(0xB0, "fb_d")
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
    a.label("init").abs(0x20, GO["clr"]).b(0xA9, 0x20).abs(0x8D, SPD).b(0xA9, 0x28).abs(0x8D, SPD + 1)   # darknut speeds: red, blue
    a.b(0xA5, 0x00, 0xC9, 0x0B).br(0xD0, "i_aq")
    a.b(0xA9, RED_DMG).abs(0x8D, DMG + 0x0B)
    a.abs(0xAD, HVE).b(0xC9, BROWN_AT).br(0x90, "i_r")
    a.b(0xA9, BROWN_DMG).abs(0x8D, DMG + 0x0B)
    a.b(0xA9, BROWN_HP).abs(0x9D, 0x0485).b(0xA9, BROWN_SPEED).abs(0x8D, SPD)
    a.abs(0xBD, 0x04BF).b(0x09, 0x08).abs(0x9D, 0x04BF)
    a.b(0xA9, 0x17).abs(0x8D, T1).b(0xA9, 0x27).abs(0x8D, T2).abs(0xAD, TUNIC).abs(0x8D, T3)
    a.label("i_set").b(0xA5, 0x15).abs(0xCD, FLAG).br(0xF0, "i_r").abs(0x8D, FLAG)   # (once a frame)
    a.abs(0x20, "queue")
    a.label("i_r").b(0x60)
    a.label("i_aq").b(0xC9, 0x3D).br(0xD0, "i_ot")
    a.abs(0xAD, HVE).b(0xC9, BLUE_AQ_AT).br(0x90, "i_back")
    a.b(0xA9, BLUE_AQ_HP).abs(0x9D, 0x0485)
    for k, t in enumerate((T1, T2, T3)):
        a.abs(0xAD, PAL1 + k).abs(0x8D, t)
    a.abs(0x4C, "i_set")
    # blue pols voice (lol_newups, 10+ containers): 5 health
    a.label("i_ot").b(0xC9, 0x16).br(0xD0, "i_mb").abs(0xAD, HVE).b(0xC9, 0x90).br(0x90, "i_back")
    a.b(0xA9, 0x50).abs(0x9D, 0x0485)
    a.label("i_back").b(0x60)
    # red moblin ($04) at 8+ (HVE $70): 6 health, 2 hearts on contact, blue (its 4 frames' sprite palette 1);
    # below: half a heart, red (palette 2). (The damage and palette tables are WRAM: set both ways.)
    a.label("i_mb").b(0xC9, 0x04).br(0xD0, "i_oc").b(0xA0, 0x80, 0xA9, 0x02, 0x48).abs(0xAD, HVE).b(0xC9, MOBLIN_AT)
    a.br(0x90, "i_mn").b(0x68, 0xA9, 0x60).abs(0x9D, 0x0485).b(0xA0, 0x02, 0xA9, 0x01, 0x48)
    a.label("i_mn").abs(0x8C, DMG + 0x04).b(0x68)
    for f in range(4):
        a.abs(0x8D, PALT + MOBLIN_FRAMES + f)
    a.b(0x60)
    # red octoroks ($07 slow, $08 fast) at 10+ (HVE $90): 4 health, the Zora's sprite palette 3 (frames 27-32)
    a.label("i_oc").b(0xC9, 0x07).br(0xF0, "oc").b(0xC9, 0x08).br(0xF0, "oc").abs(0x4C, GO["i_go"])
    a.label("oc").abs(0xAD, HVE).b(0xC9, OCTOROK_AT).br(0xB0, "oc_u").b(0xA0, 0x05)
    a.label("oc_v").abs(0xB9, "ocpv").abs(0x99, PALT + OCTOROK_FRAMES).b(0x88).br(0x10, "oc_v").b(0x60)
    a.label("oc_u").b(0xA9, 0x40).abs(0x9D, 0x0485).b(0xA0, 0x05)
    a.label("oc_w").abs(0xB9, "ocpu").abs(0x99, PALT + OCTOROK_FRAMES).b(0x88).br(0x10, "oc_w").b(0x60)
    a.label("ocpv").b(*OCTOROK_PAL)
    a.label("ocpu").b(*[(v & 0x80) | 3 for v in OCTOROK_PAL])
    # Y 10: a bomb octorok's rock (X), each frame after its move: touching Link? blast; else drawn as a red bomb
    a.label("rk").b(0xA9, 0x00).abs(0x9D, 0x0394).abs(0x4C, "fb_l")
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
    assert D.MORE + len(code) <= 0xB900, hex(D.MORE + len(code))
    place(rom, 2, D.MORE, code)
    def charger(at):
        c = Asm(at)
        # (bank 2, far-called from UpdateObject's entry for $05): the Goriya Charger's delay and charge
        c.label("gor").abs(0xEC, CSLOT).br(0xD0, "g_n")
        c.abs(0xAD, 0x066C).b(0x15, 0x3D).br(0xD0, "g_r")                       # (the clock / stunned: still)
        c.abs(0xAD, CTIME).br(0xD0, "g_mv")
        c.abs(0xAD, CHG).br(0xF0, "g_n").b(0xC9, 0x01).br(0xD0, "g_dc")
        # (owner 2026-11-25: chargers got stuck) the charge starts only from a square (x & $0F 0, y & $0F $0D), as
        # the goriya's own walk needs; till then it walks on
        c.b(0xB5, 0x70, 0x29, 0x0F).br(0xD0, "g_n").b(0xB5, 0x84, 0x29, 0x0F, 0xC9, 0x0D).br(0xD0, "g_n")
        c.label("g_dc").abs(0xCE, CHG).br(0xD0, "g_n")
        # the charge begins: along the axis Link is nearer lined up on
        c.b(0xA5, 0x70, 0x38, 0xF5, 0x70).br(0xB0, "g_a1").b(0x49, 0xFF, 0x69, 0x01)
        c.label("g_a1").b(0x85, 0x00)
        c.b(0xA5, 0x84, 0x38, 0xF5, 0x84).br(0xB0, "g_a2").b(0x49, 0xFF, 0x69, 0x01)
        c.label("g_a2").b(0xC5, 0x00).br(0x90, "g_h")
        c.label("g_v").b(0xA0, 0x04, 0xA5, 0x84, 0xD5, 0x84).br(0xB0, "g_s").b(0xA0, 0x08).br(0xD0, "g_s")
        c.label("g_h").b(0xA0, 0x01, 0xA5, 0x70, 0xD5, 0x70).br(0xB0, "g_s").b(0xA0, 0x02)
        c.label("g_s").b(0x94, 0x98, 0xA9, CHARGE_MAX).abs(0x8D, CTIME)
        c.label("g_r").b(0x38, 0x60)
        c.label("g_n").b(0x18, 0x60)                                         # (C clear: the goriya's own)
        c.label("g_mv").abs(0x20, "g_st").abs(0xAD, CTIME).br(0xF0, "g_r").abs(0x20, "g_st")
        c.abs(0xAD, CTIME).b(0xC9, 0x02).br(0x90, "g_r").abs(0xCE, CTIME).b(0x38, 0x60)
        # one pixel; first: time up, the room's edge, 16 px past Link or a wall ahead end it (each pixel: goriyas
        # stand anywhere, not only on squares)
        c.label("g_st").abs(0xAD, CTIME).b(0xC9, 0x01).br(0xF0, "g_end")
        c.b(0xB5, 0x98, 0x4A).br(0x90, "g_nr")                                          # right
        c.b(0xB5, 0x70, 0xC9, 0xD0).br(0xB0, "g_end").b(0x38, 0xE5, 0x70).br(0x90, "g_t")
        c.b(0xC9, 0x10).br(0xB0, "g_end").br(0x90, "g_t")
        c.label("g_nr").b(0x4A).br(0x90, "g_nl")                                         # left
        c.b(0xB5, 0x70, 0xC9, 0x21).br(0x90, "g_end").b(0xA5, 0x70, 0x38, 0xF5, 0x70).br(0x90, "g_t")
        c.b(0xC9, 0x10).br(0xB0, "g_end").br(0x90, "g_t")
        c.label("g_nl").b(0x4A).br(0x90, "g_nd")                                         # down
        c.b(0xB5, 0x84, 0xC9, 0xBD).br(0xB0, "g_end").b(0x38, 0xE5, 0x84).br(0x90, "g_t")
        c.b(0xC9, 0x10).br(0xB0, "g_end").br(0x90, "g_t")
        c.label("g_nd").b(0xB5, 0x84, 0xC9, 0x5E).br(0x90, "g_end")                     # up
        c.b(0xA5, 0x84, 0x38, 0xF5, 0x84).br(0x90, "g_t").b(0xC9, 0x10).br(0xB0, "g_end")
        c.label("g_t").b(0xB5, 0x98, 0x85, 0x0F).abs(0x20, 0xEDFA).abs(0xCD, 0x034A).br(0xB0, "g_end")
        c.label("g_go").b(0xB5, 0x98, 0x4A).br(0x90, "g_m1").b(0xF6, 0x70, 0x60)
        c.label("g_m1").b(0x4A).br(0x90, "g_m2").b(0xD6, 0x70, 0x60)
        c.label("g_m2").b(0x4A).br(0x90, "g_m3").b(0xF6, 0x84, 0x60)
        c.label("g_m3").b(0xD6, 0x84, 0x60)
        # the end: back onto the square it last passed (the way it came is open), so its own walk goes on
        c.label("g_end").b(0xA9, 0x00).abs(0x8D, CTIME).abs(0x8D, CSLOT)
        c.b(0xB5, 0x98, 0x4A).br(0x90, "e_1").b(0xB5, 0x70, 0x29, 0xF0, 0x95, 0x70, 0x60)              # right
        c.label("e_1").b(0x4A).br(0x90, "e_2").b(0xB5, 0x70, 0x18, 0x69, 0x0F, 0x29, 0xF0, 0x95, 0x70, 0x60)  # left
        c.label("e_2").b(0x4A).br(0x90, "e_3").b(0xB5, 0x84, 0x38, 0xE9, 0x0D, 0x29, 0xF0, 0x18, 0x69, 0x0D)  # down
        c.b(0x95, 0x84, 0x60)
        c.label("e_3").b(0xB5, 0x84, 0x18, 0x69, 0x02, 0x29, 0xF0, 0x18, 0x69, 0x0D, 0x95, 0x84, 0x60)     # up
        return c
    # (2026-11-26) bank 2 fills up: the charger's code is placed last (late(), from lol_build once every other
    # module's code is in): bank 2's smallest hole that holds it, else bank 3's tail, else bank 6's free runs
    global _LATE
    _LATE = charger
    s2 = Asm(STUB_W)
    s2.b(0xA0, 0x08).abs(0x4C, a.labels["arrow"])
    place(rom, 2, STUB_W, s2.bytes())
    # (2026-11-26, lag: the arrow check runs for every monster every frame, arrow or not) its setup (WRAM
    # $7D74-$7D85: the type $04, the damage $20 / $40 by the arrow, the size $0B): no arrow ($AC,Y 0, which never
    # hits): $06 0 and out of the check at once (in WRAM); else a bank 7 stub (the check runs with bank 1, 2 or 4
    # in), to bank 0 only with piercing arrows (the arrow hit's type, bank 2), the miser's bow or the bow of greed
    # (lol_newups)
    import lol_newups as N
    m, g = N.bit("misers bow"), N.bit("bow of greed")

    def az2(o):
        q = Asm(o)
        q.abs(0xAD, U.PIERCING[0]).b(0x29, U.PIERCING[1]).br(0xF0, "np").b(*V.far(2, a.labels["arrow"]))
        q.label("np").abs(0xAD, 0x0659).b(0x4A, 0xA9, 0x20).br(0xB0, "w").b(0x0A)    # (the wooden arrow, 1: $20)
        q.label("w").b(0x48).abs(0xAD, m[0]).b(0x29, m[1]).br(0xD0, "b")
        q.abs(0xAD, g[0]).b(0x29, g[1]).br(0xD0, "b").b(0x68, 0xA0, 0x0B, 0x84, 0x0D, 0x60)
        return q.label("b").b(0x68).abs(0x4C, N.ARROW0)
    z_at = V.put0(rom, az2).cpu

    def aw(o):
        q = Asm(o)
        for at, bt in (m, g, U.PIERCING):
            q.abs(0xAD, at).b(0x29, bt).br(0xD0, "f")
        q.abs(0xAD, 0x0659).b(0x4A, 0xA9, 0x20).br(0xB0, "w").b(0x0A)
        q.label("w").b(0xA0, 0x0B, 0x84, 0x0D, 0x60)
        return q.label("f").b(*V.far(0, z_at)).b(0x60)
    w_at = V.put7(rom, aw).cpu
    patch(rom, 1, 0xB5E4, bytes.fromhex("a9048509a920ac5906c001f0010aa00b840d"),
          bytes([0xA8, 0xD0, 0x03, 0x85, 0x06, 0x60, 0xA9, 0x04, 0x85, 0x09, 0x20, w_at & 0xFF, w_at >> 8, 0x4C, 0x86,
                 0x7D]) + b"\xEA" * 2)       # (A: the arrow's state; TAY for its Z, Y reloaded after)
    # (2026-11-24) the arrow check runs from WRAM with whatever bank the object's update has in: the persons' (bank
    # 1: the old men in levels) ran into bank 1's empty $BD58 and on into lol_pictures' STUB, loading the pictures
    # (picture off: a black screen) and scribbling RAM (Link hurt) every frame. Bank 1 (the persons' updates; banks
    # 2 and 4 have theirs): a far call.
    import lol_v3core as V
    for bank in (1,):
        sf = Asm(STUB_W)
        sf.b(*V.far(2, a.labels["arrow"])).b(0x60)
        place(rom, bank, STUB_W, sf.bytes())
    notes.append(f"brown darknuts at 9 containers, blue Aquamentus at 10 ({len(code)} bytes in bank 2 at ${D.MORE:04X})")


_LATE = None


def late(rom: bytearray, notes: list) -> None:
    """The Goriya Charger's code, placed once everything else is (lol_build, before the seed code)."""
    if _LATE is None:
        return
    import lol_v3core as V
    from lol_newups import best_in, free_in
    charger = _LATE
    n_ch = len(charger(0x8000).bytes())
    cbank = None
    # (2026-11-26: the unseeded build's bank 6 holds the in-game roller: none of those has room) then the data banks'
    # free space below their trampoline (the charger calls only the fixed bank)
    for bk, lo, hi in ((2, 0x8000, 0xBF00), (3, 0xB300, 0xBE00), (6, 0x9D66, 0xA000), (6, 0xBC10, 0xBD00),
                       (14, 0x8000, 0xBB80), (13, 0x8000, 0xBB80)):
        try:
            cat = best_in(rom, bk, n_ch, lo, hi)
        except AssertionError:
            continue
        cbank = bk
        break
    assert cbank is not None, "no room for the Goriya Charger"
    ch = charger(cat)
    place(rom, cbank, cat, ch.bytes())
    # bank 4: UpdateObject's entry for $05 -> a far call (C set: the charger's handled it), else $8119
    # (2026-11-26, lag: a far call for every blue goriya every frame) only the charger's slot goes there (its "gor"
    # starts with that check)
    gs = free_in(rom, 4, 18, 0xBE00, 0xBFB0)                              # (bank 4's tail)
    st = Asm(gs).abs(0xEC, CSLOT).br(0xD0, "o").b(*V.far(cbank, ch.labels["gor"])).br(0xB0, "r")
    st.label("o").abs(0x4C, 0x8119).label("r").b(0x60)
    place(rom, 4, gs, st.bytes())
    ut = BANK(4) + V.TABLES4 + 3 + 2 * 0x05 - 0x8000                      # UpdateObject's entry for $05
    assert rom[ut:ut + 4] == bytes([0x19, 0x81, 0x19, 0x81])
    rom[ut:ut + 2] = bytes([gs & 0xFF, gs >> 8])
    notes.append(f"Goriya Charger: {n_ch} bytes in bank {cbank} at ${cat:04X}")

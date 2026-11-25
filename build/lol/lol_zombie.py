"""Legend of Link: Zombie Link and the brain potion (owner, 2026-11-24; upgrades in lol_uptable).

Zombie Link (75, tier 2, rare; only at exactly 3 heart containers, with no ring and without regen):
- health: the containers stay, the health goes to 0 (as the mugger leaves 3 hearts: every heart empty; the next hit
  kills) when bought, and after every start or continue; potions (without the brain potion) drain half his
  containers' worth, fairies 3 hearts, a heart 1, a fairy fountain everything (never below 0). Nothing else heals him:
  the frame hook puts back any rise it didn't allow (LAST: the health it last saw); hitting a humanoid with a melee
  blow heals a quarter of the damage (a damage point a heart: the doubled wood sword's 2 heals half a heart), and
  the brain potion's refill is allowed (ALLOW).
- melee (the sword's and the wand's swing; not beams) deals double; he takes double, except half from touching a
  Pols Voice, Gibdo, Ghini or Stalfos, and 4x from his own candle flame with the holy fire.
- drawn as the blue Moblins are in dungeons: Link's frames use sprite palette 3 (teal outside, each level's in a
  dungeon); set at each start / continue and when bought, put back for a file without him.
- no low-health beep; rings leave every prize list (lol_odds' even spread, level 9's upgrade).
Brain potion (50, tier 1; with Zombie Link and a potion, never with the bat potion): potions are brain potions (their
pictures: lol_pictures) and refill him as a normal potion does.

Bank 0 (lib, far-called or called from other bank 0 code): z_set0 z_sync z_drain z_heal z_frame z_dmg z_pot z_cont
z_buy z_item z_pond z_melee. RAM: LAST $600F / $6010, ALLOW $6011, ZT $6012-$6013 (file 2's and 3's names: unused)."""
from lol_af import Asm, BANK, place, patch

LAST_LO, LAST_HI, ALLOW, ZT = 0x600F, 0x6010, 0x6011, 0x6340   # (ZT: file 2's spare flags; $6012 on:
#  lol_upgrades' cave lines)
PALT, START = 0x76DF, 0x7594             # WRAM: the frames' palettes; each type's first frame (by type + 1)
WRAM_DELTA = 0x3870
HUMANOIDS = (0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x0B, 0x0C, 0x23, 0x24, 0x28)
SOFT = (0x16, 0x21, 0x22, 0x2A, 0x30)    # Pols Voice, Ghinis, Stalfos, Gibdo: half damage
LIB = {}


def link_frames(rom):
    w = lambda a: rom[BANK(1) + a + WRAM_DELTA - 0x8000]
    s0, s1 = w(START), w(START + 1)        # (Link's: the first entry's frames)
    return s0, s1, bytes(w(PALT + i) for i in range(s0, s1))


def lib(rom):
    if LIB:
        return LIB
    import lol_v3core as V
    import lol_uptable as T
    zb, holy, brain = T.bit("zombie link"), T.bit("holy fire"), T.bit("brain potion")
    s0, s1, orig = link_frames(rom)

    def build(org):
        a = Asm(org)
        isz = lambda no: a.abs(0xAD, zb[0]).b(0x29, zb[1]).br(0xF0, no)
        # z_set0: health 0
        a.label("z_set0").abs(0xAD, 0x066F).b(0x29, 0xF0).abs(0x8D, 0x066F).b(0xA9, 0x00).abs(0x8D, 0x0670)
        a.label("z_sync").abs(0xAD, 0x066F).b(0x29, 0x0F).abs(0x8D, LAST_HI).abs(0xAD, 0x0670).abs(0x8D, LAST_LO)
        a.b(0x60)
        # z_drain: A hearts off (0 at least)
        a.label("z_drain").abs(0x8D, ZT).abs(0xAD, 0x066F).b(0x29, 0x0F, 0x38).abs(0xED, ZT).br(0x90, "dr_0")
        a.abs(0x8D, ZT).abs(0xAD, 0x066F).b(0x29, 0xF0).abs(0x0D, ZT).abs(0x8D, 0x066F).abs(0x4C, "z_sync")
        a.label("dr_0").abs(0x4C, "z_set0")
        # z_heal: A = the damage dealt ($10 a point): its quarter in hearts (A * 4 of $0670's units), up to the max
        a.label("z_heal").abs(0x8D, ZT).b(0xA9, 0x00).abs(0x8D, ZT + 1)
        a.abs(0x0E, ZT).abs(0x2E, ZT + 1).abs(0x0E, ZT).abs(0x2E, ZT + 1)
        a.abs(0xAD, 0x0670).b(0x18).abs(0x6D, ZT).abs(0x8D, 0x0670)
        a.abs(0xAD, 0x066F).b(0x29, 0x0F).abs(0x6D, ZT + 1).abs(0x8D, ZT)               # the new hearts nibble
        a.abs(0xAD, 0x066F).b(0x4A, 0x4A, 0x4A, 0x4A).abs(0xCD, ZT).br(0xB0, "hl_ok")     # above the containers?
        a.abs(0x8D, ZT).b(0xA9, 0xFF).abs(0x8D, 0x0670)
        a.label("hl_ok").abs(0xAD, 0x066F).b(0x29, 0xF0).abs(0x0D, ZT).abs(0x8D, 0x066F).abs(0x4C, "z_sync")
        # z_frame: a rise it didn't allow is put back
        a.label("z_frame").abs(0xAD, 0x066F).b(0x29, 0x0F).abs(0xCD, LAST_HI).br(0x90, "fr_s").br(0xD0, "fr_up")
        a.abs(0xAD, 0x0670).abs(0xCD, LAST_LO).br(0x90, "fr_s").br(0xF0, "fr_s")
        a.label("fr_up").abs(0xAD, ALLOW).br(0xD0, "fr_s")
        a.abs(0xAD, 0x066F).b(0x29, 0xF0).abs(0x0D, LAST_HI).abs(0x8D, 0x066F).abs(0xAD, LAST_LO).abs(0x8D, 0x0670)
        a.label("fr_s").abs(0x20, "z_sync").b(0xA5, 0xE0).br(0xD0, "fr_r").b(0xA9, 0x00).abs(0x8D, ALLOW)
        a.label("fr_r").b(0x60)
        # z_dmg: the damage to Link ($0D hearts, $0E fraction; X the attacker): the ring's halving, then the zombie's
        a.label("z_dmg").abs(0xAC, 0x0662).br(0xF0, "dm_z")
        a.label("dm_r").b(0x46, 0x0D, 0x66, 0x0E, 0x88).br(0xD0, "dm_r")
        a.label("dm_z").abs(0xAD, zb[0]).b(0x29, zb[1]).br(0xF0, "dm_x")
        a.b(0xE0, 0x10).br(0x90, "dm_m").b(0xE0, 0x12).br(0xB0, "dm_m")          # his own flame (slots $10/$11)
        a.abs(0xAD, holy[0]).b(0x29, holy[1]).br(0xF0, "dm_2").abs(0x20, "dbl")
        a.label("dm_2").abs(0x4C, "dbl")
        a.label("dm_m").abs(0xBD, 0x034F)
        for t in SOFT:
            a.b(0xC9, t).br(0xF0, "dm_h")
        a.abs(0x4C, "dbl")
        a.label("dm_h").b(0x46, 0x0D, 0x66, 0x0E)
        a.label("dm_x").b(0x60)
        a.label("dbl").b(0x06, 0x0E, 0x26, 0x0D, 0xA5, 0x0D, 0xC9, 0x10).br(0x90, "db_r")
        a.b(0xA9, 0x0F, 0x85, 0x0D, 0xA9, 0xFF, 0x85, 0x0E)
        a.label("db_r").b(0x60)
        # z_pot: a potion drunk (from bank 5's UsePotion, the bat potion's not owned): brain -> a normal refill
        # (allowed); else half his containers' worth drained
        a.label("z_pot").abs(0xCE, 0x065E).abs(0xAD, brain[0]).b(0x29, brain[1]).br(0xF0, "pt_d")
        a.b(0xA9, 0x01, 0x85, 0x63).abs(0x8D, ALLOW).b(0xA9, 0x02, 0x85, 0xE0, 0x60)
        a.label("pt_d").abs(0xAD, 0x066F).b(0x4A, 0x4A, 0x4A, 0x4A, 0x18, 0x69, 0x01, 0x4A).abs(0x4C, "z_drain")
        # z_cont: a start or continue (and z_buy: bought): health 0 and the palette, or the palette put back
        a.label("z_cont").abs(0xAD, zb[0]).b(0x29, zb[1]).br(0xD0, "z_buy")
        a.b(0xA2, s1 - s0 - 1).label("ct_l").abs(0xBD, "orig").abs(0x9D, PALT + s0).b(0xCA).br(0x10, "ct_l").b(0x60)
        a.label("z_buy").abs(0x20, "z_set0")
        a.b(0xA2, s1 - s0 - 1).label("by_l").abs(0xBD, "orig").b(0x09, 0x03).abs(0x9D, PALT + s0).b(0xCA)
        a.br(0x10, "by_l").b(0x60)
        # z_item: A = an item taken (kept): a heart drains 1, a fairy 3
        a.label("z_item").b(0x48).abs(0xAD, zb[0]).b(0x29, zb[1]).br(0xF0, "it_r").b(0x68, 0x48)
        a.b(0xC9, 0x22).br(0xD0, "it_f").b(0xA9, 0x01).abs(0x20, "z_drain").abs(0x4C, "it_r")
        a.label("it_f").b(0xC9, 0x23).br(0xD0, "it_r").b(0xA9, 0x03).abs(0x20, "z_drain")
        a.label("it_r").b(0x68, 0x60)
        # z_pond: a fairy fountain: everything
        a.label("z_pond").abs(0xAD, zb[0]).b(0x29, zb[1]).br(0xF0, "pd_r").abs(0x4C, "z_set0")
        a.label("pd_r").b(0x60)
        # z_melee (the damage hook, X the monster, $00 the weapon slot, $07 the damage): the sword's ($0D) or the
        # wand's ($12) blow doubled; a humanoid's heals a quarter of it
        a.label("z_melee").abs(0xAD, zb[0]).b(0x29, zb[1]).br(0xF0, "ml_r")
        a.b(0xA5, 0x00, 0xC9, 0x0D).br(0xF0, "ml_go").b(0xC9, 0x12).br(0xD0, "ml_r")
        a.label("ml_go").b(0x06, 0x07).br(0x90, "ml_h").b(0xA9, 0xFF, 0x85, 0x07)
        a.label("ml_h").abs(0xBD, 0x034F)
        for t in HUMANOIDS:
            a.b(0xC9, t).br(0xF0, "ml_y")
        a.label("ml_r").b(0x60)
        a.label("ml_y").b(0xA5, 0x07).abs(0x4C, "z_heal")
        a.label("orig").b(*orig)
        return a
    a = V.put0(rom, build)
    LIB.update(a.labels)
    LIB["far"] = lambda name: V.far(0, LIB[name])
    return LIB


def apply(rom: bytearray, notes: list) -> None:
    """The hooks outside bank 0 (lol_upgrades and lol_bombup call the lib directly)."""
    import lol_v3core as V
    import lol_uptable as T
    from lol_newups import put, free_in
    L = lib(rom)
    zb = T.bit("zombie link")
    # the damage to Link (WRAM $7B5B: the ring's halving loop) -> a common-area stub -> z_dmg
    def build_c(org):
        c = Asm(org)
        c.label("dmg").b(*L["far"]("z_dmg")).b(0x60)
        c.label("beep").abs(0xAD, zb[0]).b(0x29, zb[1]).br(0xD0, "bp_r").abs(0xAD, 0x066F).b(0x29, 0x0F)
        c.label("bp_r").b(0x60)
        return c
    n = len(build_c(0xBE00).bytes())
    at = next(x for x in range(0xBE00, 0xBF40)
              if all(rom[BANK(b) + x - 0x8000 + k] == 0xFF for b in range(7) for k in range(-1, n + 1)))
    c = build_c(at)
    code = c.bytes()
    for bank in range(7):
        place(rom, bank, at, code)
    d = c.labels["dmg"]
    patch(rom, 1, 0x7B5B + WRAM_DELTA, bytes.fromhex("ac6206f007460d660e88d0f9"),
          bytes([0x20, d & 0xFF, d >> 8]) + b"\xEA" * 9)
    bp = c.labels["beep"]
    patch(rom, 7, 0xED18, bytes.fromhex("ad6f06290fd008"), bytes([0x20, bp & 0xFF, bp >> 8, 0xEA, 0xEA, 0xD0, 0x08]))
    # start / continue (bank 5 $8B81: LDA #$FF / STA $0670, after the hearts)
    def b5(org):
        a = Asm(org)
        a.b(0xA9, 0xFF).abs(0x8D, 0x0670).b(*L["far"]("z_cont")).b(0x60)
        return a
    s5 = put(rom, 5, b5)
    patch(rom, 5, 0x8B81, bytes.fromhex("a9ff8d7006"), bytes([0x20, s5.cpu & 0xFF, s5.cpu >> 8, 0xEA, 0xEA]))
    notes.append(f"zombie link: lib in bank 0 (${L['z_set0']:04X}), damage / beep hooks (common ${at:04X})")


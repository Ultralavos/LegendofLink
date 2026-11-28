"""Legend of Link (test 1): experience hearts on a clean PRG1 ROM.

XP per kill = the enemy's value - your heart containers (nothing if that is 0 or less). Every 50 XP gives a heart
container (and a heart), up to 16. The XP is kept at $0677: an inventory byte the game never uses, saved with the
file.

Usage: python3 lol_build.py <PRG1 ROM> <out.ips> [out.nes]
"""
import sys

XP = 0x0677                     # the XP (saved with the file)
HUD_CPU = 0xBE60                # bank 5 (mapped when its hook runs): the status bar's XP code ($BE45-$BF4F free)
HVE = 0x016F                    # the containers enemies level up by (HeartValues; hard mode + 3; build_hud)
TMP = 0x0173                    # scratch (RAM: the stack page's unused bottom)
XP_PER_HEART = 50
HEART_CONTAINER_ITEM = 0x1A
TAKE_ITEM = 0x7370              # TakeItem (WRAM): A = item; the jingle, the container and a heart

# The enemy values (types below $4B; anything not listed gives nothing). BOSS values are flat: no containers taken off.
BOSS = 0x80
XP_VALUES = {
    0x07: 5, 0x08: 5, 0x09: 5, 0x0A: 5,        # octoroks (all four)
    0x0D: 5, 0x0E: 5,                          # tektites
    0x14: 4, 0x15: 4, 0x1B: 4, 0x1C: 4, 0x1D: 4,   # gels, keese
    0x13: 6,                                   # zol (killed outright; a split one becomes gels)
    0x28: 5,                                   # rope (8+ containers: 11)
    0x10: 6, 0x03: 6, 0x04: 6,                 # red leever, both moblins
    0x0F: 7, 0x1A: 7, 0x11: 7,                 # blue leever, peahat, zora
    0x01: 9, 0x02: 9,                          # lynels
    0x2A: 6,                                   # stalfos (8+ containers: 10)
    0x06: 6, 0x05: 7,                          # red goriya, blue goriya
    0x27: 5,                                   # wallmaster
    0x0B: 7, 0x0C: 12,                         # red darknut, blue darknut
    0x30: 7, 0x17: 8, 0x16: 7,                 # gibdo, like like, pols voice
    0x24: 7, 0x23: 15,                         # red wizzrobe, blue wizzrobe (the enum's names are swapped)
    0x3A: 10, 0x3B: 12,                        # red lanmola, blue lanmola
    0x12: 8,                                   # vire (killed in one shot; a split one becomes keese)
    0x41: 7,                                   # moldorm
    0x31: BOSS | 8, 0x32: BOSS | 15,           # triple dodongo (each), single dodongo
    0x3D: BOSS | 15,                           # aquamentus
    0x18: BOSS | 10,                           # digdogger babies
    0x34: BOSS | 15, 0x33: BOSS | 20,          # gohma: red-orange (level 6), blue (level 8, the tougher one)
    0x42: BOSS | 5, 0x43: BOSS | 10, 0x44: BOSS | 15, 0x45: BOSS | 20,   # gleeok: 1 head (not given: 5), 2, 3, 4
    0x3C: BOSS | 20,                           # manhandla
    0x47: BOSS | 30, 0x48: BOSS | 30,          # patra
}
XP_HARD = {0x2A: 10, 0x28: 11, 0x30: 11}       # stalfos, ropes and (red) gibdos once Link has 8 containers
HARD_HEARTS = 0x70                             # HeartValues' high nibble = containers - 1: 8 containers
TABLE_SIZE = 0x4B
XP_EXT = 0xBC10                                # bank 4 free ($BC0D-$BC83): the value, with the 9 / 10 container enemies
XP_BROWN, XP_BLUE_AQUA = 14, BOSS | 20         # brown darknut (blue's 12 + 2), blue Aquamentus (15 + 5)
XP_BLUE_POLS = 7 + 3                           # blue pols voice (lol_newups): the pols voice's 7 + 3
XP_BLUE_MOBLIN = 10                            # red moblins at 8+ containers (lol_enemies2): blue, charging
XP_BOMB_OCTOROK = 12                           # red octoroks at 10+ containers (lol_enemies2): Zora-colored, red bombs
XP_CHARGER = 15                                # Goriya Charger: blue goriyas at 12+ containers (lol_enemies2)
XP_BOMBER = 16                                 # Bomber Wizzrobe: red wizzrobes at 14+ containers (lol_wizzrobe)

HOOK = 0x1FCCD                                 # bank 7 $FCBD: LDA $034F,X / CMP #$11 / BEQ $FCC7 / INC RoomKillCount
HOOK_BYTES = bytes.fromhex("bd4f03c911f003ee4f03")
BANK4 = 16 + 4 * 0x4000
FREE = 0xB46F                                  # bank 4's free run (2785 bytes of $FF in PRG1)


def build_helper(cpu: int) -> bytes:
    """The death routine's kill-count step (bank 7, bank 4 switched in) becomes JSR helper. X = the enemy's slot."""
    code = bytearray()
    lab, fix = {}, []

    def b(*xs): code.extend(xs)
    def br(op, name): b(op, 0); fix.append((len(code) - 1, name, "rel"))
    def ab(op, addr): b(op, addr & 0xFF, addr >> 8)
    def abl(op, name): b(op, 0, 0); fix.append((len(code) - 2, name, "abs"))
    def L(name): lab[name] = len(code)

    b(0x98, 0x48)                          # TYA / PHA
    ab(0xBD, 0x034F)                       # LDA ObjType,X
    b(0xC9, TABLE_SIZE); br(0x90, "known"); abl(0x4C, "orig")   # CMP #$4B / BCS orig (as BCC / JMP: too far)
    L("known")
    b(0xA8)                                # TAY
    ab(0xAD, 0x066F); b(0xC9, 0xF0); br(0x90, "lv"); abl(0x4C, "orig")   # sixteen containers: no more XP
    L("lv"); ab(0xAD, HVE)                        # (the containers enemies level up by: hard mode + 3)
    b(0xC9, HARD_HEARTS); br(0x90, "soft") # 8+ containers: stalfos and ropes are worth more
    b(0xC0, 0x2A); br(0xD0, "nst"); b(0xA9, XP_HARD[0x2A]); br(0xD0, "calc")
    L("nst"); b(0xC0, 0x28); br(0xD0, "nrp"); b(0xA9, XP_HARD[0x28]); br(0xD0, "calc")
    L("nrp"); b(0xC0, 0x30); br(0xD0, "nwm"); b(0xA9, XP_HARD[0x30]); br(0xD0, "calc")
    L("nwm"); b(0xC0, 0x27); br(0xD0, "soft"); b(0xC9, 0xB0); br(0x90, "soft"); b(0xA9, 15); br(0xD0, "calc")   # red wallmaster (12)
    L("soft"); ab(0x20, XP_EXT)            # JSR ext: LDA table,Y (the value), or a brown darknut's / blue
                                           # Aquamentus' (lol_enemies2)
    br(0xF0, "orig")
    br(0x10, "calc")                       # a boss: flat
    b(0x29, 0x7F); br(0x10, "add")         # AND #$7F / BPL add
    L("calc"); ab(0x8D, TMP)               # STA tmp (the value)
    ab(0xAD, 0x066F)                       # LDA HeartValues (containers - 1 in the high nibble)
    b(0x4A, 0x4A, 0x4A, 0x4A)              # LSR x4: n = containers - 1
    b(0x49, 0xFF, 0x18); ab(0x6D, TMP)     # EOR #$FF / CLC / ADC value: value + ~n = value - containers
    br(0x90, "orig"); br(0xF0, "orig")     # nothing if 0 or less
    L("add"); b(0x18); ab(0x6D, XP)        # CLC / ADC XP
    ab(0x8D, XP)
    L("again"); abl(0x20, "thr"); ab(0xAD, XP)   # TMP = a heart level's XP
    ab(0xCD, TMP); br(0x90, "orig")             # below the level's XP: done
    b(0x38); ab(0xED, TMP); ab(0x8D, XP)        # XP -= it
    b(0x8A, 0x48)                          # TXA / PHA
    b(0xA9, HEART_CONTAINER_ITEM); ab(0x20, TAKE_ITEM)   # LDA #heart container / JSR TakeItem
    b(0x68, 0xAA)                          # PLA / TAX
    ab(0xAD, 0x066F); b(0xC9, 0xF0); br(0x90, "again")   # a boss's 30 can be worth more than one heart
    b(0xA9, 0x00); ab(0x8D, XP)            # sixteen: XP stays 0
    L("orig"); b(0x68, 0xA8)               # PLA / TAY
    ab(0xBD, 0x034F); b(0xC9, 0x11); br(0xF0, "ret")   # the vanilla step: no kill count for the zora
    ab(0xEE, 0x034F)                       # INC RoomKillCount
    L("ret"); b(0x60)
    L("thr"); ab(0xAD, 0x7FF8)                 # lol_modes' hard mode: 100 a heart level
    br(0xF0, "t50"); b(0xA9, 2 * XP_PER_HEART); br(0xD0, "tst")
    L("t50"); b(0xA9, XP_PER_HEART)
    L("tst"); ab(0x8D, TMP); b(0x60)
    # Stalfos (beams) and ropes (HP, speed) are the second quest's once Link has 8 containers, in every dungeon:
    # the three LDY CurSaveSlot / LDA QuestNumbers,Y checks in bank 4 call this instead (Z clear = harder).
    L("hard"); b(0xA4, 0x16); ab(0xAD, HVE); b(0xC9, HARD_HEARTS); br(0xB0, "h_yes")
    b(0xA9, 0x00, 0x60)
    L("h_yes"); b(0xA9, 0x01, 0x60)
    L("table")
    code.extend(XP_VALUES.get(t, 0) for t in range(TABLE_SIZE))
    for at, name, kind in fix:
        if kind == "rel":
            d = lab[name] - (at + 1); assert -128 <= d < 128, (name, at, lab[name]); code[at] = d & 0xFF
        else:
            a = cpu + lab[name]; code[at], code[at + 1] = a & 0xFF, a >> 8
    build_helper.labels = {k: cpu + v for k, v in lab.items()}
    return bytes(code)


HARD_CHECKS = (0x92C7, 0x9348, 0x9388)          # bank 4: rope HP, rope speed, stalfos beams


HUD_HOOK = 16 + 0x0654B                        # World_ChangeRupees' LDA FrameCounter / LSR (bank 1 code run from RAM)
HUD_HOOK_BYTES = bytes.fromhex("a5154a")
BANK5 = 16 + 5 * 0x4000


XP_ICON_TILE = 0x31                            # CommonBackgroundPatterns' tile $4E: blank and unused in PRG1
XP_ICON_CHR = 16 + 0x0877F + XP_ICON_TILE * 16
XP_ICON = ("........",                         # 'X' and 'P' in one tile, color 3 (the lightest in that column)
           "3.3.333.",
           "3.3.3.3.",
           ".3..333.",
           "3.3.3...",
           "3.3.3...",
           "........",
           "........")


def icon_bytes(rows) -> bytes:
    low, high = bytearray(8), bytearray(8)
    for y, row in enumerate(rows):
        for x, px in enumerate(row):
            c = 0 if px == "." else int(px)
            low[y] |= (c & 1) << (7 - x); high[y] |= (c >> 1) << (7 - x)
    return bytes(low + high)


def build_hud(cpu: int) -> bytes:
    """'XP' and the two digits of the XP in the status bar's empty row under the rupees (PPU $208B), written to
    the dynamic tile buffer on the frames the game doesn't format the status bar (as the 3Q/4Q item counter)."""
    # every frame: HVE = HeartValues, + 3 containers in hard mode (lol_modes' HARD), $FF at most: the containers
    # the enemies level up by (their checks read HVE)
    pre = bytes([0xAD, 0xF8, 0x7F, 0xF0, 0x02, 0xA9, 0x30,                   # LDA HARD / BEQ / LDA #$30
                 0x18, 0x6D, 0x6F, 0x06, 0x90, 0x02, 0xA9, 0xFF,              # CLC / ADC HeartValues / BCC / LDA #$FF
                 0x8D, HVE & 0xFF, HVE >> 8])                                 # STA HVE
    # (owner 2026-11-25) unseeded: lol_names' HVE instead (also a file named IDDQD: as at 16 containers): a JSR to its
    # bank 5 stub (patched by lol_names.apply)
    import lol_fixed as _fx
    if not _fx.FIXED:
        import lol_names
        lol_names.HVE_FAR_AT[0] = cpu
        pre = bytes([0x20, 0xFF, 0xFF])
    # the bait's item palette (WRAM $72EC + 6, its row of the item attribute table): blue (1) with the poison bait
    # upgrade (lol_uptable, UP5 bit 7), else red (2)
    import lol_uptable as UT
    pb = UT.bit("poison bait")[0]
    pre += bytes([0xA9, 0x02, 0x2C, pb & 0xFF, pb >> 8, 0x10, 0x02, 0xA9, 0x01, 0x8D, 0xF2, 0x72])
    cpu += len(pre)
    # (every other frame: the game's own status bar work, the heart row, on the others)
    w = cpu + 10 + 5                                     # write: after the RTS and its table
    code = pre + bytes([0xA5, 0x15, 0x4A, 0x90, 0x04,    # LDA FrameCounter / LSR / BCC ret
                        0x20, w & 0xFF, w >> 8, 0x38])   # JSR write / SEC
    code += bytes([0x60])                                # ret: RTS
    t = cpu + len(code) - len(pre)
    code += bytes([0x20, 0x8B, 0x04, XP_ICON_TILE, 0x24])   # PPU $208B: the icons' column, 4 tiles: the icon, a space
    w2 = bytes([0xA2, 0x04, 0xBD, t & 0xFF, t >> 8, 0x9D, 0x02, 0x03, 0xCA, 0x10, 0xF7,   # (the 5 header bytes)
                0xA9, 0xFF, 0x8D, 0x09, 0x03,                                 # end
                0xAD, XP & 0xFF, XP >> 8, 0xA2, 0x00,                         # LDA XP / LDX #0
                0xC9, 0x0A, 0x90, 0x05, 0xE9, 0x0A, 0xE8, 0xD0, 0xF7,         # tens
                0x8D, 0x08, 0x03, 0x8E, 0x07, 0x03, 0x60])                    # ones, tens
    assert cpu + len(code) - len(pre) == w
    return code + w2


def make_ips(src: bytes, dst: bytes) -> bytes:
    out = bytearray(b"PATCH"); i = 0
    while i < len(dst):
        if i < len(src) and src[i] == dst[i]:
            i += 1; continue
        j = i
        while j < len(dst) and j - i < 0xFFFF and (j >= len(src) or src[j] != dst[j]):
            j += 1
        out += i.to_bytes(3, "big") + (j - i).to_bytes(2, "big") + dst[i:j]; i = j
    return bytes(out + b"EOF")


def main():
    src = open(sys.argv[1], "rb").read()
    import lolpaths
    import lol_seedcode as _sc                            # (a ROM with Link's own colors: identified as PRG1's)
    src = _sc.blank_unused(src)                           # (custom tiles: PRG1's blank ones blank again)
    lolpaths.SOURCE_ROM = _sc.vanilla_colors(bytes(src))
    rom = bytearray(src)
    # (owner 2026-11-25) the page's tunic colors (no ring, blue ring, red ring; LOL_TUNIC "29,32,16" in hex): both
    # copies; unset, the ROM's own (a palette hack's are kept)
    import os
    if os.environ.get("LOL_TUNIC"):
        import lol_seedcode
        tun = bytes(int(v, 16) & 0x3F for v in os.environ["LOL_TUNIC"].split(","))
        assert len(tun) == 3
        for o in lol_seedcode.TUNIC_COPIES:
            rom[o:o + 3] = tun
    # (owner 2026-11-25) the page's "Reduce flashing" (LOL_NOFLASH=1): ZORA's four flashes off (cosmetic: the seed and
    # its code don't change; lol_seedcode masks these bytes)
    if os.environ.get("LOL_NOFLASH") == "1":
        import lol_seedcode
        for (o, n), (old, new) in zip(lol_seedcode.FLASH_BYTES, lol_seedcode.FLASH_PATCH):
            assert rom[o:o + n] == old, (hex(o), rom[o:o + n].hex())
            rom[o:o + n] = new
    assert rom[HOOK:HOOK + 10] == HOOK_BYTES, rom[HOOK:HOOK + 10].hex()
    at = BANK4 + (FREE - 0x8000)
    code = build_helper(FREE)
    import lol_names
    lol_names.XP_LABELS.update(build_helper.labels, TMP=TMP)
    assert all(x == 0xFF for x in rom[at:at + len(code)]), "bank 4's free run is not free"
    rom[at:at + len(code)] = code
    rom[HOOK:HOOK + 10] = bytes([0x20, FREE & 0xFF, FREE >> 8]) + b"\xEA" * 7
    x = bytearray()                                      # ext (Y = the type)
    tbl = build_helper.labels["table"]
    # (HVE: the containers enemies level up by) the levelled-up enemies' values, else the table's
    ups = [(0x0B, 0x80, XP_BROWN), (0x3D, 0x90, XP_BLUE_AQUA), (0x16, 0x90, XP_BLUE_POLS),
           (0x04, 0x70, XP_BLUE_MOBLIN), (0x07, 0x90, XP_BOMB_OCTOROK), (0x08, 0x90, XP_BOMB_OCTOROK),
           (0x05, 0xB0, XP_CHARGER), (0x24, 0xD0, XP_BOMBER)]
    tail = 3 + 11 * len(ups)
    x += bytes([0xAD, HVE & 0xFF, HVE >> 8])
    for k, (t, at, v) in enumerate(ups):                 # CPY #t / BNE next / CMP #at / BCC table / LDA #v / RTS
        here = 3 + 11 * k
        x += bytes([0xC0, t, 0xD0, 0x07, 0xC9, at, 0x90, tail - (here + 8), 0xA9, v, 0x60])
    x += bytes([0xB9, tbl & 0xFF, tbl >> 8, 0x60])
    xo = BANK4 + XP_EXT - 0x8000
    assert all(v == 0xFF for v in rom[xo:xo + len(x)]) and XP_EXT + len(x) <= 0xBC80
    rom[xo:xo + len(x)] = x
    hard = build_helper.labels["hard"]
    for cpu in HARD_CHECKS:
        o = BANK4 + cpu - 0x8000
        assert rom[o:o + 5] == bytes([0xA4, 0x16, 0xB9, 0x2D, 0x06]), hex(cpu)
        rom[o:o + 5] = bytes([0x20, hard & 0xFF, hard >> 8, 0xEA, 0xEA])
    assert rom[HUD_HOOK:HUD_HOOK + 3] == HUD_HOOK_BYTES
    hud_cpu = HUD_CPU
    hud = build_hud(hud_cpu)
    h_at = BANK5 + hud_cpu - 0x8000
    assert all(x == 0xFF for x in rom[h_at:h_at + len(hud)])
    rom[h_at:h_at + len(hud)] = hud
    rom[HUD_HOOK:HUD_HOOK + 3] = bytes([0x20, hud_cpu & 0xFF, hud_cpu >> 8])
    # (blank in PRG1; a ROM with custom background tiles may have drawn there: LoL's icon wins)
    rom[XP_ICON_CHR:XP_ICON_CHR + 16] = icon_bytes(XP_ICON)
    # The bosses' heart containers become blue potions (every dungeon, both quests' room tables)
    potions = 0
    for base in (0x18710, 0x18A10, 0x18D10, 0x19010):
        for room in range(128):
            at = base + 0x200 + room
            if rom[at] & 0x1F == 0x1A:
                rom[at] = (rom[at] & 0xE0) | 0x1F; potions += 1
    assert potions >= 8, potions
    notes = []
    import lol_v3core
    lol_v3core.apply_early(rom, notes)
    import lol_dungeons
    lol_dungeons.apply(rom, notes)
    import lol_levels
    lol_levels.apply(rom, notes)
    import lol_af
    lol_af.apply(rom, notes)
    import lol_choice
    lol_choice.apply(rom, notes)
    lol_choice.apply_rewards(rom, notes)
    import lol_odds
    lol_odds.apply(rom, notes)
    import lol_v10
    lol_v10.apply_secrets(rom, notes)              # (1.0: the secret caves' amounts)
    import lol_bombup
    lol_bombup.apply(rom, notes)
    import lol_books
    lol_books.apply(rom, notes)
    lol_books.dungeon_items_to_bombs(rom, notes)
    lol_af.apply_pre_load(rom, notes)
    import lol_swords
    lol_swords.apply(rom, notes)
    import lol_save
    lol_save.apply(rom, notes)
    import lol_upgrades
    lol_upgrades.apply(rom, notes)
    import lol_moves
    lol_moves.apply(rom, notes)
    import lol_subscreen
    lol_subscreen.apply(rom, notes)
    import lol_titlelist           # (replaces lol_legend: the title's story and item scroll)
    lol_titlelist.apply(rom, notes)
    import lol_dodongo
    lol_dodongo.apply(rom, notes)
    import lol_entrances
    lol_entrances.apply(rom, notes)
    import lol_select
    lol_select.apply(rom, notes)
    import lol_pictures
    lol_pictures.apply(rom, notes)
    lol_upgrades.apply_caves(rom, notes)
    import lol_upmix
    lol_upmix.apply(rom, notes)                   # (the page's Upgrade mix: off unless LOL_UPMIX=1)
    import lol_newups
    lol_newups.apply(rom, notes)
    import lol_rodsong
    lol_rodsong.apply(rom, notes)
    import lol_ending
    lol_ending.apply(rom, notes)
    import lol_enemies2
    lol_enemies2.apply(rom, notes)
    import lol_wizzrobe
    lol_wizzrobe.apply(rom, notes)
    import lol_gleeok
    lol_gleeok.apply(rom, notes)
    import lol_digdogger
    lol_digdogger.apply(rom, notes)
    import lol_gohma
    lol_gohma.apply(rom, notes)
    import lol_patra
    lol_patra.apply(rom, notes)
    import lol_ganon
    lol_ganon.apply(rom, notes)
    lol_ganon.debug_apply(rom, notes)
    import lol_potion
    lol_potion.apply(rom, notes)
    import lol_zombie
    lol_zombie.apply(rom, notes)
    import lol_xray
    lol_xray.apply(rom, notes)
    import lol_heavy
    lol_heavy.apply(rom, notes)
    import lol_secret
    lol_secret.apply(rom, notes)
    import lol_names
    lol_names.apply(rom, notes)
    import lol_shrineui
    lol_shrineui.apply(rom, notes)
    import lol_v3core
    lol_v3core.apply(rom, notes)
    import lol_modes
    lol_modes.apply_rom(rom, notes)
    lol_modes.apply_ground(rom, notes)
    lol_modes.apply_continue(rom, notes)
    lol_modes.apply_hud(rom, notes)
    import lol_snubber
    lol_snubber.apply(rom, notes)
    import lol_stats
    lol_stats.apply(rom, notes)                   # (the end screen: before the fixed bank's copy)
    if lol_entrances.GEN:
        import lol_genload
        lol_genload.apply(rom, notes)
        lol_odds.late(rom)                        # (1.0: the odds engine, bank 9)
        lol_upmix.late(rom)                       # (the Upgrade mix's code: in a data bank)
        lol_pictures.late(rom)                    # (its picture queue's NMI hook: bank 6)
        lol_xray.late(rom)                        # (the X-ray glasses' code: in a data bank)
        lol_genload.finish(rom)                   # (last: the fixed bank's copy)
    import lol_mixgroups
    lol_mixgroups.apply(rom, notes)               # the page's Mix enemy groups (after everything: LoL's bytes win)
    import lol_seedcode
    lol_seedcode.apply(rom, notes)                # the title's version and seed, the file select's code
    import lol_enemies2
    lol_digdogger.late(rom, notes)                # (unseeded: bank 3 full: a data bank)
    lol_enemies2.late(rom, notes)                 # (the Goriya Charger's code: wherever room is left)
    lol_seedcode.apply_code(rom, notes)           # (last: a hash of the finished ROM)
    import lol_encode
    lol_encode.apply(rom, notes)                  # (after the code: Race Rom, LOL_RACE=1: the level data encoded)
    print("\n".join(notes))
    open(sys.argv[2], "wb").write(make_ips(src, bytes(rom)))
    if len(sys.argv) > 3:
        open(sys.argv[3], "wb").write(rom)
    print(f"helper at bank 4 ${FREE:04X} ({len(code)} bytes); XP at ${XP:04X}, {XP_PER_HEART} per heart")


if __name__ == "__main__":
    main()

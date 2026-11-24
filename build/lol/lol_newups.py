"""Legend of Link (test14): the second batch of upgrades' effects (the table, pictures and caves: lol_uptable,
lol_icons2, lol_upgrades' engine).

  ganon visible     bank 4 Ganon_MoveAndShoot ($AD1E, JSR the blue wizzrobe move): then Ganon is drawn (pose 0)
  slow fireballs    bank 4 UpdateFireball's state 0 ($83C5, LDA #$10 / STA ObjState,X): both q-speeds halved, not
                    in a blue Aquamentus' room (its shots are bombs)
  key hoarder       TakeItem's item check (lol_pictures' POUCH_W, bank 7): a key ($19) adds one more
  unlimited candle  WieldCandle (bank 1 $A9CA in WRAM, LDA InvCandle / CMP #1): read as the red candle
  miser's bow       WieldArrow (bank 5 $8E8A): no rupee needed or taken; the arrow's damage - $10 (bank 1 $B5F2)
  bow of greed      WieldArrow: 5 rupees needed and taken; the arrow's damage doubled
  refilling bag     the frame hook (lol_upgrades' regen stub): a bomb every 5400 frames (90 s) while the bag isn't
                    full; the count restarts when a bomb is used
  map master        lol_upgrades' engine, when bought: every map (levels, level 9, the shrines)
  spider bomber     InitGohma's mask ($A166) lets bombs in; Gohma_HandleWeaponCollision's eye check ($A44E):
                    a bomb deals its damage, eye open or not
  holy fire         CheckMonsterBombOrFireCollision (bank 1 $B552): fire deals $20 to stalfos, gibdos, ghinis and
                    pols voice; pols voice's mask ($9C31, bank 4) lets fire in
  poison bait       the bait's update (bank 7 $F4A0, bank 4 in): blue, lures gibdos, drains moblins / goriyas /
                    octoroks touching it and heals gibdos (lol_build's status-bar code turns its item palette blue)
  blue pols voice   (not an upgrade) once enemies see 10 containers: pols voice's mask ($9C31) lets only bombs in
                    (and fire with holy fire), its draw ($9C2E) uses palette 1, the arrow kill (bank 1 $B604) is
                    skipped, the recorder's tune stuns it ($9BA6); 5 health (lol_enemies2), 10 XP (lol_build)
  xp boost          the XP helper's value (bank 4 $B4A8, JSR XP_EXT): non-boss values doubled, bosses + 5
  ghost hunter      SetUpDroppedItem's help-drop check (bank 4 $B0C3): a ghini ($21 / $22) drops 5 rupees
  healerang         HandleMonsterDied (bank 1 $B4E6, INC WorldKillCount): a boomerang kill ($0F) heals 1/4 heart
  shield breaker    HandleMonsterWeaponCollision's darknut check (bank 1 $B4B7): never a parry
  membership card   lol_choice's shop fill: prices halved (rounded up)"""
from lol_af import Asm, BANK, patch, place
import lol_uptable as T
BLUE_POLS_AT = 0x90                     # blue pols voice: HVE >= $90 (10 containers; hard mode 7)
BLUE_POLS = 0x016E                      # RAM: 1 while pols voices are blue (their update sets it)
BAIT_T = 0x6090                         # RAM (save RAM spare; the stack reaches $017x): the poison bait's count
BAIT_EVERY = 8                          # (a drain each 8 frames: $10, a hit point, every ~2 s)
REC_LATCH = 0x6091                      # RAM (save RAM spare): the frame the recorder's tune ended (blue pols voice's stun)
PCHK = 0xADFA                           # bank 1 (run from WRAM $758A): 10 free bytes
WRAM1 = 0x3870                          # bank 1's code runs from WRAM at its address - $3870
HVE = 0x016F                            # lol_build: the containers enemies level up by (HeartValues; hard mode + 3)

GHINI, FLY_GHINI, STALFOS, GIBDO, POLS = 0x21, 0x22, 0x2A, 0x30, 0x16
UNDEAD = (STALFOS, GIBDO, GHINI, FLY_GHINI, POLS)
REFILL_FRAMES = 5400
RT_LO, RT_HI, RLAST = 0x608A, 0x608B, 0x608C     # the refilling bag's count and last bomb count (save RAM spare)


def bit(name):
    return T.bit(name)


def gate(a, name, skip):
    """LDA byte / AND #bit / BEQ skip"""
    addr, b = bit(name)
    a.abs(0xAD, addr).b(0x29, b).br(0xF0, skip)


def free_in(rom, bank, size, lo=0x8000, hi=0xBF00):
    base = BANK(bank) - 0x8000
    for c in range(lo, hi):
        if all(x == 0xFF for x in rom[base + c - 2:base + c + size + 2]):
            return c
    raise AssertionError(f"no {size} bytes free in bank {bank}")


def put(rom, bank, build):
    n = len(build(0x8000).bytes())
    at = free_in(rom, bank, n, 0xB000 if bank == 4 else 0x8000)
    a = build(at)
    place(rom, bank, at, a.bytes())
    return a


def apply(rom: bytearray, notes: list) -> None:
    import lol_v3core as V
    # --- bank 7 stubs (called from WRAM code, any bank in) ---
    def candle(o):
        a = Asm(o)
        gate(a, "unlimited candle", "n")
        return a.b(0xA9, 0x02, 0x60).label("n").abs(0xAD, 0x065B).b(0x60)
    c = V.put7(rom, candle).cpu
    patch(rom, 1, 0xA9CA, bytes([0xAD, 0x5B, 0x06]), bytes([0x20, c & 0xFF, c >> 8]))

    def shield(o):
        a = Asm(o)
        gate(a, "shield breaker", "n")
        return a.b(0xA9, 0x00, 0x60).label("n").abs(0xB9, 0x0098).b(0x60)
    c = V.put7(rom, shield).cpu
    o = BANK(1) + 0xB4B7 - 0x8000
    assert rom[o - 7:o] == bytes([0xC9, 0x0B, 0xF0, 0x04, 0xC9, 0x0C, 0xD0]) or rom[o - 8:o - 6] == bytes([0xC9, 0x0B]), \
        rom[o - 8:o + 3].hex()
    patch(rom, 1, 0xB4B7, bytes([0xB9, 0x98, 0x00]), bytes([0x20, c & 0xFF, c >> 8]))

    def heal0(o):                       # bank 0: a quarter heart (to the containers' limit)
        a = Asm(o)
        a.abs(0xAD, 0x0670).b(0x18, 0x69, 0x40).br(0x90, "set")
        a.b(0x48).abs(0xAD, 0x066F).b(0x29, 0x0F, 0x85, 0x00).abs(0xAD, 0x066F).b(0x4A, 0x4A, 0x4A, 0x4A, 0xC5, 0x00)
        a.br(0xF0, "full").abs(0xEE, 0x066F).b(0x68).br(0xD0, "set")
        a.label("full").b(0x68, 0xA9, 0xFF)
        return a.label("set").abs(0x8D, 0x0670).b(0x60)
    h0 = V.put0(rom, heal0).cpu

    def heal(o):
        a = Asm(o)
        a.abs(0xEE, 0x0627).b(0xC0, 0x0F).br(0xD0, "r")                         # INC WorldKillCount; the boomerang?
        gate(a, "healerang", "r")
        return a.b(*V.far(0, h0)).label("r").b(0x60)
    c = V.put7(rom, heal).cpu
    patch(rom, 1, 0xB4E6, bytes([0xEE, 0x27, 0x06]), bytes([0x20, c & 0xFF, c >> 8]))

    def holy0(o):                       # bank 0 (X the monster): fire deals $20 to the undead
        a = Asm(o)
        a.abs(0xBD, 0x034F)
        for t in UNDEAD:
            a.b(0xC9, t).br(0xF0, "d")
        a.b(0xA9, 0x10, 0x85, 0x07, 0x60)
        return a.label("d").b(0xA9, 0x20, 0x85, 0x07, 0x60)
    hz = V.put0(rom, holy0).cpu

    def holy(o):                        # (Y, the weapon's slot, kept)
        a = Asm(o)
        gate(a, "holy fire", "n")
        a.b(*V.far(0, hz)).b(0x60)
        return a.label("n").b(0xA9, 0x10, 0x85, 0x07, 0x60)
    c = V.put7(rom, holy).cpu
    patch(rom, 1, 0xB552, bytes([0xA9, 0x10, 0x85, 0x07]), bytes([0x20, c & 0xFF, c >> 8, 0xEA]))

    def arrow0(o):                      # bank 0: A the arrow's damage
        a = Asm(o)
        a.b(0x48)
        gate(a, "misers bow", "g")
        a.b(0x68, 0x38, 0xE9, 0x10).br(0xB0, "t").b(0xA9, 0x00).br(0xF0, "t")
        a.label("g").b(0x68, 0x0A).br(0x90, "t").b(0xA9, 0xFF)                  # (bow of greed)
        return a.label("t").b(0xA0, 0x0B, 0x84, 0x0D, 0x60)
    az = V.put0(rom, arrow0).cpu

    def arrow(o):
        a = Asm(o)
        m, g = bit("misers bow"), bit("bow of greed")
        a.b(0x48).abs(0xAD, m[0]).b(0x29, m[1]).br(0xD0, "f").abs(0xAD, g[0]).b(0x29, g[1]).br(0xD0, "f")
        a.b(0x68, 0xA0, 0x0B, 0x84, 0x0D, 0x60)
        return a.label("f").b(0x68).b(*V.far(0, az)).b(0x60)
    c = V.put7(rom, arrow).cpu
    patch(rom, 1, 0xB5F2, bytes([0xA0, 0x0B, 0x84, 0x0D]), bytes([0x20, c & 0xFF, c >> 8, 0xEA]))

    # --- poison bait. The bait's update (bank 7 $F4A0, run from the object loop with no bank switched) ends with
    # JSR $FA93 / LDA #$02 / LDY #$06 / JMP $790C ($F4D8); that becomes a far call to bank 4 and the JMP. There,
    # with the upgrade: a gibdo room's monsters target the bait too (vanilla lures moblin / goriya / octorok / vire
    # / keese rooms: $035F, the room's type, at $F4B9); the bait is drawn blue; and every 8 frames each moblin,
    # goriya or octorok ($03-$0A) touching it (12 px) loses 1/16 of a hit point - one point per ~2 s, no knockback
    # or flash; the last one goes through HandleMonsterWeaponCollision's damage (WRAM $7C54) so it dies as usual -
    # and each gibdo gains it, up to its spawn health ($70; $90 once enemies see 8 containers, lol_upgrades)
    PB, PBIT = bit("poison bait")
    assert PBIT == 0x80                   # (read with BIT: N)
    def poison(o):
        a = Asm(o)
        a.label("pz").abs(0x2C, PB).br(0x30, "pz_o").abs(0x4C, "pz_d")
        a.label("pz_o").abs(0xAD, 0x035F).b(0xC9, 0x30).br(0xD0, "pz_t").b(0xA5, 0x70 + 0x0F, 0x85, 0x61, 0xA5, 0x84 + 0x0F, 0x85, 0x62)
        a.label("pz_t").abs(0xCE, BAIT_T).br(0x30, "pz_g").abs(0x4C, "pz_d")   # (its own count: not every frame)
        a.label("pz_g")
        a.b(0xA9, BAIT_EVERY - 1).abs(0x8D, BAIT_T).b(0xA2, 0x0B)
        a.label("lp").abs(0xBD, 0x0405).br(0xD0, "nx")                     # (dying, or not here yet: left alone)
        a.abs(0xBD, 0x034F).b(0xC9, 0x03).br(0x90, "nx").b(0xC9, 0x0B).br(0x90, "tch")
        a.b(0xC9, 0x30).br(0xD0, "nx")
        a.label("tch").b(0xB5, 0x70, 0x38, 0xE5, 0x70 + 0x0F).abs(0x20, 0x701F).b(0xC9, 0x0C).br(0xB0, "nx")
        a.b(0xB5, 0x84, 0x38, 0xE5, 0x84 + 0x0F).abs(0x20, 0x701F).b(0xC9, 0x0C).br(0xB0, "nx")
        a.abs(0xBD, 0x034F).b(0xC9, 0x30).br(0xF0, "heal")
        a.abs(0xBD, 0x0485).b(0xC9, 0x02).br(0x90, "kill").abs(0xDE, 0x0485).abs(0x4C, "nx")
        a.label("kill").b(0x8A, 0x48, 0xA9, 0x00).abs(0x9D, 0x0485).b(0xA9, 0x01, 0x85, 0x07, 0x85, 0x09)
        a.abs(0x20, 0x7C54)                                       # (as the arrow's pols voice kill: health 0 first)
        a.b(0x68, 0xAA).abs(0x4C, "nx")
        a.label("heal").b(0xA9, 0x70).abs(0xAC, HVE).b(0xC0, 0x70).br(0x90, "hm").b(0xA9, 0x90)
        a.label("hm").abs(0xDD, 0x0485).br(0x90, "nx").br(0xF0, "nx").abs(0xFE, 0x0485)
        a.label("nx").b(0xCA).br(0xD0, "lp").b(0xA2, 0x0F)
        # the vanilla tail: the frame, then palette 2 (1, blue, with the upgrade) and Y 6 for the draw
        a.label("pz_d").abs(0x20, 0xFA93).b(0xA9, 0x02).abs(0x2C, PB).br(0x10, "pl_s").b(0xA9, 0x01)
        a.label("pl_s").b(0xA0, 0x06, 0x60)
        return a
    pa = put(rom, 4, poison)
    patch(rom, 7, 0xF4D8, bytes.fromhex("2093faa902a0064c0c79"),
          V.far(4, pa.labels["pz"]) + bytes([0x4C, 0x0C, 0x79]))

    # --- bank 5: the arrow's price ---
    def cost(o):
        a = Asm(o)
        a.label("chk")
        gate(a, "misers bow", "c_g")
        a.b(0xA9, 0x01, 0x60)                                                   # free: always shoot
        a.label("c_g")
        gate(a, "bow of greed", "c_n")
        a.abs(0xAD, 0x066D).b(0xC9, 0x05).br(0x90, "c_0").b(0x60)              # 5 or more: shoot
        a.label("c_0").b(0xA9, 0x00, 0x60)
        a.label("c_n").abs(0xAD, 0x066D).b(0x60)
        a.label("pay")
        gate(a, "misers bow", "p_g")
        a.b(0x60)
        a.label("p_g")
        gate(a, "bow of greed", "p_n")
        a.abs(0xAD, 0x067E).b(0x18, 0x69, 0x05).abs(0x8D, 0x067E).b(0x60)
        return a.label("p_n").abs(0xEE, 0x067E).b(0x60)
    cs = put(rom, 5, cost).labels
    o = BANK(5) + 0x8E8A - 0x8000
    assert rom[o:o + 3] == bytes([0xAD, 0x6D, 0x06]) and rom[o + 10:o + 13] == bytes([0xEE, 0x7E, 0x06])
    rom[o:o + 3] = bytes([0x20, cs["chk"] & 0xFF, cs["chk"] >> 8])
    rom[o + 10:o + 13] = bytes([0x20, cs["pay"] & 0xFF, cs["pay"] >> 8])

    # --- bank 4 ---
    def b4(o):
        a = Asm(o)
        # slow fireballs (X the fireball): not where a blue Aquamentus is (lol_enemies2's check: its shots are bombs)
        a.label("fire")
        gate(a, "slow fireballs", "f_n")
        a.abs(0xAD, HVE).b(0xC9, BLUE_AQ_AT).br(0x90, "f_s").b(0xA0, 0x0B)
        a.label("f_lp").abs(0xB9, 0x034F).b(0xC9, 0x3D).br(0xF0, "f_n").b(0x88).br(0xD0, "f_lp")
        a.label("f_s").abs(0x5E, 0x041F).abs(0x5E, 0x0444)
        a.label("f_n").b(0xA9, 0x10, 0x95, 0xAC, 0x60)
        # Ganon visible: after his move, drawn in pose 0 (his pose counter kept)
        a.label("ganon").abs(0x20, GANON_MOVE)
        gate(a, "ganon visible", "g_r")
        a.abs(0xBD, 0x046B).b(0x48, 0xA9, 0x00).abs(0x9D, 0x046B).abs(0x20, GANON_DRAW)
        a.b(0x68).abs(0x9D, 0x046B)
        a.label("g_r").b(0x60)
        # spider bomber: Gohma's mask without the bomb bit; a bomb deals its damage, eye open or not
        a.label("gmask").b(0xA9, 0xFB, 0x48)
        gate(a, "spider bomber", "m_n")
        a.b(0x68, 0x29, 0xF7, 0x48)
        a.label("m_n").b(0x68).abs(0x9D, 0x04B2).b(0x60)
        a.label("geye").b(0xA5, 0x09, 0xC9, 0x08).br(0xD0, "e_n")
        a.b(0xA9, 0x02).abs(0x8D, 0x0601).abs(0x20, 0x7C54).abs(0x20, 0x800D)    # boss hit, damage, cry
        a.b(0x68, 0x68, 0x68, 0x68, 0x60)        # (out of the collision and its caller's shove: back to its caller)
        a.label("e_n").b(0xA5, 0x0F, 0xC9, 0x03, 0x60)
        # holy fire: pols voice's every-frame mask without the fire bit. Blue pols voice (once enemies see 10
        # containers, HVE): only bombs hurt it (mask $F7), drawn with sprite palette 1
        a.label("pols").b(0xA9, 0x00).abs(0x8D, BLUE_POLS).abs(0xAD, HVE).b(0xC9, BLUE_POLS_AT).br(0x90, "pv_0")
        a.abs(0xEE, BLUE_POLS)                                                 # (BLUE_POLS: the arrow check's)
        a.abs(0xBD, 0x04BF).b(0x09, 0x08).abs(0x9D, 0x04BF)                    # (its draw takes $04 / $05's palette)
        a.b(0xA9, 0xF7).br(0xD0, "pv_h")                                       # (and holy fire, below)
        a.label("pv_0").b(0xA9, 0xFE)
        a.label("pv_h").b(0x48)
        gate(a, "holy fire", "pv_n")
        a.b(0x68, 0x29, 0xDF, 0x48)
        a.label("pv_n").b(0x68)
        a.label("pv_s").abs(0x9D, 0x04B2).b(0x60)
        # blue pols voice and the recorder: the first frame after the tune ($051B set, $3C back to 0; the monsters
        # are frozen while it plays) stuns it as a boomerang does (ObjStunTimer $3D,X = $10). REC_LATCH holds that
        # frame's counter, so every pols voice in the room is stunned that frame only; a new tune clears it. The
        # update's own LDA $066C / ORA $3D,X follow.
        a.label("prec").abs(0xAD, 0x051B).br(0xF0, "pr_c").b(0xA5, 0x3C).br(0xD0, "pr_c")
        a.abs(0xAD, REC_LATCH).br(0xF0, "pr_1").b(0xC5, 0x15).br(0xD0, "pr_o").br(0xF0, "pr_s")
        a.label("pr_1").b(0xA5, 0x15).abs(0x8D, REC_LATCH)
        a.label("pr_s").abs(0xAD, BLUE_POLS).br(0xF0, "pr_o").b(0xA9, 0x10, 0x95, 0x3D).br(0xD0, "pr_o")
        a.label("pr_c").b(0xA9, 0x00).abs(0x8D, REC_LATCH)
        a.label("pr_o").abs(0xAD, 0x066C).b(0x15, 0x3D, 0x60)
        a.label("pdraw").b(0x48).abs(0xAD, HVE).b(0xC9, BLUE_POLS_AT).br(0x90, "pd_n").b(0xA9, 0x01, 0x85, 0x04, 0x85, 0x05)
        a.label("pd_n").b(0x68).abs(0x4C, 0x77DB)
        # xp boost: the value (A, from XP_EXT; bit 7 a boss)
        a.label("xp").abs(0x20, XP_EXT).br(0xF0, "x_r").b(0x48)
        gate(a, "xp boost", "x_n")
        a.b(0x68).br(0x30, "x_b").b(0x0A).br(0x10, "x_ok").b(0xA9, 0x7F)
        a.label("x_ok").b(0x09, 0x00, 0x60)
        a.label("x_b").b(0x18, 0x69, 0x05, 0x60)
        a.label("x_n").b(0x68)
        a.label("x_r").b(0x60)
        # ghost hunter: a ghini's drop is the help drop (5 rupees)
        a.label("ghost")
        gate(a, "ghost hunter", "gh_n")
        a.abs(0xBD, 0x0412).b(0xC9, GHINI).br(0xF0, "gh_y").b(0xC9, FLY_GHINI).br(0xD0, "gh_n")
        a.label("gh_y").b(0xA9, 0x0A, 0x85, 0x50, 0xA9, 0x00, 0x85, 0x51)
        a.label("gh_n").b(0xA5, 0x50, 0xC9, 0x0A, 0x60)
        return a
    from lol_enemies2 import BLUE_AQ_AT
    from lol_build import XP_EXT
    GANON_MOVE = rd16(rom, 4, 0xAD1F)
    o = BANK(4) + 0xACDC - 0x8000
    assert rom[o:o + 6] == bytes([0xA9, 0x00, 0x9D, 0x6B, 0x04, 0x4C])
    GANON_DRAW = rom[o + 6] | rom[o + 7] << 8
    globals().update(GANON_MOVE=GANON_MOVE, GANON_DRAW=GANON_DRAW, BLUE_AQ_AT=BLUE_AQ_AT, XP_EXT=XP_EXT)
    L4 = put(rom, 4, b4).labels
    j = lambda n: bytes([0x20, L4[n] & 0xFF, L4[n] >> 8])
    patch(rom, 4, 0x83C5, bytes([0xA9, 0x10, 0x95, 0xAC]), j("fire") + b"\xEA")
    patch(rom, 4, 0xAD1E, bytes([0x20, GANON_MOVE & 0xFF, GANON_MOVE >> 8]), j("ganon"))
    patch(rom, 4, 0xA166, bytes([0xA9, 0xFB, 0x9D, 0xB2, 0x04]), j("gmask") + b"\xEA\xEA")
    patch(rom, 4, 0xA44E, bytes([0xA5, 0x0F, 0xC9, 0x03]), j("geye") + b"\xEA")
    patch(rom, 4, 0x9C31, bytes([0xA9, 0xFE, 0x9D, 0xB2, 0x04]), j("pols") + b"\xEA\xEA")
    patch(rom, 4, 0x9C2E, bytes([0x20, 0xDB, 0x77]), j("pdraw"))          # pols voice's draw: blue at 10
    patch(rom, 4, 0x9BA6, bytes.fromhex("ad6c06153d"), j("prec") + b"\xEA\xEA")   # pols voice's update: the recorder

    # blue pols voice: arrows don't kill it. HandleMonsterArrowCollision's pols check (bank 1 $B604, run from WRAM
    # $7D94: CMP #$16 / BNE normal / LDA #0 / STA ObjHP,X / JMP $7C54) calls PCHK (bank 1's free $ADFA, WRAM $758A):
    # Z set (A = 0) only for a pols voice that isn't blue (BLUE_POLS, set by its update above): the kill; else the
    # normal hit, which a blue one's mask turns away.
    pchk = Asm(PCHK - WRAM1)
    pchk.b(0xC9, 0x16).br(0xD0, "r").abs(0xAD, BLUE_POLS)
    pchk.label("r").b(0x60)
    place(rom, 1, PCHK, pchk.bytes())
    w = PCHK - WRAM1
    patch(rom, 1, 0xB604, bytes.fromhex("c916d008a9009d85044c547c"),
          bytes([0x20, w & 0xFF, w >> 8, 0xD0, 0x07, 0x9D, 0x85, 0x04, 0x4C, 0x54, 0x7C, 0xEA]))
    import lol_build as LB                # the XP helper's JSR XP_EXT ("soft"; it was $B4A8)
    LB.build_helper(LB.FREE)
    patch(rom, 4, LB.build_helper.labels["soft"], bytes([0x20, XP_EXT & 0xFF, XP_EXT >> 8]), j("xp"))
    patch(rom, 4, 0xB0C3, bytes([0xA5, 0x50, 0xC9, 0x0A]), j("ghost") + b"\xEA")
    notes.append("second batch of upgrades: ganon visible, slow fireballs, key hoarder, unlimited candle, miser's bow, "
                 "refilling bag, map master, spider bomber, bow of greed, holy fire, xp boost, ghost hunter, healerang, "
                 "shield breaker, membership card")


def rd16(rom, bank, cpu):
    o = BANK(bank) + cpu - 0x8000
    return rom[o] | rom[o + 1] << 8

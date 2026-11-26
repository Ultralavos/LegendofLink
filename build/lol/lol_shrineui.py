"""Legend of Link: shrine touches (owner, 2026-11-24).

Roars: in Level 9 and the shrines, a room next to (north, south, east or west of) Ganon's room (Level 9) or a
shrine's guardian (the boss beside a shrine's prize room; other bosses there don't) roars as the boss's own room does: its sample when Link comes in, and
again every 192 frames he stays, while that boss lives (its room's kill count, world flags bits 6-7, not full).
Samples as the bosses' own: $10 Aquamentus / Gleeok / Ganon, $20 Dodongo / Gohma, $40 Digdogger / Manhandla / Patra.
roar(rom) gives bank 0's routine, called from lol_upgrades' frame hook (every frame of play).

Shrine letters: the overworld item screen's TRIFORCE gets A B to its left and C D to its right, each shrine's
letter once its reward is taken (lol_bombup's rec: the odds' saved byte 11 + shrine, bit 7). The submenu's row
cue (bank 5 Submenu_CueTransferRowOW's LDA SubmenuTransferBufSelectorsOW,Y) for the triforce frame's bottom row
(selector $5A, bank 6 $A235) writes that row and the letters' row into the dynamic buffer instead (selector 0).
Scratch: $01BD (the room last seen), $01BE (the roar's timer).

(owner 2026-11-25) While a room roars, the status bar's -LIFE- reads -ROAR- (for players who can't hear it): set
at each check (coming in, then every 192 frames), back to -LIFE- when it stops or Link leaves the level."""
from lol_af import Asm, BANK, patch

LASTR, RT = 0x01BD, 0x01BE
ROARF, ROARN = 0x0164, 0x0165           # (stack page, untouched) -ROAR- up; this check's answer
HUD_AT = 0x2078                         # the status bar's LIFE (between its dashes at $2077 / $207C)
WORD_LIFE, WORD_ROAR = bytes([0x15, 0x12, 0x0F, 0x0E]), bytes([0x1B, 0x18, 0x0A, 0x1B])
ATTR_A, ATTR_B, ATTR_C, ATTR_D = 0x687E, 0x68FE, 0x697E, 0x69FE
WORLD_FLAGS = 0x6BAF
LEVEL_NO = 0x6BB1
PRIZE_ROOM = 0x6B7E + 0x30              # the level info's triforce room: a shrine's prize room (its guardian next door)
SAMPLE = 0x0601
EVERY = 192
SAMPLES = {**{t: 0x20 for t in (0x31, 0x32, 0x33, 0x34)}, **{t: 0x40 for t in (0x38, 0x39, 0x3C, 0x47, 0x48)},
           **{t: 0x10 for t in (0x3D, 0x3E, 0x42, 0x43, 0x44, 0x45)}}
GANON = 0x3E
TRI_SEL = 0x5A
_LIB = {}


def roar(rom: bytearray) -> int:
    if "roar" in _LIB:
        return _LIB["roar"]
    import lol_v3core as V
    lo, hi = 0x31, 0x48
    tbl = [SAMPLES.get(t, 0) for t in range(lo, hi + 1)]

    # gchk (bank 6, far-called; Y the neighbour, kept): C set if it is the guardian - beside the prize room, its door
    # into it a shutter. (X: 0 east of it / 1 south: the neighbour's west / north door, bits 7-5; 2 west / 3 north:
    # its east / south door, bits 4-2; ATTR_B the west-east byte, ATTR_A the north-south one)
    def gchk(o):
        q = Asm(o)
        q.label("gchk").b(0x98, 0x38).abs(0xED, PRIZE_ROOM).b(0xA2, 0x03)
        q.label("g_lp").abs(0xDD, "gdif").br(0xF0, "g_f").b(0xCA).br(0x10, "g_lp")
        q.label("g_n").b(0x18, 0x60)
        q.label("g_f").b(0x8A, 0x4A).br(0xB0, "g_a").abs(0xB9, ATTR_B).br(0x90, "g_b")
        q.label("g_a").abs(0xB9, ATTR_A)
        q.label("g_b").b(0x4A, 0x4A, 0xE0, 0x02).br(0xB0, "g_ck").b(0x4A, 0x4A, 0x4A)
        q.label("g_ck").b(0x29, 0x07, 0xC9, 0x07).br(0xD0, "g_n").b(0x38, 0x60)    # (7: a shutter)
        q.label("gdif").b(0x01, 0x10, 0xFF, 0xF0)
        return q
    import lol_names
    n_g = len(gchk(0x8000).bytes())
    g_at = lol_names.put6(rom, n_g)
    o6 = BANK(6) + g_at - 0x8000
    rom[o6:o6 + n_g] = gchk(g_at).bytes()
    GCHK = [g_at]

    def build(org):
        a = Asm(org)
        # (owner 2026-11-25) out of the levels with -ROAR- still up: -LIFE- back (in play)
        a.label("roar").b(0xA5, 0x10).br(0xD0, "r_lv").abs(0xAD, ROARF).br(0xF0, "r_r").b(0xA5, 0x12, 0xC9, 0x05)
        a.br(0xD0, "r_r").b(0xA9, 0x00).abs(0x4C, "hud")
        a.label("r_lv").b(0xA5, 0x12, 0xC9, 0x05).br(0xD0, "r_r")
        a.abs(0xAD, LEVEL_NO).b(0xC9, 0x09).br(0x90, "r_r")                     # Level 9 and the shrines
        a.b(0xA5, 0xEB).abs(0xCD, LASTR).br(0xF0, "r_t")
        a.abs(0x8D, LASTR).abs(0x4C, "r_go")                                    # a new room: now
        a.label("r_t").abs(0xCE, RT).br(0xF0, "r_go")                           # else every EVERY frames
        a.label("r_r").b(0x60)
        a.label("r_go").b(0xA9, EVERY).abs(0x8D, RT).b(0xA9, 0x00).abs(0x8D, ROARN)
        for z in (0, 1, 2, 3):
            a.b(0xA5, z, 0x48)
        a.abs(0xAD, WORLD_FLAGS).b(0x85, 0x00).abs(0xAD, WORLD_FLAGS + 1).b(0x85, 0x01)
        a.b(0xA9, 0x03, 0x85, 0x02)                                              # $02: the direction (E W S N)
        a.label("n_lp").b(0xA6, 0x02, 0xA5, 0xEB, 0x18).abs(0x7D, "dofs").b(0xA8)   # Y = the neighbour
        a.b(0xE0, 0x02).br(0xB0, "n_v")
        a.b(0x45, 0xEB, 0x29, 0xF0).br(0xD0, "nx0")                              # east / west: the same row
        a.abs(0x4C, "n_in")
        a.label("n_v").b(0x98, 0xC9, 0x80).br(0xB0, "nx0")                       # north / south: inside
        a.label("n_in").abs(0xB9, ATTR_D).b(0x29, 0x80).br(0xF0, "n_lo").b(0xA9, 0x40)
        a.label("n_lo").b(0x85, 0x03).abs(0xB9, ATTR_C).b(0x29, 0x3F, 0x05, 0x03)   # A = its monster
        a.abs(0xAE, LEVEL_NO).b(0xE0, 0x09).br(0xD0, "n_sh")
        a.b(0xC9, GANON).br(0xD0, "nx0").b(0xA9, 0x10).br(0xD0, "n_alive")       # Level 9: Ganon
        a.label("nx0").abs(0x4C, "n_nx")                                       # (a long way down)
        # (owner 2026-11-25) a shrine: only its guardian, the boss beside the prize room whose door into it is the
        # prize room is its shutter (lol_gen's "boss" role; another dungeon's room may lie beside it on the shared grid)
        # (X: 0 east of it / 1 south: the neighbour's west / north door, bits 7-5; 2 west / 3 north: its east / south
        #  door, bits 4-2; B the west-east byte, A the north-south one)
        a.label("n_sh").b(0x48).b(*V.far(6, GCHK[0])).br(0xB0, "g_ok")         # (bank 6: gchk)
        a.label("g_no").b(0x68)
        a.label("g_x").abs(0x4C, "n_nx")
        a.label("g_ok").b(0x68, 0x38, 0xE9, lo).br(0x90, "g_x").b(0xC9, hi - lo + 1).br(0xB0, "g_x")
        a.b(0xAA).abs(0xBD, "smp").br(0xF0, "g_x")                               # a shrine: a guardian
        a.label("n_alive").b(0x85, 0x03, 0xB1, 0x00, 0x29, 0xC0, 0xC9, 0xC0).br(0xF0, "g_x")   # dead: no
        a.b(0xA5, 0x03).abs(0x8D, SAMPLE).b(0xA9, 0x01).abs(0x8D, ROARN).abs(0x4C, "n_end")
        a.label("n_nx").b(0xC6, 0x02).br(0x30, "n_end").abs(0x4C, "n_lp")
        a.label("n_end")
        for z in (3, 2, 1, 0):
            a.b(0x68, 0x85, z)
        # the status bar's -LIFE- reads -ROAR- while a roar is on here (for those who can't hear it)
        a.abs(0xAD, ROARN).abs(0xCD, ROARF).br(0xD0, "hud").b(0x60)
        a.label("hud").abs(0x8D, ROARF).b(0x0A, 0x0A, 0xA8).abs(0xAE, 0x0301)
        a.b(0xA9, HUD_AT >> 8).abs(0x9D, 0x0302).b(0xA9, HUD_AT & 0xFF).abs(0x9D, 0x0303).b(0xA9, 0x04).abs(0x9D, 0x0304)
        a.label("h_l").abs(0xB9, "words").abs(0x9D, 0x0305).b(0xE8, 0xC8, 0x98, 0x29, 0x03).br(0xD0, "h_l")
        a.b(0xA9, 0xFF).abs(0x9D, 0x0305).b(0x8A, 0x18, 0x69, 0x03).abs(0x8D, 0x0301).b(0x60)
        a.label("words").b(*WORD_LIFE, *WORD_ROAR)
        a.label("dofs").b(0x01, 0xFF, 0x10, 0xF0)                                 # E W S N
        a.label("smp").b(*tbl)
        return a
    a = V.put0(rom, build)
    _LIB["roar"] = a.labels["roar"]
    return _LIB["roar"]


ROW_SITE = 0xB28E                       # bank 5: LDA SubmenuTransferBufSelectorsOW,Y ($B225) / STA TileBufSelector


def apply(rom: bytearray, notes: list) -> None:
    """The shrine letters beside TRIFORCE (the roar is lol_upgrades' frame hook's)."""
    import lol_entrances
    if not lol_entrances.GEN:
        return
    from lol_newups import put
    from lol_odds import STORE
    enc = lambda c: 0x24 if c == " " else ord(c) - 55
    # selector $5A is the triforce frame's bottom row (bank 6 $A235: 2B6A, 12 tiles): kept, then the letters' row
    b6 = BANK(6) - 0x8000
    bottom = bytes(rom[b6 + 0xA235:b6 + 0xA235 + 15])
    assert bottom[:3] == bytes([0x2B, 0x6A, 0x0C]) and rom[b6 + 0xA235 + 15] == 0xFF, bottom.hex()
    text = list(bottom) + [0x2B, 0xA9, 0x0E] + [enc(c) for c in "AB TRIFORCE CD"] + [0xFF]
    spots = tuple(15 + x for x in (3, 4, 15, 16))           # A B ... C D in the record
    b5 = BANK(5) - 0x8000
    assert rom[b5 + ROW_SITE:b5 + ROW_SITE + 5] == bytes([0xB9, 0x25, 0xB2, 0x85, 0x14])

    # gchk (bank 6, far-called; Y the neighbour, kept): C set if it is the guardian - beside the prize room, its door
    # into it a shutter. (X: 0 east of it / 1 south: the neighbour's west / north door, bits 7-5; 2 west / 3 north:
    # its east / south door, bits 4-2; ATTR_B the west-east byte, ATTR_A the north-south one)
    def gchk(o):
        q = Asm(o)
        q.label("gchk").b(0x98, 0x38).abs(0xED, PRIZE_ROOM).b(0xA2, 0x03)
        q.label("g_lp").abs(0xDD, "gdif").br(0xF0, "g_f").b(0xCA).br(0x10, "g_lp")
        q.label("g_n").b(0x18, 0x60)
        q.label("g_f").b(0x8A, 0x4A).br(0xB0, "g_a").abs(0xB9, ATTR_B).br(0x90, "g_b")
        q.label("g_a").abs(0xB9, ATTR_A)
        q.label("g_b").b(0x4A, 0x4A, 0xE0, 0x02).br(0xB0, "g_ck").b(0x4A, 0x4A, 0x4A)
        q.label("g_ck").b(0x29, 0x07, 0xC9, 0x07).br(0xD0, "g_n").b(0x38, 0x60)    # (7: a shutter)
        q.label("gdif").b(0x01, 0x10, 0xFF, 0xF0)
        return q
    import lol_names
    n_g = len(gchk(0x8000).bytes())
    g_at = lol_names.put6(rom, n_g)
    o6 = BANK(6) + g_at - 0x8000
    rom[o6:o6 + n_g] = gchk(g_at).bytes()
    GCHK = [g_at]

    def build(org):
        a = Asm(org)
        a.label("row").b(0xB9, 0x25, 0xB2, 0xC9, TRI_SEL).br(0xF0, "t_go").b(0x60)
        a.label("t_go").b(0xA2, len(text) - 1)
        a.label("t_cp").abs(0xBD, "rec").abs(0x9D, 0x0302).b(0xCA).br(0x10, "t_cp")
        for k, sp in enumerate(spots):
            a.abs(0xAD, STORE + 11 + k).br(0x30, f"t_k{k}").b(0xA9, 0x24).abs(0x8D, 0x0302 + sp)
            a.label(f"t_k{k}")
        a.b(0xA9, len(text) - 1).abs(0x8D, 0x0301).b(0xA9, 0x00, 0x60)        # (selector 0: the dynamic buffer)
        a.label("rec").b(*text)
        return a
    a = put(rom, 5, build)
    r = a.labels["row"]
    # the status bar's SHRINE-X from the first frame (InitMode3_Sub7's JSR at $B02A): a shrine's label
    # through the dynamic buffer, Z set (the game's LEVEL-X transfer skipped)
    def b_lvq(org):
        q = Asm(org)
        q.label("lvq").abs(0xAD, LEVEL_NO).b(0xC9, 0x0A).br(0x90, "lq_r")
        q.b(0xA2, 9).label("lq_l").abs(0xBD, "txt").abs(0x9D, 0x0302).b(0xCA).br(0x10, "lq_l")
        q.abs(0xAD, LEVEL_NO).abs(0x8D, 0x030C).b(0xA9, 0xFF).abs(0x8D, 0x030D).b(0xA9, 0x0B).abs(0x8D, 0x0301)
        q.b(0xA9, 0x00, 0x60)
        q.label("lq_r").abs(0xAD, LEVEL_NO).b(0x60)                                # (Z: the overworld's 0)
        q.label("txt").b(0x20, 0x41, 0x08, 0x1C, 0x11, 0x1B, 0x12, 0x17, 0x0E, 0x62)
        return q
    lq = put(rom, 5, b_lvq).labels["lvq"]
    o = BANK(5) + 0xB02A - 0x8000                           # (InitMode3_Sub7's JSR, lol_upgrades' lvq before)
    assert rom[o] == 0x20
    rom[o + 1:o + 3] = bytes([lq & 0xFF, lq >> 8])
    patch(rom, 5, ROW_SITE, bytes([0xB9, 0x25, 0xB2]), bytes([0x20, r & 0xFF, r >> 8]))
    notes.append(f"shrine letters beside TRIFORCE (bank 5 ${r:04X}); roars next to Ganon and the guardians")

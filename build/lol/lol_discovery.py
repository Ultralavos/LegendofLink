"""Legend of Link: the Song of Discovery's recorder spots (owner, 2026-11-25; the caves: lol_heavy, the same deal).

Only on seeds whose upgrade pool has the Song of Discovery (75, tier 2, with the recorder). With it:
  - H16: the recorder drains a patch of the sea east of the shore (columns 9-11, rows 2-4: sand) with stairs at its
    east middle (11, 3); nothing is saved, so the water is back whenever the screen loads again (Link comes out of
    the cave on the sand, column 7 row 4).
  - E4 (the fountain in the dead woods): the recorder turns the bush right of the pond (12, 4) into stairs; like
    H16's, nothing is saved, so the bush is back whenever the screen loads again (Link comes out above the pond).
  - the four recorder spots (E3's lake, F9's bush, E4's bush, H16's stairs) show a recorder sprite until they're
    revealed.
How: WieldFlute summons the whirlwind for a room not in its list (bank 7 $EFBF: JSR SummonWhirlwind, bank 1 in);
that JSR goes to a bank 1 stub first: DISC (bank 0) takes H16 / E4 with the upgrade (no whirlwind) and sets PEND;
the frame hook (lol_upgrades' frame, FRAME here) waits for the tune (FluteTimer $3C) and writes one square a frame
(PlayAreaTiles and the tile buffer), then the secret tune. Leaving and coming back (the square no longer
stairs) lets the recorder work again. RAM: $652B-$652D (battery RAM past the save files'
markers, unused): the room it last saw, PEND (1 H16, 2 E4, $80 done), STEP."""
from lol_af import Asm, BANK, place, patch
import lol_uptable as T

H16, E4, E3, F9 = 0x7F, 0x43, 0x42, 0x58
ROOMP, PEND, STEP = 0x652B, 0x652C, 0x652D
SACT, FLAST = 0x652E, 0x652F            # the Song of Sleep: this room's (bit 0 on, 6 babies, 7 pols die); the tune
HVE = 0x016F                            #  was playing last frame
PLAY = 0x6530
FLUTE_T = 0x3C
SECRET_CYCLE = 0x051A
WORLD_FLAGS = 0x6BAF
DISC_BIT = T.bit("song of discovery")
OW = 0x18410
LAYOUTS = 0x15428
E4_LAYOUT = 0x7A
SAND_REF = (7, 4)                       # H16's square whose tiles the drained ones copy
DRAIN = [(c, r) for r in (2, 3, 4) for c in (9, 10, 11) if (c, r) != (11, 3)] + [(11, 3)]
E4_BUSH = (12, 4)                       # (owner: an existing bush, above the right pair's lower one)
MARKS = [(E3, 0x60, 0x90, 0), (F9, 0x60, 0x90, 1), (E4, 0xC0, 0x80, 2), (H16, 0xB0, 0x70, 2)]
RECORDER_TILE, RECORDER_ATTR = 0x24, 0x02
OAM = 0x02FC                            # the last sprite


def _off(c, r):
    return c * 44 + r * 2


def frame_code(rom):
    """lol_upgrades' frame hook calls this (bank 0) every frame of play; None without the upgrade this seed."""
    import lol_heavy
    if not lol_heavy.ACTIVE2:
        return None
    import lol_v3core as V
    # the squares: (room, column, row, source: 0 stairs, 1 H16's sand, 2 E4's bush)
    sq = [(H16, c, r, 0 if (c, r) == (11, 3) else 1) for c, r in DRAIN]
    E4_ST = len(sq)
    sq += [(E4, E4_BUSH[0], E4_BUSH[1], 0)]
    refs = {1: PLAY + _off(*SAND_REF)}
    OFF = (0, 1, 22, 23)

    def build(org):
        a = Asm(org)
        a.label("fr").b(0xA5, 0xEB).abs(0xCD, ROOMP).br(0xF0, "f_s").abs(0x8D, ROOMP).b(0xA9, 0x00)
        a.abs(0x8D, PEND).abs(0x8D, STEP).abs(0x8D, SACT)
        a.label("f_s").b(0xA5, 0x10).br(0xF0, "f_ow").abs(0x4C, "slp")
        a.label("f_ow").b(0xA5, 0x12, 0xC9, 0x05).br(0xF0, "f_m5").b(0x60)
        a.label("f_m5").abs(0xAD, DISC_BIT[0]).b(0x29, DISC_BIT[1]).br(0xD0, "f_up").b(0x60)
        # the screen loaded anew (out of the cave: the water's back, the bush too): the recorder works again
        a.label("f_up").abs(0xAD, PEND).b(0xC9, 0x80).br(0xD0, "f_p")
        a.b(0xA5, 0xEB, 0xC9, H16).br(0xD0, "f_h4").abs(0xAD, PLAY + _off(11, 3)).abs(0x4C, "f_hc")
        a.label("f_h4").b(0xC9, E4).br(0xD0, "f_p").abs(0xAD, PLAY + _off(*E4_BUSH))
        a.label("f_hc").b(0xC9, 0x70).br(0xF0, "f_p")
        a.b(0xA9, 0x00).abs(0x8D, PEND).abs(0x8D, STEP)
        # a reveal under way (PEND 1 / 2), after the tune: one square a frame
        a.label("f_p").abs(0xAD, PEND).b(0xC9, 0x01).br(0xF0, "f_go").b(0xC9, 0x02).br(0xF0, "f_go")
        a.abs(0x4C, "f_mk")
        a.label("f_go").b(0xA5, FLUTE_T).br(0xF0, "f_n").abs(0x4C, "f_mk")
        a.label("f_n").abs(0xAD, PEND).b(0xC9, 0x02).br(0xF0, "f_e4")
        a.abs(0xAE, STEP).abs(0x20, "wsq").abs(0xEE, STEP).abs(0xAD, STEP).b(0xC9, len(DRAIN)).br(0x90, "f_x")
        a.br(0xB0, "f_dn")
        a.label("f_e4").b(0xA2, E4_ST).abs(0x20, "wsq")
        a.label("f_dn").b(0xA9, 0x80).abs(0x8D, PEND).b(0xA9, 0x04).abs(0x8D, 0x0602)
        a.label("f_x").b(0x60)
        # found: Z clear if this room's secret is flagged found
        a.label("found").b(0xA5, 0x00, 0x48, 0xA5, 0x01, 0x48)
        a.abs(0xAD, WORLD_FLAGS).b(0x85, 0x00).abs(0xAD, WORLD_FLAGS + 1).b(0x85, 0x01)
        a.b(0xA4, 0xEB, 0xB1, 0x00, 0x29, 0x80, 0xA8, 0x68, 0x85, 0x01, 0x68, 0x85, 0x00, 0x98, 0x60)
        # wsq: square X written (PlayAreaTiles and the tile buffer); $00-$05 kept
        a.label("wsq").b(0xA0, 0x05)
        a.label("w_sv").abs(0xB9, 0x0000).b(0x48, 0x88).br(0x10, "w_sv")
        a.abs(0xBD, "q_lo").b(0x85, 0x00).abs(0xBD, "q_hi").b(0x85, 0x01)
        a.abs(0xBD, "q_src").br(0xD0, "w_ref")
        for k in range(4):
            a.b(0xA9, 0x70 + k, 0x85, 0x02 + k)
        a.abs(0x4C, "w_wr")
        a.label("w_ref")
        for k in range(4):
            a.abs(0xAD, refs[1] + OFF[k]).b(0x85, 0x02 + k)
        a.label("w_wr")
        for k in range(4):
            a.b(0xA0, OFF[k], 0xA5, 0x02 + k, 0x91, 0x00)
        a.abs(0xAC, 0x0301)
        a.abs(0xBD, "q_ph").abs(0x99, 0x0302).abs(0x99, 0x0307)
        a.abs(0xBD, "q_pl").abs(0x99, 0x0303).b(0x18, 0x69, 0x20).abs(0x99, 0x0308)
        a.b(0xA9, 0x02).abs(0x99, 0x0304).abs(0x99, 0x0309)
        a.b(0xA5, 0x02).abs(0x99, 0x0305).b(0xA5, 0x04).abs(0x99, 0x0306)
        a.b(0xA5, 0x03).abs(0x99, 0x030A).b(0xA5, 0x05).abs(0x99, 0x030B)
        a.b(0xA9, 0xFF).abs(0x99, 0x030C).b(0x98, 0x18, 0x69, 0x0A).abs(0x8D, 0x0301)
        a.b(0xA0, 0x00)
        a.label("w_rl").b(0x68).abs(0x99, 0x0000).b(0xC8, 0xC0, 0x06).br(0xD0, "w_rl").b(0x60)
        # the recorder marks, until the spot is revealed
        a.label("f_mk").b(0xA2, len(MARKS) - 1)
        a.label("m_l").b(0xA5, 0xEB).abs(0xDD, "m_room").br(0xF0, "m_f").b(0xCA).br(0x10, "m_l")
        a.label("m_r").b(0x60)
        a.label("m_f").abs(0xBD, "m_kind").br(0xF0, "m_k0").b(0xC9, 0x01).br(0xF0, "m_k1")
        a.label("m_k2").abs(0xAD, PEND).br(0xD0, "m_r").br(0xF0, "m_draw")                 # H16 / E4: not revealed
        a.label("m_k1").abs(0xAD, SECRET_CYCLE).br(0xD0, "m_r").br(0xF0, "m_draw")         # F9
        a.label("m_k0").abs(0x20, "found").br(0xD0, "m_r")                                 # E3
        a.label("m_draw").abs(0xBD, "m_y").abs(0x8D, OAM).b(0xA9, RECORDER_TILE).abs(0x8D, OAM + 1)
        a.b(0xA9, RECORDER_ATTR).abs(0x8D, OAM + 2).abs(0xBD, "m_x").abs(0x8D, OAM + 3).b(0x60)
        # --- the Song of Sleep (in a level): when the tune ends, this room's sleepers are stunned for as long as
        # Link stays (every frame); blue and brown darknuts slow a step; pols voices die (lol_newups' pols update,
        # SACT bit 7); Digdogger's babies sleep only if they were there when the tune ended (bit 6)
        a.label("slp").abs(0xAD, T.SLEEP[0]).b(0x29, T.SLEEP[1]).br(0xD0, "s_on").b(0x60)
        a.label("s_on").b(0xA5, FLUTE_T).br(0xF0, "s_t0").abs(0x8D, FLAST).b(0x60)
        a.label("s_t0").abs(0xAD, FLAST).br(0xF0, "s_act").b(0xA9, 0x00).abs(0x8D, FLAST)
        a.b(0xA9, 0x81).abs(0x8D, SACT).b(0xA2, 0x0B)                                   # (the tune just ended)
        a.label("s_l0").abs(0xBD, 0x034F).b(0xC9, 0x18).br(0xD0, "s_n0").abs(0xAD, SACT).b(0x09, 0x40)
        a.abs(0x8D, SACT)
        a.label("s_n0").b(0xC9, 0x0C).br(0xF0, "s_slow").b(0xC9, 0x0B).br(0xD0, "s_x0").abs(0xAD, HVE).b(0xC9, 0x80)
        a.br(0x90, "s_x0")
        a.label("s_slow").abs(0xBD, 0x03BC).b(0x38, 0xE9, 0x08).b(0xC9, 0x10).br(0x90, "s_x0").abs(0x9D, 0x03BC)
        a.label("s_x0").b(0xCA).br(0xD0, "s_l0")
        a.label("s_act").abs(0xAD, SACT).br(0xD0, "s_go").b(0x60)
        a.label("s_go").b(0xA2, 0x0B)
        a.label("s_l").abs(0xBD, 0x034F).b(0xC9, 0x03).br(0xF0, "s_st").b(0xC9, 0x06).br(0xF0, "s_st")
        a.b(0xC9, 0x28).br(0xF0, "s_st").b(0xC9, 0x12).br(0xF0, "s_st")
        a.b(0xC9, 0x04).br(0xD0, "s_g").abs(0xAD, HVE).b(0xC9, 0x70).br(0x90, "s_st").br(0xB0, "s_nx")
        a.label("s_g").b(0xC9, 0x05).br(0xD0, "s_d").abs(0xAD, HVE).b(0xC9, 0xB0).br(0x90, "s_st").br(0xB0, "s_nx")
        a.label("s_d").b(0xC9, 0x0B).br(0xD0, "s_b").abs(0xAD, HVE).b(0xC9, 0x80).br(0x90, "s_st").br(0xB0, "s_nx")
        a.label("s_b").b(0xC9, 0x18).br(0xD0, "s_nx").abs(0xAD, SACT).b(0x29, 0x40).br(0xF0, "s_nx")
        a.label("s_st").b(0xA9, 0x10, 0x95, 0x3D)
        a.label("s_nx").b(0xCA).br(0xD0, "s_l").b(0x60)
        a.label("q_lo").b(*[(PLAY + _off(c, r)) & 0xFF for s, c, r, k in sq])
        a.label("q_hi").b(*[(PLAY + _off(c, r)) >> 8 for s, c, r, k in sq])
        a.label("q_src").b(*[k for s, c, r, k in sq])
        a.label("q_ph").b(*[(0x2100 + r * 64 + 2 * c) >> 8 for s, c, r, k in sq])
        a.label("q_pl").b(*[(0x2100 + r * 64 + 2 * c) & 0xFF for s, c, r, k in sq])
        a.label("m_room").b(*[m[0] for m in MARKS])
        a.label("m_x").b(*[m[1] + 4 for m in MARKS])
        a.label("m_y").b(*[m[2] - 1 for m in MARKS])
        a.label("m_kind").b(*[m[3] for m in MARKS])
        return a
    from lol_newups import put3 as put
    return put(rom, 3, build).labels["fr"]                  # (bank 3: bank 0 is full; far-called)


def apply(rom: bytearray, notes: list) -> None:
    import lol_v3core as V
    import lol_heavy as H
    from lol_newups import free_in
    f = OW + 0x280
    # E4: out of the cave above the pond (no layout change: FRAME draws the stairs)
    assert rom[f + E4] == 0x00 and rom[OW + 0x80 + E4] >> 2 == 0
    rom[f + E4] = 1                                             # (owner: out above the fairy's pond, a row clear of it)
    rom[OW + E4] = (7 << 4) | (rom[OW + E4] & 0x0F)
    # H16: out of the cave on the sand
    assert rom[OW + 0x80 + H16] >> 2 == 0
    rom[OW + H16] = (8 << 4) | (rom[OW + H16] & 0x0F)       # (column 8: 5-7 left Link stuck in the exit)
    rom[f + H16] = (rom[f + H16] & 0xF8) | 4

    # the recorder: DISC (bank 0) before the whirlwind
    def bdisc(o):
        a = Asm(o)
        a.label("d").b(0xA5, 0x10).br(0xD0, "d_no").abs(0xAD, DISC_BIT[0]).b(0x29, DISC_BIT[1]).br(0xF0, "d_no")
        a.b(0xA5, 0xEB, 0xC9, H16).br(0xF0, "d_h").b(0xC9, E4).br(0xD0, "d_no")
        a.abs(0xAD, PEND).br(0xD0, "d_y").b(0xA9, 0x02).br(0xD0, "d_st")
        a.label("d_h").abs(0xAD, PEND).br(0xD0, "d_y").b(0xA9, 0x01)
        a.label("d_st").abs(0x8D, PEND).b(0xA9, 0x00).abs(0x8D, STEP)
        a.label("d_y").b(0x38, 0x60)
        a.label("d_no").b(0x18, 0x60)
        return a
    from lol_newups import put3 as put
    D = put(rom, 3, bdisc).labels["d"]
    b7 = 16 + 7 * 0x4000 - 0xC000
    assert rom[b7 + 0xEFBA:b7 + 0xEFBF] == bytes([0xA9, 0x01, 0x20, 0xAC, 0xFF]) and rom[b7 + 0xEFBF] == 0x20
    old = rom[b7 + 0xEFC0] | rom[b7 + 0xEFC1] << 8

    def bstub(o):
        a = Asm(o)
        a.b(*V.far(3, D)).br(0xB0, "r").abs(0x4C, old)
        a.label("r").b(0x60)
        return a
    sa = free_in(rom, 1, len(bstub(0x8000).bytes()), 0xB000)
    place(rom, 1, sa, bstub(sa).bytes())
    rom[b7 + 0xEFC0:b7 + 0xEFC2] = bytes([sa & 0xFF, sa >> 8])
    notes.append(f"song of discovery: H16 / E4 spots (recorder stub bank 1 ${sa:04X})")

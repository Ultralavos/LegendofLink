"""Legend of Link: Ganon's guards (owner, 2026-11-25): at 16 heart containers (as enemies see them: HVE $F0), and
always in hard mode, Ganon calls up Level 9's strongest ordinary monster (the most XP at 16 containers, from Level
9's own sprite set, which his room shows whatever the level's enemy group; no bosses, Lanmolas, Patras, traps or Vires), in a cloud of smoke, 60 frames into the fight
and every 580 after while fewer than 3 of them are alive (with 3 the timer stops; it starts again when one dies). When Ganon falls (his dying count,
$042C, running) they die too. Called-up monsters drop nothing.

Ganon's update (UpdateObject's $3E, bank 4) -> a far call (bank 3) first: in his room, during the fight, the count,
the timer and the call; past it, the guards' death. The death hook (lol_wizzrobe's, bank 2) -> a called-up monster
(marked in MK) dies dropping nothing ($0412 = $5D: a type that drops nothing).
RAM (stack page: no code of the game or LoL touches it): GROOM $0110, TL / TH $0111-$0112, SPT $0113, MK $0114-$011F."""
from lol_af import Asm, place, BANK

HVE = 0x016F
AT = 0xF0
HARD = 0x7FF8
REC9 = 0x7FAD + 8 * 5 + 1               # Level 9's record [1]: the enemy group in bits 2-3
GROOM, TL, TH, SPT, MK = 0x0110, 0x0111, 0x0112, 0x0113, 0x0114   # (stack page, unused)
PERIOD = 580                            # (owner 2026-11-25: frames between calls)
FIRST = 60                              # (the first: 60 frames into the fight)
MAX = 3
FIND_EMPTY, SET_TYPE = 0xFEBB, 0xFEB3
GANON = 0x3E
SPOTS = ((0x30, 0x6D), (0xC0, 0x6D), (0x30, 0xBD), (0xC0, 0xBD))
NO_DROP = 0x5D


def _xp16(t):
    """A monster's XP value once enemies see 16 containers (lol_build's table and level-ups)."""
    import lol_build as B
    v = B.XP_VALUES.get(t, 0)
    if t in B.XP_HARD:
        v = B.XP_HARD[t]
    if t == 0x27:
        v = 15
    for (u, _at, x) in [(0x0B, 0, B.XP_BROWN), (0x16, 0, B.XP_BLUE_POLS), (0x04, 0, B.XP_BLUE_MOBLIN),
                        (0x07, 0, B.XP_BOMB_OCTOROK), (0x08, 0, B.XP_BOMB_OCTOROK), (0x05, 0, B.XP_CHARGER),
                        (0x24, 0, B.XP_BOMBER)]:
        if t == u:
            v = x
    return v & 0x7F


def best_per_group():
    """Each enemy group's (0-3) strongest ordinary monster."""
    import lol_genload as GL
    import lol_mixgroups
    rom = lol_mixgroups.source()
    b5, la = BANK(5), 0x873F
    out = []
    for ent in GL.enemy_groups():
        kinds = set()
        for m, _c, _t in ent:
            if m >= 0x62:
                o = BANK(5) + (rom[b5 + la - 0x8000 + 2 * (m - 0x62)] | rom[b5 + la - 0x8000 + 2 * (m - 0x62) + 1] << 8) - 0x8000
                kinds |= set(rom[o:o + 8])
            else:
                kinds.add(m)
        ok = [k for k in kinds if 0 < k < 0x31 and k != 0x12 and k not in GL.TRAPS]
        out.append(max(ok, key=lambda k: (_xp16(k), k != 0x27, k)) if ok else 0x24)   # (a tie: not a Wallmaster)
    return out


def BEST_OF(best):
    """(2026-11-25) Ganon's room shows Level 9's own sprite set (levels 4, 6 and 9's: groups 2 and 3), whatever the
    level's enemy group: the strongest of those two groups' monsters."""
    return max((best[2], best[3]), key=lambda k: (_xp16(k), k != 0x27, k))


def apply(rom: bytearray, notes: list) -> None:
    import lol_v3core as V
    import lol_wizzrobe as W
    from lol_newups import free_in
    best = best_per_group()
    global BEST
    BEST = BEST_OF(best)

    def code(o):
        a = Asm(o)
        a.label("gan").abs(0xAD, HARD).br(0xD0, "g_on").abs(0xAD, HVE).b(0xC9, AT).br(0xB0, "g_on").b(0x60)
        a.label("g_on").b(0xA5, 0xEB).abs(0xCD, GROOM).br(0xF0, "g_same").abs(0x8D, GROOM)
        a.b(0xA9, FIRST & 0xFF).abs(0x8D, TL).b(0xA9, FIRST >> 8).abs(0x8D, TH)
        a.b(0xA9, 0x00, 0xA0, 0x0B)
        a.label("g_c0").abs(0x99, MK).b(0x88).br(0x10, "g_c0")
        a.label("g_same").b(0xA9, BEST).abs(0x8D, SPT)
        a.abs(0xAD, 0x0445).b(0xC9, 0x02).br(0xD0, "g_r")                   # (phase 2: the fight)
        a.abs(0xBD, 0x042C).br(0xD0, "g_kill")                               # (his dying count running)
        # the count (marks of the dead cleared)
        a.b(0xA9, 0x00, 0x85, 0x0E, 0xA0, 0x0B)
        a.label("g_cl").abs(0xB9, MK).br(0xF0, "g_cn").abs(0xB9, 0x034F).abs(0xCD, SPT).br(0xF0, "g_al")
        a.b(0xA9, 0x00).abs(0x99, MK).br(0xF0, "g_cn")
        a.label("g_al").b(0xE6, 0x0E)
        a.label("g_cn").b(0x88).br(0xD0, "g_cl")
        a.b(0xA5, 0x0E, 0xC9, MAX).br(0xB0, "g_r")
        # the timer
        a.abs(0xAD, TL).br(0xD0, "g_dl").abs(0xCE, TH)
        a.label("g_dl").abs(0xCE, TL).abs(0xAD, TL).abs(0x0D, TH).br(0xD0, "g_r")
        a.b(0xA9, PERIOD & 0xFF).abs(0x8D, TL).b(0xA9, PERIOD >> 8).abs(0x8D, TH)
        # the call: a free slot, the monster, a cloud
        a.abs(0x20, FIND_EMPTY).br(0xF0, "g_r")
        a.b(0x8A, 0x48, 0x98, 0xAA).abs(0xAD, SPT).abs(0x20, SET_TYPE)
        a.b(0xA5, 0x18, 0x29, 0x03, 0xA8).abs(0xB9, "sx").b(0x95, 0x70).abs(0xB9, "sy").b(0x95, 0x84)
        a.b(0xA9, 0x01).abs(0x9D, 0x0405).abs(0x9D, MK, ).b(0xA9, 0xFF).abs(0x9D, 0x0492)
        a.b(0x68, 0xAA)
        a.label("g_r").b(0x60)
        # Ganon fallen: his guards die (once each: their dying not restarted)
        a.label("g_kill").b(0xA0, 0x0B)
        a.label("g_kl").abs(0xB9, MK).br(0xF0, "g_kn").abs(0xB9, 0x034F).abs(0xCD, SPT).br(0xD0, "g_kn")
        a.abs(0xB9, 0x0405).b(0x29, 0x10).br(0xD0, "g_kn").b(0xA9, 0x11).abs(0x99, 0x0405)
        a.label("g_kn").b(0x88).br(0xD0, "g_kl").b(0x60)
        a.label("sx").b(*[x for x, _ in SPOTS])
        a.label("sy").b(*[y for _, y in SPOTS])
        return a
    from lol_newups import put3
    c = put3(rom, 3, code)                                                  # (bank 3: bank 2 is full)
    at = c.labels["gan"]
    L = c.labels

    def nd(o):
        # the death hook (bank 2, X): a called-up monster drops nothing
        a = Asm(o)
        a.label("nodrop").abs(0xBD, MK).br(0xF0, "n_r").b(0xA9, 0x00).abs(0x9D, MK).b(0xA9, NO_DROP).abs(0x9D, 0x0412)
        a.label("n_r").b(0x60)
        return a
    nn = len(nd(0x8000).bytes())
    an = free_in(rom, 2, nn, 0xB300)
    place(rom, 2, an, nd(an).bytes())
    d = BANK(2) + W.LABELS["death"] - 0x8000
    assert rom[d:d + 3] == bytes([0xEA, 0xEA, 0xEA])
    rom[d:d + 3] = bytes([0x20, an & 0xFF, an >> 8])
    b4 = BANK(4) - 0x8000
    ut = b4 + V.TABLES4 + 3 + 2 * GANON
    old = rom[ut] | rom[ut + 1] << 8
    s = Asm(0).b(*V.far(3, L["gan"])).abs(0x4C, old)
    n4 = len(s.bytes())
    s4 = free_in(rom, 4, n4, 0xB000, 0xBE00)
    s = Asm(s4).b(*V.far(3, L["gan"])).abs(0x4C, old)
    place(rom, 4, s4, s.bytes())
    rom[ut:ut + 2] = bytes([s4 & 0xFF, s4 >> 8])
    notes.append(f"Ganon's guards (16 containers / hard): ${BEST:02X} every {PERIOD} frames (first {FIRST}) (bank 3 ${at:04X}, stub bank 4 ${s4:04X})")


# ---------------- the owner's test build (LOL_DEBUG_GANON=1; never the page's) ----------------
import os as _os
DEBUG = _os.environ.get("LOL_DEBUG_GANON") == "1"
DBG1, DBG2 = 0x0162, 0x0163             # given yet (this file: $A5), level 9 fixed this entry
H8 = 0x77
_DBG = [None]


def debug_frame(rom):
    """(lol_upgrades' frame hook) the test build's every-frame code in bank 3, or None."""
    if not DEBUG:
        return None
    if _DBG[0] is not None:
        return _DBG[0]
    import lol_genload as GL
    from lol_newups import put3
    A = GL.ATTR

    def code(o):
        a = Asm(o)
        # once: 16 hearts full, the magical sword, the red ring, the bow, silver arrows, 30 rupees, 8 triforces
        a.label("dbg").abs(0xAD, DBG1).b(0xC9, 0xA5).br(0xF0, "d_9").b(0xA9, 0xA5).abs(0x8D, DBG1)
        for addr, v in ((0x066F, 0xFF), (0x0670, 0xFF), (0x0657, 3), (0x0662, 2), (0x065A, 1), (0x0659, 2),
                        (0x066D, 30), (0x0671, 0xFF)):
            a.b(0xA9, v).abs(0x8D, addr)
        # Level 9: Ganon's room moved to the square north of the room Link came in by (DBG2: it, | $80), doors open
        a.label("d_9").b(0xA5, 0x10).br(0xD0, "d_l").b(0xA9, 0x00).abs(0x8D, DBG2).b(0x60)     # (the overworld)
        a.label("d_l").b(0xC9, 0x09).br(0xF0, "d_in").b(0x60)
        a.label("d_in").abs(0xAD, DBG2).br(0xD0, "d_go").b(0xA5, 0x12, 0xC9, 0x05).br(0xF0, "d_rec").b(0x60)
        a.label("d_rec").b(0xA5, 0xEB, 0x09, 0x80).abs(0x8D, DBG2)                # (in play: the room he came in by)
        a.label("d_go").b(0xA2, 0x7F)
        a.label("d_f").abs(0xBD, A[2]).b(0x29, 0x3F, 0xC9, GANON).br(0xF0, "d_g").b(0xCA).br(0x10, "d_f").b(0x60)
        a.label("d_g").abs(0xAD, DBG2).b(0x29, 0x7F, 0x38, 0xE9, 0x10, 0xA8)   # Y: north of the way in
        a.b(0x86, 0x0E).b(0xC4, 0x0E).br(0xF0, "d_o")
        for t in A:                                                          # swap the two rooms' attributes
            a.abs(0xBD, t).b(0x48).abs(0xB9, t).abs(0x9D, t).b(0x68).abs(0x99, t)
        a.label("d_o").abs(0xB9, A[0]).b(0x29, 0xE3).abs(0x99, A[0])          # its south door open
        a.abs(0xAD, DBG2).b(0x29, 0x7F, 0xAA).abs(0xBD, A[0]).b(0x29, 0x1F).abs(0x9D, A[0])   # the way in's north door
        a.label("d_r").b(0x60)
        return a
    _DBG[0] = put3(rom, 3, code).labels["dbg"]
    return _DBG[0]


def debug_apply(rom, notes):
    """The test build's ROM edits: the wood sword cave (H8) leads into Level 9."""
    if not DEBUG:
        return
    OW = 0x18410
    rom[OW + 0x80 + H8] = (9 << 2) | (rom[OW + 0x80 + H8] & 3)
    notes.append("TEST BUILD: H8 -> Level 9 (Ganon north of its entrance); 16 hearts, magical sword, red ring, "
                 "bow, silver arrows, 30 rupees, 8 triforces")

"""Legend of Link 1.0: the letter's secret info shop (owner 2026-11-28; seeded Race Roms only, the only games with the
letter: lol_v10's deck gives it when the deck runs out).

Once Link has the letter, B2 and A15 each become a potion shop (the old woman, cave 10) when what the deal put there is
spent or a game: a shop, upgrade cave, triforce cave or secret already taken (the room's taken flag), a gambling game,
a hint cave, or (Upgrade mix) an upgrade cave turned plain shop. As in the original game the old woman waits for the
letter (Link must show it: no potion, so the letter is on B). Then "TOP SECRET INFO FOR SALE!" and three rupees, 50,
75 and 100: the original hint shops' engine (the hint flag) - paid each time, the words in HINT_BUF.

How:
  - lol_entrances' roll_entry (bank 6, entering an entrance) far-calls ENTRY last: on B2 / A15 with the letter and a
    spent cave, LevelBlockAttrsB's destination becomes $1A (the potion shop) for this visit (the overworld's reload
    writes the deal's back).
  - bank 1, three stubs (in lol_upgrades' WS_TABLE, free in 1.0): InitCave's taken check (never closed), its fill
    (FILL: the wares, prices, flags and opening words) and the hint state's text pick (HINT: the words of the one
    paid for).
  - the words are stored scrambled (a running key), so ROM viewers can't read them; lol_heavy's cave words (the
    secret spots' hints) likewise in seeded games (KEY0, unscramble()).
The code and words: bank 14 at INFO_AT (free in every build; placed by late(), once the data banks exist)."""
import os
from lol_af import Asm, BANK, place
import lol_fixed

BANK_I, INFO_AT, INFO_END = 14, 0xB300, 0xB700
ROOM = 0xEB
ATTR_B = 0x68FE
CAVE_WARES, CAVE_PRICES = 0x6A7E, 0x6ABA
STORE = 0x7F00
LETTER = 0x0666
OBJ1 = 0x0350                          # ObjType+1: the cave's person
CHOSEN = 0x0438                        # CaveChosenIndex
WORLD_FLAGS = 0x6BAF                   # LevelInfo_WorldFlagsAddr (the overworld's: the rooms' taken flags, $10)
POTION_SHOP, CAVE10 = 0x1A, 30         # its destination; its wares' place (cave 10 * 3)
B2, A15 = 0x11, 0x0E
HINT_SEL_AT = 0x8958                   # bank 1: the hint state's LDA HintCaveTextSelectors0,Y
TAKEN_AT, FILL_AT = 0x85D7, 0x85F9     # bank 1: InitCave's taken check and fill (JSRs)
STUBS1 = 0x8CB0                        # bank 1: lol_upgrades' WS_TABLE (1.0: free)
KEY0, KMUL, KADD = 0xA7, 5, 0x3B
PRICES = (50, 75, 100)
WARES = (0x18, 0x58, 0xD8)             # rupees; the original hint shops' flags (hint; items + prices), no minus
OPEN = ["TOP SECRET INFO", "FOR SALE!"]
HINTS = [["SOME SEEDS HAVE SECRET", "SPOTS NO ONE", "KNOWS ABOUT"],
         ["THEY ARE IN SCREENS", "YOU DON'T THINK", "SECRETS COULD BE"],
         ["YOU NEED EITHER BOMBS,", "CANDLE, POWER BRACELET", "OR RECORDER"]]
_PENDING = []


def on():
    import lol_v10 as V10
    return V10.ON and V10.has_letter()          # (only seeds with the letter)


def scramble(data: bytes) -> bytes:
    """Each byte XOR a running key (k = k * 5 + $3B from KEY0, stepped before each byte)."""
    k, out = KEY0, bytearray()
    for b in data:
        k = (k * KMUL + KADD) & 0xFF
        out.append(b ^ k)
    return bytes(out)


def unscramble(a: Asm, p: str, src: str, dst: int, n: int, key_zp: int = 0x00) -> None:
    """Code: copy n bytes from src (a label, indexed by Y from its start) to dst (X from 0), unscrambled. Y, X: start
    offsets set by the caller (Y the text's, X 0)."""
    a.b(0xA9, KEY0, 0x85, key_zp)
    a.label(p).b(0xA5, key_zp, 0x0A, 0x0A, 0x18, 0x65, key_zp, 0x18, 0x69, KADD, 0x85, key_zp)
    a.abs(0x59, src).abs(0x9D, dst).b(0xC8, 0xE8, 0xE0, n).br(0xD0, p)


def _text(lines):
    import sys, lolpaths
    for q in (lolpaths.ZORA, lolpaths.Q3B):
        if q not in sys.path:
            sys.path.insert(0, q)
    from zora.rom.serialize.text import _encode_quote
    import build_mock as base
    t = bytes(_encode_quote(base.centered(lines)))
    assert len(t) <= 80, lines
    return scramble(t + bytes(80 - len(t)))


def apply(rom: bytearray, notes: list) -> None:
    """After lol_heavy / lol_secret (their bank 1 stubs are chained here)."""
    if not on():
        return
    import lol_v3core as V
    import lol_entrances as LE
    import lol_modes
    from lol_saveblock import HINT_BUF
    ents = LE.ENTS
    have = [(r, ents.index(r)) for r in (B2, A15) if r in ents]
    assert have, "neither B2 nor A15 is an entrance"
    import lol_upgrades as U
    import lol_uptable as UT
    upmasks = {0x10 + c: m for (p, c, w), m in zip(U.SHOPS, (0x10, 0x20, 0x40))}
    taken_dests = [LE.WHITE, LE.MAGIC, *LE.UPGRADES, *LE.SHOPS, LE.SHOP4, LE.SECRET10, LE.SECRET30, LE.SECRET100]
    from lol_entrances import V_OFF

    def build(org):
        a = Asm(org)
        a.abs(0x4C, "entry").abs(0x4C, "fill").abs(0x4C, "hint")
        # entry (roll_entry's end; V_OFF set): B2 / A15 with the letter and a spent cave: the potion shop
        a.label("entry").abs(0xAD, LETTER).br(0xF0, "e_r").b(0xA5, ROOM)
        for r, i in have:
            a.b(0xC9, r).br(0xD0, f"e_n{r}").b(0xA9, i).br(0x10, "e_go")
            a.label(f"e_n{r}")
        a.label("e_r").b(0x60)
        a.label("e_go").b(0x18).abs(0x6D, V_OFF).b(0xAA).abs(0xBD, STORE).b(0x29, 0x3F)
        a.b(0xC9, LE.GAMBLE).br(0xF0, "e_yes").b(0xC9, LE.HINT).br(0xF0, "e_yes")
        if lol_fixed.UPMIX:             # an upgrade cave turned plain shop (lol_upmix's ucave)
            for d, m in upmasks.items():
                a.b(0xC9, d).br(0xD0, f"e_u{d}").abs(0xAC, UT.OWN_N).b(0xC0, 0x03).br(0xB0, "e_yes")
                a.b(0x48).abs(0xAD, UT.LINES + 7).b(0x29, m).br(0xF0, f"e_up{d}").b(0x68).br(0xD0, "e_yes")
                a.label(f"e_up{d}").b(0x68)
                a.label(f"e_u{d}")
        a.b(0xA2, len(taken_dests) - 1)
        a.label("e_tl").abs(0xDD, "e_td").br(0xF0, "e_tk").b(0xCA).br(0x10, "e_tl").b(0x60)
        a.label("e_tk").abs(0xAD, WORLD_FLAGS).b(0x85, 0x00).abs(0xAD, WORLD_FLAGS + 1).b(0x85, 0x01)
        a.b(0xA4, ROOM, 0xB1, 0x00, 0x29, 0x10).br(0xF0, "e_r2")
        a.label("e_yes").b(0xA6, ROOM).abs(0xBD, ATTR_B).b(0x29, 0x03, 0x09, POTION_SHOP << 2).abs(0x9D, ATTR_B)
        a.label("e_r2").b(0x60)
        a.label("e_td").b(*taken_dests)
        # fill (InitCave, the potion shop): its wares, prices and opening words
        a.label("fill").b(0xA2, 0x02)
        a.label("f_l").abs(0xBD, "f_w").abs(0x9D, CAVE_WARES + CAVE10).abs(0xBD, "f_p").abs(0x9D, CAVE_PRICES + CAVE10)
        a.b(0xCA).br(0x10, "f_l").b(0xA0, 0x00, 0xA2, 0x00)
        unscramble(a, "f_u", "t_open", HINT_BUF, 80)
        a.b(0xA9, lol_modes.HINT_SEL).abs(0x8D, lol_modes.QOVR).b(0x60)
        a.label("f_w").b(*WARES).label("f_p").b(*PRICES)
        # hint (the hint state; CaveChosenIndex): the words of the one paid for; A = their selector
        a.label("hint").abs(0xAC, CHOSEN).b(0xA9, 0x00)
        a.label("h_m").b(0x88).br(0x30, "h_go").b(0x18, 0x69, 80).br(0x90, "h_m")
        a.label("h_go").b(0xA8, 0xA2, 0x00)
        unscramble(a, "h_u", "t_hints", HINT_BUF, 80)
        a.b(0xA9, lol_modes.HINT_SEL, 0x60)
        a.label("t_open").b(*_text(OPEN))
        a.label("t_hints").b(*b"".join(_text(h) for h in HINTS))
        return a
    a = build(INFO_AT)
    code = a.bytes()
    assert INFO_AT + len(code) <= INFO_END, hex(INFO_AT + len(code))
    _PENDING[:] = [code]

    # --- bank 1: the stubs
    def jsr_at(cpu):
        o = BANK(1) + cpu - 0x8000
        assert rom[o] == 0x20, hex(cpu)
        return rom[o + 1] | rom[o + 2] << 8
    old_taken, old_fill = jsr_at(TAKEN_AT), jsr_at(FILL_AT)
    o = BANK(1) + HINT_SEL_AT - 0x8000
    assert rom[o] == 0xB9
    sel_tbl = rom[o + 1] | rom[o + 2] << 8
    s = Asm(STUBS1)
    s.label("taken").abs(0xAD, OBJ1).b(0xC9, 0x74).br(0xD0, "t_o").b(0x38, 0x60)
    s.label("t_o").abs(0x4C, old_taken)
    s.label("fill").abs(0x20, old_fill).b(0x48).abs(0xAD, OBJ1).b(0xC9, 0x74).br(0xD0, "f_o")
    s.b(*V.far(BANK_I, INFO_AT + 3))
    s.label("f_o").b(0x68, 0x38, 0x60)
    s.label("hint").abs(0xAD, OBJ1).b(0xC9, 0x74).br(0xF0, "h_i").abs(0xB9, sel_tbl).b(0x60)
    s.label("h_i").b(*V.far(BANK_I, INFO_AT + 6)).b(0x60)
    sb = s.bytes()
    assert STUBS1 + len(sb) <= 0x8D00
    place(rom, 1, STUBS1, sb)
    for cpu, lab in ((TAKEN_AT, "taken"), (FILL_AT, "fill")):
        p = s.labels[lab]
        rom[BANK(1) + cpu - 0x8000 + 1:BANK(1) + cpu - 0x8000 + 3] = bytes([p & 0xFF, p >> 8])
    p = s.labels["hint"]
    rom[o:o + 3] = bytes([0x20, p & 0xFF, p >> 8])
    notes.append(f"info shop (Race Rom): B2 / A15 with the letter ({len(code)} bytes in bank {BANK_I}, {len(sb)} in bank 1)")


def entry_far():
    """lol_entrances' roll_entry: its last call (7 bytes), or b'' when off."""
    if not on():
        return b""
    import lol_v3core as V
    return V.far(BANK_I, INFO_AT)


def late(rom):
    if _PENDING:
        place(rom, BANK_I, INFO_AT, _PENDING[0])

"""Legend of Link: the two secret modes (v2.02 test 17).

Swordless: Link walks into 5 different entrances (caves, shops, levels: any rolled entrance; the wood sword cave
doesn't count) before he has a sword, then into the wood sword cave (H8): the old man says "NO SWORD FOR YOU! BOMB
BEHIND THE FAIRY" and offers nothing, for good. D10's second-quest secret (the rock wall behind the fairy) opens in
the first quest too, to a cave (the wood sword cave's person and table) with a wood boomerang, or a bomb upgrade if
Link has a boomerang: "I GUESS SWORDLESS IS YOUR STYLE". Every offer of the white or magical sword (old men, A-F,
the white sword cave, level 9's upgrade) is a bomb upgrade instead while he holds fewer than 32 bombs (the bag goes
to 32); upgrades that need a sword (beams, sword mastery) need one in every mode.

Hard mode: Link dies 5 times without walking into any entrance, then walks into the wood sword cave: the old man says
"OH, YOU WANT HARD MODE?", Link loses 2 heart containers (at least 1 is left) and still gets the sword; a heart level
takes 100 XP instead of 50, and enemies level up 3 heart containers sooner (their checks read lol_build's HVE,
HeartValues + 3 containers in hard mode, kept every frame by the status bar's XP code).

State (battery RAM, past lol_saveblock's version byte; cleared for a new file by lol_entrances' clear):
  SWL $7FF7 (1: swordless), HARD $7FF8 (1: hard), NCAVE $7FF9 (entrances walked into, up to 5), CROOMS $7FFA-$7FFE.
"""
import os
SWL, HARD, NCAVE, CROOMS = 0x7FF7, 0x7FF8, 0x7FF9, 0x7FFA
# build options (the randomizer page sets these): a mode from the start, and a fixed seed
START = os.environ.get("LOL_START", "normal")           # normal | swordless | hard
assert START in ("normal", "swordless", "hard"), START
SEED_OPT = int(os.environ["LOL_SEED"]) & 0xFFFFFFFF if os.environ.get("LOL_SEED") else None
HARD_PENDING = 0x80                     # NCAVE's bit for "hard mode from the start: take the 2 containers"
NROOMS = 5
H8, D10 = 0x77, 0x39
QOVR = 0x01A6                           # (stack page, unused): a quote selector for the cave being set up (0: none)
HINT_SEL = 0x06                         # the selector whose text is HINT_BUF (lol_genload)
ATTR_A, ATTR_B, ATTR_D, ATTR_F = 0x687E, 0x68FE, 0x69FE, 0x6AFE   # the overworld's level block in WRAM: tables A
                                        # (exit column), B (cave), D (layout), F (quest bits, exit row)
LAYOUT = 0x7B                           # an unused layout: D10's with the secret behind the fairy
SECRET_COL, SECRET_ROW = 7, 1           # the square above the pond's middle (column 7, row 1)
ROCK_WALL_SECRET = 0x27                 # the secret rock wall square (a bomb opens it)
LAYOUTS = 0x15428                       # RoomLayoutsOW (file): 16 column codes a layout
COL_DIR = 0x19D1F                       # bank 6 $9D0F (file): the 16 column heaps' addresses (copied to WRAM $6827)
B5 = 16 + 5 * 0x4000 - 0x8000
DEATHS = 0x0630                         # vanilla's death count per save slot
WOOD_SWORD, BOOMERANG_ITEM, BOMB_UP, NO_ITEM = 0x01, 0x1D, 0x24, 0x3F
CAVE0_WARES = 0x6A7E                    # the wood sword cave's three items (WRAM)
TEXTS = {"nosword": ["NO SWORD FOR YOU!", "BOMB BEHIND THE FAIRY"],
         "style": ["I GUESS SWORDLESS", "IS YOUR STYLE"],
         "hard": ["OH, YOU WANT", "HARD MODE?"]}


def track(a):
    """lol_entrances' roll entry (bank 6), an entrance found (X kept): count a new room while neither mode is on."""
    a.label("md_track").abs(0xAD, SWL).abs(0x0D, HARD).br(0xD0, "md_tr")
    a.abs(0xAC, NCAVE).b(0xC0, NROOMS).br(0xB0, "md_tr")
    a.b(0xA5, 0xEB)
    a.label("md_tl").b(0x88).br(0x30, "md_new").abs(0xD9, CROOMS).br(0xF0, "md_tr").br(0xD0, "md_tl")
    a.label("md_new").abs(0xAC, NCAVE).abs(0x99, CROOMS).abs(0xEE, NCAVE)
    a.label("md_tr").b(0x60)


def d10_writes(a):
    """D10 as the swordless game has it: the layout with the secret, the cave (the wood sword cave's), its exit at
    the secret's square, both quests."""
    a.abs(0xAD, ATTR_B + D10).b(0x29, 0x03, 0x09, 0x40).abs(0x8D, ATTR_B + D10)
    a.abs(0xAD, ATTR_A + D10).b(0x29, 0x0F, 0x09, SECRET_COL << 4).abs(0x8D, ATTR_A + D10)
    a.abs(0xAD, ATTR_D + D10).b(0x29, 0x80, 0x09, LAYOUT).abs(0x8D, ATTR_D + D10)
    a.abs(0xAD, ATTR_F + D10).b(0x29, 0x38, 0x09, SECRET_ROW - 1).abs(0x8D, ATTR_F + D10)


def d10(a):
    """lol_entrances' apply (bank 6, after the overworld's level block copy): swordless opens D10's secret; hard mode
    from the start (the pending bit) takes its two containers, once."""
    a.abs(0xAD, SWL).br(0xF0, "md_dx")
    d10_writes(a)
    a.label("md_dx")
    a.abs(0xAD, NCAVE).br(0x10, "md_hx").b(0xA9, 0x00).abs(0x8D, NCAVE)
    a.abs(0xAD, 0x066F).b(0x4A, 0x4A, 0x4A, 0x4A, 0x38, 0xE9, 0x02).br(0xB0, "md_h1").b(0xA9, 0x00)
    a.label("md_h1").b(0x85, 0x00, 0x0A, 0x0A, 0x0A, 0x0A, 0x05, 0x00).abs(0x8D, 0x066F)
    a.b(0xA9, 0xFF).abs(0x8D, 0x0670)
    a.label("md_hx")


CLEAR_AT = None                         # bank 2: the new-file part (install_clear)


def clear(a):
    """lol_entrances' new-file clear (A = 0 kept): JSR to the routine install_clear placed."""
    a.abs(0x20, CLEAR_AT)


def install_clear(rom):
    """The new-file part in bank 2 (free space): this file's state cleared; with build options, the starting mode
    and the fixed seed (the odds' per-file seed byte and the entrances' RNG; lol_entrances then never stirs the RNG
    with the frame count). Returns with A = 0."""
    global CLEAR_AT
    from lol_af import Asm, place
    from lol_newups import free_in

    def build(org):
        a = Asm(org)
        a.b(0xA9, 0x00, 0xA2, 3 + NROOMS - 1)
        a.label("md_c").abs(0x9D, SWL).b(0xCA).br(0x10, "md_c")
        if START == "swordless":
            a.b(0xA9, 0x01).abs(0x8D, SWL)
        elif START == "hard":
            a.b(0xA9, 0x01).abs(0x8D, HARD).b(0xA9, HARD_PENDING).abs(0x8D, NCAVE)
        if SEED_OPT is not None:
            from lol_odds import STORE, SEED_AT
            from lol_entrances import RNG
            b = SEED_OPT.to_bytes(4, "little")
            a.b(0xA9, b[0] | 1).abs(0x8D, STORE + SEED_AT)
            a.b(0xA9, b[1]).abs(0x8D, RNG).b(0xA9, b[2] | (0 if b[1] else 1)).abs(0x8D, RNG + 1)
        a.b(0xA9, 0x00, 0x60)
        return a
    CLEAR_AT = 0xB400                   # (bank 2's long free run, $B381-$B8FF)
    code = build(CLEAR_AT).bytes()
    assert CLEAR_AT + len(code) <= 0xB8FF
    place(rom, 2, CLEAR_AT, code)


CAVE = None                             # bank 0: the cave routine (lol_upgrades' wares stub far-calls it first)


def _texts():
    import sys
    import lolpaths
    for p in (lolpaths.ZORA, lolpaths.Q3B):
        if p not in sys.path:
            sys.path.insert(0, p)
    from zora.rom.serialize.text import _encode_quote
    import build_mock as base
    out, blob = {}, bytearray()
    for k, lines in TEXTS.items():
        out[k] = len(blob)
        blob += bytes(_encode_quote(base.centered(lines)))
    blob += bytes(80)
    assert len(blob) < 256
    return out, bytes(blob)


def install(rom: bytearray, notes: list) -> None:
    """The bank 0 cave routine and bank 1's quote override."""
    global CAVE
    import lol_v3core as V3
    from lol_af import Asm, patch
    from lol_saveblock import HINT_BUF
    from lol_newups import free_in
    OW = 0x18410
    fl = [rom[OW + 0x200 + k] & 0xC0 for k in range(3)]
    offs, blob = _texts()

    def build(org):
        a = Asm(org)
        a.label("cv").b(0x48, 0x8A, 0x48, 0x98, 0x48)
        a.b(0xA9, 0x00).abs(0x8D, QOVR)
        a.abs(0xAD, 0x0350).b(0xC9, 0x6A).br(0xD0, "o1")
        a.b(0xA5, 0xEB, 0xC9, H8).br(0xF0, "h8").b(0xC9, D10).br(0xD0, "o1")
        a.abs(0xAD, 0x0674).abs(0x0D, 0x0675).br(0xF0, "boom")
        a.b(0xA9, BOMB_UP).br(0xD0, "put")
        a.label("boom").b(0xA9, BOOMERANG_ITEM)
        a.label("put").abs(0x20, "setmid").b(0xA2, offs["style"]).abs(0x20, "quote")
        a.label("o1").abs(0x4C, "out")
        a.label("h8")
        import lol_fixed as _fx
        if not _fx.FIXED:                       # (owner 2026-11-25: a file named UNSEED never turns swordless)
            a.abs(0x20, "unsck")
        a.abs(0xAD, SWL).br(0xD0, "nosw")
        a.abs(0xAD, HARD).br(0xD0, "normal").abs(0xAD, 0x0657).br(0xD0, "normal")
        a.abs(0xAD, NCAVE).b(0xC9, NROOMS).br(0xB0, "mk_swl").abs(0xAD, NCAVE).br(0xD0, "normal")
        a.b(0xA4, 0x16).abs(0xB9, DEATHS).b(0xC9, 5).br(0x90, "normal")
        # hard mode: two heart containers fewer (at least one), hearts at most the containers
        a.b(0xA9, 0x01).abs(0x8D, HARD)
        a.abs(0xAD, 0x066F).b(0x4A, 0x4A, 0x4A, 0x4A, 0x38, 0xE9, 0x02).br(0xB0, "hc_ok").b(0xA9, 0x00)
        a.label("hc_ok").b(0x85, 0x00, 0x0A, 0x0A, 0x0A, 0x0A, 0x05, 0x00).abs(0x8D, 0x066F)
        a.b(0xA9, 0xFF).abs(0x8D, 0x0670)                                   # (the last heart full)
        a.b(0xA2, offs["hard"]).abs(0x20, "quote").abs(0x4C, "normal")
        a.label("mk_swl").b(0xA9, 0x01).abs(0x8D, SWL)
        a.label("nosw").b(0xA9, NO_ITEM).abs(0x20, "setmid").b(0xA2, offs["nosword"]).abs(0x20, "quote")
        d10_writes(a)                                                               # D10's secret, now
        a.abs(0x4C, "out")
        a.label("normal").b(0xA9, WOOD_SWORD).abs(0x20, "setmid")
        a.label("out").b(0x68, 0xA8, 0x68, 0xAA, 0x68, 0x60)
        if not _fx.FIXED:                       # unsck: a file named UNSEED: no entrances counted (lol_names)
            import lol_names
            import lol_v3core as _V
            a.label("unsck").b(*_V.far(3, lol_names.lib(rom)["namek"])).b(0xC9, 0x01).br(0xD0, "uns_r")
            a.abs(0xAD, NCAVE).b(0x29, HARD_PENDING).abs(0x8D, NCAVE)      # (its entrance count: never 5)
            a.label("uns_r").b(0x60)
        # setmid: the cave's three places: nothing, A, nothing (their flag bits kept)
        a.label("setmid").b(0x09, fl[1]).abs(0x8D, CAVE0_WARES + 1)
        a.b(0xA9, NO_ITEM | fl[0]).abs(0x8D, CAVE0_WARES).b(0xA9, NO_ITEM | fl[2]).abs(0x8D, CAVE0_WARES + 2).b(0x60)
        # quote: text X into the hint buffer, and the override
        a.label("quote").b(0xA0, 0x00)
        a.label("q_l").abs(0xBD, "texts").abs(0x99, HINT_BUF).b(0xE8, 0xC8, 0xC0, 80).br(0xD0, "q_l")
        a.b(0xA9, HINT_SEL).abs(0x8D, QOVR).b(0x60)
        a.label("texts").b(*blob)
        return a
    a = V3.put0(rom, build)
    CAVE = a.labels["cv"]
    # bank 1 InitCave: STA $0415 (the quote selector) -> the override when one is set (then cleared)
    q = Asm(0)
    def qb(org):
        q = Asm(org)
        q.label("qf").abs(0x8D, 0x0415).abs(0xAD, QOVR).br(0xF0, "qr").abs(0x8D, 0x0415)
        q.b(0xA9, 0x00).abs(0x8D, QOVR)
        q.label("qr").b(0x60)
        return q
    n = len(qb(0x8000).bytes())
    at = free_in(rom, 1, n, 0xB000)
    q = qb(at)
    from lol_af import place
    place(rom, 1, at, q.bytes())
    patch(rom, 1, 0x8606, bytes([0x8D, 0x15, 0x04]), bytes([0x20, at & 0xFF, at >> 8]))
    notes.append(f"modes: cave routine bank 0 ${CAVE:04X} ({len(a.bytes())} bytes), quote override bank 1 ${at:04X}")


def apply_rom(rom: bytearray, notes: list) -> None:
    """D10's secret: column group D's heap copied (bank 5) with one more column (column $D1, the pond's top edge,
    with the secret rock wall at row 1), and layout $7B = D10's layout with that column at the secret's place."""
    from lol_newups import free_in
    from lol_af import place
    dirp = [rom[COL_DIR + 2 * k] | rom[COL_DIR + 2 * k + 1] << 8 for k in range(16)]

    def col(code):
        g, i = code >> 4, code & 15
        p, n = dirp[g], -1
        while True:
            if rom[B5 + p] & 0x80:
                n += 1
                if n == i:
                    break
            p += 1
        sq, start = [], p
        while len(sq) < 11:
            b = rom[B5 + p]; sq.append(b & 0x3F)
            if b & 0x40:
                sq.append(b & 0x3F)
            p += 1
        return sq[:11], start, p
    g = 0xD
    lo, hi = dirp[g], dirp[g + 1]
    heap = bytes(rom[B5 + lo:B5 + hi])
    n = sum(1 for b in heap if b & 0x80)
    for i in range(n):                                  # every column of the group ends inside it
        assert col(g << 4 | i)[2] <= hi, i
    lay = rom[0x18410 + 0x180 + D10] & 0x7F
    base_col = rom[LAYOUTS + 16 * lay + SECRET_COL]
    sq, _, _ = col(base_col)
    assert sq[SECRET_ROW] == 0x1B and sq[SECRET_ROW + 1] == 0x0E, sq   # brown rock above the sand
    sq[SECRET_ROW] = ROCK_WALL_SECRET
    newcol = bytes([sq[0] | 0x80] + sq[1:])
    new_heap = heap + newcol
    at = free_in(rom, 5, len(new_heap), 0x8000, 0xBD40 - len(new_heap))   # (lol_snubber: $BD5E on)
    place(rom, 5, at, new_heap)
    rom[COL_DIR + 2 * g:COL_DIR + 2 * g + 2] = bytes([at & 0xFF, at >> 8])
    code = g << 4 | n
    assert n < 16
    # the layout: unused by every screen
    assert all(rom[0x18410 + 0x180 + s] & 0x7F != LAYOUT for s in range(0x80))
    cols = bytearray(rom[LAYOUTS + 16 * lay:LAYOUTS + 16 * lay + 16])
    cols[SECRET_COL] = code
    rom[LAYOUTS + 16 * LAYOUT:LAYOUTS + 16 * LAYOUT + 16] = cols
    notes.append(f"modes: D10's secret layout ${LAYOUT:02X} (column ${code:02X}, group D's heap now bank 5 ${at:04X})")


GROUND = (("coast", 5, 0x1789A - 1, 0x24, 0), ("Armos", 4, 0x10D05 - 1, 0x29, 3))   # (bank, file of LDA #item)
SEED = 0x606A + 17                      # lol_odds' per-file seed (file 1)


def apply_ground(rom: bytearray, notes: list) -> None:
    """The coast's and the Armos' items (lol_moves' LDA #item / STA RoomItem): an S, D or X badge, or an orange or
    blue XP potion, each 1 in 5 (by the file's seed, so the same each visit; a badge Link has three of: the orange
    potion); swordless: a bomb upgrade."""
    import lol_v3core as V3
    from lol_af import Asm, place
    from lol_newups import free_in

    def build(org):
        a = Asm(org)
        a.label("pk").b(0x85, 0x00, 0x8A, 0x48).abs(0xAD, SWL).br(0xF0, "p_r").b(0xA9, BOMB_UP).br(0xD0, "p_x")
        a.label("p_r").abs(0xAD, SEED).b(0x18, 0x65, 0x00)
        a.label("p_m").b(0xC9, 5).br(0x90, "p_i").b(0xE9, 5).br(0xB0, "p_m")
        a.label("p_i").b(0xAA).abs(0xBD, "items").b(0xE0, 3).br(0xB0, "p_x")
        a.b(0x85, 0x00).abs(0xAD, 0x0673).abs(0x3D, "mask").abs(0xDD, "mask").br(0xD0, "p_ok")
        a.b(0xA9, 0x29).br(0xD0, "p_x")                                    # three already: the orange potion
        a.label("p_ok").b(0xA5, 0x00)
        a.label("p_x").b(0x85, 0x01, 0x68, 0xAA, 0xA5, 0x01, 0x60)        # (X kept)
        a.label("items").b(0x26, 0x27, 0x28, 0x29, 0x2A)
        a.label("mask").b(0x03, 0x0C, 0x30)
        return a
    pk = V3.put0(rom, build).labels["pk"]
    for name, bank, at, item, kind in GROUND:
        assert rom[at:at + 4] == bytes([0xA9, item, 0x85, 0xAB]), (name, rom[at:at + 4].hex())
        stub = lambda org: bytes([0xA9, kind]) + V3.far(0, pk) + bytes([0x85, 0xAB, 0x60])
        s = free_in(rom, bank, len(stub(0)), 0xB000)
        place(rom, bank, s, stub(s))
        rom[at:at + 4] = bytes([0x20, s & 0xFF, s >> 8, 0xEA])
    notes.append("modes: the coast's and the Armos' items rolled (badges / XP potions; swordless a bomb upgrade)")


def apply_continue(rom: bytearray, notes: list) -> None:
    """Bank 5's start / continue sets Link's hearts to 3 (LDA $066F / AND #$F0 / ORA #$02): no more than his
    containers (hard mode can leave fewer than 3)."""
    from lol_af import place, patch
    from lol_newups import free_in
    from lol_af import Asm

    def code(org):
        a = Asm(org)
        # hard mode from the start (lol_modes.clear's pending bit): two containers fewer, once
        a.b(0x48).abs(0xAD, NCAVE).br(0x10, "nf").b(0xA9, 0x00).abs(0x8D, NCAVE).b(0x68)
        a.b(0x4A, 0x4A, 0x4A, 0x4A, 0x38, 0xE9, 0x02).br(0xB0, "ok").b(0xA9, 0x00)
        a.label("ok").b(0x0A, 0x0A, 0x0A, 0x0A).abs(0x8D, 0x066F).b(0x48)
        a.label("nf").b(0x68)
        a.b(0x29, 0xF0, 0x48, 0x4A, 0x4A, 0x4A, 0x4A, 0xC9, 0x02, 0x90, 0x02, 0xA9, 0x02,
            0x8D, 0x73, 0x01, 0x68, 0x0D, 0x73, 0x01, 0x60)
        return a.bytes()
    at = free_in(rom, 5, len(code(0x8000)), 0xB000)
    place(rom, 5, at, code(at))
    patch(rom, 5, 0x8B7A, bytes.fromhex("29f00902"), bytes([0x20, at & 0xFF, at >> 8, 0xEA]))
    notes.append(f"modes: start / continue hearts at most the containers (bank 5 ${at:04X})")


def apply_hud(rom: bytearray, notes: list) -> None:
    """Bank 1's heart row (copied to WRAM $6E79): a hearts byte of 0 drew no hearts at all (an empty file); hard mode
    can leave 1 container with no full heart (byte 0, the half heart in $0670). Blank only when that is empty too:
    LDA $0E / BEQ blank / CPX $01 -> JSR (bank 7) / NOP x3, keeping BCS / blank."""
    import lol_v3core as V3
    from lol_af import Asm, patch

    def build(org):
        a = Asm(org)
        a.label("hd").b(0xA5, 0x0E, 0x05, 0x0F).br(0xF0, "hz").b(0xE4, 0x01, 0x60)
        a.label("hz").b(0x18, 0x60)
        return a
    hd = V3.put7(rom, build).labels["hd"]
    patch(rom, 1, 0xA71E, bytes.fromhex("a50ef004e401"), bytes([0x20, hd & 0xFF, hd >> 8, 0xEA, 0xEA, 0xEA]))
    notes.append(f"modes: the heart row draws a lone container (bank 7 ${hd:04X})")

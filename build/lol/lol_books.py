"""Legend of Link: the red and blue books. The red one is the book (item $11, $0661 = 1); the blue one is item $25
($0661 = 2). Either still makes the wand burn; with one, every hit Link deals does more damage: red +1, blue +2
(a damage unit is $10, the wooden sword's hit).

Code that can run with any bank at $8000 goes in the COMMON area, the same bytes at the same address in banks 0-6:
  pal   (bank 7 $E73A: LDA ItemSlotToPalette,X): the book's slot is drawn blue (palette 1) for the blue book
        ($0661 = 2, or item $25 being drawn: FLAG bit 1, set by the bomb upgrade's draw helper)
  bonus (bank 1 $B4C9, run from WRAM $7C59: LDA ObjHP,X before CMP / SBC damage $07): $07 += $10 * book; a stub
        here far-calls the body in bank 0
The take (bank 1 $891E: the caves' JSR TakeItem; item $25 is taken as the book, then $0661 = 2) is in bank 1 only.
"""
from lol_af import Asm, BANK, patch, place
from lol_bombup import FLAG, WRAM_DELTA

BLUE_BOOK = 0x25
BOOK = 0x0661
COMMON = 0xBD00                          # free in every switchable bank of PRG1 ($BB61-$BDBF), above bank 1's code
TAKE_AT = 0xBD2F                         # bank 1 only
BSTUB = TAKE = BONUS0 = None


def apply(rom: bytearray, notes: list) -> None:
    global BSTUB, TAKE, BONUS0
    import lol_v3core as V
    # bonus: in bank 0, far-called from the common stub (lol_upgrades chains its sword +1 in front)
    def build(org):
        b = Asm(org)
        b.label("bonus").abs(0xAD, BOOK).br(0xF0, "b_n").b(0x0A, 0x0A, 0x0A, 0x0A, 0x18, 0x65, 0x07)
        b.br(0x90, "b_st").b(0xA9, 0xFF)
        b.label("b_st").b(0x85, 0x07)
        b.label("b_n").abs(0xBD, 0x0485).b(0x60)
        return b
    BONUS0 = V.put0(rom, build).labels["bonus"]
    a = Asm(COMMON)
    import lol_uptable as UT
    rod = UT.bit("divining rod")
    a.label("pal").b(0xE0, 0x08).br(0xD0, "p_bk").abs(0xAD, rod[0]).b(0x29, rod[1]).br(0xF0, "p_red")
    a.b(0xA9, 0x00, 0x60)                                                       # the divining rod: Link's colors
    a.label("p_bk").b(0xE0, 0x0A).br(0xD0, "p_red")                             # the book's slot?
    a.abs(0xAD, BOOK).b(0xC9, 0x02).br(0xF0, "p_blue")                          # Link's is blue
    a.abs(0xAD, FLAG).b(0x29, 0x02).br(0xF0, "p_red")                           # or item $25 is being drawn
    a.label("p_blue").b(0xA9, 0x01, 0x60)
    a.label("p_red").abs(0xBD, 0x72EC).b(0x60)
    a.label("bstub").b(*V.far(0, BONUS0)).b(0x60)
    code = a.bytes()
    for bank in range(7):
        place(rom, bank, COMMON, code)
    # take: only ever from bank 1 (its caves' JSR TakeItem)
    t = Asm(TAKE_AT)
    t.label("take").b(0xC9, BLUE_BOOK).br(0xF0, "t_bb").abs(0x4C, 0x7370)
    t.label("t_bb").b(0xA9, 0x11).abs(0x20, 0x7370).b(0xA9, 0x02).abs(0x8D, BOOK)
    t.b(0xA9, BLUE_BOOK).abs(0x8D, 0x0505).b(0x60)                              # held up: the blue one
    place(rom, 1, TAKE_AT, t.bytes())
    L = {**a.labels, **t.labels}
    BSTUB, TAKE = L["bstub"], L["take"]
    j = lambda n: bytes([0x20, L[n] & 0xFF, L[n] >> 8])
    patch(rom, 7, 0xE73A, bytes([0xBD, 0xEC, 0x72]), j("pal"))
    patch(rom, 1, 0x7C59 + WRAM_DELTA, bytes([0xBD, 0x85, 0x04]), j("bstub"))
    patch(rom, 1, 0x891E, bytes([0x20, 0x70, 0x73]), j("take"))
    notes.append(f"books: red +1, blue (item $25) +2 ({len(code)} bytes in every bank at ${COMMON:04X}, the bonus in bank 0, the take in bank 1)")


# Every major item a dungeon gives (room items and item cellars, both quests) becomes bombs
MAJOR = {0x01, 0x02, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15,
         0x1C, 0x1D, 0x1E}
BLOCKS = (0x18710, 0x18A10, 0x18D10, 0x19010)


def dungeon_items_to_bombs(rom: bytearray, notes: list) -> None:
    n = 0
    for base in BLOCKS:
        for room in range(128):
            at = base + 0x200 + room
            if rom[at] & 0x1F in MAJOR:
                rom[at] &= 0xE0; n += 1
    notes.append(f"dungeon items -> bombs: {n}")

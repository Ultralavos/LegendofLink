"""Legend of Link: the title's story and item scroll become a scrolling list of the upgrades' names.

The story page (bank 6's StoryTileAttrTransferBuf: 30 rows of 32 tiles for nametable $2000, then its attributes) is
cleared (frame and text) and holds a heading and the first names, all white. The item scroll (bank 2, demo phase 1
subphase 2) keeps its machinery: every 8 pixels it clears the next row and, when the row's flag (the table at $915E)
has bit 7, writes the next text line (the line pointers, normally at $94AD). The new flags never set bit 5 (the item
sprites and the Link with the note at the end), keep the game's bit 6 (each attribute row set to palette 0 before it
shows) and put a name on every other row. The scroll stops once the last name is well on screen, then the usual hold
and the return to the title."""
from lol_af import patch

STORY = 0x1A499                     # file: the story transfer buffer (records: hi, lo, $20, 32 tiles)
FLAGS = 0x915E                      # bank 2: one flag byte per 8 pixels of the item scroll
N_FLAGS = 176                       # (5 * 256 + 128 pixels)
DATA, DATA_END = 0x929A, 0x94E7     # bank 2: the game's text lines and their pointers (now free)
PTR_LO, PTR_HI = 0x96B8, 0x96BD     # LDA $94AD,X / LDA $94AE,X
START = 0x95F7                      # LDA #$29 / STA $041D / LDA #$00 / STA $041C: the first row's address
END_HI, END_LO = 0x9630, 0x9637     # CMP #$05 / CMP #$80: the scroll's length

HEADING, HEAD_ROW = "UPGRADES", 2
PAGE_FIRST, PITCH = 5, 2            # the page's first name row; a name every other row (odd rows)
HOOK = 0x95EC                       # subphase 1 (the pause): INC $041A
CODE = 0xB060                       # bank 2 free (lol_legend's old room)
NAMES = {"beams": "SWORD BEAMS", "regen": "REGENERATION", "fairy bottle": "FAIRY IN A BOTTLE",
         "unlimited candle": "UNLIMITED BLUE CANDLE", "misers bow": "MISERS BOW", "refilling bag": "REFILLING BOMB BAG",
         "xp boost": "XP BOOST"}


def enc(s):
    return bytes(0x24 if c == " " else (ord(c) - 48 if c.isdigit() else ord(c) - 55) for c in s)


def names():
    import lol_uptable as T
    out = sorted(NAMES.get(r[0], r[0].upper()) for r in T.ROWS)
    assert all(len(n) <= 28 and all(c == " " or c.isalnum() for c in n) for n in out)
    return out


def row_at(r, col):
    return STORY + r * 35 + 3 + col


def apply(rom: bytearray, notes: list) -> None:
    from lol_af import BANK
    for r in range(4):
        assert rom[STORY + r * 35:STORY + r * 35 + 3] == bytes([0x20, r * 0x20, 0x20])
    b2 = lambda cpu: BANK(2) + cpu - 0x8000
    every = names()
    # the page: blank, all palette 0, the heading and as many names as fit
    for r in range(30):
        rom[row_at(r, 0):row_at(r, 32)] = b"\x24" * 32
    att = STORY + 30 * 35
    assert rom[att:att + 3] == bytes([0x23, 0xC0, 0x20]) and rom[att + 35:att + 38] == bytes([0x23, 0xE0, 0x20])
    rom[att + 3:att + 35] = bytes(32)
    rom[att + 38:att + 70] = bytes(32)
    centre = lambda s: (32 - len(s)) // 2
    rom[row_at(HEAD_ROW, centre(HEADING)):row_at(HEAD_ROW, centre(HEADING) + len(HEADING))] = enc(HEADING)
    page_rows = list(range(PAGE_FIRST, 30, PITCH))
    on_page, rest = every[:len(page_rows)], every[len(page_rows):]
    for r, n in zip(page_rows, on_page):
        rom[row_at(r, centre(n)):row_at(r, centre(n) + len(n))] = enc(n)
    # below the page: nametable 2's rows 0-7 (the title's blank top rows, offscreen during the pause) get the next
    # names from a hook in the pause (one full row a frame, at its frames 1-4, then their attributes), then the item scroll's rows from row 8
    first_v = page_rows[-1] + PITCH                    # 31: the next name's row, counted from the page's top
    gap_rows = list(range(first_v, 38, PITCH))
    gap, rest = rest[:len(gap_rows)], rest[len(gap_rows):]
    from lol_af import Asm, place
    recs = []
    for r, n in zip(gap_rows, gap):
        addr = 0x2800 + (r - 30) * 32
        row = bytearray(b"\x24" * 32)
        row[centre(n):centre(n) + len(n)] = enc(n)
        recs.append(bytes([addr >> 8, addr & 0xFF, 32]) + bytes(row) + b"\xFF")
    recs.append(bytes([0x2B, 0xC0, 32]) + bytes(32) + b"\xFF")   # nametable 2's rows 0-15 attributes: palette 0
    assert all(len(r) == 36 for r in recs)
    a = Asm(CODE)
    a.label("h").abs(0xEE, 0x041A).abs(0xAC, 0x041A).b(0x88, 0xC0, len(recs)).br(0xB0, "r")
    a.abs(0xB9, "lo").b(0x85, 0x00).abs(0xB9, "hi").b(0x85, 0x01)
    a.b(0xA0, 0x00)
    a.label("cp").b(0xB1, 0x00).abs(0x99, 0x0302).b(0xC8, 0xC0, 36).br(0xD0, "cp")
    a.label("r").b(0x60)
    a.label("lo").b(*[0] * len(recs)).label("hi").b(*[0] * len(recs))
    for k in range(len(recs)):
        a.label("rec%d" % k).b(*recs[k])
    code = bytearray(a.bytes())
    L = a.labels
    for k in range(len(recs)):
        p = L["rec%d" % k]
        code[L["lo"] - CODE + k] = p & 0xFF
        code[L["hi"] - CODE + k] = p >> 8
    place(rom, 2, CODE, bytes(code))
    patch(rom, 2, HOOK, bytes.fromhex("ee1a04"), bytes([0x20, CODE & 0xFF, CODE >> 8]))
    first_dyn = gap_rows[-1] + PITCH - 38              # the item scroll's first name row (its rows start at 38)
    # flags: keep bit 6, a line on every other row from the first
    old = rom[b2(FLAGS):b2(FLAGS) + N_FLAGS]
    flags = bytearray(f & 0x40 for f in old)
    for k in range(len(rest)):
        flags[first_dyn + k * PITCH] |= 0x80
    rom[b2(FLAGS):b2(FLAGS) + N_FLAGS] = flags
    # the lines (column, tiles, $FF) and their pointers
    blob, ptrs = bytearray(), []
    ptr_at = DATA
    base = DATA + 2 * len(rest)
    for n in rest:
        ptrs.append(base + len(blob))
        blob += bytes([centre(n)]) + enc(n) + b"\xFF"
    data = b"".join(bytes([p & 0xFF, p >> 8]) for p in ptrs) + bytes(blob)
    assert DATA + len(data) <= DATA_END, len(data)
    rom[b2(DATA):b2(DATA_END)] = data + b"\xFF" * (DATA_END - DATA - len(data))
    patch(rom, 2, PTR_LO, bytes.fromhex("bdad94"), bytes([0xBD, ptr_at & 0xFF, ptr_at >> 8]))
    patch(rom, 2, PTR_HI, bytes.fromhex("bdae94"), bytes([0xBD, (ptr_at + 1) & 0xFF, (ptr_at + 1) >> 8]))
    # the end: once the last name is near the screen's bottom third (pixels scrolled in the item scroll)
    last_v = 38 + first_dyn + (len(rest) - 1) * PITCH
    px = (last_v - 22) * 8
    px = max(px, 8)
    patch(rom, 2, END_HI, bytes([0xC9, 0x05]), bytes([0xC9, px >> 8]))
    patch(rom, 2, END_LO, bytes([0xC9, 0x80]), bytes([0xC9, px & 0xFF]))
    notes.append(f"title: a list of {len(every)} upgrades ({len(on_page)} on the page, {len(gap)} below it, {len(rest)} scrolled; "
                 f"{len(data)} bytes of lines; the scroll ends after {px} pixels)")

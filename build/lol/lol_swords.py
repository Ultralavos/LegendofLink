"""Legend of Link: the sword caves. A11's (cave 2) gives the white sword once Link has 4 triforces; C2's (cave 3)
gives the silver arrows once he has all 8. The caves' heart check (bank 1 $88FC: LDY #$40 or #$B0 / CPY HeartValues)
counts the triforce pieces instead. Their old men get their own texts (quotes 5 and 15: the door repair's and the
expensive shop's, both unused now that those caves are shops)."""
import sys
from lol_af import Asm, BANK, place, patch

CODE = 0x9ED4                                  # bank 1 free from $9ED4 (DemoBackgroundPatterns ends at $9ED3)
TEXT_AT = 0xBCA4
CAVE_WARES, CAVE_QUOTES = 0x18610, 0x45B2      # file offsets
QUOTE_PTRS = 0x4010                            # bank 1 $8000: a pointer per quote
WHITE_CAVE, MAGIC_CAVE = 2, 3
TEXTS = {5: ["DO YOU HAVE 4", "TRIFORCES YET?"],
         15: ["YOU CAN HAVE THESE ONCE", "YOU HAVE ALL 8 TRIFORCES"]}
CAVE_TEXT = {WHITE_CAVE: 5, MAGIC_CAVE: 15}
SILVER_ARROWS = 0x09


def apply(rom: bytearray, notes: list) -> None:
    import lolpaths
    for p in (lolpaths.ZORA, lolpaths.Q3B):
        if p not in sys.path:
            sys.path.insert(0, p)
    from zora.rom.serialize.text import _encode_quote
    import build_mock as base
    a = Asm(CODE)
    # triforce pieces (bits of $0671) >= 4 (cave 2's person $6C) or 8: carry set
    a.label("tri").abs(0xAD, 0x0671).b(0xA0, 0x00)
    a.label("t_lp").b(0xC9, 0x00).br(0xF0, "t_dn").b(0x0A).br(0x90, "t_lp").b(0xC8).br(0xD0, "t_lp")
    a.label("t_dn").abs(0xAD, 0x0350).b(0xC9, 0x6C).br(0xF0, "t_w").b(0xC0, 0x08, 0x60)
    a.label("t_w").b(0xC0, 0x04, 0x60)
    tx = Asm(TEXT_AT)                          # the two quotes (bank 1's common-area tail: free in every bank)
    for q, lines in TEXTS.items():
        tx.label(f"q{q}").b(*_encode_quote(base.centered(lines)))
    code = a.bytes()
    place(rom, 1, CODE, code)
    tcode = tx.bytes()
    assert TEXT_AT + len(tcode) <= 0xBD00
    place(rom, 1, TEXT_AT, tcode)
    t = a.labels["tri"]
    patch(rom, 1, 0x88FC, bytes.fromhex("a040ad5003c96cf002a0b0cc6f06f0039001"),
          bytes([0x20, t & 0xFF, t >> 8, 0xB0, 0x890F - 0x8901, 0x60]))
    for q in TEXTS:
        p = tx.labels[f"q{q}"]
        rom[QUOTE_PTRS + 2 * q:QUOTE_PTRS + 2 * q + 2] = bytes([p & 0xFF, p >> 8])
    for cave, q in CAVE_TEXT.items():
        rom[CAVE_QUOTES + cave] = (rom[CAVE_QUOTES + cave] & 0xC0) | (2 * q)
    w = CAVE_WARES + 3 * MAGIC_CAVE + 1
    assert rom[w] & 0x3F == 0x03 and rom[CAVE_WARES + 3 * WHITE_CAVE + 1] & 0x3F == 0x02
    rom[w] = (rom[w] & 0xC0) | SILVER_ARROWS
    notes.append(f"sword caves: white sword at 4 triforces, silver arrows at 8 ({len(code)} + {len(tcode)} bytes)")

"""Legend of Link: the title's version and seed, and the seed's code on the file-select screen (owner, 2026-11-24).

Title (bank 6's GameTitleTransferBuf: one 32-tile record a row): the two blank rows under "(c)1986 NINTENDO" read
LEGEND OF LINK / BETA <VERSION>, and the PUSH START BUTTON row the seed (SEED n, or NEW SEED EACH FILE without one).

File select: the heading (- S E L E C T -: one save file, nothing to select) reads CODE, followed by four vanilla
item icons: a hash of the finished ROM (everything the page's settings change), so two players with the same four
icons have the same game. Drawn as ZORA's FP-HASH-01 draws them: the menu's second step (bank 2 $A4BD: LDA #$14 /
STA TileBufSelector / INC GameSubmode / RTS) -> icons, drawing each item with DrawItemBySlot (bank 7 $E73A) into
OAM offsets the menu leaves alone, then Link's palette row kept and every other row made the cursor's (row 3).
apply_code runs last (lol_build): the hash is of the ROM with the four bytes still 0, and the sprite tiles (a custom
sprite ROM's pictures) left out."""
import hashlib
import os
from lol_af import Asm, BANK, place, patch

VERSION = "0.337"
TITLE_ROWS = {0x2240: "LEGEND OF LINK", 0x2260: "BETA " + VERSION}   # (24 free columns: 4-27)
SEED_ROW = 0x2280                     # PUSH START BUTTON's (22 free columns: 6-27)
HEADING = 0x1A128                     # file offset: the heading record's length byte (bank 6 $A118)
HOOK = 0xA4BD                         # bank 2
DRAW_ITEM = 0xE73A
SLOT_TABLE = 0x72A4                   # WRAM (bank 1's copy): ItemIdToSlot, then ItemIdToDescriptor ($24 each)
WRAM_DELTA = 0x3870
ICON_Y, ICON_X = 0x27, (0x68, 0x78, 0x88, 0x98)
# vanilla items with a picture of their own (ZORA's list: SEED_CODE_NAMES)
ITEMS = (0x00, 0x01, 0x03, 0x04, 0x05, 0x06, 0x08, 0x0A, 0x0B, 0x0C, 0x0D, 0x0F, 0x10, 0x11, 0x12, 0x14, 0x15, 0x16,
         0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1F, 0x21, 0x22, 0x23)
DOMAIN = b"Legend of Link seed code\x00"
# the sprite pattern blocks a custom-sprite ROM may change (file offsets: header included; the page's check is the
# same list): Link and the items, the overworld's and the dungeons' enemies, the bosses
SPRITE_BLOCKS = tuple((16 + o, n) for o, n in ((32895, 1792), (53595, 1824), (55419, 544), (55963, 544), (56507, 256),
                                               (56763, 544), (57307, 1024), (58331, 1024), (59355, 1024)))
# (owner 2026-11-25) Link's colors a player's ROM may change too (file offsets): the two copies of the three tunic
# colors (no ring, blue ring, red ring: LinkColors, LinkColors_CommonCode) and his colors 2 and 3 in the ten level
# palettes, the title story's and the file-select screen's three (ZORA's player_settings offsets)
TUNIC_COPIES = (41623, 27557)
LINK_COLOR_BYTES = tuple((o, 3) for o in TUNIC_COPIES) + tuple(
    (o, 2) for o in (103205, 103457, 103709, 103961, 104213, 104465, 104717, 104969, 105221, 105473, 38260,
                     105725, 105729, 105733))
# (owner 2026-11-25) the page's "Reduce flashing" (ZORA's FP-FIX-02 setting, PRG1 offsets): the bomb's grayscale
# (STA $FE), the Triforce of Power's flash (STY $14), the ending's flash colors, the level-end flash (STY $14)
FLASH_BYTES = ((0x06A5B, 2), (0x061A3, 2), (0x0AA2F, 4), (0x16895, 2))
FLASH_PATCH = ((bytes.fromhex("85fe"), bytes.fromhex("eaea")), (bytes.fromhex("8414"), bytes.fromhex("eaea")),
               (bytes.fromhex("0f12162a"), bytes.fromhex("0f0f0f0f")), (bytes.fromhex("8414"), bytes.fromhex("eaea")))
LINK_COLOR_VANILLA = bytes.fromhex("293216293216" + "2717" * 3 + "3717" + "2717" * 6 + "3717" + "2707" * 3)   # (PRG1's)


def vanilla_colors(rom: bytes) -> bytes:
    """The ROM with Link's colors as PRG1 has them (for the tools that identify the player's ROM)."""
    out, k = bytearray(rom), 0
    for o, n in LINK_COLOR_BYTES:
        out[o:o + n] = LINK_COLOR_VANILLA[k:k + n]
        k += n
    return bytes(out)


ICONS = []                            # after apply_code: [(name, 16 rows of 16 NES colors)] for the page
CODE_AT = None                        # (bank 2: the four icons' slot and value bytes)


def enc(s):
    return bytes(0x24 if c == " " else 0x2C if c == "." else (ord(c) - 48 if c.isdigit() else ord(c) - 55) for c in s)


def _row(rom, ppu):
    """The file offset of title row `ppu`'s 32 tiles."""
    lo, hi = BANK(6), BANK(6) + 0x4000
    key = bytes([ppu >> 8, ppu & 0xFF, 0x20])
    at = rom.find(key, 0x1A900, 0x1AD00)
    assert lo <= at < hi, hex(ppu)
    return at + 3


def _centre(rom, ppu, text, first, last):
    at = _row(rom, ppu)
    width = last - first + 1
    assert len(text) <= width, text
    col = first + (width - len(text)) // 2
    for c in range(first, last + 1):
        assert rom[at + c] in (0x24,) or ppu == SEED_ROW, (hex(ppu), c, hex(rom[at + c]))
        rom[at + c] = 0x24
    rom[at + col:at + col + len(text)] = enc(text)


def apply(rom: bytearray, notes: list) -> None:
    global CODE_AT
    # --- the title
    for ppu, text in TITLE_ROWS.items():
        _centre(rom, ppu, text, 4, 27)
    seed = os.environ.get("LOL_SEED")
    _centre(rom, SEED_ROW, f"SEED {seed}" if seed else "NEW SEED EACH FILE", 6, 27)
    # --- the file select's heading: CODE, then the icons
    h = HEADING
    assert rom[h - 2:h + 1] == bytes([0x20, 0xA8, 0x0F]) and rom[h + 1:h + 16] == bytes(
        [0x62, 0x24, 0x1C, 0x24, 0x0E, 0x24, 0x15, 0x24, 0x0E, 0x24, 0x0C, 0x24, 0x1D, 0x24, 0x62]), rom[h:h + 16].hex()
    rom[h + 1:h + 16] = enc("CODE") + bytes([0x24] * 11)

    def build(org):
        a = Asm(org)
        a.label("icons").b(0xA9, 0x14, 0x85, 0x14, 0xE6, 0x13, 0xA2, 0x03)
        a.label("i_lp").b(0x8A, 0x48).abs(0xBD, "xs").b(0x85, 0x00, 0xA9, ICON_Y, 0x85, 0x01)
        a.b(0x8A, 0x0A).abs(0x8D, 0x0341)                                   # RollingSpriteIndex: 2X
        a.abs(0xBD, "vals").b(0x85, 0x04).abs(0xBC, "slots").b(0x98, 0xAA)    # $04 the value; X = Y = the slot
        a.abs(0x20, DRAW_ITEM)
        a.b(0xA0, 0x01)
        a.label("i_row").abs(0xBE, 0x0343).abs(0xBD, 0x0202).b(0x29, 0x03).br(0xF0, "i_k")
        a.b(0xA9, 0x03).abs(0x1D, 0x0202).abs(0x9D, 0x0202)
        a.label("i_k").b(0x88).br(0x10, "i_row")
        a.b(0x68, 0xAA, 0xCA).br(0x10, "i_lp").b(0x60)
        a.label("xs").b(*ICON_X)
        a.label("slots").b(0, 0, 0, 0)
        a.label("vals").b(0, 0, 0, 0)
        return a
    from lol_newups import put
    a = put(rom, 2, build)
    i = a.labels["icons"]
    patch(rom, 2, HOOK, bytes([0xA9, 0x14, 0x85, 0x14, 0xE6, 0x13, 0x60]),
          bytes([0x4C, i & 0xFF, i >> 8, 0xEA, 0xEA, 0xEA, 0xEA]))
    CODE_AT = (BANK(2) + a.labels["slots"] - 0x8000, BANK(2) + a.labels["vals"] - 0x8000)
    notes.append(f"title: Legend of Link beta {VERSION}, seed {seed or 'none'}; file-select code (bank 2 ${i:04X})")


def apply_code(rom: bytearray, notes: list) -> None:
    """Last: the four icons, from a hash of the finished ROM."""
    s_at, v_at = CODE_AT
    assert not any(rom[s_at:s_at + 8])
    import lol_bombup
    plain = bytearray(rom)              # (custom sprites don't change the code: the same game, other pictures)
    for at, n in SPRITE_BLOCKS + tuple(lol_bombup.SPRITE_COPIES) + LINK_COLOR_BYTES + FLASH_BYTES:  # (and Link's
        # colors, and the flashes)
        plain[at:at + n] = bytes(n)
    digest = hashlib.sha256(DOMAIN + bytes(plain)).digest()
    items = [ITEMS[b % len(ITEMS)] for b in digest[:4]]
    tbl = BANK(1) + SLOT_TABLE + WRAM_DELTA - 0x8000
    for k, it in enumerate(items):
        desc = rom[tbl + 0x24 + it]
        rom[s_at + k] = rom[tbl + it]
        rom[v_at + k] = (0xFF if desc == 0x30 else desc) & 0x0F
    notes.append("seed code: " + " ".join(f"${x:02X}" for x in items))
    # the page shows them under its downloads: drawn as the file-select screen draws them, from this ROM's own
    # tiles, frame tables and menu palette (ZORA's seed_code_icons: custom sprites show as in the game)
    global ICONS
    from zora.rom.code_patches import SEED_CODE_NAMES
    from zora.rom.seed_code_icons import draw_item
    ICONS = [(SEED_CODE_NAMES[it], [list(r) for r in draw_item(bytes(rom), it)]) for it in items]

"""Legend of Link: the heart snubber (owner, 2026-11-24; was "attack over heart"), an upgrade (lol_uptable: 200
rupees, tier 3, only in the second upgrade cave Link finds, while he has 3 heart containers or fewer).

Once Link owns it:
- His level goes on in the background: the containers' nibble of HeartValues ($066F) still counts every level up (so
  the enemies' level ups, the odds' rows and everything else that reads it work as before), but he has at most 3
  hearts: lol_upgrades' frame hook (snub) cuts the hearts back to the containers or 3, whichever is fewer, every frame
  of play, and sets ForceSwordShot ($0529) while they're full (the game's own beam check wants all the containers).
- The sword's attack is at least half his level from level 4 on (2 at 4-5, 3 at 6-7 .. 8 at 16; lol_upgrades' sword).
- No sword is offered again: the old men and the shrines' rewards (lol_odds: a rolled sword's odds go evenly to the
  rest), the white sword cave (its next item), level 9's upgrade (lol_genload), and the sword upgrades (beams, sword
  mastery: lol_uptable's NO_SNUB).
- The status bar (this module): the heart row shows 3 containers at most; the top row, where hearts 9-16 would be,
  shows a sword for every 2 levels and a cross (the hilt) for an odd level (level 16: 8 swords).

The status bar's heart row (bank 1's WRAM code: LDA HeartValues / STA $0E / LDA $0670 / STA $0F / JSR $6E79 at
$6D0D, reached with bank 5 in: after its JSR to lol_build's status-bar code at $BE60, or from bank 5's JSR $6D00)
calls HEARTS here (bank 5) instead."""
from lol_af import Asm, BANK, place, patch

SITE = 0x6D0D                           # WRAM (bank 1 file cpu + $3870)
WRAM_DELTA = 0x3870
HEARTS_AT = 0xBD5E                      # bank 5 free (162 bytes)


SWORD_TILE = 0x60                       # the common background patterns' one blank tile nothing draws (checked:
HALF_TILE = 0x64                        # title, menu, play, item screen); the odd level's mark: the cross ($64)
                                        # (no second free tile: LoL's pictures fill $34-$5F)


def sword_tiles():
    """The sword (blade 3, hilt 2, in the heart row's palette)."""
    full = ["...3....", "..333...", "..333...", "..333...", "..333...", ".22222..", "...2....", "...2...."]

    def tile(rows):
        lo, hi = bytearray(8), bytearray(8)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                c = 0 if ch == "." else int(ch)
                lo[y] |= (c & 1) << (7 - x)
                hi[y] |= (c >> 1) << (7 - x)
        return bytes(lo + hi)
    return tile(full)


def apply(rom: bytearray, notes: list) -> None:
    import lol_bombup as B
    import lol_uptable as T
    snub = T.bit("heart snubber")
    at = B.BG_CHR + SWORD_TILE * 16
    assert not any(rom[at:at + 16])
    rom[at:at + 16] = sword_tiles()
    a = Asm(HEARTS_AT)
    a.label("hearts").abs(0xAD, 0x066F).b(0x85, 0x0E).abs(0xAD, 0x0670).b(0x85, 0x0F)
    a.abs(0xAD, snub[0]).b(0x29, snub[1]).br(0xD0, "h_s").abs(0x4C, 0x6E79)
    # 3 containers at most (and hearts no more than that), then the row; then the top row's swords
    a.label("h_s").b(0xA5, 0x0E, 0x4A, 0x4A, 0x4A, 0x4A, 0xC9, 0x02).br(0x90, "h_c").b(0xA9, 0x02)
    a.label("h_c").b(0x85, 0x01, 0x0A, 0x0A, 0x0A, 0x0A, 0x85, 0x00)
    a.b(0xA5, 0x0E, 0x29, 0x0F, 0xC5, 0x01).br(0x90, "h_h").b(0xA5, 0x01)
    a.label("h_h").b(0x05, 0x00, 0x85, 0x0E)
    a.b(0x84, 0x02).abs(0x20, 0x6E79)                                       # ($02: the row's place in the buffer)
    a.abs(0xAD, 0x066F).b(0x4A, 0x4A, 0x4A, 0x4A, 0x18, 0x69, 0x01, 0x85, 0x01)   # the level, 1-16
    a.b(0xA9, 0x01, 0x85, 0x00, 0xA2, 0x00)                                  # $00: 2i + 1
    a.label("h_l").b(0xA5, 0x01, 0x38, 0xE5, 0x00).br(0x90, "h_b").br(0xF0, "h_hf")
    a.b(0xA9, SWORD_TILE).br(0xD0, "h_p")
    a.label("h_hf").b(0xA9, HALF_TILE).br(0xD0, "h_p")
    a.label("h_b").b(0xA9, 0x24)
    a.label("h_p").b(0x48, 0x8A, 0x18, 0x65, 0x02, 0xA8, 0x68).abs(0x99, 0x0302)   # hearts 9-16: $0302 + row + i
    a.b(0xE6, 0x00, 0xE6, 0x00, 0xE8, 0xE0, 0x08).br(0xD0, "h_l")
    a.b(0xA4, 0x02)
    a.b(0x60)
    code = a.bytes()
    place(rom, 5, HEARTS_AT, code)
    old = bytes([0xAD, 0x6F, 0x06, 0x85, 0x0E, 0xAD, 0x70, 0x06, 0x85, 0x0F, 0x20, 0x79, 0x6E])
    patch(rom, 1, SITE + WRAM_DELTA, old, bytes([0x20, HEARTS_AT & 0xFF, HEARTS_AT >> 8]) + b"\xEA" * 10)
    notes.append(f"heart snubber: the heart row (bank 5 ${HEARTS_AT:04X}, {len(code)} bytes), sword tile "
                 f"${SWORD_TILE:02X}")

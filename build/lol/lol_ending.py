"""Legend of Link: the ending.

- Zelda's message after Ganon ("THANKS LINK,YOU'RE THE HERO OF HYRULE.") becomes the 3Q build's lines. Bank 2's
  routine ($A998) types from the address loaded by LDA #lo / LDA #hi at $A9B4 / $A9B8; a character's $80 bit ends
  line 1, $40 line 2, $C0 the text; $25 is a skipped blank (centring).
- The credits' last lines ("ANOTHER QUEST WILL START / FROM HERE. / PRESS THE START BUTTON.", records of
  [length][column][text] at bank 2 $AD33, each through a pointer) say the stats come next (lol_stats' end screen);
  the music stops once they show (FINAL_WAIT).
- Beating the game (bank 2 $AF5A: room flags and inventory cleared, which also clears lol_af's MARKER, so the next
  load clears the file's other memory - the A-F rooms, the odds bytes and upgrades, the dealt entrances and
  dungeons - as a new file's) no longer sets the second quest; it zeroes the file's death count instead."""
from lol_af import Asm, BANK, patch

ENDING_LINES = ["RANDOMIZE MY MIND INTO", "NOTHING. YOU KNOW I", "USED TO KNOW THIS PLACE."]   # the 3Q build's
# (owner 2026-11-25: say the stats come next; padded with blanks to the old lines' 57 characters, each centred)
_CL = ["YOUR LEGEND IS COMPLETE.", "PRESS START TO SEE", "YOUR STATS."]
_pad = 57 - sum(map(len, _CL))
_CL[2] = " " * (_pad // 2) + _CL[2] + " " * (_pad - _pad // 2)
CREDIT_LINES = [((32 - len(t)) // 2, t) for t in _CL]
FINAL_WAIT = 0xAB7F                      # bank 2: the credits' last step (the lines shown, waiting for Start):
                                         # JSR $E5F7 first; there the music stops (owner 2026-11-25)
SONG, SONG_NOW = 0x0600, 0x0609
FONT = {**{str(d): d for d in range(10)}, **{chr(65 + i): 10 + i for i in range(26)},
        " ": 0x24, ",": 0x28, "!": 0x29, "'": 0x2A, "&": 0x2B, ".": 0x2C, '"': 0x2D, "?": 0x2E, "-": 0x2F}
CLOSING_LINES = ["LATELY,", "EVERYTHING IS JUST", "A LITTLE BIT OUT OF PHASE"]   # the 3Q build's (52 chars max)
TEXT_AT = 0xA830                         # bank 2 free


def apply(rom: bytearray, notes: list) -> None:
    b2 = BANK(2) - 0x8000
    # Zelda's message
    lda = b2 + 0xA9B4
    assert rom[lda:lda + 2] == bytes([0xA9, 0x59]) and rom[lda + 4:lda + 6] == bytes([0xA9, 0xA9]), rom[lda:lda + 6].hex()
    assert len(ENDING_LINES) == 3 and all(len(t) <= 24 for t in ENDING_LINES)
    text = bytearray()
    for k, line in enumerate(ENDING_LINES):
        enc = bytearray([0x25] * ((24 - len(line)) // 2) + [FONT[c] for c in line])
        enc[-1] |= (0x80, 0x40, 0xC0)[k]
        text += enc
    at = b2 + TEXT_AT
    assert all(x == 0xFF for x in rom[at:at + len(text)])
    rom[at:at + len(text)] = text
    rom[lda + 1], rom[lda + 5] = TEXT_AT & 0xFF, TEXT_AT >> 8
    # the credits' last lines (the same bytes in all)
    cr = b2 + 0xAD33
    old = [(4, "ANOTHER QUEST WILL START"), (11, "FROM HERE."), (5, "PRESS THE START BUTTON.")]
    enc = lambda lines: b"".join(bytes([len(t), col]) + bytes(FONT[c] for c in t) for col, t in lines)
    assert rom[cr:cr + len(enc(old))] == enc(old), rom[cr:cr + 8].hex()
    new = enc(CREDIT_LINES)
    assert len(new) == len(enc(old)), (len(new), len(enc(old)))
    rom[cr:cr + len(new)] = new
    # each line's record is found through a pointer (low bytes at $AC3A.., all on page $AD): lines 2 and 3 move
    lo = b2 + 0xAC3A
    assert rom[lo:lo + 4] == bytes([0x33, 0x4D, 0x59, 0x72]), rom[lo:lo + 4].hex()
    start = 0x33
    for k, (col, t) in enumerate(CREDIT_LINES):
        rom[lo + k] = start
        start += 2 + len(t)
    assert start == 0x72
    # The closing text after Zelda ("FINALLY, / PEACE RETURNS TO HYRULE. / THIS ENDS THE STORY."): bank 2 types
    # $AB07,Y (to $FF) at PPU low byte $AAD3,Y (high $22, or $23 below $A0), 52 slots each. Rows 21, 23, 26, centred.
    pos_at, txt_at = b2 + 0xAAD3, b2 + 0xAB07
    assert rom[txt_at:txt_at + 8] == bytes(FONT[c] for c in "FINALLY,") and rom[txt_at + 52] == 0xFF
    text, pos = bytearray(), bytearray()
    for row, line in zip((21, 23, 26), CLOSING_LINES):
        col = (32 - len(line)) // 2
        for k, c in enumerate(line):
            text.append(FONT[c]); pos.append((0x2000 + row * 32 + col + k) & 0xFF)
    assert len(text) <= 52, len(text)
    rom[pos_at:pos_at + len(pos)] = pos
    rom[txt_at:txt_at + len(text) + 1] = text + b"\xFF"
    # the music stops once PRESS START shows (the end screen after it runs silent): the last step's first call
    # (JSR $E5F7) goes through hush - the song request and the playing song cleared, the channels cut ($4015)
    from lol_newups import put

    def b_hush(org):
        a = Asm(org)
        a.label("hush").abs(0xAD, SONG_NOW).br(0xF0, "h_go")
        a.b(0xA9, 0x00).abs(0x8D, SONG).abs(0x8D, SONG_NOW).abs(0x8D, 0x4015).b(0xA9, 0x0F).abs(0x8D, 0x4015)
        a.label("h_go").abs(0x4C, 0xE5F7)
        return a
    h = put(rom, 2, b_hush).labels["hush"]
    patch(rom, 2, FINAL_WAIT, bytes([0x20, 0xF7, 0xE5]), bytes([0x20, h & 0xFF, h >> 8]))
    # the end: no second quest; deaths back to 0 (LDY $16 / LDA #1 / STA QuestNumbers,Y)
    patch(rom, 2, 0xAF88, bytes.fromhex("a416a901992d06"), bytes.fromhex("a416a900993006"))
    notes.append("ending: Zelda says " + " / ".join(ENDING_LINES) + "; then " + " / ".join(CLOSING_LINES) + "; credits: " +
                 " / ".join(t.strip() for _, t in CREDIT_LINES) + "; beating the game starts the file over")

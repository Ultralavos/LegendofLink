"""Legend of Link v3.0 stage 4: the file's save map, in one place.

The game keeps one file (files 2 and 3 are hidden: their save RAM holds the generated dungeons' memory). Two kinds of
per-file data:

Saved with the file (the game's own rule: progress since the last save is undone by a reset or power-off). Each has
a working copy the game uses and a saved copy; the file's load copies saved -> working (a new file clears both),
its save (the menu's and the autosave's) copies working -> saved. SEGMENTS lists them (working, saved, length):
  grid 2's room memory   working $6392  saved $6412            (A-F's LIVE / store before)
  grid 3's               working $6492  saved $6212            (stage 4: was never saved or cleared)
  grid 4's second group  working $6292  saved $6342 / $6042 / $7FEE in three pieces   (stage 4: likewise)
  (grid 1 and grid 4's first group are the game's own level memory, $077F / $06FF: saved by the game itself.)

Kept at once (written straight to save RAM; cleared for a new file):
  $606A  20   lol_odds: the rolls' bytes; byte 17 the seed, 18 the ranks, 19 upgrades UP3
  $7F00  72   lol_entrances: the dealt entrances          $7F48 72  the hint quotes (lol_genload HINT_QS)
  $7F90  16   the whirlwind's tables                       $7FA0 13  the entrances' scratch and RNG
  $7FAD  65   lol_genload: the generated levels' records
  VERSION ($7FF6): 1 once this file has stage 4's saved copies. A file from before (no copies yet) takes its
  working memory as saved on its first load.
Free for later: $607E-$6091 (20), $7FF7-$7FFF (9).
Moved for room: the hint text buffer to $6BFA (the overworld level info's palette cycles; test12 had it at $67F0, which is
bank 6's data in RAM - the overworld column directory: fixed in test13), the
potion pictures' code (lol_pictures POT_W / POUCH_W) from WRAM to bank 7."""
from lol_af import Asm

SEGMENTS = [(0x6392, 0x6412, 0x80),          # grid 2
            (0x6492, 0x6212, 0x80),          # grid 3
            (0x6292, 0x6342, 0x50),          # grid 4's second group, in three pieces
            (0x62E2, 0x6042, 0x28),
            (0x630A, 0x7FEE, 0x08)]
VERSION, VERSION_VALUE = 0x7FF6, 0x01
HINT_BUF = 0x6BFA                       # (the overworld level info's palette cycles: dark-room fades only, never
                                        #  used on the overworld; a level load rewrites them)
assert sum(n for _, _, n in SEGMENTS[2:]) == 0x80


def emit_copy(a: Asm, to_saved: bool, segs=None) -> None:
    """Every segment copied, working -> saved (a save) or saved -> working (a load). A, Y used."""
    for w, s, n in (segs or SEGMENTS):
        src, dst = (w, s) if to_saved else (s, w)
        lb = f"cp{len(a.code)}"
        a.b(0xA0, n - 1).label(lb).abs(0xB9, src).abs(0x99, dst).b(0x88).br(0x10, lb)


def emit_clear_saved(a: Asm) -> None:
    """A new file: every saved copy cleared (the load then copies them to the working ones), the version set."""
    a.b(0xA9, 0x00)
    for w, s, n in SEGMENTS:
        lb = f"cl{len(a.code)}"
        a.b(0xA0, n - 1).label(lb).abs(0x99, s).b(0x88).br(0x10, lb)
    a.b(0xA9, VERSION_VALUE).abs(0x8D, VERSION)


def emit_migrate(a: Asm) -> None:
    """A file saved before stage 4: grids 3 and 4's working memory (kept at once before) becomes the saved copy,
    then the version is set. (Grid 2 had its saved copy already.)"""
    lb = f"mg{len(a.code)}"
    a.abs(0xAD, VERSION).b(0xC9, VERSION_VALUE).br(0xF0, lb)
    emit_copy(a, True, SEGMENTS[1:])
    a.b(0xA9, VERSION_VALUE).abs(0x8D, VERSION)
    a.label(lb)


ROUTINES = {}


def install(rom: bytearray) -> dict:
    """The four routines in bank 0 (lol_v3core put0), far-called by lol_af's load and save: clear (a new file),
    migrate, to_work (a load), to_saved (a save). Each ends in RTS; A and Y are used."""
    if ROUTINES:
        return ROUTINES
    import lol_v3core as V
    for name, body in (("clear", emit_clear_saved), ("migrate", emit_migrate),
                       ("to_work", lambda a: emit_copy(a, False)), ("to_saved", lambda a: emit_copy(a, True))):
        def build(org, body=body):
            a = Asm(org)
            body(a)
            return a.b(0x60)
        ROUTINES[name] = V.put0(rom, build).cpu
    return ROUTINES

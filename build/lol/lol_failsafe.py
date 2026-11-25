"""Legend of Link: the hard-lock fail-safe (owner, 2026-11-25; an approximate detector).

Blocker items (bits): candle 1, power bracelet 2, recorder 4, raft 8, ladder $10, bow $20, arrows $40 (bombs can be
farmed: never a blocker). The build writes, for each of the 71 entrances, what reaching it takes (its screen's
secret: a burnable bush the candle, a rock the bracelet, a recorder spot the recorder; ZORA's raft and ladder
screens), and for each level 1-8 what finishing it may take (Gohma: bow and arrows; Digdogger: the recorder; any moat
room: the ladder). Entering an entrance marks its screen visited (overworld room flag $40, unused there).

STUCK (bank 3, far-called): Link is stuck when no entrance he can reach with his items still offers anything:
  - a level 1-8 whose triforce he lacks (and whose needs he meets),
  - a shop not bought out (shops change as he levels up: one counts until he's bought there),
  - the white sword cave with 4 triforces / the 8-triforce cave with 8, not taken yet,
  - any other entrance he hasn't been in,
and some entrance or level needs an item he lacks. Then (C set) A = the first such item in the owner's order:
ladder, bow, arrows, recorder, raft, bracelet, candle.

While stuck: every old man's cave says "YOU AREN'T HARD LOCKED, GO BACK TO WHERE YOU STARTED", and the wood sword
cave (H8) becomes the door-repair cave (an old man, a shop's flags): that item for 100 rupees. Buying it flags H8's
item taken; the next time Link is stuck that's cleared again."""
from lol_af import Asm

OW = 0x18410
STORE = 0x7F00
OWN, NEED, DST, TRIC = 0x7FA2, 0x7FA3, 0x7FA4, 0x7FA5      # (lol_entrances' scratch: free while this runs)
WORLD_FLAGS = 0x6BAF
VISITED = 0x40
H8 = 0x77
WOOD_DEST, HELP_DEST = 0x10, 0x17                         # the wood sword cave; the door-repair cave (unused now)
PRICE = 100
# (bit, inventory byte, item) in the owner's order
ORDER = [(0x10, 0x0663, 0x0D), (0x20, 0x065A, 0x0A), (0x40, 0x0659, 0x08), (0x04, 0x065C, 0x05),
         (0x08, 0x0660, 0x0C), (0x02, 0x0665, 0x14), (0x01, 0x065B, 0x07)]
RAFT_SCREENS, LADDER_SCREENS = (0x2F, 0x45), (0x5F, 0x18, 0x19)
GOHMA, DIGDOGGER = (0x33, 0x34), (0x38, 0x39)
SHOPS = (0x1D, 0x1E, 0x1F, 0x20)
TEXT = ["YOU AREN'T HARD LOCKED", "GO BACK TO WHERE", "YOU STARTED"]
HELP_TEXT = ["THIS WILL GET YOU", "UNSTUCK. 100 RUPEES"]
OLD_MEN = (0x6B, 0x6C, 0x6D, 0x6E, 0x6F, 0x70, 0x72, 0x73, 0x75, 0x76)   # (the caves' persons: not shopkeepers)


def tables(rom):
    """(the entrances' screens, their needs, the levels' needs by number 0-9)."""
    import sys
    import lolpaths
    if lolpaths.ZORA not in sys.path:
        sys.path.insert(0, lolpaths.ZORA)
    from zora.rom.vanilla_overworld import layouts as L
    from zora.rom.vanilla_overworld.tables import ROOM_LAYOUTS_OW
    import lol_entrances as E
    import lol_gen
    import lol_fixed
    import lol_genload as GL
    name = lambda x: "ABCDEFGH"[x // 16] + str(x % 16 + 1)
    ents = [x for x in range(128) if rom[OW + 0x80 + x] >> 2 and rom[OW + 0x280 + x] >> 6 != 2
            and rom[OW + 0x80 + x] >> 2 != 0x14 and name(x) not in E.EXCLUDED]
    assert len(ents) == 71
    ta = bytes(rom).index(ROOM_LAYOUTS_OW.read(rom))
    heaps = L._heap_starts(rom)
    fl = rom.find(bytes.fromhex("42580629"), 16 + 7 * 0x4000)   # (lol_moves: the first two reveal: E3, F9)
    recorder = set(rom[fl:fl + 2]) if fl > 0 else {0x42, 0x58}
    req = []
    for s in ents:
        code = rom[OW + 0x180 + s] & 0x7F
        sq = set()
        for c in range(16):
            col = rom[ta + code * 16 + c]
            sq |= set(L._column(rom, heaps[col >> 4], col & 15))
        r = 0
        if 0x28 in sq:
            r |= 0x01
        if 0x26 in sq:
            r |= 0x02
        if s in recorder:
            r |= 0x04
        if s in RAFT_SCREENS:
            r |= 0x08
        if s in LADDER_SCREENS:
            r |= 0x10
        req.append(r)
    lvl = [0] * 10
    if lol_fixed.FIXED:
        ds, out = GL.build_variants()
        for i, rec in enumerate(lol_fixed.records()[:8]):
            d, v, boss = rec[0] - 1, rec[1] & 3, rec[2]
            n = 0
            if boss in GOHMA:
                n |= 0x60
            if boss in DIGDOGGER:
                n |= 0x04
            cells = out[(d, GL.SLOT_CLASS[i + 1])][v]["cells"]
            if any((c.get("layout", 0) & 0x3F) in lol_gen.MOATS for c in cells.values()):
                n |= 0x10
            lvl[i + 1] = n
    return ents, req, lvl


def emit(a: Asm, rom):
    """NOT BUILT YET (parked 2026-11-25: the owner wants it as a backup, off the live build, until hard locks are
    reported). The plan, to finish it:
      - VISIT (bank 3): OW room flag |= VISITED for $EB; called first from lol_heavy.entry_code (made always-present).
      - STUCK (bank 3): OWN from the ORDER inventory bytes; for each entrance X: d = STORE[X], needs = ereq[X]
        (| lreq[d] for an unfinished level 1-8); missing = needs & ~OWN -> NEED |= missing; else not stuck if the
        level lacks its triforce, a shop ($1D-$20) lacks taken $10, the $12 cave (4+ triforces) / $13 (8) isn't
        taken, or the screen isn't VISITED. Stuck when NEED != 0: C set, A = the first ORDER item in NEED.
      - entry_code: at H8, stuck -> ATTR_B dest HELP_DEST and clear H8's $10; else restore WOOD_DEST.
      - lol_heavy caves() fill: stuck at H8 -> wares [$3F, item, $3F], flags ($00, $00, $C0), price PRICE, quote
        HELP_TEXT (QOVR; maybe rom[0x45B2 + 7] = $C0 | quote); stuck with person $0350 in OLD_MEN -> TEXT.
      - Test: set every entrance screen VISITED and the triforces, take the ladder/bow, then check the old men's
        text and the H8 offer in the emulator."""
    raise NotImplementedError("lol_failsafe is parked (see the docstring)")

"""Legend of Link: the bomb upgrade as an item (code $24): +4 bombs carried (up to 20) and the bag filled.

Its picture is the bomb with a plus at the lower right, in the background table's free tiles $32/$33 (blank in the
overworld and the dungeons), drawn as sprite tile $33 (bit 0: the $1000 table) with the bombs' palette.

  DrawItem (bank 7 $E71D: TAX / LDA ItemIdToDescriptor,X): item $24 is drawn as the bombs (item 0) with FLAG set;
  the frame's tile lookup (WRAM $793D: LDA Anim_ItemFrameTiles,Y / STA $02) gives $33 while FLAG is set (and clears it);
  TakeItem (WRAM $7391: TAX / LDA ItemIdToSlot,X): item $24 raises the most bombs by 4 (to 20) and fills them.
"""
from lol_af import Asm, BANK, place, patch

BOMB_UP = 0x24
FLAG = 0x0171                              # (RAM: the stack page's unused bottom) which new item DrawItem draws
BADGES = 0x0673                            # saved (an inventory byte the game never uses): S / D / X badges, 2 bits each
# ($067F is not free: it is the overworld room flags' start, screen A1)
XP = 0x0677
BADGE_S, BADGE_D, BADGE_X, XP_ORANGE, XP_BLUE = 0x26, 0x27, 0x28, 0x29, 0x2A
COMMON = 0xBBA0                            # free in every switchable bank (bank 1's code ends before)
MAX_BOMBS, BOMBS = 0x067C, 0x0658
TILE = 0x33
PICTURE = ("..1111..",
           ".122111.",
           "12321111",
           "12211111",
           "11111111",
           "11111131",
           ".1111333",
           "..11113.")
BG_CHR = 16 + 0x0877F                      # CommonBackgroundPatterns tile 0 (file)
SPR_CHR = 0x808F                           # CommonSpritePatterns tile 0 (file)
N_FLAGS = 0x39 - 0x26 + 1                 # $26-$39
WLW, WRW = 0x6312 - 3, 0x6312 + N_FLAGS - 3    # WRAM (file 2's old area): the 16x16 items' halves by FLAG ($26 = 3 .. $36)
PTILE, PPAL = WLW + 3 + 2 * N_FLAGS, WLW + 3 + 2 * N_FLAGS + 4   # WRAM: the potion's tile / palette by its count 1-4
POT_W = POUCH_W = None                  # bank 7 (stage 4; lol_pictures writes them): the frame tile lookup's potion
POT_LEN, POUCH_LEN = 0x28, 0x38           # case; TakeItem's potions with the pouch (and the key hoarder)
WRAM_DELTA = 0x3870                        # bank 1 $A500-$B76F runs from WRAM $6C90 (cpu - $3870)


def tile_bytes(rows):
    lo, hi = bytearray(8), bytearray(8)
    for y, row in enumerate(rows):
        for x, px in enumerate(row):
            c = 0 if px == "." else int(px)
            lo[y] |= (c & 1) << (7 - x); hi[y] |= (c >> 1) << (7 - x)
    return bytes(lo + hi)


def _badge(letter):
    L = ["........", "......11", ".....111", "....1111", "...11111", "..111111", ".1111111", ".1111111",
         "....1111", "....1111", "....1111", "....1111", "....1111", "....1111", "....1111", "....1111"]
    shape = [[ch == "1" for ch in row + row[::-1]] for row in L]
    LET = {"S": ["111", "1..", "111", "..1", "111"], "D": ["11.", "1.1", "1.1", "1.1", "11."],
           "X": ["1.1", "1.1", ".1.", "1.1", "1.1"]}
    inside = lambda x, y: 0 <= x < 16 and 0 <= y < 16 and shape[y][x]
    g = [[0] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            if inside(x, y):
                edge = not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                g[y][x] = 1 if edge else 2
    for y in range(16):
        for x in range(16):
            if g[y][x] == 2 and (g[y][x - 1] == 1 or g[y - 1][x] == 1) and x < 8:
                g[y][x] = 3
    for y, row in enumerate(LET[letter]):
        for x, ch in enumerate(row):
            if ch == "1":
                g[9 + y][8 + x] = 3
    return g


def _xp_potion():
    spans = {0: (6, 9), 1: (6, 9), 2: (7, 8), 3: (6, 9), 4: (5, 10), 5: (4, 11), 6: (3, 12),
             **{y: (2, 13) for y in range(7, 14)}, 14: (3, 12), 15: (4, 11)}
    inside = lambda x, y: y in spans and spans[y][0] <= x <= spans[y][1]
    g = [[0] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            if inside(x, y):
                edge = not all(inside(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                g[y][x] = 1 if edge or y <= 1 else 2
    g[0][7] = g[0][8] = 3
    for y, x in ((4, 6), (5, 5), (6, 4), (7, 3), (8, 3), (9, 3), (3, 7)):
        g[y][x] = 3
    X = ["1.1", "1.1", ".1.", "1.1", "1.1"]; P = ["111", "1.1", "111", "1..", "1.."]
    for y in range(5):
        for x in range(3):
            if X[y][x] == "1": g[8 + y][5 + x] = 1
            if P[y][x] == "1": g[8 + y][9 + x] = 1
    return g


def _grid(rows):
    return [[0 if ch == "." else int(ch) for ch in row] for row in rows]


def _beam_sword():      # the sword with an infinity sign across the blade
    return _grid(["........1.......",
                  ".......131......",
                  ".......131......",
                  "..222..131..222.",
                  ".2...2.131.2...2",
                  ".2....2232.....2",
                  ".2.....2322....2",
                  ".2...2.131.2...2",
                  "..222..131..222.",
                  ".......131......",
                  ".......131......",
                  "....11111111....",
                  "....13333331....",
                  "....11122111....",
                  "......1221......",
                  ".......11......."])


def _boomstick():       # the wand (its left half is the game's own wand, sprite pair $4A) and a lit bomb at its tip
    return _grid(["..............3.",
                  ".............3..",
                  "...........1131.",
                  "..........122111",
                  ".........1221111",
                  ".........1211111",
                  ".........1111111",
                  "..........11111.",
                  "...........111..",
                  "................",
                  "................",
                  "................",
                  "................",
                  "................",
                  "................",
                  "................"])


def _regen():           # a heart with an arrow rising beside it (its tail broken in dashes)
    return _grid(["............3...",
                  "...........333..",
                  "..........33333.",
                  ".11..11..3333333",
                  "1311111.....3...",
                  "13111111....3...",
                  "11111111....3...",
                  "11111111....3...",
                  ".1111111........",
                  "..111111....3...",
                  "...1111.....3...",
                  "....11..........",
                  "............3...",
                  "............3...",
                  "................",
                  "............3..."])

def _skull_ring():      # a ring with a skull on top
    return _grid(["....111111......",
                  "...13333331.....",
                  "..1333333331....",
                  "..1311331131....",
                  "..1311331131....",
                  "..1333113331....",
                  "...13333331.....",
                  "....131131......",
                  "...1222222......",
                  "..12.....21.....",
                  ".12.......21....",
                  ".12.......21....",
                  ".12.......21....",
                  "..12.....21.....",
                  "...1222221......",
                  "................"])


def _sword_plus():      # the sword with a plus
    return _grid(["....1...........",
                  "...131..........",
                  "...131..........",
                  "...131......2...",
                  "...131......2...",
                  "...131....22222.",
                  "...131......2...",
                  "...131......2...",
                  "...131..........",
                  "...131..........",
                  "11111111........",
                  "13333331........",
                  "11122111........",
                  "..1221..........",
                  "..1221..........",
                  "...11..........."])


def _fairy_bottle():    # a fairy in a bottle
    return _grid(["......3333......",
                  "......2332......",
                  "......2..2......",
                  ".....2....2.....",
                  "....2......2....",
                  "...2..3..3..2...",
                  "..2..333333..2..",
                  "..2.33.33.33.2..",
                  "..2..3.33.3..2..",
                  "..2....33....2..",
                  "..2...3..3...2..",
                  "..2..........2..",
                  "..2..........2..",
                  "...2........2...",
                  "....22222222....",
                  "................"])


LL_ROWS = ["....OOOOOOOO....", "..OORRRRRRRROO..", ".ORRRRRRRRRRRRO.", "OORRRRRRRRRRRROO",
           "OOORRRRRRRRRROOO", "OOWOOOOWOWOOOWOO", "OOWOOOOOOOOOOWOO", ".OOORROOOORROOW.",
           "ORRROORRRROORWWO", "OOWOOOWOOWOOWWOO", "ROWOORRRRRRBBBOR", "ORRRROWOOWBBBBBO",
           ".OWO..OOOOBBBBB.", "..........BBBBB.", "...........BBB..", "................"]
import os
LL_VARIANT = os.environ.get("LL_VARIANT", "b")   # a: red palette, the bomb white with a red outline; b: blue palette


def _likelike_bomb():   # the user's like-like with a bomb
    rows = [list(r) for r in LL_ROWS]
    bomb = {(y, x) for y in range(16) for x in range(16) if rows[y][x] == "B"}
    if LL_VARIANT == "a":       # orange 2, red 1, white 3; the bomb's edge red, its inside white
        for y, x in bomb:
            edge = any((y + dy, x + dx) not in bomb for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            rows[y][x] = "R" if edge else "W"
    else:                       # blue palette: orange periwinkle 2, red dark blue 1, white 3, the bomb dark blue
        for y, x in bomb:
            rows[y][x] = "R"
    m = {"O": "2", "R": "1", "W": "3"}
    return _grid(["".join(m.get(c, ".") for c in r) for r in rows])


def _rupee_speed():   # the user's rupee with a speed arrow (blue palette: blue 2, white 3, gray dark blue)
    return _grid([".......32.......",
                  "......3322......",
                  ".....333222.....",
                  "....32321212....",
                  "....33222122....",
                  "....33222122....",
                  "....33222122....",
                  "....33222122....",
                  "....33222122....",
                  "....33222122....",
                  "....33222122.3..",
                  "....32322122.33.",
                  ".3.3232333333333",
                  ".3.3.32333333333",
                  "......2222...33.",
                  ".......22....3.."])


def _ganon_boomerang():   # the user's Ganon with a boomerang (blue palette: cyan 2, light cyan 3, red dark blue; the orange boomerang white)
    return _grid(["2...111111...2..",
                  "22211111111222..",
                  "22221222212222..",
                  "22222233222222..",
                  ".221123321122...",
                  "..2111221112....",
                  "..2231111322....",
                  ".222223322222...",
                  ".22223333222233.",
                  "22223133132233..",
                  "22223133132332..",
                  "22223311333322..",
                  "22222111123322..",
                  ".222211112233...",
                  ".....2112...33..",
                  ".....2222....33."])
def _critter_crusher():   # a boot about to stamp on a keese below it (red: red 1, orange 2, white 3)
    return _grid(["...1111111......",
                  "...1333331......",
                  "...1222331......",
                  "...1222221......",
                  "...1222331......",
                  "...12222221111..",
                  "...1222222222221",
                  "...1222222222221",
                  "...1111111111111",
                  "...111......111.",
                  "................",
                  "11............11",
                  "121...1111...121",
                  ".12211311311221.",
                  "..1.1.1111.1.1..",
                  "......1..1......"])


def _statue_jammer():     # a statue's face with a plug in its mouth (blue palette: dark 1, blue 2, white 3)
    return _grid(["...1111111111...",
                  "..122222222221..",
                  ".12222222222221.",
                  ".12111222211121.",
                  ".12131222213121.",
                  ".12222222222221.",
                  ".12222111122221.",
                  ".12222222222221.",
                  ".12211111111221.",
                  ".1221333333333..",
                  ".1221333333333..",
                  ".12211111111221.",
                  ".12222222222221.",
                  ".12222222222221.",
                  ".11111111111111.",
                  "................"])


def _bombsmith():         # a bomb with a keyhole (blue palette)
    return _grid(["...........3.3..",
                  "............3...",
                  "...........1.3..",
                  "..........1.....",
                  ".....111111.....",
                  "...1122222211...",
                  "..123322222221..",
                  "..123222112221..",
                  ".12222211112221.",
                  ".12222211112221.",
                  ".12222221122221.",
                  ".12222211112221.",
                  "..122221111221..",
                  "..122222222221..",
                  "...1122222211...",
                  ".....111111....."])


# the potions (8x16, a sprite pair): the game's is liquid 1, outline 3, cork / shine 2
POTION = ["..2222..", "...11...", "..3333..", "..3113..", "..3..3..", "..3..3..", ".33..33.", "3......3",
          "3......3", "31111113", "31111123", "31211113", "31112113", "33111133", "33333333", ".333333."]
BAT_CUT = {(9, 1), (9, 6), (10, 1), (10, 2), (10, 5), (10, 6), (11, 1), (11, 2), (11, 3), (11, 4), (11, 5), (11, 6),
           (12, 2), (12, 5)}                          # the bat: see-through (black on the item screen)
BAT = ["1......1", "11....11", "111..111", "11311311", ".111111.", "..1..1..", "........", "........",
       "........", "........", "........", "........", "........", "........", "........", "........"]


def potion_rows(liquid, bat):
    """liquid: 'blue' (the game's: blue / red by palette), 'orange' (red palette: liquid 2), 'white' (blue palette:
    liquid 3, outline 1)."""
    m = {"blue": {}, "orange": {"1": "2", "2": "1"}, "white": {"1": "3", "3": "1"}}[liquid]
    rows = ["".join(m.get(c, c) for c in r) for r in POTION]
    if bat:
        rows = ["".join("." if (y, x) in BAT_CUT else c for x, c in enumerate(r)) for y, r in enumerate(rows)]
    return rows


def pair_bytes(rows):
    return tile_bytes(rows[:8]) + tile_bytes(rows[8:])


def _pouch():             # a pouch (left) and a white potion (right): blue palette
    left = ["........", "........", "...11...", "..1221..", "...11...", "..1221..", ".122221.", "12222221",
            "12232221", "12322221", "12222221", "12222221", "12222221", ".122221.", "..1111..", "........"]
    right = potion_rows("white", False)
    return [[0 if c == "." else int(c) for c in l + r] for l, r in zip(left, right)]


def _bat_potion():        # the bat potion (left) and a bat (right): red palette
    left = potion_rows("blue", True)
    right = ["........"] * 4 + BAT[:12]
    return [[0 if c == "." else int(c) for c in l + r] for l, r in zip(left, right)]


def _piercing():          # an arrow through a block (blue palette)
    return _grid(["................",
                  "................",
                  "...........1111.",
                  "...........1221.",
                  "...........1221.",
                  "3..........1221.",
                  "33.........1221.",
                  "3333333333333333",
                  "33.........1221.",
                  "3..........1221.",
                  "...........1221.",
                  "...........1221.",
                  "...........1111.",
                  "................",
                  "................",
                  "................"])


# code: (name, picture); the palette comes from the item they're drawn as (CONV, from $24 on). The upgrades'
# pictures come from lol_uptable (by index; the first POWER_ON of them in the power-on tiles, for the title's legend)
NEW_ITEMS = {0x26: ("S badge", lambda: _badge("S")), 0x27: ("D badge", lambda: _badge("D")),
             0x28: ("X badge", lambda: _badge("X")), 0x29: ("XP potion +15", _xp_potion),
             0x2A: ("XP potion +25", _xp_potion)}
# drawn as: $24 bombs (blue), $25 the book, S the bow (Link's palette), D bombs (blue), X / orange XP the recorder
# (red), blue XP bombs (blue); $2B-$30 the upgrade slots: SCONV (RAM, set with their pictures)
CONV = (0x00, 0x11, 0x0A, 0x00, 0x05, 0x05, 0x00)
SLOT_CONV = (len(CONV), len(CONV) + 6)       # the draw's X range read from SCONV


def apply(rom: bytearray, notes: list) -> None:
    global POT_W, POUCH_W
    import lol_v3core as V3
    POT_W, POUCH_W = V3.alloc7(POT_LEN), V3.alloc7(POUCH_LEN)
    # the picture: the bomb's top tile as it is, the bottom one with the plus
    top = rom[SPR_CHR + 0x34 * 16:SPR_CHR + 0x35 * 16]
    bottom_rows = ["".join(".123"[((top[y] >> (7 - x)) & 1) | (((top[8 + y] >> (7 - x)) & 1) << 1)] for x in range(8))
                   for y in range(8)]
    # top tile: the fuse (rows 0-5) and the first two rows of the bomb (6-7); bottom: the rest with the plus
    top_rows = bottom_rows[:6] + list(PICTURE[0:2])
    bot_rows = list(PICTURE[2:8]) + ["........", "........"]
    for t, rows in ((TILE - 1, top_rows), (TILE, bot_rows)):
        at = BG_CHR + t * 16
        assert not any(rom[at:at + 16]), hex(t)
        rom[at:at + 16] = tile_bytes(rows)

    # the new items' pictures (16x16: a left and a right 8x16 half). Each half is a tile pair: background pairs
    # from $34 to $5F, then $AA/$AB, then the sprite table's blank $1C/$1D; identical halves share a pair (the badges'
    # left halves, the two XP potions)
    tiles = {}
    pool = [("bg", t) for t in range(0x34, 0x60, 2)]      # (not sprite $1C: dungeons use it as a blank mask)     # (not $AA: areas load their own there)
    seen_half = {}
    global HALVES, UP_PAIRS
    HALVES = {}                         # upgrade index: per half, ("fixed", sprite tile) or ("data", 32 bytes)
    UP_PAIRS = []                       # the pool pairs the power-on upgrade pictures take (the loaded ones' room)
    import lol_uptable as T
    pictures = [(code, NEW_ITEMS[code][1], {}, False) for code in NEW_ITEMS]
    import lol_icons2
    pic = lambda n: globals().get(n) or getattr(lol_icons2, n)
    pictures += [(("up", k), pic(T.ROWS[k][T.PIC]), T.ROWS[k][T.FIXED], k >= T.POWER_ON) for k in range(T.N_UP)]
    for code, fn, fixed, dynamic in pictures:
        g = fn()
        up = isinstance(code, tuple)
        halves = []
        for x0 in (0, 8):
            if x0 in fixed:
                halves.append(fixed[x0])
                if up:
                    HALVES.setdefault(code[1], []).append(("fixed", fixed[x0]))
                continue
            data = b"".join(tile_bytes(["".join(".123"[g[y0 + y][x0 + x]] for x in range(8)) for y in range(8)])
                            for y0 in (0, 8))
            if up:
                HALVES.setdefault(code[1], []).append(("data", data))
            if dynamic:
                halves.append(0)
                continue
            if data not in seen_half:
                while True:
                    kind, t = pool.pop(0)
                    chr_at = (BG_CHR if kind == "bg" else SPR_CHR) + t * 16
                    if not any(rom[chr_at:chr_at + 32]):
                        break
                rom[chr_at:chr_at + 32] = data
                seen_half[data] = t + 1 if kind == "bg" else t      # the sprite tile byte (bit 0: the $1000 table)
                if up:
                    assert kind == "bg"
                    UP_PAIRS.append(t)
            halves.append(seen_half[data])
        tiles[code] = halves
    global TILES, FREE_PAIRS
    TILES = tiles                       # item code, or ("up", index) for an upgrade's power-on tiles
    FREE_PAIRS = [t for kind, t in pool if kind == "bg" and not any(rom[BG_CHR + t * 16:BG_CHR + t * 16 + 32])]
    notes.append(f"item pictures: {len(seen_half)} tile pairs, {len(pool)} left")

    # In every switchable bank (COMMON): DrawItem's, the frame tile lookup's and TakeItem's helpers.
    from lol_choice import REWARD_ROOM, INSIDE
    a = Asm(COMMON)
    # draw (bank 7 $E71D: TAX / LDA ItemIdToDescriptor,X): items $24+ are drawn as the item conv[] (its slot's
    # palette) with FLAG = 1 + their index (the others: FLAG = 0)
    a.label("draw").b(0xA2, 0x00, 0xC9, BOMB_UP).br(0x90, "d_st")
    a.b(0xE9, BOMB_UP, 0xAA).b(0xE0, SLOT_CONV[0]).br(0x90, "d_rom").b(0xE0, SLOT_CONV[1]).br(0xB0, "d_rom")
    a.abs(0xBD, T.SCONV - SLOT_CONV[0]).br(0x90, "d_inx")                    # an upgrade slot: its palette item
    a.label("d_rom").abs(0xBD, "conv")
    a.label("d_inx").b(0xE8)
    a.label("d_st").abs(0x8E, FLAG).b(0xAA).abs(0xBD, 0x72C8).b(0x60)
    # tile (WRAM $793D: LDA Anim_ItemFrameTiles,Y / STA $02): FLAG 1 the bomb upgrade's tile; 2 (the blue book) the
    # book's; 3+ a 16x16 item of two different halves, drawn as the wide items are ($7868 with $02 / $03)
    a.label("tile").abs(0xAD, FLAG).br(0xF0, "t_n").b(0x48, 0xA9, 0x00).abs(0x8D, FLAG).b(0x68)
    a.b(0xC9, 0x01).br(0xF0, "t_bomb").b(0xC9, 0x02).br(0xF0, "t_n")
    a.b(0xA8).abs(0xB9, WLW).b(0x85, 0x02).abs(0xB9, WRW).b(0x85, 0x03, 0x68, 0x68).abs(0x4C, 0x7868)
    a.label("t_bomb").b(0xA9, TILE, 0x85, 0x02, 0x60)
    a.label("t_n").abs(0x4C, POT_W)                                           # (WRAM: the potions' pictures)
    # take (WRAM $7391 in TakeItem: TAX / LDA ItemIdToSlot,X): A-F's reward leaves the dungeon as the triforce does
    # (JSR $EBA3 / mode $12); $24 raises the bombs; $26-$28 count a badge (up to 3 each); $29 / $2A add XP
    # (the body in bank 0, far-called: lol_v3core)
    import lol_v3core as V
    from lol_odds import STORE
    from lol_af import AF_LEVELS
    REC_T = 0x0173                                      # (scratch: b_hi's too)
    def b_af(org):                                      # A-F's reward: out as the triforce (A = the item, kept)
        t = Asm(org)
        t.label("af").abs(0x20, "rec").b(0x48, 0xC5, 0xAB).br(0xD0, "k_n")       # PHA / the room's item?
        t.b(0xA5, 0x10).br(0xF0, "k_n").abs(0xAD, INSIDE).br(0xF0, "k_n")        # in A-F
        t.abs(0xAD, REWARD_ROOM).b(0x49, 0x80, 0xC5, 0xEB).br(0xD0, "k_n")       # the reward's room
        t.b(0xA9, 0x00).abs(0x8D, REWARD_ROOM).abs(0x20, 0xEBA3).b(0xA9, 0x12, 0x85, 0x12)
        t.label("k_n").b(0x68, 0x60)
        # rec (lol_stats' end screen): the item a level's old man gave (the take-any, $6B, in a first-quest level:
        # the odds' saved byte of that level, 0-8) or a shrine's reward (A-F's room, by its letter: 11-16) is kept
        # in that saved byte with bit 7 set (lol_odds keeps such a byte: the offer no longer matters). A, Y kept.
        t.label("rec").abs(0x8D, REC_T).b(0x98, 0x48)
        t.b(0xA5, 0x10).br(0xF0, "r_out")                                        # a level?
        t.b(0xA4, 0x16).abs(0xB9, 0x062D).br(0xD0, "r_sh")                       # the second quest: A-F / shrines
        t.abs(0xAD, 0x0350).b(0xC9, 0x6B).br(0xD0, "r_out")                      # the take-any old man
        t.b(0xA4, 0x10, 0x88, 0xC0, 0x09).br(0xB0, "r_out").br(0x90, "r_st")
        t.label("r_sh").abs(0xAD, INSIDE).br(0xF0, "r_out")
        t.abs(0xAD, REWARD_ROOM).b(0x49, 0x80, 0xC5, 0xEB).br(0xD0, "r_out")     # the reward's room
        t.abs(0xAD, REC_T).b(0xC5, 0xAB).br(0xD0, "r_out")                       # and its item
        t.b(0xA4, 0x10, 0xC0, 0x07).br(0xB0, "r_out").abs(0xB9, "r_let").b(0xA8)
        t.label("r_st").abs(0xAD, REC_T).b(0x09, 0x80).abs(0x99, STORE)
        t.label("r_out").b(0x68, 0xA8).abs(0xAD, REC_T).b(0x60)
        return t.label("r_let").b(0, *[11 + AF_LEVELS.index(lv) for lv in range(1, 7)])
    def b_hi(org):                                      # $24+ (TakeItem's own rest is skipped after)
        t = Asm(org)
        t.label("hi").b(0xC9, BOMB_UP).br(0xD0, "new")
        t.b(0xA9, 0x14).abs(0xAC, 0x7FF7).br(0xF0, "cap").b(0xA9, 0x20)         # (to 20; swordless 32)
        t.label("cap").abs(0x8D, 0x0173).abs(0xAD, MAX_BOMBS).abs(0xCD, 0x0173).br(0xB0, "full")
        t.b(0x69, 0x04).abs(0x8D, MAX_BOMBS)
        t.label("full").abs(0x8D, BOMBS).b(0x60)
        t.label("new").b(0xC9, XP_ORANGE).br(0xB0, "xp")
        t.b(0xE9, BADGE_S - 1, 0xAA)                                              # carry clear: A - $26
        t.abs(0xAD, BADGES).abs(0x3D, "mask").abs(0xDD, "mask").br(0xF0, "b_full")  # three of this kind already?
        t.abs(0xAD, BADGES).b(0x18).abs(0x7D, "inc").abs(0x8D, BADGES)
        t.label("b_full").b(0x60)
        t.label("xp").b(0xE9, XP_ORANGE, 0xAA).abs(0xAD, 0x066F).b(0xC9, 0xF0).br(0xB0, "x_done")   # 16 containers
        t.b(0xA9, 50).abs(0xAC, 0x7FF8).br(0xF0, "x_t").b(0xA9, 100)              # (lol_modes' hard mode: 100)
        t.label("x_t").abs(0x8D, 0x0173)
        t.abs(0xAD, XP).b(0x18).abs(0x7D, "xpv").abs(0xCD, 0x0173).br(0x90, "x_st")
        t.abs(0xED, 0x0173).abs(0x8D, XP).b(0xA9, 0x1A).abs(0x4C, 0x7370)          # a heart container
        t.label("x_st").abs(0x8D, XP)
        t.label("x_done").b(0x60)
        t.label("mask").b(0x03, 0x0C, 0x30)
        t.label("inc").b(0x01, 0x04, 0x10)
        return t.label("xpv").b(15, 25)
    af0 = V.put0(rom, b_af).labels["af"]
    hi0 = V.put0(rom, b_hi).labels["hi"]
    a.label("take").b(*V.far(0, af0)).b(0xC9, BOMB_UP).br(0xB0, "k_hi").abs(0x4C, POUCH_W)   # (WRAM: potions)
    a.label("k_hi").b(*V.far(0, hi0)).b(0x68, 0x68, 0x60)                     # (out of TakeItem)
    a.label("conv").b(*CONV)
    global WL_INIT, WR_INIT             # (copied to WRAM at power-on by lol_pictures; the loads change them)
    WL_INIT = bytes(tiles.get(c, [0, 0])[0] for c in range(0x26, 0x26 + N_FLAGS))   # (the upgrade slots: set by
    WR_INIT = bytes(tiles.get(c, [0, 0])[1] for c in range(0x26, 0x26 + N_FLAGS))   #  the loads)
    code = a.bytes()
    assert COMMON + len(code) <= 0xBC84, hex(COMMON + len(code))   # (bank 4's stubs from $BC84)
    for bank in range(7):
        at = BANK(bank) + COMMON - 0x8000
        assert all(x == 0xFF for x in rom[at:at + len(code)]), bank
        rom[at:at + len(code)] = code
    L = a.labels
    j = lambda n: bytes([0x20, L[n] & 0xFF, L[n] >> 8])
    patch(rom, 7, 0xE71D, bytes([0xAA, 0xBD, 0xC8, 0x72]), j("draw"))
    patch(rom, 1, 0x793D + WRAM_DELTA, bytes([0xB9, 0xDC, 0x78, 0x85, 0x02]), j("tile"))
    patch(rom, 1, 0x7391 + WRAM_DELTA, bytes([0xAA, 0xBD, 0xA4, 0x72]), j("take"))
    notes.append(f"items: bomb upgrade $24, badges S/D/X $26-$28, XP potions $29 (+15) / $2A (+25); "
                 f"{len(code)} bytes at ${COMMON:04X} in every bank")

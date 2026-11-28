"""Legend of Link: secret spots (owner, 2026-11-25). One seed in 100 gets one, never two: one of five spots, and
behind it an old man with one of five hints (each seed's own pick). Nothing shows it: no X-ray, no grey marks, no
Song of Discovery, not on the tracker, not in the manual.

  F1  row 4, column 4    a grey wall: bombed, a cave opens
  D9  row 6, column 12   a lone bush: burned, stairs
  E16 row 5, column 12   the broken bridge's right tile: the recorder there, stairs (no drain); out on the sand
  E2  row 5, column 9    a grave: pushed from the north or south, with the power bracelet, stairs (in its place);
                         touching it calls up no Ghini
  E13 row 4, column 9    the green wall two right of the ladder: bombed, a cave opens

How: the build picks (LOL_SEED / LOL_SET_SEED; LOL_SECRET="spot,hint" forces one for tests). The cave is lol_heavy's
(a hint cave, its own words). Each frame on the overworld (lol_upgrades' frame hook, bank 3): on the spot's screen,
a bomb's blast or a flame on the square, or Link pushing into it (with the bracelet), reveals it: the square written
(PlayAreaTiles and the tile buffer), the screen's secret flag ($80 of its world flags) set, the secret sound. The
recorder on E16 (lol_discovery's whirlwind hook, wrapped) does the same. A found spot is written again whenever Link
comes back to the screen. RAM: LASTR $0166 (the screen last seen), PUSH $0167 (the push's frames)."""
import os
import random
from lol_af import Asm, BANK, place

F1, D9, E16, E2, E13 = 0x50, 0x38, 0x4F, 0x41, 0x4C
BOMB, FIRE, RECORDER, PUSH = 1, 2, 3, 4
CAVE_TILES, STAIR_TILES = (0xF3, 0x24, 0xF3, 0x24), (0x70, 0x71, 0x72, 0x73)
# (room, column, row, trigger, tiles, exit column, exit row)
SPOTS = [(F1, 4, 4, BOMB, CAVE_TILES, 4, 4), (D9, 12, 6, FIRE, STAIR_TILES, 12, 6),
         (E16, 12, 5, RECORDER, STAIR_TILES, 8, 5), (E2, 9, 5, PUSH, STAIR_TILES, 9, 5),
         (E13, 9, 4, BOMB, CAVE_TILES, 9, 4)]
HINTS = [["1. UNSEED ON UNSEEDED"],
         ["2. TI NOSIOP DNA", "TIAB YUB"],
         ["3. WHO ALWAYS FILLS", "YOU UP BUT NEVER HAS", "THEIR OWN MEAL?"],
         ["4. MHMHHSJI JA ZHKMO!"],
         ["5. IT'S JUST", "LIKE IDDQD"]]
ODDS = 100
LASTR, PUSHC = 0x0166, 0x0167
WORLD_FLAGS = 0x6BAF
PLAY = 0x6530
OW = 0x18410
PUSH_FRAMES = 24


def _pick():
    forced = os.environ.get("LOL_SECRET")
    if forced:
        s, h = (int(v) for v in forced.split(","))
        return s, h
    if os.environ.get("LOL_RACE") != "1":      # (owner 2026-11-25) only ever on a Race Rom
        return None
    import lol_fixed
    if not lol_fixed.FIXED:                    # (2026-11-28) an unseeded Race Rom: no room for a spot's cave (the build
        return None                            #  stopped): none
    seed = os.environ.get("LOL_SEED") or os.environ.get("LOL_SET_SEED") or "0"
    rng = random.Random(f"lol secret spot {seed}")
    if rng.randrange(ODDS):
        return None
    s, h = rng.randrange(len(SPOTS)), rng.randrange(len(HINTS))
    import lol_odds
    if SPOTS[s][0] == E2 and not getattr(lol_odds, "LATE", False):
        # (owner 2026-11-28) E2's cave code doesn't fit bank 3 while lol_odds' engine is there (1.0 moves it): one of
        # the other four instead, until then
        s = [k for k in range(len(SPOTS)) if SPOTS[k][0] != E2][rng.randrange(len(SPOTS) - 1)]
    return s, h


PICK = _pick()
SPOT = SPOTS[PICK[0]] if PICK else None
TEXT = HINTS[PICK[1]] if PICK else None


def caves():
    """lol_heavy's cave list's entry for it (a hint cave, mode "secret"), or none."""
    if not PICK:
        return []
    import lol_heavy as H
    return [(SPOT[0], H.HINT_C, 0, None, "secret")]


def describe():
    if not PICK:
        return "none this seed"
    r = SPOT[0]
    return f"{'ABCDEFGH'[r // 16]}{r % 16 + 1} (hint {PICK[1] + 1})"


def _off(c, r):
    return c * 44 + r * 2


_FRAME = [None]


def frame_code(rom):
    """lol_upgrades' frame hook far-calls this (bank 3) every frame of play; None without a spot."""
    if not PICK:
        return None
    if _FRAME[0] is not None:
        return _FRAME[0]
    room, c, r, trig, tiles, _ec, _er = SPOT
    sx, sy = c * 16, 0x40 + r * 16
    ppu = 0x2100 + r * 64 + 2 * c
    OFF = (0, 1, 22, 23)

    def build(org):
        a = Asm(org)
        a.label("fr").b(0xA5, 0x10).br(0xD0, "x0").b(0xA5, 0x12, 0xC9, 0x05).br(0xD0, "x0")
        a.b(0xA5, 0xEB, 0xC9, room).br(0xF0, "here")
        a.label("x0").b(0xA9, 0xFF).abs(0x8D, LASTR)                          # (elsewhere, a cave, a scroll)
        a.label("x").b(0x60)
        a.label("here").abs(0x20, "found").br(0xF0, "look")
        # found: written again as Link comes back
        a.b(0xA5, 0xEB).abs(0xCD, LASTR).br(0xF0, "x").abs(0x8D, LASTR).abs(0x4C, "wsq")
        a.label("look").b(0xA5, 0xEB).abs(0x8D, LASTR)
        if trig in (BOMB, FIRE):
            # a bomb blasting ($13) / a flame ($20+) in slot $10 or $11, its middle within 16 px of the square's
            a.b(0xA2, 0x11)
            a.label("w_l").b(0xB5, 0xAC)
            if trig == BOMB:
                a.b(0xC9, 0x13).br(0xD0, "w_n")
            else:
                a.b(0xC9, 0x20).br(0x90, "w_n")
            a.b(0xB5, 0x70, 0x38, 0xE9, sx & 0xFF).abs(0x20, "abs").b(0xC9, 0x10).br(0xB0, "w_n")
            a.b(0xB5, 0x84, 0x38, 0xE9, sy & 0xFF).abs(0x20, "abs").b(0xC9, 0x10).br(0xB0, "w_n")
            a.abs(0x4C, "reveal")
            a.label("w_n").b(0xCA, 0xE0, 0x10).br(0xB0, "w_l").b(0x60)
        elif trig == PUSH:
            # Link, with the bracelet, pressing into the grave from a side next to it, PUSH_FRAMES frames
            a.abs(0xAD, 0x0665).br(0xD0, "p_b").abs(0x4C, "p_0")
            a.label("p_b").b(0xA5, 0xFA, 0x29, 0x0F).br(0xD0, "p_h").abs(0x4C, "p_0")
            a.label("p_h").b(0x85, 0x0F)
            # (owner) pushed from the north or the south: up from right below (a grave stops Link 5 px into its
            # row) or down from right above (19 px above it)
            for btn, dx, dy in ((0x08, 0, 8), (0x04, 0, -16)):
                a.b(0xA5, 0x0F, 0x29, btn).br(0xF0, f"p_s{btn}")
                a.b(0xA5, 0x70, 0x38, 0xE9, (sx + dx) & 0xFF).abs(0x20, "abs").b(0xC9, 0x05).br(0xB0, f"p_s{btn}")
                a.b(0xA5, 0x84, 0x38, 0xE9, (sy + dy - 3) & 0xFF).abs(0x20, "abs").b(0xC9, 0x05).br(0x90, "p_in")
                a.label(f"p_s{btn}")
            a.label("p_0").b(0xA9, 0x00).abs(0x8D, PUSHC).b(0x60)
            a.label("p_in").abs(0xEE, PUSHC).abs(0xAD, PUSHC).b(0xC9, PUSH_FRAMES).br(0xB0, "reveal").b(0x60)
        else:
            a.b(0x60)
        # the reveal: the flag, the sound, the square
        a.label("reveal").abs(0xAD, WORLD_FLAGS).b(0x85, 0x0C).abs(0xAD, WORLD_FLAGS + 1).b(0x85, 0x0D)
        a.b(0xA4, 0xEB, 0xB1, 0x0C, 0x09, 0x80, 0x91, 0x0C).b(0xA9, 0x04).abs(0x8D, 0x0602)
        # wsq: the square's four tiles to PlayAreaTiles and the tile buffer (two columns of two)
        a.label("wsq")
        for k in range(4):
            a.b(0xA9, tiles[k]).abs(0x8D, PLAY + _off(c, r) + OFF[k])
        a.abs(0xAC, 0x0301)
        a.b(0xA9, ppu >> 8).abs(0x99, 0x0302).abs(0x99, 0x0307)
        a.b(0xA9, ppu & 0xFF).abs(0x99, 0x0303).b(0xA9, (ppu + 32) & 0xFF).abs(0x99, 0x0308)
        a.b(0xA9, 0x02).abs(0x99, 0x0304).abs(0x99, 0x0309)
        a.b(0xA9, tiles[0]).abs(0x99, 0x0305).b(0xA9, tiles[2]).abs(0x99, 0x0306)
        a.b(0xA9, tiles[1]).abs(0x99, 0x030A).b(0xA9, tiles[3]).abs(0x99, 0x030B)
        a.b(0xA9, 0xFF).abs(0x99, 0x030C).b(0x98, 0x18, 0x69, 0x0A).abs(0x8D, 0x0301).b(0x60)
        # found: Z clear when this screen's secret is flagged
        a.label("found").abs(0xAD, WORLD_FLAGS).b(0x85, 0x0C).abs(0xAD, WORLD_FLAGS + 1).b(0x85, 0x0D)
        a.b(0xA4, 0xEB, 0xB1, 0x0C, 0x29, 0x80, 0x60)
        a.label("abs").br(0xB0, "a_r").b(0x49, 0xFF, 0x69, 0x01)
        a.label("a_r").b(0x60)
        # the recorder (E16): C set when it revealed the spot (no whirlwind)
        a.label("rec").b(0xA5, 0x10).br(0xD0, "r_no").b(0xA5, 0xEB, 0xC9, room).br(0xD0, "r_no")
        a.abs(0x20, "found").br(0xD0, "r_no").abs(0x20, "reveal").b(0x38, 0x60)
        a.label("r_no").b(0x18, 0x60)
        return a
    from lol_newups import put3
    a = put3(rom, 3, build)
    _FRAME[0] = a.labels["fr"]
    _FRAME.append(a.labels["rec"])
    return _FRAME[0]


def apply(rom: bytearray, notes: list) -> None:
    if not PICK:
        notes.append("secret spot: " + describe())
        return
    import lol_v3core as V
    from lol_newups import free_in
    room, c, r, trig, tiles, ec, er = SPOT
    assert rom[OW + 0x80 + room] >> 2 == 0, "the spot's screen has an entrance"
    rom[OW + room] = (ec << 4) | (rom[OW + room] & 0x0F)                     # where Link comes back out
    rom[OW + 0x280 + room] = (rom[OW + 0x280 + room] & 0xF8) | er
    if trig == RECORDER:
        rec = _FRAME[1] if len(_FRAME) > 1 else None
        assert rec, "lol_upgrades' frame hook builds the code first"
        b7 = BANK(7) - 0xC000
        old = rom[b7 + 0xEFC0] | rom[b7 + 0xEFC1] << 8

        def bstub(o):
            s = Asm(o)
            s.b(*V.far(3, rec)).br(0xB0, "r").abs(0x4C, old)
            s.label("r").b(0x60)
            return s
        sa = free_in(rom, 1, len(bstub(0x8000).bytes()), 0xB000)
        place(rom, 1, sa, bstub(sa).bytes())
        rom[b7 + 0xEFC0:b7 + 0xEFC2] = bytes([sa & 0xFF, sa >> 8])
    if trig == PUSH:
        # (owner) touching this grave calls up no Ghini: the tile object spawn's JSR FindEmptyMonsterSlot (bank 1
        # $A271) answers "none" for a square within 16 px across / 24 down of it on its screen
        sx, sy = c * 16, 0x40 + r * 16

        def gstub(o):
            s = Asm(o)
            s.b(0xA5, 0xEB, 0xC9, room).br(0xD0, "n")
            s.b(0xA5, 0x00, 0x38, 0xE9, sx).br(0xB0, "p1").b(0x49, 0xFF, 0x69, 0x01)
            s.label("p1").b(0xC9, 0x10).br(0xB0, "n")
            s.b(0xA5, 0x01, 0x38, 0xE9, sy).br(0xB0, "p2").b(0x49, 0xFF, 0x69, 0x01)
            s.label("p2").b(0xC9, 0x18).br(0xB0, "n").b(0xA9, 0x00, 0x60)            # (from above: 19 px off)
            s.label("n").abs(0x4C, 0xFEBB)
            return s
        ga = free_in(rom, 1, len(gstub(0x8000).bytes()), 0xB000)
        place(rom, 1, ga, gstub(ga).bytes())
        b1 = BANK(1) - 0x8000
        assert rom[b1 + 0xA271:b1 + 0xA274] == bytes([0x20, 0xBB, 0xFE])
        rom[b1 + 0xA271:b1 + 0xA274] = bytes([0x20, ga & 0xFF, ga >> 8])
    notes.append("secret spot: " + describe())

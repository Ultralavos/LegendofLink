"""Legend of Link: the upgrades' pictures are loaded when they're needed.

The background tiles $34-$5F (they last through the levels and the caves) hold the new items' pictures. At power-on
they hold the first nine upgrades' (the title's legend shows them); after that, 12 of those tile pairs are six
picture slots: 0-2 the upgrades Link owns (at most three: an upgrade cave sells one), 3-5 the wares of the upgrade
cave he's in. Each item's two halves are found through WRAM tables (lol_bombup's WLW / WRW, by FLAG), which a load
points at its slot; a half that is a game picture (the sword, the wand, the bottle and fairy) is just its sprite
tile.

  power-on (bank 2's common-pattern load, $8045: LDA #$5A / STA $F5): the tables from their ROM copy
  an overworld load (lol_entrances' post_copy, bank 6) and an upgrade cave's wares (bank 1): STUB, the same in banks
    1, 2 and 6, switches to bank 2 and runs LOAD (X = 0 the owned ones, 1 also the wares), then back.

LOAD turns the picture off for the rest of the frame (the next NMI turns it back on from $FE) and writes each half's
32 bytes to the PPU at $1000 + pair * 16 (NMI is already off: the game runs inside it)."""
from lol_af import Asm, place, patch, BANK

LOAD = None
STUB = 0xBD8E                          # banks 1, 2, 6 free
STUB_LEN = 15
STUB_END = STUB + STUB_LEN
SWITCH = 0xFFAC
LOAD_AT = 0xB330                       # bank 2 free ($B322-, 1502 bytes)
INIT_HOOK = 0x8045                     # bank 2: LDA #$5A / STA $F5 (the common patterns loaded)
U_MODE, U_SLOT, U_IT, U_K = 0x019D, 0x019E, 0x019F, 0x01A0   # (stack page, unused)
CI = 0x0194                            # lol_upgrades: the upgrade cave's index (0-2)
CAVE_WARES = 0x6A7E
import lol_uptable
N_UP = lol_uptable.N_UP
CODE_MAX = 0x280                       # the code's room; the pictures' data after it
FIRST = 0x2B
POT_DATA = 0x9BD8                      # bank 2 free (297 bytes)


def apply(rom: bytearray, notes: list) -> None:
    import lol_bombup as B
    import lol_upgrades as U
    import lol_uptable as T0
    assert T0.N_UP == N_UP
    pairs = B.UP_PAIRS[:12]
    assert len(pairs) == 12 and len(set(pairs)) == 12
    ppairs = B.UP_PAIRS[12:14] + [B.FREE_PAIRS[1]]       # the potion's three: counts 1-2, 3, 4
    assert len(ppairs) == 3 and B.FREE_PAIRS[0] == U.FAIRY_TILE
    # every upgrade's halves: data in bank 2, or a fixed sprite tile
    halves = [B.HALVES[k] for k in range(N_UP)]
    assert all(len(h) == 2 for h in halves)
    w = Asm(B.POT_W)
    w.abs(0xB9, 0x78DC).b(0xC9, 0x40).br(0xD0, "st")
    w.b(0x98, 0x48, 0xA5, 0x04, 0x29, 0x07, 0xA8, 0x88, 0xC0, 0x04).br(0xB0, "pr")
    w.abs(0xB9, B.PPAL).b(0x85, 0x04).abs(0xB9, B.PTILE).b(0x85, 0x02, 0x68, 0xA8, 0x60)
    w.label("pr").b(0x68, 0xA8, 0xA9, 0x40)
    w.label("st").b(0x85, 0x02, 0x60)
    wc = w.bytes(); assert len(wc) <= B.POT_LEN, len(wc)
    v = Asm(B.POUCH_W)
    v.b(0xAA, 0xE0, 0x1F).br(0x90, "v").b(0xE0, 0x21).br(0xB0, "v").abs(0xAD, U.POUCH[0]).b(0x29, U.POUCH[1]).br(0xF0, "v")
    v.b(0x8A, 0x38, 0xE9, 0x1E, 0x18).abs(0x6D, 0x065E).b(0xC9, 0x05).br(0x90, "s").b(0xA9, 0x04)
    v.label("s").abs(0x8D, 0x065E).b(0x68, 0x68, 0x60)
    v.label("v").b(0xE0, 0x19).br(0xD0, "v2")                                 # key hoarder: a key counts twice
    import lol_uptable as TU
    kh = TU.bit("key hoarder")
    v.abs(0xAD, kh[0]).b(0x29, kh[1]).br(0xF0, "v2").abs(0xEE, 0x066E)
    v.label("v2").abs(0xBD, 0x72A4).b(0x60)
    vc = v.bytes(); assert len(vc) <= B.POUCH_LEN, len(vc)
    import lol_v3core as V3                                             # (bank 7 since stage 4)
    for at, c in ((B.POT_W, wc), (B.POUCH_W, vc)):
        assert all(x == 0xFF for x in rom[V3.b7(at):V3.b7(at) + len(c)])
        rom[V3.b7(at):V3.b7(at) + len(c)] = c
    wram = [0x40] * 4 + [1, 2, 2, 1]                                    # the potion tables (PTILE / PPAL)
    import lol_uptable as T
    BAT = T.index("bat potion")
    # every upgrade's halves: their data (bank 0, after the code), or a fixed sprite tile
    order = [halves[k][0] for k in range(N_UP)] + [halves[k][1] for k in range(N_UP)]
    pp = [B.pair_bytes(B.potion_rows(l, bt)) for l, bt in (("blue", True), ("orange", True), ("white", True),
                                                             ("blue", True), ("blue", True), ("blue", True),
                                                             ("orange", False), ("white", False))]
    pp += [B.pair_bytes(B.brain_rows(l)) for l in ("blue", "orange", "white")]   # 8-10: Zombie Link's brain potions

    def build(org, blob_at=None):
        datas, blob = {}, b""
        lo, hi, plo, phi = [], [], [], []
        base = blob_at if blob_at is not None else 0x8000
        for kind, v in order:
            if kind == "fixed":
                lo.append(v); hi.append(0)
            else:
                if v not in datas:
                    datas[v] = base + len(blob); blob += v
                lo.append(datas[v] & 0xFF); hi.append(datas[v] >> 8)
        for d in pp:
            if d not in datas:
                datas[d] = base + len(blob); blob += d
            plo.append(datas[d] & 0xFF); phi.append(datas[d] >> 8)
        a = Asm(org)
        a.label("load").abs(0x8E, U_MODE).b(0xA5, 0x00, 0x48, 0xA5, 0x01, 0x48)
        a.b(0xA9, 0x00).abs(0x8D, 0x2001)                                  # the picture off
        a.b(0xA5, 0xFF, 0x29, 0x7B).abs(0x8D, 0x2000)                      # (+1 a write, NMI off)
        a.b(0xA9, 0x00).abs(0x8D, U_SLOT).b(0xA2, 0x00)
        # the owned ones: slots 0-2, in table order
        a.label("o_lp").abs(0x20, "uget").br(0xF0, "o_nx")
        a.abs(0xAD, U_SLOT).b(0xC9, 0x03).br(0xB0, "o_nx")
        a.abs(0x20, "put").abs(0xEE, U_SLOT)
        a.label("o_nx").b(0xE8, 0xE0, N_UP).br(0xD0, "o_lp")
        a.abs(0xAD, U_SLOT).abs(0x8D, T.OWN_N)
        # the potion's pictures: with the bat potion its own for 1-2 (else the game's $40), 3 orange, 4 white
        a.b(0xA2, T.index("brain potion")).abs(0x20, "uget").br(0xF0, "p_nbr")   # brain potions: their three
        a.b(0xA2, 8).abs(0x20, "pot").b(0xA2, 9).br(0xD0, "p_34")
        a.label("p_nbr").b(0xA2, BAT).abs(0x20, "uget").br(0xF0, "p_nb")
        a.b(0xA2, 0).abs(0x20, "pot").b(0xA2, 1).br(0xD0, "p_34")
        a.label("p_nb").b(0xA9, 0x40).abs(0x8D, B.PTILE).abs(0x8D, B.PTILE + 1).b(0xA2, 6)
        a.label("p_34").abs(0x20, "pot").b(0xE8).abs(0x20, "pot")
        a.abs(0xAD, U_MODE).br(0xF0, "done")
        # the wares: slots 3-5, the upgrades WIX names ($FF: none)
        a.b(0xA9, 0x03).abs(0x8D, U_SLOT).b(0xA0, 0x00)
        a.label("w_lp").abs(0xBE, T.WIX).b(0xE0, N_UP).br(0xB0, "w_nx")
        a.b(0x98, 0x48).abs(0x20, "put").b(0x68, 0xA8)
        a.label("w_nx").b(0xC8).abs(0xEE, U_SLOT).abs(0xAD, U_SLOT).b(0xC9, 0x06).br(0xD0, "w_lp")
        a.label("done").abs(0xAD, 0x2002).b(0xA5, 0xFF).abs(0x8D, 0x2000)
        a.b(0x68, 0x85, 0x01, 0x68, 0x85, 0x00, 0x60)
        # pot: X = the picture (0 bat 1-2, 1 bat 3, 2 bat 4 / 3-5 unused, 6 orange, 7 white); its place by X mod 3 /
        # X 0: counts 1 and 2. (X kept)
        a.label("pot").abs(0xBD, "pplo").b(0x85, 0x00).abs(0xBD, "pphi").b(0x85, 0x01)
        a.abs(0xBC, "ppk").abs(0xB9, "ppair").abs(0x20, "up32").abs(0x99, B.PTILE + 1)
        a.b(0xC0, 0x00).br(0xD0, "pt_r").abs(0x8D, B.PTILE)
        a.label("pt_r").b(0x60)
        # up32: 32 bytes from ($00) to the pair A; A = its sprite tile byte (Y kept)
        a.label("up32").abs(0x8D, U_K).b(0x4A, 0x4A, 0x4A, 0x4A, 0x09, 0x10).abs(0x8D, 0x2006)
        a.abs(0xAD, U_K).b(0x0A, 0x0A, 0x0A, 0x0A).abs(0x8D, 0x2006)
        a.b(0x98, 0x48, 0xA0, 0x00)
        a.label("u3_lp").b(0xB1, 0x00).abs(0x8D, 0x2007).b(0xC8, 0xC0, 0x20).br(0xD0, "u3_lp")
        a.b(0x68, 0xA8).abs(0xAD, U_K).b(0x18, 0x69, 0x01, 0x60)
        # uget: X = the upgrade, A = its owned bit (Z clear: owned); X kept
        a.label("uget").abs(0xBD, "uahi").b(0x85, 0x01).abs(0xBD, "ualo").b(0x85, 0x00).b(0xA0, 0x00, 0xB1, 0x00)
        a.abs(0x3D, "ubits").b(0x60)
        # put: X = the upgrade, U_SLOT the slot: both halves loaded, the slot's tables pointed at them, its palette
        a.label("put").abs(0x8E, U_IT).abs(0xAD, U_SLOT).b(0x0A).abs(0x8D, U_K)
        a.abs(0x20, "half").abs(0xAC, U_SLOT).abs(0x99, B.WLW + 8)
        a.abs(0xEE, U_K).abs(0xAE, U_IT).b(0x8A, 0x18, 0x69, N_UP, 0xAA).abs(0x20, "half")
        a.abs(0xAC, U_SLOT).abs(0x99, B.WRW + 8)
        a.abs(0xAE, U_IT).abs(0xBD, "upal").abs(0x99, T.SCONV).b(0x60)
        # half: X = the half (0 .. 2N-1); A = its tile byte
        a.label("half").abs(0xBD, "hhi").br(0xD0, "h_data").abs(0xBD, "hlo").b(0x60)
        a.label("h_data").b(0x85, 0x01).abs(0xBD, "hlo").b(0x85, 0x00)
        a.abs(0xAC, U_K).abs(0xB9, "slotp").b(0x48)
        a.b(0x4A, 0x4A, 0x4A, 0x4A, 0x09, 0x10).abs(0x8D, 0x2006)
        a.b(0x68, 0x48, 0x0A, 0x0A, 0x0A, 0x0A).abs(0x8D, 0x2006)
        a.b(0xA0, 0x00)
        a.label("h_lp").b(0xB1, 0x00).abs(0x8D, 0x2007).b(0xC8, 0xC0, 0x20).br(0xD0, "h_lp")
        a.b(0x68, 0x18, 0x69, 0x01, 0x60)                                   # (bit 0: the $1000 table)
        a.label("ualo").b(*[T.ROWS[k][T.SAVE][0] & 0xFF for k in range(N_UP)])
        a.label("uahi").b(*[T.ROWS[k][T.SAVE][0] >> 8 for k in range(N_UP)])
        a.label("ubits").b(*[T.ROWS[k][T.SAVE][1] for k in range(N_UP)])
        a.label("upal").b(*[T.ROWS[k][T.PAL] for k in range(N_UP)])
        a.label("slotp").b(*pairs)
        a.label("ppk").b(0, 1, 2, 0, 0, 0, 1, 2, 0, 1, 2)
        a.label("ppair").b(*ppairs)
        a.label("pplo").b(*plo)
        a.label("pphi").b(*phi)
        a.label("hlo").b(*lo)
        a.label("hhi").b(*hi)
        return a, blob

    import lol_v3core as V3
    a0, blob0 = build(0x8000)
    size = len(a0.bytes()) + len(blob0)
    at = V3.alloc0(size)
    a, _ = build(at)
    a, blob = build(at, at + len(a.bytes()))
    code = a.bytes()
    off = BANK(0) + at - 0x8000
    assert all(x == 0xFF for x in rom[off:off + len(code) + len(blob)])
    rom[off:off + len(code) + len(blob)] = code + blob
    L = a.labels
    global LOAD
    LOAD = dict(L)
    # power-on (bank 2): the tables
    i2 = Asm(LOAD_AT)
    i2.label("init").b(0xA2, len(B.WL_INIT) - 1)
    i2.label("i_lp").abs(0xBD, "wl0").abs(0x9D, B.WLW + 3).abs(0xBD, "wr0").abs(0x9D, B.WRW + 3)
    i2.b(0xCA).br(0x10, "i_lp")
    i2.b(0xA2, len(wram) - 1)                                           # the potion tables
    i2.label("i_w").abs(0xBD, "wram").abs(0x9D, B.PTILE).b(0xCA).br(0x10, "i_w")
    i2.b(0xA9, 0x5A, 0x85, 0xF5, 0x60)
    i2.label("wl0").b(*B.WL_INIT)
    i2.label("wr0").b(*B.WR_INIT)
    i2.label("wram").b(*wram)
    place(rom, 2, LOAD_AT, i2.bytes())
    patch(rom, 2, INIT_HOOK, bytes([0xA9, 0x5A, 0x85, 0xF5]), bytes([0x20, LOAD_AT & 0xFF, LOAD_AT >> 8, 0xEA]))
    for bank in (1, 2, 6):                                              # (a far call: LOAD is in bank 0)
        s = Asm(STUB)
        s.b(*V3.far(0, L["load"])).b(0x60)
        assert len(s.bytes()) <= STUB_LEN
        place(rom, bank, STUB, s.bytes())
    notes.append(f"upgrade pictures loaded on demand: 6 slots in pairs {[hex(p) for p in pairs]}; "
                 f"{len(code)} + {len(blob)} bytes in bank 0 at ${at:04X}")

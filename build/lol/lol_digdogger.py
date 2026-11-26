"""Legend of Link: the Bomb Digdogger (owner, 2026-11-26; a test build first): the triple Digdogger ($38 that splits in
3) once enemies see 8 heart containers (HVE $70).

  - pink (sprite palette 3 sent as COLORS every 16 frames while one is in the room, as the red Gleeok's red);
  - moves as ever, but the recorder doesn't split it: each tune drops 3 red bombs (lol_dodongo's type $29: lit,
    then the blast, 4 hearts to Link only), one under Link and one on each side of him;
  - every 120 frames a red bomb on a random square;
  - it splits in 3 only when it touches the bait (the vanilla split, started by setting UsedFlute); the minis have
    10 health ($A0) and the bombs go on while any is left;
  - the poison bait kills it at once (HandleMonsterDied: no split).

Bank 4: UpdateDigdogger's LDA InvClock ($95F0) -> a stub: far(3, dg), then LDA InvClock.
Bank 7: FlagFluteUsed ($EFC7: LDA UsedFlute / BNE / INC UsedFlute / RTS) -> far(3, fl) / RTS: in a Bomb Digdogger's
  room the bombs instead, else the replaced code.
RAM (save RAM spare): DGR the room it's in (one is there), BT the bomb timer, LASTF the frame done, SPL 1: a bait
split to come (its minis get their health)."""
from lol_af import Asm, BANK, patch

AT = 0x70                                       # HVE: 8 containers
COLORS = (0x14, 0x24, 0x34)
EVERY = 120
MINI_HP = 0xA0
DGR, BT, LASTF, SPL = 0x6092, 0x6093, 0x6094, 0x6095
HVE = 0x016F
USED_FLUTE, CHILDREN, IS_CHILD = 0x051B, 0x0507, 0x046B
ROOM = 0xEB
BAIT = 0x0F                                     # the bait's slot (state bit 7: the bait)
DIED = 0xB4E6 - 0x3870                          # HandleMonsterDied (WRAM)
FIND_EMPTY, SET_TYPE = 0xFEBB, 0xFEB3
BOMB = 0x29                                     # lol_dodongo's red bomb
X0, X1, Y0, ROWS = 0x20, 0xD0, 0x5D, 7          # the floor's squares (x $20-$D0, y $5D + 16 * 0-6)


def apply(rom: bytearray, notes: list) -> None:
    import lol_v3core as V
    import lol_newups as N
    pb, pbit = N.bit("poison bait")

    def build(o):
        a = Asm(o)
        # ---- dg: UpdateDigdogger, X the digdogger ----
        a.label("dg").abs(0xAD, HVE).b(0xC9, AT).br(0xB0, "d_on").label("d_r0").b(0x60)
        a.label("d_on").abs(0xBD, 0x034F).b(0xC9, 0x38).br(0xD0, "d_ch")
        a.abs(0xBD, IS_CHILD).br(0xD0, "d_r0")
        a.abs(0xAD, CHILDREN).b(0xC9, 0x03).br(0xD0, "d_r0")                 # the triple only
        a.b(0xA5, ROOM).abs(0xCD, DGR).br(0xF0, "d_bait")
        a.abs(0x8D, DGR).b(0xA9, EVERY).abs(0x8D, BT).b(0xA9, 0x00).abs(0x8D, SPL)
        # the bait touching it (32x32 at its x / y; the bait 16x16)
        a.label("d_bait").b(0xA5, 0xAC + BAIT).br(0x10, "d_com")
        a.b(0xA5, 0x70 + BAIT, 0x38, 0xF5, 0x70, 0x18, 0x69, 0x10, 0xC9, 0x30).br(0xB0, "d_com")
        a.b(0xA5, 0x84 + BAIT, 0x38, 0xF5, 0x84, 0x18, 0x69, 0x10, 0xC9, 0x30).br(0xB0, "d_com")
        a.abs(0xAD, pb).b(0x29, pbit).br(0xF0, "d_split")
        a.b(0xA9, 0x00, 0x85, 0x09, 0x85, 0x00).abs(0x20, DIED).b(0x60)        # poison: dead, no split
        a.label("d_split").abs(0xAD, USED_FLUTE).br(0xD0, "d_com")
        a.b(0xA9, 0x01).abs(0x8D, USED_FLUTE).abs(0x8D, SPL).abs(0x4C, "d_com")
        # a mini ($18) in its room: their health once after the split
        a.label("d_ch").b(0xC9, 0x18).br(0xD0, "d_r1").b(0xA5, ROOM).abs(0xCD, DGR).br(0xF0, "d_c2")
        a.label("d_r1").b(0x60)
        a.label("d_c2")
        a.abs(0xAD, SPL).br(0xF0, "d_com").b(0xA9, 0x00).abs(0x8D, SPL)
        a.b(0x8A, 0x48, 0xA2, 0x0B)
        a.label("d_hp").abs(0xBD, 0x034F).b(0xC9, 0x18).br(0xD0, "d_hn").b(0xA9, MINI_HP).abs(0x9D, 0x0485)
        a.label("d_hn").b(0xCA).br(0xD0, "d_hp").b(0x68, 0xAA)
        # once a frame: the palette every 16, the bomb every EVERY
        a.label("d_com").b(0xA5, 0x15).abs(0xCD, LASTF).br(0xF0, "d_r").abs(0x8D, LASTF)
        a.b(0x29, 0x0F).br(0xD0, "d_t")
        a.b(0x8A, 0x48).abs(0xAE, 0x0301)
        a.b(0xA9, 0x3F).abs(0x9D, 0x0302).b(0xA9, 0x1D).abs(0x9D, 0x0303).b(0xA9, 0x03).abs(0x9D, 0x0304)
        for i, c in enumerate(COLORS):
            a.b(0xA9, c).abs(0x9D, 0x0305 + i)
        a.b(0xA9, 0xFF).abs(0x9D, 0x0308).b(0x8A, 0x18, 0x69, 0x06).abs(0x8D, 0x0301)
        a.b(0x68, 0xAA)
        a.label("d_t").abs(0xCE, BT).br(0xD0, "d_r").b(0xA9, EVERY).abs(0x8D, BT)
        a.label("d_rx").b(0xA5, 0x18, 0x29, 0x0F, 0xC9, 12).br(0x90, "d_rx2").b(0xE9, 0x04)     # column 0-11
        a.label("d_rx2").b(0x0A, 0x0A, 0x0A, 0x0A, 0x69, X0, 0x85, 0x00)
        a.label("d_ry").b(0xA5, 0x19, 0x29, 0x07, 0xC9, ROWS).br(0x90, "d_ry2").b(0xA9, 0x03)
        a.label("d_ry2").b(0x0A, 0x0A, 0x0A, 0x0A, 0x69, Y0, 0x85, 0x01).abs(0x4C, "bomb")
        a.label("d_r").b(0x60)
        # ---- fl: the recorder's tune in a dungeon (FlagFluteUsed) ----
        a.label("fl").abs(0xAD, HVE).b(0xC9, AT).br(0x90, "f_v").b(0xA5, ROOM).abs(0xCD, DGR).br(0xD0, "f_v")
        a.b(0xA0, 0x0B)
        a.label("f_lp").abs(0xB9, 0x034F).b(0xC9, 0x38).br(0xF0, "f_yes").b(0xC9, 0x18).br(0xF0, "f_yes")
        a.b(0x88).br(0xD0, "f_lp")
        a.label("f_v").abs(0xAD, USED_FLUTE).br(0xD0, "f_r").abs(0xEE, USED_FLUTE)
        a.label("f_r").b(0x60)
        a.label("f_yes").b(0x8A, 0x48)
        for dx in (0x00, 0xF0, 0x10):                                     # under Link, left, right
            a.b(0xA5, 0x70, 0x18, 0x69, dx).abs(0x20, "clx").b(0x85, 0x00, 0xA5, 0x84, 0x85, 0x01).abs(0x20, "bomb")
        a.b(0x68, 0xAA, 0x60)
        a.label("clx").b(0xC9, X0).br(0xB0, "c_1").b(0xA9, X0)
        a.label("c_1").b(0xC9, X1 + 1).br(0x90, "c_2").b(0xA9, X1)
        a.label("c_2").b(0x60)
        # ---- bomb: a red bomb at $00 / $01 (X kept) ----
        a.label("bomb").abs(0x20, FIND_EMPTY).br(0xF0, "b_r")
        a.b(0x8A, 0x48, 0x98, 0xAA, 0xA9, BOMB).abs(0x20, SET_TYPE)
        a.b(0xA9, 0x00).abs(0x9D, 0x0405).b(0x95, 0x98)                    # (no spawn cloud; no owner)
        a.b(0xA5, 0x00, 0x95, 0x70, 0xA5, 0x01, 0x95, 0x84, 0x68, 0xAA)
        a.label("b_r").b(0x60)
        return a
    a = N.put3_best(rom, build)
    L = a.labels

    def stub(o):
        return Asm(o).b(*V.far(3, L["dg"])).abs(0xAD, 0x066C).b(0x60)
    s = N.put(rom, 4, stub)
    patch(rom, 4, 0x95F0, bytes([0xAD, 0x6C, 0x06]), bytes([0x20, s.cpu & 0xFF, s.cpu >> 8]))
    patch(rom, 7, 0xEFC7, bytes.fromhex("ad1b05d003ee1b0560"), bytes(V.far(3, L["fl"])) + bytes([0x60, 0xEA]))
    notes.append(f"Bomb Digdogger: 8+ containers, {len(a.bytes())} bytes in bank 3 at ${L['dg']:04X}")

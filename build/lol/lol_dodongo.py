"""Legend of Link: blue dodongos once Link has 10 heart containers.

A blue dodongo is drawn with palette 1, isn't stunned by a bomb's blast (it still eats bombs: two kill it), and
each time it turns it drops a red bomb, one at a time: object type $29 (unused, DoNothing in vanilla), owner slot
in its ObjDir. The bomb lights for $30 frames, then blasts like Link's (big then small clouds, the blast sound),
hurting only Link (contact while blasting: type $29's damage, 4 hearts; invincibility mask $FF).

Bank 4 is full, so the new code is in bank 2, reached through a trampoline in the common area ($BD46: the same
bytes in banks 2 and 4): LDY #0 / BIT (turned) or LDY #1 (the bomb), switch to bank 2, JSR the dispatcher,
switch back to bank 4."""
from lol_af import Asm, place, patch, BANK

HC_AT = 0x90                                   # HeartValues >= $90: 10 containers
HVE = 0x016F                            # lol_build: the containers enemies level up by (HeartValues; hard mode + 3)
BOMB_TYPE = 0x29
TRAMP = 0xBD46                                 # banks 2 and 4: free
MORE = 0xB680                                  # bank 2: lol_enemies2's handlers (Y 2+; to $B8FF at most)
CODE2 = 0xB200                                 # bank 2 free ($B16A-$BBA0)
WRAP4, PAL4, STUN4 = 0x9088, 0xBDEA, 0xBF42    # bank 4 free (vanilla padding)
SWITCH = 0xFFAC
FIND_EMPTY, SET_TYPE = 0xFEBB, 0xFEB3          # bank 7: FindEmptyMonsterSlot, SetTypeAndClearObject
WRITE_ITEM_SPRITES = 0x7915                    # WRAM: Anim_WriteItemSprites (bank 1 $B185)
CHECK_COLLISIONS = 0x79D0                      # WRAM: CheckMonsterCollisions
DODONGO_STATE, LEVEL_PAL = 0x98BD, 0x9AFB      # bank 4: UpdateDodongoState, Anim_SetSpriteDescriptorLevelPaletteRow
DAMAGE_TABLE = 0xB2BA                          # bank 1 (WRAM $7A4A): ObjTypeToDamagePoints
CLOUD_Y = (0xF3, 0x00, 0x0E, 0, 0, 0, 0xF3, 0x00, 0x0E)    # DrawOtherBombClouds' offsets (two sets, +6)
CLOUD_X = (0xF9, 0x0E, 0x07, 0, 0, 0, 0x07, 0xF3, 0xF9)


def apply(rom: bytearray, notes: list) -> None:
    # the trampoline, the same in banks 2 and 4
    t = Asm(TRAMP)
    t.label("turned").b(0xA0, 0x00, 0x2C)                  # LDY #0 / BIT abs (skips LDY #1)
    t.label("bomb").b(0xA0, 0x01)
    t.b(0xA9, 0x02).abs(0x20, SWITCH).abs(0x20, CODE2).b(0xA9, 0x04).abs(0x4C, SWITCH)
    tc = t.bytes()
    for bank in (2, 4):
        place(rom, bank, TRAMP, tc)
    # bank 2: the dispatcher, the turn, the bomb
    a = Asm(CODE2)
    a.b(0xC0, 0x01).br(0x90, "turn").br(0xF0, "bomb1").abs(0x4C, MORE)   # (Y 2+: lol_enemies2)
    a.label("bomb1").abs(0x4C, "bombupd")
    # a blue dodongo (X) turned: if no bomb of its own is out, drop one where it stands
    a.label("turn").abs(0xAD, HVE).b(0xC9, HC_AT).br(0x90, "t_r")
    a.b(0xA0, 0x0B)
    a.label("t_lp").abs(0xB9, 0x034F).b(0xC9, BOMB_TYPE).br(0xD0, "t_nx").b(0x8A).abs(0xD9, 0x0098).br(0xF0, "t_r")
    a.label("t_nx").b(0x88).br(0xD0, "t_lp")
    a.abs(0x20, FIND_EMPTY).br(0xF0, "t_r")                  # (Y: an empty slot)
    a.b(0x8A, 0x48)                                          # the dodongo
    a.b(0x98, 0xAA, 0xA9, BOMB_TYPE).abs(0x20, SET_TYPE)      # X: the bomb
    a.b(0xA9, 0x00).abs(0x9D, 0x0405)                        # (no spawn cloud)
    a.b(0x68, 0xA8)                                          # Y: the dodongo
    a.b(0x98).b(0x95, 0x98)                                  # its owner
    a.abs(0xB9, 0x0070).b(0x18, 0x69, 0x08, 0x95, 0x70)      # x + 8
    a.abs(0xB9, 0x0084).b(0x95, 0x84)
    a.b(0x98, 0xAA)                                          # X: the dodongo again
    a.label("t_r").b(0x60)
    # the bomb (X): state 0 set up, 1 lit, 2 big cloud (blast), 3 small clouds, then gone
    a.label("bombupd").b(0xB5, 0xAC).br(0xD0, "b_1")
    a.b(0xA9, 0xFF).abs(0x9D, 0x04B2).b(0xA9, 0x30, 0x95, 0x28, 0xF6, 0xAC)
    a.abs(0xBD, 0x04BF).b(0x09, 0x20).abs(0x9D, 0x04BF)                     # (no weapon checks)
    a.label("b_1").b(0xB5, 0x28).br(0xD0, "b_draw")
    a.b(0xB5, 0xAC, 0xC9, 0x03).br(0x90, "b_next").abs(0x4C, "b_gone")
    a.label("b_next")
    a.b(0xF6, 0xAC, 0xA9, 0x10, 0x95, 0x28)
    a.b(0xB5, 0xAC, 0xC9, 0x02).br(0xD0, "b_draw")
    a.b(0xA9, 0x10).abs(0x8D, 0x0603)                        # the blast sound
    a.label("b_draw").b(0xB5, 0xAC, 0xC9, 0x02).br(0xD0, "b_nohit")
    a.abs(0x20, "hit")                                      # the blast: Link takes type $29's damage
    a.label("b_nohit").b(0xB5, 0x70, 0x85, 0x00, 0xB5, 0x84, 0x85, 0x01)
    a.b(0xB5, 0xAC, 0x38, 0xE9, 0x01).abs(0x20, "draw")     # frame: 0 the bomb, 1 big, 2 small cloud
    a.b(0xB5, 0xAC, 0xC9, 0x02).br(0x90, "b_r")
    a.b(0xA0, 0x02)                                          # the other three clouds
    a.label("c_lp").b(0x98, 0x48, 0xA5, 0x15, 0x4A).br(0x90, "c_set").b(0x98, 0x18, 0x69, 0x06, 0xA8)
    a.label("c_set").b(0xB5, 0x84, 0x18).abs(0x79, "cy").b(0x85, 0x01)
    a.b(0xB5, 0x70, 0x18).abs(0x79, "cx").b(0x85, 0x00)
    a.b(0xB5, 0xAC, 0x38, 0xE9, 0x01).abs(0x20, "draw")
    a.b(0x68, 0xA8, 0x88).br(0x10, "c_lp")
    a.label("b_r").b(0x60)
    # the blast's reach, as Link's bombs' on monsters: within $18 of Link on both axes. Then the game's own
    # contact check (with the bomb moved onto Link for it) does the damage, the knock-back, the flashing.
    a.label("hit").b(0xA5, 0x70, 0x38, 0xF5, 0x70).abs(0x20, "abs").b(0xC9, 0x18).br(0xB0, "h_r")
    a.b(0xA5, 0x84, 0x38, 0xF5, 0x84).abs(0x20, "abs").b(0xC9, 0x18).br(0xB0, "h_r")
    a.b(0xB5, 0x70, 0x48, 0xB5, 0x84, 0x48, 0xA5, 0x70, 0x95, 0x70, 0xA5, 0x84, 0x95, 0x84)
    a.abs(0x20, CHECK_COLLISIONS)
    a.b(0x68, 0x95, 0x84, 0x68, 0x95, 0x70)
    a.label("h_r").b(0x60)
    a.label("abs").br(0xB0, "a_r").b(0x49, 0xFF, 0x69, 0x01)
    a.label("a_r").b(0x60)
    a.label("b_gone").b(0xA9, 0x00, 0x9D, 0x4F, 0x03, 0x95, 0xAC).b(0x60)
    # draw frame A of the bomb item slot at [00] / [01], red
    a.label("draw").b(0x85, 0x0C, 0xA9, 0x00, 0x85, 0x0F, 0xA9, 0x02, 0x85, 0x04, 0x85, 0x05, 0xA0, 0x01)
    a.abs(0x4C, WRITE_ITEM_SPRITES)
    a.label("cy").b(*CLOUD_Y)
    a.label("cx").b(*CLOUD_X)
    code = a.bytes()
    place(rom, 2, CODE2, code)
    global LABELS, TLABELS
    LABELS, TLABELS = a.labels, t.labels
    # bank 4: the dodongo's state update, remembering its direction
    w = Asm(WRAP4)
    w.b(0xB5, 0x98, 0x48).abs(0x20, DODONGO_STATE).b(0x68, 0xD5, 0x98).br(0xF0, "w_r").abs(0x20, t.labels["turned"])
    w.label("w_r").b(0xA0, 0x06).abs(0x4C, t.labels["bomb"] + 2)        # every frame: lol_enemies2 (Y 6)
    wc = w.bytes(); assert WRAP4 + len(wc) <= 0x90A0
    place(rom, 4, WRAP4, wc)
    patch(rom, 4, 0x98A9, bytes([0x20, DODONGO_STATE & 0xFF, DODONGO_STATE >> 8]), bytes([0x20, WRAP4 & 0xFF, WRAP4 >> 8]))
    # its palette
    p = Asm(PAL4)
    p.abs(0x20, LEVEL_PAL).abs(0xAD, HVE).b(0xC9, HC_AT).br(0x90, "p_r").b(0xA9, 0x01, 0x85, 0x04, 0x85, 0x05)
    p.label("p_r").b(0x60)
    pc = p.bytes(); assert PAL4 + len(pc) <= 0xBE00
    place(rom, 4, PAL4, pc)
    for site in (0x9A84, 0x9AF0):                  # Dodongo_Draw: the left side (or the only one), the right side
        patch(rom, 4, site, bytes([0x20, LEVEL_PAL & 0xFF, LEVEL_PAL >> 8]), bytes([0x20, PAL4 & 0xFF, PAL4 >> 8]))
    # no stun from a blast
    s = Asm(STUN4)
    s.abs(0xAD, HVE).b(0xC9, HC_AT).br(0xB0, "s_r").b(0xA9, 0x02, 0x95, 0xAC)
    s.label("s_r").b(0x60)
    sc = s.bytes(); assert STUN4 + len(sc) <= 0xBF50
    place(rom, 4, STUN4, sc)
    patch(rom, 4, 0x99F6, bytes.fromhex("a90295ac"), bytes([0x20, STUN4 & 0xFF, STUN4 >> 8, 0xEA]))
    # type $29: updated by the trampoline (UpdateObject's table, in bank 4 since v3), 4 hearts of damage
    import lol_v3core as V
    i = BANK(4) + V.TABLES4 + 3 - 0x8000 + 2 * 0x31                           # UpdateObject's $31 / $32
    assert rom[i:i + 4] == bytes([0xA9, 0x98, 0xA9, 0x98])
    entry = i - 2 * 0x31 + 2 * BOMB_TYPE
    assert rom[entry:entry + 2] == rom[i - 2 * 0x31:i - 2 * 0x31 + 2]          # DoNothing, like type 0
    tb = t.labels["bomb"]
    rom[entry:entry + 2] = bytes([tb & 0xFF, tb >> 8])
    d = BANK(1) + DAMAGE_TABLE - 0x8000 + BOMB_TYPE
    assert rom[d] == 0x80
    rom[d] = 0x04
    notes.append(f"dodongos: blue at 10 containers, a bomb on each turn ({len(code)} bytes in bank 2 at ${CODE2:04X})")

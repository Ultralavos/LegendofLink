"""Legend of Link: dungeons A-F (the second quest's levels 1-6) inside the first-quest game.

Entering: an overworld screen whose destination is $0A-$0F loads the second quest's level AF_LEVELS[d - $0A];
while inside, the game runs as the second quest (QuestNumbers[slot] = 1), INSIDE = 1, and the compass / map bits
($0667 / $0668) are swapped with A-F's own ($0679 / $067A). The next overworld load switches everything back.

Room memory: the second quest's levels 1-6 use LIVE (their LevelInfo's room flags address); the third save slot's
room flag area holds LIVE and each of the two files' copies. Loading a file copies its copy into LIVE (clearing it
first for a new file: MARKER), saving copies LIVE back. The third slot can't be registered.
"""

INSIDE = 0x0678                 # 1 while in A-F (saved)
AF_COMPASS, AF_MAP = 0x0679, 0x067A
MARKER = 0x067B                 # $5A once this file's A-F memory is set up
MARKER_VALUE = 0x5A
QUEST = 0x062D                  # QuestNumbers,Y
SLOT = 0x16
LIVE = 0x6392                   # the third slot's room flags (0x180 bytes): LIVE, then file 1's and file 2's copies
STORES = (0x6412, 0x6492)
# Destination $0A + n (A-F) -> the second quest's level
AF_LEVELS = (1, 3, 2, 5, 4, 6)
# The overworld: A D8, B D5, C H5, D C16, E A12, F C3
AF_SCREENS = {"D8": 0, "D5": 1, "H5": 2, "C16": 3, "A12": 4, "C3": 5}

BANK = lambda b: 16 + b * 0x4000


def screen(name):
    return "ABCDEFGH".index(name[0]) * 16 + int(name[1:]) - 1


class Asm:
    """A tiny two-pass assembler: b(bytes), abs(op, addr|label), br(op, label), label(name)."""

    def __init__(self, cpu):
        self.cpu, self.code, self.labels, self.fix = cpu, bytearray(), {}, []

    def b(self, *xs):
        self.code.extend(xs); return self

    def abs(self, op, a):
        self.code.append(op)
        if isinstance(a, str):
            self.fix.append((len(self.code), a, "abs")); self.code.extend(b"\0\0")
        else:
            self.code.extend((a & 0xFF, a >> 8))
        return self

    def br(self, op, name):
        self.code.append(op); self.fix.append((len(self.code), name, "rel")); self.code.append(0); return self

    def label(self, name):
        assert name not in self.labels, f"label {name} defined twice"
        self.labels[name] = self.cpu + len(self.code); return self

    def bytes(self):
        for at, name, kind in self.fix:
            t = self.labels[name]
            if kind == "rel":
                d = t - (self.cpu + at + 1); assert -128 <= d < 128, name; self.code[at] = d & 0xFF
            else:
                self.code[at], self.code[at + 1] = t & 0xFF, t >> 8
        return bytes(self.code)


def place(rom, bank, cpu, code):
    at = BANK(bank) + cpu - 0x8000
    assert all(x == 0xFF for x in rom[at:at + len(code)]), f"bank {bank} ${cpu:04X} isn't free"
    rom[at:at + len(code)] = code


def patch(rom, bank, cpu, old, new):
    at = BANK(bank) + (cpu - (0xC000 if bank == 7 else 0x8000))
    assert rom[at:at + len(old)] == old, (hex(cpu), rom[at:at + len(old)].hex(), old.hex())
    assert len(new) <= len(old)
    rom[at:at + len(old)] = new + b"\xEA" * (len(old) - len(new))


def swap_code(a: Asm):
    """Swap the compass and map bytes with A-F's."""
    for live, mine in ((0x0667, AF_COMPASS), (0x0668, AF_MAP)):
        a.abs(0xAD, live).abs(0xAE, mine).abs(0x8D, mine).abs(0x8E, live)   # LDA / LDX / STA / STX


def apply(rom: bytearray, notes: list) -> None:
    # --- bank 5: entering (LSR / LSR / STA CurLevel at $B49F) and the overworld load ($E9F7's LDA #1 / STA $17)
    B5 = 0xAC2A
    a = Asm(B5)
    a.label("enter").b(0x4A, 0x4A, 0xC9, 0x0A).br(0x90, "e_norm")          # LSR / LSR / CMP #$0A / BCC
    a.b(0xE9, 0x0A, 0xAA).abs(0xBD, "levels").b(0x48)                         # SBC #$0A / TAX / LDA levels,X / PHA
    a.b(0xA9, 0x01).abs(0x8D, INSIDE).b(0xA4, SLOT).abs(0x99, QUEST)         # INSIDE = quest = 1
    swap_code(a)
    a.b(0x68)                                                                 # PLA
    a.label("e_norm").b(0x85, 0x10, 0x60)                                     # STA CurLevel / RTS
    a.label("owload").b(0xA5, 0x10).br(0xD0, "o_done")                        # loading the overworld?
    a.abs(0xAD, INSIDE).br(0xF0, "o_done")
    a.b(0xA9, 0x00).abs(0x8D, INSIDE).b(0xA4, SLOT).abs(0x99, QUEST)         # INSIDE = quest = 0
    swap_code(a)
    a.label("o_done").b(0xA9, 0x01, 0x85, 0x17, 0x60)                         # LDA #1 / STA $17 / RTS
    a.label("levels").b(*AF_LEVELS)
    code = a.bytes(); place(rom, 5, B5, code)
    patch(rom, 5, 0xB49F, bytes([0x4A, 0x4A, 0x85, 0x10]), bytes([0x20, a.labels["enter"] & 0xFF, a.labels["enter"] >> 8]))
    patch(rom, 7, 0xE9F7, bytes([0xA9, 0x01, 0x85, 0x17]), bytes([0x20, a.labels["owload"] & 0xFF, a.labels["owload"] >> 8]))

    # --- bank 2: loading a file (JMP $EBA1 at $A635), saving (JSR $9D2A at $A72B), registering (slot 3 locked)
    B2 = 0xAF90
    KEEP3 = 0xBB60
    a = Asm(B2)

    import lol_saveblock as SB
    import lol_v3core as V3
    R = SB.install(rom)                                                       # (bank 0, far-called)
    a.label("load")
    a.abs(0xAD, MARKER).b(0xC9, MARKER_VALUE).br(0xF0, "l_old")              # set up already?
    a.b(0xA9, MARKER_VALUE).abs(0x8D, MARKER)
    a.b(*V3.far(0, R["clear"]))                                              # a new file: its saved memory cleared
    from lol_odds import STORE, PER_FILE                                      # and the odds' saved bytes
    a.b(0xA0, PER_FILE + 1, 0xA9, 0x00).label("l_oc").abs(0x99, STORE).b(0x88).br(0x10, "l_oc")   # (+ UP4 / UP5)
    import lol_entrances                                                      # and the entrances' choices
    a.abs(0x20, lol_entrances.CLEAR2)
    import os
    if os.environ.get("LOL_DEBUG"):                                           # debug build only: a new file starts
        a.b(0xA9, 0x01).abs(0x8D, 0x065C).abs(0x8D, 0x0665).abs(0x8D, 0x065B)  # with the recorder, the bracelet,
        a.b(0xA9, 250).abs(0x8D, 0x066D)                                       # the blue candle and 250 rupees
    a.abs(0x4C, "l_copy")
    a.label("l_old")
    a.b(*V3.far(0, R["migrate"]))                                            # (a file from before stage 4)
    a.label("l_copy")
    a.b(*V3.far(0, R["to_work"]))                                            # saved -> working
    a.abs(0x4C, 0xEBA1)                                                       # JMP (the vanilla tail)
    a.label("save")
    a.b(*V3.far(0, R["to_saved"]))                                           # working -> saved
    a.abs(0x4C, 0x9D2A)                                                       # JMP (the vanilla call)
    # The cursor's next row: in elimination mode ($12 = $0F) the third row is skipped here; registering skips it
    # through the game's own used-slot loop ($A24E, reg_used), which keeps the arrow's y ($84) in step.
    a.label("reg_next").b(0xE6, SLOT, 0xA5, 0x12, 0xC9, 0x0F).br(0xD0, "r_w")
    a.b(0xA4, SLOT, 0xC0, 0x01).br(0xD0, "r_w").b(0xA9, 0x03, 0x85, SLOT)         # (one file: past rows 2 and 3)
    a.label("r_w").b(0xA4, SLOT, 0xC0, 0x04).br(0xD0, "r_ret").b(0xA0, 0x00, 0x84, SLOT)
    a.label("r_ret").b(0x60)
    a.label("reg_used").b(0xC0, 0x01).br(0xF0, "u_yes").b(0xC0, 0x02).br(0xF0, "u_yes").abs(0xB9, 0x0633).b(0x60)   # the second and third count as used
    a.label("u_yes").b(0xA9, 0x01, 0x60)
    a.label("keep3").abs(0x4C, KEEP3)
    a.label("row3").b(0xE6, SLOT, 0xE6, 0x13, 0x60)
    code = a.bytes(); place(rom, 2, B2, code)
    # Saving copies the quest number to the file (LDA QuestNumbers,Y / LDY #0 / STA ($CC),Y): it is always saved
    # as the first quest, so a file saved in A-F doesn't show the second quest's sword on the menu
    qs = rom.index(bytes.fromhex("993306b92d06a00091cc"), BANK(2), BANK(2) + 0x4000) + 3
    rom[qs:qs + 3] = bytes([0xA9, 0x00, 0xEA])
    L = a.labels
    patch(rom, 2, 0xA635, bytes([0x4C, 0xA1, 0xEB]), bytes([0x4C, L["load"] & 0xFF, L["load"] >> 8]))
    patch(rom, 2, 0xA72B, bytes([0x20, 0x2A, 0x9D]), bytes([0x20, L["save"] & 0xFF, L["save"] >> 8]))
    patch(rom, 2, 0xA20F, bytes.fromhex("e616a416c004d004a0008416"), bytes([0x20, L["reg_next"] & 0xFF, L["reg_next"] >> 8, 0xA4, SLOT]))
    patch(rom, 2, 0xA24E, bytes([0xB9, 0x33, 0x06]), bytes([0x20, L["reg_used"] & 0xFF, L["reg_used"] >> 8]))
    # The menu's check of every file (bank 2 $A2A0: a file whose checksum fits is copied over its second copy, else
    # restored or erased) would wipe the third file's room flags, A-F's memory: it checks the first two only.
    # keep3 (the menu's erase of every unregistered file, Y = its slot): files 2 and 3 are kept - no deaths,
    # their names and room flags (SRAM the generated levels use) untouched. Y kept (the caller loops on it).
    k3 = Asm(KEEP3)
    k3.b(0xB1, 0x06).abs(0x99, 0x0633).br(0xD0, "k_ret")                    # LDA (active),Y / STA / BNE
    k3.b(0xC0, 0x01).br(0xF0, "k_yes").b(0xC0, 0x02).br(0xF0, "k_yes").b(0xA9, 0x00)   # the first: Z set (erase)
    k3.label("k_ret").b(0x60)
    # (2026-11-24: no longer blanks their names: file 2's name holds lol_stats' clock, lol_uptable's UP6 and Zombie
    # Link's bytes, file 3's Zombie Link's scratch; the blank tile $24 there gave the brain potion and took X-ray)
    k3.label("k_yes").b(0xA9, 0x00, 0x91, 0x0A)
    k3.b(0xA9, 0x01, 0x60)                                                  # Z clear: kept
    place(rom, 2, KEEP3, k3.bytes())
    # one file now: the menu's file check stops after file 1, and files 2 and 3 never count as active
    CHK1 = 0xBB40
    c1 = Asm(CHK1)
    c1.b(0xA9, 0x00).abs(0x8D, 0x0634).abs(0x8D, 0x0635)
    c1.b(0xA2, 0x07, 0xA9, 0x24).label("nm").abs(0x9D, 0x0640).b(0xCA).br(0x10, "nm")   # file 2's name: blank
    c1.b(0xA5, SLOT, 0xC9, 0x01, 0x60)
    place(rom, 2, CHK1, c1.bytes())
    patch(rom, 2, 0xA2FE, bytes([0xA5, SLOT, 0xC9, 0x03]), bytes([0x20, CHK1 & 0xFF, CHK1 >> 8, 0xEA]))
    # The menu's load ($9069) erases every unregistered file ($A35D): the third file's room flags are kept.
    patch(rom, 2, 0x9069, bytes([0xB1, 0x06, 0x99, 0x33, 0x06]), bytes([0x20, L["keep3"] & 0xFF, L["keep3"] >> 8]))
    # The third file disappears from the menus: its row (the third DrawFileRow, $A4C4, in the menu's step table)
    # and its Link (the menu's Link loop, CMP #3 at $A69C).
    tbl = rom.index(bytes.fromhex("c4a4c4a4c4a41ea5"), BANK(2), BANK(2) + 0x4000) + 4
    rom[tbl:tbl + 2] = bytes([L["row3"] & 0xFF, L["row3"] >> 8])
    rom[tbl - 2:tbl] = bytes([L["row3"] & 0xFF, L["row3"] >> 8])                 # and the second (one file)
    patch(rom, 2, 0xA69C, bytes([0xC9, 0x03]), bytes([0xC9, 0x01]))
    patch(rom, 2, 0x9EC8, bytes([0xB9, 0x33, 0x06]), bytes([0x20, L["reg_used"] & 0xFF, L["reg_used"] >> 8]))

    # --- the second quest's levels 1-6 keep their rooms' memory in LIVE (LevelInfo + $31, replaced from $29 on)
    sizes = 0x183C6                     # the 2Q replacement arrays' sizes (PRG1; lol_dungeons rewrites 1-6)
    addrs = sizes - 18                                                        # and their pointers (bank 6)
    for lv in range(1, 7):
        p = rom[addrs + 2 * (lv - 1)] | rom[addrs + 2 * (lv - 1) + 1] << 8
        at = BANK(6) + p - 0x8000 + (0x31 - 0x29)
        assert rom[at:at + 2] == bytes([0xFF, 0x06]), (lv, rom[at:at + 2].hex())
        rom[at:at + 2] = bytes([LIVE & 0xFF, LIVE >> 8])
        num = BANK(6) + p - 0x8000 + (0x33 - 0x29)                           # LevelInfo_LevelNumber: LEVEL-A..F
        assert 1 <= rom[num] <= 6, (lv, rom[num])
        rom[num] = 0x0A + AF_LEVELS.index(lv)

    # --- the overworld: A-F's entrances (destination $0A + n, in both quests' visibility)
    ow = 0x18410
    for name, n in AF_SCREENS.items():
        s = screen(name)
        rom[ow + 0x80 + s] = ((0x0A + n) << 2) | (rom[ow + 0x80 + s] & 0x03)
        rom[ow + 0x280 + s] &= 0x3F                                          # quest field: both
    # The recorder: its list's first entry (E3's pond) works only in the first quest, the rest only in the second.
    # D1 (F) moves to the second entry and the first two count as the first quest's ($EF98: CPY #0 / BNE -> CPY #2 /
    # BCS).
    if "D1" in AF_SCREENS:
        lst = BANK(7) + 0xEF66 - 0xC000
        entries = list(rom[lst:lst + 11])
        assert entries[0] == 0x42 and screen("D1") in entries, entries
        entries.remove(screen("D1")); entries.insert(1, screen("D1"))
        rom[lst:lst + 11] = bytes(entries)
        patch(rom, 7, 0xEF98, bytes([0xC0, 0x00, 0xD0, 0x05]), bytes([0xC0, 0x02, 0xB0, 0x05]))
    notes.append("A-F: " + ", ".join(f"{chr(65 + n)} {nm} (2Q L{AF_LEVELS[n]})" for nm, n in AF_SCREENS.items()))




def apply_pre_load(rom: bytearray, notes: list) -> None:
    """Mode 2 (loading a level) starts with JSR $EA00 at $E97E: before it, loading the overworld ($10 = 0) puts the
    first quest back (always: Link's overworld is the first quest's) and, coming out of A-F, swaps the compass and map
    back. Done any later, the overworld would load as the second quest's (its LevelInfo, and the 2Q screen changes
    at H5/H6, A12, D13... that bank 6 $8109 writes at the end of the load)."""
    import lol_v3core as V
    def build(org):
        a = Asm(org)
        a.label("pre").b(0xA5, 0x10).br(0xD0, "p_go")                          # the overworld?
        a.b(0xA4, SLOT).abs(0x99, QUEST)                                        # quest = 0 (A = 0)
        a.abs(0xAD, INSIDE).br(0xF0, "p_go")
        a.b(0xA9, 0x00).abs(0x8D, INSIDE)
        swap_code(a)
        a.label("p_go").b(0x60)
        return a
    body = V.put0(rom, build)                                                    # bank 0, reached by a far call
    pre = body.labels["pre"]
    stub = V.put7(rom, lambda org: Asm(org).b(*V.far(0, pre)).abs(0x4C, 0xEA00))
    code = body.bytes()
    patch(rom, 7, 0xE97E, bytes([0x20, 0x00, 0xEA]), bytes([0x20, stub.cpu & 0xFF, stub.cpu >> 8]))
    notes.append(f"overworld loads as the first quest ({len(code)} bytes in bank 0 at ${pre:04X})")

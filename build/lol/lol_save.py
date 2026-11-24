"""Legend of Link: the game saves itself whenever Link takes an old man's choice (the take-any person $6B) or buys
from a shop (the potion shop, shops A-D).

Bank 1's cave take (after JSR $730C, the taken flag, and the item's take) ends 'LDA #$40 / STA $29'; that becomes
JSR to a helper here: for those persons it deducts the price still counting down ($067E) at once, and runs bank 2's
save steps ($A6B8, then $A734) through a bank-7 trampoline, with NMI off (the save outlasts a frame). It keeps
Link's hearts (the save step refills them in RAM), the zero page it uses ($00-$0F, $C0-$CF, $13), and saves the
file as the first quest (A-F run in the second; a file always starts on the 1Q overworld)."""
from lol_af import Asm, place, patch, BANK

HELPER = 0x9F40                         # bank 1 free (after lol_swords' code)
T1, T2 = 0xED94, 0xFAE4                 # bank 7 free: switch to bank 2 / save / back to bank 1
T3 = 0xFFC0                             # bank 7 free: bank 6's InitMode2_Sub0 (copies the level block to WRAM)
RELOAD = 0x8047
T4, RELOAD_INFO = 0xFF42, 0x8070      # bank 7 free: bank 6's InitMode2_Sub1 (the level info; second file's save covers it)
Q2_FIX = 0xAF28                         # bank 6 free: the level info, then the 2Q replacements
QUEST_KEEP = 0x017F                     # (stack page, unused)
SAVING = 0x01A7                         # (stack page, unused): 1 while the save reloads the level (no picture load)
SAVERS = (0x6B, 0x72, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A)   # take-any (old man choices), potion shop, H1's upgrades, shops A-D


def apply(rom: bytearray, notes: list) -> None:
    tr1 = bytes([0xA9, 0x02, 0x20, 0xAC, 0xFF, 0x20, 0xB8, 0xA6, 0x4C, T2 & 0xFF, T2 >> 8])
    tr2 = bytes([0x20, 0x34, 0xA7, 0xA9, 0x01, 0x20, 0xAC, 0xFF, 0x60])
    tr3 = bytes([0xA9, 0x06, 0x20, 0xAC, 0xFF, 0x20, RELOAD & 0xFF, RELOAD >> 8, 0xA9, 0x01, 0x4C, 0xAC, 0xFF])
    rl = BANK(6) + RELOAD - 0x8000
    assert rom[rl:rl + 10] == bytes.fromhex("a5100aaaa416b92d06d0"), rom[rl:rl + 10].hex()
    # The level info again, then the second quest's replacements (UpdateMode2Load_Full, $8109: nothing in the first
    # quest). Without them, saving in A-F (E's and F's old men) left the first quest's level info in place: its map,
    # its item positions and Levels 1-6's room flags ($06FF), which A-F's rooms then wrote over.
    assert rom[BANK(6) + Q2_FIX - 0x8000:BANK(6) + Q2_FIX - 0x8000 + 6] == b"\xff" * 6
    rom[BANK(6) + Q2_FIX - 0x8000:BANK(6) + Q2_FIX - 0x8000 + 6] = bytes([0x20, RELOAD_INFO & 0xFF, RELOAD_INFO >> 8,
                                                                         0x4C, 0x09, 0x81])
    q2 = BANK(6) + 0x8109 - 0x8000
    assert rom[q2:q2 + 6] == bytes.fromhex("a416b92d06f0"), rom[q2:q2 + 6].hex()
    tr4 = bytes([0xA9, 0x06, 0x20, 0xAC, 0xFF, 0x20, Q2_FIX & 0xFF, Q2_FIX >> 8, 0xA9, 0x01, 0x4C, 0xAC, 0xFF])
    ri = BANK(6) + RELOAD_INFO - 0x8000
    assert rom[ri:ri + 5] == bytes.fromhex("a5100aaabd"), rom[ri:ri + 5].hex()
    for cpu, b in ((T1, tr1), (T2, tr2), (T3, tr3), (T4, tr4)):
        at = BANK(7) + cpu - 0xC000
        assert all(x == 0xFF for x in rom[at:at + len(b)]), hex(cpu)
        rom[at:at + len(b)] = b
    a = Asm(HELPER)
    a.b(0xA9, 0x40, 0x85, 0x29)                                          # (the replaced LDA #$40 / STA $29)
    a.abs(0xAD, 0x0350)
    for p in SAVERS:
        a.b(0xC9, p).br(0xF0, "go")
    a.b(0x60)
    a.label("go").b(0x8A, 0x48)                                          # TXA / PHA
    a.abs(0xAD, 0x066D).b(0x38).abs(0xED, 0x067E).br(0xB0, "rs").b(0xA9, 0x00)   # rupees - pending (floor 0)
    a.label("rs").abs(0x8D, 0x066D).b(0xA9, 0x00).abs(0x8D, 0x067E)
    a.abs(0xAD, 0x066F).b(0x48).abs(0xAD, 0x0670).b(0x48)               # keep the hearts
    a.b(0xA4, 0x16).abs(0xB9, 0x062D).abs(0x8D, QUEST_KEEP).b(0xA9, 0x00).abs(0x99, 0x062D)   # quest -> first while saving
    a.b(0xA2, 0x0F).label("ps").b(0xB5, 0x00, 0x48, 0xB5, 0xC0, 0x48, 0xCA).br(0x10, "ps")
    a.b(0xA5, 0x13, 0x48, 0xA5, 0x11, 0x48)
    a.b(0xA5, 0xFF, 0x29, 0x7F).abs(0x8D, 0x2000)                       # NMI off
    a.b(0xA9, 0x01).abs(0x8D, SAVING)
    a.abs(0x20, T1)
    a.b(0xA4, 0x16).abs(0xAD, QUEST_KEEP).abs(0x99, 0x062D)              # the quest back
    a.abs(0x20, T3)                                                     # the level block again (the save's copy
                                                                        # used its WRAM, $6880-$6A8F)
    a.abs(0x20, T4)                                                     # and the level info (file 2's world flags
    a.b(0xA9, 0x00).abs(0x8D, SAVING)
                                                                        # reach $6C0F)
    # ... and the save's file-B bytes at $6D90-$6D9B (slot flags, death count, quest) sit on bank 1's code copied
    # to WRAM (the cave entry's LDA #$70 / STA ObjX ...): copy those 16 bytes back from the ROM ($A600-$A60F)
    a.b(0xA2, 0x0F).label("rc").abs(0xBD, 0xA600).abs(0x9D, 0x6D90).b(0xCA).br(0x10, "rc")
    a.abs(0xAD, 0x2002).b(0xA5, 0xFF).abs(0x8D, 0x2000)                 # NMI back on
    a.b(0x68, 0x85, 0x11, 0x68, 0x85, 0x13)
    a.b(0xA2, 0x00).label("pp").b(0x68, 0x95, 0xC0, 0x68, 0x95, 0x00, 0xE8, 0xE0, 0x10).br(0xD0, "pp")
    a.b(0x68).abs(0x8D, 0x0670).b(0x68).abs(0x8D, 0x066F)
    a.b(0x68, 0xAA, 0x60)                                               # PLA / TAX / RTS
    code = a.bytes()
    place(rom, 1, HELPER, code)
    patch(rom, 1, 0x8926, bytes([0xA9, 0x40, 0x85, 0x29]), bytes([0x20, HELPER & 0xFF, HELPER >> 8]))
    notes.append(f"autosave on old man choices and shop buys (bank 1 ${HELPER:04X}, {len(code)} bytes)")

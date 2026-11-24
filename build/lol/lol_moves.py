"""Legend of Link: first-quest overworld moves (with A-F's own entrances in lol_af.AF_SCREENS).

  Level 1 A16 (the old 100 rupee cave), Level 3 C13 (bomb wall), Level 5 B12 (the second quest's power bracelet
  rock), Level 6 B10 (the second quest's bomb wall, past the ladder); 30 rupee secrets at H6 and E8, 100 at H12.
Each screen's destination (bits 7-2 of OverworldAttrs + $80) is set and its quest field cleared (both quests). The
recorder's whirlwind (WhirlwindPrevRoomIdList: the screen left of each level 1-8) follows the levels."""
from lol_af import BANK, screen

OW = 0x18410
LEVEL = {1: "A16", 3: "C13", 5: "B12", 6: "B10"}
SECRETS = {"H6": 0x21, "E8": 0x21, "H12": 0x22, "A15": 0x22}   # MEDIUM (30) / LARGE (100) secret
SHOWN = {"B2": 0x18}                                  # the second quest's B2 (power bracelet rock): its cave in the
                                                      # first quest too (the letter cave's: B2's upgrade shop)
WHIRL = 0x6020                                        # file: WhirlwindPrevRoomIdList (bank 1)
LAND_Y = {3: 0xAD}                                    # C13: below the mound (its middle row is rock)


def apply(rom: bytearray, notes: list) -> None:
    assert rom[WHIRL:WHIRL + 8] == bytes([0x36, 0x3B, 0x73, 0x44, 0x0A, 0x21, 0x41, 0x6C])
    for lv, name in LEVEL.items():
        s = screen(name)
        rom[OW + 0x80 + s] = (lv << 2) | (rom[OW + 0x80 + s] & 0x03)
        rom[OW + 0x280 + s] &= 0x3F
        rom[WHIRL + lv - 1] = s - 1
    ys = rom.find(bytes.fromhex("8dad8d8dad8dad5d"), BANK(1), BANK(2))
    assert ys > 0
    for lv, y in LAND_Y.items():
        rom[ys + lv - 1] = y
    for name, d in SHOWN.items():
        s = screen(name)
        assert rom[OW + 0x80 + s] >> 2 == d, (name, hex(rom[OW + 0x80 + s]))
        rom[OW + 0x280 + s] &= 0x3F
    for name, d in SECRETS.items():
        s = screen(name)
        rom[OW + 0x80 + s] = (d << 2) | (rom[OW + 0x80 + s] & 0x03)
        rom[OW + 0x280 + s] &= 0x3F
    # caves moved: H1's upgrade cave (hint shop 2) to C9's burned bush (its 30 secret to H1); B11's (hint shop 1)
    # to F9, the second quest's recorder spot (shown in the first quest now); a 30 secret behind B11's waterfall
    for name, old, new in (("H1", 0x1C, 0x21), ("C9", 0x21, 0x1C), ("B11", 0x1B, 0x21), ("F9", 0x21, 0x1B)):
        s = screen(name)
        assert rom[OW + 0x80 + s] >> 2 == old, (name, hex(rom[OW + 0x80 + s]))
        rom[OW + 0x80 + s] = (new << 2) | (rom[OW + 0x80 + s] & 0x03)
        rom[OW + 0x280 + s] &= 0x3F
    # The recorder: WieldFlute's list (FluteRoomSecretsOW) reveals its first entry in the first quest and the others
    # in the second; F9 ($58) moves to the second entry and the check becomes "entry < 2" (CPY #$02 / BCS)
    fl = rom.find(bytes.fromhex("4206292b303a3c58606e72"), BANK(7))
    assert fl > 0
    rom[fl + 1], rom[fl + 7] = 0x58, 0x06
    ck = rom.find(bytes.fromhex("c000d0"), fl, fl + 0x60)
    assert ck > 0
    rom[ck + 1], rom[ck + 2] = 0x02, 0xB0
    # the overworld's two ground items: the coast heart container (F16) becomes a bomb upgrade ($24), the Armos'
    # power bracelet an orange XP potion ($29, +15): bank 5 / bank 4's LDA #item
    for name, at, old, new in (("coast", 0x1789A, 0x1A, 0x24), ("Armos", 0x10D05, 0x14, 0x29)):
        assert rom[at - 1:at + 1] == bytes([0xA9, old]), (name, rom[at - 1:at + 1].hex())
        rom[at] = new
    # potions only in dungeons: every potion shop ($1A) becomes a 10 rupee secret ($23), its quest field kept
    potions = [s for s in range(0x80) if rom[OW + 0x80 + s] >> 2 == 0x1A]
    for s in potions:
        rom[OW + 0x80 + s] = (0x23 << 2) | (rom[OW + 0x80 + s] & 0x03)
    notes.append(f"overworld: {len(potions)} potion shops are 10 rupee secrets")
    notes.append("overworld: " + ", ".join(f"L{lv} {n}" for lv, n in LEVEL.items()) + "; secrets "
                 + ", ".join(f"{n} {30 if d == 0x21 else 100}" for n, d in SECRETS.items()))

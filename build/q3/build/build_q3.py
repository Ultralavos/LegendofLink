"""3Q test patch for The Legend of Zelda (US PRG1): Levels 1 and 2 and the overworld so far.

    python3 build_q3.py PRG1.nes OUT.ips OUT.nes

Parses the PRG1 ROM with ZORA's model (in PRG0's layout). Vanilla Levels 1 and 2 are cleared, the rooms the new
Levels 1 and 2 take from Levels 3-6 are cleared, and every door of another level into them is walled. The new
levels, their staircases, the overworld changes and the Like Like / Wallmaster group swap are written, the world is
serialized back (ZORA's serializer, no ZORA patches) and moved back to PRG1's layout.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_mock as base  # noqa: E402  (Level 1's tables, the helpers and the overworld column edits)

from zora.generate.shapes.minimap import command_block, drawn_commands, synthesize_minimap  # noqa: E402
from zora.model.enums import (BossSound, Destination, Direction, Enemy, Item, OverworldDirection,  # noqa: E402
                              RoomType)
from zora.model.levels import Level  # noqa: E402
from zora.model.overworld import EntranceType, ShopItem  # noqa: E402
from zora.model.enums import QuestVisibility  # noqa: E402
from zora.model.rooms import (EnemyInfo, EnemySpec, ItemInfo, LayoutInfo, Room, SecretInfo,  # noqa: E402
                              StaircaseRoom, WallSet)
from zora.model.sprites import EnemySpriteSet  # noqa: E402
from zora.rom.base_rom import recognized_player_rom, using_player_rom  # noqa: E402
from zora.rom.game_config import GameConfig  # noqa: E402
from zora.rom.parse.rom_file import original_bins_from_rom, parse_rom  # noqa: E402
from zora.rom.serialize.game_world import serialize_game_world  # noqa: E402

E, R, A, P = base.E, base.R, base.A, base.P
OPEN, WALL, WALK, LOCK, SHUT = base.OPEN, base.WALL, base.WALK, base.LOCK, base.SHUT
BOMB = base.W.BOMB_HOLE
cell = base.cell
GRID = base.GRID
QTY, COUNT = base.QTY, base.COUNT

# ---------------------------------------------------------------------------------------------------------------
# Level 2 (q3/level_2.json). Item spots A 8,9  B 11,8  C 2,6  D 5,9.
L2_SPOTS = [0x89, 0xB8, 0x26, 0x59]
# Only four mixed-list codes are free, so: C2 uses vanilla $7A (3 red + 3 blue Goriyas at count 6), and L1's G9
# shares B3's list at count 8 (2 Bubbles, 3 Ropes, 3 Like Likes); B3 at count 6 gets 2 Bubbles, 3 Ropes, 1 Like Like.
L2_MIXED = {
    # Bubbles and traps go first in a mixed list: the game respawns a list's first (count - killed) members, so
    # anything after the killable enemies would vanish on re-entry once they were killed.
    "G6": [E.RED_BUBBLE] * 2 + [E.BLUE_BUBBLE] + [E.BLUE_GORIYA] * 3,
    "B3": [E.BUBBLE] * 2 + [E.ROPE] * 3 + [E.LIKE_LIKE] * 3,   # B3 (count 6) and L1 G9 (count 8)
}
L2_MIXED_COUNT = {"G6": 6, "B3": 6, "C2": 6}
SHARED = {"C2": Enemy(0x7A)}
L2_ROOMS = {   # layout, push, enemy or mixed key, count, item, position, trigger, walls N E S W, inner palette
    "H6": (R.ENTRANCE_ROOM, False, E.NOTHING, 3, Item.NOTHING, P.POSITION_A, A.NONE, (OPEN, WALL, OPEN, WALL), 3),
    "G6": (R.DOUBLE_BLOCK, True, "G6", None, Item.NOTHING, P.POSITION_A, A.BLOCK_STAIRS, (WALL, WALL, OPEN, WALL), 2),
    "B2": (R.DIAMOND_STAIR_ROOM, True, E.BLUE_KEESE, 6, Item.BOMBS, P.POSITION_B, A.ALL_DEAD_ITEM,
           (OPEN, OPEN, WALL, WALL), 2),
    "B3": (R.GRID_ROOM, False, "B3", None, Item.COMPASS, P.POSITION_B, A.NONE, (OPEN, WALL, WALL, OPEN), 2),
    "A3": (R.PLAIN_ROOM, False, E.MOLDORM, 0, Item.NOTHING, P.POSITION_A, A.ALL_DEAD, (WALL, SHUT, SHUT, SHUT), 2),
    "A4": (R.FOUR_FIREBALL_ROOM, False, E.SINGLE_DIGDOGGER, 0, Item.HEART_CONTAINER, P.POSITION_A, A.ALL_DEAD_ITEM,
           (WALL, SHUT, WALL, OPEN), 2),
    "A5": (R.TRIFORCE_ROOM, False, E.NOTHING, 3, Item.TRIFORCE, P.POSITION_A, A.NONE, (WALL, WALL, WALL, OPEN), 2),
    "A2": (R.POINTLESS_MOAT_ROOM, False, E.RED_GORIYA, 6, Item.MAP, P.POSITION_C, A.ALL_DEAD_ITEM, (WALL, OPEN, OPEN, OPEN), 2),
    "A1": (R.BLACK_ROOM, False, E.ELDER, 3, Item.NOTHING, P.POSITION_A, A.NONE, (WALL, OPEN, BOMB, WALL), 0),
    "B1": (R.FOUR_FIREBALL_ROOM, False, E.BLUE_KEESE, 8, Item.KEY, P.POSITION_A, A.ALL_DEAD_ITEM,
           (BOMB, WALL, OPEN, WALL), 2),
    "C1": (R.VERTICAL_ROWS, False, E.ROPE, 8, Item.NOTHING, P.POSITION_A, A.NONE, (OPEN, LOCK, WALK, WALL), 2),
    "C2": (R.DOUBLE_SIX_BLOCK_ROOM, False, "C2", None, Item.BOMBS, P.POSITION_A, A.ALL_DEAD_ITEM, (WALK, WALL, WALL, LOCK), 2),
    "D1": (R.AQUAMENTUS_ROOM, False, E.AQUAMENTUS, 0, Item.KEY, P.POSITION_A, A.ALL_DEAD_ITEM, (WALK, WALL, SHUT, WALL), 2),
    "E1": (R.NARROW_STAIR_ROOM, False, E.RED_BUBBLE, 6, Item.NOTHING, P.POSITION_A, A.NONE, (OPEN, WALL, WALL, WALL), 2),
}
# One-ways: C2's north into B2 (B2's south is a wall). A3's shutters face open doors on A2/A4/B3's sides.
L2_TEXTS = {20: ["TRY PLAYING MUSIC IN", "THE DESERT AND AT", "PONDS"],   # A1: ELDER in group A -> quote 20
            21: ["THE BLUE FLAME WILL", "ONLY BURN DEAD BUSHES."],       # L4 D4: ELDER in group B -> quote 21
            18: ["FEED ME, SEYMOUR!"]}                                     # the hungry Goriya (L8 E1)
OW_TEXTS = {6: ["GOTTA HAVE HEART!"],       # A15, the letter cave (now a heart container)
            1: ["IF YOU HAVE ENOUGH", "HEARTS YOU CAN HAVE", "THIS!"],   # both heart-gated caves (white and magical sword caves)
            # C3's paid hints (hint shop 1): 25 -> quote 24, 50 -> quote 28 (both freed), 100 -> quote 11
            24: ["THERE IS A SECRET AT", "THE SOUTH EAST COAST."],
            28: ["THE POWER TO PUSH", "ROCKS LIES WHERE", "GANON ONCE LIVED."],
            11: ["CHECK UNDER THE", "GREY ARMOS."],
            3: ["WITHOUT THE RED", "CANDLE THAT BUSH", "REALLY IS A DEAD END."],   # B13's hint cave (lost hills hint)
            # C5's paid hints (hint shop 2, H1's): 25 -> quote 10 (free now that shop 1 uses 24), 50 -> 12, 100 -> 13
            10: ["SOUTH OF GRAVE HIDES", "A SECRET."],
            12: ["AN OLD MAN ON AN", "ISLAND HAS A", "MAGICAL KEY."],
            13: ["BACK AND FORTH WILL", "GAIN YOU THE RED RING."]}

# ---------------------------------------------------------------------------------------------------------------
# Level 3 (q3/level_3.json). Item spots A 8,9  B 5,7  C 10,7  D 10,12.
L3_SPOTS = [0x89, 0x57, 0xA7, 0xAC]
L3_SHARED = {"G15": Enemy(0x74), "B12": Enemy(0x74), "A12": Enemy(0x6F)}   # vanilla lists, Bubbles first
L3_MIXED_COUNT = {"G15": 8, "B12": 6, "A12": 8}
L3_ROOMS = {
    "H15": (R.ENTRANCE_ROOM, False, E.NOTHING, 3, Item.NOTHING, P.POSITION_A, A.NONE, (OPEN, WALL, OPEN, WALL), 3),
    "G15": (R.FIVE_PAIR_ROOM, True, "G15", None, Item.COMPASS, P.POSITION_B, A.BLOCK_STAIRS, (WALL, WALL, OPEN, WALL), 2),
    "F13": (R.GOHMA_ROOM, True, E.ZOL, 5, Item.NOTHING, P.POSITION_A, A.BLOCK_STAIRS, (WALL, WALL, WALL, OPEN), 2),
    "F12": (R.FOUR_FIREBALL_ROOM, False, E.RED_DARKNUT, 3, Item.KEY, P.POSITION_A, A.ALL_DEAD_ITEM,
            (SHUT, SHUT, WALL, WALL), 2),
    "E12": (R.SPIRAL_STAIR_ROOM, False, E.BLUE_KEESE, 8, Item.KEY, P.POSITION_D, A.ALL_DEAD_ITEM,
            (WALL, WALL, OPEN, WALL), 2),
    "C12": (R.SINGLE_BLOCK_ROOM, True, E.BLUE_DARKNUT, 5, Item.NOTHING, P.POSITION_A, A.BLOCK_STAIRS,
            (OPEN, WALK, WALL, WALL), 2),
    "B12": (R.REVERSE_C, False, "B12", None, Item.NOTHING, P.POSITION_A, A.NONE, (LOCK, WALL, OPEN, WALL), 2),
    "A12": (R.DOUBLE_BLOCK, True, "A12", None, Item.NOTHING, P.POSITION_A, A.BLOCK_STAIRS, (WALL, WALL, LOCK, OPEN), 2),
    "A11": (R.NSU, False, E.GIBDO, 5, Item.MAP, P.POSITION_A, A.NONE, (WALL, OPEN, WALL, WALL), 2),
    "C13": (R.GLEEOK_ROOM, False, E.GLEEOK_2, 0, Item.BOMBS, P.POSITION_A, A.ALL_DEAD_ITEM, (SHUT, WALL, WALL, WALL), 2),
    "B13": (R.SPIKE_TRAP_ROOM, True, E.THREE_PAIRS_OF_TRAPS, 0, Item.NOTHING, P.POSITION_A, A.BLOCK_STAIRS,
            (WALL, WALL, OPEN, WALK), 2),
    "E16": (R.NARROW_STAIR_ROOM, False, E.MANHANDLA, 0, Item.HEART_CONTAINER, P.POSITION_A, A.ALL_DEAD_ITEM,
            (SHUT, WALL, WALL, WALL), 2),
    "D16": (R.TRIFORCE_ROOM, False, E.NOTHING, 3, Item.TRIFORCE, P.POSITION_A, A.NONE, (WALL, WALL, OPEN, WALL), 2),
}
# One-ways: C12's walk-through east into C13 (C13's west is a wall), B13's walk-through west into B12 (B12's east
# is a wall). Shutters face open doors: F12 N/E (E12 S, F13 W), C13 N (B13 S), E16 N (D16 S).

# ---------------------------------------------------------------------------------------------------------------
# Level 4 (q3/level_4.json). Item spots A 13,12  B 5,7  C 3,11  D 8,9 (center).
L4_SPOTS = [0xDC, 0x57, 0x3B, 0x89]
L4_MIXED = {"H5": [E.BUBBLE] * 3 + [E.WALLMASTER] * 5}         # 1Q L7's $79 with Wallmasters (L1's $79 has Like Likes)
L4_SHARED = {"E3": Enemy(0x71), "D2": Enemy(0x7C)}              # vanilla Wizzrobe mixes, Bubble(s) first
L4_MIXED_COUNT = {"H5": 8, "E3": 8, "D2": 8}
PA, PB, PC, PD = P.POSITION_A, P.POSITION_B, P.POSITION_C, P.POSITION_D
# In game, object $23 (ZORA's RED_WIZZROBE) is the blue one and $24 (BLUE_WIZZROBE) the orange/red one.
BLUE_LOOK_WIZZROBE, RED_LOOK_WIZZROBE = E.RED_WIZZROBE, E.BLUE_WIZZROBE
L4_ROOMS = {
    "H3": (R.ENTRANCE_ROOM, False, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (OPEN, OPEN, OPEN, WALK), 3),
    "H2": (R.HORIZONTAL_CHUTE_ROOM, False, E.BLUE_KEESE, 8, Item.KEY, PB, A.NONE, (OPEN, WALL, WALL, LOCK), 2),
    "H1": (R.REVERSE_C, False, E.RED_BUBBLE, 6, Item.MAP, PD, A.NONE, (WALK, LOCK, WALL, WALL), 2),
    "H4": (R.FIVE_PAIR_ROOM, False, E.BLUE_BUBBLE, 6, Item.NOTHING, PA, A.NONE, (WALL, WALL, WALL, OPEN), 2),
    "H5": (R.REVERSE_C, True, "H5", None, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, WALL, WALK), 2),
    "G1": (R.GLEEOK_ROOM, False, E.GLEEOK_2, 0, Item.BLUE_CANDLE, PC, A.ALL_DEAD_ITEM, (WALL, LOCK, WALL, WALL), 2),
    "G2": (R.FOUR_FIREBALL_ROOM, False, E.VIRE, 6, Item.BOMBS, PD, A.ALL_DEAD_ITEM, (WALK, OPEN, OPEN, LOCK), 2),
    "G3": (R.DOUBLE_BLOCK, True, BLUE_LOOK_WIZZROBE, 3, Item.NOTHING, PA, A.BLOCK_DOOR, (SHUT, WALL, SHUT, SHUT), 2),
    "G4": (R.GOHMA_ROOM, False, E.RED_GOHMA, 0, Item.KEY, PD, A.ALL_DEAD_ITEM, (OPEN, BOMB, WALL, WALL), 2),
    "G5": (R.POINTLESS_MOAT_ROOM, False, BLUE_LOOK_WIZZROBE, 6, Item.FIVE_RUPEES, PA, A.ALL_DEAD_ITEM,
           (WALL, WALL, WALK, BOMB), 2),
    "F2": (R.TWO_FIREBALL_ROOM, False, BLUE_LOOK_WIZZROBE, 3, Item.KEY, PD, A.ALL_DEAD_ITEM, (WALK, WALL, WALL, WALL), 2),
    "F3": (R.GRID_ROOM, False, E.WALLMASTER, 8, Item.COMPASS, PA, A.ALL_DEAD_ITEM, (OPEN, BOMB, OPEN, WALL), 2),
    "F4": (R.HORIZONTAL_MOAT_ROOM, False, E.GEL_2, 8, Item.FIVE_RUPEES, PD, A.ALL_DEAD_ITEM, (OPEN, WALL, OPEN, BOMB), 2),
    "E2": (R.POINTLESS_MOAT_ROOM, False, E.GEL_2, 5, Item.FIVE_RUPEES, PA, A.ALL_DEAD_ITEM, (LOCK, BOMB, WALK, WALL), 2),
    "E3": (R.PLAIN_ROOM, False, "E3", None, Item.NOTHING, PA, A.ALL_DEAD, (SHUT, BOMB, OPEN, BOMB), 2),
    "E4": (R.DOUBLE_MOAT_ROOM, False, BLUE_LOOK_WIZZROBE, 6, Item.KEY, PD, A.ALL_DEAD_ITEM, (OPEN, WALL, OPEN, BOMB), 2),
    "D2": (R.DOUBLE_MOAT_ROOM, False, "D2", None, Item.BOMBS, PD, A.ALL_DEAD_ITEM, (WALL, WALL, LOCK, WALL), 2),
    "D3": (R.GLEEOK_ROOM, False, E.GLEEOK_3, 0, Item.HEART_CONTAINER, PD, A.ALL_DEAD_ITEM, (SHUT, WALL, SHUT, WALL), 2),
    "D4": (R.BLACK_ROOM, False, E.ELDER, 3, Item.NOTHING, PA, A.NONE, (WALL, WALL, OPEN, WALL), 0),   # old man, quote 21
    "C3": (R.TRIFORCE_ROOM, False, E.NOTHING, 3, Item.TRIFORCE, PD, A.NONE, (WALL, WALL, OPEN, WALL), 2),
}
# One-ways: H3 W into H2's chute (H2's east a wall), G2 N into F2, H1 N into G1, G5 S into H5, H5 W into H4.
# F2 <-> E2 walk-through both ways. Shutters face open doors except E3 N / D3 S (shutters on both sides).

# ---------------------------------------------------------------------------------------------------------------
# Level 5 (q3/level_5.json). Item spots A 8,9  B 8,12  C 2,12  D 13,6.
L5_SPOTS = [0x89, 0x8C, 0x2C, 0xD6]
L5_SHARED = {"L5F7": Enemy(0x74), "L5C9": Enemy(0x74)}      # 2 Bubbles, 3 Darknuts, 3 Gibdos
L5_MIXED_COUNT = {"L5F7": 8, "L5C9": 8}
L5_ROOMS = {
    "H7": (R.ENTRANCE_ROOM, False, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (OPEN, OPEN, OPEN, WALL), 3),
    "H8": (R.DESERT_ROOM, False, E.SINGLE_DODONGO, 0, Item.MAP, PA, A.ALL_DEAD_ITEM, (WALL, BOMB, WALL, OPEN), 2),
    "H9": (R.TWO_FIREBALL_ROOM, False, E.BLUE_DARKNUT, 3, Item.KEY, PA, A.ALL_DEAD_ITEM, (WALL, WALL, WALL, BOMB), 2),
    "G7": (R.DESERT_ROOM, False, E.SINGLE_DIGDOGGER, 0, Item.KEY, PA, A.ALL_DEAD_ITEM, (BOMB, WALL, OPEN, WALL), 2),
    "F6": (R.FOUR_FIREBALL_ROOM, False, E.TRIPLE_DODONGO, 0, Item.KEY, PA, A.ALL_DEAD_ITEM, (WALL, WALK, WALL, WALL), 2),
    "F7": (R.CHEVY_ROOM, False, "L5F7", None, Item.NOTHING, PA, A.NONE, (BOMB, WALK, BOMB, WALL), 2),
    "F8": (R.FOUR_FIREBALL_ROOM, False, E.TRIPLE_DODONGO, 0, Item.KEY, PA, A.ALL_DEAD_ITEM, (WALL, WALK, WALL, WALL), 2),
    "F9": (R.FIVE_PAIR_ROOM, True, E.BLUE_DARKNUT, 5, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, WALL, WALK), 2),
    "E6": (R.TURNSTILE_ROOM, True, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (WALL, WALL, WALK, WALL), 2),
    "E7": (R.DESERT_ROOM, False, E.RED_LANMOLA, 3, Item.BOMBS, PA, A.ALL_DEAD_ITEM, (SHUT, WALL, BOMB, WALK), 2),
    "D5": (R.DOUBLE_BLOCK, False, E.TRIPLE_DODONGO, 0, Item.NOTHING, PA, A.NONE, (LOCK, WALK, WALL, WALL), 2),
    "D6": (R.BLACK_ROOM, False, E.ELDER_3, 3, Item.NOTHING, PA, A.NONE, (WALL, BOMB, WALL, WALL), 0),     # quote 23
    "D7": (R.TWO_FIREBALL_ROOM, False, E.TRIPLE_DIGDOGGER, 0, Item.HEART_CONTAINER, PA, A.ALL_DEAD_ITEM,
           (SHUT, SHUT, SHUT, BOMB), 2),
    "D8": (R.BLACK_ROOM, False, E.BLUE_DARKNUT, 8, Item.KEY, PA, A.ALL_DEAD_ITEM, (SHUT, WALL, WALL, OPEN), 0),
    "C5": (R.NSU, False, E.BLUE_KEESE, 8, Item.FIVE_RUPEES, PA, A.NONE, (WALL, BOMB, LOCK, WALL), 2),
    "C6": (R.T_ROOM, False, E.NOTHING, 3, Item.KEY, PC, A.NONE, (WALL, WALL, WALL, BOMB), 2),
    "C7": (R.TRIFORCE_ROOM, False, E.NOTHING, 3, Item.TRIFORCE, PA, A.NONE, (WALL, WALK, OPEN, WALK), 2),
    "C8": (R.HORIZONTAL_CHUTE_ROOM, False, E.BLUE_KEESE, 5, Item.FIVE_RUPEES, PA, A.ALL_DEAD_ITEM, (WALK, LOCK, OPEN, WALK), 2),
    "C9": (R.MAZE_ROOM, True, "L5C9", None, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, WALL, LOCK), 2),
    "B5": (R.DIAMOND_STAIR_ROOM, True, E.ZOL, 8, Item.NOTHING, PA, A.NONE, (WALL, OPEN, WALK, WALL), 2),
    "B6": (R.DESERT_ROOM, False, E.AQUAMENTUS, 0, Item.NOTHING, PA, A.ALL_DEAD, (SHUT, WALL, WALL, OPEN), 2),
    "B7": (R.FIVE_PAIR_ROOM, False, E.BLUE_DARKNUT, 6, Item.KEY, PB, A.ALL_DEAD_ITEM, (BOMB, BOMB, WALL, WALL), 2),
    "B8": (R.REVERSE_C, False, E.RED_DARKNUT, 5, Item.COMPASS, PA, A.NONE, (WALL, WALL, WALK, BOMB), 2),
    "A6": (R.VERTICAL_MOAT_ROOM, False, E.BLUE_DARKNUT, 8, Item.NOTHING, PA, A.NONE, (WALL, BOMB, OPEN, WALL), 2),
    "A7": (R.BLACK_ROOM, False, E.BOMB_UPGRADER, 3, Item.NOTHING, PA, A.NONE, (WALL, WALL, BOMB, BOMB), 0),
}
L5_TEXTS = {23: ["THE SWORD DUNGEON", "HOLDS MORE THAN ONE."]}   # D6: ELDER_3 in group A -> quote 23

# ---------------------------------------------------------------------------------------------------------------
# Level 6 (q3/level_6.json). Item spots = vanilla Level 6's: A 8,9  B 13,6  C 2,6  D 2,12.
L6_SPOTS = [0x89, 0xD6, 0x26, 0x2C]
L6_MIXED = {"L6F14": [E.RED_BUBBLE] * 3 + [E.BLUE_BUBBLE] + [RED_LOOK_WIZZROBE, BLUE_LOOK_WIZZROBE] * 2}
L6_MIXED_CODE = 0x76            # vanilla 1Q Level 9's only (Levels 7-9 are cleared); written after the others
L6_MIXED_COUNT = {"L6F14": 8}
L6_ROOMS = {
    "H13": (R.ENTRANCE_ROOM, False, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (WALL, OPEN, OPEN, WALK), 3),
    "H12": (R.CIRCLE_MOAT_ROOM, False, E.BLUE_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (WALL, WALK, WALL, WALL), 2),
    "H14": (R.HORIZONTAL_MOAT_ROOM, False, E.ZOL, 8, Item.KEY, PA, A.ALL_DEAD_ITEM, (LOCK, WALL, WALL, OPEN), 2),
    "G14": (R.TWO_FIREBALL_ROOM, False, BLUE_LOOK_WIZZROBE, 5, Item.MAP, PA, A.ALL_DEAD_ITEM, (OPEN, WALL, LOCK, WALL), 2),
    "F14": (R.ZIGZAG_ROOM, False, "L6F14", None, Item.NOTHING, PA, A.NONE, (OPEN, WALK, OPEN, WALL), 2),
    "E14": (R.GRID_ROOM, False, E.WALLMASTER, 8, Item.BOMBS, PC, A.ALL_DEAD_ITEM, (BOMB, WALL, OPEN, WALL), 2),
    "D14": (R.POINTLESS_MOAT_ROOM, False, E.POLS_VOICE, 6, Item.KEY, PC, A.ALL_DEAD_ITEM, (WALL, WALL, BOMB, WALK), 2),
    "D13": (R.HORIZONTAL_CHUTE_ROOM, False, E.RED_BUBBLE, 8, Item.BOMBS, PA, A.NONE, (WALL, WALL, WALL, LOCK), 2),
    "D12": (R.ZIGZAG_ROOM, True, E.ZOL, 8, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, LOCK, WALL, WALL), 2),
    "A14": (R.VERTICAL_CHUTE_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (WALL, WALL, WALK, WALL), 2),
    "B14": (R.POINTLESS_MOAT_ROOM, False, E.ZOL, 8, Item.BOW, PC, A.ALL_DEAD_ITEM, (WALK, WALL, WALK, WALL), 2),
    "C14": (R.GLEEOK_ROOM, False, E.POLS_VOICE, 8, Item.KEY, PA, A.ALL_DEAD_ITEM, (WALK, WALL, WALK, WALL), 2),
    "F15": (R.GOHMA_ROOM, False, E.RED_GOHMA, 0, Item.COMPASS, PA, A.ALL_DEAD_ITEM, (OPEN, SHUT, WALL, WALK), 2),
    "F16": (R.GLEEOK_ROOM, False, E.GLEEOK_2, 0, Item.NOTHING, PA, A.ALL_DEAD, (WALL, WALL, WALK, SHUT), 2),
    "G16": (R.VERTICAL_ROWS, False, E.POLS_VOICE, 8, Item.KEY, PC, A.ALL_DEAD_ITEM, (WALK, WALL, SHUT, WALL), 2),
    "H16": (R.SPIRAL_STAIR_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (OPEN, WALL, WALL, WALL), 2),
    "E15": (R.VERTICAL_CHUTE_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (OPEN, WALL, OPEN, WALL), 2),
    "D15": (R.VERTICAL_CHUTE_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (OPEN, WALL, OPEN, WALL), 2),
    "C15": (R.FOUR_FIREBALL_ROOM, False, E.MANHANDLA, 0, Item.KEY, PA, A.ALL_DEAD_ITEM, (WALL, SHUT, SHUT, WALL), 2),
    "C16": (R.SPIRAL_STAIR_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (WALL, WALL, WALL, OPEN), 2),
    "B16": (R.NARROW_STAIR_ROOM, False, E.POLS_VOICE, 8, Item.BOMBS, PA, A.ALL_DEAD_ITEM, (WALL, WALL, WALL, SHUT), 2),
    "B15": (R.GLEEOK_ROOM, False, E.GLEEOK_3, 0, Item.HEART_CONTAINER, PA, A.ALL_DEAD_ITEM, (SHUT, SHUT, WALL, WALL), 2),
    "A15": (R.TRIFORCE_ROOM, False, E.NOTHING, 3, Item.TRIFORCE, PA, A.NONE, (WALL, WALL, OPEN, WALL), 2),
}
# One-ways: D14 W into D13 (D13's east a wall), C14 S into D14 (D14's north a wall), D12's stairs to A14 (A14 has
# none). Two-ways: H12 <-> H13, F14 <-> F15, A14 <-> B14 <-> C14 walk-throughs.

ENTRANCE_ONLY = {}
EXTRA_ROOMS = {}
# ---------------------------------------------------------------------------------------------------------------
# Levels 7-9 block (q3/grid_7_9.json: b = Level 8, r = Level 7, g = Level 9, w = free). Level 8 is built in full
# (q3/level_8.json); Levels 7 and 9 are an entrance room with their item for now.
GRID79 = json.load(open(base.Q3 / "grid_7_9.json"))["rows"]
NEW79 = {k: {r * 16 + c for r in range(8) for c in range(16) if GRID79[r][c] == ch} for k, ch in ((7, "r"), (8, "b"), (9, "g"))}
L8_SPOTS = [0x89, 0xD6, 0x26, 0x2C]        # vanilla Level 8's: A 8,9  B 13,6  C 2,6  D 2,12
L8_SHARED = {"L8F2": Enemy(0x74)}           # 2 Bubbles, 3 Darknuts, 3 Gibdos
L8_MIXED_COUNT = {"L8F2": 8}
L8_ROOMS = {
    "H1": (R.ENTRANCE_ROOM, False, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (OPEN, WALL, OPEN, WALL), 3),
    "G1": (R.TWO_FIREBALL_ROOM, False, E.RED_LANMOLA, 3, Item.NOTHING, PA, A.ALL_DEAD, (SHUT, SHUT, SHUT, WALL), 2),
    "F1": (R.VERTICAL_CHUTE_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (OPEN, WALL, OPEN, WALL), 2),
    # the hungry Goriya stands in the north door until fed (vanilla: an open door, no shutter)
    "E1": (R.BLACK_ROOM, False, E.HUNGRY_GORIYA, 3, Item.NOTHING, PA, A.NONE, (OPEN, WALL, OPEN, WALL), 0),
    "D1": (R.GOHMA_ROOM, True, E.MANHANDLA, 0, Item.NOTHING, PA, A.BLOCK_STAIRS, (LOCK, WALL, OPEN, WALL), 2),
    "C1": (R.DOUBLE_SIX_BLOCK_ROOM, False, E.BLUE_LANMOLA, 3, Item.NOTHING, PA, A.ALL_DEAD, (SHUT, WALL, LOCK, WALL), 2),
    "B1": (R.TURNSTILE_ROOM, True, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (WALL, LOCK, OPEN, WALL), 2),
    "A1": (R.NARROW_STAIR_ROOM, False, E.BLUE_GOHMA, 0, Item.RED_CANDLE, PA, A.ALL_DEAD_ITEM, (WALL, WALL, WALK, WALL), 2),
    "B2": (R.FOUR_FIREBALL_ROOM, False, E.BLUE_GOHMA, 0, Item.NOTHING, PA, A.ALL_DEAD, (WALL, SHUT, SHUT, LOCK), 2),
    "C2": (R.CIRCLE_MOAT_ROOM, False, E.CORNER_TRAPS, 0, Item.COMPASS, PA, A.NONE, (OPEN, WALL, OPEN, WALL), 2),
    "D2": (R.TURNSTILE_ROOM, True, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (OPEN, OPEN, OPEN, WALL), 2),
    "E2": (R.SINGLE_BLOCK_ROOM, True, E.BLUE_LANMOLA, 3, Item.NOTHING, PA, A.BLOCK_DOOR, (SHUT, WALL, SHUT, WALL), 2),
    "F2": (R.VERTICAL_MOAT_ROOM, False, "L8F2", None, Item.KEY, PA, A.ALL_DEAD_ITEM, (SHUT, LOCK, WALL, WALL), 2),
    "G2": (R.DOUBLE_MOAT_ROOM, False, E.GIBDO, 5, Item.BOMBS, PA, A.ALL_DEAD_ITEM, (WALL, WALL, OPEN, OPEN), 2),
    "H2": (R.DESERT_ROOM, False, E.BLUE_KEESE, 6, Item.FIVE_RUPEES, PA, A.ALL_DEAD_ITEM, (OPEN, OPEN, WALL, WALL), 2),
    "A3": (R.SINGLE_BLOCK_ROOM, True, E.NOTHING, 3, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, OPEN, WALL), 2),   # south: one way into B3
    "B3": (R.SPIRAL_STAIR_ROOM, True, E.RED_BUBBLE, 6, Item.NOTHING, PA, A.BLOCK_DOOR, (WALL, OPEN, WALL, SHUT), 2),
    "D3": (R.BLACK_ROOM, False, E.GLEEOK_3, 0, Item.KEY, PA, A.ALL_DEAD_ITEM, (WALL, WALL, WALL, SHUT), 0),
    "F3": (R.NARROW_STAIR_ROOM, False, E.BLUE_BUBBLE, 5, Item.NOTHING, PA, A.NONE, (WALL, WALL, OPEN, LOCK), 2),
    "G3": (R.CHEVY_ROOM, False, E.RED_BUBBLE, 6, Item.NOTHING, PA, A.NONE, (OPEN, OPEN, WALL, WALL), 2),
    "H3": (R.ZIGZAG_ROOM, False, E.BLUE_DARKNUT, 5, Item.NOTHING, PA, A.NONE, (WALL, LOCK, WALL, OPEN), 2),
    "B4": (R.HORIZONTAL_CHUTE_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (WALL, OPEN, WALL, OPEN), 2),
    "D4": (R.SINGLE_BLOCK_ROOM, False, E.GIBDO, 5, Item.NOTHING, PA, A.ALL_DEAD, (WALL, OPEN, SHUT, WALL), 2),
    "E4": (R.DOUBLE_BLOCK, True, E.RED_LANMOLA, 3, Item.NOTHING, PA, A.BLOCK_STAIRS, (OPEN, WALL, WALL, WALL), 2),
    "G4": (R.HORIZONTAL_CHUTE_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (WALL, LOCK, WALL, OPEN), 2),
    "H4": (R.DOUBLE_SIX_BLOCK_ROOM, False, E.MANHANDLA, 0, Item.KEY, PA, A.ALL_DEAD_ITEM, (WALL, OPEN, WALL, LOCK), 2),
    "B5": (R.GLEEOK_ROOM, False, E.GLEEOK_4, 0, Item.HEART_CONTAINER, PD, A.ALL_DEAD_ITEM, (WALL, SHUT, WALL, OPEN), 2),
    "D5": (R.SPIRAL_STAIR_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (WALL, WALL, WALL, OPEN), 2),
    "G5": (R.SPIRAL_STAIR_ROOM, False, E.GIBDO, 5, Item.KEY, PC, A.ALL_DEAD_ITEM, (WALL, WALL, WALL, LOCK), 2),
    "H5": (R.SPIKE_TRAP_ROOM, True, E.RED_GOHMA, 0, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, WALL, OPEN), 2),
    "B6": (R.TRIFORCE_ROOM, False, E.NOTHING, 3, Item.TRIFORCE, PA, A.NONE, (WALL, WALL, WALL, OPEN), 2),
    "G7": (R.SPIRAL_STAIR_ROOM, False, E.RED_BUBBLE, 8, Item.KEY, PC, A.NONE, (WALL, LOCK, WALL, WALL), 2),
    "H7": (R.THREE_ROWS, True, E.GIBDO, 6, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, OPEN, WALL, WALL), 2),   # push: stairs back to H5
    "A8": (R.DOUBLE_BLOCK, True, E.BLUE_DARKNUT, 6, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, OPEN, WALL), 2),
    "B8": (R.SPIRAL_STAIR_ROOM, False, E.NOTHING, 3, Item.KEY, PC, A.NONE, (OPEN, WALL, WALL, WALL), 2),
    "G8": (R.FOUR_FIREBALL_ROOM, False, E.MANHANDLA, 0, Item.MAP, PA, A.ALL_DEAD_ITEM, (WALL, WALL, OPEN, LOCK), 2),
    "H8": (R.BLACK_ROOM, False, E.MUGGER, 3, Item.NOTHING, PA, A.MONEY_OR_LIFE, (SHUT, WALL, WALL, SHUT), 0),
}
# Stairs in free (white) cells. The order of Level 8's list is what makes F3 -> A8 -> A3 -> red ring one way:
# the game takes the first staircase that touches the room (tested, chain_test.py).
L8_TRANSPORTS = [("A8", "A3", "A4"), ("F3", "A8", "A2"), ("B8", "B3", "C4"), ("D1", "D5", "E3"),
                 ("E4", "G5", "F4"), ("A1", "G7", "F5"), ("H5", "H7", "B11")]
L8_CELLAR = ("A3", Item.RED_RING, "C3")
ENTRANCES_79 = {}
# Level 9 (q3/level_9.json): the Serpent, plus D15 (a free cell made a room, left off the map).
L9_SPOTS = [0x89, 0xD6, 0x26, 0x2C]        # vanilla Level 9's: A 8,9  B 13,6  C 2,6  D 2,12
L9_HIDDEN = {"D15"}
P_C14 = PB    # C14: the compass at B (13,6, the top-right floor), off the grid's blocks
L9_ROOMS = {
    "H10": (R.ENTRANCE_ROOM, False, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (WALL, WALL, OPEN, OPEN), 3),
    "H9": (R.BLACK_ROOM, False, E.HUNGRY_GORIYA, 3, Item.NOTHING, PA, A.NONE, (OPEN, OPEN, WALL, WALL), 0),   # fed: open N
    "G9": (R.BLACK_ROOM, False, E.ELDER, 3, Item.NOTHING, PA, A.NONE, (SHUT, WALL, OPEN, WALL), 0),   # triforce gate
    "F9": (R.TWO_FIREBALL_ROOM, False, E.PATRA_2, 0, Item.MAP, PA, A.ALL_DEAD_ITEM, (OPEN, WALL, OPEN, WALL), 2),
    "E9": (R.CIRCLE_MOAT_ROOM, False, "E3", None, Item.KEY, PB, A.ALL_DEAD_ITEM, (SHUT, WALL, SHUT, WALL), 2),
    "D9": (R.DOUBLE_BLOCK, True, E.PATRA_1, 0, Item.NOTHING, PA, A.BLOCK_STAIRS, (LOCK, WALL, OPEN, WALL), 2),
    "C9": (R.ZIGZAG_ROOM, True, RED_LOOK_WIZZROBE, 6, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, LOCK, WALL), 2),
    "B9": (R.BLACK_ROOM, False, E.BLUE_BUBBLE, 6, Item.NOTHING, PA, A.NONE, (WALK, WALL, WALL, WALL), 0),
    "A9": (R.DOUBLE_MOAT_ROOM, False, E.VIRE, 6, Item.NOTHING, PA, A.NONE, (WALL, OPEN, WALK, WALL), 2),
    "A10": (R.POINTLESS_MOAT_ROOM, False, "H5", None, Item.KEY, PB, A.ALL_DEAD_ITEM, (WALL, LOCK, WALL, OPEN), 2),
    "A11": (R.REVERSE_C, False, BLUE_LOOK_WIZZROBE, 6, Item.NOTHING, PA, A.NONE, (WALL, LOCK, WALL, LOCK), 2),
    "A12": (R.GRID_ROOM, False, E.POLS_VOICE, 8, Item.NOTHING, PA, A.NONE, (WALL, OPEN, WALL, LOCK), 2),
    "A13": (R.FOUR_FIREBALL_ROOM, False, E.VIRE, 6, Item.NOTHING, PA, A.NONE, (WALL, LOCK, WALL, OPEN), 2),
    "A14": (R.FIVE_PAIR_ROOM, False, E.ZOL, 6, Item.FIVE_RUPEES, PA, A.ALL_DEAD_ITEM, (WALL, WALL, WALL, LOCK), 2),
    "A15": (R.GOHMA_ROOM, True, "E3", None, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALK, WALL, WALL), 2),   # Wizzrobe/Bubble mix
    "A16": (R.DOUBLE_SIX_BLOCK_ROOM, False, E.VIRE, 6, Item.NOTHING, PA, A.NONE, (WALL, WALL, WALK, WALK), 2),
    "B16": (R.NARROW_STAIR_ROOM, False, E.BLUE_BUBBLE, 6, Item.NOTHING, PA, A.NONE, (WALL, WALL, WALL, WALL), 2),
    "C13": (R.POINTLESS_MOAT_ROOM, False, E.POLS_VOICE, 6, Item.NOTHING, PA, A.NONE, (WALL, LOCK, WALK, WALL), 2),
    "C14": (R.GRID_ROOM, False, E.WALLMASTER, 5, Item.COMPASS, P_C14, A.ALL_DEAD_ITEM, (WALL, BOMB, WALL, LOCK), 2),
    "C15": (R.DOUBLE_BLOCK, True, BLUE_LOOK_WIZZROBE, 6, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, LOCK, WALL, BOMB), 2),
    "C16": (R.SPIRAL_STAIR_ROOM, False, E.BLUE_BUBBLE, 6, Item.NOTHING, PA, A.NONE, (WALL, WALL, WALL, LOCK), 2),
    "D13": (R.SPIRAL_STAIR_ROOM, False, E.RED_BUBBLE, 6, Item.NOTHING, PA, A.NONE, (WALL, WALL, WALL, WALL), 2),
    "E13": (R.DOUBLE_BLOCK, False, E.BLUE_KEESE, 8, Item.BOMBS, PA, A.ALL_DEAD_ITEM, (WALK, WALL, WALK, WALL), 2),
    "F13": (R.POINTLESS_MOAT_ROOM, False, RED_LOOK_WIZZROBE, 6, Item.BOMBS, PB, A.NONE, (WALK, OPEN, WALL, WALL), 2),
    "E14": (R.TWO_FIREBALL_ROOM, False, E.PATRA_2, 0, Item.NOTHING, PA, A.ALL_DEAD, (WALL, SHUT, SHUT, WALL), 2),
    "F14": (R.ZIGZAG_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (WALL, OPEN, WALL, OPEN), 2),
    "E15": (R.BLACK_ROOM, False, E.MUGGER, 3, Item.NOTHING, PA, A.MONEY_OR_LIFE, (WALK, SHUT, WALL, SHUT), 0),
    "D15": (R.FIVE_PAIR_ROOM, True, "E3", None, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, WALK, WALL), 2),
    "F15": (R.FIVE_PAIR_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (WALK, WALL, WALL, OPEN), 2),
    "G15": (R.SINGLE_BLOCK_ROOM, True, "E3", None, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALK, WALL, WALL, WALL), 2),
    "H15": (R.NARROW_STAIR_ROOM, False, E.PATRA_1, 0, Item.NOTHING, PA, A.ALL_DEAD, (WALK, WALL, WALL, SHUT), 2),
    "H14": (R.GANON_ROOM, False, E.THE_BEAST, 0, Item.TRIFORCE_OF_POWER, PA, A.LAST_BOSS, (SHUT, SHUT, WALL, WALL), 3),
    "G14": (R.ZELDA_ROOM, False, E.THE_KIDNAPPED, 0, Item.NOTHING, PA, A.ALL_DEAD, (WALL, WALL, SHUT, WALL), 2),
    "E16": (R.FOUR_FIREBALL_ROOM, False, E.PATRA_1, 0, Item.BOMBS, PA, A.ALL_DEAD_ITEM, (WALL, WALL, LOCK, SHUT), 2),
    "F16": (R.HORIZONTAL_MOAT_ROOM, False, E.POLS_VOICE, 5, Item.KEY, PC, A.ALL_DEAD_ITEM, (LOCK, WALL, WALL, WALL), 2),
}
# One-ways: H15 N into G15, G15 N into F15, F15 N into E15, C13 S into D13, E13 N into D13, A16 S into B16 (the far
# sides are walls); F14's north a wall (E14's south shutter is the way in). Two-way walk-throughs elsewhere.
# Transports: D15 <-> H15 both have stairs; the others land in a room without stairs at the exit spot (tiles).
L9_TRANSPORTS = [("D15", "H15", "G16", (6, 9)), ("D9", "C13", "D16", (2, 9)), ("D13", "A9", "F12", (6, 8)),
                 ("C9", "A13", "G10", (6, 9)), ("C15", "A16", "G12", (6, 9)), ("B16", "F9", "G13", (4, 9)),
                 ("A15", "F16", "H12", (6, 6)), ("C16", "A11", "H13", (6, 9))]
L9_CELLAR = ("G15", Item.SILVER_ARROWS, "H16")
# Level 7 (q3/level_7.json): the Twin Pines, plus B12 (a free cell made a room, left off the map).
L7_SPOTS = [0x89, 0xB9, 0x57, 0x5C]        # A 8,9  B 11,9  C 5,7  D 5,12 (the user's, off the four shooter statues)
L7_HIDDEN = {"B12"}
L7_ROOMS = {
    "H6": (R.ENTRANCE_ROOM, False, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (OPEN, WALL, OPEN, WALL), 3),
    "G6": (R.AQUAMENTUS_ROOM, False, E.AQUAMENTUS, 0, Item.FIVE_RUPEES, PA, A.ALL_DEAD_ITEM, (LOCK, WALL, OPEN, WALL), 2),
    "F6": (R.FOUR_FIREBALL_ROOM, False, E.LIKE_LIKE, 5, Item.MAP, PA, A.ALL_DEAD_ITEM, (LOCK, WALK, LOCK, WALL), 2),
    "E6": (R.DESERT_ROOM, False, E.TRIPLE_DODONGO, 0, Item.NOTHING, PA, A.NONE, (LOCK, LOCK, LOCK, LOCK), 2),
    "E5": (R.BLACK_ROOM, False, E.BOMB_UPGRADER, 3, Item.NOTHING, PA, A.NONE, (WALL, LOCK, WALL, WALL), 0),
    "F7": (R.CHEVY_ROOM, False, "G6", None, Item.BOMBS, PA, A.ALL_DEAD_ITEM, (LOCK, WALK, WALL, WALK), 2),   # L2 G6's mix
    "F8": (R.FIVE_PAIR_ROOM, True, E.STALFOS, 8, Item.NOTHING, PA, A.BLOCK_STAIRS, (LOCK, WALL, WALL, WALK), 2),
    "B10": (R.SINGLE_BLOCK_ROOM, True, E.BLUE_GORIYA, 8, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, OPEN, WALL), 2),
    "A7": (R.DESERT_ROOM, False, E.SINGLE_DODONGO, 0, Item.NOTHING, PA, A.NONE, (WALL, WALL, OPEN, OPEN), 2),
    "A6": (R.FOUR_FIREBALL_ROOM, False, E.TRIPLE_DODONGO, 0, Item.HEART_CONTAINER, PC, A.ALL_DEAD_ITEM, (WALL, SHUT, WALL, SHUT), 2),
    "A5": (R.TRIFORCE_ROOM, False, E.NOTHING, 3, Item.TRIFORCE, PA, A.NONE, (WALL, OPEN, WALL, WALL), 2),
    "B7": (R.VERTICAL_CHUTE_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (OPEN, WALL, OPEN, WALL), 2),
    "C7": (R.MAZE_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (OPEN, LOCK, LOCK, WALK), 2),
    "B12": (R.FIVE_PAIR_ROOM, True, E.BLUE_KEESE, 8, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALL, WALL, WALK, WALL), 2),
    "C5": (R.DIAMOND_STAIR_ROOM, True, E.BLUE_GORIYA, 6, Item.RAFT, PC, A.ALL_DEAD_ITEM, (WALL, LOCK, WALL, WALL), 2),
    "C6": (R.TURNSTILE_ROOM, True, E.NOTHING, 3, Item.NOTHING, PA, A.NONE, (WALL, WALK, OPEN, LOCK), 2),
    "D6": (R.NSU, False, E.CORNER_TRAPS, 0, Item.KEY, PA, A.NONE, (OPEN, LOCK, LOCK, WALL), 2),
    "D7": (R.FOUR_FIREBALL_ROOM, False, E.SINGLE_DIGDOGGER, 0, Item.NOTHING, PA, A.NONE, (LOCK, LOCK, LOCK, LOCK), 2),
    "C10": (R.AQUAMENTUS_ROOM, False, E.AQUAMENTUS, 0, Item.KEY, PA, A.ALL_DEAD_ITEM, (OPEN, BOMB, OPEN, WALL), 2),
    "H11": (R.REVERSE_C, True, E.BLUE_GORIYA, 6, Item.NOTHING, PA, A.BLOCK_STAIRS, (WALK, WALL, WALL, WALL), 2),
    "D10": (R.ZIGZAG_ROOM, False, E.STALFOS, 6, Item.BOMBS, PA, A.ALL_DEAD_ITEM, (OPEN, WALL, OPEN, WALL), 2),
    "E10": (R.GOHMA_ROOM, False, E.TRIPLE_DIGDOGGER, 0, Item.FIVE_RUPEES, PA, A.ALL_DEAD_ITEM, (SHUT, WALK, SHUT, WALL), 2),
    "E11": (R.MAZE_ROOM, False, E.RED_BUBBLE, 8, Item.NOTHING, PA, A.NONE, (OPEN, WALK, WALL, WALL), 2),
    "D11": (R.LAVA_MOAT, False, E.NOTHING, 3, Item.KEY, PA, A.NONE, (WALL, WALL, OPEN, WALK), 2),
    "E12": (R.NARROW_STAIR_ROOM, False, E.BLUE_BUBBLE, 6, Item.KEY, PA, A.NONE, (WALL, WALL, WALL, WALK), 2),
    "E8": (R.GOHMA_ROOM, False, E.STALFOS, 6, Item.COMPASS, PA, A.ALL_DEAD_ITEM, (WALK, WALL, LOCK, LOCK), 2),
    "D8": (R.AQUAMENTUS_ROOM, False, E.AQUAMENTUS, 0, Item.BOMBS, PA, A.ALL_DEAD_ITEM, (SHUT, WALL, WALK, LOCK), 2),
    "C8": (R.DOUBLE_SIX_BLOCK_ROOM, False, E.BLUE_GORIYA, 6, Item.NOTHING, PA, A.ALL_DEAD, (WALL, WALL, SHUT, LOCK), 2),
    "E7": (R.DESERT_ROOM, False, E.MOLDORM, 0, Item.FIVE_RUPEES, PA, A.ALL_DEAD_ITEM, (LOCK, LOCK, LOCK, LOCK), 2),
    "F10": (R.BLACK_ROOM, False, E.RUPEE_BOSS, 3, Item.NOTHING, PA, A.NONE, (OPEN, BOMB, WALL, WALL), 0),
    "F11": (R.BLACK_ROOM, False, E.ELDER_5, 3, Item.NOTHING, PA, A.NONE, (WALL, WALL, BOMB, BOMB), 0),   # quote 31
    "G11": (R.VERTICAL_CHUTE_ROOM, False, E.RED_BUBBLE, 6, Item.NOTHING, PA, A.NONE, (BOMB, WALL, WALK, WALL), 2),
    "C11": (R.BLACK_ROOM, False, E.RUPEE_BOSS, 3, Item.NOTHING, PA, A.NONE, (WALL, WALK, WALL, BOMB), 0),
    "C12": (R.FOUR_FIREBALL_ROOM, False, E.TRIPLE_DIGDOGGER, 0, Item.NOTHING, PA, A.NONE, (WALK, WALL, WALL, WALK), 2),
}
# One-ways: E10 E into E11 (E11's west a wall), D11 W into D10 (D10's east a wall). Two-way walk-throughs elsewhere.
# Transports (list order: B10's first entry is B10 -> A7). A7, D6 and E8 have no stairs: one way, Link lands at the
# staircase's exit spot (x, y in tiles).
L7_TRANSPORTS = [("B10", "A7", "B13", (6, 9)), ("F8", "B10", "B14", (6, 9)), ("B12", "C5", "B15", (6, 9)),
                 ("H11", "D6", "D12", (8, 9)), ("E12", "E8", "D14", (6, 9))]
L7_TEXTS = {31: ["YOU SHOULD HAVE TAKEN", "THE SHORTCUTS"]}   # F11: ELDER_5 in group A -> quote 31
ENTRANCE_SPOTS = [0x89, 0x57, 0xA7, 0xAC]

# Staircase rooms only in the grid's free cells (q3/grid_1_6.json, 0s): L1 2, L2 2, L3 4.
STAIR_CELLS = {"l1_transport": "A8", "l1_cellar": "A9", "l2_transport": "B4", "l2_cellar": "C4",
               "l3_a12_e16": "A13", "l3_c12_e12": "B9", "l3_f13_g15": "D9", "l3_cellar": "E8",
               "l4_cellar": "F5", "l5_cellar": "E9", "l5_transport": "E5",
               "l6_d12_a14": "E13", "l6_cellar": "A16", "l6_c16_b16": "F1"}

NEW = {k: {r * 16 + c for r in range(8) for c in range(16) if GRID[r][c] == k} for k in (1, 2, 3, 4, 5, 6)}
NEW.update({k: {cell(name)} for k, (name, _) in ENTRANCE_ONLY.items()})
for k, (_, extra) in EXTRA_ROOMS.items():
    NEW[k] |= {cell(name) for name in extra}
    assert all(GRID[cell(name) // 16][cell(name) % 16] == k for name in extra)
for name in STAIR_CELLS.values():
    assert GRID[cell(name) // 16][cell(name) % 16] == 0, name
NO_SCREEN = 0x80


def make_room(n, spec, codes, mixed_count, count_map=None):
    count_map = count_map or COUNT
    layout, push, enemy, count, item, pos, trigger, walls, palette_1 = spec
    if isinstance(enemy, str):
        info = EnemyInfo(codes[enemy], COUNT[mixed_count[enemy]])
    else:
        info = EnemyInfo(enemy, count if count == 0 else count_map[count] if enemy != E.NOTHING else count_map.get(count, 0))
    return Room(room_num=n, walls=WallSet(*walls), enemy_info=info, layout_info=LayoutInfo(layout, push),
                item_info=ItemInfo(item, BossSound.NONE, False), secret_info=SecretInfo(trigger, pos),
                palette_0=2, palette_1=palette_1)


def build(prg1: bytes):
    notes: list[str] = []
    player = recognized_player_rom(prg1)
    assert player is not None and player.revision.name == "PRG1", "not PRG1"
    with using_player_rom(player):
        image = player.canvas
        world = parse_rom(image)
        old1, old2 = world.levels[0], world.levels[1]
        block = old1.block
        assert all(lv.block is block for lv in world.levels[:6])
        taken = NEW[1] | NEW[2]

        # --- clear vanilla Levels 1 and 2, and the cells the new levels take from Levels 3-6 -----------------
        removed: set[int] = set()
        for old in (old1, old2):
            removed |= set(old.room_nums) | set(old.staircase_nums)
        others = world.levels[2:6]
        for lv in others:
            lost = sorted(set(lv.room_nums) & taken)
            if lost:
                notes.append(f"Level {lv.level_num} loses rooms {', '.join(f'${n:02X}' for n in lost)}")
            lv.room_nums = [n for n in lv.room_nums if n not in taken]
            removed |= set(lost)
            if lv.entrance_room in taken:
                notes.append(f"Level {lv.level_num}'s entrance room ${lv.entrance_room:02X} is gone")
        for lv in others:
            keep = []
            for n in lv.staircase_nums:
                st = block.staircase(n)
                exits = {st.return_dest} if st.room_type == RoomType.ITEM_STAIRCASE else {st.left_exit, st.right_exit}
                if n in taken or exits & (removed | taken):
                    notes.append(f"Level {lv.level_num} loses staircase ${n:02X}")
                    removed.add(n)
                else:
                    keep.append(n)
            lv.staircase_nums = keep
            lv.staircase_room_pool = keep
            lv.stairway_data_raw = bytes(keep) + b"\xFF" * (10 - len(keep))
        for n in removed - taken:
            p0, p1 = block.palette_bits(n)
            block[n] = Room.blank(n, p0, p1)
        step = {"N": -16, "S": 16, "E": 1, "W": -1}

        def neighbors(n):
            for side, delta in step.items():
                other = n + delta
                if side == "E" and n % 16 == 15 or side == "W" and n % 16 == 0 or not 0 <= other < 128:
                    continue
                yield side, other
        walled = 0
        for lv in others:
            for n in lv.room_nums:
                for side, other in neighbors(n):
                    if other in taken:
                        base.set_side(block, n, side, WALL)
                        walled += 1
        notes.append(f"{walled} doors of Levels 3-6 into the new levels walled")

        # --- Levels 3-6 are rebuilt as well: clear the rest of their vanilla rooms and staircases ---------------
        old_levels = {lv.level_num: lv for lv in world.levels[:6]}
        for lv in others:
            removed |= set(lv.room_nums) | set(lv.staircase_nums)
        for n in removed:
            p0, p1 = block.palette_bits(n)
            block[n] = Room.blank(n, p0, p1)

        # --- mixed lists ---------------------------------------------------------------------------------------
        all_mixed = {k: v for k, v in base.MIXED.items() if k != "G9"} | L2_MIXED | L4_MIXED
        base.MIXED.clear()
        base.MIXED.update(all_mixed)                 # write_mixed_lists and pick_mixed_codes read base.MIXED
        codes = base.pick_mixed_codes(world, removed | taken)
        codes = {**codes, **SHARED}
        codes["G9"] = codes["B3"]
        mixed_count = {**base.MIXED_COUNT, **L2_MIXED_COUNT, **L3_MIXED_COUNT, **L4_MIXED_COUNT, **L8_MIXED_COUNT, **L5_MIXED_COUNT, **L6_MIXED_COUNT}
        shared = {**L3_SHARED, **L4_SHARED, **L8_SHARED, **L5_SHARED}
        assert not set(shared.values()) & set(codes.values())
        codes.update(shared)
        assert L6_MIXED_CODE not in {s_.enemy_spec.enemy.value for s_ in world.overworld.screens}
        assert Enemy(L6_MIXED_CODE) not in codes.values()
        codes["L6F14"] = Enemy(L6_MIXED_CODE)

        # --- rooms ---------------------------------------------------------------------------------------------
        entrances = {1: cell("H10"), 2: cell("H6"), 3: cell("H15"), 4: cell("H3"), 5: cell("H7"), 6: cell("H13")}
        entrances.update({k: cell(name) for k, (name, _) in ENTRANCE_ONLY.items()})
        level_rooms = [(1, base.ROOMS), (2, L2_ROOMS), (3, L3_ROOMS), (4, L4_ROOMS), (5, L5_ROOMS), (6, L6_ROOMS)]
        for k, (name, item) in ENTRANCE_ONLY.items():
            side, extra = EXTRA_ROOMS.get(k, (None, {}))
            walls = tuple(OPEN if s_ == side or s_ == "S" else WALL for s_ in "NESW")
            level_rooms.append((k, {name: (R.ENTRANCE_ROOM, False, E.NOTHING, 3, item, P.POSITION_A, A.NONE,
                                           walls, 3), **extra}))
        for level, rooms in level_rooms:
            for name, spec in rooms.items():
                n = cell(name)
                assert n in NEW[level], name
                block[n] = make_room(n, spec, codes, mixed_count)
            for n in NEW[level]:
                for side, other in neighbors(n):
                    if other not in NEW[level] and not (n == entrances[level] and side == "S"):
                        base.set_side(block, n, side, WALL)
            missing = NEW[level] - {cell(name) for name in rooms}
            assert not missing, (level, missing)

        # Locked doors are locked on both sides (opening one side clears both)
        side_attr = {"N": "north", "S": "south", "E": "east", "W": "west"}
        opposite = {"N": "S", "S": "N", "E": "W", "W": "E"}
        for level, _ in level_rooms:
            for n in sorted(NEW[level]):
                for side, other in neighbors(n):
                    if other in NEW[level] and getattr(block.room(n).walls, side_attr[side]) == LOCK:
                        if getattr(block.room(other).walls, side_attr[opposite[side]]) != LOCK:
                            notes.append(f"lock both sides: L{level} {base.ROWS[other // 16]}{other % 16 + 1} "
                                         f"{opposite[side]} -> locked (was "
                                         f"{getattr(block.room(other).walls, side_attr[opposite[side]]).name})")
                            base.set_side(block, other, opposite[side], LOCK)

        # --- staircases ----------------------------------------------------------------------------------------
        st = {key: cell(name) for key, name in STAIR_CELLS.items()}
        l1_transport, l1_cellar, l2_transport, l2_cellar = (st["l1_transport"], st["l1_cellar"],
                                                            st["l2_transport"], st["l2_cellar"])
        raft = next(s for lv in world.levels_2q for s in lv.staircase_rooms if s.item == Item.RAFT)
        block[l1_transport] = StaircaseRoom(room_num=l1_transport, room_type=RoomType.TRANSPORT_STAIRCASE,
                                            exit_x=6, exit_y=9, left_exit=cell("G13"), right_exit=cell("C10"), t5_raw=0)
        block[l1_cellar] = StaircaseRoom(room_num=l1_cellar, room_type=RoomType.ITEM_STAIRCASE,
                                         exit_x=raft.exit_x, exit_y=raft.exit_y, item=Item.WOOD_SWORD,
                                         return_dest=cell("A10"), t5_raw=base.ITEM_SPOTS.index(0x89) << 4)
        # G6 <-> B2 both ways (vanilla 1Q Level 9 pairs a double block room and a diamond stairs room at 6,9 too)
        block[l2_transport] = StaircaseRoom(room_num=l2_transport, room_type=RoomType.TRANSPORT_STAIRCASE,
                                            exit_x=6, exit_y=9, left_exit=cell("G6"), right_exit=cell("B2"), t5_raw=0)
        # E1's cellar: exit 6,8 as vanilla 1Q Level 3's cellar under its narrow stairs room
        block[l2_cellar] = StaircaseRoom(room_num=l2_cellar, room_type=RoomType.ITEM_STAIRCASE,
                                         exit_x=6, exit_y=8, item=Item.RECORDER, return_dest=cell("E1"),
                                         t5_raw=L2_SPOTS.index(0x89) << 4)
        # Level 3: three two-way transports and the ladder cellar under B13's push block (exit 6,9 as 2Q L6's)
        for key, (a, b) in {"l3_a12_e16": ("A12", "E16"), "l3_c12_e12": ("C12", "E12"),
                            "l3_f13_g15": ("F13", "G15")}.items():
            block[st[key]] = StaircaseRoom(room_num=st[key], room_type=RoomType.TRANSPORT_STAIRCASE,
                                           exit_x=6, exit_y=9, left_exit=cell(a), right_exit=cell(b), t5_raw=0)
        block[st["l3_cellar"]] = StaircaseRoom(room_num=st["l3_cellar"], room_type=RoomType.ITEM_STAIRCASE,
                                               exit_x=6, exit_y=9, item=Item.LADDER, return_dest=cell("B13"),
                                               t5_raw=L3_SPOTS.index(0x89) << 4)
        # Level 4: the blue candle's cellar under H5's push block
        block[st["l4_cellar"]] = StaircaseRoom(room_num=st["l4_cellar"], room_type=RoomType.ITEM_STAIRCASE,
                                               exit_x=6, exit_y=9, item=Item.LETTER, return_dest=cell("H5"),
                                               t5_raw=L4_SPOTS.index(0x89) << 4)
        # Level 5: F9 <-> B5, and the power bracelet's cellar under C9's push block
        block[st["l5_transport"]] = StaircaseRoom(room_num=st["l5_transport"], room_type=RoomType.TRANSPORT_STAIRCASE,
                                                  exit_x=6, exit_y=9, left_exit=cell("F9"), right_exit=cell("B5"), t5_raw=0)
        block[st["l5_cellar"]] = StaircaseRoom(room_num=st["l5_cellar"], room_type=RoomType.ITEM_STAIRCASE,
                                               exit_x=6, exit_y=9, item=Item.POWER_BRACELET, return_dest=cell("C9"),
                                               t5_raw=L5_SPOTS.index(0x89) << 4)
        # Level 6: D12's push block -> A14 one way (A14 has no stairs), the wand's cellar under H16, C16 <-> B16
        block[st["l6_d12_a14"]] = StaircaseRoom(room_num=st["l6_d12_a14"], room_type=RoomType.TRANSPORT_STAIRCASE,
                                                # exit 7,9: A14 has no stairs, so Link comes up here, in the chute
                                                exit_x=7, exit_y=9, left_exit=cell("D12"), right_exit=cell("A14"), t5_raw=0)
        block[st["l6_cellar"]] = StaircaseRoom(room_num=st["l6_cellar"], room_type=RoomType.ITEM_STAIRCASE,
                                               exit_x=6, exit_y=9, item=Item.WAND, return_dest=cell("H16"),
                                               t5_raw=L6_SPOTS.index(0x89) << 4)
        block[st["l6_c16_b16"]] = StaircaseRoom(room_num=st["l6_c16_b16"], room_type=RoomType.TRANSPORT_STAIRCASE,
                                                exit_x=6, exit_y=9, left_exit=cell("C16"), right_exit=cell("B16"), t5_raw=0)
        notes.append("Stairs: " + ", ".join(f"{k} ${v:02X}" for k, v in st.items()))

        # --- level records -------------------------------------------------------------------------------------
        def level_record(num, old, entrance, boss, spots, pool, sprites=EnemySpriteSet.A):
            cells = sorted(NEW[num])
            map_data, commands, map_start, map_cursor = synthesize_minimap(set(cells))
            new = Level(
                level_num=num, entrance_room=entrance, entrance_direction=Direction.SOUTH,
                palette_raw=old.palette_raw, fade_palette_raw=old.fade_palette_raw,
                staircase_room_pool=pool, room_nums=cells, staircase_nums=pool, block=block,
                boss_room=boss, enemy_sprite_set=sprites, boss_sprite_set=old.boss_sprite_set,
                start_y=old.start_y, item_position_table=list(spots), map_start=map_start,
                map_cursor_offset=map_cursor, map_data=map_data,
                map_ppu_commands=command_block(commands, old.map_ppu_commands), qty_table=list(QTY),
                stairway_data_raw=bytes(pool) + b"\xFF" * (10 - len(pool)), rom_level_num=old.rom_level_num,
                screen_status_ram_offset=old.screen_status_ram_offset,
            )
            new.triforce_room_ptr = None
            return new
        new1 = level_record(1, old1, cell("H10"), cell("F11"), base.ITEM_SPOTS, [l1_cellar, l1_transport])
        new2 = level_record(2, old2, cell("H6"), cell("A4"), L2_SPOTS, [l2_cellar, l2_transport])
        new3 = level_record(3, old_levels[3], cell("H15"), cell("E16"), L3_SPOTS,
                            [st["l3_cellar"], st["l3_a12_e16"], st["l3_c12_e12"], st["l3_f13_g15"]],
                            old_levels[3].enemy_sprite_set)
        new4 = level_record(4, old_levels[4], cell("H3"), cell("D3"), L4_SPOTS, [st["l4_cellar"]],
                            old_levels[4].enemy_sprite_set)
        new5 = level_record(5, old_levels[5], cell("H7"), cell("D7"), L5_SPOTS, [st["l5_cellar"], st["l5_transport"]],
                            old_levels[5].enemy_sprite_set)
        new6 = level_record(6, old_levels[6], cell("H13"), cell("B15"), L6_SPOTS,
                            [st["l6_d12_a14"], st["l6_cellar"], st["l6_c16_b16"]], old_levels[6].enemy_sprite_set)
        rest = {k: level_record(k, old_levels[k], cell(name), cell(name), ENTRANCE_SPOTS, [],
                                old_levels[k].enemy_sprite_set) for k, (name, _) in ENTRANCE_ONLY.items()}
        for old in old_levels.values():
            block.levels.remove(old)
        world.levels[0], world.levels[1], world.levels[2], world.levels[3], world.levels[4], world.levels[5] = new1, new2, new3, new4, new5, new6
        for k, lv in rest.items():
            world.levels[k - 1] = lv

        # --- Levels 7-9: clear the block; Level 8 in full, Levels 7 and 9 an entrance room each --------------
        olds79 = {lv.level_num: lv for lv in world.levels[6:9]}
        block79 = olds79[8].block
        assert all(lv.block is block79 for lv in olds79.values())
        for lv in olds79.values():
            for n in (*lv.room_nums, *lv.staircase_nums):
                p0, p1 = block79.palette_bits(n)
                block79[n] = Room.blank(n, p0, p1)
        for k, (name, item) in ENTRANCES_79.items():
            NEW[k] = {cell(name)}
        NEW[8] = set(NEW79[8])
        NEW[7] = set(NEW79[7]) | {cell(n) for n in L7_HIDDEN}
        NEW[9] = set(NEW79[9]) | {cell(n) for n in L9_HIDDEN}
        assert {cell(n) for n in L7_ROOMS} == NEW[7], sorted(NEW[7] ^ {cell(n) for n in L7_ROOMS})
        assert {cell(n) for n in L8_ROOMS} == NEW[8], sorted(NEW[8] ^ {cell(n) for n in L8_ROOMS})
        assert {cell(n) for n in L9_ROOMS} == NEW[9], sorted(NEW[9] ^ {cell(n) for n in L9_ROOMS})
        rooms79 = {8: L8_ROOMS, 7: L7_ROOMS, 9: L9_ROOMS}
        entrance79 = {7: "H6", 8: "H1", 9: "H10", **{k: name for k, (name, _) in ENTRANCES_79.items()}}
        for k, (name, item) in ENTRANCES_79.items():
            rooms79[k] = {name: (R.ENTRANCE_ROOM, False, E.NOTHING, 3, item, P.POSITION_A, A.NONE, (WALL, WALL, OPEN, WALL), 3)}
        for k, rooms in rooms79.items():
            for name, spec in rooms.items():
                n = cell(name)
                p0, p1 = block79.palette_bits(n)
                room = make_room(n, spec, codes, mixed_count)
                block79[n] = room
            for n in NEW[k]:
                for side, other in neighbors(n):
                    if other not in NEW[k] and not (side == "S" and n == cell(entrance79[k])):
                        base.set_side(block79, n, side, WALL)
        ganon = block79.room(cell("H14"))      # Ganon's room is dark (vanilla)
        ganon.item_info = ItemInfo(Item.TRIFORCE_OF_POWER, BossSound.NONE, True)
        for lvk in (7, 8, 9):               # locked doors locked on both sides
            for n in sorted(NEW[lvk]):
                for side, other in neighbors(n):
                    if other in NEW[lvk] and getattr(block79.room(n).walls, side_attr[side]) == LOCK:
                        if getattr(block79.room(other).walls, side_attr[opposite[side]]) != LOCK:
                            notes.append(f"lock both sides: L{lvk} {base.ROWS[other // 16]}{other % 16 + 1} {opposite[side]}")
                        base.set_side(block79, other, opposite[side], LOCK)
        pool8 = []
        name, item, where = L8_CELLAR
        n = cell(where); assert GRID79[n // 16][n % 16] == "w", where
        block79[n] = StaircaseRoom(room_num=n, room_type=RoomType.ITEM_STAIRCASE, exit_x=6, exit_y=9, item=item,
                                   return_dest=cell(name), t5_raw=L8_SPOTS.index(0x89) << 4)
        pool8.append(n)
        for a_, b_, where in L8_TRANSPORTS:
            n = cell(where); assert GRID79[n // 16][n % 16] == "w", where
            block79[n] = StaircaseRoom(room_num=n, room_type=RoomType.TRANSPORT_STAIRCASE, exit_x=6, exit_y=9,
                                       left_exit=cell(a_), right_exit=cell(b_), t5_raw=0)
            pool8.append(n)
        notes.append("Level 8 stairs (in order): " + ", ".join(f"${n:02X}" for n in pool8))
        pool7 = []
        for a_, b_, where, (ex, ey) in L7_TRANSPORTS:
            n = cell(where); assert GRID79[n // 16][n % 16] == "w" and where not in L7_HIDDEN and n not in pool8, where
            block79[n] = StaircaseRoom(room_num=n, room_type=RoomType.TRANSPORT_STAIRCASE, exit_x=ex, exit_y=ey,
                                       left_exit=cell(a_), right_exit=cell(b_), t5_raw=0)
            pool7.append(n)
        notes.append("Level 7 stairs (in order): " + ", ".join(f"${n:02X}" for n in pool7))
        pool9 = []
        name, item, where = L9_CELLAR
        n = cell(where); assert GRID79[n // 16][n % 16] == "w" and n not in pool8 + pool7, where
        block79[n] = StaircaseRoom(room_num=n, room_type=RoomType.ITEM_STAIRCASE, exit_x=6, exit_y=9, item=item,
                                   return_dest=cell(name), t5_raw=L9_SPOTS.index(0x89) << 4)
        pool9.append(n)
        for a_, b_, where, (ex, ey) in L9_TRANSPORTS:
            n = cell(where)
            assert GRID79[n // 16][n % 16] == "w" and where not in L9_HIDDEN and n not in pool8 + pool7 + pool9, where
            block79[n] = StaircaseRoom(room_num=n, room_type=RoomType.TRANSPORT_STAIRCASE, exit_x=ex, exit_y=ey,
                                       left_exit=cell(a_), right_exit=cell(b_), t5_raw=0)
            pool9.append(n)
        notes.append("Level 9 stairs (in order): " + ", ".join(f"${n:02X}" for n in pool9))

        def level_record79(num, old, entrance, boss, spots, pool, cells, map_cells=None):
            map_data, commands, map_start, map_cursor = synthesize_minimap(set(map_cells if map_cells is not None else cells))
            new = Level(
                level_num=num, entrance_room=entrance, entrance_direction=Direction.SOUTH,
                palette_raw=old.palette_raw, fade_palette_raw=old.fade_palette_raw,
                staircase_room_pool=pool, room_nums=sorted(cells), staircase_nums=sorted(pool), block=block79,
                boss_room=boss, enemy_sprite_set=old.enemy_sprite_set, boss_sprite_set=old.boss_sprite_set,
                start_y=old.start_y, item_position_table=list(spots), map_start=map_start,
                map_cursor_offset=map_cursor, map_data=map_data,
                map_ppu_commands=command_block(commands, old.map_ppu_commands), qty_table=list(QTY),
                stairway_data_raw=bytes(pool) + b"\xFF" * (10 - len(pool)), rom_level_num=old.rom_level_num,
                screen_status_ram_offset=old.screen_status_ram_offset,
            )
            new.triforce_room_ptr = None
            return new
        new79 = {8: level_record79(8, olds79[8], cell("H1"), cell("B5"), L8_SPOTS, pool8, NEW[8]),
                 7: level_record79(7, olds79[7], cell("H6"), cell("A6"), L7_SPOTS, pool7, NEW[7],
                                   map_cells=NEW[7] - {cell(n) for n in L7_HIDDEN}),
                 9: level_record79(9, olds79[9], cell("H10"), cell("H14"), L9_SPOTS, pool9, NEW[9],
                                   map_cells=NEW[9] - {cell(n) for n in L9_HIDDEN})}
        for k, (name, item) in ENTRANCES_79.items():
            new79[k] = level_record79(k, olds79[k], cell(name), cell(name), L8_SPOTS, [], NEW[k])
        for old in olds79.values():
            block79.levels.remove(old)
        for k, lv in new79.items():
            world.levels[k - 1] = lv
        notes.append(f"Level 2 boss sprite set {old2.boss_sprite_set}")

        base.swap_like_like_and_wallmaster(world, notes)

        # --- overworld -----------------------------------------------------------------------------------------
        ow = world.overworld
        scr = ow.screens
        scr[0x0A].destination = Destination.LEVEL_1          # A11
        scr[0x37].destination = Destination.LEVEL_2          # D8 (vanilla Level 1's cave)
        scr[0x2B].destination = Destination.LEVEL_3          # C12, the 2Q desert spot the recorder opens
        scr[0x2B].quest_visibility = QuestVisibility.BOTH_QUESTS
        scr[0x42].destination = Destination.LEVEL_4          # E3, the lake the recorder drains
        scr[0x1F].destination = Destination.LEVEL_6          # B16 (was a money making game)
        scr[0x11].destination = Destination.LEVEL_7          # B2: the power bracelet rock (2Q's letter spot)
        scr[0x11].quest_visibility = QuestVisibility.BOTH_QUESTS
        scr[0x47].destination = Destination.NONE             # E8: no entrance (its bush is a plain tree now)
        scr[0x7B].destination = Destination.LARGE_SECRET     # H12: a 100-rupee secret behind its bomb wall (was a take-any)
        scr[0x09].destination = Destination.TAKE_ANY         # A10: a take-any under the bracelet rock (2Q's magical sword spot)
        scr[0x09].quest_visibility = QuestVisibility.BOTH_QUESTS
        f1 = scr[0x50]                                       # F1: the take-any, behind a bomb wall at col 8
        f1.destination = Destination.TAKE_ANY
        f1.exit_x_position, f1.exit_y_position = 8, 3
        f1.quest_visibility = QuestVisibility.BOTH_QUESTS
        scr[0x45].destination = Destination.MAGICAL_SWORD_CAVE   # E6 (vanilla Level 4's island, by raft): the magic key, 10 hearts
        scr[0x22].destination = Destination.LARGE_SECRET     # C3 (vanilla Level 6's entrance)
        scr[0x6F].destination = Destination.LOST_HILLS_HINT  # G16: an old man (was shop 1); his text: q3_g16_hint
        scr[0x74].destination = Destination.SHOP_2           # H5 (vanilla Level 3's entrance): the magical boomerang shop
        scr[0x4A].destination = Destination.MEDIUM_SECRET    # E11: a 30-rupee secret (was shop 1)
        scr[0x2C].destination = Destination.SHOP_1           # C13: the bomb shop (was a take-any, behind its bomb wall)
        # H5 and F15 trade screens (same edges: open west only); Level 8 at F15, shop 2 at H5
        a, b = scr[0x74], scr[0x5E]
        for field in ("screen_code", "exit_x_position", "exit_y_position", "stairs_position_code", "outer_palette",
                      "inner_palette", "enemy_spec", "enemy_quantity", "has_zola", "has_ocean_sound",
                      "enemies_from_sides"):
            va, vb = getattr(a, field), getattr(b, field)
            setattr(a, field, vb); setattr(b, field, va)
        b.destination = Destination.LEVEL_8                  # F15, with H5's old dungeon-entrance screen
        a.destination = Destination.SHOP_2                   # H5, with F15's old shop screen
        scr[0x3C].destination = Destination.SHOP_3           # D13 (vanilla Level 2's entrance)
        ow.recorder_reveals_listed_secrets_in_first_quest = True
        # Recorder whirlwind: Level n's piece takes you to Level n's screen (the table holds the screen to its
        # west: the whirlwind blows Link in from there), set down at Link's y
        ow.recorder_warp_destinations = [s - 1 for s in (0x0A, 0x37, 0x2B, 0x42, 0x05, 0x1F, 0x11, 0x5E)]
        ow.recorder_warp_y_coordinates = list(RECORDER_Y)
        # 3Q: E3, C12, C3; 4Q: B11 (RECORDER_QUESTS says which quest each entry works in)
        ow.recorder_secret_screens = [0x42, 0x2B, 0x22, 0x1A] + [NO_SCREEN] * (len(ow.recorder_secret_screens) - 4)
        c3 = scr[0x22]                                       # C3: 2Q D13's pond screen ($7B); the recorder opens it
        c3.screen_code = 0x7B
        c3.destination = Destination.HINT_SHOP_1           # C3: B11's paid hint cave moves here (was 100 rupees)
        scr[0x1A].destination = Destination.SMALL_SECRET     # B11: a small secret in the waterfall
        c3.exit_x_position, c3.exit_y_position, c3.stairs_position_code = 7, 1, 0   # out north of the lake
        c3.outer_palette, c3.inner_palette = scr[0x21].outer_palette, scr[0x21].inner_palette   # gray, as the graveyard
        fairy, a12 = scr[0x39], scr[0x0B]                    # A12 becomes a fairy pond like D10, no entrance
        a12.screen_code = fairy.screen_code
        a12.enemy_spec = fairy.enemy_spec
        a12.enemy_quantity = fairy.enemy_quantity
        a12.outer_palette, a12.inner_palette = fairy.outer_palette, fairy.inner_palette
        a12.has_zola, a12.has_ocean_sound = fairy.has_zola, fairy.has_ocean_sound
        a12.enemies_from_sides = fairy.enemies_from_sides
        a12.destination = Destination.NONE
        a12.quest_visibility = QuestVisibility.BOTH_QUESTS
        scr[0x77].destination = Destination.DEAD_WOODS_HINT  # H8
        scr[0x75].destination = Destination.MONEY_MAKING_GAME   # H6 (was the woods hint; H8 has that now)
        scr[0x21].destination = Destination.WOOD_SWORD_CAVE  # C2's grave
        scr[0x2F].destination = Destination.LEVEL_9          # C16
        scr[0x05].destination = Destination.LEVEL_5          # A6: vanilla Level 9's bomb wall
        scr[0x6D].destination = Destination.DOOR_REPAIR      # G14's bush (was Level 8; the burned stairs stay the way east)
        h16 = scr[0x7F]
        h16.destination = Destination.TAKE_ANY
        h16.entrance_type = EntranceType.BOMB
        h16.exit_x_position, h16.exit_y_position = 3, 2
        h16.enemies_from_sides = True
        h16.enemy_spec = EnemySpec(enemy=E.NOTHING, is_group=False, group_members=None)
        h16.has_zola = False
        # D4: no bomb wall (its potion shop goes); the Armos item moves from C5 to D4's far-right Armos column
        # (top row) and becomes the book
        scr[0x33].destination = Destination.NONE
        scr[0x0C].destination = Destination.SHOP_4           # A13: shop 4 moves here (was shop 2)
        scr[0x34].destination = Destination.TAKE_ANY         # D5: a take-any under its Armos (was shop 4)
        ow.armos_screen_ids[0], ow.armos_positions[0] = 0x33, 176
        # C5: H1's paid hint cave moves under C5's far-right Armos (the entry for A12, now a fairy pond with no Armos)
        assert ow.armos_screen_ids[1] == 0x0B
        ow.armos_screen_ids[1], ow.armos_positions[1] = 0x24, 224
        scr[0x24].destination = Destination.HINT_SHOP_2
        scr[0x24].exit_x_position, scr[0x24].exit_y_position = 14, 4   # out between the two Armos rows
        scr[0x70].destination = Destination.NONE             # H1
        scr[0x51].destination = Destination.WHITE_SWORD_CAVE # F2's bush: the blue ring, 6 hearts (was 10 rupees)
        for cave in ow.caves:
            if cave.destination == Destination.ARMOS_ITEM:
                cave.item = Item.BOOK
            if COAST_MAGICAL_SWORD and cave.destination == Destination.COAST_ITEM:   # F16's coast: magical sword
                cave.item = Item.MAGICAL_SWORD
            if cave.destination == Destination.WHITE_SWORD_CAVE:
                cave.item, cave.heart_requirement = Item.BLUE_RING, 6
            if cave.destination == Destination.MAGICAL_SWORD_CAVE:
                cave.item, cave.heart_requirement = Item.MAGICAL_KEY, 12
            if cave.destination == Destination.HINT_SHOP_1:      # C3's paid hints: 25, 50, 100
                for hint, price, quote in zip(cave.hints, (25, 50, 100), (24, 28, 11)):
                    hint.price, hint.quote_id = price, quote
            if cave.destination == Destination.HINT_SHOP_2:      # C5's paid hints: 25, 50, 100
                for hint, price, quote in zip(cave.hints, (25, 50, 100), (10, 12, 13)):
                    hint.price, hint.quote_id = price, quote
            if cave.destination == Destination.LETTER_CAVE:   # A15: the coast's heart container (the letter goes to L4)
                cave.item = Item.HEART_CONTAINER
            if cave.destination == Destination.WOOD_SWORD_CAVE:
                cave.item = Item.WOOD_BOOMERANG
            if cave.destination == Destination.SHOP_4:           # A13: the blue ring goes (it's under F2's bush)
                assert cave.items[1].item == Item.BLUE_RING
                cave.items[1] = ShopItem(Item.WOOD_ARROWS, 40)
            if cave.destination == Destination.SHOP_2:
                cave.items[2] = ShopItem(Item.MAGICAL_BOOMERANG, 150)
        ow.dead_woods_directions = [OverworldDirection.LEFT_WEST, OverworldDirection.LEFT_WEST,
                                    OverworldDirection.UP_NORTH, OverworldDirection.LEFT_WEST]
        dup = [f"{base.ROWS[s.screen_num // 16]}{s.screen_num % 16 + 1} -> {s.destination.name}"
               for s in scr if s.destination.name.startswith("LEVEL")
               and s.quest_visibility in (QuestVisibility.BOTH_QUESTS, QuestVisibility.FIRST_QUEST)]
        notes.append("1Q level entrances: " + ", ".join(dup))

        by_id = {q.quote_id: q for q in world.quotes}
        for quote_id, lines in {**base.TEXTS, **L2_TEXTS, **OW_TEXTS, **L5_TEXTS, **L7_TEXTS}.items():
            by_id[quote_id].text = base.centered(lines)
        # quote 24 (Digdogger hint, only Level 5's room $67, which Level 1 took) and 28 below are reused by C3's hints
        # quotes 22 and 29: 3Q's G16 old man (q3_g16_hint); 4Q has its own texts for them (Q4_QUOTE_TEXTS)
        by_id[22].text = ""      # (the quote bank is full: their texts go in free space)
        by_id[29].text = ""
        by_id[MUGGER_9_QUOTE].text = ""   # Level 9's Mugger: its text goes in free space (mugger_quote)
        # was: by_id[29].text = ""      # Gohma hint: group B's ELDER_3, in Level 6's room $6A; Level 6 is unplayable until rebuilt
        # quote 21 ('Did you get the sword...', group B's ELDER, only vanilla Level 3's room $2B) is Level 4's D4 hint now
        # quote 23 ('Secret power is said to be in the arrow', group A's ELDER_3) is Level 5's D6 hint now
        by_id[35].text = ""      # 'Patra has the map': vanilla Level 9's (its rooms are cleared); room for Level 5's hint
        # (22, 'Walk into the waterfall': group B's ELDER_4, only in Level 4's room $00, which Level 2 took)
        if os.environ.get("DUMP_QUOTES"):
            for q in sorted(world.quotes, key=lambda q: q.quote_id):
                print("QUOTE", q.quote_id, len(q.text), repr(q.text))
        # Fairies hint: group B's ELDER_2, only in Level 6's room $0B; Level 6's entrance is Level 1's H10 now
        world.quotes_raw = None

        counter_places = item_counter_places(world, st)
        notes.append("item counter: " + "; ".join(f"{a}: " + " ".join(f"${x:02X}" for x in v)
                                                   for a, v in counter_places.items()))
        # --- boss roars: every room of a level touching its boss room roars while the boss lives --------------
        roar_of = {E.AQUAMENTUS: BossSound.ROAR_AQUAMENTUS_GLEEOK_GANON, E.GLEEOK_2: BossSound.ROAR_AQUAMENTUS_GLEEOK_GANON,
                   E.GLEEOK_3: BossSound.ROAR_AQUAMENTUS_GLEEOK_GANON, E.GLEEOK_4: BossSound.ROAR_AQUAMENTUS_GLEEOK_GANON,
                   E.SINGLE_DIGDOGGER: BossSound.ROAR_DIGDOGGER_MANHANDLA_PATRA,
                   E.TRIPLE_DIGDOGGER: BossSound.ROAR_DIGDOGGER_MANHANDLA_PATRA,
                   E.MANHANDLA: BossSound.ROAR_DIGDOGGER_MANHANDLA_PATRA,
                   E.SINGLE_DODONGO: BossSound.ROAR_DODONGO_GOHMA, E.TRIPLE_DODONGO: BossSound.ROAR_DODONGO_GOHMA,
                   E.RED_GOHMA: BossSound.ROAR_DODONGO_GOHMA, E.BLUE_GOHMA: BossSound.ROAR_DODONGO_GOHMA,
                   E.THE_BEAST: BossSound.ROAR_AQUAMENTUS_GLEEOK_GANON}       # vanilla L9 E4/F3 roar for Ganon
        for lv in world.levels[:9]:
            if lv.boss_room == lv.entrance_room:
                continue                                   # entrance-only levels: no boss yet
            boss = lv.block.room(lv.boss_room)
            sound = roar_of[boss.enemy]
            cells = set(lv.room_nums)
            roared = []
            for side, other in neighbors(lv.boss_room):
                if other in cells:
                    lv.block.room(other).boss_sound = sound
                    roared.append(f"{base.ROWS[other // 16]}{other % 16 + 1}")
            notes.append(f"L{lv.level_num} roar {sound.name}: {', '.join(roared)}")
        # ZORA's "no item" remap ($03 -> $0E, and the engine's compare): $03 can then be the magical sword in a
        # dungeon room (4Q Level 9's Torch entrance)
        from zora.model.enums import DungeonNothingCode
        world.dungeon_nothing_code = DungeonNothingCode.ZORA_REMAP
        patch = serialize_game_world(world, original_bins_from_rom(image),
                                     config=GameConfig(dungeon_nothing_code=DungeonNothingCode.ZORA_REMAP))
        out = bytearray(image)
        patch.apply(out)
        rows = dict(base.LAYOUT_ROWS)
        rows[50] = bytes.fromhex("000002b702b7b6b702b702b702b60000")   # D4: col 10 $D2 -> $02, no bomb wall
        for row, codes_ in rows.items():
            out[base.ROOM_LAYOUTS_OW + row * 16:base.ROOM_LAYOUTS_OW + (row + 1) * 16] = codes_
        base.write_mixed_lists(out, codes, notes)
        base.overworld_mock(out, notes)
        bank5 = 16 + 5 * 0x4000
        for name, members in L6_MIXED.items():
            offset = base.free_run(out, bank5 + 0x3900, bank5 + 0x3F00, 8 + 16) + 8
            out[offset:offset + 8] = bytes(m.value for m in members)
            cpu = 0x8000 + offset - bank5
            index = codes[name].value - 0x62
            out[base.MIXED_ENEMY_POINTER_TABLE_ADDRESS + 2 * index:base.MIXED_ENEMY_POINTER_TABLE_ADDRESS + 2 * index + 2] = \
                bytes([cpu & 0xFF, cpu >> 8])
            notes.append(f"{name}: mixed list ${codes[name].value:02X} at ${cpu:04X}")
        # D5 <-> D6 passage (rows 4-5), and the C6/D6 ladder becomes rock; all existing columns
        more = {51: {15: 0x51},                         # D5 east edge: rock x4, ground x2, shore, water
                52: {0: 0x51, 1: 0x51, 2: 0x51, 3: 0x51, 4: 0x51},   # D6 west: same; col 4 had the ladder
                36: {4: 0x02},                          # C6: the ladder down to D6 becomes rock
                20: {15: 0x00}, 21: {0: 0x00},           # B6 east edge, B7 west edge: rock
                64: {7: 0x02, 8: 0x08},                 # E5 south gap: rock
                80: {7: 0x17, 8: 0x17}}                 # F5 north gap: bushes
        for code, cols in more.items():
            for col, value in cols.items():
                out[base.ROOM_LAYOUTS_OW + code * 16 + col] = value
        final = bytearray(player.finished(bytes(out)))
        if Q4_PLACEHOLDERS and not BETA_3Q_ONLY:
            q4_placeholders(world, final, notes)
        candle_rules(final, notes)
        item_counter(final, counter_places, notes)
        quiet_stairwells(final, notes)
        sword_makes_2q_enemies(final, notes)
        no_screen_flashes(final, notes)
        wizzrobe_hand_with_magic_sword(final, notes)
        book_shows_secrets(final, notes)
        book_recorder_icons(final, notes)
        red_candle_damage(final, notes)
        if not BETA_3Q_ONLY:
            loop_screens(final, notes)
            q4_secret_squares(final, notes)
            q4_overworld(final, notes)
            book_secrets_4q(final, notes)
            q4_second_entrance(final, notes)
            q4_recorder_warps(final, notes)
            q4_hint_quotes(final, notes)
        recorder_by_quest(final, notes)          # keeps B11's recorder spot 4Q-only (so off in the 3Q-only build)
        if not BETA_3Q_ONLY:
            q4_waterfall(final, notes)
            q4_recorder_stairs_stay(final, notes)
        recorder_stairs_spots(final, notes)
        hungry_goriya_mirrored(final, notes)
        no_clip_screens(final, notes)
        if not BETA_3Q_ONLY:
            q4_back_exit(final, notes)           # after no_clip_screens: it chains the overworld JSR at $B540
        ending_message(final, notes)
        mugger_quote(final, notes)
        if not BETA_3Q_ONLY:
            q4_caves(final, notes)
            q4_quote_texts(final, notes)
            q4_poison(final, notes)
            q4_book_man(final, notes)
            q4_destiny(final, notes)             # after q4_book_man: it chains Level 9's person entry
            q4_overworld_items(final, notes)
            q4_sprite_sets(final, notes)
            q4_bomb_cost(final, notes)
            book2(final, notes)
            e16_no_drain(final, notes)
        q3_g16_hint(final, notes)                # after q4_caves (it may hold the selector read)
        if BETA_3Q_ONLY:
            beta_3q_only(final, notes)
            if os.environ.get("ZELDAQ3_SEAN") == "1":
                sean_start(final, notes)
        return bytes(final), notes


# Candles (PRG1 file offsets, applied to the finished ROM)
BLUE_CANDLE_LIMIT = 0x69DE     # bank 1 $A9CD 'CMP #$01' (copied to RAM $715D): the blue candle's once-per-screen check
FIRE_SECRET_CHECK = 0x10F1E    # bank 4 $8F0E 'JSR $8F5A' at the top of the fire-burns-a-secret check
RECORDER_Y = (173, 141, 141, 173, 141, 141, 141, 141)   # A11 and E3: below their lakes
COAST_MAGICAL_SWORD = True   # F16's coast item -> magical sword: tested, held until more levels are done
WAND_BOOK_FIRE = 0x1F3E9     # bank 7 $F3D9 'LDA $0661 (book); BEQ': the wand beam's fire
FIRE_RULE_ADDR = 0xB470        # bank 4 free space (vanilla $FF)
FIRE_RULE = bytes([            # JSR $8F5A; BCS done; blue candle ($065B = 1) burns only where the inner palette is 3
    0x20, 0x5A, 0x8F,          #   JSR $8F5A        vanilla check (carry set: no)
    0xB0, 0x25,                #   BCS done
    0xAD, 0x5B, 0x06,          #   LDA $065B        candle
    0xC9, 0x01,                #   CMP #$01
    0xD0, 0x0D,                #   BNE ok           red candle (or the wand without a candle): every bush
    0xA4, 0xEB,                #   LDY $EB          screen
    0xB9, 0xFE, 0x68,          #   LDA $68FE,Y      level block table 1: destination << 2 | inner palette
    0x29, 0x03,                #   AND #$03
    0xC9, 0x03,                #   CMP #$03         brown (dead wood) bushes
    0xF0, 0x02,                #   BEQ ok
    0x38, 0x60,                #   SEC, RTS         no secret
    0xA5, 0xEB,                # ok: LDA $EB         G2 in 4Q: its bush is the recorder's, not fire's
    0xC9, 0x61,                #   CMP #$61
    0xD0, 0x0A,                #   BNE yes
    0xAC, 0x16, 0x00,          #   LDY CurSaveSlot (absolute: keeps sword_makes_2q_enemies' search unique)
    0xB9, 0x2D, 0x06,          #   LDA QuestNumbers,Y
    0xF0, 0x02,                #   BEQ yes
    0x38, 0x60,                #   SEC, RTS
    0x18,                      # yes: CLC
    0x60,                      # done: RTS
])


def quiet_stairwells(rom: bytearray, notes: list[str]) -> None:
    """A boss roar keeps looping into a stairwell (mode 9 never runs the room's boss-sound check). Mode 9's
    TransferAttrs step (submode 5) first silences it, as leaving a roar room does: LDA #$80, JSR PlayEffect."""
    bank5 = 16 + 5 * 0x4000
    bank = rom[bank5:bank5 + 0x4000]
    check = bank.index(bytes([0x29, 0x60, 0x0A, 0x2A, 0x2A, 0x2A, 0xAA]))     # CheckBossSoundEffectUW's AND #$60...
    silence = bank.index(bytes([0xA9, 0x80, 0x4C]), check)
    play_effect = bank[silence + 3] | bank[silence + 4] << 8
    attrs = 0x8000 + bank.index(bytes([0xA9, 0x26, 0x85, 0x14, 0xE6, 0x13, 0x60]))   # InitMode9_TransferAttrs
    entry = bytes([attrs & 0xFF, attrs >> 8])
    table = bank.index(bytes([0x62, 0xAB, 0x10, 0xAC]) + entry) + 4          # InitMode9's table: ..., Copy, Attrs
    assert bank.count(bytes([0x62, 0xAB, 0x10, 0xAC]) + entry) == 1
    code = bytes([0xA9, 0x80, 0x20, play_effect & 0xFF, play_effect >> 8, 0x4C]) + entry
    at = base.free_run(rom, bank5 + 0x3900, bank5 + 0x3F00, len(code) + 16) + 8
    rom[at:at + len(code)] = code
    cpu = 0x8000 + at - bank5
    rom[bank5 + table:bank5 + table + 2] = bytes([cpu & 0xFF, cpu >> 8])
    notes.append(f"stairwells silence boss roars: ${cpu:04X} (PlayEffect ${play_effect:04X}), table ${0x8000 + table:04X}")


def _patch_all(rom: bytearray, banks, old: bytes, new: bytes, count: int, what: str, notes: list[str]) -> None:
    hits = []
    for b in banks:
        start = 16 + b * 0x4000
        i = rom.find(old, start, start + 0x4000)
        while i >= 0:
            hits.append(i)
            i = rom.find(old, i + 1, start + 0x4000)
    assert len(hits) == count, (what, [hex(h) for h in hits])
    for i in hits:
        rom[i:i + len(new)] = new
    notes.append(f"{what}: {len(hits)} place(s) " + ", ".join(f"${h:05X}" for h in hits))


def sword_makes_2q_enemies(rom: bytearray, notes: list[str]) -> None:
    """Stalfos shoot, Ropes get 2Q HP ($40) and flash once Link has any sword: each 'second quest?' check
    (LDY CurSaveSlot; LDA QuestNumbers,Y; BEQ) becomes LDA Items+0 (sword); NOP; NOP; BEQ."""
    _patch_all(rom, [4], bytes([0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0]), bytes([0xAD, 0x57, 0x06, 0xEA, 0xEA]), 3,
               "Stalfos/Rope 2Q once Link has a sword", notes)


def no_screen_flashes(rom: bytearray, notes: list[str]) -> None:
    """No full-screen flashing: the Triforce piece's white flash (both copies of the end-level code: the white
    palette buffer $78 becomes the level's own, $18), the ending's background color cycle (all black), and the
    bomb's grayscale blink (UpdateBombFlashEffect returns at once)."""
    _patch_all(rom, [1, 5], bytes([0x29, 0x07, 0xC9, 0x04, 0x90, 0x02, 0xA0, 0x78, 0x84, 0x14]),
               bytes([0x29, 0x07, 0xC9, 0x04, 0x90, 0x02, 0xA0, 0x18]), 2, "no Triforce flash", notes)
    _patch_all(rom, [2], bytes([0x0F, 0x12, 0x16, 0x2A, 0x20]), bytes([0x0F, 0x0F, 0x0F, 0x0F]), 1,
               "no ending flash", notes)
    _patch_all(rom, [1], bytes([0xB5, 0xAC, 0xC9, 0x13, 0xD0, 0x1C, 0xA5]), bytes([0x60]), 1,
               "no bomb blink", notes)


def wizzrobe_hand_with_magic_sword(rom: bytearray, notes: list[str]) -> None:
    """ZORA's Wizzrobes Shoot Wallmasters (asm/flags2/wizzrobe-hand, idea: Ultralavos), gated: only once Link has
    the magical sword (Items $0657 = 3) is a Wizzrobe's shot drawn as the Wallmaster's hand and does a hit send
    Link back to the level's entrance; before that it is the plain magic shot. Both routines get
    LDA $0657 / CMP #$03 / BNE <plain> after their CurLevel test. The damage hook is left out (vanilla damage)."""
    bank4 = 16 + 4 * 0x4000
    seg = 0x13C10
    assert rom[seg:seg + 0x80] == b"\xFF" * 0x80
    assert rom[0x1030E:0x10311] == bytes.fromhex("207183")
    assert rom[0x1F3D4:0x1F3DA] == bytes.fromhex("c957f009d005")
    grab = bytes.fromhex("207183" "ad4b03" "f01c" "a510" "f018" "ad5706" "c903" "d011"
                         "bd4f03" "c958" "900a" "c95a" "b006" "a50c" "d003" "e606" "60"
                         "a512" "c911" "f0f9" "208a82" "a903" "8512" "a900" "85ac" "8511" "8513" "60")
    draw = bytes.fromhex("c957" "f03a" "a023" "a510" "f034" "ad5706" "c903" "d02d"
                         "a504" "29fc" "0901" "8504" "8505" "a900" "8552" "ac4103" "b9ab77" "8d4303"
                         "b9ac77" "8d4403" "8608" "a901" "8507" "a908" "850a" "ada576" "4c4079" "4c1579")
    code = grab + draw
    assert len(code) <= 0x80, len(code)
    rom[seg:seg + len(code)] = code
    base_cpu = 0x8000 + seg - bank4
    draw_cpu = base_cpu + len(grab)
    rom[0x1030F:0x10311] = bytes([base_cpu & 0xFF, base_cpu >> 8])              # JSR CheckShotLinkCollisionOrGrab
    rom[0x1F3D4:0x1F3DA] = bytes([0x4C, draw_cpu & 0xFF, draw_cpu >> 8, 0xEA, 0xEA, 0xEA])   # JMP ChooseMonsterShotSprites
    notes.append(f"Wizzrobe hand with the magical sword: grab ${base_cpu:04X}, draw ${draw_cpu:04X} ({len(code)} bytes)")
    # The hand deals the Wallmaster's damage ($80, half a heart) once Link has the magical sword: HarmLink's
    # LDY ObjType,X / LDA ObjTypeToDamagePoints,Y becomes JSR to a fixed-bank helper that returns $80 for a
    # Wizzrobe shot ($58/$59) in a dungeon with the magical sword, else the table's byte.
    hook = rom.index(bytes([0xE6, 0x0C, 0xBC, 0x4F, 0x03, 0xB9])) + 2
    assert rom.count(bytes([0xE6, 0x0C, 0xBC, 0x4F, 0x03, 0xB9])) == 1 and (hook - 16) // 0x4000 == 1
    table = rom[hook + 4:hook + 6]
    helper_at = 0x1FFD0                                                    # fixed bank $FFC0, free
    assert rom[helper_at:helper_at + 32] == b"\xFF" * 32
    helper = (bytes.fromhex("bc4f03" "c058" "9012" "c05a" "b00e" "a510" "f00a" "ad5706" "c903" "d003" "a980" "60" "b9")
              + table + bytes([0x60]))
    rom[helper_at:helper_at + len(helper)] = helper
    rom[hook:hook + 6] = bytes([0x20, 0xC0, 0xFF, 0xEA, 0xEA, 0xEA])
    notes.append(f"Wizzrobe hand damage = Wallmaster's with the magical sword: helper $FFC0, hook ${hook:05X}")


Q4_DESTS: dict[int, int] = {}          # 4Q overworld destinations that differ (q4_overworld fills it)
BOOK_TABLE_4Q = [None, None]            # file offsets of the 4Q tables, Book 1 and Book 2 (book_shows_secrets)
BOOK2_SKIP_4Q = {0x1A}                  # B11: no book shows it
BOOK_SKIP_4Q = {0x38, 0x39, 0x1A, 0x69}   # D9 (paid hints), D10 (blue ring cave), B11, G10 (100-rupee bush): Book 2 only (B11: never)


def book_secrets_4q(rom: bytearray, notes: list[str]) -> None:
    """The book's 4Q table: a square for each screen whose secret is in 4Q (quest field 0 or 2, a 4Q destination),
    but D7's and B11's. Built after the 4Q overworld changes (its new secret squares and quest fields)."""
    from zora.rom.vanilla_overworld.layouts import read_layout, OW_LAYOUT_COUNT
    ow = rom[0x18410:0x18410 + 0x300]
    kinds = {0x26: "rock", 0x27: "wall", 0x28: "bush", 0x29: "grave"}
    for k, skip in enumerate((BOOK_SKIP_4Q, BOOK2_SKIP_4Q)):
        table = bytearray(b"\xFF" * 128)
        shown = []
        for screen in range(128):
            layout_num = ow[0x180 + screen] & 0x7F
            dest = Q4_DESTS.get(screen, (ow[0x80 + screen] >> 2) & 0x3F)
            quest = Q4_QUEST.get(screen, ow[0x280 + screen] >> 6)
            if layout_num >= OW_LAYOUT_COUNT or dest == 0 or quest not in (0, 2) or screen in skip:
                continue
            layout = read_layout(bytes(rom), layout_num)
            spots = [(c, r) for c in range(16) for r in range(11) if layout[c][r] in kinds]
            if not spots:
                continue
            c, r = spots[0]
            table[screen] = (r >> 1) * 8 + (c >> 1) | ((r & 1) * 2 + (c & 1)) << 6
            shown.append(f"{base.ROWS[screen // 16]}{screen % 16 + 1}")
        rom[BOOK_TABLE_4Q[k]:BOOK_TABLE_4Q[k] + 128] = table
        notes.append(f"Book {k + 1} shows 4Q secrets: " + ", ".join(shown))


def book_shows_secrets(rom: bytearray, notes: list[str]) -> None:
    """With the book, an overworld screen's unfound secret square (pushable rock, bombable wall, burnable bush,
    pushable gravestone) swaps palettes: brown (3) <-> gray (0); green and red are left alone. FillPlayAreaAttrs
    (bank 5) is wrapped: after it fills PlayAreaAttrs, in level 0 with the book and the room's secret flag
    ($067F,Y bit 7) clear, the square's attribute quadrant flips. A 128-byte table holds each screen's square:
    attribute index (0-47) | quadrant << 6, or $FF."""
    from zora.rom.vanilla_overworld.layouts import read_layout, OW_LAYOUT_COUNT
    bank5 = 16 + 5 * 0x4000
    ow = rom[0x18410:0x18410 + 0x300]
    table = bytearray(b"\xFF" * 128)
    kinds = {0x26: "rock", 0x27: "wall", 0x28: "bush", 0x29: "grave"}
    found = {}
    for screen in range(128):
        layout_num = ow[0x180 + screen] & 0x7F
        dest = (ow[0x80 + screen] >> 2) & 0x3F
        quest = ow[0x280 + screen] >> 6
        if layout_num >= OW_LAYOUT_COUNT or dest == 0 or quest not in (0, 1):
            continue
        layout = read_layout(bytes(rom), layout_num)
        spots = [(c, r) for c in range(16) for r in range(11) if layout[c][r] in kinds]
        if not spots:
            continue
        c, r = spots[0]
        table[screen] = (r >> 1) * 8 + (c >> 1) | ((r & 1) * 2 + (c & 1)) << 6
        k = kinds[layout[c][r]]
        found[k] = found.get(k, 0) + 1
    entry = bytes.fromhex("a8b9")            # FillPlayAreaAttrs: TAY / LDA LevelBlockAttrsA,Y / AND #$03 / TAX / LDA sel,X / LDX #$2F
    bank = rom[bank5:bank5 + 0x4000]
    hits = [i for i in range(len(bank) - 12) if bank[i:i + 2] == entry and bank[i + 4:i + 7] == bytes.fromhex("2903aa")
            and bank[i + 7] == 0xBD and bank[i + 10:i + 12] == bytes.fromhex("a22f")]
    assert len(hits) == 1, hits
    fill = hits[0]
    attrs_a = bank[fill + 2:fill + 4]
    cont = 0x8000 + fill + 4
    size = 384 + 150
    at = base.free_run(rom, bank5 + 0x2C00, bank5 + 0x3F00, size + 16) + 8
    tbl_cpu = 0x8000 + at - bank5
    tbl4_cpu = tbl_cpu + 128              # 4Q's tables (book_secrets_4q), Book 1 and Book 2; all $FF until then
    tbl4b_cpu = tbl_cpu + 256
    BOOK_TABLE_4Q[0], BOOK_TABLE_4Q[1] = at + 128, at + 256
    code_cpu = tbl_cpu + 384
    def asm(lines):
        """Two-pass: items are bytes, a label 'name:', ('br', op, label) or ('abs', op, label|int)."""
        for _ in range(2):
            out, labels_ = bytearray(), {}
            for it in lines:
                if isinstance(it, str):
                    labels_[it.rstrip(':')] = code_cpu + len(out)
                elif isinstance(it, tuple) and it[0] == 'br':
                    tgt = asm.labels.get(it[2], code_cpu)
                    out += bytes([it[1], (tgt - (code_cpu + len(out) + 2)) & 0xFF])
                elif isinstance(it, tuple) and it[0] == 'abs':
                    v = it[2] if isinstance(it[2], int) else asm.labels.get(it[2], 0)
                    out += bytes([it[1], v & 0xFF, v >> 8])
                else:
                    out += bytes(it)
            asm.labels = labels_
        return out
    asm.labels = {}
    ATTRS = 0x0530
    code = asm([
        [0x48, 0xA8, 0xB9], attrs_a,                       # PHA / TAY / LDA LevelBlockAttrsA,Y
        ('abs', 0x20, cont),                               # JSR FillPlayAreaAttrs+4
        [0x68, 0xA8],                                      # PLA / TAY
        [0xA5, 0x10], ('br', 0xD0, 'done'),                # overworld only
        ('abs', 0xAD, 0x0661), ('br', 0xF0, 'done'),       # with the book
        ('abs', 0xB9, 0x067F), ('br', 0x30, 'done'),       # secret not found yet
        [0xA6, 0x16], ('abs', 0xBD, 0x062D), ('br', 0xF0, 'q3'),   # LDX slot / LDA quest,X / BEQ q3
        ('abs', 0xAD, 0x0661), [0xC9, 0x02], ('br', 0xB0, 'b2'),   # Book 2?
        ('abs', 0xB9, tbl4_cpu), [0xB8], ('br', 0x50, 'got'),     # 4Q table / CLV / BVC got (always)
        'b2:', ('abs', 0xB9, tbl4b_cpu), [0xB8], ('br', 0x50, 'got'),
        'q3:', ('abs', 0xB9, tbl_cpu),
        'got:', [0xC9, 0xFF], ('br', 0xF0, 'done'),
        [0x48, 0x29, 0x3F, 0xAA, 0x68, 0x4A, 0x4A, 0x4A, 0x4A, 0x4A, 0x4A, 0xA8],   # X = index, Y = quadrant
        ('abs', 0xBD, ATTRS), ('abs', 0x39, 'masks'), ('br', 0xF0, 'gray'),
        ('abs', 0xD9, 'masks'), ('br', 0xF0, 'brown'),
        ('abs', 0xD9, 'masks2'), ('br', 0xD0, 'done'),             # green (2): Book 2 makes it brown
        ('abs', 0xAD, 0x0661), [0xC9, 0x02], ('br', 0xB0, 'gray'), [0x60],
        'gray:', ('abs', 0xBD, ATTRS), ('abs', 0x19, 'masks'), ('abs', 0x9D, ATTRS), [0x60],   # 0 -> 3
        'brown:', ('abs', 0xBD, ATTRS), ('abs', 0x59, 'masks'), ('abs', 0x9D, ATTRS), [0x60],  # 3 -> 0
        'done:', [0x60],
        'masks:', [0x03, 0x0C, 0x30, 0xC0],
        'masks2:', [0x02, 0x08, 0x20, 0x80],
    ])
    assert len(code) + 384 <= size, len(code)
    rom[at:at + 128] = table
    rom[at + 128:at + 384] = b"\xFF" * 256
    rom[at + 384:at + 384 + len(code)] = code
    rom[bank5 + fill:bank5 + fill + 4] = bytes([0x4C, code_cpu & 0xFF, code_cpu >> 8, 0xEA])   # JMP wrapper
    notes.append(f"book shows secrets: table ${tbl_cpu:04X}, code ${code_cpu:04X} ({len(code)} bytes), "
                 f"FillPlayAreaAttrs ${0x8000 + fill:04X}; screens {found}")


RECORDER_ICON = """
......1111......
....11133111....
..113333333311..
..133..1222331..
.133...12222331.
.13....12212231.
113....122122311
133....122111331
133..111221..331
113.1222221..311
.1312222221..31.
.133222221..331.
..1332221..331..
..113333333311..
....11133111....
......1111......
"""
# Where the recorder's stairs come up (square top-left, pixels; checked against the stairs in the emulator), and
# what the square is: water (E3, C3) or sand (C12).
RECORDER_ICON_SPOTS = {0x42: (96, 144, "water"), 0x2B: (96, 144, "sand"), 0x22: (96, 144, "water"),
                       0x61: (112, 112, "sand"), 0x06: (96, 144, "sand"), 0x10: (128, 144, "sand"),   # 4Q: G2, A7, B1
                       0x58: (96, 144, "sand"), 0x30: (96, 144, "sand")}                               # 4Q: F9, D1
# both quests' recorder secrets but B11 (4Q), which has no icon
RECORDER_ICON_QUESTS = {0x42: [0, 1], 0x2B: [0, 1], 0x22: [0, 1], 0x61: [1], 0x06: [1], 0x10: [1], 0x58: [1], 0x30: [1]}
# Icon pixels -> background color index. Water squares (palette 3 on E3: black, brown, tan, blue; palette 0 on C3:
# black, white, gray, blue): blue around it, a brown/white ring, a tan/gray note. Sand (palette 3 on C12): tan
# around it, a blue ring and note. '1' is the black outline.
RECORDER_ICON_COLORS = {"water": {".": 3, "1": 0, "3": 1, "2": 2}, "sand": {".": 2, "1": 0, "3": 3, "2": 3}}
RECORDER_ICON_TILES = {"water": 0x32, "sand": 0x36}


def book_recorder_icons(rom: bytearray, notes: list[str]) -> None:
    """With the book, a recorder screen whose secret isn't open ($067F,Y bit 7 clear) shows a music note in a ring
    as a background square where the recorder's stairs come up. Only the picture changes: the play area map in RAM
    (what collisions read) keeps its water or sand, so walking is unchanged. Tiles: the common BG block's empty
    $32-$39 (water set, sand set). UpdateMode5Play's JSR CheckZora (bank 4, overworld play frames) goes to a
    routine that calls CheckZora and then, every 8th frame, appends two 2-tile vertical records for the square to
    the dynamic transfer buffer (nametable 0, as ChangeTileObjTiles does), so the icon comes back after a cave,
    the menu or a redraw."""
    rows = RECORDER_ICON.strip().split("\n")
    def tile(colors, x0, y0):
        lo, hi = bytearray(8), bytearray(8)
        for y in range(8):
            for x in range(8):
                v = colors[rows[y0 + y][x0 + x]]
                lo[y] |= (v & 1) << (7 - x); hi[y] |= (v >> 1) << (7 - x)
        return bytes(lo + hi)
    chr_src = 0x878F                                   # the common BG block: tile n at chr_src + 16 n
    assert rom[chr_src + 0x30 * 16:chr_src + 0x30 * 16 + 16] == bytes.fromhex("fb5f555555000000fb5f555555000000")
    assert not any(rom[chr_src + 0x32 * 16:chr_src + 0x3A * 16])
    for kind, first in RECORDER_ICON_TILES.items():
        for k, (x0, y0) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
            n = first + k
            rom[chr_src + n * 16:chr_src + n * 16 + 16] = tile(RECORDER_ICON_COLORS[kind], x0, y0)
    fixed = 16 + 7 * 0x4000
    i = rom.find(bytes([0x29, 0x04, 0x0A, 0x0A, 0x0A, 0x20]), fixed, fixed + 0x4000)
    call = i + 6 + 2 + 2 + 3                            # JSR PlayEffect / LDA #4 / JSR SwitchBank / JSR CheckZora
    assert rom[call - 5:call - 3] == bytes([0xA9, 0x04]) and rom[call] == 0x20, rom[i:i + 20].hex()
    check_zora = rom[call + 1] | rom[call + 2] << 8
    bank4 = 16 + 4 * 0x4000
    entries = [(r, q) for r in RECORDER_ICON_SPOTS for q in RECORDER_ICON_QUESTS[r]]
    rooms = [r for r, _ in entries]
    ppu = [0x2000 + ((RECORDER_ICON_SPOTS[r][1] >> 3) * 32) + (RECORDER_ICON_SPOTS[r][0] >> 3) for r in rooms]
    tiles = [RECORDER_ICON_TILES[RECORDER_ICON_SPOTS[r][2]] for r in rooms]
    size = 220
    at = base.free_run(rom, bank4 + 0x3000, bank4 + 0x3F00, size + 16) + 8
    cpu = 0x8000 + at - bank4
    def build(lab):
        out = bytearray(); fix = []
        def here(): return cpu + len(out)
        def br(op, name): out.extend([op, (lab.get(name, here() + 2) - (here() + 2)) & 0xFF])
        def ab(op, v): out.extend([op, v & 0xFF, v >> 8])
        def tab(op, name): fix.append((len(out) + 1, name)); out.extend([op, 0, 0])
        ab(0x20, check_zora)                            # JSR CheckZora
        ab(0xAD, 0x0661); br(0xF0, "rts")               # the book?
        out.extend([0xA5, 0x12, 0xC9, 0x05]); br(0xD0, "rts")       # mode 5
        out.extend([0xA5, 0x15, 0x29, 0x07]); br(0xD0, "rts")       # every 8th frame
        out.extend([0xA2, len(rooms) - 1])
        lab_loop = here(); lab["loop"] = lab_loop
        tab(0xBD, "rooms"); out.extend([0xC5, 0xEB]); br(0xD0, "next")
        out.extend([0xA4, 0x16, 0xB9, 0x2D, 0x06]); tab(0xDD, "quests"); br(0xF0, "found")   # this quest's?
        lab["next"] = here()
        out.append(0xCA); br(0x10, "loop"); out.append(0x60)
        lab["found"] = here()
        out.extend([0xA4, 0xEB]); ab(0xB9, 0x067F); br(0x30, "rts")  # secret open: leave the screen alone
        ab(0xAC, 0x0301)                                            # LDY DynTileBufLen
        tab(0xBD, "hi"); ab(0x99, 0x0302); ab(0x99, 0x0307)
        tab(0xBD, "lo"); ab(0x99, 0x0303); out.extend([0x18, 0x69, 0x01]); ab(0x99, 0x0308)
        out.extend([0xA9, 0x82]); ab(0x99, 0x0304); ab(0x99, 0x0309)
        tab(0xBD, "tile"); ab(0x99, 0x0305)
        for dst in (0x0306, 0x030A, 0x030B):
            out.extend([0x18, 0x69, 0x01]); ab(0x99, dst)
        out.extend([0xA9, 0xFF]); ab(0x99, 0x030C)
        out.extend([0x98, 0x18, 0x69, 0x0A]); ab(0x8D, 0x0301)      # DynTileBufLen += 10
        lab["rts"] = here(); out.append(0x60)
        for name, data in (("rooms", rooms), ("hi", [p >> 8 for p in ppu]), ("lo", [p & 0xFF for p in ppu]),
                           ("tile", tiles), ("quests", [q for _, q in entries])):
            lab[name] = here(); out.extend(data)
        for off, name in fix:
            v = lab.get(name, 0); out[off:off + 2] = bytes([v & 0xFF, v >> 8])
        return out
    lab = {}
    for _ in range(3):
        code = build(lab)
    assert len(code) <= size, len(code)
    rom[at:at + len(code)] = code
    rom[call + 1:call + 3] = bytes([cpu & 0xFF, cpu >> 8])
    notes.append(f"book recorder icons (background squares): code ${cpu:04X} ({len(code)} bytes), tiles $32-$39, "
                 + ", ".join(f"${r:02X} at ${p:04X}" for r, p in zip(rooms, ppu)))


def red_candle_damage(rom: bytearray, notes: list[str]) -> None:
    """Fire hits for $20 (the white sword's) once Link has the red candle ($065B = 2), else $10 as vanilla.
    CheckMonsterBombOrFireCollision's LDA #$10 / STA $07 becomes JSR to a 14-byte fixed-bank helper (the last free
    bytes before the $FFEB header): LDA $065B / CMP #$02 / LDA #$10 / BCC +2 / LDA #$20 / STA $07 / RTS.
    A bomb still overwrites [07] with $40 after it."""
    pat = bytes([0xA9, 0x20, 0x85, 0x09, 0xA9, 0x10, 0x85, 0x07, 0xA9, 0x0E, 0x85, 0x0D])
    assert rom.count(pat) == 1
    site = rom.index(pat) + 4
    helper_at, helper_cpu = 0x1FFED, 0xFFDD
    helper = bytes.fromhex("ad5b06" "c902" "a910" "9002" "a920" "8507" "60")
    assert len(helper) == 14 and rom[helper_at:helper_at + 14] == b"\xFF" * 14 and rom[helper_at + 14:helper_at + 19] == b"ZELDA"
    rom[helper_at:helper_at + 14] = helper
    rom[site:site + 4] = bytes([0x20, helper_cpu & 0xFF, helper_cpu >> 8, 0xEA])
    notes.append(f"red candle fire $20: helper ${helper_cpu:04X}, site ${site:05X}")


# Test (2026-11-13): the wood sword cave with a quest check. 3Q (save quest 0): unchanged at C2. 2Q (quest 1):
# at H8 (C2's cave is 1Q-only already), "CHOOSE YOUR DESTINY", power bracelet / ladder / recorder, take one.
TEST_2Q_WOOD_CAVE = True
BETA_3Q_ONLY = os.environ.get("ZELDAQ3_BETA") == "1"
BETA_VERSION = "1.6"   # the 3Q-only build: no 4Q, no ZELDA name
WOOD_CAVE_2Q_SCREEN = 0x77                         # H8
WOOD_CAVE_2Q_WARES = (0x14, 0x0D, 0x05 | 0x40)      # power bracelet, ladder, recorder (+ the cave's flag bit, as $7F had)
WOOD_CAVE_2Q_QUOTE = 29


Q4_LETTER_CAVE_WARES = (0x3F, 0x11, 0x7F)            # the letter cave (index 8) in 4Q: the Book (vanilla: 3F 1A 7F)
Q4_MAGICAL_SWORD_CAVE_WARES = (0x7F, 0x09, 0x7F)     # the magical sword cave (index 3) in 4Q: the silver arrows
Q4_LETTER_CAVE_QUOTE = 22                            # "KNOWLEDGE IS POWER" (quote 22 is unused in 3Q)
# 4Q's four shops (cave indices 13-16 = destinations $1D-$20): (item, price) x3. Items: bombs $00, bait $04,
# arrows $08, letter $15, key $19, magic shield $1C, heart $22. Each ware byte keeps vanilla's top two flag bits.
Q4_SHOPS = {13: [(0x19, 60), (0x00, 10), (0x22, 5)],      # shop 1: key, bombs, heart
            14: [(0x08, 60), (0x04, 100), (0x1C, 90)],    # shop 2: arrows, bait, magic shield
            15: [(0x15, 50), (0x1C, 60), (0x04, 25)],     # shop 3: letter, magic shield, bait
            16: [(0x22, 1), (0x00, 5), (0x08, 20)]}       # shop 4 (the rare shop, E6 only): heart, bombs, arrows
Q4_RARE_SHOP_SCREEN = 0x45                           # E6


Q4_SCREEN_CAVE_QUOTES = {(0x00, 5): 19,     # A1: a hint cave (cave 5, the lost hills hint's) with quote 19 (4Q text)
                         (0x4F, 8): 30}     # E16: the letter cave's Book (made Book 2 by book2_take) with quote 30


def q4_caves(rom: bytearray, notes: list[str]) -> None:
    """Caves with other wares and text in 4Q. InitCaveContinue's LDA OverworldPersonTextSelectors,Y (Y = cave
    index) becomes JSR to a bank-1 helper: in quest 1, for a listed cave it writes the three wares into the RAM copy
    of attribute E (cave index * 3; prices stay) and returns that cave's selector; else the vanilla selector.
    Listed: the letter cave (8: the Book, quote 22) and, while TEST_2Q_WOOD_CAVE, the wood sword cave (0: its test
    wares, quote 29 with the 'pick one' flag)."""
    bank1 = 16 + 1 * 0x4000
    sel_file = rom.index(bytes([0x40, 0x60, 0x42, 0x42, 0x04, 0x06, 0x48, 0x0A]))
    sel_cpu = 0x8000 + sel_file - bank1
    site = rom.index(bytes([0xB9, sel_cpu & 0xFF, sel_cpu >> 8]), bank1, bank1 + 0x4000)
    E = 0x6A7E
    caves = {8: (Q4_LETTER_CAVE_WARES, (rom[sel_file + 8] & 0xC0) | Q4_LETTER_CAVE_QUOTE * 2)}
    caves[3] = (Q4_MAGICAL_SWORD_CAVE_WARES, rom[sel_file + 3])
    caves[2] = ((0x7F, 0x12, 0x7F), rom[sel_file + 2])          # the white sword cave: the blue ring (same heart check)   # the magical sword cave: silver arrows, same text
    if TEST_2Q_WOOD_CAVE:
        caves[0] = (WOOD_CAVE_2Q_WARES, (rom[sel_file] & 0xC0) | WOOD_CAVE_2Q_QUOTE * 2)
    ow_e = 0x18410 + 4 * 0x80
    prices = {}
    for idx, items in Q4_SHOPS.items():
        flags = rom[ow_e + idx * 3: ow_e + idx * 3 + 3]
        caves[idx] = (tuple((f & 0xC0) | it for f, (it, _) in zip(flags, items)), rom[sel_file + idx])
        prices[idx] = [pr for _, pr in items]
    head = bytearray([0x98, 0x48,                              # TYA / PHA
                      0xA4, 0x16, 0xB9, 0x2D, 0x06,            # LDY CurSaveSlot / LDA QuestNumbers,Y
                      0xF0, 0x00,                              # BEQ vanilla
                      0x68, 0x48, 0xA8])                       # PLA / PHA / TAY
    checks, bodies = bytearray(), []
    for idx, (wares, sel) in caves.items():
        body = bytearray()
        for k, w in enumerate(wares):
            a = E + idx * 3 + k
            body += bytes([0xA9, w, 0x8D, a & 0xFF, a >> 8])
        for k, pr in enumerate(prices.get(idx, [])):         # shops: prices too (attribute E + 60)
            a = E + 60 + idx * 3 + k
            body += bytes([0xA9, pr, 0x8D, a & 0xFF, a >> 8])
        body += bytes([0x68, 0xA8, 0xA9, sel, 0x60])           # PLA / TAY / LDA #selector / RTS
        bodies.append((idx, body))
    # one screen's cave with its own text: (screen, cave index) -> quote; checked before the cave checks
    screen_bodies = []
    for (scr, idx), quote in Q4_SCREEN_CAVE_QUOTES.items():
        wares_part = bytearray()
        for k, w in enumerate(caves[idx][0] if idx in caves else ()):    # the cave's 4Q wares too
            a = E + idx * 3 + k
            wares_part += bytes([0xA9, w, 0x8D, a & 0xFF, a >> 8])
        screen_bodies.append(((scr, idx), bytes(wares_part) + bytes([0x68, 0xA8, 0xA9, (rom[sel_file + idx] & 0xC0) | quote * 2, 0x60])))
    vanilla = bytes([0x68, 0xA8, 0xB9, sel_cpu & 0xFF, sel_cpu >> 8, 0x60])   # PLA / TAY / LDA selectors,Y / RTS
    # layout: head, checks (CPY #i / BEQ body_i ...), JMP-free fallthrough to vanilla, bodies
    n = len(bodies)
    check_len = 7 * n + 13 * len(screen_bodies)
    code = bytearray(head)
    vanilla_at = len(head) + check_len
    body_at = vanilla_at + len(vanilla)
    offs = []
    p_ = body_at
    for idx, body in screen_bodies + bodies:
        offs.append(p_); p_ += len(body)
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(head) + check_len + len(vanilla) + p_ - body_at + 16) + 8
    cpu = 0x8000 + at - bank1
    for ((scr, idx), body), target in zip(screen_bodies, offs):
        t = cpu + target                                   # LDA $EB / CMP #scr / BNE +7 / CPY #i / BNE +3 / JMP body
        code += bytes([0xA5, 0xEB, 0xC9, scr, 0xD0, 0x07, 0xC0, idx, 0xD0, 0x03, 0x4C, t & 0xFF, t >> 8])
    for (idx, body), target in zip(bodies, offs[len(screen_bodies):]):
        t = cpu + target                                   # CPY #i / BNE +3 / JMP body_i
        code += bytes([0xC0, idx, 0xD0, 0x03, 0x4C, t & 0xFF, t >> 8])
    code += vanilla
    for idx, body in screen_bodies + bodies:
        code += body
    code[8] = vanilla_at - 9              # BEQ vanilla (3Q): the vanilla tail PLAs the saved Y
    rom[at:at + len(code)] = code
    rom[site:site + 3] = bytes([0x20, cpu & 0xFF, cpu >> 8])
    notes.append(f"4Q caves (helper ${cpu:04X}): " + ", ".join(f"cave {i} wares {w[0]:02X} {w[1]:02X} {w[2]:02X} selector ${sl:02X}"
                                                         for i, (w, sl) in caves.items()))


# 4Q (the second quest's data): every room of the user's 4Q dungeons (q4/q4_grids.json) as an entrance-style room
# with open doors between rooms of the same piece, until the levels are designed. Entrances picked at a bottom room.
Q4_PLACEHOLDERS = True
Q4_ENTRANCES = {1: "H15", 2: "H4", 3: "H8", 4: "H12", 5: "H13", 6: "H6", 7: "H11", 8: "H12", 9: "H4"}   # bottom of each largest piece
# Level 9's second entrance: the Torch, entered from B11 (q4_second_entrance)
Q4_SECOND_ENTRANCES = [(9, "H7", 0x1A),     # the Torch wing, from B11
                       (9, "H1", 0x77)]     # destiny: H8's cave goes straight to Zelda (q4_destiny)
Q4_ENEMY_SET_FROM = {1: 4, 4: 1}     # 4Q Levels 1 and 4 swap enemy sets
from zora.model.enums import BossSpriteSet as _BSS  # noqa: E402
Q4_BOSS_SETS = {1: _BSS.B, 4: _BSS.A}   # 4Q L1: the Gohma set (Gohma, Manhandla, Gleeok); 4Q L4: the Digdogger set (Aquamentus, Dodongo, Digdogger)
# items on the floor of 4Q rooms: (level, room) -> item
Q4_ROOM_ITEMS = {(6, "B4"): Item.WHITE_SWORD,    # the tip of the Scorpion's tail
                 # the rest of each level's items, on the floor until the levels are designed: the entrance,
                 # and the room north of it for a second item; the magical sword in the Torch's entrance
                 
                 
                 
                 (6, "H6"): Item.RED_CANDLE,
                 (7, "H11"): Item.LADDER,
                 (8, "H12"): Item.WAND, (8, "G12"): Item.MAGICAL_KEY,
                 (9, "H4"): Item.RED_RING, (9, "H7"): Item.MAGICAL_SWORD}
# designed 4Q rooms: (level, room) -> (layout, enemy, count, item, dark); walls stay the placeholder's
Q4_ROOMS = {
    (9, "G5"): (R.BLACK_ROOM, E.ELDER_2, 3, Item.NOTHING, False),      # old man, quote 35 in L9 (Q4_QUOTE_TEXTS);
                                                                       # L9's ELDER is the triforce guard
    (9, "G6"): (R.CIRCLE_WALL, E.BLUE_KEESE, 8, Item.WOOD_SWORD, True),  # 1Q L7's dark keese room; the wood sword in
                                                                       # the walled-in center, out of reach
    (9, "G7"): (R.VERTICAL_CHUTE_ROOM, E.NOTHING, 3, Item.NOTHING, False),   # the Torch's room east of it (a tease)
    # destiny (q4_destiny): Ganon, then an old man where Zelda should be; the real Zelda is reached from H8
    (9, "B6"): (R.GANON_ROOM, E.THE_BEAST, 0, Item.TRIFORCE_OF_POWER, False, A.LAST_BOSS),
    (9, "A6"): (R.BLACK_ROOM, E.ELDER_2, 3, Item.NOTHING, False, A.NONE),    # the shutter never opens
    (9, "H1"): (R.ZELDA_ROOM, E.THE_KIDNAPPED, 0, Item.NOTHING, False, A.NONE),
    # Level 1 (the Bow and Arrow): entrance H15
    (1, "H14"): (R.FIVE_PAIR_ROOM, E.ZOL, 3, Item.KEY, False, A.ALL_DEAD_ITEM, PD),            # key: bottom middle
    (1, "H16"): (R.VERTICAL_MOAT_ROOM, E.POLS_VOICE, 5, Item.MAP, False, A.ALL_DEAD_ITEM, PB),   # map: east side
    (1, "G15"): (R.DOUBLE_MOAT_ROOM, RED_LOOK_WIZZROBE, 3, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),
    (1, "F15"): (R.GLEEOK_ROOM, E.GLEEOK_3, 0, Item.NOTHING, False, A.ALL_DEAD, PA),          # north shutter opens
    (1, "F14"): (R.SPIRAL_STAIR_ROOM, RED_LOOK_WIZZROBE, 5, Item.NOTHING, False),              # stairs: <-> F9
    (1, "F9"): (R.NARROW_STAIR_ROOM, E.VIRE, 6, Item.KEY, False, A.ALL_DEAD_ITEM, PA),         # corridor stairs
    (1, "E9"): (R.SPIKE_TRAP_ROOM, E.THREE_PAIRS_OF_TRAPS, 0, Item.BOMBS, False, A.BLOCK_STAIRS, PA, True),
                                                                       # bomb pack on the floor; push: <-> G11
    (1, "D9"): (R.DOUBLE_MOAT_ROOM, Enemy(0x7B), 5, Item.FIVE_RUPEES, False, A.ALL_DEAD_ITEM, PA),   # 0x7B's first 5:
                                                                       # red and blue Wizzrobes only
    (1, "C9"): (R.FOUR_TALL_ROOM, RED_LOOK_WIZZROBE, 3, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),   # "narrow 4", 4 below
    (1, "B9"): (R.FIVE_PAIR_ROOM, E.POLS_VOICE, 8, Item.KEY, False, A.ALL_DEAD_ITEM, PD),      # key off the blocks
    (1, "B10"): (R.DIAMOND_STAIR_ROOM, E.CORNER_TRAPS, 0, Item.NOTHING, False, A.NONE, PA, True),   # stairs <-> C11
    (1, "C11"): (R.DIAMOND_STAIR_ROOM, E.ZOL, 3, Item.BOW, False, A.ALL_DEAD_ITEM, PD, True),        # 4 Zols (3 -> QTY 3; see
                                                                       # Q4_COUNTS); the bow off the stairs
    (1, "B11"): (R.BLACK_ROOM, E.BOMB_UPGRADER, 3, Item.NOTHING, False),                      # 4Q price: Q4_BOMB_COST
    (1, "G11"): (R.NARROW_STAIR_ROOM, E.RED_GOHMA, 0, Item.COMPASS, False, A.ALL_DEAD_ITEM, PA),   # stairs <-> E9
    (1, "G9"): (R.FOUR_SHORT_ROOM, Enemy(0x7B), 5, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),    # "wide four block"
    (1, "H9"): (R.TURNSTILE_ROOM, E.NOTHING, 3, Item.NOTHING, False, A.NONE, PA, True),
    (1, "H10"): (R.GOHMA_ROOM, E.RED_GOHMA, 0, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),   # push: <-> D15
    (1, "D15"): (R.NARROW_STAIR_ROOM, E.MANHANDLA, 0, Item.FIVE_RUPEES, False, A.ALL_DEAD_ITEM, PA),
    (1, "E15"): (R.VERTICAL_CHUTE_ROOM, E.BLUE_KEESE, 8, Item.KEY, False, A.ALL_DEAD_ITEM, PA),
    (1, "C15"): (R.TWO_FIREBALL_ROOM, E.RED_GOHMA, 0, Item.HEART_CONTAINER, False, A.ALL_DEAD_ITEM, PA),   # the boss
    (1, "C14"): (R.POINTLESS_MOAT_ROOM, E.NOTHING, 3, Item.FIVE_RUPEES, False, A.NONE, PD),    # 5 rupees, off the moat
    (1, "C16"): (R.GRID_ROOM, RED_LOOK_WIZZROBE, 6, Item.BLUE_POTION, False, A.ALL_DEAD_ITEM, PB),   # off the blocks
    (1, "B15"): (R.TRIFORCE_ROOM, E.NOTHING, 3, Item.TRIFORCE, False),
    (1, "F16"): (R.REVERSE_C, E.WALLMASTER, 6, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),  # push: <-> F12
    (1, "F12"): (R.DOUBLE_BLOCK, E.VIRE, 6, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),     # push: <-> F16
    (1, "E12"): (R.TWO_FIREBALL_ROOM, E.VIRE, 6, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),
    (1, "D12"): (R.FOUR_FIREBALL_ROOM, RED_LOOK_WIZZROBE, 6, Item.BLUE_POTION, False, A.ALL_DEAD_ITEM, PA),
    # Level 2 (the Rabbit): entrance H4
    (2, "H5"): (R.DOUBLE_BLOCK, E.STALFOS, 3, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),   # push: <-> F5
    (2, "F5"): (R.SPIRAL_STAIR_ROOM, E.BLUE_KEESE, 6, Item.KEY, False, A.ALL_DEAD_ITEM, PD),     # off the blocks    # stairs <-> H5
    (2, "F4"): (R.FIVE_PAIR_ROOM, E.RED_GORIYA, 6, Item.MAP, False, A.ALL_DEAD_ITEM, PD),
    (2, "C4"): (R.CHEVY_ROOM, E.RED_GORIYA, 3, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),
    (2, "C3"): (R.PLAIN_ROOM, E.RUPEE_BOSS, 3, Item.NOTHING, True),                           # hidden, dark
    (2, "B3"): (R.FOUR_FIREBALL_ROOM, E.SINGLE_DODONGO, 0, Item.BLUE_CANDLE, False, A.ALL_DEAD_ITEM, PA),
    (2, "E4"): (R.SINGLE_SIX_BLOCK_ROOM, E.BLUE_GORIYA, 6, Item.COMPASS, False, A.ALL_DEAD_ITEM, PD),   # off the blocks
    (2, "E3"): (R.PLAIN_ROOM, E.ROPE, 6, Item.KEY, False, A.ALL_DEAD_ITEM, PA),                # layout not given yet
    (2, "D3"): (R.POINTLESS_MOAT_ROOM, E.STALFOS, 6, Item.KEY, False, A.NONE, PA),   # key shown from the start: slot 1's
                                                                       # Stalfos carries it (built-in carrier 0x2A)
    (2, "E2"): (R.TURNSTILE_ROOM, E.NOTHING, 3, Item.NOTHING, False, A.NONE, PA, True),
    (2, "D2"): (R.ZIGZAG_ROOM, E.GEL_2, 6, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),     # push: <-> C5
    (2, "C5"): (R.NARROW_STAIR_ROOM, Enemy(0x7A), 6, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),  # $7A: 3 red + 3 blue
    (2, "D4"): (R.HORIZONTAL_MOAT_ROOM, E.SINGLE_DIGDOGGER, 0, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),
    (2, "D5"): (R.FOUR_FIREBALL_ROOM, E.SINGLE_DODONGO, 0, Item.HEART_CONTAINER, False, A.ALL_DEAD_ITEM, PA),  # boss
    (2, "D6"): (R.TRIFORCE_ROOM, E.NOTHING, 3, Item.TRIFORCE, False),
    # Level 3 (the Broken Boomerang): entrance H8
    (3, "G7"): (R.BLACK_ROOM, E.ELDER, 3, Item.NOTHING, False),        # 'pick your poison' (q4_poison): take one boomerang
    (3, "G8"): (R.DOUBLE_BLOCK, E.BLUE_KEESE, 8, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),   # push: <-> E10
    (3, "E10"): (R.NARROW_STAIR_ROOM, E.BLUE_GOHMA, 0, Item.COMPASS, False, A.ALL_DEAD_ITEM, PA),  # stairs <-> G8
    (3, "F10"): (R.PLAIN_ROOM, E.RED_DARKNUT, 3, Item.MAP, False, A.ALL_DEAD_ITEM, PA),
    (3, "G10"): (R.NSU, E.BLUE_KEESE, 8, Item.KEY, False, A.ALL_DEAD_ITEM, PA),
    (3, "F11"): (R.DOUBLE_SIX_BLOCK_ROOM, E.RED_DARKNUT, 3, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),
    (3, "E11"): (R.FOUR_TALL_ROOM, E.GIBDO, 6, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),          # "narrow four block"
    (3, "D11"): (R.DOUBLE_BLOCK, E.RED_LANMOLA, 0, Item.BLUE_POTION, False, A.ALL_DEAD_ITEM, PA),
    (3, "D10"): (R.FOUR_FIREBALL_ROOM, E.MANHANDLA, 0, Item.HEART_CONTAINER, False, A.ALL_DEAD_ITEM, PA),   # the boss
    (3, "C10"): (R.TRIFORCE_ROOM, E.NOTHING, 3, Item.TRIFORCE, False),
    # Level 4 (the Whirlwind): entrance H12; the Digdogger boss set
    (4, "H11"): (R.GOHMA_ROOM, E.TRIPLE_DIGDOGGER, 0, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),   # push: <-> C8
    (4, "C8"): (R.DOUBLE_BLOCK, E.GEL_2, 6, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),         # hidden; push: <-> H11
    (4, "B8"): (R.VERTICAL_CHUTE_ROOM, E.NOTHING, 3, Item.BOMBS, False, A.NONE, PA),                # empty, bombs in the middle
    (4, "A8"): (R.FOUR_FIREBALL_ROOM, E.TRIPLE_DIGDOGGER, 0, Item.HEART_CONTAINER, False, A.ALL_DEAD_ITEM, PA),   # the boss
    (4, "A9"): (R.TRIFORCE_ROOM, E.NOTHING, 3, Item.TRIFORCE, False),
    (4, "G12"): (R.ZIGZAG_ROOM, Enemy(0x7A), 6, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),     # push: <-> B7
    (4, "B7"): (R.REVERSE_C, E.LIKE_LIKE, 6, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),          # push: <-> G12
    (4, "A7"): (R.FOUR_FIREBALL_ROOM, E.TRIPLE_DODONGO, 0, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),
    (4, "B6"): (R.TWO_FIREBALL_ROOM, E.LIKE_LIKE, 6, Item.KEY, False, A.ALL_DEAD_ITEM, PA),
    (4, "B5"): (R.GRID_ROOM, Enemy(0x7A), 6, Item.MAP, False, A.ALL_DEAD_ITEM, PA),
    (4, "A5"): (R.TWO_FIREBALL_ROOM, E.SINGLE_DIGDOGGER, 0, Item.BLUE_POTION, False, A.ALL_DEAD_ITEM, PA),
    (4, "A6"): (R.SINGLE_SIX_BLOCK_ROOM, Enemy(0x7A), 3, Item.BOMBS, False, A.ALL_DEAD_ITEM, PD),   # red/blue Goriya mix
    (4, "C7"): (R.VERTICAL_CHUTE_ROOM, E.BLUE_KEESE, 8, Item.BOMBS, False, A.NONE, PA),              # bombs on the floor
    (4, "D7"): (R.FOUR_FIREBALL_ROOM, E.SINGLE_DODONGO, 0, Item.COMPASS, False, A.ALL_DEAD_ITEM, PA),
    (4, "D8"): (R.PLAIN_ROOM, E.ROPE, 6, Item.FIVE_RUPEES, False, A.ALL_DEAD_ITEM, PA),             # layout not given
    (4, "E8"): (R.FOUR_FIREBALL_ROOM, Enemy(0x7A), 5, Item.KEY, False, A.ALL_DEAD_ITEM, PA),
    (4, "F8"): (R.REVERSE_C, E.ROPE, 6, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),        # push: the recorder cellar
    # Level 5 (the Hammer): entrance H13
    (5, "G13"): (R.FIVE_PAIR_ROOM, E.CORNER_TRAPS, 0, Item.COMPASS, False, A.BLOCK_STAIRS, PD, True),   # compass on the floor; push: <-> B12
    (5, "B12"): (R.NARROW_STAIR_ROOM, E.GIBDO, 6, Item.FIVE_RUPEES, False, A.ALL_DEAD_ITEM, PA),       # stairs <-> G13
    (5, "A12"): (R.DESERT_ROOM, E.RED_LANMOLA, 0, Item.BOMBS, False, A.ALL_DEAD_ITEM, PA),
    (5, "A13"): (R.DOUBLE_BLOCK, E.RED_DARKNUT, 6, Item.MAP, False, A.ALL_DEAD_ITEM, PA),
    (5, "A14"): (R.POINTLESS_MOAT_ROOM, E.ZOL, 6, Item.KEY, False, A.ALL_DEAD_ITEM, PD),   # off the moat
    (5, "B14"): (R.REVERSE_C, E.GIBDO, 6, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),             # push: <-> E13
    (5, "E13"): (R.DOUBLE_BLOCK, E.BLUE_DARKNUT, 6, Item.NOTHING, False, A.BLOCK_STAIRS, PA, True),   # push: <-> B14
    (5, "F13"): (R.DOUBLE_MOAT_ROOM, E.AQUAMENTUS, 0, Item.NOTHING, False, A.ALL_DEAD, PA),
    (5, "D13"): (R.AQUAMENTUS_ROOM, E.AQUAMENTUS, 0, Item.HEART_CONTAINER, False, A.ALL_DEAD_ITEM, PA),   # the boss
    (5, "C13"): (R.TRIFORCE_ROOM, E.NOTHING, 3, Item.TRIFORCE, False),
    (5, "B13"): (R.BLACK_ROOM, E.BLUE_KEESE, 8, Item.POWER_BRACELET, False, A.ALL_DEAD_ITEM, PA),
    # Level 8 (the Crown): the back way out, G16 (hidden) -> E14 -> D14 (hidden) -> C1 on the overworld
    (8, "G16"): (R.NARROW_STAIR_ROOM, E.NOTHING, 3, Item.NOTHING, False),      # stairs -> E14 (one way); design TBD
    (8, "E14"): (R.HORIZONTAL_CHUTE_ROOM, E.NOTHING, 3, Item.NOTHING, False),  # arrive on the north side
    (8, "D14"): (R.BLACK_ROOM, E.ELDER, 3, Item.NOTHING, False),              # quote 21 in 4Q; east door -> C1 (q4_back_exit)
    (2, "C2"): (R.VERTICAL_ROWS, E.BLUE_KEESE, 8, Item.BOMBS, False, A.NONE, PC),               # bombs on the floor
    (2, "B2"): (R.TWO_FIREBALL_ROOM, E.STALFOS, 3, Item.KEY, False, A.ALL_DEAD_ITEM, PA),
}
# 4Q transports: (level, stairs room, other room, free cell for the staircase, exit spot in a room without stairs)
Q4_TRANSPORTS = [(1, "F14", "F9", "E14", (6, 9)),     # both stair rooms (spiral / corridor)
                 (1, "E9", "G11", "D14", (6, 9)),     # E9's push block / G11's corridor stairs
                 (1, "H10", "D15", "D16", (6, 9)),    # H10's push block / D15's corridor stairs
                 (1, "F16", "F12", "E16", (6, 9)),    # both push blocks
                 (2, "H5", "F5", "E5", (6, 9)),       # H5's push block / F5's spiral stairs
                 (2, "D2", "C5", "F2", (6, 9)),       # D2's push block / C5's corridor stairs
                 (3, "G8", "E10", "F3", (6, 9)),      # G8's push block / E10's corridor stairs
                 (4, "H11", "C8", "A10", (6, 9)),     # both push blocks (C8: the hidden room)
                 (4, "G12", "B7", "A11", (6, 9)),     # both push blocks
                 (5, "G13", "B12", "A16", (6, 9)),    # G13's push block / B12's corridor stairs
                 (5, "B14", "E13", "C6", (6, 9)),     # both push blocks
                 (8, "G16", "E14", "A15", (6, 6)),    # G16's corridor stairs -> E14's north side (no stairs: one way)
                 (1, "B10", "C11", "G14", (6, 9))]    # both diamond stair rooms
Q4_BOSS_ROOMS = {1: "C15", 2: "D5", 3: "D10", 4: "A8", 5: "D13"}
# 4Q item cellars: (level, room whose stairs lead down, free cell for the cellar, item)
Q4_CELLARS = [(4, "F8", "A15", Item.RECORDER)]
Q4_QTY = {}                          # e.g. {4: [4, 5, 6, 8]}: index 0 is also the triple Dodongo's count           # per-level enemy counts (a level has four); others: QTY
Q4_HIDDEN = {(9, "H1"), (1, "B11"), (2, "C3"), (4, "C8"), (8, "G16"), (8, "D14")}                              # rooms left off the level map
Q4_BOMB_COST = 50                                     # the bomb upgrade's price in 4Q (3Q keeps 100)
Q4_ITEM_SPOTS = {1: [0x89, 0xD6, 0x26, 0x8C], 2: [0x89, 0xD6, 0x69, 0x8C]}   # L2 C: 6,9 (a free column in C2)     # A 8,9  B 13,6 (east)  C 2,6  D 8,12 (bottom middle)
# 4Q wall changes from the placeholder's: (level, room) -> {side: wall}
Q4_WALLS = {(9, "G5"): {"N": WALL},                  # the old man: no north door
            (9, "B6"): {"N": SHUT},                  # Ganon -> the fake Zelda room
            (9, "A6"): {"S": SHUT, "E": WALL, "W": WALL},
            (9, "H1"): {"N": WALL, "E": WALL},       # Zelda: only the way in (south, from H8)
            (9, "H2"): {"W": WALL},
            (9, "G6"): {"E": WALK},                  # sword room <-> the Torch's G7: a two-way walk-through wall
            (9, "G7"): {"W": WALK},
            (1, "G15"): {"N": SHUT},
            (1, "F15"): {"N": SHUT},
            (1, "F9"): {"S": LOCK}, (1, "G9"): {"N": LOCK},           # locked both sides
            (1, "B9"): {"S": SHUT}, (1, "C9"): {"N": SHUT},
            (1, "B10"): {"E": WALK}, (1, "B11"): {"W": WALK, "S": WALL},
            (1, "C11"): {"N": WALK},                                  # one way up into B11
            (1, "D15"): {"N": SHUT, "S": BOMB}, (1, "E15"): {"N": BOMB},
            (1, "C15"): {"N": SHUT, "E": WALK, "W": WALK}, (1, "C14"): {"E": WALK}, (1, "C16"): {"W": WALK},
            (1, "E12"): {"N": LOCK}, (1, "D12"): {"S": LOCK},
            (2, "C4"): {"W": WALK}, (2, "C3"): {"E": WALK, "N": WALK, "S": WALL, "W": WALL},
            (2, "B3"): {"S": WALK, "W": LOCK}, (2, "B2"): {"E": LOCK},
            (2, "E4"): {"N": BOMB},
            (2, "D3"): {"N": WALL, "W": BOMB}, (2, "D2"): {"E": BOMB, "N": LOCK},
            (2, "C2"): {"S": LOCK, "E": WALL},
            (2, "C5"): {"S": SHUT, "W": OPEN, "E": WALL}, (2, "D5"): {"N": SHUT, "W": SHUT, "E": SHUT},
            (2, "D4"): {"S": BOMB, "E": SHUT, "N": WALK}, (2, "C4"): {"S": WALK},
            (3, "E10"): {"N": SHUT, "E": WALL}, (3, "E11"): {"W": WALL, "N": SHUT, "S": BOMB},
            (3, "F10"): {"E": LOCK}, (3, "F11"): {"W": LOCK, "N": BOMB},
            (3, "D10"): {"N": SHUT, "S": SHUT},
            (4, "C8"): {"E": WALL}, (4, "B8"): {"S": WALL, "W": LOCK}, (4, "A8"): {"E": SHUT, "W": SHUT, "S": SHUT},
            (4, "B7"): {"E": LOCK, "W": LOCK, "S": WALK}, (4, "A7"): {"E": SHUT, "W": SHUT},
            (4, "B6"): {"E": LOCK, "N": SHUT}, (4, "A5"): {"E": SHUT}, (4, "A6"): {"E": SHUT, "W": SHUT, "S": SHUT},
            (4, "C7"): {"N": WALK, "S": WALK, "E": WALL}, (4, "D7"): {"N": WALK},
            (4, "D8"): {"N": WALL, "S": SHUT}, (4, "E8"): {"S": LOCK}, (4, "F8"): {"N": LOCK},
            (5, "G13"): {"N": LOCK}, (5, "B12"): {"N": SHUT, "E": WALL}, (5, "A12"): {"E": SHUT, "S": SHUT},
            (5, "A13"): {"S": WALL}, (5, "A14"): {"S": LOCK}, (5, "B14"): {"N": LOCK, "W": WALL},
            (5, "F13"): {"N": SHUT}, (5, "D13"): {"N": SHUT}, (5, "C13"): {"N": WALK},
            (5, "B13"): {"W": WALL, "S": WALK},
            (8, "E14"): {"N": WALK}, (8, "D14"): {"S": WALK, "E": OPEN}}
# the item counter's 4Q places (the wood sword in L9 G6 is left out): area -> screens / rooms
Q4_COUNTER_PLACES = {0: [0x77, 0x37, 0x0A, 0x39, 0x33, 0x5F, 0x4F], 3: [0x66]}   # L3 G7: one boomerang (q4_poison)   # + E16: Book 2  # H8 wood cave, D8 Book, A11 silver arrows,
                                                              # D10 blue ring, D4 Armos, F16 coast; the levels'
                                                              # rooms are added by q4_placeholders (MAJOR items)


def q4_placeholders(world, rom: bytearray, notes: list[str]) -> None:
    """Writes the two second-quest room blocks and the second-quest level information. 2Q level info is 1Q's
    with the bytes from $29 on (item spots, map, entrance, stairs, boss, map mask, map PPU commands) replaced
    from LevelInfoUWQ2Replacements1-9 in bank 6 when a 2Q level loads (UpdateMode2Load_Full copies size+1
    bytes). New arrays go to bank 6 free space; the address and size tables are repointed."""
    from zora.rom.serialize.levels import encode_level_block, _serialize_level_info
    from zora.rom.layout import LEVEL_1_6_DATA_ADDRESS_Q2, LEVEL_7_9_DATA_ADDRESS_Q2
    g = json.load(open(base.Q3 / "q4" / "q4_grids.json"))
    level_cells, piece = {}, {}
    for key, info in g["levels"].items():
        blk, ch = key.split(":")
        rows = g[blk]["rows"]
        cells = {r * 16 + c for r in range(8) for c in range(16) if rows[r][c] == ch}
        lv = info["level"]
        level_cells.setdefault(lv, set()).update(cells)
        for n in cells:
            piece[(lv, n)] = key
    blocks = world.blocks_2q
    pools: dict[int, list[int]] = {}
    for blk_index, levels in ((0, range(1, 7)), (1, range(7, 10))):
        block = blocks[blk_index]
        for n in range(128):
            p0, p1 = block.palette_bits(n)
            block[n] = Room.blank(n, p0, p1)
        for lv in levels:
            ent = cell(Q4_ENTRANCES[lv])
            assert ent in level_cells[lv], (lv, Q4_ENTRANCES[lv])
            for n in level_cells[lv]:
                walls = []
                for side, delta in (("N", -16), ("E", 1), ("S", 16), ("W", -1)):
                    other = n + delta
                    edge = (side == "E" and n % 16 == 15) or (side == "W" and n % 16 == 0) or not 0 <= other < 128
                    same = not edge and piece.get((lv, other)) == piece[(lv, n)]
                    second = any(lv == l2 and n == cell(r2) for l2, r2, _ in Q4_SECOND_ENTRANCES)
                    walls.append(OPEN if same or ((n == ent or second) and side == "S") else WALL)
                for (l, rm), sides in Q4_WALLS.items():
                    if l == lv and cell(rm) == n:
                        for side, w in sides.items():
                            walls["NESW".index(side)] = w
                item = next((it for (l, rm), it in Q4_ROOM_ITEMS.items() if l == lv and cell(rm) == n), Item.NOTHING)
                spec = (R.ENTRANCE_ROOM, False, E.NOTHING, 3, item, PA, A.NONE, tuple(walls), 3 if n == ent else 2)
                design = next((d for (l, rm), d in Q4_ROOMS.items() if l == lv and cell(rm) == n), None)
                if design:
                    layout, enemy, count, item, dark = design[:5]
                    trig, pos, push = (design + (A.NONE, PA, False)[len(design) - 5:])[5:8]   # defaults
                    spec = (layout, push, enemy, count, item, pos, trig, tuple(walls), 0 if enemy.name.startswith("ELDER") or enemy in (E.BOMB_UPGRADER, E.MUGGER, E.HUNGRY_GORIYA, E.RUPEE_BOSS) else 2)
                block[n] = make_room(n, spec, {}, {}, {q: i for i, q in enumerate(Q4_QTY.get(lv, QTY))})
                if block[n].item_info.item in MAJOR and block[n].item_info.item != Item.WOOD_SWORD:
                    Q4_COUNTER_PLACES.setdefault(lv, []).append(n)
                if design and dark:
                    block[n].is_dark = True
            for l, a_, b_, where, (ex, ey) in Q4_TRANSPORTS:
                if l != lv:
                    continue
                n = cell(where)
                assert all(n not in level_cells[k] for k in levels), where
                block[n] = StaircaseRoom(room_num=n, room_type=RoomType.TRANSPORT_STAIRCASE, exit_x=ex, exit_y=ey,
                                         left_exit=cell(a_), right_exit=cell(b_), t5_raw=0)
                pools.setdefault(lv, []).append(n)
            for l, rm, where, it in Q4_CELLARS:
                if l != lv:
                    continue
                n = cell(where)
                assert all(n not in level_cells[k] for k in levels), where
                block[n] = StaircaseRoom(room_num=n, room_type=RoomType.ITEM_STAIRCASE, exit_x=6, exit_y=9, item=it,
                                         return_dest=cell(rm),   # the item at 8,9 like vanilla: this level's spot for it
                                         t5_raw=list(Q4_ITEM_SPOTS.get(lv, ENTRANCE_SPOTS)).index(0x89) << 4)
                pools.setdefault(lv, []).append(n)
                if it in MAJOR:
                    Q4_COUNTER_PLACES.setdefault(lv, []).append(n)
    rom[LEVEL_1_6_DATA_ADDRESS_Q2:LEVEL_1_6_DATA_ADDRESS_Q2 + 0x300] = encode_level_block(blocks[0], 0x0E)
    rom[LEVEL_7_9_DATA_ADDRESS_Q2:LEVEL_7_9_DATA_ADDRESS_Q2 + 0x300] = encode_level_block(blocks[1], 0x0E)
    # level info replacements
    bank6 = 16 + 6 * 0x4000
    sizes_at = rom.index(bytes([0x39, 0x37, 0x3D, 0x39, 0x43, 0x40, 0x3F, 0x43, 0x4A]))
    addrs_at = sizes_at - 18
    old_ptrs = [rom[addrs_at + 2 * i] | rom[addrs_at + 2 * i + 1] << 8 for i in range(9)]
    assert old_ptrs[0] == 0x816F, hex(old_ptrs[0])
    info_at = 0x19310
    arrays = []
    for lv in range(1, 10):
        old = world.levels[lv - 1]
        old_repl = rom[bank6 + old_ptrs[lv - 1] - 0x8000: bank6 + old_ptrs[lv - 1] - 0x8000 + rom[sizes_at + lv - 1] + 1]
        cells = sorted(level_cells[lv])
        map_data, commands, map_start, map_cursor = synthesize_minimap(
            set(cells) - {cell(rm) for l, rm in Q4_HIDDEN if l == lv})
        new = Level(
            level_num=lv, entrance_room=cell(Q4_ENTRANCES[lv]), entrance_direction=Direction.SOUTH,
            palette_raw=old.palette_raw, fade_palette_raw=old.fade_palette_raw, staircase_room_pool=pools.get(lv, []),
            room_nums=cells, staircase_nums=sorted(pools.get(lv, [])), block=blocks[0 if lv <= 6 else 1],
            boss_room=cell(Q4_BOSS_ROOMS.get(lv, Q4_ENTRANCES[lv])),
            enemy_sprite_set=world.levels[Q4_ENEMY_SET_FROM.get(lv, lv) - 1].enemy_sprite_set,
            boss_sprite_set=Q4_BOSS_SETS.get(lv, old.boss_sprite_set), start_y=old.start_y,
            item_position_table=list(Q4_ITEM_SPOTS.get(lv, ENTRANCE_SPOTS)), map_start=map_start, map_cursor_offset=map_cursor,
            map_data=map_data, map_ppu_commands=command_block(commands, old.map_ppu_commands), qty_table=list(Q4_QTY.get(lv, QTY)),
            stairway_data_raw=bytes(pools.get(lv, [])) + b"\xFF" * (10 - len(pools.get(lv, []))), rom_level_num=old.rom_level_num,
            screen_status_ram_offset=(old_repl[0x31 - 0x29], old_repl[0x32 - 0x29]))
        new.triforce_room_ptr = None
        blk = bytearray(rom[info_at + lv * 0xFC:info_at + (lv + 1) * 0xFC])
        _serialize_level_info(new, blk)
        end = 0x4F + len(drawn_commands(bytes(blk[0x4F:0x7C])))   # records + terminator ($FF is also a map tile)
        arrays.append(bytes(blk[0x29:end]))
    total = sum(len(a) for a in arrays)
    at = base.free_run(rom, bank6 + 0x2D00, bank6 + 0x3F00, total + 16) + 8
    p = at
    for lv, a in enumerate(arrays, 1):
        rom[p:p + len(a)] = a
        cpu = 0x8000 + p - bank6
        rom[addrs_at + 2 * (lv - 1):addrs_at + 2 * lv] = bytes([cpu & 0xFF, cpu >> 8])
        rom[sizes_at + lv - 1] = len(a) - 1
        p += len(a)
    notes.append(f"4Q placeholders: 2Q blocks rewritten ({sum(len(v) for v in level_cells.values())} rooms), "
                 f"level info arrays at ${0x8000 + at - bank6:04X} ({total} bytes); entrances "
                 + ", ".join(f"L{k} {v}" for k, v in Q4_ENTRANCES.items()))


# Overworld loop screens: leaving the screen this way brings Link back onto the same screen (from the opposite
# edge), like a wrong turn in the forest maze, but with no way through. (screen, direction): east $01, west $02,
# south $04, north $08. Both quests for now.
LOOP_SCREENS = [(0x18, 0x01, 1)]       # (screen, direction, quest: 0 = 3Q, 1 = 4Q): B9's east loops in 4Q


def loop_screens(rom: bytearray, notes: list[str]) -> None:
    """The overworld's JSR CheckMazes (bank 5, after NextRoomId is set) goes to a bank-5 routine that first checks
    the loop table: on a match it sets NextRoomId = RoomId and returns; otherwise it jumps to CheckMazes."""
    maze = rom.index(bytes([0xAE, 0x2F, 0x05, 0xA5, 0x98, 0xA4, 0xEB, 0xC0]))
    check_mazes = maze + 0x780                         # bank 1's code at file $6xxx runs from WRAM at +$780
    assert check_mazes == 0x752F, hex(check_mazes)
    call = rom.index(bytes([0x20, check_mazes & 0xFF, check_mazes >> 8]))
    bank5 = 16 + 5 * 0x4000
    assert (call - 16) // 0x4000 == 5
    n = len(LOOP_SCREENS)
    size = 40 + 3 * n
    at = base.free_run(rom, bank5 + 0x3000, bank5 + 0x3F00, size + 16) + 8
    cpu = 0x8000 + at - bank5
    rooms_cpu = cpu + 40; dirs_cpu = rooms_cpu + n; quests_cpu = dirs_cpu + n
    # loop: CPY rooms,X (no CPY abs,X on the 6502) -> compare via TYA/CMP
    code = bytearray([
        0xA2, n - 1,                                   # LDX #n-1
        0xA5, 0xEB,                                    # loop: LDA RoomId
        0xDD, rooms_cpu & 0xFF, rooms_cpu >> 8,        #   CMP rooms,X
        0xD0, 0x0B,                                    #   BNE next
        0xA5, 0x98,                                    #   LDA ObjDir
        0xDD, dirs_cpu & 0xFF, dirs_cpu >> 8,          #   CMP dirs,X
        0xD0, 0x04,                                    #   BNE next
        0xA4, 0x16, 0xB9, 0x2D, 0x06,                  #   LDY CurSaveSlot / LDA QuestNumbers,Y
        0xDD, quests_cpu & 0xFF, quests_cpu >> 8,      #   CMP quests,X
        0xD0, 0x00,                                    #   BNE next (patched below)
        0xA5, 0xEB, 0x85, 0xEC,                        #   LDA RoomId / STA NextRoomId
        # (falls into RTS below only on a match: the BNE targets skip it)
    ])
    code += bytes([0x60])                              # RTS
    nxt = len(code)
    code += bytes([0xCA, 0x10, (2 - (nxt + 3)) & 0xFF,  # next: DEX / BPL loop
                   0x4C, check_mazes & 0xFF, check_mazes >> 8])   # JMP CheckMazes
    code[8] = nxt - 9                                  # BNE next (after CMP rooms)
    code[15] = nxt - 16                                # BNE next (after CMP dirs)
    code[25] = nxt - 26                                # BNE next (after CMP quests)
    code = bytes(code)
    pad = 40 - len(code)
    assert pad >= 0, len(code)
    code = code + b"\xEA" * pad + bytes(r for r, _, _ in LOOP_SCREENS) + bytes(d for _, d, _ in LOOP_SCREENS) + bytes(q for _, _, q in LOOP_SCREENS)
    rom[at:at + len(code)] = code
    rom[call + 1:call + 3] = bytes([cpu & 0xFF, cpu >> 8])
    notes.append(f"loop screens at ${cpu:04X}: " + ", ".join(f"${r:02X} dir ${d:02X} quest {q}" for r, d, q in LOOP_SCREENS))


Q4_G6 = 0x65                    # G6: Level 3's entrance in 4Q, under one of its rocks
Q4_G6_ROCK = (10, 5)            # the middle rock of column 10 (layout entry 10, square row 5)
Q4_G6_EXIT_ROW = 5
Q4_G6_STAIRS = (11, 5)          # the stairs: the sand right of the rock (below it Link would stand on them while pushing)
Q4_G6_STAIRS_CODE = 3           # overworld stairs spot 3 ($69, used by no push screen) becomes $A9 (column 10, row 5)
Q4_G2 = 0x61                    # G2 (the lost woods): Level 2 in 4Q, the recorder turns a bush into stairs
Q4_G2_BUSH = (7, 3)             # column 7, square row 3: the bush just above the path
Q4_G2_EXIT_ROW = 3
Q4_F9 = 0x58                    # F9: shop 1 in 4Q, the recorder's stairs at the default spot ($60, $90)
Q4_D1 = 0x30                    # D1: 100-rupee secret in 4Q, the recorder's stairs at the default spot ($60, $90)
Q4_G10 = 0x69                   # G10: 100-rupee secret in 4Q under a burnable bush (the middle one of column 5)
Q4_G10_BUSH = (5, 5)
Q4_G14 = 0x6D                   # G14: the dead-end bush burns in 4Q too, a 30-rupee secret (its quest field was 1Q only)
Q4_G14_BUSH = (10, 2)
Q4_QUEST = {Q4_G14: 2}          # quest fields 4Q sets in RAM (q4_overworld), for the book's table
Q4_ARMOS_100 = (0x24, 0x34)     # C5, D5: their secret Armos stairs (both quests) lead to a 100-rupee secret in 4Q
Q4_D10 = 0x39                   # D10 (the fairy pond): a bombable wall behind the fairy -> the white sword cave (blue ring)
Q4_D10_WALL = (7, 1)
Q4_D10_LAYOUT = 33              # D10 shares its layout with A12, E3, E4: it gets the one unused layout code
Q4_D9 = 0x38                    # D9: hint shop 2 (4Q's second paid hints) under the upper lone bush
Q4_D9_BUSH = (12, 4)
Q4_E16 = 0x4F                   # E16: the recorder turns the second broken pier tile into stairs (4Q; no icon)
Q4_E16_PIER = (12, 5)
Q4_E16_EXIT = (8, 5)            # leaving its cave: on the sand by the water (the stairs are in the water)
Q4_A7 = 0x06                    # A7: Level 6 in 4Q, the recorder's stairs at the default spot ($60, $90)
Q4_B1 = 0x10                    # B1: Level 8 in 4Q, the recorder turns the lone rock into stairs; no bomb wall in 4Q
Q4_B1_ROCK = (8, 5)
Q4_D7 = 0x36                    # D7: Level 4 in 4Q, behind a bombable wall (the flat rock above the sand)
Q4_D7_WALL = (5, 3)
# (screen, layout entry, row, plain square, secret square)
Q4_SECRET_SQUARES = [(Q4_G6, Q4_G6_ROCK[0], Q4_G6_ROCK[1], 0x13, 0x26),    # plain rock -> pushable rock
                     (Q4_G2, Q4_G2_BUSH[0], Q4_G2_BUSH[1], 0x19, 0x28),    # plain bush -> secret (burnable) bush
                     (Q4_D7, Q4_D7_WALL[0], Q4_D7_WALL[1], 0x1B, 0x27),
                     (Q4_G10, Q4_G10_BUSH[0], Q4_G10_BUSH[1], 0x19, 0x28),   # plain bush -> burnable bush
                     (Q4_D10, Q4_D10_WALL[0], Q4_D10_WALL[1], 0x1B, 0x27),   # plain rock wall -> bombable
                     (Q4_D9, Q4_D9_BUSH[0], Q4_D9_BUSH[1], 0x19, 0x28)]   # (G14's bush is a secret square already)      # plain bush -> burnable    # plain rock wall -> bombable rock wall


def q4_secret_squares(rom: bytearray, notes: list[str]) -> None:
    """4Q-only secret squares in layouts both quests share (each layout used by its one screen):
    - each needs a column like the screen's with one square made secret; none exists, so new columns are made:
      heap 4 (10 columns) is copied to free space in bank 5 with the new columns appended (codes $4A on) and
      ColumnDirectoryOW (bank 6, copied to $6827) points there;
    - the screen's quest field becomes 'second quest only', so in 3Q the square stays plain
      (IsQuestSecretMismatch);
    - G6's pushed rock shows the stairs at the overworld stairs spot named by LevelBlockAttrsF bits 5-4 (LevelInfo
      spots $57 $49 $99 $69); spot 3 is used by no rock or armos screen, so it becomes $A9;
    - G2's bush: the recorder (RECORDER_STAIRS) puts the stairs on it, and once found the layout draws the secret
      bush square as stairs. Fire there is turned off in 4Q (FIRE_RULE)."""
    from zora.rom.vanilla_overworld import layouts as L
    from zora.rom.vanilla_overworld.tables import ROOM_LAYOUTS_OW
    ow = 0x18410
    table_at = bytes(rom).index(ROOM_LAYOUTS_OW.read(rom))
    heaps = L._heap_starts(rom)
    h = 4
    order = sorted(range(16), key=lambda i: heaps[i])
    end = heaps[order[order.index(h) + 1]]
    ncols = sum(1 for x in rom[heaps[h]:end] if x & 0x80)
    pos = heaps[h] - 1                       # the heap's last column may run on into the next heap's bytes
    for _ in range(ncols):
        pos += 1
        while not rom[pos] & 0x80: pos += 1
    rows, rep = 0, False
    while rows < 11:
        rows += 1
        if rom[pos] & 0x40:
            rep = not rep
            if rep: continue
        pos += 1
    heap = bytearray(rom[heaps[h]:pos])
    placed = []
    # D10: its own copy of its shared layout (code Q4_D10_LAYOUT, used by no screen)
    assert all(rom[ow + 0x180 + x] & 0x7F != Q4_D10_LAYOUT for x in range(0x80))
    old_code = rom[ow + 0x180 + Q4_D10] & 0x7F
    rom[table_at + Q4_D10_LAYOUT * 16:table_at + Q4_D10_LAYOUT * 16 + 16] = rom[table_at + old_code * 16:table_at + old_code * 16 + 16]
    rom[ow + 0x180 + Q4_D10] = (rom[ow + 0x180 + Q4_D10] & 0x80) | Q4_D10_LAYOUT
    for screen, col, row, plain, secret in Q4_SECRET_SQUARES:
        code = rom[ow + 0x180 + screen] & 0x7F
        users = [x for x in range(0x80) if rom[ow + 0x180 + x] & 0x7F == code]
        assert users == [screen], (hex(screen), users)
        entry = table_at + code * 16 + col
        old = rom[entry]
        squares = list(L._column(rom, heaps[old >> 4], old & 15))
        assert squares[row] == plain, (hex(screen), hex(old), squares)
        squares[row] = secret
        enc = bytearray()
        k = 0
        while k < 11:
            if k + 1 < 11 and squares[k + 1] == squares[k]:
                enc.append(squares[k] | 0x40); k += 2
            else:
                enc.append(squares[k]); k += 1
        enc[0] |= 0x80
        new_code = (h << 4) | ncols
        ncols += 1
        assert ncols <= 16
        heap += enc
        placed.append((screen, entry, old, new_code, squares))
    bank5 = 16 + 5 * 0x4000
    at = base.free_run(rom, bank5 + 0x3000, bank5 + 0x3F00, len(heap) + 16) + 8
    rom[at:at + len(heap)] = heap
    cpu = 0x8000 + at - bank5
    d = 16 + 0x19D0F + 2 * h                        # ColumnDirectoryOW (PRG 0x19D0F)
    rom[d:d + 2] = bytes([cpu & 0xFF, cpu >> 8])
    heaps = L._heap_starts(rom)
    for screen, entry, old, new_code, squares in placed:
        assert L._column(rom, heaps[h], new_code & 15) == squares
        rom[entry] = new_code
        f = ow + 0x280 + screen
        assert rom[f] >> 6 == 0 or screen == Q4_D10 and rom[f] >> 6 == 2, hex(rom[f])
        rom[f] = (rom[f] & 0x3F) | (2 << 6)
        notes.append(f"4Q secret square on ${screen:02X}: column ${old:02X} -> ${new_code:02X}")
    # No secret in 4Q: F1's bomb wall becomes first quest only (3Q keeps its take any cave); C1's grave (second quest
    # only, a take any cave) gets quest field 3, which IsQuestSecretMismatch ($8F5A) treats as a mismatch in both
    # quests (its table $8F57 has no entry 3: the byte read is code, $AD, never a quest number)
    for screen, want_old, new in ((0x50, 0, 1), (0x20, 2, 3), (0x26, 0, 1)):   # F1, C1, C7 (bomb wall)
        f = ow + 0x280 + screen
        assert rom[f] >> 6 == want_old, (hex(screen), hex(rom[f]))
        rom[f] = (rom[f] & 0x3F) | (new << 6)
    # G6's stairs spot
    spots = 0x19339
    assert rom[spots:spots + 4] == bytes([0x57, 0x49, 0x99, 0x69])
    others = [x for x in range(0x80) if x != Q4_G6 and (rom[ow + 0x280 + x] >> 4) & 3 == Q4_G6_STAIRS_CODE]
    assert others == [0x20], others        # C1: an open cave (2Q take-any), the spot unused
    rom[spots + Q4_G6_STAIRS_CODE] = (Q4_G6_STAIRS[0] << 4) | (Q4_G6_STAIRS[1] + 4)
    f = ow + 0x280 + Q4_G6
    rom[f] = (rom[f] & 0xCF) | (Q4_G6_STAIRS_CODE << 4)
    # G2: a recorder screen (4Q)
    lst = 0x1EF76                                   # FluteRoomSecretsOW
    k = list(rom[lst:lst + 11]).index(0x80)
    assert RECORDER_QUESTS[k] == 2, (k, RECORDER_QUESTS)
    rom[lst + k] = Q4_G2
    for extra in (Q4_A7, Q4_B1, Q4_F9, Q4_D1, Q4_E16):
        k2 = list(rom[lst:lst + 11]).index(0x80)
        assert RECORDER_QUESTS[k2] == 2, (k2, RECORDER_QUESTS)
        rom[lst + k2] = extra
    # B1's bomb wall: first quest only (3Q keeps its money-making game; 4Q has none)
    f = ow + 0x280 + Q4_B1
    assert rom[f] >> 6 == 0, hex(rom[f])
    rom[f] = (rom[f] & 0x3F) | (1 << 6)
    notes.append(f"heap 4 moved to ${cpu:04X}; G6 stairs spot {Q4_G6_STAIRS_CODE} = ${rom[spots + Q4_G6_STAIRS_CODE]:02X}; "
                 f"G2 in the recorder list (entry {k})")


def q4_overworld(rom: bytearray, notes: list[str]) -> None:
    """4Q's overworld differences, written over the RAM copies when the overworld loads in quest 2: vanilla's
    @PatchQ2Rooms (bank 6) ends LDA #$00 / STA LevelBlockAttrsF+116 / RTS; that becomes JMP to a routine that
    does the same and then applies a list of (RAM address, value) writes."""
    ow = rom[0x18410:0x18410 + 0x300]
    attrs_b, any_road = 0x68FE, 0x6BB2                      # LevelBlockAttrsB; the overworld's cellar array = any road list
    roads = list(rom[0x19344:0x19348])
    pal = lambda screen: ow[0x80 + screen] & 0x03
    writes = [
        (attrs_b + Q4_G6, (0x03 << 2) | pal(Q4_G6)),        # G6 (its pushable rock, 4Q only): Level 3
        # G6's exit (out of Level 3): beside the rock's square
        (0x687E + Q4_G6, (Q4_G6_STAIRS[0] << 4) | (ow[Q4_G6] & 0x07)),   # (bit 3 off: no Zora in 4Q)
        (0x6AFE + Q4_G6, (ow[0x280 + Q4_G6] & 0xF8) | Q4_G6_EXIT_ROW),
        (attrs_b + 0x19, (0x09 << 2) | pal(0x19)),          # B10 (its bombable wall, 2Q only): Level 9's main entrance
        (attrs_b + 0x0F, (0x07 << 2) | pal(0x0F)),          # A16 (its open cave): Level 7
        (attrs_b + 0x5E, (0x01 << 2) | pal(0x5E)),          # F15 (3Q's Level 8 front): Level 1
        (attrs_b + 0x37, (0x18 << 2) | pal(0x37)),          # D8: the letter cave (4Q: the Book, "KNOWLEDGE IS POWER")
        (attrs_b + Q4_G2, (0x02 << 2) | pal(Q4_G2)),        # G2 (the recorder's bush): Level 2
        (attrs_b + 0x22, (0x05 << 2) | pal(0x22)),          # C3 (the recorder's lake, both quests): Level 5
        (attrs_b + Q4_A7, (0x06 << 2) | pal(Q4_A7)),        # A7 (recorder): Level 6
        (0x687E + Q4_A7, (6 << 4) | (ow[Q4_A7] & 0x0F)),
        (0x6AFE + Q4_A7, (ow[0x280 + Q4_A7] & 0xF8) | 5),
        (attrs_b + Q4_B1, (0x08 << 2) | pal(Q4_B1)),        # B1 (recorder, the lone rock): Level 8
        (attrs_b + 0x0A, (0x13 << 2) | pal(0x0A)),          # A11 (3Q's Level 1 front): the magical sword cave (silver arrows)
        (attrs_b + 0x2F, (0x1B << 2) | pal(0x2F)),          # C16 (3Q's Level 9 front): the paid hint cave (3Q's C3)
        (attrs_b + 0x1F, (0x16 << 2) | pal(0x1F)),          # B16 (3Q's Level 6 front): the money-making game
        (attrs_b + Q4_D7, (0x04 << 2) | pal(Q4_D7)),        # D7 (bombable wall): Level 4
        (0x687E + Q4_D7, (Q4_D7_WALL[0] << 4) | (ow[Q4_D7] & 0x0F)),
        (0x6AFE + Q4_D7, (ow[0x280 + Q4_D7] & 0xF8) | Q4_D7_WALL[1]),
        (0x687E + Q4_B1, (Q4_B1_ROCK[0] << 4) | (ow[Q4_B1] & 0x0F)),
        (0x6AFE + Q4_B1, (ow[0x280 + Q4_B1] & 0xF8) | Q4_B1_ROCK[1]),
        (0x687E + Q4_G2, (Q4_G2_BUSH[0] << 4) | (ow[Q4_G2] & 0x0F)),
        (0x6AFE + Q4_G2, (ow[0x280 + Q4_G2] & 0xF8) | Q4_G2_EXIT_ROW),
        (attrs_b + Q4_RARE_SHOP_SCREEN, (0x20 << 2) | pal(Q4_RARE_SHOP_SCREEN)),   # E6: shop 4 (the rare shop)
        (attrs_b + 0x0C, (0x1D << 2) | pal(0x0C)),          # A13: shop 1 (so shop 4 is only at E6)
        (attrs_b + Q4_F9, (0x1D << 2) | pal(Q4_F9)),        # F9 (recorder): shop 1
        (attrs_b + Q4_D1, (0x22 << 2) | pal(Q4_D1)),        # D1 (recorder): 100-rupee secret
        (attrs_b + Q4_E16, (0x18 << 2) | pal(Q4_E16)),      # E16 (recorder, the pier): the letter cave -> Book 2
        (0x687E + Q4_E16, (Q4_E16_EXIT[0] << 4) | (ow[Q4_E16] & 0x0F)),
        (0x6AFE + Q4_E16, (ow[0x280 + Q4_E16] & 0xF8) | Q4_E16_EXIT[1]),
        (0x687E + Q4_D1, (6 << 4) | (ow[Q4_D1] & 0x0F)),
        (0x6AFE + Q4_D1, (ow[0x280 + Q4_D1] & 0xF8) | 5),
        (attrs_b + Q4_D10, (0x12 << 2) | pal(Q4_D10)),      # D10 (bomb wall): the white sword cave (4Q: blue ring)
        (0x687E + Q4_D10, (Q4_D10_WALL[0] << 4) | (ow[Q4_D10] & 0x0F)),
        (0x6AFE + Q4_D10, (ow[0x280 + Q4_D10] & 0xF8) | Q4_D10_WALL[1]),
        (attrs_b + 0x51, (0x17 << 2) | pal(0x51)),
        (attrs_b + 0x09, (0x19 << 2) | pal(0x09)),          # A10: a hint cave (cave 9, quote 7: 4Q text)
        (attrs_b + 0x1B, (0x11 << 2) | pal(0x1B)),          # B12: take any
        (attrs_b + 0x04, (0x11 << 2) | pal(0x04)),          # A5: take any
        (attrs_b + 0x0E, (0x1E << 2) | pal(0x0E)),          # A15: shop 2 (was a second letter cave)
        (attrs_b + 0x11, (0x21 << 2) | pal(0x11)),          # B2 (push rock): 30-rupee secret
        (attrs_b + 0x2B, (0x17 << 2) | pal(0x2B)),          # C12 (recorder, as 3Q's): door repair
        (attrs_b + 0x42, (0x1A << 2) | pal(0x42)),          # E3 (recorder, as 3Q's): potion shop
        (attrs_b + 0x74, (0x16 << 2) | pal(0x74)),          # H5: money-making game
        (attrs_b + 0x1C, (0x23 << 2) | pal(0x1C)),          # B13 (secret Armos): 10-rupee secret
        (attrs_b + 0x3C, (0x17 << 2) | pal(0x3C)),          # D13: door repair
        (attrs_b + Q4_D9, (0x1C << 2) | pal(Q4_D9)),        # D9 (burnable bush): hint shop 2
        (0x687E + Q4_D9, (Q4_D9_BUSH[0] << 4) | (ow[Q4_D9] & 0x0F)),
        (0x6AFE + Q4_D9, (ow[0x280 + Q4_D9] & 0xF8) | Q4_D9_BUSH[1]),
        (attrs_b + 0x6C, (0x17 << 2) | pal(0x6C)),          # G13 (burnable bush): door repair
        (attrs_b + Q4_G14, (0x21 << 2) | pal(Q4_G14)),      # G14 (burnable bush): 30-rupee secret in 4Q
        (0x687E + Q4_G14, (Q4_G14_BUSH[0] << 4) | (ow[Q4_G14] & 0x0F)),
        (0x6AFE + Q4_G14, (Q4_QUEST[Q4_G14] << 6) | (ow[0x280 + Q4_G14] & 0x38) | Q4_G14_BUSH[1]),
        (attrs_b + 0x00, (0x15 << 2) | pal(0x00)),          # A1: a hint cave (its own text, Q4_SCREEN_CAVE_QUOTES)
        (attrs_b + 0x7F, (0x17 << 2) | pal(0x7F)),          # H16: door repair
        (attrs_b + 0x6F, (0x11 << 2) | pal(0x6F)),          # G16: take any          # F2: door repair (its white sword cave is D10's in 4Q)
        (attrs_b + Q4_G10, (0x22 << 2) | pal(Q4_G10)),      # G10 (burnable bush): 100-rupee secret
        (0x687E + Q4_G10, (Q4_G10_BUSH[0] << 4) | (ow[Q4_G10] & 0x0F)),
        (0x6AFE + Q4_G10, (ow[0x280 + Q4_G10] & 0xF8) | Q4_G10_BUSH[1]),
        (attrs_b + 0x24, (0x22 << 2) | pal(0x24)),          # C5 (secret Armos): 100-rupee secret
        (attrs_b + 0x34, (0x22 << 2) | pal(0x34)),          # D5 (secret Armos): 100-rupee secret
        (0x687E + Q4_F9, (6 << 4) | (ow[Q4_F9] & 0x0F)),
        (0x6AFE + Q4_F9, (ow[0x280 + Q4_F9] & 0xF8) | 5),
        (attrs_b + 0x1A, (0x09 << 2) | pal(0x1A)),          # B11 (the waterfall): Level 9's second entrance (the Torch)
        # B11's exit (where Link comes out of Level 9's Torch): just below the recorder's stairs, on the sand
        # (standing on the stairs would take him straight back down)
        (0x687E + 0x1A, ((RECORDER_STAIRS[0x1A][0] // 16) << 4) | (ow[0x1A] & 0x0F)),
        (0x6AFE + 0x1A, (ow[0x280 + 0x1A] & 0xF8) | ((RECORDER_STAIRS[0x1A][1] - 64) // 16)),
        # C1's exit (where Link comes out of Level 8's back door, q4_back_exit): between two graves
        (0x687E + Q4_BACK_EXIT_SCREEN, (Q4_BACK_EXIT_XY[0] << 4) | (ow[Q4_BACK_EXIT_SCREEN] & 0x0F)),
        (0x6AFE + Q4_BACK_EXIT_SCREEN, (ow[0x280 + Q4_BACK_EXIT_SCREEN] & 0xF8) | Q4_BACK_EXIT_XY[1]),
    ]
    if TEST_2Q_WOOD_CAVE:
        writes.append((attrs_b + WOOD_CAVE_2Q_SCREEN, (0x10 << 2) | pal(WOOD_CAVE_2Q_SCREEN)))   # H8: wood sword cave
    tail = bytes([0xA9, 0x01, 0x8D, 0x3A, 0x6B, 0xA9, 0x00, 0x8D, 0x72, 0x6B, 0x60])
    assert rom.count(tail) == 1
    site = rom.index(tail) + 5
    bank6 = 16 + 6 * 0x4000
    Q4_DESTS.update({a - attrs_b: v >> 2 for a, v in writes if attrs_b <= a < attrs_b + 0x80})
    n = len(writes)
    size = 32 + 3 * n
    at = base.free_run(rom, bank6 + 0x2D00, bank6 + 0x3F00, size + 16) + 8
    cpu = 0x8000 + at - bank6
    lo_cpu = cpu + 32; hi_cpu = lo_cpu + n; val_cpu = hi_cpu + n
    code = bytearray([0xA9, 0x00, 0x8D, 0x72, 0x6B,         # LDA #0 / STA LevelBlockAttrsF+116 (vanilla's last write)
                      0xA2, n - 1,                          # LDX #n-1
                      0xBD, lo_cpu & 0xFF, lo_cpu >> 8, 0x85, 0x00,
                      0xBD, hi_cpu & 0xFF, hi_cpu >> 8, 0x85, 0x01,
                      0xBD, val_cpu & 0xFF, val_cpu >> 8,
                      0xA0, 0x00, 0x91, 0x00,               # LDY #0 / STA ($00),Y
                      0xCA, 0x10, 0x00,                     # DEX / BPL loop
                      0x60])
    code[26] = (7 - 27) & 0xFF
    code += b"\xEA" * (32 - len(code))
    code += bytes(a & 0xFF for a, _ in writes) + bytes(a >> 8 for a, _ in writes) + bytes(v for _, v in writes)
    rom[at:at + len(code)] = code
    rom[site:site + 6] = bytes([0x4C, cpu & 0xFF, cpu >> 8, 0xEA, 0xEA, 0xEA])
    notes.append(f"4Q overworld patch list at ${cpu:04X}: " + ", ".join(f"${a:04X}=${v:02X}" for a, v in writes))


def q4_second_entrance(rom: bytearray, notes: list[str]) -> None:
    """A level entered from a given overworld screen starts in another room: when a quest-2 level loads,
    UpdateMode2Load_Full copies its level info replacement bytes down to Y = 0 (LDA ($00),Y / STA $6BA7,Y);
    that copy becomes JSR to a bank-6 helper which, after the last byte, sets LevelInfo_StartRoomId to the second
    entrance when CurLevel and CaveSourceRoomId (the overworld screen entered from) match."""
    loop = bytes([0xB1, 0x00, 0x99, 0xA7, 0x6B, 0x88, 0x10, 0xF8, 0x60])
    assert rom.count(loop) == 1
    site = rom.index(loop)
    bank6 = 16 + 6 * 0x4000
    # 4Q enemy counts: the replacement starts at $29, so the counts ($24-$27) would stay 1Q's; after the copy the
    # helper also writes the level's four counts from a 4Q table (Q4_QTY, else the 1Q level's own)
    info_at = 0x19310
    qty = bytearray()
    for lv in range(1, 10):
        qty += bytes(Q4_QTY.get(lv, rom[info_at + lv * 0xFC + 0x24:info_at + lv * 0xFC + 0x28]))
    head = bytes([0xB1, 0x00, 0x99, 0xA7, 0x6B,         # LDA ($00),Y / STA LevelInfo+$29,Y (the vanilla copy)
                  0xC0, 0x00, 0xD0, 0x00])              # CPY #0 / BNE ret
    at = base.free_run(rom, bank6 + 0x2D00, bank6 + 0x3F00, 96 + 16) + 8
    cpu = 0x8000 + at - bank6
    body = bytearray([0x8A, 0x48, 0xA5, 0x10, 0x0A, 0x0A, 0xAA])   # TXA / PHA / LDA CurLevel / ASL / ASL / TAX
    tail_len = 7 + 4 * 6 + 2 + 18 * len(Q4_SECOND_ENTRANCES) + 1   # body + RTS
    tq = cpu + len(head) + tail_len - 4                 # table - 4 (levels 1-9)
    for k in range(4):
        body += bytes([0xBD, (tq + k) & 0xFF, (tq + k) >> 8, 0x8D, 0xA2 + k, 0x6B])   # LDA tbl,X / STA LevelInfo+$24+k
    body += bytes([0x68, 0xAA])                         # PLA / TAX
    for level, room_name, screen in Q4_SECOND_ENTRANCES:
        body += bytes([0xA5, 0x10, 0xC9, level, 0xD0, 0x0C,  # LDA CurLevel / CMP #level / BNE next
                       0xAD, 0x26, 0x05, 0xC9, screen, 0xD0, 0x05,   # LDA CaveSourceRoomId / CMP #screen / BNE next
                       0xA9, cell(room_name), 0x8D, 0xAD, 0x6B])     # LDA #room / STA LevelInfo_StartRoomId
    code = bytearray(head) + body + bytes([0x60])       # ret: RTS
    assert len(code) == len(head) + tail_len, (len(code), len(head) + tail_len)
    code[8] = len(code) - 1 - 9
    code += qty
    rom[at:at + len(code)] = code
    rom[site:site + 5] = bytes([0x20, cpu & 0xFF, cpu >> 8, 0xEA, 0xEA])
    notes.append("4Q second entrances: " + ", ".join(f"Level {lv} from ${sc:02X} starts in {rm}"
                                                     for lv, rm, sc in Q4_SECOND_ENTRANCES) + f" (helper ${cpu:04X})")


Q4_BACK_EXIT = (8, "D14", "E")         # 4Q: walking out this room's door leaves the dungeon ...
Q4_BACK_EXIT_SCREEN = 0x20             # ... onto C1
Q4_BACK_EXIT_XY = (8, 4)               # C1's exit: column 8, y code 4 (Link's y $8D): between two graves


def q4_back_exit(rom: bytearray, notes: list[str]) -> None:
    """A second way out of a dungeon. Mode 6 (bank 5 $B53C) works out the next room ($EC) and, if it runs off
    the grid (negative), leaves the level for the overworld screen in CaveSourceRoomId ($0526). Its 'LDA $10 /
    BNE / JSR (overworld) / LDA $EC / BPL' becomes JSR helper / BPL: in quest 1, in that level and room, going
    that way, the helper sets $0526 to the screen and returns negative, so Link leaves the dungeon there; he
    comes out at the screen's exit spot (set in 4Q by q4_overworld)."""
    lv, name, side = Q4_BACK_EXIT
    room = cell(name)
    nxt = room + {"N": -16, "S": 16, "W": -1, "E": 1}[side]
    bank5 = 16 + 5 * 0x4000
    site = bank5 + 0x353C
    old = rom[site:site + 11]
    assert old[:4] == bytes([0xA5, 0x10, 0xD0, 0x03]) and old[4] == 0x20 and old[7:] == bytes([0xA5, 0xEC, 0x10, 0x12]), old.hex()
    ow_jsr = old[4:7]
    code = bytearray([0xA5, 0x10, 0xD0, 0x05])            # LDA CurLevel / BNE uw
    code += ow_jsr + bytes([0xA5, 0xEC, 0x60])             # JSR (overworld) / LDA $EC / RTS
    uw = len(code)
    code += bytes([0xC9, lv, 0xD0, 0x00,                   # CMP #level / BNE norm
                   0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x00,   # LDY slot / LDA quest,Y / BEQ norm
                   0xA5, 0xEB, 0xC9, room, 0xD0, 0x00,     # LDA room / CMP / BNE norm
                   0xA5, 0xEC, 0xC9, nxt, 0xD0, 0x00,      # LDA next / CMP / BNE norm
                   0xA9, Q4_BACK_EXIT_SCREEN, 0x8D, 0x26, 0x05,   # LDA #screen / STA CaveSourceRoomId
                   0xA9, 0x80, 0x60])                      # LDA #$80 (negative: leave) / RTS
    norm = len(code)
    code += bytes([0xA5, 0xEC, 0x60])                      # norm: LDA $EC / RTS
    code[3] = uw - 4
    for at_ in (uw + 3, uw + 10, uw + 16, uw + 22):
        code[at_] = norm - (at_ + 1)
    at = base.free_run(rom, bank5 + 0x2C00, bank5 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank5
    rom[at:at + len(code)] = code
    b559 = 0xB559 - (0xB53C + 5)
    rom[site:site + 11] = bytes([0x20, cpu & 0xFF, cpu >> 8, 0x10, b559]) + b"\xEA" * 6
    notes.append(f"4Q back exit: L{lv} {name} {side} -> screen ${Q4_BACK_EXIT_SCREEN:02X} (helper ${cpu:04X})")


Q4_WARP_ENTRANCES = {1: "F15", 2: "G2", 3: "G6", 4: "D7", 5: "C3", 6: "A7", 7: "A16", 8: "B1"}   # 4Q level entrances so far; the whirlwind drops Link one screen west
Q4_WARP_Y = {1: 0x8D, 2: 0x8D, 3: 0x8D, 4: 0x8D, 5: 0xAD, 6: 0x8D, 7: 0x8D, 8: 0x8D}   # 5 (C3): below the pond, not in it


def q4_recorder_warps(rom: bytearray, notes: list[str]) -> None:
    """The whirlwind (bank 1 $A06D / $A135) reads one table for both quests: screen ($A010,Y) and Link's y
    ($A119,Y) per level 1-8, the screen west of each entrance. Both reads become JSRs to bank-1 helpers that use a
    4Q table when QuestNumbers[CurSaveSlot] is 1 (4Q), the 3Q table otherwise. Levels not yet placed in 4Q keep
    the 3Q values."""
    bank1 = 16 + 1 * 0x4000
    sites = {"screen": (0x607D, 0xA010), "y": (0x6145, 0xA119)}
    tables = {}
    for k, (site, table) in sites.items():
        assert rom[site:site + 3] == bytes([0xB9, table & 0xFF, table >> 8]), (k, rom[site:site + 3].hex())
        f = bank1 + table - 0x8000
        tables[k] = bytearray(rom[f:f + 8])
    for lvl, name in Q4_WARP_ENTRANCES.items():
        tables["screen"][lvl - 1] = cell(name) - 1
        tables["y"][lvl - 1] = Q4_WARP_Y[lvl]
    for k, (site, table) in sites.items():
        size = 21 + 8
        at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, size + 16) + 8
        cpu = 0x8000 + at - bank1
        t4 = cpu + 21
        helper = bytes([0x98, 0x48, 0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x06,   # TYA/PHA/LDY slot/LDA quest,Y/BEQ q3
                        0x68, 0xA8, 0xB9, t4 & 0xFF, t4 >> 8, 0x60,            # PLA/TAY/LDA 4Q,Y/RTS
                        0x68, 0xA8, 0xB9, table & 0xFF, table >> 8, 0x60])     # q3: PLA/TAY/LDA 3Q,Y/RTS
        assert len(helper) == 21
        rom[at:at + size] = helper + bytes(tables[k])
        rom[site:site + 3] = bytes([0x20, cpu & 0xFF, cpu >> 8])
    notes.append("4Q whirlwind: screens " + " ".join(f"${x:02X}" for x in tables["screen"]) +
                 ", y " + " ".join(f"${x:02X}" for x in tables["y"]))


# 4Q's paid hint cave (hint shop 1, B16): its three hints (25, 50, 100 rupees) as quote ids; None keeps 3Q's
Q4_HINT_SHOP_1_QUOTES = [None, None, None]


def q4_hint_quotes(rom: bytearray, notes: list[str]) -> None:
    """The hint shops' quote table (bank 1 $893B: shop 1's three slots, then shop 2's) is read by one
    LDA $893B,Y; that becomes JSR to a bank-1 helper that reads a 4Q copy in quest 1, so 4Q's hint shop 1 can say
    other hints."""
    bank1 = 16 + 1 * 0x4000
    table = 0x893B
    site = rom.index(bytes([0xB9, table & 0xFF, table >> 8, 0x8D, 0x15, 0x04]), bank1, bank1 + 0x4000)
    f = bank1 + table - 0x8000
    t4 = bytearray(rom[f:f + 6])
    for k, q in enumerate(Q4_HINT_SHOP_1_QUOTES):
        if q is not None:
            assert q < 32, q
            t4[k] = (t4[k] & 0xC1) | (q * 2)
    size = 21 + 6
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, size + 16) + 8
    cpu = 0x8000 + at - bank1
    tq = cpu + 21
    helper = bytes([0x98, 0x48, 0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x06,   # TYA/PHA/LDY slot/LDA quest,Y/BEQ q3
                    0x68, 0xA8, 0xB9, tq & 0xFF, tq >> 8, 0x60,            # PLA/TAY/LDA 4Q,Y/RTS
                    0x68, 0xA8, 0xB9, table & 0xFF, table >> 8, 0x60])     # q3: PLA/TAY/LDA 3Q,Y/RTS
    rom[at:at + size] = helper + bytes(t4)
    rom[site:site + 3] = bytes([0x20, cpu & 0xFF, cpu >> 8])
    notes.append(f"4Q hint shop quotes (helper ${cpu:04X}): " + " ".join(f"{b:02X}" for b in t4))


# 4Q-only texts for quotes: quote id -> lines (bank 1's text pointer read, LDY $0415 / LDA $8000,Y ...,
# goes through a helper that, in quest 1, points listed quotes at new text). Quote 7 is the lost woods hint
# cave's (cave 9), which 4Q has only at A10.
Q4_QUOTE_TEXTS = {7: ["THEY SAY THE", "SCORPIONS TAIL IS AS", "SHARP AS A SWORD"],
                  19: ["GANNON'S FORTRESS CAN", "ONLY BE REACHED FROM", "THE EAST"],   # A1 (Q4_SCREEN_CAVE_QUOTES)
                  35: ["YOU CAN'T HAVE IT, BUT", "THERE IS ANOTHER HERE"],
                  30: ["I HAVE THE UNABRIDGED", "VERSION!"],
                  31: ["PICK YOUR POISON"],
                  21: ["PLAY YOUR RECORDER", "ON THE EAST COAST"],   # 4Q L8 D14 (group B's ELDER)
                  22: ["KNOWLEDGE IS POWER"],                        # 4Q's letter cave (q4_caves); 3Q: G16's old man
                  36: ["FIND MY STOLEN BLUE", "BOOK AND I'LL TELL", "YOU SOMETHING"],   # L9's ELDER_3: the book man
                  23: ["I USED TO LOVE PLAYING", "MY RECORDER AT THE", "WATERFALL"]}   # the book man with Book 2 (q4_book_man)
Q4_DESTINY_QUOTE = 38                  # a new quote id (the bank has 0-37): only its 4Q text exists
Q4_QUOTE_TEXTS[Q4_DESTINY_QUOTE] = ["ZELDA'S NOT HERE!", "JUST RESET AND FULFILL", "YOUR DESTINY"]
if TEST_2Q_WOOD_CAVE:
    Q4_QUOTE_TEXTS[29] = ["CHOOSE YOUR DESTINY"]                     # 4Q's wood sword cave (test); 3Q: G16's old man
# (7: A10; 19: A1; 35: L9 G5's old man; 30: E16's old man (Book 2); 31: L3 G7 (q4_poison))


Q3_G16 = 0x6F                          # 3Q: G16's cave (the lost hills hint cave, 5) ...
Q3_G16_CAVE = 5
Q3_G16_TEXTS = (["YOU HAVEN'T FOUND", "THAT ACCURSED", "MAGICAL SWORD YET?"],   # quote 22: no magical sword
                ["I SUGGEST YOU BUY A", "MAGICAL SHIELD!"])                     # quote 29: with it


def q3_g16_hint(rom: bytearray, notes: list[str]) -> None:
    """3Q's G16 old man: the cave's selector read (LDA OverworldPersonTextSelectors,Y; after q4_caves, in its
    vanilla tail) becomes JSR helper: on G16 in the hint cave, quote 22, or 29 with the magical sword ($0657 = 3);
    else the vanilla selector. (4Q's G16 is a take-any, cave 1.)"""
    bank1 = 16 + 1 * 0x4000
    sel_file = rom.index(bytes([0x40, 0x60, 0x42, 0x42, 0x04, 0x06, 0x48, 0x0A]))
    sel_cpu = 0x8000 + sel_file - bank1
    pat = bytes([0xB9, sel_cpu & 0xFF, sel_cpu >> 8])
    sites = [i for i in range(bank1, bank1 + 0x4000) if rom[i:i + 3] == pat]
    assert len(sites) == 1, sites
    flags = rom[sel_file + Q3_G16_CAVE] & 0xC0
    code = bytearray([0xA5, 0xEB, 0xC9, Q3_G16, 0xD0, 0x0F,         # LDA room / CMP #G16 / BNE v
                      0xC0, Q3_G16_CAVE, 0xD0, 0x0B,                # CPY #cave / BNE v
                      0xAD, 0x57, 0x06, 0xC9, 0x03, 0xB0, 0x03,     # LDA sword / CMP #3 / BCS has
                      0xA9, flags | 22 * 2, 0x60,                   # LDA #quote 22 / RTS
                      0xA9, flags | 29 * 2, 0x60])                  # has: LDA #quote 29 / RTS
    code[5], code[9] = len(code) - 6, len(code) - 10                # -> v
    code += pat + bytes([0x60])                                     # v: LDA selectors,Y / RTS
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank1
    rom[at:at + len(code)] = code
    rom[sites[0]:sites[0] + 3] = bytes([0x20, cpu & 0xFF, cpu >> 8])
    # the texts: the quote bank is full, so they go in bank 1's free space and quotes 22 and 29 point there
    from zora.rom.serialize.text import _encode_quote
    for qid, lines in zip((22, 29), Q3_G16_TEXTS):
        text = bytes(_encode_quote(base.centered(lines)))
        t_at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(text) + 16) + 8
        t_cpu = 0x8000 + t_at - bank1
        rom[t_at:t_at + len(text)] = text
        rom[0x4010 + 2 * qid:0x4010 + 2 * qid + 2] = bytes([t_cpu & 0xFF, t_cpu >> 8])
    notes.append(f"3Q G16 hint (helper ${cpu:04X})")


def q4_quote_texts(rom: bytearray, notes: list[str]) -> None:
    from zora.rom.serialize.text import _encode_quote
    bank1 = 16 + 1 * 0x4000
    old = bytes.fromhex("ac1504b900808500c8b900808501")
    assert rom.count(old) == 1
    site = rom.index(old)
    ids = list(Q4_QUOTE_TEXTS)
    texts = [bytes(_encode_quote(base.centered(Q4_QUOTE_TEXTS[i]))) for i in ids]
    n = len(ids)
    code_len = 50
    size = code_len + 3 * n + sum(len(t) for t in texts)
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, size + 16) + 8
    cpu = 0x8000 + at - bank1
    t_ids, t_lo = cpu + code_len, cpu + code_len + n
    t_hi = t_lo + n
    code = bytearray([0xAC, 0x15, 0x04, 0xB9, 0x00, 0x80, 0x85, 0x00, 0xB9, 0x01, 0x80, 0x85, 0x01,   # vanilla pointer
                      0x8A, 0x48,                                   # TXA / PHA
                      0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x00,     # LDY slot / LDA quest,Y / BEQ done
                      0xAD, 0x15, 0x04, 0xA2, n - 1,                # LDA $0415 / LDX #n-1
                      0xDD, t_ids & 0xFF, t_ids >> 8, 0xF0, 0x05,   # loop: CMP ids,X / BEQ hit
                      0xCA, 0x10, 0xF8, 0x30, 0x00,                 # DEX / BPL loop / BMI done
                      0xBD, t_lo & 0xFF, t_lo >> 8, 0x85, 0x00,     # hit: LDA lo,X / STA $00
                      0xBD, t_hi & 0xFF, t_hi >> 8, 0x85, 0x01])    # LDA hi,X / STA $01
    done = len(code)
    code += bytes([0x68, 0xAA, 0x60])                              # done: PLA / TAX / RTS
    code[21] = done - 22
    code[36] = done - 37
    assert len(code) == code_len, len(code)
    text_at = t_hi + n
    lo, hi, blob = [], [], bytearray()
    for t in texts:
        a = text_at + len(blob); lo.append(a & 0xFF); hi.append(a >> 8); blob += t
    rom[at:at + size] = code + bytes(i * 2 for i in ids) + bytes(lo) + bytes(hi) + blob
    rom[site:site + len(old)] = bytes([0x20, cpu & 0xFF, cpu >> 8, 0xAC, 0x15, 0x04, 0xC8]) + b"\xEA" * (len(old) - 7)
    notes.append(f"4Q quote texts (helper ${cpu:04X}): " + ", ".join(str(i) for i in ids))


Q4_BOOK_MAN = None                     # (9, "room"): Level 9's ELDER_3 there says quote 23 instead of 36 with Book 2
Q4_BOOK_MAN_QUOTE = 23
if os.environ.get("ZQ4_BOOKMAN_TEST"):
    Q4_BOOK_MAN = (9, os.environ["ZQ4_BOOKMAN_TEST"])
    Q4_ROOMS[Q4_BOOK_MAN] = (R.BLACK_ROOM, E.ELDER_3, 3, Item.NOTHING, False)   # (a test placement)


def q4_book_man(rom: bytearray, notes: list[str]) -> None:
    """Level 9's entry in InitUnderworldPerson's jump table ($8A07 + 2*9) goes to a helper: the vanilla init,
    then in quest 1, in the book man's room, with Book 2 ($0661 = 2), the other quote."""
    if Q4_BOOK_MAN is None:
        return
    lv, name = Q4_BOOK_MAN
    bank1 = 16 + 1 * 0x4000
    entry = 0x4A17 + 2 * lv
    van = rom[entry] | rom[entry + 1] << 8
    code = bytearray([0x20, van & 0xFF, van >> 8,                 # JSR vanilla
                      0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x00,   # LDY slot / LDA quest,Y / BEQ done
                      0xA5, 0xEB, 0xC9, cell(name), 0xD0, 0x00,   # LDA room / CMP / BNE done
                      0xAD, 0x61, 0x06, 0xC9, 0x02, 0xD0, 0x00,   # LDA Book / CMP #2 / BNE done
                      0xA9, Q4_BOOK_MAN_QUOTE * 2, 0x8D, 0x15, 0x04,   # LDA #quote / STA $0415
                      0x60])                                      # done: RTS
    for at_ in (9, 15, 22):
        code[at_] = len(code) - 1 - (at_ + 1)
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank1
    rom[at:at + len(code)] = code
    rom[entry:entry + 2] = bytes([cpu & 0xFF, cpu >> 8])
    notes.append(f"4Q L{lv} {name}: the book man (helper ${cpu:04X})")


Q4_DESTINY_ROOM = (9, "A6")            # 4Q: the fake Zelda room north of Ganon
Q4_DESTINY_SCREEN = 0x77               # H8: its cave goes to Level 9's H1 (Zelda) once the destiny bit is set
Q4_DESTINY_BIT = 0x0673                # saved inventory byte unused in vanilla; bit 0 = destiny
Q4_DESTINY_RELOAD_AT = 0xFF42           # bank 7 free: bank 6's level block copy, back to bank 1
Q4_DESTINY_TRAMPOLINE = (0xED94, 0xFAE4)   # free bytes in bank 7: switch to bank 2, save, switch back to 1


def q4_destiny(rom: bytearray, notes: list[str]) -> None:
    """4Q's ending twist. Level 9's person entry (InitUnderworldPerson's table, after q4_book_man) gets a helper:
    the vanilla init, then in quest 1 in the fake Zelda room, quote Q4_DESTINY_QUOTE, the saved inventory
    ($0657-$067E) and every room flag ($067F-$07FE) wiped to a new game's (3 hearts, 8 bombs max), the destiny
    bit set, and the game saved (bank 2's save steps $A6B8 and $A734, through a bank-7 trampoline; $13, $00-$0F
    and $C0-$CF are kept). Bank 5: the overworld's entrance read (LDA $68FE,Y / AND #$FC) on H8 with the bit gives
    Level 9 (q4_second_entrances then starts it in H1); controller 2's Up+A is ignored in the fake room."""
    lv, name = Q4_DESTINY_ROOM
    room = cell(name)
    bank1, bank5, bank7 = 16 + 0x4000, 16 + 5 * 0x4000, 16 + 7 * 0x4000
    db = Q4_DESTINY_BIT
    t1, t2 = Q4_DESTINY_TRAMPOLINE
    tr1 = bytes([0xA9, 0x02, 0x20, 0xAC, 0xFF, 0x20, 0xB8, 0xA6, 0x4C, t2 & 0xFF, t2 >> 8])   # bank 2 / save 1
    tr2 = bytes([0x20, 0x34, 0xA7, 0xA9, 0x01, 0x20, 0xAC, 0xFF, 0x60])                         # save 2 / bank 1
    rl = 0x8047                                                    # bank 6: InitMode2_Sub0 (level block -> WRAM)
    assert rom[16 + 6 * 0x4000 + rl - 0x8000:][:10] == bytes.fromhex("a5100aaaa416b92d06d0")
    tr3 = bytes([0xA9, 0x06, 0x20, 0xAC, 0xFF, 0x20, rl & 0xFF, rl >> 8, 0xA9, 0x01, 0x4C, 0xAC, 0xFF])
    for cpu_, b in ((t1, tr1), (t2, tr2), (Q4_DESTINY_RELOAD_AT, tr3)):
        f = bank7 + cpu_ - 0xC000
        assert set(rom[f - 1:f + len(b) + 1]) <= {0xFF} or set(rom[f:f + len(b)]) <= {0x00, 0xFF}, (hex(cpu_), rom[f - 1:f + len(b) + 1].hex())
        rom[f:f + len(b)] = b
    # the person helper (bank 1)
    entry = 0x4A17 + 2 * lv
    van = rom[entry] | rom[entry + 1] << 8
    c = bytearray([0x20, van & 0xFF, van >> 8,                    # JSR vanilla
                   0x8A, 0x48, 0x98, 0x48,                        # TXA / PHA / TYA / PHA
                   0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x00,      # LDY slot / LDA quest,Y / BEQ done
                   0xA5, 0xEB, 0xC9, room, 0xD0, 0x00,            # LDA room / CMP / BNE done
                   0xA9, Q4_DESTINY_QUOTE * 2, 0x8D, 0x15, 0x04,  # LDA #quote / STA $0415
                   0xA9, 0x00, 0xA2, 0x27,                        # LDA #0 / LDX #$27
                   0x9D, 0x57, 0x06, 0xCA, 0x10, 0xFA,            # STA $0657,X / DEX / BPL
                   0xA2, 0x7F,                                    # LDX #$7F
                   0x9D, 0x7F, 0x06, 0x9D, 0xFF, 0x06, 0x9D, 0x7F, 0x07, 0xCA, 0x10, 0xF4,   # three pages of flags
                   0xA9, 0x22, 0x8D, 0x6F, 0x06,                  # 3 hearts
                   0xA9, 0x08, 0x8D, 0x7C, 0x06,                  # 8 bombs max
                   0xA9, 0x01, 0x8D, db & 0xFF, db >> 8,          # destiny
                   0xA2, 0x0F,                                    # LDX #15
                   0xB5, 0x00, 0x48, 0xB5, 0xC0, 0x48, 0xCA, 0x10, 0xF7,   # push $00,X / $C0,X
                   0xA5, 0x13, 0x48,                              # LDA $13 / PHA
                   0xA5, 0xFF, 0x29, 0x7F, 0x8D, 0x00, 0x20,      # NMI off (the save outlasts a frame)
                   0x20, t1 & 0xFF, t1 >> 8,                      # JSR trampoline (save)
                   0x20, Q4_DESTINY_RELOAD_AT & 0xFF, Q4_DESTINY_RELOAD_AT >> 8,   # the level block again (the
                                                                  # save's working copy used its WRAM, $6880-$6A8F)
                   0xAD, 0x02, 0x20, 0xA5, 0xFF, 0x8D, 0x00, 0x20,   # clear vblank / NMI back on
                   0x68, 0x85, 0x13,                              # PLA / STA $13
                   0xA2, 0x00,                                    # LDX #0
                   0x68, 0x95, 0xC0, 0x68, 0x95, 0x00, 0xE8, 0xE0, 0x10, 0xD0, 0xF5])   # pop back
    done = len(c)
    c += bytes([0x68, 0xA8, 0x68, 0xAA, 0x60])                   # done: PLA / TAY / PLA / TAX / RTS
    c[13] = done - 14
    c[19] = done - 20
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(c) + 16) + 8
    cpu = 0x8000 + at - bank1
    rom[at:at + len(c)] = c
    rom[entry:entry + 2] = bytes([cpu & 0xFF, cpu >> 8])
    # bank 5: H8's entrance with the destiny bit -> Level 9
    site = bank5 + 0x348B
    assert rom[site:site + 5].hex() == "b9fe6829fc", rom[site:site + 5].hex()
    h = bytes([0xB9, 0xFE, 0x68, 0x29, 0xFC,                     # LDA $68FE,Y / AND #$FC
               0xC0, Q4_DESTINY_SCREEN, 0xD0, 0x0A,              # CPY #screen / BNE r
               0x48, 0xAD, db & 0xFF, db >> 8, 0x4A, 0x68,       # PHA / LDA bit / LSR / PLA
               0x90, 0x02, 0xA9, 9 << 2,                         # BCC r / LDA #level 9
               0x60])                                            # r: RTS
    at5 = base.free_run(rom, bank5 + 0x3000, bank5 + 0x3F00, len(h) + 16) + 8
    rom[at5:at5 + len(h)] = h
    h_cpu = 0x8000 + at5 - bank5
    rom[site:site + 5] = bytes([0x20, h_cpu & 0xFF, h_cpu >> 8, 0xEA, 0xEA])
    # bank 5: no Up+A (controller 2) in the fake room
    site2 = bank5 + 0x00DA
    assert rom[site2:site2 + 4].hex() == "a5fb2988", rom[site2:site2 + 4].hex()
    u = bytearray([0xA5, 0xFB, 0x29, 0x88, 0xC9, 0x88, 0xD0, 0x00,   # LDA $FB / AND #$88 / CMP #$88 / BNE out
                   0xA5, 0x10, 0xC9, lv, 0xD0, 0x00,              # LDA level / CMP / BNE yes
                   0xA5, 0xEB, 0xC9, room, 0xD0, 0x00,            # LDA room / CMP / BNE yes
                   0x98, 0x48, 0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x05,   # TYA / PHA / LDY slot / LDA quest,Y / BEQ q
                   0x68, 0xA8, 0xA9, 0x00, 0x60,                  # PLA / TAY / LDA #0 / RTS
                   0x68, 0xA8])                                   # q: PLA / TAY
    yes = len(u)
    u += bytes([0xA9, 0x88])                                      # yes: LDA #$88
    out = len(u)
    u += bytes([0x60])                                            # out: RTS
    u[7] = out - 8
    u[13] = yes - 14
    u[19] = yes - 20
    at5b = base.free_run(rom, bank5 + 0x3000, bank5 + 0x3F00, len(u) + 16) + 8
    rom[at5b:at5b + len(u)] = u
    u_cpu = 0x8000 + at5b - bank5
    rom[site2:site2 + 4] = bytes([0x20, u_cpu & 0xFF, u_cpu >> 8, 0xEA])
    notes.append(f"4Q destiny: L{lv} {name} wipes and saves (helper ${cpu:04X}); H8 -> L9 H1 with ${db:04X} bit 0 "
                 f"(${h_cpu:04X}); no Up+A there (${u_cpu:04X})")


Q4_POISON_ROOM = (3, "G7")          # 4Q: an old man with a take-any choice of the two boomerangs
Q4_POISON_WARES = (0x1D, 0x3F, 0x40 | 0x1E)   # boomerang, nothing, magical boomerang (+ 'show items')
Q4_POISON_QUOTE = 31


def q4_poison(rom: bytearray, notes: list[str]) -> None:
    """4Q Level 3's G7 old man: the level's entry in InitUnderworldPerson's jump table (bank 1 $8A07, entry
    = level) goes to a helper that, in quest 1 in that room, makes the person the take-any cave dweller ($6B, cave
    1: remembers its taking through the room's item bit, as $7314/$730C read and set it), swaps the two boomerangs
    (no prices) into the RAM wares InitCave reads for cave 1, calls InitCave ($85D0), puts back the bytes (the level
    block's attribute E), and sets the quote. Else the vanilla entry."""
    bank1 = 16 + 1 * 0x4000
    lv, name = Q4_POISON_ROOM
    room = "ABCDEFGH".index(name[0]) * 16 + int(name[1:]) - 1
    entry = 0x4A17 + 2 * lv
    van = rom[entry] | rom[entry + 1] << 8
    code = bytearray([0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x00,        # LDY slot / LDA quest,Y / BEQ van
                      0xA5, 0xEB, 0xC9, room, 0xD0, 0x00,              # LDA room / CMP / BNE van
                      0xA9, 0x6B, 0x8D, 0x50, 0x03,                    # LDA #$6B / STA $0350
                      0xA0, 0x00])                                     # LDY #0
    l1 = len(code)
    code += bytes([0xB9, 0x81, 0x6A, 0x48, 0xB9, 0, 0, 0x99, 0x81, 0x6A,   # LDA $6A81,Y / PHA / LDA wares,Y / STA
                   0xB9, 0xBD, 0x6A, 0x48, 0xA9, 0x00, 0x99, 0xBD, 0x6A,   # LDA $6ABD,Y / PHA / LDA #0 / STA
                   0xC8, 0xC0, 0x03, 0xD0, 0x00])                          # INY / CPY #3 / BNE l1
    code[-1] = (l1 - len(code)) & 0xFF
    code += bytes([0x20, 0xD0, 0x85, 0xA0, 0x02])                         # JSR InitCave / LDY #2
    l2 = len(code)
    code += bytes([0x68, 0x99, 0xBD, 0x6A, 0x68, 0x99, 0x81, 0x6A, 0x88, 0x10, 0x00])
    code[-1] = (l2 - len(code)) & 0xFF
    code += bytes([0xAD, 0x50, 0x03, 0xF0, 0x05, 0xA9, Q4_POISON_QUOTE * 2, 0x8D, 0x15, 0x04, 0x60])
    van_at = len(code)
    code += bytes([0x4C, van & 0xFF, van >> 8])
    wares_at = len(code)
    code += bytes(Q4_POISON_WARES)
    code[6] = van_at - 7
    code[12] = van_at - 13
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank1
    w = cpu + wares_at
    code[l1 + 5], code[l1 + 6] = w & 0xFF, w >> 8
    rom[at:at + len(code)] = code
    rom[entry:entry + 2] = bytes([cpu & 0xFF, cpu >> 8])
    notes.append(f"4Q L{lv} {name}: pick your poison (helper ${cpu:04X}, vanilla ${van:04X})")


# 4Q's own overworld items: the item byte of 'LDA #item / STA $AB' -> (bank, item in 4Q)
Q4_OW_ITEMS = {0x10CF5 + 16: (4, Item.HEART_CONTAINER),   # the Armos item (D4; 3Q: the Book)
               0x1788A + 16: (5, Item.RAFT)}              # the coast (F16; 3Q: the magical sword)


def q4_overworld_items(rom: bytearray, notes: list[str]) -> None:
    """LDA #item / STA $AB becomes JSR helper / NOP: in quest 1 the helper stores the 4Q item, else the 3Q one;
    Y is kept and A / the flags end as LDA #item left them."""
    for addr, (bank, item4) in Q4_OW_ITEMS.items():
        assert rom[addr - 1] == 0xA9 and rom[addr + 1:addr + 3] == bytes([0x85, 0xAB]), hex(addr)
        item3 = rom[addr]
        b = 16 + bank * 0x4000
        code = bytes([0x98, 0x48, 0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x04,   # TYA/PHA/LDY slot/LDA quest,Y/BEQ q3
                      0xA9, int(item4), 0xD0, 0x02,                          # LDA #item4 / BNE store
                      0xA9, item3,                                           # q3: LDA #item3
                      0x85, 0xAB, 0x68, 0xA8, 0xA5, 0xAB, 0x60])             # STA $AB / PLA / TAY / LDA $AB / RTS
        at = base.free_run(rom, b + 0x3000, b + 0x3F00, len(code) + 16) + 8
        cpu = 0x8000 + at - b
        rom[at:at + len(code)] = code
        rom[addr - 1:addr + 3] = bytes([0x20, cpu & 0xFF, cpu >> 8, 0xEA])
        notes.append(f"4Q overworld item at ${addr:05X}: ${item3:02X} -> ${int(item4):02X} (helper ${cpu:04X})")


def q4_sprite_sets(rom: bytearray, notes: list[str]) -> None:
    """The enemy and boss sprite sets are one table each by level number (bank 3 $8000 / $8014), so both quests
    share them. The two routines that read them (LDA CurLevel / ASL / TAX / LDA $80xx,X / STA $00 / INX /
    LDA $80xx,X / STA $01 / RTS) become JMPs to bank-3 helpers that read 4Q copies in quest 1 (Q4_ENEMY_SET_FROM,
    Q4_BOSS_SETS)."""
    from zora.rom.serialize.levels import _BOSS_SET_CPU_ADDRS
    b3 = 16 + 3 * 0x4000
    enemy3, boss3 = bytearray(rom[b3:b3 + 20]), bytearray(rom[b3 + 20:b3 + 40])
    enemy4, boss4 = bytearray(enemy3), bytearray(boss3)
    for lv, src in Q4_ENEMY_SET_FROM.items():
        enemy4[2 * lv:2 * lv + 2] = enemy3[2 * src:2 * src + 2]
    for lv, bset in Q4_BOSS_SETS.items():
        a = _BOSS_SET_CPU_ADDRS[bset]; boss4[2 * lv:2 * lv + 2] = bytes([a & 0xFF, a >> 8])
    for table, t4 in ((0x8000, enemy4), (0x8014, boss4)):
        old = bytes([0xA5, 0x10, 0x0A, 0xAA, 0xBD, table & 0xFF, table >> 8, 0x85, 0x00, 0xE8,
                     0xBD, table & 0xFF, table >> 8, 0x85, 0x01, 0x60])
        site = rom.index(old, b3, b3 + 0x4000)
        size = 36 + 20
        at = base.free_run(rom, b3 + 0x2C00, b3 + 0x3F00, size + 16) + 8
        cpu = 0x8000 + at - b3
        t = 0
        code = bytes([0xA5, 0x10, 0x0A, 0xAA, 0x98, 0x48,          # LDA level / ASL / TAX / TYA / PHA
                      0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x0C,    # LDY slot / LDA quest,Y / BEQ q3
                      0xBD, t & 0xFF, t >> 8, 0x85, 0x00,          # LDA t4,X / STA $00
                      0xBD, (t + 1) & 0xFF, (t + 1) >> 8, 0x85, 0x01, 0xD0, 0x0A,   # LDA t4+1,X / STA $01 / BNE done
                      0xBD, table & 0xFF, table >> 8, 0x85, 0x00,  # q3: LDA table,X / STA $00
                      0xBD, (table + 1) & 0xFF, (table + 1) >> 8, 0x85, 0x01])      # LDA table+1,X / STA $01
        code += bytes([0x68, 0xA8, 0xE8, 0x60])                    # done: PLA / TAY / INX / RTS
        n = len(code)
        assert n == 39, n
        t = cpu + n                                                # the 4Q table right after the code
        code = bytearray(code); code[14:16] = bytes([t & 0xFF, t >> 8]); code[19:21] = bytes([(t + 1) & 0xFF, (t + 1) >> 8])
        rom[at:at + n] = code; rom[at + n:at + n + 20] = t4
        rom[site:site + 3] = bytes([0x4C, cpu & 0xFF, cpu >> 8])
        notes.append(f"4Q sprite set table ${table:04X}: helper ${cpu:04X}, 4Q {bytes(t4).hex()}")


def q4_bomb_cost(rom: bytearray, notes: list[str]) -> None:
    """The bomb upgrade's price: bank 1 LDA #cost / CMP Rupees (the check, and later the charge) and its display
    (LDA #$6C / STA $14: the transfer string at bank 6 $A29E, "-100"). In quest 1 a helper loads Q4_BOMB_COST, and
    the display helper copies a "-50" string into the dynamic buffer ($0302, transfer selector 0)."""
    bank1 = 16 + 1 * 0x4000
    old = bytes([0xA9, None, 0xCD, 0x6D, 0x06]) if False else None
    site = rom.index(bytes.fromhex("cd6d06f002b0f6186d7e06")) - 2
    assert rom[site] == 0xA9, rom[site:site + 5].hex()
    cost3 = rom[site + 1]
    c = Q4_BOMB_COST
    code = bytes([0x98, 0x48, 0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x08,      # TYA/PHA/LDY slot/LDA quest,Y/BEQ q3
                  0x68, 0xA8, 0xA9, c, 0xCD, 0x6D, 0x06, 0x60,               # PLA/TAY/LDA #c4/CMP Rupees/RTS
                  0x68, 0xA8, 0xA9, cost3, 0xCD, 0x6D, 0x06, 0x60])          # q3: same with the 3Q cost
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank1
    rom[at:at + len(code)] = code
    rom[site:site + 5] = bytes([0x20, cpu & 0xFF, cpu >> 8, 0xEA, 0xEA])
    # the display: "22 CD 04 62 h t o FF" (62 = '-', $24 = blank)
    disp = bytes.fromhex("a96c8514")
    assert rom.count(disp) == 1
    dsite = rom.index(disp)
    tiles = [0x24 if c < 100 else c // 100, (c // 10) % 10 if c >= 10 else 0x24, c % 10]
    if c < 100:
        string = bytes([0x22, 0xCD, 0x04, 0x24, 0x62, tiles[1], tiles[2], 0xFF])
    else:
        string = bytes([0x22, 0xCD, 0x04, 0x62, *tiles, 0xFF])
    code2 = bytearray([0x98, 0x48, 0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x00,      # TYA/PHA/LDY/LDA quest,Y/BEQ q3
                       0xA0, 0x07, 0xB9, 0, 0, 0x99, 0x02, 0x03, 0x88, 0x10, 0xF7,   # LDY #7 / copy string -> $0302
                       0xA9, 0x00, 0xD0, 0x02,                                    # LDA #0 (buffer) / BNE-skip... (see below)
                       0xA9, 0x6C,                                                # q3: LDA #$6C
                       0x85, 0x14, 0x68, 0xA8, 0x60])                             # STA $14 / PLA / TAY / RTS
    # BNE after LDA #0 never branches: use JMP-free layout: q4 path ends with LDA #0 then jumps over LDA #$6C
    code2[22:24] = bytes([0xF0, 0x02])                                            # BEQ (A = 0): skip LDA #$6C
    code2[8] = 24 - 9                                                             # BEQ q3 -> LDA #$6C
    at2 = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(code2) + len(string) + 16) + 8
    cpu2 = 0x8000 + at2 - bank1
    s_cpu = cpu2 + len(code2)
    code2[12:14] = bytes([s_cpu & 0xFF, s_cpu >> 8])
    rom[at2:at2 + len(code2)] = code2
    rom[at2 + len(code2):at2 + len(code2) + len(string)] = string
    rom[dsite:dsite + 4] = bytes([0x20, cpu2 & 0xFF, cpu2 >> 8, 0xEA])
    notes.append(f"4Q bomb upgrade: {c} rupees (helpers ${cpu:04X}, ${cpu2:04X})")


def book2(rom: bytearray, notes: list[str]) -> None:
    """Book 2 (4Q, E16's cave): the Book slot ($0661) at 2.
    - The Book's descriptor becomes graded ($21: keep the higher), so the first Book never takes Book 2 away.
    - TakeItem's bank-1 caller (JSR $7370) becomes JSR to a helper: after TakeItem, in quest 1 on overworld screen
      E16, the Book slot is set to 2.
    - DrawItemBySlot (bank 7): LDA ItemSlotToPalette,X becomes JSR to a helper in bank 7's free $DFF0: the Book's
      slot at 2 draws in the blue row (1); else the table's row."""
    desc = 0x6B48 + int(Item.BOOK)
    assert rom[desc] == 0x01, hex(rom[desc])
    rom[desc] = 0x21
    bank1 = 16 + 1 * 0x4000
    call = bytes([0x20, 0x70, 0x73])
    sites = [i for i in range(bank1, bank1 + 0x4000) if rom[i:i + 3] == call]
    assert len(sites) == 1, [hex(i) for i in sites]
    code = bytes([0x20, 0x70, 0x73,                              # JSR TakeItem
                  0x08, 0x48, 0x98, 0x48,                        # PHP / PHA / TYA / PHA
                  0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x0F,      # LDY slot / LDA quest,Y / BEQ out
                  0xA5, 0x10, 0xD0, 0x0B,                        # LDA level / BNE out
                  0xA5, 0xEB, 0xC9, Q4_E16, 0xD0, 0x05,          # LDA room / CMP #E16 / BNE out
                  0xA9, 0x02, 0x8D, 0x61, 0x06,                  # LDA #2 / STA Book
                  0x68, 0xA8, 0x68, 0x28, 0x60])                 # out: PLA / TAY / PLA / PLP / RTS
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank1
    rom[at:at + len(code)] = code
    rom[sites[0]:sites[0] + 3] = bytes([0x20, cpu & 0xFF, cpu >> 8])
    # the inventory's color
    draw = bytes.fromhex("bd57068504bdec72")
    assert rom.count(draw) == 1
    d = rom.index(draw) + 5
    helper = 0x1C010 + 0x1FF0                                    # bank 7 $DFF0, 17 free bytes
    assert rom[helper:helper + 17] == b"\xFF" * 17
    h = bytes([0xE0, 0x0A, 0xD0, 0x09,                           # CPX #Book slot / BNE table
               0xA5, 0x04, 0xC9, 0x02, 0xD0, 0x03,               # LDA value / CMP #2 / BNE table
               0xA9, 0x01, 0x60,                                 # LDA #1 (blue) / RTS
               0xBD, 0xEC, 0x72, 0x60])                          # table: LDA ItemSlotToPalette,X / RTS
    assert len(h) == 17
    rom[helper:helper + 17] = h
    rom[d:d + 3] = bytes([0x20, 0xF0, 0xDF])
    notes.append(f"Book 2: take helper ${cpu:04X} (call at {sites[0]:#x}), inventory color helper $DFF0")


def e16_no_drain(rom: bytearray, notes: list[str]) -> None:
    """The recorder's pond object dries the water step by step ($051A counts up; step 10 makes the water walkable,
    step 11 reveals the stairs, 12 is done). Its LDY $051A / CPY #$0C (then BCS done) becomes JSR to a bank-4 helper
    (objects update with bank 4 in): on E16 the step jumps to 11, so the stairs come up at once and the sea stays."""
    site_pat = bytes.fromhex("ac1a05c00cb02d")
    assert rom.count(site_pat) == 1
    site = rom.index(site_pat)
    bank4 = 16 + 4 * 0x4000
    code = bytes([0xA5, 0xEB, 0xC9, Q4_E16, 0xD0, 0x0C,          # LDA room / CMP #E16 / BNE n
                  0xAD, 0x1A, 0x05, 0xC9, 0x0B, 0xB0, 0x05,      # LDA step / CMP #11 / BCS n
                  0xA9, 0x0B, 0x8D, 0x1A, 0x05,                  # LDA #11 / STA step
                  0xAC, 0x1A, 0x05, 0xC0, 0x0C, 0x60])           # n: LDY step / CPY #12 / RTS
    at = base.free_run(rom, bank4 + 0x3000, bank4 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank4
    rom[at:at + len(code)] = code
    rom[site:site + 5] = bytes([0x20, cpu & 0xFF, cpu >> 8, 0xEA, 0xEA])
    notes.append(f"E16: the recorder's stairs without the drying (helper ${cpu:04X})")


RECORDER_QUESTS = [3, 3, 3, 2, 2, 2, 2, 2, 2, 2] + [0] * 1   # quests each recorder list entry works in: 1 3Q, 2 4Q, 3 both
                                                # (E3, C12: both (4Q: potion shop, door repair); C3: both (4Q's Level 5); B11, G2, A7, B1, F9, D1: 4Q)


def recorder_by_quest(rom: bytearray, notes: list[str]) -> None:
    """The recorder reveals an entry's secret only in that entry's quests, else it calls the whirlwind. In the
    fixed bank's recorder code, the 12 bytes after the room search (vanilla's entry-0 special case and the quest
    test, which ZORA's flag left as 'first quest only') become PLA / CLC / ADC #1 / AND RecorderQuests,Y /
    BEQ whirlwind and NOPs: each entry's value is a mask, bit 0 3Q, bit 1 4Q. The table is in bank 5, which this
    code has in (it switches back to bank 5 when done)."""
    old = bytes.fromhex("c000d00568d01bf00368d016")
    assert rom.count(old) == 1
    site = rom.index(old)
    bank5 = 16 + 5 * 0x4000
    at = base.free_run(rom, bank5 + 0x3000, bank5 + 0x3F00, len(RECORDER_QUESTS) + 16) + 8
    cpu = 0x8000 + at - bank5
    rom[at:at + len(RECORDER_QUESTS)] = bytes(RECORDER_QUESTS)
    whirl = 12 + 0x16                                   # SummonWhirlwind, from the start of the 12 bytes
    new = bytes([0x68, 0x18, 0x69, 0x01, 0x39, cpu & 0xFF, cpu >> 8, 0xF0, whirl - 9]) + b"\xEA" * 3
    rom[site:site + 12] = new
    notes.append(f"recorder by quest: table ${cpu:04X} {RECORDER_QUESTS[:4]}")


def q4_waterfall(rom: bytearray, notes: list[str]) -> None:
    """4Q: B11's waterfall is solid. After LayoutRoomOrCaveOW (bank 5; its one caller JMPs to it) a wrapper turns
    the waterfall's doorway square (tiles $89 $88 / $8B $88 at square column 6, row 4) into plain waterfall
    ($8A, $8C below: unwalkable) in the play area map, which is both what's drawn and what collisions read.
    The recorder (4Q entry) reveals stairs at the waterfall's foot instead."""
    bank5 = 16 + 5 * 0x4000
    # LayoutRoomOW (falls into LayoutRoomOrCaveOW); its one caller: JSR LayoutRoomOW / JMP CheckShortcut
    pat = bytes([0xA9, 0x00, 0x85, 0x06, 0xA6, 0xEB])
    layout = 0x8000 + rom.rindex(pat, bank5, rom.index(bytes([0xAD, 0xAF, 0x6B, 0x85, 0x08]), bank5, bank5 + 0x4000)) - bank5 - 10
    assert rom[bank5 + layout - 0x8000:bank5 + layout - 0x8000 + 3] == bytes([0xAD, 0x9C, 0x9F]), hex(layout)
    jmp = rom.index(bytes([0x20, layout & 0xFF, layout >> 8, 0x4C]), bank5, bank5 + 0x4000)
    tiles = 0x6530
    left, right = tiles + 12 * 22 + 9, tiles + 13 * 22 + 9
    # once the recorder has opened it (B11's secret flag), the doorway square is the stairs instead, so Link
    # coming back out of the Torch stands on them
    code = bytearray([0x20, layout & 0xFF, layout >> 8,     # JSR LayoutRoomOW
                      0xA5, 0x10, 0xD0, 0x00,               # overworld only           (BNE ret)
                      0xA4, 0x16, 0xB9, 0x2D, 0x06, 0xF0, 0x00,   # quest 2 (4Q) only  (BEQ ret)
                      0xA5, 0xEB, 0xC9, 0x1A, 0xD0, 0x00,   # B11 only                 (BNE ret)
                      0xAD, 0x99, 0x06, 0x30, 0x00,         # LDA $067F+$1A / BMI stairs
                      0xA9, 0x8A, 0x8D, left & 0xFF, left >> 8,
                      0xA9, 0x8C, 0x8D, right & 0xFF, right >> 8,
                      0x60,
                      # stairs: tiles $70 $71 / $72 $73 over the whole square (rows 8 and 9)
                      0xA9, 0x70, 0x8D, (left - 1) & 0xFF, (left - 1) >> 8,
                      0xA9, 0x71, 0x8D, left & 0xFF, left >> 8,
                      0xA9, 0x72, 0x8D, (right - 1) & 0xFF, (right - 1) >> 8,
                      0xA9, 0x73, 0x8D, right & 0xFF, right >> 8,
                      0x60])
    ret = 35                                                # the first RTS
    stairs = 36
    for at_, target in ((6, ret), (13, ret), (19, ret), (24, stairs)):
        code[at_] = target - (at_ + 1)
    assert code[ret] == 0x60 and code[stairs] == 0xA9
    code = bytes(code)
    at = base.free_run(rom, bank5 + 0x3000, bank5 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank5
    rom[at:at + len(code)] = code
    rom[jmp + 1:jmp + 3] = bytes([cpu & 0xFF, cpu >> 8])
    global Q4_LAYOUT_CALL
    Q4_LAYOUT_CALL = jmp
    notes.append(f"4Q B11 waterfall solid: wrapper ${cpu:04X}")


Q4_LAYOUT_CALL = None
# 4Q recorder screens whose stairs are drawn by code once found: screen -> stairs square (column, row)
Q4_KEPT_STAIRS = {Q4_A7: (6, 5), Q4_B1: Q4_B1_ROCK, Q4_F9: (6, 5), Q4_D1: (6, 5), Q4_E16: Q4_E16_PIER}
Q4_B1_WALL = ((9, 1), (8, 1))    # B1's bomb wall square, and a plain wall square to copy over it


def q4_recorder_stairs_stay(rom: bytearray, notes: list[str]) -> None:
    """In 4Q, A7's and B1's recorder stairs are an object the game makes when the recorder plays; nothing redraws
    them when Link comes back. After LayoutRoomOW (chained after the B11 waterfall wrapper) a bank-5 routine
    writes the stairs tiles ($70 $71 / $72 $73) into the play area map ($6530, 22 tiles a column) when the screen's
    secret is found. Found also opens B1's bomb wall (a found rock wall square draws as a cave), which 4Q doesn't
    have: its four tiles are copied from the plain wall square beside it."""
    assert Q4_LAYOUT_CALL is not None
    site = Q4_LAYOUT_CALL
    prev = rom[site + 1] | rom[site + 2] << 8
    tiles = 0x6530
    sq = lambda c, r: tiles + (2 * c) * 22 + 2 * r
    screens = list(Q4_KEPT_STAIRS)
    n = len(screens)
    (wc, wr), (pc, pr) = Q4_B1_WALL
    code = bytearray()
    lab, fix = {}, []
    def br(op, name): fix.append((len(code) + 1, name, "rel")); code.extend([op, 0])
    def tab(op, name): fix.append((len(code) + 1, name, "abs")); code.extend([op, 0, 0])
    code += bytes([0x20, prev & 0xFF, prev >> 8])           # JSR (waterfall wrapper -> LayoutRoomOW)
    code += bytes([0xA5, 0x10]); br(0xD0, "ret")            # overworld only
    code += bytes([0xA4, 0x16, 0xB9, 0x2D, 0x06]); br(0xF0, "ret")   # 4Q only
    code += bytes([0x8A, 0x48])                             # TXA / PHA
    code += bytes([0xA2, n - 1])
    lab["loop"] = len(code)
    code += bytes([0xA5, 0xEB]); tab(0xDD, "scr"); br(0xD0, "next")
    code += bytes([0xA4, 0xEB, 0xB9, 0x7F, 0x06]); br(0x10, "next")   # secret found (bit 7)?
    tab(0xBD, "lo"); code += bytes([0x85, 0x00]); tab(0xBD, "hi"); code += bytes([0x85, 0x01])
    for y, t in ((0, 0x70), (1, 0x71), (22, 0x72), (23, 0x73)):
        code += bytes([0xA0, y, 0xA9, t, 0x91, 0x00])
    code += bytes([0xA5, 0xEB, 0xC9, Q4_B1]); br(0xD0, "next")
    for dc in (0, 1):
        for dr in (0, 1):
            src = tiles + (2 * pc + dc) * 22 + 2 * pr + dr
            dst = tiles + (2 * wc + dc) * 22 + 2 * wr + dr
            code += bytes([0xAD, src & 0xFF, src >> 8, 0x8D, dst & 0xFF, dst >> 8])
    lab["next"] = len(code)
    code += bytes([0xCA]); br(0x10, "loop")
    code += bytes([0x68, 0xAA])                             # PLA / TAX
    lab["ret"] = len(code)
    code += bytes([0x60])
    lab["scr"] = len(code); code += bytes(screens)
    lab["lo"] = len(code); code += bytes(sq(*Q4_KEPT_STAIRS[s_]) & 0xFF for s_ in screens)
    lab["hi"] = len(code); code += bytes(sq(*Q4_KEPT_STAIRS[s_]) >> 8 for s_ in screens)
    bank5 = 16 + 5 * 0x4000
    at = base.free_run(rom, bank5 + 0x3000, bank5 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank5
    for off, name, kind in fix:
        if kind == "rel":
            d = lab[name] - (off + 1); assert -128 <= d < 128, name; code[off] = d & 0xFF
        else:
            a = cpu + lab[name]; code[off:off + 2] = bytes([a & 0xFF, a >> 8])
    rom[at:at + len(code)] = code
    rom[site + 1:site + 3] = bytes([cpu & 0xFF, cpu >> 8])
    notes.append(f"4Q recorder stairs kept on " + ", ".join(f"${x:02X}" for x in screens) + f" (wrapper ${cpu:04X})")


# Where the recorder's stairs come up, per screen (pixels, top-left of the square); others: vanilla (96, 144).
RECORDER_STAIRS = {0x1A: (96, 128), 0x61: (7 * 16, 64 + 3 * 16), Q4_B1: (Q4_B1_ROCK[0] * 16, 64 + Q4_B1_ROCK[1] * 16),
                   Q4_E16: (Q4_E16_PIER[0] * 16, 64 + Q4_E16_PIER[1] * 16)}   # + G2 (4Q): the bush above the path      # B11 (4Q): in the waterfall's doorway, where its entrance normally is


def hungry_goriya_mirrored(rom: bytearray, notes: list[str]) -> None:
    """The hungry Goriya wears the Zol (a mirrored sprite: left half drawn twice, flipped): UpdateGrumble's
    JSR $77DF (draw not mirrored, right half = tile + 2) becomes JSR $77DB (the mirrored entry, LDY #1)."""
    site = 0x4C7C                                       # bank 1 $8C6C
    assert rom[site:site + 3] == bytes([0x20, 0xDF, 0x77]), rom[site:site + 3].hex()
    assert rom[0x77DB - 0x780:0x77DB - 0x780 + 4] == bytes([0xA0, 0x01, 0xD0, 0x02])
    rom[site + 1] = 0xDB
    notes.append("hungry Goriya drawn mirrored: $8C6C JSR $77DB")


NO_CLIP_SCREENS = [0x27, 0x17, 0x51, 0x60]     # C8, B8, F2, G1 (both quests): ZORA's B84 "prevent clipping" there only
# Vanilla's two step routines (bank 1, run from WRAM $6FC1/$6FE8) rewritten so the subtracting one starts at $6FE6
# like B84's: same behavior, 60 bytes from $6FCF (the part B84 replaces), so either version can be copied in.
VANILLA_EQ_STEPS = bytes.fromhex(
    "cd0e01f005cd0f01d003281808280869009d94032860ea"          # $6FCF: add tail (A = grid offset from $6FCC)
    "bda80338fdbc039da80308bd9403cd0e01f005cd0f01d003283808"  # $6FE6: subtract
    "2808e9009d94032860ea")


def no_clip_screens(rom: bytearray, notes: list[str]) -> None:
    """ZORA's Prevent Clipping (B84, FP-CLIP-01) on NO_CLIP_SCREENS only.
    1. B84's MoveObject (bank 7) always: with vanilla's step routines it moves exactly as vanilla (4 steps a frame).
    2. The step routines live in WRAM: the ROM keeps a vanilla-equivalent copy (entries $6FC1/$6FE6); when Link
       leaves an overworld screen (after CheckMazes) a bank-5 routine copies B84's or the vanilla one in, by NextRoomId.
    3. The room-to-room walk's end test (bank 7 $EBC4, run with bank 2 mapped) calls a bank-2 helper: B84's wider
       test when B84's steps are in WRAM ($6FCF holds $69), vanilla's otherwise."""
    from zora.rom import small_settings as ss
    writes = dict(ss.prevent_clipping_writes())
    b84_steps, b84_move = writes[0x0684F], writes[0x1F09E]
    assert len(b84_steps) == 60 == len(VANILLA_EQ_STEPS) and b84_steps[0] == 0x69 and VANILLA_EQ_STEPS[0] == 0xCD
    assert rom[0x0684F:0x0684F + 5] == bytes.fromhex("cd0e01f005"), "step routines not vanilla"
    assert rom[0x1F09E:0x1F09E + 5] == bytes.fromhex("08a0f8e000"), "MoveObject not vanilla"
    rom[0x1F09E:0x1F09E + len(b84_move)] = b84_move
    rom[0x0684F:0x0684F + 60] = VANILLA_EQ_STEPS
    # 3. bank-2 helper and the hook at $EBC4 (file 0x1EBD4): JSR helper / BEQ $EBF2 / 8 NOPs
    hook = 0x1EBD4
    assert rom[hook:hook + 13] == bytes.fromhex("ad9403f029c908f025c9f8f021"), rom[hook:hook + 13].hex()
    bank2 = 16 + 2 * 0x4000
    helper = bytes.fromhex("ad9403f00daccf6fc069f007c908f002c9f860c90a9007c9f8b003a90160a90060")
    at = base.free_run(rom, bank2 + 0x3000, bank2 + 0x3F00, len(helper) + 16) + 8
    hcpu = 0x8000 + at - bank2
    rom[at:at + len(helper)] = helper
    rom[hook:hook + 13] = bytes([0x20, hcpu & 0xFF, hcpu >> 8, 0xF0, 0x29]) + b"\xEA" * 8
    # 2. bank-5 swap routine, chained after whatever the overworld's JSR CheckMazes calls now
    maze = rom.index(bytes([0xAE, 0x2F, 0x05, 0xA5, 0x98, 0xA4, 0xEB, 0xC0]))
    site = 0x14000 + 16 + 0x3540                 # bank 5 $B540: JSR CheckMazes (or the loop routine)
    assert rom[site] == 0x20, hex(rom[site])
    prev = rom[site + 1] | rom[site + 2] << 8
    bank5 = 16 + 5 * 0x4000
    n = len(NO_CLIP_SCREENS)
    size = 36 + n + 120
    at5 = base.free_run(rom, bank5 + 0x3000, bank5 + 0x3F00, size + 16) + 8
    cpu5 = 0x8000 + at5 - bank5
    lst, blobs = cpu5 + 36, cpu5 + 36 + n
    code = bytes([0x20, prev & 0xFF, prev >> 8,         # JSR CheckMazes (or the loop routine)
                  0xA5, 0xEC, 0xA0, 0x00, 0xA2, n - 1,  # LDA NextRoomId / LDY #0 / LDX #n-1
                  0xDD, lst & 0xFF, lst >> 8,           # l: CMP list,X
                  0xF0, 0x05, 0xCA, 0x10, 0xF8,         #    BEQ f / DEX / BPL l
                  0x30, 0x02, 0xA0, 0x3C,               #    BMI c / f: LDY #60
                  0xA2, 0x00,                           # c: LDX #0
                  0xB9, blobs & 0xFF, blobs >> 8,       # cl: LDA blobs,Y
                  0x9D, 0xCF, 0x6F, 0xC8, 0xE8,         #    STA $6FCF,X / INY / INX
                  0xE0, 0x3C, 0xD0, 0xF4, 0x60])        #    CPX #60 / BNE cl / RTS
    assert len(code) == 36
    rom[at5:at5 + size] = code + bytes(NO_CLIP_SCREENS) + VANILLA_EQ_STEPS + b84_steps
    rom[site + 1:site + 3] = bytes([cpu5 & 0xFF, cpu5 >> 8])
    notes.append(f"no clipping on {', '.join(f'${r:02X}' for r in NO_CLIP_SCREENS)}: swap ${cpu5:04X} (after ${prev:04X}), "
                 f"end-test helper bank 2 ${hcpu:04X}")


# A test start (ZELDAQ3_SEAN=1): a new file starts with these (Items block, $0657 + index)
SEAN_START = {0x00: 2,      # white sword
              0x01: 8,      # bombs
              0x02: 1,      # wood arrows
              0x03: 1,      # bow
              0x04: 2,      # red candle
              0x05: 1,      # recorder
              0x06: 1,      # bait
              0x08: 1,      # wand
              0x09: 1,      # raft
              0x0A: 1,      # book
              0x0C: 1,      # ladder
              0x0D: 1,      # magic key
              0x0E: 1,      # power bracelet
              0x0F: 1,      # letter
              0x16: 200,    # rupees
              0x18: 0xFF,   # 16 heart containers, all full
              0x19: 0xFF,
              0x1A: 0xFF,   # all 8 triforce pieces
              0x1D: 1,      # boomerang
              0x25: 8}      # bomb capacity


def sean_start(rom: bytearray, notes: list[str]) -> None:
    """New-file init (bank 2 $9F40: LDY #$18 / LDA #$22 / STA ($C0),Y / INY / LDA #$FF / STA ($C0),Y / LDY #$25 /
    LDA #$08 / STA ($C0),Y, after the block is zeroed) becomes JSR to a helper that writes the whole 40-byte
    Items block from SEAN_START."""
    old = bytes.fromhex("a018a92291c0c8a9ff91c0a025a90891c0")
    assert rom.count(old) == 1
    site = rom.index(old)
    b2 = 16 + 2 * 0x4000
    table = bytearray(40)
    for k, v in SEAN_START.items():
        table[k] = v
    at = base.free_run(rom, b2 + 0x3075, b2 + 0x3F00, 11 + 40 + 16) + 8
    cpu = 0x8000 + at - b2
    t = cpu + 11
    code = bytes([0xA0, 0x27, 0xB9, t & 0xFF, t >> 8, 0x91, 0xC0, 0x88, 0x10, 0xF8, 0x60])   # LDY #39 / loop / RTS
    rom[at:at + 11] = code; rom[at + 11:at + 51] = table
    rom[site:site + len(old)] = bytes([0x20, cpu & 0xFF, cpu >> 8]) + b"\xEA" * (len(old) - 3)
    notes.append(f"Sean start: helper ${cpu:04X}")


def beta_3q_only(rom: bytearray, notes: list[str]) -> None:
    """The 3Q-only build: the ZELDA name no longer starts the second quest, and beating the game keeps the file in
    quest 0 (3Q again) instead of moving it to the second quest."""
    name = 0x9EFB                                    # bank 2 $9EEB: "ZELDA" (23 0E 15 0D 0A)
    assert rom[name:name + 5] == bytes([0x23, 0x0E, 0x15, 0x0D, 0x0A])
    rom[name] = 0xFE                                 # no name can hold $FE
    end = 0xAF9A                                     # bank 2 $AF8A: LDA #$01 / STA QuestNumbers,Y
    assert rom[end - 2:end + 5] == bytes([0xA4, 0x16, 0xA9, 0x01, 0x99, 0x2D, 0x06]), rom[end - 2:end + 5].hex()
    rom[end + 1] = 0x00
    notes.append("3Q only: ZELDA name off, the ending keeps quest 0")
    # Title screen: the row under PUSH START BUTTON (PPU $22A0, blank in columns 7-27) gets the version line.
    row = 0x1ABE3                                    # "22 A0 20" + 32 tiles
    assert rom[row:row + 3] == bytes([0x22, 0xA0, 0x20])
    tiles = rom[row + 3:row + 35]
    assert tiles[7:28] == bytes([0x24]) * 21
    text = os.environ.get("ZELDAQ3_TITLE") or f"3RD QUEST BETA V{BETA_VERSION}"
    assert len(text) <= 21, text
    font = {**{str(d): d for d in range(10)}, **{chr(65 + i): 10 + i for i in range(26)}, " ": 0x24, ".": 0x2C}
    enc = bytes(font[c] for c in text)
    start = 7 + (21 - len(enc)) // 2
    rom[row + 3 + start:row + 3 + start + len(enc)] = enc
    notes.append(f"title: '{text}' at PPU ${0x22A0 + start:04X}")


# Level 9's Mugger (E15) has his own text; Level 8's (H8) keeps quote 27 ("LEAVE YOUR LIFE OR MONEY")
MUGGER_9_QUOTE = 37      # vanilla 'Eyes of skull has a secret' (Levels 7-9), unused in 3Q
MUGGER_9_LINES = ["IF YOU WANT TO RESCUE", "ZELDA, YOU HAVE TO GO", "THROUGH ME!"]


def mugger_quote(rom: bytearray, notes: list[str]) -> None:
    """The Mugger's text is fixed (bank 1: LDA #$36 / STA $0415, quote 27). That becomes JSR to a bank-1 helper:
    in Level 9 (CurLevel $10 = 9) it stores MUGGER_9_QUOTE instead."""
    old = bytes.fromhex("a9368d1504")
    assert rom.count(old) == 1
    site = rom.index(old)
    bank1 = 16 + 1 * 0x4000
    code = bytes([0xA5, 0x10, 0xC9, 0x09, 0xF0, 0x04,           # LDA CurLevel / CMP #9 / BEQ l9
                  0xA9, 0x36, 0xD0, 0x02,                       # LDA #quote 27 / BNE store
                  0xA9, MUGGER_9_QUOTE * 2,                     # l9: LDA #quote
                  0x8D, 0x15, 0x04, 0x60])                      # store: STA $0415 / RTS
    at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(code) + 16) + 8
    cpu = 0x8000 + at - bank1
    rom[at:at + len(code)] = code
    rom[site:site + 5] = bytes([0x20, cpu & 0xFF, cpu >> 8, 0xEA, 0xEA])
    # the text: the quote bank is full, so it goes in bank 1's free space and quote 37's pointer points there
    from zora.rom.serialize.text import _encode_quote
    text = bytes(_encode_quote(base.centered(MUGGER_9_LINES)))
    t_at = base.free_run(rom, bank1 + 0x3700, bank1 + 0x3F00, len(text) + 16) + 8
    t_cpu = 0x8000 + t_at - bank1
    rom[t_at:t_at + len(text)] = text
    ptr = 0x4010 + 2 * MUGGER_9_QUOTE
    rom[ptr:ptr + 2] = bytes([t_cpu & 0xFF, t_cpu >> 8])
    notes.append(f"Level 9 Mugger quote {MUGGER_9_QUOTE} (helper ${cpu:04X}, text ${t_cpu:04X})")


CLOSING_LINES = ["LATELY,", "EVERYTHING IS JUST", "A LITTLE BIT OUT OF PHASE"]   # 52 chars max
ENDING_LINES = ["RANDOMIZE MY MIND INTO", "NOTHING. YOU KNOW I", "USED TO KNOW THIS PLACE."]   # the user's, 3 x 24 max


def ending_message(rom: bytearray, notes: list[str]) -> None:
    """Zelda's message after Ganon ("THANKS LINK,YOU'RE THE HERO OF HYRULE.") becomes ENDING_LINES. The routine
    (bank 2 $A998) types from the address in LDA #lo / LDA #hi at $A9B4/$A9B8; a char's $80 bit ends line 1 (next
    at PPU $21C4), $40 ends line 2 ($21E4), $C0 ends the text; $25 is a blank that is skipped. Lines start at
    column 4 and are centred with $25."""
    lda = 0xA9C4                                     # file of $A9B4
    assert rom[lda:lda + 2] == bytes([0xA9, 0x59]) and rom[lda + 4:lda + 6] == bytes([0xA9, 0xA9]), rom[lda:lda + 6].hex()
    font = {**{str(d): d for d in range(10)}, **{chr(65 + i): 10 + i for i in range(26)},
            " ": 0x24, ",": 0x28, "!": 0x29, "'": 0x2A, "&": 0x2B, ".": 0x2C, '"': 0x2D, "?": 0x2E, "-": 0x2F}
    assert len(ENDING_LINES) == 3 and all(len(t) <= 24 for t in ENDING_LINES)
    text = bytearray()
    for k, line in enumerate(ENDING_LINES):
        enc = bytearray([0x25] * ((24 - len(line)) // 2) + [font[c] for c in line])
        enc[-1] |= (0x80, 0x40, 0xC0)[k]
        text += enc
    bank2 = 16 + 2 * 0x4000
    at = base.free_run(rom, bank2 + 0x3000, bank2 + 0x3F00, len(text) + 16) + 8
    cpu = 0x8000 + at - bank2
    rom[at:at + len(text)] = text
    rom[lda + 1], rom[lda + 5] = cpu & 0xFF, cpu >> 8
    notes.append(f"ending message at ${cpu:04X}: " + " / ".join(ENDING_LINES))
    # The closing text after the credits ("FINALLY, / PEACE RETURNS TO HYRULE. / THIS ENDS THE STORY."): bank 2
    # types $AB07,Y (to $FF) at PPU low byte $AAD3,Y (high $22, or $23 below $A0), 52 slots each. Same rows (21, 23,
    # 26), each line centred.
    f = lambda c: c - 0x8000 + 0x8010
    pos_at, txt_at = f(0xAAD3), f(0xAB07)
    assert rom[txt_at:txt_at + 8] == bytes([font[c] for c in "FINALLY,"]) and rom[txt_at + 52] == 0xFF
    text, pos = bytearray(), bytearray()
    for row, line in zip((21, 23, 26), CLOSING_LINES):
        col = (32 - len(line)) // 2
        for k, c in enumerate(line):
            text.append(font[c]); pos.append((0x2000 + row * 32 + col + k) & 0xFF)
    assert len(text) <= 52, len(text)
    rom[pos_at:pos_at + len(pos)] = pos
    rom[txt_at:txt_at + len(text) + 1] = text + b"\xFF"
    notes.append("closing text: " + " / ".join(CLOSING_LINES))


def recorder_stairs_spots(rom: bytearray, notes: list[str]) -> None:
    """RevealPondStairs (fixed bank) sets the stairs at ($60, $90) for every recorder screen. Its LDA #$60 /
    STA ObjX,X / LDA #$90 / STA ObjY,X becomes JSR to a bank-4 helper (objects update with bank 4 in) that looks
    the screen up in RECORDER_STAIRS and falls back to ($60, $90)."""
    pat = bytes([0xA9, 0x60, 0x95, 0x70, 0xA9, 0x90, 0x95, 0x84, 0x4C])
    assert rom.count(pat) == 1
    site = rom.index(pat)
    bank4 = 16 + 4 * 0x4000
    rooms = list(RECORDER_STAIRS)
    n = len(rooms)
    code = bytearray([0xA0, n - 1,                       # LDY #n-1
                      0xA5, 0xEB,                        # loop: LDA RoomId
                      0xD9, 0, 0,                        #   CMP rooms,Y
                      0xF0, 0x0B,                        #   BEQ found
                      0x88, 0x10, 0xF7,                  #   DEY / BPL loop
                      0xA9, 0x60, 0x95, 0x70,            # default: X $60
                      0xA9, 0x90, 0x95, 0x84, 0x60,      #          Y $90, RTS
                      0xB9, 0, 0, 0x95, 0x70,            # found: LDA xs,Y / STA ObjX,X
                      0xB9, 0, 0, 0x95, 0x84,            #        LDA ys,Y / STA ObjY,X
                      0x60])
    assert code[8] == 21 - 9 - 1 or True
    code[8] = 21 - 9                                     # BEQ -> 'found' at index 21
    code[11] = (2 - 12) & 0xFF                           # BPL -> 'loop' at index 2
    size = len(code) + 3 * n
    at = base.free_run(rom, bank4 + 0x3000, bank4 + 0x3F00, size + 16) + 8
    cpu = 0x8000 + at - bank4
    t_rooms, t_x, t_y = cpu + len(code), cpu + len(code) + n, cpu + len(code) + 2 * n
    code[5:7] = bytes([t_rooms & 0xFF, t_rooms >> 8])
    code[22:24] = bytes([t_x & 0xFF, t_x >> 8])
    code[27:29] = bytes([t_y & 0xFF, t_y >> 8])
    data = bytes(code) + bytes(rooms) + bytes(RECORDER_STAIRS[r][0] for r in rooms) + bytes(RECORDER_STAIRS[r][1] for r in rooms)
    rom[at:at + len(data)] = data
    rom[site:site + 8] = bytes([0x20, cpu & 0xFF, cpu >> 8, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA])
    notes.append(f"recorder stairs spots at ${cpu:04X}: " + ", ".join(f"${r:02X} {RECORDER_STAIRS[r]}" for r in rooms))


def candle_rules(rom: bytearray, notes: list[str]) -> None:
    """Blue candle: as many fires per screen as the red one; it burns only brown bushes (inner palette 3)."""
    assert rom[BLUE_CANDLE_LIMIT - 1:BLUE_CANDLE_LIMIT + 1] == bytes([0xC9, 0x01])
    rom[BLUE_CANDLE_LIMIT] = 0x00          # CMP #$00: candle 1 never takes the once-per-screen branch
    assert rom[FIRE_SECRET_CHECK:FIRE_SECRET_CHECK + 3] == bytes([0x20, 0x5A, 0x8F])
    bank4 = 16 + 4 * 0x4000
    off = base.free_run(rom, bank4 + 0x3000, bank4 + 0x3F00, len(FIRE_RULE) + 16) + 8
    rom[off:off + len(FIRE_RULE)] = FIRE_RULE
    fire_rule_addr = 0x8000 + off - bank4
    rom[FIRE_SECRET_CHECK + 1:FIRE_SECRET_CHECK + 3] = fire_rule_addr.to_bytes(2, "little")
    # The Book of Magic no longer turns the wand's beam into fire (it will switch on the chest counter instead)
    assert rom[WAND_BOOK_FIRE:WAND_BOOK_FIRE + 5] == bytes([0xAD, 0x61, 0x06, 0xF0, 0x35])
    rom[WAND_BOOK_FIRE:WAND_BOOK_FIRE + 3] = bytes([0xA9, 0x00, 0xEA])   # LDA #$00, NOP: the BEQ always skips the fire
    notes.append(f"candles: blue candle unlimited, burns only inner-palette-3 screens; none on 4Q G2 (rule at bank 4 ${fire_rule_addr:04X})")



# ---------------------------------------------------------------------------------------------------------------
# Item counter (scratchpad/vanilla_counter's PRG1 counter: chest, found, chest, total under the rupees), shown only
# once Link has the Book of Magic. 3Q's first-quest areas are counted from this build's world.
MAJOR = {Item.WOOD_SWORD, Item.WHITE_SWORD, Item.MAGICAL_SWORD, Item.RECORDER, Item.BLUE_CANDLE, Item.RED_CANDLE,
         Item.SILVER_ARROWS, Item.BOW, Item.MAGICAL_KEY, Item.RAFT, Item.LADDER, Item.WAND, Item.BOOK,
         Item.BLUE_RING, Item.RED_RING, Item.POWER_BRACELET, Item.LETTER, Item.HEART_CONTAINER,
         Item.WOOD_BOOMERANG, Item.MAGICAL_BOOMERANG}


def item_counter_places(world, st) -> dict[int, list[int]]:
    from zora.model.overworld import ItemCave
    places: dict[int, list[int]] = {}
    ow = world.overworld
    cave_items = {c.destination: c.item for c in ow.caves if isinstance(c, ItemCave)}
    screens = [s.screen_num for s in ow.screens if s.quest_visibility != QuestVisibility.SECOND_QUEST
               and cave_items.get(s.destination) in MAJOR]
    screens += [ow.armos_screen_ids[0], 0x5F]          # the Armos item (D4's book) and the coast item
    places[0] = sorted(set(screens))
    for lv in world.levels:
        block = lv.block
        rooms = [n for n in sorted(NEW[lv.level_num]) if block.room(n).item_info.item in MAJOR]
        cellars = [n for n in lv.staircase_nums
                   if block.staircase(n).room_type == RoomType.ITEM_STAIRCASE and block.staircase(n).item in MAJOR]
        places[lv.level_num] = rooms + cellars
        assert len(places[lv.level_num]) <= 9
    return places


COUNTER_DIR = Path(__file__).resolve().parents[2] / "vanilla_counter"
BOOK_GATE_ADDRESS = 0xBEC0      # bank 5, after the counter's code ($BDC0-$BEBF)


def item_counter(rom: bytearray, places: dict[int, list[int]], notes: list[str]) -> None:
    sys.path.insert(0, str(COUNTER_DIR))
    import build as counter                       # noqa: E402  (vanilla_counter/build.py)
    counter.QUESTS[1] = {area: tuple(v) for area, v in places.items()}
    if Q4_PLACEHOLDERS and not BETA_3Q_ONLY:
        counter.QUESTS[2] = {area: tuple(Q4_COUNTER_PLACES.get(area, [])) for area in range(10)}
    code, table, chest = counter.assemble(), counter.table_bytes(), counter.tile_bytes(counter.CHEST)
    entry = counter.CODE_ADDRESS
    gate = bytes([0xAD, 0x61, 0x06,              # LDA $0661   book
                  0xD0, 0x04,                    # BNE show
                  0xA5, 0x15, 0x4A, 0x60,        # LDA FrameCounter, LSR, RTS: the game's own two instructions
                  0x4C, entry & 0xFF, entry >> 8])   # show: JMP ItemCounterOnSkippedFrames
    sites = [(counter.HOOK, counter.HOOK_ORIGINAL, bytes([0x20, BOOK_GATE_ADDRESS & 0xFF, BOOK_GATE_ADDRESS >> 8])),
             (counter.bank_5(counter.CODE_ADDRESS), b"\xff" * counter.CODE_SPACE, code),
             (counter.bank_5(counter.TABLE_ADDRESS), b"\xff" * counter.TABLE_SPACE, table),
             (counter.bank_5(BOOK_GATE_ADDRESS), b"\xff" * 16, gate),
             (counter.CHEST_TILE, bytes(16), chest)]
    for offset, expected, data in sites:
        assert rom[offset:offset + len(expected)] == expected, hex(offset)
        rom[offset:offset + len(data)] = data
    notes.append(f"item counter: code {len(code)} bytes at ${entry:04X}, table {len(table)} at "
                 f"${counter.TABLE_ADDRESS:04X}, book gate at ${BOOK_GATE_ADDRESS:04X}")


if __name__ == "__main__":
    rom = Path(sys.argv[1]).read_bytes()
    patched, notes = build(rom)
    sys.path.insert(0, str(HERE.parent.parent / "vanilla_counter"))
    from build import ips      # noqa: E402
    Path(sys.argv[2]).write_bytes(ips(rom, patched))
    Path(sys.argv[3]).write_bytes(patched)
    print("\n".join(notes))

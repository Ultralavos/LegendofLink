from zora.model.overworld import EntranceType
from zora.model.rooms import EnemySpec
"""3Q Level 1 test patch for The Legend of Zelda (US PRG1).

    python3 build_l1.py PRG1.nes OUT.ips OUT.nes

Parses the player's PRG1 ROM with ZORA's model (in PRG0's layout), rewrites Level 1 on the 3Q grid, clears the
rooms it takes from Levels 1-6 and walls off doors into it, makes the overworld changes, swaps the Like Like's
and the Wallmaster's sprite groups, then writes the world back (ZORA's serializer, no ZORA patches) and moves
it back to PRG1's layout.
"""
import json
import sys
from dataclasses import replace
from pathlib import Path

from zora.generate.shapes.minimap import command_block, synthesize_minimap
from zora.generate.steps import shuffle_enemy_groups as seg
from zora.generate.steps.group_banks import Staged
from zora.model.enums import (BossSound, Destination, Direction, Enemy, Item, ItemPosition, OverworldDirection,
                              RoomAction, RoomType, WallType)
from zora.model.levels import Level
from zora.model.overworld import ShopItem
from zora.model.rooms import EnemyInfo, ItemInfo, LayoutInfo, Room, SecretInfo, StaircaseRoom, WallSet
from zora.model.sprites import EnemySpriteSet
from zora.rom.base_rom import recognized_player_rom, using_player_rom
from zora.rom.game_config import GameConfig
from zora.rom.layout import MIXED_ENEMY_POINTER_TABLE_ADDRESS
from zora.rom.parse.rom_file import original_bins_from_rom, parse_rom
from zora.rom.serialize.game_world import serialize_game_world

HERE = Path(__file__).resolve().parent
Q3 = HERE.parent
E = Enemy
W = WallType
OPEN, WALL, WALK, LOCK, SHUT = W.OPEN_DOOR, W.SOLID_WALL, W.WALK_THROUGH_WALL_1, W.LOCKED_DOOR_1, W.SHUTTER_DOOR
ROWS = "ABCDEFGH"


def cell(name: str) -> int:
    return ROWS.index(name[0]) * 16 + int(name[1:]) - 1


GRID = json.loads((Q3 / "grid_1_6.json").read_text())
NEW_L1 = {r * 16 + c for r in range(8) for c in range(16) if GRID[r][c] == 1}
QTY = [3, 5, 6, 8]
COUNT = {n: i for i, n in enumerate(QTY)}

# Mixed lists: members in spawn order, padded with NOTHING to 8.
MIXED = {
    "C11": [E.CORNER_TRAPS, E.NOTHING, E.NOTHING, E.NOTHING, E.STALFOS, E.STALFOS, E.STALFOS, E.STALFOS],
    "G9": [E.LIKE_LIKE] * 2 + [E.ROPE] * 4 + [E.BUBBLE] * 2,
    "G8": [E.BLUE_GORIYA] * 3 + [E.STALFOS] * 3 + [E.LIKE_LIKE] * 2,
}
# Rooms that use an existing list: D11 $75 (2 bubbles, 3 blue Goriyas, then Keese), F10 $79 (3 bubbles,
# then Wallmasters, which the swap below turns into Like Likes in group A's levels).
EXISTING = {"D11": Enemy(0x75), "F10": Enemy(0x79)}
MIXED_COUNT = {"C11": 8, "D11": 5, "F10": 6, "G9": 8, "G8": 8}

# room: (layout, push-block variant, enemy or mixed key, count, item, item position, trigger,
#        walls N E S W, inner palette)
P = ItemPosition
R = RoomType
A = RoomAction
ROOMS = {
    "H10": (R.ENTRANCE_ROOM, False, E.NOTHING, 3, Item.NOTHING, P.POSITION_A, A.NONE, (OPEN, LOCK, OPEN, WALL), 3),
    "H11": (R.BLACK_ROOM, False, E.ELDER_2, 3, Item.NOTHING, P.POSITION_A, A.NONE, (WALL, WALL, WALL, LOCK), 0),
    "G10": (R.TWO_FIREBALL_ROOM, False, E.STALFOS, 5, Item.KEY, P.POSITION_C, A.ALL_DEAD_ITEM,
            (SHUT, OPEN, OPEN, OPEN), 2),
    "G11": (R.HORIZONTAL_CHUTE_ROOM, False, E.BLUE_KEESE, 6, Item.MAP, P.POSITION_C, A.NONE, (WALL, WALK, WALL, OPEN), 2),
    "G12": (R.T_ROOM, False, E.GEL_2, 8, Item.KEY, P.POSITION_A, A.ALL_DEAD, (WALL, SHUT, WALL, WALK), 2),
    "G13": (R.NARROW_STAIR_ROOM, False, E.AQUAMENTUS, 3, Item.KEY, P.POSITION_C, A.ALL_DEAD_ITEM,
            (WALL, WALL, WALL, SHUT), 2),
    "C10": (R.FIVE_PAIR_ROOM, False, E.BLUE_KEESE, 8, Item.NOTHING, P.POSITION_A, A.ALL_DEAD, (WALL, SHUT, WALL, WALL), 2),
    "C11": (R.PLAIN_ROOM, False, "C11", None, Item.NOTHING, P.POSITION_A, A.ALL_DEAD, (WALK, WALL, SHUT, SHUT), 2),
    "B11": (R.ZIGZAG_ROOM, False, E.GEL_2, 6, Item.KEY, P.POSITION_C, A.ALL_DEAD_ITEM, (WALL, WALL, WALK, LOCK), 2),
    "B10": (R.LAVA_MOAT, False, E.GEL_2, 8, Item.NOTHING, P.POSITION_A, A.ALL_DEAD, (SHUT, LOCK, WALL, WALL), 2),
    "A10": (R.MAZE_ROOM, True, E.BLUE_KEESE, 8, Item.NOTHING, P.POSITION_A, A.BLOCK_STAIRS, (WALL, WALL, OPEN, WALL), 2),
    "D11": (R.SINGLE_SIX_BLOCK_ROOM, False, "D11", None, Item.COMPASS, P.POSITION_D, A.ALL_DEAD_ITEM,
            (OPEN, WALL, WALL, OPEN), 2),
    "D10": (R.BLACK_ROOM, False, E.ELDER_6, 3, Item.NOTHING, P.POSITION_A, A.NONE, (WALL, OPEN, WALK, WALL), 0),
    "E10": (R.POINTLESS_MOAT_ROOM, False, E.BLUE_GORIYA, 6, Item.KEY, P.POSITION_B, A.ALL_DEAD_ITEM,
            (WALL, WALL, OPEN, WALL), 2),
    "F10": (R.PLAIN_ROOM, False, "F10", None, Item.NOTHING, P.POSITION_A, A.ALL_DEAD, (SHUT, LOCK, SHUT, WALL), 2),
    "F11": (R.AQUAMENTUS_ROOM, False, E.AQUAMENTUS, 3, Item.HEART_CONTAINER, P.POSITION_A, A.ALL_DEAD_ITEM,
            (SHUT, WALL, WALL, SHUT), 2),
    "E11": (R.TRIFORCE_ROOM, False, E.NOTHING, 3, Item.TRIFORCE, P.POSITION_C, A.NONE, (WALL, WALL, OPEN, WALL), 2),
    "G9": (R.VERTICAL_MOAT_ROOM, False, "G9", None, Item.KEY, P.POSITION_C, A.ALL_DEAD_ITEM, (WALL, OPEN, WALL, WALK), 2),
    "G8": (R.FOUR_FIREBALL_ROOM, False, "G8", None, Item.WHITE_SWORD, P.POSITION_C, A.ALL_DEAD_ITEM,
           (WALL, WALK, WALL, WALL), 2),
}
# D10's south is one-way into E10 (E10's north stays a wall).
ITEM_SPOTS = [0x2C, 0xAC, 0x89, 0xA8]          # A 2,12  B 10,12  C 8,9  D 10,8

TEXTS = {   # quote id: text ('|' starts a line; lines centered on 22 columns)
    7: ["I DON'T HAVE A SWORD", "FOR YOU. TRY CHECKING", "ABOVE THE WATERFALL."],       # H8's cave (and H6's)
    0: ["GELS AND KEESE ARE", "DANGEROUS, TAKE THIS!"],                               # C2's grave cave
    19: ["W W N W THROUGH THE", "FOREST MAZE, SEEK THE", "MAN AT THE GRAVE"],            # H11 (ELDER_2, group A)
    26: ["TAKE THE LONG BRIDGE", "TO THE ISLAND."],                                    # D10 (ELDER_6, group A)
}
LINE = 22

# Overworld layout rows (PRG0 offsets): D3 east wall, D4 west wall
ROOM_LAYOUTS_OW = 0x15428
LAYOUT_ROWS = {49: bytes.fromhex("f0f1a9c8c7a00683a1a5a4c8c7a60000"),
               50: bytes.fromhex("000002b702b7b6b702b7d2b702b60000")}
SET_A_LEVELS = {1, 2, 7}
SET_C_LEVELS = {4, 6, 9}


def centered(lines: list[str]) -> str:
    return "|".join("~" * max(0, (LINE - len(line)) // 2) + line for line in lines)


def set_side(block, room_num: int, side: str, wall: WallType) -> None:
    room = block.room(room_num)
    setattr(room.walls, {"N": "north", "E": "east", "S": "south", "W": "west"}[side], wall)


def free_run(image: bytes, start: int, end: int, size: int) -> int:
    """The first `size` bytes of $FF in [start, end) of the image."""
    run = 0
    for offset in range(start, end):
        run = run + 1 if image[offset] == 0xFF else 0
        if run == size:
            return offset - size + 1
    raise SystemExit("no free space for the mixed lists")


def build(prg1: bytes) -> tuple[bytes, list[str]]:
    notes: list[str] = []
    player = recognized_player_rom(prg1)
    assert player is not None and player.revision.name == "PRG1", "not PRG1"
    with using_player_rom(player):
        image = player.canvas
        world = parse_rom(image)
        old = world.levels[0]
        block = old.block
        assert all(lv.block is block for lv in world.levels[:6])

        # --- clear the rooms Level 1 takes, and vanilla Level 1 -------------------------------
        removed: set[int] = set(old.room_nums) | set(old.staircase_nums)
        for lv in world.levels[1:6]:
            taken = sorted(set(lv.room_nums) & NEW_L1)
            if taken:
                notes.append(f"Level {lv.level_num} loses rooms {', '.join(f'${n:02X}' for n in taken)}")
            lv.room_nums = [n for n in lv.room_nums if n not in NEW_L1]
            removed |= set(taken)
            if lv.entrance_room in NEW_L1:
                notes.append(f"Level {lv.level_num}'s entrance room ${lv.entrance_room:02X} is gone")
        # Staircases of other levels that lead into a removed room, or sit on a new Level 1 cell
        for lv in world.levels[1:6]:
            keep = []
            for n in lv.staircase_nums:
                st = block.staircase(n)
                exits = {st.return_dest} if st.room_type == RoomType.ITEM_STAIRCASE else {st.left_exit, st.right_exit}
                if n in NEW_L1 or exits & (removed | NEW_L1):
                    notes.append(f"Level {lv.level_num} loses staircase ${n:02X}")
                    removed.add(n)
                else:
                    keep.append(n)
            lv.staircase_nums = keep
            lv.staircase_room_pool = keep
            lv.stairway_data_raw = bytes(keep) + b"\xFF" * (10 - len(keep))
        for n in removed - NEW_L1:
            p0, p1 = block.palette_bits(n)
            block[n] = Room.blank(n, p0, p1)
        # Walls: any door of another level's room into a Level 1 cell
        step = {"N": (-16, "S"), "S": (16, "N"), "E": (1, "W"), "W": (-1, "E")}
        for lv in world.levels[1:6]:
            for n in lv.room_nums:
                for side, (delta, _) in step.items():
                    other = n + delta
                    if side == "E" and n % 16 == 15 or side == "W" and n % 16 == 0 or not 0 <= other < 128:
                        continue
                    if other in NEW_L1:
                        set_side(block, n, side, WALL)

        # --- the new Level 1 rooms --------------------------------------------------------------
        mixed_codes = pick_mixed_codes(world, removed | NEW_L1)
        for name, (layout, push, enemy, count, item, pos, trigger, walls, palette_1) in ROOMS.items():
            n = cell(name)
            assert n in NEW_L1, name
            if isinstance(enemy, str):
                info = EnemyInfo(mixed_codes[enemy], COUNT[MIXED_COUNT[enemy]])
            else:
                info = EnemyInfo(enemy, 0 if enemy == E.AQUAMENTUS else COUNT[count])
            block[n] = Room(
                room_num=n,
                walls=WallSet(*walls),
                enemy_info=info,
                layout_info=LayoutInfo(layout, push),
                item_info=ItemInfo(item, BossSound.NONE, False),
                secret_info=SecretInfo(trigger, pos),
                palette_0=2, palette_1=palette_1,
            )
        # Walls facing out of the level
        for n in NEW_L1:
            for side, (delta, _) in step.items():
                other = n + delta
                edge = side == "E" and n % 16 == 15 or side == "W" and n % 16 == 0 or not 0 <= other < 128
                if not edge and other not in NEW_L1 and not (n == cell("H10") and side == "S"):
                    set_side(block, n, side, WALL)

        # --- staircases: the one-way transport G13 -> C10, and A10's cellar ----------------------
        owned = {n for lv in world.levels[1:6] for n in (*lv.room_nums, *lv.staircase_nums)}
        free = sorted(n for n in removed - NEW_L1 if n not in owned)
        transport_cell, cellar_cell = free[-1], free[-2]
        raft = next(s for lv in world.levels_2q for s in lv.staircase_rooms if s.item == Item.RAFT)
        block[transport_cell] = StaircaseRoom(room_num=transport_cell, room_type=RoomType.TRANSPORT_STAIRCASE,
                                              exit_x=6, exit_y=9, left_exit=cell("G13"), right_exit=cell("C10"),
                                              t5_raw=0)
        block[cellar_cell] = StaircaseRoom(room_num=cellar_cell, room_type=RoomType.ITEM_STAIRCASE,
                                           exit_x=raft.exit_x, exit_y=raft.exit_y, item=Item.WOOD_SWORD,
                                           return_dest=cell("A10"),
                                           t5_raw=ITEM_SPOTS.index(0x89) << 4)
        notes.append(f"Stairs: transport in block room ${transport_cell:02X}, cellar ${cellar_cell:02X}")

        # --- the Level 1 record --------------------------------------------------------------------
        cells = sorted(NEW_L1)
        map_data, commands, map_start, map_cursor = synthesize_minimap(set(cells))
        pool = [cellar_cell, transport_cell]
        new = Level(
            level_num=1, entrance_room=cell("H10"), entrance_direction=Direction.SOUTH,
            palette_raw=old.palette_raw, fade_palette_raw=old.fade_palette_raw,
            staircase_room_pool=pool, room_nums=cells, staircase_nums=pool, block=block,
            boss_room=cell("F11"), enemy_sprite_set=EnemySpriteSet.A, boss_sprite_set=old.boss_sprite_set,
            start_y=old.start_y, item_position_table=list(ITEM_SPOTS), map_start=map_start,
            map_cursor_offset=map_cursor, map_data=map_data,
            map_ppu_commands=command_block(commands, old.map_ppu_commands), qty_table=list(QTY),
            stairway_data_raw=bytes(pool) + b"\xFF" * (10 - len(pool)), rom_level_num=old.rom_level_num,
            screen_status_ram_offset=old.screen_status_ram_offset,
        )
        block.levels.remove(old)
        world.levels[0] = new
        new.triforce_room_ptr = None

        # --- Like Like and Wallmaster trade sprite groups ---------------------------------------
        swap_like_like_and_wallmaster(world, notes)

        # --- overworld ------------------------------------------------------------------------------
        ow = world.overworld
        ow.screens[0x0A].destination = Destination.LEVEL_1          # A11
        ow.screens[0x77].destination = Destination.DEAD_WOODS_HINT  # H8: the grave-hint old man
        ow.screens[0x21].destination = Destination.WOOD_SWORD_CAVE  # C2's grave
        for cave in ow.caves:
            if cave.destination == Destination.WOOD_SWORD_CAVE:
                cave.item = Item.WOOD_BOOMERANG
            if cave.destination == Destination.SHOP_2:
                cave.items[2] = ShopItem(Item.MAGICAL_BOOMERANG, 150)
        ow.dead_woods_directions = [OverworldDirection.LEFT_WEST, OverworldDirection.LEFT_WEST,
                                    OverworldDirection.UP_NORTH, OverworldDirection.LEFT_WEST]
        by_id = {q.quote_id: q for q in world.quotes}
        for quote_id, lines in TEXTS.items():
            by_id[quote_id].text = centered(lines)
        # Quote 24 (Digdogger hint) was only group A's ELDER_4, in Level 5's room $67, which Level 1 takes:
        # it gives its bytes to the new texts.
        by_id[24].text = ""
        world.quotes_raw = None

        h16 = ow.screens[0x7F]
        h16.destination = Destination.TAKE_ANY
        h16.entrance_type = EntranceType.BOMB
        h16.exit_x_position, h16.exit_y_position = 3, 2      # out of the cave mouth
        h16.enemies_from_sides = True     # its spawn spots are under water now; the spawn search would hang
        h16.enemy_spec = EnemySpec(enemy=E.NOTHING, is_group=False, group_members=None)   # no enemies
        h16.has_zola = False
        ow.screens[0x2F].destination = Destination.LEVEL_9   # C16 (its take-any moves to H16)
        ow.screens[0x05].destination = Destination.DOOR_REPAIR   # A6, the old Level 9 bomb wall
        patch = serialize_game_world(world, original_bins_from_rom(image), config=GameConfig())
        out = bytearray(image)
        patch.apply(out)
        for row, codes in LAYOUT_ROWS.items():
            out[ROOM_LAYOUTS_OW + row * 16:ROOM_LAYOUTS_OW + (row + 1) * 16] = codes
        write_mixed_lists(out, mixed_codes, notes)
        overworld_mock(out, notes)
        return player.finished(bytes(out)), notes


def overworld_mock(out, notes):
    from zora.rom.vanilla_overworld import layouts as Lm
    T, O = 0x19, 0x0E
    H1, H2, DIR = 0x15C1D, 0x15C4E, 0x19D1F
    assert out[DIR + 2:DIR + 4] == (H1 - 0x10 - 0x14000 + 0x8000).to_bytes(2, "little")
    orig = [Lm._column(out, H1, i) for i in range(10)]
    NEW = 0xB930
    off = 0x10 + 0x14000 + NEW - 0x8000
    assert out[off:off + 80] == b"\xff" * 80
    blob = bytes(out[H1:H2 + 2])
    g14 = bytes([0xD9, 0x4E, 0x4E, 0x0E, 0x59, 0x59])            # bushes x2, ground x5, bushes x4
    h16 = bytes([0xDB, 0x1B, 0x27, 0x4E, 0x06, 0x45, 0x45])      # rock x3, bombable, ground x2, shore, water x4
    d15 = bytes([0xC5, 0x45, 0x05, 0x48, 0x48, 0x1A, 0x1B])      # water x5, water with left shore x4, rock x2
    d16 = bytes([0xC5, 0x45, 0x05, 0x49, 0x49, 0x1A, 0x1B])      # water x5, water with right shore x4, rock x2
    new = g14 + h16 + d15 + d16
    assert sum(1 for b in out[H1:H2 + 2] if b & 0x80) + 4 <= 16      # a heap holds 16 columns
    out[off:off + len(blob) + len(new)] = blob + new
    base = sum(1 for b in blob if b & 0x80)
    assert [Lm._column(out, off, i) for i in range(10)] == orig
    assert Lm._column(out, off, base) == [T, T] + [O] * 5 + [T] * 4
    assert Lm._column(out, off, base + 1) == [0x1B] * 3 + [0x27, O, O, 0x06] + [0x05] * 4
    assert Lm._column(out, off, base + 2) == [0x05] * 5 + [0x08] * 4 + [0x1A, 0x1B]
    assert Lm._column(out, off, base + 3) == [0x05] * 5 + [0x09] * 4 + [0x1A, 0x1B]
    out[DIR + 2:DIR + 4] = NEW.to_bytes(2, "little")
    # Heap 1's copy is full (16 columns): heap 2 is copied after it, with the next new columns. (Not heap 0: the
    # game's RAM copy of the directory keeps heap 0's vanilla pointer.)
    H0, H0_END, ENTRY = 0x15C4E, 0x15C90, 2
    orig0 = [Lm._column(out, H0, i) for i in range(10)]
    blob0 = bytes(out[H0:H0_END + 2])
    NEW0 = NEW + len(blob) + len(new)
    off0 = 0x10 + 0x14000 + NEW0 - 0x8000
    b14 = bytes([0xDB, 0x5B, 0x1B, 0x4E, 0x4E, 0x1A, 0x1B])      # rock x5 (as col 9: no jut), ground x4, rock wall x2
    c14a = bytes([0xC8, 0x48, 0x17, 0x4E, 0x4E, 0x4E])           # lake's left shore x4, corner, ground x6
    c14b = bytes([0xC5, 0x45, 0x07, 0x4E, 0x4E, 0x4E])           # water x4, shore, ground x6
    f1 = bytes([0xDB, 0x5B, 0x27, 0x4E, 0x4E, 0x4E])             # rock x4, bombable, ground x6
    new0 = b14 + c14a + c14b + f1
    assert out[off0:off0 + len(blob0) + len(new0)] == b"\xff" * (len(blob0) + len(new0))
    out[off0:off0 + len(blob0) + len(new0)] = blob0 + new0
    base0 = sum(1 for b in blob0 if b & 0x80)
    assert base0 + 4 <= 16
    assert [Lm._column(out, off0, i) for i in range(10)] == orig0
    assert Lm._column(out, off0, base0) == [0x1B] * 5 + [O] * 4 + [0x1A, 0x1B]
    assert Lm._column(out, off0, base0 + 1) == [0x08] * 4 + [0x17] + [O] * 6
    assert Lm._column(out, off0, base0 + 2) == [0x05] * 4 + [0x07] + [O] * 6
    assert out[DIR + 2 * ENTRY:DIR + 2 * ENTRY + 2] == (H0 - 0x10 - 0x14000 + 0x8000).to_bytes(2, "little")
    out[DIR + 2 * ENTRY:DIR + 2 * ENTRY + 2] = NEW0.to_bytes(2, "little")
    c_b14, c_c14a, c_c14b, c_f1 = (ENTRY << 4 | (base0 + k) for k in range(4))
    assert Lm._column(out, off0, base0 + 3) == [0x1B] * 4 + [0x27] + [O] * 6
    notes.append(f"overworld mock: heap 2 at ${NEW0:04X}, new columns ${c_b14:02X} (B14), ${c_c14a:02X} ${c_c14b:02X} (C14)")
    # B14: stairs rock, rock wall at the bottom of the gap. C14: stairs rock, the lake reaches west over the gap's top
    edits = {76: {8: c_f1}, 67: {11: 0x62},   # F1: bomb wall in the top rock; E8: its bush becomes a plain tree
             27: {3: 0x02}, 43: {3: 0x02},     # B13/C13: the stairs between them become rock
             28: {2: 0x02, 7: c_b14, 8: c_b14}, 44: {2: 0x06, 7: c_c14a, 8: c_c14b, 9: 0x36},
             60: {15: 0x10 | (base + 2)}, 61: {0: 0x10 | (base + 3)}, 89: {12: 0x19}, 104: {12: 0x10 | base}, 106: {5: 0x58, 6: 0x58, 7: 0x58, 8: 0xF6, 9: 0xE0},
             120: {3: 0x10 | (base + 1), 5: 0x13, 6: 0x13, 7: 0x13, 8: 0x13, 9: 0x13}}
    for code, cols in edits.items():
        for col, value in cols.items():
            out[ROOM_LAYOUTS_OW + code * 16 + col] = value
    notes.append(f"overworld mock: heap 1 at ${NEW:04X}, new columns ${0x10 | base:02X} (G14), "
                 f"${0x10 | (base + 1):02X} (H16)")


def pick_mixed_codes(world, gone: set[int]) -> dict[str, Enemy]:
    """Five mixed-list codes no first-quest room or overworld screen uses any more (the second quest's
    rooms that use them get the new lists: this test patch is first quest only)."""
    block = world.levels[1].block
    used_1q = {r.enemy.value for lv in world.levels for r in lv.rooms
               if lv.block is not block or (r.room_num not in gone and lv.entrance_room not in gone)}
    used_ow = {s.enemy_spec.enemy.value for s in world.overworld.screens}
    candidates = [c for c in range(0x62, 0x80) if c not in used_1q | used_ow]
    print("free mixed codes:", [hex(c) for c in candidates])
    assert len(candidates) >= len(MIXED), candidates
    return {**{name: Enemy(code) for name, code in zip(MIXED, candidates)}, **EXISTING}


def write_mixed_lists(out: bytearray, codes: dict[str, Enemy], notes: list[str]) -> None:
    """The five lists go in bank 5's free space; their codes' pointers point there."""
    size = 8 * len(MIXED)
    bank5 = 16 + 5 * 0x4000
    start = free_run(out, bank5 + 0x3900, bank5 + 0x3F00, size + 16) + 8
    for k, (name, members) in enumerate(MIXED.items()):
        assert codes[name] not in EXISTING.values()
        data = bytes(m.value for m in members + [E.NOTHING] * (8 - len(members)))
        offset = start + 8 * k
        out[offset:offset + 8] = data
        cpu = 0x8000 + offset - bank5
        index = codes[name].value - 0x62
        out[MIXED_ENEMY_POINTER_TABLE_ADDRESS + 2 * index] = cpu & 0xFF
        out[MIXED_ENEMY_POINTER_TABLE_ADDRESS + 2 * index + 1] = cpu >> 8
        notes.append(f"{name}: mixed list ${codes[name].value:02X} at ${cpu:04X}")


def swap_like_like_and_wallmaster(world, notes: list[str]) -> None:
    """Like Like joins group 0 (levels 1, 2, 7), Wallmaster group 2 (4, 6, 9): their tiles move, every room
    and mixed list of a level follows its group."""
    deal = seg.EnemyDeal(order=[], seed=E.ZOL, groups={
        0: [E.RED_GORIYA, E.LIKE_LIKE, E.ROPE, E.STALFOS],
        # Levels 3, 5, 8: Lanmolas at their fixed 158-161, Darknuts 162-181, Gibdos 182-185, Zol 188-191
        1: [E.ZOL, E.RED_DARKNUT, E.GIBDO, E.RED_LANMOLA],
        # Levels 4, 6, 9 without the red Lanmola: its fixed tiles 158-161 cover the two the Wallmaster borrows
        # (158, 159). Wizzrobe first: 160-171, Wallmaster 172-175, Vire 176-183, Pols Voice 184-187, Zol 188-191.
        2: [E.ZOL, E.BLUE_WIZZROBE, E.WALLMASTER, E.VIRE, E.POLS_VOICE],   # Pols Voice 184-187
    })
    staged = Staged()
    placed = seg.pack_enemies(world, deal, staged)
    for blk, offset, data in staged.tiles:
        world.sprites.write_tile(blk, offset, data)
    for offset, value in sorted(staged.frames.items()):
        world.enemies.set_frame_bytes(offset, [value])
    # The hungry Goriya's one frame byte (shared by every level): 3Q has it in Level 8 (group 1) and Level 9 (group 2),
    # where Goriya tiles aren't loaded. It wears the Zol (188-191, the seed every group shares), so it looks the same
    # in both levels (the user's pick).
    world.enemies.set_frame_bytes(seg.GORIYA_TILE_OFFSET, [placed[2][E.ZOL][0]])
    assert placed[1][E.ZOL][0] == placed[2][E.ZOL][0] == 188, (placed[1][E.ZOL], placed[2][E.ZOL])
    # Not ZORA's FIXED_FRAME_91 ($B0): that goes with ZORA moving the overworld group's tiles. The overworld is
    # untouched here, and frame 91 ($F8) is the secret caves' Moblin.
    swapped = 0
    for levels in (world.levels, world.levels_2q):
        for lv in levels:
            group_a = lv.enemy_sprite_set == EnemySpriteSet.A
            group_c = lv.enemy_sprite_set == EnemySpriteSet.C
            for room in lv.rooms:
                if group_a and room.enemy == E.WALLMASTER:
                    room.enemy = E.LIKE_LIKE; swapped += 1
                elif group_c and room.enemy == E.LIKE_LIKE:
                    room.enemy = E.WALLMASTER; swapped += 1
    notes.append(f"Like Like / Wallmaster: {swapped} rooms changed to match their level's group")
    # Mixed lists follow the levels that use them
    users: dict[int, set] = {}
    for levels in (world.levels, world.levels_2q):
        for lv in levels:
            for room in lv.rooms:
                if room.enemy.value >= 0x62:
                    users.setdefault(room.enemy.value, set()).add(lv.enemy_sprite_set)
    data = bytearray(world.enemies.mixed_enemy_data)
    for code, start in world.enemies.mixed_group_offsets.items():
        sets = users.get(code, set())
        window = range(start, min(start + 8, len(data)))
        if sets == {EnemySpriteSet.A}:
            change = (E.WALLMASTER, E.LIKE_LIKE)
        elif sets == {EnemySpriteSet.C}:
            change = (E.LIKE_LIKE, E.WALLMASTER)
        else:
            if any(data[i] in (E.WALLMASTER, E.LIKE_LIKE) for i in window) and sets:
                notes.append(f"mixed list ${code:02X} is used by groups {sorted(x.name for x in sets)}: left as is")
            continue
        for i in window:
            if data[i] == change[0]:
                data[i] = change[1]
                notes.append(f"mixed list ${code:02X}: {change[0].name} -> {change[1].name} at byte {i}")
    world.enemies.mixed_enemy_data = data


if __name__ == "__main__":
    rom = Path(sys.argv[1]).read_bytes()
    patched, notes = build(rom)
    sys.path.insert(0, str(Q3.parent / "vanilla_counter"))
    from build import ips      # noqa: E402
    Path(sys.argv[2]).write_bytes(ips(rom, patched))
    Path(sys.argv[3]).write_bytes(patched)
    print("\n".join(notes))

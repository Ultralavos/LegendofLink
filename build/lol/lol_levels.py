"""Legend of Link: the first quest's Levels 1-9 rebuilt in the user's shapes (new_grids.py), each from its own
vanilla rooms (a first pass; the user redesigns them later).

Per level, from the shape:
  entrance  the vanilla entrance room, at the user's entrance
  triforce  the vanilla triforce room in the farthest dead end; the boss (vanilla boss room, a blue potion) is its
            only neighbour, the door between them a shutter (opens when the boss dies). Level 9: Zelda A16, Ganon
            B16 (the user's), and the triforce-check old man right inside the entrance (his shutter west)
  choice    an old man room (the level's own) without a north door (a person stops Link walking up past him), in a
            dead end where there is one; lol_choice makes him the choice of two
  cellars   the vanilla number of item stairs (Level 5's goes to a floor when the block has no free square left);
            the stairs room is the vanilla one, the cellar in a free square of the block
  transports the user's (Levels 1-6), picked here for 7 (joining its four pieces), 8 and 9
  locks     on the way to the boss, each with a key found before it; keys beyond locks + 1 become rupees
The rest are the level's other rooms in vanilla order (persons and stairs rooms left out), repeated (without their
items) when the shape is bigger. CHOICE_ROOMS / SUBS of lol_choice are set from the result.
"""
import sys
from collections import deque

import lolpaths
B = lolpaths.Q3B
for p in (lolpaths.ZORA, B):
    if p not in sys.path:
        sys.path.insert(0, p)
from new_grids import LEVELS_1_6, LEVELS_7_9, ENTRANCES, TRANSPORTS as GIVEN, HIDDEN  # noqa: E402

ROWS = "ABCDEFGH"
STEP = {"N": -16, "E": 1, "S": 16, "W": -1}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
PERSONS = ("ELDER", "MUGGER", "HUNGRY_GORIYA", "BOMB_UPGRADER", "RUPEE_BOSS")
STAIR_LAYOUTS = ("SPIRAL_STAIR_ROOM", "NARROW_STAIR_ROOM", "DIAMOND_STAIR_ROOM")
L9_CHECK = "G16"                        # the triforce-check old man (vanilla G7), north of the entrance H16
LAYOUT = {}                             # level -> {cell: role}, for the map picture / tests
RESULT = {}
SNAP = {}                               # level -> (vanilla rooms, vanilla staircases), before the blocks are cleared


def cell(n):
    return ROWS.index(n[0]) * 16 + int(n[1:]) - 1


def name(c):
    return f"{ROWS[c // 16]}{c % 16 + 1}"


def grid(lv):
    return LEVELS_1_6 if lv <= 6 else LEVELS_7_9


def cells_of(lv):
    g = grid(lv)
    return {r * 16 + c for r in range(8) for c in range(16) if g[r][c] == str(lv)}


def free_of(group):
    g = LEVELS_1_6 if group == 0 else LEVELS_7_9
    return [r * 16 + c for r in range(8) for c in range(16) if g[r][c] == "."]


def nbrs(c, cells):
    for s, d in STEP.items():
        y = c + d
        if (s == "E" and c % 16 == 15) or (s == "W" and c % 16 == 0) or not 0 <= y < 128:
            continue
        if y in cells:
            yield s, y


def pieces(cells):
    piece, k = {}, 0
    for c in sorted(cells):
        if c in piece:
            continue
        piece[c] = k; q = [c]
        while q:
            x = q.pop()
            for _, y in nbrs(x, cells):
                if y not in piece:
                    piece[y] = k; q.append(y)
        k += 1
    return piece


def bfs(start, edges):
    dist = {start: 0}; q = deque([start]); prev = {}
    while q:
        x = q.popleft()
        for y in edges[x]:
            if y not in dist:
                dist[y] = dist[x] + 1; prev[y] = x; q.append(y)
    return dist, prev


def graph(cells, doors, trans, blocked=frozenset()):
    e = {c: set() for c in cells}
    for (a, b) in doors:
        if frozenset((a, b)) in blocked:
            continue
        e[a].add(b); e[b].add(a)
    for a, b in trans:
        e[a].add(b); e[b].add(a)
    return e


def pick_transports(lv, cells, piece, ent):
    """Level 7: chain its pieces from the entrance's (each hop from the farthest square of one piece to the
    farthest-from-the-rest square of the next); 8: one between its two farthest squares; 9: six far pairs."""
    doors = {(a, b) for a in cells for _, b in nbrs(a, cells) if piece[a] == piece[b] and a < b}
    if lv == 7:
        order = [piece[ent]] + sorted({piece[c] for c in cells} - {piece[ent]},
                                      key=lambda k: min(c // 16 for c in cells if piece[c] == k), reverse=True)
        out, entry = [], ent
        for k in range(len(order) - 1):
            g = graph(cells, doors, out)
            d, _ = bfs(entry, g)
            here = [c for c in cells if piece[c] == order[k] and c != ent]
            a = max(here, key=lambda c: (d.get(c, 0), -c))
            nxt = [c for c in cells if piece[c] == order[k + 1]]
            inner = {c: len(list(nbrs(c, cells))) for c in nxt}
            b = min(nxt, key=lambda c: (inner[c], c))            # a corner of the next piece
            out.append((a, b)); entry = b
        return out
    g = graph(cells, doors, [])
    n = {8: 1, 9: 6}[lv]
    out, used = [], set()
    allc = sorted(cells)
    dist = {c: bfs(c, g)[0] for c in allc}
    for _ in range(n):
        best = None
        for a in allc:
            for b in allc:
                if a >= b or {a, b} & used:
                    continue
                if any(abs(a % 16 - u % 16) + abs(a // 16 - u // 16) < 2 or
                       abs(b % 16 - u % 16) + abs(b // 16 - u // 16) < 2 for u in used):
                    continue
                if {a, b} & {ent, cell("A16"), cell("B16"), cell(L9_CHECK)}:
                    continue
                gg = graph(cells, doors, out)
                dd = bfs(a, gg)[0]
                score = dd[b]
                if best is None or score > best[0]:
                    best = (score, a, b)
        _, a, b = best
        out.append((a, b)); used |= {a, b}
    return out


def plan(lv, src_rooms, src_level, n_cellars):
    """The level's layout: {cell: (room spec, walls)}, transports, cellars, roles."""
    cells = cells_of(lv)
    ent = cell(ENTRANCES[lv])
    piece = pieces(cells)
    doors = {(a, b) for a in cells for _, b in nbrs(a, cells) if piece[a] == piece[b] and a < b}
    trans = [(cell(a), cell(b)) for a, b in GIVEN.get(lv, [])] or pick_transports(lv, cells, piece, ent)
    walls = {c: {s: ("OPEN" if piece.get(y) == piece[c] else "WALL") for s, y in
                 [(s, c + d) for s, d in STEP.items()]} for c in cells}
    for c in cells:
        for s, d in STEP.items():
            y = c + d
            if (s == "E" and c % 16 == 15) or (s == "W" and c % 16 == 0) or y not in cells or piece[y] != piece[c]:
                walls[c][s] = "WALL"
    walls[ent]["S"] = "OPEN"
    roles = {ent: "entrance"}
    t_ends = {x for p in trans for x in p}
    for x in t_ends:
        roles[x] = "transport"

    def degree(c):
        return [y for s, y in nbrs(c, cells) if walls[c][s] != "WALL"]

    g = graph(cells, doors, trans)
    dist, prev = bfs(ent, g)
    assert len(dist) == len(cells), (lv, "unreachable", sorted(name(c) for c in cells - set(dist)))

    def wall_between(a, b, ka="WALL", kb="WALL"):
        for s, d in STEP.items():
            if a + d == b:
                walls[a][s] = ka; walls[b][OPP[s]] = kb

    if lv == 9:
        tri, boss = cell("A16"), cell("B16")
        chk = cell(L9_CHECK)
        roles[chk] = "check"
        wall_between(ent, cell("H15"))
        walls[chk]["W"] = "SHUT"
    else:
        # the farthest square that can be closed off to one neighbour (the boss) with every room still reachable
        def connected_without(c, keep):
            dd = {(a, b) for a in cells for s, b in nbrs(a, cells) if walls[a][s] != "WALL" and a < b
                  and not (c in (a, b) and keep not in (a, b))}
            return len(bfs(ent, graph(cells, dd, trans))[0]) == len(cells)
        best = None
        for c in cells:
            if c in roles:
                continue
            for b in degree(c):
                if b in roles or not connected_without(c, b):
                    continue
                score = (dist[c], len(degree(c)) == 1, -c)
                if best is None or score > best[0]:
                    best = (score, c, b)
        _, tri, boss = best
    for s, y in nbrs(tri, cells):
        if y != boss:
            wall_between(tri, y)
    for s, d in STEP.items():
        if tri + d == boss:
            walls[tri][s] = "OPEN"; walls[boss][OPP[s]] = "SHUT"
    roles[tri], roles[boss] = "triforce", "boss"

    # the old man's choice: a room without a north door (a person stops Link walking up past him), a dead end
    # if there is one
    cands = [c for c in cells if c not in roles and walls[c]["N"] == "WALL" and tri not in degree(c)]
    choice = max(cands, key=lambda c: (len(degree(c)) == 1, dist[c], -c))
    roles[choice] = "choice"

    # item stairs: the deepest remaining squares (dead ends first)
    stairs = []
    for _ in range(n_cellars):
        rest = [c for c in cells if c not in roles]
        c = max(rest, key=lambda c: (len(degree(c)) == 1, dist[c], -c))
        roles[c] = "stairs"; stairs.append(c)
    RESULT.setdefault(lv, {})["stairs"] = stairs
    return cells, ent, trans, walls, roles, tri, boss, choice, stairs, doors


def assign(lv, src, vanilla, cells, ent, trans, roles, tri, boss, choice, stairs, n_cellars):
    """Which vanilla room each square gets: {cell: (room, overrides)}."""
    rooms = {r.room_num: r for r in SNAP[lv][0]}
    nm = lambda r: r.enemy_info.enemy.name
    out, used = {}, set()

    def take(r, c, **kw):
        out[c] = (r, kw); used.add(r.room_num)
    take(rooms[vanilla.entrance_room], ent)
    take(rooms[vanilla.boss_room], boss, item="BLUE_POTION" if lv != 9 else None)
    tri_room = next(r for r in rooms.values() if r.layout_info.room_type.name == "TRIFORCE_ROOM" or
                    r.layout_info.room_type.name == "ZELDA_ROOM")
    take(tri_room, tri)
    elders = [r for r in rooms.values() if nm(r).startswith("ELDER")]
    if lv == 9:
        check = next(r for r in elders if nm(r) == "ELDER")
        take(check, cell(L9_CHECK), trigger="NONE")
        elders = [r for r in elders if r is not check]
    take(elders[0], choice)
    # cellars: the vanilla stairs rooms (by their cellar's return room), in the vanilla cellar order
    vcell = [s for s in SNAP[lv][1] if s.room_type.name == "ITEM_STAIRCASE"]
    for c, s in zip(stairs, vcell):
        take(rooms[s.return_dest], c)
    # transports: the vanilla stairs rooms not used, else rooms given stairs
    stair_rooms = [r for r in rooms.values() if r.room_num not in used and
                   (r.layout_info.room_type.name in STAIR_LAYOUTS or r.secret_info.trigger.name == "BLOCK_STAIRS")]
    normal = [r for r in sorted(rooms.values(), key=lambda r: (r.room_num // 16 * -1, r.room_num))
              if r.room_num not in used and r not in stair_rooms and not nm(r).startswith(PERSONS)
              and nm(r) not in ("THE_BEAST", "THE_KIDNAPPED") and r.secret_info.trigger.name != "MONEY_OR_LIFE"]
    # keys, maps and compasses first
    normal.sort(key=lambda r: r.item_info.item.name not in ("KEY", "MAP", "COMPASS"))
    for c in sorted({x for p in trans for x in p}):
        if stair_rooms:
            r = stair_rooms.pop(0)
            take(r, c, trigger="NONE" if r.secret_info.trigger.name == "BLOCK_STAIRS" else None,
                 layout=None if r.layout_info.room_type.name in STAIR_LAYOUTS else "SPIRAL_STAIR_ROOM", push=False)
        else:
            r = normal.pop() if normal else rooms[vanilla.entrance_room]
            take(r, c, layout="SPIRAL_STAIR_ROOM", push=False, item="NOTHING", trigger="NONE")
    rest = sorted((c for c in cells if c not in out), key=lambda c: c)
    k = 0
    pool = list(normal)
    for c in rest:
        if pool:
            take(pool.pop(0), c)
        else:                                   # more squares than rooms: repeat, without items
            r = normal[k % len(normal)]; k += 1
            take(r, c, item="NOTHING", trigger="NONE" if r.secret_info.trigger.name in ("BLOCK_STAIRS",) else None)
    return out


def apply(rom: bytearray, notes: list) -> None:
    import build_q3 as q
    from zora.model.enums import Item, RoomType, Direction
    from zora.model.rooms import Room, StaircaseRoom, EnemyInfo, LayoutInfo, ItemInfo, SecretInfo, WallSet
    from zora.model.levels import Level
    from zora.rom.parse.bin_files import load_bin_files_from_rom
    from zora.rom.parse.game_world import parse_game_world
    from zora.rom.serialize.levels import encode_level_block, _serialize_level_info
    from zora.rom.layout import LEVEL_1_6_DATA_ADDRESS, LEVEL_7_9_DATA_ADDRESS
    from zora.generate.shapes.minimap import synthesize_minimap, command_block, drawn_commands
    import lol_choice
    world = parse_game_world(load_bin_files_from_rom(bytes(rom)), rom_bytes=bytes(rom))
    R, E, A, P = q.R, q.E, q.A, q.P
    K = {"OPEN": q.OPEN, "WALL": q.WALL, "LOCK": q.LOCK, "SHUT": q.SHUT}
    info_at = 0x19310
    # cellars per level (vanilla), cut where a block has too few free squares
    want = {lv: len([s for s in world.levels[lv - 1].staircase_rooms if s.room_type.name == "ITEM_STAIRCASE"])
            for lv in range(1, 10)}
    plans = {}
    for group, lvs in ((0, range(1, 7)), (1, range(7, 10))):
        free = free_of(group)
        ntr = 0
        for lv in lvs:
            cells = cells_of(lv)
            ntr += len(GIVEN.get(lv, [])) or {7: 3, 8: 1, 9: 6}[lv]
        cut = []
        while ntr + sum(want[lv] for lv in lvs) > len(free):
            lv = 5 if want.get(5) and 5 in lvs else max(lvs, key=lambda l: want[l])
            want[lv] -= 1; cut.append(lv)
        if cut:
            notes.append(f"levels: no free square for {len(cut)} item stairs (Level {', '.join(map(str, cut))}): "
                         "that item is on a floor instead")
    for lv in range(1, 10):
        SNAP[lv] = ([r for r in world.levels[lv - 1].rooms if hasattr(r, "layout_info")],
                    list(world.levels[lv - 1].staircase_rooms))
    old_subs = {(l, r): it for l, r, it in lol_choice.SUBS}
    new_subs, choice_rooms = [], {}
    for group, lvs in ((0, range(1, 7)), (1, range(7, 10))):
        block = world.levels[lvs[0] - 1].block
        free = free_of(group)
        for n in range(128):
            p0, p1 = block.palette_bits(n)
            block[n] = Room.blank(n, p0, p1)
        for lv in lvs:
            vanilla = world.levels[lv - 1]
            cells, ent, trans, walls, roles, tri, boss, choice, stairs, doors = plan(lv, None, vanilla, want[lv])
            asg = assign(lv, None, vanilla, cells, ent, trans, roles, tri, boss, choice, stairs, want[lv])
            # locks along the way to the boss
            keys = {c for c, (r, kw) in asg.items() if (kw.get("item") or r.item_info.item.name) == "KEY"}
            g = graph(cells, {(a, b) for a in cells for s, b in nbrs(a, cells) if walls[a][s] != "WALL" and a < b},
                      trans)
            dist, prev = bfs(ent, g)
            path, x = [], boss
            while x != ent:
                path.append((prev[x], x)); x = prev[x]
            path.reverse()
            locks = []
            alld = {(a, b) for a in cells for s, b in nbrs(a, cells) if walls[a][s] != "WALL" and a < b}
            for a, b in path:
                if (a, b) not in alld and (b, a) not in alld:
                    continue                                    # a transport
                if roles.get(a) in ("check",) or roles.get(b) in ("triforce",) or walls[a].get("S") == "SHUT":
                    continue
                cut_g = graph(cells, alld, trans, blocked={frozenset((a, b))})
                before = set(bfs(ent, cut_g)[0])
                if b in before:
                    continue                                    # not a bridge
                if len(keys & before) > len(locks):
                    locks.append((a, b))
            for a, b in locks:
                for s, d in STEP.items():
                    if a + d == b:
                        walls[a][s] = "LOCK"; walls[b][OPP[s]] = "LOCK"
            surplus = sorted(keys, key=lambda c: -dist[c])[:max(0, len(keys) - len(locks) - 1)]
            for c in surplus:
                r, kw = asg[c]; kw = dict(kw); kw["item"] = "FIVE_RUPEES"; asg[c] = (r, kw)
            # the rooms
            for c, (r, kw) in asg.items():
                kw = {k: v for k, v in kw.items() if v is not None}
                layout = R[kw["layout"]] if "layout" in kw else r.layout_info.room_type
                push = kw.get("push", r.layout_info.movable_block)
                item = Item[kw["item"]] if "item" in kw else r.item_info.item
                trig = A[kw["trigger"]] if "trigger" in kw else r.secret_info.trigger
                if trig == A.BLOCK_DOOR:
                    trig = A.NONE
                if trig == A.RINGLEADER:
                    trig = A.ALL_DEAD_ITEM
                if item == Item.NOTHING and trig == A.ALL_DEAD_ITEM:
                    trig = A.ALL_DEAD                   # (else clearing it shows item $03: a magical sword)
                if layout == R.NARROW_STAIR_ROOM and walls[c]["E"] != "WALL":
                    layout = R.SPIRAL_STAIR_ROOM                # its stairs fill the east end: no door there
                if roles.get(c) not in ("stairs", "transport"):     # stairs anywhere else lead nowhere (a crash)
                    assert layout.name not in STAIR_LAYOUTS and trig != A.BLOCK_STAIRS, (lv, name(c), layout.name)
                w = WallSet(*(K[walls[c][s]] for s in "NESW"))
                block[c] = Room(room_num=c, walls=w, enemy_info=EnemyInfo(r.enemy_info.enemy, r.enemy_info.count_index),
                                layout_info=LayoutInfo(layout, push),
                                item_info=ItemInfo(item, r.item_info.boss_sound, r.item_info.is_dark),
                                secret_info=SecretInfo(trig, r.secret_info.item_position),
                                palette_0=r.palette_0, palette_1=r.palette_1)
            # staircases
            stair_cells = []
            vtr = [s for s in SNAP[lv][1] if s.room_type.name == "TRANSPORT_STAIRCASE"]
            for a, b in trans:
                n = free.pop(0)
                proto = vtr[0] if vtr else None
                block[n] = StaircaseRoom(room_num=n, room_type=RoomType.TRANSPORT_STAIRCASE,
                                         exit_x=proto.exit_x if proto else 6, exit_y=proto.exit_y if proto else 9,
                                         left_exit=a, right_exit=b, t5_raw=proto.t5_raw if proto else 0)
                stair_cells.append(n)
            vcell = [s for s in SNAP[lv][1] if s.room_type.name == "ITEM_STAIRCASE"]
            cellar_of = {}
            for st_room, s in zip(stairs, vcell):
                n = free.pop(0)
                block[n] = StaircaseRoom(room_num=n, room_type=RoomType.ITEM_STAIRCASE, exit_x=s.exit_x,
                                         exit_y=s.exit_y, item=s.item, return_dest=st_room, t5_raw=s.t5_raw)
                stair_cells.append(n); cellar_of[s.room_num] = n
            # LoL items: the old cellars' and floors' substitutes
            vroom_at = {r.room_num: c for c, (r, kw) in asg.items() if kw.get("item") in (None,)}
            floor_spots = [c for c in sorted(asg, key=lambda c: dist[c]) if roles.get(c) is None
                           and asg[c][1].get("item") is None and c not in vroom_at.values() or False]
            for (l, rm), it in old_subs.items():
                if l != lv:
                    continue
                v = cell(rm)
                if v in cellar_of:
                    new_subs.append((lv, name(cellar_of[v]), it))
                elif v in vroom_at and roles.get(vroom_at[v]) is None:
                    new_subs.append((lv, name(vroom_at[v]), it))
                else:                                           # its cellar was cut, or its room left out
                    spots = [c for c in sorted(cells, key=lambda c: -dist[c]) if roles.get(c) is None
                             and c not in {cell(s[1]) for s in new_subs if s[0] == lv}]
                    new_subs.append((lv, name(spots[0]), it))
            choice_rooms[lv] = name(choice)
            # the level information
            shown = cells - {cell(x) for x in HIDDEN.get(lv, [])}
            map_data, commands, map_start, map_cursor = synthesize_minimap(shown)
            assert len(commands) <= 45, (lv, len(commands))
            new = Level(
                level_num=lv, entrance_room=ent, entrance_direction=Direction.SOUTH,
                palette_raw=vanilla.palette_raw, fade_palette_raw=vanilla.fade_palette_raw,
                staircase_room_pool=stair_cells, room_nums=sorted(cells), staircase_nums=sorted(stair_cells),
                block=block, boss_room=boss, enemy_sprite_set=vanilla.enemy_sprite_set,
                boss_sprite_set=vanilla.boss_sprite_set, start_y=vanilla.start_y,
                item_position_table=list(vanilla.item_position_table), map_start=map_start,
                map_cursor_offset=map_cursor, map_data=map_data,
                map_ppu_commands=command_block(commands, vanilla.map_ppu_commands),
                qty_table=list(vanilla.qty_table),
                stairway_data_raw=bytes(stair_cells) + b"\xFF" * (10 - len(stair_cells)),
                rom_level_num=vanilla.rom_level_num, screen_status_ram_offset=vanilla.screen_status_ram_offset)
            new.triforce_room_ptr = tri if lv != 9 else vanilla.triforce_room_ptr
            blk = bytearray(rom[info_at + lv * 0xFC:info_at + (lv + 1) * 0xFC])
            old_num = blk[0x33]
            _serialize_level_info(new, blk)
            blk[0x33] = old_num
            rom[info_at + lv * 0xFC:info_at + (lv + 1) * 0xFC] = blk
            LAYOUT[lv] = {"roles": roles, "trans": trans, "locks": locks, "stairs": stairs, "cellars": cellar_of,
                          "rooms": {c: name(r.room_num) for c, (r, kw) in asg.items()}}
            notes.append(f"L{lv}: {len(cells)} rooms, boss {name(boss)}, triforce {name(tri)}, old man {name(choice)}, "
                         f"transports {', '.join(name(a) + '-' + name(b) for a, b in trans)}, "
                         f"stairs {', '.join(name(s) for s in stairs) or '-'}, keys {len(keys) - len(surplus)} / "
                         f"locks {len(locks)}")
        addr = LEVEL_1_6_DATA_ADDRESS if group == 0 else LEVEL_7_9_DATA_ADDRESS
        rom[addr:addr + 0x300] = encode_level_block(block)
    import json, os
    json.dump({lv: {"roles": {name(c): r for c, r in v["roles"].items()},
                    "trans": [[name(a), name(b)] for a, b in v["trans"]],
                    "locks": [[name(a), name(b)] for a, b in v["locks"]],
                    "rooms": {name(c): r for c, r in v["rooms"].items()},
                    "cellars": {name(k): name(x) for k, x in v["cellars"].items()}}
               for lv, v in LAYOUT.items()},
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lol_levels_layout.json"), "w"), indent=1)
    lol_choice.CHOICE_ROOMS.clear(); lol_choice.CHOICE_ROOMS.update(choice_rooms)
    lol_choice.SUBS[:] = new_subs
    notes.append("LoL items: " + ", ".join(f"L{l} {r} ${i:02X}" for l, r, i in new_subs))

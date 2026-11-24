"""Legend of Link v2 (test): generated dungeons from the user's four grids (lol_gen's variants), loaded in the game.

The ROM is doubled to 256KB (16 banks; the fixed bank moves to bank 15). Banks 8-14 hold the variants, each with a
copy of the decoder and its tables at the same addresses.

Designs: all 21 of the user's. Allowed: the three 9s only level 9; the Face only shrines and 1-4; no Bell, Rook,
Unicorn, Stallion as shrines; no Cactus, Vice, Piranha, Robber, Pompadour, Bat, Giraffe, Face as 7 or 8.

Records (test: file 1 only; save RAM $7FAD + 5 * slot index, slot index = level 1-9 -> 0-8, shrine A-D -> 9-12):
  [0] design + 1 (0: not made)   [1] variant (bits 0-1) | enemy group (bits 2-3) | palette (bits 4-7: level - 1)
  [2] the boss                   [3] seed
  [4] items: levels: bits 0-2 the cellar's, 3-5 level 1's floor drop (0-4: S, D, X badge, orange, blue XP potion);
      level 9: its second cellar's item code (the first: a red potion)
Room memory by grid: grid 1 $077F, grid 2 $6392 (A-F's: saved per file by lol_af), grid 3 $6492 (file 2's copy of
A-F's: the test is file 1 only), grid 4 $06FF.

Made by GEN_FORCE (lol_entrances' roll: the test's first 13 caves are dungeons). Loaded at UpdateMode2Load_Full's
end (bank 6 $8109; also after an autosave): the palette from that vanilla level's info (bank 6), then DECODE (bank 8+)
writes the rooms (enemies / boss from the seed and the room's class), cellars, the level info and the map.
Level 2: the item stairs' block opens shutters; the cellar item goes to a room's bombs / rupees / key. Level 1: its
cellar item and a floor drop. Level 9: the triforce check at the entrance, Ganon and Zelda, two cellars.
Walking south out of the start room leaves the level (bank 5).
"""
import os
import sys
import lolpaths
for p in (lolpaths.ZORA,):
    if p not in sys.path:
        sys.path.insert(0, p)
import lol_gen as G
from lol_af import Asm, BANK, place, patch, AF_LEVELS

GRID_FILE = lolpaths.GRID_FILE
NAMES = {1: {'G': 'Serpent', 'M': 'Bell', 'B': 'Face', 'O': 'Rook'},
         2: {'B': 'Bat', 'C': 'Stallion', 'O': 'Giraffe', 'G': 'Unicorn', 'R': 'Pompadour', 'M': 'Whale'},
         3: {'P': 'Ghost', 'G': 'Gecko', 'B': 'Balloon'},
         4: {'M': 'Anteater', 'O': 'Robber', 'B': 'Sock Puppet', 'Y': 'Vice', 'P': 'Elephant', 'G': 'Cactus',
             'C': 'Poodle', 'N': 'Piranha'}}
HIDDEN = {'Pompadour': ['B15'], 'Ghost': ['B4', 'B6', 'D5', 'E4', 'E5'], 'Balloon': ['D11']}
NINES = {'Serpent', 'Balloon', 'Ghost'}
NO_SHRINE = {'Bell', 'Rook', 'Unicorn', 'Stallion'}
NO_78 = {'Cactus', 'Vice', 'Piranha', 'Robber', 'Pompadour', 'Bat', 'Giraffe', 'Face'}
ONLY_14_SH = {'Face'}
FLAGS = {1: 0x077F, 2: 0x6392, 3: 0x6492, 4: 0x06FF}
FLAGS_4B = 0x6292                       # grid 4's second group (file 2's room flags: one save file now)


def flags_of(d, ds):
    """Room memory of design d: its grid's, but grid 4's designs alternate between two areas, so their item cellars
    (more designs than free squares) never share a flag with another grid-4 dungeon of the same area."""
    gi = ds[d][0]
    if gi == 4 and grid_index(d, ds) % 2:
        return FLAGS_4B
    return FLAGS[gi]


def grid_index(d, ds):
    return [x for x in range(len(ds)) if ds[x][0] == ds[d][0]].index(d)
CLASS_LIST = G.LEVEL_CLASSES            # a layout set per level 1-9 and shrine A-D (class index = slot index)
NC = len(CLASS_LIST)
K = 3

REC = 0x7FAD
NSLOT = 13
CUR_GEN, GEN_CHOICE, SUB_RM, SUB_IT = 0x0168, 0x0169, 0x016A, 0x016C   # RAM (stack page, unused)
SCR = 0x0150                            # scratch (stack page, unused)
TRAMP = 0xBB90                          # bank 6 and the data banks
DECODE = 0x8000                         # each data bank: decoder + tables, then variants
DATA_BANKS = range(8, 15)
B3G = 0xABE0                            # bank 3: the pattern getters
B5X = 0x9360                            # bank 5: the start room's exit
INFO = 0x6B7E
ATTR = (0x687E, 0x68FE, 0x697E, 0x69FE, 0x6A7E, 0x6AFE)
CELLAR_ITEMS = (0x26, 0x27, 0x28, 0x29, 0x2A)
# minor drops (v2.02 test 16): each room still empty after the placed items is 25% left empty (DROP_EMPTY / 256);
# the rest roll this table (percent; what's left over, 14%, is nothing). A drop is then 75% on clear, 25% on the floor
DROP_EMPTY = 64
DROPS = ((G.I_KEY, 40), (G.I_BOMBS, 25), (G.I_RUPEES, 20), (G.I_BLUE_POTION, 1))
BOSSES = G.BOSS_OF
BOSS_A = (0x3D, 0x31, 0x32, 0x38, 0x39)
ENEMY_GROUP_LEVELS = ((1, 2, 7), (3, 5, 8), (4, 6), (9,))
GROUP_LEVEL = (1, 3, 4, 9)
TRAPS = (0x49, 0x4A)
# slot code (1-9, $0A-$0D) -> class
SLOT_CLASS = [0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 0, 0]
SLOT_INDEX = [0xFF, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 0xFF, 0xFF]
DESTS = list(range(1, 10)) + [0x0A, 0x0B, 0x0C, 0x0D]


BUILDING = False                        # (while lol_sets builds the set: LoL's own designs and classes)
CUSTOM = None                           # a dungeon set from lol_sets ({grid: rows, names, classes}); None: grids.txt


def custom_set():
    """The page's dungeon set (LOL_SET, with LOL_SEED or LOL_SET_SEED), built once."""
    global CUSTOM, BUILDING
    import os
    which = os.environ.get("LOL_SET", "lol")
    if which == "lol" or CUSTOM is False or BUILDING:
        return None
    if CUSTOM is None:
        import lol_sets
        seed = int(os.environ.get("LOL_SET_SEED") or os.environ.get("LOL_SEED") or 0)
        BUILDING = True
        try:
            CUSTOM = lol_sets.build_set(which, seed)
        finally:
            BUILDING = False
        if CUSTOM is None:                 # (Random picked LoL's own maps)
            CUSTOM = False
    return CUSTOM or None


def lol_designs():
    """LoL's own designs (grids.txt): call while BUILDING."""
    assert BUILDING
    return designs()


def designs():
    """[(grid, letter, name, cells, hidden cells)] and the free squares per grid."""
    cs = custom_set()
    if cs is not None:
        out, free = [], {}
        for gi in (1, 2, 3, 4):
            rows = cs[gi]["rows"]
            free[gi] = [r * 16 + c for r in range(8) for c in range(16) if rows[r][c] == '.']
            for k in sorted(cs[gi]["names"]):
                cells = [r * 16 + c for r in range(8) for c in range(16) if rows[r][c] == k]
                nm = cs[gi]["names"][k]
                out.append((gi, k, nm, cells, list(cs[gi].get("hidden", {}).get(nm, []))))
        return out, free
    txt = open(GRID_FILE).read().split('\n\n')
    out, free = [], {}
    for gi in (1, 2, 3, 4):
        rows = [l for l in txt[gi].split('\n') if len(l) == 16]
        free[gi] = [r * 16 + c for r in range(8) for c in range(16) if rows[r][c] == '.']
        for k in sorted(NAMES[gi]):
            nm = NAMES[gi][k]
            cells = [r * 16 + c for r in range(8) for c in range(16) if rows[r][c] == k]
            out.append((gi, k, nm, cells, [G.cell(x) for x in HIDDEN.get(nm, [])]))
    return out, free


def classes_of(nm):
    cs = custom_set()
    if cs is not None:
        for g in cs.values():
            if nm in g["classes"]:
                return tuple(g["classes"][nm])
    if nm in NINES:
        return ("L9",)
    cl = ["L13", "L4", "L57", "L8", "SH"]
    if nm in ONLY_14_SH:
        cl = ["L13", "L4", "SH"]
    if nm in NO_SHRINE:
        cl.remove("SH")
    out = [c for c in CLASS_LIST if G.GROUP[c] in cl]
    if nm in NO_78:
        out = [c for c in out if c not in ("L7", "L8")]
    return tuple(out)


def slot_mask(nm):
    """The slot codes (bit n = code n) a design may take."""
    m = 0
    for d in DESTS:
        cls = CLASS_LIST[SLOT_CLASS[d]]
        if cls not in classes_of(nm):
            continue
        if d in (7, 8) and nm in NO_78:
            continue
        m |= 1 << d
    return m


_CACHE = {}


def rule_of(nm):
    """A quest design's stair rules (lol_sets.quest_set), with the counts the level can take; None: LoL's."""
    cs = custom_set()
    if cs is None:
        return None
    for g in cs.values():
        if nm in g.get("rules", {}):
            import lol_sets
            r = g["rules"][nm]
            return lol_sets.quest_counts(g["classes"][nm][0], r) + tuple(r[2:])
    return None


def floor_levels():
    """Levels 1-9 that get a floor badge / XP: LoL's 1 and 2; a quest's own levels with a major item on the floor."""
    out = {1, 2}
    cs = custom_set()
    if cs is not None:
        for g in cs.values():
            for nm, r in g.get("rules", {}).items():
                lv = int(g["classes"][nm][0][1:])
                if r[3]:
                    out.add(lv)
                elif lv != 2:
                    out.discard(lv)
    return out


def cellar_alloc(ds, free):
    """A page set's cellars: {design: (item cellars, transport cellars)}, each design its own squares of its grid's
    free ones (level 2's item cellar is never used, so it shares another's)."""
    import lol_sets
    out, used = {}, {}
    for gi, k, nm, cells, hid in ds:
        cl = classes_of(nm)
        if not cl:
            continue
        ni, nt = lol_sets.cellar_need(cl[0], cells, rule_of(nm))
        fr = [c for c in free[gi] if c not in used.get(gi, set())]
        assert len(fr) >= ni + nt, (nm, gi, len(fr), ni, nt)
        ic, tc = fr[:ni], fr[ni:ni + nt]
        used.setdefault(gi, set()).update(ic + tc)
        if cl[0] == "L2":
            ic = [free[gi][0]]
        out[nm] = (ic, tc)
    return out


def build_variants():
    if "v" in _CACHE:
        return _CACHE["v"]
    ds, free = designs()
    out = {}
    per_grid = {}
    alloc = cellar_alloc(ds, free) if custom_set() is not None else None
    for d, (gi, k, nm, cells, hid) in enumerate(ds):
        fr = free[gi]
        if alloc is not None:             # a page set: each design its own cellars (lol_sets.cellar_need)
            if nm in alloc:
                ic, tc = alloc[nm]
                for cls in classes_of(nm):
                    ci = CLASS_LIST.index(cls)
                    out[(d, ci)] = G.make_variants(cells, cls, K, 1000 * d + ci, ic, tc, hid, rule=rule_of(nm))
            continue
        if False:
            pass
        else:
            n9 = 7 if gi in (1, 3) else (2 if gi == 4 else 7)
            tc = fr[-n9:] if gi != 4 else fr[9:12]
        items = fr[:len(fr) - len(tc)]
        if classes_of(nm) == ("L9",):
            ic = items[-2:]                       # the 9s on a grid share (never two 9s in a game)
        else:
            i = per_grid.get(gi, 0); per_grid[gi] = i + 1
            if gi == 4:
                i //= 2                           # (two flag areas: the pairs repeat between them)
            assert 2 * i + 1 < len(items) - (2 if gi in (1, 3) else 0), (nm, gi, i)
            ic = [items[2 * i], items[2 * i + 1]]
        for cls in classes_of(nm):
            ci = CLASS_LIST.index(cls)
            out[(d, ci)] = G.make_variants(cells, cls, K, 1000 * d + ci, ic, tc, hid)
    _CACHE["v"] = (ds, out)
    return _CACHE["v"]


def encode_variant(v, gi):
    """Header: n ordinary, n literal, start, tri, boss, choice, stairs room 1, 2, cellar 1, 2, n cellars, cellars...
    Ordinary rooms 5 bytes (cell, N|S|class, W|E|pos, layout, item|trigger); literal rooms 7 (cell, A-F)."""
    reg, lit = [], []
    LIT = {"choice": (0x0D, 0xA6), "check": (0x0B, 0xA6), "ganon": (0x3E, 0x28), "zelda": (0x37, 0x27)}
    for c, r in sorted(v["cells"].items()):
        w = r["walls"]
        a = (w[G.N_] << 5) | (w[G.S_] << 2) | 2
        b = (w[G.W_] << 5) | (w[G.E_] << 2) | 2
        if r["role"] in LIT:
            cc, d = LIT[r["role"]]
            e = 0x03 if r["item"] is None else r["item"]
            f = (r["pos"] << 4) | r["trigger"]
            if r["role"] == "ganon":
                e, f = 0x8E, 0x03                       # dark, the triforce of power; the last boss
            if r["role"] == "zelda":
                e, f = 0x03, 0x01
            lit.append(bytes([c, a, b, cc, d, e, f]))
            continue
        cls = r["eclass"] if r["eclass"] in (0, 1, 2, 3) else 0
        item = 0x03 if r["item"] is None else r["item"]
        assert item < 0x20 and r["layout"] < 0x80
        reg.append(bytes([c, (w[G.N_] << 5) | (w[G.S_] << 2) | cls, (w[G.W_] << 5) | (w[G.E_] << 2) | r["pos"],
                          r["layout"], (item << 3) | r["trigger"]]))
    cellars = []
    item_sq, stair_rm = [0xFF, 0xFF], [0xFF, 0xFF]
    ii = 0
    for sq, kind, a_, b_, x, y in v["stairs"]:
        if kind == "item":
            lit.append(bytes([sq, a_, b_, (x << 4) | y, 0x3F, 0x19, 0]))
            item_sq[ii] = sq; stair_rm[ii] = a_; ii += 1
        else:
            lit.append(bytes([sq, a_, b_, (x << 4) | y, 0x3E, 0x03, 0]))
        cellars.append(sq)
    assert len(cellars) <= 10
    hdr = bytes([len(reg), len(lit), v["start"], v["tri"], 0xFF if v["boss"] is None else v["boss"],
                 0xFF if v["choice"] is None else v["choice"], stair_rm[0], stair_rm[1], item_sq[0], item_sq[1],
                 len(cellars)] + cellars)
    return hdr + b"".join(reg) + b"".join(lit)


def enemy_groups():
    """Per enemy group, the vanilla first-quest rooms' (monster id, count index, holds traps)."""
    from zora.rom.parse.bin_files import load_bin_files_from_rom
    from zora.rom.parse.game_world import parse_game_world
    import lol_mixgroups
    rom = lol_mixgroups.source()          # (Mix enemy groups: the rooms and lists redrawn from the new groups)
    from zora.rom.base_rom import player_rom_of, using_player_rom
    with using_player_rom(player_rom_of(bytes(lolpaths.source_rom()))):
        w = parse_game_world(load_bin_files_from_rom(rom), rom_bytes=rom)
    b5, la = BANK(5), 0x873F
    lists = []
    for gi, lvs in enumerate(ENEMY_GROUP_LEVELS):
        ent = []
        for lv in lvs:
            for r in w.levels[lv - 1].rooms:
                m = r.enemy_info.enemy.value
                ok_boss = gi == 3 and m in (0x47, 0x48, 0x3A, 0x3B)       # level 9: patras, lanmolas
                if m == 0 or m >= 0x80 or ((0x31 <= m < 0x62) and not ok_boss):
                    continue
                trap = m in TRAPS
                if m >= 0x62:
                    o = BANK(5) + (rom[b5 + la - 0x8000 + 2 * (m - 0x62)] |
                                   rom[b5 + la - 0x8000 + 2 * (m - 0x62) + 1] << 8) - 0x8000
                    members = rom[o:o + 8]
                    if any(0x31 <= t < 0x62 and t not in TRAPS for t in members[:5]) and gi != 3:
                        continue
                    trap = any(t in TRAPS for t in members)
                if (m, r.enemy_info.count_index, trap) not in ent:
                    ent.append((m, r.enemy_info.count_index, trap))
        lists.append(ent)
    return lists


GATED = ("B2", "B12", "E6", "C16", "E3", "B10")      # screens behind the ladder / raft / recorder / bracelet
TRAMPD = 0xBB70                         # bank 6 and the data banks: deal the entrances (a new file)


def deal_info(rom):
    """The entrances (lol_entrances' order), the contents to deal (71), A15's index, the gated screens' indexes."""
    import lol_entrances as E
    from lol_af import screen
    OW = 0x18410
    name = lambda x: "ABCDEFGH"[x // 16] + str(x % 16 + 1)
    ents = [x for x in range(128) if rom[OW + 0x80 + x] >> 2 and rom[OW + 0x280 + x] >> 6 != 2
            and rom[OW + 0x80 + x] >> 2 != 0x14 and name(x) not in E.EXCLUDED]
    cont = [d for d, n in sorted(E.MAX_GEN.items()) for _ in range(n)]
    assert len(cont) == len(ents) == 71
    return cont, ents.index(screen("A15")), [ents.index(screen(g)) for g in GATED]


def deal_code(a, info):
    """DEAL (decoder entry 2, from bank 6 on a new file's first overworld load): every entrance's contents dealt
    into the store at once - shuffled, then A15 never a level 1-8, and among the gated screens (B2, B12, E6, C16, E3,
    B10) at least one dungeon or shrine and one upgrade cave."""
    import lol_entrances as E
    cont, a15, gated = info
    N = len(cont)
    D_I, D_F, D_G = SCR, SCR + 1, SCR + 2
    ST, RNG = E.STORE, E.RNG
    import lol_modes                                    # (a fixed seed: no stirring with the frame count)
    fx = lol_modes.SEED_OPT is not None
    a.label("deal").abs(0xAD, RNG).b(*((0x49, 0x00) if fx else (0x45, 0x18))).abs(0x8D, RNG).abs(0xAD, RNG + 1)
    a.b(*((0x49, 0x00) if fx else (0x45, 0x15))).abs(0x8D, RNG + 1)
    a.abs(0x0D, RNG).br(0xD0, "dl_s").abs(0xEE, RNG)
    a.label("dl_s").b(0xA2, N - 1).label("dl_c").abs(0xBD, "dct").abs(0x9D, ST).b(0xCA).br(0x10, "dl_c")
    a.b(0xA9, N - 1).abs(0x8D, D_I)
    a.label("dl_sh").abs(0x20, "drnd").abs(0xAE, D_I).abs(0x3D, "dmask").abs(0xCD, D_I).br(0xF0, "dl_j").br(0xB0, "dl_sh")
    a.label("dl_j").b(0xA8).abs(0x20, "dswap").abs(0xCE, D_I).br(0xD0, "dl_sh")
    # A15: no level 1-8
    a.b(0xA2, a15).abs(0xBD, ST).abs(0x20, "dl18").br(0x90, "dl_a")
    a.label("dl_ar").abs(0x20, "drnd").b(0x29, 0x7F, 0xC9, N).br(0xB0, "dl_ar").b(0xA8, 0xC0, a15).br(0xF0, "dl_ar")
    a.abs(0xB9, ST).abs(0x20, "dl18").br(0xB0, "dl_ar").b(0xA2, a15).abs(0x20, "dswap")
    a.label("dl_a")
    # the gated screens: a dungeon or shrine
    a.abs(0x20, "dgcnt").br(0xD0, "dl_g")
    a.label("dl_gr").abs(0x20, "drnd").b(0x29, 0x07, 0xC9, 0x06).br(0xB0, "dl_gr").b(0xAA).abs(0xBD, "dgate").abs(0x8D, D_G)
    a.label("dl_gr2").abs(0x20, "drnd").b(0x29, 0x7F, 0xC9, N).br(0xB0, "dl_gr2").b(0xA8).abs(0x20, "dgin").br(0xB0, "dl_gr2")
    a.abs(0xB9, ST).abs(0x20, "dldun").br(0x90, "dl_gr2").abs(0xAE, D_G).abs(0x20, "dswap")
    a.label("dl_g")
    # and an upgrade cave
    a.b(0xA2, 0x05)
    a.label("dl_u1").abs(0xBC, "dgate").abs(0xB9, ST).abs(0x20, "dlup").br(0xB0, "dl_u").b(0xCA).br(0x10, "dl_u1")
    a.abs(0x20, "dgcnt").abs(0x8D, D_F)
    a.label("dl_ur").abs(0x20, "drnd").b(0x29, 0x07, 0xC9, 0x06).br(0xB0, "dl_ur").b(0xAA).abs(0xBC, "dgate")
    a.abs(0xB9, ST).abs(0x20, "dldun").br(0x90, "dl_ug").abs(0xAD, D_F).b(0xC9, 0x02).br(0x90, "dl_ur")
    a.label("dl_ug").abs(0x8C, D_G)
    a.label("dl_ur2").abs(0x20, "drnd").b(0x29, 0x7F, 0xC9, N).br(0xB0, "dl_ur2").b(0xA8, 0xC0, a15).br(0xF0, "dl_ur2")
    a.abs(0x20, "dgin").br(0xB0, "dl_ur2").abs(0xB9, ST).abs(0x20, "dlup").br(0x90, "dl_ur2")
    a.abs(0xAE, D_G).abs(0x20, "dswap")
    a.label("dl_u").b(0x60)
    # helpers
    a.label("dswap").abs(0xBD, ST).b(0x48).abs(0xB9, ST).abs(0x9D, ST).b(0x68).abs(0x99, ST).b(0x60)
    a.label("dl18").b(0xC9, 0x01).br(0x90, "dl18n").b(0xC9, 0x09).br(0xB0, "dl18n").b(0x38, 0x60)
    a.label("dl18n").b(0x18, 0x60)
    a.label("dldun").b(0xC9, 0x01).br(0x90, "dl18n").b(0xC9, 0x0E).br(0xB0, "dl18n").b(0x38, 0x60)
    a.label("dlup").b(0xC9, E.UPGRADES[0]).br(0xF0, "dlupy").b(0xC9, E.UPGRADES[1]).br(0xF0, "dlupy")
    a.b(0xC9, E.UPGRADES[2]).br(0xF0, "dlupy").b(0x18, 0x60)
    a.label("dlupy").b(0x38, 0x60)
    a.label("dgin").b(0xA2, 0x05).label("dgi").b(0x98).abs(0xDD, "dgate").br(0xF0, "dgy").b(0xCA).br(0x10, "dgi")
    a.b(0x18, 0x60)
    a.label("dgy").b(0x38, 0x60)
    a.label("dgcnt").b(0xA9, 0x00).abs(0x8D, D_F).b(0xA2, 0x05)
    a.label("dgc").abs(0xBC, "dgate").abs(0xB9, ST).abs(0x20, "dldun").br(0x90, "dgcn").abs(0xEE, D_F)
    a.label("dgcn").b(0xCA).br(0x10, "dgc").abs(0xAD, D_F).b(0x60)
    # drnd: lol_entrances' rnd (the same state, $7FA0)
    a.label("drnd").abs(0xAD, RNG + 1).b(0x4A).abs(0xAD, RNG).b(0x6A).abs(0x4D, RNG + 1).abs(0x8D, RNG + 1)
    a.b(0x6A).abs(0x4D, RNG).abs(0x8D, RNG).abs(0x4D, RNG + 1).abs(0x8D, RNG + 1).b(0x60)
    a.label("dct").b(*cont)
    a.label("dmask").b(*[(1 << max(1, i.bit_length())) - 1 for i in range(N)])
    a.label("dgate").b(*gated)


def decoder(groups, ptr_table, maps, info):
    """DECODE (each data bank). In: $08 = variant index, $09 seed, $0A group, $0B boss, $0E slot code, $0F design.
    Writes the rooms, the level info (start, triforce, boss, cellars, item positions, room flags, map).
    Out: $03 old man, $04/$05 stairs rooms, $06/$07 cellars, $08 level 1 / 2's floor item room ($FF none)."""
    S_N, S_CLS, S_POS, S_LAY, S_T, S_CNT, S_X, S_HI, S_R, S_BX, L1, L2, L3, S_RT, S_G = range(SCR, SCR + 15)
    P = 0x0C                                                                  # pointer $0C/$0D
    a = Asm(DECODE)
    a.abs(0x4C, "decode").abs(0x4C, "quote").abs(0x4C, "deal")
    a.label("decode")
    # the variant (called in bank 8: the tables are there): its address, then its bank (the same code is there)
    a.b(0xA6, 0x08, 0xA5, 0x0D)
    for pg in range(4):
        a.b(0xC9, pg).br(0xD0, f"t_n{pg}")
        a.abs(0xBD, f"vlo{pg}").b(0x85, P).abs(0xBD, f"vhi{pg}").b(0x85, P + 1).abs(0xBD, f"vb{pg}").abs(0x4C, "t_sw")
        a.label(f"t_n{pg}")
    a.label("t_sw").abs(0x20, 0xFFAC)
    a.label("t_go")
    a.b(0xA5, 0x0E, 0x45, 0x0F, 0x49, 0xA5).abs(0x8D, S_HI)                  # the generator's high byte
    a.b(0xA9, 0xFF).abs(0x8D, L1).abs(0x8D, L2).abs(0x8D, L3)
    # the main boss's graphics group (1: Aquamentus / Dodongos / Digdogger; 0: Manhandla / Gleeok / Gohma)
    a.b(0xA9, 0x00).abs(0x8D, S_G).b(0xA5, 0x0B, 0x38, 0xE9, 0x31, 0xC9, 0x15).br(0xB0, "bg_x")
    a.b(0xA8).abs(0xB9, "bgrp").abs(0x8D, S_G)
    a.label("bg_x")
    # how many of the other boss rooms keep a boss: levels 1-3 0-1, 4-6 1-2, 7-8 2-4, 9 3-5 Patras, shrines 1
    a.label("bx_r").abs(0x20, "prng").b(0x29, 0x03, 0xA6, 0x0E).abs(0xDD, "bxspan").br(0xB0, "bx_r")
    a.b(0x18).abs(0x7D, "bxmin").abs(0x8D, S_BX)
    # header -> $00-$07 (start, tri, boss, choice, stairs rooms, cellars)
    a.b(0xA0, 0x02, 0xA2, 0x00).label("h").b(0xB1, P, 0x95, 0x00, 0xE8, 0xC8, 0xC0, 10).br(0xD0, "h")
    a.b(0xA2, 0x09, 0xA9, 0xFF).label("cz").abs(0x9D, INFO + 0x34).b(0xCA).br(0x10, "cz")
    a.b(0xA0, 10, 0xB1, P).abs(0x8D, S_T).br(0xF0, "c_no").b(0xA2, 0x00)
    a.label("cl").b(0xC8, 0xB1, P).abs(0x9D, INFO + 0x34).b(0xE8).abs(0xEC, S_T).br(0xD0, "cl")
    a.label("c_no").b(0xA0, 0x00, 0xB1, P).abs(0x8D, S_N).b(0xC8, 0xB1, P).abs(0x8D, S_X)   # counts
    a.abs(0xAD, S_T).b(0x18, 0x69, 11, 0x65, P, 0x85, P).br(0x90, "rg0").b(0xE6, P + 1)   # pointer -> the rooms
    a.label("rg0").abs(0xAD, S_N).br(0xD0, "rg").abs(0x4C, "lits")
    # ordinary rooms (5 bytes)
    a.label("rg").b(0xA0, 0x00, 0xB1, P, 0xAA, 0xC8)                         # X = cell
    a.b(0xB1, P, 0x48, 0x29, 0x03).abs(0x8D, S_CLS).b(0x68, 0x29, 0xFC, 0x09, 0x02).abs(0x9D, ATTR[0]).b(0xC8)
    a.b(0xB1, P, 0x48, 0x29, 0x03).abs(0x8D, S_POS).b(0x68, 0x29, 0xFC, 0x09, 0x02).abs(0x9D, ATTR[1]).b(0xC8)
    a.b(0xB1, P).abs(0x8D, S_LAY).b(0xC8)
    a.b(0xB1, P, 0x48, 0x4A, 0x4A, 0x4A).abs(0x9D, ATTR[4])
    a.abs(0xAD, S_POS).b(0x0A, 0x0A, 0x0A, 0x0A).abs(0x8D, S_T).b(0x68, 0x29, 0x07).abs(0x0D, S_T).abs(0x9D, ATTR[5])
    a.label("ir_no")
    a.abs(0xAD, S_CLS).br(0xD0, "en")
    a.b(0xA9, 0x00).abs(0x9D, ATTR[2]).abs(0xAD, S_LAY).abs(0x9D, ATTR[3]).abs(0x4C, "rg_nx")
    a.label("en").b(0xC9, 0x03).br(0xD0, "en_reg").b(0xE4, 0x02).br(0xF0, "en_bs")      # the main boss
    a.abs(0xAD, S_BX).br(0xF0, "en_dem").abs(0xCE, S_BX)
    a.label("en_bs").b(0xA5, 0x0E, 0xC9, 0x09).br(0xD0, "en_b1")
    a.abs(0x20, "prng").b(0x29, 0x01, 0x18, 0x69, 0x47).br(0xD0, "en_b2")              # level 9: a Patra
    # any boss of the group that fits this room's layout
    a.label("en_b1").abs(0xAD, S_LAY).b(0x29, 0x3F, 0xA8).abs(0xB9, "blrow").br(0xF0, "en_b0")
    a.b(0x0A).abs(0x0D, S_G).b(0xA8).abs(0xB9, "blen").br(0xF0, "en_b0").abs(0x8D, S_T)
    a.label("en_br").abs(0x20, "prng").b(0x29, 0x07).abs(0xCD, S_T).br(0xB0, "en_br")
    a.b(0x18).abs(0x79, "bofs").b(0xA8).abs(0xB9, "bfl").br(0xD0, "en_b2")
    a.label("en_b0").b(0xA5, 0x0B)
    a.label("en_b2").abs(0x8D, S_T).b(0xA9, 0x00).abs(0x8D, S_CNT)
    a.abs(0x4C, "en_put")
    a.label("en_dem").b(0xA9, 0x01).abs(0x8D, S_CLS)                                  # an ordinary room after all
    # an ordinary room's enemies: any of the group's (vanilla rooms', each kind once), not one of the last 3 picked
    a.label("en_reg").b(0xA9, 12).abs(0x8D, S_RT)
    a.label("en_rt").abs(0x20, "prng").b(0x29, 0x3F)
    a.b(0xA4, 0x0A).abs(0xD9, "glen").br(0xB0, "en_rt")
    a.b(0x18).abs(0x79, "gofs").b(0xA8)
    a.abs(0xAD, S_CLS).b(0xC9, 0x02).br(0xD0, "en_ok").abs(0xB9, "gtrap").br(0xD0, "en_rt")
    a.label("en_ok").abs(0xCE, S_RT).br(0xF0, "en_acc")
    a.abs(0xB9, "gid").abs(0xCD, L1).br(0xF0, "en_rt").abs(0xCD, L2).br(0xF0, "en_rt").abs(0xCD, L3).br(0xF0, "en_rt")
    a.label("en_acc").abs(0xAD, L2).abs(0x8D, L3).abs(0xAD, L1).abs(0x8D, L2).abs(0xB9, "gid").abs(0x8D, L1)
    a.abs(0xB9, "gcnt").abs(0x8D, S_CNT).abs(0xB9, "gid").abs(0x8D, S_T)
    a.label("en_put").abs(0xAD, S_T).b(0x29, 0x3F).abs(0x0D, S_CNT).abs(0x9D, ATTR[2])
    a.abs(0xAD, S_T).b(0xC9, 0x40, 0xA9, 0x00, 0x6A).abs(0x0D, S_LAY).abs(0x9D, ATTR[3])
    a.label("rg_nx").b(0xA5, P, 0x18, 0x69, 0x05, 0x85, P).br(0x90, "rg_n2").b(0xE6, P + 1)
    a.label("rg_n2").abs(0xCE, S_N).br(0xF0, "lits").abs(0x4C, "rg")
    # literal rooms (7 bytes)
    a.label("lits").abs(0xAD, S_X).br(0xF0, "info")
    a.label("lt").b(0xA0, 0x00, 0xB1, P, 0xAA, 0xC8)
    for t in range(6):
        a.b(0xB1, P).abs(0x9D, ATTR[t]).b(0xC8)
    a.b(0xA5, P, 0x18, 0x69, 0x07, 0x85, P).br(0x90, "lt2").b(0xE6, P + 1)
    a.label("lt2").abs(0xCE, S_X).br(0xD0, "lt")
    # the level info
    a.label("info").b(0xA5, 0x00).abs(0x8D, INFO + 0x2F).b(0xA5, 0x01).abs(0x8D, INFO + 0x30)
    a.b(0xA5, 0x02).abs(0x8D, INFO + 0x3E)
    a.b(0xA2, 0x03).label("ip").abs(0xBD, "postab").abs(0x9D, INFO + 0x29).b(0xCA).br(0x10, "ip")
    a.b(0xA6, 0x0F).abs(0xBD, "flo").abs(0x8D, INFO + 0x31).abs(0xBD, "fhi").abs(0x8D, INFO + 0x32)
    a.b(0xA5, 0x0F, 0x0A, 0xAA).abs(0xBD, "mtab").b(0x85, P).abs(0xBD, "mtab1").b(0x85, P + 1)
    a.b(0xA0, 0x00, 0xB1, P).abs(0x8D, INFO + 0x2D).b(0xC8, 0xB1, P).abs(0x8D, INFO + 0x2E)
    a.b(0xA2, 0x00).label("mp").b(0xC8, 0xB1, P).abs(0x9D, INFO + 0x3F).b(0xE8, 0xE0, 16 + 45).br(0xD0, "mp")
    # the items (the generator marked the rooms that may hold one: $10 | 1 center usable | 2 standing only):
    # levels 1-8 the triforce (a center room), then the map, the compass, levels 1-8 the blue potion, levels 1-2
    # the floor item (a key here: the reward hook swaps it), then every other marked room: 25% nothing, else DROPS
    # (40% key, 25% bombs, 20% five rupees, 1% blue potion, 14% nothing). Each: 75% dropped when all its enemies are
    # dead, 25% on the floor (a room with no enemies: on the floor).
    a.b(0xA9, 0xFF, 0x85, 0x08, 0xA9, 0x00).abs(0x8D, S_POS)
    a.b(0xA5, 0x0E, 0xC9, 0x09).br(0xB0, "pl_nt")
    a.b(0xA9, 0x1D).abs(0x8D, S_T).b(0xA9, 0x11).abs(0x8D, S_CNT).abs(0x20, "pl_pick").b(0xE0, 0xFF).br(0xF0, "pl_nt")
    a.abs(0x8E, INFO + 0x30).b(0xA9, 0x01).abs(0x8D, S_POS).b(0xA9, G.I_TRIFORCE).abs(0x20, "pl_put")
    a.label("pl_nt").b(0xA9, 0x00).abs(0x8D, S_POS)
    for it, cond in ((G.I_MAP, None), (G.I_COMPASS, None), (G.I_BLUE_POTION, "18"), (0x19, "12")):
        lab = f"pl_{it:02x}"
        if cond == "18":
            a.b(0xA5, 0x0E, 0xC9, 0x09).br(0xB0, lab)
        elif cond == "12":                # the floor item: levels 1-2, and a quest's levels with a floor major item
            a.b(0xA6, 0x0E).abs(0xBD, "flr").br(0xF0, lab)
        a.b(0xA9, 0x1C).abs(0x8D, S_T).b(0xA9, 0x10).abs(0x8D, S_CNT).abs(0x20, "pl_pick").b(0xE0, 0xFF).br(0xF0, lab)
        if cond == "12":
            a.b(0x86, 0x08)
        a.b(0xA9, it).abs(0x20, "pl_put")
        a.label(lab)
    a.abs(0x20, "cl_ptr").b(0xA0, 0x01)
    a.label("pr_l").b(0xB1, P, 0xAA).abs(0xBD, ATTR[4]).b(0x29, 0x1C, 0xC9, 0x10).br(0xF0, "pr_y").abs(0x4C, "px_n")
    a.label("pr_y")
    a.b(0x98, 0x48).abs(0x20, "prng").b(0xC9, DROP_EMPTY).br(0x90, "pr_no")
    a.abs(0x20, "prng").b(0xA0, 0x00)
    a.label("pr_t").abs(0xD9, "rthr").br(0x90, "pr_it").b(0xC8, 0xC0, len(DROPS)).br(0xD0, "pr_t")
    a.label("pr_no").b(0xA9, 0x03).abs(0x9D, ATTR[4]).br(0xD0, "pr_d")
    a.label("pr_it").abs(0xB9, "rtab").abs(0x20, "pl_put")
    a.label("pr_d").b(0x68, 0xA8)
    a.label("px_n").b(0xC8).abs(0xCC, S_N).br(0xF0, "pr_x").abs(0x4C, "pr_l")
    a.label("pr_x")
    # level 9: the boss roar only in the rooms beside Ganon's
    a.b(0xA5, 0x0E, 0xC9, 0x09).br(0xD0, "ro_x")
    a.b(0xA5, 0x02, 0xC9, 0x10).br(0x90, "ro_1").b(0xE9, 0x10).abs(0x20, "roar")
    a.label("ro_1").b(0xA5, 0x02, 0xC9, 0x70).br(0xB0, "ro_2").b(0x69, 0x10).abs(0x20, "roar")
    a.label("ro_2").b(0xA5, 0x02, 0x29, 0x0F).br(0xF0, "ro_3").b(0xA5, 0x02, 0x38, 0xE9, 0x01).abs(0x20, "roar")
    a.label("ro_3").b(0xA5, 0x02, 0x29, 0x0F, 0xC9, 0x0F).br(0xF0, "ro_x").b(0xA5, 0x02, 0x18, 0x69, 0x01)
    a.abs(0x20, "roar")
    a.label("ro_x")
    # level 2: its stairs room's push block reveals nothing (the floor item instead of the cellar)
    a.b(0xA5, 0x0E, 0xC9, 0x02).br(0xD0, "l2_x").b(0xA6, 0x04, 0xE0, 0xFF).br(0xF0, "l2_x")
    a.abs(0xBD, ATTR[5]).b(0x29, 0xF8).abs(0x9D, ATTR[5])               # no stairs: a plain block, no trigger
    a.abs(0xBD, ATTR[3]).b(0x29, 0xBF).abs(0x9D, ATTR[3])
    a.label("l2_x").b(0x60)
    # cl_ptr: P = this design's cell list, S_N = its count + 1 (Y = 0)
    a.label("cl_ptr").b(0xA5, 0x0F, 0x0A, 0xA8).abs(0xB9, "cltab").b(0x85, P).abs(0xB9, "cltab1").b(0x85, P + 1)
    a.b(0xA0, 0x00, 0xB1, P, 0x18, 0x69, 0x01).abs(0x8D, S_N).b(0x60)
    # pl_pick: X = a random cell of the design whose ATTR E & S_T = S_CNT ($FF: none)
    a.label("pl_pick").abs(0x20, "cl_ptr").b(0xA9, 0x00).abs(0x8D, S_X).b(0xA0, 0x01)
    a.label("pk_c").b(0xB1, P, 0xAA).abs(0xBD, ATTR[4]).abs(0x2D, S_T).abs(0xCD, S_CNT).br(0xD0, "pk_cn")
    a.abs(0xEE, S_X)
    a.label("pk_cn").b(0xC8).abs(0xCC, S_N).br(0xD0, "pk_c")
    a.abs(0xAD, S_X).br(0xD0, "pk_r").b(0xA2, 0xFF, 0x60)
    a.label("pk_r").abs(0x20, "prng").b(0x29, 0x3F).abs(0xCD, S_X).br(0xB0, "pk_r").abs(0x8D, S_CLS)
    a.b(0xA0, 0x01)
    a.label("pk_w").b(0xB1, P, 0xAA).abs(0xBD, ATTR[4]).abs(0x2D, S_T).abs(0xCD, S_CNT).br(0xD0, "pk_wn")
    a.abs(0xAD, S_CLS).br(0xF0, "pk_f").abs(0xCE, S_CLS)
    a.label("pk_wn").b(0xC8).br(0xD0, "pk_w")
    a.label("pk_f").b(0x60)
    # pl_put: item A into cell X (S_POS 1: at the center); 75% dropped (25% floor) unless standing only
    a.label("pl_put").abs(0x8D, S_LAY).abs(0xBD, ATTR[4]).abs(0x8D, S_RT).abs(0xAD, S_LAY).abs(0x9D, ATTR[4])
    a.abs(0xAD, S_POS).br(0xF0, "pp1").abs(0xBD, ATTR[5]).b(0x29, 0xCF).abs(0x9D, ATTR[5])
    a.label("pp1").abs(0xAD, S_RT).b(0x29, 0x02).br(0xD0, "pp_x")
    a.abs(0xBD, ATTR[5]).b(0x29, 0x07).br(0xF0, "pp_g").b(0xC9, 0x01).br(0xF0, "pp_g").b(0xC9, 0x07).br(0xD0, "pp_x")
    a.label("pp_g").abs(0x20, "prng").b(0x29, 0x03).br(0xF0, "pp_x")
    a.abs(0xBD, ATTR[5]).b(0x29, 0xF8, 0x09, 0x07).abs(0x9D, ATTR[5])
    a.label("pp_x").b(0x60)
    cum, thr = 0, []
    for _, w in DROPS:
        cum += w
        thr.append(round(cum * 256 / 100))
    assert thr[-1] < 256 and len(set(thr)) == len(thr)
    a.label("rthr").b(*thr)                                # (A at or past the last: nothing)
    a.label("rtab").b(*[it for it, _ in DROPS])
    # mine: C = 1 if cell X is one of this dungeon's (an ordinary room: walk the variant again)
    a.label("mine").b(0x8A).abs(0x8D, S_LAY)
    a.b(0xA4, 0x08) if False else None
    a.abs(0xAD, "cellsN").b(0x60) if False else None
    a.label("mine2").b(0xA5, 0x0F, 0x0A, 0xA8).abs(0xB9, "cltab").b(0x85, P).abs(0xB9, "cltab1").b(0x85, P + 1)
    a.b(0xA0, 0x00, 0xB1, P).abs(0x8D, S_POS)
    a.label("mi").b(0xC8, 0xB1, P).abs(0xCD, S_LAY).br(0xF0, "mi_y").abs(0xCE, S_POS).br(0xD0, "mi")
    a.b(0xAE, S_LAY & 0xFF, S_LAY >> 8, 0x18, 0x60)
    a.label("mi_y").b(0xAE, S_LAY & 0xFF, S_LAY >> 8, 0x38, 0x60)
    # prng: a 16-bit LFSR ($09 low, S_HI high), 8 steps a call; A = the low byte (X, Y kept)
    a.label("prng").b(0xA9, 0x08).abs(0x8D, S_R)
    a.label("pr").abs(0x4E, S_HI).b(0x66, 0x09).br(0x90, "pr_n").abs(0xAD, S_HI).b(0x49, 0xB4).abs(0x8D, S_HI)
    a.label("pr_n").abs(0xCE, S_R).br(0xD0, "pr").b(0xA5, 0x09, 0x60)
    a.label("roar").b(0xAA).abs(0x20, "mine").br(0x90, "rr_n").abs(0xBD, ATTR[4]).b(0x29, 0x9F, 0x09, 0x20)
    a.abs(0x9D, ATTR[4])
    a.label("rr_n").b(0x60)
    a.label("bxmin").b(0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 1, 1, 1, 1, 1, 1)
    a.label("bxspan").b(1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 1, 1, 1, 1, 1, 1)
    # bosses: group 1 (Aquamentus, Dodongos, Digdogger) or 0 (Manhandla, Gleeok, Gohma); per boss layout, the ones
    # of each group it can hold
    GA = {0x3D, 0x31, 0x32, 0x38, 0x39}
    a.label("bgrp").b(*[1 if 0x31 + i in GA else 0 for i in range(0x15)])
    lays = sorted(G.BOSS_OF)
    row = [0] * 64
    for k, L in enumerate(lays):
        row[L] = k + 1
    a.label("blrow").b(*row)
    blen, bofs, bfl = [0, 0], [0, 0], []
    for L in lays:
        for grp in (0, 1):
            lst = [b for b in G.BOSS_OF[L] if (b in GA) == bool(grp)]
            assert len(lst) <= 8
            bofs.append(len(bfl)); blen.append(len(lst)); bfl += lst
    a.label("blen").b(*blen)
    a.label("bofs").b(*bofs)
    a.label("bfl").b(*bfl)
    # shq: Y = 1 if attribute byte A has a shutter (7) in its top or middle field
    a.label("shq").b(0x48, 0x29, 0xE0, 0xC9, 0xE0).br(0xD0, "sq1").b(0xA0, 0x01)
    a.label("sq1").b(0x68, 0x29, 0x1C, 0xC9, 0x1C).br(0xD0, "sq2").b(0xA0, 0x01)
    a.label("sq2").b(0x60)
    glen, gofs, gid, gcnt, gtrap = [], [], [], [], []
    for ent in groups:
        gofs.append(len(gid)); glen.append(min(64, len(ent)))
        for m, cidx, trap in ent[:64]:
            gid.append(m); gcnt.append(cidx << 6); gtrap.append(1 if trap else 0)
    assert len(gid) < 256
    a.label("glen").b(*glen)
    a.label("gofs").b(*gofs)
    a.label("gid").b(*gid)
    a.label("gcnt").b(*gcnt)
    a.label("gtrap").b(*gtrap)
    a.label("postab").b(*G.POS_TABLE)
    fl = floor_levels()                   # the levels that get a floor badge / XP, by slot code $0E
    a.label("flr").b(*[1 if i in fl else 0 for i in range(16)])
    ds, _ = build_variants()
    a.label("flo").b(*[flags_of(i, ds) & 0xFF for i in range(len(ds))])
    a.label("fhi").b(*[flags_of(i, ds) >> 8 for i in range(len(ds))])
    # maps (start, cursor, 16 mask, 45 status bar) and the design's cells
    a.label("mtab").b(*([0] * (2 * len(ds))))
    a.labels["mtab1"] = a.labels["mtab"] + 1
    a.label("cltab").b(*([0] * (2 * len(ds))))
    a.labels["cltab1"] = a.labels["cltab"] + 1
    a.label("maps")
    for m in maps:
        a.b(*m)
    a.label("cells")
    for d in ds:
        a.b(len(d[3]), *d[3])
    # ---- bank 8 only from here (the quote, the deal and the variant table: used only in bank 8; the other data
    # banks hold variants here) ----
    a.label("b8only")
    # quote: copy hint quote $00 to the hint old man's text buffer
    a.label("quote").b(0xA6, 0x00).abs(0xBD, "qlo").b(0x48).abs(0xBD, "qhi").b(0x85, 0x01, 0x68, 0x85, 0x00)
    a.b(0xA0, 0x00).label("qc").b(0xB1, 0x00).abs(0x99, HINT_BUF).b(0xC8, 0xC0, 80).br(0xD0, "qc").b(0x60)
    deal_code(a, info)
    for pg in range(4):
        t = ptr_table[256 * pg:256 * pg + 256]
        a.label(f"vlo{pg}").b(*[p_ & 0xFF for _, p_ in t])
        a.label(f"vhi{pg}").b(*[p_ >> 8 for _, p_ in t])
        a.label(f"vb{pg}").b(*[b_ for b_, _ in t])
    qs = hint_quotes()
    a.label("qlo").b(*([0] * len(qs)))
    a.label("qhi").b(*([0] * len(qs)))
    a.label("quotes")
    for q in qs:
        a.b(*q)
    a.b(*([0] * 80))                           # (the last quote's copy stays in the bank)
    code = bytearray(a.bytes())
    pos = a.labels["quotes"]
    for i, q in enumerate(qs):
        code[a.labels["qlo"] - DECODE + i], code[a.labels["qhi"] - DECODE + i] = pos & 0xFF, pos >> 8
        pos += len(q)
    mt, ct = a.labels["mtab"] - DECODE, a.labels["cltab"] - DECODE
    pos = a.labels["maps"]
    for i, m in enumerate(maps):
        code[mt + 2 * i], code[mt + 2 * i + 1] = pos & 0xFF, pos >> 8; pos += len(m)
    pos = a.labels["cells"]
    for i, d in enumerate(ds):
        code[ct + 2 * i], code[ct + 2 * i + 1] = pos & 0xFF, pos >> 8; pos += 1 + len(d[3])
    decoder.common = a.labels["b8only"] - DECODE
    return bytes(code)


HINTS_FILE = lolpaths.HINTS_FILE
from lol_saveblock import HINT_BUF      # the hint old man's text (scratch past the play area's tiles)
HINT_QS = 0x7F48                        # per entrance: its quote + 1 (test: file 2's entrance store)
TRAMPQ = 0xBB80                         # bank 6 and the data banks: copy a quote
# the two quotes too long for 3 lines of 22, shortened
HINT_SHORT = {"THE BOOK WILL TEACH YOU HOW TO DEAL MORE DAMAGE WITH ALL WEAPONS":
              "THE BOOK TEACHES YOU TO DEAL MORE DAMAGE WITH ALL WEAPONS",
              "LEVELS 1-8 ALL HAVE AN OLD MAN AND A STAIRCASE ITEM, SEEK THEM":
              "LEVELS 1-8 HIDE AN OLD MAN AND A STAIRCASE ITEM, SEEK THEM"}


def hint_quotes():
    """The user's hint quotes, encoded (centred, up to 3 lines)."""
    import re, textwrap
    from zora.rom.serialize.text import _encode_quote
    out = []
    for l in open(HINTS_FILE):
        m = re.match(r"(\d+)\. (.*)", l.strip())
        if not m:
            continue
        t = m.group(2).split("   (shown:")[0].split("   (was:")[0].split("   [")[0].replace("Gannon", "Ganon").upper()
        t = HINT_SHORT.get(t, t)
        w = textwrap.wrap(t, 22)                 # the old man's box: 3 lines of 22
        assert len(w) <= 3, t
        w = [" " * ((22 - len(x)) // 2) + x for x in w]
        b = bytes(_encode_quote("|".join(w), center=False))
        assert len(b) <= 80, t
        out.append(b)                            # (stored back to back: the copy's 80 bytes run on harmlessly)
    return out


# conditional quotes ("[only with ...]" in the hints file): (inventory byte - $0600, the least it must hold)
HINT_CONDS = {"the magical boomerang": (0x75, 1), "the magical shield": (0x76, 1),
              "16 heart containers": (0x6F, 0xF0), "20 max bombs": (0x7C, 20),
              "level 10": (0x016F, 0x90)}      # (a full address: lol_build's HVE, the containers enemies see)


def hint_conds():
    """Each quote's condition, in hint_quotes' order: (address, mask, least): offered while (byte & mask) >= least.
    Inventory ones: $06xx, mask $FF; upgrades: the upgrade's owned bit; always: mask 0."""
    import re
    import lol_uptable as T
    out = []
    for l in open(HINTS_FILE):
        m = re.match(r"(\d+)\. (.*)", l.strip())
        if not m:
            continue
        c = re.search(r"\[only with (.*)\]", m.group(2))
        if not c:
            out.append((0x0600, 0, 0))
        elif c.group(1).startswith("the upgrade "):
            addr, bit = T.bit(c.group(1)[len("the upgrade "):])
            out.append((addr, bit, bit))
        else:
            off, least = HINT_CONDS[c.group(1)]
            out.append((off if off > 0xFF else 0x0600 + off, 0xFF, least))
    return out


def vindex(d, ci, v):
    """The variant tables' index (two pages: classes 0-3, 4-5)."""
    return (ci >> 2) * 256 + (ci & 3) * 64 + d * K + v


def expand(rom: bytearray) -> None:
    """128KB -> 256KB: 8 more banks (bank 7, the fixed one, is copied to bank 15 at the end: finish)."""
    if len(rom) == 16 + 8 * 0x4000:
        rom.extend(b"\xFF" * (8 * 0x4000))
        rom[4] = 16


def finish(rom: bytearray) -> None:
    rom[BANK(15):BANK(15) + 0x4000] = rom[BANK(7):BANK(7) + 0x4000]


def apply(rom: bytearray, notes: list) -> None:
    expand(rom)
    ds, out = build_variants()
    from zora.generate.shapes.minimap import synthesize_minimap
    groups = enemy_groups()
    nd = len(ds)
    maps = []
    for d in ds:
        md, cmds, start, cur = synthesize_minimap(set(d[3]))
        maps.append(bytes([start, cur]) + bytes(md) + bytes(cmds) + b"\xff" * (45 - len(cmds)))
    # place the variants (pass 1: sizes with a dummy decoder; pass 2: real)
    bodies = {}
    for key in sorted(out):
        for v, var in enumerate(out[key]):
            bodies[key + (v,)] = encode_variant(var, ds[key[0]][0])
    info = deal_info(rom)
    dummy = decoder(groups, [(8, 0)] * 1024, maps, info)
    common = decoder.common
    start = DECODE + common + 0x10                  # banks 9-14: after the shared part
    fill = {b: start for b in DATA_BANKS}
    fill[8] = DECODE + len(dummy) + 0x10            # bank 8: after its tail too
    ptr = {}
    for key in sorted(bodies):
        body = bodies[key]
        for b in DATA_BANKS:
            if fill[b] + len(body) <= TRAMPD - 0x10:
                ptr[key] = (b, fill[b]); fill[b] += len(body)
                break
        else:
            raise RuntimeError("variants don't fit")
    assert nd * K <= 64
    table = [(8, 0)] * 1024
    for d in range(nd):
        for ci in range(NC):
            for v in range(K):
                table[vindex(d, ci, v)] = ptr.get((d, ci, v), ptr.get((d, ci, 0), (8, 0)))
    dec = decoder(groups, table, maps, info)
    assert len(dec) == len(dummy)
    tramp = bytes([0x20, 0xAC, 0xFF, 0x20, DECODE & 0xFF, DECODE >> 8, 0xA9, 0x06, 0x4C, 0xAC, 0xFF])
    trampq = bytes([0x20, 0xAC, 0xFF, 0x20, (DECODE + 3) & 0xFF, (DECODE + 3) >> 8, 0xA9, 0x06, 0x4C, 0xAC, 0xFF])
    trampd = bytes([0x20, 0xAC, 0xFF, 0x20, (DECODE + 6) & 0xFF, (DECODE + 6) >> 8, 0xA9, 0x06, 0x4C, 0xAC, 0xFF])
    for b in DATA_BANKS:
        place(rom, b, DECODE, dec if b == 8 else dec[:common])
        place(rom, b, TRAMP, tramp)
        place(rom, b, TRAMPQ, trampq)
        place(rom, b, TRAMPD, trampd)
    place(rom, 6, TRAMPQ, trampq)
    place(rom, 6, TRAMPD, trampd)
    # the hint old man's text (cave 5's selector $06 in PersonTextAddrs, bank 1 $8000): the buffer
    t = BANK(1) + 0x0006
    rom[t:t + 2] = bytes([HINT_BUF & 0xFF, HINT_BUF >> 8])
    for key, (b, p) in ptr.items():
        place(rom, b, p, bodies[key])
    place(rom, 6, TRAMP, tramp)
    used = {b: fill[b] - DECODE for b in DATA_BANKS}
    notes.append("v2 data banks used: " + ", ".join(f"{b}: {used[b]}" for b in DATA_BANKS))

    # ---------------- bank 6: the load hook (palette, SUB / CHOICE) ----------------
    B6 = BANK(6) + TRAMPD - 0x8000
    while rom[B6 - 1] == 0xFF:
        B6 -= 1
    B6 = B6 - BANK(6) + 0x8000 + 0x10
    a = Asm(B6)
    a.label("full").b(0xA4, 0x16).abs(0xB9, 0x062D).abs(0x4C, 0x810E)      # the vanilla start (JMP'd over)
    a.label("newfull").abs(0x20, "full")
    a.b(0xA9, 0xFF).abs(0x8D, CUR_GEN).abs(0x8D, GEN_CHOICE).abs(0x8D, SUB_RM).abs(0x8D, SUB_RM + 1)
    a.b(0xA5, 0x10).br(0xD0, "nf_lv").b(0x60)
    a.label("nf_lv")
    for z in range(0x00, 0x10):
        a.b(0xA5, z, 0x48)
    a.abs(0x20, "find").br(0xB0, "nf_go").abs(0x4C, "nf_end")              # Y = the record, $0E slot
    a.label("nf_go").abs(0xB9, REC).b(0x38, 0xE9, 0x01, 0x85, 0x0F).abs(0x8D, CUR_GEN)   # $0F = design
    # palette: from the first-quest level (bits 4-7) + 1: its info bytes $00-$23 and $7C-$FB
    a.abs(0xB9, REC + 1).b(0x4A, 0x4A, 0x4A, 0x29, 0x1E, 0x18, 0x69, 0x02, 0xAA)
    a.abs(0xBD, 0x8014).b(0x85, 0x00).abs(0xBD, 0x8015).b(0x85, 0x01)
    a.b(0x98, 0x48, 0xA0, 0x00).label("p1").b(0xB1, 0x00).abs(0x99, INFO).b(0xC8, 0xC0, 0x24).br(0xD0, "p1")
    a.b(0xA0, 0x7C).label("p2").b(0xB1, 0x00).abs(0x99, INFO).b(0xC8, 0xC0, 0xFC).br(0xD0, "p2")
    a.b(0x68, 0xA8)
    a.abs(0xB9, REC + 3).b(0xD0, 0x02, 0xA9, 0x01, 0x85, 0x09)              # seed
    a.abs(0xB9, REC + 1).b(0x4A, 0x4A, 0x29, 0x03, 0x85, 0x0A)              # group
    a.abs(0xB9, REC + 2).b(0x85, 0x0B)                                      # boss
    # variant index = (class & 3) * 64 + design * 3 + variant; $0D = class >> 2
    a.b(0xA6, 0x0E).abs(0xBD, "slot_class").b(0x48, 0x4A, 0x4A, 0x85, 0x0D, 0x68, 0x29, 0x03)
    a.b(0x0A, 0x0A, 0x0A, 0x0A, 0x0A, 0x0A, 0x85, 0x08)
    a.b(0xA5, 0x0F, 0x0A, 0x65, 0x0F, 0x65, 0x08, 0x85, 0x08)
    a.abs(0xB9, REC + 1).b(0x29, 0x03, 0x18, 0x65, 0x08, 0x85, 0x08)
    a.b(0x98, 0x48, 0xA9, 0x08).abs(0x20, TRAMP).b(0x68, 0xA8)
    a.b(0xA5, 0x03).abs(0x8D, GEN_CHOICE)
    # cellar items: levels: the record's two; level 9: a red potion and the record's item
    a.abs(0xB9, REC + 4).b(0x85, 0x01)
    a.b(0xA5, 0x0E, 0xC9, 0x09).br(0xD0, "nf_lvi")
    a.b(0xA9, 0x20).abs(0x8D, SUB_IT).b(0xA5, 0x01).abs(0x8D, SUB_IT + 1).br(0xD0, "nf_c")
    a.label("nf_lvi").b(0xA5, 0x01, 0x29, 0x07, 0xAA).abs(0xBD, "citems").abs(0x8D, SUB_IT)
    a.b(0xA5, 0x01, 0x4A, 0x4A, 0x4A, 0x29, 0x07, 0xAA).abs(0xBD, "citems").abs(0x8D, SUB_IT + 1)
    a.b(0xA5, 0x0E, 0xC9, 0x02).br(0xD0, "nf_1")
    a.b(0xA5, 0x08).abs(0x8D, SUB_RM).abs(0x4C, "nf_end")                   # level 2: the floor room
    # levels 1, 3-8: the two items go to the level's cellars, then its floor item room (whichever it has)
    a.label("nf_1").b(0xC9, 0x09).br(0xF0, "nf_c")
    a.b(0xA2, 0x00, 0xA9, 0xFF).abs(0x8D, SUB_RM).abs(0x8D, SUB_RM + 1)
    a.b(0xA5, 0x06).abs(0x20, "nf_add").b(0xA5, 0x07).abs(0x20, "nf_add").b(0xA5, 0x08).abs(0x20, "nf_add")
    a.abs(0x4C, "nf_end")
    a.label("nf_add").b(0xC9, 0xFF).br(0xF0, "na_x").b(0xE0, 0x02).br(0xB0, "na_x").abs(0x9D, SUB_RM).b(0xE8)
    a.label("na_x").b(0x60)
    a.label("nf_c").b(0xA5, 0x06).abs(0x8D, SUB_RM).b(0xA5, 0x07).abs(0x8D, SUB_RM + 1)
    a.label("nf_end")
    for z in reversed(range(0x00, 0x10)):
        a.b(0x68, 0x85, z)
    a.b(0x60)
    # find: C = 1, Y = the record (5 * slot index), $0E = slot code, when this level's slot has a record
    a.label("find").b(0xA5, 0x10).b(0xA4, 0x16).abs(0xBE, 0x062D).br(0xF0, "fd_q1")
    a.b(0xAA).abs(0xBD, "letter")
    a.label("fd_q1").b(0x85, 0x0E, 0xAA).abs(0xBD, "sidx").b(0xC9, 0xFF).br(0xF0, "fd_no")
    a.b(0x85, 0x08, 0x0A, 0x0A, 0x65, 0x08, 0xA8).abs(0xB9, REC).br(0xF0, "fd_no").b(0x38, 0x60)
    a.label("fd_no").b(0x18, 0x60)
    a.label("slot_class").b(*SLOT_CLASS)
    a.label("sidx").b(*SLOT_INDEX)
    a.label("letter").b(0, *[0x0A + AF_LEVELS.index(lv) for lv in range(1, 7)], 0, 0, 0)
    a.label("citems").b(*CELLAR_ITEMS, 0x19, 0x19, 0x19)
    code = a.bytes()
    assert B6 + len(code) <= TRAMPD, hex(B6 + len(code))
    place(rom, 6, B6, code)
    patch(rom, 6, 0x8109, bytes.fromhex("a416b9"), bytes([0x4C, a.labels["newfull"] & 0xFF, a.labels["newfull"] >> 8]))

    # ---------------- bank 3: the enemy and boss pattern sets ----------------
    g = Asm(B3G)
    for which in ("e", "b"):
        g.label(which).b(0x8A, 0x48, 0x98, 0x48, 0xA5, 0x08, 0x48, 0xA5, 0x0E, 0x48)
        g.abs(0x20, "find3").br(0x90, which + "_lv")
        if which == "e":
            g.abs(0xB9, REC + 1).b(0x4A, 0x4A, 0x29, 0x03, 0xAA).abs(0xBD, "elv").abs(0x4C, "out3")
        else:
            g.b(0xA5, 0x0E, 0xC9, 0x09).br(0xD0, "b_n9").b(0xA9, 0x09).br(0xD0, "out3")
            g.label("b_n9").abs(0xB9, REC + 2).b(0xA2, len(BOSS_A) - 1)
            g.label("bb").abs(0xDD, "bossa").br(0xF0, "b_a").b(0xCA).br(0x10, "bb").b(0xA9, 0x03).br(0xD0, "out3")
            g.label("b_a").b(0xA9, 0x01).br(0xD0, "out3")
        g.label(which + "_lv").b(0xA5, 0x10)
        if which == "e":
            g.abs(0x4C, "out3")
        else:
            g.br(0xD0, "out3").b(0xA5, 0x10)
    g.label("out3").b(0x0A).abs(0x8D, SCR + 9)
    g.b(0x68, 0x85, 0x0E, 0x68, 0x85, 0x08, 0x68, 0xA8, 0x68, 0xAA).abs(0xAD, SCR + 9).b(0x60)
    g.label("find3").b(0xA5, 0x10).b(0xA4, 0x16).abs(0xBE, 0x062D).br(0xF0, "f3_q1")
    g.b(0xAA).abs(0xBD, "letter3")
    g.label("f3_q1").b(0x85, 0x0E, 0xAA).abs(0xBD, "sidx3").b(0xC9, 0xFF).br(0xF0, "f3_no")
    g.b(0x85, 0x08, 0x0A, 0x0A, 0x65, 0x08, 0xA8).abs(0xB9, REC).br(0xF0, "f3_no").b(0x38, 0x60)
    g.label("f3_no").b(0x18, 0x60)
    g.label("letter3").b(0, *[0x0A + AF_LEVELS.index(lv) for lv in range(1, 7)], 0, 0, 0)
    g.label("sidx3").b(*SLOT_INDEX)
    g.label("elv").b(*GROUP_LEVEL)
    g.label("bossa").b(*BOSS_A)
    c3 = g.bytes()
    assert B3G + len(c3) <= 0xACFF
    place(rom, 3, B3G, c3)
    sites, k = [], BANK(3)
    while True:
        k = rom.find(bytes.fromhex("a5100aaabd"), k + 1, BANK(3) + 0x4000)
        if k < 0:
            break
        sites.append(k)
    assert len(sites) == 2, [hex(x) for x in sites]
    for x, which in zip(sites, ("e", "b")):
        t = g.labels[which]
        rom[x:x + 3] = bytes([0x20, t & 0xFF, t >> 8])

    # ---------------- bank 5: south out of the start room leaves the level ----------------
    x = Asm(B5X)
    x.label("chk").b(0xA5, 0x10).br(0xF0, "x_no").b(0xA5, 0xE7, 0x29, 0x04).br(0xF0, "x_no")
    x.b(0xA5, 0xEB).abs(0xCD, INFO + 0x2F).br(0xD0, "x_no")
    x.b(0x68, 0x68).abs(0x4C, 0xB547)                                       # EndGameMode12 (leave the level)
    x.label("x_no").b(0x60)
    place(rom, 5, B5X, x.bytes())
    patch(rom, 5, 0xB531, bytes.fromhex("8de404"), bytes([0x20, B5X & 0xFF, B5X >> 8]))
    nv = sum(len(v) for v in out.values())
    notes.append(f"generated dungeons: {nd} designs, {nv} variants; banks 8-14 used " +
                 ", ".join(f"{b}:{used[b]}" for b in DATA_BANKS if used[b]))


def gen_force(a, V_IDX, V_OFF, A15, STORE, N_ENT):
    """lol_entrances' roll (bank 6), label "gen_make": A = the rolled destination. A level 1-9 or shrine A-D gets a
    free design that may take it (keeping enough designs that can be levels 7-8 for those still to come) and its
    record. Returns A = the destination, C = 1; C = 0: no design for it (roll again)."""
    ds, out = build_variants()
    nd = len(ds)
    T0 = 0x0130                           # count, then a list ($0131 ...; stack page, unused)
    masks = [slot_mask(d[2]) for d in ds]
    cap78 = [1 if m & 0x180 else 0 for m in masks]
    # each variant's boss list (an index into the lists; 0 = none)
    blists, bl = [()], [0] * 1024
    for (d, ci), vs in out.items():
        for v, var in enumerate(vs):
            t = tuple(var.get("bosses", ()))
            if t not in blists:
                blists.append(t)
            bl[vindex(d, ci, v)] = blists.index(t)
    # gen_need: A = a dealt destination: a level or shrine without a record gets one now (gen_make)
    a.label("gen_need").b(0xC9, 0x0E).br(0xB0, "gn_x").b(0xC9, 0x01).br(0x90, "gn_x")
    a.b(0x48).abs(0x20, "gf_slotrec").b(0x68).abs(0xBE, REC).br(0xD0, "gn_x").abs(0x4C, "gen_make")
    a.label("gn_x").b(0x60)
    a.label("gen_make").b(0xC9, 0x0E).br(0xB0, "gm_any").b(0xC9, 0x01).br(0xB0, "gm_go")
    a.label("gm_any").b(0x38, 0x60)                                                     # not a dungeon
    a.label("gm_go").abs(0x8D, SCR + 11).b(0xA5, 0x0E, 0x48, 0xA5, 0x0F, 0x48)
    a.abs(0xAD, SCR + 11).b(0x85, 0x0E).abs(0x20, "gf_body")
    a.abs(0x8D, SCR + 15).b(0x08, 0x68).abs(0x8D, SCR + 11)
    a.b(0x68, 0x85, 0x0F, 0x68, 0x85, 0x0E).abs(0xAD, SCR + 11).b(0x48).abs(0xAD, SCR + 15).b(0x28, 0x60)
    # a free design allowed for it (first without the designs levels 7-8 still need, if they're scarce)
    a.label("gf_body")
    a.b(0xA9, 0x00).abs(0x8D, SCR + 10)                                                 # scarce = 0
    a.b(0xA5, 0x0E, 0xC9, 0x07).br(0xF0, "gf_sc").b(0xC9, 0x08).br(0xF0, "gf_sc")
    a.b(0xA9, 0x00).abs(0x8D, T0)                                                       # still to come: 7, 8
    for lv in (7, 8):
        a.b(0xA9, lv).abs(0x20, "gf_slotrec").abs(0xB9, REC).br(0xD0, f"gf_h{lv}").abs(0xEE, T0)
        a.label(f"gf_h{lv}")
    a.b(0xA5, 0x0E, 0x48, 0xA9, 0x07, 0x85, 0x0E)                                       # free designs for 7
    a.b(0xA9, 0x00).abs(0x8D, T0 + 1).b(0xA2, nd - 1)
    a.label("gf_c7").abs(0x20, "gf_okd").br(0x90, "gf_c7n").abs(0xEE, T0 + 1)
    a.label("gf_c7n").b(0xCA).br(0x10, "gf_c7")
    a.b(0x68, 0x85, 0x0E)
    a.abs(0xAD, T0).br(0xF0, "gf_sc").abs(0xCD, T0 + 1).br(0x90, "gf_sc")              # needed >= free: scarce
    a.b(0xA9, 0x01).abs(0x8D, SCR + 10)
    a.label("gf_sc")
    a.label("gf_pass").b(0xA9, 0x00).abs(0x8D, T0).b(0xA2, nd - 1)
    a.label("gf_f").abs(0x20, "gf_okd").br(0x90, "gf_fn")
    a.abs(0xAD, SCR + 10).br(0xF0, "gf_ok").abs(0xBD, "gf_cap").br(0xD0, "gf_fn")
    a.label("gf_ok").b(0x8A).abs(0xAC, T0).abs(0x99, T0 + 1).abs(0xEE, T0)
    a.label("gf_fn").b(0xCA).br(0x10, "gf_f")
    a.abs(0xAD, T0).br(0xD0, "gf_pick")
    a.abs(0xAD, SCR + 10).br(0xF0, "gf_none").b(0xA9, 0x00).abs(0x8D, SCR + 10).abs(0x4C, "gf_pass")
    a.label("gf_none").b(0xA5, 0x0E, 0x18, 0x60)
    a.label("gf_pick").abs(0x20, "gf_mod").b(0xAA).abs(0xBD, T0 + 1).b(0x85, 0x0F)       # $0F = design
    a.b(0xA5, 0x0E).abs(0x20, "gf_slotrec")                                              # Y = record
    a.b(0xA5, 0x0F, 0x18, 0x69, 0x01).abs(0x99, REC)                                    # [0]
    # [1] variant | group << 2 | palette << 4 (level 9: palette 8)
    a.b(0xA9, K).abs(0x20, "gf_modn").abs(0x8D, T0 + 1)
    a.b(0xA9, 0x03).abs(0x20, "gf_modn").b(0x0A, 0x0A).abs(0x0D, T0 + 1).abs(0x8D, T0 + 1)    # group (any of 3)
    a.b(0xA5, 0x0E, 0xC9, 0x09)
    a.br(0xD0, "gf_n9") if not os.environ.get("LOL_PAL8") else a.b(0xEA, 0xEA)       # (test: level 9's colours)
    a.abs(0xAD, T0 + 1).b(0x09, 0x80).br(0xD0, "gf_s1")                                 # level 9: its colours
    a.label("gf_n9").b(0xA9, 0x09).abs(0x20, "gf_modn").b(0x0A, 0x0A, 0x0A, 0x0A).abs(0x0D, T0 + 1)
    a.label("gf_s1").abs(0x99, REC + 1)
    # [2] boss: one of the variant's boss list
    a.b(0xA6, 0x0E).abs(0xBD, "gf_cls").b(0x48, 0x29, 0x03, 0x0A, 0x0A, 0x0A, 0x0A, 0x0A, 0x0A).abs(0x8D, T0 + 2)
    a.b(0xA5, 0x0F, 0x0A, 0x65, 0x0F).abs(0x6D, T0 + 2).abs(0x8D, T0 + 2)
    a.abs(0xB9, REC + 1).b(0x29, 0x03, 0x18).abs(0x6D, T0 + 2).b(0xAA)
    a.b(0x68).abs(0x8D, SCR + 11).b(0x8A, 0x4A, 0xAA, 0x08)                  # (two per byte; 4 pages)
    a.abs(0xAD, SCR + 11).b(0x4A, 0x4A)
    for pg in range(3):
        a.b(0xC9, pg).br(0xD0, f"gf_pn{pg}").b(0x28).abs(0xBD, f"gf_bl{pg}").abs(0x4C, "gf_bq")
        a.label(f"gf_pn{pg}")
    a.b(0x28).abs(0xBD, "gf_bl3")
    a.label("gf_bq").br(0x90, "gf_bp").b(0x4A, 0x4A, 0x4A, 0x4A)
    a.label("gf_bp").b(0x29, 0x0F, 0xAA).abs(0xBD, "gf_bn").br(0xF0, "gf_nob")
    a.b(0x48).abs(0xBD, "gf_bo").abs(0x8D, T0 + 2).b(0x68).abs(0x20, "gf_modn").b(0x18).abs(0x6D, T0 + 2).b(0xAA)
    a.abs(0xBD, "gf_bf")
    a.label("gf_nob").abs(0x99, REC + 2)
    a.abs(0x20, "rnd").abs(0x99, REC + 3)                                               # [3] seed
    # [4] items
    a.b(0xA5, 0x0E, 0xC9, 0x09).br(0xF0, "gf_i9")
    a.abs(0x20, "gf_cel").abs(0x8D, T0 + 2).abs(0x20, "gf_cel").b(0x0A, 0x0A, 0x0A).abs(0x0D, T0 + 2)
    a.abs(0x4C, "gf_i_st")
    a.label("gf_i9").abs(0x20, "gf_up")
    a.label("gf_i_st").abs(0x99, REC + 4)
    a.b(0xA5, 0x0E, 0x38, 0x60)                                                          # A = dest, C = 1
    # gf_anyd: C = 1 if a free design may take dest $0E
    a.label("gf_anyd").b(0xA2, nd - 1).label("ga").abs(0x20, "gf_okd").br(0xB0, "ga_y").b(0xCA).br(0x10, "ga")
    a.b(0x18)
    a.label("ga_y").b(0x60)
    # gf_okd: C = 1 if design X is free and may take dest $0E (X kept)
    a.label("gf_okd").b(0x8A, 0x48)
    a.b(0xA0, 5 * (NSLOT - 1)).label("go_u").abs(0xB9, REC).b(0x38, 0xE9, 0x01).abs(0x8D, SCR + 13)
    a.b(0x68, 0x48).abs(0xCD, SCR + 13).br(0xF0, "go_no")                                # in use
    a.b(0x98, 0x38, 0xE9, 0x05, 0xA8).br(0xB0, "go_u")
    a.b(0x68, 0xAA, 0x48)
    a.b(0xA4, 0x0E, 0xC0, 0x08).br(0xB0, "go_hi")
    a.abs(0xBD, "gf_mlo").abs(0x39, "gf_bit").br(0xF0, "go_no").br(0xD0, "go_y")
    a.label("go_hi").abs(0xBD, "gf_mhi").abs(0x39, "gf_bit8").br(0xF0, "go_no")
    a.label("go_y").b(0x68, 0xAA, 0x38, 0x60)
    a.label("go_no").b(0x68, 0xAA, 0x18, 0x60)
    # gf_slotrec: Y = 5 * slot index of dest A
    a.label("gf_slotrec").b(0xAA).abs(0xBD, "gf_sidx").abs(0x8D, SCR + 12).b(0x0A, 0x0A, 0x18).abs(0x6D, SCR + 12)
    a.b(0xA8, 0x60)
    # cellar item roll (Y kept)
    a.label("gf_cel").b(0x98, 0x48).abs(0x20, "gf_cel2").abs(0x8D, SCR + 14).b(0x68, 0xA8).abs(0xAD, SCR + 14).b(0x60)
    a.label("gf_cel2").b(0xA2, 0x04).label("gw").abs(0xBD, "gf_w0").abs(0x9D, T0 + 3).b(0xCA).br(0x10, "gw")
    a.b(0xA2, 0x02).label("gb").abs(0xAD, 0x0673).abs(0x3D, "gf_bmask").abs(0xBC, "gf_bsh")
    a.label("gs").b(0x88).br(0x30, "gs_d").b(0x4A).br(0x10, "gs")
    a.label("gs_d").b(0xC9, 0x03).br(0x90, "gb_n")                     # three of that badge: not offered
    a.b(0xA9, 0x00).abs(0x9D, T0 + 3).b(0xA9, 0x06, 0x18).abs(0x6D, T0 + 6).abs(0x8D, T0 + 6)  # (its share to XP)
    a.label("gb_n").b(0xCA).br(0x10, "gb")
    a.abs(0x20, "rnd").b(0x29, 0x3F, 0xA2, 0x00)
    a.label("gc").b(0x38).abs(0xFD, T0 + 3).br(0x90, "gc_y").b(0xE8, 0xE0, 0x04).br(0x90, "gc")
    a.label("gc_y").b(0x8A, 0x60)
    # level 9's upgrade: book, ring, sword, arrows, magic key - the next one Link lacks, evenly; else a red potion
    a.label("gf_up").b(0x98, 0x48, 0xA9, 0x00).abs(0x8D, T0)
    ups = [(0x0661, [0x11, 0x25]), (0x0662, [0x12, 0x13]), (0x0657, [0x02, 0x02, 0x03]), (0x0659, [0x08, 0x09]),
           (0x0664, [0x0B])]
    for i, (addr, nxt) in enumerate(ups):
        if addr == 0x0657:              # lol_modes' swordless: the sword is a bomb upgrade (below 32 bombs)
            a.abs(0xAD, 0x7FF7).br(0xF0, f"upn{i}").abs(0xAD, 0x067C).b(0xC9, 32).br(0xB0, f"up{i}")
            a.b(0xA9, 0x24).br(0xD0, f"ups{i}")
            a.label(f"upn{i}")
        a.abs(0xAE, addr).b(0xE0, len(nxt)).br(0xB0, f"up{i}").abs(0xBD, f"upt{i}")
        a.label(f"ups{i}")
        a.abs(0xAC, T0).abs(0x99, T0 + 1).abs(0xEE, T0)
        a.label(f"up{i}")
    a.abs(0xAD, T0).br(0xD0, "up_p").b(0xA9, 0x20).br(0xD0, "up_r")
    a.label("up_p").abs(0x20, "gf_mod").b(0xAA).abs(0xBD, T0 + 1)
    a.label("up_r").abs(0x8D, SCR + 14).b(0x68, 0xA8).abs(0xAD, SCR + 14).b(0x60)
    for i, (addr, nxt) in enumerate(ups):
        a.label(f"upt{i}").b(*nxt)
    a.label("gf_w0").b(13, 13, 13, 13, 12)     # v2.02 test 17: S, D, X badge, orange, blue XP about 20% each
    a.label("gf_bmask").b(0x03, 0x0C, 0x30)
    a.label("gf_bsh").b(0, 2, 4)
    a.label("gf_mod").abs(0xAD, T0)
    a.label("gf_modn").abs(0x8D, SCR + 9)
    a.label("gm").abs(0x20, "rnd").b(0x29, 0x1F).abs(0xCD, SCR + 9).br(0xB0, "gm").b(0x60)
    a.label("gf_dests").b(*DESTS)
    a.label("gf_sidx").b(*SLOT_INDEX)
    a.label("gf_cls").b(*SLOT_CLASS)
    a.label("gf_mlo").b(*[m & 0xFF for m in masks])
    a.label("gf_mhi").b(*[m >> 8 for m in masks])
    a.label("gf_bit").b(*[1 << i for i in range(8)])
    a.labels["gf_bit8"] = a.labels["gf_bit"] - 8
    assert len(blists) <= 16
    for pg in range(4):
        n = max([i - 256 * pg for i in range(256 * pg, 256 * pg + 256) if bl[i]] + [0]) // 2 + 1
        a.label(f"gf_bl{pg}").b(*[bl[256 * pg + 2 * k] | bl[256 * pg + 2 * k + 1] << 4 for k in range(n)])
    a.label("gf_bn").b(*[len(t) for t in blists])
    offs, flat = [], []
    for t in blists:
        offs.append(len(flat)); flat += list(t)
    a.label("gf_bo").b(*offs)
    a.label("gf_bf").b(*(flat or [0]))
    a.label("gf_cap").b(*cap78)

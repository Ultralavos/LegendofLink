"""Mix enemy groups (the page's flag; LOL_MIX=1): ZORA's Shuffle Enemy Groups (B42 with its overworld group, B43),
fully mixed, on the player's clean ROM.

The fifteen grouped enemies (Zol, Goriya, Darknut, Vire, Pols Voice, Like Like, Wizzrobe, Wallmaster, Rope, Stalfos,
Gibdo, Lanmola; Tektite, Lynel, Moblin; each with its color partner) are dealt into three new dungeon groups and a new
overworld group, at most 34 tiles of graphics each. ZORA's rules keep Wallmasters, Vires, Like Likes, Zols and
Lanmolas out of the overworld, Vires always share the Wizzrobes' group (their split), and so do Wizzrobes here (ZORA's overworld-Wizzrobe code hooks where LoL's does); Gels and Keese (the dungeon's common graphics) and Octoroks, Peahats, Leevers,
boulders, Zoras, Ghinis and Armos (the overworld's own) never move out of the overworld. The overworld screens'
monsters are then dealt to other screens (_shuffle_overworld), Zoras and Ghinis staying put.

mixed() computes it once per build (the seed's): the clean ROM with the new graphics, animation frames, mixed monster
lists, overworld monsters, item-carrier operands and ZORA's overworld-Wizzrobe bytes written, and the vanilla dungeon
rooms redrawn from the new groups (lol_genload.enemy_groups reads its groups from those rooms and lists).
apply(rom) writes the changed bytes outside the dungeon room blocks into the finished LoL ROM, where LoL left the
clean ROM's bytes (a byte LoL changed too stops the build).
"""
import os

import lolpaths

MIX = os.environ.get("LOL_MIX") == "1"
ROOM_BLOCKS = range(0x18010 + 0x0700, 0x18010 + 0x1300)   # bank 6 $8700-$92FF: the four dungeon room blocks
_CACHE = {}


def _seed():
    for k in ("LOL_SEED", "LOL_SET_SEED"):
        if os.environ.get(k):
            return int(os.environ[k])
    return 0


def mixed():
    """(clean ROM, the mixed ROM, the deal), in the player's release (PRG1 for the build)."""
    if "m" in _CACHE:
        return _CACHE["m"]
    from zora.rom.base_rom import player_rom_of, using_player_rom
    from zora.rom.parse.bin_files import load_bin_files_from_rom
    from zora.rom.parse.game_world import parse_game_world
    from zora.rom.parse.rom_file import original_bins_from_rom
    from zora.rom.serialize.game_world import serialize_game_world
    from zora.generate.rng import Rng
    from zora.generate.steps.group_banks import Staged
    from zora.generate.steps.shuffle_enemy_groups import shuffle_enemy_groups
    from zora.generate.steps.shuffle_groups import GroupShuffleResult, apply_groups
    from zora.generate.steps.change_enemy_hp import EnemyHpResult
    from zora.model.enums import Enemy
    clean = bytes(lolpaths.source_rom())
    player = player_rom_of(clean)
    # (owner, 2026-11-24) Vires stay in Wizzrobes' group: past 12 containers a vire splits into blue Wizzrobes
    # (lol_upgrades), whose graphics must be loaded. A deal that parts them is dealt again (the next stream).
    for attempt in range(64):
        with using_player_rom(player):
            canvas = player.canvas
            gw = parse_game_world(load_bin_files_from_rom(canvas), rom_bytes=canvas)
            zol_hp = EnemyHpResult.unchanged(gw.enemies).hp[Enemy.ZOL]
            result = GroupShuffleResult(staged=Staged())
            rng = Rng(_seed() * 7919 + 0x4D1 + 0x10001 * attempt)
            import zora.generate.steps.shuffle_enemy_groups as SEG
            barred = SEG.OVERWORLD_BARRED
            SEG.OVERWORLD_BARRED = barred | {Enemy.BLUE_WIZZROBE}       # (its partner, the red, follows it)
            try:
                result.enemy_deal, result.goriya_tile, result.rooms_redrawn = shuffle_enemy_groups(
                    gw.blocks, gw, 0, rng, gw.overworld, zol_hp, result.staged, overworld_group=True)
            finally:
                SEG.OVERWORLD_BARRED = barred
            d = result.enemy_deal
            gv = next((g for g in d.groups if Enemy.VIRE in d.members(g)), None)
            if gv is not None and Enemy.BLUE_WIZZROBE not in d.members(gv):
                continue
            assert not result.staged.red_wizzrobe_overworld
            _shuffle_overworld(gw, rng)
            apply_groups(gw, result)
            patch = serialize_game_world(gw, original_bins_from_rom(canvas))
            image = bytearray(canvas)
            patch.apply(image)
            out = player.finished(bytes(image))
            break
    else:
        raise AssertionError("Mix enemy groups: no deal keeps the vires with the wizzrobes")
    _CACHE["m"] = (clean, out, result.enemy_deal)
    return _CACHE["m"]


KEEP_OW = (0x11, 0x21, 0x22)            # Zora, the Ghinis: never moved (owner 2026-11-24)


def _shuffle_overworld(gw, rng):
    """(owner 2026-11-24) The overworld screens' monsters dealt to other screens: ZORA's Shuffle Overworld Monsters
    (its forward walk and barred placements: no blue moblin on the bracelet screens, peahats / leevers where they'd
    stick), with every screen that holds a Zora or a Ghini kept as it is; screens without monsters keep none."""
    import zora.generate.steps.shuffle_overworld_monsters as OWM
    ow = gw.overworld
    def keep(screen):
        pair = OWM.MonsterPair(ow.screens[screen].enemy_spec, ow.screens[screen].enemy_quantity)
        return any(OWM._holds(gw, pair, v) for v in KEEP_OW)
    cand = [s.screen_num for s in ow.screens
            if OWM._monster_byte(ow, s.screen_num) not in OWM.EXCLUDED_MONSTER_BYTES and not keep(s.screen_num)]
    pairs = [OWM.MonsterPair(ow.screens[x].enemy_spec, ow.screens[x].enemy_quantity) for x in cand]
    n = len(pairs)
    for pos in range(n):
        for _ in range(200):
            other = pos + rng.below(n - pos)
            if not (OWM._is_barred(gw, pairs[pos], cand[other]) or OWM._is_barred(gw, pairs[other], cand[pos])):
                break
        else:
            other = pos
        pairs[pos], pairs[other] = pairs[other], pairs[pos]
    for x, p in zip(cand, pairs):
        ow.screens[x].enemy_spec = p.spec
        ow.screens[x].enemy_quantity = p.quantity


def source():
    """The ROM lol_genload.enemy_groups reads its groups from: the mixed one with the flag on."""
    return mixed()[1] if MIX else lolpaths.source_rom()


def describe():
    d = mixed()[2]
    name = lambda e: e.name.replace("_", " ").title()
    return "; ".join(("overworld" if g == 3 else f"group {g + 1}") + ": " + ", ".join(name(e) for e in d.members(g))
                     for g in sorted(d.groups))


def apply(rom, notes):
    """The mix's bytes into the finished ROM (banks 0-6 at their offsets; bank 7's also in bank 15, the fixed bank
    of the doubled ROM)."""
    if not MIX:
        return
    clean, out, _ = mixed()
    big = len(rom) > len(clean)
    written = kept = 0
    for i in range(16, len(clean)):
        if clean[i] == out[i] or i in ROOM_BLOCKS:
            continue
        spots = [i]
        if big and 0x1C010 <= i < 0x20010:
            spots.append(i + 0x20000)
        for j in spots:
            if rom[j] == clean[i]:
                rom[j] = out[i]; written += 1
            elif rom[j] != out[i]:
                kept += 1
    # a byte LoL changed too would leave half of a ZORA write: never ship that
    assert not kept, f"Mix enemy groups: {kept} bytes LoL changed too"
    notes.append(f"mixed enemy groups: {describe()} ({written} bytes)")

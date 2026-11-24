# Legend of Link

A randomizer and rework of *The Legend of Zelda* (NES), built on [ZORA](https://github.com/Ultralavos/zora).

**Play:** open the randomizer page (GitHub Pages for this repo), choose your own ROM of *The Legend of Zelda (USA)*,
PRG0 or PRG1, pick your settings and build. Everything runs in your browser; your ROM is never uploaded and no game
data is stored in this repository.

## Settings (first version)

- **Seed**: blank gives a different game on every new file (as the IPS releases do). A number fixes the game: the
  same seed and settings give everyone the same overworld and dungeons.
- **Mode**: normal (the secret modes can still be found), swordless from the start, or hard mode from the start.
- **Mix enemy groups**: the dungeon and overworld enemies dealt into new groups (ZORA's Shuffle Enemy Groups with its
  overworld group, `build/lol/lol_mixgroups.py`). Wallmasters, Vires, Like Likes, Zols, Lanmolas, Wizzrobes, Gels and
  Keese stay in dungeons; Octoroks, Peahats, Leevers, boulders, Zoras, Ghinis and Armos stay outside.

## Upgrades and hints per seed

Each seed picks the upgrades its shops can offer (`build/lol/lol_uptable.py`: up to 10 per tier, 3 of them from the
tier's upgrades with no conditions), and the old men's quotes to go with them (`build/lol/v2_grids/hints.txt`):
quotes about upgrades the seed left out are dropped, and fun quotes fill the set up to 40 (at least 3 of them). The
title's list still shows every upgrade.

**Heart Snubber** (200, tier 3; only in the second upgrade cave Link finds, at 3 heart containers or fewer;
`build/lol/lol_snubber.py`): Link stays at 3 hearts for good while his level keeps counting (enemies, offers and
hard mode go by it). From level 4 his sword's attack is half his level (2 at 4, up to 8 at 16); no sword or sword
upgrade is offered again (a sword's odds go evenly to the rest); the top heart row shows a sword per 2 levels and a
cross for an odd one.

**Red Gleeok** (`build/lol/lol_gleeok.py`): at 12+ heart containers (as enemies see them) Gleeok turns red and,
every 2-4 seconds, two of its attached heads (one if only one is left) spit a candle flame straight down: it moves
16 pixels and burns about a second, 2 hearts to Link.

## The end screen

After the credits, Start opens two pages (`build/lol/lol_stats.py`; Start flips them, Select goes on):

1. Levels 1-9 and shrines A-D, each with its dungeon's nickname and the item its old man gave (a level) or its
   reward (a shrine), if Link took one.
2. The time from the file's start to the finish (H:MM:SS, counted while the game runs, resets included), the
   badges, the upgrades bought, and the inventory: the items above the box, the sword, and the box.

## Planned

- Dungeon sets: 1Q, 2Q, 3Q, 4Q, Legend of Link's own maps, random shapes, random (one set) and mixed (per level).
  Shrines always come from Legend of Link's maps or random shapes. Quest shapes are used shape-only: rooms, walls
  and stairs; enemies and items follow Legend of Link's rules.
- A spoiler log.

## Layout

- `build/lol/` the Legend of Link build (`lol_build.py` and its modules, the odds tables and the dungeon grids)
- `build/q3/` the 3Q build it sits on
- `build/shapes/` dungeon shapes (4Q)
- `web/` the page; `web/worker.js` runs the build with Pyodide
- `scripts/package_build.py` packs `build/` and ZORA into `web/lol-build.zip` (the Pages workflow does this)

## Building from the command line

```
git clone https://github.com/Ultralavos/zora ../zora      # (the commit in .github/workflows/pages.yml)
LOL_GEN=1 [LOL_SEED=12345] [LOL_START=normal|swordless|hard] \
  python3 build/lol/lol_build.py "Legend of Zelda, The (USA) (Rev 1).nes" out.ips out.nes
```

The build takes a PRG1 ROM; the page turns a PRG0 ROM into PRG1 first (`web/prg0-to-prg1.ips`).

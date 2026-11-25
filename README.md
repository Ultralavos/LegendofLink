# Legend of Link

A randomizer and rework of *The Legend of Zelda* (NES), built on [ZORA](https://github.com/Ultralavos/zora).

**Play:** open the randomizer page (GitHub Pages for this repo), choose your own ROM of *The Legend of Zelda (USA)*,
PRG0 or PRG1, pick your settings and build. Everything runs in your browser; your ROM is never uploaded and no game
data is stored in this repository.

**Custom sprites**: a ROM whose only changes are in the sprite pattern blocks (Link and the items, the overworld's
and the dungeons' enemies, the bosses) is taken too, PRG0 or PRG1 (`web/app.js` zeroes those blocks and checks the
rest against clean PRG1). Anything else changed, colors included, and the page turns it down. The file-select code
leaves the sprite tiles out, so players with different sprites and the same settings see the same code.

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
half sword for an odd one.

**Zombie Link** (75, tier 2, rare; replaces Glass Cannon; only at exactly 3 heart containers, with no ring and no
Regen, and Regen is never offered after it; `build/lol/lol_zombie.py`): Link takes sprite palette 3, as the blue
Moblins do (each level's colors in a dungeon). His health drops to 0 with the containers kept (as paying the mugger
with 3 hearts does) when he buys it and after every continue, death or save. Nothing heals him the usual way: a potion
drains half his hearts, a fairy 3, a heart 1 and a fairy fountain all of them (never below 0). His sword or wand
swing (not beams) deals double, and a swing that hits a Darknut, Moblin, Goriya, Lynel, Rope or Wizzrobe heals a
quarter of the damage (a 2-damage hit heals half a heart). He takes double damage, half from touching a Pols Voice,
Gibdo, Ghini or Stalfos, and 4x from his own candle flame with Holy Fire. No low-health beep; rings leave every prize
list.

**Brain Potion** (50, tier 1; with Zombie Link and a potion, never with the Bat Potion): every potion becomes a
brain potion (its own picture at all four pouch levels) and refills Zombie Link fully, as a normal potion would.

**X-ray Glasses** (200, tier 3; `build/lol/lol_xray.py`): in dungeons and shrines, a bombable wall not yet blown
open shows grey and a walk-through wall orange (only the wall's palette changes; a blown wall gets its color back).
Always in the pool when the seed's dungeons can have walk-through walls (2Q, 3Q, 4Q, and Random when it deals one of
their grids); otherwise it's rolled like any other upgrade.

**Red Gleeok** (`build/lol/lol_gleeok.py`): at 12+ heart containers (as enemies see them) Gleeok turns red and,
every 2-4 seconds, two of its attached heads (one if only one is left) spit a candle flame straight down: it moves
16 pixels and burns about a second, 2 hearts to Link.

## Seeded games, upgrade lines and item lines

**Seeded (the norm)** (`build/lol/lol_fixed.py`): the build decides the entrance deal and every level's and shrine's
record (design, variant, enemy group, palette, boss, the rooms' seed, the cellar items: old men cards and XP bags),
so a seed is one fixed game for everyone; a blank seed gets one picked by the page. Level 9's stair item is still
rolled in the game. A card Link already holds three of comes as an orange XP bag. **Unseeded** (the page's option,
LOL_FIXED=0) keeps the old way: the game deals and makes these itself.

**Item lines** (old men's choices, shrine prizes, shops; `lol_odds`): for each list and each level 1-16 the build
shuffles that level's odds row into a line (items with odds above 0, likelier ones tending to come first). The game
offers the first items of the line for Link's level that he can get (owned ones, ones he can't have yet and the bait
while he holds one are skipped). A second tier he can't have yet gives its first tier instead: magical sword -> white
sword, red candle -> blue candle, red ring -> blue ring, silver arrows -> wood arrows, blue book -> red book.

**Upgrade caves** (always): the build shuffles each tier's pool into a line (rarer upgrades tend to come later). The
first time Link enters an upgrade cave it takes, for each tier, the first upgrade in the line that no cave has taken
and that he can have right now; a skipped one keeps its place. A cave's three are locked from then on, and after a
purchase all three are gone. Hints about an upgrade are offered from the start if it is among the first 3 of its
line, otherwise once a cave has offered it.

## Shrine touches

`build/lol/lol_shrineui.py`: rooms next to Ganon's (Level 9) or a shrine guardian's room roar while that boss
lives (on entering and every few seconds); the overworld item screen shows A B left of TRIFORCE and C D right of it
as each shrine's reward is taken; a shrine's status bar reads SHRINE-X from the first frame. A level-up from an XP
bag in a cellar keeps Link lifting the bag (not a heart container).

## Title and seed code

The title screen reads LEGEND OF LINK / BETA 0.301 and the seed below it (NEW SEED EACH FILE without one;
`build/lol/lol_seedcode.py`). The file-select heading shows CODE and four item icons: a hash of the finished ROM, so
players whose four icons match have the same game (same seed and settings). The page shows the same four icons
with their names under the download buttons, drawn from the built ROM's own graphics (ZORA's `seed_code_icons`).

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

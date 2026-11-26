# Legend of Link

A randomizer and rework of *The Legend of Zelda* (NES), built on [ZORA](https://github.com/Ultralavos/zora).

**Play:** open the randomizer page (GitHub Pages for this repo), choose your own ROM of *The Legend of Zelda (USA)*,
PRG0 or PRG1, pick your settings and build. Everything runs in your browser; your ROM is never uploaded and no game
data is stored in this repository.

**Custom sprites**: a ROM whose only changes are in the sprite pattern blocks (Link and the items, the overworld's
and the dungeons' enemies, the bosses) and the background pattern blocks (lol_seedcode.BG_BLOCKS: the common one,
bank 3's dungeon and overworld ones: bushes, Armos statues...; and bank 1's two title screen blocks) is taken too, PRG0 or PRG1 (`web/app.js` zeroes those
blocks and checks the rest against clean PRG1). The build first blanks the tiles blank in PRG1 (never drawn; LoL puts
its own pictures there: lol_seedcode.BLANK_TILES). Anything else changed, colors included, and the page turns it
down. The file-select code leaves those tiles out, so players with different graphics and the same settings see the
same code.

## Settings (first version)

- **Seed**: blank gives a different game on every new file (as the IPS releases do). A number fixes the game: the
  same seed and settings give everyone the same overworld and dungeons.
- **Link's colors**: his tunic with no ring, the blue ring and the red ring, each "From your ROM" or an NES color
  (LOL_TUNIC="29,32,16"). A ROM whose only changes are Link's colors (the tunic colors' two copies, his colors 2
  and 3 in the palettes; lol_seedcode.LINK_COLOR_BYTES) and custom sprites is taken, its colors kept; the seed's
  icon code ignores them.
- **Reduce flashing** (LOL_NOFLASH=1): ZORA's four flashes off (the bomb's grayscale, the triforce pickup's and the
  Triforce of Power's flashes, the ending's flash colors; lol_seedcode.FLASH_BYTES, 10 bytes). Cosmetic: the seed is
  the same game and its icon code ignores those bytes.
- **Race Rom** (LOL_RACE=1; lol_encode): the level data (bank 6 $8400-$9CD7: the five level blocks and ten level
  infos) XORed with a 64-byte key (a hash of the plain data), decoded by CopyBlock as the game loads a level, so map
  viewers and ROM tools can't read the seed. Its icon code is its own (the hash is marked). Not cheat-proof: the
  decoder is in the ROM.
- **Mode**: (hidden for now: always normal; the secret modes can still be found in the game. The build still takes
  LOL_START=swordless|hard.)
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

**Boomerang Mastery** (75, tier 2; with either boomerang): boomerang hits deal +1 damage ($10; `lol_upgrades`' sword
hook, weapon slot $0F), so they hurt as well as stun.

**Bookworm** (200, tier 3; from level 8, 8+ heart containers): the books' bonus doubles (red +2, blue +4;
`lol_books`). Until Link owns a book, the last of a dungeon old man's choices is the red book (an extra one when he'd
offer fewer) and every shop's third ware is the red book for 25 rupees (`lol_choice.book_routines`).

**Red Gleeok** (`build/lol/lol_gleeok.py`): at 12+ heart containers (as enemies see them) Gleeok turns red and,
every 2-4 seconds, two of its attached heads (one if only one is left) spit a candle flame straight down: it moves
16 pixels and burns about a second, 2 hearts to Link.

**Heavy Bracelet** (75, tier 2, with the power bracelet; `build/lol/lol_heavy.py`): only on seeds whose upgrade pool
has it. A10 gets the second quest's pushable rock and G6 the owner's 4Q one (the middle rock of column 10, stairs
right of it), both pushable only with the Heavy Bracelet; with it, every pushable overworld rock shows grey. The seed
decides each cave (out of 64, never the same option in both): 30 the Thorn Bracelet (free; its old man says "WITH
THIS YOU DEAL DAMAGE BACK WHEN ENEMIES TOUCH YOU", and the Song of Sleep's "THIS LULLABY PUTS SOME ENEMIES TO
SLEEP, AND SLOWS OTHERS"), 10 a secret shop (ring
150, sword 150, book 100, each the next one Link can use), 20 100 rupees, 3 an old man's hint about a secret mode,
1 a free ring, book or sword. **Thorn Bracelet** (UP6 $80): replaces the Heavy Bracelet's picture on the item screen;
a monster that touches Link takes what Link loses (rings count), rounded up to whole hearts, $10 a heart.

**Song of Discovery** (75, tier 2, with the recorder; `build/lol/lol_discovery.py`, caves in `lol_heavy.py`): only on
seeds whose upgrade pool has it. With it the recorder drains a patch of sea at H16 (east of the shore, 3x3) with
stairs in it, and turns E4's bush right of the fairy pond into stairs; neither is saved (the water and the bush are
back when the screen loads again; play again, as with the vanilla recorder spots). Link comes out of H16's cave on
the sand and E4's above the pond. A recorder sprite marks the four recorder spots (E3, F9, E4, H16) until they're
revealed. The seed deals the two caves as the Heavy Bracelet's, with the **Song of Sleep** (EXTRA $02) in the Thorn
Bracelet's place; it replaces the Song of Discovery's picture on the item screen. In a level, when the recorder's
tune ends, the room's red and blue Goriyas (not Chargers), Ropes, red Darknuts, Vires (which then can't split) and
Moblins (not the charging top tier) fall asleep until Link leaves the room; blue and brown Darknuts slow a step;
every Pols Voice dies; Digdogger's babies sleep if they were already there when the tune ended.
Bits: $7F47 (lol_entrances' spare byte, cleared for a new file; lol_upgrades' uget reads rows from K7F there).

**Goriya Charger** (`build/lol/lol_enemies2.py`): at 12+ heart containers (as enemies see them) blue Goriyas wear
Link's colors (sprite palette 0, so they follow his ring), have 6 health, deal 4 hearts on contact (with knockback)
and give 15 XP. Their boomerang does no damage: it stuns Link for 30 frames (no input, no flashing; lol_upgrades'
frame hook clears the buttons), and 20 frames after it hits, that Goriya charges straight at him (2 px a frame,
until a wall, the room's edge, contact, 16 px past Link or 64 frames). The hit is caught at HarmLink's start (the
critter crusher's hook, then a common stub at $BFC0 far-calling bank 2); the charge is UpdateObject's entry for $05
(bank 4 $BF20, a far call into bank 2, else $8119).

**Bomber Wizzrobe** (`build/lol/lol_wizzrobe.py`): at 14+ heart containers (as enemies see them) red Wizzrobes wear the
level's colors (sprite palette 3), have 12 health and give 16 XP. Bombs don't hurt them; the candles' fire does (the
blue candle 4 per hit, the red candle kills). Four frames before one starts to fade out it leaves a red bomb where it
stands (lol_dodongo's type $29: lit $30 frames, then a blast that only hurts Link, 4 hearts), so the blast comes
shortly after it's gone, and it leaves one when it dies. At most 3 red bombs on the floor, never two within 16 px.

**Hydra Gohma** (`build/lol/lol_gohma.py`): at 14+ heart containers (as enemies see them) a Gohma (either kind) in a
room's first slot turns purple, and two of Gleeok's heads hang on necks from inside the north wall (halfway from the
middle to each side), while Gohma keeps to a band two squares lower than its own (y $90-$B0): heads and Gohma seldom
share a row, so hardly any flicker. Going south it speeds up to two steps above the blue Darknut ($38: 7/8 px a
frame); back up and sideways at its own pace. The heads sway and spit fireballs as Gleeok's, and Gohma spits its own. A head cut off flies about as
Gleeok's do. While any head is on, Gohma's eye stays shut (and its health held); once both are gone the eye opens for
good, with the blue Gohma's health (arrows from below, as ever). The slot becomes a two-headed Gleeok (Gleeok's code
owns slots 1-6, cut heads 7-8) and the Gohma moves to slot 11; flags at $0160-$0161 (stack page, unused).

**Fire Sage** (`build/lol/lol_patra.py`): at 15+ heart containers (as enemies see them) a Patra becomes an old man
with 6 flames circling him (Patra's own moves and patterns; six evenly spaced, not eight). The old man has 15 health,
does 4 hearts on touch and throws a fireball (1 heart) every 1.5 seconds; each flame has 8 health and does 2 hearts.
They're hurt as Patra is (sword and wand hits; arrows too with piercing arrows), the old man only once the flames are
gone. His picture is the cave old man's, written over Patra's body tiles ($F8-$FB) as the room starts.
(RAM: stack-page bytes no code touches; $6530+ is the play area's tiles, not free.)

**Ganon's guards** (`build/lol/lol_ganon.py`): at 16 heart containers (as enemies see them), and always in hard mode,
Ganon calls up Level 9's strongest ordinary monster (the most XP at 16 containers, from Level 9's own sprite set,
which his room shows whatever the level's enemy group; no bosses, Lanmolas, Patras, traps or Vires; a tie never a
Wallmaster) in a cloud of smoke 60 frames into the fight and every 580 frames after, while fewer than 3 are alive
(with 3 the timer stops, and starts again when one dies). They drop nothing, and they die when Ganon
does. Test build: `LOL_DEBUG_GANON=1` (never the page's) starts a file with 16 hearts, the magical sword, the red
ring, the bow, silver arrows, 30 rupees and the triforce, sends the wood sword cave into Level 9 and moves Ganon's
room north of the way in.

**-ROAR-** (`build/lol/lol_shrineui.py`): while a room roars (next to Ganon's room or a living shrine guardian's),
the status bar's -LIFE- reads -ROAR-, for players who can't hear it; back to -LIFE- when the roar stops or Link
leaves the level.

**Secret spots** (`build/lol/lol_secret.py`): about one seed in 100 hides one hint cave that nothing marks (not the
X-ray Glasses, the Heavy Bracelet's grey, the Song of Discovery, the tracker or the manual). Which spot and which
words are the seed's own; `LOL_SECRET="spot,hint"` forces one for tests.

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

## The triforce caves

The 4-triforce cave (the white sword cave) offers the first item Link lacks from its list (a book first once he has
the white sword or better: red, then blue; then white sword, bow, arrows, wand, ladder, ...). The 8-triforce cave offers, once he has all 8, the first he can still use of: silver arrows,
magic key, book (red, then blue), sword (white, then magical), ring (blue, then red), bow, ladder, recorder, power
bracelet, raft, wand; with all of them, a red potion (`lol_upgrades.MS_LIST`). No swords with the Heart Snubber (a bomb
upgrade instead when swordless), no rings with Zombie Link.

## Shrine touches

`build/lol/lol_shrineui.py`: rooms next to Ganon's (Level 9) or a shrine guardian's room roar while that boss
lives (on entering and every few seconds); the overworld item screen shows A B left of TRIFORCE and C D right of it
as each shrine's reward is taken; a shrine's status bar reads SHRINE-X from the first frame. A level-up from an XP
bag in a cellar keeps Link lifting the bag (not a heart container).

## Title and seed code

The title screen reads LEGEND OF LINK / BETA 0.371 and the seed below it (NEW SEED EACH FILE without one;
`build/lol/lol_seedcode.py`). The file-select heading shows CODE and four item icons: a hash of the finished ROM, so
players whose four icons match have the same game (same seed and settings). The page shows the same four icons
with their names under the download buttons, drawn from the built ROM's own graphics (ZORA's `seed_code_icons`).

## Instruction booklet and version

`manual/gen.py` builds the booklet as a web page, `web/manual/index.html` (its pictures in `web/manual/img`); the
randomizer page links to it. `node manual/pdf.js web/manual/index.html out.pdf` prints it as a PDF. The version
(`lol_seedcode.VERSION`, `web/app.js` VERSION, the booklet's cover, the pages' `?v=`) goes up by 0.001 with every change
set: `python3 scripts/bump_version.py`, then `python3 manual/gen.py`.

## Tracker

`web/tracker/` (linked from the page): items with tiers, triforce 1-8 and shrines A-D, hearts, bomb upgrades, S/D/X
cards, the 37 upgrades (seen / bought), the overworld map (rendered from the game) with its 71 entrances to mark,
a room grid per level and shrine with its nickname, the old men of Levels 1-8 (lit when one is drawn in that
level's grid; click to record the item taken), notes and a timer; kept in the browser's localStorage. Its
layout follows ZORATracker (TheGobOne, MIT), rebuilt here as a plain web page.

## The end screen

After the credits, Start opens two pages (`build/lol/lol_stats.py`; Start flips them, Select goes on):

1. Levels 1-9 and shrines A-D, each with its dungeon's nickname and the item its old man gave (a level) or its
   reward (a shrine), if Link took one.
2. The time from the file's start to the finish (H:MM:SS, counted while the game runs, resets included), the
   badges, the upgrades bought, and the inventory: the items above the box, the sword, and the box.

## Planned

- A spoiler log.
- Upgrades from the owner's first list not built yet (what each does is still to be decided): Destruction Expert, Bomb Blast Suit, Expert Arsonist,
  Orbital Shield. (Glass Cannon became Zombie Link and Attack over Heart became the Heart Snubber.)

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

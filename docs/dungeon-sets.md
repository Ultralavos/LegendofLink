# Dungeon sets (plan, 2026-11-24)

Decided with the owner:

- One dropdown: **1Q, 2Q, 3Q, 4Q, LoL, Shapes, Random** (the seed picks one set for levels 1-9) and **Mixed**
  (each level from any set).
- Quest shapes are **footprint only**: which squares are rooms. Doors, locked doors, bomb walls, room layouts,
  enemies and items are made by Legend of Link's generator (`build/lol/lol_gen.py`) and the game's loader.
- Shrines A-D: from LoL's shrine designs or random shapes (the quests have no shrines).

## How it fits the current build

The game holds a library of designs in data banks 8-14 (`lol_genload`): each design is a footprint on one of up to
four 8x16 "grids" (each grid has its own room-flag area; its free squares hold the design's cellars: two item
cellars per level 1-8 design, transport cellars), with K variants made by `lol_gen.make_variants`. The game picks a
design for a level the first time it's entered.

The page will build that library from the chosen footprints instead of `v2_grids/grids.txt`:

1. Footprints per source:
   - 1Q / 2Q: from the player's ROM (ZORA's parse of the levels).
   - 3Q: `build/q3/grid_1_6.json`, `grid_7_9.json`.
   - 4Q: `build/shapes/q4/q4_grids.json` (block_1_6, block_7_9; `levels` assigns letters to levels).
   - LoL: `build/lol/v2_grids/grids.txt` (as now).
   - Shapes: a random footprint per level (room counts in each level's usual range), connected or in pieces joined
     by transport stairs where the level class allows.
2. Pack the 13 chosen footprints onto at most 4 grids, leaving the free squares each design needs for cellars.
3. One design per level and shrine (each design allowed only in its own slot), so a seed fixes the dungeons.
4. Spoiler log: the chosen footprints, their variants and the generator's placements.

## Shapes (owner's rules, 2026-11-24)

- Shapes makes four new grids like LoL's: one grid with 8 random shapes, one with 6, one with 4, one with 3
  (21 shapes). Each shape is 12-60 rooms.
- Which shapes a level may use, by room count:
  - Levels 1-3 and every shrine: 12-20 rooms (shrines take the smallest shapes first); levels 1-3 may also take
    the 6-shape grid's shapes of 20 rooms or fewer
  - Levels 4-5: 15-30
  - Levels 6-8: 20-45
  - Level 9: 30-60
- Each grid still needs free squares for its shapes' cellars (item stairs, transports).
- Every set (quests, LoL, Shapes) keeps LoL's rules, which `lol_gen` already applies by level class
  (`v2_grids/generator_spec.txt`): levels 1-8 their stairs (item cellars, transports by class) and old men
  (choice rooms); shrines the prize room behind the boss with shutter doors.

### Order (owner, 2026-11-24, replaces the pools above)

The page gives each level one shape, in this order, at random among the shapes left that the level may use (its
grids, inside its size range): level 9 one of the 3-shape grid's (30-40 rooms); level 8, then 7, from the 4- or
3-shape grids; level 6 from the 6-, 4- or 3-shape grids; the shrines the four smallest of the 8-shape grid; level 5,
then 4, from the 6- or 4-shape grids; levels 1-3 from the 8- or 6-shape grids. The 8 shapes left over stay on their
grids unused. (Level 4 wasn't named: it follows level 5's rule.)

### Quest sets (owner, 2026-11-24)

1Q-4Q: the quest's blocks 1-6 and 7-9 stay as they are (grids 1 and 2). The other two grid slots load two LoL grids
at random (of six: grids.txt's four and grids_extra.txt's two, added by the owner), and the shrines are any four of
their designs of 12-20 rooms. Cellars are given per design (its class's item stairs, one transport per extra piece
plus the class's own; level 2's item cellar is never used and shares another's), which is exactly what the quests'
blocks have room for (1Q: 7 and 13 free squares).

Designs on the two LoL grids that no shrine uses leave their grid, which frees their squares for cellars.

### Quest rules (owner, 2026-11-24)

- **Level numbers as the game shows them.** 2Q's levels 2-3, 4-5 and 7-8 are stored in each other's slots; the sets
  use the number on the status bar (ZORA's `rom_level_num`).
- **Each quest's own stairs** (`lol_quests.rules`): item stairs and transports per level. 1Q and 2Q come from the
  ROM; 3Q from our 3Q maps; 4Q levels 1-5 from our 4Q designs, levels 6-9 (not designed yet) use 3Q's. Level 2's
  stairs stay LoL's (its floor item), level 9 keeps two cellars (its upgrade and the red potion), and a level has at
  most two item stairs. When a block can't hold every stair, the extra transports go first (4Q's 7-9 block: 15 free
  squares, so L7-L9 lose some).
- **Walk-through walls in 2Q-4Q**, at the quest's own share of the doors between rooms, per level (2Q from the ROM,
  3Q from our maps, 4Q levels 1-5 from our designs, 6-9 3Q's). 1Q has none.
- **Floor items.** A level whose quest has a major item on the floor or dropped (2Q L1's boomerang, 3Q L4's blue
  candle, 4Q L3's boomerang-choice old man) gets a floor badge / XP like LoL's levels 1 and 2. The level's two rolled
  items go to its cellars first, then its floor room. Heart containers don't count (LoL puts a blue potion in 1-8).

| Quest | Floor-item levels |
|---|---|
| 1Q | 1, 2 |
| 2Q | 1, 2, 3 |
| 3Q | 1, 2, 4, 6, 7, 8 |
| 4Q | 1, 2, 3, 5, 6, 7, 8 |

### More LoL grids (owner, 2026-11-24)

- **Grid 7** (Hero 31 rooms: levels 6-9; Hellhound 43: levels 7-9) takes grid 3's place (Ghost, Gecko, Balloon) in
  half the seeds of the plain LoL set.
- **Grid 8** (Corners, Bomb, Camel, Guillotine, Bird, Ladle) and **grid 9** (Notes, Question Mark, Pyramids,
  Heart, Bull, Periscope; the Pyramids' darker square a hidden room) each take grid 2's place in a third of the
  seeds (grid 2 itself the other third). Their levels go by size, kept where lol_gen can generate them: Corners
  1-3 or a shrine (four pieces), Question Mark only a shrine (ten rooms in four pieces).
- All of them join the Mixed / Random pool.
- Ghost's five and Balloon's one hidden rooms are deleted (Ghost 42 rooms, Balloon 39).
- Page sets' cellars: item cellars stay each design's own (grid 4's two room-memory areas reuse each other's
  squares), transport cellars are shared by a grid's designs (as LoL's own grids share them); a design reserves
  what its neediest level takes.

### Quest level nicknames (owner, 2026-11-24)

| Level | 1Q | 2Q (in-game number) | 3Q | 4Q |
|---|---|---|---|---|
| 1 | The Eagle | The E | The Sword | The Bow and Arrow |
| 2 | The Moon | The A | The Kite | The Rabbit |
| 3 | The Manji | The L | The Islands | The Broken Boomerang |
| 4 | The Snake | The D | The Candle | The Whirlwind |
| 5 | The Lizard | The Z | The Crane | The Hammer |
| 6 | The Dragon | The Cap | The Dancer | The Scorpion |
| 7 | The Demon | The Flail | The Lock Picks | The Armos |
| 8 | The Lion | The Whip | The Vire | The Crown |
| 9 | The Skull | The Pig | The Serpent | The Swiss Cheese (+ the Torch) |

(`lol_quests.NICKNAMES`; 3Q's 1-4 and 9 as proposed, 5-8 the owner's.)

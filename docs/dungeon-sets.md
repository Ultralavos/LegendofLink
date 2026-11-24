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
  - Levels 1-3 and every shrine: 12-20 rooms (shrines take the smallest shapes first)
  - Levels 4-5: 15-30
  - Levels 6-8: 20-45
  - Level 9: 30-60
- Each grid still needs free squares for its shapes' cellars (item stairs, transports).
- Every set (quests, LoL, Shapes) keeps LoL's rules, which `lol_gen` already applies by level class
  (`v2_grids/generator_spec.txt`): levels 1-8 their stairs (item cellars, transports by class) and old men
  (choice rooms); shrines the prize room behind the boss with shutter doors.

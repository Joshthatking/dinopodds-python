# DinoPodds

A Pokémon GBA-style RPG (think FireRed / Emerald) built in Python with Pygame, starring original creatures called **dinos**.

You play as Jet. You explore the Lost Region, catch and train dinos, battle trainers and gym leaders, and uncover a story about an eclipse, a mysterious "Shadow Team" and the celestials that once ruled the region.

## Features

- **Exploring:** a large overworld built from stitched-together Tiled maps (towns, routes, a corn maze, caves and a lake), with day/night, an eclipse event and surfing.
- **Dinos:** 46 species with types, evolutions, level-up movesets, TMs and a Dinodex.
- **Battles:** wild, trainer and double battles, catching with DinoPods, XP and a type chart.
- **Story:**
  - 3 gyms and their rematches
  - a rival
  - scripted cutscenes and side quests
  - legendary encounters
  - post-credits portals to a lunar planet and a solar planet
- **Game modes:** Standard, Randomizer, Nuzlocke, and Sandbox (a debug mode with every item, teleporting and quest skipping).
- **Extras:** procedurally generated sound effects, saving and loading, and an options menu.

## Running the game

You'll need Python 3.8+ and these packages:

```bash
pip install pygame pytmx numpy
python main.py
```

`numpy` is only needed to regenerate sound effects with `tools/make_sfx.py`.

## Controls

| Key | Action |
|---|---|
| W A S D | Move / move the menu cursor |
| Hold Space | Run |
| J | Talk, interact, confirm |
| I | Open the menu |
| Space | Back / close |
| + / − | Zoom in / out |

There's a full list in-game under **Menu → Options → Controls**. In Sandbox mode it also lists the debug keys, such as Ctrl+Z to teleport and Ctrl+Q to jump to a quest step.

## Repo layout

```
main.py          Entry point — creates the Game and runs it
game.py          The engine: game loop, state stack, world loading, battles,
                 catching, XP/evolution, cutscenes and story events, saving
player.py        Player movement, collision and encounter checks
npc.py           NPCs: trainers (line-of-sight battles), guards, story characters
screens.py       Every UI screen: battle UI, menus, party, bag, Dinodex,
                 objectives/quests, options, title screen...
config.py        Settings and paths: screen size, fonts, sprites, items,
                 and which NPCs stand where in each map
data.py          Game data: dino species, moves, type chart, trainers,
                 wild encounter zones, doors/teleports, portal spots
story.py         Story beats, the quest list and the sandbox quest steps
moves.py         Battle move animations
randomizer.py    Randomizer mode logic
sfx.py           Sound effects and audio settings

ANIM/            Visual effects: battle transitions, catch/send-out animations,
                 surfing, grass/water effects, sky backgrounds, the Lake Meridian
                 lights, celestial portals, legendary intros, credits
tools/           Scripts that generate assets in code:
                   make_sfx.py      all sound effects
                   make_planets.py  the planet tilesets, maps and battle backgrounds
                   make_mansion.py  the Episc Chateau tileset
info/            Notes — TILED_INFO.txt documents map-making conventions
PRD.md           In-depth design / project reference document

assets/
  MAPS/          Individual Tiled maps (.tmx)
  WORLD/         .world files that stitch maps together (LOST_REGION.world is
                 the overworld) and standalone maps (houses, gyms, planets)
  TILESET/       Tilesets (.tsx + .png)
  DINOS/         Dino sprites — FRONT/ and BACK/
  NPC/           NPC sprite sheets and overworld sprites
  Items/ Badges/ SCREENS/ SOUND/ Jet/ ...   Item icons, badges, backgrounds, audio, player sprites
```

## Making changes

- **Maps** are edited in [Tiled](https://www.mapeditor.org/). Tile behavior (collision, encounters, doors) comes from custom tile properties. See `info/TILED_INFO.txt` for the properties, layer order and handy teleport coordinates.
- **Dinos, moves, trainers and wild spawns** live in `data.py`. Sprites are matched by name in `assets/DINOS/FRONT` and `assets/DINOS/BACK`.
- **NPC placement** is in `config.py` (`WORLD_NPCS`). Their dialogue is in `game.py` (`_interact_story_npc`).
- **Generated assets** (sounds, planets) should be changed in their script under `tools/` and regenerated, not edited by hand. Note that re-running `make_planets.py` overwrites the planet maps.
- **Save files** (`dinopodds_save.json`) and audio settings (`settings.json`) are written next to `main.py`.

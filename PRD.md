# DinoPodds — Project Reference Document

## What This Is

DinoPodds is a Pokemon GBA-style game built in Python with Pygame. The player controls a character named Jet who walks around a stitched-together Tiled world, encounters wild dinos, catches them, battles trainers and gym leaders, and levels up their team. Layered on top of the core catch/battle/level loop is a scripted story: an eclipse-driven intro, two working gyms, a rival, a "Shadow Team" antagonist faction, and several NPC-escort cutscenes. The design target is feature parity with Pokemon FireRed/Emerald — the GBA era — applied to an original IP with custom creatures called "dinos."

This document exists so Claude understands the full project context at the start of every session, without needing to rediscover it from the code. It reflects the state of the project as of 2026-08; re-verify specifics against the code before relying on exact numbers (species/move/trainer counts, in particular, change often).

---

## Tech Stack

- **Language:** Python 3 (virtualenv at `dino/`)
- **Engine:** Pygame
- **World:** Tiled maps (`.tmx`), stitched into one continuous world via a Tiled `.world` file (`assets/WORLD/LOST_REGION.world`) and loaded with `pytmx`
- **Tile size:** 32×32 pixels
- **Screen:** 640×480 @ 60 FPS, with camera zoom (default 1.25×)
- **Art:** Custom pixel art sprites (.png)
- **Fonts:** Pixeloid Sans / Pixeloid Mono (pixel-style fonts), loaded via `config.FONT_DEFS`
- **Save format:** Single JSON file, `dinopodds_save.json`, at the project root

---

## File Map

| File | Purpose |
|---|---|
| `main.py` | Entry point — constructs `Game` and calls `run()` |
| `game.py` | Main game engine (~5,200 lines): state stack, world loading/stitching, encounters, single & double battles, XP, evolution, capture, save/load, story-event dispatch, day/night, camera |
| `player.py` | Player sprite: grid movement/animation, collision, encounter/zone-banner triggering |
| `screens.py` | All UI screens (~3,150 lines) — see **UI Screens** below |
| `config.py` | Global config: colors, screen size, fonts, sprite/tileset paths, NPC sheets, per-world NPC placement table, items, badges, encounter-dino image paths |
| `data.py` | Game data (~1,050 lines): dino species (`DINODEX_DATA`, `DINO_DATA`), moves (`MOVE_DATA`), type chart (`TYPE_DATA`), trainers (`TRAINER_DATA`), encounter zones (`ENCOUNTER_ZONES`, `ZONE_REGIONS`), route/town banner strips |
| `story.py` | Scripted story events (`STORY_EVENTS`, fired via story flags) and the ordered quest checklist used by the sandbox quest-debug menu (`QUEST_STEPS`) |

### Assets

```
assets/
  MAPS/           — Tiled .tmx map files (~45 maps: towns, routes, gyms, interiors, corn maze, Lake Meridian...)
  WORLD/          — LOST_REGION.world — stitches all overworld .tmx maps into one grid via pixel offsets
  TILESET/        — Shared .tsx tilesets + their .png sheets, referenced by the .tmx maps
  DINOS/FRONT/    — Dino front sprites (wild battle / dex / party icon)
  DINOS/BACK/     — Dino back sprites (player-side battle view)
  NPC/            — NPC spritesheets (4x4: row=direction, col=still/walk)
  Items/          — Item & ball icons
  Badges/         — Gym badge icons
  SCREENS/        — Full-screen backgrounds (battle backdrops, type chart, title, etc.)
  info/TILED_INFO.txt — Tiled authoring notes: custom tile properties, layer conventions, quick-teleport coords, route/town crossing tile coordinates
```

---

## World / Map System

The overworld is **not** a single CSV grid anymore — it's a set of individually-authored Tiled `.tmx` maps (32×32 tiles, typically 20×15 tiles / 640×480px each), stitched into one continuous tile grid at load time:

- `assets/WORLD/LOST_REGION.world` lists every overworld `.tmx` file plus its pixel `(x, y)` offset. `Game.load_world()` loads each map with `pytmx`, converts each tile's local coordinates into world-tile coordinates using that offset, and merges everything into global lookup sets/dicts: `solid_tile_coords`, `encounter_tile_coords`, `tile_types`, `entrance_tile_coords`, `exit_tile_coords`.
- Per-tile custom properties (authored in Tiled, documented in `assets/info/TILED_INFO.txt`) drive behavior: `collision`, `encounter`, `type` (grass/water/tallgrass/sand/cave/ball/heal/buy), `entrance`/`entrance_id`, `exit`, `npc`, `battle`.
- `world_bounds` is the bounding box of *all* loaded maps' tile ranges — player movement is clamped to it, but it's a rectangle, not a precise outline, so areas inside the box that no map occupies render as an untextured void with no collision unless something (a wall of solid tiles, or another map) blocks it. `TREE_BLOCK*` / `*_FILL_*` maps exist specifically to plug such gaps.
- Small interior maps (homes, DinoCenter, gyms, lab) are loaded individually via `_load_single_tmx()` rather than through the `.world` file, and swapped in/out as `current_world_file` changes (e.g. walking through a door).
- Regions currently built: Silverleaf (start town) → Route 1 (4 sub-maps) → Sierra Town → Route 2 (multiple sub-maps + the Corn Maze, 5 sub-maps) → Elder Town (Town 2, 3 sub-maps) → Route 3 (2 sub-maps) → Lake Meridian (7 sub-maps). Interiors: `HOME_JET`/`HOME_JET2` (player house), `DINOCENTER`, `RESEARCH_LAB`, `GYM1`, `GYM2`.
- Crossing into a new route/town shows a top-left banner naming the area, driven by `ZONE_BANNER_LOOKUP` (short tile strips + the direction of travel that triggers them) in `data.py`.

---

## Core Systems

### Movement
Grid-based tile movement with smooth interpolation (`player.py`), WASD input, 4-directional, sprint on Space. Collision checks the global `solid_tile_coords` set plus item pickups; movement is also clamped to `world_bounds`.

### Encounter System
Stepping on an `encounter` tile has a per-step chance to trigger `Game.trigger_encounter()`. Which dino appears is zone-based: `get_zone_for_tile()` maps the player's tile to a named zone via `ZONE_REGIONS` (rectangular regions) or falls back to the tile's Tiled `type` property; `ENCOUNTER_ZONES` (10 zones as of this writing) then defines a weighted dino pool and level range per zone. Individual pool entries can be day- or night-gated (`pick_zone_dino()` checks `self.night_active`).

### Battle System
Turn-based combat, both **single** and **double** battles (`DoubleBattleUI`, rotating multi-dino trainer fights — used in the Vanessa/grunt story battle). Flow:
1. Player selects: Fight / Bag / Party / Run
2. Move accuracy checked → damage calculated, priority moves and abilities (stat boosts, DoT, heal, recoil, lock, field effects) resolved
3. Enemy AI picks a move
4. Faint detection → forced party swap
5. Post-battle: XP award, level-up checks, evolution checks

**Damage formula:** `((2*level/7 * atk * power / def / 50 + 2) * STAB * effectiveness/10) * random/255`
**STAB:** 1.5× if move type matches dino type.
**Type effectiveness:** 11-type chart (Aqua, Magma, Earth, Dark, Light, Spike, Flying, Rock, Lightning, Ice, Ancient) defined per-type as `super_eff` / `weak_eff` / `resist` / `weak_to` lists in `TYPE_DATA`.

### Trainer Battles & NPCs
NPCs are placed per-world-file in `config.WORLD_NPCS` as `(sprite_key, tile_x, tile_y, facing, sight_range, npc_type)`. Trainer-type NPCs have line-of-sight detection (`sight_range`) and initiate a walk-up + dialogue + battle sequence; some appear in pairs for double battles. `npc_type` also covers `healer` (DinoCenter), `shop` (DinoMart), and `story` (lore/cutscene props). One NPC (Abby) can follow the player as an escort during a scripted sequence.

### Capture System
Using a ball item (see **Items**) on a weakened wild dino. Success → captured dino joins party (max 5) or goes to the box. Failure → enemy takes a turn. XP is awarded on capture at a reduced multiplier.

### Party / Box Management
Active party: max 5 dinos (`PARTY_LIMIT`). Box: unlimited storage (`BoxScreen`). `PartyScreen` allows swapping dinos in/out. During battle, a fainted active dino forces a swap.

### XP & Leveling
XP is split between the active dino and the bench by a fixed table (`ACTIVE_XP_MULT_SOLO`/`_PARTY`, `BENCH_XP_MULT` in `data.py`) so the on-screen "gained X XP" message and the actual XP award can't drift apart. Multi-level-up in one battle is supported. New moves are auto-learned into open moveset slots (up to 4); once 4 slots are full, further learned moves are currently just **not** added — there's no forced-forget UI yet.

### Evolution System
A species can define an `evolve: {level: 'TargetName'}` in `DINO_DATA`. On level-up past the threshold, stats/moveset are recalculated, the sprite swaps, and a message sequence plays. Current chains: Corlave→Anemamace (19), Creuw→Luna (16), Floravel→Palidian (19), Netaslam→Netyrant (22), Volkit→Tygraflare (19), Prickly→Cyflactus (21).

### Story & Quest System
`story.py`'s `STORY_EVENTS` list defines one-shot scripted events (a `new_game` trigger, or `{"requires_flags": [...], "location": ...}`), each of which can show messages, award items/coins/dinos, and set flags — flags persist in the save file and gate later content. Beyond the declarative list, the current story arc (eclipse intro → Amber's missing-dino fetch quest → Gym 1 vs. Skyy → Corn Maze folklore reveal → Abby's solar-panel escort mission → Shadow Team (Vanessa + grunts) double-battle confrontation) is largely hand-coded directly in `game.py`, keyed off the same `story_flags` dict. A **sandbox quest-debug menu** (Ctrl+Q, `QuestDebugScreen`) lets you jump to any milestone in `QUEST_STEPS` for testing, retroactively applying/removing the trainer-defeated and badge flags each step implies.

### Day/Night & Eclipse
`day_night_timer`/`is_night` drive a tinted overlay over the world and battle screens. The intro sequence includes a scripted **eclipse** (day/night cycling paused, darker overlay) that lifts once the player clears Amber's opening fetch quest.

### Gyms & Badges
Two gyms are complete: **Gym 1** (leader Skyy → Sierra/"flying" badge) and **Gym 2** (leader Log → "earth" badge), each with a small roster of gym trainers blocking the path to the leader. `badges_earned` (list, saved/loaded) gates late-game content and is shown on `TrainerCardScreen`; `BadgeEarnedScreen` plays the badge-award animation.

### Shop & Healing
`ShopScreen` sells items from `config.SHOP_ITEMS` (currently DinoPod, Whitepod, Repel) for in-game coins. `healer`-type NPCs (the DinoCenter lady) fully heal the party via a heal animation.

### Message / Dialogue System
A queue-based message system (`queue_messages()`) blocks input and displays sequential dialog boxes, with `on_complete` callbacks to chain events (e.g. XP message → evolution cutscene → return to world). Named story characters get a cropped portrait next to their dialogue (`config.DIALOGUE_PORTRAITS`), and long lines scroll rather than being truncated.

### Save / Load
Single JSON save (`dinopodds_save.json`) captures party/box, story flags, badges, inventory, coins, and world/position state; loaded on continue from the title screen.

---

## Data Structures

### Dino Species (`data.py`)
`DINODEX_DATA` (dex number + flavor text) and `DINO_DATA` (stats/typing/moveset/evolution) are keyed by species name and kept in sync by hand — every species needs an entry in both.

```python
DINODEX_DATA['Anemamace'] = {'number': 3, 'desc': "..."}
DINO_DATA['Anemamace'] = {
    'stats': {'type': ['aqua', 'spike'], 'health': 140, 'attack': 115, 'defense': 120, 'speed': 80},
    'moves': {0: 'Whirlpool+', 1: 'Arise', 8: 'Quick Slash', ...},  # level -> move learned
    'evolve': None,  # or {level: 'TargetSpecies'}
}
```
29 species as of this writing (most recently Rhinecicle and Celestreeyl, added as placeholder stat blocks pending final design/art).

### Move Data (`MOVE_DATA` in data.py)
```python
'Sky Scorch': {'target': 'opponent', 'damage': 120, 'accuracy': 90, 'type': 'flying',
               'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -2, 'target': 'self', 'chance': 100}}
```
79 moves as of this writing. `ability.kind` covers `stat_boost`, `dot`, `heal`, `recoil`, `lock`, and `field` (temporary type-power boosts, speed-swap, etc.). Some moves also set `priority` or `pierces_defend`.

### Type Chart (`TYPE_DATA`)
11 types (aqua, magma, earth, dark, light, spike, flying, rock, lightning, ice, ancient), each with its own `super_eff` / `weak_eff` / `resist` / `weak_to` lists (not a symmetric matrix).

### Trainers (`TRAINER_DATA`)
23 trainers as of this writing — party (dino, level pairs), dialogue, facing/look-around behavior, biome, coin reward, and a rank (`lowest`/`medium`/`rival`/`boss`) used for tuning.

### Items (`config.ITEMS`, `config.BALL_ICONS`)
DinoPod (0.9 catch rate), DinoCapsule, Whitepod (0.95 catch rate), Repel (wards off lower-level wild dinos for 250 steps).

---

## UI Screens (`screens.py`)

| Screen | Purpose |
|---|---|
| `EncounterUI` | Single wild/trainer battle |
| `DoubleBattleUI` | Two-vs-two rotating battles |
| `PartyScreen` | Party management, swap active dino |
| `BoxScreen` | Unlimited storage, box↔party transfer |
| `MoveInfoScreen` | Move detail lookup |
| `ItemsScreen` | Inventory / use items |
| `ShopScreen` | DinoMart purchases |
| `TrainerCardScreen` | Player profile — badges, stats |
| `BadgeEarnedScreen` | Badge-award animation |
| `TitleScreen` | New Game / Continue |
| `DinodexScreen` | Seen/caught dex, sorted by number, per-species type matchups |
| `QuestDebugScreen` | Sandbox quest-jump menu (Ctrl+Q) |

Plus in-world overlays: the message/dialogue box (with portraits), the route/town entrance banner, the level-up UI, and the heal/badge animations.

---

## State Machine

Stack-based (`state_stack`, `push_state()`/`pop_state()`) so menus/battles/dialogue can layer over the world without losing the underlying context.

---

## Design Conventions

- **Pokemon → DinoPodds equivalents:** Pokemon = Dino, Pokeball = DinoPod, Pokedex = Dinodex, Pokemon Center = DinoCenter, Pokemart = DinoMart
- **Type system is original** — 11 custom types, each with its own effectiveness lists (not a Pokemon-style shared matrix)
- **All game balance** (species, moves, type chart, trainers, encounter zones) lives in `data.py`
- **All asset paths, NPC placement, and per-item/badge config** live in `config.py`
- **World geography** lives in Tiled — add/edit `.tmx` maps under `assets/MAPS/`, register new overworld maps in `assets/WORLD/LOST_REGION.world` with correct pixel offsets so they line up with neighbors, and keep tileset `source=` paths relative to the map file's own directory (`assets/MAPS/`) — a bare filename (e.g. `"snowy.tsx"`) will fail to resolve; it needs to be `"../TILESET/snowy.tsx"`.
- **Sprite loading is fallback-safe for player-owned dinos** (`player_dino_images`/`player_dino_front_images` — missing art renders a placeholder square) **but not for the wild-encounter idle-animation path** (`Game.dino_frames`, `config.ENCOUNTER_DINOS_PATHS`) — pointing those at a nonexistent file crashes on boot. Only wire a new species into those once its front/front2 art actually exists.
- **Screens are stateless renderers** — game logic lives in `game.py`; screens display what `game.py` gives them
- **`on_complete` callbacks** are the pattern for chaining sequential events/cutscenes
- **Story progression is flag-based** (`story_flags`, saved/loaded) — new story content should declare its flags and check/set them the same way, and ideally get a corresponding `QUEST_STEPS` entry so it's reachable from the debug menu

---

## Features Roadmap

### Implemented
- [x] Tiled-based, multi-map overworld stitched via a `.world` file
- [x] 4-directional player movement with animation, camera zoom
- [x] Zone-based wild encounters with day/night-gated species pools
- [x] Single and double turn-based battles, with move abilities (stat boosts, DoT, heal, recoil, lock, field effects)
- [x] 11-type effectiveness chart
- [x] Capture mechanics (multiple ball types, different catch rates)
- [x] Party (5) + unlimited box management
- [x] XP, leveling, and evolution (6 chains so far)
- [x] Move learning on level-up (auto-fill up to 4 slots)
- [x] Trainer battles with line-of-sight NPCs, dialogue, and rewards
- [x] Two complete gyms with leaders and badges
- [x] DinoCenter healing, DinoMart shop
- [x] Dinodex (seen/caught tracker with type matchups)
- [x] Day/night cycle with a scripted eclipse story beat
- [x] Escort/follower NPC mechanic
- [x] Save/load (JSON)
- [x] Sandbox quest-debug menu for jumping to any story milestone
- [x] Route/town entrance banner notification
- [x] Scrolling dialogue with character portraits

### In Progress / Next Up
- [ ] Move-forget UI (currently, moves learned past the 4-slot cap are just silently dropped)
- [ ] Continuing the story arc past the Vanessa/Shadow Team confrontation
- [ ] Filling out remaining regions (Route 3 / Lake Meridian are mapped but not yet populated with encounters/trainers/story)
- [ ] Finishing Rhinecicle & Celestreeyl (real stats/moves/typing, sprite art, spawn-table and/or trainer placement)

### Planned (GBA Feature Parity)
- [ ] More gyms / a full 8-gym arc + Elite 4 / Champion endgame
- [ ] HM/field moves (e.g. cut trees, surf water)
- [ ] Status effects (burn, paralyze, sleep, freeze, poison)
- [ ] Held items
- [ ] Wild dino flee mechanic
- [ ] Dino happiness / friendship
- [ ] Trading (local or simulated)
- [ ] Sound effects and background music

---

## How to Run

```bash
cd c:\Users\Jk\Documents\Javascript\Dinopodds
python main.py
```

Requires Python 3, Pygame, and pytmx installed in the `dino/` virtual environment.

---

*This file is the source of truth for project context. Keep it updated as new features are added.*

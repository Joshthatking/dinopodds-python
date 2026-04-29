# DinoPodds — Project Reference Document

## What This Is

DinoPodds is a Pokemon GBA-style game built in Python with Pygame. The player controls a character named Jet who walks around a tile-based CSV world, encounters wild dinos, catches them, battles trainers, and levels up their team. The design target is feature parity with Pokemon FireRed/Emerald — the GBA era — applied to an original IP with custom creatures called "dinos."

This document exists so Claude understands the full project context at the start of every session, without needing to rediscover it from the code.

---

## Tech Stack

- **Language:** Python 3
- **Engine:** Pygame
- **World:** Tile-based CSV map (`assets/MapAssets/MAP_DINO.csv`)
- **Tile size:** 32x32 pixels
- **Screen:** 640x480 @ 60 FPS
- **Art:** Custom pixel art sprites (.png), Aseprite source files (.ase)
- **Fonts:** Pixeloid Sans / Pixeloid Mono (pixel-style fonts)

---

## File Map

| File | Purpose |
|---|---|
| `main.py` | Entry point — initializes and runs the Game |
| `game.py` | Main game engine (~1450 lines): state machine, encounters, battles, XP, evolution, camera |
| `player.py` | Player sprite: movement, animation, collision, encounter triggering |
| `screens.py` | All UI screens (~1460 lines): EncounterUI, PartyScreen, ItemsScreen, Menu, MessageBox, LevelUpUI |
| `config.py` | Global config: colors, screen size, fonts, tile paths, dino stat tables, spawn points, item defs |
| `data.py` | Game data: dino species, move data, type chart, XP formulas, trainer data |

### Assets

```
assets/
  DINOS/          — Dino sprite sheets (idle, encounter, attack)
  Jet/            — Player walk animations (4 directions, 4 frames each)
  MapAssets/      — World tiles (grass, water, tree, buildings) + MAP_DINO.csv
  Items/          — Item icons, UI icons, pixel fonts
  Vusion/         — Additional Vusion dino animations
```

---

## Map System

The world is a CSV grid (~97 rows × 45 columns) where each cell is a tile code:

| Code | Tile | Walkable | Notes |
|---|---|---|---|
| `G` | Grass | Yes | Plain walkable ground |
| `g` | Spawn grass | Yes | 15% encounter rate per step |
| `W` | Water | No | Solid obstacle |
| `T` | Tree (large) | No | Solid obstacle |
| `t` | Tree (small) | No | Solid obstacle |

Camera follows the player with zoom support (1.0×–1.75×). Entities like the DinoCenter building are placed at fixed tile coordinates (currently tile 36,28). Player spawns at tile (33, 29).

---

## Core Systems

### Movement
Grid-based tile movement with smooth interpolation at 128 px/sec. WASD input, 4-directional. Collision against solid tiles and entity hitboxes.

### Encounter System
Stepping on a `g` tile triggers a 15% random encounter. Encounters are zone-based — each zone defines which dino species can appear and at what level range. Zones defined in `config.py`: `starter_grass`, `deep_jungle`, `volcano_top`.

### Battle System
Turn-based combat, player-first. Flow:
1. Player selects: Fight / Bag / Party / Run
2. Move accuracy checked → damage calculated
3. Enemy AI picks random move
4. Faint detection → force party swap if needed
5. Post-battle: XP award, level-up checks, evolution checks

**Damage formula:** `((2*level/7 * atk * power / def / 50 + 2) * STAB * effectiveness/10) * random/255`

**STAB:** 1.5× if move type matches dino type

**Type effectiveness** uses an 11-type chart (Aqua, Magma, Earth, Dark, Light, Spike, Flying, Rock, Lightning, Ice, Ancient) with a 5–20 scale (10 = neutral).

### Capture System
Using a DinoPod (90% base catch rate) on a weakened wild dino. Success → captured dino joins party (max 5) or goes to box. Failure → enemy takes a turn. XP is awarded on capture (50% multiplier).

### Party / Box Management
Active party: max 5 dinos. Box: unlimited storage. Party screen allows swapping dinos in/out (O key). During battle, if the active dino faints, the player is forced to swap to a living party member.

### XP & Leveling
- XP formula: `(level * 1.93)^2` total XP per level
- XP distribution: active dino gets +30% bonus, rest of party splits the remainder equally
- Multi-level-up in a single battle is possible
- Stats recalculate each level: `base_stat * (level / 50)`, HP uses exponent 1.4
- Moves can be learned on level-up (up to 4 moves; forced-forget UI not yet built)

### Evolution System
Species can define an evolution trigger level in `DINO_DATA`. After a level-up, if the dino meets the threshold, evolution begins: stats recalculate, sprite swaps, moveset updates, message sequence plays. Current chain: Corlave → Anemamace at level 17.

### Message System
A queue-based message system (`queue_messages()`) blocks input and displays sequential dialog boxes. Supports `on_complete` callbacks to chain events (e.g., show XP → then evolution cutscene → then return to world).

---

## Data Structures

### Dino Species (`DINO_DATA` in data.py)
```python
{
  "Vusion": {
    "hp": 60, "attack": 65, "defense": 55, "speed": 80,
    "types": ["dark", "magma"],
    "moves": {1: ["Force Shift"], 7: ["Ember Claw"]},
    "evolution": None
  }
}
```
Currently 3 species: **Vusion**, **Anemamace**, **Corlave**

### Move Data (`MOVE_DATA` in data.py)
```python
{
  "Force Shift": {"damage": 40, "accuracy": 95, "ability": None, "type": "dark"}
}
```
Currently 13 moves.

### Type Chart (`TYPE_CHART_VAL`)
11×11 matrix. Values: 5 = not very effective (0.5×), 10 = neutral (1×), 15 = super effective (1.5×), 20 = double effective (2×), 0 = immune.

---

## UI Screens

| Screen | Access | Key Controls |
|---|---|---|
| World/Overworld | Default state | WASD move, J interact, Esc menu |
| Battle/Encounter | Wild encounter or trainer | J select, WASD navigate moves |
| Party Screen | Menu → Party | WASD navigate, O move to/from box |
| Items Screen | Menu → Items | WASD scroll, J use item |
| Main Menu | Esc key | WASD navigate, J select |
| Message Box | Events/dialog | J or Space to advance |
| Level Up UI | Post-battle level-up | J to dismiss |

---

## State Machine

The game uses a **stack-based state system**: `push_state()` / `pop_state()`. States: `world`, `encounter`, `menu`, `party`, `items`. This allows menus to layer over the world and party screens to open during battles without losing context.

---

## Trainer Battles

Trainer data exists in `data.py` (`TRAINER_DATA`). Trainers have a party, dialogue, and a direction they face. Trainer encounter logic is partially scaffolded but not fully wired up. This is a key feature to build out next.

---

## Features Roadmap (GBA-Parity Goals)

### Implemented
- [x] Tile-based overworld with CSV map
- [x] 4-directional player movement with animation
- [x] Camera with zoom
- [x] Wild encounters on spawn tiles
- [x] Turn-based battle system
- [x] Type effectiveness chart (11 types)
- [x] Capture mechanics (DinoPod/DinoCapsule)
- [x] Party management (5-member limit + box)
- [x] XP and leveling system
- [x] Evolution system (level-based)
- [x] Item inventory and item use
- [x] Menu system (party/items/save)
- [x] Message/dialog queue system
- [x] Move learning on level-up

### In Progress / Next Up
- [ ] Trainer battles (NPC walks toward player, initiates battle)
- [ ] Move forget UI (when learning a 5th move)
- [ ] DinoCenter healing (walk up and press J to heal party)
- [ ] Dinopod throw animation in battle
- [ ] Trainer dialogue and pre-battle cutscene

### Planned (GBA Feature Parity)
- [ ] More dino species (target: 20–30)
- [ ] More moves (target: 50+)
- [ ] Gym battles with gym leaders
- [ ] Rival trainer with recurring battles
- [ ] Multiple towns and routes (map expansion)
- [ ] HM/field moves (e.g., cut trees, surf water)
- [ ] PC box with full dino management
- [ ] Save/load system (persistent game state)
- [ ] Status effects (burn, paralyze, sleep, freeze, poison)
- [ ] Held items
- [ ] Multiple capture ball types with different rates
- [ ] Wild dino flee mechanic
- [ ] Dino happiness / friendship
- [ ] Trading (local or simulated)
- [ ] Pokedex / Dinodex (seen/caught tracker)
- [ ] Story/narrative events and scripted cutscenes
- [ ] Sound effects and background music
- [ ] Elite 4 / Champion endgame

---

## Design Conventions

- **Pokemon → DinoPodds equivalents:** Pokemon = Dino, Pokeball = DinoPod, Pokedex = Dinodex, Pokemon Center = DinoCenter
- **Type system** is original (not the Pokemon 18-type chart). 11 custom types with their own chart.
- **All game balance** lives in `data.py` — stats, moves, type chart. Touch that file when rebalancing.
- **All asset paths and configuration** live in `config.py`. Touch that when adding new species art or tiles.
- **Screens are stateless renderers** — game logic lives in `game.py`, screens only display what game.py gives them.
- **State callbacks** (`on_complete`) are the pattern for chaining sequential events. Use this pattern for any new story sequences.
- **No hardcoded paths** in game logic — always route through `config.py` constants.

---

## How to Run

```bash
cd c:\Users\Jk\Documents\Javascript\Dinopodds
python main.py
```

Requires Python 3 and Pygame installed in the `dino/` virtual environment.

---

*This file is the source of truth for project context. Keep it updated as new features are added.*

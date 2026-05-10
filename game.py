import pygame
import pytmx
import json
from player import Player
from npc import NPC
import os
import config
from screens import *
from data import *
import random


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        pygame.display.set_caption('DinoPodds')
        self.clock = pygame.time.Clock()
        self.running = True
        self.state_stack = ['world']

        self.fonts = {name: pygame.font.Font(path, size) for name, (path, size) in config.FONT_DEFS.items()}
        self.camera_x, self.camera_y = 0, 0
        self.zoom = 1.25
        self.render_surface = pygame.Surface((config.WIDTH // self.zoom, config.HEIGHT // self.zoom))
        self.current_world_file = 'LOST_REGION.world'
        self.map_ball_images = {}
        self.map_ball_items = {}
        self._ballwhite_img = pygame.transform.scale(
            pygame.image.load('assets/Items/ballwhite.png').convert_alpha(),
            (config.TILE_SIZE, config.TILE_SIZE))
        self.dino_pickup_popup = None
        (self.world_maps, self.solid_tile_coords, self.encounter_tile_coords,
         self.tile_types, self.entrance_tile_coords, self.exit_tile_coords,
         _init_ball_items) = self.load_world('LOST_REGION.world')
        self.world_bounds = self._compute_world_bounds()
        print(f"[DEBUG] entrance_tile_coords: {self.entrance_tile_coords}")
        print(f"[DEBUG] exit_tile_coords: {self.exit_tile_coords}")

        # DETERMINE PLAYER SPAWN
        self.player = Player(spawn_point='home')
        self.all_sprites = pygame.sprite.Group(self.player)

        self.fade_alpha = 0
        self.fading = False

        # Dino frames & images
        self.dino_frames = {}
        for base in ("Vusion", "Anemamace", "Corlave", "Creuw", "Luna"):
            img1 = pygame.image.load(config.ENCOUNTER_DINOS_PATHS[base]).convert_alpha()
            img2 = pygame.image.load(config.ENCOUNTER_DINOS_PATHS[base + "2"]).convert_alpha()
            self.dino_frames[base] = [img1, img2]

        self.active_dino_index = 0
        self.PARTY_LIMIT = 5
        self.box_dinos = []
        self.player_dino_images = {}        # back sprite — battle only
        self.player_dino_front_images = {}  # front sprite — party/UI
        for name in DINO_DATA:
            front_path = os.path.join(config.DINOS_FRONT, f'{name}.png')
            back_path  = os.path.join(config.DINOS_BACK,  f'{name}_back.png')
            fallback = pygame.Surface((80, 80), pygame.SRCALPHA)
            fallback.fill((100, 100, 200, 200))
            try:
                front_img = load_image(front_path, alpha=True)
            except Exception:
                front_img = fallback
            try:
                back_img = load_image(back_path, alpha=True) if os.path.exists(back_path) else front_img
            except Exception:
                back_img = front_img
            self.player_dino_images[name]       = back_img
            self.player_dino_front_images[name] = front_img
        self.player_dinos = [
            self.create_dino('Vusion', 12),
            self.create_dino('Vusion', 3),
            self.create_dino('Corlave', 5),
            self.create_dino('Corlave', 16),
        ]

        # Screens
        self.menu = Menu(self)
        self.party_screen = PartyScreen(self)
        self.party_screen.reset()
        self.trainer_card_screen = TrainerCardScreen(self)
        self.box_tile_coords = set()
        self.box_screen = BoxScreen(self)

        # Items
        self.item_image = pygame.image.load(config.ITEMS["DinoPod"]['icon']).convert_alpha()
        self.items_on_map = {}
        self._apply_ball_items(_init_ball_items)
        self.inventory = {item: 0 for item in config.ITEMS.keys()}
        self.item_icons = {}
        for key, data in config.ITEMS.items():
            try:
                self.item_icons[key] = pygame.image.load(data["icon"]).convert_alpha()
            except Exception:
                surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                surf.fill((200, 100, 200))
                self.item_icons[key] = surf
        self.item_descriptions = {key: data["description"] for key, data in config.ITEMS.items()}
        self.items_screen = ItemsScreen(self.inventory, self.item_icons, self.item_descriptions, self.fonts)
        self.items_screen.reset()

        # Shop
        self.shop_screen = ShopScreen(self.fonts)
        for item_name in (s['name'] for s in config.SHOP_ITEMS):
            self.shop_screen.icons[item_name] = self.item_icons.get(item_name)

        # Map entities (populated via Tiled object layers in future)
        self.solid_tiles = set()
        self.map_entities = []

        # Message box
        self.message_box = MessageBox(config.WIDTH, self.fonts)

        # Heal animation state
        self.heal_anim = None
        self.yes_no_prompt = None
        self.yes_no_callback = None
        self.ball_icons = {}
        for name, path in config.BALL_ICONS.items():
            try:
                self.ball_icons[name] = pygame.image.load(path).convert_alpha()
            except Exception:
                surf = pygame.Surface((16, 16), pygame.SRCALPHA)
                surf.fill((200, 200, 200))
                self.ball_icons[name] = surf

        # NPCs — populated per-world via WORLD_NPCS config
        self.npcs = []
        self._spawn_world_npcs('LOST_REGION.world')

        # Hit flash state
        self.hit_flash = None   # None | {'target':'player'|'enemy','timer':0,'duration':1.5,'interval':0.08}

        # Battle state
        self.awaiting_switch = False
        self.current_turn = None
        self.encounter_anim = None
        self.is_trainer_battle = False
        self.current_trainer_npc = None
        self.trainer_dino_queue = []
        self.trainer_dinos_total = 0
        self.trainer_dinos_defeated = 0

        # Player stats counters
        self.stats_blackouts        = 0
        self.stats_dinos_fainted    = 0
        self.stats_enemies_defeated = 0

        # Economy
        self.coins       = 1000
        self.repel_steps = 0

        # Trainer card / adventure tracking
        import datetime
        self.adventure_start_date = datetime.date.today()
        self.play_time_seconds    = 0.0
        self.dinos_seen           = set()
        self.badges_earned        = []  # list of badge names/ids, max 8

        # World transitions
        self.world_stack = []          # saved states for returning from interiors
        self.entrance_fade_state = None  # None | 'out' | 'in'
        self.entrance_pending = None
        self.last_dinocenter_world = None  # world file of most-recently visited DinoCenter
        self.last_dinocenter_tile  = None  # (tx, ty) overworld tile just outside it

        # Day/Night Cycle
        self.day_night_timer = 0.0
        self.CYCLE_DURATION = 15 * 60.0  # 900 seconds per phase
        self.is_night = False

################ FORCE DAY NIGHT #############
        self.force_night = None          # None=auto, True=force night, False=force day
        # self.force_night = True
##################################################

        self.dn_transitioning = False
        self.dn_transition_timer = 0.0
        self.DN_TRANSITION_DURATION = 1.0
        self._night_overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        self._night_overlay.fill((30, 15, 60, 150))
        # self._night_overlay.fill((1, 5, 150, 150)) #ECLIPSE?
        self._dn_fade = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._dn_fade.fill((0, 0, 0))

################ ECLIPSE MODE: EVENT OVERLAY #################
        self.event_overlay_active = False   # flip True during special events
        self._event_overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        self._event_overlay.fill((8, 0, 55, 210))   # deep blue-purple, heavier than night
#################################################

    # --- Entity / Collision Helpers ---

    def _add_solid_rect_as_tiles(self, rect):
        ts = config.TILE_SIZE
        for ty in range(rect.top // ts, (rect.bottom - 1) // ts + 1):
            for tx in range(rect.left // ts, (rect.right - 1) // ts + 1):
                self.solid_tiles.add((tx, ty))

    def _add_map_entity(self, name, image, tile_x, tile_y):
        ts = config.TILE_SIZE
        rect = image.get_rect()
        rect.topleft = (tile_x * ts, tile_y * ts)
        self.map_entities.append({"name": name, "image": image, "tile": (tile_x, tile_y), "rect": rect})
        self._add_solid_rect_as_tiles(rect)

    # --- State Stack ---

    @property
    def state(self):
        return self.state_stack[-1]

    def push_state(self, state):
        self.state_stack.append(state)

    def pop_state(self):
        if len(self.state_stack) > 1:
            self.state_stack.pop()

    def pop_to_world(self):
        while len(self.state_stack) > 1:
            self.pop_state()

    def trigger_blackout(self):
        self.stats_blackouts += 1
        for dino in self.player_dinos:
            dino['hp'] = dino['max_hp']

        self.pop_to_world()
        self.fading = False
        self.encounter_anim = None
        self.awaiting_switch = False
        self.is_trainer_battle = False
        self.entrance_fade_state = None

        # Unwind interior world stack back to the overworld
        while self.world_stack:
            prev = self.world_stack.pop()
            if not self.world_stack:
                self._load_world_data(prev['file'])
                self.npcs = prev['npcs']
                for npc in self.npcs:
                    self.solid_tile_coords.add((npc.tile_x, npc.tile_y))

        # Place player at last DinoCenter or home spawn
        if self.last_dinocenter_tile is not None:
            tx, ty = self.last_dinocenter_tile
        else:
            px, py = config.SPAWN_POINTS.get('home', (160, 1248))
            tx, ty = px // config.TILE_SIZE, py // config.TILE_SIZE

        self._place_player(tx, ty)
        self.fade_alpha = 255
        self.entrance_fade_state = 'in'

    # --- Dino Creation ---

    def create_dino(self, name, level):
        base_stats = DINO_DATA[name]['stats']
        max_hp  = HP_Base(base_stats["health"], level)
        attack  = Base_Stats(base_stats["attack"], level)
        defense = Base_Stats(base_stats["defense"], level)
        speed   = Base_Stats(base_stats["speed"], level)

        learned_moves = [move for lvl, move in DINO_DATA[name]['moves'].items() if lvl <= level]
        moveset = []
        for move_name in learned_moves:
            m = MOVE_DATA.get(move_name, {})
            moveset.append({
                "name": move_name,
                "type": m.get("type", "normal"),
                "damage": m.get("damage", 0),
                "accuracy": m.get("accuracy", 100),
            })

        return {
            "name": name,
            "level": level,
            "type": base_stats['type'],
            "hp": max_hp,
            "max_hp": max_hp,
            "attack": attack,
            "defense": defense,
            "speed": speed,
            "moveset": moveset,
            "moves": learned_moves,
            "image": self.player_dino_images[name],
            "front_image": self.player_dino_front_images[name],
            "frames": self.dino_frames.get(name),
            "xp": 0,
            "xp_to_next": LevelXP(level + 1) - LevelXP(level),
            "displayed_xp": 0,
        }

    # --- XP & Leveling ---

    def award_xp(self, dino, amount):
        dino['xp'] += amount
        while dino['xp'] >= dino['xp_to_next']:
            base_stats = DINO_DATA[dino["name"]]['stats']
            prev_hp = HP_Base(base_stats['health'], dino['level'])
            dino['xp'] -= dino['xp_to_next']
            dino['level'] += 1
            dino['xp_to_next'] = LevelXP(dino['level'] + 1) - LevelXP(dino['level'])
            dino['max_hp']  = HP_Base(base_stats["health"], dino['level'])
            dino['attack']  = Base_Stats(base_stats["attack"], dino['level'])
            dino['defense'] = Base_Stats(base_stats["defense"], dino['level'])
            dino['speed']   = Base_Stats(base_stats["speed"], dino['level'])
            dino['hp'] += dino['max_hp'] - prev_hp
            self.message_box.queue_messages(
                [f"{dino['name']} grew to Lv {dino['level']}!"], wait_for_input=True
            )
            evo_target = self.check_evolution(dino)
            if evo_target:
                self.start_evolution(dino, evo_target)
                break

    def _grant_party_xp_and_level_ups(self, xp_gain):
        """Award XP to all alive party members and return level-up messages."""
        msgs = []
        alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
        if not alive:
            return msgs
        active = self.player_dinos[self.active_dino_index]
        for dino in alive:
            bonus = 1.3 if dino is active else 1.0
            dino['xp'] += int(round(xp_gain * bonus))
            while dino['xp'] >= dino['xp_to_next']:
                base_stats = DINO_DATA[dino['name']]['stats']
                prev_hp = HP_Base(base_stats['health'], dino['level'])
                dino['xp'] -= dino['xp_to_next']
                dino['level'] += 1
                dino['xp_to_next'] = LevelXP(dino['level'] + 1) - LevelXP(dino['level'])
                dino['max_hp']  = HP_Base(base_stats['health'], dino['level'])
                dino['attack']  = Base_Stats(base_stats['attack'], dino['level'])
                dino['defense'] = Base_Stats(base_stats['defense'], dino['level'])
                dino['speed']   = Base_Stats(base_stats['speed'], dino['level'])
                dino['hp'] = dino['hp'] + (dino['max_hp'] - prev_hp)
                msgs.append(f"{dino['name']} grew to Lv {dino['level']}!")
        return msgs

    # --- Evolution ---

    def check_evolution(self, dino):
        evo_table = DINO_DATA[dino['name']].get('evolve')
        if not evo_table:
            return None
        for evo_level, evo_target in evo_table.items():
            if dino['level'] >= evo_level:
                return evo_target
        return None

    def do_evolution(self, dino, new_name):
        old_name = dino['name']
        level = dino['level']
        hp_ratio = dino['hp'] / dino['max_hp'] if dino.get('max_hp', 0) > 0 else 1.0

        new_data = DINO_DATA[new_name]
        base_stats = new_data['stats']

        dino['name'] = new_name
        dino['stats'] = base_stats
        dino['image']       = self.player_dino_images[new_name]
        dino['front_image'] = self.player_dino_front_images[new_name]
        if new_name in self.dino_frames:
            dino['frames'] = self.dino_frames[new_name]

        dino['max_hp']  = HP_Base(base_stats['health'], level)
        dino['attack']  = Base_Stats(base_stats['attack'], level)
        dino['defense'] = Base_Stats(base_stats['defense'], level)
        dino['speed']   = Base_Stats(base_stats['speed'], level)
        dino['hp'] = max(1, int(dino['max_hp'] * hp_ratio))

        old_moves = dino.get('moves', [])[:]
        for move in [m for lvl, m in new_data['moves'].items() if lvl <= level]:
            if move not in old_moves:
                old_moves.append(move)
        dino['moves'] = old_moves

        dino['moveset'] = []
        for move_name in dino['moves']:
            m = MOVE_DATA.get(move_name, {})
            dino['moveset'].append({
                "name": move_name,
                "type": m.get("type", "normal"),
                "damage": m.get("damage", 0),
                "accuracy": m.get("accuracy", 100),
            })

        return old_name, new_name

    def start_evolution(self, dino, evo_target):
        old_name = dino['name']
        self.message_box.queue_messages(
            [f"What? {old_name} is evolving!",
             f"Congratulations! Your {old_name} evolved into {evo_target}!"],
            on_complete=lambda: self.do_evolution(dino, evo_target)
        )

    # --- Encounter ---

    def get_player_zone(self, player_x, player_y):
        zone = get_zone_for_tile(player_x, player_y)
        if zone:
            return zone
        return self.tile_types.get((player_x, player_y))

    def trigger_encounter(self):
        self.player.moving = False
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y
        self.player.pos_x = float(self.player.rect.x)
        self.player.pos_y = float(self.player.rect.y)
        self.fading = True
        self.fade_alpha = 0

        tile_x = self.player.rect.x // config.TILE_SIZE
        tile_y = self.player.rect.y // config.TILE_SIZE
        zone = self.get_player_zone(tile_x, tile_y)
        print(f"[ENCOUNTER] tile=({tile_x},{tile_y}) zone={zone}")

        if zone in ENCOUNTER_ZONES:
            zone_data = ENCOUNTER_ZONES[zone]
            dino_key = random.choice(zone_data["dinos"])
            level = random.randint(*zone_data["level_range"])
        else:
            dino_key = "Anemamace"
            level = random.randint(12, 20)

        self.enemy_dino = self.create_dino(dino_key, level)
        self.dinos_seen.add(dino_key)
        self.encounter_ui = EncounterUI(self.fonts)
        self.encounter_text = f"A wild {dino_key} appeared!"
        self.encounter = Encounter(self.fonts, dino_key)

        now = pygame.time.get_ticks()
        frames = self.dino_frames.get(self.enemy_dino['name'], [self.enemy_dino['image']])
        self.encounter_anim = {
            "frames": frames,
            "frame_idx": 0,
            "last_switch": now,
            "interval": 250,
            "start_time": now,
            "duration": 1000,
        }

    def start_trainer_battle(self, npc):
        self.player.moving = False
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y
        self.player.pos_x = float(self.player.rect.x)
        self.player.pos_y = float(self.player.rect.y)
        self.fading = True
        self.fade_alpha = 0
        self.is_trainer_battle = True
        self.current_trainer_npc = npc

        data = TRAINER_DATA.get(npc.trainer_id, {})
        dinos = data.get('dinos', {})
        sorted_keys = sorted(dinos.keys())
        dino_name, dino_level = dinos[sorted_keys[0]]

        self.trainer_dino_queue = [(dinos[k][0], dinos[k][1]) for k in sorted_keys[1:]]
        self.trainer_dinos_total = len(sorted_keys)
        self.trainer_dinos_defeated = 0

        self.enemy_dino = self.create_dino(dino_name, dino_level)
        self.encounter_ui = EncounterUI(self.fonts)
        self.encounter_text = f"Trainer sent out {dino_name}!"
        self.encounter = Encounter(self.fonts, dino_name)

        now = pygame.time.get_ticks()
        frames = self.dino_frames.get(dino_name, [self.enemy_dino['image']])
        self.encounter_anim = {
            "frames": frames,
            "frame_idx": 0,
            "last_switch": now,
            "interval": 250,
            "start_time": now,
            "duration": 1000,
        }

    # --- World Transitions ---

    def _load_world_data(self, world_file):
        self.current_world_file = world_file
        if world_file.endswith('.tmx'):
            result = self._load_single_tmx(world_file)
        else:
            result = self.load_world(world_file)
        (self.world_maps, self.solid_tile_coords, self.encounter_tile_coords,
         self.tile_types, self.entrance_tile_coords, self.exit_tile_coords,
         ball_items) = result
        self.world_bounds = self._compute_world_bounds()
        self.items_on_map = {}
        self._apply_ball_items(ball_items)

    def _load_single_tmx(self, filename):
        """Load one .tmx file directly — used for small interior maps."""
        path = os.path.join('assets/WORLD', filename)
        tmx = pytmx.load_pygame(path, pixelalpha=True)
        ts = config.TILE_SIZE
        solid, encounter, tile_types, entrances, exits, ball_items = set(), set(), {}, {}, set(), {}
        self.box_tile_coords = set()   # reset; populated below if map has a box object
        for layer in tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                above = self._layer_num(layer) >= 4
                for x, y, gid in layer:
                    if not gid:
                        continue
                    props = tmx.get_tile_properties_by_gid(gid) or {}
                    wpos = (x, y)
                    if props.get('collision') and not above:
                        solid.add(wpos)
                    if props.get('encounter'):
                        encounter.add(wpos)
                        if props.get('type'):
                            tile_types[wpos] = props['type']
                    eid = props.get('entrance_id') or (f'{x}_{y}' if props.get('entrance') else None)
                    if eid:
                        entrances[wpos] = eid
                    if props.get('exit'):
                        exits.add(wpos)
            elif isinstance(layer, pytmx.TiledObjectGroup):
                for obj in layer:
                    props = obj.properties or {}
                    ox, oy = int(obj.x // ts), int(obj.y // ts)
                    if props.get('box'):
                        # Tiled object with boolean property "box: true" → PC box terminal
                        for ty in range(oy, int((obj.y + obj.height - 1) // ts) + 1):
                            for tx in range(ox, int((obj.x + obj.width - 1) // ts) + 1):
                                self.box_tile_coords.add((tx, ty))
                    elif props.get('ball'):
                        item_name = props.get('item', 'DinoPod')
                        ball_items[(ox, oy)] = (item_name, getattr(obj, 'image', None))
                    elif props.get('collision'):
                        for ty in range(oy, int((obj.y + obj.height - 1) // ts) + 1):
                            for tx in range(ox, int((obj.x + obj.width - 1) // ts) + 1):
                                solid.add((tx, ty))
                    eid = props.get('entrance_id') or (f'{ox}_{oy}' if props.get('entrance') else None)
                    if eid:
                        entrances[(ox, oy)] = eid
                    if props.get('exit'):
                        exits.add((ox, oy))
        world_maps = [{'tmx': tmx, 'x': 0, 'y': 0,
                        'width': tmx.width * ts, 'height': tmx.height * ts}]
        print(f"[DEBUG] _load_single_tmx({filename}): entrances={list(entrances.items())} exits={list(exits)}")
        return world_maps, solid, encounter, tile_types, entrances, exits, ball_items

    def _place_player(self, tile_x, tile_y):
        self.player.rect.x = tile_x * config.TILE_SIZE
        self.player.rect.y = tile_y * config.TILE_SIZE
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y
        self.player.pos_x = float(self.player.rect.x)
        self.player.pos_y = float(self.player.rect.y)
        self.player.moving = False
        self.update_camera()

    def trigger_entrance(self, entrance_id, tile_x, tile_y):
        print(f"[DEBUG] trigger_entrance called: id={entrance_id} tile=({tile_x},{tile_y})")
        if self.fading or self.entrance_fade_state is not None:
            return
        self.entrance_pending = (entrance_id, tile_x, tile_y)
        self.entrance_fade_state = 'out'
        self.fade_alpha = 0
        self.player.moving = False
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y

    def _do_entrance_teleport(self, pending):
        entrance_id, tile_x, tile_y = pending
        print(f"[DEBUG] _do_entrance_teleport: id={entrance_id}")
        dest = ENTRANCE_DATA.get(entrance_id)
        print(f"[DEBUG] ENTRANCE_DATA lookup: {dest}")
        if not dest:
            return  # no map configured yet, fade back in silently
        self.world_stack.append({
            'file': self.current_world_file,
            'entrance_tile_x': tile_x,
            'entrance_tile_y': tile_y,
            'entrance_facing': self.player.facing,
            'npcs': self.npcs,
        })
        if 'DINOCENTER' in dest['world'].upper():
            _step = {'up': (0, 1), 'down': (0, -1), 'left': (1, 0), 'right': (-1, 0)}
            dx, dy = _step.get(self.player.facing, (0, 1))
            self.last_dinocenter_world = self.current_world_file
            self.last_dinocenter_tile  = (tile_x + dx, tile_y + dy)
        self._load_world_data(dest['world'])
        self._spawn_world_npcs(dest['world'])
        tx, ty = dest['spawn']
        self._place_player(tx, ty)

    def trigger_exit(self):
        if not self.world_stack or self.entrance_fade_state is not None:
            return
        self.entrance_pending = '__exit__'
        self.entrance_fade_state = 'out'
        self.fade_alpha = 0
        self.player.moving = False
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y

    def _do_exit_teleport(self):
        if not self.world_stack:
            return
        prev = self.world_stack.pop()
        self._load_world_data(prev['file'])
        self.npcs = prev['npcs']
        for npc in self.npcs:
            self.solid_tile_coords.add((npc.tile_x, npc.tile_y))
        # Place player one tile behind where they entered, facing back out
        reverse = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        step = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
        dx, dy = step[reverse[prev['entrance_facing']]]
        self._place_player(prev['entrance_tile_x'] + dx, prev['entrance_tile_y'] + dy)

    def _send_next_trainer_dino(self):
        dino_name, dino_level = self.trainer_dino_queue.pop(0)
        self.enemy_dino = self.create_dino(dino_name, dino_level)
        self.encounter_ui.enemy_hp_display = None
        self.encounter_ui.in_fight_menu = False
        self.encounter_ui.xp_frozen = True
        self.encounter_text = f"Trainer sent out {dino_name}!"
        self.encounter = Encounter(self.fonts, dino_name)
        self.message_box.queue_messages(
            [f"Trainer sent out {dino_name}!", "What will you do?"],
            wait_for_input=True
        )

    # --- Map ---

    def load_world(self, filename):
        path = os.path.join('assets/WORLD', filename)
        with open(path) as f:
            world_json = json.load(f)

        world_dir = os.path.dirname(os.path.abspath(path))
        ts = config.TILE_SIZE
        world_maps = []
        solid = set()
        encounter = set()
        tile_types = {}
        entrances = {}  # (tx, ty) -> entrance_id string
        exits = set()   # (tx, ty) tiles that return to previous world
        ball_items = {}  # (tx, ty) -> (item_name, image)

        for m in world_json['maps']:
            tmx_path = os.path.normpath(os.path.join(world_dir, m['fileName']))
            try:
                tmx = pytmx.load_pygame(tmx_path, pixelalpha=True)
            except Exception as e:
                print(f"Skipping {m['fileName']}: {e}")
                continue

            wx, wy = m['x'], m['y']
            wtx, wty = wx // ts, wy // ts

            for layer in tmx.visible_layers:
                if isinstance(layer, pytmx.TiledTileLayer):
                    above = self._layer_num(layer) >= 4
                    for x, y, gid in layer:
                        if not gid:
                            continue
                        props = tmx.get_tile_properties_by_gid(gid) or {}
                        wpos = (wtx + x, wty + y)
                        if props.get('collision') and not above:
                            solid.add(wpos)
                        if props.get('encounter'):
                            encounter.add(wpos)
                            tile_type = props.get('type')
                            if tile_type:
                                tile_types[wpos] = tile_type
                        eid = props.get('entrance_id') or (f'{wpos[0]}_{wpos[1]}' if props.get('entrance') else None)
                        if eid:
                            entrances[wpos] = eid
                        if props.get('exit'):
                            exits.add(wpos)
                elif isinstance(layer, pytmx.TiledObjectGroup):
                    for obj in layer:
                        props = obj.properties or {}
                        ox = wtx + int(obj.x // ts)
                        oy = wty + int(obj.y // ts)
                        if props.get('ball'):
                            item_name = props.get('item', 'DinoPod')
                            ball_items[(ox, oy)] = (item_name, getattr(obj, 'image', None))
                        elif props.get('collision'):
                            tx1 = wtx + int((obj.x + obj.width - 1) // ts)
                            ty1 = wty + int((obj.y + obj.height - 1) // ts)
                            for ty in range(oy, ty1 + 1):
                                for tx in range(ox, tx1 + 1):
                                    solid.add((tx, ty))
                        eid = props.get('entrance_id') or (f'{ox}_{oy}' if props.get('entrance') else None)
                        if eid:
                            entrances[(ox, oy)] = eid
                        if props.get('exit'):
                            exits.add((ox, oy))

            world_maps.append({'tmx': tmx, 'x': wx, 'y': wy, 'width': m['width'], 'height': m['height']})

        return world_maps, solid, encounter, tile_types, entrances, exits, ball_items

    def _compute_world_bounds(self):
        ts = config.TILE_SIZE
        min_tx = min(m['x'] // ts for m in self.world_maps)
        min_ty = min(m['y'] // ts for m in self.world_maps)
        max_tx = max((m['x'] + m['width']) // ts for m in self.world_maps)
        max_ty = max((m['y'] + m['height']) // ts for m in self.world_maps)
        return (min_tx, min_ty, max_tx, max_ty)

    # --- Main Loop ---

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000
            self.events()
            self.update(dt)
            self.draw()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # Block all input during the heal animation
            if self.heal_anim:
                return

            # Yes/No prompt (generic — callback set by whoever opens it)
            if self.yes_no_prompt:
                result = self.yes_no_prompt.handle_event(event)
                if result == 'yes':
                    cb = self.yes_no_callback
                    self.yes_no_prompt = None
                    self.yes_no_callback = None
                    if cb:
                        cb()
                elif result == 'no':
                    self.yes_no_prompt = None
                    self.yes_no_callback = None
                return

            if self.dino_pickup_popup and self.dino_pickup_popup.active:
                self.dino_pickup_popup.handle_event(event)
                if not self.dino_pickup_popup.active:
                    self.dino_pickup_popup = None
                return

            # Message box is processed first, but not while HP bars are animating in battle
            if self.message_box.visible:
                hp_animating = (
                    'encounter' in self.state_stack and
                    hasattr(self, 'encounter_ui') and
                    self.encounter_ui.is_hp_animating(
                        self.player_dinos[self.active_dino_index], self.enemy_dino)
                )
                if not hp_animating:
                    self.message_box.handle_event(event)
                return

            # Block encounter actions while HP bars animate
            if ('encounter' in self.state_stack and hasattr(self, 'encounter_ui') and
                    self.encounter_ui.is_hp_animating(
                        self.player_dinos[self.active_dino_index], self.enemy_dino)):
                continue

            if self.state == 'world':
                self.handle_world_event(event)

            elif self.state == 'menu':
                self.menu.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_i):
                    self.pop_state()

            elif self.state == 'party':
                result = self.party_screen.handle_event(event, self)
                if result == "back":
                    if len(self.state_stack) >= 2 and self.state_stack[-2] == 'menu' and self.state_stack[0] == 'world':
                        self.pop_state()
                        self.pop_state()
                        self.push_state('menu')
                    else:
                        self.pop_state()
                    self.party_screen.reset()
                elif result == 'quit':
                    self.pop_to_world()
                    self.party_screen.reset()

            elif self.state == 'items':
                result = self.items_screen.handle_event(event, self)
                if result == "back":
                    if len(self.state_stack) >= 2 and self.state_stack[-2] == 'menu' and self.state_stack[0] == 'world':
                        self.pop_state()
                        self.pop_state()
                        self.push_state('menu')
                    else:
                        self.pop_state()
                    self.items_screen.reset()
                elif result == 'quit':
                    self.pop_to_world()
                    self.items_screen.reset()
                elif result == 'used':
                    self.pop_state()
                    self.items_screen.reset()

            elif self.state == 'shop':
                result = self.shop_screen.handle_event(event, self)
                if result == 'back':
                    self.pop_state()
                    self.shop_screen.selected_index = 0

            elif self.state == 'trainer_card':
                self.trainer_card_screen.handle_event(event)

            elif self.state == 'box':
                result = self.box_screen.handle_event(event, self)
                if result == 'back':
                    self.pop_state()

            elif self.state == 'encounter':
                # No input of any kind during the intro animation
                if self.encounter_anim is not None:
                    return

                active = self.player_dinos[self.active_dino_index]

                if active.get('hp', 0) <= 0 and not self.awaiting_switch:
                    alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
                    if alive:
                        self.message_box.queue_messages(
                            [f"{active['name']} fainted!"],
                            wait_for_input=True,
                            on_complete=lambda: self.request_party_swap(active['name'])
                        )
                        self.awaiting_switch = True
                    else:
                        self.message_box.queue_messages(
                            ["You blacked out!", "Be careful next time..."], wait_for_input=True, on_complete=self.trigger_blackout
                        )
                    return

                if self.awaiting_switch:
                    return

                if self.enemy_dino.get('hp', 0) <= 0:
                    if not self.message_box.visible:
                        self.pop_to_world()  # safety net: enemy fainted but exit was missed
                    return

                result = self.encounter_ui.handle_input(event, active)

                if isinstance(result, str) and result.startswith("UseMove:"):
                    self.use_player_move_by_name(result.split("UseMove:", 1)[1])
                    return

                if result == "Run":
                    self.pop_to_world()
                elif result == "Bag":
                    self.push_state('items')
                elif result == 'Party':
                    self.push_state('party')

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    self.set_zoom(self.zoom + 0.5)
                elif event.key == pygame.K_MINUS:
                    self.set_zoom(self.zoom - 0.5)

    def check_box_interact(self):
        if self.fading:
            return False
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[self.player.facing]
        for d in range(1, 3):
            if (px + dx * d, py + dy * d) in self.box_tile_coords:
                self.box_screen.reset()
                self.push_state('box')
                return True
        return False

    def handle_world_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_i:
            self.push_state('menu')
        elif event.key == pygame.K_j:
            if self.check_box_interact():
                pass
            elif not self.interact_with_npc():
                self.pickup_item()

    def _spawn_world_npcs(self, world_file):
        self.npcs = []
        for spec in config.WORLD_NPCS.get(world_file, []):
            trainer_id, tx, ty, facing, sight, npc_type = spec
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty,
                      facing=facing, sight_range=sight, npc_type=npc_type)
            self.npcs.append(npc)
            self.solid_tile_coords.add((tx, ty))

    def trigger_heal_sequence(self):
        n = len(self.player_dinos)
        if n == 0:
            return
        fallback = self.ball_icons['DinoPod']
        ball_imgs = [
            self.ball_icons.get(d.get('caught_ball', 'DinoPod'), fallback)
            for d in self.player_dinos
        ]
        self.heal_anim = {'current': 0, 'total': n, 'timer': 0.0,
                          'per_pod': 0.55, 'ball_imgs': ball_imgs}

    def update_heal_anim(self, dt):
        if not self.heal_anim:
            return
        self.heal_anim['timer'] += dt
        if self.heal_anim['timer'] >= self.heal_anim['per_pod']:
            self.heal_anim['timer'] = 0.0
            self.heal_anim['current'] += 1
            if self.heal_anim['current'] >= self.heal_anim['total']:
                for dino in self.player_dinos:
                    dino['hp'] = dino['max_hp']
                self.heal_anim = None
                self.message_box.queue_messages(
                    ["Your Dinos have been healed! Please come again!"],
                    wait_for_input=True)

    def _draw_heal_anim(self, surface):
        anim = self.heal_anim
        healer = next((n for n in self.npcs if n.npc_type == 'healer'), None)
        if not healer:
            return
        ts = config.TILE_SIZE
        ball_imgs = anim['ball_imgs']
        machine_x = healer.tile_x * ts - self.camera_x
        machine_y = (healer.tile_y - 3) * ts - self.camera_y
        offset = -(anim['total'] * 9)
        for i in range(anim['current']):
            small = pygame.transform.scale(ball_imgs[i], (16, 16))
            surface.blit(small, (machine_x + offset + i * 18, machine_y))
        if anim['current'] < anim['total']:
            img = ball_imgs[anim['current']]
            progress = anim['timer'] / anim['per_pod']
            start_y = float(healer.tile_y * ts)
            end_y = float((healer.tile_y - 3) * ts)
            cy = start_y + (end_y - start_y) * progress
            surface.blit(img, (float(healer.tile_x * ts) - self.camera_x,
                                cy - self.camera_y))

    def _open_heal_prompt(self):
        self.yes_no_prompt = YesNoPrompt(
            "Shall I heal your Dinos?", self.fonts, config.WIDTH, config.HEIGHT)
        self.yes_no_callback = self.trigger_heal_sequence

    def interact_with_npc(self):
        if self.fading:
            return False
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[self.player.facing]
        candidates = [(px + dx, py + dy), (px + dx * 2, py + dy * 2)]
        for npc in self.npcs:
            if (npc.tile_x, npc.tile_y) not in candidates:
                continue
            npc.face_toward_player(self.player)
            if npc.npc_type == 'healer':
                self.message_box.queue_messages(
                    ["Welcome to the DinoCenter!"],
                    wait_for_input=True,
                    on_complete=self._open_heal_prompt)
                return True
            if npc.npc_type == 'shop':
                self.message_box.queue_messages(
                    ["Welcome to the DinoMart!", "Take a look at what we have!"],
                    wait_for_input=True,
                    on_complete=lambda: self.push_state('shop'))
                return True
            data = TRAINER_DATA.get(npc.trainer_id, {})
            if npc.defeated:
                dialog = data.get('dialog', {}).get('defeated', ["..."])
                self.message_box.queue_messages(dialog, wait_for_input=True)
                return True
            if npc.state == 'idle':
                dialog = data.get('dialog', {}).get('default', ["..."])
                self.message_box.queue_messages(dialog, wait_for_input=True)
                return True
            return True
        return False

    def _apply_ball_items(self, ball_items):
        for pos in list(self.map_ball_items.keys()):
            self.items_on_map.pop(pos, None)
        self.map_ball_items = {}
        self.map_ball_images = {}
        for (tx, ty), (item_name, img) in ball_items.items():
            self.items_on_map[(tx, ty)] = item_name
            self.map_ball_items[(tx, ty)] = item_name
            self.map_ball_images[(tx, ty)] = img if img is not None else self._ballwhite_img

    def pickup_item(self):
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        if self.player.facing == "up":    py -= 1
        elif self.player.facing == "down": py += 1
        elif self.player.facing == "left": px -= 1
        elif self.player.facing == "right":px += 1
        if (px, py) not in self.items_on_map:
            return
        item_name = self.items_on_map.pop((px, py))
        if item_name in config.DINO_BALL_MAP:
            dino_name = config.DINO_BALL_MAP[item_name]
            new_dino = self.create_dino(dino_name, config.DINO_BALL_LEVEL)
            new_dino['caught_ball'] = 'ballwhite'
            party_full = len(self.player_dinos) >= self.PARTY_LIMIT
            if party_full:
                self.box_dinos.append(new_dino)
            else:
                self.player_dinos.append(new_dino)
            self.dino_pickup_popup = DinoPickupPopup(
                new_dino, self.fonts, party_full, config.WIDTH, config.HEIGHT)
        else:
            self.inventory[item_name] += 1
            self.message_box.queue_messages([f'Picked up a {item_name}!'], wait_for_input=True)

    # --- Update ---

    def update(self, dt):
        self.play_time_seconds += dt
        self.update_day_night(dt)
        self.update_heal_anim(dt)
        self.update_hit_flash(dt)
        self.message_box.update(dt)

        if 'encounter' in self.state_stack and hasattr(self, 'encounter_ui'):
            active = self.player_dinos[self.active_dino_index]
            self.encounter_ui.update(dt, active, self.enemy_dino)

        # Encounter intro animation completion — kept here so draw() never triggers game logic
        if 'encounter' in self.state_stack and self.encounter_anim is not None:
            now = pygame.time.get_ticks()
            if now - self.encounter_anim["start_time"] >= self.encounter_anim["duration"]:
                anim = self.encounter_anim
                self.encounter_anim = None
                self.encounter.current_dino_surface = anim["frames"][0]
                self.enemy_dino["image"] = anim["frames"][0]
                self.message_box.queue_messages(
                    [self.encounter_text, "What will you do?"],
                    wait_for_input=True
                )

        if self.message_box.visible:
            return

        if self.state == 'world':
            if self.entrance_fade_state == 'out':
                self.fade_alpha = min(255, self.fade_alpha + 10)
                if self.fade_alpha >= 255:
                    if self.entrance_pending == '__exit__':
                        self._do_exit_teleport()
                    else:
                        self._do_entrance_teleport(self.entrance_pending)
                    self.entrance_pending = None
                    self.entrance_fade_state = 'in'
            elif self.entrance_fade_state == 'in':
                self.fade_alpha = max(0, self.fade_alpha - 10)
                if self.fade_alpha <= 0:
                    self.fade_alpha = 0
                    self.entrance_fade_state = None
            elif not self.fading:
                keys = pygame.key.get_pressed()
                self.all_sprites.update(keys, self, dt)
                self.update_camera()
                for npc in self.npcs:
                    npc.update(dt, self.player, self)
            else:
                self.fade_alpha += 10
                if self.fade_alpha >= 255:
                    self.fade_alpha = 255
                    self.fading = False
                    self.push_state('encounter')

    # --- Draw ---

    def draw(self):
        self.render_surface.fill(config.BLACK)

        background_state = 'encounter' if 'encounter' in self.state_stack else self.state_stack[0]
        current_state = self.state

        if background_state == 'world':
            self.draw_map_below(self.render_surface)
            ts = config.TILE_SIZE
            for (tx, ty), img in self.map_ball_images.items():
                if (tx, ty) in self.items_on_map:
                    self.render_surface.blit(img, (tx * ts - self.camera_x, ty * ts - self.camera_y))
            for npc in self.npcs:
                npc.draw(self.render_surface, self.camera_x, self.camera_y)
            for sprite in self.all_sprites:
                self.render_surface.blit(sprite.image,
                                         (sprite.rect.x - self.camera_x, sprite.rect.y - self.camera_y))
            self.draw_map_above(self.render_surface)
            if self.heal_anim:
                self._draw_heal_anim(self.render_surface)
            scaled_surface = pygame.transform.scale(self.render_surface, (config.WIDTH, config.HEIGHT))
            self.screen.blit(scaled_surface, (0, 0))

            if self.night_active and not self.dn_transitioning:
                self.screen.blit(self._night_overlay, (0, 0))
            if self.dn_transitioning:
                t = self.dn_transition_timer / self.DN_TRANSITION_DURATION
                alpha = int(255 * (1.0 - abs(t * 2 - 1.0)))
                self._dn_fade.set_alpha(alpha)
                self.screen.blit(self._dn_fade, (0, 0))
            if self.event_overlay_active:
                self.screen.blit(self._event_overlay, (0, 0))

        elif background_state == 'encounter':
            self.encounter.draw(self.screen)
            self.encounter_ui.draw(self.screen, self.player_dinos[self.active_dino_index],
                                   self.enemy_dino, self.encounter_text,
                                   trainer_total=self.trainer_dinos_total if self.is_trainer_battle else 0,
                                   trainer_defeated=self.trainer_dinos_defeated,
                                   pod_icon=self.item_image if self.is_trainer_battle else None)

        if current_state == 'encounter':
            # Compute hit-flash sprite visibility
            _enemy_vis = True
            _player_vis = True
            if self.hit_flash and not self.encounter_anim:
                flash_count = int(self.hit_flash['timer'] / self.hit_flash['interval'])
                vis = (flash_count % 2 == 0)
                if self.hit_flash['target'] == 'enemy':
                    _enemy_vis = vis
                else:
                    _player_vis = vis

            if self.encounter_anim:
                anim = self.encounter_anim
                now = pygame.time.get_ticks()
                if now - anim["last_switch"] >= anim["interval"]:
                    anim["frame_idx"] = (anim["frame_idx"] + 1) % len(anim["frames"])
                    anim["last_switch"] = now
                frame = anim["frames"][anim["frame_idx"]]
                self.encounter.current_dino_surface = frame
                self.encounter.draw(self.screen)
            else:
                self.encounter.draw(self.screen, enemy_visible=_enemy_vis)

            msg_active = self.message_box.visible
            display_text = self.message_box.message[:self.message_box.char_index] if msg_active else self.encounter_text
            msg_awaiting = (msg_active and self.message_box.wait_for_input and
                            self.message_box.char_index >= len(self.message_box.message))
            self.encounter_ui.draw(self.screen, self.player_dinos[self.active_dino_index],
                                   self.enemy_dino, display_text, show_actions=not msg_active,
                                   trainer_total=self.trainer_dinos_total if self.is_trainer_battle else 0,
                                   trainer_defeated=self.trainer_dinos_defeated,
                                   pod_icon=self.item_image if self.is_trainer_battle else None,
                                   msg_awaiting_input=msg_awaiting,
                                   player_visible=_player_vis)

        elif current_state == 'trainer_card':
            self.trainer_card_screen.draw(self.screen)

        elif current_state in ('menu', 'party', 'items', 'shop', 'box'):
            if background_state == 'world' and current_state not in ('shop', 'box'):
                self.draw_overlay()
            if current_state == 'menu':
                self.menu.draw(self.screen)
            elif current_state == 'party':
                self.party_screen.draw(self.screen)
            elif current_state == 'items':
                self.items_screen.draw(self.screen)
            elif current_state == 'shop':
                self.shop_screen.draw(self.screen, self.coins)
            elif current_state == 'box':
                self.box_screen.draw(self.screen, self)

        if self.fading or self.entrance_fade_state is not None:
            fade_surface = pygame.Surface((config.WIDTH, config.HEIGHT))
            fade_surface.set_alpha(self.fade_alpha)
            fade_surface.fill((0, 0, 0))
            self.screen.blit(fade_surface, (0, 0))

        if self.message_box.visible and self.state != 'encounter':
            self.message_box.draw(self.screen)

        if self.dino_pickup_popup and self.dino_pickup_popup.active:
            self.dino_pickup_popup.draw(self.screen)

        if self.yes_no_prompt:
            self.yes_no_prompt.draw(self.screen)

        pygame.display.flip()

    def draw_overlay(self):
        overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

    @property
    def night_active(self):
        if self.force_night is not None:
            return self.force_night
        return self.is_night

    def update_day_night(self, dt):
        if self.dn_transitioning:
            prev = self.dn_transition_timer
            self.dn_transition_timer += dt
            midpoint = self.DN_TRANSITION_DURATION / 2
            if prev < midpoint <= self.dn_transition_timer:
                self.is_night = not self.is_night
            if self.dn_transition_timer >= self.DN_TRANSITION_DURATION:
                self.dn_transitioning = False
                self.dn_transition_timer = 0.0
                self.day_night_timer = 0.0
            return
        if self.state == 'world':
            self.day_night_timer += dt
            if self.day_night_timer >= self.CYCLE_DURATION:
                self.dn_transitioning = True
                self.dn_transition_timer = 0.0

    def _layer_num(self, layer):
        parts = layer.name.split()
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            return 0

    def draw_map_below(self, surface):
        ts = config.TILE_SIZE
        for wmap in self.world_maps:
            ox, oy = wmap['x'] - self.camera_x, wmap['y'] - self.camera_y
            for layer in wmap['tmx'].visible_layers:
                if isinstance(layer, pytmx.TiledTileLayer) and self._layer_num(layer) < 4:
                    for x, y, gid in layer:
                        if gid:
                            img = wmap['tmx'].get_tile_image_by_gid(gid)
                            if img:
                                surface.blit(img, (ox + x * ts, oy + y * ts))
        for (x, y), item_name in self.items_on_map.items():
            if (x, y) in self.map_ball_items:
                continue
            surface.blit(self.item_icons[item_name],
                         (x * ts - self.camera_x, y * ts - self.camera_y))

    def draw_map_above(self, surface):
        ts = config.TILE_SIZE
        for wmap in self.world_maps:
            ox, oy = wmap['x'] - self.camera_x, wmap['y'] - self.camera_y
            for layer in wmap['tmx'].visible_layers:
                if isinstance(layer, pytmx.TiledTileLayer) and self._layer_num(layer) >= 4:
                    for x, y, gid in layer:
                        if gid:
                            img = wmap['tmx'].get_tile_image_by_gid(gid)
                            if img:
                                surface.blit(img, (ox + x * ts, oy + y * ts))
        for ent in self.map_entities:
            surface.blit(ent['image'], (ent['rect'].x - self.camera_x, ent['rect'].y - self.camera_y))

    def update_camera(self):
        render_w = config.WIDTH // self.zoom
        render_h = config.HEIGHT // self.zoom
        self.camera_x = self.player.rect.centerx - render_w // 2
        self.camera_y = self.player.rect.centery - render_h // 2
        min_cx = min(m['x'] for m in self.world_maps)
        min_cy = min(m['y'] for m in self.world_maps)
        max_cx = max(m['x'] + m['width'] for m in self.world_maps) - render_w
        max_cy = max(m['y'] + m['height'] for m in self.world_maps) - render_h
        self.camera_x = max(min_cx, min(self.camera_x, max_cx))
        self.camera_y = max(min_cy, min(self.camera_y, max_cy))

    def set_zoom(self, zoom):
        self.zoom = round(max(1.0, min(1.75, zoom)), 2)
        self.render_surface = pygame.Surface((int(config.WIDTH / self.zoom), int(config.HEIGHT / self.zoom)))
        self.update_camera()

    # --- Battle ---

    def trigger_hit_flash(self, target):
        self.hit_flash = {'target': target, 'timer': 0.0, 'duration': 0.8, 'interval': 0.08}

    def update_hit_flash(self, dt):
        if not self.hit_flash:
            return
        self.hit_flash['timer'] += dt
        if self.hit_flash['timer'] >= self.hit_flash['duration']:
            self.hit_flash = None

    def attempt_catch(self, item_name='DinoPod'):
        if self.inventory.get(item_name, 0) <= 0:
            self.message_box.queue_messages(
                [f"You have no {item_name}s left!"], wait_for_input=True,
                on_complete=self._enemy_turn)
            return
        self.inventory[item_name] = max(0, self.inventory[item_name] - 1)
        catch_rate = config.ITEMS.get(item_name, {}).get("catch_rate", 0.5)
        success = random.random() < catch_rate

        if success:
            base_dino = self.create_dino(self.enemy_dino["name"], self.enemy_dino["level"])
            base_dino["hp"] = min(self.enemy_dino["hp"], base_dino["max_hp"])
            base_dino["xp"] = 0
            base_dino["caught_ball"] = item_name

            alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
            active = self.player_dinos[self.active_dino_index] if self.player_dinos else None

            if alive and active is not None:
                xp_gain = calculate_xp_gain(
                    player_level=active['level'],
                    opponent_level=self.enemy_dino['level'],
                    state_multiplier=0.5,   # catching
                    party_size=len(alive)
                )
                for d in alive:
                    bonus = 1.3 if d is active else 1.0
                    self.award_xp(d, int(round(xp_gain * bonus)))

            to_evolve = [(d, self.check_evolution(d)) for d in self.player_dinos if self.check_evolution(d)]

            if len(self.player_dinos) < self.PARTY_LIMIT:
                self.player_dinos.append(base_dino)
                added_msg = f"{self.enemy_dino['name']} was added to your party!"
            else:
                self.box_dinos.append(base_dino)
                added_msg = f"{self.enemy_dino['name']} was sent to your Box!"

            msgs = [f"You caught {self.enemy_dino['name']}!", added_msg]
            if alive and active is not None:
                msgs.append(f"{active['name']} has gained {int(round(xp_gain * 1.3))} XP!")
                if len(alive) > 1:
                    msgs.append(f"Each party dino gained {xp_gain} XP!")

            def run_evolutions(i=0):
                if i >= len(to_evolve):
                    self.pop_to_world()
                    return
                dino, target = to_evolve[i]
                old_name = dino['name']
                def do_next():
                    old_species, new_species = self.do_evolution(dino, target)
                    self.message_box.queue_messages(
                        [f"Congratulations! Your {old_species} evolved into {new_species}!"],
                        wait_for_input=True,
                        on_complete=lambda: run_evolutions(i + 1)
                    )
                self.message_box.queue_messages(
                    [f"What? {old_name} is evolving!"],
                    wait_for_input=True,
                    on_complete=do_next
                )

            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=lambda: run_evolutions(0))
            return

        self.message_box.queue_messages(
            [f"{self.enemy_dino['name']} broke free!"],
            wait_for_input=True,
            on_complete=self._enemy_turn
        )

    def use_player_move(self, move_index):
        if self.message_box.visible:
            return
        if self.encounter_anim is not None:
            return
        if self.enemy_dino.get('hp', 0) <= 0:
            return
        attacker = self.player_dinos[self.active_dino_index]
        defender = self.enemy_dino

        if move_index < 0 or move_index >= len(attacker['moveset']):
            return

        move      = attacker['moveset'][move_index]
        move_name = move['name']
        power     = max(0, move.get('damage', 0))
        acc       = move.get('accuracy', 100)
        mtype     = move.get('type', 'normal')

        player_first = attacker.get('speed', 0) >= defender.get('speed', 0)

        if player_first:
            if random.random() * 100 > acc:
                self.message_box.queue_messages(
                    [f"{attacker['name']} used {move_name}!", "But it missed!"],
                    wait_for_input=True, on_complete=self._enemy_turn)
                return
            self._apply_player_attack(attacker, defender, move_name, power, mtype,
                                      after=self._enemy_turn)
        else:
            # Enemy is faster — it strikes first, then player attacks if still alive
            def then_player():
                p = self.player_dinos[self.active_dino_index]
                if p.get('hp', 0) <= 0:
                    return
                if random.random() * 100 > acc:
                    self.message_box.queue_messages(
                        [f"{p['name']} used {move_name}!", "But it missed!", "What will you do?"],
                        wait_for_input=True)
                    return
                self._apply_player_attack(p, self.enemy_dino, move_name, power, mtype, after=None)
            self._enemy_turn(after=then_player)

    def _apply_player_attack(self, attacker, defender, move_name, power, mtype, after=None):
        STAB    = stab_multiplier(mtype, attacker['type'])
        eff_val = type_effectiveness_value(mtype, defender['type'])
        rnd     = random_damage_factor()
        atk     = max(1, attacker['attack'])
        dfs     = max(1, defender['defense'])
        lvl     = max(1, attacker['level'])

        raw = Damage(lvl, atk, power, dfs, STAB, eff_val, rnd)
        dmg = max(1, int(raw)) if power > 0 else 0
        defender['hp'] = max(0, defender['hp'] - dmg)
        if dmg > 0:
            self.trigger_hit_flash('enemy')

        msgs = [f"{attacker['name']} used {move_name}!"]
        if eff_val > 10:
            msgs.append("It's super effective!")
        elif 0 < eff_val < 10:
            msgs.append("It's not very effective...")
        elif eff_val <= 0:
            msgs.append("It had no effect...")

        if defender['hp'] <= 0:
            self.stats_enemies_defeated += 1
            self.encounter_ui.in_fight_menu = False
            msgs.append(f"The wild {defender['name']} fainted!")
            alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
            multiplier = 0.9 if self.is_trainer_battle else 0.75
            xp_gain = calculate_xp_gain(
                player_level=attacker['level'],
                opponent_level=defender['level'],
                state_multiplier=multiplier,
                party_size=len(alive)
            )
            level_up_msgs = self._grant_party_xp_and_level_ups(xp_gain)
            xp_msgs = [f"{attacker['name']} has gained {int(round(xp_gain * 1.3))} XP!"]
            if len(self.player_dinos) > 1:
                xp_msgs.append(f"Each party dino gained {xp_gain} XP!")
            xp_msgs.extend(level_up_msgs)

            def handle_evolutions():
                coin_reward = 0
                if self.is_trainer_battle:
                    self.trainer_dinos_defeated += 1
                    if self.trainer_dino_queue:
                        self._send_next_trainer_dino()
                        return
                    if self.current_trainer_npc:
                        self.current_trainer_npc.defeated = True
                        coin_reward = TRAINER_DATA.get(
                            self.current_trainer_npc.trainer_id, {}).get('reward_coins', 0)
                    self.is_trainer_battle = False

                def finish_battle():
                    evolved = False
                    for dino in self.player_dinos:
                        evo_target = self.check_evolution(dino)
                        if evo_target:
                            evolved = True
                            self.start_evolution(dino, evo_target)
                            self.pop_to_world()
                    if not evolved:
                        self.pop_to_world()

                if coin_reward > 0:
                    self.coins += coin_reward
                    self.message_box.queue_messages(
                        [f"You received {coin_reward} coins!"],
                        wait_for_input=True, on_complete=finish_battle)
                else:
                    finish_battle()

            def show_xp():
                self.encounter_ui.unfreeze_xp()
                self.message_box.queue_messages(xp_msgs, wait_for_input=True, on_complete=handle_evolutions)

            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=show_xp)
        else:
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                msgs.append("What will you do?")
                self.message_box.queue_messages(msgs, wait_for_input=True)

    def use_player_move_by_name(self, move_name):
        attacker = self.player_dinos[self.active_dino_index]
        for i, m in enumerate(attacker.get('moveset', [])):
            if m.get('name') == move_name:
                self.use_player_move(i)
                return
        for i, n in enumerate(attacker.get('moves', [])):
            if n == move_name:
                self.use_player_move(i)
                return
        self.message_box.queue_messages(
            [f"{attacker['name']} doesn't know {move_name}.", "What will you do?"], wait_for_input=True
        )

    def _enemy_turn(self, after=None):
        self.encounter_ui.in_fight_menu = False
        defender = self.player_dinos[self.active_dino_index]
        attacker = self.enemy_dino

        if defender.get('hp', 0) <= 0:
            alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
            if alive:
                self.awaiting_switch = True
                self.message_box.queue_messages(
                    [f"{defender['name']} fainted!"],
                    wait_for_input=True,
                    on_complete=lambda: self.request_party_swap(defender['name'])
                )
            else:
                self.message_box.queue_messages(
                    ["You blacked out!", "Be careful next time..."],
                    wait_for_input=True, on_complete=self.trigger_blackout
                )
            return

        if not attacker.get('moveset'):
            msgs = [f"The wild {attacker['name']} is loafing around."]
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                msgs.append("What will you do?")
                self.message_box.queue_messages(msgs, wait_for_input=True)
            return

        move  = random.choice(attacker['moveset'])
        mtype = move.get('type', 'normal')
        power = max(0, move.get('damage', 0))
        acc   = move.get('accuracy', 100)

        if random.random() * 100 >= acc:
            msgs = [f"The wild {attacker['name']} used {move['name']}!", "But it missed!"]
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                msgs.append("What will you do?")
                self.message_box.queue_messages(msgs, wait_for_input=True)
            return

        STAB    = stab_multiplier(mtype, attacker['type'])
        eff_val = type_effectiveness_value(mtype, defender['type'])
        rnd     = random_damage_factor()
        atk     = max(1, attacker['attack'])
        dfs     = max(1, defender['defense'])
        lvl     = max(1, attacker['level'])

        dmg = max(1, int(Damage(lvl, atk, power, dfs, STAB, eff_val, rnd))) if power > 0 else 0
        defender['hp'] = max(0, defender['hp'] - dmg)
        if dmg > 0:
            self.trigger_hit_flash('player')

        msgs = [f"The wild {attacker['name']} used {move['name']}!"]
        if eff_val > 10:       msgs.append("It's super effective!")
        elif 0 < eff_val < 10: msgs.append("It's not very effective...")
        elif eff_val <= 0:     msgs.append("It had no effect...")

        if defender['hp'] <= 0:
            self.stats_dinos_fainted += 1
            alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
            msgs.append(f"{defender['name']} fainted!")
            if alive:
                self.awaiting_switch = True
                self.message_box.queue_messages(
                    msgs, wait_for_input=True,
                    on_complete=lambda: self.request_party_swap(defender['name'])
                )
            else:
                msgs.extend(["You blacked out!", "Be careful next time..."])
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=self.trigger_blackout)
            return

        if after:
            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
        else:
            msgs.append("What will you do?")
            self.message_box.queue_messages(msgs, wait_for_input=True)

    def request_party_swap(self, fainted_name):
        self.awaiting_switch = True
        self.message_box.queue_messages(
            [f"{fainted_name} has fainted!"],
            wait_for_input=True,
            on_complete=self._open_party_forced_swap
        )

    def _open_party_forced_swap(self):
        if self.state_stack[-1] != 'party':
            self.push_state('party')
        self.awaiting_switch = True

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
import story as _story

SAVE_PATH = 'dinopodds_save.json'


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        pygame.display.set_caption('DinoPodds')
        self.clock = pygame.time.Clock()
        self.running = True
        self.state_stack = ['title']

        self.fonts = {name: pygame.font.Font(path, size) for name, (path, size) in config.FONT_DEFS.items()}
        self.camera_x, self.camera_y = 0, 0
        self.zoom = 1.25
        self.render_surface = pygame.Surface((config.WIDTH // self.zoom, config.HEIGHT // self.zoom))
        self.current_world_file = 'LOST_REGION.world'
        self.map_ball_images = {}
        self.map_ball_items = {}
        self.picked_up_world_items = set()  # {(world_file, tx, ty)} — never respawn these
        self._ballwhite_img = pygame.transform.scale(
            pygame.image.load('assets/Items/ballwhite.png').convert_alpha(),
            (config.TILE_SIZE, config.TILE_SIZE))
        self.dino_pickup_popup = None
        (self.world_maps, self.solid_tile_coords, self.encounter_tile_coords,
         self.tile_types, self.entrance_tile_coords, self.exit_tile_coords,
         _init_ball_items) = self.load_world('LOST_REGION.world')
        self.world_bounds = self._compute_world_bounds()
        # print(f"[DEBUG] entrance_tile_coords: {self.entrance_tile_coords}")
        # print(f"[DEBUG] exit_tile_coords: {self.exit_tile_coords}")

        # DETERMINE PLAYER SPAWN
        self.player = Player(spawn_point='home')
        self.all_sprites = pygame.sprite.Group(self.player)

        self.fade_alpha = 0
        self.fading = False

        # Dino frames & images
        self.dino_frames = {}
        for base in ("Vusion", "Anemamace", "Corlave", "Creuw", "Luna", "Prowscar", "Floravel", "Bullicorn", "Netaslam", "Netyrant", "Sortle", "Sharktastrophe", "Magnecrab", "Volkit", "Drafyton", "Auraliz", "Voltzbee", "Teamtwood", "Tygraflare", "Bouldava", "Ghoulflame", "Scarecrux"):
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
        self.player_dinos = []

        # Story / progress
        self.story_flags = {}
        self.sandbox = False

        # Screens
        self.title_screen = TitleScreen(self)
        self.menu = Menu(self)
        self.party_screen = PartyScreen(self)
        self.party_screen.reset()
        self.move_info_screen = None
        self.dinodex_screen = DinodexScreen(self)
        self.trainer_card_screen = TrainerCardScreen(self)
        self.box_tile_coords = set()
        self.box_screen = BoxScreen(self)
        self.type_chart_tile_coords = set()
        self.lore_tile_coords = set()
        self.type_chart_image = pygame.image.load('assets/SCREENS/TYPE_CHARv2.png').convert_alpha()

        # Items
        self.item_image = pygame.image.load(config.ITEMS["DinoPod"]['icon']).convert_alpha()
        self.items_on_map = {}
        self.inventory = {item: 0 for item in config.ITEMS.keys()}
        self.item_icons = {}
        for key, data in config.ITEMS.items():
            try:
                self.item_icons[key] = pygame.image.load(data["icon"]).convert_alpha()
            except Exception:
                surf = pygame.Surface((32, 32), pygame.SRCALPHA)
                surf.fill((200, 100, 200))
                self.item_icons[key] = surf
        self._apply_ball_items(_init_ball_items)
        self.item_descriptions = {key: data["description"] for key, data in config.ITEMS.items()}
        self.items_screen = ItemsScreen(self.inventory, self.item_icons, self.item_descriptions, self.fonts)
        self.items_screen.reset()
        self._dino_picker = None
        self._dino_picker_starters = []

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
        self.cutscene = None
        self.cutscene_flash = None
        self.intro_sequence = None
        self.ball_icons = {}
        for name, path in config.BALL_ICONS.items():
            try:
                self.ball_icons[name] = pygame.image.load(path).convert_alpha()
            except Exception:
                surf = pygame.Surface((16, 16), pygame.SRCALPHA)
                surf.fill((200, 200, 200))
                self.ball_icons[name] = surf

        # NPCs — populated per-world via WORLD_NPCS config
        self.defeated_trainers = set()
        self.npcs = []
        self._spawn_world_npcs('LOST_REGION.world')
        self._maybe_add_gym_blocker()
        self._maybe_add_skyy()

        # Hit flash state
        self.hit_flash = None   # None | {'target':'player'|'enemy','timer':0,'duration':1.5,'interval':0.08}
        self._post_xp_callback = None
        self._post_trainer_battle_cb = None
        self.badge_earned_screen = None

        # Battle state
        self.awaiting_switch = False
        self.current_turn = None
        self.encounter_anim = None
        self.is_trainer_battle = False
        self.is_double_battle    = False
        self.forced_walk_npc     = None
        self.forced_walk_npc2    = None
        self.double_phase        = None   # None | 'p1' | 'p2'
        self.double_p1_queued    = None   # {'move_name':str,'target_is_e2':bool} | {'action':'defend'}
        self.double_p2_queued    = None
        self.double_replace_slot = None   # None | 0 | 1
        self.double_replace_queue = []    # slots still needing replacement
        self.field_effects = []
        self.defend_uses_remaining = 3
        self.enemy_defend_uses_remaining = 3
        self.current_trainer_npc = None
        self.current_trainer_npc2 = None
        self.enemy_dino2 = None
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
        self._night_overlay_battle = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        self._night_overlay_battle.fill((30, 15, 60, 70))
        self._dn_fade = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._dn_fade.fill((0, 0, 0))

################ ECLIPSE MODE: EVENT OVERLAY #################
        self.event_overlay_active = False   # flip True during special events
        self._event_overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        self._event_overlay.fill((8, 0, 55, 210))   # deep blue-purple, heavier than night
        self._event_overlay_battle = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        self._event_overlay_battle.fill((8, 0, 55, 100))
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
        self.awaiting_switch = False
        self.fading = False

    def trigger_blackout(self):
        self.stats_blackouts += 1
        for dino in self.player_dinos:
            dino['hp'] = dino['max_hp']
            dino['stat_stages'] = {"attack": 0, "defense": 0, "speed": 0}
            dino['defending']   = False

        self.pop_to_world()
        self.fading = False
        self.encounter_anim = None
        self.awaiting_switch = False
        self.is_trainer_battle = False
        self.is_double_battle    = False
        self.enemy_dino2         = None
        self.forced_walk_npc     = None
        self.forced_walk_npc2    = None
        self.double_phase        = None
        self.double_p1_queued    = None
        self.double_p2_queued    = None
        self.double_replace_slot = None
        self.double_replace_queue = []
        self.field_effects = []
        self.defend_uses_remaining = 3
        self.enemy_defend_uses_remaining = 3
        self.entrance_fade_state = None
        self._post_trainer_battle_cb = None

        # Reset Gray for rechallenge if player blacked out before winning
        for npc in self.npcs:
            if (getattr(npc, 'trainer_id', '') == 'gray'
                    and not npc.defeated
                    and npc.state == 'done'):
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                hx, hy = getattr(npc, 'home_tile', (7, 5))
                npc.tile_x, npc.tile_y = hx, hy
                npc.pos_x = float(hx * config.TILE_SIZE)
                npc.pos_y = float(hy * config.TILE_SIZE)
                npc.target_x, npc.target_y = npc.pos_x, npc.pos_y
                npc.rect.topleft = (int(npc.pos_x), int(npc.pos_y))
                npc.facing = getattr(npc, 'home_facing', 'up')
                npc.is_moving = False
                npc.state = 'idle'
                self.solid_tile_coords.add((hx, hy))

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

    # --- Title / New Game / Save-Load ---

    def new_game(self):
        import datetime
        self.story_flags = {}
        self.sandbox = False
        self.player_dinos = []
        self.box_dinos = []
        self.coins = 1000
        self.inventory = {item: 0 for item in config.ITEMS.keys()}
        self.items_screen.inventory = self.inventory
        self.badges_earned = []
        self.dinos_seen = set()
        self.stats_blackouts = 0
        self.stats_dinos_fainted = 0
        self.stats_enemies_defeated = 0
        self.play_time_seconds = 0.0
        self.adventure_start_date = datetime.date.today()
        self.world_stack = []
        self._load_world_data('HOME_JET2.tmx')
        self._spawn_world_npcs('HOME_JET2.tmx')
        # Adjust tile coords to match your Tiled spawn point in HOME_JET2.tmx
        self._place_player(7, 5)
        self.intro_sequence = IntroSequence(self)
        self.state_stack = ['intro']

    def sandbox_mode(self):
        self.story_flags = {e['id']: True for e in _story.STORY_EVENTS}
        self.story_flags['encounters_unlocked'] = True
        self.sandbox = True
        self.player_dinos = [
            self.create_dino('Vusion', 40),
            self.create_dino('Vusion', 3),
            self.create_dino('Netaslam', 21),
            self.create_dino('Corlave', 16),
        ]
        self.box_dinos = []
        self.coins = 99999
        self.inventory = {item: 99 for item in config.ITEMS.keys()}
        self.items_screen.inventory = self.inventory
        self.badges_earned = []
        self.dinos_seen = set(DINO_DATA.keys())
        px, py = config.SPAWN_POINTS.get('home', (352, 1392))
        self.player.rect.topleft = (px, py)
        self.player.pos_x = float(px)
        self.player.pos_y = float(py)
        self.player.target_x = px
        self.player.target_y = py
        self.state_stack = ['world']

    def exit_to_title(self):
        self.pop_to_world()
        self.state_stack = ['title']
        self.title_screen.reset()

    def save_game(self):
        data = {
            'coins': self.coins,
            'inventory': self.inventory,
            'world': self.current_world_file,
            'player_x': self.player.rect.x,
            'player_y': self.player.rect.y,
            'party': [self._dino_to_dict(d) for d in self.player_dinos],
            'box': [self._dino_to_dict(d) for d in self.box_dinos],
            'story_flags': self.story_flags,
            'sandbox': self.sandbox,
            'badges': self.badges_earned,
            'play_time': self.play_time_seconds,
            'dinos_seen': list(self.dinos_seen),
            'picked_up_world_items': [list(entry) for entry in self.picked_up_world_items],
            'defeated_trainers': list(self.defeated_trainers),
            'stats': {
                'blackouts': self.stats_blackouts,
                'dinos_fainted': self.stats_dinos_fainted,
                'enemies_defeated': self.stats_enemies_defeated,
            },
        }
        with open(SAVE_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        self.message_box.queue_messages(["Game saved!"], wait_for_input=True)

    def load_game(self):
        try:
            with open(SAVE_PATH) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return
        self.coins = data.get('coins', 0)
        self.inventory = {**{item: 0 for item in config.ITEMS.keys()}, **data.get('inventory', {})}
        self.items_screen.inventory = self.inventory
        self.story_flags = data.get('story_flags', {})
        self.day_night_timer    = 0.0
        self.is_night           = False
        self.dn_transitioning   = False
        self.dn_transition_timer = 0.0
        self.event_overlay_active = (
            self.story_flags.get('amber_intro_done', False) and
            not self.story_flags.get('gym1_accessible', False)
        )
        self.sandbox = data.get('sandbox', False)
        self.badges_earned = data.get('badges', [])
        self.play_time_seconds = data.get('play_time', 0.0)
        self.dinos_seen = set(data.get('dinos_seen', []))
        self.picked_up_world_items = {tuple(e) for e in data.get('picked_up_world_items', [])}
        self.defeated_trainers = set(data.get('defeated_trainers', []))
        for npc in self.npcs:
            if getattr(npc, 'trainer_id', None) in self.defeated_trainers:
                npc.defeated = True
        s = data.get('stats', {})
        self.stats_blackouts = s.get('blackouts', 0)
        self.stats_dinos_fainted = s.get('dinos_fainted', 0)
        self.stats_enemies_defeated = s.get('enemies_defeated', 0)
        self.player_dinos = [self._dict_to_dino(d) for d in data.get('party', [])]
        self.box_dinos = [self._dict_to_dino(d) for d in data.get('box', [])]
        px = data.get('player_x', config.SPAWN_POINTS['home'][0])
        py = data.get('player_y', config.SPAWN_POINTS['home'][1])
        self.player.rect.topleft = (px, py)
        self.player.pos_x = float(px)
        self.player.pos_y = float(py)
        self.player.target_x = px
        self.player.target_y = py
        self.state_stack = ['world']
        self._maybe_add_gym_blocker()
        self._maybe_add_skyy()

    def _dino_to_dict(self, dino):
        return {k: v for k, v in dino.items() if k not in ('image', 'front_image', 'frames')}

    def _dict_to_dino(self, data):
        data = dict(data)
        name = data['name']
        data['image'] = self.player_dino_images.get(name)
        data['front_image'] = self.player_dino_front_images.get(name)
        data['frames'] = self.dino_frames.get(name)
        return data

    # --- Story Events ---

    def _run_story_event(self, event_id):
        if self.story_flags.get(event_id):
            return
        event = next((e for e in _story.STORY_EVENTS if e['id'] == event_id), None)
        if event:
            self._execute_story_event(event)

    def _execute_story_event(self, event):
        msgs = event.get('messages', [])

        def on_complete():
            for item, qty in event.get('award_items', {}).items():
                self.inventory[item] = self.inventory.get(item, 0) + qty
            self.coins += event.get('award_coins', 0)
            for spec in event.get('award_dinos', []):
                dino = self.create_dino(spec['name'], spec['level'])
                if len(self.player_dinos) < self.PARTY_LIMIT:
                    self.player_dinos.append(dino)
                else:
                    self.box_dinos.append(dino)
            for flag in event.get('sets_flags', []):
                self.story_flags[flag] = True
            next_id = event.get('next_event')
            if next_id:
                self._run_story_event(next_id)

        if msgs:
            self.message_box.queue_messages(msgs, on_complete=on_complete, wait_for_input=True)
        else:
            on_complete()

    def check_story_events(self):
        if self.sandbox or self.message_box.visible:
            return
        tx = self.player.rect.x // config.TILE_SIZE
        ty = self.player.rect.y // config.TILE_SIZE
        zone = self.get_player_zone(tx, ty)
        for event in _story.STORY_EVENTS:
            eid = event['id']
            if self.story_flags.get(eid):
                continue
            trigger = event.get('trigger', {})
            if trigger == 'new_game':
                continue
            if isinstance(trigger, dict):
                if not all(self.story_flags.get(f) for f in trigger.get('requires_flags', [])):
                    continue
                req_zone = trigger.get('location')
                if req_zone and zone != req_zone:
                    continue
                self._execute_story_event(event)
                break

    # --- Dino Creation ---

    def apply_nature_boost(self, dino):
        for stat, pct in NATURE_BOOSTS.get(dino.get("nature"), {}).items():
            if stat == "hp":
                dino["max_hp"] += max(1, round(dino["max_hp"] * pct))
            else:
                bonus = max(1, round(dino[stat] * pct))
                dino[stat] += bonus
                dino[f"base_{stat}"] += bonus

    def create_dino(self, name, level):
        base_stats = DINO_DATA[name]['stats']
        max_hp  = HP_Base(base_stats["health"], level)
        attack  = Base_Stats(base_stats["attack"], level)
        defense = Base_Stats(base_stats["defense"], level)
        speed   = Base_Stats(base_stats["speed"], level)

        learned_moves = [m for _, m in sorted(DINO_DATA[name]['moves'].items()) if _ <= level]
        active_moves  = learned_moves[-4:]  # most recently learned 4 as defaults
        moveset = []
        for move_name in active_moves:
            m = MOVE_DATA.get(move_name, {})
            moveset.append({
                "name": move_name,
                "type": m.get("type", "normal"),
                "damage": m.get("damage", 0),
                "accuracy": m.get("accuracy", 100),
                "ability": m.get("ability", None),
            })

        dino = {
            "name": name,
            "level": level,
            "nature": random.choice(list(NATURE_BOOSTS.keys())),
            "type": base_stats['type'],
            "hp": max_hp,
            "max_hp": max_hp,
            "attack": attack,
            "defense": defense,
            "speed": speed,
            "base_attack": attack,
            "base_defense": defense,
            "base_speed": speed,
            "stat_stages": {"attack": 0, "defense": 0, "speed": 0},
            "defending": False,
            "moveset": moveset,
            "moves": learned_moves,
            "image": self.player_dino_images[name],
            "front_image": self.player_dino_front_images[name],
            "frames": self.dino_frames.get(name),
            "xp": 0,
            "xp_to_next": LevelXP(level + 1) - LevelXP(level),
            "displayed_xp": 0,
        }
        self.apply_nature_boost(dino)
        dino["hp"] = dino["max_hp"]
        return dino

    # --- XP & Leveling ---

    def award_xp(self, dino, amount):
        dino['xp'] += amount
        while dino['xp'] >= dino['xp_to_next']:
            base_stats = DINO_DATA[dino["name"]]['stats']
            prev_max_hp = dino['max_hp']
            dino['xp'] -= dino['xp_to_next']
            dino['level'] += 1
            dino['xp_to_next'] = LevelXP(dino['level'] + 1) - LevelXP(dino['level'])
            dino['max_hp']  = HP_Base(base_stats["health"], dino['level'])
            dino['attack']  = Base_Stats(base_stats["attack"], dino['level'])
            dino['defense'] = Base_Stats(base_stats["defense"], dino['level'])
            dino['speed']   = Base_Stats(base_stats["speed"], dino['level'])
            dino['base_attack']  = dino['attack']
            dino['base_defense'] = dino['defense']
            dino['base_speed']   = dino['speed']
            dino['stat_stages']  = {"attack": 0, "defense": 0, "speed": 0}
            self.apply_nature_boost(dino)
            dino['hp'] += dino['max_hp'] - prev_max_hp
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
        alive_count = len(alive)
        _bench_mult = {2: 1.15, 3: 0.9, 4: 0.75, 5: 0.6}
        active_mult = 2.0 if alive_count == 1 else 1.5
        bench_mult  = _bench_mult.get(alive_count, 1.0)
        for dino in alive:
            mult = active_mult if dino is active else bench_mult
            dino['xp'] += int(round(xp_gain * mult))
            while dino['xp'] >= dino['xp_to_next']:
                base_stats = DINO_DATA[dino['name']]['stats']
                prev_max_hp = dino['max_hp']
                dino['xp'] -= dino['xp_to_next']
                dino['level'] += 1
                dino['xp_to_next'] = LevelXP(dino['level'] + 1) - LevelXP(dino['level'])
                dino['max_hp']  = HP_Base(base_stats['health'], dino['level'])
                dino['attack']  = Base_Stats(base_stats['attack'], dino['level'])
                dino['defense'] = Base_Stats(base_stats['defense'], dino['level'])
                dino['speed']   = Base_Stats(base_stats['speed'], dino['level'])
                dino['base_attack']  = dino['attack']
                dino['base_defense'] = dino['defense']
                dino['base_speed']   = dino['speed']
                dino['stat_stages']  = {"attack": 0, "defense": 0, "speed": 0}
                self.apply_nature_boost(dino)
                dino['hp'] = dino['hp'] + (dino['max_hp'] - prev_max_hp)
                msgs.append(f"{dino['name']} grew to Lv {dino['level']}!")

                # Check for newly learned moves at this level
                for learn_lvl, move_name in DINO_DATA[dino['name']]['moves'].items():
                    if learn_lvl == dino['level'] and move_name not in dino.get('moves', []):
                        dino.setdefault('moves', []).append(move_name)
                        if len(dino.get('moveset', [])) < 4:
                            m = MOVE_DATA.get(move_name, {})
                            dino.setdefault('moveset', []).append({
                                "name":     move_name,
                                "type":     m.get("type", "normal"),
                                "damage":   m.get("damage", 0),
                                "accuracy": m.get("accuracy", 100),
                                "ability":  m.get("ability", None),
                            })
                            msgs.append(f"{dino['name']} learned {move_name}!")
                        else:
                            msgs.append(f"{dino['name']} can learn {move_name}! Manage moves in the party screen.")
        return msgs

    # --- Battle helpers: effective stats / move abilities / field effects ---

    def _get_effective_stat(self, dino, stat):
        stage = dino.get('stat_stages', {}).get(stat, 0)
        mult  = STAT_STAGE_MULT.get(stage, 1.0)
        base  = dino.get(f'base_{stat}', dino.get(stat, 1))
        return max(1, round(base * mult))

    def _apply_move_ability(self, ability, user, target, dmg=0):
        if not ability:
            return []
        if random.randint(1, 100) > ability['chance']:
            return []
        msgs = []
        if ability['kind'] == 'recoil':
            recoil_amt = max(1, int(dmg * ability['percent'] / 100))
            user['hp'] = max(0, user['hp'] - recoil_amt)
            msgs.append(f"{user['name']} took {recoil_amt} recoil damage!")
            return msgs
        if ability['kind'] == 'stat_boost':
            subject = user if ability['target'] == 'self' else target
            stat    = ability['stat']
            stages  = ability['stages']
            old     = subject.get('stat_stages', {}).get(stat, 0)
            new     = max(-6, min(6, old + stages))
            subject.setdefault('stat_stages', {})[stat] = new
            if new == old:
                msgs.append(f"{subject['name']}'s {stat.capitalize()} can't go {'higher' if stages > 0 else 'lower'}!")
            else:
                if stages >= 2:
                    msg = f"{subject['name']}'s {stat.capitalize()} has surged!"
                elif stages == 1:
                    msg = f"{subject['name']}'s {stat.capitalize()} has been powered up!"
                elif stages == -1:
                    msg = f"{subject['name']}'s {stat.capitalize()} has been weakened!"
                else:
                    msg = f"{subject['name']}'s {stat.capitalize()} has sharply fallen!"
                msgs.append(msg)
        elif ability['kind'] == 'field':
            effect = ability['effect']
            if not any(fx['effect'] == effect for fx in self.field_effects):
                fx = {'effect': effect, 'turns_left': ability['duration']}
                if 'boost_type' in ability:
                    fx['boost_type'] = ability['boost_type']
                    fx['multiplier'] = ability['multiplier']
                self.field_effects.append(fx)
                if effect == 'speed_swap':
                    msgs.append("Time has been distorted!")
                elif effect == 'type_power':
                    msgs.append(f"{ability['boost_type'].capitalize()} energy fills the air!")
        elif ability['kind'] == 'heal':
            heal_amount = int(user['max_hp'] * ability['percent'] / 100)
            user['hp'] = min(user['max_hp'], user['hp'] + heal_amount)
            msgs.append(f"{user['name']} restored {heal_amount} HP!")
        elif ability['kind'] == 'dot':
            target['dot'] = {
                'damage_percent': ability['damage_percent'],
                'turns_left':     ability['turns'],
                'tick_msg':       ability.get('tick_msg', 'hurt by the lingering storm'),
            }
            msgs.append(f"A storm surrounds {target['name']}!")
        elif ability['kind'] == 'lock':
            last = target.get('last_move_used')
            if last is None:
                moveset = target.get('moveset', [])
                last = moveset[0]['name'] if moveset else None
            if last:
                target['locked_move'] = last
                target['lock_turns_left'] = ability['turns']
                msgs.append(f"{target['name']} is locked into {last}!")
                msgs.append(f"{target['name']} can't switch out!")
        return msgs

    def _tick_field_effects(self):
        msgs = []
        for fx in self.field_effects:
            fx['turns_left'] -= 1
            if fx['turns_left'] <= 0:
                if fx['effect'] == 'speed_swap':
                    msgs.append("Time returned to normal.")
                elif fx['effect'] == 'type_power':
                    msgs.append(f"{fx.get('boost_type', '').capitalize()} energy dissipated.")
        self.field_effects = [fx for fx in self.field_effects if fx['turns_left'] > 0]
        return msgs

    def _tick_dino_effects(self):
        msgs = []
        targets = [
            self.player_dinos[self.active_dino_index],
            self.enemy_dino,
        ]
        for dino in targets:
            dot = dino.get('dot')
            if not dot or dino.get('hp', 0) <= 0:
                continue
            dmg = max(1, int(dino['max_hp'] * dot['damage_percent'] / 100))
            dino['hp'] = max(1, dino['hp'] - dmg)
            msgs.append(f"{dino['name']} is {dot['tick_msg']}! (-{dmg} HP)")
            dot['turns_left'] -= 1
            if dot['turns_left'] <= 0:
                dino.pop('dot', None)
                msgs.append(f"The storm around {dino['name']} cleared!")
        return msgs

    def _should_enemy_defend(self, rank):
        if not self.is_trainer_battle:
            return False
        if rank == 'lowest':
            return False
        if self.enemy_dino.get('defending', False):
            return False
        if self.enemy_defend_uses_remaining <= 0:
            return False
        if rank in ('medium', 'rival'):
            return random.random() < 0.15
        if rank == 'high':
            return random.random() < 0.25
        return False

    def _clear_defending_flags(self):
        for d in self.player_dinos:
            d['defending'] = False
        if self.enemy_dino:
            self.enemy_dino['defending'] = False
        if self.enemy_dino2:
            self.enemy_dino2['defending'] = False

    def _pick_enemy_move(self, attacker, defender, rank):
        moveset = attacker.get('moveset', [])
        if not moveset:
            return None
        if rank == 'lowest':
            return random.choice(moveset)
        player_defending = defender.get('defending', False)
        boost_chance  = 0.20 if rank in ('medium', 'rival') else 0.50
        pierce_chance = 0.15 if rank in ('medium', 'rival') else 0.25
        if player_defending:
            if random.random() < boost_chance:
                stat_moves = [m for m in moveset
                              if (m.get('ability') or {}).get('kind') == 'stat_boost'
                              and (m.get('ability') or {}).get('target') == 'self']
                if stat_moves:
                    return random.choice(stat_moves)
            if random.random() < pierce_chance:
                pierce_moves = [m for m in moveset if m.get('pierces_defend', False)]
                if pierce_moves:
                    return random.choice(pierce_moves)
        scored = []
        for move in moveset:
            mtype = move.get('type', 'normal')
            eff   = type_effectiveness_value(mtype, defender['type'])
            stab  = stab_multiplier(mtype, attacker['type'])
            score = eff * stab * move.get('damage', 0)
            scored.append((score, move))
        scored.sort(key=lambda x: x[0], reverse=True)
        if rank in ('medium', 'rival'):
            if random.random() < 0.70 and scored:
                return scored[0][1]
            return random.choice(moveset)
        # high: always best-scoring move
        return scored[0][1] if scored else random.choice(moveset)

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
        dino['base_attack']  = dino['attack']
        dino['base_defense'] = dino['defense']
        dino['base_speed']   = dino['speed']
        dino['stat_stages']  = {"attack": 0, "defense": 0, "speed": 0}
        self.apply_nature_boost(dino)
        dino['hp'] = max(1, int(dino['max_hp'] * hp_ratio))

        old_moves = dino.get('moves', [])[:]
        new_learned = []
        for move in [m for _, m in sorted(new_data['moves'].items()) if _ <= level]:
            if move not in old_moves:
                old_moves.append(move)
                new_learned.append(move)
        dino['moves'] = old_moves

        # Preserve existing active moveset; rebuild dicts in case stats changed,
        # then fill empty slots (< 4) with newly learned moves.
        active_names = [m['name'] for m in dino.get('moveset', []) if m['name'] in old_moves]
        for mv in new_learned:
            if len(active_names) < 4 and mv not in active_names:
                active_names.append(mv)
        active_names = active_names[:4]
        dino['moveset'] = []
        for move_name in active_names:
            m = MOVE_DATA.get(move_name, {})
            dino['moveset'].append({
                "name": move_name,
                "type": m.get("type", "normal"),
                "damage": m.get("damage", 0),
                "accuracy": m.get("accuracy", 100),
                "ability": m.get("ability", None),
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
        self.active_dino_index = 0
        self.fading = True
        self.fade_alpha = 0

        tile_x = self.player.rect.x // config.TILE_SIZE
        tile_y = self.player.rect.y // config.TILE_SIZE
        zone = self.get_player_zone(tile_x, tile_y)
        # print(f"[ENCOUNTER] tile=({tile_x},{tile_y}) zone={zone}")

        zone_data = ENCOUNTER_ZONES[zone]
        dino_key = random.choice(zone_data["dinos"])
        level = random.randint(*zone_data["level_range"])

        self.enemy_dino = self.create_dino(dino_key, level)
        self.field_effects = []
        self.defend_uses_remaining = 3
        self.enemy_defend_uses_remaining = 3
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
        self.active_dino_index = 0
        self.fading = True
        self.fade_alpha = 0
        self.is_trainer_battle = True
        self.current_trainer_npc = npc

        if npc.trainer_id == 'gray':
            self._post_trainer_battle_cb = lambda: self._on_gray_battle_won(npc)
        elif npc.trainer_id == 'skyy' and self.current_world_file == 'GYM1.tmx':
            self._post_trainer_battle_cb = self._on_skyy_gym_won

        data = TRAINER_DATA.get(npc.trainer_id, {})
        dinos = data.get('dinos', {})
        sorted_keys = sorted(dinos.keys())
        override = getattr(npc, 'override_first_dino', None)
        dino_name, dino_level = dinos[sorted_keys[0]]
        self.trainer_dino_queue = [(dinos[k][0], dinos[k][1]) for k in sorted_keys[1:]]
        if override:
            self.trainer_dino_queue.append(override)
        self.trainer_dinos_total = len(self.trainer_dino_queue) + 1
        self.trainer_dinos_defeated = 0

        self.enemy_dino = self.create_dino(dino_name, dino_level)
        self.field_effects = []
        self.defend_uses_remaining = 3
        self.enemy_defend_uses_remaining = 3
        self.encounter_ui = EncounterUI(self.fonts)
        trainer_name = TRAINER_DATA.get(npc.trainer_id, {}).get('name', 'Trainer')
        self.encounter_text = f"{trainer_name} sent out {dino_name}!"
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

    def start_forced_walk_double(self, npc1, npc2):
        self.forced_walk_npc  = npc1
        self.forced_walk_npc2 = npc2

    def _update_forced_walk(self, dt):
        p   = self.player
        npc = self.forced_walk_npc
        ts  = config.TILE_SIZE

        if p.moving:
            step = p.move_speed * dt
            if p.pos_x < p.target_x:   p.pos_x = min(p.pos_x + step, p.target_x)
            elif p.pos_x > p.target_x: p.pos_x = max(p.pos_x - step, p.target_x)
            if p.pos_y < p.target_y:   p.pos_y = min(p.pos_y + step, p.target_y)
            elif p.pos_y > p.target_y: p.pos_y = max(p.pos_y - step, p.target_y)
            p.rect.x = round(p.pos_x)
            p.rect.y = round(p.pos_y)
            p.anim_timer += dt
            if p.anim_timer >= 0.08:
                p.anim_timer = 0.0
                p.anim_index = (p.anim_index + 1) % 4
                p.image = p.animations[p.direction][p.anim_index]
            if p.rect.x == p.target_x and p.rect.y == p.target_y:
                p.moving    = False
                p.anim_index = 0
                p.image = p.animations[p.direction][0]
            return

        px   = p.rect.x // ts
        py   = p.rect.y // ts
        dist = abs(px - npc.tile_x) + abs(py - npc.tile_y)
        if dist <= 1:
            npc2 = self.forced_walk_npc2
            self.forced_walk_npc  = None
            self.forced_walk_npc2 = None
            data   = TRAINER_DATA.get(npc.trainer_id, {})
            dialog = data.get('dialog', {}).get('default', ["Double battle!"])
            self.message_box.queue_messages(
                dialog, wait_for_input=True,
                on_complete=lambda: self.start_double_trainer_battle(npc, npc2)
            )
            return

        dx = npc.tile_x - px
        dy = npc.tile_y - py
        if abs(dx) >= abs(dy) and dx != 0:
            sx, sy    = (1 if dx > 0 else -1), 0
            direction = 'right' if dx > 0 else 'left'
        elif dy != 0:
            sx, sy    = 0, (1 if dy > 0 else -1)
            direction = 'down' if dy > 0 else 'up'
        else:
            return

        p.direction = p.facing = direction
        p.pos_x     = float(p.rect.x)
        p.pos_y     = float(p.rect.y)
        p.target_x  = p.rect.x + sx * ts
        p.target_y  = p.rect.y + sy * ts
        p.moving    = True
        p.anim_index = 1
        p.anim_timer = 0.0
        p.image = p.animations[p.direction][1]

    def start_double_trainer_battle(self, npc1, npc2):
        self.player.moving = False
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y
        self.player.pos_x = float(self.player.rect.x)
        self.player.pos_y = float(self.player.rect.y)
        self.fading = True
        self.fade_alpha = 0
        self.is_trainer_battle = True
        self.is_double_battle = True
        self.current_trainer_npc  = npc1
        self.current_trainer_npc2 = npc2

        data1  = TRAINER_DATA.get(npc1.trainer_id, {})
        data2  = TRAINER_DATA.get(npc2.trainer_id, {})
        dinos1 = data1.get('dinos', {})
        dinos2 = data2.get('dinos', {})
        k1 = sorted(dinos1.keys())[0]
        k2 = sorted(dinos2.keys())[0]
        n1, l1 = dinos1[k1]
        n2, l2 = dinos2[k2]

        self.enemy_dino  = self.create_dino(n1, l1)
        self.enemy_dino2 = self.create_dino(n2, l2)

        self.trainer_dino_queue     = []
        self.trainer_dinos_total    = 2
        self.trainer_dinos_defeated = 0
        self.field_effects              = []
        self.defend_uses_remaining      = 3
        self.enemy_defend_uses_remaining = 3

        self.encounter_ui   = DoubleBattleUI(self.fonts)
        self.encounter_text = f"Double Battle! {n1} and {n2}!"
        self.encounter      = DoubleBattleEncounter(self.fonts, n1, n2)

        now    = pygame.time.get_ticks()
        frames = self.dino_frames.get(n1, [self.enemy_dino['image']])
        self.encounter_anim = {
            "frames": frames, "frame_idx": 0,
            "last_switch": now, "interval": 250,
            "start_time": now, "duration": 1000,
        }

    # ── Double-battle helpers ──────────────────────────────────────

    def _auto_attack_single(self, attacker, defender, attacker_label, after=None):
        """Execute one auto-chosen move from attacker → defender, then call after."""
        if not attacker or attacker.get('hp', 0) <= 0:
            if after: after()
            return
        if not defender or defender.get('hp', 0) <= 0:
            if after: after()
            return
        moveset = attacker.get('moveset', [])
        if not moveset:
            if after: after()
            return

        move      = random.choice(moveset)
        move_name = move['name']
        power     = max(0, move.get('damage', 0))
        mtype     = move.get('type', 'normal')
        ability   = move.get('ability')
        pierces   = move.get('pierces_defend', False)

        if defender.get('defending', False) and not pierces:
            defender['defending'] = False
            msgs = [f"{attacker_label}{attacker['name']} used {move_name}!",
                    f"{defender['name']} defended and took no damage!"]
            msgs.extend(self._apply_move_ability(ability, attacker, defender))
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                self.message_box.queue_messages(msgs, wait_for_input=True)
            return

        STAB    = stab_multiplier(mtype, attacker['type'])
        eff_val = type_effectiveness_value(mtype, defender['type'])
        rnd     = random_damage_factor()
        atk     = self._get_effective_stat(attacker, 'attack')
        dfs     = self._get_effective_stat(defender, 'defense')
        lvl     = max(1, attacker['level'])
        dmg     = max(1, int(Damage(lvl, atk, power, dfs, STAB, eff_val, rnd))) if power > 0 else 0
        defender['hp'] = max(0, defender['hp'] - dmg)
        if dmg > 0:
            if attacker_label == "":  # player attacking enemy
                flash_target = 'enemy1' if defender is self.enemy_dino else 'enemy2'
            else:  # enemy attacking player
                p1 = self.player_dinos[0] if self.player_dinos else None
                flash_target = 'player1' if defender is p1 else 'player2'
            self.trigger_hit_flash(flash_target)

        msgs = [f"{attacker_label}{attacker['name']} used {move_name}!"]
        if power > 0:
            if eff_val > 10:       msgs.append("It's super effective!")
            elif 0 < eff_val < 10: msgs.append("It's not very effective...")
        msgs.extend(self._apply_move_ability(ability, attacker, defender, dmg))

        if defender['hp'] <= 0:
            if attacker_label == "":   # player p2 killed an enemy
                self.stats_enemies_defeated  += 1
                self.trainer_dinos_defeated  += 1
                tn = self._trainer_name if defender is not self.enemy_dino2 else self._trainer_name2
                faint_msg = f"{tn}'s {defender['name']} fainted!"
            else:                      # enemy killed a player dino
                self.stats_dinos_fainted += 1
                faint_msg = f"{defender['name']} fainted!"

            def _show_faint(_msg=faint_msg, _after=after):
                if _after:
                    self.message_box.queue_messages([_msg], wait_for_input=True, on_complete=_after)
                else:
                    self.message_box.queue_messages([_msg], wait_for_input=True)

            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=_show_faint)
            return

        if after:
            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
        else:
            self.message_box.queue_messages(msgs, wait_for_input=True)

    def _double_continue_turn(self):
        """Chain p2 auto → e1 auto → e2 auto → turn end after player's p1 action."""
        p1 = self.player_dinos[0] if self.player_dinos else None
        p2 = self.player_dinos[1] if len(self.player_dinos) > 1 else None
        e1 = self.enemy_dino
        e2 = self.enemy_dino2

        def turn_end():
            e1_dead = e1.get('hp', 0) <= 0
            e2_dead = (not e2 or e2.get('hp', 0) <= 0)
            if e1_dead and e2_dead:
                self._finish_double_battle()
                return
            all_dead = all(d.get('hp', 0) <= 0 for d in self.player_dinos)
            if all_dead:
                self.message_box.queue_messages(
                    ["You blacked out!", "Be careful next time..."],
                    wait_for_input=True, on_complete=self.trigger_blackout)
                return
            msgs = list(self._tick_field_effects()) + list(self._tick_dino_effects())
            msgs.append("What will you do?")
            self.message_box.queue_messages(msgs, wait_for_input=True)

        def e2_attacks():
            if not e2 or e2.get('hp', 0) <= 0:
                turn_end()
                return
            target = p2 if (p2 and p2.get('hp', 0) > 0) else p1
            if not target or target.get('hp', 0) <= 0:
                turn_end()
                return
            self._auto_attack_single(e2, target, f"{self._trainer_name2}'s ", after=turn_end)

        def e1_attacks():
            if e1.get('hp', 0) <= 0:
                e2_attacks()
                return
            target = p1 if (p1 and p1.get('hp', 0) > 0) else p2
            if not target or target.get('hp', 0) <= 0:
                e2_attacks()
                return
            self._auto_attack_single(e1, target, f"{self._trainer_name}'s ", after=e2_attacks)

        def p2_attacks():
            if not p2 or p2.get('hp', 0) <= 0:
                e1_attacks()
                return
            target = e2 if (e2 and e2.get('hp', 0) > 0) else (e1 if e1.get('hp', 0) > 0 else None)
            if not target:
                e1_attacks()
                return
            self._auto_attack_single(p2, target, "", after=e1_attacks)

        p2_attacks()

    def _finish_double_battle(self):
        """Mark both trainers defeated, give XP, give coins, return to world."""
        coin_reward = 0
        if self.current_trainer_npc:
            self.current_trainer_npc.defeated = True
            self.defeated_trainers.add(self.current_trainer_npc.trainer_id)
            coin_reward += TRAINER_DATA.get(
                self.current_trainer_npc.trainer_id, {}).get('reward_coins', 0)
        if self.current_trainer_npc2:
            self.current_trainer_npc2.defeated = True
            self.defeated_trainers.add(self.current_trainer_npc2.trainer_id)
            coin_reward += TRAINER_DATA.get(
                self.current_trainer_npc2.trainer_id, {}).get('reward_coins', 0)

        alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
        active = self.player_dinos[self.active_dino_index] if self.player_dinos else None
        xp_total = 0
        if alive and active:
            ref_level = active['level']
            xp_total += calculate_xp_gain(ref_level, self.enemy_dino['level'], enemy_name=self.enemy_dino['name'], state_multiplier=0.9)
            if self.enemy_dino2:
                xp_total += calculate_xp_gain(ref_level, self.enemy_dino2['level'], enemy_name=self.enemy_dino2['name'], state_multiplier=0.9)

        level_up_msgs = self._grant_party_xp_and_level_ups(xp_total) if xp_total > 0 else []

        def pop_world():
            self.is_trainer_battle = False
            self.is_double_battle  = False
            self.enemy_dino2       = None
            for d in self.player_dinos:
                d['stat_stages'] = {"attack": 0, "defense": 0, "speed": 0}
                d['defending']   = False
            self.pop_to_world()
            for dino in self.player_dinos:
                evo_target = self.check_evolution(dino)
                if evo_target:
                    self.start_evolution(dino, evo_target)

        msgs = ["You won the double battle!"]
        if coin_reward > 0:
            self.coins += coin_reward
            msgs.append(f"You received {coin_reward} coins!")
        if xp_total > 0 and active:
            _db_act_m = 2.0 if len(alive) == 1 else 1.5
            _db_ben_m = {2: 1.33, 3: 1.25, 4: 1.1, 5: 1.0}.get(len(alive), 1.0)
            msgs.append(f"{active['name']} gained {int(round(xp_total * _db_act_m))} XP!")
            if len(alive) > 1:
                msgs.append(f"Each party dino gained {int(round(xp_total * _db_ben_m))} XP!")
        msgs.extend(level_up_msgs)
        self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=pop_world)

    # ── Double battle input-phase methods ─────────────────────────

    def _double_start_p1_turn(self):
        self.double_phase = 'p1'
        ui = self.encounter_ui
        ui.in_fight_menu    = False
        ui.in_target_menu   = False
        ui.selected_option  = 0
        ui.move_selected    = 0
        ui.selecting_p2     = False

    def _handle_double_encounter_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.double_phase is None:
            return

        p1 = self.player_dinos[0] if self.player_dinos else None
        p2 = self.player_dinos[1] if len(self.player_dinos) > 1 else None
        e1 = self.enemy_dino
        e2 = self.enemy_dino2

        active = p2 if self.double_phase == 'p2' else p1
        if not active or active.get('hp', 0) <= 0:
            if self.double_phase == 'p1':
                self.double_p1_queued = None
                self._double_advance_to_p2()
            else:
                self.double_p2_queued = None
                self._execute_double_turn()
            return

        # ── Target selection ─────────────────────────────
        if self.encounter_ui.in_target_menu:
            e1_alive = e1 and e1.get('hp', 0) > 0
            e2_alive = e2 and e2.get('hp', 0) > 0
            if event.key in (pygame.K_a, pygame.K_LEFT):
                if e1_alive:
                    self.encounter_ui.target_idx = 0
            elif event.key in (pygame.K_d, pygame.K_RIGHT):
                if e2_alive:
                    self.encounter_ui.target_idx = 1
            elif event.key == pygame.K_j:
                target_is_e2 = (self.encounter_ui.target_idx == 1 and bool(e2_alive))
                queued = {'move_name': self.encounter_ui._pending_move_name,
                          'target_is_e2': target_is_e2}
                self.encounter_ui.in_target_menu = False
                if self.double_phase == 'p1':
                    self.double_p1_queued = queued
                    self._double_advance_to_p2()
                else:
                    self.double_p2_queued = queued
                    self._execute_double_turn()
            return

        result = self.encounter_ui.handle_input(event, active)
        if result is None:
            return

        if result.startswith("UseMove:"):
            move_name = result.split("UseMove:", 1)[1]
            e1_alive  = e1 and e1.get('hp', 0) > 0
            e2_alive  = e2 and e2.get('hp', 0) > 0
            if e1_alive and e2_alive:
                self.encounter_ui._pending_move_name = move_name
                self.encounter_ui.in_target_menu     = True
                self.encounter_ui.target_idx         = 0
                self.encounter_ui.in_fight_menu      = False
            else:
                queued = {'move_name': move_name, 'target_is_e2': (bool(e2_alive) and not e1_alive)}
                self.encounter_ui.in_fight_menu = False
                if self.double_phase == 'p1':
                    self.double_p1_queued = queued
                    self._double_advance_to_p2()
                else:
                    self.double_p2_queued = queued
                    self._execute_double_turn()

        elif result == "Defend":
            if active.get('defending', False):
                self.message_box.queue_messages(
                    [f"{active['name']} can't defend twice in a row!"], wait_for_input=True)
                return
            if self.defend_uses_remaining <= 0:
                self.message_box.queue_messages(
                    ["Your team has no Defends left this battle!"], wait_for_input=True)
                return
            self.defend_uses_remaining -= 1
            active['defending'] = True
            queued = {'action': 'defend'}
            if self.double_phase == 'p1':
                self.double_p1_queued = queued
                self._double_advance_to_p2()
            else:
                self.double_p2_queued = queued
                self._execute_double_turn()

        elif result == "Run":
            self.message_box.queue_messages(
                ["You can't run from a trainer battle!"], wait_for_input=True)
        elif result == "Bag":
            self.push_state('items')
        elif result == "Party":
            self.push_state('party')

    def _double_advance_to_p2(self):
        p2 = self.player_dinos[1] if len(self.player_dinos) > 1 else None
        ui = self.encounter_ui
        ui.in_fight_menu   = False
        ui.in_target_menu  = False
        ui.selected_option = 0
        ui.move_selected   = 0
        if not p2 or p2.get('hp', 0) <= 0:
            self.double_p2_queued = None
            self._execute_double_turn()
            return
        self.double_phase    = 'p2'
        ui.selecting_p2 = True

    def _double_player_attack(self, attacker, defender, move_name, after=None):
        move = next((m for m in attacker.get('moveset', []) if m['name'] == move_name), None)
        if not move:
            if after: after()
            return
        power          = max(0, move.get('damage', 0))
        acc            = move.get('accuracy', 100)
        mtype          = move.get('type', 'normal')
        ability        = move.get('ability')
        pierces_defend = move.get('pierces_defend', False)
        attacker['defending'] = False
        if random.random() * 100 > acc:
            self.message_box.queue_messages(
                [f"{attacker['name']} used {move_name}!", "But it missed!"],
                wait_for_input=True, on_complete=after)
            return
        self._apply_player_attack(attacker, defender, move_name, power, mtype, ability,
                                  pierces_defend=pierces_defend, after=after)

    def _execute_double_turn(self):
        self.double_phase = None
        p1 = self.player_dinos[0] if self.player_dinos else None
        p2 = self.player_dinos[1] if len(self.player_dinos) > 1 else None
        e1 = self.enemy_dino
        e2 = self.enemy_dino2
        p1q = self.double_p1_queued
        p2q = self.double_p2_queued
        self.double_p1_queued = None
        self.double_p2_queued = None

        def turn_end():
            self._double_turn_end()

        def e2_attacks():
            if not e2 or e2.get('hp', 0) <= 0:
                turn_end(); return
            target = p2 if (p2 and p2.get('hp', 0) > 0) else p1
            if not target or target.get('hp', 0) <= 0:
                turn_end(); return
            self._auto_attack_single(e2, target, f"{self._trainer_name2}'s ", after=turn_end)

        def e1_attacks():
            if not e1 or e1.get('hp', 0) <= 0:
                e2_attacks(); return
            target = p1 if (p1 and p1.get('hp', 0) > 0) else p2
            if not target or target.get('hp', 0) <= 0:
                e2_attacks(); return
            self._auto_attack_single(e1, target, f"{self._trainer_name}'s ", after=e2_attacks)

        def _resolve_target(targeted_e2):
            """Return the best live target, redirecting to the other enemy if the chosen one fainted."""
            e2_alive = e2 and e2.get('hp', 0) > 0
            e1_alive = e1 and e1.get('hp', 0) > 0
            if targeted_e2:
                return e2 if e2_alive else (e1 if e1_alive else None)
            else:
                return e1 if e1_alive else (e2 if e2_alive else None)

        def p2_attacks():
            if not p2q or not p2 or p2.get('hp', 0) <= 0:
                e1_attacks(); return
            if p2q.get('action') == 'defend':
                self.message_box.queue_messages(
                    [f"{p2['name']} braced for impact!"], wait_for_input=True, on_complete=e1_attacks)
                return
            tgt = _resolve_target(p2q.get('target_is_e2', False))
            if not tgt:
                e1_attacks(); return
            self._double_player_attack(p2, tgt, p2q['move_name'], after=e1_attacks)

        def p1_attacks():
            if not p1q or not p1 or p1.get('hp', 0) <= 0:
                p2_attacks(); return
            if p1q.get('action') == 'defend':
                self.message_box.queue_messages(
                    [f"{p1['name']} braced for impact!"], wait_for_input=True, on_complete=p2_attacks)
                return
            tgt = _resolve_target(p1q.get('target_is_e2', False))
            if not tgt:
                p2_attacks(); return
            self._double_player_attack(p1, tgt, p1q['move_name'], after=p2_attacks)

        p1_attacks()

    def _double_turn_end(self):
        p1 = self.player_dinos[0] if self.player_dinos else None
        p2 = self.player_dinos[1] if len(self.player_dinos) > 1 else None
        e1 = self.enemy_dino
        e2 = self.enemy_dino2

        if (not e1 or e1.get('hp', 0) <= 0) and (not e2 or e2.get('hp', 0) <= 0):
            self._finish_double_battle()
            return

        if all(d.get('hp', 0) <= 0 for d in self.player_dinos):
            self.message_box.queue_messages(
                ["You blacked out!", "Be careful next time..."],
                wait_for_input=True, on_complete=self.trigger_blackout)
            return

        # Build replacement queue for fainted active slots
        fainted_slots = []
        if p1 and p1.get('hp', 0) <= 0:
            fainted_slots.append(0)
        if p2 and p2.get('hp', 0) <= 0:
            fainted_slots.append(1)

        if fainted_slots:
            alive_bench = [i for i, d in enumerate(self.player_dinos)
                           if d.get('hp', 0) > 0 and i >= 2]
            if alive_bench:
                self.double_replace_queue = fainted_slots.copy()
                self._double_next_replacement()
                return

        # No replacements needed — start next turn
        self._clear_defending_flags()
        msgs = list(self._tick_field_effects())
        msgs.append("What will you do?")
        self.message_box.queue_messages(msgs, wait_for_input=True)

    def _double_next_replacement(self):
        while self.double_replace_queue:
            slot = self.double_replace_queue.pop(0)
            alive_bench = [i for i, d in enumerate(self.player_dinos)
                           if d.get('hp', 0) > 0 and i >= 2]
            if alive_bench:
                self.double_replace_slot = slot
                dino_name = self.player_dinos[slot]['name']
                self.message_box.queue_messages(
                    [f"{dino_name} fainted! Choose a replacement."],
                    wait_for_input=True,
                    on_complete=self._open_party_forced_double_swap)
                return
        self._double_continue_replacements()

    def _double_continue_replacements(self):
        if self.double_replace_queue:
            self._double_next_replacement()
            return
        self._clear_defending_flags()
        msgs = list(self._tick_field_effects())
        msgs.append("What will you do?")
        self.message_box.queue_messages(msgs, wait_for_input=True)

    def _open_party_forced_double_swap(self):
        if self.state_stack[-1] != 'party':
            self.push_state('party')

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
        self.type_chart_tile_coords = set()
        self.lore_tile_coords = set()
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
                    if props.get('lore1'):
                        self.lore_tile_coords.add(wpos)
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
                    elif props.get('type_chart'):
                        for ty in range(oy, int((obj.y + (obj.height or ts) - 1) // ts) + 1):
                            for tx in range(ox, int((obj.x + (obj.width or ts) - 1) // ts) + 1):
                                self.type_chart_tile_coords.add((tx, ty))
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
                        for ety in range(oy, int((obj.y + obj.height - 1) // ts) + 1):
                            for etx in range(ox, int((obj.x + obj.width - 1) // ts) + 1):
                                exits.add((etx, ety))
        world_maps = [{'tmx': tmx, 'x': 0, 'y': 0,
                        'width': tmx.width * ts, 'height': tmx.height * ts}]
        # print(f"[DEBUG] _load_single_tmx({filename}): entrances={list(entrances.items())} exits={list(exits)}")
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
        # print(f"[DEBUG] trigger_entrance called: id={entrance_id} tile=({tile_x},{tile_y})")
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
        # print(f"[DEBUG] _do_entrance_teleport: id={entrance_id}")
        dest = ENTRANCE_DATA.get(entrance_id)
        # print(f"[DEBUG] ENTRANCE_DATA lookup: {dest}")
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
        self._maybe_add_gym1_skyy()
        tx, ty = dest['spawn']
        self._place_player(tx, ty)

    def trigger_exit(self):
        if self.entrance_fade_state is not None:
            return
        _home_maps = ('HOME_JET2.tmx', 'HOME_JET.tmx')
        if not self.world_stack and self.current_world_file not in _home_maps:
            return
        self.entrance_pending = '__exit__'
        self.entrance_fade_state = 'out'
        self.fade_alpha = 0
        self.player.moving = False
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y

    def _do_exit_teleport(self):
        if not self.world_stack:
            if self.current_world_file == 'HOME_JET2.tmx':
                self._enter_home_jet()
            elif self.current_world_file == 'HOME_JET.tmx':
                self._return_from_home_to_overworld()
            return
        prev = self.world_stack.pop()
        self._load_world_data(prev['file'])
        self.npcs = prev['npcs']
        for npc in self.npcs:
            self.solid_tile_coords.add((npc.tile_x, npc.tile_y))
        self._maybe_add_gym_blocker()
        self._maybe_add_skyy()
        self._maybe_add_gray_rival()
        # Place player one tile behind where they entered, facing back out
        reverse = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        step = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
        dx, dy = step[reverse[prev['entrance_facing']]]
        self._place_player(prev['entrance_tile_x'] + dx, prev['entrance_tile_y'] + dy)

    @property
    def _trainer_name(self):
        return TRAINER_DATA.get(getattr(self.current_trainer_npc, 'trainer_id', ''), {}).get('name', 'Trainer')

    @property
    def _trainer_name2(self):
        return TRAINER_DATA.get(getattr(self.current_trainer_npc2, 'trainer_id', ''), {}).get('name', 'Trainer')

    def _send_next_trainer_dino(self):
        dino_name, dino_level = self.trainer_dino_queue.pop(0)
        self.enemy_dino = self.create_dino(dino_name, dino_level)
        self.encounter_ui.enemy_hp_display = None
        self.encounter_ui.in_fight_menu = False
        self.encounter_ui.xp_frozen = True
        self.encounter_text = f"{self._trainer_name} sent out {dino_name}!"
        self.encounter = Encounter(self.fonts, dino_name)
        now = pygame.time.get_ticks()
        frames = self.dino_frames.get(dino_name, [self.enemy_dino['image']])
        self.encounter.current_dino_surface = frames[0]
        self.encounter_anim = {
            "frames": frames,
            "frame_idx": 0,
            "last_switch": now,
            "interval": 250,
            "start_time": now,
            "duration": 800,
        }

    # --- Intro Cutscene ---

    def _enter_home_jet(self):
        """Transition from HOME_JET2 (Jet's room) to HOME_JET (downstairs)."""
        self._load_world_data('HOME_JET.tmx')
        self._spawn_world_npcs('HOME_JET.tmx')
        for npc in self.npcs:
            self.solid_tile_coords.add((npc.tile_x, npc.tile_y))
        spawn = (9, 7)  # matches HOME_JET2.tmx entrance tile
        self._place_player(*spawn)

    def _return_from_home_to_overworld(self):
        self._load_world_data('LOST_REGION.world')
        self._spawn_world_npcs('LOST_REGION.world')
        for npc in self.npcs:
            self.solid_tile_coords.add((npc.tile_x, npc.tile_y))
        # ── Adjust to match home exit tile in LOST_REGION.world ──
        self._place_player(11, 44)
        self._maybe_add_gym_blocker()
        self._maybe_add_skyy()
        if not self.story_flags.get('amber_intro_done'):
            self._start_amber_intro_cutscene()

    def _start_amber_intro_cutscene(self):
        # ── Adjust start tile so Amber appears a few tiles from the player ──
        amber = NPC('amber', tile_x=2, tile_y=44, facing='down',
                    sight_range=0, npc_type='story')
        self.solid_tile_coords.add((amber.tile_x, amber.tile_y))
        self.npcs.append(amber)
        self.cutscene = {
            'phase': 'intro_flash',
            'npc': amber,
            # ── Adjust to the tile just above the grass entrance ──
            'leave_tile': (7, 34),
        }
        self.cutscene_flash = {'alpha': 0, 'rising': True, 'count': 0}

    def _update_cutscene(self, dt):
        c = self.cutscene
        npc = c['npc']

        # Always advance NPC slide first
        if npc.is_moving:
            npc.anim_timer += dt
            if npc.anim_timer >= npc.anim_speed:
                npc.anim_timer = 0.0
                npc.anim_frame = (npc.anim_frame + 1) % 4
            npc._slide(dt)
            return

        if c['phase'] == 'intro_flash':
            if not self.cutscene_flash:
                c['phase'] = 'approaching'

        elif c['phase'] == 'approaching':
            if npc._pixel_close(self.player):
                npc.anim_frame = 0
                npc.face_toward_player(self.player)
                # Turn player to face Amber
                dx = npc.tile_x - self.player.rect.x // config.TILE_SIZE
                dy = npc.tile_y - self.player.rect.y // config.TILE_SIZE
                if abs(dx) >= abs(dy):
                    d = 'right' if dx > 0 else 'left'
                else:
                    d = 'down' if dy > 0 else 'up'
                self.player.facing = self.player.direction = d
                self.player.image = self.player.animations[d][0]
                c['phase'] = 'dialogue'
                self.message_box.queue_messages(
                    self._split_dialogue(
                        "The solar flares are becoming more aggressive as time goes on,"
                        " our field agents are rushing back to the lab before all power"
                        " goes out and before the eclipse sets in.",
                        "I need you to go find the 3 dinos left behind and bring them"
                        " back to my Research Lab in Sierra Town! Be careful out there",
                    ),
                    wait_for_input=True, on_complete=self._on_amber_dialogue_done
                )
            else:
                npc._start_step(self.player, self.solid_tile_coords, self.solid_tiles)

        elif c['phase'] == 'walking_away':
            wx, wy = c['walk_target']
            if npc.tile_x == wx and npc.tile_y == wy:
                # Walk done — teleport Amber to her guard tile
                tx, ty = c['leave_tile']
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                npc.tile_x, npc.tile_y = tx, ty
                npc.pos_x   = float(tx * config.TILE_SIZE)
                npc.pos_y   = float(ty * config.TILE_SIZE)
                npc.rect.topleft = (int(npc.pos_x), int(npc.pos_y))
                npc.target_x = npc.pos_x
                npc.target_y = npc.pos_y
                npc.is_moving  = False
                npc.anim_frame = 0
                npc.npc_type    = 'guard'
                npc.state       = 'idle'
                npc.facing      = 'left'
                npc.home_tile   = (tx, ty)
                npc.home_facing = 'left'
                npc.sight_range = 8
                npc.block_dialog = [
                    "I need you to collect all 3 dinos before coming back to the lab!"
                ]
                self.solid_tile_coords.add((tx, ty))
                self.cutscene_flash = {'alpha': 0, 'rising': True, 'count': 0}
                c['phase'] = 'flashing'
            else:
                self._step_npc_toward_tile(npc, wx, wy)

        elif c['phase'] == 'flashing':
            if not self.cutscene_flash:
                self.story_flags['amber_intro_done'] = True
                self.event_overlay_active = True
                self.cutscene = None

        elif c['phase'] == 'skyy_walking':
            if self.message_box.visible:
                return
            wx, wy = c['walk_target']
            if npc.tile_x == wx and npc.tile_y == wy:
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                self.cutscene_flash = {'alpha': 0, 'rising': True, 'count': 0}
                c['phase'] = 'skyy_flash'
            else:
                # Force-step ignoring solid tiles so cutscene always completes
                dx, dy = wx - npc.tile_x, wy - npc.tile_y
                if abs(dx) >= abs(dy) and dx != 0:
                    sx, sy = (1 if dx > 0 else -1), 0
                elif dy != 0:
                    sx, sy = 0, (1 if dy > 0 else -1)
                else:
                    sx, sy = 0, 0
                if sx != 0 or sy != 0:
                    nx, ny = npc.tile_x + sx, npc.tile_y + sy
                    # Bump player sideways if they are directly in Skyy's path
                    ptx = self.player.rect.x // config.TILE_SIZE
                    pty = self.player.rect.y // config.TILE_SIZE
                    if (ptx, pty) == (nx, ny):
                        perps = [(-1, 0), (1, 0)] if sx == 0 else [(0, -1), (0, 1)]
                        bx, by = next(
                            (p for p in perps if (ptx + p[0], pty + p[1]) not in self.solid_tile_coords),
                            perps[0]
                        )
                        npx = (ptx + bx) * config.TILE_SIZE
                        npy = (pty + by) * config.TILE_SIZE
                        self.player.rect.x = npx
                        self.player.rect.y = npy
                        self.player.pos_x = float(npx)
                        self.player.pos_y = float(npy)
                        self.player.target_x = float(npx)
                        self.player.target_y = float(npy)
                    self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                    npc.tile_x, npc.tile_y = nx, ny
                    self.solid_tile_coords.add((nx, ny))
                    npc.facing = npc._FACING[(sx, sy)]
                    npc.target_x = float(nx * config.TILE_SIZE)
                    npc.target_y = float(ny * config.TILE_SIZE)
                    npc.is_moving = True
                    npc.anim_frame = 1
                    npc.anim_timer = 0.0

        elif c['phase'] == 'gray_walking':
            if self.message_box.visible:
                return
            wx, wy = c['walk_target']
            if npc.tile_x == wx and npc.tile_y == wy:
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                if npc in self.npcs:
                    self.npcs.remove(npc)
                self.story_flags['gray_route1_done'] = True
                self.cutscene = None
            else:
                dx, dy = wx - npc.tile_x, wy - npc.tile_y
                if abs(dx) >= abs(dy) and dx != 0:
                    sx, sy = (1 if dx > 0 else -1), 0
                elif dy != 0:
                    sx, sy = 0, (1 if dy > 0 else -1)
                else:
                    sx, sy = 0, 0
                if sx != 0 or sy != 0:
                    nx, ny = npc.tile_x + sx, npc.tile_y + sy
                    self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                    npc.tile_x, npc.tile_y = nx, ny
                    self.solid_tile_coords.add((nx, ny))
                    npc.facing = npc._FACING[(sx, sy)]
                    npc.target_x = float(nx * config.TILE_SIZE)
                    npc.target_y = float(ny * config.TILE_SIZE)
                    npc.is_moving = True
                    npc.anim_frame = 1
                    npc.anim_timer = 0.0

        elif c['phase'] == 'skyy_flash':
            if not self.cutscene_flash:
                # Remove Skyy
                if npc in self.npcs:
                    self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                    self.npcs.remove(npc)
                # Remove gym guard
                gym_guard = next((n for n in self.npcs if getattr(n, 'npc_type', '') == 'gym_guard'), None)
                if gym_guard:
                    self.solid_tile_coords.discard((gym_guard.tile_x, gym_guard.tile_y))
                    self.npcs.remove(gym_guard)
                # End eclipse, return to day
                self.story_flags['gym1_accessible'] = True
                self.event_overlay_active = False
                self.is_night = False
                self.day_night_timer = 0.0
                self.dn_transitioning = False
                self.dn_transition_timer = 0.0
                self.cutscene = None

    def _split_dialogue(self, *texts, lines_per_page=2):
        """Break one or more long strings into dialogue-box-sized message chunks."""
        font = self.message_box.font
        avail_w = self.message_box.width - 120
        pages = []
        for text in texts:
            all_lines = wrap_text(text, font, avail_w)
            for i in range(0, len(all_lines), lines_per_page):
                pages.append(' '.join(all_lines[i:i + lines_per_page]))
        return pages

    def _on_amber_dialogue_done(self):
        if not self.cutscene:
            return
        c   = self.cutscene
        npc = c['npc']
        # Walk 6 tiles left, then teleport to guard tile
        c['walk_target'] = (npc.tile_x - 6, npc.tile_y)
        c['phase'] = 'walking_away'

    def _step_npc_toward_tile(self, npc, tx, ty):
        dx, dy = tx - npc.tile_x, ty - npc.tile_y
        if abs(dx) >= abs(dy) and dx != 0:
            sx, sy = (1 if dx > 0 else -1), 0
        elif dy != 0:
            sx, sy = 0, (1 if dy > 0 else -1)
        else:
            return
        nx, ny = npc.tile_x + sx, npc.tile_y + sy
        if (nx, ny) not in self.solid_tile_coords and (nx, ny) not in self.solid_tiles:
            self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
            npc.tile_x, npc.tile_y = nx, ny
            self.solid_tile_coords.add((nx, ny))
            npc.facing = npc._FACING[(sx, sy)]
            npc.target_x = float(nx * config.TILE_SIZE)
            npc.target_y = float(ny * config.TILE_SIZE)
            npc.is_moving = True
            npc.anim_frame = 1
            npc.anim_timer = 0.0

    def _update_cutscene_flash(self, dt):
        f = self.cutscene_flash
        if f['rising']:
            f['alpha'] = min(180, f['alpha'] + 600 * dt)
            if f['alpha'] >= 180:
                f['rising'] = False
        else:
            f['alpha'] = max(0, f['alpha'] - 380 * dt)
            if f['alpha'] <= 0:
                f['count'] += 1
                if f['count'] < 2:
                    f['rising'] = True
                else:
                    self.cutscene_flash = None

    def _add_amber_blocker_to_solid(self):
        blocker = next((n for n in self.npcs if getattr(n, 'npc_type', '') == 'guard'), None)
        if blocker:
            self.solid_tile_coords.add((blocker.tile_x, blocker.tile_y))

    def _add_amber_blocker(self):
        """Re-add guard NPC when loading a save mid-intro."""
        tx, ty = 1, 27  # must match leave_tile in _start_amber_intro_cutscene
        guard = NPC('amber', tile_x=tx, tile_y=ty, facing='left',
                    sight_range=5, npc_type='guard')
        guard.state       = 'idle'
        guard.home_tile   = (tx, ty)
        guard.home_facing = 'left'
        guard.block_dialog = [
            "I need you to collect all 3 dinos before coming back to the lab!"
        ]
        self.npcs.append(guard)
        self.solid_tile_coords.add((tx, ty))

    def _maybe_add_gym_blocker(self):
        if not self.story_flags.get('encounters_unlocked'):
            return
        if self.story_flags.get('gym1_accessible'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        already = any(getattr(n, 'npc_type', '') == 'gym_guard' for n in self.npcs)
        if already:
            return
        tx, ty = 31, 13  # 1 tile below the GYM1 entrance (world tile 31,12)
        blocker = NPC('blk_b', tile_x=tx, tile_y=ty, facing='down',
                      sight_range=0, npc_type='gym_guard')
        blocker.state       = 'idle'
        blocker.home_tile   = (tx, ty)
        blocker.home_facing = 'down'
        blocker.block_dialog = self._split_dialogue(
            "Gym Leader Skyy is out investigating a ruin on Route 1."
            "He believes it has clues to why the solar flares and eclipses"
            " keep happening."
        )
        self.npcs.append(blocker)
        self.solid_tile_coords.add((tx, ty))

    def _maybe_add_skyy(self):
        if not self.story_flags.get('amber_lab_done'):
            return
        if self.story_flags.get('gym1_accessible'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        already = any(getattr(n, 'trainer_id', '') == 'skyy' for n in self.npcs)
        if already:
            return
        tx, ty = 2, -22  # center of ROUTE_1.4, shifted 3 left and 1 up
        skyy = NPC('skyy', tile_x=tx, tile_y=ty, facing='down',
                   sight_range=0, npc_type='story')
        skyy.state = 'idle'
        self.npcs.append(skyy)
        self.solid_tile_coords.add((tx, ty))

    def _maybe_add_gray_rival(self):
        if not self.story_flags.get('gym1_accessible'):
            return
        if self.story_flags.get('gray_route1_done'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        if any(getattr(n, 'trainer_id', '') == 'gray' for n in self.npcs):
            return
        # Determine Gray's first dino: the starter the player did NOT keep
        starter_names = set(config.DINO_BALL_MAP.values())
        player_starter = next(
            (d['name'] for d in self.player_dinos + self.box_dinos
             if d['name'] in starter_names), None
        )
        starter_to_gray = {
            'Volkit':  ('Corlave',  9),  # player kept magma → Gray uses aqua
            'Corlave': ('Floravel', 9),  # player kept aqua  → Gray uses earth
            'Floravel':('Volkit',   9),  # player kept earth → Gray uses magma
        }
        gray_first_dino = starter_to_gray.get(player_starter, ('Corlave', 9))
        tx, ty = -2, -11
        gray = NPC('gray', tile_x=tx, tile_y=ty, facing='right',
                   sight_range=5, npc_type='trainer')
        gray.state = 'idle'
        gray.home_tile = (tx, ty)
        gray.home_facing = 'right'
        gray.use_proximity = True
        gray.override_first_dino = gray_first_dino
        self.npcs.append(gray)
        self.solid_tile_coords.add((tx, ty))

    def _on_gray_battle_won(self, npc):
        data = TRAINER_DATA.get('gray', {})
        msgs = self._split_dialogue(*data.get('dialog', {}).get('defeated', [
            "I like a challenge, next time I'll be more prepared. Keep at it, and I will too.."
        ]))
        def start_walk_away():
            npc.facing = 'down'
            self.cutscene = {
                'phase': 'gray_walking',
                'npc': npc,
                'walk_target': (npc.tile_x, npc.tile_y + 6),
            }
        self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=start_walk_away)

    def _maybe_add_gym1_skyy(self):
        if not self.story_flags.get('gray_route1_done'):
            return
        if self.current_world_file != 'GYM1.tmx':
            return
        if any(getattr(n, 'trainer_id', '') == 'skyy' for n in self.npcs):
            return
        tx, ty = 9, 4  # top center, 5 tiles down from top
        skyy = NPC('skyy', tile_x=tx, tile_y=ty, facing='down',
                   sight_range=0, npc_type='trainer')
        skyy.state = 'idle'
        if self.story_flags.get('gym1_leader_defeated'):
            skyy.defeated = True
        self.npcs.append(skyy)
        self.solid_tile_coords.add((tx, ty))

    def _on_skyy_gym_won(self):
        self.story_flags['gym1_leader_defeated'] = True
        if 'sierra' not in self.badges_earned:
            self.badges_earned.append('sierra')

        def _after_badge():
            data = TRAINER_DATA.get('skyy', {})
            dialog = data.get('dialog', {}).get('defeated', ["..."])
            self.message_box.queue_messages(list(dialog), wait_for_input=True)

        self.badge_earned_screen = BadgeEarnedScreen(
            self, "Sierra Badge",
            os.path.join('assets', 'Badges', 'flying_badge.png'),
            on_dismiss=_after_badge)
        self.push_state('badge_earned')

    def _check_amber_blocker(self):
        if self.story_flags.get('encounters_unlocked'):
            return
        if not self.story_flags.get('amber_intro_done'):
            return
        blocker = next((n for n in self.npcs if getattr(n, 'npc_type', '') == 'guard'), None)
        if blocker and len(self.player_dinos) >= 3:
            self.solid_tile_coords.discard((blocker.tile_x, blocker.tile_y))
            self.npcs.remove(blocker)
            self.story_flags['encounters_unlocked'] = True

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
        self.lore_tile_coords = set()

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
                        if props.get('lore1'):
                            self.lore_tile_coords.add(wpos)
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

            if self.state == 'title':
                self.title_screen.handle_event(event, os.path.exists(SAVE_PATH))
                continue

            if self.state == 'intro':
                if self.intro_sequence:
                    self.intro_sequence.handle_event(event)
                continue

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

            elif self.state == 'move_info':
                if self.move_info_screen:
                    result = self.move_info_screen.handle_event(event, self)
                    if result == 'back':
                        self.pop_state()
                        self.move_info_screen = None
                        self.encounter_ui.move_selected = 0
                        self.encounter_ui.show_move_info = False

            elif self.state == 'dinodex':
                result = self.dinodex_screen.handle_event(event, self)
                if result == 'back':
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
                    self.encounter_ui.move_selected = 0
                    self.encounter_ui.show_move_info = False
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

            elif self.state == 'dino_picker':
                if self._dino_picker:
                    result = self._dino_picker.handle_event(event)
                    if result is not None:
                        self._finish_amber_lab(result)

            elif self.state == 'shop':
                result = self.shop_screen.handle_event(event, self)
                if result == 'back':
                    self.pop_state()
                    self.shop_screen.selected_index = 0

            elif self.state == 'trainer_card':
                self.trainer_card_screen.handle_event(event)

            elif self.state == 'badge_earned':
                if getattr(self, 'badge_earned_screen', None):
                    self.badge_earned_screen.handle_event(event)

            elif self.state == 'box':
                result = self.box_screen.handle_event(event, self)
                if result == 'back':
                    self.pop_state()

            elif self.state == 'type_chart':
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_j, pygame.K_SPACE, pygame.K_ESCAPE):
                    self.pop_state()

            elif self.state == 'encounter':
                # No input of any kind during the intro animation
                if self.encounter_anim is not None:
                    return

                # Double battle uses its own event handler
                if self.is_double_battle:
                    self._handle_double_encounter_event(event)
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

                all_enemies_dead = (
                    self.enemy_dino.get('hp', 0) <= 0 and
                    (not self.is_double_battle or
                     not self.enemy_dino2 or
                     self.enemy_dino2.get('hp', 0) <= 0)
                )
                if all_enemies_dead:
                    if not self.message_box.visible and not self.trainer_dino_queue:
                        if self.is_trainer_battle and self.current_trainer_npc:
                            self.current_trainer_npc.defeated = True
                            self.defeated_trainers.add(self.current_trainer_npc.trainer_id)
                        self.is_trainer_battle = False
                        self.pop_to_world()  # safety net: enemy fainted but exit was missed
                    return

                result = self.encounter_ui.handle_input(event, active)

                if isinstance(result, str) and result.startswith("UseMove:"):
                    self.use_player_move_by_name(result.split("UseMove:", 1)[1])
                    return

                if result == "Run":
                    if self.is_trainer_battle:
                        self.message_box.queue_messages(
                            ["You can't run from a trainer battle!"], wait_for_input=True)
                    else:
                        self.pop_to_world()
                elif result == "Bag":
                    self.push_state('items')
                elif result == 'Party':
                    self.push_state('party')
                elif result == 'Defend':
                    self.use_defend()

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

    def check_type_chart_interact(self):
        if self.fading:
            return False
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[self.player.facing]
        for d in range(1, 3):
            if (px + dx * d, py + dy * d) in self.type_chart_tile_coords:
                self.push_state('type_chart')
                return True
        return False

    def check_lore_interact(self):
        if self.fading:
            return False
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[self.player.facing]
        for d in range(1, 3):
            if (px + dx * d, py + dy * d) in self.lore_tile_coords:
                self.message_box.queue_messages([
                    "A Tale of 2 Halves",
                    "One exists to provide energy",
                    "The other to rest",
                    "Both in harmony bring order to all",
                    "Though entropy takes place",
                    "Chaos exists when balance is broken",
                    "Only the other can balance the imbalanced",
                ], wait_for_input=True)
                return True
        return False

    def handle_world_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        trainer_approaching = any(
            npc.npc_type == 'trainer' and npc.state in ('spotted', 'walking', 'done') and not npc.defeated
            for npc in self.npcs
        )
        guard_active = any(
            npc.npc_type == 'guard' and npc.state in ('approaching', 'returning')
            for npc in self.npcs
        )
        cutscene_locking = self.cutscene and self.cutscene.get('phase') in ('intro_flash', 'approaching', 'dialogue', 'walking_away', 'flashing', 'skyy_walking', 'skyy_flash')
        if event.key == pygame.K_z:
            tx = self.player.rect.x // config.TILE_SIZE
            ty = self.player.rect.y // config.TILE_SIZE
            in_enc = (tx, ty) in self.encounter_tile_coords
            zone = self.get_player_zone(tx, ty)
            print(f"[DEBUG] tile=({tx}, {ty})  encounter_tile={in_enc}  zone={zone}")
        elif event.key == pygame.K_i and not self.fading and self.entrance_fade_state is None and not trainer_approaching and not guard_active and not cutscene_locking:
            self.push_state('menu')
        elif event.key == pygame.K_j:
            if self.check_type_chart_interact():
                pass
            elif self.check_box_interact():
                pass
            elif self.check_lore_interact():
                pass
            elif not self.interact_with_npc():
                self.pickup_item()

    def _spawn_world_npcs(self, world_file):
        self.npcs = []
        for spec in config.WORLD_NPCS.get(world_file, []):
            trainer_id, tx, ty, facing, sight, npc_type = spec
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty,
                      facing=facing, sight_range=sight, npc_type=npc_type)
            if trainer_id in self.defeated_trainers:
                npc.defeated = True
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
        if self.fading or self.cutscene:
            return False
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[self.player.facing]
        candidates = [(px + dx, py + dy), (px + dx * 2, py + dy * 2)]
        for npc in self.npcs:
            if (npc.tile_x, npc.tile_y) not in candidates:
                continue
            npc.face_toward_player(self.player)
            if npc.npc_type in ('guard', 'gym_guard'):
                if npc.npc_type == 'gym_guard' and not self.story_flags.get('amber_lab_done'):
                    dialog = ["The gym leader is not here right now."]
                else:
                    dialog = getattr(npc, 'block_dialog', ["..."])
                self.message_box.queue_messages(dialog, wait_for_input=True)
                return True
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
            if npc.npc_type == 'story':
                self._interact_story_npc(npc)
                return True
            data = TRAINER_DATA.get(npc.trainer_id, {})
            if npc.defeated or npc.state == 'done':
                npc.defeated = True
                dialog = data.get('dialog', {}).get('defeated', ["..."])
                self.message_box.queue_messages(dialog, wait_for_input=True)
                return True
            if npc.state == 'idle':
                dialog = data.get('dialog', {}).get('default', ["..."])
                self.message_box.queue_messages(
                    dialog, wait_for_input=True,
                    on_complete=lambda n=npc: self.start_trainer_battle(n))
                return True
            return True
        return False

    def _interact_story_npc(self, npc):
        if npc.trainer_id == 'amber':
            if (self.current_world_file == 'RESEARCH_LAB.tmx'
                    and self.story_flags.get('encounters_unlocked')
                    and not self.story_flags.get('amber_lab_done')):
                self._start_amber_lab_event()
            elif self.story_flags.get('amber_lab_done'):
                self.message_box.queue_messages(
                    ["Keep up the training! The first gym awaits you!"],
                    wait_for_input=True)
            else:
                self.message_box.queue_messages(
                    ["Please collect all 3 dinos and return here!"],
                    wait_for_input=True)
        elif npc.trainer_id == 'skyy':
            if not self.story_flags.get('gym1_accessible'):
                self._start_skyy_dialogue(npc)

    def _start_skyy_dialogue(self, npc):
        npc.face_toward_player(self.player)
        dx = self.player.rect.x // config.TILE_SIZE - npc.tile_x
        dy = self.player.rect.y // config.TILE_SIZE - npc.tile_y
        if abs(dx) >= abs(dy):
            self.player.facing = self.player.direction = 'left' if dx > 0 else 'right'
        else:
            self.player.facing = self.player.direction = 'up' if dy > 0 else 'down'
        self.player.image = self.player.animations[self.player.facing][0]
        msgs = self._split_dialogue(
            "These spacial events are not of natural occurrence",
            "Just years ago our region was normal and thriving",
            "With the discovery of 100% lossless solar energy we were thriving as a society",
            "But recently things have changed, what we relied on for power has been taken from us",
            "Constant power outages from solar flares and eclipses blocking the sun...",
            "Anyway... My name is Skyy, I hope to see you at my gym",
            "I've been needing something to distract me",
            "So thank you for reminding me",
            "See you in Sierra Town!",


        )
        self.cutscene = {'phase': 'skyy_walking', 'npc': npc, 'walk_target': (npc.tile_x, npc.tile_y + 7)}
        self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=self._on_skyy_dialogue_done)

    def _on_skyy_dialogue_done(self):
        if self.cutscene and self.cutscene.get('phase') == 'skyy_walking':
            npc = self.cutscene['npc']
            npc.facing = 'down'

    def _start_amber_lab_event(self):
        starter_names = set(config.DINO_BALL_MAP.values())
        starters = [d for d in self.player_dinos + self.box_dinos
                    if d.get('name') in starter_names]

        def open_picker():
            self._dino_picker = DinoPicker(starters, self.fonts, config.WIDTH, config.HEIGHT)
            self._dino_picker_starters = starters
            self.push_state('dino_picker')

        msgs = self._split_dialogue(
            "Thank you for returning the dinos that we were missing. "
            "It seemed they all got along with you very well! "
            "For helping out during this chaotic event, I want you to keep your favorite!"
        )
        self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=open_picker)

    def _finish_amber_lab(self, chosen_idx):
        self.pop_state()
        starters = self._dino_picker_starters
        chosen = starters[chosen_idx]
        for d in starters:
            if d is not chosen:
                if d in self.player_dinos:
                    self.player_dinos.remove(d)
                if d in self.box_dinos:
                    self.box_dinos.remove(d)
        if chosen not in self.player_dinos:
            if len(self.player_dinos) < self.PARTY_LIMIT:
                self.player_dinos.append(chosen)
            if chosen in self.box_dinos:
                self.box_dinos.remove(chosen)
        self.active_dino_index = 0
        self._dino_picker = None
        self._dino_picker_starters = []
        dino_name = chosen['name']
        msgs = self._split_dialogue(
            f"Great choice, {dino_name} will love to be by your side as your journey unfolds! "
            "I recommend training harder and progressing through each gym if you would like to "
            "help our mission of solving these solar flares and eclipses from disrupting our life. "
            "The first gym is just south of us, I know you can handle it!"
        )
        self.story_flags['amber_lab_done'] = True
        self.message_box.queue_messages(msgs, wait_for_input=True)

    def _apply_ball_items(self, ball_items):
        for pos in list(self.map_ball_items.keys()):
            self.items_on_map.pop(pos, None)
        self.map_ball_items = {}
        self.map_ball_images = {}
        for (tx, ty), (item_name, img) in ball_items.items():
            if (self.current_world_file, tx, ty) in self.picked_up_world_items:
                continue
            self.items_on_map[(tx, ty)] = item_name
            self.map_ball_items[(tx, ty)] = item_name
            if img is not None:
                display_img = img
            else:
                item_icons = getattr(self, 'item_icons', {})
                icon = item_icons.get(item_name)
                if icon is not None:
                    display_img = pygame.transform.scale(icon, (config.TILE_SIZE, config.TILE_SIZE))
                else:
                    display_img = self._ballwhite_img
            self.map_ball_images[(tx, ty)] = display_img

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
        self.map_ball_items.pop((px, py), None)
        self.map_ball_images.pop((px, py), None)
        self.picked_up_world_items.add((self.current_world_file, px, py))
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
        if self.state == 'title':
            self.title_screen.update(dt)
            return

        if self.state == 'badge_earned':
            if getattr(self, 'badge_earned_screen', None):
                self.badge_earned_screen.update(dt)
            return

        if self.state == 'intro':
            if self.intro_sequence:
                self.intro_sequence.update(dt)
                if self.intro_sequence.done:
                    self.intro_sequence = None
                    self.state_stack = ['world']
                    self.message_box.queue_messages(
                        ["...beep...beep...beep..."], wait_for_input=True
                    )
            return

        self.play_time_seconds += dt
        self.update_day_night(dt)
        self.update_heal_anim(dt)
        self.update_hit_flash(dt)
        self.message_box.update(dt)

        if getattr(self, '_post_xp_callback', None):
            if not (hasattr(self, 'encounter_ui') and self.encounter_ui.is_xp_animating()):
                cb = self._post_xp_callback
                self._post_xp_callback = None
                cb()

        if 'encounter' in self.state_stack and hasattr(self, 'encounter_ui'):
            active = self.player_dinos[self.active_dino_index]
            if self.is_double_battle:
                p2 = self.player_dinos[1] if len(self.player_dinos) > 1 else active
                self.encounter_ui.update(dt, active, p2,
                                         self.enemy_dino,
                                         self.enemy_dino2 or self.enemy_dino)
            else:
                self.encounter_ui.update(dt, active, self.enemy_dino)

        # Encounter intro animation completion — kept here so draw() never triggers game logic
        if 'encounter' in self.state_stack and self.encounter_anim is not None:
            now = pygame.time.get_ticks()
            if now - self.encounter_anim["start_time"] >= self.encounter_anim["duration"]:
                anim = self.encounter_anim
                self.encounter_anim = None
                if not self.is_double_battle:
                    self.encounter.current_dino_surface = anim["frames"][0]
                self.enemy_dino["image"] = anim["frames"][0]
                self.message_box.queue_messages(
                    [self.encounter_text, "What will you do?"],
                    wait_for_input=True
                )

        if self.message_box.visible:
            return

        # After any message clears in double battle, auto-arm p1 selection for the new turn
        if (self.state == 'encounter' and self.is_double_battle
                and self.encounter_anim is None and self.double_phase is None):
            self._double_start_p1_turn()

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
                if self.cutscene:
                    self._update_cutscene(dt)
                if self.cutscene_flash:
                    self._update_cutscene_flash(dt)
                if self.forced_walk_npc:
                    self._update_forced_walk(dt)
                self.update_camera()
                for npc in self.npcs:
                    if self.cutscene and npc is self.cutscene.get('npc'):
                        continue
                    npc.update(dt, self.player, self)
            else:
                self.fade_alpha += 10
                if self.fade_alpha >= 255:
                    self.fade_alpha = 255
                    self.fading = False
                    self.push_state('encounter')

            self.check_story_events()
            self._check_amber_blocker()
            self._maybe_add_gym_blocker()
            self._maybe_add_skyy()
            self._maybe_add_gray_rival()

    # --- Draw ---

    def draw(self):
        if self.state == 'title':
            self.title_screen.draw(self.screen, os.path.exists(SAVE_PATH))
            pygame.display.flip()
            return

        if self.state == 'intro':
            if self.intro_sequence:
                self.intro_sequence.draw(self.screen)
            pygame.display.flip()
            return

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
            if self.sandbox:
                tag = self.fonts['XS'].render("SANDBOX MODE", True, (255, 80, 80))
                self.screen.blit(tag, (config.WIDTH - tag.get_width() - 6, 6))
            if self.cutscene_flash and self.cutscene_flash['alpha'] > 0:
                _flash = pygame.Surface((config.WIDTH, config.HEIGHT))
                _flash.fill((255, 235, 150))
                _flash.set_alpha(int(self.cutscene_flash['alpha']))
                self.screen.blit(_flash, (0, 0))

        elif background_state == 'encounter' and current_state != 'encounter':
            if self.is_double_battle:
                self.encounter.draw(self.screen)
            else:
                self.encounter.draw(self.screen)
                self.encounter_ui.draw(self.screen, self.player_dinos[self.active_dino_index],
                                       self.enemy_dino, self.encounter_text,
                                       trainer_total=self.trainer_dinos_total if self.is_trainer_battle else 0,
                                       trainer_defeated=self.trainer_dinos_defeated,
                                       pod_icon=self.item_image if self.is_trainer_battle else None,
                                       field_effects=self.field_effects)

        if current_state == 'encounter':
            # Compute hit-flash sprite visibility (per-dino for double battles)
            _enemy1_vis = _enemy2_vis = _player1_vis = _player2_vis = True
            if self.hit_flash and not self.encounter_anim:
                flash_count = int(self.hit_flash['timer'] / self.hit_flash['interval'])
                vis = (flash_count % 2 == 0)
                t = self.hit_flash['target']
                if t in ('enemy', 'enemy1'):   _enemy1_vis = vis
                elif t == 'enemy2':            _enemy2_vis = vis
                elif t in ('player', 'player1'): _player1_vis = vis
                elif t == 'player2':           _player2_vis = vis
            _enemy_vis  = _enemy1_vis   # alias for single-battle paths
            _player_vis = _player1_vis

            if self.is_double_battle:
                # Double battle draw path
                if self.encounter_anim:
                    anim = self.encounter_anim
                    now  = pygame.time.get_ticks()
                    if now - anim["last_switch"] >= anim["interval"]:
                        anim["frame_idx"] = (anim["frame_idx"] + 1) % len(anim["frames"])
                        anim["last_switch"] = now
                    self.encounter.frame1 = anim["frames"][anim["frame_idx"]]
                    self.encounter.draw(self.screen)
                else:
                    self.encounter.draw(self.screen,
                                        e1_visible=_enemy1_vis and self.enemy_dino.get('hp', 0) > 0,
                                        e2_visible=_enemy2_vis and (self.enemy_dino2.get('hp', 0) > 0 if self.enemy_dino2 else False))

                p1 = self.player_dinos[0] if self.player_dinos else None
                p2 = self.player_dinos[1] if len(self.player_dinos) > 1 else None
                e1 = self.enemy_dino
                e2 = self.enemy_dino2 or self.enemy_dino
                active_dino = p2 if self.double_phase == 'p2' else p1
                msg_active   = self.message_box.visible
                display_text = (self.message_box.message[:self.message_box.char_index]
                                if msg_active else self.encounter_text)
                msg_awaiting = (msg_active and self.message_box.wait_for_input and
                                self.message_box.char_index >= len(self.message_box.message))
                e1_show = _enemy1_vis and e1.get('hp', 0) > 0
                e2_show = _enemy2_vis and (e2.get('hp', 0) > 0 if e2 else False)
                self.encounter_ui.draw(
                    self.screen, p1, p2, e1, e2,
                    display_text,
                    active_dino=active_dino,
                    show_actions=not msg_active and self.double_phase is not None,
                    msg_awaiting_input=msg_awaiting,
                    p1_visible=_player1_vis,
                    p2_visible=_player2_vis,
                    e1_visible=e1_show,
                    e2_visible=e2_show,
                )
            else:
                # Single battle draw path
                if self.encounter_anim:
                    anim = self.encounter_anim
                    now  = pygame.time.get_ticks()
                    if now - anim["last_switch"] >= anim["interval"]:
                        anim["frame_idx"] = (anim["frame_idx"] + 1) % len(anim["frames"])
                        anim["last_switch"] = now
                    frame = anim["frames"][anim["frame_idx"]]
                    self.encounter.current_dino_surface = frame
                    self.encounter.draw(self.screen)
                else:
                    self.encounter.draw(self.screen, enemy_visible=_enemy_vis)

                msg_active   = self.message_box.visible
                display_text = (self.message_box.message[:self.message_box.char_index]
                                if msg_active else self.encounter_text)
                msg_awaiting = (msg_active and self.message_box.wait_for_input and
                                self.message_box.char_index >= len(self.message_box.message))
                self.encounter_ui.draw(self.screen, self.player_dinos[self.active_dino_index],
                                       self.enemy_dino, display_text, show_actions=not msg_active,
                                       trainer_total=self.trainer_dinos_total if self.is_trainer_battle else 0,
                                       trainer_defeated=self.trainer_dinos_defeated,
                                       pod_icon=self.item_image if self.is_trainer_battle else None,
                                       msg_awaiting_input=msg_awaiting,
                                       player_visible=_player_vis,
                                       field_effects=self.field_effects)

        if background_state == 'encounter' and current_state == 'encounter':
            if self.night_active and not self.dn_transitioning:
                self.screen.blit(self._night_overlay_battle, (0, 0))
            if self.dn_transitioning:
                t = self.dn_transition_timer / self.DN_TRANSITION_DURATION
                alpha = int(255 * (1.0 - abs(t * 2 - 1.0)))
                self._dn_fade.set_alpha(alpha)
                self.screen.blit(self._dn_fade, (0, 0))
            if self.event_overlay_active:
                self.screen.blit(self._event_overlay_battle, (0, 0))

        elif current_state == 'type_chart':
            img = pygame.transform.scale(self.type_chart_image, (config.WIDTH, config.HEIGHT))
            self.screen.blit(img, (0, 0))

        elif current_state == 'trainer_card':
            self.trainer_card_screen.draw(self.screen)

        elif current_state == 'badge_earned':
            self.screen.fill((0, 0, 0))
            if getattr(self, 'badge_earned_screen', None):
                self.badge_earned_screen.draw(self.screen)

        elif current_state == 'move_info':
            if self.move_info_screen:
                self.move_info_screen.draw(self.screen)

        elif current_state == 'dinodex':
            self.dinodex_screen.draw(self.screen)

        elif current_state in ('menu', 'party', 'items', 'shop', 'box', 'dino_picker'):
            if background_state == 'encounter':
                if self.night_active and not self.dn_transitioning:
                    self.screen.blit(self._night_overlay_battle, (0, 0))
                if self.dn_transitioning:
                    t = self.dn_transition_timer / self.DN_TRANSITION_DURATION
                    alpha = int(255 * (1.0 - abs(t * 2 - 1.0)))
                    self._dn_fade.set_alpha(alpha)
                    self.screen.blit(self._dn_fade, (0, 0))
                if self.event_overlay_active:
                    self.screen.blit(self._event_overlay_battle, (0, 0))
            elif background_state == 'world' and current_state not in ('shop', 'box', 'dino_picker'):
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
            elif current_state == 'dino_picker' and self._dino_picker:
                self._dino_picker.draw(self.screen)

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
                    enemy_name=self.enemy_dino['name'],
                    state_multiplier=0.5,   # catching
                )
                _catch_bench = {2: 1.33, 3: 1.25, 4: 1.1, 5: 1.0}
                _alive_ct    = len(alive)
                _act_m       = 2.0 if _alive_ct == 1 else 1.5
                _ben_m       = _catch_bench.get(_alive_ct, 1.0)
                for d in alive:
                    mult = _act_m if d is active else _ben_m
                    self.award_xp(d, int(round(xp_gain * mult)))

            to_evolve = [(d, self.check_evolution(d)) for d in self.player_dinos if self.check_evolution(d)]

            if len(self.player_dinos) < self.PARTY_LIMIT:
                self.player_dinos.append(base_dino)
                added_msg = f"{self.enemy_dino['name']} was added to your party!"
            else:
                self.box_dinos.append(base_dino)
                added_msg = f"{self.enemy_dino['name']} was sent to your Box!"

            msgs = [f"You caught {self.enemy_dino['name']}!", added_msg]
            if alive and active is not None:
                _ct_act_m = 2.0 if len(alive) == 1 else 1.5
                _ct_ben_m = {2: 1.33, 3: 1.25, 4: 1.1, 5: 1.0}.get(len(alive), 1.0)
                msgs.append(f"{active['name']} has gained {int(round(xp_gain * _ct_act_m))} XP!")
                if len(alive) > 1:
                    msgs.append(f"Each party dino gained {int(round(xp_gain * _ct_ben_m))} XP!")

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
        attacker['defending'] = False
        attacker['_prev_action_defend'] = False

        if move_index < 0 or move_index >= len(attacker['moveset']):
            return

        move          = attacker['moveset'][move_index]
        move_name     = move['name']
        power         = max(0, move.get('damage', 0))
        acc           = move.get('accuracy', 100)
        mtype         = move.get('type', 'normal')
        ability       = move.get('ability')
        pierces_defend = move.get('pierces_defend', False)

        # Enforce lock — override chosen move if locked
        lock_turns = attacker.get('lock_turns_left', 0)
        if lock_turns > 0:
            locked_name = attacker.get('locked_move')
            forced = next((m for m in attacker['moveset'] if m['name'] == locked_name), None)
            if forced:
                move          = forced
                move_name     = forced['name']
                power         = max(0, forced.get('damage', 0))
                acc           = forced.get('accuracy', 100)
                mtype         = forced.get('type', 'normal')
                ability       = forced.get('ability')
                pierces_defend = forced.get('pierces_defend', False)
            attacker['lock_turns_left'] = lock_turns - 1
            if attacker['lock_turns_left'] == 0:
                attacker.pop('locked_move', None)

        attacker['last_move_used'] = move_name

        # Defend is always priority — enemy decides to defend BEFORE attack order is resolved
        if self.is_trainer_battle:
            _rank = TRAINER_DATA.get(
                getattr(self.current_trainer_npc, 'trainer_id', ''), {}
            ).get('rank', 'lowest') if self.current_trainer_npc else 'lowest'
            if self._should_enemy_defend(_rank):
                self.enemy_defend_uses_remaining -= 1
                self.enemy_dino['defending'] = True
                n = self.enemy_defend_uses_remaining
                _acc, _mn, _att, _def = acc, move_name, attacker, defender
                _pwr, _mtype, _abl, _pd = power, mtype, ability, pierces_defend
                def _after_announce():
                    def _end_turn():
                        self._clear_defending_flags()
                        fe = list(self._tick_field_effects())
                        fe.append("What will you do?")
                        self.message_box.queue_messages(fe, wait_for_input=True)
                    if random.random() * 100 > _acc:
                        self._clear_defending_flags()
                        self.message_box.queue_messages(
                            [f"{_att['name']} used {_mn}!", "But it missed!", "What will you do?"],
                            wait_for_input=True)
                    else:
                        self._apply_player_attack(_att, _def, _mn, _pwr, _mtype, _abl,
                                                  pierces_defend=_pd, after=_end_turn)
                self.message_box.queue_messages(
                    [f"{self._trainer_name}'s {self.enemy_dino['name']} braced for impact!",
                     f"({n} Defend{'s' if n != 1 else ''} remaining)"],
                    wait_for_input=True, on_complete=_after_announce)
                return

        speed_swap   = any(fx['effect'] == 'speed_swap' for fx in self.field_effects)
        p_spd        = self._get_effective_stat(attacker, 'speed')
        e_spd        = self._get_effective_stat(defender, 'speed')

        # Priority: higher priority always goes first; ties fall back to speed
        p_priority = MOVE_DATA.get(move_name, {}).get('priority', 0)
        _peek_rank = 'lowest'
        if self.is_trainer_battle and self.current_trainer_npc:
            _peek_rank = TRAINER_DATA.get(
                self.current_trainer_npc.trainer_id, {}).get('rank', 'lowest')
        _peeked    = self._pick_enemy_move(defender, attacker, _peek_rank)
        e_priority = MOVE_DATA.get((_peeked or {}).get('name', ''), {}).get('priority', 0)

        if p_priority != e_priority:
            player_first = p_priority > e_priority
        elif speed_swap:
            player_first = p_spd <= e_spd
        else:
            player_first = p_spd >= e_spd

        if player_first:
            if random.random() * 100 > acc:
                self.message_box.queue_messages(
                    [f"{attacker['name']} used {move_name}!", "But it missed!"],
                    wait_for_input=True, on_complete=self._enemy_turn)
                return
            self._apply_player_attack(attacker, defender, move_name, power, mtype, ability,
                                      pierces_defend=pierces_defend, after=self._enemy_turn)
        else:
            # Enemy is faster — it strikes first, then player attacks if still alive
            def then_player():
                p = self.player_dinos[self.active_dino_index]
                if p.get('hp', 0) <= 0:
                    return
                if random.random() * 100 > acc:
                    self._clear_defending_flags()
                    self.message_box.queue_messages(
                        [f"{p['name']} used {move_name}!", "But it missed!", "What will you do?"],
                        wait_for_input=True)
                    return
                self._apply_player_attack(p, self.enemy_dino, move_name, power, mtype, ability,
                                          pierces_defend=pierces_defend, after=None)
            self._enemy_turn(after=then_player)

    def _apply_player_attack(self, attacker, defender, move_name, power, mtype, ability=None, pierces_defend=False, after=None):
        # Trainer dino defending check — only blocks damage moves
        if self.is_trainer_battle and defender.get('defending', False) and not pierces_defend and power > 0:
            defender['defending'] = False
            msgs = [f"{attacker['name']} used {move_name}!",
                    f"The trainer's {defender['name']} defended and took no damage!"]
            msgs.extend(self._apply_move_ability(ability, attacker, defender))
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                msgs.extend(self._tick_field_effects())
                msgs.extend(self._tick_dino_effects())
                self._clear_defending_flags()
                msgs.append("What will you do?")
                self.message_box.queue_messages(msgs, wait_for_input=True)
            return

        defender['defending'] = False
        STAB    = stab_multiplier(mtype, attacker['type'])
        eff_val = type_effectiveness_value(mtype, defender['type'])
        rnd     = random_damage_factor()
        atk     = self._get_effective_stat(attacker, 'attack')
        dfs     = self._get_effective_stat(defender, 'defense')
        lvl     = max(1, attacker['level'])

        type_boost = next((fx['multiplier'] for fx in self.field_effects
                           if fx['effect'] == 'type_power' and fx.get('boost_type') == mtype), 1.0)
        raw = Damage(lvl, atk, power, dfs, STAB, eff_val, rnd) * type_boost
        dmg = max(1, int(raw)) if power > 0 else 0
        defender['hp'] = max(0, defender['hp'] - dmg)
        if dmg > 0:
            if self.is_double_battle:
                flash_target = 'enemy1' if defender is self.enemy_dino else 'enemy2'
            else:
                flash_target = 'enemy'
            self.trigger_hit_flash(flash_target)

        msgs = [f"{attacker['name']} used {move_name}!"]
        if power > 0:
            if eff_val > 10:
                msgs.append("It's super effective!")
            elif 0 < eff_val < 10:
                msgs.append("It's not very effective...")
            elif eff_val <= 0:
                msgs.append("It had no effect...")
        msgs.extend(self._apply_move_ability(ability, attacker, defender, dmg))

        if defender['hp'] <= 0:
            self.stats_enemies_defeated += 1
            self.encounter_ui.in_fight_menu = False
            faint_prefix = f"{self._trainer_name}'s" if self.is_trainer_battle else "The wild"
            faint_msg = f"{faint_prefix} {defender['name']} fainted!"
            if self.is_trainer_battle:
                t_data = TRAINER_DATA.get(self.current_trainer_npc.trainer_id, {}) if self.current_trainer_npc else {}
                multiplier = 1.0 if t_data.get('rank') == 'rival' else 0.9
            else:
                multiplier = 0.8
            xp_gain = calculate_xp_gain(
                player_level=attacker['level'],
                opponent_level=defender['level'],
                enemy_name=defender['name'],
                state_multiplier=multiplier,
            )
            level_up_msgs = self._grant_party_xp_and_level_ups(xp_gain)
            _disp_alive = len([d for d in self.player_dinos if d.get('hp', 0) > 0])
            _disp_act_m = 2.0 if _disp_alive == 1 else 1.5
            _disp_ben_m = {2: 1.33, 3: 1.25, 4: 1.1, 5: 1.0}.get(_disp_alive, 1.0)
            xp_msgs = [f"{attacker['name']} has gained {int(round(xp_gain * _disp_act_m))} XP!"]
            if _disp_alive > 1:
                xp_msgs.append(f"Each party dino gained {int(round(xp_gain * _disp_ben_m))} XP!")
            xp_msgs.extend(level_up_msgs)

            def handle_evolutions():
                coin_reward = 0
                if self.is_trainer_battle:
                    self.trainer_dinos_defeated += 1
                    if self.is_double_battle:
                        # Let _double_turn_end decide when the battle is won
                        if after:
                            after()
                        return
                    if self.trainer_dino_queue:
                        self._send_next_trainer_dino()
                        return
                    if self.current_trainer_npc:
                        self.current_trainer_npc.defeated = True
                        self.defeated_trainers.add(self.current_trainer_npc.trainer_id)
                        coin_reward = TRAINER_DATA.get(
                            self.current_trainer_npc.trainer_id, {}).get('reward_coins', 0)
                    self.is_trainer_battle = False

                def finish_battle():
                    for dino in self.player_dinos:
                        dino['stat_stages'] = {"attack": 0, "defense": 0, "speed": 0}
                        dino['defending']   = False
                    evolved = False
                    for dino in self.player_dinos:
                        evo_target = self.check_evolution(dino)
                        if evo_target:
                            evolved = True
                            self.start_evolution(dino, evo_target)
                            self.pop_to_world()
                    if not evolved:
                        self.pop_to_world()
                    cb = self._post_trainer_battle_cb
                    if cb:
                        self._post_trainer_battle_cb = None
                        cb()

                if coin_reward > 0:
                    self.coins += coin_reward
                    self.message_box.queue_messages(
                        [f"You received {coin_reward} coins!"],
                        wait_for_input=True, on_complete=finish_battle)
                else:
                    finish_battle()

            def show_xp():
                if self.is_double_battle:
                    # Skip XP animation mid-battle; award silently then continue turn
                    handle_evolutions()
                    return
                self.encounter_ui.unfreeze_xp()
                def after_xp_msgs():
                    self._post_xp_callback = handle_evolutions
                self.message_box.queue_messages(xp_msgs, wait_for_input=True, on_complete=after_xp_msgs)

            def show_faint():
                self.message_box.queue_messages([faint_msg], wait_for_input=True, on_complete=show_xp)

            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=show_faint)
        else:
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                msgs.extend(self._tick_field_effects())
                msgs.extend(self._tick_dino_effects())
                self._clear_defending_flags()
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

    def use_defend(self):
        if self.message_box.visible or self.encounter_anim is not None:
            return
        attacker = self.player_dinos[self.active_dino_index]
        if attacker.get('_prev_action_defend', False):
            self.message_box.queue_messages(
                [f"{attacker['name']} can't defend twice in a row!"], wait_for_input=True)
            return
        if self.defend_uses_remaining <= 0:
            self.message_box.queue_messages(
                ["Your team has no Defends left this battle!"], wait_for_input=True)
            return
        self.defend_uses_remaining -= 1
        attacker['defending'] = True
        attacker['_prev_action_defend'] = True
        self.message_box.queue_messages(
            [f"{attacker['name']} braced for impact!",
             f"({self.defend_uses_remaining} Defend{'s' if self.defend_uses_remaining != 1 else ''} remaining)"],
            wait_for_input=True, on_complete=self._enemy_turn)

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

        # Get trainer rank for AI (wild dinos use lowest logic)
        rank = 'lowest'
        if self.is_trainer_battle and self.current_trainer_npc:
            t_data = TRAINER_DATA.get(self.current_trainer_npc.trainer_id, {})
            rank = t_data.get('rank', 'lowest')

        # Trainer AI: decide to defend? (checks current defending flag to block back-to-back)
        if self._should_enemy_defend(rank):
            self.enemy_defend_uses_remaining -= 1
            attacker['defending'] = True
            n = self.enemy_defend_uses_remaining
            msgs = [f"{self._trainer_name}'s {attacker['name']} braced for impact!",
                    f"({n} Defend{'s' if n != 1 else ''} remaining)"]
            msgs.extend(self._tick_field_effects())
            self._clear_defending_flags()
            msgs.append("What will you do?")
            self.message_box.queue_messages(msgs, wait_for_input=True)
            return

        # Taking an action — clear defending flag
        attacker['defending'] = False

        # Pick move based on rank
        if self.is_trainer_battle:
            move = self._pick_enemy_move(attacker, defender, rank)
        else:
            move = random.choice(attacker['moveset'])

        # Enforce lock — override picked move if locked
        lock_turns = attacker.get('lock_turns_left', 0)
        if lock_turns > 0:
            locked_name = attacker.get('locked_move')
            forced = next((m for m in attacker.get('moveset', []) if m['name'] == locked_name), None)
            if forced:
                move = forced
            attacker['lock_turns_left'] = lock_turns - 1
            if attacker['lock_turns_left'] == 0:
                attacker.pop('locked_move', None)

        if move:
            attacker['last_move_used'] = move['name']

        if move is None:
            msgs = [f"The wild {attacker['name']} is loafing around."]
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                msgs.append("What will you do?")
                self.message_box.queue_messages(msgs, wait_for_input=True)
            return

        mtype   = move.get('type', 'normal')
        power   = max(0, move.get('damage', 0))
        acc     = move.get('accuracy', 100)
        ability = move.get('ability')
        prefix  = f"{self._trainer_name}'s " if self.is_trainer_battle else "The wild "

        if random.random() * 100 >= acc:
            msgs = [f"{prefix}{attacker['name']} used {move['name']}!", "But it missed!"]
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                self._clear_defending_flags()
                msgs.append("What will you do?")
                self.message_box.queue_messages(msgs, wait_for_input=True)
            return

        # Defend check — only blocks damage moves; 0-power moves (self-buffs, terrain) pass through
        if defender.get('defending', False) and not move.get('pierces_defend', False) and power > 0:
            defender['defending'] = False
            msgs = [f"{prefix}{attacker['name']} used {move['name']}!",
                    f"{defender['name']} defended and took no damage!"]
            msgs.extend(self._apply_move_ability(ability, attacker, defender))
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                msgs.extend(self._tick_field_effects())
                msgs.extend(self._tick_dino_effects())
                self._clear_defending_flags()
                msgs.append("What will you do?")
                self.message_box.queue_messages(msgs, wait_for_input=True)
            return

        STAB    = stab_multiplier(mtype, attacker['type'])
        eff_val = type_effectiveness_value(mtype, defender['type'])
        rnd     = random_damage_factor()
        atk     = self._get_effective_stat(attacker, 'attack')
        dfs     = self._get_effective_stat(defender, 'defense')
        lvl     = max(1, attacker['level'])

        type_boost = next((fx['multiplier'] for fx in self.field_effects
                           if fx['effect'] == 'type_power' and fx.get('boost_type') == mtype), 1.0)
        dmg = max(1, int(Damage(lvl, atk, power, dfs, STAB, eff_val, rnd) * type_boost)) if power > 0 else 0
        defender['hp'] = max(0, defender['hp'] - dmg)
        if dmg > 0:
            self.trigger_hit_flash('player')

        msgs = [f"{prefix}{attacker['name']} used {move['name']}!"]
        if power > 0:
            if eff_val > 10:       msgs.append("It's super effective!")
            elif 0 < eff_val < 10: msgs.append("It's not very effective...")
            elif eff_val <= 0:     msgs.append("It had no effect...")
        msgs.extend(self._apply_move_ability(ability, attacker, defender, dmg))

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
            msgs.extend(self._tick_field_effects())
            self._clear_defending_flags()
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

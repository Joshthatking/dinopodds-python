import pygame
import pytmx
import json
import re
import math
from player import Player
from npc import NPC
import os
import config
from screens import *
from data import *
import random
import story as _story

SAVE_PATH = 'dinopodds_save.json'

# CORN_MAZE5's 3x3 tomb monument (world tile coords) — the interactable
# lore object housing the Scarecrux <-> Gourdecrux night transformation.
GOURDECRUX_TOMB_TILES = {
    (124, -68), (125, -68), (126, -68),
    (124, -67), (125, -67), (126, -67),
    (124, -66), (125, -66), (126, -66),
}
GOURDECRUX_TOMB_CENTER = (125, -67)


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
        for base in ("Vusion", "Anemamace", "Corlave", "Creuw", "Luna", "Prowscar", "Floravel", "Bullicorn", "Netaslam", "Netyrant", "Sortle", "Sharktastrophe", "Magnecrab", "Volkit", "Drafyton", "Auraliz", "Voltzbee", "Teamtwood", "Tygraflare", "Bouldava", "Ghoulflame", "Scarecrux", "Palidian", "Rockull", "Prickly", "Cyflactus", "Gourdecrux", "Rhysnow", "Seasoo", "Chomper", "Cobaltion", "Roxer", "Skolt"):
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
        self.quest_debug_screen = QuestDebugScreen(self)
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
        self.message_box = DialogueBox(config.WIDTH, self.fonts)
        self.route_banner = RouteBanner(self.fonts)

        # Sandbox-only coordinate teleport input (Ctrl+Z)
        self.coord_input_active = False
        self.coord_input_text = ''

        # Heal animation state
        self.heal_anim = None
        self.yes_no_prompt = None
        self.yes_no_callback = None
        self.cutscene = None
        self.cutscene_flash = None
        self.orb_fx = None
        self.abby_follower = None
        self.abby_dinos = []
        self.is_vanessa_battle = False
        self.vanessa_dino_queue = []
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
        self._maybe_add_gym2_blocker()
        self._maybe_add_route2_blocker()
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

        # Reset any trainer stuck mid-approach so rechallenge (and the "i" menu,
        # which is blocked while a trainer is spotted/walking/done) works again
        for npc in self.npcs:
            if (getattr(npc, 'npc_type', '') == 'trainer'
                    and not npc.defeated
                    and npc.state in ('spotted', 'walking', 'done')):
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                hx, hy = getattr(npc, 'home_tile', (npc.tile_x, npc.tile_y))
                npc.tile_x, npc.tile_y = hx, hy
                npc.pos_x = float(hx * config.TILE_SIZE)
                npc.pos_y = float(hy * config.TILE_SIZE)
                npc.target_x, npc.target_y = npc.pos_x, npc.pos_y
                npc.rect.topleft = (int(npc.pos_x), int(npc.pos_y))
                npc.facing = getattr(npc, 'home_facing', npc.facing)
                npc.is_moving = False
                npc.state = 'idle'
                npc.spot_timer = 0.0
                npc._double_engaged = False
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
        self._maybe_add_gym2_blocker()
        self._maybe_add_route2_blocker()
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
        defense = Base_Stats(base_stats["defense"], level, p=0.9)
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
            dino['defense'] = Base_Stats(base_stats["defense"], dino['level'], p=0.9)
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
        active_mult = ACTIVE_XP_MULT_SOLO if alive_count == 1 else ACTIVE_XP_MULT_PARTY
        bench_mult  = BENCH_XP_MULT.get(alive_count, 1.0)
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
                dino['defense'] = Base_Stats(base_stats['defense'], dino['level'], p=0.9)
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
        dino['defense'] = Base_Stats(base_stats['defense'], level, p=0.9)
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

    def check_zone_banner(self, tile_x, tile_y, direction):
        """Called after the player finishes a tile-step (see
        Player.check_for_zone_banner()). Shows the route/town banner if
        the tile just arrived at is one of ZONE_BANNER_TRANSITIONS's
        strips and `direction` is one of that strip's mapped directions."""
        entry = ZONE_BANNER_LOOKUP.get((tile_x, tile_y))
        if entry and direction in entry:
            self.route_banner.show(entry[direction])

    def trigger_encounter(self, forced_dino=None, forced_level=None):
        if forced_dino:
            dino_key, level = forced_dino, forced_level
        else:
            tile_x = self.player.rect.x // config.TILE_SIZE
            tile_y = self.player.rect.y // config.TILE_SIZE
            zone = self.get_player_zone(tile_x, tile_y)
            # print(f"[ENCOUNTER] tile=({tile_x},{tile_y}) zone={zone}")

            zone_data = ENCOUNTER_ZONES[zone]
            dino_key = pick_zone_dino(zone_data, self.night_active)
            if dino_key is None:
                return  # nothing available right now (e.g. a night-only zone by day)
            level = random.randint(*zone_data["level_range"])

        self.player.moving = False
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y
        self.player.pos_x = float(self.player.rect.x)
        self.player.pos_y = float(self.player.rect.y)
        self.active_dino_index = 0
        self.fading = True
        self.fade_alpha = 0

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
        elif npc.trainer_id == 'log' and self.current_world_file == 'GYM2.tmx':
            self._post_trainer_battle_cb = self._on_log_gym_won

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
            dialog = self._tag_dialogue(data.get('name', 'Trainer'), data.get('dialog', {}).get('default', ["Double battle!"]))
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

    def _abby_is_ally(self):
        """True when Abby is fighting alongside the player in this double
        battle, once she's joined post-escort — the grunt pair, or the
        Vanessa boss fight."""
        if not (self.abby_follower and self.abby_dinos):
            return False
        if self.is_vanessa_battle:
            return True
        return bool(
            self.current_trainer_npc and self.current_trainer_npc2
            and {self.current_trainer_npc.trainer_id, self.current_trainer_npc2.trainer_id} == {'grunt1', 'grunt2'}
        )

    def _double_battle_p2(self):
        """The player's double-battle ally slot: Abby's own first dino once
        she's fighting alongside the player against the grunts, otherwise
        the player's own second party member as before."""
        if self._abby_is_ally():
            return self.abby_dinos[0]
        return self.player_dinos[1] if len(self.player_dinos) > 1 else None

    def _double_continue_turn(self):
        """Chain p2 auto → e1 auto → e2 auto → turn end after player's p1 action."""
        p1 = self.player_dinos[0] if self.player_dinos else None
        p2 = self._double_battle_p2()
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
        npc1 = self.current_trainer_npc
        npc2 = self.current_trainer_npc2
        if npc1:
            npc1.defeated = True
            self.defeated_trainers.add(npc1.trainer_id)
            coin_reward += TRAINER_DATA.get(npc1.trainer_id, {}).get('reward_coins', 0)
        if npc2:
            npc2.defeated = True
            self.defeated_trainers.add(npc2.trainer_id)
            coin_reward += TRAINER_DATA.get(npc2.trainer_id, {}).get('reward_coins', 0)

        grunt_pair = bool(npc1 and npc2 and
                          {npc1.trainer_id, npc2.trainer_id} == {'grunt1', 'grunt2'})

        alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
        active = self.player_dinos[self.active_dino_index] if self.player_dinos else None
        xp_total = 0
        if alive and active:
            ref_level = active['level']
            mult1 = 1.0 if npc1 and is_boss_tier_trainer(TRAINER_DATA.get(npc1.trainer_id, {})) else 0.9
            xp_total += calculate_xp_gain(ref_level, self.enemy_dino['level'], enemy_name=self.enemy_dino['name'], state_multiplier=mult1)
            if self.enemy_dino2:
                mult2 = 1.0 if npc2 and is_boss_tier_trainer(TRAINER_DATA.get(npc2.trainer_id, {})) else 0.9
                xp_total += calculate_xp_gain(ref_level, self.enemy_dino2['level'], enemy_name=self.enemy_dino2['name'], state_multiplier=mult2)

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
            if grunt_pair:
                self._start_grunts_walk_away(npc1, npc2)

        msgs = ["You won the double battle!"]
        if coin_reward > 0:
            self.coins += coin_reward
            msgs.append(f"You received {coin_reward} coins!")
        if xp_total > 0 and active:
            _db_act_m = ACTIVE_XP_MULT_SOLO if len(alive) == 1 else ACTIVE_XP_MULT_PARTY
            _db_ben_m = BENCH_XP_MULT.get(len(alive), 1.0)
            msgs.append(f"{active['name']} gained {int(round(xp_total * _db_act_m))} XP!")
            if len(alive) > 1:
                msgs.append(f"Each party dino gained {int(round(xp_total * _db_ben_m))} XP!")
        msgs.extend(level_up_msgs)
        if grunt_pair:
            msgs.extend(self._tag_dialogue('Grunt', ["Always interrupting our plans.. just wait you'll see whats coming soon"]))
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
        p2 = self._double_battle_p2()
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
        p2 = self._double_battle_p2()
        ui = self.encounter_ui
        ui.in_fight_menu   = False
        ui.in_target_menu  = False
        ui.selected_option = 0
        ui.move_selected   = 0
        if not p2 or p2.get('hp', 0) <= 0:
            self.double_p2_queued = None
            self._execute_double_turn()
            return
        if self._abby_is_ally():
            # A seasoned trainer in her own right — Abby picks her own move
            # and target instead of waiting on the player.
            e1 = self.enemy_dino
            e2 = self.enemy_dino2
            alive_targets = [is_e2 for is_e2, alive in (
                (False, bool(e1 and e1.get('hp', 0) > 0)),
                (True,  bool(e2 and e2.get('hp', 0) > 0)),
            ) if alive]
            moveset = p2.get('moveset', [])
            if alive_targets and moveset:
                move_name = random.choice(moveset)['name']
                self.double_p2_queued = {'move_name': move_name, 'target_is_e2': random.choice(alive_targets)}
            else:
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
        p2 = self._double_battle_p2()
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
        p2 = self._double_battle_p2()
        e1 = self.enemy_dino
        e2 = self.enemy_dino2

        # Rotating boss battle (Vanessa): refill any fainted enemy slot from
        # her remaining roster before deciding the fight is actually over.
        if self.is_vanessa_battle and self.vanessa_dino_queue:
            refill_msgs = []
            if e1 and e1.get('hp', 0) <= 0:
                name, level = self.vanessa_dino_queue.pop(0)
                self.enemy_dino = e1 = self.create_dino(name, level)
                self.encounter.set_dino(1, name)
                refill_msgs.append(f"{self._trainer_name} sent out {name}!")
            if e2 and e2.get('hp', 0) <= 0 and self.vanessa_dino_queue:
                name, level = self.vanessa_dino_queue.pop(0)
                self.enemy_dino2 = e2 = self.create_dino(name, level)
                self.encounter.set_dino(2, name)
                refill_msgs.append(f"{self._trainer_name} sent out {name}!")
            if refill_msgs:
                self.message_box.queue_messages(
                    refill_msgs, wait_for_input=True,
                    on_complete=self._double_turn_end_after_abby_swap)
                return

        if (not e1 or e1.get('hp', 0) <= 0) and (not e2 or e2.get('hp', 0) <= 0):
            if self.is_vanessa_battle:
                self._finish_vanessa_battle(won=True)
            else:
                self._finish_double_battle()
            return

        if all(d.get('hp', 0) <= 0 for d in self.player_dinos):
            if self.is_vanessa_battle:
                self._finish_vanessa_battle(won=False)
            else:
                self.message_box.queue_messages(
                    ["You blacked out!", "Be careful next time..."],
                    wait_for_input=True, on_complete=self.trigger_blackout)
            return

        # Abby swaps in her own bench dino automatically — it's her roster
        # to manage, not the player's, so no "choose a replacement" prompt.
        if self._abby_is_ally() and p2 and p2.get('hp', 0) <= 0:
            if len(self.abby_dinos) > 1 and self.abby_dinos[1].get('hp', 0) > 0:
                fainted_name = self.abby_dinos[0]['name']
                self.abby_dinos[0], self.abby_dinos[1] = self.abby_dinos[1], self.abby_dinos[0]
                new_name = self.abby_dinos[0]['name']
                self.message_box.queue_messages(
                    [f"{fainted_name} fainted!", f"Abby sent out {new_name}!"],
                    wait_for_input=True,
                    on_complete=self._double_turn_end_after_abby_swap)
                return

        self._double_turn_end_after_abby_swap()

    def _double_turn_end_after_abby_swap(self):
        p1 = self.player_dinos[0] if self.player_dinos else None
        p2 = self._double_battle_p2()

        # Build replacement queue for fainted active slots (player's own
        # roster only — Abby's fainted dino, if any, was just handled above).
        fainted_slots = []
        if p1 and p1.get('hp', 0) <= 0:
            fainted_slots.append(0)
        if not self._abby_is_ally() and p2 and p2.get('hp', 0) <= 0:
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
            'entrance_id': entrance_id,
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
        banner_name = ENTRANCE_BANNER_NAMES.get(entrance_id)
        if banner_name:
            self.route_banner.show(banner_name)

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
        self._maybe_add_gym2_blocker()
        self._maybe_add_route2_blocker()
        self._maybe_add_skyy()
        self._maybe_add_gray_rival()
        self._maybe_add_grunts_vanessa()
        # Place player one tile behind where they entered, facing back out
        reverse = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        step = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
        dx, dy = step[reverse[prev['entrance_facing']]]
        self._place_player(prev['entrance_tile_x'] + dx, prev['entrance_tile_y'] + dy)
        banner_name = EXIT_BANNER_NAMES.get(prev.get('entrance_id'))
        if banner_name:
            self.route_banner.show(banner_name)

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
        self._maybe_add_gym2_blocker()
        self._maybe_add_route2_blocker()
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

    def _start_grunts_walk_away(self, npc1, npc2):
        npc1.facing = npc2.facing = 'right'
        self.cutscene = {
            'phase': 'grunts_walking',
            'npc': npc1,
            'npc2': npc2,
            'walk_target': (npc1.tile_x + 7, npc1.tile_y),
            'walk_target2': (npc2.tile_x + 7, npc2.tile_y),
        }

    def _update_grunts_walking(self, dt):
        c = self.cutscene
        npc1, npc2 = c['npc'], c['npc2']
        all_done = True
        for npc, target in ((npc1, c['walk_target']), (npc2, c['walk_target2'])):
            if npc.is_moving:
                npc.anim_timer += dt
                if npc.anim_timer >= npc.anim_speed:
                    npc.anim_timer = 0.0
                    npc.anim_frame = (npc.anim_frame + 1) % 4
                npc._slide(dt)
                all_done = False
                continue
            if (npc.tile_x, npc.tile_y) == target:
                continue
            all_done = False
            nx, ny = npc.tile_x + 1, npc.tile_y
            self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
            npc.tile_x, npc.tile_y = nx, ny
            self.solid_tile_coords.add((nx, ny))
            npc.facing = 'right'
            npc.target_x = float(nx * config.TILE_SIZE)
            npc.target_y = float(ny * config.TILE_SIZE)
            npc.is_moving = True
            npc.anim_frame = 1
            npc.anim_timer = 0.0

        if all_done:
            is_grunt_pair = {npc1.trainer_id, npc2.trainer_id} == {'grunt1', 'grunt2'}
            for npc in (npc1, npc2):
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                if npc in self.npcs:
                    self.npcs.remove(npc)
            self.cutscene = None
            if is_grunt_pair and not self.story_flags.get('vanessa_shadow_event_done'):
                self._start_vanessa_heal_sequence()

    # ── Gym 2 corn maze reveal ──────────────────────────────────────────
    GOURDECRUX_SCARECROW_TILE = (145, -53)  # matches WORLD_NPCS 'scarecrux' spawn
    CREUW_DANCE_TILES = [(144, -53), (146, -53), (145, -54)]

    def _check_gym2_corn_maze_reveal(self):
        if self.story_flags.get('gym2_corn_maze_reveal_done') or self.cutscene:
            return
        if not self.story_flags.get('gym1_leader_defeated'):
            return
        if self.fading or self.message_box.visible:
            return
        tx = self.player.rect.x // config.TILE_SIZE
        ty = self.player.rect.y // config.TILE_SIZE
        if self.get_player_zone(tx, ty) != 'corn_maze':
            return
        if tx < 136:
            return
        self._start_gym2_corn_maze_cutscene()

    def _start_gym2_corn_maze_cutscene(self):
        self.player.moving = False
        self.player.current_move_speed = self.player.move_speed  # force normal (non-sprint) pace
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y

        # Spawn everyone up front so the whole scene is already there to see
        # while the player walks up to it, instead of popping in mid-dialogue.
        log    = NPC('log',    tile_x=142, tile_y=-53, facing='down', sight_range=0, npc_type='story')
        curfeu = NPC('curfeu', tile_x=145, tile_y=-52, facing='left', sight_range=0, npc_type='story')
        self.npcs.append(log)
        self.npcs.append(curfeu)
        self.solid_tile_coords.add((log.tile_x, log.tile_y))
        self.solid_tile_coords.add((curfeu.tile_x, curfeu.tile_y))
        creuw_img = pygame.transform.scale(self.player_dino_front_images['Creuw'], (26, 26))
        creuws = [{'tile': t, 'img': creuw_img} for t in self.CREUW_DANCE_TILES]

        self.cutscene = {'phase': 'gym2_pre_walk_wait', 'log': log, 'curfeu': curfeu, 'creuws': creuws}
        self.message_box.queue_messages(
            self._tag_dialogue('Log', ["Jet come check this out"]),
            wait_for_input=True,
            on_complete=self._gym2_start_forced_walk
        )

    def _gym2_start_forced_walk(self):
        if not self.cutscene:
            return
        self.cutscene['phase'] = 'gym2_walk_to_scene'
        self.cutscene['walk_target'] = (142, -52)

    def _update_gym2_walk_to_scene(self, dt):
        p  = self.player
        ts = config.TILE_SIZE
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
                p.moving = False
                p.anim_index = 0
                p.image = p.animations[p.direction][0]
            return

        tx, ty = self.cutscene['walk_target']
        px, py = p.rect.x // ts, p.rect.y // ts
        if (px, py) == (tx, ty):
            self._gym2_log_dialogue()
            return
        dx, dy = tx - px, ty - py
        if abs(dx) >= abs(dy) and dx != 0:
            sx, sy = (1 if dx > 0 else -1), 0
        elif dy != 0:
            sx, sy = 0, (1 if dy > 0 else -1)
        else:
            return
        d = {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'down', (0, -1): 'up'}[(sx, sy)]
        p.facing = p.direction = d
        p.target_x = float((px + sx) * ts)
        p.target_y = float((py + sy) * ts)
        p.pos_x = float(p.rect.x)
        p.pos_y = float(p.rect.y)
        p.moving = True

    def _gym2_log_dialogue(self):
        self.cutscene['phase'] = 'gym2_dialogue_wait'
        self.message_box.queue_messages(
            self._split_dialogue(
                "Look at how the Creuws dance around the scarecrow."
                "Folklore says in the past a ghostly scarecrow would haunt the corn fields and scare all the Creuws away,"
                "until a brave Luna took the liberty to fly above ensuring the scarecrow would hide away in slumber for eternity."
                ,
                name='Log'
            ),
            wait_for_input=True,
            on_complete=self._gym2_start_curfeu_approach
        )

    def _gym2_start_curfeu_approach(self):
        if not self.cutscene:
            return
        c = self.cutscene
        p = self.player
        px, py = p.rect.x // config.TILE_SIZE, p.rect.y // config.TILE_SIZE
        c['walk_target'] = (px, py + 1)
        c['phase'] = 'gym2_curfeu_approaching'

    def _update_gym2_curfeu_approaching(self, dt):
        c = self.cutscene
        curfeu = c['curfeu']
        if curfeu.is_moving:
            curfeu.anim_timer += dt
            if curfeu.anim_timer >= curfeu.anim_speed:
                curfeu.anim_timer = 0.0
                curfeu.anim_frame = (curfeu.anim_frame + 1) % 4
            curfeu._slide(dt)
            return
        tx, ty = c['walk_target']
        if (curfeu.tile_x, curfeu.tile_y) == (tx, ty):
            curfeu.facing = 'up'
            self._face_player('down')
            c['phase'] = 'gym2_dialogue_wait'
            self._gym2_curfeu_dialogue()
            return
        self._step_npc_toward_tile(curfeu, tx, ty)

    def _gym2_curfeu_dialogue(self):
        if not self.cutscene:
            return
        self.message_box.queue_messages(
            self._split_dialogue(
                "Legend says one of the scarecrows had a transformation and became a protector of my families mansion beyond the corn field for years."
                "It was a daunting yet innocent spirit devoted to protecting the gates of our land."
                " Its tomb is just north of here.",
                name='Curfeu'
            ),
            wait_for_input=True,
            on_complete=self._gym2_start_creuw_dance
        )

    def _gym2_start_creuw_dance(self):
        if not self.cutscene:
            return
        self.cutscene['dance_elapsed'] = 0.0
        self.cutscene['phase'] = 'gym2_creuw_jumping'

    CREUW_JUMP_DURATION = 1.2   # ~2 hops
    CREUW_JUMP_HEIGHT   = 10

    def _update_gym2_creuw_jumping(self, dt):
        c = self.cutscene
        c['dance_elapsed'] += dt
        if c['dance_elapsed'] >= self.CREUW_JUMP_DURATION:
            self._gym2_start_scarecrux_glow()

    SCARECRUX_GLOW_DURATION = 1.0

    def _gym2_start_scarecrux_glow(self):
        c = self.cutscene
        c['glow_elapsed'] = 0.0
        c['phase'] = 'gym2_scarecrux_glow'

    def _update_gym2_scarecrux_glow(self, dt):
        c = self.cutscene
        c['glow_elapsed'] += dt
        if c['glow_elapsed'] >= self.SCARECRUX_GLOW_DURATION:
            self._gym2_start_creuws_run_off()

    CREUW_RUNOFF_DURATION = 0.8

    CREUW_RUNOFF_TILES = 7  # north, deeper into the corn field

    def _gym2_start_creuws_run_off(self):
        c = self.cutscene
        ts = config.TILE_SIZE
        self._face_player('right')
        for creuw in c['creuws']:
            tx, ty = creuw['tile']
            creuw['start'] = (tx * ts, ty * ts)
            creuw['end']   = (tx * ts, (ty - self.CREUW_RUNOFF_TILES) * ts)
        c['runoff_elapsed'] = 0.0
        c['phase'] = 'gym2_creuws_running_off'

    def _update_gym2_creuws_running_off(self, dt):
        c = self.cutscene
        c['runoff_elapsed'] += dt
        if c['runoff_elapsed'] >= self.CREUW_RUNOFF_DURATION:
            c['creuws'] = []
            self._gym2_vigilant_dialogue()

    def _gym2_vigilant_dialogue(self):
        if not self.cutscene:
            return
        self._face_player('up')
        self.cutscene['phase'] = 'gym2_dialogue_wait'
        self.message_box.queue_messages(
            self._split_dialogue(
                "Some of that energy is still around it seems, I would be vigilant around"
                " here at night ok Jet? I hope to see you at my gym soon, would love a good"
                " challenge",
                name='Log'
            ),
            wait_for_input=True,
            on_complete=self._gym2_start_walk_away
        )

    LOG_CURFEU_WALK_AWAY_TILES = 14

    def _gym2_start_walk_away(self):
        if not self.cutscene:
            return
        c = self.cutscene
        log, curfeu = c['log'], c['curfeu']
        log.facing = curfeu.facing = 'left'
        d = self.LOG_CURFEU_WALK_AWAY_TILES
        c['walk_target']  = (log.tile_x - d, log.tile_y)
        c['walk_target2'] = (curfeu.tile_x - d, curfeu.tile_y)
        c['phase'] = 'gym2_walking_away'

    def _update_gym2_walking_away(self, dt):
        c = self.cutscene
        log, curfeu = c['log'], c['curfeu']
        all_done = True
        for npc, target in ((log, c['walk_target']), (curfeu, c['walk_target2'])):
            if npc.is_moving:
                npc.anim_timer += dt
                if npc.anim_timer >= npc.anim_speed:
                    npc.anim_timer = 0.0
                    npc.anim_frame = (npc.anim_frame + 1) % 4
                npc._slide(dt)
                all_done = False
                continue
            if (npc.tile_x, npc.tile_y) == target:
                continue
            all_done = False
            nx, ny = npc.tile_x - 1, npc.tile_y
            self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
            npc.tile_x, npc.tile_y = nx, ny
            self.solid_tile_coords.add((nx, ny))
            npc.facing = 'left'
            npc.target_x = float(nx * config.TILE_SIZE)
            npc.target_y = float(ny * config.TILE_SIZE)
            npc.is_moving = True
            npc.anim_frame = 1
            npc.anim_timer = 0.0

        if all_done:
            for npc in (log, curfeu):
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                if npc in self.npcs:
                    self.npcs.remove(npc)
            self.story_flags['gym2_corn_maze_reveal_done'] = True
            self.cutscene = None

    # ── Route 2.6 Abby escort ────────────────────────────────────────────
    # NOTE: the force-step movement (like Skyy's cutscene) guarantees this
    # always completes regardless of scenery, since a solid-respecting walk
    # can dead-end with no path-around and soft-lock the cutscene.
    ABBY_ESCORT_TRIGGER_X = 88
    ABBY_SPAWN_TILE = (81, -53)
    ABBY_ESCORT_WAYPOINTS = [(83, -53), (83, -32), (71, -32), (71, -25), (65, -25)]
    ROUTE26_BOUNDARY_Y = -28

    def _check_route26_abby_reveal(self):
        if self.story_flags.get('route26_abby_started') or self.cutscene:
            return
        if not self.story_flags.get('gym2_corn_maze_reveal_done'):
            return
        if self.fading or self.message_box.visible:
            return
        tx = self.player.rect.x // config.TILE_SIZE
        ty = self.player.rect.y // config.TILE_SIZE
        if not (75 <= tx < 95 and -58 <= ty < -43):  # ROUTE2.6.tmx bounds
            return
        if tx != self.ABBY_ESCORT_TRIGGER_X:
            return
        self.story_flags['route26_abby_started'] = True
        self._start_route26_abby_cutscene()

    def _start_route26_abby_cutscene(self):
        self.player.moving = False
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y
        sx, sy = self.ABBY_SPAWN_TILE
        abby = NPC('abby', tile_x=sx, tile_y=sy, facing='down', sight_range=0, npc_type='story')
        self.npcs.append(abby)
        self.solid_tile_coords.add((sx, sy))
        self.cutscene = {'phase': 'abby_approaching', 'npc': abby}

    def _update_abby_approaching(self, dt):
        c = self.cutscene
        abby = c['npc']
        if abby.is_moving:
            abby.anim_timer += dt
            if abby.anim_timer >= abby.anim_speed:
                abby.anim_timer = 0.0
                abby.anim_frame = (abby.anim_frame + 1) % 4
            abby._slide(dt)
            return
        if abby._pixel_close(self.player):
            abby.anim_frame = 0
            abby.face_toward_player(self.player)
            dx = abby.tile_x - self.player.rect.x // config.TILE_SIZE
            dy = abby.tile_y - self.player.rect.y // config.TILE_SIZE
            if abs(dx) >= abs(dy):
                self._face_player('right' if dx > 0 else 'left')
            else:
                self._face_player('down' if dy > 0 else 'up')
            c['phase'] = 'abby_dialogue_wait'
            self.message_box.queue_messages(
                self._tag_dialogue('Abby', [
                    "Long time no see Jet!",
                    "So the professor has you on a journey too?",
                    "That is great! I have my own mission, can you help me?",
                    "Professor Amber said some suspicious activity is occurring by the solar panels powering Sierra Town",
                    "She wants us to go stop the intruders from damaging the solar panels!",
                    "Follow me!",
                ]),
                wait_for_input=True,
                on_complete=self._start_route26_guided_walk
            )
        else:
            # Force-step ignoring solids (same reasoning as Skyy's cutscene
            # and the guided walk below): route2.6 has scattered tree/rock
            # obstacles, and a solid-respecting approach can dead-end with
            # no path-around, soft-locking the cutscene.
            px = self.player.rect.x // config.TILE_SIZE
            py = self.player.rect.y // config.TILE_SIZE
            dx, dy = px - abby.tile_x, py - abby.tile_y
            if abs(dx) >= abs(dy) and dx != 0:
                sx, sy = (1 if dx > 0 else -1), 0
            elif dy != 0:
                sx, sy = 0, (1 if dy > 0 else -1)
            else:
                sx, sy = 0, 0
            if sx or sy:
                nx, ny = abby.tile_x + sx, abby.tile_y + sy
                self.solid_tile_coords.discard((abby.tile_x, abby.tile_y))
                abby.tile_x, abby.tile_y = nx, ny
                self.solid_tile_coords.add((nx, ny))
                abby.facing = abby._FACING[(sx, sy)]
                abby.target_x = float(nx * config.TILE_SIZE)
                abby.target_y = float(ny * config.TILE_SIZE)
                abby.is_moving = True
                abby.anim_frame = 1
                abby.anim_timer = 0.0

    def _start_route26_guided_walk(self):
        if not self.cutscene:
            return
        c = self.cutscene
        c['waypoints'] = list(self.ABBY_ESCORT_WAYPOINTS)
        c['phase'] = 'route26_guided_walk'
        # Turn to face the walking direction as its own beat, distinct from
        # the "facing the player" pose she was just in for the dialogue.
        abby = c['npc']
        tx, ty = c['waypoints'][0]
        dx, dy = tx - abby.tile_x, ty - abby.tile_y
        if dx or dy:
            if abs(dx) >= abs(dy) and dx != 0:
                abby.facing = 'right' if dx > 0 else 'left'
            elif dy != 0:
                abby.facing = 'down' if dy > 0 else 'up'

    def _update_route26_guided_walk(self, dt):
        c = self.cutscene
        abby = c['npc']
        p = self.player
        ts = config.TILE_SIZE

        moving = False
        if abby.is_moving:
            abby.anim_timer += dt
            if abby.anim_timer >= abby.anim_speed:
                abby.anim_timer = 0.0
                abby.anim_frame = (abby.anim_frame + 1) % 4
            abby._slide(dt)
            moving = True
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
                p.moving = False
                p.anim_index = 0
                p.image = p.animations[p.direction][0]
            moving = True
        if moving:
            return

        if not c['waypoints']:
            self._finish_route26_guided_walk()
            return
        tx, ty = c['waypoints'][0]
        if (abby.tile_x, abby.tile_y) == (tx, ty):
            c['waypoints'].pop(0)
            return

        dx, dy = tx - abby.tile_x, ty - abby.tile_y
        if abs(dx) >= abs(dy) and dx != 0:
            sx, sy = (1 if dx > 0 else -1), 0
        elif dy != 0:
            sx, sy = 0, (1 if dy > 0 else -1)
        else:
            return
        prev_tile = (abby.tile_x, abby.tile_y)
        nx, ny = abby.tile_x + sx, abby.tile_y + sy
        d = {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'down', (0, -1): 'up'}[(sx, sy)]

        # Force-step ignoring solids, like Skyy's cutscene, so a long
        # multi-map guided walk can't get stuck on scenery.
        self.solid_tile_coords.discard((abby.tile_x, abby.tile_y))
        abby.tile_x, abby.tile_y = nx, ny
        self.solid_tile_coords.add((nx, ny))
        abby.facing = d
        abby.target_x = float(nx * ts)
        abby.target_y = float(ny * ts)
        abby.is_moving = True
        abby.anim_frame = 1
        abby.anim_timer = 0.0

        # Player follows directly behind, into the tile Abby just left.
        p.facing = p.direction = d
        p.target_x = float(prev_tile[0] * ts)
        p.target_y = float(prev_tile[1] * ts)
        p.pos_x = float(p.rect.x)
        p.pos_y = float(p.rect.y)
        p.moving = True

    def _finish_route26_guided_walk(self):
        c = self.cutscene
        abby = c['npc']
        abby.facing = 'down'
        c['phase'] = 'gym2_dialogue_wait'  # reuse the generic no-op dialogue-wait phase
        self.message_box.queue_messages(
            self._tag_dialogue('Abby', ["ok now it is your turn, lets go investigate the solar panels"]),
            wait_for_input=True,
            on_complete=self._end_route26_abby_cutscene
        )

    # The starter neither the player nor Gray ended up with — same
    # counter-type mapping as _maybe_add_gray_rival, applied once more.
    ABBY_STARTER_MAP = {
        'Volkit':   'Floravel',
        'Corlave':  'Volkit',
        'Floravel': 'Corlave',
    }

    def _end_route26_abby_cutscene(self):
        self.abby_follower = self.cutscene['npc']
        self.story_flags['route26_abby_escort_done'] = True
        self.cutscene = None

        starter_names = set(config.DINO_BALL_MAP.values())
        player_starter = next(
            (d['name'] for d in self.player_dinos + self.box_dinos
             if d['name'] in starter_names), None
        )
        abby_starter = self.ABBY_STARTER_MAP.get(player_starter, 'Corlave')
        self.abby_dinos = [
            self.create_dino(abby_starter, 15),
            self.create_dino('Auraliz', 15),
        ]

    def _update_abby_follow(self, dt):
        abby = self.abby_follower
        if not abby or self.cutscene:
            return
        ts = config.TILE_SIZE
        if abby.is_moving:
            abby.anim_timer += dt
            if abby.anim_timer >= abby.anim_speed:
                abby.anim_timer = 0.0
                abby.anim_frame = (abby.anim_frame + 1) % 4
            abby._slide(dt)
            return
        p = self.player
        px, py = p.rect.x // ts, p.rect.y // ts
        behind = {'up': (0, 1), 'down': (0, -1), 'left': (1, 0), 'right': (-1, 0)}[p.facing]
        tx, ty = px + behind[0], py + behind[1]
        if (abby.tile_x, abby.tile_y) == (tx, ty):
            return
        if abs(abby.tile_x - px) + abs(abby.tile_y - py) <= 1:
            return
        self._step_npc_toward_tile(abby, tx, ty)

    def _check_route26_boundary(self):
        if not self.story_flags.get('route26_abby_escort_done'):
            return
        # Deactivated once the investigation is over — whether reached
        # normally or jumped to via the sandbox quest-skip menu, both set
        # the same flag.
        if self.story_flags.get('vanessa_shadow_event_done'):
            return
        if self.cutscene or self.fading or self.message_box.visible:
            return
        p = self.player
        ty = p.rect.y // config.TILE_SIZE
        if ty >= self.ROUTE26_BOUNDARY_Y:
            return
        ny = ty + 1
        p.rect.y = ny * config.TILE_SIZE
        p.pos_y = float(p.rect.y)
        p.target_y = p.pos_y
        p.target_x = float(p.rect.x)
        p.moving = False
        self.message_box.queue_messages(
            self._tag_dialogue('Abby', ["We can't leave now, we have a mission to complete!"]),
            wait_for_input=True)

    # ── Vanessa, Shadow Team Leader ──────────────────────────────────────
    def _start_vanessa_heal_sequence(self):
        self.cutscene = {'phase': 'vanessa_pre_wait'}
        self.message_box.queue_messages(
            self._tag_dialogue('Abby', ["Let me heal your dinos"]),
            wait_for_input=True,
            on_complete=self._start_vanessa_heal_flash
        )

    def _start_vanessa_heal_flash(self):
        for dino in self.player_dinos:
            dino['hp'] = dino['max_hp']
        self.cutscene_flash = {'alpha': 0, 'rising': True, 'count': 0, 'color': (255, 255, 255)}
        self.cutscene = {'phase': 'vanessa_heal_flash'}

    def _start_vanessa_approach(self):
        vanessa = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'vanessa'), None)
        if not vanessa:
            self.cutscene = None
            return
        self.cutscene = {'phase': 'vanessa_approaching', 'npc': vanessa}

    def _update_vanessa_approaching(self, dt):
        c = self.cutscene
        vanessa = c['npc']
        if vanessa.is_moving:
            vanessa.anim_timer += dt
            if vanessa.anim_timer >= vanessa.anim_speed:
                vanessa.anim_timer = 0.0
                vanessa.anim_frame = (vanessa.anim_frame + 1) % 4
            vanessa._slide(dt)
            return
        if vanessa._pixel_close(self.player):
            vanessa.anim_frame = 0
            vanessa.face_toward_player(self.player)
            dx = vanessa.tile_x - self.player.rect.x // config.TILE_SIZE
            dy = vanessa.tile_y - self.player.rect.y // config.TILE_SIZE
            if abs(dx) >= abs(dy):
                self._face_player('right' if dx > 0 else 'left')
            else:
                self._face_player('down' if dy > 0 else 'up')
            c['phase'] = 'vanessa_dialogue_wait'
            self.message_box.queue_messages(
                self._tag_dialogue('Vanessa', [
                    "You fools, in time you will understand the harm you are causing",
                    "These solar panels giving power to our region are the true danger",
                    "Just look at the trees surrounding them...",
                    "and what happened to prickly's evolution, its so sad to see",
                    "But oh well, we won't need to be on the ground disrupting the power for long",
                    "Ill go easy on you this first time",
                ]),
                wait_for_input=True,
                on_complete=self._start_vanessa_battle
            )
        else:
            # Force-step ignoring solids (same reasoning as Abby's approach)
            # so she's guaranteed to reach the player regardless of scenery.
            px = self.player.rect.x // config.TILE_SIZE
            py = self.player.rect.y // config.TILE_SIZE
            dx, dy = px - vanessa.tile_x, py - vanessa.tile_y
            if abs(dx) >= abs(dy) and dx != 0:
                sx, sy = (1 if dx > 0 else -1), 0
            elif dy != 0:
                sx, sy = 0, (1 if dy > 0 else -1)
            else:
                sx, sy = 0, 0
            if sx or sy:
                nx, ny = vanessa.tile_x + sx, vanessa.tile_y + sy
                self.solid_tile_coords.discard((vanessa.tile_x, vanessa.tile_y))
                vanessa.tile_x, vanessa.tile_y = nx, ny
                self.solid_tile_coords.add((nx, ny))
                vanessa.facing = vanessa._FACING[(sx, sy)]
                vanessa.target_x = float(nx * config.TILE_SIZE)
                vanessa.target_y = float(ny * config.TILE_SIZE)
                vanessa.is_moving = True
                vanessa.anim_frame = 1
                vanessa.anim_timer = 0.0

    def _start_vanessa_battle(self):
        vanessa = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'vanessa'), None)
        if not vanessa:
            self.cutscene = None
            return
        self.cutscene = None
        self.player.moving = False
        self.player.target_x = self.player.rect.x
        self.player.target_y = self.player.rect.y
        self.player.pos_x = float(self.player.rect.x)
        self.player.pos_y = float(self.player.rect.y)
        self.active_dino_index = 0
        self.fading = True
        self.fade_alpha = 0
        self.is_trainer_battle = True
        self.is_double_battle  = True
        self.is_vanessa_battle = True
        self.current_trainer_npc  = vanessa
        self.current_trainer_npc2 = vanessa

        dinos = TRAINER_DATA.get('vanessa', {}).get('dinos', {})
        keys = sorted(dinos.keys())
        n1, l1 = dinos[keys[0]]
        n2, l2 = dinos[keys[1]]
        self.vanessa_dino_queue = [dinos[k] for k in keys[2:]]

        self.enemy_dino  = self.create_dino(n1, l1)
        self.enemy_dino2 = self.create_dino(n2, l2)

        self.trainer_dino_queue     = []
        self.trainer_dinos_total    = len(dinos)
        self.trainer_dinos_defeated = 0
        self.field_effects               = []
        self.defend_uses_remaining       = 3
        self.enemy_defend_uses_remaining = 3

        self.encounter_ui   = DoubleBattleUI(self.fonts)
        self.encounter_text = f"Vanessa sent out {n1} and {n2}!"
        self.encounter      = DoubleBattleEncounter(self.fonts, n1, n2)

        now    = pygame.time.get_ticks()
        frames = self.dino_frames.get(n1, [self.enemy_dino['image']])
        self.encounter_anim = {
            "frames": frames, "frame_idx": 0,
            "last_switch": now, "interval": 250,
            "start_time": now, "duration": 1000,
        }

    def _finish_vanessa_battle(self, won):
        """Clean up and return to the overworld first, then have Vanessa
        deliver her win/lose line standing on the map (not the battle
        screen) before she walks off."""
        vanessa = self.current_trainer_npc
        self.is_trainer_battle  = False
        self.is_double_battle   = False
        self.is_vanessa_battle  = False
        self.enemy_dino2        = None
        self.vanessa_dino_queue = []
        for d in self.player_dinos:
            d['stat_stages'] = {"attack": 0, "defense": 0, "speed": 0}
            d['defending']   = False
        self.pop_to_world()

        if won:
            msg = self._tag_dialogue('Vanessa', ["Next time I won't be as easy on you..."])
        else:
            msg = self._tag_dialogue('Vanessa', ["What a shame, I expected more from you two"])
        self.message_box.queue_messages(
            msg, wait_for_input=True,
            on_complete=lambda: self._start_vanessa_walk_away(vanessa))

    def _start_vanessa_walk_away(self, vanessa):
        # Instant snap, not the async-slide _push_player_back_from — since
        # self.cutscene gets set right after, player.update() would freeze
        # before an async slide ever got a chance to finish.
        ts = config.TILE_SIZE
        px = self.player.rect.x // ts
        py = self.player.rect.y // ts
        all_solid = self.solid_tile_coords | self.solid_tiles
        npx, npy = px, py + 1
        if (npx, npy) not in all_solid:
            self.player.rect.y   = npy * ts
            self.player.pos_y    = float(self.player.rect.y)
            self.player.target_y = self.player.pos_y
            self.player.target_x = float(self.player.rect.x)
            self.player.moving   = False
        vanessa.facing = 'right'
        self.cutscene = {
            'phase': 'vanessa_walking_away',
            'npc': vanessa,
            'walk_target': (vanessa.tile_x + 8, vanessa.tile_y),
        }

    def _update_vanessa_walking_away(self, dt):
        c = self.cutscene
        npc = c['npc']
        if npc.is_moving:
            npc.anim_timer += dt
            if npc.anim_timer >= npc.anim_speed:
                npc.anim_timer = 0.0
                npc.anim_frame = (npc.anim_frame + 1) % 4
            npc._slide(dt)
            return
        tx, ty = c['walk_target']
        if (npc.tile_x, npc.tile_y) == (tx, ty):
            self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
            if npc in self.npcs:
                self.npcs.remove(npc)
            self.cutscene = None
            self._start_post_vanessa_abby_sequence()
            return
        nx, ny = npc.tile_x + 1, npc.tile_y
        self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
        npc.tile_x, npc.tile_y = nx, ny
        self.solid_tile_coords.add((nx, ny))
        npc.facing = 'right'
        npc.target_x = float(nx * config.TILE_SIZE)
        npc.target_y = float(ny * config.TILE_SIZE)
        npc.is_moving = True
        npc.anim_frame = 1
        npc.anim_timer = 0.0

    def _start_post_vanessa_abby_sequence(self):
        for dino in self.player_dinos:
            dino['hp'] = dino['max_hp']
        self.cutscene = {'phase': 'vanessa_pre_wait'}
        self.message_box.queue_messages(
            self._tag_dialogue('Abby', [
                "Im sure we will see more of them soon",
                "I am going to go report back to Professor",
                "Be safe out here I think its getting dark out",
            ]),
            wait_for_input=True,
            on_complete=self._start_abby_departure_walk
        )

    def _start_abby_departure_walk(self):
        abby = self.abby_follower
        if not abby:
            self._finish_vanessa_event()
            return
        self.abby_follower = None
        abby.facing = 'right'
        self.cutscene = {
            'phase': 'abby_departing',
            'npc': abby,
            'walk_target': (abby.tile_x + 8, abby.tile_y),
        }

    def _update_abby_departing(self, dt):
        c = self.cutscene
        npc = c['npc']
        if npc.is_moving:
            npc.anim_timer += dt
            if npc.anim_timer >= npc.anim_speed:
                npc.anim_timer = 0.0
                npc.anim_frame = (npc.anim_frame + 1) % 4
            npc._slide(dt)
            return
        tx, ty = c['walk_target']
        if (npc.tile_x, npc.tile_y) == (tx, ty):
            self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
            if npc in self.npcs:
                self.npcs.remove(npc)
            self.cutscene = None
            self._finish_vanessa_event()
            return
        nx, ny = npc.tile_x + 1, npc.tile_y
        self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
        npc.tile_x, npc.tile_y = nx, ny
        self.solid_tile_coords.add((nx, ny))
        npc.facing = 'right'
        npc.target_x = float(nx * config.TILE_SIZE)
        npc.target_y = float(ny * config.TILE_SIZE)
        npc.is_moving = True
        npc.anim_frame = 1
        npc.anim_timer = 0.0

    def _finish_vanessa_event(self):
        self.is_night = True
        self.day_night_timer = 0.0
        self.dn_transitioning = False
        self.story_flags['vanessa_shadow_event_done'] = True

    def _draw_gym2_cutscene_fx(self, surface):
        c = self.cutscene
        if not c:
            return
        ts = config.TILE_SIZE
        phase = c.get('phase')

        if phase == 'gym2_creuws_running_off':
            t = min(1.0, c['runoff_elapsed'] / self.CREUW_RUNOFF_DURATION)
            for creuw in c.get('creuws', []):
                sx, sy = creuw['start']
                ex, ey = creuw['end']
                x = sx + (ex - sx) * t
                y = sy + (ey - sy) * t
                img = creuw['img']
                surface.blit(img, (int(x - self.camera_x) - img.get_width() // 2,
                                    int(y - self.camera_y) - img.get_height() // 2))
        else:
            # Creuws stand idle around the scarecrow from the moment the
            # scene loads, and only actually bounce during the dance phase.
            bounce_t = c.get('dance_elapsed') if phase == 'gym2_creuw_jumping' else None
            for creuw in c.get('creuws', []):
                tx, ty = creuw['tile']
                cx = tx * ts + ts // 2 - self.camera_x
                cy = ty * ts + ts // 2 - self.camera_y
                bounce = 0
                if bounce_t is not None:
                    bounce = abs(math.sin(bounce_t * (2 * math.pi / (self.CREUW_JUMP_DURATION / 2)))) * self.CREUW_JUMP_HEIGHT
                img = creuw['img']
                surface.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2 - bounce))

        if phase == 'gym2_scarecrux_glow':
            gx, gy = self.GOURDECRUX_SCARECROW_TILE
            progress = c['glow_elapsed'] / self.SCARECRUX_GLOW_DURATION
            alpha = int(220 * math.sin(min(1.0, progress) * math.pi))
            if alpha > 0:
                radius = 20 + int(10 * math.sin(min(1.0, progress) * math.pi))
                glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 248, 200, alpha), (radius, radius), radius)
                cx = gx * ts + ts // 2 - self.camera_x
                cy = gy * ts + ts // 2 - self.camera_y
                surface.blit(glow, (cx - radius, cy - radius))

    def _update_cutscene(self, dt):
        c = self.cutscene
        if c['phase'] == 'grunts_walking':
            self._update_grunts_walking(dt)
            return
        if c['phase'] == 'gym2_walk_to_scene':
            self._update_gym2_walk_to_scene(dt)
            return
        if c['phase'] == 'gym2_curfeu_approaching':
            self._update_gym2_curfeu_approaching(dt)
            return
        if c['phase'] == 'gym2_creuw_jumping':
            self._update_gym2_creuw_jumping(dt)
            return
        if c['phase'] == 'gym2_scarecrux_glow':
            self._update_gym2_scarecrux_glow(dt)
            return
        if c['phase'] == 'gym2_creuws_running_off':
            self._update_gym2_creuws_running_off(dt)
            return
        if c['phase'] == 'gym2_walking_away':
            self._update_gym2_walking_away(dt)
            return
        if c['phase'] == 'abby_approaching':
            self._update_abby_approaching(dt)
            return
        if c['phase'] == 'route26_guided_walk':
            self._update_route26_guided_walk(dt)
            return
        if c['phase'] == 'vanessa_heal_flash':
            if not self.cutscene_flash:
                self._start_vanessa_approach()
            return
        if c['phase'] == 'vanessa_approaching':
            self._update_vanessa_approaching(dt)
            return
        if c['phase'] == 'vanessa_walking_away':
            self._update_vanessa_walking_away(dt)
            return
        if c['phase'] == 'abby_departing':
            self._update_abby_departing(dt)
            return
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
                        name='Amber'
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
                npc.guard_id    = 'amber_intro'
                npc.unlock_flag = 'encounters_unlocked'
                npc.state       = 'idle'
                npc.facing      = 'left'
                npc.home_tile   = (tx, ty)
                npc.home_facing = 'left'
                npc.sight_range = 8
                npc.block_dialog = [
                    "[Amber] I need you to collect all 3 dinos before coming back to the lab!"
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

    # Splits after a comma or period (that's followed by whitespace), so a
    # clause boundary always lands on a natural pause in speech rather
    # than mid-word-flow. Used by _split_dialogue() below.
    _CLAUSE_SPLIT_RE = re.compile(r'(?<=[.,])\s+')

    def _split_dialogue(self, *texts, name=None):
        """Break one or more dialogue strings into one queued box per
        clause, splitting only at commas and periods.

        Each clause becomes its own entry for queue_messages() — its own
        box. A clause that's too long to fit the box's two lines isn't
        cut into a fresh box mid-sentence; DialogueBox wraps and
        paginates it internally and scrolls to finish it, since scrolling
        (not a new box) is how a single clause continues. A new box only
        ever starts at the next clause boundary (the next comma/period).

        Pass `name` to prefix every clause with a speaker tag (e.g.
        "[Log] ..."). Because DialogueBox does its own wrapping on
        whatever string it's given, the tag is simply part of that
        string — there's no separate pre-wrap pass here to fall out of
        sync with it (that mismatch was the old source of stray
        one-word pages)."""
        tag = f"[{name}] " if name else ""
        clauses = []
        for text in texts:
            clauses.extend(c.strip() for c in self._CLAUSE_SPLIT_RE.split(text) if c.strip())
        return [tag + c for c in clauses] if tag else clauses

    def _tag_dialogue(self, name, lines):
        """Prefix short, already-fits-in-one-page dialogue lines with a
        speaker tag, e.g. '[Log] Jet come check this out'. Do NOT use
        this on _split_dialogue() output — pass name=... to
        _split_dialogue() instead so the tag width is accounted for
        before wrapping (see its docstring)."""
        return [f"[{name}] {line}" for line in lines]

    def _face_player(self, direction):
        self.player.facing = self.player.direction = direction
        self.player.image = self.player.animations[direction][0]

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

    def _spawn_active_guard(self, guard_id, trainer_id, tx, ty, facing, sight_range,
                             block_dialog, unlock_flag, home_tile=None, home_facing=None):
        """Universal 'active approach' blocker — spots the player via line of
        sight, walks up, shows block_dialog, pushes them back a tile, then
        returns to its post. This is the exact mechanism Professor Amber's
        intro guard uses; reuse it for any future story gate instead of
        writing a new NPC state machine. Removed later via _check_guard_removal.
        """
        guard = NPC(trainer_id, tile_x=tx, tile_y=ty, facing=facing,
                    sight_range=sight_range, npc_type='guard')
        guard.state       = 'idle'
        guard.guard_id    = guard_id
        guard.unlock_flag = unlock_flag
        guard.home_tile   = home_tile or (tx, ty)
        guard.home_facing = home_facing or facing
        guard.block_dialog = block_dialog
        self.npcs.append(guard)
        self.solid_tile_coords.add((tx, ty))
        return guard

    def _check_guard_removal(self, guard_id):
        """Remove an active-guard NPC (see _spawn_active_guard) once its
        unlock_flag has been set True."""
        guard = next((n for n in self.npcs if getattr(n, 'guard_id', '') == guard_id), None)
        if guard and self.story_flags.get(guard.unlock_flag):
            self.solid_tile_coords.discard((guard.tile_x, guard.tile_y))
            self.npcs.remove(guard)

    def _add_amber_blocker_to_solid(self):
        blocker = next((n for n in self.npcs if getattr(n, 'guard_id', '') == 'amber_intro'), None)
        if blocker:
            self.solid_tile_coords.add((blocker.tile_x, blocker.tile_y))

    def _add_amber_blocker(self):
        """Re-add guard NPC when loading a save mid-intro."""
        tx, ty = 1, 27  # must match leave_tile in _start_amber_intro_cutscene
        self._spawn_active_guard(
            'amber_intro', 'amber', tx, ty, facing='left', sight_range=5,
            block_dialog=["[Amber] I need you to collect all 3 dinos before coming back to the lab!"],
            unlock_flag='encounters_unlocked',
        )

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

    def _push_player_back_from(self, npc, tiles=2, vector=(-1, 1)):
        """Shove the player back so a static blocker's dialogue doesn't
        immediately re-trigger on the next interact press. Defaults to a
        left+down diagonal shove; freezes player input briefly once it lands."""
        dx, dy = vector
        ts = config.TILE_SIZE
        all_solid = self.solid_tile_coords | self.solid_tiles
        px = self.player.rect.x // ts
        py = self.player.rect.y // ts
        nx, ny = px, py
        for _ in range(tiles):
            cand = (nx + dx, ny + dy)
            if cand in all_solid:
                break
            nx, ny = cand
        if (nx, ny) != (px, py):
            self.player.target_x = nx * ts
            self.player.target_y = ny * ts
            self.player.pos_x    = float(self.player.rect.x)
            self.player.pos_y    = float(self.player.rect.y)
            self.player.moving   = True
            self.player.forced_move = True

    def _maybe_add_gym2_blocker(self):
        if self.story_flags.get('vanessa_shadow_event_done'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        already = any(getattr(n, 'npc_type', '') == 'gym2_guard' for n in self.npcs)
        if already:
            return
        tx, ty = 64, -65
        blocker = NPC('blk_b', tile_x=tx, tile_y=ty, facing='down',
                      sight_range=0, npc_type='gym2_guard')
        blocker.state       = 'idle'
        blocker.home_tile   = (tx, ty)
        blocker.home_facing = 'down'
        blocker.block_dialog = [
            "The gym leader is not here right now.",
            "Check the corn maze, he always likes to explore around there.",
        ]
        self.npcs.append(blocker)
        self.solid_tile_coords.add((tx, ty))

    def _maybe_add_route2_blocker(self):
        if self.story_flags.get('gym1_leader_defeated'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        already = any(getattr(n, 'guard_id', '') == 'route2' for n in self.npcs)
        if already:
            return
        self._spawn_active_guard(
            'route2', 'blk_b', 33, -42, facing='down', sight_range=6,
            block_dialog=[
                "This road isn't safe to cross yet.",
                "Come back once you've earned the Sierra Badge at Gym 1.",
            ],
            unlock_flag='gym1_leader_defeated',
        )

    def _check_route2_blocker(self):
        self._check_guard_removal('route2')

    def _check_gym2_blocker_removal(self):
        if not self.story_flags.get('vanessa_shadow_event_done'):
            return
        blocker = next((n for n in self.npcs if getattr(n, 'npc_type', '') == 'gym2_guard'), None)
        if blocker:
            self.solid_tile_coords.discard((blocker.tile_x, blocker.tile_y))
            self.npcs.remove(blocker)

    def apply_quest_step(self, index):
        """Sandbox debug: jump story_flags (and related state) to QUEST_STEPS[index].

        Only touches trainer_ids/badges that QUEST_STEPS itself tracks (gray, skyy,
        sierra badge) — anything the player defeated/earned outside the scripted
        story (route 2 trainers, etc.) is left alone.
        """
        steps = _story.QUEST_STEPS
        tracked_trainers = {t for step in steps for t in step.get('defeated_trainers', [])}
        tracked_badges   = {b for step in steps for b in step.get('badges', [])}
        should_defeat = set()
        should_have_badge = set()
        for i, step in enumerate(steps):
            self.story_flags[step['flag']] = (i <= index)
            if i <= index:
                should_defeat.update(step.get('defeated_trainers', []))
                should_have_badge.update(step.get('badges', []))

        self.defeated_trainers -= (tracked_trainers - should_defeat)
        self.defeated_trainers |= should_defeat
        self.badges_earned = [b for b in self.badges_earned if b not in tracked_badges]
        for b in should_have_badge:
            if b not in self.badges_earned:
                self.badges_earned.append(b)
        for npc in self.npcs:
            if getattr(npc, 'trainer_id', None) in tracked_trainers:
                npc.defeated = npc.trainer_id in should_defeat

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
        ]), name=data.get('name', 'Gray'))
        def start_walk_away():
            npc.facing = 'down'
            self.cutscene = {
                'phase': 'gray_walking',
                'npc': npc,
                'walk_target': (npc.tile_x, npc.tile_y + 6),
            }
        self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=start_walk_away)

    def _maybe_add_grunts_vanessa(self):
        if not self.story_flags.get('gym2_corn_maze_reveal_done'):
            return
        if self.story_flags.get('vanessa_shadow_event_done'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        if self.cutscene or self.is_vanessa_battle:
            return
        present = {getattr(n, 'trainer_id', '') for n in self.npcs}
        for spec in config.WORLD_NPCS.get(self.current_world_file, []):
            trainer_id, tx, ty, facing, sight, npc_type = spec
            if trainer_id not in ('grunt1', 'grunt2', 'vanessa'):
                continue
            if trainer_id in present or trainer_id in self.defeated_trainers:
                continue
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty,
                      facing=facing, sight_range=sight, npc_type=npc_type)
            npc.home_tile   = (tx, ty)
            npc.home_facing = facing
            self.npcs.append(npc)
            self.solid_tile_coords.add((tx, ty))

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
            dialog = self._tag_dialogue(data.get('name', 'Skyy'), data.get('dialog', {}).get('defeated', ["..."]))
            self.message_box.queue_messages(dialog, wait_for_input=True)

        self.badge_earned_screen = BadgeEarnedScreen(
            self, "Sierra Badge",
            os.path.join('assets', 'Badges', 'flying_badge.png'),
            on_dismiss=_after_badge)

    def _on_log_gym_won(self):
        self.story_flags['gym2_leader_defeated'] = True
        if 'earth' not in self.badges_earned:
            self.badges_earned.append('earth')

        def _after_badge():
            data = TRAINER_DATA.get('log', {})
            dialog = self._tag_dialogue(data.get('name', 'Log'), data.get('dialog', {}).get('defeated', ["..."]))
            self.message_box.queue_messages(dialog, wait_for_input=True)

        self.badge_earned_screen = BadgeEarnedScreen(
            self, "Earth Badge",
            os.path.join('assets', 'Badges', 'earth_badge.png'),
            on_dismiss=_after_badge)
        self.push_state('badge_earned')

    def _check_amber_blocker(self):
        if self.story_flags.get('encounters_unlocked'):
            return
        if not self.story_flags.get('amber_intro_done'):
            return
        if len(self.player_dinos) >= 3:
            self.story_flags['encounters_unlocked'] = True
        self._check_guard_removal('amber_intro')

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

            if self.coord_input_active:
                self._handle_coord_input_event(event)
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

            elif self.state == 'quest_debug':
                result = self.quest_debug_screen.handle_event(event, self)
                if result == 'back':
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
            tile = (px + dx * d, py + dy * d)
            if tile in GOURDECRUX_TOMB_TILES:
                self._interact_gourdecrux_tomb()
                return True
            if tile in self.lore_tile_coords:
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

    def _interact_gourdecrux_tomb(self):
        self.message_box.queue_messages(
            ["The tomb of Gourdecrux, gatekeeper of the Mansion"],
            wait_for_input=True,
            on_complete=self._maybe_start_gourdecrux_transform)

    def _maybe_start_gourdecrux_transform(self):
        if not self.night_active:
            return
        target = next((d for d in self.player_dinos if d['name'] in ('Scarecrux', 'Gourdecrux')), None)
        if not target:
            return
        tx, ty = GOURDECRUX_TOMB_CENTER
        self._start_orb_fx(tx, ty, on_complete=lambda: self._finish_gourdecrux_transform(target))

    def _finish_gourdecrux_transform(self, dino):
        old_name = dino['name']
        new_name = 'Gourdecrux' if old_name == 'Scarecrux' else 'Scarecrux'
        self._apply_form_swap(dino, new_name)
        self.message_box.queue_messages(
            [f"... Your {old_name} has morphed into {new_name}"],
            wait_for_input=True)

    def _apply_form_swap(self, dino, new_name):
        """Fully re-derive type/stats/moves for a new species — unlike
        do_evolution (which preserves old moves alongside new ones, correct
        for a one-way evolution), a reversible form-switch should look like
        a fresh create_dino() for the new species at the same level/HP state,
        so nothing lingers from the old form after switching back and forth."""
        level = dino['level']
        hp_ratio = dino['hp'] / dino['max_hp'] if dino.get('max_hp', 0) > 0 else 1.0

        new_data = DINO_DATA[new_name]
        base_stats = new_data['stats']

        dino['name']  = new_name
        dino['type']  = base_stats['type']
        dino['stats'] = base_stats
        dino['image']       = self.player_dino_images[new_name]
        dino['front_image'] = self.player_dino_front_images[new_name]
        if new_name in self.dino_frames:
            dino['frames'] = self.dino_frames[new_name]

        dino['max_hp']  = HP_Base(base_stats['health'], level)
        dino['attack']  = Base_Stats(base_stats['attack'], level)
        dino['defense'] = Base_Stats(base_stats['defense'], level, p=0.9)
        dino['speed']   = Base_Stats(base_stats['speed'], level)
        dino['base_attack']  = dino['attack']
        dino['base_defense'] = dino['defense']
        dino['base_speed']   = dino['speed']
        dino['stat_stages']  = {"attack": 0, "defense": 0, "speed": 0}
        self.apply_nature_boost(dino)
        dino['hp'] = max(1, int(dino['max_hp'] * hp_ratio))

        learned_moves = [m for _, m in sorted(new_data['moves'].items()) if _ <= level]
        dino['moves']   = learned_moves
        dino['moveset'] = []
        for move_name in learned_moves[-4:]:
            m = MOVE_DATA.get(move_name, {})
            dino['moveset'].append({
                "name": move_name,
                "type": m.get("type", "normal"),
                "damage": m.get("damage", 0),
                "accuracy": m.get("accuracy", 100),
                "ability": m.get("ability", None),
            })

    # ── Gourdecrux tomb orb effect ───────────────────────────────────────
    ORB_FX_DURATION = 4.0

    def _start_orb_fx(self, world_tile_x, world_tile_y, on_complete):
        ts = config.TILE_SIZE
        cx = world_tile_x * ts + ts // 2
        cy = world_tile_y * ts + ts // 2
        orbs = []
        colors = [(15, 10, 20), (58, 22, 92), (35, 12, 55)]
        for _ in range(14):
            orbs.append({
                'angle':     random.uniform(0, 360),
                'radius':    random.uniform(16, 48),
                'ang_speed': random.uniform(90, 170) * random.choice((-1, 1)),
                'size':      random.randint(3, 7),
                'color':     random.choice(colors),
                'rise_speed': random.uniform(14, 30),
                'y_bob':     random.uniform(0, 6.28),
            })
        self.orb_fx = {
            'cx': cx, 'cy': cy,
            'elapsed': 0.0,
            'orbs': orbs,
            'on_complete': on_complete,
        }

    def _update_orb_fx(self, dt):
        fx = self.orb_fx
        fx['elapsed'] += dt
        for o in fx['orbs']:
            o['angle'] += o['ang_speed'] * dt
        if fx['elapsed'] >= self.ORB_FX_DURATION:
            cb = fx['on_complete']
            self.orb_fx = None
            if cb:
                cb()

    def _draw_orb_fx(self, surface):
        fx = self.orb_fx
        if not fx:
            return
        t = fx['elapsed']
        progress = min(1.0, t / self.ORB_FX_DURATION)
        for o in fx['orbs']:
            rad = math.radians(o['angle'])
            r = o['radius'] * (1.0 - 0.3 * progress)
            x = fx['cx'] + r * math.cos(rad)
            y = fx['cy'] + r * math.sin(rad) * 0.55 - t * o['rise_speed']
            alpha = max(0, int(230 * (1.0 - progress)))
            if alpha <= 0:
                continue
            size = o['size']
            dot = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(dot, (*o['color'], alpha), (size, size), size)
            surface.blit(dot, (int(x - self.camera_x) - size, int(y - self.camera_y) - size))

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
        cutscene_locking = bool(self.cutscene)
        if event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL) and self.sandbox:
            self.coord_input_active = True
            self.coord_input_text = ''
        elif event.key == pygame.K_z:
            tx = self.player.rect.x // config.TILE_SIZE
            ty = self.player.rect.y // config.TILE_SIZE
            in_enc = (tx, ty) in self.encounter_tile_coords
            zone = self.get_player_zone(tx, ty)
            print(f"[DEBUG] tile=({tx}, {ty})  encounter_tile={in_enc}  zone={zone}")
        elif event.key == pygame.K_i and not self.fading and self.entrance_fade_state is None and not trainer_approaching and not guard_active and not cutscene_locking:
            self.push_state('menu')
        elif (event.key == pygame.K_q and (event.mod & pygame.KMOD_CTRL) and self.sandbox
                and not self.fading and self.entrance_fade_state is None and not cutscene_locking):
            self.quest_debug_screen.reset()
            self.push_state('quest_debug')
        elif event.key == pygame.K_n and (event.mod & pygame.KMOD_CTRL) and self.sandbox:
            self.force_night = not self.night_active
            print(f"[DEBUG] force_night -> {self.force_night}")
        elif event.key == pygame.K_j and not self.orb_fx:
            if self.check_type_chart_interact():
                pass
            elif self.check_box_interact():
                pass
            elif self.check_lore_interact():
                pass
            elif not self.interact_with_npc():
                self.pickup_item()

    def _handle_coord_input_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.coord_input_active = False
            self.coord_input_text = ''
            return
        if event.key == pygame.K_RETURN:
            nums = re.findall(r'-?\d+', self.coord_input_text)
            if len(nums) >= 2:
                self._teleport_player_sandbox(int(nums[0]), int(nums[1]))
            self.coord_input_active = False
            self.coord_input_text = ''
            return
        if event.key == pygame.K_BACKSPACE:
            self.coord_input_text = self.coord_input_text[:-1]
            return
        ch = event.unicode
        if ch and ch in '0123456789-,. ' and len(self.coord_input_text) < 20:
            self.coord_input_text += ch

    def _teleport_player_sandbox(self, tx, ty):
        ts = config.TILE_SIZE
        px, py = tx * ts, ty * ts
        self.player.rect.topleft = (px, py)
        self.player.pos_x = float(px)
        self.player.pos_y = float(py)
        self.player.target_x = float(px)
        self.player.target_y = float(py)
        self.player.moving = False
        self.update_camera()

    def _spawn_world_npcs(self, world_file):
        self.npcs = []
        for spec in config.WORLD_NPCS.get(world_file, []):
            trainer_id, tx, ty, facing, sight, npc_type = spec
            if trainer_id == 'scarecrux' and self.story_flags.get('scarecrux_awakened'):
                continue
            if trainer_id in ('grunt1', 'grunt2', 'vanessa') and not self.story_flags.get('gym2_corn_maze_reveal_done'):
                continue
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty,
                      facing=facing, sight_range=sight, npc_type=npc_type)
            npc.home_tile   = (tx, ty)
            npc.home_facing = facing
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
            if npc.npc_type in ('guard', 'gym_guard', 'gym2_guard'):
                if npc.npc_type == 'gym_guard' and not self.story_flags.get('amber_lab_done'):
                    dialog = ["The gym leader is not here right now."]
                else:
                    dialog = getattr(npc, 'block_dialog', ["..."])
                if npc.npc_type == 'gym2_guard':
                    self.message_box.queue_messages(
                        dialog, wait_for_input=True,
                        on_complete=lambda n=npc: self._push_player_back_from(n))
                else:
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
            name = data.get('name', 'Trainer')
            if npc.defeated or npc.state == 'done':
                npc.defeated = True
                dialog = self._tag_dialogue(name, data.get('dialog', {}).get('defeated', ["..."]))
                self.message_box.queue_messages(dialog, wait_for_input=True)
                return True
            if npc.state == 'idle':
                dialog = self._tag_dialogue(name, data.get('dialog', {}).get('default', ["..."]))
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
                    self._tag_dialogue('Amber', ["Keep up the training! The first gym awaits you!"]),
                    wait_for_input=True)
            else:
                self.message_box.queue_messages(
                    self._tag_dialogue('Amber', ["Please collect all 3 dinos and return here!"]),
                    wait_for_input=True)
        elif npc.trainer_id == 'skyy':
            if not self.story_flags.get('gym1_accessible'):
                self._start_skyy_dialogue(npc)
        elif npc.trainer_id == 'scarecrux':
            if self.night_active:
                self.message_box.queue_messages(
                    ["The scarecrow has awoken in the night..."],
                    wait_for_input=True,
                    on_complete=lambda: self._start_scarecrux_battle(npc))
            else:
                self.message_box.queue_messages(
                    ["The scarecrow's purpose is to ward off luna's in the area",
                     "... Somethings feels a bit off"],
                    wait_for_input=True)

    def _start_scarecrux_battle(self, npc):
        """One-time night event: the scarecrow leaves for good once it wakes up."""
        self.story_flags['scarecrux_awakened'] = True
        self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
        if npc in self.npcs:
            self.npcs.remove(npc)
        self.trigger_encounter(forced_dino='Scarecrux', forced_level=15)

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
            name='Skyy'
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
        self.route_banner.update(dt)

        if getattr(self, '_post_xp_callback', None):
            if not (hasattr(self, 'encounter_ui') and self.encounter_ui.is_xp_animating()):
                cb = self._post_xp_callback
                self._post_xp_callback = None
                cb()

        if 'encounter' in self.state_stack and hasattr(self, 'encounter_ui'):
            active = self.player_dinos[self.active_dino_index]
            if self.is_double_battle:
                p2 = self._double_battle_p2() or active
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

        if self.coord_input_active:
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
            elif self.orb_fx:
                self._update_orb_fx(dt)
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
            self._check_route2_blocker()
            self._maybe_add_gym_blocker()
            self._maybe_add_gym2_blocker()
            self._check_gym2_blocker_removal()
            self._maybe_add_route2_blocker()
            self._maybe_add_skyy()
            self._maybe_add_gray_rival()
            self._maybe_add_grunts_vanessa()
            self._check_gym2_corn_maze_reveal()
            self._check_route26_abby_reveal()
            self._update_abby_follow(dt)
            self._check_route26_boundary()

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
            if self.orb_fx:
                self._draw_orb_fx(self.render_surface)
            if self.cutscene:
                self._draw_gym2_cutscene_fx(self.render_surface)
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
            self.route_banner.draw(self.screen)
            if self.cutscene_flash and self.cutscene_flash['alpha'] > 0:
                _flash = pygame.Surface((config.WIDTH, config.HEIGHT))
                _flash.fill(self.cutscene_flash.get('color', (255, 235, 150)))
                _flash.set_alpha(int(self.cutscene_flash['alpha']))
                self.screen.blit(_flash, (0, 0))
            if self.coord_input_active:
                self._draw_coord_input(self.screen)

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
                p2 = self._double_battle_p2()
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

        elif current_state in ('menu', 'party', 'items', 'shop', 'box', 'dino_picker', 'quest_debug'):
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
            elif current_state == 'quest_debug':
                self.quest_debug_screen.draw(self.screen)

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

    def _draw_coord_input(self, surface):
        box = pygame.Rect(0, 0, 480, 50)
        box.center = (config.WIDTH // 2, 40)
        pygame.draw.rect(surface, (255, 255, 255), box)
        pygame.draw.rect(surface, (0, 0, 0), box, 3)
        font = self.fonts['DIALOGUE']
        label = font.render(f"Teleport x,y: {self.coord_input_text}", True, (0, 0, 0))
        surface.blit(label, (box.x + 10, box.y + (box.height - label.get_height()) // 2))

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

    def _visible_world_maps(self):
        """world_maps entries whose rect overlaps a padded viewport — pad
        the camera's visible area out to 2x its size (centered) so maps
        don't pop in/out right at the screen edge. Large stitched worlds
        (LOST_REGION.world is 80+ maps) would otherwise blit every tile of
        every map every frame regardless of camera position."""
        render_w = config.WIDTH // self.zoom
        render_h = config.HEIGHT // self.zoom
        pad_x, pad_y = render_w / 2, render_h / 2
        view_left = self.camera_x - pad_x
        view_top = self.camera_y - pad_y
        view_right = self.camera_x + render_w + pad_x
        view_bottom = self.camera_y + render_h + pad_y
        return [
            wmap for wmap in self.world_maps
            if wmap['x'] < view_right and wmap['x'] + wmap['width'] > view_left
            and wmap['y'] < view_bottom and wmap['y'] + wmap['height'] > view_top
        ]

    def draw_map_below(self, surface):
        ts = config.TILE_SIZE
        for wmap in self._visible_world_maps():
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
        for wmap in self._visible_world_maps():
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
                _alive_ct    = len(alive)
                _act_m       = ACTIVE_XP_MULT_SOLO if _alive_ct == 1 else ACTIVE_XP_MULT_PARTY
                _ben_m       = BENCH_XP_MULT.get(_alive_ct, 1.0)
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
                _ct_act_m = ACTIVE_XP_MULT_SOLO if len(alive) == 1 else ACTIVE_XP_MULT_PARTY
                _ct_ben_m = BENCH_XP_MULT.get(len(alive), 1.0)
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
                multiplier = 1.0 if is_boss_tier_trainer(t_data) else 0.9
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
            _disp_act_m = ACTIVE_XP_MULT_SOLO if _disp_alive == 1 else ACTIVE_XP_MULT_PARTY
            _disp_ben_m = BENCH_XP_MULT.get(_disp_alive, 1.0)
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

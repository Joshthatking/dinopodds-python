import pygame
import pytmx
import json
import re
import math
from collections import deque
from player import Player
from npc import NPC
from ANIM.surf import Surf  # SURF (testing)
from ANIM.environment_fx import EnvironmentFX  # ENV FX
from ANIM.aether_bg import AetherBackground
from ANIM.lake_aurora import LakeAurora  # LAKE AURORA
from ANIM.space_bg import LunarBackground, SolarBackground
from ANIM.celestial_portals import CelestialPortals  # PORTALS
from ANIM.legend_awaken import DeimoAwaken, VYAwaken
from ANIM.battle_transition import BattleTransition
from moves import MoveAnimation
from ANIM.catch_anim import CatchAnimation
from ANIM import send_out_anim
from ANIM.send_out_anim import SendOutAnimation, enemy_slide_offset
from ANIM.title_anim import LaunchIntro
from ANIM.sky_transition import SkyTransition
from ANIM.credits import CreditsSequence
from sfx import SFX
from randomizer import Randomizer, area_for_zone
import os
import config
from screens import *
from data import *
import random
import story as _story

SAVE_PATH = 'dinopodds_save.json'
TITLE_MUSIC_PATH = os.path.join('assets', 'SOUND', 'title.wav')
TITLE_MUSIC_GAIN = 1.3   # the title / credits theme plays a little louder than the Options level

# Looping area music: (world file, where, track). `where` is a tile rect
# (x1, y1, x2, y2), a map-name prefix like 'PALM_PORT' (every .tmx in the
# .world whose file name starts with it), or None for the whole world. The
# first match for the player's tile plays; anywhere else is silent. See
# Game._update_area_music.
_MUSIC = os.path.join('assets', 'SOUND')
AREA_MUSIC = [
    ('LOST_REGION.world', (-5, -28, 14, 31), os.path.join(_MUSIC, 'route1.wav')),        # ROUTE_1 .. ROUTE_1.4
    ('LOST_REGION.world', (-5, 32, 14, 46), os.path.join(_MUSIC, 'silverleaf.wav')),     # START_TOWN (Silverleaf)
    ('LOST_REGION.world', (-25, 17, -6, 46), os.path.join(_MUSIC, 'silverleaf.wav')),    # START_COAST + START_COAST_1.1
    ('LOST_REGION.world', (15, -26, 34, 16), os.path.join(_MUSIC, 'sierratown.wav')),    # TOWN_1 .. 1.3, up to the Route 2 banner (y=-27)
    ('LOST_REGION.world', (-20, -120, 55, -76), os.path.join(_MUSIC, 'lake_meridian.wav')),  # Lake Meridian
    ('LOST_REGION.world', (-25, -74, 54, -59), os.path.join(_MUSIC, 'route3.wav')),       # ROUTE3_1 .. ROUTE3_4
    ('LOST_REGION.world', 'POWER_PLANT', os.path.join(_MUSIC, 'route3.wav')),            # outside the Power Plant (POWER_PLANT1/2)
    ('LOST_REGION.world', 'PALM_PORT', os.path.join(_MUSIC, 'palmport.wav')),            # PALM_PORT1 .. 15
    ('LOST_REGION.world', 'ROUTE4', os.path.join(_MUSIC, 'route4.wav')),                 # ROUTE4.1, ROUTE4_2
    # Corn Maze before Route 2: ROUTE2.6's strip east of the "Corn Maze" banner (x=89) is the maze
    ('LOST_REGION.world', (89, -58, 94, -44), os.path.join(_MUSIC, 'corn_maze.wav')),
    ('LOST_REGION.world', 'CORN_MAZE', os.path.join(_MUSIC, 'corn_maze.wav')),           # CORN_MAZE1 .. 6
    ('LOST_REGION.world', 'ROUTE2', os.path.join(_MUSIC, 'route2.wav')),                 # ROUTE2, 2.1 .. 2.7, ROUTE2_FILL_0
    ('LOST_REGION.world', 'TOWN2_4', None),                                               # Episc Chateau grounds: silent (haunted)
    ('LOST_REGION.world', 'TOWN2', os.path.join(_MUSIC, 'elder_town.wav')),              # Elder Town: TOWN2_1/2/3, TOWN2_BLOCK
    ('COBALT_CAVE.world', None, os.path.join(_MUSIC, 'cobalt_cave.wav')),
    ('DINOCENTER.tmx', None, os.path.join(_MUSIC, 'dc.wav')),                           # every town's DinoCenter
    ('LUNAR_PLANET.tmx', None, os.path.join(_MUSIC, 'spacial.wav')),
    ('SOLAR_PLANET.tmx', None, os.path.join(_MUSIC, 'spacial.wav')),
    ('HORIZON_CAVE.world', None, os.path.join(_MUSIC, 'spacial.wav')),
    ('HORIZON_CAVE1.tmx', None, os.path.join(_MUSIC, 'spacial.wav')),                    # Josh's entrance room
]
LAKE_MUSIC = os.path.join(_MUSIC, 'lake_meridian.wav')     # swells while the Lake Meridian lights are out
BATTLE_MUSIC = os.path.join(_MUSIC, 'encounter.wav')  # wild + ordinary trainer battles
BOSS_MUSIC = os.path.join(_MUSIC, 'boss.wav')         # gym leaders, rival, bosses, legendaries
GYM_LEADERS = ('skyy', 'log', 'sam')

# CORN_MAZE5's 3x3 tomb monument (world tile coords) — the interactable
# lore object housing the Scarecrux <-> Gourdecrux night transformation.
GOURDECRUX_TOMB_TILES = {
    (124, -68), (125, -68), (126, -68),
    (124, -67), (125, -67), (126, -67),
    (124, -66), (125, -66), (126, -66),
}
GOURDECRUX_TOMB_CENTER = (125, -67)

# LAKE_MERIDIAN7's 3x3 ruin (world tile coords) — tagged lore1 in the
# tileset, so it's checked before lore_tile_coords to give it its own text.
LAKE_MERIDIAN_PROPHECY_TILES = {
    (3, -102), (4, -102), (5, -102),
    (3, -101), (4, -101), (5, -101),
    (3, -100), (4, -100), (5, -100),
}

# LAKE_MERIDIAN8's 3x3 ruin (world tile coords) — tagged lore1 in the tileset,
# so it's checked before lore_tile_coords to give it its own text.
LAKE_MERIDIAN_CELESTIAL_RUIN_TILES = {
    (24, -111), (25, -111), (26, -111),
    (24, -110), (25, -110), (26, -110),
    (24, -109), (25, -109), (26, -109),
}


class Game:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)   # small buffer so SFX play without lag
        pygame.init()
        self.sfx = SFX()
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        pygame.display.set_caption('DinoPodds')
        self.clock = pygame.time.Clock()
        self.running = True
        self.state_stack = ['launch']

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
        self.surf = Surf(self)  # SURF (testing)
        self.env_fx = EnvironmentFX(self)  # ENV FX
        self.aether_bg = AetherBackground()  # void backdrop for AETHER_WORLDS
        self.lake_aurora = LakeAurora(self)  # LAKE AURORA
        self._space_bgs = {}   # SPACE_WORLDS file -> backdrop, built on first visit
        self.portals = CelestialPortals(self)  # PORTALS — post-credits lunar/solar portals
        self._area_music = None        # AREA_MUSIC track playing right now (None = silent)
        self._area_music_wait = 0      # ticks: don't start a track before this (lets fades finish)
        self._menu_duck = 1.0          # music volume multiplier, glides to MENU_DUCK while the menu is open
        self._scene_hold_until = 0     # ticks: area music stays off until then (story scene + grace)
        self._battle_in_scene = False  # the current battle started during a story scene
        self._music_scene_quiet = False

        self.fade_alpha = 0
        self.fade_color = (0, 0, 0)   # set white for one fade by a light-burst encounter
        self.battle_transition = None  # BattleTransition while a battle is starting
        self.fading = False

        # Dino frames & images
        self.dino_frames = {}
        for base in ("Vusion", "Anemamace", "Corlave", "Creuw", "Luna", "Prowscar", "Floravel", "Bullicorn", "Netaslam", "Netyrant", "Sortle", "Sharktastrophe", "Magnecrab", "Volkit", "Drafyton", "Auraliz", "Voltzbee", "Teamtwood", "Tygraflare", "Bouldava", "Ghoulflame", "Scarecrux", "Palidian", "Rockull", "Prickly", "Cyflactus", "Gourdecrux", "Rhysnow", "Seasoo", "Chomper", "Cobaltion", "Roxer", "Skolt", "Frostle", "Typhoonray", "Rhinecicle", "Celestreeyl", "Sharka", "Deimo", "VY", "Stormulus", "Lavaleo", "Pectura", "Ghoslink", "Browler", "Scarlust"):
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
        self.launch_intro = LaunchIntro(self)
        self._title_music_on = False
        self._start_title_music()
        self.menu = Menu(self)
        self.quest_debug_screen = QuestDebugScreen(self)
        self.party_screen = PartyScreen(self)
        self.party_screen.reset()
        self.move_info_screen = None
        self.dinodex_screen = DinodexScreen(self)
        self.trainer_card_screen = TrainerCardScreen(self)
        self.objectives_screen = ObjectivesScreen(self)
        self.options_screen = OptionsScreen(self)
        self.rules_screen = RulesScreen(self)
        self.controls_screen = ControlsScreen(self)
        self.box_tile_coords = set()
        self.box_screen = BoxScreen(self)
        self.type_chart_tile_coords = set()
        self.lore_tile_coords = set()
        self.type_chart_image = self._build_type_chart_image()

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
        self.dino_spawn_picker = None  # sandbox Ctrl+D: {'filter': str, 'index': int}

        # Heal animation state
        self.heal_anim = None
        self.yes_no_prompt = None
        self.yes_no_callback = None
        self.cutscene = None
        self.cutscene_flash = None
        self.orb_fx = None
        self.shadowhq_wave = None   # Cobaltion's dark energy rings (Shadow HQ intro)
        self._cobaltion_battle = False  # True from Cobaltion's battle start until its result is read
        self._surf_shack_prep_active = False  # True while the Surf Shack Preparation scene plays
        self._lantern_battle = None     # wisp index whose Ghoulflame battle is in progress (side quest)
        self._celestreeyl_battle = None  # the Celestreeyl NPC while its Horizon Cave battle runs
        self._legend_battle = None       # (npc, LEGENDS key) while a planet legendary's battle runs
        self._wild_caught = False       # set by attempt_catch on a successful catch
        self.screen_shake = 0.0         # seconds of screenshake left
        self.abby_follower = None
        self.abby_dinos = []
        self.is_vanessa_battle = False
        self.vanessa_dino_queue = []
        self.is_skyy_battle = False
        self.camera_locked = False  # True while a scripted camera pan owns camera_x/y
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
        self._maybe_add_horizon_blockers()
        self._maybe_add_route2_blocker()
        self._maybe_add_skyy()

        # Hit flash state
        self.hit_flash = None   # None | {'target':'player'|'enemy','timer':0,'duration':1.5,'interval':0.08}
        self.move_anim = None   # moves.MoveAnimation currently playing in battle
        self.catch_anim = None  # catch_anim.CatchAnimation for a thrown pod
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
        self.item_target_mode = None   # None | 'Revival Gem' | 'Mega Spray'
        self.pending_pp_exit_reveal = False   # fires after the player's next completed step

        # Trainer card / adventure tracking
        import datetime
        self.adventure_start_date = datetime.date.today()
        self.play_time_seconds    = 0.0
        self.objective_times      = {}  # OBJECTIVES id -> play-time seconds (None = beaten, time unknown)
        self.game_mode            = 'standard'  # chosen at New Game (see GAME_MODES)
        self.randomizer           = None        # randomizer.Randomizer in Randomizer mode
        self.nz_route_caught      = {}    # Nuzlocke: area -> species caught there (max 2)
        self.nz_owned_species     = []    # Nuzlocke: species owned before (e.g. traded away)
        self.nz_encounter         = None  # Nuzlocke: this wild battle's {'area','status','label'}
        self._nz_blackout_msgs    = []
        self.credits              = None  # ANIM.credits.CreditsSequence while the end credits play
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

        self.dn_transitioning = False      # True while a day<->night SkyTransition card plays
        self.dn_transition_timer = 0.0
        self.sky_transition = None         # sky_transition.SkyTransition card (pauses the game)
        self._night_overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        self._night_overlay.fill((30, 15, 60, 150))
        self._night_overlay_battle = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        self._night_overlay_battle.fill((30, 15, 60, 70))

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
        self.item_target_mode = None
        self.fading = False
        self.catch_anim = None

    def trigger_blackout(self):
        lost_npc = self.current_trainer_npc
        self.stats_blackouts += 1
        self._nz_blackout_msgs = []
        self._nuzlocke_retire_fainted(force=True)   # Nuzlocke: the fallen go to the box first
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
        self._clear_recharge_flags()
        self.entrance_fade_state = None
        self._post_trainer_battle_cb = None
        self.fade_color = (0, 0, 0)
        self.battle_transition = None
        # Blackout is a full reset back to normal world state — a scripted
        # cutscene that led into this battle (e.g. a walkup trigger) must
        # not stay "in progress" afterward, or it can never fire again.
        self.cutscene = None
        self.camera_locked = False

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

        # Losing Gray's Route 3 rematch used to leave him standing there as a
        # static NPC — since the scripted approach never touches npc.state,
        # the generic "reset spotted/walking/done trainers" loop above never
        # catches him, so he'd just sit there requiring a manual walk-up
        # rebattle. If the player didn't notice, gray_route3_done never got
        # set, permanently softlocking the Power Plant reveal that needs it
        # (see _check_skyy_powerplant_trigger). Instead, fully undo the
        # trigger: remove him and clear the "started" flag so walking onto
        # the Route 3 trigger tile again replays the whole cutscene.
        if lost_npc is not None and getattr(lost_npc, 'trainer_id', '') == 'gray2':
            self.story_flags['gray_route3_started'] = False
            if lost_npc in self.npcs:
                self.solid_tile_coords.discard((lost_npc.tile_x, lost_npc.tile_y))
                self.npcs.remove(lost_npc)

        # Place player at last DinoCenter or home spawn
        if self.last_dinocenter_tile is not None:
            tx, ty = self.last_dinocenter_tile
        else:
            px, py = config.SPAWN_POINTS.get('home', (160, 1248))
            tx, ty = px // config.TILE_SIZE, py // config.TILE_SIZE

        self._place_player(tx, ty)
        self.fade_alpha = 255
        self.entrance_fade_state = 'in'
        if self._nz_blackout_msgs:
            self.message_box.queue_messages(self._nz_blackout_msgs, wait_for_input=True)
            self._nz_blackout_msgs = []

    # --- Title / New Game / Save-Load ---

    def new_game(self, mode='standard'):
        import datetime
        self.story_flags = {}
        self.sandbox = False
        self.game_mode = mode
        self.randomizer = Randomizer() if mode in ('randomizer', 'randomizer_nuzlocke') else None
        self.nz_route_caught = {}
        self.nz_owned_species = []
        self.nz_encounter = None
        self.credits = None
        self.player_dinos = []
        self.box_dinos = []
        self.coins = 1000
        self.inventory = {item: 0 for item in config.ITEMS.keys()}
        if self.nuzlocke:
            self.inventory['DinoPod'] = 99
            self.inventory['Whitepod'] = 99
        self.items_screen.inventory = self.inventory
        self.badges_earned = []
        self.dinos_seen = set()
        self.stats_blackouts = 0
        self.stats_dinos_fainted = 0
        self.stats_enemies_defeated = 0
        self.play_time_seconds = 0.0
        self.objective_times = {}
        self.adventure_start_date = datetime.date.today()
        self.world_stack = []

        # A brand new game must never carry over runtime state left behind by
        # a previous playthrough (trainers marked defeated, picked-up ground
        # items, leftover battle/cutscene/day-night state, etc.) — see also
        # the equivalent reset block in load_game().
        self.defeated_trainers = set()
        self.picked_up_world_items = set()
        self.repel_steps = 0
        self.item_target_mode = None
        self.pending_pp_exit_reveal = False

        self.is_trainer_battle = False
        self.is_double_battle = False
        self.current_trainer_npc = None
        self.current_trainer_npc2 = None
        self.enemy_dino2 = None
        self.trainer_dino_queue = []
        self.trainer_dinos_total = 0
        self.trainer_dinos_defeated = 0
        self.awaiting_switch = False
        self.double_replace_slot = None
        self.double_replace_queue = []

        self.abby_follower = None
        self.abby_dinos = []
        self.is_vanessa_battle = False
        self.vanessa_dino_queue = []
        self.is_skyy_battle = False
        self.camera_locked = False
        self.cutscene = None
        self.cutscene_flash = None
        self.orb_fx = None
        self.shadowhq_wave = None
        self._cobaltion_battle = False
        self._surf_shack_prep_active = False
        self._lantern_battle = None
        self._wild_caught = False
        self.screen_shake = 0.0
        self.heal_anim = None
        self.yes_no_prompt = None
        self.yes_no_callback = None
        self.dino_pickup_popup = None

        self.day_night_timer = 0.0
        self.is_night = False
        self.force_night = None
        self.dn_transitioning = False
        self.dn_transition_timer = 0.0
        self.sky_transition = None
        self.event_overlay_active = False

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
        self.game_mode = 'standard'
        self.randomizer = None
        self.nz_encounter = None
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

    def _start_title_music(self):
        """Loop the title theme (launch splash + title menu). Silently skipped
        if there's no audio device."""
        if self._title_music_on:
            return
        self._area_music = None   # the title theme takes over the music channel
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(TITLE_MUSIC_PATH)
            pygame.mixer.music.set_volume(min(1.0, self.sfx.music_volume() * TITLE_MUSIC_GAIN))   # i menu -> Options
            pygame.mixer.music.play(-1, fade_ms=1500)
            self._title_music_on = True
        except pygame.error as e:
            print(f"[audio] title music unavailable: {e}")

    AREA_FADE_OUT_MS = 1500
    AREA_FADE_IN_MS = 2000
    BATTLE_FADE_OUT_MS = 350     # battles cut in (and back out) quickly
    BATTLE_FADE_IN_MS = 150
    LAKE_SWELL = 0.6             # Lake Meridian music gets up to 60% louder under the lights
    MENU_DUCK = 0.5              # music sits at 50% while the i menu (or a screen from it) is open
    MENU_DUCK_STEP = 0.02        # per frame, so the duck glides over ~0.4s

    SCENE_FADE_OUT_MS = 900      # area music clears out quickly when a story scene starts
    SCENE_GRACE_MS = 4000        # ...and stays off this long after it ends (scenes come in steps)

    def _is_big_trainer(self, npc):
        """Gym leaders (and their rematches), the rival and bosses."""
        key = self._trainer_key(npc)
        if key.replace('_rematch', '') in GYM_LEADERS:
            return True
        return TRAINER_DATA.get(key, {}).get('rank') in ('rival', 'boss')

    def _is_big_battle(self):
        """Big trainers and the scripted legendary fights get BOSS_MUSIC
        instead of BATTLE_MUSIC."""
        if self._legend_battle or self._celestreeyl_battle or self._cobaltion_battle:
            return True
        npc = self.current_trainer_npc
        return bool(self.is_trainer_battle and npc is not None and self._is_big_trainer(npc))

    def _story_scene_active(self):
        """A scripted story moment is playing: any cutscene phase, a forced
        walk, the scripted light/dark effects, or a rival / boss / gym leader
        walking up to challenge the player."""
        if (self.cutscene or self.forced_walk_npc or self.orb_fx or self.shadowhq_wave
                or self.cutscene_flash):
            return True
        return any(npc.npc_type == 'trainer' and npc.state in ('spotted', 'walking', 'done')
                   and not npc.defeated and self._is_big_trainer(npc)
                   for npc in self.npcs)

    def _wanted_music(self):
        """The track that should be playing right now (None = silence).
        Sets self._music_scene_quiet when it's silent because of a story scene."""
        self._music_scene_quiet = False
        if self._title_music_on or self.credits:
            return None
        now = pygame.time.get_ticks()
        if 'encounter' in self.state_stack:
            if now < self._scene_hold_until:
                self._battle_in_scene = True      # a story battle: stay quiet again once it's over
            return BOSS_MUSIC if self._is_big_battle() else BATTLE_MUSIC
        if self._battle_in_scene:
            self._battle_in_scene = False
            self._scene_hold_until = now + self.SCENE_GRACE_MS
        if self._story_scene_active():
            self._scene_hold_until = now + self.SCENE_GRACE_MS
        if now < self._scene_hold_until:
            if self.message_box.visible:          # the scene's dialogue is still going
                self._scene_hold_until = now + self.SCENE_GRACE_MS
            self._music_scene_quiet = True
            return None
        ts = config.TILE_SIZE
        tx, ty = self.player.rect.centerx // ts, self.player.rect.centery // ts
        for world, where, track in AREA_MUSIC:
            if world != self.current_world_file:
                continue
            if where is None:
                return track
            if isinstance(where, str):
                if self._map_name_at(tx, ty).startswith(where):
                    return track
            elif where[0] <= tx <= where[2] and where[1] <= ty <= where[3]:
                return track
        return None

    def _map_name_at(self, tx, ty):
        """File name of the .tmx (within the current .world) covering tile
        (tx, ty), or '' if none does. Cached per tile — it's asked every frame."""
        key = (self.current_world_file, tx, ty)
        if getattr(self, '_map_name_cache', (None,))[0] != key:
            ts = config.TILE_SIZE
            name = ''
            for m in self.world_maps:
                if (m['x'] // ts <= tx < (m['x'] + m['width']) // ts
                        and m['y'] // ts <= ty < (m['y'] + m['height']) // ts):
                    name = m.get('name', '')
                    break
            self._map_name_cache = (key, name)
        return self._map_name_cache[1]

    def _update_area_music(self):
        """Play the track for wherever the player is: the area's loop while
        walking around, the battle / boss theme during a battle, silence
        anywhere without music. Changes fade out, then the new track fades in."""
        if not pygame.mixer.get_init():
            return
        # menu duck: glide toward MENU_DUCK while the overworld menu is open
        menu_open = 'menu' in self.state_stack and 'encounter' not in self.state_stack
        target = self.MENU_DUCK if menu_open else 1.0
        step = self.MENU_DUCK_STEP
        self._menu_duck += max(-step, min(step, target - self._menu_duck))
        want = self._wanted_music()
        if want == self._area_music:
            if want is not None:
                self._apply_music_volume()
            return
        now = pygame.time.get_ticks()
        battle = (BATTLE_MUSIC, BOSS_MUSIC)
        quick = want in battle or self._area_music in battle
        if self._area_music is not None:
            fade = (self.BATTLE_FADE_OUT_MS if quick else
                    self.SCENE_FADE_OUT_MS if self._music_scene_quiet else self.AREA_FADE_OUT_MS)
            pygame.mixer.music.fadeout(fade)
            self._area_music = None
            self._area_music_wait = now + fade + 60
            return
        # wait for any fade-out (ours or the title theme's) to finish first
        if want is None or now < self._area_music_wait or pygame.mixer.music.get_busy():
            return
        try:
            pygame.mixer.music.load(want)
            pygame.mixer.music.set_volume(self.sfx.music_volume() * self._menu_duck)   # i menu -> Options
            pygame.mixer.music.play(-1, fade_ms=self.BATTLE_FADE_IN_MS if quick else self.AREA_FADE_IN_MS)
            self._area_music = want
        except pygame.error as e:
            print(f"[audio] area music unavailable: {e}")
            self._area_music_wait = now + 10_000

    def _apply_music_volume(self):
        """Volume for the playing track: the Options level, raised while the
        Lake Meridian lights are out (following the show's own fade), and
        ducked while the menu is open. Only touches the mixer when it changes,
        and also corrects a reset from Options (which sets the plain level)."""
        vol = self.sfx.music_volume() * self._menu_duck
        if self._area_music == LAKE_MUSIC and self.lake_aurora.active():
            vol *= 1 + self.LAKE_SWELL * self.lake_aurora._envelope()
        vol = min(1.0, vol)
        if abs(pygame.mixer.music.get_volume() - vol) > 0.01:
            pygame.mixer.music.set_volume(vol)

    def _stop_title_music(self):
        if not self._title_music_on:
            return
        self._title_music_on = False
        if pygame.mixer.get_init():
            pygame.mixer.music.fadeout(1200)

    def exit_to_title(self):
        self.pop_to_world()
        self.state_stack = ['title']
        self.title_screen.reset()
        self._start_title_music()

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
            'objective_times': self.objective_times,
            'game_mode': self.game_mode,
            'randomizer': self.randomizer.to_dict() if self.randomizer else None,
            'nuzlocke': {'route_caught': self.nz_route_caught,
                         'owned_species': self.nz_owned_species},
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
        self.sky_transition     = None
        self.event_overlay_active = (
            (self.story_flags.get('amber_intro_done', False) and
             not self.story_flags.get('gym1_accessible', False))
            or (self.story_flags.get('pp_eclipse_active', False)
                and not self.story_flags.get('shadowhq_event_done', False))
        )
        self.sandbox = data.get('sandbox', False)
        self.badges_earned = data.get('badges', [])
        self.play_time_seconds = data.get('play_time', 0.0)
        self.objective_times = dict(data.get('objective_times', {}))
        self.game_mode = data.get('game_mode', 'standard')
        rando = data.get('randomizer')
        self.randomizer = Randomizer.from_dict(rando) if rando else None
        nz = data.get('nuzlocke') or {}
        self.nz_route_caught = {k: list(v) for k, v in nz.get('route_caught', {}).items()}
        self.nz_owned_species = list(nz.get('owned_species', []))
        self.nz_encounter = None
        # Saves from before the notepad existed: anything already beaten
        # has no real time, so it's marked done-but-unknown (None) rather
        # than stamped with the load time.
        for obj_id, _, _, flags in OBJECTIVES:
            if obj_id not in self.objective_times and any(self.story_flags.get(f) for f in flags):
                self.objective_times[obj_id] = None
        self.dinos_seen = set(data.get('dinos_seen', []))
        self.picked_up_world_items = {tuple(e) for e in data.get('picked_up_world_items', [])}
        self.defeated_trainers = set(data.get('defeated_trainers', []))
        for npc in self.npcs:
            if getattr(npc, 'trainer_id', None) in self.defeated_trainers:
                npc.defeated = True
        self._refresh_gym_trainers_defeated()
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
        self._maybe_add_horizon_blockers()
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
            for i, spec in enumerate(event.get('award_dinos', [])):
                dino = self.create_dino(self._rando(spec['name'], f"gift:{event.get('id')}:{i}"),
                                        spec['level'])
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
        defense = Base_Stats(base_stats["defense"], level, p=DEFENSE_EXP)
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

    def _clamp_xp_to_cap(self, dino, cap):
        """Nuzlocke: at/over the level cap, XP stops one short of the next level."""
        if cap is not None and dino['level'] >= cap:
            dino['xp'] = min(dino['xp'], dino['xp_to_next'] - 1)

    def award_xp(self, dino, amount):
        cap = self._nuzlocke_level_cap()
        dino['xp'] += amount
        while dino['xp'] >= dino['xp_to_next'] and (cap is None or dino['level'] < cap):
            base_stats = DINO_DATA[dino["name"]]['stats']
            prev_max_hp = dino['max_hp']
            dino['xp'] -= dino['xp_to_next']
            dino['level'] += 1
            dino['xp_to_next'] = LevelXP(dino['level'] + 1) - LevelXP(dino['level'])
            dino['max_hp']  = HP_Base(base_stats["health"], dino['level'])
            dino['attack']  = Base_Stats(base_stats["attack"], dino['level'])
            dino['defense'] = Base_Stats(base_stats["defense"], dino['level'], p=DEFENSE_EXP)
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
        self._clamp_xp_to_cap(dino, cap)

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
        cap = self._nuzlocke_level_cap()
        for dino in alive:
            mult = active_mult if dino is active else bench_mult
            dino['xp'] += int(round(xp_gain * mult))
            while dino['xp'] >= dino['xp_to_next'] and (cap is None or dino['level'] < cap):
                base_stats = DINO_DATA[dino['name']]['stats']
                prev_max_hp = dino['max_hp']
                dino['xp'] -= dino['xp_to_next']
                dino['level'] += 1
                dino['xp_to_next'] = LevelXP(dino['level'] + 1) - LevelXP(dino['level'])
                dino['max_hp']  = HP_Base(base_stats['health'], dino['level'])
                dino['attack']  = Base_Stats(base_stats['attack'], dino['level'])
                dino['defense'] = Base_Stats(base_stats['defense'], dino['level'], p=DEFENSE_EXP)
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
                            # Its 4 active slots are already full — the move is
                            # known but not battle-ready. Easy to miss as just
                            # another line of level-up text, so give it its
                            # own emphatic, separately-dismissed message.
                            msgs.append(f">> {dino['name']} can learn {move_name}! <<")
                            msgs.append(f"It already knows 4 moves - visit the Party screen to swap {move_name} in.")
            self._clamp_xp_to_cap(dino, cap)
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
        elif ability['kind'] == 'recharge':
            # Consumed on the user's next turn: _player_recharge_turn (single
            # battle, player), _enemy_turn, _auto_attack_single, and the
            # double-battle p1/p2 slots.
            user['must_recharge'] = True
            msgs.append(f"{user['name']} is drained and must recharge!")
        return msgs

    def _clear_recharge_flags(self):
        """A pending recharge never carries over into another battle."""
        for d in list(self.player_dinos) + list(getattr(self, 'abby_dinos', None) or []):
            d.pop('must_recharge', None)

    def _player_recharge_turn(self, dino):
        """Single battle: the player's active dino spends this turn recharging
        instead of acting, so the enemy gets a free turn."""
        dino.pop('must_recharge', None)
        dino['defending'] = False
        dino['_prev_action_defend'] = False
        self.encounter_ui.in_fight_menu = False
        self.message_box.queue_messages(
            [f"{dino['name']} must recharge!"],
            wait_for_input=True, on_complete=self._enemy_turn)

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
        dino['defense'] = Base_Stats(base_stats['defense'], level, p=DEFENSE_EXP)
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

    def _first_alive_dino_index(self):
        """Which party slot a new single battle should open on. Defaults to
        0 like before, but if the front dino is already fainted from an
        earlier fight, skip straight to the first one that isn't instead of
        opening on a dead dino and immediately forcing a "choose a
        replacement" prompt the player never gets to bypass."""
        return next((i for i, d in enumerate(self.player_dinos) if d.get('hp', 0) > 0), 0)

    # TYPE_CHARv2.png grid: row/column order and the grid-line pixel
    # positions (the art's cells aren't evenly sized). Each cell is
    # repainted from TYPE_CHART_VAL so the chart can't drift from the data.
    TYPE_CHART_ORDER = ('magma', 'aqua', 'earth', 'ice', 'spike', 'lightning',
                        'flying', 'rock', 'dark', 'light', 'ancient')
    TYPE_CHART_COL_LINES = (249, 356, 466, 580, 692, 806, 945, 1059, 1171, 1285, 1396, 1509)
    TYPE_CHART_ROW_LINES = (163, 231, 300, 369, 439, 508, 577, 646, 715, 784, 853, 925)
    TYPE_CHART_COLORS = {20: (37, 150, 24), 5: (214, 8, 9), 10: (251, 251, 251)}

    def _build_type_chart_image(self):
        img = pygame.image.load('assets/SCREENS/TYPE_CHARv2.png').convert_alpha()
        cols, rows = self.TYPE_CHART_COL_LINES, self.TYPE_CHART_ROW_LINES
        for r, atk in enumerate(self.TYPE_CHART_ORDER):
            for c, dfn in enumerate(self.TYPE_CHART_ORDER):
                val = TYPE_CHART_VAL.get(atk, {}).get(dfn, 10)
                x0, x1 = cols[c] + 2, cols[c + 1]
                y0, y1 = rows[r] + 2, rows[r + 1]
                img.fill(self.TYPE_CHART_COLORS.get(val, self.TYPE_CHART_COLORS[10]),
                         (x0, y0, x1 - x0, y1 - y0))
        # Redraw the inner grid lines over the fills (the art has gaps in a few).
        line_col = (86, 92, 92)
        for x in cols[1:-1]:
            img.fill(line_col, (x, rows[0], 2, rows[-1] - rows[0]))
        for y in rows[1:-1]:
            img.fill(line_col, (cols[0], y, cols[-1] - cols[0], 2))
        return img

    def _battle_bg_override(self):
        """Cobalt Cave gets its own encounter/battle background instead of
        the default grass art, for every wild and trainer battle fought
        anywhere inside it (COBALT_CAVE.world covers the whole cave, every
        sub-room included). Horizon Cave (past Josh) gets the aether one,
        and battles fought while surfing in the overworld get the water one."""
        if self.current_world_file == 'COBALT_CAVE.world':
            return config.CAVE_ENCOUNTER_BG_PATH
        if self.current_world_file == 'HORIZON_CAVE.world':
            return config.HORIZON_ENCOUNTER_BG_PATH
        if self.current_world_file == 'LUNAR_PLANET.tmx':
            return config.LUNAR_ENCOUNTER_BG_PATH
        if self.current_world_file == 'SOLAR_PLANET.tmx':
            return config.SOLAR_ENCOUNTER_BG_PATH
        if self.current_world_file == 'LOST_REGION.world':
            ts = config.TILE_SIZE
            tile = (self.player.rect.x // ts, self.player.rect.y // ts)
            if self.surf.active or self.surf.is_water(tile):
                return config.WATER_ENCOUNTER_BG_PATH
        return None

    def get_player_zone(self, player_x, player_y):
        # ZONE_REGIONS is authored entirely in LOST_REGION.world's global
        # tile-coordinate space (Route 1, Route 2, Corn Maze, ...). Every
        # other world — single-map interiors especially — uses its own
        # small, locally-originated tile coordinates that can coincidentally
        # fall inside one of those overworld rectangles (e.g. an interior's
        # (2,2) lands inside route1_grass's region), so only consult it
        # while actually standing in the overworld. Other .worlds with
        # their own regions (e.g. Horizon Cave) live in WORLD_ZONE_REGIONS.
        zone = get_zone_for_tile(player_x, player_y, self.current_world_file)
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

    # --- Randomizer helpers (randomizer.py) ---
    # In Standard mode these all hand back the normal species.

    def _rando(self, name, tag):
        """`name`, or in Randomizer mode the save's fixed random dino for `tag`."""
        return self.randomizer.fixed(tag) if self.randomizer else name

    def _rando_team(self, dino_list, tag):
        """[(name, level), ...] with each slot randomized, levels kept."""
        if not self.randomizer:
            return list(dino_list)
        return [(self.randomizer.fixed(f"{tag}:{i}"), lvl) for i, (_, lvl) in enumerate(dino_list)]

    def _starter_map(self):
        """Starter ball id -> species (randomized in Randomizer mode)."""
        if self.randomizer:
            return self.randomizer.starters(config.DINO_BALL_MAP.keys())
        return config.DINO_BALL_MAP

    def _starter_names(self):
        return set(self._starter_map().values())

    def _player_original_starter(self):
        """The starter the player kept, as its Standard-mode species name
        (Floravel / Volkit / Corlave), so story logic keyed on the original
        starters (Gray's counter pick, Abby's partner) keeps working."""
        ball_of = {name: ball for ball, name in self._starter_map().items()}
        for d in self.player_dinos + self.box_dinos:
            if d['name'] in ball_of:
                return config.DINO_BALL_MAP[ball_of[d['name']]]
        return None

    # --- Nuzlocke (game modes 'nuzlocke' / 'randomizer_nuzlocke') ---
    # Rules (also shown on the i menu -> Rules page):
    #   * Level cap = the ace (highest level) of the next gym leader to beat,
    #     in NUZLOCKE_CAP_ORDER. At the cap, XP stops 1 short of the next
    #     level — except the KO on that leader's last dino, which counts
    #     against the next cap.
    #   * Each route/area (randomizer.area_for_zone) lets you catch its first
    #     2 new dinos. Those encounters are catch-only (no Fight/Defend/Run);
    #     after 2/2 you can only fight or run. A species you've already owned
    #     is a "Duplicate Skip": fight or run, no catching, doesn't count.
    #   * Sprays / Revival Gems are out-of-battle only (true in every mode).
    #   * A dino that faints is moved to the box for good after the battle.
    NUZLOCKE_MODES = ('nuzlocke', 'randomizer_nuzlocke')
    NUZLOCKE_ROUTE_CATCHES = 2
    NUZLOCKE_CAP_ORDER = [   # (flag set when beaten, TRAINER_DATA key whose ace sets the cap)
        ('gym1_leader_defeated',  'skyy'),
        ('gym2_leader_defeated',  'log'),
        ('gym3_leader_defeated',  'sam'),
        ('gym1_rematch_defeated', 'skyy_rematch'),
        ('gym2_rematch_defeated', 'log_rematch'),
        ('gym3_rematch_defeated', 'sam_rematch'),
    ]

    @property
    def nuzlocke(self):
        return self.game_mode in self.NUZLOCKE_MODES

    def _nuzlocke_cap_info(self, skip_key=None):
        """(cap level, leader key) for the next unbeaten gym, or (None, None)
        once every gym is done. `skip_key` treats that leader as beaten."""
        for flag, key in self.NUZLOCKE_CAP_ORDER:
            if self.story_flags.get(flag) or key == skip_key:
                continue
            return max(lvl for _, lvl in TRAINER_DATA[key]['dinos'].values()), key
        return None, None

    def _nuzlocke_level_cap(self):
        """Current cap, or None (no cap / not a Nuzlocke run). On the KO of
        the cap leader's final dino, the next gym's cap applies instead."""
        if not self.nuzlocke:
            return None
        cap, key = self._nuzlocke_cap_info()
        npc = self.current_trainer_npc
        if (key and self.is_trainer_battle and npc is not None
                and self._trainer_key(npc) == key and not self.trainer_dino_queue
                and self.enemy_dino and self.enemy_dino.get('hp', 1) <= 0):
            cap, _ = self._nuzlocke_cap_info(skip_key=key)
        return cap

    def _track_dex_seen(self):
        """Dinodex: register every species the player has met — any dino
        on the field in a wild/trainer/double battle, plus anything they own
        (starters, gifts, trades and evolutions arrive without a battle)."""
        seen = self.dinos_seen
        if 'encounter' in self.state_stack:
            foes = [getattr(self, 'enemy_dino', None)]
            if getattr(self, 'is_double_battle', False):   # enemy_dino2 can be stale otherwise
                foes.append(getattr(self, 'enemy_dino2', None))
            for d in foes:
                if d:
                    seen.add(d['name'])
        for d in self.player_dinos:
            seen.add(d['name'])
        for d in self.box_dinos:
            seen.add(d['name'])

    def _nuzlocke_owned_species(self):
        return ({d['name'] for d in self.player_dinos + self.box_dinos}
                | set(self.nz_owned_species))

    def _nuzlocke_setup_encounter(self, zone, tile_x, dino_key):
        """Decide this wild encounter's Nuzlocke status (None = no rule)."""
        self.nz_encounter = None
        if not self.nuzlocke or zone is None:
            return
        area = area_for_zone(zone, tile_x)
        caught = len(self.nz_route_caught.get(area, []))
        if caught >= self.NUZLOCKE_ROUTE_CATCHES:
            status, label = 'full', f"{self.NUZLOCKE_ROUTE_CATCHES}/{self.NUZLOCKE_ROUTE_CATCHES}"
        elif dino_key in self._nuzlocke_owned_species():
            status, label = 'dupe', "Duplicate Skip"
        else:
            status, label = 'catch', f"{caught}/{self.NUZLOCKE_ROUTE_CATCHES}"
        self.nz_encounter = {'area': area, 'status': status, 'label': label}

    def _nuzlocke_catch_only(self):
        """True while the battle must be a catch (no Fight/Defend/Run) — unless
        the player has no catching items left, so they can never get stuck."""
        nz = self.nz_encounter
        if not nz or nz['status'] != 'catch' or self.is_trainer_battle:
            return False
        return any(self.inventory.get(name, 0) > 0
                   for name, data in config.ITEMS.items() if data.get('catch_rate') is not None)

    def _nuzlocke_retire_fainted(self, force=False):
        """Move fainted party dinos to the box for good. Normally waits for a
        calm world frame; `force` runs it right away (blackout)."""
        if not self.nuzlocke:
            return
        if not force and (self.state_stack != ['world'] or self.message_box.visible
                          or self.cutscene or self.fading or self.entrance_fade_state):
            return
        fallen = [d for d in self.player_dinos if d.get('hp', 0) <= 0]
        if not fallen:
            return
        for d in fallen:
            d['nuzlocke_fainted'] = True
            self.player_dinos.remove(d)
            self.box_dinos.append(d)
        # An empty party pulls in any living dinos waiting in the box
        if not self.player_dinos:
            for d in [d for d in self.box_dinos if not d.get('nuzlocke_fainted')]:
                if len(self.player_dinos) >= self.PARTY_LIMIT:
                    break
                self.box_dinos.remove(d)
                self.player_dinos.append(d)
        self.active_dino_index = 0
        msgs = [f"{d['name']} fainted... it has been sent to the box for good." for d in fallen]
        if not self.player_dinos:
            msgs += ["You have no dinos left that can battle.", "Your Nuzlocke run is over."]
            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=self.exit_to_title)
            return
        if not force:
            self.message_box.queue_messages(msgs, wait_for_input=True)
        else:
            self._nz_blackout_msgs = msgs

    def _nuzlocke_battle_hud(self, screen):
        """Route catch counter, top center of wild battles."""
        nz = self.nz_encounter
        if not nz or self.is_trainer_battle:
            return
        font = self.fonts['BAG']
        text = font.render(nz['label'], True, (255, 255, 255))
        box = pygame.Rect(0, 0, max(70, text.get_width() + 24), text.get_height() + 10)
        box.midtop = (config.WIDTH // 2, 6)
        colour = {'catch': (40, 120, 60), 'full': (90, 90, 110), 'dupe': (150, 110, 30)}[nz['status']]
        pygame.draw.rect(self.screen, colour, box, border_radius=6)
        pygame.draw.rect(self.screen, (0, 0, 0), box, 2, border_radius=6)
        self.screen.blit(text, text.get_rect(center=box.center))

    def trigger_encounter(self, forced_dino=None, forced_level=None):
        self.nz_encounter = None
        if forced_dino:
            dino_key, level = self._rando(forced_dino, f"static:{forced_dino}"), forced_level
        else:
            tile_x = self.player.rect.x // config.TILE_SIZE
            tile_y = self.player.rect.y // config.TILE_SIZE
            zone = self.get_player_zone(tile_x, tile_y)
            # print(f"[ENCOUNTER] tile=({tile_x},{tile_y}) zone={zone}")

            zone_data = ENCOUNTER_ZONES[zone]
            dino_key = pick_zone_dino(zone_data, self.night_active)
            if dino_key is None:
                return  # nothing available right now (e.g. a night-only zone by day)
            if self.randomizer:
                dino_key = self.randomizer.wild(zone, tile_x)
            level = random.randint(*zone_data["level_range"])
            self._nuzlocke_setup_encounter(zone, tile_x, dino_key)

        self.player.freeze_in_place()
        self.active_dino_index = self._first_alive_dino_index()
        self.fading = True
        self.fade_alpha = 0

        self.enemy_dino = self.create_dino(dino_key, level)
        self.field_effects = []
        self.defend_uses_remaining = 3
        self.enemy_defend_uses_remaining = 3
        self._clear_recharge_flags()
        self.dinos_seen.add(dino_key)
        self.encounter_ui = EncounterUI(self.fonts)
        self.encounter_text = f"A wild {dino_key} appeared!"
        self.encounter = Encounter(self.fonts, dino_key, bg_path=self._battle_bg_override())

        now = pygame.time.get_ticks()
        frames = self.dino_frames.get(self.enemy_dino['name'], [self.enemy_dino['image']])
        self.encounter_anim = {
            "frames": frames,
            "frame_idx": 0,
            "last_switch": now,
            "interval": 250,
            "start_time": now,
            "duration": send_out_anim.TOTAL_MS,
            "intro": 'send_out',   # enemy slides in, then the player's pod is thrown
        }

    def start_trainer_battle(self, npc):
        # Guard against a duplicate/overlapping trigger (e.g. the NPC's own
        # sight-based approach firing its challenge at the same time the
        # player manually interacted with it) re-entering and stomping an
        # already-starting battle's state mid-transition.
        if self.is_trainer_battle:
            return
        self.player.freeze_in_place()
        self.active_dino_index = self._first_alive_dino_index()
        self.fading = True
        self.fade_alpha = 0
        self.is_trainer_battle = True
        # This starts a single-opponent battle — always clear any leftover
        # double-battle state (e.g. from an earlier double battle this same
        # playthrough that didn't get torn down cleanly), or the battle
        # renders/behaves as a double with a stale, already-fainted second
        # enemy slot that looks like "the first dino was already defeated".
        self.is_double_battle = False
        self.enemy_dino2 = None
        self.current_trainer_npc = npc
        self.current_trainer_npc2 = None

        key = self._trainer_key(npc)
        rematch_i, rematch_g = self._gym_rematch_entry(npc.trainer_id)
        if key.endswith('_rematch') and npc.trainer_id == rematch_g['leader']:
            self._post_trainer_battle_cb = lambda i=rematch_i: self._on_gym_rematch_won(i)
        elif npc.trainer_id == 'gray':
            self._post_trainer_battle_cb = lambda: self._on_gray_battle_won(npc)
        elif npc.trainer_id == 'gray2':
            self._post_trainer_battle_cb = lambda: self._on_gray2_battle_won(npc)
        elif npc.trainer_id == 'skyy' and self.current_world_file == 'GYM1.tmx':
            self._post_trainer_battle_cb = self._on_skyy_gym_won
        elif npc.trainer_id == 'log' and self.current_world_file == 'GYM2.tmx':
            self._post_trainer_battle_cb = self._on_log_gym_won
        elif npc.trainer_id == 'sam' and self.current_world_file == 'GYM3.tmx':
            self._post_trainer_battle_cb = self._on_sam_gym_won
        elif npc.trainer_id == 'josh':
            self._post_trainer_battle_cb = lambda: self._on_josh_battle_won(npc)
        elif npc.trainer_id == 'pp_grunt_a':
            self._post_trainer_battle_cb = lambda: self._on_pp_grunt_a_won(npc)
        elif npc.trainer_id == 'pp_grunt_b':
            self._post_trainer_battle_cb = lambda: self._on_pp_grunt_b_won(npc)

        data = TRAINER_DATA.get(key, {})
        dinos = data.get('dinos', {})
        sorted_keys = sorted(dinos.keys())
        override = getattr(npc, 'override_first_dino', None)
        dino_list = [(dinos[k][0], dinos[k][1]) for k in sorted_keys]
        if override and getattr(npc, 'override_replaces_first', False):
            # Override replaces the placeholder first dino (e.g. Gray's Route 1
            # counter-starter trick) rather than adding an extra one.
            dino_list[0] = override
        elif override:
            # Override is an additional dino tacked on at the end (e.g. Gray's
            # Route 3 rematch, where the evolved counter-starter closes it out).
            dino_list.append(override)
        dino_list = self._rando_team(dino_list, f"trainer:{key}")
        dino_name, dino_level = dino_list[0]
        self.trainer_dino_queue = dino_list[1:]
        self.trainer_dinos_total = len(self.trainer_dino_queue) + 1
        self.trainer_dinos_defeated = 0

        self.enemy_dino = self.create_dino(dino_name, dino_level)
        self.field_effects = []
        self.defend_uses_remaining = 3
        self.enemy_defend_uses_remaining = 3
        self._clear_recharge_flags()
        self.encounter_ui = EncounterUI(self.fonts)
        trainer_name = TRAINER_DATA.get(npc.trainer_id, {}).get('name', 'Trainer')
        self.encounter_text = f"{trainer_name} sent out {dino_name}!"
        self.encounter = Encounter(self.fonts, dino_name, bg_path=self._battle_bg_override())

        now = pygame.time.get_ticks()
        frames = self.dino_frames.get(dino_name, [self.enemy_dino['image']])
        self.encounter_anim = {
            "frames": frames,
            "frame_idx": 0,
            "last_switch": now,
            "interval": 250,
            "start_time": now,
            "duration": send_out_anim.TOTAL_MS,
            "intro": 'send_out',
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
        self.player.freeze_in_place()
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
        n1 = self._rando(n1, f"trainer:{self._trainer_key(npc1)}:0")
        n2 = self._rando(n2, f"trainer:{self._trainer_key(npc2)}:0")

        self.enemy_dino  = self.create_dino(n1, l1)
        self.enemy_dino2 = self.create_dino(n2, l2)

        self.trainer_dino_queue     = []
        self.trainer_dinos_total    = 2
        self.trainer_dinos_defeated = 0
        self.field_effects              = []
        self.defend_uses_remaining      = 3
        self.enemy_defend_uses_remaining = 3
        self._clear_recharge_flags()

        self.encounter_ui   = DoubleBattleUI(self.fonts)
        self.encounter_text = f"Double Battle! {n1} and {n2}!"
        self.encounter      = DoubleBattleEncounter(self.fonts, n1, n2, bg_path=self._battle_bg_override())

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
        if attacker.pop('must_recharge', False):
            attacker['defending'] = False
            self.message_box.queue_messages(
                [f"{attacker_label}{attacker['name']} must recharge!"],
                wait_for_input=True, on_complete=after)
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
        p1 = self.player_dinos[0] if self.player_dinos else None
        if attacker_label == "":  # player attacking enemy
            flash_target = 'enemy1' if defender is self.enemy_dino else 'enemy2'
            anim_source  = 'player1' if attacker is p1 else 'player2'
        else:  # enemy attacking player
            flash_target = 'player1' if defender is p1 else 'player2'
            anim_source  = 'enemy1' if attacker is self.enemy_dino else 'enemy2'
        self.play_move_anim(move_name, flash_target, anim_source)
        if dmg > 0:
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
        """True when an NPC ally is fighting alongside the player in this
        double battle — Abby (once she's joined post-escort, the grunt pair,
        or the Vanessa boss fight) or Skyy (the Power Plant grunt pair).
        `self.abby_dinos` doubles as the generic "ally's team" slot for
        whichever ally is actually active; see _ally_name() for display text."""
        if self.is_skyy_battle:
            return bool(self.abby_dinos)
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
        p1 = self.player_dinos[0] if self.player_dinos else None
        if p1 and p1.get('hp', 0) > 0 and p1.get('must_recharge'):
            self.double_p1_queued = {'action': 'recharge'}
            self._double_advance_to_p2()

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
        if p2.get('must_recharge'):
            self.double_p2_queued = {'action': 'recharge'}
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
            if p2q.get('action') == 'recharge':
                p2.pop('must_recharge', None)
                self.message_box.queue_messages(
                    [f"{p2['name']} must recharge!"], wait_for_input=True, on_complete=e1_attacks)
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
            if p1q.get('action') == 'recharge':
                p1.pop('must_recharge', None)
                self.message_box.queue_messages(
                    [f"{p1['name']} must recharge!"], wait_for_input=True, on_complete=p2_attacks)
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
            elif self.is_skyy_battle:
                self._finish_skyy_grunts_battle(won=True)
            else:
                self._finish_double_battle()
            return

        if all(d.get('hp', 0) <= 0 for d in self.player_dinos):
            if self.is_vanessa_battle:
                self._finish_vanessa_battle(won=False)
            elif self.is_skyy_battle:
                self._finish_skyy_grunts_battle(won=False)
            else:
                self.message_box.queue_messages(
                    ["You blacked out!", "Be careful next time..."],
                    wait_for_input=True, on_complete=self.trigger_blackout)
            return

        # Ally (Abby or Skyy) swaps in their own bench dino automatically —
        # it's their roster to manage, not the player's, so no "choose a
        # replacement" prompt.
        if self._abby_is_ally() and p2 and p2.get('hp', 0) <= 0:
            if len(self.abby_dinos) > 1 and self.abby_dinos[1].get('hp', 0) > 0:
                fainted_name = self.abby_dinos[0]['name']
                self.abby_dinos[0], self.abby_dinos[1] = self.abby_dinos[1], self.abby_dinos[0]
                new_name = self.abby_dinos[0]['name']
                ally = 'Skyy' if self.is_skyy_battle else 'Abby'
                self.message_box.queue_messages(
                    [f"{fainted_name} fainted!", f"{ally} sent out {new_name}!"],
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
        if not os.path.exists(path):  # cave interiors like HORIZON_CAVE1 live in MAPS
            path = os.path.join('assets/MAPS', filename)
        tmx = pytmx.load_pygame(path, pixelalpha=True)
        ts = config.TILE_SIZE
        solid, encounter, tile_types, entrances, exits, ball_items = set(), set(), {}, {}, set(), {}
        self.box_tile_coords = set()   # reset; populated below if map has a box object
        self.type_chart_tile_coords = set()
        self.lore_tile_coords = set()
        for layer in tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                above = self._layer_num(layer) >= 4
                # Layer property "no_collision: true" — e.g. a floor layer
                # reusing a tile whose tileset entry is marked collision.
                no_collision = bool((layer.properties or {}).get('no_collision'))
                for x, y, gid in layer:
                    if not gid:
                        continue
                    props = tmx.get_tile_properties_by_gid(gid) or {}
                    wpos = (x, y)
                    if props.get('collision') and not above and not no_collision:
                        solid.add(wpos)
                    if props.get('encounter'):
                        encounter.add(wpos)
                    if (props.get('encounter') or props.get('interact')) and props.get('type'):
                        tile_types[wpos] = props['type']   # see load_world
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
        self.player.freeze_in_place()
        self.sfx.play('door')

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
        if entrance_id == 'shadowhq1' and self.story_flags.get('shadow_confrontation_done'):
            # Skyy follows the player into Shadow HQ — drop the Cobalt Cave
            # copy so he isn't also still standing back in the cave.
            cave_npcs = self.world_stack[-1]['npcs']
            cave_npcs[:] = [n for n in cave_npcs if getattr(n, 'trainer_id', '') != 'skyy']
        tx, ty = dest['spawn']
        self._place_player(tx, ty)
        banner_name = ENTRANCE_BANNER_NAMES.get(entrance_id)
        if banner_name:
            self.route_banner.show(banner_name)

    def trigger_exit(self):
        if self.entrance_fade_state is not None:
            return
        # Can't leave the Power Plant while the elite grunt pair inside
        # POWER_PLANT_IN3 is still unresolved.
        if (self.current_world_file == 'POWERPLANT.world'
                and self.story_flags.get('pp_grunts2_started')
                and not self.story_flags.get('pp_grunts2_done')
                and not self.message_box.visible):
            self.message_box.queue_messages(
                self._tag_dialogue('Skyy', ["We can't leave yet — not until we deal with those two!"]),
                wait_for_input=True)
            return
        _home_maps = ('HOME_JET2.tmx', 'HOME_JET.tmx')
        if not self.world_stack and self.current_world_file not in _home_maps:
            return
        self.entrance_pending = '__exit__'
        self.entrance_fade_state = 'out'
        self.fade_alpha = 0
        self.player.freeze_in_place()
        self.sfx.play('door')

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
        self._maybe_add_horizon_blockers()
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
        if (prev.get('entrance_id') == 'power' and self._pp_all_battles_done()
                and not self.story_flags.get('pp_eclipse_reveal_done')):
            self._pp_setup_reveal_npcs()
            # Dialogue itself still doesn't fire immediately — wait until
            # the player takes one more step in the overworld (see
            # Player.update's step-complete block).
            self.pending_pp_exit_reveal = True

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
        self.encounter = Encounter(self.fonts, dino_name, bg_path=self._battle_bg_override())
        now = pygame.time.get_ticks()
        frames = self.dino_frames.get(dino_name, [self.enemy_dino['image']])
        self.encounter.current_dino_surface = frames[0]
        self.encounter_anim = {
            "frames": frames,
            "frame_idx": 0,
            "last_switch": now,
            "interval": 250,
            "start_time": now,
            "duration": send_out_anim.SLIDE_ONLY_MS,
            "intro": 'slide',   # the player's dino is already out
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

    # ── Mom (HOME_JET downstairs) ────────────────────────────────────────
    def _check_mom_greeting(self):
        """First time the player comes downstairs on a new game. Waits for
        the stairs fade-in to finish so the dialogue isn't shown over a
        black screen."""
        if self.story_flags.get('mom_greeting_done') or self.current_world_file != 'HOME_JET.tmx':
            return
        if self.story_flags.get('amber_intro_done') or self.story_flags.get('credits_done'):
            # Older save already past the opening — don't greet as if it's day one.
            self.story_flags['mom_greeting_done'] = True
            return
        if self.cutscene or self.message_box.visible or self.fading or self.entrance_fade_state:
            return
        mom = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'mom'), None)
        if not mom:
            return
        self.player.freeze_in_place()
        mom.face_toward_player(self.player)
        self.cutscene = {'phase': 'shadowhq_wait'}  # generic no-op wait
        self.message_box.queue_messages(
            self._tag_dialogue('Mom', [
                "Good morning Jet! There are blueberry muffins on the counter!",
                "The professor is looking for you, have fun today sweetie!",
            ]),
            wait_for_input=True,
            on_complete=lambda: self._finish_mom_greeting(mom))

    # ── Ending: credits -> wake up at home -> Mom ─────────────────────────
    # Picking up the Celestial Solar Shard rolls ANIM/credits.py. Afterwards
    # the player wakes in their room (HOME_JET2) to the alarm, and Mom
    # greets them downstairs. Flags: credits_done -> credits_wakeup_done ->
    # mom_ending_done.

    def _start_credits(self):
        self.player.freeze_in_place()
        self.credits = CreditsSequence(self.screen)
        self._title_music_on = False
        self._start_title_music()   # the title theme plays over the credits

    def _finish_credits(self):
        self.credits = None
        self._stop_title_music()
        self.story_flags['credits_done'] = True
        self.cutscene = None
        self.world_stack = []
        self._load_world_data('HOME_JET2.tmx')
        self._spawn_world_npcs('HOME_JET2.tmx')
        self._place_player(7, 5)      # in bed, same spot as a new game
        self.player.direction = self.player.facing = 'down'
        self.player.image = self.player.animations['down'][0]
        self.state_stack = ['world']
        self.fade_alpha = 255
        self.entrance_fade_state = 'in'

    def _check_credits_wakeup(self):
        """The alarm, once the fade back in from the credits has finished."""
        f = self.story_flags
        if not f.get('credits_done') or f.get('credits_wakeup_done'):
            return
        if self.current_world_file != 'HOME_JET2.tmx':
            f['credits_wakeup_done'] = True
            return
        if self.entrance_fade_state or self.fading or self.message_box.visible:
            return
        f['credits_wakeup_done'] = True
        self.message_box.queue_messages(["...beep...beep...beep..."], wait_for_input=True)

    def _check_mom_ending(self):
        f = self.story_flags
        if not f.get('credits_done') or f.get('mom_ending_done') or self.current_world_file != 'HOME_JET.tmx':
            return
        if self.cutscene or self.message_box.visible or self.fading or self.entrance_fade_state:
            return
        mom = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'mom'), None)
        if not mom:
            return
        self.player.freeze_in_place()
        mom.face_toward_player(self.player)
        self.cutscene = {'phase': 'shadowhq_wait'}  # generic no-op wait

        def done():
            f['mom_ending_done'] = True
            self.cutscene = None
        self.message_box.queue_messages(
            self._tag_dialogue('Mom', [
                "Jet you did it!",
                "I am so proud of you, you had quite the adventure dear",
                "There is so much more the world has to offer, this is only the beginning",
            ]),
            wait_for_input=True, on_complete=done)

    def _finish_mom_greeting(self, mom):
        self.story_flags['mom_greeting_done'] = True
        mom.facing = 'down'
        self.cutscene = None

    def _interact_mom(self, npc):
        if self.story_flags.get('package_started') and not self.story_flags.get('package_delivered'):
            self._deliver_package_to_mom()
            return
        if not self.player_dinos:
            self.message_box.queue_messages(
                self._tag_dialogue('Mom', ["Be careful out there today, Jet!"]), wait_for_input=True)
            return
        self.message_box.queue_messages(
            self._tag_dialogue('Mom', ["Welcome home, Jet! Let me take care of your dinos."]),
            wait_for_input=True,
            on_complete=self._start_mom_heal)

    def _start_mom_heal(self):
        for dino in self.player_dinos:
            dino['hp'] = dino['max_hp']
        self.cutscene_flash = {'alpha': 0, 'rising': True, 'count': 0, 'color': (255, 255, 255)}
        self.cutscene = {'phase': 'mom_heal_flash'}

    def _finish_mom_heal(self):
        self.cutscene = None
        self.message_box.queue_messages(
            self._tag_dialogue('Mom', ["All better! Your dinos are fully healed."]), wait_for_input=True)

    def _return_from_home_to_overworld(self):
        self._load_world_data('LOST_REGION.world')
        self._spawn_world_npcs('LOST_REGION.world')
        for npc in self.npcs:
            self.solid_tile_coords.add((npc.tile_x, npc.tile_y))
        # ── Adjust to match home exit tile in LOST_REGION.world ──
        self._place_player(11, 44)
        self._maybe_add_gym_blocker()
        self._maybe_add_gym2_blocker()
        self._maybe_add_horizon_blockers()
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
        self.player.freeze_in_place()
        self.player.current_move_speed = self.player.move_speed  # force normal (non-sprint) pace

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
        self.player.freeze_in_place()
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

        player_starter = self._player_original_starter()
        abby_starter = self.ABBY_STARTER_MAP.get(player_starter, 'Corlave')
        self.abby_dinos = [self.create_dino(n, lvl) for n, lvl in
                           self._rando_team([(abby_starter, 15), ('Auraliz', 15)], "ally:abby_route26")]

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
        self.player.freeze_in_place()
        self.active_dino_index = self._first_alive_dino_index()
        self.fading = True
        self.fade_alpha = 0
        self.is_trainer_battle = True
        self.is_double_battle  = True
        self.is_vanessa_battle = True
        self.current_trainer_npc  = vanessa
        self.current_trainer_npc2 = vanessa

        dinos = TRAINER_DATA.get('vanessa', {}).get('dinos', {})
        team = self._rando_team([dinos[k] for k in sorted(dinos.keys())], "trainer:vanessa")
        n1, l1 = team[0]
        n2, l2 = team[1]
        self.vanessa_dino_queue = team[2:]

        self.enemy_dino  = self.create_dino(n1, l1)
        self.enemy_dino2 = self.create_dino(n2, l2)

        self.trainer_dino_queue     = []
        self.trainer_dinos_total    = len(dinos)
        self.trainer_dinos_defeated = 0
        self.field_effects               = []
        self.defend_uses_remaining       = 3
        self.enemy_defend_uses_remaining = 3
        self._clear_recharge_flags()

        self.encounter_ui   = DoubleBattleUI(self.fonts)
        self.encounter_text = f"Vanessa sent out {n1} and {n2}!"
        self.encounter      = DoubleBattleEncounter(self.fonts, n1, n2, bg_path=self._battle_bg_override())

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
        if c['phase'] == 'celestreeyl_awaken':
            self._update_celestreeyl_awaken(dt)
            return
        if c['phase'] == 'legend_awaken':
            self._update_legend_awaken(dt)
            return
        if c['phase'] == 'solar_shard_reveal':
            self._update_solar_shard_reveal(dt)
            return
        if c['phase'] == 'lunar_shard_reveal':
            self._update_lunar_shard_reveal(dt)
            return
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
        if c['phase'] == 'skyy_pp_guided_walk':
            self._update_skyy_pp_guided_walk(dt)
            return
        if c['phase'] == 'skyy_pp_heal_flash':
            if not self.cutscene_flash:
                self._start_pp_grunts_approach()
            return
        if c['phase'] == 'pp_grunts_approaching':
            self._update_pp_grunts_approaching(dt)
            return
        if c['phase'] == 'pp_grunts_walking_away':
            self._update_pp_grunts_walking_away(dt)
            return
        if c['phase'] == 'camera_pan':
            self._update_camera_pan(dt)
            return
        if c['phase'] == 'pp_grunts2_wait':
            return  # generic no-op wait, no npc needed
        if c['phase'] == 'pp_grunt_a_walkup':
            self._update_pp_grunt_a_walkup(dt)
            return
        if c['phase'] == 'pp_grunt_b_walkup':
            self._update_pp_grunt_b_walkup(dt)
            return
        if c['phase'] == 'pp_grunts2_flash':
            if not self.cutscene_flash:
                self._finish_pp_grunts2_disappear()
            return
        if c['phase'] == 'pp_reveal_flares':
            if not self.cutscene_flash:
                self._pp_reveal_activate_eclipse(c['npc1'], c['npc2'])
            return
        if c['phase'] == 'pp_reveal_walking_away':
            self._update_pp_reveal_walking_away(dt)
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
        if c['phase'] == 'shadow_confrontation_wait':
            return  # generic no-op wait, no npc needed
        if c['phase'] == 'shadow_confrontation_walk':
            self._update_shadow_confrontation_walk(dt)
            return
        if c['phase'] == 'shadow_confrontation_splitup':
            self._update_shadow_confrontation_splitup(dt)
            return
        if c['phase'] == 'shadowhq_skyy_walk':
            self._update_shadowhq_skyy_walk(dt)
            return
        if c['phase'] == 'shadowhq_wait':
            return  # generic no-op wait, no npc needed
        if c['phase'] == 'shadowhq_grunt_walkup':
            self._update_shadowhq_grunt_walkup(dt)
            return
        if c['phase'] == 'shadowhq_walk':
            self._update_shadowhq_walk(dt)
            return
        if c['phase'] == 'mom_heal_flash':
            if not self.cutscene_flash:
                self._finish_mom_heal()
            return
        if c['phase'] == 'shadowhq_heal_flash':
            if not self.cutscene_flash:
                self._finish_shadowhq_heal()
            return
        if c['phase'] == 'cobaltion_collapse':
            self._update_cobaltion_collapse(dt)
            return
        if c['phase'] == 'surf_shack_prep_greet':
            self._surf_shack_prep_greet()
            return
        if c['phase'] == 'surf_shack_prep_walk':
            self._update_surf_shack_prep_walk(dt)
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
                self.cutscene = None
                self.start_sky_transition('eclipse', on_swap=self._enable_eclipse_overlay)

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

        elif c['phase'] == 'gray2_approaching':
            wx, wy = c['walk_target']
            if npc.tile_x == wx and npc.tile_y == wy:
                npc.anim_frame = 0
                self.player.facing = self.player.direction = 'left'
                self.player.image = self.player.animations['left'][0]
                c['phase'] = 'gray2_dialogue_wait'
                data = TRAINER_DATA.get('gray2', {})
                self.message_box.queue_messages(
                    self._tag_dialogue('Gray', data.get('dialog', {}).get('default', [])),
                    wait_for_input=True,
                    on_complete=lambda: self._start_gray2_battle(npc)
                )
            else:
                self._force_step_npc_toward_tile(npc, wx, wy)

        elif c['phase'] == 'gray2_dialogue_wait':
            pass  # waiting on the message_box's on_complete to fire

        elif c['phase'] == 'gray2_walking_away':
            if self.message_box.visible:
                return
            wx, wy = c['walk_target']
            if npc.tile_x == wx and npc.tile_y == wy:
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                if npc in self.npcs:
                    self.npcs.remove(npc)
                self.story_flags['gray_route3_done'] = True
                self.cutscene = None
            else:
                self._force_step_npc_toward_tile(npc, wx, wy)

        elif c['phase'] == 'josh_walking_away':
            if self.message_box.visible:
                return
            path = c['path']
            wx, wy = path[0]
            if npc.tile_x == wx and npc.tile_y == wy:
                path.pop(0)
                if not path:
                    self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                    if npc in self.npcs:
                        self.npcs.remove(npc)
                    self.story_flags['josh_defeated'] = True
                    self.cutscene = None
            else:
                self._force_step_npc_toward_tile(npc, wx, wy)

        elif c['phase'] == 'sam_surf_dialogue_wait':
            pass  # waiting on the message_box's on_complete chain

        elif c['phase'] == 'sam_surf_walking_away':
            if self.message_box.visible:
                return
            wx, wy = c['walk_target']
            if npc.tile_x == wx and npc.tile_y == wy:
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                if npc in self.npcs:
                    self.npcs.remove(npc)
                self.story_flags['sam_surf_intro_done'] = True
                self.cutscene = None
            else:
                self._force_step_npc_toward_tile(npc, wx, wy)

        elif c['phase'] == 'skyy_pp_approaching':
            wx, wy = c['walk_target']
            if npc.tile_x == wx and npc.tile_y == wy:
                npc.anim_frame = 0
                self.player.facing = self.player.direction = 'left'
                self.player.image = self.player.animations['left'][0]
                c['phase'] = 'skyy_pp_dialogue_wait'
                self.message_box.queue_messages(
                    self._tag_dialogue('Skyy', [
                        "Jet! There has been power disruptions all over the region again, we need to go to the central power plant!",
                        "Follow me!",
                    ]),
                    wait_for_input=True,
                    on_complete=self._start_skyy_pp_guided_walk
                )
            else:
                self._force_step_npc_toward_tile(npc, wx, wy)

        elif c['phase'] == 'skyy_pp_dialogue_wait':
            pass  # waiting on the message_box's on_complete to fire

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

    def _force_step_npc_toward_tile(self, npc, tx, ty):
        """Same as _step_npc_toward_tile but ignores solids — for a fixed
        multi-tile scripted walk (Gray/Skyy cutscenes) where a stray tree or
        rock along the path must never be able to soft-lock the cutscene by
        leaving it permanently stuck one tile short of its target."""
        dx, dy = tx - npc.tile_x, ty - npc.tile_y
        if abs(dx) >= abs(dy) and dx != 0:
            sx, sy = (1 if dx > 0 else -1), 0
        elif dy != 0:
            sx, sy = 0, (1 if dy > 0 else -1)
        else:
            return
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
                if f['count'] < f.get('max_count', 2):
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

    # Three BLK_Bs block the bridge to the Horizon Cave island until Gym 3 is beaten.
    HORIZON_BLOCKER_TILES = ((24, -102), (25, -102), (26, -102))
    HORIZON_BLOCKER_FLAG  = 'gym3_leader_defeated'

    def _maybe_add_horizon_blockers(self):
        if self.story_flags.get(self.HORIZON_BLOCKER_FLAG):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        if any(getattr(n, 'npc_type', '') == 'horizon_guard' for n in self.npcs):
            return
        for tx, ty in self.HORIZON_BLOCKER_TILES:
            blocker = NPC('blk_b', tile_x=tx, tile_y=ty, facing='down',
                          sight_range=0, npc_type='horizon_guard')
            blocker.state       = 'idle'
            blocker.home_tile   = (tx, ty)
            blocker.home_facing = 'down'
            blocker.block_dialog = ["You may not enter"]
            self.npcs.append(blocker)
            self.solid_tile_coords.add((tx, ty))

    def _check_horizon_blockers_removal(self):
        if not self.story_flags.get(self.HORIZON_BLOCKER_FLAG):
            return
        for blocker in [n for n in self.npcs if getattr(n, 'npc_type', '') == 'horizon_guard']:
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
            for flag in step.get('extra_flags', []):
                self.story_flags[flag] = (i <= index)
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
        # Gym NPCs battle under '<id>_rematch' keys while a rematch is up.
        self._refresh_gym_trainers_defeated()
        # Past the credits the Solar Shard is already collected (picking it up
        # would roll the credits again); before them it's back on the ground.
        shard = ('HORIZON_CAVE.world', *self.CELES_TILE)
        if self.story_flags.get('credits_done'):
            self.picked_up_world_items.add(shard)
            self.inventory[self.SOLAR_SHARD_ITEM] = max(1, self.inventory.get(self.SOLAR_SHARD_ITEM, 0))
        else:
            self.picked_up_world_items.discard(shard)

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
        player_starter = self._player_original_starter()
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
        # Gray's Route 1 dict entry for slot 0 (Prowscar) is just a fallback
        # placeholder — the counter-starter override should replace it, not
        # be tacked on as an extra 3rd dino.
        gray.override_replaces_first = True
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

    # ── Gray's second battle — Route 3, right after the Gym 2 badge ──────
    GRAY2_TRIGGER_X = 33
    GRAY2_TRIGGER_Y_RANGE = (-65, -59)  # inclusive, both ends given in the design

    def _check_gray2_route3_rival(self):
        # Checks both flags, not just 'started': jumping straight to this
        # milestone via the sandbox quest-debug menu (Ctrl+Q) sets
        # 'gray_route3_done' directly without ever passing through
        # 'started', which would otherwise leave this re-triggerable.
        if self.story_flags.get('gray_route3_started') or self.story_flags.get('gray_route3_done') or self.cutscene:
            return
        if not self.story_flags.get('gym2_leader_defeated'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        if self.fading or self.message_box.visible:
            return
        tx = self.player.rect.x // config.TILE_SIZE
        ty = self.player.rect.y // config.TILE_SIZE
        if tx != self.GRAY2_TRIGGER_X:
            return
        lo, hi = self.GRAY2_TRIGGER_Y_RANGE
        if not (lo <= ty <= hi):
            return
        self.story_flags['gray_route3_started'] = True
        self._start_gray2_route3_cutscene()

    def _start_gray2_route3_cutscene(self):
        self.player.freeze_in_place()
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE

        sx, sy = px - 7, py
        gray = NPC('gray2', tile_x=sx, tile_y=sy, facing='right',
                   sight_range=0, npc_type='trainer')
        gray.state = 'idle'
        gray.home_tile = (sx, sy)
        gray.home_facing = 'right'
        self.npcs.append(gray)
        self.solid_tile_coords.add((sx, sy))

        # Same counter-starter trick as his first battle (_maybe_add_gray_rival),
        # just the evolved form at level 21 this time.
        player_starter = self._player_original_starter()
        starter_to_gray2 = {
            'Volkit':   ('Anemamace', 21),  # player kept magma → Gray uses evolved aqua counter
            'Corlave':  ('Palidian', 21),   # player kept aqua  → Gray uses evolved earth counter
            'Floravel': ('Tygraflare', 21), # player kept earth → Gray uses evolved magma counter
        }
        gray.override_first_dino = starter_to_gray2.get(player_starter, ('Anemamace', 21))

        self.cutscene = {'phase': 'gray2_approaching', 'npc': gray, 'walk_target': (px - 1, py)}

    def _start_gray2_battle(self, npc):
        self.cutscene = None
        self.start_trainer_battle(npc)

    def _on_gray2_battle_won(self, npc):
        data = TRAINER_DATA.get('gray2', {})
        msgs = self._split_dialogue(*data.get('dialog', {}).get('defeated', [
            "Ha... you're really something else."
        ]), name=data.get('name', 'Gray'))
        def start_walk_away():
            npc.facing = 'left'
            self.cutscene = {
                'phase': 'gray2_walking_away',
                'npc': npc,
                'walk_target': (npc.tile_x - 7, npc.tile_y),
            }
        self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=start_walk_away)

    # ── Sam hands over Surf — waiting outside Gym 2 right after Log's badge ──
    SAM_SURF_TILE = (63, -65)          # one tile left of the Gym 2 exit tile
    SAM_SURF_LEAVE_TILE = (55, -69)    # walks here, then disappears

    def _maybe_add_sam_surf_intro(self):
        if not self.story_flags.get('gym2_leader_defeated'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        sam = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'sam'), None)
        if (self.story_flags.get('sam_surf_intro_done')
                or self.story_flags.get('gym3_leader_defeated')):
            # Quest-menu jump past this scene — don't leave him standing there.
            if sam and not self.cutscene:
                self.solid_tile_coords.discard((sam.tile_x, sam.tile_y))
                self.npcs.remove(sam)
            return
        if sam:
            return
        tx, ty = self.SAM_SURF_TILE
        sam = NPC('sam', tile_x=tx, tile_y=ty, facing='right',
                  sight_range=0, npc_type='story')
        sam.state = 'idle'
        sam.home_tile = (tx, ty)
        sam.home_facing = 'right'
        self.npcs.append(sam)
        self.solid_tile_coords.add((tx, ty))

    def _check_sam_surf_intro(self):
        if self.story_flags.get('sam_surf_intro_done') or self.cutscene:
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        if self.fading or self.entrance_fade_state or self.message_box.visible:
            return
        sam = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'sam'), None)
        if not sam:
            return
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        if abs(px - sam.tile_x) + abs(py - sam.tile_y) > 2:
            return
        self.player.freeze_in_place()
        sam.face_toward_player(self.player)
        dx, dy = sam.tile_x - px, sam.tile_y - py
        if abs(dx) >= abs(dy):
            self._face_player('right' if dx > 0 else 'left')
        else:
            self._face_player('down' if dy > 0 else 'up')
        self.cutscene = {'phase': 'sam_surf_dialogue_wait', 'npc': sam}
        self.message_box.queue_messages(
            self._tag_dialogue('Sam', [
                "Hey nice job on the 2nd gym leader!",
                "My name is Sam and I am the 3rd gym leader so I expect to see you very soon.",
                "My gym is west of here in the most beautiful part of the region, Palm Port.",
                "..Oh and before I forget, I wanted to show you the ability to surf.",
            ]),
            wait_for_input=True,
            on_complete=self._sam_grant_surf)

    def _sam_grant_surf(self):
        self.story_flags['surf_unlocked'] = True
        self.message_box.queue_messages([
            "You now have the ability to surf!",
            "Try interacting with water to surf above it as a new way of traversing the region!",
        ], wait_for_input=True, on_complete=self._sam_surf_farewell)

    def _sam_surf_farewell(self):
        self.message_box.queue_messages(
            self._tag_dialogue('Sam', ["Try it out sometime, you might need it for me, later!"]),
            wait_for_input=True,
            on_complete=self._start_sam_surf_walk_away)

    def _start_sam_surf_walk_away(self):
        if not self.cutscene:
            return
        self.cutscene['phase'] = 'sam_surf_walking_away'
        self.cutscene['walk_target'] = self.SAM_SURF_LEAVE_TILE

    # ── Skyy's Power Plant reveal — free exploration after Gray's 2nd battle,
    # triggers on crossing either of two strips back toward Route 3 ────────
    SKYY_PP_WAYPOINTS = [(2, -61), (2, -57), (-13, -57), (-13, -47), (-19, -47)]
    SKYY_PP_TRIGGER_STRIP_A = (-5, -72, -5, -65)  # x fixed, y range
    SKYY_PP_TRIGGER_STRIP_B = (1, -59, 7, -59)    # y fixed, x range

    def _check_skyy_powerplant_trigger(self):
        if (self.story_flags.get('skyy_pp_started')
                or self.story_flags.get('powerplant_skyy_reveal_done') or self.cutscene):
            return
        if not self.story_flags.get('gray_route3_done'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        if self.fading or self.message_box.visible:
            return
        tx = self.player.rect.x // config.TILE_SIZE
        ty = self.player.rect.y // config.TILE_SIZE
        ax, ay1, _, ay2 = self.SKYY_PP_TRIGGER_STRIP_A
        _, by, bx1, bx2 = self.SKYY_PP_TRIGGER_STRIP_B
        in_strip_a = tx == ax and min(ay1, ay2) <= ty <= max(ay1, ay2)
        in_strip_b = ty == by and min(bx1, bx2) <= tx <= max(bx1, bx2)
        if not (in_strip_a or in_strip_b):
            return
        self.story_flags['skyy_pp_started'] = True
        self._start_skyy_powerplant_cutscene()

    def _start_skyy_powerplant_cutscene(self):
        self.player.freeze_in_place()
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE

        sx, sy = px - 7, py
        skyy = NPC('skyy', tile_x=sx, tile_y=sy, facing='right',
                   sight_range=0, npc_type='story')
        skyy.state = 'idle'
        skyy.home_tile = (sx, sy)
        skyy.home_facing = 'right'
        self.npcs.append(skyy)
        self.solid_tile_coords.add((sx, sy))

        self.cutscene = {'phase': 'skyy_pp_approaching', 'npc': skyy, 'walk_target': (px - 1, py)}

    def _start_skyy_pp_guided_walk(self):
        if not self.cutscene:
            return
        c = self.cutscene
        c['waypoints'] = list(self.SKYY_PP_WAYPOINTS)
        c['phase'] = 'skyy_pp_guided_walk'
        skyy = c['npc']
        tx, ty = c['waypoints'][0]
        dx, dy = tx - skyy.tile_x, ty - skyy.tile_y
        if dx or dy:
            if abs(dx) >= abs(dy) and dx != 0:
                skyy.facing = 'right' if dx > 0 else 'left'
            elif dy != 0:
                skyy.facing = 'down' if dy > 0 else 'up'

    def _update_skyy_pp_guided_walk(self, dt):
        c = self.cutscene
        skyy = c['npc']
        p = self.player
        ts = config.TILE_SIZE

        moving = False
        if skyy.is_moving:
            skyy.anim_timer += dt
            if skyy.anim_timer >= skyy.anim_speed:
                skyy.anim_timer = 0.0
                skyy.anim_frame = (skyy.anim_frame + 1) % 4
            skyy._slide(dt)
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
            self._finish_skyy_pp_guided_walk()
            return
        tx, ty = c['waypoints'][0]
        if (skyy.tile_x, skyy.tile_y) == (tx, ty):
            c['waypoints'].pop(0)
            return

        dx, dy = tx - skyy.tile_x, ty - skyy.tile_y
        if abs(dx) >= abs(dy) and dx != 0:
            sx, sy = (1 if dx > 0 else -1), 0
        elif dy != 0:
            sx, sy = 0, (1 if dy > 0 else -1)
        else:
            return
        prev_tile = (skyy.tile_x, skyy.tile_y)
        nx, ny = skyy.tile_x + sx, skyy.tile_y + sy
        d = {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'down', (0, -1): 'up'}[(sx, sy)]

        # Force-step ignoring solids, like the Route 2.6 guided walk, so this
        # long cross-map lead can't get stuck on scenery.
        self.solid_tile_coords.discard((skyy.tile_x, skyy.tile_y))
        skyy.tile_x, skyy.tile_y = nx, ny
        self.solid_tile_coords.add((nx, ny))
        skyy.facing = d
        skyy.target_x = float(nx * ts)
        skyy.target_y = float(ny * ts)
        skyy.is_moving = True
        skyy.anim_frame = 1
        skyy.anim_timer = 0.0

        # Player follows directly behind, into the tile Skyy just left.
        p.facing = p.direction = d
        p.target_x = float(prev_tile[0] * ts)
        p.target_y = float(prev_tile[1] * ts)
        p.pos_x = float(p.rect.x)
        p.pos_y = float(p.rect.y)
        p.moving = True

    def _finish_skyy_pp_guided_walk(self):
        c = self.cutscene
        skyy = c['npc']
        skyy.face_toward_player(self.player)
        c['phase'] = 'skyy_pp_dialogue_wait'  # reuse the generic no-op dialogue-wait phase
        self.message_box.queue_messages(
            self._tag_dialogue('Skyy', ["Let me heal you before we go battle."]),
            wait_for_input=True,
            on_complete=self._start_skyy_pp_heal_flash
        )

    def _start_skyy_pp_heal_flash(self):
        for dino in self.player_dinos:
            dino['hp'] = dino['max_hp']
        skyy = self.cutscene['npc']
        self.cutscene_flash = {'alpha': 0, 'rising': True, 'count': 0, 'color': (255, 255, 255)}
        self.cutscene = {'phase': 'skyy_pp_heal_flash', 'npc': skyy}

    def _start_pp_grunts_approach(self):
        skyy = self.cutscene['npc']
        # pp_grunt1/pp_grunt2 have already been standing guard, waiting,
        # since gray_route3_done (see _maybe_add_pp_grunts_waiting) — just
        # grab the existing NPCs rather than spawning fresh ones.
        g1 = next(n for n in self.npcs if getattr(n, 'trainer_id', '') == 'pp_grunt1')
        g2 = next(n for n in self.npcs if getattr(n, 'trainer_id', '') == 'pp_grunt2')

        self.cutscene = {
            'phase': 'pp_grunts_approaching',
            'npc': skyy,
            'npc1': g1, 'npc2': g2,
            'walk_target1': (-19, -48),
            'walk_target2': (-18, -48),
        }

    def _update_pp_grunts_approaching(self, dt):
        c = self.cutscene
        npc1, npc2 = c['npc1'], c['npc2']
        all_done = True
        for npc, target in ((npc1, c['walk_target1']), (npc2, c['walk_target2'])):
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
            self._force_step_npc_toward_tile(npc, *target)
        if all_done:
            self.player.facing = self.player.direction = 'up'
            self.player.image = self.player.animations['up'][0]
            c['npc'].facing = 'up'
            c['phase'] = 'skyy_pp_dialogue_wait'  # reuse the generic no-op dialogue-wait phase
            self.message_box.queue_messages(
                self._tag_dialogue('Grunt', ["We won't let you stop us this easy!"]),
                wait_for_input=True,
                on_complete=self._start_skyy_grunts_battle
            )

    def _start_skyy_grunts_battle(self):
        npc1, npc2 = self.cutscene['npc1'], self.cutscene['npc2']
        self.start_double_trainer_battle(npc1, npc2)
        self.is_skyy_battle = True
        self.abby_dinos = [self.create_dino(n, lvl) for n, lvl in
                           self._rando_team([('Luna', 25), ('Netyrant', 25)], "ally:abby_skyy")]

    def _finish_skyy_grunts_battle(self, won):
        npc1 = self.current_trainer_npc
        npc2 = self.current_trainer_npc2
        skyy = self.cutscene['npc'] if self.cutscene else None
        self.is_trainer_battle = False
        self.is_double_battle  = False
        self.is_skyy_battle    = False
        self.enemy_dino2       = None
        self.abby_dinos        = []
        for d in self.player_dinos:
            d['stat_stages'] = {"attack": 0, "defense": 0, "speed": 0}
            d['defending']   = False
        self.pop_to_world()

        self.cutscene = {'phase': 'skyy_pp_dialogue_wait', 'npc': skyy, 'npc1': npc1, 'npc2': npc2}
        self.message_box.queue_messages(
            self._tag_dialogue('Grunt', ["You will see us again soon!"]),
            wait_for_input=True,
            on_complete=self._start_pp_grunts_walk_away
        )

    def _start_pp_grunts_walk_away(self):
        c = self.cutscene
        npc1, npc2 = c['npc1'], c['npc2']
        npc1.facing = 'right'
        npc2.facing = 'right'
        # Right 4 tiles, then up 4.
        c['phase'] = 'pp_grunts_walking_away'
        c['waypoints1'] = [(npc1.tile_x + 6, npc1.tile_y), (npc1.tile_x + 6, npc1.tile_y - 4)]
        c['waypoints2'] = [(npc2.tile_x + 6, npc2.tile_y), (npc2.tile_x + 6, npc2.tile_y - 4)]

    def _update_pp_grunts_walking_away(self, dt):
        c = self.cutscene
        npc1, npc2 = c['npc1'], c['npc2']
        all_done = True
        for npc, wp_key in ((npc1, 'waypoints1'), (npc2, 'waypoints2')):
            if npc.is_moving:
                npc.anim_timer += dt
                if npc.anim_timer >= npc.anim_speed:
                    npc.anim_timer = 0.0
                    npc.anim_frame = (npc.anim_frame + 1) % 4
                npc._slide(dt)
                all_done = False
                continue
            waypoints = c[wp_key]
            if not waypoints:
                continue
            tx, ty = waypoints[0]
            if (npc.tile_x, npc.tile_y) == (tx, ty):
                waypoints.pop(0)
                all_done = False
                continue
            all_done = False
            self._force_step_npc_toward_tile(npc, tx, ty)
        if all_done:
            for npc in (npc1, npc2):
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                if npc in self.npcs:
                    self.npcs.remove(npc)
            self._finish_pp_grunts_walk_away()

    def _finish_pp_grunts_walk_away(self):
        skyy = self.cutscene['npc']
        skyy.face_toward_player(self.player)  # faces the player (right, given their positions)
        self.cutscene = {'phase': 'skyy_pp_dialogue_wait', 'npc': skyy}
        self.message_box.queue_messages(
            self._tag_dialogue('Skyy', ["Go inside and stop them while I handle the grunts out here."]),
            wait_for_input=True,
            on_complete=self._end_skyy_pp_cutscene
        )

    def _end_skyy_pp_cutscene(self):
        skyy = self.cutscene['npc']
        skyy.npc_type = 'guard'
        skyy.block_dialog = ["Go on, I've got this handled!"]
        skyy.state = 'idle'
        self.story_flags['powerplant_skyy_reveal_done'] = True
        self.cutscene = None

    def _maybe_add_powerplant_scene_npcs(self):
        """Re-adds Skyy (now guarding, post-cutscene) and pp_grunt3 blocking
        the Power Plant entrance after a world reload. pp_grunt1/pp_grunt2
        are deliberately NOT included — they're consumed by the double
        battle and walk off for good afterward, so they must never respawn.
        pp_grunt3 stops being re-added once pp_reveal_npcs_ready (removed
        for good at exit-teleport time — see _pp_setup_reveal_npcs). Skyy
        stops being re-added once pp_eclipse_reveal_done — he and Abby leave
        for Cobalt Cave for good at the end of that scene."""
        if not self.story_flags.get('powerplant_skyy_reveal_done'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        if self.cutscene:
            return
        present = {getattr(n, 'trainer_id', '') for n in self.npcs}
        specs = []
        if not self.story_flags.get('pp_reveal_npcs_ready'):
            specs.append(('pp_grunt3', -22, -48, 'right', ["Don't worry about us.", "Get out of here, kid."]))
        if not self.story_flags.get('pp_eclipse_reveal_done'):
            specs.insert(0, ('skyy', -19, -47, 'right', ["Go on, I've got this handled!"]))
        for trainer_id, tx, ty, facing, dialog in specs:
            if trainer_id in present:
                continue
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty, facing=facing,
                      sight_range=0, npc_type='guard')
            npc.state = 'idle'
            npc.home_tile = (tx, ty)
            npc.home_facing = facing
            npc.block_dialog = dialog
            self.npcs.append(npc)
            self.solid_tile_coords.add((tx, ty))

    def _maybe_add_pp_grunts_waiting(self):
        """All 3 Power Plant grunts stand waiting outside as soon as Gray's
        Route 3 rematch is done — visible well before Skyy's own cutscene
        triggers. Stops once the reveal sequence is complete: pp_grunt1/2
        get claimed (and later removed for good) by that sequence, and
        _maybe_add_powerplant_scene_npcs takes over persisting Skyy/grunt3."""
        if not self.story_flags.get('gray_route3_done'):
            return
        if self.story_flags.get('powerplant_skyy_reveal_done'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        # A cutscene being active spans the whole reveal sequence, including
        # the moment pp_grunt1/2 are removed for their final walk-off (which
        # happens before powerplant_skyy_reveal_done actually gets set) —
        # without this guard that gap would look like "they're missing" and
        # this would immediately respawn them back at their starting spot.
        if self.cutscene:
            return
        present = {getattr(n, 'trainer_id', '') for n in self.npcs}
        specs = [
            ('pp_grunt1', -19, -49, 'down',  ["Don't worry about us.", "Get out of here, kid."]),
            ('pp_grunt2', -18, -49, 'down',  ["Don't worry about us.", "Get out of here, kid."]),
            ('pp_grunt3', -22, -48, 'right', ["Don't worry about us.", "Get out of here, kid."]),
        ]
        for trainer_id, tx, ty, facing, dialog in specs:
            if trainer_id in present:
                continue
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty, facing=facing,
                      sight_range=0, npc_type='guard')
            npc.state = 'idle'
            npc.home_tile = (tx, ty)
            npc.home_facing = facing
            npc.block_dialog = dialog
            self.npcs.append(npc)
            self.solid_tile_coords.add((tx, ty))

    # Crossing into the Power Plant entrance itself, once Skyy's reveal has
    # already happened — a one-time bark, not a full cutscene.
    SKYY_DISRUPTION_LINE_X = -15
    SKYY_DISRUPTION_LINE_Y_RANGE = (-49, -46)  # inclusive

    def _check_skyy_disruption_line(self):
        if not self.story_flags.get('powerplant_skyy_reveal_done'):
            return
        if self.story_flags.get('skyy_disruption_line_done') or self.cutscene:
            return
        # Once the grunt pair is actually defeated, the disruption they
        # caused is already stopped — this "we must stop this" bark no
        # longer makes sense and shouldn't fire at all from that point on.
        if self.story_flags.get('pp_grunts2_done'):
            return
        if self.current_world_file != 'LOST_REGION.world':
            return
        if self.fading or self.message_box.visible:
            return
        tx = self.player.rect.x // config.TILE_SIZE
        ty = self.player.rect.y // config.TILE_SIZE
        if tx != self.SKYY_DISRUPTION_LINE_X:
            return
        lo, hi = self.SKYY_DISRUPTION_LINE_Y_RANGE
        if not (lo <= ty <= hi):
            return
        self.story_flags['skyy_disruption_line_done'] = True
        self.message_box.queue_messages(
            self._tag_dialogue('Skyy', ["We must stop this disruption from occuring"]),
            wait_for_input=True
        )

    # ── Generic scripted camera pan — camera_locked keeps update_camera()
    # from re-centering on the player while one of these is in flight. ──
    def _start_camera_pan(self, target_px, target_py, duration, on_complete):
        self.camera_locked = True
        render_w = config.WIDTH // self.zoom
        render_h = config.HEIGHT // self.zoom
        end_x = target_px - render_w // 2
        end_y = target_py - render_h // 2
        min_cx = min(m['x'] for m in self.world_maps)
        min_cy = min(m['y'] for m in self.world_maps)
        max_cx = max(m['x'] + m['width'] for m in self.world_maps) - render_w
        max_cy = max(m['y'] + m['height'] for m in self.world_maps) - render_h
        end_x = max(min_cx, min(end_x, max_cx))
        end_y = max(min_cy, min(end_y, max_cy))
        self.cutscene = {
            'phase': 'camera_pan', 'elapsed': 0.0, 'duration': duration,
            'start': (self.camera_x, self.camera_y), 'end': (end_x, end_y),
            'on_complete': on_complete,
        }

    def _update_camera_pan(self, dt):
        c = self.cutscene
        c['elapsed'] += dt
        t = min(1.0, c['elapsed'] / c['duration'])
        sx, sy = c['start']
        ex, ey = c['end']
        self.camera_x = sx + (ex - sx) * t
        self.camera_y = sy + (ey - sy) * t
        if t >= 1.0:
            cb = c['on_complete']
            self.cutscene = None
            cb()

    # ── Power Plant interior — the "elite" grunt pair confrontation ──────
    PP_GRUNTS2_TRIGGER_X = 34
    PP_GRUNTS2_TRIGGER_Y_RANGE = (-6, -5)  # inclusive
    PP_GRUNTS2_CAM_TARGET = (30, -11)      # tile the camera pans to

    def _check_pp_grunts2_scene(self):
        if self.story_flags.get('pp_grunts2_started') or self.cutscene:
            return
        if self.current_world_file != 'POWERPLANT.world':
            return
        if self.fading or self.message_box.visible:
            return
        tx = self.player.rect.x // config.TILE_SIZE
        ty = self.player.rect.y // config.TILE_SIZE
        if tx != self.PP_GRUNTS2_TRIGGER_X:
            return
        lo, hi = self.PP_GRUNTS2_TRIGGER_Y_RANGE
        if not (lo <= ty <= hi):
            return
        self.story_flags['pp_grunts2_started'] = True
        self._start_pp_grunts2_scene()

    def _start_pp_grunts2_scene(self):
        self.player.freeze_in_place()

        # Both inert (npc_type='story') until the intro finishes — grunt A
        # only turns into a real challengeable 'trainer' once camera control
        # is back with the player (see _end_pp_grunts2_intro), so his sight
        # range can't fire mid-cutscene.
        ga = NPC('pp_grunt_a', tile_x=29, tile_y=-11, facing='right', sight_range=0, npc_type='story')
        gb = NPC('pp_grunt_b', tile_x=30, tile_y=-11, facing='left', sight_range=0, npc_type='story')
        ga.state = gb.state = 'idle'
        ga.home_tile, ga.home_facing = (29, -11), 'right'
        gb.home_tile, gb.home_facing = (30, -11), 'left'
        self.npcs.append(ga)
        self.npcs.append(gb)
        self.solid_tile_coords.add((29, -11))
        self.solid_tile_coords.add((30, -11))

        ts = config.TILE_SIZE
        tx, ty = self.PP_GRUNTS2_CAM_TARGET
        self._start_camera_pan(
            tx * ts + ts // 2, ty * ts + ts // 2, 0.6,
            self._show_pp_grunts2_intro_dialogue
        )

    def _show_pp_grunts2_intro_dialogue(self):
        self.cutscene = {'phase': 'pp_grunts2_wait'}  # generic no-op wait, no npc needed
        self.message_box.queue_messages(
            self._tag_dialogue('Grunt', [
                "Our distraction is working.",
                "It is only a matter of time before the plan commences.",
                "Soon it will be too late to stop.",
            ]),
            wait_for_input=True,
            on_complete=self._pan_camera_back_to_player
        )

    def _pan_camera_back_to_player(self):
        self._start_camera_pan(
            self.player.rect.centerx, self.player.rect.centery, 0.6,
            self._end_pp_grunts2_intro
        )

    def _end_pp_grunts2_intro(self):
        self.camera_locked = False
        self.story_flags['pp_grunts2_intro_done'] = True
        # Grunt A stays inert — his walk-up is triggered by crossing a tile
        # strip (_check_pp_grunt_a_walkup_trigger), not sight range.

    # Crossing this strip (only reachable at x=29/30 — x=28 is a wall, kept
    # in the range anyway since it's harmless) sends grunt A walking up.
    PP_GRUNT_A_TRIGGER_X_RANGE = (28, 30)
    PP_GRUNT_A_TRIGGER_Y = -7

    def _check_pp_grunt_a_walkup_trigger(self):
        if not self.story_flags.get('pp_grunts2_intro_done'):
            return
        if 'pp_grunt_a' in self.defeated_trainers or self.cutscene:
            return
        if self.current_world_file != 'POWERPLANT.world':
            return
        if self.fading or self.message_box.visible:
            return
        tx = self.player.rect.x // config.TILE_SIZE
        ty = self.player.rect.y // config.TILE_SIZE
        if ty != self.PP_GRUNT_A_TRIGGER_Y:
            return
        lo, hi = self.PP_GRUNT_A_TRIGGER_X_RANGE
        if not (lo <= tx <= hi):
            return
        ga = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'pp_grunt_a'), None)
        if not ga:
            return
        self._start_pp_grunt_a_walkup(ga)

    def _start_pp_grunt_a_walkup(self, ga):
        self.player.freeze_in_place()
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        self.cutscene = {'phase': 'pp_grunt_a_walkup', 'npc1': ga, 'walk_target': (px, py - 1)}

    def _update_pp_grunt_a_walkup(self, dt):
        c = self.cutscene
        ga = c['npc1']
        if ga.is_moving:
            ga.anim_timer += dt
            if ga.anim_timer >= ga.anim_speed:
                ga.anim_timer = 0.0
                ga.anim_frame = (ga.anim_frame + 1) % 4
            ga._slide(dt)
            return
        tx, ty = c['walk_target']
        if (ga.tile_x, ga.tile_y) == (tx, ty):
            ga.facing = 'down'
            self.player.facing = self.player.direction = 'up'
            self.player.image = self.player.animations['up'][0]
            self.cutscene = {'phase': 'pp_grunts2_wait'}  # generic no-op wait
            data = TRAINER_DATA.get('pp_grunt_a', {})
            self.message_box.queue_messages(
                self._tag_dialogue('Grunt', data.get('dialog', {}).get('default', [])),
                wait_for_input=True,
                on_complete=lambda: self.start_trainer_battle(ga)
            )
            return
        self._force_step_npc_toward_tile(ga, tx, ty)

    def _on_pp_grunt_a_won(self, npc):
        gb = next(n for n in self.npcs if getattr(n, 'trainer_id', '') == 'pp_grunt_b')
        self._start_pp_grunt_b_walkup(gb)

    def _start_pp_grunt_b_walkup(self, gb):
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        gb.facing = 'left'
        # +1 on x so he doesn't walk onto grunt A's tile, who's still
        # standing right where he finished his own walk-up.
        self.cutscene = {'phase': 'pp_grunt_b_walkup', 'npc1': gb, 'walk_target': (px + 1, py - 1)}

    def _update_pp_grunt_b_walkup(self, dt):
        c = self.cutscene
        gb = c['npc1']
        if gb.is_moving:
            gb.anim_timer += dt
            if gb.anim_timer >= gb.anim_speed:
                gb.anim_timer = 0.0
                gb.anim_frame = (gb.anim_frame + 1) % 4
            gb._slide(dt)
            return
        tx, ty = c['walk_target']
        if (gb.tile_x, gb.tile_y) == (tx, ty):
            gb.facing = 'down'
            self.cutscene = {'phase': 'pp_grunts2_wait'}  # generic no-op wait
            data = TRAINER_DATA.get('pp_grunt_b', {})
            self.message_box.queue_messages(
                self._tag_dialogue('Grunt', data.get('dialog', {}).get('default', [])),
                wait_for_input=True,
                on_complete=lambda: self.start_trainer_battle(gb)
            )
            return
        self._force_step_npc_toward_tile(gb, tx, ty)

    def _on_pp_grunt_b_won(self, npc):
        ga = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'pp_grunt_a'), None)
        gb = npc
        self.message_box.queue_messages(
            self._tag_dialogue('Grunt', ["Well... our job here is done."]),
            wait_for_input=True,
            on_complete=lambda: self._start_pp_grunts2_disappear(ga, gb)
        )

    def _start_pp_grunts2_disappear(self, ga, gb):
        self.cutscene_flash = {'alpha': 0, 'rising': True, 'count': 0, 'color': (0, 0, 0)}
        self.cutscene = {'phase': 'pp_grunts2_flash', 'npc1': ga, 'npc2': gb}

    def _finish_pp_grunts2_disappear(self):
        c = self.cutscene
        for npc in (c['npc1'], c['npc2']):
            if npc is None:
                continue
            self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
            if npc in self.npcs:
                self.npcs.remove(npc)
        self.story_flags['pp_grunts2_done'] = True
        self.cutscene = None

    def _maybe_add_pp_grunts2(self):
        """Persists the grunt pair across a world reload, matching whichever
        stage of the confrontation the player last left it at."""
        if not self.story_flags.get('pp_grunts2_intro_done'):
            return
        if self.story_flags.get('pp_grunts2_done'):
            return
        if self.current_world_file != 'POWERPLANT.world':
            return
        if self.cutscene:
            return
        present = {getattr(n, 'trainer_id', '') for n in self.npcs}
        a_defeated = 'pp_grunt_a' in self.defeated_trainers
        if 'pp_grunt_a' not in present:
            # Inert either way — pre-fight he waits for the walkup trigger;
            # post-fight he's just a defeated bystander with nothing to do.
            ga = NPC('pp_grunt_a', tile_x=29, tile_y=-11, facing='right',
                      sight_range=0, npc_type='story')
            ga.state = 'idle'
            ga.home_tile, ga.home_facing = (29, -11), 'right'
            ga.defeated = a_defeated
            self.npcs.append(ga)
            self.solid_tile_coords.add((29, -11))
        if a_defeated and 'pp_grunt_b' not in present:
            # He was mid-walkup (or about to start it) when we left — spawn
            # him back at his waiting spot and immediately resume.
            gb = NPC('pp_grunt_b', tile_x=30, tile_y=-11, facing='left',
                      sight_range=0, npc_type='story')
            gb.state = 'idle'
            gb.home_tile, gb.home_facing = (30, -11), 'left'
            self.npcs.append(gb)
            self.solid_tile_coords.add((30, -11))
            self._start_pp_grunt_b_walkup(gb)

    # ── Power Plant exit reveal — Abby & Skyy warn of the forced eclipse ──
    def _pp_all_battles_done(self):
        # Only the elite pair inside POWER_PLANT_IN3 (pp_grunt_a/pp_grunt_b,
        # tracked via pp_grunts2_done) gates the Abby reveal now — pp_grunt_c
        # and pp_grunt_d (elsewhere in the building) are optional.
        return self.story_flags.get('pp_grunts2_done', False)

    def _pp_setup_reveal_npcs(self):
        """Remove the outside grunt and get Skyy + Abby standing together
        by the exit — done at exit-teleport time, the instant the player is
        back in the overworld, rather than waiting on the one-more-step
        dialogue delay. That way nothing pops in: the scene already looks
        finished the moment it's visible, and only the dialogue itself
        waits for that extra step (see Player's step-complete block /
        pending_pp_exit_reveal)."""
        if self.story_flags.get('pp_reveal_npcs_ready'):
            return
        self.story_flags['pp_reveal_npcs_ready'] = True

        pp_grunt3 = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'pp_grunt3'), None)
        if pp_grunt3 is not None:
            self.solid_tile_coords.discard((pp_grunt3.tile_x, pp_grunt3.tile_y))
            self.npcs.remove(pp_grunt3)

        present = {getattr(n, 'trainer_id', '') for n in self.npcs}
        if 'skyy' not in present:
            skyy = NPC('skyy', tile_x=-19, tile_y=-47, facing='right', sight_range=0, npc_type='guard')
            skyy.state = 'idle'
            skyy.home_tile, skyy.home_facing = (-19, -47), 'right'
            skyy.block_dialog = ["Go on, I've got this handled!"]
            self.npcs.append(skyy)
            self.solid_tile_coords.add((-19, -47))
        if 'abby' not in present:
            # Already standing right next to Skyy, facing him (he's one
            # tile to her left), instead of walking up to him mid-scene.
            abby = NPC('abby', tile_x=-18, tile_y=-47, facing='left', sight_range=0, npc_type='story')
            abby.state = 'idle'
            abby.home_tile, abby.home_facing = (-18, -47), 'left'
            self.npcs.append(abby)
            self.solid_tile_coords.add((-18, -47))

    def _start_pp_exit_reveal_cutscene(self):
        self.player.freeze_in_place()

        # Both should already be here — _pp_setup_reveal_npcs ran at
        # exit-teleport time. Fallback spawn just in case something
        # unusual happened (e.g. this got reached without going through
        # the normal exit path).
        skyy = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'skyy'), None)
        if skyy is None:
            skyy = NPC('skyy', tile_x=-19, tile_y=-47, facing='right', sight_range=0, npc_type='guard')
            skyy.state = 'idle'
            skyy.home_tile, skyy.home_facing = (-19, -47), 'right'
            skyy.block_dialog = ["Go on, I've got this handled!"]
            self.npcs.append(skyy)
            self.solid_tile_coords.add((-19, -47))
        abby = next((n for n in self.npcs if getattr(n, 'trainer_id', '') == 'abby'), None)
        if abby is None:
            abby = NPC('abby', tile_x=-18, tile_y=-47, facing='left', sight_range=0, npc_type='story')
            abby.state = 'idle'
            abby.home_tile, abby.home_facing = (-18, -47), 'left'
            self.npcs.append(abby)
            self.solid_tile_coords.add((-18, -47))

        self.cutscene = {'phase': 'pp_grunts2_wait'}  # generic no-op wait
        self.message_box.queue_messages(
            self._tag_dialogue('Abby', [
                "Professor Amber just warned me about all of this.",
                "Something big is about to happen, we need to hurry to Cobalt Cave.",
            ]),
            wait_for_input=True,
            on_complete=lambda: self._pp_reveal_skyy_line1(skyy, abby)
        )

    def _pp_reveal_skyy_line1(self, skyy, abby):
        self.message_box.queue_messages(
            self._tag_dialogue('Skyy', ["I should have known this was a trick."]),
            wait_for_input=True,
            on_complete=lambda: self._pp_reveal_start_flares(skyy, abby)
        )

    def _pp_reveal_start_flares(self, skyy, abby):
        # 3 flashes of yellow light, same look as the game's opening eclipse
        # flash (cutscene_flash defaults to a warm yellow when no color is
        # given), just 3 cycles instead of the usual 2.
        self.cutscene_flash = {'alpha': 0, 'rising': True, 'count': 0, 'max_count': 3}
        self.cutscene = {'phase': 'pp_reveal_flares', 'npc1': skyy, 'npc2': abby}

    def _pp_reveal_activate_eclipse(self, skyy, abby):
        self.story_flags['pp_eclipse_active'] = True
        self.start_sky_transition('eclipse', on_swap=self._enable_eclipse_overlay)
        self.cutscene = {'phase': 'pp_grunts2_wait'}
        self.message_box.queue_messages(
            self._tag_dialogue('Skyy', [
                "This solar eclipse is anything but natural.",
                "They seemed to have found a way to conjure it forcibly.",
                "We need to make a move, meet us at the Cave Jet.",
            ]),
            wait_for_input=True,
            on_complete=lambda: self._start_pp_reveal_walk_away(skyy, abby)
        )

    def _start_pp_reveal_walk_away(self, skyy, abby):
        skyy.facing = 'right'
        abby.facing = 'right'
        self.cutscene = {
            'phase': 'pp_reveal_walking_away',
            'npc1': skyy, 'npc2': abby,
            # Right 6 tiles, then up 6 — verified clear of solid tiles.
            'waypoints1': [(skyy.tile_x + 6, skyy.tile_y), (skyy.tile_x + 6, skyy.tile_y - 6)],
            'waypoints2': [(abby.tile_x + 6, abby.tile_y), (abby.tile_x + 6, abby.tile_y - 6)],
        }

    def _update_pp_reveal_walking_away(self, dt):
        c = self.cutscene
        npc1, npc2 = c['npc1'], c['npc2']
        all_done = True
        for npc, wp_key in ((npc1, 'waypoints1'), (npc2, 'waypoints2')):
            if npc.is_moving:
                npc.anim_timer += dt
                if npc.anim_timer >= npc.anim_speed:
                    npc.anim_timer = 0.0
                    npc.anim_frame = (npc.anim_frame + 1) % 4
                npc._slide(dt)
                all_done = False
                continue
            waypoints = c[wp_key]
            if not waypoints:
                continue
            tx, ty = waypoints[0]
            if (npc.tile_x, npc.tile_y) == (tx, ty):
                waypoints.pop(0)
                all_done = False
                continue
            all_done = False
            self._force_step_npc_toward_tile(npc, tx, ty)
        if all_done:
            for npc in (npc1, npc2):
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                if npc in self.npcs:
                    self.npcs.remove(npc)
            self.story_flags['pp_eclipse_reveal_done'] = True
            self.cutscene = None

    # ── Shadow Group Confrontation — Cobalt Cave, right after the Power
    # Plant Takedown. Abby, Skyy and Gray are already standing in
    # COBALT_CAVE1 the moment the player walks in; crossing either of two
    # tiles just inside the room forces the player to walk up to the group
    # before the scene plays. ─────────────────────────────────────────────
    SHADOW_CONFRONTATION_NPC_SPAWNS = {
        'abby': (4, 12, 'right'),
        'gray': (9, 15, 'up'),
        'skyy': (6, 10, 'down'),
    }
    SHADOW_CONFRONTATION_TRIGGER_TILES = {(15, y) for y in range(4, 10)}  # (15,4)..(15,9) inclusive
    SHADOW_CONFRONTATION_PLAYER_TARGET = (9, 12)
    GRAY_SHADOW_HQ_GUARD_POST  = (-33, 41)
    ABBY_SHADOW_HQ_GUARD_POST  = (17, 6)

    def _maybe_add_shadow_confrontation_npcs(self):
        """Keeps Abby/Skyy/Gray persistent across a world reload, matching
        whichever stage of the confrontation the player last left it at."""
        if not self.story_flags.get('pp_eclipse_reveal_done'):
            return
        if self.current_world_file != 'COBALT_CAVE.world':
            return
        if self.cutscene:
            return
        if self.story_flags.get('shadowhq_event_done'):
            return  # Abby and Gray have left the cave for good
        present = {getattr(n, 'trainer_id', '') for n in self.npcs}

        if self.story_flags.get('shadow_confrontation_done'):
            specs = [
                ('gray', *self.GRAY_SHADOW_HQ_GUARD_POST, 'down',
                 ["I'm watching this passage - go help Skyy find Curfeu!"], 'guard'),
                ('abby', *self.ABBY_SHADOW_HQ_GUARD_POST, 'down',
                 ["I've got this entrance covered. Go help Curfeu!"], 'guard'),
            ]
            # Once Skyy has followed the player into Shadow HQ he stays there.
            if not self.story_flags.get('shadowhq_intro_done'):
                specs.append(('skyy', 6, 10, 'down', None, 'story'))
        else:
            # A save/reload mid-scene (cutscene is None here, so it can't be
            # mid-dialogue/mid-walk right now) leaves 'started' stuck True
            # without ever finishing — reset it so the trigger can fire again.
            self.story_flags['shadow_confrontation_started'] = False
            specs = [(tid, tx, ty, facing, None, 'story')
                     for tid, (tx, ty, facing) in self.SHADOW_CONFRONTATION_NPC_SPAWNS.items()]

        for trainer_id, tx, ty, facing, dialog, npc_type in specs:
            if trainer_id in present:
                continue
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty, facing=facing,
                      sight_range=0, npc_type=npc_type)
            npc.state = 'idle'
            npc.home_tile, npc.home_facing = (tx, ty), facing
            if dialog:
                npc.block_dialog = dialog
            self.npcs.append(npc)
            self.solid_tile_coords.add((tx, ty))

    def _check_shadow_confrontation_trigger(self):
        if not self.story_flags.get('pp_eclipse_reveal_done'):
            return
        if self.story_flags.get('shadow_confrontation_started') or self.cutscene:
            return
        if self.current_world_file != 'COBALT_CAVE.world':
            return
        if self.fading or self.message_box.visible:
            return
        tx = self.player.rect.x // config.TILE_SIZE
        ty = self.player.rect.y // config.TILE_SIZE
        if (tx, ty) not in self.SHADOW_CONFRONTATION_TRIGGER_TILES:
            return
        self.story_flags['shadow_confrontation_started'] = True
        self.player.freeze_in_place()
        self.cutscene = {'phase': 'shadow_confrontation_walk',
                          'walk_target': self.SHADOW_CONFRONTATION_PLAYER_TARGET}

    def _update_shadow_confrontation_walk(self, dt):
        if self._force_walk_player_toward(*self.cutscene['walk_target'], dt):
            p = self.player
            p.facing = p.direction = 'left'
            p.image = p.animations['left'][0]
            self._start_shadow_confrontation_dialogue()

    def _force_walk_player_toward(self, tx, ty, dt):
        """Force-walks the player (input fully blocked by self.cutscene
        being set) one tile at a time toward (tx, ty), longer axis first, same
        solid-ignoring approach as every other scripted walk — a stray rock
        along the path must never be able to soft-lock the scene. Returns
        True once the player is standing on the target tile."""
        p = self.player
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
            return False

        px, py = p.rect.x // config.TILE_SIZE, p.rect.y // config.TILE_SIZE
        if (px, py) == (tx, ty):
            return True
        dx, dy = tx - px, ty - py
        if abs(dx) >= abs(dy) and dx != 0:
            sx, sy = (1 if dx > 0 else -1), 0
        else:
            sx, sy = 0, (1 if dy > 0 else -1)
        d = {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'down', (0, -1): 'up'}[(sx, sy)]
        p.facing = p.direction = d
        p.target_x = float((px + sx) * config.TILE_SIZE)
        p.target_y = float((py + sy) * config.TILE_SIZE)
        p.pos_x = float(p.rect.x)
        p.pos_y = float(p.rect.y)
        p.moving = True
        return False

    def _start_shadow_confrontation_dialogue(self):
        self.cutscene = {'phase': 'shadow_confrontation_wait'}  # generic no-op wait
        gray = next(n for n in self.npcs if getattr(n, 'trainer_id', '') == 'gray')
        skyy = next(n for n in self.npcs if getattr(n, 'trainer_id', '') == 'skyy')
        abby = next(n for n in self.npcs if getattr(n, 'trainer_id', '') == 'abby')
        self.message_box.queue_messages(
            self._tag_dialogue('Gray', [
                "I was on my way to challenge gym 3 but then I saw Curfeu battling a bunch of grunts in the cave.",
                "He seemed concerned... and he continued onward into their makeshift base to confront the leaders by himself.",
            ]),
            wait_for_input=True,
            on_complete=lambda: self._shadow_confrontation_skyy_line(gray, skyy, abby)
        )

    def _shadow_confrontation_skyy_line(self, gray, skyy, abby):
        self.message_box.queue_messages(
            self._tag_dialogue('Skyy', [
                "We need to help him, I am sure he can handle the grunts on his own since he is the strongest gym leader of our region.",
                "Though the leaders of the Shadow Group are tough.",
            ]),
            wait_for_input=True,
            on_complete=lambda: self._shadow_confrontation_abby_line(gray, skyy, abby)
        )

    def _shadow_confrontation_abby_line(self, gray, skyy, abby):
        self.message_box.queue_messages(
            self._tag_dialogue('Abby', [
                "I can handle any backups that try to come inside the cave.",
                "Gray, watch the other entrance of the cave while I stay here.",
                "Skyy and Josh, go support Curfeu.",
            ]),
            wait_for_input=True,
            on_complete=lambda: self._start_shadow_confrontation_splitup(gray, skyy, abby)
        )

    def _start_shadow_confrontation_splitup(self, gray, skyy, abby):
        # Skyy stays put — he goes with the player to find Curfeu next,
        # which isn't built yet (no instructions were given for him beyond
        # the dialogue line), so he's left idle here for now.
        gray.facing = 'left'
        self.cutscene = {
            'phase': 'shadow_confrontation_splitup',
            'npc1': gray, 'npc2': abby,
            # Left 4, then down 6 — verified clear of solid tiles — before
            # teleporting to the Route 4 side of the cave.
            'waypoints1': [(gray.tile_x - 4, gray.tile_y), (gray.tile_x - 4, gray.tile_y + 6)],
            'waypoints2': [(17, 6)],
        }

    def _update_shadow_confrontation_splitup(self, dt):
        c = self.cutscene
        gray, abby = c['npc1'], c['npc2']
        all_done = True
        for npc, wp_key in ((gray, 'waypoints1'), (abby, 'waypoints2')):
            if npc.is_moving:
                npc.anim_timer += dt
                if npc.anim_timer >= npc.anim_speed:
                    npc.anim_timer = 0.0
                    npc.anim_frame = (npc.anim_frame + 1) % 4
                npc._slide(dt)
                all_done = False
                continue
            waypoints = c[wp_key]
            if not waypoints:
                continue
            tx, ty = waypoints[0]
            if (npc.tile_x, npc.tile_y) == (tx, ty):
                waypoints.pop(0)
                all_done = False
                continue
            all_done = False
            self._force_step_npc_toward_tile(npc, tx, ty)
        if all_done:
            self._finish_shadow_confrontation(gray, abby)

    def _finish_shadow_confrontation(self, gray, abby):
        # Gray teleports to the Route 4 side of the cave to guard that
        # entrance — he's already walked off camera by this point.
        self.solid_tile_coords.discard((gray.tile_x, gray.tile_y))
        gx, gy = self.GRAY_SHADOW_HQ_GUARD_POST
        gray.tile_x, gray.tile_y = gx, gy
        gray.pos_x = gray.target_x = float(gx * config.TILE_SIZE)
        gray.pos_y = gray.target_y = float(gy * config.TILE_SIZE)
        gray.rect.topleft = (int(gray.pos_x), int(gray.pos_y))
        gray.is_moving = False
        gray.facing = 'down'
        gray.npc_type = 'guard'
        gray.block_dialog = ["I'm watching this passage - go help Skyy find Curfeu!"]
        gray.state = 'idle'
        self.solid_tile_coords.add((gx, gy))

        abby.facing = 'down'
        abby.npc_type = 'guard'
        abby.block_dialog = ["I've got this entrance covered. Go help Curfeu!"]
        abby.state = 'idle'

        self.story_flags['shadow_confrontation_done'] = True
        self.cutscene = None

    # ── Shadow HQ intro — plays the moment the player first walks into
    # SHADOWHQ1 after Abby/Gray split off to guard the cave. Skyy follows the
    # player in and squares up to a grunt, then the camera pans over to
    # Curfeu facing down Vanessa and Emerson. ─────────────────────────────
    SHADOWHQ_NPC_SPAWNS = {
        'hq_grunt_a': (12, 10, 'down'),
        'hq_grunt_b': (9, 10, 'down'),
        'curfeu':     (4, 5, 'up'),
        'vanessa_hq': (5, 4, 'down'),
        'emerson':    (4, 4, 'down'),
        'cobaltion':  (10, 3, 'down'),
    }
    SHADOWHQ_SKYY_START     = (10, 13)  # right beside the player's spawn tile
    SHADOWHQ_SKYY_POST      = (12, 11)  # just below hq_grunt_a
    SHADOWHQ_SKYY_HEAL_SPOT = (8, 13)   # reload fallback for where Skyy healed the player
    SHADOWHQ_CAM_TARGET     = (4, 5)    # Curfeu
    SHADOWHQ_EXIT_TILE      = (10, 13)  # everyone who leaves walks here and vanishes
    COBALTION_TILE          = (10, 3)
    TWILIGHT_SHARD_ITEM     = 'Twilight Lunar Shard'

    # Dark energy waves pulsing out of Cobaltion — they run nonstop (through
    # every battle and re-entry) until the player confronts it directly.
    SHADOWHQ_WAVE_INTERVAL = 0.6     # seconds between new rings
    SHADOWHQ_WAVE_LIFE     = 2.0     # seconds each ring takes to fade out
    SHADOWHQ_WAVE_MAX_R    = 190     # px radius a ring reaches before vanishing
    COBALTION_COLLAPSE_DURATION = 1.5   # whole condense + burst, = screenshake length
    COBALTION_CONDENSE_TIME     = 0.6   # rings collapse inward, then the burst

    # Story flags, in order: shadowhq_intro_done -> hq_grunt_b defeated ->
    # shadowhq_grunt_b_left -> shadowhq_grunts_left -> shadowhq_skyy_heal_done
    # -> vanessa_hq defeated -> shadowhq_leaders_left -> shadowhq_curfeu_done
    # -> cobaltion_waves_collapsed -> shadowhq_event_done.
    # _advance_shadowhq_event starts whichever step is next, so the chain
    # resumes on its own after a battle, a blackout, or a save/reload.

    def _shadowhq_npc(self, trainer_id):
        return next((n for n in self.npcs if getattr(n, 'trainer_id', '') == trainer_id), None)

    def _maybe_add_shadowhq_npcs(self):
        """Keeps the Shadow HQ cast persistent across a world reload, matching
        whichever stage of the event the player last left it at."""
        f = self.story_flags
        if not f.get('shadow_confrontation_done'):
            return
        if self.current_world_file != 'SHADOWHQ1.tmx':
            return
        if f.get('shadowhq_event_done'):
            self._maybe_place_twilight_shard()
            return
        if self.cutscene:
            # Mid-scene, an NPC that already vanished at the exit (while its
            # partner is still walking) must not pop back in before the
            # step's flag gets set.
            return
        present = {getattr(n, 'trainer_id', '') for n in self.npcs}
        specs = []
        for trainer_id, spec in self.SHADOWHQ_NPC_SPAWNS.items():
            if trainer_id == 'hq_grunt_b' and f.get('shadowhq_grunt_b_left'):
                continue
            if trainer_id == 'hq_grunt_a' and f.get('shadowhq_grunts_left'):
                continue
            if trainer_id in ('vanessa_hq', 'emerson') and f.get('shadowhq_leaders_left'):
                continue
            if trainer_id == 'curfeu' and f.get('shadowhq_curfeu_done'):
                continue
            if trainer_id == 'cobaltion' and self._cobaltion_battle:
                continue  # off-map while its battle is in progress
            specs.append((trainer_id, spec))
        if not f.get('shadowhq_curfeu_done'):
            if f.get('shadowhq_skyy_heal_done'):
                specs.append(('skyy', (*self.SHADOWHQ_SKYY_HEAL_SPOT, 'right')))
            elif f.get('shadowhq_intro_done'):
                specs.append(('skyy', (*self.SHADOWHQ_SKYY_POST, 'up')))
            else:
                specs.append(('skyy', (*self.SHADOWHQ_SKYY_START, 'up')))
        for trainer_id, (tx, ty, facing) in specs:
            if trainer_id in present:
                continue
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty, facing=facing,
                      sight_range=0, npc_type='story')
            npc.state = 'idle'
            npc.home_tile, npc.home_facing = (tx, ty), facing
            npc.defeated = trainer_id in self.defeated_trainers
            self.npcs.append(npc)
            self.solid_tile_coords.add((tx, ty))

    def _advance_shadowhq_event(self):
        f = self.story_flags
        if not f.get('shadow_confrontation_done') or f.get('shadowhq_event_done'):
            return
        if self.current_world_file != 'SHADOWHQ1.tmx':
            return
        if self.cutscene or self.message_box.visible or self._cobaltion_battle:
            return
        if self.is_trainer_battle or self.fading or self.state != 'world':
            return
        if self.entrance_fade_state == 'out':
            return  # on the way out of the HQ
        if not f.get('shadowhq_intro_done'):
            self._start_shadowhq_intro()
        elif 'hq_grunt_b' not in self.defeated_trainers:
            self._start_shadowhq_grunt_walkup()
        elif not f.get('shadowhq_grunts_left'):
            self._start_shadowhq_grunts_leave()
        elif not f.get('shadowhq_skyy_heal_done'):
            self._start_shadowhq_skyy_heal()
        elif 'vanessa_hq' not in self.defeated_trainers:
            return  # free roam — the player walks up to Vanessa themselves
        elif not f.get('shadowhq_leaders_left'):
            self._start_shadowhq_leaders_leave()
        elif not f.get('shadowhq_curfeu_done'):
            self._start_shadowhq_curfeu_talk()
        # After that it's on the player to go interact with Cobaltion.

    # ── shared helpers ─────────────────────────────────────────────────

    def _shadowhq_path(self, start, goal, walkers=()):
        """BFS tile path start -> goal (start excluded) around walls, items,
        the player and every NPC not in `walkers`. Falls back to a straight
        force-walk if no path exists, so a scene can never soft-lock."""
        min_tx, min_ty, max_tx, max_ty = self.world_bounds
        walker_tiles = {(n.tile_x, n.tile_y) for n in walkers}
        blocked = (set(self.solid_tile_coords) | self.solid_tiles | set(self.items_on_map)) - walker_tiles
        ts = config.TILE_SIZE
        blocked.add((self.player.rect.x // ts, self.player.rect.y // ts))
        blocked.discard(start)
        prev = {start: None}
        queue = deque([start])
        while queue:
            cur = queue.popleft()
            if cur == goal:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (cur[0] + dx, cur[1] + dy)
                if nxt in prev or nxt in blocked:
                    continue
                if not (min_tx <= nxt[0] < max_tx and min_ty <= nxt[1] < max_ty):
                    continue
                prev[nxt] = cur
                queue.append(nxt)
        if goal not in prev:
            return [goal]
        path = []
        cur = goal
        while cur != start:
            path.append(cur)
            cur = prev[cur]
        return path[::-1]

    def _shadowhq_exit_goal(self):
        ts = config.TILE_SIZE
        player_tile = (self.player.rect.x // ts, self.player.rect.y // ts)
        for tile in (self.SHADOWHQ_EXIT_TILE, (9, 13), (10, 12)):
            if tile != player_tile:
                return tile
        return self.SHADOWHQ_EXIT_TILE

    def _shadowhq_spot_beside_player(self, npc):
        """A free tile next to the player for `npc` to walk up to — never the
        exit tile, since everyone else walks off through it later."""
        ts = config.TILE_SIZE
        px, py = self.player.rect.x // ts, self.player.rect.y // ts
        others = {(n.tile_x, n.tile_y) for n in self.npcs if n is not npc}
        min_tx, min_ty, max_tx, max_ty = self.world_bounds
        for tile in ((px - 1, py), (px, py - 1), (px + 1, py), (px, py + 1)):
            if tile == self.SHADOWHQ_EXIT_TILE:
                continue
            if tile == (npc.tile_x, npc.tile_y):
                return tile
            if (tile in self.solid_tile_coords or tile in self.solid_tiles
                    or tile in others or tile in self.items_on_map):
                continue
            if min_tx <= tile[0] < max_tx and min_ty <= tile[1] < max_ty:
                return tile
        return (npc.tile_x, npc.tile_y)

    def _shadowhq_face_each_other(self, npc):
        npc.anim_frame = 0
        npc.face_toward_player(self.player)
        ts = config.TILE_SIZE
        dx = npc.tile_x - self.player.rect.x // ts
        dy = npc.tile_y - self.player.rect.y // ts
        if abs(dx) >= abs(dy):
            d = 'right' if dx > 0 else 'left'
        else:
            d = 'down' if dy > 0 else 'up'
        self._face_player(d)

    def _shadowhq_walk(self, walkers, then, vanish=False):
        """walkers: [(npc, goal_tile)], all walked at once along BFS paths.
        With vanish=True each NPC disappears the moment it reaches its goal."""
        moving = [n for n, _ in walkers]
        self.cutscene = {
            'phase': 'shadowhq_walk', 'vanish': vanish, 'then': then,
            'walkers': [[npc, self._shadowhq_path((npc.tile_x, npc.tile_y), goal, moving)]
                        for npc, goal in walkers],
        }

    def _update_shadowhq_walk(self, dt):
        c = self.cutscene
        busy = False
        for entry in c['walkers']:
            npc, path = entry
            if npc is None:
                continue
            if npc.is_moving:
                npc.anim_timer += dt
                if npc.anim_timer >= npc.anim_speed:
                    npc.anim_timer = 0.0
                    npc.anim_frame = (npc.anim_frame + 1) % 4
                npc._slide(dt)
                busy = True
                continue
            while path and (npc.tile_x, npc.tile_y) == path[0]:
                path.pop(0)
            if path:
                self._force_step_npc_toward_tile(npc, *path[0])
                busy = True
                continue
            npc.anim_frame = 0
            if c['vanish']:
                self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
                if npc in self.npcs:
                    self.npcs.remove(npc)
                entry[0] = None
        if busy:
            return
        then = c['then']
        self.cutscene = None
        then()

    # ── 1. intro: Skyy squares up, camera visits Curfeu vs. the leaders ──

    def _start_shadowhq_intro(self):
        skyy = self._shadowhq_npc('skyy')
        if not skyy:
            return
        # Starts during the entrance fade-in so the player never gets a single
        # frame of control before the scene takes over — the walk itself
        # only starts once the fade finishes (_update_cutscene is gated on it).
        self.player.freeze_in_place()
        sx, sy = self.SHADOWHQ_SKYY_POST
        self.cutscene = {
            'phase': 'shadowhq_skyy_walk', 'npc1': skyy,
            # Right to x=12, then up to the grunt.
            'waypoints': [(sx, skyy.tile_y), (sx, sy)],
        }

    def _update_shadowhq_skyy_walk(self, dt):
        c = self.cutscene
        skyy = c['npc1']
        if skyy.is_moving:
            skyy.anim_timer += dt
            if skyy.anim_timer >= skyy.anim_speed:
                skyy.anim_timer = 0.0
                skyy.anim_frame = (skyy.anim_frame + 1) % 4
            skyy._slide(dt)
            return
        waypoints = c['waypoints']
        while waypoints and (skyy.tile_x, skyy.tile_y) == waypoints[0]:
            waypoints.pop(0)
        if waypoints:
            self._force_step_npc_toward_tile(skyy, *waypoints[0])
            return
        skyy.anim_frame = 0
        skyy.facing = 'up'
        skyy.home_tile, skyy.home_facing = self.SHADOWHQ_SKYY_POST, 'up'
        ts = config.TILE_SIZE
        tx, ty = self.SHADOWHQ_CAM_TARGET
        self._start_camera_pan(
            tx * ts + ts // 2, ty * ts + ts // 2, 0.8,
            self._shadowhq_curfeu_line
        )

    def _shadowhq_curfeu_line(self):
        self.cutscene = {'phase': 'shadowhq_wait'}  # generic no-op wait
        self.message_box.queue_messages(
            self._tag_dialogue('Curfeu', [
                "I cannot let you take the twilight lunar shard",
                "You do not understand the consequences at stake",
            ]),
            wait_for_input=True,
            on_complete=self._shadowhq_vanessa_line
        )

    def _shadowhq_vanessa_line(self):
        self.message_box.queue_messages(
            self._tag_dialogue('Vanessa', [
                "It is you who does not understand",
                "This will expose the fake power in our region for what it really is",
                "This is nature at its finest and nature will take its course",
            ]),
            wait_for_input=True,
            on_complete=self._shadowhq_emerson_line
        )

    def _shadowhq_emerson_line(self):
        self.message_box.queue_messages(
            self._tag_dialogue('Emerson', ["I will take this from here"]),
            wait_for_input=True,
            on_complete=lambda: self._start_camera_pan(
                self.player.rect.centerx, self.player.rect.centery, 0.8,
                self._end_shadowhq_intro)
        )

    def _end_shadowhq_intro(self):
        self.camera_locked = False
        self.story_flags['shadowhq_intro_done'] = True
        # cutscene is None here — _advance_shadowhq_event starts the grunt
        # walk-up later this same frame.

    # ── 2. grunt (9,10) walks up and battles ─────────────────────────────

    def _start_shadowhq_grunt_walkup(self):
        grunt = self._shadowhq_npc('hq_grunt_b')
        if not grunt:
            return
        self.player.freeze_in_place()
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        self.cutscene = {'phase': 'shadowhq_grunt_walkup', 'npc1': grunt, 'walk_target': (px, py - 1)}

    def _update_shadowhq_grunt_walkup(self, dt):
        c = self.cutscene
        grunt = c['npc1']
        if grunt.is_moving:
            grunt.anim_timer += dt
            if grunt.anim_timer >= grunt.anim_speed:
                grunt.anim_timer = 0.0
                grunt.anim_frame = (grunt.anim_frame + 1) % 4
            grunt._slide(dt)
            return
        tx, ty = c['walk_target']
        if (grunt.tile_x, grunt.tile_y) == (tx, ty):
            grunt.anim_frame = 0
            grunt.facing = 'down'
            self.player.facing = self.player.direction = 'up'
            self.player.image = self.player.animations['up'][0]
            self.cutscene = {'phase': 'shadowhq_wait'}  # generic no-op wait
            data = TRAINER_DATA.get('hq_grunt_b', {})
            self.message_box.queue_messages(
                self._tag_dialogue('Grunt', data.get('dialog', {}).get('default', [])),
                wait_for_input=True,
                on_complete=lambda: self._start_shadowhq_trainer_battle(grunt)
            )
            return
        self._force_step_npc_toward_tile(grunt, tx, ty)

    def _start_shadowhq_trainer_battle(self, npc):
        # Battle state (is_trainer_battle) takes over from here; the
        # cutscene has to be cleared or input stays locked after the win.
        self.cutscene = None
        self.start_trainer_battle(npc)

    # ── 3. both grunts leave ─────────────────────────────────────────────

    def _start_shadowhq_grunts_leave(self):
        self.player.freeze_in_place()
        gb = self._shadowhq_npc('hq_grunt_b')
        if not gb:
            self._shadowhq_grunt_b_gone()
            return
        self._shadowhq_face_each_other(gb)
        self.cutscene = {'phase': 'shadowhq_wait'}
        self.message_box.queue_messages(
            self._tag_dialogue('Grunt', ["My honor has been tainted, I must leave to amend my failure"]),
            wait_for_input=True,
            on_complete=lambda: self._shadowhq_walk(
                [(gb, self._shadowhq_exit_goal())], self._shadowhq_grunt_b_gone, vanish=True)
        )

    def _shadowhq_grunt_b_gone(self):
        self.story_flags['shadowhq_grunt_b_left'] = True
        ga = self._shadowhq_npc('hq_grunt_a')
        if ga:
            self._shadowhq_walk([(ga, self._shadowhq_exit_goal())], self._shadowhq_grunts_gone, vanish=True)
        else:
            self._shadowhq_grunts_gone()

    def _shadowhq_grunts_gone(self):
        self.story_flags['shadowhq_grunts_left'] = True
        self.cutscene = None

    # ── 4. Skyy walks over and heals the party ───────────────────────────

    def _start_shadowhq_skyy_heal(self):
        skyy = self._shadowhq_npc('skyy')
        if not skyy:
            self.story_flags['shadowhq_skyy_heal_done'] = True
            return
        self.player.freeze_in_place()
        goal = self._shadowhq_spot_beside_player(skyy)
        self._shadowhq_walk([(skyy, goal)], lambda: self._shadowhq_skyy_heal_talk(skyy))

    def _shadowhq_skyy_heal_talk(self, skyy):
        self._shadowhq_face_each_other(skyy)
        skyy.home_tile, skyy.home_facing = (skyy.tile_x, skyy.tile_y), skyy.facing
        self.cutscene = {'phase': 'shadowhq_wait'}
        self.message_box.queue_messages(
            self._tag_dialogue('Skyy', [
                "While Curfeu handles the guy, take on Vanessa, this is our chance to prevent a catastrophic event",
                "Let's heal your dinos first",
            ]),
            wait_for_input=True,
            on_complete=self._start_shadowhq_heal_flash
        )

    def _start_shadowhq_heal_flash(self):
        for dino in self.player_dinos:
            dino['hp'] = dino['max_hp']
        # max_count defaults to 2 -> two white flashes.
        self.cutscene_flash = {'alpha': 0, 'rising': True, 'count': 0, 'color': (255, 255, 255)}
        self.cutscene = {'phase': 'shadowhq_heal_flash'}

    def _finish_shadowhq_heal(self):
        self.story_flags['shadowhq_skyy_heal_done'] = True
        self.cutscene = None

    # ── 5. Vanessa battle (started from _interact_story_npc) ─────────────

    def _interact_shadowhq_vanessa(self, npc):
        if not self.story_flags.get('shadowhq_skyy_heal_done'):
            return
        if 'vanessa_hq' in self.defeated_trainers:
            return
        npc.anim_frame = 0
        npc.face_toward_player(self.player)
        data = TRAINER_DATA.get('vanessa_hq', {})
        self.message_box.queue_messages(
            self._tag_dialogue('Vanessa', data.get('dialog', {}).get('default', [])),
            wait_for_input=True,
            on_complete=lambda: self.start_trainer_battle(npc)
        )

    # ── 6. Vanessa + Emerson leave ───────────────────────────────────────

    def _start_shadowhq_leaders_leave(self):
        self.player.freeze_in_place()
        van = self._shadowhq_npc('vanessa_hq')
        em = self._shadowhq_npc('emerson')
        leavers = [n for n in (van, em) if n]

        def walk_off():
            goal = self._shadowhq_exit_goal()
            self._shadowhq_walk([(n, goal) for n in leavers], self._shadowhq_leaders_gone, vanish=True)

        if not van:
            walk_off()
            return
        self._shadowhq_face_each_other(van)
        self.cutscene = {'phase': 'shadowhq_wait'}
        self.message_box.queue_messages(
            self._tag_dialogue('Vanessa', [
                "This is not the last time you will see me, there is much more that you do not know...",
            ]),
            wait_for_input=True,
            on_complete=walk_off
        )

    def _shadowhq_leaders_gone(self):
        self.story_flags['shadowhq_leaders_left'] = True
        self.cutscene = None

    # ── 7. Curfeu thanks the player, then he and Skyy leave ──────────────

    def _start_shadowhq_curfeu_talk(self):
        curfeu = self._shadowhq_npc('curfeu')
        skyy = self._shadowhq_npc('skyy')
        leavers = [n for n in (curfeu, skyy) if n]

        def walk_off():
            goal = self._shadowhq_exit_goal()
            self._shadowhq_walk([(n, goal) for n in leavers], self._shadowhq_curfeu_gone, vanish=True)

        self.player.freeze_in_place()
        if not curfeu:
            walk_off()
            return
        self._shadowhq_face_each_other(curfeu)
        self.cutscene = {'phase': 'shadowhq_wait'}
        self.message_box.queue_messages(
            self._tag_dialogue('Curfeu', [
                "Thank you both for coming to help in such a dire time",
                "But the mission isn't over yet",
                "Jet, go stop the dark energy pulsing from that ancient creature",
                "I can fill you in on whats going on after",
                "Meet me in Palm Port after this is taken care of",
            ]),
            wait_for_input=True,
            on_complete=walk_off
        )

    def _shadowhq_curfeu_gone(self):
        self.story_flags['shadowhq_curfeu_done'] = True
        self.cutscene = None

    # ── 8. Cobaltion: waves collapse, then a wild battle ─────────────────

    def _interact_cobaltion(self, npc):
        f = self.story_flags
        if not f.get('shadowhq_curfeu_done'):
            return  # can't be approached until Curfeu sends the player
        self.player.freeze_in_place()
        self.cutscene = {'phase': 'shadowhq_wait'}
        if f.get('cobaltion_waves_collapsed'):
            # Ran away / blacked out last time — skip straight to the battle.
            self._cobaltion_cry(npc)
            return
        self.message_box.queue_messages(
            ["... the energy is shifting"],
            wait_for_input=True,
            on_complete=lambda: self._start_cobaltion_collapse(npc)
        )

    def _start_cobaltion_collapse(self, npc):
        self.story_flags['cobaltion_waves_collapsed'] = True
        wave_t = self.shadowhq_wave['elapsed'] if self.shadowhq_wave else 0.0
        self.shadowhq_wave = None
        self.screen_shake = self.COBALTION_COLLAPSE_DURATION
        self.cutscene = {'phase': 'cobaltion_collapse', 'npc1': npc,
                         'elapsed': 0.0, 'wave_t': wave_t, 'particles': None}
        self.sfx.play('dark_collapse')

    def _update_cobaltion_collapse(self, dt):
        c = self.cutscene
        c['elapsed'] += dt
        if c['particles'] is None and c['elapsed'] >= self.COBALTION_CONDENSE_TIME:
            c['particles'] = []
            for _ in range(56):
                a = random.uniform(0, 2 * math.pi)
                speed = random.uniform(60, 190)
                c['particles'].append({
                    'x': 0.0, 'y': 0.0,
                    'vx': math.cos(a) * speed, 'vy': math.sin(a) * speed,
                    'size': random.choice((2, 2, 3, 4)),
                    'color': random.choice(((255, 255, 255), (220, 235, 255),
                                            (200, 220, 255), (235, 215, 255))),
                })
        if c['particles']:
            for p in c['particles']:
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vx'] *= 0.97
                p['vy'] *= 0.97
        if c['elapsed'] >= self.COBALTION_COLLAPSE_DURATION:
            self._cobaltion_cry(c['npc1'])

    def _cobaltion_cry(self, npc):
        self.cutscene = {'phase': 'shadowhq_wait'}
        self.sfx.play('dark_roar')
        self.message_box.queue_messages(
            self._tag_dialogue('Cobaltion', ["aaaggyyuyu"]),
            wait_for_input=True,
            on_complete=lambda: self._start_cobaltion_battle(npc)
        )

    def _start_cobaltion_battle(self, npc):
        self.cutscene = None
        # Set before the NPC is removed so _maybe_add_shadowhq_npcs doesn't
        # put it straight back. Resolved in _check_cobaltion_battle_result.
        self._cobaltion_battle = True
        self._wild_caught = False
        self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
        if npc in self.npcs:
            self.npcs.remove(npc)
        self.trigger_encounter(forced_dino='Cobaltion', forced_level=25)

    def _check_cobaltion_battle_result(self):
        """Runs on world frames only; trigger_encounter keeps self.fading True
        right up until the encounter state is pushed, so the first non-fading
        world frame after starting is the one after the battle ended."""
        if not self._cobaltion_battle or self.fading or self.state != 'world':
            return
        self._cobaltion_battle = False
        won = self._wild_caught or (self.enemy_dino and self.enemy_dino.get('hp', 1) <= 0)
        if won:
            self._finish_shadowhq_event()
        # Otherwise (ran / blacked out) Cobaltion is re-added on the next
        # visit by _maybe_add_shadowhq_npcs and can be challenged again.

    def _finish_shadowhq_event(self):
        self.story_flags['shadowhq_event_done'] = True
        # Cobaltion caught/defeated — the forced Power Plant eclipse lifts, back to day
        self.story_flags['pp_eclipse_active'] = False
        self.event_overlay_active = False
        self.is_night = False
        self.day_night_timer = 0.0
        self.dn_transitioning = False
        self.dn_transition_timer = 0.0
        self.player.freeze_in_place()
        self.cutscene = {'phase': 'lunar_shard_reveal', 'tile': self.COBALTION_TILE,
                         't': 0.0, 'landed': False}
        self.sfx.play('lunar_descend')
        # Abby and Gray stop guarding Cobalt Cave — strip them from the
        # cave's saved NPC list so they're gone when the player walks back.
        for entry in self.world_stack:
            if entry.get('file') == 'COBALT_CAVE.world':
                entry['npcs'][:] = [n for n in entry['npcs']
                                    if getattr(n, 'trainer_id', '') not in ('gray', 'abby')]

    def _maybe_place_twilight_shard(self):
        if self.current_world_file != 'SHADOWHQ1.tmx':
            return
        if self.cutscene and self.cutscene.get('phase') == 'lunar_shard_reveal':
            return
        tx, ty = self.COBALTION_TILE
        if (self.current_world_file, tx, ty) in self.picked_up_world_items:
            return
        if (tx, ty) in self.items_on_map:
            return
        self.items_on_map[(tx, ty)] = self.TWILIGHT_SHARD_ITEM
        # Registering it as a map_ball_item makes draw() render only this
        # one image — otherwise draw_map_below() also blits the raw icon for
        # any loose item and the two overlap.
        self.map_ball_items[(tx, ty)] = self.TWILIGHT_SHARD_ITEM
        self.map_ball_images[(tx, ty)] = self._fit_icon_to_tile(
            self.item_icons.get(self.TWILIGHT_SHARD_ITEM))

    def _fit_icon_to_tile(self, icon):
        """Scale an item icon down to fit one tile, keeping its aspect
        ratio, centered on a transparent tile-sized surface."""
        ts = config.TILE_SIZE
        if icon is None:
            return self._ballwhite_img
        r = icon.get_bounding_rect()   # trim transparent padding first
        icon = icon.subsurface(r) if r.width and r.height else icon
        w, h = icon.get_size()
        scale = min(ts / w, ts / h)
        icon = pygame.transform.scale(icon, (max(1, round(w * scale)), max(1, round(h * scale))))
        tile = pygame.Surface((ts, ts), pygame.SRCALPHA)
        tile.blit(icon, ((ts - icon.get_width()) // 2, (ts - icon.get_height()) // 2))
        return tile

    # ── wave / collapse rendering ────────────────────────────────────────

    def _update_shadowhq_wave(self, dt):
        f = self.story_flags
        active = (self.current_world_file == 'SHADOWHQ1.tmx'
                  and f.get('shadow_confrontation_done')
                  and not f.get('cobaltion_waves_collapsed'))
        if not active:
            self.shadowhq_wave = None
            return
        if not self.shadowhq_wave:
            self.shadowhq_wave = {'elapsed': 0.0}
        before = int(self.shadowhq_wave['elapsed'] // self.SHADOWHQ_WAVE_INTERVAL)
        self.shadowhq_wave['elapsed'] += dt
        after = int(self.shadowhq_wave['elapsed'] // self.SHADOWHQ_WAVE_INTERVAL)
        # Throb on every other ring — every ring is too busy to listen to
        if after != before and after % 2 == 0:
            self.sfx.play('dark_pulse')

    def _cobaltion_center(self, cob):
        img = cob._current_image()
        # Sprite grows upward from its tile (see NPC.draw), so its visual
        # center sits above the tile's center.
        return (cob.rect.centerx - self.camera_x,
                cob.rect.bottom - img.get_height() // 2 - self.camera_y)

    def _draw_wave_ring(self, surface, cx, cy, r, alpha, thick, wobble, phase):
        size = int(r + wobble + thick + 8) * 2
        ring = pygame.Surface((size, size), pygame.SRCALPHA)
        mid = size // 2
        # Rippling edge: radius wobbles around the circle and drifts
        # over time, so each ring reads as a wave rather than a hoop.
        pts = []
        for k in range(48):
            a = k / 48 * 2 * math.pi
            rr = r + math.sin(a * 6 + phase) * wobble
            pts.append((mid + math.cos(a) * rr, mid + math.sin(a) * rr))
        pygame.draw.polygon(ring, (40, 0, 60, alpha // 2), pts, thick + 4)
        pygame.draw.polygon(ring, (5, 0, 10, alpha), pts, thick)
        surface.blit(ring, (cx - mid, cy - mid))

    def _draw_cobaltion_aura(self, surface, cob, cx, cy, radius, alpha):
        aura = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(aura, (10, 0, 20, alpha), (radius, radius), radius)
        surface.blit(aura, (cx - radius, cy - radius))
        # Redraw Cobaltion over its own aura so the sprite stays readable.
        cob.draw(surface, self.camera_x, self.camera_y)

    def _draw_shadowhq_wave(self, surface):
        w = self.shadowhq_wave
        cob = self._shadowhq_npc('cobaltion')
        if not w or not cob:
            return
        t = w['elapsed']
        cx, cy = self._cobaltion_center(cob)
        interval, life, max_r = self.SHADOWHQ_WAVE_INTERVAL, self.SHADOWHQ_WAVE_LIFE, self.SHADOWHQ_WAVE_MAX_R
        n = int(t // interval)
        for i in range(n, -1, -1):
            age = t - i * interval
            if age >= life:
                break
            p = age / life
            self._draw_wave_ring(surface, cx, cy,
                                 r=12 + (max_r - 12) * p,
                                 alpha=int(235 * (1.0 - p)),
                                 thick=max(2, int(14 * (1.0 - p))),
                                 wobble=3 + 5 * p, phase=t * 5 + i)
        pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi / interval)
        self._draw_cobaltion_aura(surface, cob, cx, cy, int(26 + 6 * pulse), int(70 + 60 * pulse))

    def _draw_cobaltion_collapse(self, surface):
        c = self.cutscene
        cob = c['npc1']
        cx, cy = self._cobaltion_center(cob)
        e = c['elapsed']
        condense = self.COBALTION_CONDENSE_TIME
        if e < condense:
            # Rings rush inward and darken as the energy condenses.
            p = e / condense
            for k in range(4):
                r = (50 + k * 45) * (1.0 - p) ** 1.5
                if r < 3:
                    continue
                self._draw_wave_ring(surface, cx, cy, r=r,
                                     alpha=int(150 + 100 * p),
                                     thick=max(2, int(6 + 8 * p)),
                                     wobble=4 * (1.0 - p), phase=c['wave_t'] * 5 + e * 20 + k)
            self._draw_cobaltion_aura(surface, cob, cx, cy, int(26 + 10 * p), int(120 + 120 * p))
            return
        # Burst: a quick bright flash, then lighter particles flying out.
        b = (e - condense) / (self.COBALTION_COLLAPSE_DURATION - condense)
        if b < 0.35:
            fp = b / 0.35
            fr = int(10 + 60 * fp)
            flash = pygame.Surface((fr * 2, fr * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash, (235, 240, 255, int(230 * (1.0 - fp))), (fr, fr), fr)
            surface.blit(flash, (cx - fr, cy - fr))
        alpha = int(255 * max(0.0, 1.0 - b))
        for p in c['particles'] or ():
            s = p['size']
            dot = pygame.Surface((s, s), pygame.SRCALPHA)
            dot.fill((*p['color'], alpha))
            surface.blit(dot, (int(cx + p['x']) - s // 2, int(cy + p['y']) - s // 2))

    # ── Surf Shack Preparation — after the Shadow HQ (shadowhq_event_done),
    # Cade, Curfeu, Skyy and Abby are waiting in Palm Port's Surf Shack. The
    # moment the player walks in, Cade greets them, the player is walked up
    # to the group and the whole talk plays with input blocked. Curfeu, Abby
    # and Skyy then leave one after another, Cade gets the last word and
    # leaves too. Flag: surf_shack_prep_done. ──────────────────────────────
    SURF_SHACK_PREP_NPC_SPAWNS = {
        'cade':   (7, 3, 'down'),
        'curfeu': (12, 3, 'left'),
        'skyy':   (7, 5, 'right'),
        'abby':   (12, 5, 'left'),
    }
    SURF_SHACK_PREP_PLAYER_SPOT = (10, 6)
    SURF_SHACK_EXIT_TILE        = (9, 13)  # the door tile — leavers walk here and vanish

    def _maybe_add_surf_shack_prep_npcs(self):
        f = self.story_flags
        if not f.get('shadowhq_event_done') or f.get('surf_shack_prep_done'):
            return
        if self.current_world_file != 'SURF_SHACK.tmx':
            return
        if self._surf_shack_prep_active:
            return  # mid-scene — anyone who already walked out stays gone
        present = {getattr(n, 'trainer_id', '') for n in self.npcs}
        for trainer_id, (tx, ty, facing) in self.SURF_SHACK_PREP_NPC_SPAWNS.items():
            if trainer_id in present:
                continue
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty, facing=facing,
                      sight_range=0, npc_type='story')
            npc.state = 'idle'
            npc.home_tile, npc.home_facing = (tx, ty), facing
            self.npcs.append(npc)
            self.solid_tile_coords.add((tx, ty))

    def _check_surf_shack_prep(self):
        f = self.story_flags
        if not f.get('shadowhq_event_done') or f.get('surf_shack_prep_done'):
            return
        if self.current_world_file != 'SURF_SHACK.tmx' or self._surf_shack_prep_active:
            return
        if self.cutscene or self.message_box.visible or self.fading or self.state != 'world':
            return
        if self.entrance_fade_state == 'out':
            return  # on the way out
        if not self._shadowhq_npc('cade'):
            return
        # Claimed during the entrance fade-in so the player never gets a
        # frame of control; the phase itself only runs once the fade is done.
        self._surf_shack_prep_active = True
        self.player.freeze_in_place()
        self.cutscene = {'phase': 'surf_shack_prep_greet'}

    def _surf_shack_prep_greet(self):
        self.cutscene = {'phase': 'shadowhq_wait'}  # generic no-op wait
        self.message_box.queue_messages(
            self._tag_dialogue('Cade', ["Nice to meet you Jet!"]),
            wait_for_input=True,
            on_complete=lambda: setattr(self, 'cutscene', {'phase': 'surf_shack_prep_walk'})
        )

    def _update_surf_shack_prep_walk(self, dt):
        if not self._force_walk_player_toward(*self.SURF_SHACK_PREP_PLAYER_SPOT, dt):
            return
        p = self.player
        p.facing = p.direction = 'up'
        p.image = p.animations['up'][0]
        self.cutscene = {'phase': 'shadowhq_wait'}
        self._surf_shack_prep_say([
            ('Cade', [
                "Sounds like you are becoming a formidable trainer. Thank you for helping us with the threats in our region",
                "We need to discuss the implications now of the lunar shard you possess",
            ]),
            ('Curfeu', [
                "From ancient lore it seems the shadow group has figured out that the shards have the capability to contact the lunar Dino Deimo...",
                "A celestial known to have conquered our lands eons ago, the marionette of darkness",
            ]),
            ('Abby', [
                "It is all making sense now! The spontaneous eclipses haven't been random at all! They have been using the guardian of the shards to awaken Deimo and use its power",
                "The leader mentioned to Jet and I at the Route 2 solar panels that they see the damage our solar energy has been causing to our region, and want to put an end to it",
                "But why all the solar flares?",
            ]),
            ('Skyy', ["Perhaps the solar dino is fighting back..."]),
            ('Cade', [
                "This lunar shard you hold Jet can signal Deimo and awaken it. It has been told by legend to be a devious entity, capable of total chaos...",
                "protect it at all costs. If in the wrong hands a catastrophic event could occur",
            ]),
            ('Curfeu', [
                "Legend suggests a second lunar shard exists, with both combined allowing to summon Deimo to Earth. Looks like we got lucky that they didn't get both before us.",
                "We will need to remain vigilant. Keep in contact if you see anything suspicious.",
                "I will be checking the ruins for any hints as to where this last shard is located.",
            ]),
            ('Abby', [
                "I will continue researching this group for Professor Amber. I know what they are doing is not right, but their reason may be valid..",
                "The solar energy is beginning to damage our planet, there must be another way...",
            ]),
            ('Skyy', [
                "At this point in time the threat is priority..",
                "maybe this would not have happened if we worked with them to begin with years ago...",
            ]),
            ('Curfeu', [
                "We will revisit this when the final shard is found. I am counting on yall.",
            ]),
        ], then=lambda: self._surf_shack_prep_leave(['curfeu', 'abby', 'skyy'], self._surf_shack_prep_cade_farewell))

    def _surf_shack_prep_say(self, script, then):
        """Plays [(speaker, lines), ...] back to back, then calls `then`."""
        if not script:
            then()
            return
        name, lines = script[0]
        self.message_box.queue_messages(
            self._tag_dialogue(name, lines),
            wait_for_input=True,
            on_complete=lambda: self._surf_shack_prep_say(script[1:], then)
        )

    def _surf_shack_prep_leave(self, trainer_ids, then):
        """Walks each NPC out the door one after another (each vanishes on
        the exit tile before the next sets off), then calls `then`."""
        remaining = [n for n in (self._shadowhq_npc(t) for t in trainer_ids) if n]
        if not remaining:
            then()
            return
        npc = remaining[0]
        rest = [n.trainer_id for n in remaining[1:]]
        self._shadowhq_walk([(npc, self.SURF_SHACK_EXIT_TILE)],
                            lambda: self._surf_shack_prep_leave(rest, then), vanish=True)

    def _surf_shack_prep_cade_farewell(self):
        self.cutscene = {'phase': 'shadowhq_wait'}
        cade = self._shadowhq_npc('cade')
        if cade:
            cade.anim_frame = 0
            cade.face_toward_player(self.player)
        self.message_box.queue_messages(
            self._tag_dialogue('Cade', [
                "Hope we will get a good battle in before all this goes down.",
                "I will be waiting at the Rouge gym for you, be careful on your way up, it is known for getting pretty hot!",
            ]),
            wait_for_input=True,
            on_complete=lambda: self._surf_shack_prep_leave(['cade'], self._finish_surf_shack_prep)
        )

    def _finish_surf_shack_prep(self):
        self.story_flags['surf_shack_prep_done'] = True
        self._surf_shack_prep_active = False
        self.cutscene = None

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

    # --- Gym rematches (data.GYM_REMATCHES) ---
    # Unlocked by beating Sam; must go Skyy -> Log -> Sam. While a gym's
    # rematch is the next one up, its leader and trainers battle with
    # TRAINER_DATA['<id>_rematch'], tracked in defeated_trainers under that key.

    def _gym_rematch_entry(self, trainer_id):
        for i, g in enumerate(GYM_REMATCHES):
            if self.current_world_file == g['world'] and trainer_id in (g['leader'],) + g['guards']:
                return i, g
        return None, None

    def _gym_rematch_active(self, i):
        f = self.story_flags
        if not f.get('gym_rematches_unlocked') or f.get(GYM_REMATCHES[i]['flag']):
            return False
        return all(f.get(g['flag']) for g in GYM_REMATCHES[:i])

    def _trainer_key(self, npc):
        """TRAINER_DATA key this trainer battles as right now."""
        tid = getattr(npc, 'trainer_id', '')
        i, _ = self._gym_rematch_entry(tid)
        if i is not None and self._gym_rematch_active(i):
            return tid + '_rematch'
        return tid

    def _trainer_data(self, npc):
        return TRAINER_DATA.get(self._trainer_key(npc), {})

    def _refresh_gym_trainers_defeated(self):
        """Re-sync defeated state for gym trainers whose battle key just
        changed (a rematch opened up or was finished)."""
        for npc in self.npcs:
            tid = getattr(npc, 'trainer_id', '')
            i, g = self._gym_rematch_entry(tid)
            if i is None:
                continue
            key = self._trainer_key(npc)
            if key == 'skyy':   # the original Skyy fight is tracked by flag
                npc.defeated = bool(self.story_flags.get('gym1_leader_defeated'))
            else:
                npc.defeated = key in self.defeated_trainers
            if not npc.defeated and npc.state == 'done':
                npc.state = 'idle'

    def _gym_rematch_wait_dialog(self, npc):
        """Leader lines when rematches are open but it isn't their turn yet."""
        i, g = self._gym_rematch_entry(npc.trainer_id)
        if (i is None or npc.trainer_id != g['leader'] or not self.story_flags.get('gym_rematches_unlocked')
                or self.story_flags.get(g['flag']) or self._gym_rematch_active(i)):
            return None
        prev = next(p for p in GYM_REMATCHES[:i] if not self.story_flags.get(p['flag']))
        prev_name = TRAINER_DATA[prev['leader']]['name']
        return [f"Rematch? I'd love to, but go take on {prev_name} first.",
                "Come back once you've beaten them again!"]

    def _on_gym_rematch_won(self, i):
        g = GYM_REMATCHES[i]
        self.story_flags[g['flag']] = True
        self._refresh_gym_trainers_defeated()
        data = TRAINER_DATA[g['leader'] + '_rematch']
        self.message_box.queue_messages(
            self._tag_dialogue(data['name'], data['dialog']['defeated']), wait_for_input=True)

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
        self.npcs.append(skyy)
        self.solid_tile_coords.add((tx, ty))
        self._refresh_gym_trainers_defeated()

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

    def _on_sam_gym_won(self):
        self.story_flags['gym3_leader_defeated'] = True
        # (Surf itself is handed over earlier — see _check_sam_surf_intro.)
        if 'aqua' not in self.badges_earned:
            self.badges_earned.append('aqua')

        self.story_flags['gym_rematches_unlocked'] = True

        def _after_badge():
            data = TRAINER_DATA.get('sam', {})
            lines = data.get('dialog', {}).get('defeated', ["..."]) + [
                "Oh hey also I think the other gym leaders might be ready for a rematch with you "
                "now that you've proven to be a real challenger",
                "Just a heads up",
            ]
            dialog = self._tag_dialogue(data.get('name', 'Sam'), lines)
            self.message_box.queue_messages(dialog, wait_for_input=True)

        # Input locked for the first 2s, then any key dismisses it.
        self.badge_earned_screen = BadgeEarnedScreen(
            self, "Aqua Badge",
            os.path.join('assets', 'Badges', 'aqua_badge.png'),
            on_dismiss=_after_badge, min_display=2.0)

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
                    no_collision = bool((layer.properties or {}).get('no_collision'))  # see _load_single_tmx
                    for x, y, gid in layer:
                        if not gid:
                            continue
                        props = tmx.get_tile_properties_by_gid(gid) or {}
                        wpos = (wtx + x, wty + y)
                        if props.get('collision') and not above and not no_collision:
                            solid.add(wpos)
                        if props.get('encounter'):
                            encounter.add(wpos)
                        # `interact` tiles (e.g. Horizon Cave's surf pool) keep
                        # their type too, so water with no encounters is still surfable.
                        if props.get('encounter') or props.get('interact'):
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

            world_maps.append({'tmx': tmx, 'x': wx, 'y': wy, 'width': m['width'], 'height': m['height'],
                               'name': os.path.basename(m['fileName'])})

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

            if self.state == 'launch':
                self.launch_intro.handle_event(event)
                continue

            if self.state == 'title':
                self._ui_sfx(event)
                self.title_screen.handle_event(event, os.path.exists(SAVE_PATH))
                continue

            if self.state == 'intro':
                if self.intro_sequence:
                    self.intro_sequence.handle_event(event)
                continue

            if self.credits:
                self.credits.handle_event(event)   # J/Space held = scroll faster
                continue

            if self.sky_transition:
                continue  # no input while a sky transition card plays

            # Block all input during the heal animation
            if self.heal_anim:
                return

            self._ui_sfx(event)

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

            if self.dino_spawn_picker:
                self._handle_dino_spawn_event(event)
                continue  # not return — keep fast-typed filter letters from this frame

            # Message box is processed first, but not while HP bars or a move
            # animation (moves.py) are still playing in battle
            if self.message_box.visible:
                hp_animating = (
                    'encounter' in self.state_stack and
                    hasattr(self, 'encounter_ui') and
                    self.encounter_ui.is_hp_animating(
                        self.player_dinos[self.active_dino_index], self.enemy_dino)
                )
                if not hp_animating and self.move_anim is None:
                    self.message_box.handle_event(event)
                return

            # Between "gained XP!" and the rest of the win sequence, we're
            # waiting in real time for the XP bar to finish filling (see
            # EncounterUI.is_xp_animating / skip_xp_animation) — nothing
            # else is actionable here, so let a keypress instantly finish
            # it instead of leaving the player watching a silent screen for
            # however long a big XP gain (or several stacked level-ups)
            # takes to animate at its normal pace.
            if (event.type == pygame.KEYDOWN and getattr(self, '_post_xp_callback', None)
                    and hasattr(self, 'encounter_ui')):
                self.encounter_ui.skip_xp_animation()
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
                        # Move Info can be opened from the Party screen either
                        # mid-battle or from the overworld menu — encounter_ui
                        # only exists once a battle has actually started.
                        if hasattr(self, 'encounter_ui'):
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
                elif result == 'target_party':
                    self.pop_state()
                    self.items_screen.reset()
                    self.party_screen.reset()
                    self.push_state('party')

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

            elif self.state == 'objectives':
                self.objectives_screen.handle_event(event)

            elif self.state == 'options':
                self.options_screen.handle_event(event)

            elif self.state == 'rules':
                self.rules_screen.handle_event(event)

            elif self.state == 'controls':
                self.controls_screen.handle_event(event)

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
                # No input of any kind during the intro or a pod throw
                if self.encounter_anim is not None:
                    return
                if self.catch_anim and not self.catch_anim.done:
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
                            self.defeated_trainers.add(self._trainer_key(self.current_trainer_npc))
                        self.is_trainer_battle = False
                        self.pop_to_world()  # safety net: enemy fainted but exit was missed
                    return

                result = self.encounter_ui.handle_input(event, active)

                # Nuzlocke: a route's first new dinos can only be caught
                if self._nuzlocke_catch_only() and (
                        self.encounter_ui.in_fight_menu or result in ('Run', 'Defend')):
                    self.encounter_ui.in_fight_menu = False
                    self.message_box.queue_messages(
                        ["Nuzlocke: this is one of the first new dinos on this route.",
                         "You can't fight or run - try to catch it!"], wait_for_input=True)
                    return

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
            if tile in LAKE_MERIDIAN_PROPHECY_TILES:
                self.message_box.queue_messages([
                    "Light can always overcome darkness",
                    "Even on the darkest day...",
                    "Light finds a way to overwhelm",
                ], wait_for_input=True)
                return True
            if tile in LAKE_MERIDIAN_CELESTIAL_RUIN_TILES:
                self.message_box.queue_messages([
                    "The presence of celestials carries a large toll on the world",
                    "Space-time, sun-moon, light-dark...",
                    "The warping of reality is at risk",
                    "Only balance can restore...",
                ], wait_for_input=True)
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
        self.sfx.play('morph')

    def _finish_gourdecrux_transform(self, dino):
        old_name = dino['name']
        new_name = 'Gourdecrux' if old_name == 'Scarecrux' else 'Scarecrux'
        self._apply_form_swap(dino, new_name)
        self.sfx.play('morph_done')
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
        dino['defense'] = Base_Stats(base_stats['defense'], level, p=DEFENSE_EXP)
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
        if self.portals.warp:  # PORTALS — no menus mid-warp
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
            self.sfx.play('click')
            self.push_state('menu')
        elif (event.key == pygame.K_q and (event.mod & pygame.KMOD_CTRL) and self.sandbox
                and not self.fading and self.entrance_fade_state is None and not cutscene_locking):
            self.quest_debug_screen.reset()
            self.push_state('quest_debug')
        elif event.key == pygame.K_n and (event.mod & pygame.KMOD_CTRL) and self.sandbox:
            target = not self.night_active

            def _force():
                self.force_night = target
                print(f"[DEBUG] force_night -> {self.force_night}")
            self.start_sky_transition('to_night' if target else 'to_day', on_swap=_force)
        elif event.key == pygame.K_e and (event.mod & pygame.KMOD_CTRL) and self.sandbox:
            # Sandbox: toggle eclipse mode (turning it on plays the eclipse card)
            if self.event_overlay_active:
                self.event_overlay_active = False
            else:
                self.start_sky_transition('eclipse', on_swap=self._enable_eclipse_overlay)
        elif (event.key == pygame.K_d and (event.mod & pygame.KMOD_CTRL) and self.sandbox
                and not self.fading and self.entrance_fade_state is None and not cutscene_locking):
            self.dino_spawn_picker = {'filter': '', 'index': 0}
        elif event.key == pygame.K_l and (event.mod & pygame.KMOD_CTRL) and self.sandbox:
            self.lake_aurora.trigger()  # LAKE AURORA — show the lake lights now
        elif event.key == pygame.K_p and (event.mod & pygame.KMOD_CTRL) and self.sandbox:
            # PORTALS — move both celestial portals to new random spots now
            if self.portals.active():
                self.portals.relocate_all()
                print("[DEBUG] portals ->", self.portals.describe())
                self.message_box.queue_messages(
                    [f"[SANDBOX] Portals moved - {self.portals.describe()}"], wait_for_input=True)
            else:
                self.message_box.queue_messages(
                    ["[SANDBOX] The portals appear after the credits.",
                     "Use Ctrl+Q and jump to 18. End Credits first."], wait_for_input=True)
        elif (event.key in (pygame.K_m, pygame.K_u) and (event.mod & pygame.KMOD_CTRL) and self.sandbox
                and not self.fading and self.entrance_fade_state is None and not cutscene_locking):
            # Sandbox: warp to the lunar (M) / solar (U) planet; same key again returns
            entrance_id = 'lunar_planet' if event.key == pygame.K_m else 'solar_planet'
            if self.current_world_file == ENTRANCE_DATA[entrance_id]['world']:
                self.trigger_exit()
            else:
                ts = config.TILE_SIZE
                self.trigger_entrance(entrance_id, self.player.rect.x // ts, self.player.rect.y // ts)
        elif (event.key == pygame.K_j and not self.orb_fx
                and not self.fading and self.entrance_fade_state is None):
            if (self.check_type_chart_interact()
                    or self.check_box_interact()
                    or self.check_lore_interact()
                    or self.interact_with_npc()
                    or self.surf.try_offer()  # SURF (testing)
                    or self.pickup_item()):
                self.sfx.play('click')

    UI_MOVE_KEYS = (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d)
    UI_PRESS_KEYS = (pygame.K_j, pygame.K_SPACE, pygame.K_i, pygame.K_ESCAPE)

    def _ui_sfx(self, event):
        """Menu/dialogue sounds: 'select' for moving a cursor, 'click' for
        confirming/advancing/backing out. Overworld presses play their own
        sounds where something actually happens (interact, open menu)."""
        if event.type != pygame.KEYDOWN or self.coord_input_active or self.dino_spawn_picker:
            return
        k = event.key
        if self.message_box.visible:
            if k in (pygame.K_j, pygame.K_SPACE):
                self.sfx.play('click')
            return
        if self.state == 'world' and not self.yes_no_prompt:
            return
        if self.state == 'encounter' and (self.encounter_anim is not None
                                          or (self.catch_anim and not self.catch_anim.done)
                                          or self.fading):
            return
        if k in self.UI_MOVE_KEYS:
            self.sfx.play('select')
        elif k in self.UI_PRESS_KEYS:
            self.sfx.play('click')

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

    # ── Sandbox Ctrl+D: add any dino to the party at a fixed level ───────
    SANDBOX_SPAWN_LEVEL = 40
    DINO_SPAWN_VISIBLE_ROWS = 8

    def _dino_spawn_matches(self):
        text = self.dino_spawn_picker['filter'].lower()
        names = sorted(DINO_DATA.keys(),
                       key=lambda n: (DINODEX_DATA.get(n, {}).get('number', 999), n))
        return [n for n in names if text in n.lower()]

    def _handle_dino_spawn_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        p = self.dino_spawn_picker
        matches = self._dino_spawn_matches()
        if event.key == pygame.K_ESCAPE:
            self.dino_spawn_picker = None
            return
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if matches:
                self._sandbox_add_dino(matches[min(p['index'], len(matches) - 1)])
            self.dino_spawn_picker = None
            return
        if event.key == pygame.K_UP:
            p['index'] = max(0, p['index'] - 1)
            return
        if event.key == pygame.K_DOWN:
            p['index'] = min(max(0, len(matches) - 1), p['index'] + 1)
            return
        if event.key == pygame.K_BACKSPACE:
            p['filter'] = p['filter'][:-1]
            p['index'] = 0
            return
        ch = event.unicode
        if ch and ch.isalnum() and len(p['filter']) < 20:
            p['filter'] += ch
            p['index'] = 0

    def _sandbox_add_dino(self, name):
        dino = self.create_dino(name, self.SANDBOX_SPAWN_LEVEL)
        dino['caught_ball'] = 'DinoPod'
        self.dinos_seen.add(name)
        if len(self.player_dinos) < self.PARTY_LIMIT:
            self.player_dinos.append(dino)
            where = "your party"
        else:
            self.box_dinos.append(dino)
            where = "your Box (party is full)"
        self.message_box.queue_messages(
            [f"[SANDBOX] Lv.{self.SANDBOX_SPAWN_LEVEL} {name} was added to {where}!"],
            wait_for_input=True)

    def _draw_dino_spawn_picker(self, surface):
        p = self.dino_spawn_picker
        matches = self._dino_spawn_matches()
        font = self.fonts['DIALOGUE']
        small = self.fonts['XS']
        row_h = font.get_height() + 6
        rows = self.DINO_SPAWN_VISIBLE_ROWS
        box = pygame.Rect(0, 0, 460, 70 + rows * row_h + 26)
        box.center = (config.WIDTH // 2, config.HEIGHT // 2)
        pygame.draw.rect(surface, (255, 255, 255), box)
        pygame.draw.rect(surface, (0, 0, 0), box, 3)
        title = font.render(f"Add Lv.{self.SANDBOX_SPAWN_LEVEL} dino: {p['filter']}_", True, (0, 0, 0))
        surface.blit(title, (box.x + 12, box.y + 12))
        idx = min(p['index'], max(0, len(matches) - 1))
        top = max(0, min(idx - rows // 2, len(matches) - rows))
        list_y = box.y + 12 + title.get_height() + 12
        if not matches:
            surface.blit(font.render("No matches", True, (140, 140, 140)), (box.x + 20, list_y))
        for i, name in enumerate(matches[top:top + rows]):
            y = list_y + i * row_h
            if top + i == idx:
                pygame.draw.rect(surface, (200, 200, 255),
                                 (box.x + 8, y - 2, box.width - 16, row_h), border_radius=4)
            num = DINODEX_DATA.get(name, {}).get('number')
            label = f"#{num:03d}  {name}" if num is not None else name
            surface.blit(font.render(label, True, (0, 0, 0)), (box.x + 20, y))
        hint = small.render("Type to filter  |  Up/Down  |  Enter add  |  Esc cancel", True, (90, 90, 90))
        surface.blit(hint, (box.x + 12, box.bottom - hint.get_height() - 8))

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
            # Gray leaves home once the 3 missing dinos are collected; Abby once Gym 1 is beaten
            if trainer_id == 'gray_home' and self.story_flags.get('encounters_unlocked'):
                continue
            if trainer_id == 'abby_home' and self.story_flags.get('gym1_leader_defeated'):
                continue
            if trainer_id == 'josh' and self.story_flags.get('josh_defeated'):
                continue
            if trainer_id == 'celestreeyl' and self.story_flags.get('celestreeyl_done'):
                continue
            if trainer_id in self.LEGENDS and self.story_flags.get(self.LEGENDS[trainer_id]['flag']):
                continue
            npc = NPC(trainer_id, tile_x=tx, tile_y=ty,
                      facing=facing, sight_range=sight, npc_type=npc_type)
            npc.home_tile   = (tx, ty)
            npc.home_facing = facing
            if trainer_id in self.defeated_trainers:
                npc.defeated = True
            self.npcs.append(npc)
            self.solid_tile_coords.add((tx, ty))
        self._refresh_gym_trainers_defeated()

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
            if npc.npc_type in ('guard', 'gym_guard', 'gym2_guard', 'horizon_guard'):
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
            data = self._trainer_data(npc)
            name = data.get('name', 'Trainer')
            wait = self._gym_rematch_wait_dialog(npc)
            if wait:
                self.message_box.queue_messages(self._tag_dialogue(name, wait), wait_for_input=True)
                return True
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
            elif self.story_flags.get('shadow_confrontation_done'):
                self.message_box.queue_messages(
                    self._tag_dialogue('Skyy', [
                        "This battle is crucial, the more we encounter them the more I worry",
                        "Curfeu must know what they are plotting lets help him",
                    ]),
                    wait_for_input=True)
        elif npc.trainer_id == 'mom':
            self._interact_mom(npc)
        elif npc.trainer_id == 'barley':
            self.message_box.queue_messages(self._tag_dialogue('Barley', ["Meeooww"]), wait_for_input=True)
        elif npc.trainer_id == 'solar_lady':
            self.message_box.queue_messages(
                self._tag_dialogue('Kayla', [
                    "Have you seen the damage the solar panels have caused our area?",
                    "Just east of my backyard I can see dead trees from all the energy the panels produce, its quite sad",
                ]),
                wait_for_input=True)
        elif npc.trainer_id == 'horizon_beard':
            self.message_box.queue_messages(
                self._tag_dialogue('Brady', [
                    "I've heard of a place only few select trainers ever get to see...",
                    "They say its a myth but it has to be real, Horizon Cave, just north of here",
                    "I know it exists but the stories they tell from it are out of this world",
                ]),
                wait_for_input=True)
        elif npc.trainer_id == 'dawson':
            self.message_box.queue_messages(
                self._tag_dialogue('Dawson', [
                    "Been noticing more and more of the nature activists gathering around the power plant",
                    "I wonder what stunt they are trying to pull this time",
                ]),
                wait_for_input=True)
        elif npc.trainer_id == 'nick':
            self.message_box.queue_messages(
                self._tag_dialogue('Nick', [
                    "We were better off before the solar panels...",
                    "Our crops have suffered ever since they got installed",
                ]),
                wait_for_input=True)
        elif npc.trainer_id == 'hannah':
            self.message_box.queue_messages(
                self._tag_dialogue('Hannah', [
                    "There is always mystical activity surrounding this lake",
                    "I come here all the time to see the iridescent lights that emit from it occasionally",
                ]),
                wait_for_input=True,
                # turn back to watching the lake once she's done talking
                on_complete=lambda n=npc: setattr(n, 'facing', n.home_facing))
        elif npc.trainer_id == 'tommy':
            self.message_box.queue_messages(
                self._tag_dialogue('Tommy', [
                    "All these solar flares and eclipses began shortly after they installed the solar panels just east of here!",
                ]),
                wait_for_input=True)
        elif npc.trainer_id == 'gracie':
            self.message_box.queue_messages(
                self._tag_dialogue('Gracie', [
                    "Apparently a rare dino lurks in the corn maze only at night",
                    "We only know because one strong lady trainer has it",
                ]),
                wait_for_input=True)
        elif npc.trainer_id == 'carrie':
            self._interact_carrie(npc)
        elif npc.trainer_id == 'vanessa_hq':
            self._interact_shadowhq_vanessa(npc)
        elif npc.trainer_id == 'cobaltion':
            self._interact_cobaltion(npc)
        elif npc.trainer_id == 'farmer':
            self._interact_lantern_farmer(npc)
        elif npc.trainer_id == 'debby':
            self._interact_package_debby(npc)
        elif npc.trainer_id == 'collector':
            self._interact_trade_collector(npc)
        elif npc.trainer_id == 'josh':
            self._interact_josh(npc)
        elif npc.trainer_id == 'celestreeyl':
            self._interact_celestreeyl(npc)
        elif npc.trainer_id in self.LEGENDS:
            self._start_legend_awaken(npc)
        elif npc.trainer_id == 'gray_home':
            self.message_box.queue_messages(
                self._tag_dialogue('Gray', [
                    f"Hey {config.PLAYER_NAME}, I can't wait to start our dino journey, you better be able to keep up with me"]),
                wait_for_input=True)
        elif npc.trainer_id == 'abby_home':
            self.message_box.queue_messages(
                self._tag_dialogue('Abby', [
                    f'Hey {config.PLAYER_NAME}! The professor is having me research some "nature activists" in the area',
                    "Hope you get to enjoy the tasks she gave you!"]),
                wait_for_input=True)
        elif npc.trainer_id == 'scarecrux':
            if self.night_active:
                self.sfx.play('eerie')
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

    # --- Side quest: The Lanterns in the Corn ---
    # Farmer Hollis (ELDER_HOUSE.tmx) tells the player about blue lights in
    # the Corn Maze. Once started, the wisps below appear at night only.
    # Touching one starts a wild Ghoulflame battle; winning/catching clears
    # it. After the first 2 are cleared the 3rd (stronger, by the scarecrow)
    # appears. Clearing it sets lanterns_wisps_done; Hollis then gives the
    # Solar Flare TM. Flags: lanterns_started, lanterns_wisp0..2,
    # lanterns_wisps_done, lanterns_rewarded. No main-story flag is touched.
    LANTERN_WISPS = [(94, -46), (131, -72), (147, -49)]  # last = final wisp
    LANTERN_WISP_LEVELS = (13, 15)
    LANTERN_FINAL_LEVEL = 18
    LANTERN_REWARD = 'TM Solar Flare'

    def _lantern_wisps_active(self):
        f = self.story_flags
        return (self.current_world_file == 'LOST_REGION.world'
                and f.get('lanterns_started') and not f.get('lanterns_wisps_done')
                and self.night_active)

    def _lantern_cleared(self, i):
        return bool(self.story_flags.get(f'lanterns_wisp{i}'))

    def _visible_lantern_wisps(self):
        first = range(len(self.LANTERN_WISPS) - 1)
        remaining = [i for i in first if not self._lantern_cleared(i)]
        if remaining:
            return remaining
        final = len(self.LANTERN_WISPS) - 1
        return [] if self._lantern_cleared(final) else [final]

    def _check_lantern_wisps(self):
        if (not self._lantern_wisps_active() or self._lantern_battle is not None
                or self.fading or self.entrance_fade_state is not None or self.cutscene
                or self.message_box.visible or self.yes_no_prompt or self.player.moving):
            return
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        for i in self._visible_lantern_wisps():
            wx, wy = self.LANTERN_WISPS[i]
            if max(abs(px - wx), abs(py - wy)) <= 1:
                self._start_lantern_wisp(i)
                return

    def _start_lantern_wisp(self, i):
        self.player.freeze_in_place()
        final = i == len(self.LANTERN_WISPS) - 1
        if final:
            lines = ["The last lights swirl together into one blazing blue flame...",
                     "A fierce Ghoulflame bursts out of the corn!"]
            level = self.LANTERN_FINAL_LEVEL
        else:
            lines = ["A pale blue light flickers between the stalks...",
                     "It flared up into a wild Ghoulflame!"]
            level = random.randint(*self.LANTERN_WISP_LEVELS)

        def start_battle():
            self._lantern_battle = i
            self._wild_caught = False
            self.trigger_encounter(forced_dino='Ghoulflame', forced_level=level)
        self.message_box.queue_messages(lines, wait_for_input=True, on_complete=start_battle)

    def _check_lantern_battle_result(self):
        """Same timing trick as _check_cobaltion_battle_result: the first
        non-fading world frame after the battle starts is the one after it ends."""
        if self._lantern_battle is None or self.fading or self.state != 'world':
            return
        i, self._lantern_battle = self._lantern_battle, None
        won = self._wild_caught or (self.enemy_dino and self.enemy_dino.get('hp', 1) <= 0)
        if not won:
            return  # ran / blacked out — the light is still out there
        self.story_flags[f'lanterns_wisp{i}'] = True
        final = len(self.LANTERN_WISPS) - 1
        visible = self._visible_lantern_wisps()
        if i == final:
            self.story_flags['lanterns_wisps_done'] = True
            msgs = ["The last light rises above the corn and fades into the night sky...",
                    "The maze is quiet again.",
                    "Maybe the old farmer in Elder Town would like to hear about this."]
        elif visible == [final]:
            msgs = ["The light winks out...",
                    "The remaining glow drifts deeper into the corn, toward the old scarecrow."]
        else:
            left = len(visible)
            msgs = ["The light winks out...",
                    f"{left} more light{'s' if left != 1 else ''} still drift{'s' if left == 1 else ''} through the corn."]
        self.message_box.queue_messages(msgs, wait_for_input=True)

    def _interact_lantern_farmer(self, npc):
        f = self.story_flags
        if f.get('lanterns_rewarded'):
            lines = ["Ha! Lanterns in the corn... and they were Ghoulflames from the old Chateau all along.",
                     "Thanks for humoring an old man, Jet."]
            self.message_box.queue_messages(self._split_dialogue(*lines, name='Hollis'), wait_for_input=True)
        elif f.get('lanterns_wisps_done'):
            self._give_lantern_reward()
        elif f.get('lanterns_started'):
            cleared = sum(self._lantern_cleared(i) for i in range(len(self.LANTERN_WISPS)))
            lines = ["The lights only drift through the Corn Maze after dark.",
                     f"You've chased off {cleared} of them so far? Keep at it!" if cleared else
                     "Go take a look one night. Just don't get lost in there!"]
            self.message_box.queue_messages(self._split_dialogue(*lines, name='Hollis'), wait_for_input=True)
        else:
            lines = [
                "Oh! A young trainer. Pull up a chair, would ya?",
                "Folks around Elder Town say that on some nights, little blue lights drift through the Corn Maze.",
                "Lanterns in the corn, we used to call 'em. My grandkid swore he followed them once...",
                "...and came back with a strange disc, warm to the touch like a summer afternoon.",
                "Nobody believes an old man's stories anymore. But if you're ever in the maze after dark, keep your eyes open.",
                "Chase every last light out of the corn and come tell me about it. I might have something for you.",
            ]

            def start():
                f['lanterns_started'] = True
            self.message_box.queue_messages(self._split_dialogue(*lines, name='Hollis'),
                                            wait_for_input=True, on_complete=start)

    def _give_lantern_reward(self):
        lines = [
            "You chased off every light in the corn? So they were Ghoulflames all along!",
            "Heh. I've got a confession. That grandkid who followed the lanterns... it was me, sixty years ago.",
            "This is the disc I found that night. I think it belongs with someone who's seen the lights too.",
        ]
        item = self.LANTERN_REWARD

        def give():
            self.story_flags['lanterns_rewarded'] = True
            self.inventory[item] = self.inventory.get(item, 0) + 1
            move = config.ITEMS[item]['tm_move']
            mtype = MOVE_DATA[move]['type'].capitalize()
            self.message_box.queue_messages(
                [f"{config.PLAYER_NAME} received {item}!",
                 *self._split_dialogue(
                     f"A TM can only be used once, and only on a Dino that shares its move's type. "
                     f"{move} is a {mtype} move!", name='Hollis')],
                wait_for_input=True)
        self.message_box.queue_messages(self._split_dialogue(*lines, name='Hollis'),
                                        wait_for_input=True, on_complete=give)

    # --- Side quest: Deliver Package to Mom ---
    # Debby (SIERRA_HOUSE3.tmx, Mom's sister) hands the player a gift for Mom.
    # Talking to Mom while it's active delivers it and gives the TM.
    # Flags: package_started, package_delivered. No main-story flag is touched.
    PACKAGE_REWARD = 'TM Tree Spin'

    def _interact_package_debby(self, npc):
        f = self.story_flags
        if f.get('package_delivered'):
            lines = ["Your mother loved the gift? Oh, I knew she would!",
                     "Take care out there, sweetie."]
            self.message_box.queue_messages(self._split_dialogue(*lines, name='Debby'), wait_for_input=True)
        elif f.get('package_started'):
            lines = ["Did you bring that gift to your mother yet?",
                     "She's back home in Silverleaf Town."]
            self.message_box.queue_messages(self._split_dialogue(*lines, name='Debby'), wait_for_input=True)
        else:
            lines = ["Oh dear give your mother this gift, I have been shopping and saw the perfect decor for her house!",
                     "There is also a little something for you in there as well!"]

            def start():
                f['package_started'] = True
                self.message_box.queue_messages(
                    [f"{config.PLAYER_NAME} received Debby's package!"], wait_for_input=True)
            self.message_box.queue_messages(self._split_dialogue(*lines, name='Debby'),
                                            wait_for_input=True, on_complete=start)

    def _deliver_package_to_mom(self):
        lines = ["Thank you, oh Debby is the best sister!",
                 "Here she left you this for you journey ahead, how sweet of her!"]
        item = self.PACKAGE_REWARD

        def give():
            self.story_flags['package_delivered'] = True
            self.inventory[item] = self.inventory.get(item, 0) + 1
            move = config.ITEMS[item]['tm_move']
            mtype = MOVE_DATA[move]['type'].capitalize()
            self.message_box.queue_messages(
                [f"{config.PLAYER_NAME} received {item}!",
                 *self._split_dialogue(
                     f"A TM can only be used once, and only on a Dino that shares its move's type. "
                     f"{move} is a {mtype} move!", name='Mom')],
                wait_for_input=True)
        self.message_box.queue_messages(self._split_dialogue(*lines, name='Mom'),
                                        wait_for_input=True, on_complete=give)

    # --- Carrie (MAZE_HOUSE.tmx) ---
    # Warns about the corn maze at night and hands over 5 Repels the first
    # time; afterwards just repeats the warning. Flag: carrie_repels_given.
    CARRIE_REPELS = 5

    def _interact_carrie(self, npc):
        if self.story_flags.get('carrie_repels_given'):
            self.message_box.queue_messages(
                self._split_dialogue("This maze is known for anomalies throughout the night",
                                     name='Carrie'),
                wait_for_input=True)
            return
        lines = ["This maze is known for anomalies throughout the night",
                 "Be careful around here past sunset, here take these repels with you!"]

        def give():
            self.story_flags['carrie_repels_given'] = True
            self.inventory['Repel'] = self.inventory.get('Repel', 0) + self.CARRIE_REPELS
            self.message_box.queue_messages(
                [f"{config.PLAYER_NAME} received {self.CARRIE_REPELS} Repels!"], wait_for_input=True)
        self.message_box.queue_messages(self._split_dialogue(*lines, name='Carrie'),
                                        wait_for_input=True, on_complete=give)

    # --- Horizon Cave legendary: Celestreeyl ---
    # Stands at (40,-31) in HORIZON_CAVE.world. Interacting starts a light
    # burst — rays and gathering motes build up, then the screen whites out
    # and fades (white, not black) straight into a wild Lv 40 battle.
    # Catching or defeating it sets celestreeyl_done; running or blacking out
    # leaves it standing there to try again.
    CELES_LEVEL = 40
    CELES_TILE = (40, -31)   # matches config's HORIZON_CAVE.world spawn
    CELES_CHARGE = 1.8    # rays + motes build up, screen shakes
    CELES_FLASH = 0.5     # bright burst grows to a full white-out
    CELES_HOLD = 0.25     # hold on white before the battle loads
    CELES_RAY_COLS = ((255, 236, 160), (255, 255, 255), (170, 255, 170), (200, 190, 255))

    def _interact_celestreeyl(self, npc):
        if self.cutscene or self.fading:
            return
        self.player.freeze_in_place()
        self.screen_shake = self.CELES_CHARGE + self.CELES_FLASH
        self.cutscene = {'phase': 'celestreeyl_awaken', 'npc': npc, 't': 0.0}
        self.sfx.play('celes_awaken')

    def _update_celestreeyl_awaken(self, dt):
        c = self.cutscene
        c['t'] += dt
        if c['t'] < self.CELES_CHARGE + self.CELES_FLASH + self.CELES_HOLD:
            return
        self.cutscene = None
        self._celestreeyl_battle = c['npc']
        self._wild_caught = False
        self.fade_color = (255, 255, 255)
        self.trigger_encounter(forced_dino='Celestreeyl', forced_level=self.CELES_LEVEL)
        self.fade_alpha = 255   # already white — go straight into the battle

    # --- Planet legendaries: Deimo (Lunar Planet) and VY (Solar Planet) ---
    # Each stands on its planet (config.WORLD_NPCS). Interacting plays its
    # awakening (ANIM/legend_awaken.py), which ends fully covered and fades
    # straight into a wild Lv 50 battle. Catching or defeating it sets its
    # flag and it's gone for good; running or blacking out leaves it there.
    LEGENDS = {
        'deimo': {'dino': 'Deimo', 'level': 50, 'flag': 'deimo_done', 'fx': DeimoAwaken,
                  'sound': 'deimo_awaken', 'shake': ((1.9, 0.35),),
                  'after': ["The strings fall slack...", "The lunar sky grows still once more."]},
        'vy':    {'dino': 'VY', 'level': 50, 'flag': 'vy_done', 'fx': VYAwaken,
                  'sound': 'vy_awaken', 'shake': ((1.0, 1.4),),
                  'after': ["VY's blaze settles into a gentle glow...", "The solar winds grow calm."]},
    }

    def _start_legend_awaken(self, npc):
        if self.cutscene or self.fading:
            return
        legend = self.LEGENDS[npc.trainer_id]
        self.player.freeze_in_place()
        self.cutscene = {'phase': 'legend_awaken', 'npc': npc, 't': 0.0, 'fx': legend['fx'](),
                         'shakes': list(legend['shake'])}
        self.sfx.play(legend['sound'])

    def _update_legend_awaken(self, dt):
        c = self.cutscene
        c['t'] += dt
        while c['shakes'] and c['t'] >= c['shakes'][0][0]:
            self.screen_shake = max(self.screen_shake, c['shakes'].pop(0)[1])
        if c['t'] < c['fx'].DURATION:
            return
        npc = c['npc']
        legend = self.LEGENDS[npc.trainer_id]
        self.cutscene = None
        self._legend_battle = (npc, npc.trainer_id)
        self._wild_caught = False
        self.fade_color = c['fx'].END_COLOR
        self.trigger_encounter(forced_dino=legend['dino'], forced_level=legend['level'])
        self.fade_alpha = 255   # already covered by the awakening — straight into the battle

    def _draw_legend_awaken(self, screen):
        c = self.cutscene
        npc = c['npc']
        scale = config.WIDTH / self.render_surface.get_width()
        img = npc._current_image()
        legend_xy = ((npc.rect.centerx - self.camera_x) * scale,
                     (npc.rect.bottom - img.get_height() * 0.55 - self.camera_y) * scale)
        player_xy = ((self.player.rect.centerx - self.camera_x) * scale,
                     (self.player.rect.centery - self.camera_y) * scale)
        # the legendary's own sprite, placed exactly as NPC.draw puts it
        if c.get('sprite_src') is not img:
            c['sprite_src'] = img
            c['sprite_img'] = pygame.transform.scale(
                img, (int(img.get_width() * scale), int(img.get_height() * scale)))
        ts = config.TILE_SIZE
        topleft = ((npc.rect.x - self.camera_x - (img.get_width() - ts) // 2) * scale,
                   (npc.rect.y - self.camera_y - (img.get_height() - ts)) * scale)
        c['fx'].draw(screen, legend_xy, player_xy, c['t'], sprite=(c['sprite_img'], topleft))

    def _check_legend_battle_result(self):
        """Same timing trick as _check_celestreeyl_battle_result."""
        if self._legend_battle is None or self.fading or self.state != 'world':
            return
        (npc, key), self._legend_battle = self._legend_battle, None
        won = self._wild_caught or (self.enemy_dino and self.enemy_dino.get('hp', 1) <= 0)
        if not won:
            return
        legend = self.LEGENDS[key]
        self.story_flags[legend['flag']] = True
        self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
        if npc in self.npcs:
            self.npcs.remove(npc)
        self.message_box.queue_messages(legend['after'], wait_for_input=True)

    def _check_celestreeyl_battle_result(self):
        """Same timing trick as _check_cobaltion_battle_result."""
        if self._celestreeyl_battle is None or self.fading or self.state != 'world':
            return
        npc, self._celestreeyl_battle = self._celestreeyl_battle, None
        won = self._wild_caught or (self.enemy_dino and self.enemy_dino.get('hp', 1) <= 0)
        if not won:
            return
        self.story_flags['celestreeyl_done'] = True
        self.solid_tile_coords.discard((npc.tile_x, npc.tile_y))
        if npc in self.npcs:
            self.npcs.remove(npc)
        self.player.freeze_in_place()
        self.cutscene = {'phase': 'solar_shard_reveal', 'tile': (npc.tile_x, npc.tile_y),
                         't': 0.0, 'landed': False}
        self.sfx.play('solar_shard')

    # --- Celestial Solar Shard reveal ---
    # Right after Celestreeyl is caught/defeated: the leftover light fades,
    # prismatic motes spiral into the spot where it stood, the shard drifts
    # down spinning, lands in a rainbow burst, and is left as a pickup.
    SOLAR_SHARD_ITEM    = 'Celestial Solar Shard'
    SOLAR_FADE          = 0.7    # white from the battle's end fades away
    SOLAR_DESCEND_START = 0.9
    SOLAR_LAND          = 2.7    # shard touches down -> burst
    SOLAR_END           = 3.7
    SOLAR_DROP_TILES    = 3      # how far above its spot the shard appears
    SOLAR_COLS = ((255, 120, 120), (255, 200, 110), (255, 250, 140), (140, 255, 150),
                  (120, 220, 255), (150, 150, 255), (230, 140, 255))

    def _update_solar_shard_reveal(self, dt):
        c = self.cutscene
        c['t'] += dt
        if not c['landed'] and c['t'] >= self.SOLAR_LAND:
            c['landed'] = True
            self.screen_shake = 0.25
            self.sfx.play('shard_land')
        if c['t'] < self.SOLAR_END:
            return
        self.cutscene = None
        self._maybe_place_solar_shard()
        self.message_box.queue_messages(
            ['Celestreeyl left something behind...',
             f'A {self.SOLAR_SHARD_ITEM} glimmers where it stood!'],
            wait_for_input=True)

    def _maybe_place_solar_shard(self):
        if self.current_world_file != 'HORIZON_CAVE.world' or not self.story_flags.get('celestreeyl_done'):
            return
        if self.cutscene and self.cutscene.get('phase') == 'solar_shard_reveal':
            return
        tx, ty = self.CELES_TILE
        if (self.current_world_file, tx, ty) in self.picked_up_world_items or (tx, ty) in self.items_on_map:
            return
        self.items_on_map[(tx, ty)] = self.SOLAR_SHARD_ITEM
        self.map_ball_items[(tx, ty)] = self.SOLAR_SHARD_ITEM
        self.map_ball_images[(tx, ty)] = self._fit_icon_to_tile(
            self.item_icons.get(self.SOLAR_SHARD_ITEM))

    def _draw_solar_shard_reveal(self, screen):
        c = self.cutscene
        t = c['t']
        W, H = config.WIDTH, config.HEIGHT
        scale = W / self.render_surface.get_width()
        ts = config.TILE_SIZE
        tx, ty = c['tile']
        cx = (tx * ts + ts / 2 - self.camera_x) * scale
        cy = (ty * ts + ts / 2 - self.camera_y) * scale

        def add(col, k):
            return tuple(max(0, min(255, int(v * k))) for v in col)

        build = max(0.0, min(1.0, (t - 0.3) / (self.SOLAR_LAND - 0.3)))
        after = max(0.0, (t - self.SOLAR_LAND) / (self.SOLAR_END - self.SOLAR_LAND))
        glow_k = build * (1 - after)

        # dim the snow a little so the light and colours read
        dim = self.__dict__.get('_celes_dim')
        if dim is None or dim.get_size() != (W, H):
            dim = self._celes_dim = pygame.Surface((W, H))
            dim.fill((6, 4, 18))
        dim.set_alpha(int(150 * glow_k))
        screen.blit(dim, (0, 0))

        fx = self.__dict__.get('_solar_fx')
        if fx is None or fx.get_size() != (W, H):
            fx = self._solar_fx = pygame.Surface((W, H))
        fx.fill((0, 0, 0))

        # thin rainbow rays slowly turning around the spot
        n = 14
        length = (30 + 90 * build) * scale
        for i in range(n):
            a = i * math.tau / n - t * 0.8
            half = 0.04 + 0.02 * (i % 2)
            k = glow_k * 0.45 * (0.7 + 0.3 * math.sin(t * 7 + i * 1.3))
            pts = [(cx, cy),
                   (cx + math.cos(a - half) * length, cy + math.sin(a - half) * length),
                   (cx + math.cos(a + half) * length, cy + math.sin(a + half) * length)]
            pygame.draw.polygon(fx, add(self.SOLAR_COLS[i % len(self.SOLAR_COLS)], k), pts)

        # prismatic motes spiralling inward
        rng = random.Random(4321)
        for _ in range(36):
            ang0 = rng.uniform(0, math.tau)
            q = (t * rng.uniform(0.5, 0.9) + rng.random()) % 1.0
            d = (1 - q) * rng.uniform(70, 150) * scale
            ang = ang0 + q * 2.2
            x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d
            pygame.draw.circle(fx, add(rng.choice(self.SOLAR_COLS), glow_k * (0.5 + q)),
                               (int(x), int(y)), max(1, int((1 + 1.5 * q) * scale)))

        # soft green-white glow pooling on the ground
        core = (8 + 18 * build) * scale
        for k in range(10, 0, -1):
            f = k / 10
            pygame.draw.circle(fx, add((200, 255, 215), glow_k * (1 - f) ** 1.5 * 1.4),
                               (int(cx), int(cy)), max(1, int(core * f)))

        # landing burst: expanding rainbow rings + star sparkles
        if c['landed']:
            for j, col in enumerate(self.SOLAR_COLS):
                r = (6 + 110 * after + j * 3) * scale
                pygame.draw.circle(fx, add(col, 1.0 - after), (int(cx), int(cy)),
                                   int(r), max(1, int(1.5 * scale)))
            srng = random.Random(99)
            for _ in range(14):
                ang = srng.uniform(0, math.tau)
                d = (10 + srng.uniform(30, 70) * (after ** 0.6)) * scale
                x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d
                s = (1 - after) * 4 * scale
                col = add(srng.choice(self.SOLAR_COLS), 1.0 - after)
                pygame.draw.line(fx, col, (x - s, y), (x + s, y), max(1, int(scale / 2)))
                pygame.draw.line(fx, col, (x, y - s), (x, y + s), max(1, int(scale / 2)))
        screen.blit(fx, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # the shard itself: drifts down spinning, then rests and pulses
        icon = self.item_icons.get(self.SOLAR_SHARD_ITEM)
        if icon is not None and t >= self.SOLAR_DESCEND_START:
            tile_img = self._fit_icon_to_tile(icon)
            size = int(ts * scale)
            if c['landed']:
                drop, spin = 0.0, 1.0
            else:
                p = (t - self.SOLAR_DESCEND_START) / (self.SOLAR_LAND - self.SOLAR_DESCEND_START)
                ease = 1 - (1 - p) ** 2
                drop = (1 - ease) * self.SOLAR_DROP_TILES * ts * scale + math.sin(t * 6) * 2 * scale * (1 - p)
                spin = abs(math.cos((1 - ease) * math.tau * 2.5))
            w = max(1, int(size * max(0.08, spin)))
            img = pygame.transform.scale(tile_img, (w, size))
            alpha = int(255 * min(1.0, (t - self.SOLAR_DESCEND_START) / 0.3))
            img.set_alpha(alpha)
            screen.blit(img, (int(cx - w / 2), int(cy - size / 2 - drop)))

        # leftover white from the battle melting away, then a flash on landing
        white_a = 0
        if t < self.SOLAR_FADE:
            white_a = 255 * (1 - t / self.SOLAR_FADE) ** 1.5
        elif c['landed'] and after < 0.25:
            white_a = 150 * (1 - after / 0.25)
        if white_a > 0:
            white = self.__dict__.get('_celes_white')
            if white is None or white.get_size() != (W, H):
                white = self._celes_white = pygame.Surface((W, H))
                white.fill((255, 255, 255))
            white.set_alpha(int(white_a))
            screen.blit(white, (0, 0))

    # --- Twilight Lunar Shard reveal ---
    # Right after Cobaltion is caught/defeated: night settles over the HQ,
    # a crescent moon rises over the spot, cold motes spiral in, the shard
    # drifts down spinning, lands in a silver-violet burst, and is left as
    # a pickup. Same beats as the solar reveal, in a moonlit palette.
    LUNAR_FADE_IN       = 0.6    # night veil settles in
    LUNAR_DESCEND_START = 0.9
    LUNAR_LAND          = 2.7
    LUNAR_END           = 3.7
    LUNAR_DROP_TILES    = 3
    LUNAR_COLS = ((150, 170, 255), (205, 215, 255), (120, 90, 220), (180, 140, 255),
                  (235, 238, 255), (90, 120, 220), (160, 110, 240))

    def _update_lunar_shard_reveal(self, dt):
        c = self.cutscene
        c['t'] += dt
        if not c['landed'] and c['t'] >= self.LUNAR_LAND:
            c['landed'] = True
            self.screen_shake = 0.25
            self.sfx.play('lunar_shard')
        if c['t'] < self.LUNAR_END:
            return
        self.cutscene = None
        self._maybe_place_twilight_shard()
        self.message_box.queue_messages(
            ['Cobaltion left something behind...',
             f'A {self.TWILIGHT_SHARD_ITEM} shimmers where it stood!'],
            wait_for_input=True)

    def _draw_lunar_shard_reveal(self, screen):
        c = self.cutscene
        t = c['t']
        W, H = config.WIDTH, config.HEIGHT
        scale = W / self.render_surface.get_width()
        ts = config.TILE_SIZE
        tx, ty = c['tile']
        cx = (tx * ts + ts / 2 - self.camera_x) * scale
        cy = (ty * ts + ts / 2 - self.camera_y) * scale

        def add(col, k):
            return tuple(max(0, min(255, int(v * k))) for v in col)

        build = max(0.0, min(1.0, (t - 0.3) / (self.LUNAR_LAND - 0.3)))
        after = max(0.0, (t - self.LUNAR_LAND) / (self.LUNAR_END - self.LUNAR_LAND))
        glow_k = build * (1 - after)

        # a deep night-blue veil settles over the room
        veil_k = min(1.0, t / self.LUNAR_FADE_IN) * (1 - after)
        dim = self.__dict__.get('_lunar_dim')
        if dim is None or dim.get_size() != (W, H):
            dim = self._lunar_dim = pygame.Surface((W, H))
            dim.fill((4, 6, 26))
        dim.set_alpha(int(175 * veil_k))
        screen.blit(dim, (0, 0))

        fx = self.__dict__.get('_lunar_fx')
        if fx is None or fx.get_size() != (W, H):
            fx = self._lunar_fx = pygame.Surface((W, H))
        fx.fill((0, 0, 0))

        # a pale crescent moon rising above the spot
        moon_r = 20 * scale
        mx, my = cx, cy - (60 + 20 * build) * scale
        for k in range(6, 0, -1):   # soft halo
            f = k / 6
            pygame.draw.circle(fx, add((120, 130, 230), glow_k * (1 - f) * 0.6),
                               (int(mx), int(my)), int(moon_r * (1 + f)))
        # crescent on its own layer (moon minus an offset disc), then added
        # over the halo so the halo still shows through the hollow
        side = int(moon_r * 2) + 4
        moon = pygame.Surface((side, side))
        m = side // 2
        pygame.draw.circle(moon, add((225, 230, 255), glow_k), (m, m), int(moon_r))
        pygame.draw.circle(moon, (0, 0, 0), (int(m + moon_r * 0.45), int(m - moon_r * 0.2)),
                           int(moon_r * 0.9))
        fx.blit(moon, (int(mx) - m, int(my) - m), special_flags=pygame.BLEND_RGB_ADD)

        # slender silver-violet rays turning the opposite way to the sun's
        n = 12
        length = (30 + 80 * build) * scale
        for i in range(n):
            a = i * math.tau / n + t * 0.5
            half = 0.03 + 0.02 * (i % 2)
            k = glow_k * 0.4 * (0.7 + 0.3 * math.sin(t * 4 + i * 1.7))
            pts = [(cx, cy),
                   (cx + math.cos(a - half) * length, cy + math.sin(a - half) * length),
                   (cx + math.cos(a + half) * length, cy + math.sin(a + half) * length)]
            pygame.draw.polygon(fx, add(self.LUNAR_COLS[i % len(self.LUNAR_COLS)], k), pts)

        # cold motes spiralling inward, twinkling as they go
        rng = random.Random(8642)
        for _ in range(40):
            ang0 = rng.uniform(0, math.tau)
            q = (t * rng.uniform(0.4, 0.8) + rng.random()) % 1.0
            d = (1 - q) * rng.uniform(70, 160) * scale
            ang = ang0 - q * 2.6
            x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d
            tw = 0.6 + 0.4 * math.sin(t * 9 + ang0 * 5)
            pygame.draw.circle(fx, add(rng.choice(self.LUNAR_COLS), glow_k * (0.4 + q) * tw),
                               (int(x), int(y)), max(1, int((1 + 1.5 * q) * scale)))

        # moonlight pooling on the floor
        core = (8 + 18 * build) * scale
        for k in range(10, 0, -1):
            f = k / 10
            pygame.draw.circle(fx, add((170, 185, 255), glow_k * (1 - f) ** 1.5 * 1.3),
                               (int(cx), int(cy)), max(1, int(core * f)))

        # landing burst: silver-violet rings + four-point star glints
        if c['landed']:
            for j, col in enumerate(self.LUNAR_COLS):
                r = (6 + 110 * after + j * 3) * scale
                pygame.draw.circle(fx, add(col, 1.0 - after), (int(cx), int(cy)),
                                   int(r), max(1, int(1.5 * scale)))
            srng = random.Random(77)
            for _ in range(14):
                ang = srng.uniform(0, math.tau)
                d = (10 + srng.uniform(30, 70) * (after ** 0.6)) * scale
                x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d
                s = (1 - after) * 4 * scale
                col = add(srng.choice(self.LUNAR_COLS), 1.0 - after)
                pygame.draw.line(fx, col, (x - s, y), (x + s, y), max(1, int(scale / 2)))
                pygame.draw.line(fx, col, (x, y - s), (x, y + s), max(1, int(scale / 2)))
        screen.blit(fx, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # the shard itself: drifts down spinning, then rests
        icon = self.item_icons.get(self.TWILIGHT_SHARD_ITEM)
        if icon is not None and t >= self.LUNAR_DESCEND_START:
            tile_img = self._fit_icon_to_tile(icon)
            size = int(ts * scale)
            if c['landed']:
                drop, spin = 0.0, 1.0
            else:
                p = (t - self.LUNAR_DESCEND_START) / (self.LUNAR_LAND - self.LUNAR_DESCEND_START)
                ease = 1 - (1 - p) ** 2
                drop = (1 - ease) * self.LUNAR_DROP_TILES * ts * scale + math.sin(t * 5) * 2 * scale * (1 - p)
                spin = abs(math.cos((1 - ease) * math.tau * 2.5))
            w = max(1, int(size * max(0.08, spin)))
            img = pygame.transform.scale(tile_img, (w, size))
            img.set_alpha(int(255 * min(1.0, (t - self.LUNAR_DESCEND_START) / 0.3)))
            screen.blit(img, (int(cx - w / 2), int(cy - size / 2 - drop)))

        # pale lavender flash on landing
        if c['landed'] and after < 0.25:
            flash = self.__dict__.get('_lunar_flash')
            if flash is None or flash.get_size() != (W, H):
                flash = self._lunar_flash = pygame.Surface((W, H))
                flash.fill((210, 205, 255))
            flash.set_alpha(int(140 * (1 - after / 0.25)))
            screen.blit(flash, (0, 0))

    def _draw_celestreeyl_awaken(self, screen):
        c = self.cutscene
        npc, t = c['npc'], c['t']
        W, H = config.WIDTH, config.HEIGHT
        scale = W / self.render_surface.get_width()
        img = npc._current_image()
        cx = (npc.rect.centerx - self.camera_x) * scale
        cy = (npc.rect.bottom - img.get_height() * 0.55 - self.camera_y) * scale
        charge = min(1.0, t / self.CELES_CHARGE)
        flash = max(0.0, min(1.0, (t - self.CELES_CHARGE) / self.CELES_FLASH))
        grow = charge * charge * (3 - 2 * charge)

        # the cave darkens as the light gathers, so the rays read even on snow
        dim = self.__dict__.get('_celes_dim')
        if dim is None or dim.get_size() != (W, H):
            dim = self._celes_dim = pygame.Surface((W, H))
            dim.fill((6, 4, 18))
        dim.set_alpha(int(190 * grow))
        screen.blit(dim, (0, 0))

        fx = self.__dict__.get('_celes_fx')
        if fx is None or fx.get_size() != (W, H):
            fx = self._celes_fx = pygame.Surface((W, H))
        fx.fill((0, 0, 0))

        def add(col, k):
            return tuple(min(255, int(v * k)) for v in col)

        # light rays fanning out and slowly turning
        n = 16
        length = (60 + 560 * grow + 400 * flash) * scale / 2
        for i in range(n):
            a = i * math.tau / n + t * 0.6 + (0.12 * math.sin(t * 3 + i) if i % 2 else 0)
            half = 0.05 + 0.04 * (i % 3) + 0.1 * flash
            k = (0.2 + 0.5 * grow + 0.3 * flash) * (0.7 + 0.3 * math.sin(t * 9 + i * 1.7))
            col = self.CELES_RAY_COLS[i % len(self.CELES_RAY_COLS)]
            for w, kk in ((1.0, 0.35), (0.4, 0.75)):   # soft wide beam, bright narrow core
                pts = [(cx, cy),
                       (cx + math.cos(a - half * w) * length, cy + math.sin(a - half * w) * length),
                       (cx + math.cos(a + half * w) * length, cy + math.sin(a + half * w) * length)]
                pygame.draw.polygon(fx, add(col, k * kk), pts)

        # motes of light streaming inward to the tree
        rng = random.Random(1234)
        for _ in range(42):
            ang = rng.uniform(0, math.tau)
            q = (t * rng.uniform(0.6, 1.1) + rng.random()) % 1.0
            d = (1 - q) * rng.uniform(140, 260) * scale
            x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d
            pygame.draw.circle(fx, add(rng.choice(self.CELES_RAY_COLS), grow * (0.4 + q)),
                               (int(x), int(y)), max(1, int((1 + 2 * q) * scale)))

        # pulsing rings and a swelling core of light
        for k in range(3):
            q = (t * 1.6 + k / 3) % 1.0
            r = int((10 + 120 * q) * scale)
            pygame.draw.circle(fx, add((255, 245, 200), grow * (1 - q)), (int(cx), int(cy)), r, max(1, int(2 * scale)))
        core = (14 + 40 * grow + 600 * flash * flash) * scale
        for k in range(16, 0, -1):
            f = k / 16
            pygame.draw.circle(fx, add((255, 250, 225), (0.15 + 0.85 * grow) * (1 - f) ** 1.5 * 1.6),
                               (int(cx), int(cy)), max(1, int(core * f)))
        screen.blit(fx, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # white-out: ramps in during the burst and holds until the battle loads
        if flash > 0:
            white = self.__dict__.get('_celes_white')
            if white is None or white.get_size() != (W, H):
                white = self._celes_white = pygame.Surface((W, H))
                white.fill((255, 255, 255))
            white.set_alpha(int(255 * flash ** 1.5))
            screen.blit(white, (0, 0))

    # --- Quest: Horizon Cave guardian ---
    # Josh stands at (9,3) in HORIZON_CAVE1, right in front of the "cele"
    # entrance to HORIZON_CAVE.world. Until JOSH_UNLOCK_FLAG is set he only
    # turns the player away; after it he battles (TRAINER_DATA['josh']), and
    # on a win walks out of the cave and is gone for good. Flag: josh_defeated.
    JOSH_UNLOCK_FLAG = 'gym3_rematch_defeated'  # Sam's rematch — the last of the 3 (see GYM_REMATCHES)
    JOSH_EXIT_TILE = (9, 14)                    # HORIZON_CAVE1's exit tile

    def _interact_josh(self, npc):
        dialog = TRAINER_DATA['josh']['dialog']
        npc.face_toward_player(self.player)
        if not self.story_flags.get(self.JOSH_UNLOCK_FLAG):
            self.message_box.queue_messages(
                self._split_dialogue(*dialog['locked'], name='Josh'), wait_for_input=True)
            return
        self.message_box.queue_messages(
            self._split_dialogue(*dialog['default'], name='Josh'),
            wait_for_input=True, on_complete=lambda: self.start_trainer_battle(npc))

    def _record_objective_times(self):
        """Stamp the play time the first frame each objective's flag is set."""
        for obj_id, _, _, flags in OBJECTIVES:
            if obj_id not in self.objective_times and any(self.story_flags.get(f) for f in flags):
                self.objective_times[obj_id] = self.play_time_seconds

    def _on_josh_battle_won(self, npc):
        self.story_flags['josh_battle_won'] = True   # objective time = the win, not the walk-off
        msgs =self._split_dialogue(*TRAINER_DATA['josh']['dialog']['defeated'], name='Josh')
        ex, ey = self.JOSH_EXIT_TILE
        px = self.player.rect.x // config.TILE_SIZE
        # The player is usually standing right below him; sidestep down a
        # neighbouring column so the scripted walk never passes through them.
        lane = npc.tile_x - 1 if px == npc.tile_x else npc.tile_x
        path = [(lane, npc.tile_y), (lane, ey - 1), (ex, ey - 1), (ex, ey)]

        def start_walk_away():
            self.cutscene = {'phase': 'josh_walking_away', 'npc': npc, 'path': path}
        self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=start_walk_away)

    # --- Side quest: Pectura trade ---
    # A collector from Skelig Town (SIERRA_HOUSE2.tmx) wants a Pectura. If one
    # is in the party he offers a yes/no trade for a Lv 10 Rhysnow, which takes
    # the Pectura's party slot. Flag: collector_traded.
    TRADE_WANT = 'Pectura'
    TRADE_GIVE = ('Rhysnow', 10)

    def _trade_want(self):
        return self._rando(self.TRADE_WANT, "trade_want:collector")

    def _trade_give(self):
        name, level = self.TRADE_GIVE
        return self._rando(name, "gift:collector"), level

    def _interact_trade_collector(self, npc):
        want = self._trade_want()
        if self.story_flags.get('collector_traded'):
            lines = [f"{want} and I are getting along great!",
                     "Good luck against Skyy... and remember, you didn't hear it from me."]
            self.message_box.queue_messages(self._split_dialogue(*lines, name='Collector'), wait_for_input=True)
            return
        find_line = (f"Hey I love to collect rare dinos, and I can never seem to find {want}!"
                     if self.randomizer else
                     "Hey I love to collect rare dinos, and I can never seem to find Pectura, the magma and flying type!")
        lines = [find_line,
                 "I am visiting from Skelig Town up north and only see cold dinos you see",
                 f"If you can find me a {want} to trade I would happily give you something you cannot find around here!"]
        offer = next((d for d in self.player_dinos if d['name'] == want), None)
        on_complete = None
        if offer:
            def ask():
                self.yes_no_prompt = YesNoPrompt(
                    f"Trade your Lv {offer['level']} {offer['name']} for a {self._trade_give()[0]}?",
                    self.fonts, config.WIDTH, config.HEIGHT)
                self.yes_no_callback = lambda: self._do_collector_trade(offer)
            on_complete = ask
        self.message_box.queue_messages(self._split_dialogue(*lines, name='Collector'),
                                        wait_for_input=True, on_complete=on_complete)

    def _do_collector_trade(self, offer):
        if offer not in self.player_dinos:
            return
        name, level = self._trade_give()
        if offer['name'] not in self.nz_owned_species:   # Nuzlocke dupes count traded-away dinos
            self.nz_owned_species.append(offer['name'])
        received = self.create_dino(name, level)
        self.player_dinos[self.player_dinos.index(offer)] = received
        self.dinos_seen.add(name)
        self.story_flags['collector_traded'] = True
        lines = [f"You are the best! Here as promised a {name}!",
                 "This should help with the flying gym leader Skyy, don't tell him I gave you this..."]
        self.message_box.queue_messages(
            [f"{config.PLAYER_NAME} traded {offer['name']} for {name}!",
             *self._split_dialogue(*lines, name='Collector')],
            wait_for_input=True)

    def _lantern_glow(self, r):
        cache = self.__dict__.setdefault('_lantern_glow_cache', {})
        spr = cache.get(r)
        if spr is None:
            spr = pygame.Surface((r * 2, r * 2))
            for k in range(r, 0, -2):
                f = (1 - k / r) ** 1.6
                pygame.draw.circle(spr, (int(40 * f), int(140 * f), int(255 * f)), (r, r), k)
            cache[r] = spr
        return spr

    def _draw_lantern_wisps(self, surface):
        if not self._lantern_wisps_active():
            return
        ts = config.TILE_SIZE
        scale = config.WIDTH / self.render_surface.get_width()
        t = pygame.time.get_ticks() / 1000.0
        final = len(self.LANTERN_WISPS) - 1
        for i in self._visible_lantern_wisps():
            wx, wy = self.LANTERN_WISPS[i]
            big = 1.5 if i == final else 1.0
            cx = (wx * ts + ts / 2 - self.camera_x) * scale + math.sin(t * 1.3 + i) * 3 * scale
            cy = (wy * ts + ts / 2 - self.camera_y) * scale + math.sin(t * 2.1 + i * 2) * 4 * scale
            if not (-80 < cx < config.WIDTH + 80 and -80 < cy < config.HEIGHT + 80):
                continue
            flick = 0.85 + 0.15 * math.sin(t * 9 + i * 3) + random.uniform(-0.05, 0.05)
            r = int(26 * scale * big * flick) // 2 * 2
            if r > 2:
                surface.blit(self._lantern_glow(r), (cx - r, cy - r), special_flags=pygame.BLEND_RGB_ADD)
            core = 5 * scale * big * flick
            # teardrop flame: round base + a tip that sways
            sway = math.sin(t * 5 + i) * core * 0.5
            pygame.draw.polygon(surface, (120, 200, 255),
                                [(cx - core, cy), (cx + sway, cy - core * 2.6), (cx + core, cy)])
            pygame.draw.circle(surface, (120, 200, 255), (int(cx), int(cy)), int(core))
            pygame.draw.circle(surface, (235, 250, 255), (int(cx), int(cy + core * 0.2)), max(1, int(core * 0.55)))
            # a few sparks rising off the flame
            for k in range(3):
                q = (t * 0.7 + k / 3 + i * 0.37) % 1.0
                sx = cx + math.sin(q * 6 + k * 2 + i) * core * 1.4
                sy = cy - core - q * 22 * scale * big
                c = int(255 * (1 - q))
                pygame.draw.circle(surface, (c // 3, c * 3 // 4, c), (int(sx), int(sy)), max(1, int(scale * (1 - q) * 1.5)))

    def use_tm(self, dino, item_name):
        """Teach a TM's move to `dino`. Returns (used, messages). A TM is
        consumed only when the move is actually learned, and only Dinos that
        share the move's type can learn it."""
        move = config.ITEMS[item_name]['tm_move']
        md = MOVE_DATA[move]
        mtype = md['type']
        if mtype not in dino.get('type', []):
            return False, [f"{dino['name']} can't learn {move}!",
                           f"Only {mtype.capitalize()}-type Dinos can use this TM."]
        if move in dino.get('moves', []) or any(m['name'] == move for m in dino.get('moveset', [])):
            return False, [f"{dino['name']} already knows {move}!"]
        self.inventory[item_name] = max(0, self.inventory.get(item_name, 0) - 1)
        dino.setdefault('moves', []).append(move)
        msgs = [f"{dino['name']} learned {move}!"]
        if len(dino.get('moveset', [])) < 4:
            dino.setdefault('moveset', []).append({
                "name":     move,
                "type":     mtype,
                "damage":   md.get("damage", 0),
                "accuracy": md.get("accuracy", 100),
                "ability":  md.get("ability", None),
            })
        else:
            msgs.append(f"It already knows 4 moves - visit the Party screen to swap {move} in.")
        return True, msgs

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
        starter_names = self._starter_names()
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
        ball_items = dict(ball_items)
        for tx, ty, item_name in config.SCRIPTED_WORLD_ITEMS.get(self.current_world_file, []):
            ball_items[(tx, ty)] = (item_name, None)
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
            return False
        item_name = self.items_on_map.pop((px, py))
        self.map_ball_items.pop((px, py), None)
        self.map_ball_images.pop((px, py), None)
        self.picked_up_world_items.add((self.current_world_file, px, py))
        if item_name in config.DINO_BALL_MAP:
            dino_name = self._starter_map()[item_name]
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
            # The Celestial Solar Shard ends the story — roll the credits
            on_done = self._start_credits if item_name == self.SOLAR_SHARD_ITEM else None
            self.message_box.queue_messages([f'Picked up a {item_name}!'], wait_for_input=True,
                                            on_complete=on_done)
        return True

    # --- Update ---

    def update(self, dt):
        if self.state == 'launch':
            self.launch_intro.update(dt)
            if self.launch_intro.done:
                self.launch_intro = None
                self.state_stack = ['title']
                self.title_screen.reset(fade_from_black=False)
            return

        if self.state == 'title':
            self.title_screen.update(dt)
            return

        if self.credits:
            self.credits.update(dt)
            if self.credits.done:
                self._finish_credits()
            return

        # Left the title (New Game / Continue / Sandbox) — fade the theme out
        self._stop_title_music()

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

        # A sky transition card pauses everything underneath it
        if self.sky_transition:
            tr = self.sky_transition
            tr.update(dt)
            if tr.done and self.sky_transition is tr:
                self.sky_transition = None
            return

        self.play_time_seconds += dt
        self._record_objective_times()
        self.update_day_night(dt)
        self.update_heal_anim(dt)
        self.update_hit_flash(dt)
        self.update_move_anim(dt)
        if self.catch_anim:
            self.catch_anim.update(dt)
        self.env_fx.update(dt)  # ENV FX
        self.lake_aurora.update(dt)  # LAKE AURORA
        self.portals.update(dt)  # PORTALS
        self._update_area_music()
        self._track_dex_seen()
        if self.screen_shake > 0:
            self.screen_shake = max(0.0, self.screen_shake - dt)
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

        if self.battle_transition is not None and self.battle_transition.done:
            self.battle_transition = None

        # Encounter intro animation completion — kept here so draw() never triggers game logic
        if 'encounter' in self.state_stack and self.encounter_anim is not None:
            now = pygame.time.get_ticks()
            if now - self.encounter_anim["start_time"] >= self.encounter_anim["duration"]:
                anim = self.encounter_anim
                self.encounter_anim = None
                if not self.is_double_battle:
                    self.encounter.current_dino_surface = anim["frames"][0]
                self.enemy_dino["image"] = anim["frames"][0]
                # The send-out intro already showed encounter_text and "Go!"
                # while it played, so only the prompt is left.
                msgs = (["What will you do?"] if anim.get("intro") == 'send_out'
                        else [self.encounter_text, "What will you do?"])
                self.message_box.queue_messages(msgs, wait_for_input=True)

        if self.message_box.visible:
            return

        if self.coord_input_active or self.dino_spawn_picker:
            return

        # After any message clears in double battle, auto-arm p1 selection for the new turn
        if (self.state == 'encounter' and self.is_double_battle
                and self.encounter_anim is None and self.double_phase is None):
            self._double_start_p1_turn()

        # Single battle: a dino that used a recharge move skips its next
        # turn — play it out the moment control would return to the player.
        if (self.state == 'encounter' and not self.is_double_battle
                and self.encounter_anim is None and not self.awaiting_switch
                and not self.fading and not self._post_xp_callback and not self.catch_anim
                and self.player_dinos and self.enemy_dino
                and self.enemy_dino.get('hp', 0) > 0):
            active = self.player_dinos[self.active_dino_index]
            if active.get('must_recharge') and active.get('hp', 0) > 0:
                self._player_recharge_turn(active)

        if self.state == 'world':
            if self.portals.warp:  # PORTALS — warp transition; the player stays frozen
                self.portals.update_warp(dt)
            elif self.entrance_fade_state == 'out':
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
                self.surf.update(dt)  # SURF (testing)
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
            elif self.fade_alpha >= 255:
                # Already covered by a scripted white-out (e.g. Celestreeyl) —
                # straight into the battle, no standard transition.
                self.fading = False
                self.fade_color = (0, 0, 0)   # a white-out transition only lasts one fade
                self.push_state('encounter')
                if self.encounter_anim is not None:
                    now = pygame.time.get_ticks()
                    self.encounter_anim['start_time'] = now
                    self.encounter_anim['last_switch'] = now
            else:
                if self.battle_transition is None:
                    self.battle_transition = BattleTransition()
                if self.battle_transition.covered:
                    self.fading = False
                    self.push_state('encounter')
                    # The intro (enemy frames + "A wild X appeared!") was timed
                    # from the trigger; restart it so it plays once visible.
                    if self.encounter_anim is not None:
                        now = pygame.time.get_ticks()
                        self.encounter_anim['start_time'] = now
                        self.encounter_anim['last_switch'] = now

            self.check_story_events()
            self._check_amber_blocker()
            self._check_route2_blocker()
            self._maybe_add_gym_blocker()
            self._maybe_add_gym2_blocker()
            self._check_gym2_blocker_removal()
            self._maybe_add_horizon_blockers()
            self._check_horizon_blockers_removal()
            self._maybe_add_route2_blocker()
            self._maybe_add_skyy()
            self._maybe_add_gym1_skyy()
            self._maybe_add_gray_rival()
            self._check_gray2_route3_rival()
            self._maybe_add_sam_surf_intro()
            self._check_sam_surf_intro()
            self._check_skyy_powerplant_trigger()
            self._maybe_add_pp_grunts_waiting()
            self._maybe_add_powerplant_scene_npcs()
            self._check_skyy_disruption_line()
            self._check_pp_grunts2_scene()
            self._maybe_add_pp_grunts2()
            self._check_pp_grunt_a_walkup_trigger()
            self._maybe_add_grunts_vanessa()
            self._maybe_add_shadow_confrontation_npcs()
            self._check_shadow_confrontation_trigger()
            self._check_mom_greeting()
            self._check_credits_wakeup()
            self._check_mom_ending()
            self._check_cobaltion_battle_result()
            self._check_celestreeyl_battle_result()
            self._check_legend_battle_result()
            self._nuzlocke_retire_fainted()
            self._maybe_place_solar_shard()
            self._check_lantern_battle_result()
            self._check_lantern_wisps()
            self._maybe_add_shadowhq_npcs()
            self._advance_shadowhq_event()
            self._update_shadowhq_wave(dt)
            self._maybe_add_surf_shack_prep_npcs()
            self._check_surf_shack_prep()
            self._check_gym2_corn_maze_reveal()
            self._check_route26_abby_reveal()
            self._update_abby_follow(dt)
            self._check_route26_boundary()

    # --- Draw ---

    def draw(self):
        if self.state == 'launch':
            self.launch_intro.draw(self.screen)
            pygame.display.flip()
            return

        if self.state == 'title':
            self.title_screen.draw(self.screen, os.path.exists(SAVE_PATH))
            pygame.display.flip()
            return

        if self.state == 'intro':
            if self.intro_sequence:
                self.intro_sequence.draw(self.screen)
            pygame.display.flip()
            return

        if self.credits:
            self.credits.draw(self.screen)
            pygame.display.flip()
            return

        self.render_surface.fill(config.BLACK)

        background_state = 'encounter' if 'encounter' in self.state_stack else self.state_stack[0]
        current_state = self.state

        if background_state == 'world':
            space = self.current_world_file in self.SPACE_WORLDS
            if self.current_world_file in self.AETHER_WORLDS:
                self.aether_bg.draw(self.render_surface, self.camera_x, self.camera_y,
                                    pygame.time.get_ticks() / 1000.0)
            elif space:
                self._space_bg().draw(self.render_surface, self.camera_x, self.camera_y,
                                      pygame.time.get_ticks() / 1000.0)
            self.draw_map_below(self.render_surface)
            self.env_fx.draw_ground(self.render_surface, self.camera_x, self.camera_y)  # ENV FX
            ts = config.TILE_SIZE
            for (tx, ty), img in self.map_ball_images.items():
                if (tx, ty) in self.items_on_map:
                    self.render_surface.blit(img, (tx * ts - self.camera_x, ty * ts - self.camera_y))
            for npc in self.npcs:
                npc.draw(self.render_surface, self.camera_x, self.camera_y)
            self.portals.draw_world(self.render_surface, self.camera_x, self.camera_y)  # PORTALS
            if self.shadowhq_wave:
                self._draw_shadowhq_wave(self.render_surface)
            if self.cutscene and self.cutscene.get('phase') == 'cobaltion_collapse':
                self._draw_cobaltion_collapse(self.render_surface)
            self.surf.draw_under_player(self.render_surface, self.camera_x, self.camera_y)  # SURF (testing)
            for sprite in self.all_sprites:
                oy = self.surf.player_offset_y() if sprite is self.player else 0  # SURF (testing)
                self.render_surface.blit(sprite.image,
                                         (sprite.rect.x - self.camera_x, sprite.rect.y - self.camera_y + oy))
            self.env_fx.draw_over_player(self.render_surface, self.camera_x, self.camera_y)  # ENV FX
            self.draw_map_above(self.render_surface)
            if self.orb_fx:
                self._draw_orb_fx(self.render_surface)
            if self.cutscene:
                self._draw_gym2_cutscene_fx(self.render_surface)
            if self.heal_anim:
                self._draw_heal_anim(self.render_surface)
            scaled_surface = pygame.transform.scale(self.render_surface, (config.WIDTH, config.HEIGHT))
            shake = (random.randint(-6, 6), random.randint(-6, 6)) if self.screen_shake > 0 else (0, 0)
            if shake != (0, 0):
                self.screen.fill(config.BLACK)
            self.screen.blit(scaled_surface, shake)

            # out in space there's no day/night or eclipse sky over the planet
            if self.night_active and not space:
                self.screen.blit(self._night_overlay, (0, 0))
            if self.event_overlay_active and not space:
                self.screen.blit(self._event_overlay, (0, 0))
            self._draw_lantern_wisps(self.screen)   # after the night overlay so they glow
            self.lake_aurora.draw(self.screen)  # LAKE AURORA
            self.portals.draw_glow(self.screen)  # PORTALS
            if self.cutscene and self.cutscene.get('phase') == 'celestreeyl_awaken':
                self._draw_celestreeyl_awaken(self.screen)
            if self.cutscene and self.cutscene.get('phase') == 'legend_awaken':
                self._draw_legend_awaken(self.screen)
            if self.cutscene and self.cutscene.get('phase') == 'solar_shard_reveal':
                self._draw_solar_shard_reveal(self.screen)
            if self.cutscene and self.cutscene.get('phase') == 'lunar_shard_reveal':
                self._draw_lunar_shard_reveal(self.screen)
            if self.sandbox:
                tag = self.fonts['XS'].render("SANDBOX MODE", True, (255, 80, 80))
                self.screen.blit(tag, (config.WIDTH - tag.get_width() - 6, 6))
            self.portals.draw_warp(self.screen)  # PORTALS — warp covers the world, not the banner
            self.route_banner.draw(self.screen)
            if self.cutscene_flash and self.cutscene_flash['alpha'] > 0:
                _flash = pygame.Surface((config.WIDTH, config.HEIGHT))
                _flash.fill(self.cutscene_flash.get('color', (255, 235, 150)))
                _flash.set_alpha(int(self.cutscene_flash['alpha']))
                self.screen.blit(_flash, (0, 0))
            if self.coord_input_active:
                self._draw_coord_input(self.screen)
            if self.dino_spawn_picker:
                self._draw_dino_spawn_picker(self.screen)

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
                    field_effects=self.field_effects,
                )
            else:
                # Single battle draw path
                send_out_fx, intro_t = None, 0.0
                if self.encounter_anim:
                    anim = self.encounter_anim
                    now  = pygame.time.get_ticks()
                    if now - anim["last_switch"] >= anim["interval"]:
                        anim["frame_idx"] = (anim["frame_idx"] + 1) % len(anim["frames"])
                        anim["last_switch"] = now
                    frame = anim["frames"][anim["frame_idx"]]
                    self.encounter.current_dino_surface = frame
                    intro = anim.get("intro")
                    intro_t = max(0.0, (now - anim["start_time"]) / 1000.0)
                    offset_x = 0
                    if intro in ('send_out', 'slide'):
                        size = int(config.ENCOUNTER_BASE_SIZE
                                   * config.ENCOUNTER_DINO_SIZES.get(self.encounter.dino_key, 1.0))
                        (ex, _), _ = self._battle_slot_pos('enemy')
                        offset_x = enemy_slide_offset(intro_t, ex, size)
                    if intro == 'send_out':
                        send_out_fx = anim.get("send_out_fx")
                        if send_out_fx is None:
                            d = self.player_dinos[self.active_dino_index]
                            pod = self.ball_icons.get(d.get('caught_ball', 'DinoPod'),
                                                      self.ball_icons['DinoPod'])
                            send_out_fx = anim["send_out_fx"] = SendOutAnimation(
                                pod, d['image'],
                                EncounterUI.player_sprite_rect(config.WIDTH, config.HEIGHT),
                                start_pos=(-30, config.HEIGHT - 80))
                    self.encounter.draw(self.screen, offset_x=offset_x)
                else:
                    catch_hides = bool(self.catch_anim and self.catch_anim.hides_enemy)
                    self.encounter.draw(self.screen, enemy_visible=_enemy_vis and not catch_hides)

                msg_active   = self.message_box.visible
                throwing     = bool(self.catch_anim and not self.catch_anim.done)
                display_text = (self.message_box.message[:self.message_box.char_index]
                                if msg_active else self.encounter_text)
                if throwing and not msg_active:
                    display_text = self._catch_throw_text
                if send_out_fx is not None:
                    if intro_t >= send_out_anim.SEND_START and not msg_active:
                        display_text = f"Go! {self.player_dinos[self.active_dino_index]['name']}!"
                    _player_vis = _player_vis and not send_out_fx.player_hidden(intro_t)
                msg_awaiting = (msg_active and self.message_box.wait_for_input and
                                self.message_box.char_index >= len(self.message_box.message))
                self.encounter_ui.draw(self.screen, self.player_dinos[self.active_dino_index],
                                       self.enemy_dino, display_text,
                                       show_actions=not msg_active and not throwing and not self.encounter_anim,
                                       trainer_total=self.trainer_dinos_total if self.is_trainer_battle else 0,
                                       trainer_defeated=self.trainer_dinos_defeated,
                                       pod_icon=self.item_image if self.is_trainer_battle else None,
                                       msg_awaiting_input=msg_awaiting,
                                       player_visible=_player_vis,
                                       field_effects=self.field_effects)
                if send_out_fx is not None:
                    send_out_fx.draw(self.screen, intro_t)
                self._nuzlocke_battle_hud(self.screen)

            if self.move_anim and not self.encounter_anim:
                self.move_anim.draw(self.screen)
            if self.catch_anim and not self.is_double_battle:
                self.catch_anim.draw(self.screen)

        if background_state == 'encounter' and current_state == 'encounter':
            if self.night_active:
                self.screen.blit(self._night_overlay_battle, (0, 0))
            if self.event_overlay_active:
                self.screen.blit(self._event_overlay_battle, (0, 0))

        elif current_state == 'type_chart':
            img = pygame.transform.scale(self.type_chart_image, (config.WIDTH, config.HEIGHT))
            self.screen.blit(img, (0, 0))

        elif current_state == 'trainer_card':
            self.trainer_card_screen.draw(self.screen)

        elif current_state == 'objectives':
            self.objectives_screen.draw(self.screen)

        elif current_state == 'options':
            self.options_screen.draw(self.screen)

        elif current_state == 'rules':
            self.rules_screen.draw(self.screen)

        elif current_state == 'controls':
            self.controls_screen.draw(self.screen)

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
                if self.night_active:
                    self.screen.blit(self._night_overlay_battle, (0, 0))
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

        if self.battle_transition is not None:
            self.battle_transition.draw(self.screen)
        elif self.fading or self.entrance_fade_state is not None:
            fade_surface = pygame.Surface((config.WIDTH, config.HEIGHT))
            fade_surface.set_alpha(self.fade_alpha)
            fade_surface.fill(self.fade_color)
            self.screen.blit(fade_surface, (0, 0))

        if self.message_box.visible and self.state != 'encounter':
            self.message_box.draw(self.screen)

        if self.dino_pickup_popup and self.dino_pickup_popup.active:
            self.dino_pickup_popup.draw(self.screen)

        if self.yes_no_prompt:
            self.yes_no_prompt.draw(self.screen)

        if self.sky_transition:
            self.sky_transition.draw(self.screen)

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
        # Eclipse mode always overwrites night mode — never show both at once.
        if self.event_overlay_active:
            return False
        if self.force_night is not None:
            return self.force_night
        return self.is_night

    # --- Sky transition cards (day/night + eclipse) ---

    def start_sky_transition(self, kind, on_swap=None, on_done=None):
        """Play a full-screen SkyTransition card ('to_night' | 'to_day' | 'eclipse').
        The world is paused and input ignored until it finishes; on_swap runs
        while the card fully covers the screen."""
        self.sky_transition = SkyTransition(kind, on_swap=on_swap, on_done=on_done)

    def _enable_eclipse_overlay(self):
        self.event_overlay_active = True

    def _flip_day_night(self):
        self.is_night = not self.is_night

    def _finish_day_night(self):
        self.dn_transitioning = False
        self.day_night_timer = 0.0

    def update_day_night(self, dt):
        if self.dn_transitioning or self.state != 'world':
            return
        self.day_night_timer += dt
        if self.day_night_timer < self.CYCLE_DURATION:
            return
        if self.event_overlay_active or self.force_night is not None:
            # Eclipse / forced night hides the cycle anyway — flip quietly
            self._flip_day_night()
            self.day_night_timer = 0.0
            return
        self.dn_transitioning = True
        self.start_sky_transition('to_day' if self.is_night else 'to_night',
                                  on_swap=self._flip_day_night, on_done=self._finish_day_night)

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

    # Worlds whose off-map void shows the aether_bg starfield instead of black.
    AETHER_WORLDS = ('HORIZON_CAVE.world',)

    # Standalone celestial planet maps (tools/make_planets.py) and the space
    # backdrop each one floats in. Separate from LOST_REGION.world.
    SPACE_WORLDS = {
        'LUNAR_PLANET.tmx': LunarBackground,
        'SOLAR_PLANET.tmx': SolarBackground,
    }

    def _space_bg(self):
        world = self.current_world_file
        if world not in self._space_bgs:
            self._space_bgs[world] = self.SPACE_WORLDS[world]()
        return self._space_bgs[world]

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
        if self.camera_locked:
            return  # a scripted camera pan (_update_camera_pan) owns camera_x/y right now
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

    # Screen-space sprite centers + effect scale for each battle slot
    # (mirrors the sprite placement in screens.Encounter / EncounterUI / DoubleBattle*)
    def _battle_slot_pos(self, slot):
        if self.is_double_battle:
            return {
                'enemy1':  ((config.WIDTH - 250, 145), 0.85),
                'enemy2':  ((config.WIDTH - 120, 145), 0.85),
                'player1': ((94, 280), 1.1),
                'player2': ((244, 280), 1.1),
            }.get(slot, ((config.WIDTH - 250, 145), 0.85))
        if slot.startswith('enemy'):
            return (config.WIDTH - 157, 155), 1.0
        return (166, 255), 1.4

    def play_move_anim(self, move_name, target_slot, source_slot):
        """Start the moves.py hit animation for move_name. Self-targeting moves play on the user."""
        if MOVE_DATA.get(move_name, {}).get('target') == 'self':
            target_slot = source_slot
        tpos, scale = self._battle_slot_pos(target_slot)
        spos, _ = self._battle_slot_pos(source_slot)
        self.move_anim = MoveAnimation(move_name, tpos, spos, scale)

    def update_move_anim(self, dt):
        if self.move_anim:
            self.move_anim.update(dt)
            if self.move_anim.done:
                self.move_anim = None

    # Catch chance = pod's catch_rate x HP mult x level mult x stat-total mult,
    # clamped to [CATCH_FLOOR, 1.0].
    CATCH_FLOOR = 0.05
    CATCH_LOW_HP_BONUS = 1.0        # 1 HP left -> up to x2.0, full HP -> x1.0
    CATCH_LEVEL_PENALTY = 0.05      # per level the wild dino is above yours
    CATCH_LEVEL_PENALTY_MIN = 0.5   # level mult never drops below this
    CATCH_LEVEL_BONUS = 0.02        # per level the wild dino is below yours
    CATCH_LEVEL_BONUS_MAX = 1.2
    # (max base stat total, mult) — health + attack + defense + speed
    CATCH_STAT_TIERS = [(440, 1.0), (460, 0.85), (float('inf'), 0.7)]

    def _catch_chance(self, item_name):
        chance = config.ITEMS.get(item_name, {}).get("catch_rate", 0.5)
        enemy = self.enemy_dino

        max_hp = max(1, enemy.get('max_hp', 1))
        hp_frac = max(0.0, min(1.0, enemy.get('hp', max_hp) / max_hp))
        chance *= 1 + (1 - hp_frac) * self.CATCH_LOW_HP_BONUS

        active = self.player_dinos[self.active_dino_index] if self.player_dinos else None
        if active is not None:
            diff = enemy['level'] - active['level']
            if diff > 0:
                chance *= max(self.CATCH_LEVEL_PENALTY_MIN, 1 - diff * self.CATCH_LEVEL_PENALTY)
            elif diff < 0:
                chance *= min(self.CATCH_LEVEL_BONUS_MAX, 1 + -diff * self.CATCH_LEVEL_BONUS)

        stats = DINO_DATA.get(enemy['name'], {}).get('stats', {})
        total = sum(stats.get(k, 0) for k in ('health', 'attack', 'defense', 'speed'))
        chance *= next(m for cap, m in self.CATCH_STAT_TIERS if total <= cap)

        return max(self.CATCH_FLOOR, min(1.0, chance))

    def attempt_catch(self, item_name='DinoPod'):
        nz = self.nz_encounter if self.nuzlocke else None
        if nz and nz['status'] in ('full', 'dupe'):
            reason = ("You've already caught this route's 2 dinos." if nz['status'] == 'full'
                      else "You've already caught this kind of dino (Duplicate Skip).")
            self.message_box.queue_messages(
                [f"Nuzlocke: {reason}", "You can only fight or run."], wait_for_input=True)
            return
        if self.inventory.get(item_name, 0) <= 0:
            self.message_box.queue_messages(
                [f"You have no {item_name}s left!"], wait_for_input=True,
                on_complete=self._enemy_turn)
            return
        self.inventory[item_name] = max(0, self.inventory[item_name] - 1)
        success = random.random() < self._catch_chance(item_name)

        # Throw the pod first; the result messages wait for it to land.
        dino_key = self.encounter.dino_key
        enemy_size = int(config.ENCOUNTER_BASE_SIZE * config.ENCOUNTER_DINO_SIZES.get(dino_key, 1.0))
        enemy_center, _ = self._battle_slot_pos('enemy')
        self._catch_throw_text = f"You threw a {item_name}!"
        self.catch_anim = CatchAnimation(
            self.item_icons.get(item_name, self.item_image),
            self.encounter.current_dino_surface,
            enemy_center, enemy_size,
            start_pos=(140, 290),   # just in front of the player's dino
            success=success,
            on_finish=lambda: self._finish_catch(item_name, success))

    def _finish_catch(self, item_name, success):
        if not success:
            self.catch_anim = None   # dino is back out — scene draws it again

        if success:
            self._wild_caught = True
            nz = self.nz_encounter
            if self.nuzlocke:
                if nz and nz['status'] == 'catch':
                    self.nz_route_caught.setdefault(nz['area'], []).append(self.enemy_dino['name'])
                    caught = len(self.nz_route_caught[nz['area']])
                    nz['label'] = f"{caught}/{self.NUZLOCKE_ROUTE_CATCHES}"
                if self.enemy_dino['name'] not in self.nz_owned_species:
                    self.nz_owned_species.append(self.enemy_dino['name'])
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
        if self.is_double_battle:
            flash_target = 'enemy1' if defender is self.enemy_dino else 'enemy2'
            anim_source = 'player1' if self.player_dinos and attacker is self.player_dinos[0] else 'player2'
        else:
            flash_target = 'enemy'
            anim_source = 'player'
        self.play_move_anim(move_name, flash_target, anim_source)
        if dmg > 0:
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
                        self.defeated_trainers.add(self._trainer_key(self.current_trainer_npc))
                        coin_reward = self._trainer_data(self.current_trainer_npc).get('reward_coins', 0)
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

        if attacker.pop('must_recharge', False):
            attacker['defending'] = False
            prefix = f"{self._trainer_name}'s " if self.is_trainer_battle else "The wild "
            msgs = [f"{prefix}{attacker['name']} must recharge!"]
            if after:
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=after)
            else:
                msgs.extend(self._tick_field_effects())
                msgs.extend(self._tick_dino_effects())
                self._clear_defending_flags()
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
        self.play_move_anim(move['name'], 'player', 'enemy')
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

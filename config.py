import os
import pygame

PLAYER_NAME = 'Jet'

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
DARK = "#201624"
LIGHT = "#c0c0b9"
GRAY = '#3a373b'
LIGHT_GRAY = '#4b484d'
MAGMA = "#da563e"
AQUA = '#50b0d8'
EARTH = '#64a990'
SOFT_WHITE = '#f0f0f0'
ROCK = "#57513e"
SPIKE = "#d4ba93"
FLYING = "#b1c5da"
LIGHTNING = "#f3ed7a"
ICE = "#73dfe9"
ANCIENT = "#521F45"

# Screen
WIDTH = 640
HEIGHT = 480
FPS = 60

# World
TILE_SIZE = 32
PLAYER_SPEED = TILE_SIZE

# Font paths
FONT_PATH_B = os.path.join('assets', 'Items', 'PixeloidSans-Bold.ttf')
FONT_PATH   = os.path.join('assets', 'Items', 'PixeloidSans.ttf')
FONT_PATH_R = os.path.join('assets', 'Items', 'PixeloidMono.ttf')

FONT_XS     = 12
FONT_SMALL  = 16
FONT_MEDIUM = 24
FONT_LARGE  = 28

FONT_DEFS = {
    "BAG":      (FONT_PATH_B, FONT_SMALL),
    "BATTLE":   (FONT_PATH_B, FONT_MEDIUM),
    "BATTLE2":  (FONT_PATH_R, FONT_SMALL),
    "XS":       (FONT_PATH_B, FONT_XS),
    "DIALOGUE": (FONT_PATH_B, FONT_LARGE),
    "DIALOGUE_BOX": (FONT_PATH_B, 22),  # overworld dialogue box — a bit smaller than FONT_LARGE
}

# Asset paths
ASSETS_PATH  = "assets/MapAssets"
DINOS_PATH   = "assets/DINOS"
DINOS_FRONT  = "assets/DINOS/FRONT"
DINOS_BACK   = "assets/DINOS/BACK"
ITEMS_PATH   = "assets/Items"

# Map tiles
TILE_PATHS = {
    "G": os.path.join(ASSETS_PATH, "grassa.png"),
    "g": os.path.join(ASSETS_PATH, "grass_spawn.png"),
    "W": os.path.join(ASSETS_PATH, "water1.png"),
    "t": os.path.join(ASSETS_PATH, "tree1.png"),
    "T": os.path.join(ASSETS_PATH, "tree2.png"),
}

# Encounter assets
ENCOUNTER_BG_PATH = os.path.join(ASSETS_PATH, 'Grass_Encounter.png')
CAVE_ENCOUNTER_BG_PATH = os.path.join('assets', 'SCREENS', 'cave_encounter.png')
ENCOUNTER_DINOS_PATHS = {
    'Vusion':     os.path.join(DINOS_FRONT, 'Vusion.png'),
    'Vusion2':    os.path.join(DINOS_FRONT, 'Vusion2.png'),
    'Anemamace':  os.path.join(DINOS_FRONT, 'Anemamace.png'),
    'Anemamace2': os.path.join(DINOS_FRONT, 'Anemamace2.png'),
    'Corlave':    os.path.join(DINOS_FRONT, 'Corlave.png'),
    'Corlave2':   os.path.join(DINOS_FRONT, 'Corlave2.png'),
    'Creuw':      os.path.join(DINOS_FRONT, 'Creuw.png'),
    'Creuw2':     os.path.join(DINOS_FRONT, 'Creuw.png'),
    'Luna':       os.path.join(DINOS_FRONT, 'Luna.png'),
    'Luna2':      os.path.join(DINOS_FRONT, 'Luna.png'),
    'Prowscar':   os.path.join(DINOS_FRONT, 'Prowscar.PNG'),
    'Prowscar2':  os.path.join(DINOS_FRONT, 'Prowscar.PNG'),
    'Floravel':   os.path.join(DINOS_FRONT, 'Floravel.PNG'),
    'Floravel2':  os.path.join(DINOS_FRONT, 'Floravel.PNG'),
    'Bullicorn':   os.path.join(DINOS_FRONT, 'Bullicorn.png'),
    'Bullicorn2':  os.path.join(DINOS_FRONT, 'Bullicorn.png'),
    'Netaslam':    os.path.join(DINOS_FRONT, 'Netaslam.png'),
    'Netaslam2':   os.path.join(DINOS_FRONT, 'Netaslam.png'),
    'Netyrant':         os.path.join(DINOS_FRONT, 'Netyrant.png'),
    'Netyrant2':        os.path.join(DINOS_FRONT, 'Netyrant.png'),
    'Sortle':           os.path.join(DINOS_FRONT, 'Sortle.png'),
    'Sortle2':          os.path.join(DINOS_FRONT, 'Sortle.png'),
    'Sharktastrophe':   os.path.join(DINOS_FRONT, 'Sharktastrophe.png'),
    'Sharktastrophe2':  os.path.join(DINOS_FRONT, 'Sharktastrophe.png'),
    'Magnecrab':        os.path.join(DINOS_FRONT, 'Magnecrab.png'),
    'Magnecrab2':       os.path.join(DINOS_FRONT, 'Magnecrab.png'),
    'Volkit':           os.path.join(DINOS_FRONT, 'Volkit.png'),
    'Volkit2':          os.path.join(DINOS_FRONT, 'Volkit.png'),
    'Drafyton':         os.path.join(DINOS_FRONT, 'Drafyton.png'),
    'Drafyton2':        os.path.join(DINOS_FRONT, 'Drafyton.png'),
    'Auraliz':          os.path.join(DINOS_FRONT, 'Auraliz.png'),
    'Auraliz2':         os.path.join(DINOS_FRONT, 'Auraliz.png'),
    'Voltzbee':         os.path.join(DINOS_FRONT, 'Voltzbee.png'),
    'Voltzbee2':        os.path.join(DINOS_FRONT, 'Voltzbee.png'),
    'Teamtwood':        os.path.join(DINOS_FRONT, 'Teamtwood.png'),
    'Teamtwood2':       os.path.join(DINOS_FRONT, 'Teamtwood.png'),
    'Tygraflare':        os.path.join(DINOS_FRONT, 'Tygraflare.png'),
    'Tygraflare2':       os.path.join(DINOS_FRONT, 'Tygraflare.png'),
    'Bouldava':         os.path.join(DINOS_FRONT, 'Bouldava.png'),
    'Bouldava2':        os.path.join(DINOS_FRONT, 'Bouldava.png'),
    'Ghoulflame':       os.path.join(DINOS_FRONT, 'Ghoulflame.png'),
    'Ghoulflame2':      os.path.join(DINOS_FRONT, 'Ghoulflame.png'),
    'Scarecrux':        os.path.join(DINOS_FRONT, 'scarecrux.png'),
    'Scarecrux2':       os.path.join(DINOS_FRONT, 'scarecrux.png'),
    'Palidian':         os.path.join(DINOS_FRONT, 'Palidian.png'),
    'Palidian2':        os.path.join(DINOS_FRONT, 'Palidian.png'),
    'Rockull':          os.path.join(DINOS_FRONT, 'Rockull.png'),
    'Rockull2':         os.path.join(DINOS_FRONT, 'Rockull.png'),
    'Prickly':          os.path.join(DINOS_FRONT, 'Prickly.png'),
    'Prickly2':         os.path.join(DINOS_FRONT, 'Prickly.png'),
    'Cyflactus':        os.path.join(DINOS_FRONT, 'Cyflactus.png'),
    'Cyflactus2':       os.path.join(DINOS_FRONT, 'Cyflactus.png'),
    'Gourdecrux':       os.path.join(DINOS_FRONT, 'Gourdecrux.png'),
    'Gourdecrux2':      os.path.join(DINOS_FRONT, 'Gourdecrux.png'),
    'Rhysnow':          os.path.join(DINOS_FRONT, 'Rhysnow.png'),
    'Rhysnow2':         os.path.join(DINOS_FRONT, 'Rhysnow.png'),
    'Seasoo':           os.path.join(DINOS_FRONT, 'Seasoo.png'),
    'Seasoo2':          os.path.join(DINOS_FRONT, 'Seasoo.png'),
    'Chomper':          os.path.join(DINOS_FRONT, 'Chomper.png'),
    'Chomper2':         os.path.join(DINOS_FRONT, 'Chomper.png'),
    'Cobaltion':        os.path.join(DINOS_FRONT, 'Cobaltion.png'),
    'Cobaltion2':       os.path.join(DINOS_FRONT, 'Cobaltion.png'),
    'Roxer':            os.path.join(DINOS_FRONT, 'Roxer.png'),
    'Roxer2':           os.path.join(DINOS_FRONT, 'Roxer.png'),
    'Skolt':            os.path.join(DINOS_FRONT, 'Skolt.png'),
    'Skolt2':           os.path.join(DINOS_FRONT, 'Skolt.png'),
    'Frostle':          os.path.join(DINOS_FRONT, 'Frostle.png'),
    'Frostle2':         os.path.join(DINOS_FRONT, 'Frostle.png'),
    'Typhoonray':       os.path.join(DINOS_FRONT, 'Typhoonray.png'),
    'Typhoonray2':      os.path.join(DINOS_FRONT, 'Typhoonray.png'),
    'Rhinecicle':       os.path.join(DINOS_FRONT, 'Rhinecicle.png'),
    'Rhinecicle2':      os.path.join(DINOS_FRONT, 'Rhinecicle.png'),
    'Celestreeyl':      os.path.join(DINOS_FRONT, 'Celestreeyl.png'),
    'Celestreeyl2':     os.path.join(DINOS_FRONT, 'Celestreeyl.png'),
    'Sharka':           os.path.join(DINOS_FRONT, 'Sharka.png'),
    'Sharka2':          os.path.join(DINOS_FRONT, 'Sharka.png'),
    'Deimo':            os.path.join(DINOS_FRONT, 'Deimo.png'),
    'Deimo2':           os.path.join(DINOS_FRONT, 'Deimo.png'),
    'VY':               os.path.join(DINOS_FRONT, 'VY.png'),
    'VY2':              os.path.join(DINOS_FRONT, 'VY.png'),
    'Stormulus':        os.path.join(DINOS_FRONT, 'Stormulus.png'),
    'Stormulus2':       os.path.join(DINOS_FRONT, 'Stormulus.png'),
    'Lavaleo':          os.path.join(DINOS_FRONT, 'Lavaleo.png'),
    'Lavaleo2':         os.path.join(DINOS_FRONT, 'Lavaleo.png'),
    'Pectura':          os.path.join(DINOS_FRONT, 'Pectura.png'),
    'Pectura2':         os.path.join(DINOS_FRONT, 'Pectura.png'),
    'Ghoslink':         os.path.join(DINOS_FRONT, 'Ghoslink.png'),
    'Ghoslink2':        os.path.join(DINOS_FRONT, 'Ghoslink.png'),
}

NPC_SHEETS = {
    # sprite_key -> path to 4x4 spritesheet (32x32 per cell)
    # row 0=down, 1=left, 2=right, 3=up  |  col 0=still, 1=walk, 2=still, 3=walk
    'amber':              os.path.join('assets', 'NPC', 'Professor_Amber.png'),
    'dc_lady':            os.path.join('assets', 'NPC', 'DC_LADY.png'),
    'dcmart_lady':        os.path.join('assets', 'NPC', 'DCMart_LADY.png'),
    'basic_trainer':      os.path.join('assets', 'NPC', 'BasicTrainer.png'),
    'basic_trainer2':     os.path.join('assets', 'NPC', 'BasicTrainer2.png'),
    'basic_trainer_girl': os.path.join('assets', 'NPC', 'BasicGirlTrainer.png'),
    'blk_b':              os.path.join('assets', 'NPC', 'BLK_B.png'),
    'skyy':               os.path.join('assets', 'NPC', 'Skyy.png'),
    'gray':               os.path.join('assets', 'NPC', 'gray.png'),
    'enemy_male':         os.path.join('assets', 'NPC', 'Enemy_Male.png'),
    'scarecrux':          os.path.join('assets', 'NPC', 'scarecrux_overworld.png'),
    'rocko':              os.path.join('assets', 'NPC', 'Beard.png'),
    'log':                os.path.join('assets', 'NPC', 'Log.png'),
    'curfeu':             os.path.join('assets', 'NPC', 'Curfeu.png'),
    'abby':               os.path.join('assets', 'NPC', 'Abby.png'),
    'vanessa':            os.path.join('assets', 'NPC', 'Enemy_Girl.png'),
    'emerson':            os.path.join('assets', 'NPC', 'Emerson.png'),
    'cobaltion':          os.path.join('assets', 'NPC', 'Cobaltion_overworld.png'),
    'sam':                os.path.join('assets', 'NPC', 'Sam.png'),
    'mom':                os.path.join('assets', 'NPC', 'Mom.png'),
    'barley':             os.path.join('assets', 'NPC', 'Volkit_overworld.png'),
    'cade':               os.path.join('assets', 'NPC', 'cade.png'),
    'farmer':             os.path.join('assets', 'NPC', 'farmer.png'),
    'debby':              os.path.join('assets', 'NPC', 'Blue_G.png'),
    'josh':               os.path.join('assets', 'NPC', 'Josh.png'),
    'celestreeyl':        os.path.join('assets', 'NPC', 'Celestreeyl_overworld.png'),
    'sparky':             os.path.join('assets', 'NPC', 'sparky_overworld.png'),
    'carrie':             os.path.join('assets', 'NPC', 'lady2.png'),
}

# Static (non-4x4-sheet) NPC images scaled down to fit inside this (w, h)
# box, aspect ratio kept and transparent padding trimmed. Keyed by NPC_SHEETS key.
NPC_STATIC_FIT = {
    'barley': (32, 32),
    'celestreeyl': (48, 80),   # 1254px source art, ~2.5 tiles tall in the overworld
}

# Maps trainer_id -> NPC_SHEETS key for trainers that share a sprite.
# If a trainer_id isn't listed here, it falls back to its own trainer_id as the key.
NPC_SPRITE_KEY = {
    'ethan':         'basic_trainer',
    'shinji':        'basic_trainer2',
    'gym_trainer_a': 'blk_b',
    'gym_trainer_b': 'blk_b',
    'gym2_trainer_a': 'blk_b',
    'gym2_trainer_b': 'blk_b',
    'gym2_trainer_c': 'blk_b',
    'gym2_trainer_d': 'blk_b',
    'gym3_trainer_a': 'blk_b',
    'gym3_trainer_b': 'blk_b',
    'grunt1':        'enemy_male',
    'grunt2':        'enemy_male',
    'route2_girl':   'basic_trainer_girl',
    'route2_boy':    'basic_trainer',
    'dylan':         'basic_trainer2',
    'john':          'rocko',
    'cornmaze1':     'basic_trainer_girl',
    'cornmaze2':     'basic_trainer',
    'cornmaze3':     'rocko',
    'cornmaze4':     'basic_trainer_girl',
    'gray2':         'gray',
    'pp_grunt1':     'enemy_male',
    'pp_grunt2':     'enemy_male',
    'pp_grunt3':     'enemy_male',
    'pp_grunt_a':    'enemy_male',
    'pp_grunt_b':    'enemy_male',
    'pp_grunt_c':    'enemy_male',
    'pp_grunt_d':    'enemy_male',
    'hq_grunt_a':    'enemy_male',
    'hq_grunt_b':    'enemy_male',
    'vanessa_hq':    'vanessa',
    'gray_home':     'gray',
    'abby_home':     'abby',
    'collector':     'rocko',
    'jill':          'carrie',   # lady2.png
    'becca':         'debby',    # Blue_G.png
}

# Dialogue-box speaker portraits: the display name used in a dialogue tag
# (e.g. "[Log] ...", from _tag_dialogue()/_split_dialogue()'s `name`) ->
# an NPC_SHEETS key to crop a small portrait from. Only named story cast
# members need an entry here; anyone not listed just shows no portrait.
DIALOGUE_PORTRAITS = {
    'Log':     'log',
    'Curfeu':  'curfeu',
    'Abby':    'abby',
    'Skyy':    'skyy',
    'Vanessa': 'vanessa',
    'Amber':   'amber',
    'Gray':    'gray',
    'Emerson': 'emerson',
    'Sam':     'sam',
    'Mom':     'mom',
    'Cade':    'cade',
    'Hollis':  'farmer',
    'Debby':   'debby',
    'Collector': 'rocko',
    'Josh':    'josh',
    'Carrie':  'carrie',
}

DOUBLE_BATTLE_BG_PATH = os.path.join('assets', 'SCREENS', 'Grass_Double Battles.png')

# Per-world NPC definitions: (trainer_id, tile_x, tile_y, facing, sight_range, npc_type)
WORLD_NPCS = {
    'LOST_REGION.world': [
        #Route 1.0 single battles
        ('basic_trainer_girl', 8, 29, 'left', 5, 'trainer'),
        ('ethan', -4, 20, 'up', 4, 'trainer'),

        # ROUTE_1.3 double battle pair — face south (down) watching for the player
        ('basic_trainer',  -2, -4, 'down', 6, 'trainer'),
        ('basic_trainer2', -1, -4, 'down', 6, 'trainer'),
        ('shinji', 13, -12, 'down', 5, 'trainer'),

        # ROUTE_2 double battle pair — ROUTE2.4, face north
        # Only spawns after the corn maze reveal (see game.py _spawn_world_npcs)
        ('grunt1', 50, -20, 'up', 6, 'trainer'),
        ('grunt2', 51, -20, 'up', 6, 'trainer'),

        # ROUTE_2.1 single battle
        ('route2_girl', 36, -37, 'up', 5, 'trainer'),
        ('rocko', 16, -35, 'right', 5, 'trainer'),

        # ROUTE_2.2 single battle
        ('route2_boy', 59, -29, 'up', 5, 'trainer'),
        ('dylan', 67, -38, 'down', 5, 'trainer'),

        # ROUTE2.7 single battle
        ('john', 68, -47, 'up', 5, 'trainer'),

        # CORN_MAZE3 lore prop
        ('scarecrux', 145, -53, 'down', 0, 'story'),
        ('sparky', 101, -71, 'down', 0, 'story'),

        # ROUTE4_2 / PALM_PORT9 single battles
        ('jill', -72, -41, 'down', 5, 'trainer'),
        ('becca', -49, 3, 'right', 5, 'trainer'),

        # Corn Maze single battles
        ('cornmaze1', 96, -56, 'right', 5, 'trainer'),
        ('cornmaze2', 119, -57, 'down', 5, 'trainer'),
        ('cornmaze3', 97, -71, 'down', 5, 'trainer'),
        ('cornmaze4', 115, -48, 'up', 5, 'trainer'),

        # Shadow Team Leader Vanessa — only spawns once the corn maze
        # reveal is done (see game.py _spawn_world_npcs); dormant (sight
        # range 0) until the post-grunt-battle story event activates her.
        ('vanessa', 47, -22, 'down', 0, 'story'),

    ],
    'DINOCENTER.tmx': [
        ('dc_lady',     9, 2, 'down', 0, 'healer'),
        ('dcmart_lady', 3, 2, 'down', 0, 'shop'),   # adjust tile position as needed
    ],
    'RESEARCH_LAB.tmx': [
        ('amber', 10, 3, 'down', 0, 'story'),
    ],
    'GYM1.tmx': [
        ('gym_trainer_a', 6, 8,  'down', 5, 'trainer'),
        ('gym_trainer_b', 13, 8, 'left', 5, 'trainer'),
    ],
    'GYM2.tmx': [
        ('log', 10, 2, 'down', 0, 'trainer'),
        ('gym2_trainer_a', 1, 6,   'right', 5, 'trainer'),
        ('gym2_trainer_b', 1, 3,   'right', 5, 'trainer'),
        ('gym2_trainer_c', 18, 11, 'left',  5, 'trainer'),
        ('gym2_trainer_d', 15, 4,  'up',    5, 'trainer'),
    ],
    # Silverleaf homes — present only early on (see Game._spawn_world_npcs)
    'GRAY_HOUSE.tmx': [
        ('gray_home', 4, 7, 'up', 0, 'story'),   # gone once encounters_unlocked
    ],
    'ABBY_HOUSE.tmx': [
        ('abby_home', 6, 5, 'down', 0, 'story'),   # gone once gym1_leader_defeated
    ],
    'MAZE_HOUSE.tmx': [
        ('carrie', 8, 9, 'down', 0, 'story'),   # warns about the maze at night, gives 5 Repels once
    ],
    'ELDER_HOUSE.tmx': [
        ('farmer', 8, 8, 'down', 0, 'story'),   # Hollis — "Lanterns in the Corn" side quest
    ],
    'HORIZON_CAVE.world': [
        ('celestreeyl', 40, -31, 'down', 0, 'story'),   # top of HORIZON_CAVE8 — light-flash legendary battle
    ],
    'HORIZON_CAVE1.tmx': [
        ('josh', 9, 3, 'down', 0, 'story'),   # Horizon Cave guardian — gone once josh_defeated
    ],
    'SIERRA_HOUSE2.tmx': [
        ('collector', 13, 8, 'down', 0, 'story'),   # Skelig Town visitor — Pectura -> Rhysnow trade
    ],
    'SIERRA_HOUSE3.tmx': [
        ('debby', 8, 7, 'down', 0, 'story'),    # Mom's sister — "Deliver Package to Mom" side quest
    ],
    'HOME_JET.tmx': [
        ('mom',    6, 9, 'down', 0, 'story'),
        ('barley', 4, 9, 'down', 0, 'story'),   # the family Volkit
    ],
    'GYM3.tmx': [
        ('sam', 9, 2, 'down', 0, 'trainer'),
        ('gym3_trainer_a', 16, 6, 'left',  5, 'trainer'),
        ('gym3_trainer_b', 4, 8,  'right', 5, 'trainer'),
    ],
    'POWERPLANT.world': [
        ('pp_grunt_c', 14, 4, 'down', 5, 'trainer'),
        ('pp_grunt_d', 33, 6, 'left', 5, 'trainer'),
    ],
}

ENCOUNTER_BASE_SIZE = 150
ENCOUNTER_DINO_SIZES = {
    # Scale multipliers relative to ENCOUNTER_BASE_SIZE (1.0 = 150x150)
    'Creuw': 0.70,
    'Luna':  1.35,
}


ICON_DINOS_PATH = {
    'Vusion':    os.path.join(DINOS_PATH, 'Vusion_Icon.png'),
}

MAP_ENTITY_PATH = {
    'dinocenter': os.path.join(ASSETS_PATH, 'dc.png'),
}

ITEMS = {
    "DinoPod": {
        "name": "DinoPod",
        "icon": os.path.join(ITEMS_PATH, "dinopod.png"),
        "description": "A basic device used to capture wild Dinos",
        "catch_rate": 0.3,
    },
    "DinoCapsule": {
        "name": "DinoCapsule",
        "icon": os.path.join(ITEMS_PATH, "dinopod+.png"),
        "description": "A powerful device used to capture wild Dinos",
    },
    "Whitepod": {
        "name": "Whitepod",
        "icon": os.path.join(ITEMS_PATH, "ballwhite.png"),
        "description": "Premium pod with a higher catch rate",
        "catch_rate": 0.95,
    },
    "Repel": {
        "name": "Repel",
        "icon": os.path.join(ITEMS_PATH, "repel.png"),
        "description": "Wards off lower-level dinos for 250 steps",
    },
    "Revival Gem": {
        "name": "Revival Gem",
        "icon": os.path.join(ITEMS_PATH, "revival_gem.png"),
        "description": "Revives a fainted Dino with half its max HP back",
    },
    "Mega Spray": {
        "name": "Mega Spray",
        "icon": os.path.join(ITEMS_PATH, "mega_heal.png"),
        "description": "Heals a chosen Dino for 20 HP",
    },
    "Twilight Lunar Shard": {
        "name": "Twilight Lunar Shard",
        "icon": os.path.join(ITEMS_PATH, "twilight_lunar_shard.png"),
        "description": "A lunar shard left behind by Cobaltion, humming with twilight energy",
    },
    "Celestial Solar Shard": {
        "name": "Celestial Solar Shard",
        "icon": os.path.join(ITEMS_PATH, "celestial_solar_shard.png"),
        "description": "A solar shard left behind by Celestreeyl, shimmering with every color of light",
    },
    # TMs: one-time use, teach `tm_move` to a Dino that shares the move's type
    # (see Game.use_tm). Any item with a 'tm_move' key is treated as a TM.
    "TM Solar Flare": {
        "name": "TM Solar Flare",
        "icon": os.path.join(ITEMS_PATH, "tm_magma.png"),
        "description": "Teaches Solar Flare to a Magma-type Dino. Single use.",
        "tm_move": "Solar Flare",
    },
    "TM Leaf Ultima": {
        "name": "TM Leaf Ultima",
        "icon": os.path.join(ITEMS_PATH, "tm_earth.png"),
        "description": "Teaches Leaf Ultima to an Earth-type Dino. Single use.",
        "tm_move": "Leaf Ultima",
    },
    "TM Tree Spin": {
        "name": "TM Tree Spin",
        "icon": os.path.join(ITEMS_PATH, "tm_earth.png"),
        "description": "Teaches Tree Spin to an Earth-type Dino. Single use.",
        "tm_move": "Tree Spin",
    },
    "TM Eternal Blue": {
        "name": "TM Eternal Blue",
        "icon": os.path.join(ITEMS_PATH, "tm_aqua.png"),
        "description": "Teaches Eternal Blue to an Aqua-type Dino. Single use.",
        "tm_move": "Eternal Blue",
    },
}

# Items placed in a world from code rather than from the map's TMX objects.
# world file -> [(tile_x, tile_y, item name)]. Once picked up they stay gone
# (Game.picked_up_world_items), same as TMX items.
SCRIPTED_WORLD_ITEMS = {
    'LOST_REGION.world': [
        (2, -104, "TM Eternal Blue"),
        (-30, 10, "TM Leaf Ultima"),
    ],
}

# Ball type -> icon path (used for heal animation and party display)
BALL_ICONS = {
    'DinoPod':     os.path.join(ITEMS_PATH, 'dinopod.png'),
    'DinoCapsule': os.path.join(ITEMS_PATH, 'dinopod+.png'),
    'Whitepod':    os.path.join(ITEMS_PATH, 'ballwhite.png'),
    'ballwhite':   os.path.join(ITEMS_PATH, 'ballwhite.png'),
}

# Items available in the DinoMart shop
SHOP_ITEMS = [
    {'name': 'DinoPod',      'price': 500},
    {'name': 'Whitepod',     'price': 1500},
    {'name': 'Repel',        'price': 1000},
    {'name': 'Mega Spray',   'price': 1500},
    {'name': 'Revival Gem',  'price': 2000},
]

# Ball pickups on map — Tiled object property "item" -> dino name
DINO_BALL_MAP = {
    'dino1': 'Floravel',
    'dino2': 'Volkit',
    'dino3': 'Corlave',
}
DINO_BALL_LEVEL = 5

SPAWN_POINTS = {
    # 'home':      (352, 1392),   # START_TOWN tile (10,7) in world pixels 32 per tile
    'home':  (608, -672),   # TOWN_1.3 tile (25, -21) in world pixels
}


class MapEntity(pygame.sprite.Sprite):
    def __init__(self, image, tile_x, tile_y, tile_size, solid=True):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (tile_x * tile_size, tile_y * tile_size)
        self.solid = solid

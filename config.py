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
    'Tygrafire':        os.path.join(DINOS_FRONT, 'Tygrafire.png'),
    'Tygrafire2':       os.path.join(DINOS_FRONT, 'Tygrafire.png'),
    'Bouldava':         os.path.join(DINOS_FRONT, 'Bouldava.png'),
    'Bouldava2':        os.path.join(DINOS_FRONT, 'Bouldava.png'),
    'Ghoulflame':       os.path.join(DINOS_FRONT, 'Ghoulflame.png'),
    'Ghoulflame2':      os.path.join(DINOS_FRONT, 'Ghoulflame.png'),
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
}

# Maps trainer_id -> NPC_SHEETS key for trainers that share a sprite.
# If a trainer_id isn't listed here, it falls back to its own trainer_id as the key.
NPC_SPRITE_KEY = {
    'ethan':         'basic_trainer',
    'shinji':        'basic_trainer2',
    'gym_trainer_a': 'blk_b',
    'gym_trainer_b': 'blk_b',
    'grunt1':        'enemy_male',
    'grunt2':        'enemy_male',
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

        # ROUTE_2 double battle pair — top-center, face south
        ('grunt1', 32, -42, 'down', 6, 'trainer'),
        ('grunt2', 33, -42, 'down', 6, 'trainer'),

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
        "catch_rate": 0.9,
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
    {'name': 'DinoPod',  'price': 500},
    {'name': 'Whitepod', 'price': 1500},
    {'name': 'Repel',    'price': 1000},
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

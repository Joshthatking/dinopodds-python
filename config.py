import os
import pygame

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
DARK = "#201624"
LIGHT = "#fffef0"
GRAY = '#3a373b'
LIGHT_GRAY = '#4b484d'
MAGMA = '#f8a060'
AQUA = '#50b0d8'
EARTH = '#64a990'
SOFT_WHITE = '#f0f0f0'
ROCK = "#57513e"
SPIKE = "#d4ba93"
FLYING = "#b1c5da"
LIGHTNING = "#fff646"
ICE = "#15dcee"
ANCIENT = "#712B81"

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
}

NPC_SHEETS = {
    # trainer_id -> path to 4x4 spritesheet (32x32 per cell)
    # row 0=down, 1=left, 2=right, 3=up  |  col 0=still, 1=walk, 2=still, 3=walk
    'amber': os.path.join('assets', 'NPC', 'Professor_Amber.png'),
}

ENCOUNTER_BASE_SIZE = 150
ENCOUNTER_DINO_SIZES = {
    # Scale multipliers relative to ENCOUNTER_BASE_SIZE (1.0 = 150x150)
    'Creuw': 0.70,
    'Luna':  1.35,
}

PLAYER_DINO_PATH = {
    'Vusion':    os.path.join(DINOS_BACK,  'Vusion_back.png'),
    'Anemamace': os.path.join(DINOS_FRONT, 'Anemamace.png'),
    'Corlave':   os.path.join(DINOS_FRONT, 'Corlave.png'),
    'Creuw':   os.path.join(DINOS_FRONT, 'Creuw.png'),
    'Luna':   os.path.join(DINOS_FRONT, 'Luna.png'),

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
        "icon": os.path.join(ITEMS_PATH, "dinopodd.png"),
        "description": "A basic device used to capture wild Dinos",
        "catch_rate": 0.9,
    },
    "DinoCapsule": {
        "name": "DinoCapsule",
        "icon": os.path.join(ITEMS_PATH, "dinpodd.png"),
        "description": "A basic device used to capture wild Dinos",
    },
}

SPAWN_POINTS = {
    # 'home':      (160, 1248),   # START_TOWN tile (10,7) in world pixels
    # 'home':      (160, 1500),   # START_TOWN tile (10,7) in world pixels
    'town1':  (608, -672),   # TOWN_1.3 tile (25, -21) in world pixels
}


class MapEntity(pygame.sprite.Sprite):
    def __init__(self, image, tile_x, tile_y, tile_size, solid=True):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (tile_x * tile_size, tile_y * tile_size)
        self.solid = solid

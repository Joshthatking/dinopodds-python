import os
import pygame
#######################
#### Configurations ###
#######################

#COLORS
BLACK = (0,0,0)
WHITE = (255,255,255)
RED = (255,0,0)
DARK = '#2b292c'
LIGHT = '#c8c8c8'
GRAY = '#3a373b'
LIGHT_GRAY = '#4b484d'
MAGMA = '#f8a060'
AQUA = '#50b0d8'
EARTH = '#64a990'
SOFT_WHITE = '#f0f0f0'



# SCREEN
WIDTH = 640 
HEIGHT = 480 
FPS = 60

#WORLD
TILE_SIZE = 32

# PLAYER
PLAYER_SPEED = TILE_SIZE




FONT_PATH_B = os.path.join('assets','Items', 'PixeloidSans-Bold.ttf')
FONT_PATH = os.path.join('assets','Items', 'PixeloidSans.ttf')

FONT_XS = 12
FONT_SMALL = 16
FONT_MEDIUM = 24
FONT_LARGE = 30

# Just a mapping of font names to (path, size)
FONT_DEFS = {
    "BAG": (FONT_PATH_B, FONT_SMALL),
    "BATTLE": (FONT_PATH_B, FONT_MEDIUM),
    "XS": (FONT_PATH_B, FONT_XS),
    "BAG2": (FONT_PATH_B, FONT_SMALL),
    "PARTY": (FONT_PATH_B, FONT_MEDIUM),
    "DIALOGUE": (FONT_PATH_B, FONT_LARGE),
}

##############
### TILES ####
##############

# tile_images = {
#     "G": pygame.image.load(os.path.join("assets/MapAssets", "grassa.png")),
#     "g": pygame.image.load(os.path.join("assets/MapAssets", "grass_spawn.png")),
#     "W": pygame.image.load(os.path.join("assets/MapAssets", "water1.png")),
#     "t": pygame.image.load(os.path.join("assets/MapAssets", "tree1.png")),
#     "T": pygame.image.load(os.path.join("assets/MapAssets", "tree2.png")),
#     "g": pygame.image.load(os.path.join('assets/MapAssets', 'grass_spawn.png')),
# }

# DINOS_PATH = os.path.join('assets/DINOS')

# DINOS = {
#     'vusion': load_image(os.path.join(DINOS_PATH, 'Vusion_Encounter.png'),alpha = True),
# }

# ENCOUNTER_BG = pygame.image.load(os.path.join('assets/MapAssets/Grass_Encounter.png'))


#spawn blocks/grass/snow
# overlay_tiles = {
#     "g": pygame.image.load(os.path.join('assets/MapAssets', 'grass_spawn.png')),
# }


# Paths
ASSETS_PATH = "assets/MapAssets"
DINOS_PATH = "assets/DINOS"
ITEMS_PATH = "assets/Items"

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
    'vusion': os.path.join(DINOS_PATH, 'Vusion_Encounter.png'),
}


# #Item assets
# ITEMS = {
#     'dp': os.path.join(ITEMS_PATH, 'dinopodd.png'),
#     'dp2': os.path.join(ITEMS_PATH, 'dinpodd.png'),
# }


ITEMS = {
    "DinoPod": {
        "name": "DinoPod",
        "icon": os.path.join(ITEMS_PATH, "dinopodd.png"),
        "description": " A basic device used to capture wild Dinos"
    },
    "DinoCapsule": {
        "name": "DinoCapsule",
        "icon": os.path.join(ITEMS_PATH, "dinpodd.png"),
        "description": "A basic device used to capture wild Dinos"
    }
}

#### SPAWN POINTS

SPAWN_POINTS = {
    'home': (9,5)
}
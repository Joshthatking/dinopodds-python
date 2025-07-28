import os
import pygame
#######################
#### Configurations ###
#######################

#COLORS
BLACK = (0,0,0)
WHITE = (255,255,255)
RED = (255,0,0)


# SCREEN
WIDTH = 640 #480
HEIGHT = 480 #320
FPS = 60

#WORLD
TILE_SIZE = 32

# PLAYER
PLAYER_SPEED = TILE_SIZE





##############
### TILES ####
##############

tile_images = {
    "G": pygame.image.load(os.path.join("assets/MapAssets", "grassa.png")),
    "g": pygame.image.load(os.path.join("assets/MapAssets", "grass_spawn.png")),
    "W": pygame.image.load(os.path.join("assets/MapAssets", "water1.png")),
    "t": pygame.image.load(os.path.join("assets/MapAssets", "tree1.png")),
    "T": pygame.image.load(os.path.join("assets/MapAssets", "tree2.png")),
    "g": pygame.image.load(os.path.join('assets/MapAssets', 'grass_spawn.png')),
}

#spawn blocks/grass/snow
# overlay_tiles = {
#     "g": pygame.image.load(os.path.join('assets/MapAssets', 'grass_spawn.png')),
# }


#### SPAWN POINTS

SPAWN_POINTS = {
    'home': (10,25)
}
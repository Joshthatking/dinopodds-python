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
WIDTH = 640
HEIGHT = 480
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
    "V": pygame.image.load(os.path.join("assets/MapAssets", "grass4.png")),
    "W": pygame.image.load(os.path.join("assets/MapAssets", "water1.png")),
    "T": pygame.image.load(os.path.join("assets/MapAssets", "tree1.png")),
}


#### SPAWN POINTS

SPAWN_POINTS = {
    'home': (5,8)
}
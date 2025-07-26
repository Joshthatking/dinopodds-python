############
## Player ##
############

import pygame
import config
import os

# class Player:
#     def __init__(self):
#         print('player created')

#     def update(self):
#         print('player updated')

#     def render(self,screen):
#         pygame.draw.rect(screen,config.WHITE, (10,10,10,10),2)


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        #load player asset
        player_frontpng = os.path.join('assets', 'front1.png')
        self.image = pygame.image.load(player_frontpng).convert_alpha() # keeps transparency
        self.rect = self.image.get_rect()
        self.rect.center = (config.WIDTH //2, config.HEIGHT //2) #places sprite in center of screen
        self.speed = config.PLAYER_SPEED

    def update(self,keys,game):
        new_x, new_y = self.rect.x, self.rect.y
        speed = self.speed

        map_data = game.world_map

        if keys[pygame.K_a]:
            new_x -= speed
        elif keys[pygame.K_d]:
            new_x += speed
        elif keys[pygame.K_w]:
            new_y -= speed
        elif keys[pygame.K_s]:
            new_y += speed

         # Calculate which tile the player's center would move to
        tile_x = (new_x + self.rect.width // 2) // config.TILE_SIZE
        tile_y = (new_y + self.rect.height // 2) // config.TILE_SIZE

        # Check bounds
        if 0 <= tile_x < len(map_data[0]) and 0 <= tile_y < len(map_data):
            blocked_tiles = ["W", "T"]  # Tiles player cannot walk on
            if map_data[tile_y][tile_x] not in blocked_tiles:
                self.rect.x = new_x
                self.rect.y = new_y
            
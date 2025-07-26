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

    def update(self,keys):
        if keys[pygame.K_a]:
            self.rect.x -= self.speed
        elif keys[pygame.K_d]:
            self.rect.x += self.speed
        elif keys[pygame.K_w]:
            self.rect.y -= self.speed
        elif keys[pygame.K_s]:
            self.rect.y += self.speed
        
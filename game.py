############
### Game ###
############
import pygame
import config
from player import Player
import os 


# class Game:
#     def __init__(self,screen):
#         self.screen = screen
#         self.objects = []

# def set_up(self):
#     player = Player()
#     self.objects.append(player)
#     print('do set up')

# def update(self):
#     print('update')

#     for object in self.objects:
#         object.render()


#WORLD MAP 

#-Start Town  640/480 needs 20/15
start_town = [
     ["G", "G", "G", "G", "G", "G", "G", "G", "G", "G"],
    ["G", "S", "S", "S", "S", "S", "S", "S", "S", "G"],
    ["G", "S", "W", "W", "S", "S", "S", "W", "S", "G"],
    ["G", "S", "S", "S", "S", "S", "S", "S", "S", "G"],
    ["G", "G", "G", "G", "G", "G", "G", "G", "G", "G"]
]






class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        pygame.display.set_caption('DinoPodds')
        self.clock = pygame.time.Clock()
        self.running = True

        self.player = Player()
        self.all_sprites = pygame.sprite.Group() #all active sprites
        self.all_sprites.add(self.player)

    def run(self):
        while self.running:
            self.clock.tick(config.FPS)
            self.events()
            self.update()
            self.draw()
    
    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
    
    def update(self):
        keys = pygame.key.get_pressed()
        self.all_sprites.update(keys)

    def draw(self):
        self.screen.fill(config.BLACK)
        self.all_sprites.draw(self.screen)
        pygame.display.flip()
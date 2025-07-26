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

        self.camera_x = 0
        self.camera_y = 0

                #WORLD MAP 

        #-Start Town  640/480 needs 20/15
        # 20 columns x 15 rows
        self.world_map = [
        list("GGGGGGGGGGGGGGGGGGGG"),
        list("GGGGGGGGGGGGGGGGGGGG"),
        list("GGWWWWGGGGGWWWWWWGG"),
        list("GWWWWWGGGGGGGGWWWG"),
        list("GGWWWWGGGGGWWWWWWGG"),
        list("GGGGGGGGGGGGGGGGGGG"),
        list("GGGGGGGGGGGGGGGGGGG"),
        list("GGGGTTGGGGGGTTGGGGG"),
        list("GGGGGGGGGGGGGGGGGGG"),
        list("GGGGGGGGGGGGGGGGGGG"),
        list("GGWWWWGGGWWWWWWWGGG"),
        list("GGWWWWGGGGGGGGGGGGG"),
        list("GGGWWWGGGGGGGGGGGGG"),
        list("GGGGGGGGGGGGGGGGGGG"),
        list("GGGGGGGGGGGGGGGGGGG"),
        ]



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
        self.all_sprites.update(keys,self)

        #camera logic
        self.camera_x = self.player.rect.centerx - config.WIDTH // 2
        self.camera_y = self.player.rect.centery - config.HEIGHT // 2

        # Optional: Clamp camera so it doesn’t scroll past map edges
        max_x = len(self.world_map[0]) * config.TILE_SIZE - config.WIDTH
        max_y = len(self.world_map) * config.TILE_SIZE - config.HEIGHT
        self.camera_x = max(0, min(self.camera_x, max_x))
        self.camera_y = max(0, min(self.camera_y, max_y))


    def draw(self):
        self.screen.fill(config.BLACK)
        self.draw_map() # v

        for sprite in self.all_sprites: #v
            self.screen.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y - self.camera_y))
            pygame.display.flip()

        # self.all_sprites.draw(self.screen)
        # pygame.display.flip()

    def draw_map(self):
        for index,row in enumerate(self.world_map):
            for col,tile in enumerate(row):
                x = col * config.TILE_SIZE - self.camera_x
                y = index * config.TILE_SIZE - self.camera_x
                if -config.TILE_SIZE < x < config.WIDTH and -config.TILE_SIZE < y < config.HEIGHT:
                    self.screen.blit(config.tile_images[tile],(x,y))
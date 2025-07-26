############
### Game ###
############
import pygame
import config
from player import Player
import os 


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
        list("GGWWWWGGGGGWWWWWWGGT"),
        list("GWWWWWGGGGGGGGWWWGTT"),
        list("GGWWWWGGGGGWWWWWWGGT"),
        list("GGGGGGGGGGGGGGGGGGGT"),
        list("GGGGGGGGGGGGGGGGGGGT"),
        list("GGGGTTGGGGGGTTGGGGGT"),
        list("GGGGGGGGGGGGGGGGGGGT"),
        list("GGGGGGGGGGGGGGGGGGGT"),
        list("GGWWWWGGGWWWWWWWGGGT"),
        list("GGWWWWGGGGGGGGGGGGGT"),
        list("GGGWWWGGGGGGGGGGGGGT"),
        list("GGGGGGGGGGGGGGGGGGGT"),
        list("GGGGGGGGGGGGGGGGGGGT"),
        ]



    def run(self):
        while self.running:
            # self.clock.tick(config.FPS)
            dt = self.clock.tick() / 1000
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

        # #camera logic v1
        # self.camera_x = self.player.rect.centerx - config.WIDTH // 2
        # self.camera_y = self.player.rect.centery - config.HEIGHT // 2

        # Desired camera target (keep player near center) v2
        target_x = self.player.rect.centerx - config.WIDTH // 2
        target_y = self.player.rect.centery - config.HEIGHT // 2

        # Optional: Clamp camera so it doesn’t scroll past map edges
        max_x = len(self.world_map[0]) * config.TILE_SIZE - config.WIDTH
        max_y = len(self.world_map) * config.TILE_SIZE - config.HEIGHT
        # self.camera_x = max(0, min(self.camera_x, max_x)) #v1
        # self.camera_y = max(0, min(self.camera_y, max_y)) #v1
        target_x = max(0, min(target_x, max_x)) #v2
        target_y = max(0, min(target_y, max_y)) #v2

          # Smooth interpolation (lerp) for camera v2
        cam_speed = 0.2  # lower = slower camera, higher = snappier
        self.camera_x += (target_x - self.camera_x) * cam_speed
        self.camera_y += (target_y - self.camera_y) * cam_speed


##### v2
    def draw(self):
        self.screen.fill(config.BLACK)
        self.draw_map()

        # Draw all sprites with camera offset
        for sprite in self.all_sprites:
            self.screen.blit(sprite.image, (sprite.rect.x - int(self.camera_x), sprite.rect.y - int(self.camera_y)))
    
        pygame.display.flip()  # Flip once after drawing everything
    
    
    def draw_map(self):
        for row_index, row in enumerate(self.world_map):
            for col_index, tile in enumerate(row):
                x = col_index * config.TILE_SIZE - int(self.camera_x)
                y = row_index * config.TILE_SIZE - int(self.camera_y)  # FIXED: use camera_y for vertical
                # Only draw tiles that are visible on screen (optimization)
                if -config.TILE_SIZE < x < config.WIDTH and -config.TILE_SIZE < y < config.HEIGHT:
                    self.screen.blit(config.tile_images[tile], (x, y))

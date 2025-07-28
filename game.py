############
### Game ###
############
import pygame
import config
from player import Player
import os 
import csv

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        pygame.display.set_caption('DinoPodds')
        self.clock = pygame.time.Clock()
        self.running = True

        self.player = Player(spawn_point='home')
        self.all_sprites = pygame.sprite.Group() #all active sprites
        self.all_sprites.add(self.player)

        self.camera_x = 0
        self.camera_y = 0

        #Zoom
        self.zoom = 1.25 #normal display size 1.0
        self.render_surface = pygame.Surface((config.WIDTH // self.zoom, config.HEIGHT // self.zoom))

        #-Start Town  640/480 needs 20/15
        # 20 columns x 15 rows
        # CSV MAP
        self.world_map = self.load_csv_map('MAP_DINO.csv')

        #Overlay Tiles


    def load_csv_map(self, filename):
        path = os.path.join('assets/MapAssets', filename)
        with open(path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            return [[cell.strip() if cell.strip() else 'T' for cell in row] for row in reader]  # Replace blanks with 'G'


    def run(self):
        while self.running:
            self.clock.tick(config.FPS)
            # dt = self.clock.tick() / 1000.0 #delta time in seconds
            self.events()
            self.update()#dt)
            self.draw()
    
    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                #Zoom in controls
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:  # Zoom in
                    self.set_zoom(self.zoom + .5)
                elif event.key == pygame.K_MINUS:  # Zoom out
                    self.set_zoom(self.zoom - .5)
    
    def update(self):#,dt):
        keys = pygame.key.get_pressed()
        self.all_sprites.update(keys,self)#,dt)
        self.update_camera() #keeps camera locked on player
        

        # Desired camera target (keep player near center) v2
        target_x = self.player.rect.centerx - config.WIDTH // 2
        target_y = self.player.rect.centery - config.HEIGHT // 2

        # Optional: Clamp camera so it doesn’t scroll past map edges
        max_x = len(self.world_map[0]) * config.TILE_SIZE - config.WIDTH
        max_y = len(self.world_map) * config.TILE_SIZE - config.HEIGHT

        target_x = max(0, min(target_x, max_x)) #v2
        target_y = max(0, min(target_y, max_y)) #v2

          # Smooth interpolation (lerp) for camera v2
        cam_speed = 0.2  # lower = slower camera, higher = snappier
        self.camera_x += (target_x - self.camera_x) * cam_speed
        self.camera_y += (target_y - self.camera_y) * cam_speed


##### Draw Method
    def draw(self):
        # 1. Clear the smaller render surface
        self.render_surface.fill(config.BLACK)

        # 2. Draw the map on the smaller surface
        self.draw_map(surface=self.render_surface)

        # 3. Draw all sprites adjusted for camera
        for sprite in self.all_sprites:
            self.render_surface.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y - self.camera_y))
            # self.player.draw(self.render_surface, self.camera_x, self.camera_y) # new logic for overlay tiles

        
        #3.5 Overlay Tiles
        # self.draw_overlays(self.render_surface) #draw overlays on top

        # 4. Scale up to the main screen for zoom
        scaled_surface = pygame.transform.scale(self.render_surface, (config.WIDTH, config.HEIGHT))
        self.screen.blit(scaled_surface, (0, 0))

    # 5. Flip display
        pygame.display.flip()
    
    def draw_map(self, surface):
        for index, row in enumerate(self.world_map):
            for col, tile in enumerate(row):
                if not tile:  # skip blanks
                    continue
                x = col * config.TILE_SIZE - self.camera_x
                y = index * config.TILE_SIZE - self.camera_y
                surface.blit(config.tile_images[tile], (x, y))


    # Draw overlays on top of player later


        # for index, row in enumerate(self.world_map):
        #     for col, tile in enumerate(row):
        #         x = col * config.TILE_SIZE - self.camera_x
        #         y = index * config.TILE_SIZE - self.camera_y
        #         if -config.TILE_SIZE < x < config.WIDTH and -config.TILE_SIZE < y < config.HEIGHT:
        #             if tile != '':
        #                 surface.blit(config.tile_images[tile], (x, y))

    #logic for overlay tiles
    # def draw_overlays(self, surface):
    #     for y, row in enumerate(self.world_map):
    #         for x, tile in enumerate(row):
    #             if tile in config.overlay_tiles:
    #                 screen_x = x * config.TILE_SIZE - self.camera_x
    #                 screen_y = y * config.TILE_SIZE - self.camera_y

    #                 # Get overlay image
    #                 overlay = config.overlay_tiles[tile]

    #                 # Create a clipped version to only cover bottom half of tile
    #                 clipped_overlay = overlay.subsurface((0, overlay.get_height() // 2, overlay.get_width(), overlay.get_height() // 2))

    #                 # Blit only the bottom half (covers player's feet)
    #                 surface.blit(clipped_overlay, (screen_x, screen_y + overlay.get_height() // 2))




    def update_camera(self):
        # Center the camera based on the *render surface* size
        render_w = config.WIDTH // self.zoom
        render_h = config.HEIGHT // self.zoom
        self.camera_x = self.player.rect.centerx - render_w // 2
        self.camera_y = self.player.rect.centery - render_h // 2

        # Clamp to map bounds
        max_x = len(self.world_map[0]) * config.TILE_SIZE - render_w
        max_y = len(self.world_map) * config.TILE_SIZE - render_h
        self.camera_x = max(0, min(self.camera_x, max_x))
        self.camera_y = max(0, min(self.camera_y, max_y))

    

    #Zoom switch
    def set_zoom(self, zoom):
        self.zoom = round(max(1.0, min(1.75, zoom)),2)  # clamp between 1.0x and 1.75x
        render_w = int(config.WIDTH / self.zoom)
        render_h = int(config.HEIGHT / self.zoom)
        self.render_surface = pygame.Surface((render_w, render_h))
        self.update_camera()  # Recenter after zoom





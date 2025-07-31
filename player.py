############
## Player ##
############

import pygame
import config
import os
import random


class Player(pygame.sprite.Sprite):
    def __init__(self, spawn_point = 'home'):
        super().__init__()
        #load player asset
        # player_frontpng = os.path.join('assets', 'Jet_Front.png') #v1 single idle frame

        # Walking Animations for Jet (main character)
        self.animations = {
            'down': [pygame.image.load(f'assets/Jet/Jet_Front{i}.png').convert_alpha() for i in range(1,5)],
            'up': [pygame.image.load(f'assets/Jet/Jet_Back{i}.png').convert_alpha() for i in range(1,5)],
            'right': [pygame.image.load(f'assets/Jet/Jet_Side{i}.png').convert_alpha() for i in range(1,5)],
            'left': [pygame.image.load(f'assets/Jet/Jet_SideL{i}.png').convert_alpha() for i in range(1,5)]
        }

        self.direction = 'down'
        self.image = self.animations[self.direction][0]
        # self.image = pygame.image.load(player_frontpng).convert_alpha() # keeps transparency v1
        self.rect = self.image.get_rect() #player hitbox 32x32

        #Spawn Player
        col,row = config.SPAWN_POINTS.get(spawn_point,(0,0))
        self.spawn_on_tile(col,row)
        # self.rect = pygame.Rect(0,0,30,30) # for 32x32 sprite shrunken hitbox

        # start_col = config.WIDTH // 2 // config.TILE_SIZE
        # start_row = config.WIDTH // 2 // config.TILE_SIZE
        # self.rect.topleft = (start_col*config.TILE_SIZE, start_row* config.TILE_SIZE)

        # self.rect.center = (config.WIDTH //2, config.HEIGHT //2) #places sprite in center of screen 

        #Movement
        self.tile_size = config.TILE_SIZE
        self.moving = False
        self.target_x = self.rect.x
        self.target_y = self.rect.y
        self.move_speed = 5 #speed 2 with anim speed of .2 works well

        #Animation
        self.anim_index = 0
        self.anim_timer = 0
        self.anim_speed = .2 # how fast frames change #.2 with speed of 2 seems perfect


        # #Overlay Player Logic
        # w, h = self.image.get_size()
        # # Create semi-transparent bottom half copy
        # self.image_overlay = self.image.copy()
        # bottom_rect = pygame.Rect(0, h//2, w, h//2)
        # transparent_surf = pygame.Surface((w, h//2), pygame.SRCALPHA)
        # transparent_surf.fill((255, 255, 255, 128))  # 50% opacity
        # self.image_overlay.blit(transparent_surf, bottom_rect.topleft, special_flags=pygame.BLEND_RGBA_MULT)
        # self.in_overlay_tile = False

    # # Player Draw Method for overlay tiles and regular tiles
    # def draw(self, surface, camera_x, camera_y):
    #     pos = (self.rect.x - camera_x, self.rect.y - camera_y)
    #     if self.in_overlay_tile:
    #         surface.blit(self.image_overlay, pos)
    #     else:
    #         surface.blit(self.image, pos)

    #Player Spawn Tile Logic to be directly lined up in 32x32 tile
    def spawn_on_tile(self,col,row):
        self.rect.topleft = (col* config.TILE_SIZE, row* config.TILE_SIZE)


    def update(self, keys, game):#,dt):
        if game.state != 'world':
            return
        map_data = game.world_map
        # self.move_speed = 64 # 128px/sec (crosses a 32px tile in .25s)

        # If moving, continue sliding toward target
        if self.moving:
            # Move toward target w/ speed

            if self.rect.x < self.target_x:
                self.rect.x = min(self.rect.x + self.move_speed  , self.target_x)
            elif self.rect.x > self.target_x:
                self.rect.x = max(self.rect.x - self.move_speed , self.target_x)
            if self.rect.y < self.target_y:
                self.rect.y = min(self.rect.y + self.move_speed , self.target_y)
            elif self.rect.y > self.target_y:
                self.rect.y = max(self.rect.y - self.move_speed , self.target_y)

            # Animate walk
            self.anim_timer += self.anim_speed
            if self.anim_timer >= 1:
                self.anim_timer = 0
                self.anim_index = (self.anim_index + 1) % 4
            self.image = self.animations[self.direction][self.anim_index]

            # Stop when we reach the tile
            if self.rect.x == self.target_x and self.rect.y == self.target_y:
            # if abs(self.rect.x - self.target_x) < 0.5 and abs(self.rect.y - self.target_y) < 0.5:
            #     self.rect.x = self.target_x
            #     self.rect.y = self.target_y
            #     self.moving = False
                self.moving = False
                self.anim_index = 0
                self.image = self.animations[self.direction][0]
                
                #Encounter after finishing tile 
                if game.state == 'world':
                    tile_x = (self.rect.centerx) // self.tile_size
                    tile_y = (self.rect.centery) // self.tile_size
                    if 0 <= tile_y < len(game.world_map) and 0 <= tile_x < len(game.world_map[0]):
                        current_tile = game.world_map[tile_y][tile_x]
                        if current_tile == 'g':  # grass tile
                            import random
                            if random.random() < 0.15:  # 15% chance
                                game.trigger_encounter()



            return  # Don’t take new input until we finish moving
        

                #dt method
        if self.moving:
            return  # Don't take new input until done moving

        # If NOT moving, check for key press
        new_x, new_y = self.rect.x, self.rect.y
        input_detected = False

        # First update facing/direction regardless
        if keys[pygame.K_a]:
            self.facing = 'left'
            self.direction = 'left'
            new_x -= self.tile_size #left one tile
            input_detected = True
        elif keys[pygame.K_d]:
            self.facing = 'right'
            self.direction = 'right'
            new_x += self.tile_size
            input_detected = True
        elif keys[pygame.K_w]:
            self.facing = 'up'
            self.direction = 'up'
            new_y -= self.tile_size
            input_detected = True
        elif keys[pygame.K_s]:
            self.facing = 'down'
            self.direction = 'down'
            new_y += self.tile_size
            input_detected = True

        if not input_detected:
            return  # no input

        # Check collision
        tile_x = (new_x + self.rect.width // 2) // self.tile_size
        tile_y = (new_y + self.rect.height // 2) // self.tile_size
        blocked_tiles = ["W", "T", "t"]

        # Add item positions as blocked
        for (ix, iy) in game.items_on_map:
            if (tile_x, tile_y) == (ix, iy):
                blocked = True
                break
        else:
            blocked = False
        if 0 <= tile_x < len(map_data[0]) and 0 <= tile_y < len(map_data): #if the tile is on the map
            if map_data[tile_y][tile_x] not in blocked_tiles and not blocked:
                # Set target and start moving
                self.target_x = new_x
                self.target_y = new_y
                self.moving = True

                # Jump immediately to walking frame
                self.anim_index = 1
                self.anim_timer = 0
                self.image = self.animations[self.direction][self.anim_index]
            

            #Direction Facing Collision Logic
            else:
                # Blocked tile: no movement but keep facing updated
                self.moving = False
                self.anim_index = 0
                self.image = self.animations[self.direction][0]
        else:
            # Out of bounds: no movement but keep facing updated
            self.moving = False
            self.anim_index = 0
            self.image = self.animations[self.direction][0]
        
        # --- NEW: Check for random encounter ---
        # if game.state == "world":  # Only trigger if in world state
        #     tile_x = self.rect.x // config.TILE_SIZE
        #     tile_y = self.rect.y // config.TILE_SIZE
        #     # Make sure the tile is within the map before using it
        # if 0 <= tile_y < len(game.world_map) and 0 <= tile_x < len(game.world_map[0]):
        #     current_tile = game.world_map[tile_y][tile_x]
        #     if current_tile == 'g':  # Grass tile
        #         if random.random() < .15:  # 15% chance
        #             game.trigger_encounter()
    # ---------------------------------------




                  # CHANGE SPAWN LOGIC FOR LATER
                # def change_spawn(self, spawn_point): 
                #     col, row = config.SPAWN_POINTS.get(spawn_point, (0, 0))
                #     self.spawn_on_tile(col, row)
                #     self.moving = False  # Reset movement if you want
        
        
        # # OVERLAY Player Walking Logic
        # foot_x = self.rect.centerx + game.camera_x
        # foot_y = self.rect.bottom - 1 + game.camera_y
        # tile_x = int(foot_x // config.TILE_SIZE)
        # tile_y = int(foot_y // config.TILE_SIZE)

        # self.in_overlay_tile = False
        # if 0 <= tile_y < len(game.world_map) and 0 <= tile_x < len(game.world_map[0]):
        #     current_tile = game.world_map[tile_y][tile_x]
        #     if current_tile in config.overlay_tiles:
        #         self.in_overlay_tile = True
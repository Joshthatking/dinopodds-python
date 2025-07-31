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

        #Movement
        self.tile_size = config.TILE_SIZE
        self.moving = False
        self.target_x = self.rect.x
        self.target_y = self.rect.y
        self.move_speed = 128 #speed 2 with anim speed of .2 works well

        #delta time additional info
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)



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


    def update(self, keys, game, dt):
        if game.state != 'world':
            return

        # If currently moving, slide smoothly towards target tile
        if self.moving:
            step = self.move_speed * dt
            #Horizontal Movement
            if self.pos_x < self.target_x:
                self.pos_x = min(self.pos_x + step , self.target_x)
            elif self.pos_x > self.target_x:
                self.pos_x = max(self.pos_x - step , self.target_x)
            #Vertical Movement
            if self.pos_y < self.target_y:
                self.pos_y = min(self.pos_y + step , self.target_y)
            elif self.pos_y > self.target_y:
                self.pos_y = max(self.pos_y - step , self.target_y)
            
            self.rect.x = round(self.pos_x)
            self.rect.y = round(self.pos_y)
        


            # Animate walking
            self.anim_timer += dt
            if self.anim_timer >= 0.08: #.08-/.1 looks ok
                self.anim_timer = 0
                self.anim_index = (self.anim_index + 1) % 4
            self.image = self.animations[self.direction][self.anim_index]

            # Check if we reached the target tile exactly
            if self.rect.x == self.target_x and self.rect.y == self.target_y:
                self.moving = False
                self.anim_index = 0
                self.image = self.animations[self.direction][0]

                # Optional: Trigger encounters here if needed
                # (your encounter logic)

            return  # Don't process input while moving

        # Not moving - handle input for next tile
        new_x, new_y = self.rect.x, self.rect.y
        input_detected = False
        facing_changed = False

        # Update facing and set new target tile based on key press
        if keys[pygame.K_a]:
            if self.direction != 'left':
                self.facing = 'left'
                self.direction = 'left'
                facing_changed = True
            else:
                new_x -= self.tile_size
                input_detected = True
        elif keys[pygame.K_d]:
            if self.direction != 'right':
                self.facing = 'right'
                self.direction = 'right'
                facing_changed = True
            else:
                new_x += self.tile_size
                input_detected = True
        elif keys[pygame.K_w]:
            if self.direction != 'up':
                self.facing = 'up'
                self.direction = 'up'
                facing_changed = True
            else:
                new_y -= self.tile_size
                input_detected = True
        elif keys[pygame.K_s]:
            if self.direction != 'down':
                self.facing = 'down'
                self.direction = 'down'
                facing_changed = True
            else:
                new_y += self.tile_size
                input_detected = True
        
        #If facing changed but no movement (blocked) just update sprite frame
        if facing_changed:
            self.anim_index = 0
            self.image = self.animations[self.direction][self.anim_index]
            return

        if not input_detected:
            return  # no input to process

        # Collision check
        tile_x = (new_x + self.rect.width // 2) // self.tile_size
        tile_y = (new_y + self.rect.height // 2) // self.tile_size
        blocked_tiles = ["W", "T", "t"]

        # Check if any item is blocking tile
        blocked = False
        for (ix, iy) in game.items_on_map:
            if (tile_x, tile_y) == (ix, iy):
                blocked = True
                break

        # Check map boundaries and tile blockage
        if (0 <= tile_y < len(game.world_map) and
            0 <= tile_x < len(game.world_map[0]) and
            game.world_map[tile_y][tile_x] not in blocked_tiles and
            not blocked):

            # Set new target tile to move to
            self.target_x = new_x
            self.target_y = new_y
            self.moving = True

            # Start walking animation
            self.anim_index = 1
            self.anim_timer = 0
            self.image = self.animations[self.direction][self.anim_index]

        else:
            # Blocked: just update facing without moving
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
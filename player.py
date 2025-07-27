############
## Player ##
############

import pygame
import config
import os


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
        self.move_speed = 2 #speed 2 with anim speed of .2 works well

        #Animation
        self.anim_index = 0
        self.anim_timer = 0
        self.anim_speed = .2 # how fast frames change #.2 with speed of 2 seems perfect
    
    def spawn_on_tile(self,col,row):
        self.rect.topleft = (col* config.TILE_SIZE, row* config.TILE_SIZE)


    def update(self, keys, game):#,dt):
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
            return  # Don’t take new input until we finish moving
        

                #dt method
        # if self.moving:
        #     return  # Don't take new input until done moving





        # If NOT moving, check for key press
        new_x, new_y = self.rect.x, self.rect.y
        if keys[pygame.K_a]:
            new_x -= self.tile_size
            self.direction = 'left'
        elif keys[pygame.K_d]:
            new_x += self.tile_size
            self.direction = 'right'
        elif keys[pygame.K_w]:
            new_y -= self.tile_size
            self.direction = 'up'
        elif keys[pygame.K_s]:
            new_y += self.tile_size
            self.direction = 'down'
        else:
            return  # no input

        # Check collision
        tile_x = (new_x + self.rect.width // 2) // self.tile_size
        tile_y = (new_y + self.rect.height // 2) // self.tile_size
        blocked_tiles = ["W", "T"]
        if 0 <= tile_x < len(map_data[0]) and 0 <= tile_y < len(map_data):
            if map_data[tile_y][tile_x] not in blocked_tiles:
                # Set target and start moving
                self.target_x = new_x
                self.target_y = new_y
                self.moving = True

                # Jump immediately to walking frame
                self.anim_index = 1
                self.anim_timer = 0
                self.image = self.animations[self.direction][self.anim_index]




                  # CHANGE SPAWN LOGIC FOR LATER
                # def change_spawn(self, spawn_point): 
                #     col, row = config.SPAWN_POINTS.get(spawn_point, (0, 0))
                #     self.spawn_on_tile(col, row)
                #     self.moving = False  # Reset movement if you want
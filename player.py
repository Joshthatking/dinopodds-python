import pygame
import config
import random


class Player(pygame.sprite.Sprite):
    def __init__(self, spawn_point='home'):
        super().__init__()
        self.animations = {
            'down':  [pygame.image.load(f'assets/Jet/Jet_Front{i}.png').convert_alpha() for i in range(1, 5)],
            'up':    [pygame.image.load(f'assets/Jet/Jet_Back{i}.png').convert_alpha() for i in range(1, 5)],
            'right': [pygame.image.load(f'assets/Jet/Jet_Side{i}.png').convert_alpha() for i in range(1, 5)],
            'left':  [pygame.image.load(f'assets/Jet/Jet_SideL{i}.png').convert_alpha() for i in range(1, 5)],
        }
        self.direction = 'down'
        self.facing = 'down'
        self.image = self.animations['down'][0]
        self.rect = self.image.get_rect()

        col, row = config.SPAWN_POINTS.get(spawn_point, (0, 0))
        self.rect.topleft = (col * config.TILE_SIZE, row * config.TILE_SIZE)

        self.tile_size = config.TILE_SIZE
        self.moving = False
        self.target_x = self.rect.x
        self.target_y = self.rect.y
        self.move_speed = 128

        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)

        self.anim_index = 0
        self.anim_timer = 0

    def update(self, keys, game, dt):
        if game.state_stack[-1] != 'world' or (game.message_box and game.message_box.visible):
            return

        if self.moving:
            step = self.move_speed * dt
            if self.pos_x < self.target_x:
                self.pos_x = min(self.pos_x + step, self.target_x)
            elif self.pos_x > self.target_x:
                self.pos_x = max(self.pos_x - step, self.target_x)
            if self.pos_y < self.target_y:
                self.pos_y = min(self.pos_y + step, self.target_y)
            elif self.pos_y > self.target_y:
                self.pos_y = max(self.pos_y - step, self.target_y)

            self.rect.x = round(self.pos_x)
            self.rect.y = round(self.pos_y)

            self.anim_timer += dt
            if self.anim_timer >= 0.08:
                self.anim_timer = 0
                self.anim_index = (self.anim_index + 1) % 4
            self.image = self.animations[self.direction][self.anim_index]

            if self.rect.x == self.target_x and self.rect.y == self.target_y:
                self.moving = False
                self.anim_index = 0
                self.image = self.animations[self.direction][0]
            return

        new_x, new_y = self.rect.x, self.rect.y
        input_detected = False
        facing_changed = False

        if keys[pygame.K_a]:
            if self.direction != 'left':
                self.facing = self.direction = 'left'
                facing_changed = True
            else:
                new_x -= self.tile_size
                input_detected = True
        elif keys[pygame.K_d]:
            if self.direction != 'right':
                self.facing = self.direction = 'right'
                facing_changed = True
            else:
                new_x += self.tile_size
                input_detected = True
        elif keys[pygame.K_w]:
            if self.direction != 'up':
                self.facing = self.direction = 'up'
                facing_changed = True
            else:
                new_y -= self.tile_size
                input_detected = True
        elif keys[pygame.K_s]:
            if self.direction != 'down':
                self.facing = self.direction = 'down'
                facing_changed = True
            else:
                new_y += self.tile_size
                input_detected = True

        if facing_changed:
            self.anim_index = 0
            self.image = self.animations[self.direction][0]
            return

        if not input_detected:
            return

        tile_x = (new_x + self.rect.width // 2) // self.tile_size
        tile_y = (new_y + self.rect.height // 2) // self.tile_size
        blocked_tiles = {"W", "T", "t"}

        blocked = (tile_x, tile_y) in game.solid_tiles or any(
            (tile_x, tile_y) == pos for pos in game.items_on_map
        )

        if (0 <= tile_y < len(game.world_map) and
                0 <= tile_x < len(game.world_map[0]) and
                game.world_map[tile_y][tile_x] not in blocked_tiles and
                not blocked):
            self.target_x = new_x
            self.target_y = new_y
            self.moving = True
            self.anim_index = 1
            self.anim_timer = 0
            self.image = self.animations[self.direction][1]
        else:
            self.moving = False
            self.anim_index = 0
            self.image = self.animations[self.direction][0]

        self.check_for_encounter(game)

    def check_for_encounter(self, game):
        if game.state_stack[-1] != 'world':
            return
        tile_x = self.rect.x // config.TILE_SIZE
        tile_y = self.rect.y // config.TILE_SIZE
        if (0 <= tile_y < len(game.world_map) and
                0 <= tile_x < len(game.world_map[0]) and
                game.world_map[tile_y][tile_x] == 'g' and
                random.random() < 0.15):
            game.trigger_encounter()

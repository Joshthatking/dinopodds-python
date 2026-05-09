import pygame
import config
import random
from data import ENCOUNTER_ZONES


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

        px, py = config.SPAWN_POINTS.get(spawn_point, (0, 0))
        self.rect.topleft = (px, py)

        self.tile_size = config.TILE_SIZE
        self.moving = False
        self.target_x = self.rect.x
        self.target_y = self.rect.y
        self.move_speed = 128

        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)

        self.anim_index = 0
        self.anim_timer = 0
        self.turn_timer = 0.0
        self.turn_delay = 0.08

    def update(self, keys, game, dt):
        if (game.state_stack[-1] != 'world' or
                (game.message_box and game.message_box.visible) or
                getattr(game, 'heal_anim', None) or
                getattr(game, 'yes_no_prompt', None)):
            return
        if any(npc.state in ('spotted', 'walking') for npc in getattr(game, 'npcs', [])):
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

        if self.turn_timer > 0:
            self.turn_timer = max(0.0, self.turn_timer - dt)
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
            self.turn_timer = self.turn_delay
            self.anim_index = 0
            self.image = self.animations[self.direction][0]
            return

        if not input_detected:
            return

        tile_x = (new_x + self.rect.width // 2) // self.tile_size
        tile_y = (new_y + self.rect.height // 2) // self.tile_size
        blocked = (tile_x, tile_y) in game.solid_tiles or \
                  (tile_x, tile_y) in game.solid_tile_coords or \
                  any((tile_x, tile_y) == pos for pos in game.items_on_map)

        min_tx, min_ty, max_tx, max_ty = game.world_bounds
        if (min_tx <= tile_x < max_tx and
                min_ty <= tile_y < max_ty and
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
        self.check_for_entrance(game)

    def check_for_encounter(self, game):
        if game.state_stack[-1] != 'world':
            return
        tile_x = self.rect.x // config.TILE_SIZE
        tile_y = self.rect.y // config.TILE_SIZE
        on_enc = (tile_x, tile_y) in game.encounter_tile_coords

        if getattr(game, 'repel_steps', 0) > 0:
            game.repel_steps -= 1
            if game.repel_steps == 0:
                game.message_box.queue_messages(["Repel wore off!"], wait_for_input=True)
                return
            if on_enc:
                lead = game.player_dinos[game.active_dino_index] if game.player_dinos else None
                lead_level = lead['level'] if lead else 1
                zone = game.get_player_zone(tile_x, tile_y)
                zone_data = ENCOUNTER_ZONES.get(zone, {})
                if zone_data.get('level_range', (99, 99))[1] < lead_level:
                    return  # all dinos here are lower level, repel blocks them
            else:
                return

        if on_enc and random.random() < 0.15:
            game.trigger_encounter()

    def check_for_entrance(self, game):
        if game.state_stack[-1] != 'world':
            return
        tile_x = self.rect.x // config.TILE_SIZE
        tile_y = self.rect.y // config.TILE_SIZE
        print(f"[DEBUG] player tile=({tile_x},{tile_y})  entrances={list(game.entrance_tile_coords.keys())}  exits={list(game.exit_tile_coords)}")
        if (tile_x, tile_y) in game.entrance_tile_coords:
            game.trigger_entrance(game.entrance_tile_coords[(tile_x, tile_y)], tile_x, tile_y)
        elif (tile_x, tile_y) in game.exit_tile_coords:
            game.trigger_exit()

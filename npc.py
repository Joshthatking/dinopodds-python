import pygame
import os
import config
from data import TRAINER_DATA

_ROW_DIR  = {0: 'down', 1: 'left', 2: 'right', 3: 'up'}
_ALL_DIRS = ['down', 'left', 'right', 'up']


def _load_sheet(trainer_id):
    """
    Load a 4x4 spritesheet → {direction: [col0, col1, col2, col3]}.
    Col layout: 0=still, 1=walk, 2=still, 3=walk  (cycles to still-walk-still-walk).
    Falls back to a solid-colour rect if no sheet exists.
    """
    sprite_key = config.NPC_SPRITE_KEY.get(trainer_id, trainer_id)
    path = config.NPC_SHEETS.get(sprite_key)
    ts   = config.TILE_SIZE
    if path and os.path.exists(path):
        sheet  = pygame.image.load(path).convert_alpha()
        frames = {}
        for row, direction in _ROW_DIR.items():
            frames[direction] = []
            for col in range(4):
                cell = pygame.Surface((32, 32), pygame.SRCALPHA)
                cell.blit(sheet, (0, 0), (col * 32, row * 32, 32, 32))
                if ts != 32:
                    cell = pygame.transform.scale(cell, (ts, ts))
                frames[direction].append(cell)
        return frames
    surf = pygame.Surface((ts, ts))
    surf.fill((180, 100, 50))
    return {d: [surf] * 4 for d in _ALL_DIRS}


class NPC:
    _FACING  = {(1, 0): 'right', (-1, 0): 'left', (0, 1): 'down', (0, -1): 'up'}
    _DIR_VEC = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}

    def __init__(self, trainer_id, tile_x, tile_y, facing='down', sight_range=4, npc_type='trainer'):
        self.trainer_id  = trainer_id
        self.tile_x      = tile_x
        self.tile_y      = tile_y
        self.facing      = facing
        self.sight_range = sight_range
        self.npc_type    = npc_type  # 'trainer' | 'healer'
        self.state       = 'idle'   # idle | spotted | walking | done
        self.defeated    = TRAINER_DATA.get(trainer_id, {}).get('defeated', False)

        self.spot_timer = 0.0

        # Smooth movement — mirrors player.py exactly
        ts           = config.TILE_SIZE
        self.pos_x   = float(tile_x * ts)
        self.pos_y   = float(tile_y * ts)
        self.target_x = self.pos_x
        self.target_y = self.pos_y
        self.is_moving  = False
        self.move_speed = 128          # px/s — same as player

        # Walk animation — same timing as player (0.08 s per frame, 4-frame cycle)
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.08

        self.frames = _load_sheet(trainer_id)
        self.rect   = pygame.Rect(tile_x * ts, tile_y * ts, ts, ts)
        self._exclaim_font = None

    # ── current sprite ────────────────────────────────────────────────────────

    def _current_image(self):
        col = self.anim_frame if (self.is_moving or self.state == 'walking') else 0
        return self.frames[self.facing][col]

    # ── sight helpers ─────────────────────────────────────────────────────────

    def _sight_tiles(self):
        dx, dy = self._DIR_VEC[self.facing]
        return [(self.tile_x + dx * i, self.tile_y + dy * i)
                for i in range(1, self.sight_range + 1)]

    def _player_tile(self, player):
        return player.rect.x // config.TILE_SIZE, player.rect.y // config.TILE_SIZE

    def can_see_player(self, player):
        return self._player_tile(player) in self._sight_tiles()

    def _pixel_close(self, player):
        """True when NPC sprite edge is touching the player sprite edge."""
        dx = abs(self.rect.centerx - player.rect.centerx)
        dy = abs(self.rect.centery  - player.rect.centery)
        return dx + dy <= config.TILE_SIZE

    # ── movement ──────────────────────────────────────────────────────────────

    def _start_step(self, player, solid, map_solid=None):
        px, py = self._player_tile(player)
        dx, dy = px - self.tile_x, py - self.tile_y
        if   abs(dx) >= abs(dy) and dx != 0: sx, sy = (1 if dx > 0 else -1), 0
        elif dy != 0:                         sx, sy = 0, (1 if dy > 0 else -1)
        else:                                 return

        nx, ny = self.tile_x + sx, self.tile_y + sy
        if (nx, ny) not in solid and (map_solid is None or (nx, ny) not in map_solid):
            solid.discard((self.tile_x, self.tile_y))
            self.tile_x, self.tile_y = nx, ny
            solid.add((nx, ny))
            self.facing   = self._FACING[(sx, sy)]
            self.target_x = float(nx * config.TILE_SIZE)
            self.target_y = float(ny * config.TILE_SIZE)
            self.is_moving = True
            self.anim_frame = 1
            self.anim_timer = 0.0

    def _slide(self, dt):
        """Interpolate pos toward target, identical to player movement."""
        speed = self.move_speed * dt
        if   self.pos_x < self.target_x: self.pos_x = min(self.pos_x + speed, self.target_x)
        elif self.pos_x > self.target_x: self.pos_x = max(self.pos_x - speed, self.target_x)
        if   self.pos_y < self.target_y: self.pos_y = min(self.pos_y + speed, self.target_y)
        elif self.pos_y > self.target_y: self.pos_y = max(self.pos_y - speed, self.target_y)
        self.rect.x = round(self.pos_x)
        self.rect.y = round(self.pos_y)
        if self.pos_x == self.target_x and self.pos_y == self.target_y:
            self.is_moving  = False
            self.anim_frame = 0

    # ── update ────────────────────────────────────────────────────────────────

    def _step_toward_tile(self, tx, ty, solid, map_solid=None):
        """Move one tile toward (tx, ty), identical logic to _start_step."""
        dx, dy = tx - self.tile_x, ty - self.tile_y
        if   abs(dx) >= abs(dy) and dx != 0: sx, sy = (1 if dx > 0 else -1), 0
        elif dy != 0:                         sx, sy = 0, (1 if dy > 0 else -1)
        else:                                 return
        nx, ny = self.tile_x + sx, self.tile_y + sy
        if (nx, ny) not in solid and (map_solid is None or (nx, ny) not in map_solid):
            solid.discard((self.tile_x, self.tile_y))
            self.tile_x, self.tile_y = nx, ny
            solid.add((nx, ny))
            self.facing    = self._FACING[(sx, sy)]
            self.target_x  = float(nx * config.TILE_SIZE)
            self.target_y  = float(ny * config.TILE_SIZE)
            self.is_moving = True
            self.anim_frame = 1
            self.anim_timer = 0.0

    def _update_guard(self, dt, player, game):
        """Guard NPC: approaches player on sight, delivers warning, returns to post."""
        if game.state != 'world':
            return
        if game.story_flags.get('encounters_unlocked'):
            return

        # Always resolve active slide first
        if self.is_moving:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0.0
                self.anim_frame = (self.anim_frame + 1) % 4
            self._slide(dt)
            return

        if self.state == 'idle':
            # # Radius-based detection (commented out — too aggressive)
            # px = player.rect.x // config.TILE_SIZE
            # py = player.rect.y // config.TILE_SIZE
            # dist = abs(px - self.tile_x) + abs(py - self.tile_y)
            # if not game.message_box.visible and not player.moving and dist <= self.sight_range:
            #     self.state = 'approaching'
            if not game.message_box.visible and not player.moving and self.can_see_player(player):
                self.state = 'approaching'

        elif self.state == 'approaching':
            if game.message_box.visible:
                return
            if self._pixel_close(player):
                self.state = 'talking'
                self.face_toward_player(player)
                self.anim_frame = 0
                dialog = getattr(self, 'block_dialog', ["..."])
                game.message_box.queue_messages(
                    dialog, wait_for_input=True,
                    on_complete=lambda: self._guard_warn_done(player, game)
                )
            else:
                self._start_step(player, game.solid_tile_coords, game.solid_tiles)

        elif self.state == 'returning':
            if game.message_box.visible:
                return
            hx, hy = self.home_tile
            if self.tile_x == hx and self.tile_y == hy:
                self.state  = 'idle'
                self.facing = self.home_facing
                self.anim_frame = 0
            else:
                self._step_toward_tile(hx, hy, game.solid_tile_coords, game.solid_tiles)

    def _guard_warn_done(self, player, game):
        """After guard warning dialogue: return to post and push player out of range."""
        self.state = 'returning'
        # Push player one tile down so she doesn't re-trigger immediately
        px = player.rect.x // config.TILE_SIZE
        py = player.rect.y // config.TILE_SIZE
        ts   = config.TILE_SIZE
        nx, ny = px, py + 1
        all_solid = game.solid_tile_coords | game.solid_tiles
        if (nx, ny) not in all_solid:
            player.target_x = nx * ts
            player.target_y = ny * ts
            player.pos_x    = float(player.rect.x)
            player.pos_y    = float(player.rect.y)
            player.moving   = True

    def update(self, dt, player, game):
        if self.npc_type in ('healer', 'shop', 'story', 'gym_guard'):
            return
        if self.npc_type == 'guard':
            self._update_guard(dt, player, game)
            return
        if self.defeated or game.state != 'world' or game.message_box.visible:
            return

        if self.state == 'idle':
            px, py = self._player_tile(player)
            if getattr(self, 'use_proximity', False):
                dist = abs(px - self.tile_x) + abs(py - self.tile_y)
                in_range = not player.moving and dist <= self.sight_range
            else:
                in_range = not player.moving and self.can_see_player(player)
            if in_range:
                # For double-battle pairs, also alert the partner immediately
                data       = TRAINER_DATA.get(self.trainer_id, {})
                partner_id = data.get('partner')
                if partner_id:
                    partner = next(
                        (n for n in game.npcs if n.trainer_id == partner_id
                         and not n.defeated and n.state == 'idle'),
                        None
                    )
                    if partner:
                        partner.state      = 'spotted'
                        partner.spot_timer = 0.7
                self.state      = 'spotted'
                self.spot_timer = 0.7

        elif self.state == 'spotted':
            self.spot_timer -= dt
            if self.spot_timer <= 0:
                data       = TRAINER_DATA.get(self.trainer_id, {})
                partner_id = data.get('partner')
                if partner_id and not getattr(self, '_double_engaged', False):
                    partner = next(
                        (n for n in game.npcs
                         if n.trainer_id == partner_id and not n.defeated
                         and not getattr(n, '_double_engaged', False)),
                        None
                    )
                    if partner:
                        self._double_engaged   = True
                        partner._double_engaged = True
                        self.state   = 'done'
                        partner.state = 'done'
                        self.face_toward_player(player)
                        partner.face_toward_player(player)
                        game.start_forced_walk_double(self, partner)
                        return
                self.state      = 'walking'
                self.anim_frame = 0
                self.anim_timer = 0.0

        elif self.state == 'walking':
            if self.is_moving:
                # Advance walk-frame animation
                self.anim_timer += dt
                if self.anim_timer >= self.anim_speed:
                    self.anim_timer = 0.0
                    self.anim_frame = (self.anim_frame + 1) % 4
                self._slide(dt)
            else:
                # Arrived at a tile — stop if touching player, else keep going
                if self._pixel_close(player):
                    self.state      = 'done'
                    self.anim_frame = 0
                    self._trigger_battle(game)
                else:
                    self._start_step(player, game.solid_tile_coords, game.solid_tiles)

    def face_toward_player(self, player):
        px = player.rect.x // config.TILE_SIZE
        py = player.rect.y // config.TILE_SIZE
        dx = px - self.tile_x
        dy = py - self.tile_y
        if abs(dx) >= abs(dy):
            self.facing = 'right' if dx > 0 else 'left'
        else:
            self.facing = 'down' if dy > 0 else 'up'

    def _trigger_battle(self, game):
        self.face_toward_player(game.player)
        px = game.player.rect.x // config.TILE_SIZE
        py = game.player.rect.y // config.TILE_SIZE
        dx = self.tile_x - px
        dy = self.tile_y - py
        if abs(dx) >= abs(dy):
            pd = 'right' if dx > 0 else 'left'
        else:
            pd = 'down' if dy > 0 else 'up'
        game.player.facing = game.player.direction = pd
        game.player.image = game.player.animations[pd][0]
        data   = TRAINER_DATA.get(self.trainer_id, {})
        dialog = data.get('dialog', {}).get('default', ["Let's battle!"])
        game.message_box.queue_messages(
            dialog, wait_for_input=True,
            on_complete=lambda: game.start_trainer_battle(self)
        )

    # ── draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface, camera_x, camera_y):
        surface.blit(self._current_image(), (self.rect.x - camera_x, self.rect.y - camera_y))
        if self.state == 'spotted' and self.spot_timer > 0:
            if self._exclaim_font is None:
                self._exclaim_font = pygame.font.SysFont('arial', 28, bold=True)
            txt = self._exclaim_font.render('!', True, (210, 30, 30))
            pad_x, pad_y = 6, 4
            box_w = txt.get_width() + pad_x * 2
            box_h = txt.get_height() + pad_y * 2
            cx = self.rect.x - camera_x + self.rect.width // 2
            box_x = cx - box_w // 2
            box_y = self.rect.y - camera_y - box_h - 4
            box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
            pygame.draw.rect(surface, (245, 242, 230), box_rect, border_radius=7)
            pygame.draw.rect(surface, (180, 170, 155), box_rect, width=1, border_radius=7)
            surface.blit(txt, (cx - txt.get_width() // 2, box_y + pad_y))

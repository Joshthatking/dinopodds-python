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
    path = config.NPC_SHEETS.get(trainer_id)
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

    def _start_step(self, player, solid):
        px, py = self._player_tile(player)
        dx, dy = px - self.tile_x, py - self.tile_y
        if   abs(dx) >= abs(dy) and dx != 0: sx, sy = (1 if dx > 0 else -1), 0
        elif dy != 0:                         sx, sy = 0, (1 if dy > 0 else -1)
        else:                                 return

        nx, ny = self.tile_x + sx, self.tile_y + sy
        if (nx, ny) not in solid:
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

    def update(self, dt, player, game):
        if self.npc_type in ('healer', 'shop'):
            return
        if self.defeated or game.state != 'world' or game.message_box.visible:
            return

        if self.state == 'idle':
            if self.can_see_player(player):
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
                    self._start_step(player, game.solid_tile_coords)

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
                self._exclaim_font = pygame.font.SysFont('arial', 20, bold=True)
            txt = self._exclaim_font.render('!', True, (220, 30, 30))
            surface.blit(txt, (
                self.rect.x - camera_x + self.rect.width // 2 - txt.get_width() // 2,
                self.rect.y - camera_y - 20,
            ))

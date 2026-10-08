"""SURF — testing phase.

Everything surf-related lives in this file. The only other touch points are
a handful of lines tagged `# SURF (testing)` in game.py and player.py, so the
whole feature can be removed by deleting this file and those lines.

Water = any tile whose Tiled `type` property is "water" (game.tile_types).
Those tiles are also collision tiles, which is what keeps the player off
them normally; while surfing, Player.update asks movement_verdict() instead
of doing its usual solid-tile check.
"""
import math
import pygame
import config
from screens import YesNoPrompt


class Surf:
    HOP_TIME   = 0.4                 # seconds for the jump on/off the board
    HOP_HEIGHT = 16                  # px peak of the jump arc
    RIDE_LIFT  = 4                   # px the player sits up on the board
    BOARD_W, BOARD_H = 30, 14
    BOARD_COLOR = (20, 32, 72)       # dark navy
    BOARD_RIM   = (48, 72, 130)
    BOARD_SHINE = (90, 120, 180)

    def __init__(self, game):
        self.game = game
        self.active = False   # riding the board
        self.hop = None       # {'start', 'end', 't', 'mount'} while jumping on/off
        self._t = 0.0
        self._board = self._make_board()

    # ── queries ──────────────────────────────────────────────────────────

    def unlocked(self):
        # Sam hands Surf over outside Gym 2 (surf_unlocked); the other two
        # cover quest-menu jumps and saves from before that scene existed.
        f = self.game.story_flags
        return bool(f.get('surf_unlocked') or f.get('sam_surf_intro_done')
                    or f.get('gym3_leader_defeated'))

    def is_water(self, tile):
        return self.game.tile_types.get(tile) == 'water'

    def _player_tile(self):
        p = self.game.player
        ts = config.TILE_SIZE
        return (p.rect.x // ts, p.rect.y // ts)

    def _facing_tile(self):
        dx, dy = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[self.game.player.facing]
        px, py = self._player_tile()
        return (px + dx, py + dy)

    def _occupied(self, tile):
        g = self.game
        return (tile in g.items_on_map
                or any((n.tile_x, n.tile_y) == tile for n in g.npcs))

    def _in_bounds(self, tile):
        min_tx, min_ty, max_tx, max_ty = self.game.world_bounds
        return min_tx <= tile[0] < max_tx and min_ty <= tile[1] < max_ty

    def movement_verdict(self, tile):
        """While surfing: 'move' (open water), 'dismount' (walkable land) or
        'blocked' (rocks, NPCs, items, edge of the world)."""
        g = self.game
        if not self._in_bounds(tile) or self._occupied(tile):
            return 'blocked'
        if self.is_water(tile):
            return 'move'
        if tile in g.solid_tiles or tile in g.solid_tile_coords:
            return 'blocked'
        return 'dismount'

    # ── starting / stopping ──────────────────────────────────────────────

    def try_offer(self):
        """Called on interact. Offers to surf when standing on land facing
        open water. Returns True if it handled the key press."""
        if self.active or self.hop or not self.unlocked():
            return False
        tile = self._facing_tile()
        if not self.is_water(tile) or self.is_water(self._player_tile()) or self._occupied(tile):
            return False
        g = self.game
        g.yes_no_prompt = YesNoPrompt("Would you like to surf?", g.fonts, config.WIDTH, config.HEIGHT)
        g.yes_no_callback = lambda: self.start_hop(tile, mount=True)
        return True

    def start_hop(self, tile, mount):
        p = self.game.player
        p.freeze_in_place()
        ts = config.TILE_SIZE
        self.hop = {'start': (p.rect.x, p.rect.y), 'end': (tile[0] * ts, tile[1] * ts),
                    't': 0.0, 'mount': mount}

    # ── per-frame ────────────────────────────────────────────────────────

    def update(self, dt):
        self._t += dt
        p = self.game.player
        if self.hop:
            h = self.hop
            h['t'] += dt
            k = min(1.0, h['t'] / self.HOP_TIME)
            (sx, sy), (ex, ey) = h['start'], h['end']
            p.pos_x = p.target_x = sx + (ex - sx) * k
            p.pos_y = p.target_y = sy + (ey - sy) * k
            p.rect.x, p.rect.y = round(p.pos_x), round(p.pos_y)
            if k >= 1.0:
                self.hop = None
                self.active = h['mount']
                p.freeze_in_place()
            return
        if p.moving:
            return
        # Keep the flag honest after anything that moves the player without
        # going through a hop (loading a save on water, teleports, blackout).
        on_water = self.is_water(self._player_tile())
        if on_water and not self.active:
            self.active = True
        elif self.active and not on_water:
            self.active = False

    # ── drawing ──────────────────────────────────────────────────────────

    def _make_board(self):
        w, h = self.BOARD_W, self.BOARD_H
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, self.BOARD_RIM, (0, 0, w, h))
        pygame.draw.ellipse(s, self.BOARD_COLOR, (2, 2, w - 4, h - 4))
        pygame.draw.ellipse(s, self.BOARD_SHINE, (6, 3, w // 3, h // 3))
        return s

    def _bob(self):
        return math.sin(self._t * 4.0) * 1.5

    def player_offset_y(self):
        """Vertical draw offset for the player sprite (jump arc / ride bob)."""
        if self.hop:
            k = min(1.0, self.hop['t'] / self.HOP_TIME)
            lift = self.RIDE_LIFT * (k if self.hop['mount'] else 1.0 - k)
            return -int(math.sin(k * math.pi) * self.HOP_HEIGHT + lift)
        if self.active:
            return -int(self.RIDE_LIFT + self._bob())
        return 0

    def draw_under_player(self, surface, cam_x, cam_y):
        """The board: sits under the player while riding; during a hop it
        waits at the water tile (fading in on mount, out on dismount)."""
        p = self.game.player
        ts = config.TILE_SIZE
        if self.hop:
            k = min(1.0, self.hop['t'] / self.HOP_TIME)
            bx, by = self.hop['end'] if self.hop['mount'] else self.hop['start']
            alpha = int(255 * (k if self.hop['mount'] else 1.0 - k))
            cx, cy, bob = bx + ts // 2, by + ts, 0
        elif self.active:
            cx, cy, bob = p.rect.centerx, p.rect.bottom, self._bob()
            alpha = 255
        else:
            return
        board = self._board.copy()
        board.set_alpha(alpha)
        surface.blit(board, (int(cx - cam_x - self.BOARD_W // 2),
                             int(cy - cam_y - self.BOARD_H + 2 - bob)))

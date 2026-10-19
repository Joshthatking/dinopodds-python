"""LAKE AURORA — Lake Meridian's "iridescent lights".

While the player is in Lake Meridian (LAKE_RECT on the overworld), every
45-60 seconds of walking around a faint northern-lights show plays for
5 seconds: waving colour curtains across the top of the screen, motes of
light drifting up off the lake's water tiles, and a soft pulse at the
Horizon Cave mouth. Then it fades back to normal and the timer restarts.

Everything is drawn additively on the final (scaled) screen after the night
overlay, so it glows at night; by day the map dims under a dusky tint for
the length of the show so the lights still read. Touch points in
game.py are tagged `# LAKE AURORA`.
"""
import math
import random
import pygame
import config

# Overworld tiles counted as Lake Meridian (x1, y1, x2, y2) — from the
# Route 3 / Lake Meridian banner line (y=-75) north, covering the lake,
# its snowy banks and the Horizon Cave entrance.
LAKE_WORLD = 'LOST_REGION.world'
LAKE_RECT  = (-20, -120, 55, -75)
CAVE_ENTRANCE_ID = 'horizon'

INTERVAL = (45.0, 60.0)   # seconds between shows (only counted while in the lake)
DURATION = 5.0
FADE_IN  = 1.2
FADE_OUT = 1.6
DAY_STRENGTH = 1.0        # light strength in daylight (night is always 1.0)
# Daytime only: the map dims under a dusky tint while the lights show, so
# they read clearly. Faded in/out with the show; skipped at night, which
# already has its own overlay.
DAY_DIM_COLOR = (20, 15, 45)
DAY_DIM_ALPHA = 120

# Iridescent cycle the curtains and motes move through
PALETTE = [
    (30, 255, 140),   # aurora green
    (30, 200, 255),   # cyan
    (150, 70, 255),   # violet
    (255, 70, 200),   # pink
    (40, 255, 200),   # teal
]
HUES = 30             # blended steps around the palette

COL_W     = 6         # curtain column width (screen px)
RIBBONS   = 3
SKY_FRAC  = 0.55      # curtains live in the top part of the screen
CURTAIN_PEAK = 0.3   # brightest a curtain gets (0-1) — keep low so it stays faint

MOTES_PER_SEC = 14
CAVE_MOTE_SHARE = 0.25


def _hue(i):
    """Palette colour at fractional position i (wraps)."""
    n = len(PALETTE)
    i %= n
    a, b = PALETTE[int(i)], PALETTE[(int(i) + 1) % n]
    f = i - int(i)
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class LakeAurora:
    def __init__(self, game):
        self.game = game
        self.timer = None        # seconds until the next show (None = not in the lake)
        self.show_t = None       # seconds into the current show (None = idle)
        self.motes = []
        self._mote_carry = 0.0
        self._cols = None
        self._layer = None
        self._dim = None
        self._glow_cache = {}
        self._cave_tiles = None
        self._cave_world = None

    # ── state ────────────────────────────────────────────────────────────
    def _in_lake(self):
        g = self.game
        if g.current_world_file != LAKE_WORLD:
            return False
        ts = config.TILE_SIZE
        tx, ty = g.player.rect.centerx // ts, g.player.rect.centery // ts
        x1, y1, x2, y2 = LAKE_RECT
        return x1 <= tx <= x2 and y1 <= ty <= y2

    def trigger(self):
        """Start a show right now (also used by the sandbox Ctrl+L key)."""
        self.show_t = 0.0
        self.timer = None
        self.motes = []
        self._mote_carry = 0.0

    def active(self):
        return self.show_t is not None

    def _envelope(self):
        t = self.show_t
        return _smooth(t / FADE_IN) * _smooth((DURATION - t) / FADE_OUT)

    def _strength(self):
        return 1.0 if self.game.night_active else DAY_STRENGTH

    def update(self, dt):
        g = self.game
        if g.current_world_file != LAKE_WORLD:
            self.show_t = None
            self.timer = None
            self.motes = []
            return

        if self.show_t is not None:
            self.show_t += dt
            if self.show_t >= DURATION:
                self.show_t = None
                self.motes = []
            else:
                self._update_motes(dt)
            return

        if not self._in_lake():
            self.timer = None
            return
        if self.timer is None:
            self.timer = random.uniform(*INTERVAL)
        if g.state_stack[-1] == 'world':
            self.timer -= dt
            if self.timer <= 0:
                self.trigger()

    # ── motes off the water / cave mouth ─────────────────────────────────
    def _cave_mouth(self):
        g = self.game
        if self._cave_world is not g.entrance_tile_coords:
            self._cave_world = g.entrance_tile_coords
            self._cave_tiles = [t for t, eid in g.entrance_tile_coords.items()
                                if eid == CAVE_ENTRANCE_ID]
        return self._cave_tiles

    def _visible_tiles(self):
        g = self.game
        ts = config.TILE_SIZE
        w, h = g.render_surface.get_size()
        return (int(g.camera_x // ts), int(g.camera_y // ts),
                int((g.camera_x + w) // ts), int((g.camera_y + h) // ts))

    def _spawn_mote(self):
        g = self.game
        ts = config.TILE_SIZE
        cave = self._cave_mouth()
        tile = None
        if cave and random.random() < CAVE_MOTE_SHARE:
            tile = random.choice(cave)
        else:
            x0, y0, x1, y1 = self._visible_tiles()
            for _ in range(12):
                t = (random.randint(x0, x1), random.randint(y0, y1))
                if g.tile_types.get(t) == 'water':
                    tile = t
                    break
        if tile is None:
            return
        self.motes.append({
            'x': (tile[0] + random.random()) * ts,
            'y': (tile[1] + random.random()) * ts,
            't': 0.0,
            'life': random.uniform(1.4, 2.6),
            'hue': random.uniform(0, len(PALETTE)),
            'rise': random.uniform(10, 22),
            'phase': random.uniform(0, math.tau),
            'size': random.uniform(0.7, 1.3),
        })

    def _update_motes(self, dt):
        self._mote_carry += MOTES_PER_SEC * self._envelope() * dt
        while self._mote_carry >= 1:
            self._mote_carry -= 1
            self._spawn_mote()
        for m in self.motes:
            m['t'] += dt
            m['y'] -= m['rise'] * dt
            m['hue'] += dt * 0.8
        self.motes = [m for m in self.motes if m['t'] < m['life']]

    # ── drawing ──────────────────────────────────────────────────────────
    def _build_columns(self, height):
        """Per-hue curtain column: brightest just above the bottom hem,
        fading out upward and softly at the hem itself."""
        cols = []
        for i in range(HUES):
            r, g, b = _hue(i / HUES * len(PALETTE))
            col = pygame.Surface((COL_W, height))
            for y in range(height):
                f = y / (height - 1)
                k = (f ** 2.0) * CURTAIN_PEAK * min(1.0, (1 - f) / 0.14 + 0.05)
                col.fill((int(r * k), int(g * k), int(b * k)), (0, y, COL_W, 1))
            cols.append(col)
        return cols

    def _glow(self, hue_idx, radius):
        key = (hue_idx, radius)
        surf = self._glow_cache.get(key)
        if surf is None:
            r, g, b = _hue(hue_idx / HUES * len(PALETTE))
            surf = pygame.Surface((radius * 2, radius * 2))
            for rr in range(radius, 0, -1):
                k = (1 - rr / radius) ** 1.8
                pygame.draw.circle(surf, (int(r * k), int(g * k), int(b * k)), (radius, radius), rr)
            self._glow_cache[key] = surf
        return surf

    def draw(self, screen):
        if self.show_t is None:
            return
        fade = self._envelope()
        env = fade * self._strength()
        if env <= 0.01:
            return
        W, H = screen.get_size()
        t = self.show_t
        if not self.game.night_active:
            self._draw_day_dim(screen, W, H, fade)
        self._draw_curtains(screen, W, H, t, env)
        self._draw_cave_glow(screen, t, env)
        self._draw_motes(screen, env)

    def _draw_day_dim(self, screen, W, H, fade):
        if self._dim is None or self._dim.get_size() != (W, H):
            self._dim = pygame.Surface((W, H))
            self._dim.fill(DAY_DIM_COLOR)
        self._dim.set_alpha(int(DAY_DIM_ALPHA * fade))
        screen.blit(self._dim, (0, 0))

    def _draw_curtains(self, screen, W, H, t, env):
        sky_h = int(H * SKY_FRAC)
        rib_h = int(sky_h * 0.6)
        if self._cols is None or self._cols[0].get_height() != rib_h:
            self._cols = self._build_columns(rib_h)
            self._layer = pygame.Surface((W, sky_h))
        layer = self._layer
        layer.fill((0, 0, 0))
        for r in range(RIBBONS):
            base = sky_h * (0.42 + 0.17 * r)
            ph = r * 2.1
            for x in range(0, W + COL_W, COL_W):
                y = (base
                     + math.sin(x * 0.006 + t * 0.9 + ph) * sky_h * 0.09
                     + math.sin(x * 0.017 - t * 1.6 + ph * 1.7) * sky_h * 0.035)
                ray = 0.55 + 0.45 * math.sin(x * 0.045 + t * 2.4 + ph) * math.sin(x * 0.011 - t * 0.7)
                h = max(4, int(rib_h * (0.45 + 0.55 * ray)))
                hue = int(x / W * HUES * 0.9 + t * 4 + r * 7) % HUES
                layer.blit(self._cols[hue], (x, int(y) - h),
                           area=pygame.Rect(0, rib_h - h, COL_W, h),
                           special_flags=pygame.BLEND_RGB_ADD)
        e = int(255 * env)
        layer.fill((e, e, e), special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _to_screen(self, wx, wy):
        g = self.game
        scale = config.WIDTH / g.render_surface.get_width()
        return (wx - g.camera_x) * scale, (wy - g.camera_y) * scale, scale

    def _draw_cave_glow(self, screen, t, env):
        cave = self._cave_mouth()
        if not cave:
            return
        ts = config.TILE_SIZE
        cx = sum(x for x, _ in cave) / len(cave) * ts + ts / 2
        cy = sum(y for _, y in cave) / len(cave) * ts + ts / 2
        sx, sy, scale = self._to_screen(cx, cy)
        pulse = 0.75 + 0.25 * math.sin(t * 3.0)
        radius = int(ts * 2.2 * scale * pulse * env) // 2 * 2
        if radius < 4 or not (-radius < sx < config.WIDTH + radius and -radius < sy < config.HEIGHT + radius):
            return
        hue = int(t * 5) % HUES
        screen.blit(self._glow(hue, radius), (sx - radius, sy - radius),
                    special_flags=pygame.BLEND_RGB_ADD)

    def _draw_motes(self, screen, env):
        for m in self.motes:
            q = m['t'] / m['life']
            fade = math.sin(q * math.pi) * env
            wx = m['x'] + math.sin(m['t'] * 2.2 + m['phase']) * 5
            sx, sy, scale = self._to_screen(wx, m['y'])
            if not (-20 < sx < config.WIDTH + 20 and -20 < sy < config.HEIGHT + 20):
                continue
            radius = int(10 * scale * m['size'] * (0.4 + 0.6 * fade)) // 2 * 2
            if radius < 2:
                continue
            hue = int(m['hue'] / len(PALETTE) * HUES) % HUES
            glow = self._glow(hue, radius)
            if fade < 0.98:
                glow = glow.copy()
                f = int(255 * fade)
                glow.fill((f, f, f), special_flags=pygame.BLEND_RGB_MULT)
            screen.blit(glow, (sx - radius, sy - radius), special_flags=pygame.BLEND_RGB_ADD)

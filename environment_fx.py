"""ENVIRONMENT FX — testing phase.

Small overworld ambience effects:
  * Grass  — encounter grass rustles when the player steps into it: the bottom
             of the grass tile's own art sways over the player's feet for a
             moment while a few leaf specks pop out, then fades back to normal.
  * Water  — water tiles shimmer: drifting ripple highlights and the odd
             twinkle. Only tiles currently on screen are drawn, from a small
             set of animation frames built once up front, so it stays cheap.

The only other touch points are a handful of lines tagged `# ENV FX` in
game.py, so the whole feature can be removed by deleting this file and those
lines. Each effect can also be switched off on its own via GRASS_ON / WATER_ON.

Grass = an encounter tile whose Tiled `type` is "grass" (GrassFX.TILE_TYPES).
Water = any tile whose Tiled `type` property is "water" (game.tile_types).
"""
import math
import random
import pygame
import config

GRASS_ON = True
WATER_ON = True


class GrassFX:
    DURATION   = 0.45   # seconds per rustle
    STRIP_FRAC = 0.45   # bottom fraction of the tile that sways
    SWAY_PX    = 3      # max sideways sway of the top of the strip
    SWAY_FREQ  = 3.0    # back-and-forth swings over the rustle
    FADE_FROM  = 0.6    # strip fades out over the last part of the rustle
    LEAVES     = 4
    # Tiled `type` values that rustle (regular + burnt grass are both
    # "grass"); cave, water, sand, snow, corn maze etc. stay still.
    TILE_TYPES = {'grass'}

    def __init__(self, game):
        self.game = game
        self.rustles = []        # {'tile', 't', 'art', 'leaves'}
        self._last_target = None

    def update(self, dt):
        g = self.game
        p = g.player
        ts = config.TILE_SIZE
        # A new step starting into a grass tile spawns a rustle there.
        if g.state_stack[-1] == 'world' and p.moving:
            target = (int(p.target_x) // ts, int(p.target_y) // ts)
            if target != self._last_target:
                self._last_target = target
                if (target in g.encounter_tile_coords
                        and g.tile_types.get(target) in self.TILE_TYPES):
                    self._spawn(target)
        elif not p.moving:
            self._last_target = None
        for r in self.rustles:
            r['t'] += dt
        self.rustles = [r for r in self.rustles if r['t'] < self.DURATION]

    def _spawn(self, tile):
        self.rustles = [r for r in self.rustles if r['tile'] != tile]
        leaves = [{'vx': random.uniform(-40, 40), 'vy': random.uniform(-70, -40),
                   'x0': random.uniform(0.2, 0.8)} for _ in range(self.LEAVES)]
        self.rustles.append({'tile': tile, 't': 0.0, 'art': None, 'leaves': leaves})

    def capture(self, surface, cam_x, cam_y):
        """Grab each new rustle's grass art straight off the screen — must run
        after the ground layers are drawn but before any sprites."""
        ts = config.TILE_SIZE
        bounds = surface.get_rect()
        for r in self.rustles:
            if r['art'] is not None:
                continue
            x = r['tile'][0] * ts - cam_x
            y = r['tile'][1] * ts - cam_y
            rect = pygame.Rect(x, y, ts, ts)
            if not bounds.contains(rect):
                r['art'] = False   # off-screen edge — skip the sway, leaves still show
                continue
            r['art'] = surface.subsurface(rect).copy()
            avg = pygame.transform.average_color(r['art'])
            r['color'] = (max(0, avg[0] - 25), max(0, avg[1] - 10), max(0, avg[2] - 25))

    def draw(self, surface, cam_x, cam_y):
        ts = config.TILE_SIZE
        for r in self.rustles:
            p = r['t'] / self.DURATION
            x = r['tile'][0] * ts - cam_x
            y = r['tile'][1] * ts - cam_y
            decay = 1 - p
            art = r['art']
            if art:
                alpha = 255 if p < self.FADE_FROM else int(255 * (1 - p) / (1 - self.FADE_FROM))
                strip_h = int(ts * self.STRIP_FRAC)
                top = ts - strip_h
                swing = math.sin(p * self.SWAY_FREQ * math.tau) * self.SWAY_PX * decay
                for row in range(top, ts):
                    # Blade tips (top of the strip) swing most, roots stay put
                    lean = 1 - (row - top) / strip_h
                    line = art.subsurface((0, row, ts, 1))
                    line.set_alpha(alpha)
                    surface.blit(line, (x + round(swing * lean), y + row))
            color = r.get('color', (60, 140, 50))
            for leaf in r['leaves']:
                t = r['t']
                lx = x + leaf['x0'] * ts + leaf['vx'] * t
                ly = y + ts * 0.7 + leaf['vy'] * t + 260 * t * t
                if p < 0.9:
                    pygame.draw.rect(surface, color, (int(lx), int(ly), 2, 2))


class WaterFX:
    FRAMES     = 24     # animation frames in one loop
    LOOP_TIME  = 2.4    # seconds per loop
    TEX_TILES  = 2      # pattern repeats every 2x2 tiles so the grid doesn't show
    BANDS      = 4      # ripple bands per texture height
    WOBBLE     = 0.9    # how wavy each ripple band is
    SPARKLES   = 5      # twinkles per texture
    HIGHLIGHT  = (235, 248, 255)
    SHADE      = (10, 40, 90)

    def __init__(self, game):
        self.game = game
        self.t = 0.0
        self._frames = None   # built lazily the first time water is on screen

    def update(self, dt):
        self.t = (self.t + dt) % self.LOOP_TIME

    def _build_frames(self):
        ts = config.TILE_SIZE
        size = ts * self.TEX_TILES
        rng = random.Random(7)
        sparkles = [(rng.randrange(size), rng.randrange(size), rng.random())
                    for _ in range(self.SPARKLES)]
        tau = math.tau
        frames = []
        for k in range(self.FRAMES):
            t = k / self.FRAMES
            tex = pygame.Surface((size, size), pygame.SRCALPHA)
            for y in range(size):
                v = y / size
                for x in range(size):
                    u = x / size
                    # Integer frequencies in u, v and t keep it seamless in
                    # space and looping in time.
                    a = math.sin(tau * (self.BANDS * v + t)
                                 + self.WOBBLE * math.sin(tau * (2 * u - t)))
                    # Break the bands into short glints that drift sideways
                    b = (math.sin(tau * (3 * u - v - t))
                         + math.sin(tau * (2 * u + 3 * v + 2 * t))) * 0.5
                    if b < 0.15:
                        a = min(a, 0.5) if a > 0 else a * 0.5
                    if a > 0.93:
                        tex.set_at((x, y), (*self.HIGHLIGHT, 80))
                    elif a > 0.82:
                        tex.set_at((x, y), (*self.HIGHLIGHT, 32))
                    elif a < -0.95:
                        tex.set_at((x, y), (*self.SHADE, 40))
            for sx, sy, phase in sparkles:
                glow = max(0.0, math.sin(tau * (t + phase))) ** 6
                if glow < 0.05:
                    continue
                a = int(200 * glow)
                tex.set_at((sx, sy), (255, 255, 255, a))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    tex.set_at(((sx + dx) % size, (sy + dy) % size), (255, 255, 255, a // 2))
            # Pre-cut the four tile-sized quarters so drawing is one blit per tile
            frames.append([[tex.subsurface((qx * ts, qy * ts, ts, ts))
                            for qy in range(self.TEX_TILES)]
                           for qx in range(self.TEX_TILES)])
        self._frames = frames

    def draw(self, surface, cam_x, cam_y):
        tile_types = getattr(self.game, 'tile_types', None)
        if not tile_types:
            return
        ts = config.TILE_SIZE
        w, h = surface.get_size()
        x0, y0 = int(cam_x) // ts, int(cam_y) // ts
        x1, y1 = (int(cam_x) + w) // ts, (int(cam_y) + h) // ts
        frame = None
        n = self.TEX_TILES
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if tile_types.get((tx, ty)) != 'water':
                    continue
                if frame is None:
                    if self._frames is None:
                        self._build_frames()
                    frame = self._frames[int(self.t / self.LOOP_TIME * self.FRAMES) % self.FRAMES]
                surface.blit(frame[tx % n][ty % n], (tx * ts - cam_x, ty * ts - cam_y))


class EnvironmentFX:
    def __init__(self, game):
        self.grass = GrassFX(game)
        self.water = WaterFX(game)

    def update(self, dt):
        if GRASS_ON:
            self.grass.update(dt)
        if WATER_ON:
            self.water.update(dt)

    def draw_ground(self, surface, cam_x, cam_y):
        """Call right after the map's ground layers are drawn, before sprites."""
        if WATER_ON:
            self.water.draw(surface, cam_x, cam_y)
        if GRASS_ON:
            self.grass.capture(surface, cam_x, cam_y)

    def draw_over_player(self, surface, cam_x, cam_y):
        """Call right after the player is drawn."""
        if GRASS_ON:
            self.grass.draw(surface, cam_x, cam_y)

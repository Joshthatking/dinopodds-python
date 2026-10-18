"""Spacial aetheric backdrop drawn behind the map tiles in worlds that float
in the void (currently HORIZON_CAVE.world), in place of the plain black fill.

Layers, back to front, all procedural (no image assets):
  - vertical deep-space gradient (fixed to the screen)
  - tileable nebula clouds, slow parallax, additive
  - three tileable starfield layers at increasing parallax
  - a handful of twinkling stars and rising aether motes, animated per frame

Usage (see Game.draw):
    bg = AetherBackground()
    bg.draw(render_surface, camera_x, camera_y, seconds)
"""
import math
import random
import pygame

TOP_COL = (8, 4, 22)
BOTTOM_COL = (30, 10, 48)
NEBULA_COLS = [(90, 40, 160), (40, 110, 170), (150, 50, 140), (60, 60, 190)]
MOTE_COLS = [(170, 140, 255), (120, 220, 255), (255, 170, 240)]

NEBULA_TILE = 512
STAR_TILE = 256
STAR_LAYERS = (       # (parallax, star count, max radius, brightness)
    (0.15, 70, 1, 120),
    (0.30, 45, 1, 190),
    (0.50, 22, 2, 255),
)


def _soft_blob(r, col):
    """Radial glow sprite for additive blending."""
    spr = pygame.Surface((r * 2, r * 2))
    steps = max(4, r // 4)
    for i in range(steps):
        f = (i + 1) / steps
        pygame.draw.circle(spr, tuple(int(c * f * f * 0.35) for c in col), (r, r), max(1, int(r * (1 - i / steps))))
    return spr


def _blit_wrapped(dst, src, x, y):
    """Blit src so it wraps around dst's edges (keeps tiles seamless)."""
    w, h = dst.get_size()
    for dx in (-w, 0, w):
        for dy in (-h, 0, h):
            dst.blit(src, (x + dx, y + dy), special_flags=pygame.BLEND_RGB_ADD)


class AetherBackground:
    def __init__(self, seed=7):
        rng = random.Random(seed)
        self._gradient = None
        self._gradient_size = None

        self._nebula = pygame.Surface((NEBULA_TILE, NEBULA_TILE))
        self._nebula.fill((0, 0, 0))
        for _ in range(26):
            r = rng.randint(50, 140)
            blob = _soft_blob(r, rng.choice(NEBULA_COLS))
            _blit_wrapped(self._nebula, blob, rng.randrange(NEBULA_TILE) - r, rng.randrange(NEBULA_TILE) - r)

        self._star_layers = []
        for parallax, count, max_r, bright in STAR_LAYERS:
            tile = pygame.Surface((STAR_TILE, STAR_TILE))
            tile.fill((0, 0, 0))
            for _ in range(count):
                x, y = rng.randrange(STAR_TILE), rng.randrange(STAR_TILE)
                b = rng.randint(bright // 2, bright)
                tint = rng.choice(((b, b, b), (b * 4 // 5, b * 4 // 5, b), (b, b * 4 // 5, b)))
                r = rng.randint(1, max_r)
                if r == 1:
                    tile.set_at((x, y), tint)
                else:
                    pygame.draw.circle(tile, tint, (x, y), r)
            self._star_layers.append((parallax, tile))

        # bright stars that twinkle, in nebula-tile space at parallax 0.4
        self._twinklers = [(rng.uniform(0, NEBULA_TILE), rng.uniform(0, NEBULA_TILE),
                            rng.uniform(0, math.tau), rng.uniform(1.5, 3.5)) for _ in range(14)]
        # aether motes drifting upward, in screen-fraction space
        self._motes = [(rng.random(), rng.random(), rng.uniform(0.02, 0.06), rng.uniform(0, math.tau),
                        rng.choice(MOTE_COLS)) for _ in range(18)]
        self._mote_glow = {c: _soft_blob(6, c) for c in MOTE_COLS}

    def _gradient_for(self, size):
        if self._gradient_size != size:
            w, h = size
            g = pygame.Surface(size)
            for y in range(h):
                f = y / max(1, h - 1)
                pygame.draw.line(g, tuple(int(a + (b - a) * f) for a, b in zip(TOP_COL, BOTTOM_COL)), (0, y), (w, y))
            self._gradient, self._gradient_size = g, size
        return self._gradient

    @staticmethod
    def _tile_blit(surface, tile, cam_x, cam_y, parallax, additive=True):
        w, h = surface.get_size()
        tw, th = tile.get_size()
        sx = -int(cam_x * parallax) % tw - tw
        sy = -int(cam_y * parallax) % th - th
        flags = pygame.BLEND_RGB_ADD if additive else 0
        y = sy
        while y < h:
            x = sx
            while x < w:
                surface.blit(tile, (x, y), special_flags=flags)
                x += tw
            y += th

    def draw(self, surface, cam_x, cam_y, t):
        w, h = surface.get_size()
        surface.blit(self._gradient_for((w, h)), (0, 0))
        # nebula slowly breathes and drifts on top of the camera parallax
        self._tile_blit(surface, self._nebula, cam_x + t * 4, cam_y + t * 2, 0.08)
        for parallax, tile in self._star_layers:
            self._tile_blit(surface, tile, cam_x, cam_y, parallax)

        ox = -cam_x * 0.4
        oy = -cam_y * 0.4
        for tx, ty, phase, speed in self._twinklers:
            k = 0.5 + 0.5 * math.sin(t * speed + phase)
            if k < 0.15:
                continue
            x = (tx + ox) % NEBULA_TILE
            y = (ty + oy) % NEBULA_TILE
            for bx in range(int(x) - NEBULA_TILE, w + NEBULA_TILE, NEBULA_TILE):
                for by in range(int(y) - NEBULA_TILE, h + NEBULA_TILE, NEBULA_TILE):
                    if 0 <= bx < w and 0 <= by < h:
                        c = int(255 * k)
                        arm = 2 + int(3 * k)
                        pygame.draw.line(surface, (c, c, c), (bx - arm, by), (bx + arm, by))
                        pygame.draw.line(surface, (c, c, c), (bx, by - arm), (bx, by + arm))
                        surface.set_at((bx, by), (255, 255, 255))

        for fx, fy, rise, phase, col in self._motes:
            x = (fx * w - cam_x * 0.6 + math.sin(t * 0.8 + phase) * 10) % w
            y = (fy * h - cam_y * 0.6 - t * rise * h) % h
            glow = self._mote_glow[col]
            surface.blit(glow, (int(x) - 6, int(y) - 6), special_flags=pygame.BLEND_RGB_ADD)
            surface.set_at((int(x), int(y)), col)

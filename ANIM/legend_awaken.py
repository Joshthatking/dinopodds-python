"""Battle intros for the two planet legendaries (Lv 50, see Game.LEGENDS).

  DeimoAwaken — the lunar celestial, "marionette of darkness": the sky dims
                violet, an eclipse ring opens around Deimo, glowing puppet
                strings drop from above onto the player and pull taut... then
                snap, and a black crescent swallows the screen.
  VYAwaken    — the solar celestial: the ground heats, a sun swells behind VY
                as wings of flame sweep open, then a supernova whites it out.

Both are drawn in screen space over the world. Each ends fully covered in
END_COLOR, which the game then fades out of into the battle.
"""
import math
import random
import pygame
import config


def _glow(r, col, strength=1.0):
    s = pygame.Surface((r * 2, r * 2))
    for i in range(r, 0, -1):
        k = (1 - i / r) ** 2 * strength
        pygame.draw.circle(s, tuple(min(255, int(c * k)) for c in col), (r, r), i)
    return s


def _smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class _Awaken:
    DURATION = 2.8
    END_COLOR = (0, 0, 0)

    def __init__(self):
        W, H = config.WIDTH, config.HEIGHT
        self._dim = pygame.Surface((W, H))
        self._fx = pygame.Surface((W, H))
        self._cover = pygame.Surface((W, H))
        self._cover.fill(self.END_COLOR)
        self._glows = {}

    def glow(self, r, col, strength=1.0):
        key = (max(2, int(r)) // 2 * 2, col, strength)
        if key not in self._glows:
            self._glows[key] = _glow(key[0], col, strength)
        return self._glows[key]


class DeimoAwaken(_Awaken):
    STRINGS_END = 1.9     # strings dropped and pulled taut
    SNAP = 2.15           # strings snap, crescent sweeps
    DURATION = 2.75
    END_COLOR = (0, 0, 0)
    STRING_COL = (190, 130, 255)

    def __init__(self):
        super().__init__()
        rng = random.Random(39)
        # (x fraction at the top of the screen, drop delay, sway phase, offset at the player)
        self.strings = [(rng.uniform(0.1, 0.9), i * 0.16, rng.uniform(0, math.tau),
                         (rng.uniform(-14, 14), rng.uniform(-20, 12))) for i in range(8)]
        self.motes = [(rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.1, 0.3), rng.uniform(1, 3))
                      for _ in range(40)]

    def draw(self, screen, legend_xy, player_xy, t, sprite=None):
        """sprite: (surface, topleft) of the legendary, redrawn over the
        eclipse so Deimo stays in front of its own black moon."""
        W, H = screen.get_size()
        lx, ly = legend_xy
        cx, cy = lx, ly - 18          # the eclipse hangs just behind Deimo's head
        px, py = player_xy
        build = _smooth(t / self.STRINGS_END)
        snap = _smooth((t - self.STRINGS_END) / (self.SNAP - self.STRINGS_END))
        cover = _smooth((t - self.SNAP) / (self.DURATION - 0.25 - self.SNAP))

        self._dim.fill((10, 0, 24))
        self._dim.set_alpha(int(205 * build))
        screen.blit(self._dim, (0, 0))

        # eclipse: a black moon with a violet corona opening around Deimo
        r = (18 + 60 * build) * (1 + 0.04 * math.sin(t * 6))
        g = self.glow(r * 2.2, (150, 70, 255), 0.9 * build)
        screen.blit(g, (cx - g.get_width() / 2, cy - g.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
        if r > 3:
            pygame.draw.circle(screen, (200, 150, 255), (int(cx), int(cy)), int(r) + 3, 2)
            pygame.draw.circle(screen, (6, 0, 14), (int(cx + r * 0.18), int(cy - r * 0.1)), int(r))

        # dark motes drifting up toward the eclipse
        for fx, fy, speed, size in self.motes:
            y = (fy - t * speed) % 1.0 * H
            x = fx * W + math.sin(t * 2 + fx * 9) * 8
            c = int(120 * build)
            pygame.draw.rect(screen, (c, c // 2, min(255, c * 2)), (int(x), int(y), int(size), int(size)))
        if sprite:
            screen.blit(*sprite)

        # marionette strings: drop from above onto the player, sway, pull taut, snap
        for xf, delay, ph, (ox, oy) in self.strings:
            drop = _smooth((t - delay) / 0.45)
            if drop <= 0:
                continue
            top = (xf * W, -10)
            end = (px + ox, py + oy)
            sway = (1 - _smooth((t - 1.4) / 0.4)) * 16 * math.sin(t * 3 + ph)
            if snap > 0:   # the string recoils back up off-screen
                end = (end[0] + (top[0] - end[0]) * snap, end[1] + (top[1] - end[1]) * snap * 1.2)
            tip = (top[0] + (end[0] - top[0]) * drop, top[1] + (end[1] - top[1]) * drop)
            mid = ((top[0] + tip[0]) / 2 + sway, (top[1] + tip[1]) / 2)
            pts = [top]
            for i in range(1, 11):
                u = i / 10
                pts.append(((1 - u) ** 2 * top[0] + 2 * (1 - u) * u * mid[0] + u * u * tip[0],
                            (1 - u) ** 2 * top[1] + 2 * (1 - u) * u * mid[1] + u * u * tip[1]))
            pygame.draw.lines(screen, (90, 40, 160), False, pts, 3)
            pygame.draw.lines(screen, self.STRING_COL, False, pts, 1)
            if drop >= 1 and snap <= 0:
                pygame.draw.circle(screen, (230, 200, 255), (int(tip[0]), int(tip[1])), 2)

        # the crescent: a black moon swelling out of the eclipse to fill the screen
        if cover > 0:
            R = int(30 + cover * math.hypot(W, H) * 1.15)
            cres = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(cres, (0, 0, 0, 255), (int(cx), int(cy)), R)
            bite = int(R * (1 - cover) * 0.92)
            if bite > 0:
                pygame.draw.circle(cres, (0, 0, 0, 0), (int(cx + R * 0.45), int(cy - R * 0.2)), bite)
            screen.blit(cres, (0, 0))
            if bite > 0:
                pygame.draw.circle(screen, (120, 60, 220), (int(cx), int(cy)), R, 2)
        if t >= self.DURATION - 0.25:
            screen.blit(self._cover, (0, 0))


class VYAwaken(_Awaken):
    BUILD = 1.9          # sun swells, wings of flame open
    BURST = 2.4          # supernova whites everything out
    DURATION = 2.7
    END_COLOR = (255, 240, 214)
    FIRE = [(255, 250, 220), (255, 214, 90), (255, 150, 40), (230, 80, 30)]

    def __init__(self):
        super().__init__()
        rng = random.Random(40)
        self.embers = [(rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.15, 0.45), rng.choice(self.FIRE))
                       for _ in range(50)]
        self.feathers = [(side, i) for side in (-1, 1) for i in range(9)]

    def draw(self, screen, legend_xy, player_xy, t, sprite=None):
        """sprite: (surface, topleft) of the legendary, redrawn over the
        glow so VY stays visible in front of its own sun."""
        W, H = screen.get_size()
        cx, cy = legend_xy
        build = _smooth(t / self.BUILD)
        burst = _smooth((t - self.BUILD) / (self.BURST - self.BUILD))

        # heat: the scene warms toward orange
        self._dim.fill((90, 40, 0))
        self._dim.set_alpha(int(120 * build))
        screen.blit(self._dim, (0, 0))

        fx = self._fx
        fx.fill((0, 0, 0))
        # the sun swelling behind VY, its corona pulsing
        sun_r = 20 + 90 * build + 30 * math.sin(t * 5) * build * 0.1
        for g_r, col, s in ((sun_r * 2.6, (255, 120, 30), 0.6), (sun_r * 1.6, (255, 190, 80), 0.9),
                            (sun_r, (255, 250, 210), 1.0)):
            g = self.glow(g_r, col, s * build)
            fx.blit(g, (cx - g.get_width() / 2, cy - g.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
        # rotating corona rays
        for i in range(12):
            a = i * math.tau / 12 + t * 0.8
            ln = sun_r * (1.3 + 0.5 * math.sin(t * 4 + i)) * build
            col = tuple(int(c * 0.7 * build) for c in self.FIRE[1 + i % 3])
            pygame.draw.line(fx, col, (cx, cy), (cx + math.cos(a) * ln * 1.6, cy + math.sin(a) * ln * 1.6), 3)
        # wings of flame: feathers fanning outward from VY on both sides
        spread = _smooth((t - 0.4) / 1.3)
        for side, i in self.feathers:
            base_a =math.atan2(-1, side * 1.4) + side * (-0.15 + i * 0.12) * spread
            length = (60 + i * 10) * spread
            x2 = cx + math.cos(base_a) * length
            y2 = cy + math.sin(base_a) * length * 0.8
            for w, col in ((5, self.FIRE[3]), (3, self.FIRE[2]), (1, self.FIRE[0])):
                pygame.draw.line(fx, tuple(int(c * spread) for c in col), (cx, cy - 4), (x2, y2), w)
        # embers rising
        for ex, ey, speed, col in self.embers:
            y = (ey - t * speed) % 1.0 * H
            x = ex * W + math.sin(t * 3 + ex * 11) * 10
            k = build * (0.5 + 0.5 * math.sin(t * 8 + ex * 20))
            pygame.draw.circle(fx, tuple(int(c * k) for c in col), (int(x), int(y)), 2)
        screen.blit(fx, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if sprite:
            screen.blit(*sprite)

        # supernova: a shock ring and a white-gold flood
        if burst > 0:
            R = int(burst * math.hypot(W, H))
            pygame.draw.circle(screen, (255, 230, 150), (int(cx), int(cy)), max(1, R), max(2, int(14 * (1 - burst)) + 2))
            self._cover.set_alpha(int(255 * burst ** 1.4))
            screen.blit(self._cover, (0, 0))
        if t >= self.BURST:
            self._cover.set_alpha(255)
            screen.blit(self._cover, (0, 0))

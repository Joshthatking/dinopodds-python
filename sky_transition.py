"""Full-screen sky transition cards (day -> night, night -> day, eclipse).

A pixel-art landscape is drawn at half resolution and scaled up, matching
the title screen. The card fades in over the world, plays, calls `on_swap`
while it fully covers the screen (that's when the game flips night/day or
turns eclipse mode on), then fades back out onto the changed world.

Game.update() pauses the world and Game.events() swallows input while a
card is playing — see Game.start_sky_transition.
"""
import math
import random
import pygame
import config
from title_anim import LW, LH, ADD, _lerp_col, _scale_col, _clamp01

HORIZON = 170

# Sky palettes: (top, bottom) at day / sunset / night
SKY_DAY    = ((70, 140, 230), (175, 218, 255))
SKY_SUNSET = ((58, 46, 128), (255, 138, 84))
SKY_NIGHT  = ((5, 6, 24), (32, 26, 74))
SKY_ECLIPSE = ((6, 0, 34), (86, 22, 70))

HILL_FAR  = ((96, 168, 120), (60, 70, 120), (16, 20, 46))
HILL_NEAR = ((58, 136, 72), (46, 48, 88), (8, 10, 28))


def _smooth(p):
    p = _clamp01(p)
    return p * p * (3 - 2 * p)


def _three(cols, d):
    """Blend day(0) -> sunset(0.5) -> night(1)."""
    if d < 0.5:
        return _lerp_col(cols[0], cols[1], d * 2)
    return _lerp_col(cols[1], cols[2], (d - 0.5) * 2)


def _hill_points(rng, base, amps):
    phases = [rng.uniform(0, math.tau) for _ in amps]
    pts = [(0, LH)]
    for x in range(0, LW + 1, 2):
        y = base + sum(a * math.sin(x * f + ph) for (a, f), ph in zip(amps, phases))
        pts.append((x, int(y)))
    pts.append((LW, LH))
    return pts


class SkyTransition:
    """kind: 'to_night' | 'to_day' | 'eclipse'."""

    FADE = 0.45
    DURATIONS = {'to_night': 3.0, 'to_day': 3.0, 'eclipse': 4.5}
    SWAP_AT = {'to_night': 1.5, 'to_day': 1.5, 'eclipse': 3.0}
    CAPTIONS = {'to_night': "Night Falls", 'to_day': "Dawn Breaks", 'eclipse': "ECLIPSE"}

    def __init__(self, kind, on_swap=None, on_done=None):
        self.kind = kind
        self.on_swap = on_swap
        self.on_done = on_done
        self.duration = self.DURATIONS[kind]
        self.swap_at = self.SWAP_AT[kind]
        self.t = 0.0
        self.swapped = False
        self.done = False

        rng = random.Random(8)
        self.far_hill = _hill_points(rng, HORIZON - 22, [(7, 0.021), (4, 0.057), (2, 0.13)])
        self.near_hill = _hill_points(rng, HORIZON - 4, [(6, 0.017), (3, 0.071), (1.5, 0.19)])
        self.pines = [(rng.randrange(LW), rng.randint(7, 13)) for _ in range(26)]
        self.stars = [(rng.randrange(LW), rng.randrange(HORIZON - 30), rng.uniform(0.3, 1.0),
                       rng.uniform(0, math.tau)) for _ in range(90)]
        self.clouds = [(rng.uniform(0, LW), rng.randint(24, 90), rng.uniform(4, 9), rng.randint(3, 5))
                       for _ in range(5)]
        self.rays = [(rng.uniform(0, math.tau), rng.uniform(0.6, 1.4), rng.uniform(0, math.tau))
                     for _ in range(28)]

        self.low = pygame.Surface((LW, LH))
        self.glow = pygame.Surface((LW, LH))
        self.big = pygame.Surface((config.WIDTH, config.HEIGHT))
        font = pygame.font.Font(config.FONT_PATH_B, 36 if kind == 'eclipse' else 18)
        text = self.CAPTIONS[kind]
        col = (214, 160, 255) if kind == 'eclipse' else (255, 244, 220)
        self.caption = font.render(text, False, col).convert_alpha()
        self.caption_shadow = font.render(text, False, (10, 4, 24)).convert_alpha()
        self._white = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._white.fill((255, 255, 255))

    # --- Lifecycle ---

    def update(self, dt):
        self.t += min(dt, 1 / 20)
        if not self.swapped and self.t >= self.swap_at:
            self.swapped = True
            if self.on_swap:
                self.on_swap()
        if self.t >= self.duration and not self.done:
            self.done = True
            if self.on_done:
                self.on_done()

    @property
    def card_alpha(self):
        t = self.t
        return int(255 * min(_clamp01(t / self.FADE), _clamp01((self.duration - t) / self.FADE)))

    # --- Shared scenery ---

    @staticmethod
    def _sky_at(top, bot, y):
        return _lerp_col(top, bot, _clamp01(y / HORIZON) ** 1.4)

    def _draw_sky(self, low, top, bot):
        for y in range(0, HORIZON + 1, 2):
            pygame.draw.rect(low, self._sky_at(top, bot, y), (0, y, LW, 2))

    def _draw_stars(self, low, k):
        if k <= 0.02:
            return
        for x, y, b, ph in self.stars:
            v = _clamp01(k * b * (0.6 + 0.4 * math.sin(self.t * 3 + ph)))
            low.set_at((x, y), _lerp_col(low.get_at((x, y))[:3], (255, 250, 235), v))

    def _draw_clouds(self, low, col):
        for x0, y, sp, n in self.clouds:
            x = (x0 + self.t * sp) % (LW + 60) - 30
            for i in range(n):
                pygame.draw.ellipse(low, col, (int(x + i * 9), y - (4 if i % 2 else 0), 16, 9))

    def _draw_land(self, low, d, far=None, near=None):
        far = far or _three(HILL_FAR, d)
        near = near or _three(HILL_NEAR, d)
        pygame.draw.polygon(low, far, self.far_hill)
        pygame.draw.polygon(low, near, self.near_hill)
        tree = _scale_col(near, 0.75)
        for x, h in self.pines:
            base = HORIZON - 4 + 6 * math.sin(x * 0.017)
            pygame.draw.polygon(low, tree, [(x, base - h), (x - 4, base + 1), (x + 4, base + 1)])

    def _sun_glow(self, glow, x, y, r, col, k=1.0):
        for i, (rr, f) in enumerate(((r * 4, 0.18), (r * 2.6, 0.3), (r * 1.7, 0.5))):
            pygame.draw.circle(glow, _scale_col(col, f * k), (int(x), int(y)), int(rr))

    def _letterbox(self, low):
        pygame.draw.rect(low, (0, 0, 0), (0, 0, LW, 14))
        pygame.draw.rect(low, (0, 0, 0), (0, LH - 14, LW, 14))

    def _caption(self, low, alpha, y):
        if alpha <= 0:
            return
        x = LW // 2 - self.caption.get_width() // 2
        for surf, off in ((self.caption_shadow, 1), (self.caption, 0)):
            s = surf.copy()
            s.set_alpha(int(alpha))
            low.blit(s, (x + off, y + off))

    # --- Day <-> night ---

    def _render_day_night(self):
        low, glow = self.low, self.glow
        # scene progress: 0 = day, 1 = night
        p = _smooth((self.t - self.FADE * 0.6) / (self.duration - self.FADE * 1.6))
        d = p if self.kind == 'to_night' else 1 - p

        top, bot = _three((SKY_DAY[0], SKY_SUNSET[0], SKY_NIGHT[0]), d), \
            _three((SKY_DAY[1], SKY_SUNSET[1], SKY_NIGHT[1]), d)
        self._draw_sky(low, top, bot)
        self._draw_stars(low, _clamp01((d - 0.55) / 0.35))

        glow.fill((0, 0, 0))
        # Sun sinks right / rises right; moon rises left / sets left
        sx, sy = 150 + 110 * d, 52 + 150 * d ** 1.2
        sun_col = _lerp_col((255, 250, 200), (255, 120, 50), _clamp01(d * 1.6))
        self._sun_glow(glow, sx, sy, 13, sun_col, 1.0 - 0.4 * d)
        mx, my = 70 + 40 * d, 205 - 150 * d ** 0.9
        self._sun_glow(glow, mx, my, 10, (120, 140, 200), _clamp01((d - 0.3) / 0.5))
        low.blit(glow, (0, 0), special_flags=ADD)

        pygame.draw.circle(low, sun_col, (int(sx), int(sy)), 13)
        pygame.draw.circle(low, _lerp_col((255, 255, 240), sun_col, 0.4), (int(sx) - 3, int(sy) - 3), 6)
        moon_k = _clamp01((d - 0.2) / 0.4)
        if moon_k > 0:
            moon = pygame.Surface((22, 22), pygame.SRCALPHA)
            pygame.draw.circle(moon, (236, 236, 255, int(255 * moon_k)), (11, 11), 10)
            pygame.draw.circle(moon, (0, 0, 0, 0), (16, 8), 9)   # cut out the crescent
            low.blit(moon, (int(mx) - 11, int(my) - 11))

        self._draw_clouds(low, _three(((250, 250, 255), (250, 170, 160), (40, 44, 84)), d))
        self._draw_land(low, d)
        self._letterbox(low)

        cap = math.sin(math.pi * _clamp01((self.t - 0.6) / (self.duration - 1.2)))
        self._caption(low, 255 * cap, HORIZON + 26)
        return 0

    # --- Eclipse ---

    COVER_START, COVER_END = 0.4, 2.4

    def _render_eclipse(self):
        low, glow = self.low, self.glow
        t = self.t
        cover = _smooth((t - self.COVER_START) / (self.COVER_END - self.COVER_START))
        total = t >= self.COVER_END
        after = t - self.COVER_END

        d = cover ** 1.5   # darkness
        top = _lerp_col(SKY_DAY[0], SKY_ECLIPSE[0], d)
        bot = _lerp_col(SKY_DAY[1], SKY_ECLIPSE[1], d)
        self._draw_sky(low, top, bot)
        self._draw_stars(low, _clamp01((cover - 0.7) / 0.3))

        sx, sy, R = LW // 2, 74, 22
        glow.fill((0, 0, 0))
        if not total:
            self._sun_glow(glow, sx, sy, R, (255, 236, 170), 1.0 - 0.75 * cover)
        else:
            pulse = 0.85 + 0.15 * math.sin(after * 9)
            self._sun_glow(glow, sx, sy, R, (170, 80, 255), pulse)
            # Corona: long flickering rays + rings rolling outward
            for ang, ln, ph in self.rays:
                L = R * (1.2 + ln * (1.0 + 0.35 * math.sin(after * 5 + ph))) * min(1.0, after * 3 + 0.3)
                ca, sa = math.cos(ang + after * 0.15), math.sin(ang + after * 0.15)
                col = (210, 140, 255) if ln > 1 else (255, 210, 255)
                pygame.draw.line(glow, _scale_col(col, 0.85 * pulse), (sx + ca * R, sy + sa * R),
                                 (sx + ca * (R + L), sy + sa * (R + L)), 2)
            for k in range(3):
                q = (after * 0.8 + k / 3) % 1.0
                pygame.draw.circle(glow, _scale_col((150, 70, 230), 0.6 * (1 - q)), (sx, sy), int(R + 10 + q * 150), 2)
        low.blit(glow, (0, 0), special_flags=ADD)

        if not total:
            pygame.draw.circle(low, (255, 246, 196), (sx, sy), R)
            pygame.draw.circle(low, (255, 255, 236), (sx - 5, sy - 5), 10)
        else:
            pygame.draw.circle(low, (230, 200, 255), (sx, sy), R + 2)
        # The moon slides in from the left and locks over the sun
        mx = int(sx - (R * 2 + 70) * (1 - cover))
        pygame.draw.circle(low, (8, 2, 20), (mx, sy), R + 1)

        # Diamond ring right as totality hits
        if 0 <= after < 0.5:
            k = 1 - after / 0.5
            glow.fill((0, 0, 0))
            dx, dy = sx + R * 0.7, sy - R * 0.7
            pygame.draw.circle(glow, _scale_col((255, 255, 255), k), (int(dx), int(dy)), int(4 + 8 * k))
            pygame.draw.line(glow, _scale_col((255, 255, 255), k), (dx - 40 * k, dy), (dx + 40 * k, dy), 2)
            pygame.draw.line(glow, _scale_col((255, 255, 255), k), (dx, dy - 30 * k), (dx, dy + 30 * k), 2)
            low.blit(glow, (0, 0), special_flags=ADD)

        self._draw_clouds(low, _lerp_col((250, 250, 255), (36, 20, 60), d))
        self._draw_land(low, d,
                        _lerp_col(HILL_FAR[0], (34, 14, 60), d),
                        _lerp_col(HILL_NEAR[0], (14, 4, 30), d))
        self._letterbox(low)

        if total:
            self._caption(low, 255 * _clamp01((after - 0.35) / 0.4) * _clamp01((self.duration - 0.3 - t) / 0.4),
                          HORIZON + 14)

        # Rumble builds as the moon closes in, peaks at totality
        shake = 0
        if cover > 0.6 and not total:
            shake = int(1 + 2 * (cover - 0.6) / 0.4)
        elif total and after < 1.0:
            shake = int(4 * (1 - after))
        return shake

    # --- Draw ---

    def draw(self, screen):
        shake = self._render_eclipse() if self.kind == 'eclipse' else self._render_day_night()
        pygame.transform.scale(self.low, self.big.get_size(), self.big)
        alpha = self.card_alpha
        self.big.set_alpha(alpha)
        if shake and alpha >= 255:
            screen.fill((0, 0, 0))
            off = (random.randint(-shake, shake) * 2, random.randint(-shake, shake) * 2)
        else:
            off = (0, 0)
        screen.blit(self.big, off)

        if self.kind == 'eclipse':
            after = self.t - self.COVER_END
            if 0 <= after < 0.35:
                self._white.set_alpha(int(230 * (1 - after / 0.35)))
                screen.blit(self._white, (0, 0))

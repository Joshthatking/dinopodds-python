"""Space backdrops for the celestial planet maps, drawn behind the map tiles
(in place of the black fill) the same way aether_bg is for Horizon Cave.

  LunarBackground — a dark galaxy: deep violet gradient, a dim spiral galaxy,
                    parallax starfields and three moons slowly drifting.
  SolarBackground — ordinary space: starfields, twinkling stars, comets
                    streaking past every few seconds, and a big glowing sun
                    whose corona pulses and which throws a solar flare
                    (prominence arc + ejecta + flash) periodically.

Everything is procedural (no image assets). Usage, see Game.draw:
    bg.draw(render_surface, camera_x, camera_y, seconds)
"""
import math
import random
import pygame


# ── shared helpers ───────────────────────────────────────────────────────

def _soft_blob(r, col, strength=0.35):
    """Radial glow sprite for additive blending."""
    spr = pygame.Surface((r * 2, r * 2))
    steps = max(4, r // 3)
    for i in range(steps):
        f = (i + 1) / steps
        pygame.draw.circle(spr, tuple(int(c * f * f * strength) for c in col), (r, r),
                           max(1, int(r * (1 - i / steps))))
    return spr


def _gradient(size, top, bottom):
    w, h = size
    g = pygame.Surface(size)
    for y in range(h):
        f = y / max(1, h - 1)
        pygame.draw.line(g, tuple(int(a + (b - a) * f) for a, b in zip(top, bottom)), (0, y), (w, y))
    return g


def _star_tile(rng, size, count, max_r, bright, tints):
    tile = pygame.Surface((size, size))
    tile.fill((0, 0, 0))
    for _ in range(count):
        x, y = rng.randrange(size), rng.randrange(size)
        b = rng.randint(bright // 2, bright)
        tr, tg, tb = rng.choice(tints)
        col = (int(b * tr), int(b * tg), int(b * tb))
        r = rng.randint(1, max_r)
        if r == 1:
            tile.set_at((x, y), col)
        else:
            pygame.draw.circle(tile, col, (x, y), r)
    return tile


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


class _Backdrop:
    """Gradient + parallax starfields + twinkling stars, shared by both."""
    STAR_TILE = 256

    def __init__(self, rng, top, bottom, star_layers, tints, twinkle_n):
        self._top, self._bottom = top, bottom
        self._grad = None
        self._stars = [(p, _star_tile(rng, self.STAR_TILE, n, r, b, tints)) for p, n, r, b in star_layers]
        self._twinklers = [(rng.uniform(0, 512), rng.uniform(0, 512),
                            rng.uniform(0, math.tau), rng.uniform(1.2, 3.2)) for _ in range(twinkle_n)]

    def _draw_base(self, surface, cam_x, cam_y, t):
        size = surface.get_size()
        if self._grad is None or self._grad.get_size() != size:
            self._grad = _gradient(size, self._top, self._bottom)
        surface.blit(self._grad, (0, 0))

    def _draw_stars(self, surface, cam_x, cam_y, t):
        for parallax, tile in self._stars:
            _tile_blit(surface, tile, cam_x, cam_y, parallax)
        w, h = surface.get_size()
        for tx, ty, phase, speed in self._twinklers:
            k = 0.5 + 0.5 * math.sin(t * speed + phase)
            if k < 0.2:
                continue
            x = int((tx - cam_x * 0.35) % 512)
            y = int((ty - cam_y * 0.35) % 512)
            if x >= w or y >= h:
                continue
            c = int(255 * k)
            arm = 1 + int(3 * k)
            pygame.draw.line(surface, (c, c, c), (x - arm, y), (x + arm, y))
            pygame.draw.line(surface, (c, c, c), (x, y - arm), (x, y + arm))
            surface.set_at((x, y), (255, 255, 255))


# ── lunar: moons over a dark galaxy ──────────────────────────────────────

def _moon(rng, r, base, dark, light, craters):
    """Pixel-art moon: shaded disc, terminator on the lower-right, craters."""
    d = r * 2 + 2
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = r + 1
    lx, ly = -0.62, -0.5
    lz = math.sqrt(max(0.0, 1 - lx * lx - ly * ly))
    for py in range(d):
        for px in range(d):
            nx, ny = (px + 0.5 - c) / r, (py + 0.5 - c) / r
            q = nx * nx + ny * ny
            if q > 1:
                continue
            nz = math.sqrt(1 - q)
            lit = nx * lx + ny * ly + nz * lz
            k = max(0.0, lit)
            if k < 0.12:
                col = dark
            elif k < 0.5:
                col = tuple(int(dv + (bv - dv) * (k - 0.12) / 0.38) for dv, bv in zip(dark, base))
            else:
                col = tuple(int(bv + (lv - bv) * (k - 0.5) / 0.5) for bv, lv in zip(base, light))
            s.set_at((px, py), col)
    for _ in range(craters):
        a, dist = rng.uniform(0, math.tau), rng.uniform(0, r * 0.75)
        cx, cy = c + math.cos(a) * dist, c + math.sin(a) * dist
        cr = max(1, int(rng.uniform(0.04, 0.12) * r))
        shade = s.get_at((int(cx), int(cy)))
        if shade.a == 0:
            continue
        darker = tuple(int(v * 0.86) for v in shade[:3])
        lighter = tuple(min(255, int(v * 1.1)) for v in shade[:3])
        pygame.draw.circle(s, darker, (int(cx), int(cy)), cr)
        if cr > 1:
            pygame.draw.arc(s, lighter, (int(cx) - cr, int(cy) - cr, cr * 2, cr * 2), math.pi * 1.1, math.pi * 1.9, 1)
    # thin bright limb on the lit side
    pygame.draw.arc(s, light, (1, 1, d - 2, d - 2), math.pi * 0.55, math.pi * 1.05, 1)
    return s


def _spiral_galaxy(rng, size):
    g = pygame.Surface((size, size))
    g.fill((0, 0, 0))
    c = size / 2
    cols = [(110, 60, 190), (70, 50, 170), (150, 70, 170), (60, 80, 180)]
    for arm in range(2):
        for i in range(140):
            f = i / 140
            ang = arm * math.pi + f * 3.4 * math.pi
            dist = 6 + f * size * 0.42
            x = c + math.cos(ang) * dist + rng.uniform(-6, 6)
            y = c + math.sin(ang) * dist * 0.55 + rng.uniform(-4, 4)    # tilted disc
            br = int(rng.uniform(5, 13) * (1.2 - f * 0.6))
            blob = _soft_blob(br, rng.choice(cols), 0.22 * (1.1 - f * 0.6))
            g.blit(blob, (x - br, y - br), special_flags=pygame.BLEND_RGB_ADD)
            if rng.random() < 0.5:
                g.set_at((int(x), int(y)), (200, 180, 255))
    core = _soft_blob(int(size * 0.13), (230, 200, 255), 0.6)
    g.blit(core, (c - core.get_width() / 2, c - core.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
    return g


class LunarBackground(_Backdrop):
    def __init__(self, seed=21):
        rng = random.Random(seed)
        super().__init__(rng, top=(3, 2, 10), bottom=(14, 6, 26),
                         star_layers=((0.12, 80, 1, 110), (0.25, 50, 1, 170), (0.45, 18, 2, 230)),
                         tints=((1, 1, 1), (0.8, 0.8, 1), (0.9, 0.75, 1)), twinkle_n=10)
        self._galaxy = _spiral_galaxy(rng, 300)
        self._dust = pygame.Surface((512, 512))
        self._dust.fill((0, 0, 0))
        for _ in range(16):
            r = rng.randint(50, 120)
            blob = _soft_blob(r, rng.choice([(60, 20, 90), (30, 20, 80), (70, 30, 70)]), 0.25)
            for dx in (-512, 0, 512):
                for dy in (-512, 0, 512):
                    self._dust.blit(blob, (rng.randrange(512) - r + dx, rng.randrange(512) - r + dy),
                                    special_flags=pygame.BLEND_RGB_ADD)
        # (sprite, screen fx, fy, parallax, drift radius px, drift speed, phase)
        self._moons = [
            (_moon(rng, 64, (176, 178, 196), (40, 40, 62), (232, 234, 248), 16), 0.8, 0.2, 0.02, 6, 0.05, 0.0),
            (_moon(rng, 20, (120, 150, 210), (26, 30, 66), (196, 220, 255), 6), 0.17, 0.62, 0.05, 14, 0.09, 1.3),
            (_moon(rng, 11, (200, 120, 110), (54, 24, 34), (255, 190, 170), 3), 0.42, 0.13, 0.07, 18, 0.13, 2.6),
        ]
        self._moon_glow = [_soft_blob(int(m[0].get_width() * 0.85), (120, 110, 200), 0.35) for m in self._moons]

    def draw(self, surface, cam_x, cam_y, t):
        w, h = surface.get_size()
        self._draw_base(surface, cam_x, cam_y, t)
        _tile_blit(surface, self._dust, cam_x + t * 2, cam_y + t, 0.06)
        gx = w * 0.32 - cam_x * 0.03 - self._galaxy.get_width() / 2
        gy = h * 0.42 - cam_y * 0.03 - self._galaxy.get_height() / 2
        surface.blit(self._galaxy, (gx, gy), special_flags=pygame.BLEND_RGB_ADD)
        self._draw_stars(surface, cam_x, cam_y, t)
        for (spr, fx, fy, par, drift, speed, ph), glow in zip(self._moons, self._moon_glow):
            x = w * fx - cam_x * par + math.cos(t * speed + ph) * drift
            y = h * fy - cam_y * par + math.sin(t * speed + ph) * drift * 0.5
            surface.blit(glow, (x - glow.get_width() / 2, y - glow.get_height() / 2),
                         special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(spr, (x - spr.get_width() / 2, y - spr.get_height() / 2))


# ── solar: stars, comets and a flaring sun ───────────────────────────────

SUN_CORE = (255, 250, 220)
SUN_MID = (255, 214, 96)
SUN_EDGE = (255, 150, 40)
FLARE_COLS = [(255, 250, 210), (255, 210, 90), (255, 140, 40), (230, 80, 30)]


def _sun_disc(rng, r):
    """Photosphere with limb darkening and granulation speckle."""
    d = r * 2 + 2
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    c = r + 1
    for py in range(d):
        for px in range(d):
            q = ((px + 0.5 - c) ** 2 + (py + 0.5 - c) ** 2) / (r * r)
            if q > 1:
                continue
            mu = math.sqrt(1 - q)                 # 1 at centre, 0 at the limb
            k = 0.35 + 0.65 * mu + rng.uniform(-0.06, 0.06)
            if k > 0.85:
                col = SUN_CORE
            elif k > 0.62:
                col = SUN_MID
            else:
                col = SUN_EDGE
            s.set_at((px, py), col)
    return s


class SolarBackground(_Backdrop):
    SUN_R = 46
    FLARE_EVERY = (6.0, 11.0)
    FLARE_LEN = 3.2
    COMET_EVERY = (3.5, 8.0)

    def __init__(self, seed=33):
        self._rng = random.Random(seed)
        rng = self._rng
        super().__init__(rng, top=(1, 3, 12), bottom=(6, 10, 26),
                         star_layers=((0.12, 90, 1, 130), (0.25, 55, 1, 200), (0.45, 22, 2, 255)),
                         tints=((1, 1, 1), (0.85, 0.9, 1), (1, 0.92, 0.8)), twinkle_n=16)
        self._sun = _sun_disc(rng, self.SUN_R)
        self._corona = [_soft_blob(int(self.SUN_R * f), col, s) for f, col, s in
                        ((3.4, (255, 120, 30), 0.30), (2.3, (255, 170, 60), 0.45), (1.55, (255, 230, 150), 0.7))]
        self._flare_glow = _soft_blob(18, (255, 200, 90), 0.8)
        self._ember = {c: _soft_blob(4, c, 0.9) for c in FLARE_COLS}
        self._comet_head = _soft_blob(7, (200, 230, 255), 0.9)
        self._flare = None
        self._next_flare = rng.uniform(2.0, 4.0)
        self._comets = []
        self._next_comet = rng.uniform(1.0, 3.0)
        self._last_t = None

    # ── timing ──
    def _advance(self, t, w, h):
        dt = 0.0 if self._last_t is None else max(0.0, min(0.1, t - self._last_t))
        self._last_t = t
        rng = self._rng
        self._next_flare -= dt
        if self._flare is None and self._next_flare <= 0:
            ang = rng.uniform(math.pi * 0.55, math.pi * 1.25)    # erupts on the side facing the map
            self._flare = {'t': 0.0, 'ang': ang, 'span': rng.uniform(0.35, 0.6),
                           'height': rng.uniform(0.9, 1.5),
                           'embers': [(rng.uniform(-0.25, 0.25), rng.uniform(40, 95), rng.choice(FLARE_COLS))
                                      for _ in range(14)]}
            self._next_flare = rng.uniform(*self.FLARE_EVERY)
        if self._flare is not None:
            self._flare['t'] += dt
            if self._flare['t'] >= self.FLARE_LEN:
                self._flare = None
        self._next_comet -= dt
        if self._next_comet <= 0:
            # enter from the top or left edge, travel down-right / down-left
            if rng.random() < 0.5:
                x, y, vx = rng.uniform(-0.1, 0.6) * w, -10, rng.uniform(60, 120)
            else:
                x, y, vx = -10, rng.uniform(0.0, 0.5) * h, rng.uniform(90, 140)
            vy = rng.uniform(30, 70)
            if rng.random() < 0.3:
                x, vx = w + 10, -vx
            self._comets.append({'x': x, 'y': y, 'vx': vx, 'vy': vy, 'len': rng.uniform(26, 48),
                                 'col': rng.choice([(180, 220, 255), (200, 255, 230), (255, 230, 200)])})
            self._next_comet = rng.uniform(*self.COMET_EVERY)
        for c in self._comets:
            c['x'] += c['vx'] * dt
            c['y'] += c['vy'] * dt
        self._comets = [c for c in self._comets if -80 < c['x'] < w + 80 and c['y'] < h + 80]

    # ── drawing ──
    def draw(self, surface, cam_x, cam_y, t):
        w, h = surface.get_size()
        self._advance(t, w, h)
        self._draw_base(surface, cam_x, cam_y, t)
        self._draw_stars(surface, cam_x, cam_y, t)
        self._draw_comets(surface)
        self._draw_sun(surface, w * 0.8 - cam_x * 0.02, h * 0.24 - cam_y * 0.02, t)

    def _draw_comets(self, surface):
        for c in self._comets:
            sp = math.hypot(c['vx'], c['vy'])
            ux, uy = c['vx'] / sp, c['vy'] / sp
            n = int(c['len'])
            for i in range(n, 0, -1):
                f = 1 - i / n
                col = tuple(int(v * f * 0.8) for v in c['col'])
                x, y = c['x'] - ux * i, c['y'] - uy * i
                surface.set_at((int(x), int(y)), col)
                if i < n * 0.4:   # wider near the head
                    surface.set_at((int(x - uy), int(y + ux)), tuple(v // 2 for v in col))
            surface.blit(self._comet_head, (c['x'] - 7, c['y'] - 7), special_flags=pygame.BLEND_RGB_ADD)
            surface.set_at((int(c['x']), int(c['y'])), (255, 255, 255))

    def _draw_sun(self, surface, sx, sy, t):
        R = self.SUN_R
        f = self._flare
        flash = 0.0
        if f is not None:
            p = f['t'] / self.FLARE_LEN
            flash = max(0.0, 1 - abs(p - 0.25) / 0.25) * 0.6
        pulse = 1 + 0.05 * math.sin(t * 1.3) + 0.03 * math.sin(t * 3.1) + flash * 0.25
        for i, glow in enumerate(self._corona):
            gw = int(glow.get_width() * (pulse if i < 2 else 1 + (pulse - 1) * 0.5))
            g = pygame.transform.smoothscale(glow, (gw, gw)) if gw != glow.get_width() else glow
            surface.blit(g, (sx - gw / 2, sy - gw / 2), special_flags=pygame.BLEND_RGB_ADD)
            if flash > 0.05 and i == 1:   # flare brightens the corona
                surface.blit(g, (sx - gw / 2, sy - gw / 2), special_flags=pygame.BLEND_RGB_ADD)
        surface.blit(self._sun, (sx - R - 1, sy - R - 1))
        if f is not None:
            self._draw_flare(surface, sx, sy, f)

    def _draw_flare(self, surface, sx, sy, f):
        R = self.SUN_R
        p = f['t'] / self.FLARE_LEN
        grow = min(1.0, p / 0.35)                 # arc rises
        fade = 1.0 if p < 0.6 else max(0.0, 1 - (p - 0.6) / 0.4)
        a0, a1 = f['ang'] - f['span'] / 2, f['ang'] + f['span'] / 2
        # prominence: a loop of plasma arcing between two foot points on the limb
        steps = 26
        pts = []
        for i in range(steps + 1):
            u = i / steps
            a = a0 + (a1 - a0) * u
            lift = math.sin(u * math.pi) * R * f['height'] * grow
            r = R + lift
            pts.append((sx + math.cos(a) * r, sy + math.sin(a) * r))
        if fade > 0.02:
            for width, col in ((7, FLARE_COLS[3]), (4, FLARE_COLS[2]), (2, FLARE_COLS[1]), (1, FLARE_COLS[0])):
                c = tuple(int(v * fade) for v in col)
                pygame.draw.lines(surface, c, False, pts, width)
            top = pts[steps // 2]
            surface.blit(self._flare_glow, (top[0] - 18, top[1] - 18), special_flags=pygame.BLEND_RGB_ADD)
        # ejecta: embers thrown outward once the loop snaps
        if p > 0.3:
            q = (p - 0.3) / 0.7
            for da, speed, col in f['embers']:
                a = f['ang'] + da
                r = R * (1 + f['height'] * 0.8) + speed * q * 1.4
                x, y = sx + math.cos(a) * r, sy + math.sin(a) * r
                if (1 - q) > 0.05:
                    e = self._ember[col]
                    surface.blit(e, (x - 4, y - 4), special_flags=pygame.BLEND_RGB_ADD)
                    surface.set_at((int(x), int(y)), tuple(int(v * (1 - q)) for v in col))

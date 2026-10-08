"""Launch splash + animated pixel-space title backdrop.

Everything is drawn on a half-resolution surface and scaled up with
nearest-neighbour so it reads as chunky pixel art. Glowing effects (flare
waves, shooting stars, corona, prominences, sparks) are drawn onto a black
"glow" surface which is then added onto the scene with BLEND_RGB_ADD.

LaunchIntro timeline (seconds):
    0.0 - 0.6   black
    0.6 - 5.0   "JoshThatKing / EST. 2025" fades in, holds, fades out
    5.6 - 10.6  space backdrop fades in (shooting stars, flare waves)
    10.6        white flash -> DINOPODDS / Ultra Violet + sun, loops forever
Input is ignored until shortly after the flash.
"""
import math
import random
import pygame
import config

SCALE = 2
LW, LH = config.WIDTH // SCALE, config.HEIGHT // SCALE
ADD = pygame.BLEND_RGB_ADD

SUN_C = (LW - 26, LH - 22)
SUN_R = 40
LOGO_Y = 30          # low-res y of the DINOPODDS logo top
WAVE_MAX_R = 430
WAVE_ANGLES = [math.radians(a) for a in range(156, 296, 2)]

STAR_COLS = [(255, 255, 255), (200, 215, 255), (255, 235, 200), (255, 200, 235), (190, 255, 245)]


def _clamp01(v):
    return max(0.0, min(1.0, v))


def _lerp_col(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _scale_col(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def _add_px(surf, x, y, col):
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        r, g, b = surf.get_at((x, y))[:3]
        surf.set_at((x, y), (min(255, r + col[0]), min(255, g + col[1]), min(255, b + col[2])))


def _tint(surf, col):
    out = surf.copy()
    out.fill(tuple(col) + (255,), special_flags=pygame.BLEND_RGBA_MULT)
    return out


# --- 3D logo text ---

def _render_3d_text(text, font, face_cols, side_near, side_far, depth, outline_w,
                    outline=(10, 4, 22)):
    """Pixel text with a dark outline, a diagonal extrusion and a banded gradient face."""
    # Non-AA renders are colorkeyed; convert so tinting keeps transparency
    face = font.render(text, False, (255, 255, 255)).convert_alpha()
    w, h = face.get_size()
    p = outline_w
    out = pygame.Surface((w + depth + p * 2, h + depth + p * 2), pygame.SRCALPHA)

    # Outline silhouette around the whole extruded shape
    sil = _tint(face, outline)
    for d in range(depth, -1, -1):
        for dx in range(-p, p + 1):
            for dy in range(-p, p + 1):
                if dx * dx + dy * dy <= p * p + 1:
                    out.blit(sil, (p + d + dx, p + d + dy))

    # Extrusion, darkening with depth
    for d in range(depth, 0, -1):
        out.blit(_tint(face, _lerp_col(side_near, side_far, (d - 1) / max(1, depth - 1))), (p + d, p + d))

    # Light rim on the top-left edge
    out.blit(_tint(face, (255, 250, 230)), (p - 1, p - 1))

    # Face: 3-stop vertical gradient, quantised into bands for a pixel look
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    bands = 6
    for y in range(h):
        t = math.floor(y / h * bands) / (bands - 1)
        if t < 0.5:
            col = _lerp_col(face_cols[0], face_cols[1], t * 2)
        else:
            col = _lerp_col(face_cols[1], face_cols[2], (t - 0.5) * 2)
        pygame.draw.line(grad, col + (255,), (0, y), (w, y))
    grad.blit(face, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(grad, (p, p))
    return out


def _make_halo(img, col, pad=8):
    w, h = img.get_size()
    base = pygame.Surface((w + pad * 2, h + pad * 2))
    base.fill((0, 0, 0))
    sil = pygame.mask.from_surface(img).to_surface(setcolor=col + (255,), unsetcolor=(0, 0, 0, 255))
    base.blit(sil, (pad, pad))
    bw, bh = base.get_size()
    small = pygame.transform.smoothscale(base, (max(1, bw // 5), max(1, bh // 5)))
    return pygame.transform.smoothscale(small, (bw, bh))


class TitleLogo:
    HALO_PAD = 8

    def __init__(self):
        big = pygame.font.Font(config.FONT_PATH_B, 36)
        small = pygame.font.Font(config.FONT_PATH_B, 18)
        self.title = _render_3d_text(
            "DINOPODDS", big,
            face_cols=((255, 246, 180), (255, 200, 60), (236, 112, 30)),
            side_near=(176, 64, 156), side_far=(48, 10, 72),
            depth=5, outline_w=2)
        self.sub = _render_3d_text(
            "Ultra Violet", small,
            face_cols=((250, 226, 255), (204, 140, 255), (140, 66, 232)),
            side_near=(96, 40, 160), side_far=(32, 10, 64),
            depth=3, outline_w=1)
        self.halo = _make_halo(self.title, (110, 50, 150), self.HALO_PAD)
        self.sub_halo = _make_halo(self.sub, (130, 50, 220), self.HALO_PAD)

        # Diagonal glint stripe swept across the title every few seconds
        th = self.title.get_height()
        self.stripe = pygame.Surface((th + 10, th))
        self.stripe.fill((0, 0, 0))
        pygame.draw.polygon(self.stripe, (150, 130, 90), [(th, 0), (th + 7, 0), (7, th), (0, th)])
        self.t = 0.0

    @property
    def height(self):
        return self.title.get_height() + 2 + self.sub.get_height()

    def update(self, dt):
        self.t += dt

    def draw(self, low, y):
        t = self.t
        bob = int(round(math.sin(t * 1.6) * 1.5))
        tx = LW // 2 - self.title.get_width() // 2
        ty = y + bob
        sx = LW // 2 - self.sub.get_width() // 2
        sy = y + self.title.get_height() + 2

        hp = self.HALO_PAD
        halo = self.halo.copy()
        halo.fill(_scale_col((255, 255, 255), 0.7 + 0.3 * math.sin(t * 2.2)), special_flags=pygame.BLEND_RGB_MULT)
        low.blit(halo, (tx - hp, ty - hp), special_flags=ADD)
        sub_halo = self.sub_halo.copy()
        sub_halo.fill(_scale_col((255, 255, 255), 0.75 + 0.25 * math.sin(t * 2.2 + 2.0)), special_flags=pygame.BLEND_RGB_MULT)
        low.blit(sub_halo, (sx - hp, sy - hp), special_flags=ADD)

        title = self.title
        cycle = t % 4.5
        if cycle < 0.9:
            title = self.title.copy()
            gx = int(-self.stripe.get_width() + (title.get_width() + self.stripe.get_width()) * (cycle / 0.9))
            title.blit(self.stripe, (gx, 0), special_flags=ADD)
        low.blit(title, (tx, ty))
        low.blit(self.sub, (sx, sy))


# --- Space backdrop ---

class TitleBackdrop:
    def __init__(self, seed=2025):
        rng = random.Random(seed)
        self.rng = random.Random()
        self.t = 0.0
        self.show_sun = True

        self.sky = self._bake_sky(rng)
        self.sun_frames = self._bake_sun(rng)
        self.low = pygame.Surface((LW, LH))
        self.glow = pygame.Surface((LW, LH))

        self.twinkles = [dict(x=rng.randrange(LW), y=rng.randrange(LH), b=rng.uniform(0.6, 1.0),
                              sp=rng.uniform(1.5, 4.0), ph=rng.uniform(0, math.tau),
                              col=rng.choice(STAR_COLS), big=rng.random() < 0.3)
                         for _ in range(42)]
        self.drifters = [[rng.uniform(0, LW), rng.randrange(LH), rng.uniform(1.5, 5.0), rng.randint(80, 170)]
                         for _ in range(50)]

        self.shooting = []
        self.waves = []
        self.proms = []
        self.sparks = []
        # First shooting star / wave arrive quickly so the intro always shows them
        self._shoot_timer = 0.9
        self._wave_timer = 0.4
        self._prom_timer = 0.0
        self._spark_acc = 0.0

    # --- Baking ---

    def _bake_sky(self, rng):
        sky = pygame.Surface((LW, LH))
        top, bot = (3, 2, 12), (16, 6, 30)
        for y in range(LH):
            pygame.draw.line(sky, _lerp_col(top, bot, y / (LH - 1)), (0, y), (LW, y))

        # Nebula — soft additive blobs clustered along a diagonal band
        neb_cols = [(14, 4, 26), (6, 8, 28), (18, 4, 20), (4, 12, 22)]
        for _ in range(34):
            t = rng.random()
            cx = int(-20 + (LW + 40) * t + rng.uniform(-40, 40))
            cy = int(LH * 0.15 + LH * 0.65 * t + rng.uniform(-30, 30))
            R = rng.randint(14, 42)
            col = rng.choice(neb_cols)
            blob = pygame.Surface((R * 2, R * 2))
            for i, r in enumerate(range(R, 0, -max(2, R // 6))):
                pygame.draw.circle(blob, _scale_col(col, 0.35 + 0.13 * i), (R, R), r)
            sky.blit(blob, (cx - R, cy - R), special_flags=ADD)

        # Distant galaxies (placed clear of the logo, menu and sun)
        for cx, cy, size in ((40, 150, 15), (284, 30, 12), (68, 20, 8), (178, 210, 7), (236, 124, 5)):
            self._bake_galaxy(sky, rng, cx, cy, size)

        # Faint background stars
        for _ in range(260):
            col = _scale_col(rng.choice(STAR_COLS), rng.uniform(0.15, 0.6))
            _add_px(sky, rng.randrange(LW), rng.randrange(LH), col)
        return sky

    def _bake_galaxy(self, surf, rng, cx, cy, size):
        tilt = rng.uniform(0.35, 0.7)
        phi = rng.uniform(0, math.pi)
        rot = rng.uniform(0, math.tau)
        hue = rng.choice([(80, 64, 120), (100, 76, 64), (64, 84, 120)])
        cs, sn = math.cos(phi), math.sin(phi)
        n = size * 14
        for arm in range(2):
            for i in range(n):
                t = i / n
                ang = rot + arm * math.pi + t * 3.2 * math.pi
                r = t * size + rng.uniform(-1, 1)
                x, y = math.cos(ang) * r, math.sin(ang) * r * tilt
                _add_px(surf, int(round(cx + x * cs - y * sn)), int(round(cy + x * sn + y * cs)),
                        _scale_col(hue, (1 - t) * 0.6 + 0.15))
        core = pygame.Surface((9, 9))
        for r, k in ((4, 0.25), (2, 0.6), (1, 1.0)):
            pygame.draw.circle(core, _scale_col((210, 190, 240), k), (4, 4), r)
        surf.blit(core, (cx - 4, cy - 4), special_flags=ADD)

    def _bake_sun(self, rng):
        R = SUN_R
        rings = [(R, (196, 58, 14)), (R - 2, (226, 94, 20)), (R - 6, (244, 140, 34)),
                 (R - 13, (252, 186, 66)), (R - 22, (255, 220, 120)), (R - 30, (255, 242, 190))]
        spots = [(rng.uniform(math.radians(170), math.radians(260)), rng.uniform(R * 0.35, R * 0.75))
                 for _ in range(3)]
        frames = []
        for _ in range(3):
            s = pygame.Surface((R * 2 + 2, R * 2 + 2), pygame.SRCALPHA)
            c = (R + 1, R + 1)
            for r, col in rings:
                pygame.draw.circle(s, col, c, r)
            # Granulation shimmer — differs per frame
            for _ in range(160):
                a = rng.uniform(0, math.tau)
                d = math.sqrt(rng.random()) * (R - 2)
                x, y = int(c[0] + math.cos(a) * d), int(c[1] + math.sin(a) * d)
                base = s.get_at((x, y))
                k = rng.choice((0.82, 0.88, 1.08))
                s.set_at((x, y), _scale_col(base[:3], k) + (255,))
            for a, d in spots:
                x, y = int(c[0] + math.cos(a) * d), int(c[1] + math.sin(a) * d)
                pygame.draw.circle(s, (150, 50, 14), (x, y), 2)
                s.set_at((x, y), (100, 30, 10, 255))
            frames.append(s)
        return frames

    # --- Spawning ---

    def _spawn_shooting_star(self):
        rng = self.rng
        if rng.random() < 0.65:   # down-left
            ang = math.radians(rng.uniform(148, 166))
            x, y = rng.uniform(LW * 0.35, LW + 30), rng.uniform(-10, LH * 0.35)
        else:                     # down-right
            ang = math.radians(rng.uniform(16, 34))
            x, y = rng.uniform(-30, LW * 0.6), rng.uniform(-10, LH * 0.3)
        sp = rng.uniform(190, 270)
        self.shooting.append(dict(x=x, y=y, dx=math.cos(ang), dy=math.sin(ang), sp=sp,
                                  age=0.0, life=rng.uniform(0.8, 1.3), length=rng.randint(14, 26)))

    def _spawn_wave(self, power=None, speed=None):
        rng = self.rng
        # Before the sun is revealed, waves enter already expanded from off-screen
        self.waves.append(dict(r=SUN_R if self.show_sun else 100.0,
                               speed=speed or rng.uniform(55, 85),
                               seed=rng.uniform(0, 10), k=rng.choice((10, 12, 14)),
                               amp=rng.uniform(1.5, 3.0), power=power or rng.uniform(0.7, 1.0)))

    def _spawn_spark(self, fast=False):
        rng = self.rng
        a = rng.uniform(math.radians(150), math.radians(295))
        sp = rng.uniform(60, 140) if fast else rng.uniform(15, 45)
        self.sparks.append(dict(x=SUN_C[0] + math.cos(a) * SUN_R, y=SUN_C[1] + math.sin(a) * SUN_R,
                                vx=math.cos(a) * sp, vy=math.sin(a) * sp,
                                age=0.0, life=rng.uniform(0.6, 1.5)))

    def burst(self):
        """Big flare from the sun — used on the title's white flash."""
        self._spawn_wave(power=1.4, speed=120)
        for _ in range(45):
            self._spawn_spark(fast=True)

    # --- Update ---

    def update(self, dt):
        rng = self.rng
        self.t += dt

        for s in self.drifters:
            s[0] -= s[2] * dt
            if s[0] < 0:
                s[0] += LW
                s[1] = rng.randrange(LH)

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._spawn_shooting_star()
            self._shoot_timer = rng.uniform(1.4, 3.6)
        for s in self.shooting:
            s['x'] += s['dx'] * s['sp'] * dt
            s['y'] += s['dy'] * s['sp'] * dt
            s['age'] += dt
        self.shooting = [s for s in self.shooting if s['age'] < s['life']]

        self._wave_timer -= dt
        if self._wave_timer <= 0:
            self._spawn_wave()
            self._wave_timer = rng.uniform(2.2, 4.0)
        for w in self.waves:
            w['r'] += w['speed'] * dt
        self.waves = [w for w in self.waves if w['r'] < WAVE_MAX_R]

        if self.show_sun:
            self._prom_timer -= dt
            if self._prom_timer <= 0 and len(self.proms) < 6:
                self.proms.append(dict(ang=rng.uniform(math.radians(150), math.radians(292)),
                                       w=rng.uniform(0.08, 0.2), h=rng.uniform(8, 22),
                                       age=0.0, life=rng.uniform(1.6, 3.2)))
                self._prom_timer = rng.uniform(0.5, 1.2)
            self._spark_acc += dt * 14
            while self._spark_acc >= 1:
                self._spark_acc -= 1
                self._spawn_spark()
        for p in self.proms:
            p['age'] += dt
        self.proms = [p for p in self.proms if p['age'] < p['life']]
        for s in self.sparks:
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            s['age'] += dt
        self.sparks = [s for s in self.sparks if s['age'] < s['life']]

    # --- Draw ---

    def _draw_stars(self, low):
        t = self.t
        for x, y, _, b in self.drifters:
            low.set_at((int(x), y), (b, b, min(255, b + 30)))
        for s in self.twinkles:
            k = s['b'] * (0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * s['sp'] + s['ph'])))
            col = _scale_col(s['col'], k)
            x, y = s['x'], s['y']
            low.set_at((x, y), col)
            if s['big'] and k > 0.7:
                arm = _scale_col(col, 0.45)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    low.set_at((x + dx, y + dy), arm)

    def _draw_waves(self, glow):
        t = self.t
        cx, cy = SUN_C
        layers = ((30, (40, 10, 34)), (16, (86, 36, 14)), (6, (156, 84, 28)), (2, (210, 150, 70)))
        for w in self.waves:
            fade = w['power'] * (1 - w['r'] / WAVE_MAX_R) ** 0.8 * _clamp01(w['r'] / 30)
            if fade <= 0.02:
                continue
            radii = [w['r'] + w['amp'] * math.sin(a * w['k'] + t * 3 + w['seed'])
                     + 1.5 * math.sin(a * 23 - t * 5) for a in WAVE_ANGLES]
            for thick, col in layers:
                outer = [(cx + math.cos(a) * (r + thick / 2), cy + math.sin(a) * (r + thick / 2))
                         for a, r in zip(WAVE_ANGLES, radii)]
                inner = [(cx + math.cos(a) * max(0, r - thick / 2), cy + math.sin(a) * max(0, r - thick / 2))
                         for a, r in zip(WAVE_ANGLES, radii)]
                pygame.draw.polygon(glow, _scale_col(col, fade), outer + inner[::-1])

    def _draw_shooting(self, glow):
        for s in self.shooting:
            fade = _clamp01(s['age'] / 0.1) * (1 - s['age'] / s['life']) ** 0.5
            L = s['length']
            for k in range(L):
                fall = (1 - k / L) ** 1.5
                glow.set_at((int(s['x'] - s['dx'] * k), int(s['y'] - s['dy'] * k)),
                            _scale_col((220, 210, 255), fall * fade))
            hx, hy = int(s['x']), int(s['y'])
            head = _scale_col((255, 255, 255), fade)
            pygame.draw.rect(glow, head, (hx, hy, 2, 2))

    def _draw_corona(self, glow):
        t = self.t
        cx, cy = SUN_C
        for j in range(14):
            a = j * math.tau / 14 + t * 0.05
            length = 18 + 10 * math.sin(t * 1.3 + j * 1.7)
            r0, r1 = SUN_R + 2, SUN_R + 2 + length
            pygame.draw.line(glow, (60, 26, 8), (cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                             (cx + math.cos(a) * r1, cy + math.sin(a) * r1), 2)
        pulse = 0.5 + 0.5 * math.sin(t * 1.7)
        for i, (extra, col) in enumerate(((34, (30, 8, 10)), (24, (54, 18, 8)), (14, (94, 38, 10)), (6, (146, 66, 18)))):
            pygame.draw.circle(glow, col, SUN_C, int(SUN_R + extra + pulse * 3 * (1 - i / 4)))

    def _draw_flares(self, glow):
        cx, cy = SUN_C
        for p in self.proms:
            k = math.sin(math.pi * p['age'] / p['life'])
            h = p['h'] * k
            pts = []
            for i in range(17):
                s = i / 16
                a = p['ang'] - p['w'] + 2 * p['w'] * s
                rr = SUN_R - 1 + h * math.sin(math.pi * s)
                pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
            outer = _scale_col((130, 44, 16), k)
            for x, y in pts:
                pygame.draw.circle(glow, outer, (int(x), int(y)), 2)
            pygame.draw.lines(glow, _scale_col((255, 160, 70), k), False, pts, 1)
        for s in self.sparks:
            k = 1 - s['age'] / s['life']
            glow.set_at((int(s['x']), int(s['y'])), _scale_col((255, 176, 80), k))

    def render(self, logo=None, logo_y=LOGO_Y):
        low, glow = self.low, self.glow
        low.blit(self.sky, (0, 0))
        self._draw_stars(low)

        glow.fill((0, 0, 0))
        self._draw_waves(glow)
        self._draw_shooting(glow)
        if self.show_sun:
            self._draw_corona(glow)
        low.blit(glow, (0, 0), special_flags=ADD)

        if self.show_sun:
            frame = self.sun_frames[int(self.t / 0.15) % len(self.sun_frames)]
            low.blit(frame, (SUN_C[0] - SUN_R - 1, SUN_C[1] - SUN_R - 1))
            glow.fill((0, 0, 0))
            self._draw_flares(glow)
            low.blit(glow, (0, 0), special_flags=ADD)

        if logo:
            logo.draw(low, logo_y)
        return low

    def draw(self, screen, logo=None, logo_y=LOGO_Y):
        pygame.transform.scale(self.render(logo, logo_y), screen.get_size(), screen)


# --- Launch sequence ---

class LaunchIntro:
    SPLASH_IN = (0.6, 2.0)
    SPLASH_OUT = (3.8, 5.0)
    SPACE_START = 5.6
    SPACE_FADE = 1.5
    SPACE_HOLD = 5.0
    FLASH_DUR = 1.4
    SKIP_DELAY = 0.4

    def __init__(self, game):
        self.game = game
        self.backdrop = game.title_screen.backdrop
        self.logo = game.title_screen.logo
        self.backdrop.show_sun = False
        self.t = 0.0
        self.flashed = False
        self.done = False

        self.name_surf = pygame.font.Font(config.FONT_PATH_B, 36).render("JoshThatKing", False, (240, 236, 255))
        self.est_surf = pygame.font.Font(config.FONT_PATH_B, 18).render("EST. 2025", False, (150, 135, 190))
        self.prompt_surf = game.fonts['BATTLE'].render("Press J", False, (235, 220, 255))
        self.prompt_shadow = game.fonts['BATTLE'].render("Press J", False, (20, 8, 40))
        self._black = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._black.fill((0, 0, 0))
        self._white = pygame.Surface((config.WIDTH, config.HEIGHT))
        self._white.fill((255, 255, 255))

    @property
    def flash_at(self):
        return self.SPACE_START + self.SPACE_HOLD

    def update(self, dt):
        dt = min(dt, 1 / 20)   # first frame after loading can be huge
        self.t += dt
        if self.t >= self.SPACE_START:
            self.backdrop.update(dt)
        if not self.flashed and self.t >= self.flash_at:
            self.flashed = True
            self.backdrop.show_sun = True
            self.backdrop.burst()
        if self.flashed:
            self.logo.update(dt)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or event.key not in (pygame.K_j, pygame.K_RETURN, pygame.K_SPACE):
            return
        if self.flashed and self.t >= self.flash_at + self.SKIP_DELAY:
            self.done = True

    def _draw_splash(self, screen):
        screen.fill((0, 0, 0))
        t = self.t
        vis = _clamp01((t - self.SPLASH_IN[0]) / (self.SPLASH_IN[1] - self.SPLASH_IN[0]))
        vis *= 1 - _clamp01((t - self.SPLASH_OUT[0]) / (self.SPLASH_OUT[1] - self.SPLASH_OUT[0]))
        if vis <= 0:
            return
        W, H = screen.get_size()
        name, est = self.name_surf, self.est_surf
        ny = H // 2 - name.get_height() // 2 - 14
        screen.blit(name, (W // 2 - name.get_width() // 2, ny))
        ly = ny + name.get_height() + 6
        pygame.draw.line(screen, (90, 60, 140), (W // 2 - 70, ly), (W // 2 + 70, ly), 2)
        screen.blit(est, (W // 2 - est.get_width() // 2, ly + 8))
        self._black.set_alpha(int(255 * (1 - vis)))
        screen.blit(self._black, (0, 0))

    def draw(self, screen):
        if self.t < self.SPACE_START:
            self._draw_splash(screen)
            return

        self.backdrop.draw(screen, self.logo if self.flashed else None)
        if not self.flashed:
            fade = 1 - _clamp01((self.t - self.SPACE_START) / self.SPACE_FADE)
            if fade > 0:
                self._black.set_alpha(int(255 * fade))
                screen.blit(self._black, (0, 0))
            return

        ft = self.t - self.flash_at
        if ft > self.SKIP_DELAY + 0.6 and math.sin(ft * 4.0) > -0.3:
            W = screen.get_width()
            x = W // 2 - self.prompt_surf.get_width() // 2
            y = 300
            screen.blit(self.prompt_shadow, (x + 2, y + 2))
            screen.blit(self.prompt_surf, (x, y))
        if ft < self.FLASH_DUR:
            self._white.set_alpha(int(255 * (1 - ft / self.FLASH_DUR) ** 1.5))
            screen.blit(self._white, (0, 0))

"""Battle move animations.

Every move in MOVE_DATA has its own ~1 second hit animation, drawn procedurally
with pygame shapes (no image assets). Moves with base power >= STRONG_POWER get
higher-quality, multi-phase animations (charge-up, travel, impact, screen flash
and shake).

Usage (see Game.play_move_anim in game.py):
    anim = MoveAnimation('Fireball', target_pos, source_pos, scale)
    anim.update(dt)          # every frame
    anim.draw(screen)        # after the battle scene is drawn
    if anim.done: ...

Each animation is a function f(a) where `a` is a _Frame: a.t is overall progress
0..1, (a.tx, a.ty) is the target's center, (a.sx, a.sy) the attacker's center,
a.s a size multiplier, plus drawing helpers (circle, glow, burst, bolt, slash...).
"""
import math
import random
import pygame
import config
from data import MOVE_DATA

DURATION = 1.0
DURATIONS = {'Ultra Violet': 2.2}   # signature moves that run longer than DURATION
STRONG_POWER = 70
TAU = math.pi * 2

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Type palettes: (main, light, dark)
AQUA      = ((50, 130, 245), (150, 210, 255), (20, 60, 150))
MAGMA     = ((255, 110, 30), (255, 210, 80), (170, 35, 10))
EARTH     = ((70, 170, 60), (140, 220, 90), (110, 75, 40))
FLYING    = ((200, 230, 255), (255, 255, 255), (120, 160, 210))
SPIKE     = ((200, 200, 215), (255, 255, 255), (110, 110, 130))
ROCK      = ((150, 115, 80), (215, 185, 130), (90, 65, 45))
LIGHTNING = ((255, 235, 70), (255, 255, 200), (120, 170, 255))
DARK      = ((120, 50, 170), (200, 110, 255), (35, 10, 55))
LIGHT     = ((255, 250, 190), (255, 255, 255), (255, 210, 90))
ICE       = ((150, 220, 255), (235, 250, 255), (70, 150, 220))
ANCIENT   = ((215, 160, 60), (255, 225, 140), (120, 70, 30))
POISON    = ((150, 60, 190), (170, 230, 90), (70, 20, 90))

TYPE_PALETTES = {
    'aqua': AQUA, 'magma': MAGMA, 'earth': EARTH, 'flying': FLYING,
    'spike': SPIKE, 'rock': ROCK, 'lightning': LIGHTNING, 'dark': DARK,
    'light': LIGHT, 'ice': ICE, 'ancient': ANCIENT,
}
RAINBOW = [(255, 80, 80), (255, 170, 60), (255, 240, 80), (90, 230, 110),
           (80, 180, 255), (140, 110, 255), (220, 110, 255)]


# ─────────────────────────────────────────────────────────────────────────────
# Easing / timing helpers
# ─────────────────────────────────────────────────────────────────────────────

def seg(t, a, b):
    """Local progress of t inside [a, b] as 0..1, or None when outside."""
    if t < a or t > b:
        return None
    return (t - a) / (b - a) if b > a else 1.0


def lerp(a, b, p):
    return a + (b - a) * p


def ease_out(p):
    return 1 - (1 - p) * (1 - p)


def ease_in(p):
    return p * p


def hump(p):
    """0 -> 1 -> 0 over p in 0..1."""
    return math.sin(math.pi * max(0.0, min(1.0, p)))


def fade_late(p, start=0.6):
    """Full alpha until `start`, then fades to 0 at p=1."""
    return 1.0 if p < start else max(0.0, (1 - p) / (1 - start))


def _rgba(col, alpha):
    return (col[0], col[1], col[2], max(0, min(255, int(alpha))))


def _mix(c1, c2, p):
    return tuple(int(lerp(c1[i], c2[i], p)) for i in range(3))


_GLOW_CACHE = {}


def _glow_sprite(r, col):
    key = (r, col)
    spr = _GLOW_CACHE.get(key)
    if spr is None:
        if len(_GLOW_CACHE) > 600:
            _GLOW_CACHE.clear()
        spr = pygame.Surface((r * 2 + 2, r * 2 + 2))
        spr.fill(BLACK)
        steps = max(3, min(10, r // 3))
        for i in range(steps):
            f = (i + 1) / steps
            rr = max(1, int(r * (1 - i / steps)))
            pygame.draw.circle(spr, tuple(int(v * f * f) for v in col), (r + 1, r + 1), rr)
        _GLOW_CACHE[key] = spr
    return spr


# ─────────────────────────────────────────────────────────────────────────────
# Per-frame drawing context
# ─────────────────────────────────────────────────────────────────────────────

class _Frame:
    def __init__(self, anim, t):
        self.t = t
        self.tx, self.ty = anim.target
        self.sx, self.sy = anim.source
        self.s = anim.scale
        self.W, self.H = anim.size
        self._anim = anim
        self._layer = anim.layer
        self._glow = anim.glow

    # -- randomness: stable per animation + key, so particles don't jitter --
    def rng(self, key=0):
        return random.Random(self._anim.seed * 7919 + hash(key))

    # -- screen-level effects --
    def tint(self, col, alpha):
        if alpha > 0 and (self._anim.tint is None or alpha > self._anim.tint[1]):
            self._anim.tint = (col, int(min(255, alpha)))

    def shake(self, px):
        self._anim.shake_px = max(self._anim.shake_px, int(px))

    # -- primitives --
    def circle(self, x, y, r, col, alpha=255, width=0):
        r = int(r)
        if r < 1 or alpha <= 0:
            return
        width = int(width)
        if width >= r:
            width = 0
        pygame.draw.circle(self._layer, _rgba(col, alpha), (int(x), int(y)), r, width)

    def ring(self, x, y, r, col, alpha=255, width=3):
        self.circle(x, y, r, col, alpha, max(1, width))

    def line(self, x1, y1, x2, y2, col, alpha=255, width=2):
        if alpha <= 0:
            return
        pygame.draw.line(self._layer, _rgba(col, alpha), (int(x1), int(y1)), (int(x2), int(y2)),
                         max(1, int(width)))

    def lines(self, pts, col, alpha=255, width=2, closed=False):
        if alpha <= 0 or len(pts) < 2:
            return
        pygame.draw.lines(self._layer, _rgba(col, alpha), closed,
                          [(int(x), int(y)) for x, y in pts], max(1, int(width)))

    def poly(self, pts, col, alpha=255, width=0):
        if alpha <= 0 or len(pts) < 3:
            return
        pygame.draw.polygon(self._layer, _rgba(col, alpha), [(int(x), int(y)) for x, y in pts], int(width))

    def ellipse(self, x, y, w, h, col, alpha=255, width=0):
        if alpha <= 0 or w < 2 or h < 2:
            return
        rect = pygame.Rect(0, 0, int(w), int(h))
        rect.center = (int(x), int(y))
        width = int(width)
        if width * 2 >= min(rect.w, rect.h):
            width = 0
        pygame.draw.ellipse(self._layer, _rgba(col, alpha), rect, width)

    def glow(self, x, y, r, col, k=1.0):
        """Additive soft light blob."""
        if k <= 0.03 or r < 2:
            return
        r = max(2, int(r) // 2 * 2)
        c = tuple(min(255, int(v * k)) // 8 * 8 for v in col)
        if not any(c):
            return
        self._glow.blit(_glow_sprite(r, c), (int(x) - r - 1, int(y) - r - 1),
                        special_flags=pygame.BLEND_RGB_ADD)

    # -- shapes --
    def star(self, x, y, r, col, alpha=255, points=4, rot=0.0, inner=0.3):
        pts = []
        for i in range(points * 2):
            rr = r if i % 2 == 0 else r * inner
            ang = rot + i * math.pi / points
            pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
        self.poly(pts, col, alpha)

    def shard(self, x, y, size, ang, col, alpha=255, thin=0.35):
        """Long thin triangle pointing along ang."""
        ca, sa = math.cos(ang), math.sin(ang)
        nx, ny = -sa, ca
        self.poly([(x + ca * size, y + sa * size),
                   (x - ca * size * 0.5 + nx * size * thin, y - sa * size * 0.5 + ny * size * thin),
                   (x - ca * size * 0.5 - nx * size * thin, y - sa * size * 0.5 - ny * size * thin)],
                  col, alpha)

    def leaf(self, x, y, size, ang, col, alpha=255):
        ca, sa = math.cos(ang), math.sin(ang)
        pts = []
        for i in range(9):
            u = i / 8
            along = (u - 0.5) * size * 2
            w = math.sin(math.pi * u) * size * 0.45
            pts.append((x + ca * along - sa * w, y + sa * along + ca * w))
        for i in range(7, 0, -1):
            u = i / 8
            along = (u - 0.5) * size * 2
            w = -math.sin(math.pi * u) * size * 0.45
            pts.append((x + ca * along - sa * w, y + sa * along + ca * w))
        self.poly(pts, col, alpha)

    def flame(self, x, y, size, col, alpha=255, lean=0.0):
        """Teardrop flame pointing up."""
        self.circle(x, y, size * 0.55, col, alpha)
        self.poly([(x - size * 0.53, y - size * 0.1), (x + lean * size, y - size * 1.4),
                   (x + size * 0.53, y - size * 0.1)], col, alpha)

    def bolt(self, x1, y1, x2, y2, col=LIGHTNING[0], width=3, jag=14, segs=8, glow=0.8, rng=None):
        """Jagged lightning bolt. Uses fresh randomness per frame so it flickers."""
        rng = rng or random
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        pts = [(x1, y1)]
        for i in range(1, segs):
            f = i / segs
            off = rng.uniform(-jag, jag)
            pts.append((x1 + dx * f + nx * off, y1 + dy * f + ny * off))
        pts.append((x2, y2))
        self.lines(pts, col, 255, width + 2)
        self.lines(pts, WHITE, 255, max(1, width - 1))
        if glow:
            for px, py in pts[::2]:
                self.glow(px, py, 10 + width * 4, col, glow)
        return pts

    def slash(self, x, y, ang, length, p, col, width=8, alpha=255, curve=0.18, glow=0.6):
        """Crescent slash centered on (x, y). Draws in over p 0..0.45, then fades."""
        if p is None:
            return
        draw = min(1.0, p / 0.45)
        a = alpha * (1.0 if p < 0.45 else max(0.0, (1 - p) / 0.55))
        ca, sa = math.cos(ang), math.sin(ang)
        nx, ny = -sa, ca
        top, bot = [], []
        steps = 16
        for i in range(steps + 1):
            u = i / steps * draw
            along = (u - 0.5) * length
            bend = curve * length * (1 - (2 * u - 1) ** 2)
            w = width * math.sin(math.pi * u) + 0.5
            cx, cy = x + ca * along + nx * bend, y + sa * along + ny * bend
            top.append((cx + nx * w / 2, cy + ny * w / 2))
            bot.append((cx - nx * w / 2, cy - ny * w / 2))
        self.poly(top + bot[::-1], col, a)
        if glow:
            for px, py in top[::4]:
                self.glow(px, py, width * 2.2, col, glow * a / 255)

    # -- particle systems --
    def burst(self, x, y, p, n, dist, col, size=4, alpha=255, gravity=0.0, spread=None,
              glow=0.0, shape='circle', key=0, shrink=True):
        """n particles flying outward from (x, y) as p goes 0..1."""
        if p is None:
            return
        rng = self.rng(('burst', n, int(dist), key))
        lo, hi = spread if spread else (0.0, TAU)
        a = alpha * (1 - p)
        e = ease_out(p)
        for _ in range(n):
            ang = rng.uniform(lo, hi)
            sp = rng.uniform(0.35, 1.0)
            sz = size * rng.uniform(0.6, 1.25)
            d = dist * sp * e
            px = x + math.cos(ang) * d
            py = y + math.sin(ang) * d + gravity * p * p
            r = sz * (1 - 0.55 * p) if shrink else sz
            if shape == 'square':
                self.poly([(px - r, py - r), (px + r, py - r), (px + r, py + r), (px - r, py + r)], col, a)
            elif shape == 'shard':
                self.shard(px, py, r * 2, ang, col, a)
            elif shape == 'streak':
                self.line(px, py, px - math.cos(ang) * r * 3, py - math.sin(ang) * r * 3, col, a, max(1, r / 2))
            elif shape == 'star':
                self.star(px, py, r * 1.6, col, a, rot=p * 3)
            else:
                self.circle(px, py, r, col, a)
            if glow:
                self.glow(px, py, r * 3.5, col, glow * (1 - p))

    def implode(self, x, y, p, n, dist, col, size=3, alpha=255, glow=0.0, key=0, swirl=0.0):
        """n particles converging into (x, y)."""
        if p is None:
            return
        rng = self.rng(('implode', n, int(dist), key))
        e = ease_in(p)
        for _ in range(n):
            ang = rng.uniform(0, TAU) + swirl * p
            d = dist * rng.uniform(0.6, 1.0) * (1 - e)
            px, py = x + math.cos(ang) * d, y + math.sin(ang) * d
            self.circle(px, py, size * (0.5 + 0.5 * (1 - p)), col, alpha * hump(min(1, p * 1.3)))
            if glow:
                self.glow(px, py, size * 3, col, glow)

    def rain(self, p, n, col, x0, x1, y_top, y_bot, length=12, width=2, alpha=220, slant=0.0,
             key=0, speed=1.0, shape='line'):
        """Falling particles between x0..x1 from y_top to y_bot; each drop has a start delay."""
        if p is None:
            return
        rng = self.rng(('rain', n, key))
        for _ in range(n):
            x = rng.uniform(x0, x1)
            delay = rng.uniform(0, 0.6)
            q = (p - delay) * speed / (1 - 0.6 + 1e-6)
            if q < 0 or q > 1:
                continue
            y = lerp(y_top, y_bot, q)
            xx = x + slant * (y - y_top)
            if shape == 'line':
                self.line(xx, y, xx - slant * length, y - length, col, alpha, width)
            elif shape == 'flake':
                self.star(xx, y, length * 0.5, col, alpha, points=3, rot=q * 4, inner=0.25)
            elif shape == 'shard':
                self.shard(xx, y, length, math.pi / 2 + math.atan(slant), col, alpha)
            else:
                self.circle(xx, y, width, col, alpha)

    # -- path helper --
    def travel(self, p, arc=0.0):
        """Point along source -> target at progress p, optionally arcing upward."""
        return (lerp(self.sx, self.tx, p),
                lerp(self.sy, self.ty, p) - arc * math.sin(math.pi * p))

    def angle_to_target(self):
        return math.atan2(self.ty - self.sy, self.tx - self.sx)


# ─────────────────────────────────────────────────────────────────────────────
# Shared building blocks
# ─────────────────────────────────────────────────────────────────────────────

def _impact(a, p, pal, size=1.0, n=10, key=0):
    """Small generic impact: flash core + ring + sparks."""
    if p is None:
        return
    s = a.s * size
    a.glow(a.tx, a.ty, 50 * s * (1 - p * 0.5), pal[1], 1.2 * (1 - p))
    a.ring(a.tx, a.ty, 10 * s + 45 * s * ease_out(p), pal[0], 220 * (1 - p), 3)
    a.burst(a.tx, a.ty, p, n, 55 * s, pal[1], 3 * s, key=key)


def _projectile(a, p, pal, radius=10, arc=0.0, trail=5, glow=1.0):
    if p is None:
        return None
    for i in range(trail, -1, -1):
        q = max(0.0, p - i * 0.04)
        x, y = a.travel(q, arc)
        r = radius * a.s * (1 - i / (trail + 2))
        a.circle(x, y, r, pal[0] if i else pal[1], 200 * (1 - i / (trail + 1)))
    x, y = a.travel(p, arc)
    a.glow(x, y, radius * a.s * 3, pal[0], glow)
    return x, y


def _beam(a, p, col, width, core=WHITE, glow=0.8):
    """Straight beam from source to target that extends then thins out."""
    if p is None:
        return
    reach = min(1.0, p / 0.35)
    w = width * (1.0 if p < 0.6 else max(0.0, (1 - p) / 0.4))
    x2, y2 = a.travel(reach)
    a.line(a.sx, a.sy, x2, y2, col, 230, w)
    a.line(a.sx, a.sy, x2, y2, core, 255, max(1, w * 0.35))
    for i in range(6):
        gx, gy = a.travel(reach * i / 5)
        a.glow(gx, gy, w * 2.5, col, glow * (w / max(1, width)))


def _strong_finish(a, p, pal, flash_alpha=150, shake=8):
    """Screen flash + shake that peaks on impact and decays."""
    if p is None:
        return
    a.tint(pal[1], flash_alpha * (1 - p) ** 2)
    if p < 0.6:
        a.shake(shake * (1 - p / 0.6))


# ─────────────────────────────────────────────────────────────────────────────
# AQUA
# ─────────────────────────────────────────────────────────────────────────────

def _whirlpool_core(a, arms, extra):
    t = a.t
    rot = t * TAU * 2.2
    R = 70 * a.s * (1 - 0.65 * ease_in(t))
    al = 255 * fade_late(t, 0.7)
    for arm in range(arms):
        for i in range(14):
            u = i / 13
            ang = rot + arm * TAU / arms + u * 3.0
            r = R * (1 - u * 0.85)
            x, y = a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r * 0.55
            col = AQUA[1] if (i + arm) % 3 == 0 else AQUA[0]
            a.circle(x, y, (2 + 4 * (1 - u)) * a.s, col, al)
    a.glow(a.tx, a.ty, 40 * a.s, AQUA[0], 0.6 * hump(t))
    if extra:
        p = seg(t, 0.7, 1.0)
        if p is not None:
            a.ring(a.tx, a.ty, 15 * a.s + 60 * a.s * ease_out(p), AQUA[1], 220 * (1 - p), 4)
        a.burst(a.tx, a.ty - 5, p, 16, 70 * a.s, AQUA[1], 4 * a.s, gravity=50, spread=(math.pi, TAU))


def anim_whirlpool(a):
    _whirlpool_core(a, 2, False)


def anim_whirlpool_plus(a):
    _whirlpool_core(a, 3, True)


def anim_hurricane(a):
    t = a.t
    al = 230 * fade_late(t, 0.65)
    rot = t * TAU * 3
    for k in range(6):  # funnel of rotating ellipses
        y = a.ty + 55 * a.s - k * 22 * a.s
        w = (30 + k * 18) * a.s * (0.6 + 0.4 * ease_out(min(1, t * 3)))
        a.ellipse(a.tx + math.sin(rot + k) * 6, y, w * 2, w * 0.5, FLYING[2], al * 0.8, 2)
        a.circle(a.tx + math.cos(rot + k * 1.3) * w, y + math.sin(rot + k * 1.3) * w * 0.25,
                 3 * a.s, AQUA[1], al)
    a.rain(t, 40, AQUA[0], a.tx - 110 * a.s, a.tx + 110 * a.s, a.ty - 120 * a.s, a.ty + 70 * a.s,
           length=14, slant=0.35, key=1, speed=1.4)


def anim_eternal_blue(a):
    t = a.t
    # 1. Charge: deep blue orb forms at attacker
    p = seg(t, 0.0, 0.3)
    if p is not None:
        a.implode(a.sx, a.sy, p, 24, 90 * a.s, AQUA[1], 3, glow=0.4, swirl=2)
        a.circle(a.sx, a.sy, 22 * ease_out(p), AQUA[2], 230)
        a.glow(a.sx, a.sy, 50 * p, AQUA[0], 1.2)
        a.tint(AQUA[2], 70 * p)
    # 2. Tidal surge: rolling wave crest sweeps to target
    p = seg(t, 0.25, 0.55)
    if p is not None:
        x, y = a.travel(ease_in(p), arc=40)
        for i in range(10):
            off = (i - 4.5) * 9
            ang = a.angle_to_target() + math.pi / 2
            a.circle(x + math.cos(ang) * off * 2, y + math.sin(ang) * off * 2,
                     (16 - abs(i - 4.5) * 2) * a.s, AQUA[0] if i % 2 else AQUA[1], 230)
        a.glow(x, y, 70, AQUA[0], 1.0)
        a.tint(AQUA[2], 70)
    # 3. Impact: water pillars erupt, rings, rain of droplets
    p = seg(t, 0.5, 1.0)
    if p is not None:
        for k in range(7):
            ox = (k - 3) * 22 * a.s
            h = 120 * a.s * hump(min(1, p * 1.6 - abs(k - 3) * 0.06))
            w = (14 - abs(k - 3) * 2) * a.s
            if h > 2:
                a.ellipse(a.tx + ox, a.ty + 40 * a.s - h / 2, w * 2, h, AQUA[0], 210)
                a.ellipse(a.tx + ox, a.ty + 40 * a.s - h / 2, w, h * 0.9, AQUA[1], 200)
        for k in range(3):
            q = seg(p, k * 0.15, 0.6 + k * 0.15)
            if q is not None:
                a.ring(a.tx, a.ty, 20 * a.s + 120 * a.s * ease_out(q), AQUA[1], 230 * (1 - q), 5 - k)
        a.burst(a.tx, a.ty - 30, p, 40, 140 * a.s, AQUA[1], 5 * a.s, gravity=160, glow=0.4)
        a.glow(a.tx, a.ty, 120 * a.s, AQUA[0], 1.4 * (1 - p))
        _strong_finish(a, p, AQUA, 160, 10)


def anim_wave_dash(a):
    t = a.t
    d = 1 if a.tx >= a.sx else -1
    x = a.tx + d * lerp(-120, 120, ease_in(t)) * a.s
    al = 240 * hump(t)
    for i in range(12):  # curling crest
        u = i / 11
        a.circle(x - d * u * 50 * a.s, a.ty + 45 * a.s - math.sin(u * math.pi) * 60 * a.s * (1 - u * 0.4),
                 (10 - u * 6) * a.s, AQUA[1] if i < 3 else AQUA[0], al)
    for i in range(6):  # speed lines
        yy = a.ty - 50 * a.s + i * 20 * a.s
        a.line(x - d * 40 * a.s, yy, x - d * 120 * a.s, yy, AQUA[1], al * 0.6, 2)
    _impact(a, seg(t, 0.45, 0.95), AQUA, 0.8)


# ─────────────────────────────────────────────────────────────────────────────
# MAGMA
# ─────────────────────────────────────────────────────────────────────────────

def _fireball(a, radius, embers, boom):
    t = a.t
    p = seg(t, 0.0, 0.45)
    if p is not None:
        pos = _projectile(a, ease_in(p), MAGMA, radius, arc=20, trail=embers)
        a.flame(pos[0], pos[1] + 4, radius * a.s * 1.2, MAGMA[1], 200, lean=-0.3)
    p = seg(t, 0.42, 1.0)
    if p is not None:
        a.circle(a.tx, a.ty, boom * a.s * ease_out(p), MAGMA[0], 220 * (1 - p))
        a.circle(a.tx, a.ty, boom * 0.6 * a.s * ease_out(p), MAGMA[1], 230 * (1 - p))
        a.glow(a.tx, a.ty, boom * 1.6 * a.s, MAGMA[0], 1.3 * (1 - p))
        a.burst(a.tx, a.ty, p, embers * 3, boom * 1.6 * a.s, MAGMA[1], 3 * a.s, gravity=-30, key=embers)


def anim_fireball(a):
    _fireball(a, 9, 4, 35)


def anim_fireball_plus(a):
    _fireball(a, 13, 7, 52)
    p = seg(a.t, 0.42, 1.0)
    if p is not None:
        a.ring(a.tx, a.ty, 70 * a.s * ease_out(p), MAGMA[1], 200 * (1 - p), 3)


def anim_lava_burst(a):
    t = a.t
    base = a.ty + 50 * a.s
    p = seg(t, 0.0, 0.25)
    if p is not None:  # glowing crack in ground
        a.ellipse(a.tx, base, 90 * a.s * p, 14 * a.s * p, MAGMA[2], 230)
        a.glow(a.tx, base, 50 * a.s, MAGMA[0], p)
    p = seg(t, 0.2, 1.0)
    if p is not None:
        a.ellipse(a.tx, base, 90 * a.s, 14 * a.s, MAGMA[2], 230 * (1 - p))
        rng = a.rng('lava')
        for _ in range(14):
            vx = rng.uniform(-90, 90) * a.s
            vy = rng.uniform(-260, -170) * a.s
            r = rng.uniform(5, 10) * a.s
            x = a.tx + vx * p
            y = base + vy * p + 330 * a.s * p * p
            a.circle(x, y, r, MAGMA[0], 240 * fade_late(p, 0.7))
            a.circle(x - r * 0.3, y - r * 0.3, r * 0.5, MAGMA[1], 240 * fade_late(p, 0.7))
            a.glow(x, y, r * 3, MAGMA[0], 0.5 * (1 - p))


def anim_solar_flare(a):
    t = a.t
    sun_x, sun_y = a.tx, max(50, a.ty - 130 * a.s)
    # 1. Sun forms overhead with rotating corona
    p = seg(t, 0.0, 0.55)
    if p is not None:
        r = 30 * a.s * ease_out(min(1, p * 1.6))
        for i in range(12):
            ang = i * TAU / 12 + t * 3
            ln = r * (1.6 + 0.4 * math.sin(t * 30 + i))
            a.line(sun_x + math.cos(ang) * r, sun_y + math.sin(ang) * r,
                   sun_x + math.cos(ang) * ln, sun_y + math.sin(ang) * ln, MAGMA[1], 230, 3)
        a.circle(sun_x, sun_y, r, MAGMA[0], 255)
        a.circle(sun_x, sun_y, r * 0.7, MAGMA[1], 255)
        a.glow(sun_x, sun_y, r * 3, MAGMA[0], 1.4)
        a.implode(sun_x, sun_y, p, 20, 120 * a.s, MAGMA[1], 3, glow=0.3, key=2)
        a.tint((255, 140, 40), 60 * p)
    # 2. Flare column slams down onto the target
    p = seg(t, 0.45, 0.75)
    if p is not None:
        w = 40 * a.s * hump(p)
        a.poly([(sun_x - w * 0.5, sun_y), (sun_x + w * 0.5, sun_y),
                (a.tx + w, a.ty + 40 * a.s), (a.tx - w, a.ty + 40 * a.s)], MAGMA[0], 220)
        a.poly([(sun_x - w * 0.2, sun_y), (sun_x + w * 0.2, sun_y),
                (a.tx + w * 0.4, a.ty + 40 * a.s), (a.tx - w * 0.4, a.ty + 40 * a.s)], WHITE, 230)
        for i in range(5):
            a.glow(sun_x, lerp(sun_y, a.ty, i / 4), w * 2.5, MAGMA[0], 1.0)
    # 3. Heat explosion
    p = seg(t, 0.6, 1.0)
    if p is not None:
        a.circle(a.tx, a.ty, 90 * a.s * ease_out(p), MAGMA[0], 200 * (1 - p))
        a.circle(a.tx, a.ty, 55 * a.s * ease_out(p), MAGMA[1], 220 * (1 - p))
        for k in range(3):
            q = seg(p, k * 0.12, 0.7 + k * 0.1)
            if q is not None:
                a.ring(a.tx, a.ty, 30 * a.s + 140 * a.s * ease_out(q), MAGMA[1], 220 * (1 - q), 4)
        a.burst(a.tx, a.ty, p, 36, 160 * a.s, MAGMA[1], 4 * a.s, glow=0.5, gravity=-40)
        a.glow(a.tx, a.ty, 140 * a.s, MAGMA[0], 1.5 * (1 - p))
        _strong_finish(a, p, ((255, 230, 180),) * 2, 200, 10)


def anim_flame_shatter(a):
    t = a.t
    p = seg(t, 0.0, 0.4)
    if p is not None:  # crystal shards converge
        for i in range(8):
            ang = i * TAU / 8
            d = 80 * a.s * (1 - ease_in(p))
            a.shard(a.tx + math.cos(ang) * d, a.ty + math.sin(ang) * d, 14 * a.s, ang + math.pi, MAGMA[0], 240)
        a.glow(a.tx, a.ty, 30 * a.s, MAGMA[0], p)
    p = seg(t, 0.38, 1.0)
    if p is not None:  # shatter outward
        a.burst(a.tx, a.ty, p, 18, 100 * a.s, MAGMA[1], 7 * a.s, shape='shard', glow=0.4)
        a.burst(a.tx, a.ty, p, 10, 70 * a.s, MAGMA[0], 6 * a.s, shape='shard', key=1)
        a.glow(a.tx, a.ty, 60 * a.s, MAGMA[1], 1.2 * (1 - p))


def anim_magma_boost(a):
    t = a.t
    al = fade_late(t, 0.6)
    for k in range(2):
        q = seg(t, k * 0.25, 0.6 + k * 0.25)
        if q is not None:
            a.ellipse(a.tx, a.ty + 50 * a.s, 150 * a.s * ease_out(q), 40 * a.s * ease_out(q),
                      MAGMA[0], 220 * (1 - q), 3)
    rng = a.rng('mb')
    for _ in range(16):
        x = a.tx + rng.uniform(-60, 60) * a.s
        d = rng.uniform(0, 0.5)
        q = (t - d) / 0.5
        if 0 <= q <= 1:
            a.flame(x, a.ty + 50 * a.s - q * 110 * a.s, 7 * a.s * (1 - q * 0.6), MAGMA[1], 230 * al)
    a.glow(a.tx, a.ty, 80 * a.s, MAGMA[0], 0.8 * hump(t))


# ─────────────────────────────────────────────────────────────────────────────
# EARTH
# ─────────────────────────────────────────────────────────────────────────────

def anim_log_roll(a):
    t = a.t
    p = seg(t, 0.0, 0.55)
    if p is not None:
        x, y = a.travel(ease_in(p), arc=30 * abs(math.sin(p * math.pi * 2)))
        r = 18 * a.s
        a.circle(x, y, r, EARTH[2], 255)
        a.ring(x, y, r * 0.65, (160, 115, 70), 255, 2)
        a.ring(x, y, r * 0.3, (160, 115, 70), 255, 2)
        ang = p * 14
        a.line(x, y, x + math.cos(ang) * r, y + math.sin(ang) * r, (70, 45, 25), 255, 2)
    p = seg(t, 0.5, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty + 10, p, 14, 70 * a.s, EARTH[2], 4 * a.s, gravity=80, shape='square')
        a.star(a.tx, a.ty, 30 * a.s * (1 - p), WHITE, 230 * (1 - p), points=5, rot=0.3)


def _vines(a, n, width, leaves):
    t = a.t
    grow = ease_out(min(1, t / 0.6))
    al = 255 * fade_late(t, 0.75)
    squeeze = 1 - 0.25 * hump(seg(t, 0.55, 0.95) or 0)
    for v in range(n):
        y0 = a.ty + (v - (n - 1) / 2) * 22 * a.s * squeeze
        dirn = 1 if v % 2 == 0 else -1
        pts = []
        steps = 18
        for i in range(int(steps * grow) + 1):
            u = i / steps
            x = a.tx + dirn * (u - 0.5) * 150 * a.s
            y = y0 + math.sin(u * 9 + v) * 14 * a.s
            pts.append((x, y))
        a.lines(pts, EARTH[0], al, width)
        a.lines(pts, EARTH[1], al, max(1, width // 3))
        if leaves:
            for px, py in pts[3::4]:
                a.leaf(px, py - 6 * a.s, 7 * a.s, -0.8 * dirn, EARTH[1], al)


def anim_vine_snare(a):
    _vines(a, 2, 5, False)


def anim_vine_snare_plus(a):
    _vines(a, 3, 7, True)
    p = seg(a.t, 0.6, 1.0)
    if p is not None:
        a.ring(a.tx, a.ty, 70 * a.s * (1 - 0.4 * ease_out(p)), EARTH[0], 200 * (1 - p), 4)


def anim_dread_thorn(a):
    t = a.t
    base = a.ty + 45 * a.s
    for i in range(9):
        q = seg(t, i * 0.04, 0.45 + i * 0.04)
        h = (55 + (i % 3) * 20) * a.s * (ease_out(q) if q is not None else (1 if t > 0.45 else 0))
        x = a.tx + (i - 4) * 16 * a.s
        lean = (i - 4) * 0.08
        al = 255 * fade_late(t, 0.7)
        a.poly([(x - 7 * a.s, base), (x + 7 * a.s, base), (x + lean * h, base - h)], (35, 80, 30), al)
        a.poly([(x - 2 * a.s, base), (x + 3 * a.s, base), (x + lean * h, base - h)], (90, 30, 60), al)
    _impact(a, seg(t, 0.4, 0.9), ((90, 140, 60), (200, 120, 200)), 0.8)


def anim_tree_spin(a):
    t = a.t
    # 1. Roots surge and trunk forms under target
    p = seg(t, 0.0, 0.35)
    if p is not None:
        for i in range(6):
            ang = math.pi + i * math.pi / 5
            a.line(a.tx, a.ty + 50 * a.s, a.tx + math.cos(ang) * 80 * a.s * p,
                   a.ty + 50 * a.s + abs(math.sin(ang)) * 12 * a.s * p, EARTH[2], 255, 5)
        a.glow(a.tx, a.ty + 50 * a.s, 60 * a.s, EARTH[0], p)
    # 2. Leaf tornado spirals up around the target
    p = seg(t, 0.2, 0.85)
    if p is not None:
        rng = a.rng('tree')
        spin = t * TAU * 3.5
        for i in range(36):
            h = rng.uniform(0, 1)
            ph = rng.uniform(0, TAU)
            rad = (30 + 60 * h) * a.s * (0.6 + 0.4 * ease_out(min(1, p * 2)))
            ang = spin + ph
            x = a.tx + math.cos(ang) * rad
            y = a.ty + 55 * a.s - h * 140 * a.s * ease_out(p) + math.sin(ang) * 10 * a.s
            front = math.sin(ang) > 0
            a.leaf(x, y, (6 + 4 * front) * a.s, ang * 2, EARTH[1] if front else EARTH[0], 240 if front else 160)
        for k in range(4):  # spinning bark spokes
            ang = spin * 1.5 + k * math.pi / 2
            a.line(a.tx, a.ty, a.tx + math.cos(ang) * 55 * a.s, a.ty + math.sin(ang) * 18 * a.s,
                   EARTH[2], 220 * hump(p), 6)
        a.glow(a.tx, a.ty, 70 * a.s, EARTH[0], 0.8 * hump(p))
        a.shake(3 * hump(p))
    # 3. Burst of leaves and bark
    p = seg(t, 0.72, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 24, 150 * a.s, EARTH[1], 6 * a.s, shape='shard', glow=0.3)
        a.burst(a.tx, a.ty, p, 12, 110 * a.s, EARTH[2], 5 * a.s, shape='square', gravity=90, key=1)
        a.ring(a.tx, a.ty, 30 * a.s + 110 * a.s * ease_out(p), EARTH[1], 220 * (1 - p), 4)
        _strong_finish(a, p, ((170, 255, 150),) * 2, 130, 9)


def anim_poison_ivy(a):
    t = a.t
    rng = a.rng('ivy')
    al = fade_late(t, 0.7)
    for _ in range(10):  # leaves drift down swaying
        x0 = a.tx + rng.uniform(-70, 70) * a.s
        d = rng.uniform(0, 0.35)
        q = max(0.0, min(1.0, (t - d) / 0.6))
        if q > 0:
            x = x0 + math.sin(q * 8 + x0) * 14 * a.s
            a.leaf(x, a.ty - 90 * a.s + q * 130 * a.s, 8 * a.s, math.sin(q * 8) * 0.8, POISON[1], 240 * al)
    for _ in range(12):  # toxic bubbles rise
        x = a.tx + rng.uniform(-50, 50) * a.s
        d = rng.uniform(0.2, 0.6)
        q = (t - d) / 0.4
        if 0 <= q <= 1:
            a.ring(x, a.ty + 40 * a.s - q * 80 * a.s, (3 + q * 5) * a.s, POISON[0], 230 * (1 - q), 2)
    a.glow(a.tx, a.ty, 50 * a.s, POISON[0], 0.6 * hump(t))


def anim_synthesis(a):
    t = a.t
    a.implode(a.tx, a.ty, min(1, t / 0.75), 30, 120 * a.s, EARTH[1], 3 * a.s, glow=0.5, swirl=1.5)
    p = seg(t, 0.55, 1.0)
    if p is not None:
        for i in range(8):
            ang = i * TAU / 8 + p * 2
            r = 45 * a.s * ease_out(p)
            a.leaf(a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r, 9 * a.s, ang, EARTH[0], 240 * (1 - p))
        a.glow(a.tx, a.ty, 70 * a.s, EARTH[1], 1.0 * (1 - p))


def anim_terraform(a):
    t = a.t
    base = a.ty + 50 * a.s
    rng = a.rng('terra')
    for i in range(8):  # cracks spreading outward along the ground
        ang = rng.uniform(0, math.pi) + math.pi
        ln = 110 * a.s * ease_out(min(1, t * 2))
        pts = [(a.tx, base)]
        for k in range(1, 5):
            f = k / 4 * ln
            pts.append((a.tx - math.cos(ang) * f + rng.uniform(-6, 6), base + abs(math.sin(ang)) * f * 0.2))
        a.lines(pts, ROCK[2], 255 * fade_late(t, 0.7), 3)
    for i in range(6):  # rock chunks lift up
        x = a.tx + (i - 2.5) * 30 * a.s
        q = seg(t, 0.2 + i * 0.04, 0.9)
        if q is not None:
            y = base - 70 * a.s * hump(q)
            sz = 8 * a.s
            a.poly([(x - sz, y), (x - sz * 0.4, y - sz), (x + sz, y - sz * 0.6), (x + sz * 0.6, y + sz * 0.5)],
                   ROCK[0], 240)
    a.glow(a.tx, base, 80 * a.s, EARTH[0], 0.6 * hump(t))


def anim_floral_resonance(a):
    t = a.t
    pink = (255, 150, 200)
    p = ease_out(min(1, t / 0.5))
    for i in range(5):  # blooming flower
        ang = i * TAU / 5 + t * 1.5
        r = 28 * a.s * p
        a.ellipse(a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r, 26 * a.s * p, 26 * a.s * p,
                  pink, 220 * fade_late(t, 0.7))
    a.circle(a.tx, a.ty, 12 * a.s * p, (255, 230, 120), 240 * fade_late(t, 0.7))
    for k in range(3):
        q = seg(t, 0.2 + k * 0.2, 0.7 + k * 0.1)
        if q is not None:
            a.ring(a.tx, a.ty, 30 * a.s + 70 * a.s * q, EARTH[1], 200 * (1 - q), 3)
    a.burst(a.tx, a.ty, seg(t, 0.3, 1.0), 14, 90 * a.s, WHITE, 3 * a.s, shape='star', glow=0.4, gravity=-40)
    a.glow(a.tx, a.ty, 70 * a.s, pink, 0.6 * hump(t))


# ─────────────────────────────────────────────────────────────────────────────
# FLYING
# ─────────────────────────────────────────────────────────────────────────────

def anim_swift_sneak(a):
    t = a.t
    p = seg(t, 0.0, 0.3)
    if p is not None:
        for i in range(4):
            yy = a.ty - 30 * a.s + i * 20 * a.s
            x2 = lerp(a.sx, a.tx, ease_in(p))
            a.line(x2 - (a.tx - a.sx) * 0.25, yy, x2, yy, FLYING[1], 200, 2)
    p = seg(t, 0.28, 0.9)
    if p is not None:
        a.slash(a.tx, a.ty, math.pi / 4, 90 * a.s, p, FLYING[1], 5)
        a.slash(a.tx, a.ty, -math.pi / 4, 90 * a.s, seg(t, 0.36, 1.0), FLYING[1], 5)


def anim_air_strike(a):
    t = a.t
    ang = a.angle_to_target()
    for k in range(3):
        p = seg(t, k * 0.14, 0.5 + k * 0.14)
        if p is not None:
            x, y = a.travel(ease_in(p))
            y += (k - 1) * 20 * a.s
            for i in range(9):  # crescent air blade
                u = i / 8 - 0.5
                bx = x + math.cos(ang + math.pi / 2) * u * 34 * a.s - math.cos(ang) * abs(u) * 18 * a.s
                by = y + math.sin(ang + math.pi / 2) * u * 34 * a.s - math.sin(ang) * abs(u) * 18 * a.s
                a.circle(bx, by, 3 * a.s * (1 - abs(u)), FLYING[1], 230)
    _impact(a, seg(t, 0.6, 1.0), FLYING, 0.8)


def anim_mach_speed(a):
    t = a.t
    rng = a.rng('mach')
    p = seg(t, 0.0, 0.45)
    if p is not None:
        for _ in range(14):
            yy = a.ty + rng.uniform(-70, 70) * a.s
            ln = rng.uniform(40, 120) * a.s
            x = lerp(a.sx, a.tx + 80, ease_in(min(1, p * rng.uniform(1, 1.6))))
            a.line(x, yy, x - ln, yy, FLYING[1], 200 * hump(p), 2)
    p = seg(t, 0.38, 1.0)
    if p is not None:  # sonic boom cone
        for k in range(3):
            q = seg(p, k * 0.12, 0.7 + k * 0.1)
            if q is not None:
                a.ellipse(a.tx, a.ty, 40 * a.s + 140 * a.s * ease_out(q), 20 * a.s + 90 * a.s * ease_out(q),
                          FLYING[1], 220 * (1 - q), 3)
        a.glow(a.tx, a.ty, 60 * a.s, FLYING[0], 1.0 * (1 - p))


def anim_wind_fracture(a):
    t = a.t
    # 1. Winds gather into a pressure point
    p = seg(t, 0.0, 0.4)
    if p is not None:
        rng = a.rng('wf')
        for _ in range(18):
            ang = rng.uniform(0, TAU) + p * 3
            d = 160 * a.s * (1 - ease_in(p)) * rng.uniform(0.6, 1)
            x, y = a.tx + math.cos(ang) * d, a.ty + math.sin(ang) * d
            a.line(x, y, x + math.cos(ang + 0.6) * 25 * a.s, y + math.sin(ang + 0.6) * 25 * a.s,
                   FLYING[1], 220 * p, 2)
        a.glow(a.tx, a.ty, 40 * a.s * p, FLYING[0], 1.0)
        a.tint((40, 60, 90), 80 * p)
    # 2. The air itself cracks like glass
    p = seg(t, 0.35, 0.85)
    if p is not None:
        rng = a.rng('crack')
        grow = ease_out(min(1, p * 2.5))
        for i in range(9):
            ang = i * TAU / 9 + rng.uniform(-0.2, 0.2)
            pts = [(a.tx, a.ty)]
            r = 0
            for k in range(5):
                r += rng.uniform(20, 34) * a.s
                ang += rng.uniform(-0.35, 0.35)
                pts.append((a.tx + math.cos(ang) * r * grow, a.ty + math.sin(ang) * r * grow))
            a.lines(pts, WHITE, 255 * fade_late(p, 0.6), 3)
            a.lines(pts, FLYING[2], 200 * fade_late(p, 0.6), 1)
        a.glow(a.tx, a.ty, 80 * a.s, FLYING[1], 1.3 * (1 - p))
        a.tint((40, 60, 90), 80 * (1 - p))
    # 3. Shatter: shards blown out with a shockwave
    p = seg(t, 0.55, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 28, 170 * a.s, FLYING[1], 8 * a.s, shape='shard', glow=0.3)
        a.burst(a.tx, a.ty, p, 16, 130 * a.s, FLYING[2], 6 * a.s, shape='shard', key=1)
        a.ring(a.tx, a.ty, 40 * a.s + 150 * a.s * ease_out(p), WHITE, 230 * (1 - p), 4)
        _strong_finish(a, p, FLYING, 190, 10)


def anim_turbo_booster(a):
    t = a.t
    base = a.ty + 45 * a.s
    for i in range(3):  # jet flames under the user
        x = a.tx + (i - 1) * 30 * a.s
        fl = 30 * a.s * (0.8 + 0.3 * math.sin(t * 50 + i))
        al = 230 * fade_late(t, 0.75)
        a.poly([(x - 9 * a.s, base), (x + 9 * a.s, base), (x, base + fl)], MAGMA[0], al)
        a.poly([(x - 4 * a.s, base), (x + 4 * a.s, base), (x, base + fl * 0.6)], WHITE, al)
        a.glow(x, base + 10 * a.s, 22 * a.s, MAGMA[0], 0.7 * fade_late(t, 0.75))
    rng = a.rng('turbo')
    for _ in range(12):  # upward speed lines
        x = a.tx + rng.uniform(-70, 70) * a.s
        y = a.ty + 60 * a.s - ((t * rng.uniform(1.5, 2.5) + rng.random()) % 1) * 160 * a.s
        a.line(x, y, x, y + 25 * a.s, FLYING[1], 200 * fade_late(t, 0.75), 2)
    for k in range(2):
        q = seg(t, k * 0.3, 0.6 + k * 0.3)
        if q is not None:
            a.ellipse(a.tx, base - q * 100 * a.s, 110 * a.s, 26 * a.s, WHITE, 200 * (1 - q), 2)


def anim_sky_scorch(a):
    t = a.t
    start = (a.tx + 220 * a.s, a.ty - 260 * a.s)
    # 1. Ignition high in the sky
    p = seg(t, 0.0, 0.2)
    if p is not None:
        a.glow(start[0], max(10, start[1]), 40 * p + 10, MAGMA[1], 1.5)
        a.star(start[0], max(10, start[1]), 20 * p, WHITE, 255, points=4, rot=t * 6)
        a.tint((60, 20, 0), 90 * p)
    # 2. Blazing dive
    p = seg(t, 0.15, 0.5)
    if p is not None:
        q = ease_in(p)
        x, y = lerp(start[0], a.tx, q), lerp(start[1], a.ty, q)
        ang = math.atan2(a.ty - start[1], a.tx - start[0])
        for i in range(14):  # fire trail
            d = i * 9 * a.s
            tx_, ty_ = x - math.cos(ang) * d, y - math.sin(ang) * d
            r = (16 - i) * a.s
            a.circle(tx_, ty_, r, MAGMA[0] if i > 3 else MAGMA[1], 220 - i * 12)
            a.glow(tx_, ty_, r * 2.5, MAGMA[0], 0.6)
        a.circle(x, y, 13 * a.s, WHITE, 255)
        a.glow(x, y, 50 * a.s, MAGMA[1], 1.4)
        a.tint((60, 20, 0), 90)
    # 3. Massive explosion
    p = seg(t, 0.47, 1.0)
    if p is not None:
        e = ease_out(p)
        a.circle(a.tx, a.ty, 110 * a.s * e, MAGMA[2], 200 * (1 - p))
        a.circle(a.tx, a.ty, 80 * a.s * e, MAGMA[0], 220 * (1 - p))
        a.circle(a.tx, a.ty, 45 * a.s * e, MAGMA[1], 240 * (1 - p))
        for k in range(4):
            q = seg(p, k * 0.1, 0.6 + k * 0.1)
            if q is not None:
                a.ring(a.tx, a.ty, 30 * a.s + 190 * a.s * ease_out(q), (255, 230, 180), 230 * (1 - q), 5 - k)
        a.burst(a.tx, a.ty, p, 44, 200 * a.s, MAGMA[1], 5 * a.s, glow=0.5, gravity=60)
        a.burst(a.tx, a.ty, p, 18, 150 * a.s, MAGMA[2], 7 * a.s, shape='square', gravity=140, key=1)
        a.glow(a.tx, a.ty, 160 * a.s, MAGMA[0], 1.6 * (1 - p))
        _strong_finish(a, p, ((255, 240, 210),) * 2, 230, 14)


# ─────────────────────────────────────────────────────────────────────────────
# SPIKE
# ─────────────────────────────────────────────────────────────────────────────

def _jaws(a, p, col, size, teeth, fang=False):
    """Two rows of teeth that snap shut on the target."""
    if p is None:
        return
    close = ease_in(min(1, p / 0.45))
    gap = 70 * a.s * size * (1 - close)
    al = 255 * fade_late(p, 0.7)
    w = 110 * a.s * size
    for row, sgn in ((a.ty - gap, 1), (a.ty + gap, -1)):
        for i in range(teeth):
            x = a.tx - w / 2 + (i + 0.5) * w / teeth
            big = fang and i in (0, teeth - 1)
            h = (34 if big else 20) * a.s * size
            a.poly([(x - w / teeth * 0.45, row - sgn * 6 * a.s), (x + w / teeth * 0.45, row - sgn * 6 * a.s),
                    (x, row + sgn * h)], col, al)
        a.line(a.tx - w / 2, row - sgn * 6 * a.s, a.tx + w / 2, row - sgn * 6 * a.s, (120, 30, 40), al, 4)
    if p >= 0.45:
        a.glow(a.tx, a.ty, 50 * a.s * size, WHITE, 1.2 * (1 - p))


def anim_lock_jaw(a):
    _jaws(a, a.t, SPIKE[1], 0.9, 6)
    p = seg(a.t, 0.45, 1.0)
    if p is not None:  # clamp shudder
        a.shake(3 * (1 - p))
        a.ring(a.tx, a.ty, 60 * a.s * (1 - 0.3 * p), SPIKE[2], 200 * (1 - p), 3)


def anim_horn_tackle(a):
    t = a.t
    p = seg(t, 0.0, 0.45)
    if p is not None:
        x, y = a.travel(ease_in(p))
        ang = a.angle_to_target()
        a.shard(x, y, 26 * a.s, ang, SPIKE[0], 255, thin=0.3)
        a.shard(x, y, 18 * a.s, ang, WHITE, 255, thin=0.15)
    p = seg(t, 0.42, 1.0)
    if p is not None:
        a.star(a.tx, a.ty, 45 * a.s * ease_out(p), WHITE, 240 * (1 - p), points=6, rot=0.2, inner=0.4)
        a.burst(a.tx, a.ty, p, 10, 60 * a.s, SPIKE[1], 3 * a.s, shape='streak')


def anim_double_jab(a):
    for k, off in enumerate((-22, 22)):
        p = seg(a.t, k * 0.3, 0.45 + k * 0.3)
        if p is not None:
            x, y = a.tx + off * a.s, a.ty - off * 0.4 * a.s
            a.star(x, y, 38 * a.s * ease_out(p), WHITE, 255 * (1 - p), points=5, rot=k, inner=0.45)
            a.star(x, y, 22 * a.s * ease_out(p), SPIKE[0], 255 * (1 - p), points=5, rot=k + 0.3, inner=0.5)
            a.glow(x, y, 35 * a.s, WHITE, 1.0 * (1 - p))
            if p < 0.3:
                a.shake(2)


def anim_ripping_impact(a):
    for k in range(3):
        p = seg(a.t, k * 0.1, 0.6 + k * 0.1)
        off = (k - 1) * 22 * a.s
        a.slash(a.tx + off, a.ty, math.pi * 0.35, 120 * a.s, p, (230, 60, 60), 7, curve=0.06)
        a.slash(a.tx + off, a.ty, math.pi * 0.35, 120 * a.s, p, WHITE, 3, curve=0.06, glow=0)
    _impact(a, seg(a.t, 0.45, 1.0), ((230, 60, 60), (255, 200, 200)), 0.9)


def anim_power_fang(a):
    _jaws(a, a.t, WHITE, 1.15, 5, fang=True)
    p = seg(a.t, 0.42, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 14, 90 * a.s, SPIKE[1], 4 * a.s, shape='streak', glow=0.3)
        a.shake(4 * (1 - p))


def anim_sword_slash(a):
    t = a.t
    # 1. Blade gleam
    p = seg(t, 0.0, 0.25)
    if p is not None:
        a.star(a.tx - 40 * a.s, a.ty - 40 * a.s, 26 * a.s * hump(p), WHITE, 255, points=4, rot=p)
        a.glow(a.tx - 40 * a.s, a.ty - 40 * a.s, 40 * a.s, WHITE, hump(p))
        a.tint((10, 10, 30), 90 * p)
    # 2. Two crossing crescent slashes
    p1 = seg(t, 0.2, 0.75)
    p2 = seg(t, 0.38, 0.95)
    a.slash(a.tx, a.ty, math.pi * 0.25, 190 * a.s, p1, (170, 200, 255), 16, curve=0.22, glow=0.9)
    a.slash(a.tx, a.ty, math.pi * 0.25, 190 * a.s, p1, WHITE, 7, curve=0.22, glow=0)
    a.slash(a.tx, a.ty, -math.pi * 0.25, 190 * a.s, p2, (170, 200, 255), 16, curve=-0.22, glow=0.9)
    a.slash(a.tx, a.ty, -math.pi * 0.25, 190 * a.s, p2, WHITE, 7, curve=-0.22, glow=0)
    if p1 is not None:
        a.tint((10, 10, 30), 90 * (1 - p1))
    # 3. Spark burst on the cross
    p = seg(t, 0.5, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 24, 130 * a.s, WHITE, 4 * a.s, shape='streak', glow=0.4)
        a.star(a.tx, a.ty, 60 * a.s * (1 - p), WHITE, 255 * (1 - p), points=4, rot=math.pi / 4, inner=0.15)
        _strong_finish(a, p, SPIKE, 150, 8)


def anim_quick_slash(a):
    p = seg(a.t, 0.05, 0.75)
    a.slash(a.tx, a.ty, -math.pi * 0.15, 150 * a.s, p, SPIKE[1], 5, curve=0.05)
    p = seg(a.t, 0.25, 0.8)
    if p is not None:
        a.burst(a.tx, a.ty, p, 8, 50 * a.s, SPIKE[1], 3 * a.s, shape='streak')


def anim_spike_storm(a):
    t = a.t
    # 1. Spikes gather in the air above
    p = seg(t, 0.0, 0.3)
    if p is not None:
        rng = a.rng('ss_g')
        for _ in range(14):
            x = a.tx + rng.uniform(-110, 110) * a.s
            y = a.ty - 170 * a.s + rng.uniform(-20, 20)
            a.shard(x, y, 14 * a.s * ease_out(p), math.pi / 2, SPIKE[0], 255 * p)
            a.glow(x, y, 12 * a.s, WHITE, 0.4 * p)
        a.tint((20, 20, 35), 100 * p)
    # 2. Rain of spikes, each sparking on impact
    p = seg(t, 0.25, 0.75)
    if p is not None:
        rng = a.rng('ss_r')
        for i in range(22):
            x = a.tx + rng.uniform(-110, 110) * a.s
            d = rng.uniform(0, 0.55)
            q = (p - d) / 0.45
            land = a.ty + rng.uniform(-20, 50) * a.s
            if 0 <= q <= 1:
                y = lerp(a.ty - 170 * a.s, land, ease_in(q))
                a.shard(x, y, 16 * a.s, math.pi / 2, SPIKE[0], 255)
                a.shard(x, y, 10 * a.s, math.pi / 2, WHITE, 255, thin=0.15)
            elif q > 1 and q < 1.5:
                a.star(x, land, 14 * a.s * (1.5 - q) * 2, WHITE, 255 * (1.5 - q) * 2, points=4, rot=i)
        a.tint((20, 20, 35), 100)
        a.shake(3)
    # 3. Final ring of spikes erupts outward
    p = seg(t, 0.65, 1.0)
    if p is not None:
        for i in range(16):
            ang = i * TAU / 16
            r = 20 * a.s + 130 * a.s * ease_out(p)
            a.shard(a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r, 18 * a.s, ang, SPIKE[1], 255 * (1 - p))
        a.ring(a.tx, a.ty, 20 * a.s + 130 * a.s * ease_out(p), SPIKE[0], 200 * (1 - p), 3)
        a.glow(a.tx, a.ty, 90 * a.s, WHITE, 1.3 * (1 - p))
        _strong_finish(a, p, SPIKE, 170, 11)


# ─────────────────────────────────────────────────────────────────────────────
# ROCK
# ─────────────────────────────────────────────────────────────────────────────

def _rock_poly(x, y, r, rot):
    return [(x + math.cos(rot + i * TAU / 7) * r * (0.8 + 0.25 * ((i * 37) % 5) / 4),
             y + math.sin(rot + i * TAU / 7) * r * (0.8 + 0.25 * ((i * 53) % 5) / 4)) for i in range(7)]


def anim_dust_beam(a):
    t = a.t
    p = seg(t, 0.0, 0.85)
    if p is not None:
        rng = a.rng('dust')
        reach = min(1.0, p / 0.4)
        for _ in range(40):
            u = rng.uniform(0, 1) * reach
            x, y = a.travel(u)
            jitter = rng.uniform(-10, 10) * a.s * (1 + u)
            al = 220 * fade_late(p, 0.6)
            a.circle(x, y + jitter, rng.uniform(2, 5) * a.s, ROCK[1] if rng.random() < 0.5 else ROCK[0], al)
    a.burst(a.tx, a.ty, seg(t, 0.4, 1.0), 14, 60 * a.s, ROCK[1], 5 * a.s)


def anim_boulder_smash(a):
    t = a.t
    p = seg(t, 0.0, 0.4)
    if p is not None:
        y = lerp(a.ty - 200 * a.s, a.ty, ease_in(p))
        a.poly(_rock_poly(a.tx, y, 32 * a.s, p * 2), ROCK[0], 255)
        a.poly(_rock_poly(a.tx - 6 * a.s, y - 6 * a.s, 14 * a.s, p * 2), ROCK[1], 255)
    p = seg(t, 0.38, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 12, 90 * a.s, ROCK[0], 7 * a.s, gravity=120, shape='square')
        a.burst(a.tx, a.ty + 20 * a.s, p, 14, 70 * a.s, ROCK[1], 6 * a.s, spread=(math.pi, TAU), key=1)
        if p < 0.3:
            a.shake(4)


def anim_crusher(a):
    t = a.t
    p = seg(t, 0.0, 0.4)
    gap = 90 * a.s * (1 - ease_in(p)) if p is not None else 0
    if t < 0.75:
        al = 255 * fade_late(t / 0.75, 0.7)
        for sgn in (-1, 1):
            x = a.tx + sgn * (gap + 25 * a.s)
            a.poly([(x - 22 * a.s, a.ty - 50 * a.s), (x + 22 * a.s, a.ty - 45 * a.s),
                    (x + 20 * a.s, a.ty + 50 * a.s), (x - 24 * a.s, a.ty + 45 * a.s)], ROCK[0], al)
            a.line(x - 8 * a.s, a.ty - 30 * a.s, x + 6 * a.s, a.ty + 20 * a.s, ROCK[2], al, 2)
    p = seg(t, 0.38, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 18, 80 * a.s, ROCK[1], 6 * a.s, spread=(-math.pi * 0.7, -math.pi * 0.3))
        a.burst(a.tx, a.ty, p, 18, 80 * a.s, ROCK[1], 6 * a.s, spread=(math.pi * 0.3, math.pi * 0.7), key=1)
        if p < 0.3:
            a.shake(5)


def anim_sand_kick(a):
    t = a.t
    rng = a.rng('kick')
    for _ in range(36):
        d = rng.uniform(0, 0.35)
        q = (t - d) / 0.55
        if 0 <= q <= 1:
            x, y = a.travel(q, arc=60 * rng.uniform(0.5, 1.2))
            a.circle(x + rng.uniform(-15, 15), y + rng.uniform(-15, 15), rng.uniform(2, 4) * a.s, ROCK[1], 230)
    p = seg(t, 0.55, 1.0)
    if p is not None:
        a.ellipse(a.tx, a.ty, 120 * a.s, 70 * a.s, ROCK[1], 80 * (1 - p))


def anim_iron_core(a):
    t = a.t
    steel, shine = (150, 160, 175), (230, 240, 255)
    p = ease_out(min(1, t / 0.45))
    al = 230 * fade_late(t, 0.75)
    for ring_r in (60, 42):
        r = ring_r * a.s * (1.6 - 0.6 * p)
        pts = [(a.tx + math.cos(i * TAU / 6 + math.pi / 6) * r, a.ty + math.sin(i * TAU / 6 + math.pi / 6) * r)
               for i in range(6)]
        a.lines(pts, steel, al * p, 5, closed=True)
    sweep = seg(t, 0.45, 0.85)
    if sweep is not None:  # specular shine sweeps across
        x = a.tx + lerp(-60, 60, sweep) * a.s
        a.line(x - 15 * a.s, a.ty + 50 * a.s, x + 15 * a.s, a.ty - 50 * a.s, shine, 220, 6)
        a.glow(x, a.ty, 40 * a.s, shine, 0.8)
    a.glow(a.tx, a.ty, 60 * a.s, steel, 0.5 * hump(t))


def anim_momentum(a):
    t = a.t
    p = seg(t, 0.0, 0.55)
    if p is not None:
        q = ease_in(p) ** 1.5
        x, y = a.travel(q)
        r = 20 * a.s
        for i in range(1, 5):  # speed lines grow with momentum
            a.line(x - (a.tx - a.sx) * 0.05 * i * q * 3, y - 14 * a.s + i * 7 * a.s,
                   x - (a.tx - a.sx) * 0.05 * i * q * 3 - 40 * q * a.s, y - 14 * a.s + i * 7 * a.s,
                   ROCK[1], 200, 2)
        a.poly(_rock_poly(x, y, r, p * 18), ROCK[0], 255)
        a.poly(_rock_poly(x, y, r * 0.5, p * 18 + 1), ROCK[2], 255)
    p = seg(t, 0.52, 1.0)
    if p is not None:
        a.ring(a.tx, a.ty, 70 * a.s * ease_out(p), ROCK[1], 220 * (1 - p), 4)
        a.burst(a.tx, a.ty, p, 12, 80 * a.s, ROCK[0], 5 * a.s, gravity=100, shape='square')


def anim_crash_impact(a):
    t = a.t
    # 1. Shadow grows below as a meteor rock falls
    p = seg(t, 0.0, 0.42)
    if p is not None:
        q = ease_in(p)
        a.ellipse(a.tx, a.ty + 45 * a.s, 120 * a.s * q, 24 * a.s * q, BLACK, 120)
        y = lerp(-80, a.ty, q)
        x = lerp(a.tx - 120 * a.s, a.tx, q)
        for i in range(8):
            a.circle(x - i * 12 * a.s, y - i * 22 * a.s, (26 - i * 2.5) * a.s, ROCK[1], 160 - i * 18)
        a.poly(_rock_poly(x, y, 42 * a.s, p * 4), ROCK[0], 255)
        a.poly(_rock_poly(x - 8 * a.s, y - 10 * a.s, 18 * a.s, p * 4 + 2), ROCK[1], 255)
        a.glow(x, y, 50 * a.s, MAGMA[0], 0.6 * q)
    # 2. Impact: ground cracks, dust ring, debris
    p = seg(t, 0.4, 1.0)
    if p is not None:
        rng = a.rng('crash')
        base = a.ty + 40 * a.s
        for i in range(10):
            ang = rng.uniform(-0.15, 0.15) + (i / 9) * math.pi
            pts = [(a.tx, base)]
            r = 0
            for _ in range(4):
                r += rng.uniform(18, 32) * a.s * ease_out(min(1, p * 3))
                pts.append((a.tx + math.cos(ang) * r, base + math.sin(ang) * r * 0.25))
            a.lines(pts, (60, 40, 25), 255 * fade_late(p, 0.6), 4)
        for k in range(3):
            q = seg(p, k * 0.1, 0.7 + k * 0.1)
            if q is not None:
                a.ellipse(a.tx, base, 80 * a.s + 280 * a.s * ease_out(q), 30 * a.s + 80 * a.s * ease_out(q),
                          ROCK[1], 200 * (1 - q), 6 - k)
        a.burst(a.tx, a.ty, p, 20, 170 * a.s, ROCK[0], 9 * a.s, gravity=220, shape='square', key=1)
        a.burst(a.tx, base, p, 30, 140 * a.s, ROCK[1], 10 * a.s, spread=(math.pi, TAU), key=2)
        a.glow(a.tx, a.ty, 120 * a.s, (255, 220, 170), 1.3 * (1 - p))
        _strong_finish(a, p, ((255, 235, 200),) * 2, 170, 16)


def anim_sand_storm(a):
    t = a.t
    rng = a.rng('sand')
    al = 230 * hump(t)
    for i in range(60):
        y0 = a.ty + rng.uniform(-80, 80) * a.s
        sp = rng.uniform(1.2, 2.2)
        x = a.tx - 140 * a.s + ((t * sp + rng.random()) % 1) * 280 * a.s
        y = y0 + math.sin(x * 0.05 + i) * 12 * a.s
        if rng.random() < 0.3:
            a.line(x, y, x - 14 * a.s, y, ROCK[1], al * 0.7, 2)
        else:
            a.circle(x, y, rng.uniform(1.5, 3.5) * a.s, ROCK[1] if i % 3 else ROCK[0], al)
    a.ellipse(a.tx, a.ty, 220 * a.s, 150 * a.s, ROCK[1], 40 * hump(t))


# ─────────────────────────────────────────────────────────────────────────────
# LIGHTNING
# ─────────────────────────────────────────────────────────────────────────────

def anim_stinger_shock(a):
    t = a.t
    p = seg(t, 0.0, 0.4)
    if p is not None:
        x, y = a.travel(ease_in(p))
        a.shard(x, y, 12 * a.s, a.angle_to_target(), LIGHTNING[0], 255, thin=0.2)
        a.glow(x, y, 15 * a.s, LIGHTNING[0], 0.6)
    p = seg(t, 0.38, 0.95)
    if p is not None:
        for i in range(4):
            ang = i * TAU / 4 + 0.4
            if random.random() < 0.7:
                a.bolt(a.tx, a.ty, a.tx + math.cos(ang) * 40 * a.s, a.ty + math.sin(ang) * 40 * a.s,
                       width=2, jag=6, segs=4, glow=0.4)


def anim_static_graze(a):
    t = a.t
    if t < 0.9 and int(t * 30) % 2 == 0:
        for i in range(5):
            ang = random.uniform(0, TAU)
            r = 50 * a.s
            x1, y1 = a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r
            x2, y2 = a.tx + math.cos(ang + 0.6) * r, a.ty + math.sin(ang + 0.6) * r
            a.bolt(x1, y1, x2, y2, col=LIGHTNING[2], width=2, jag=8, segs=4, glow=0.4)
    a.glow(a.tx, a.ty, 55 * a.s, LIGHTNING[2], 0.4 * hump(t))


def anim_thunder_blitz(a):
    for k, off in enumerate((-30, 25, 0)):
        p = seg(a.t, k * 0.22, 0.25 + k * 0.22)
        if p is not None:
            x = a.tx + off * a.s
            a.bolt(x + random.uniform(-15, 15), 0, x, a.ty, width=3, jag=16, segs=9)
            a.glow(x, a.ty, 40 * a.s, LIGHTNING[0], 1.0)
            a.tint(LIGHTNING[1], 50)
    _impact(a, seg(a.t, 0.66, 1.0), LIGHTNING, 0.9)


def anim_lightning_bolt(a):
    t = a.t
    p = seg(t, 0.1, 0.55)
    if p is not None and int(p * 12) % 3 != 2:
        a.bolt(a.tx + random.uniform(-10, 10), 0, a.tx, a.ty, width=6, jag=26, segs=11, glow=1.0)
        a.tint(WHITE, 110 * (1 - p))
    p = seg(t, 0.15, 1.0)
    if p is not None:
        a.glow(a.tx, a.ty, 80 * a.s, LIGHTNING[0], 1.3 * (1 - p))
        a.burst(a.tx, a.ty, p, 12, 80 * a.s, LIGHTNING[1], 3 * a.s, shape='streak', glow=0.3)
        if p < 0.25:
            a.shake(3)


def anim_volt_storm(a):
    t = a.t
    cloud_y = max(40, a.ty - 150 * a.s)
    # 1. Storm cloud gathers
    form = ease_out(min(1, t / 0.3))
    cloud_al = 230 * fade_late(t, 0.8)
    for i in range(7):
        x = a.tx + (i - 3) * 28 * a.s
        a.circle(x, cloud_y + (i % 2) * 10 * a.s, (26 + (i % 3) * 6) * a.s * form, (70, 70, 90), cloud_al)
    for i in range(5):
        x = a.tx + (i - 2) * 30 * a.s
        a.circle(x, cloud_y - 10 * a.s, 20 * a.s * form, (100, 100, 125), cloud_al)
    a.tint((10, 10, 40), 120 * min(1, t * 4) * fade_late(t, 0.8))
    # 2. Repeated strikes with crackling sphere around the target
    p = seg(t, 0.25, 0.85)
    if p is not None:
        strike = int(p * 9)
        if strike % 2 == 0:
            rng = random.Random(strike + a._anim.seed)
            x = a.tx + rng.uniform(-50, 50) * a.s
            a.bolt(x, cloud_y + 15 * a.s, a.tx + rng.uniform(-15, 15) * a.s, a.ty, width=5, jag=22, segs=9)
            a.tint(LIGHTNING[1], 90)
            a.shake(5)
        for i in range(6):
            ang = random.uniform(0, TAU)
            r = 55 * a.s
            a.bolt(a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r,
                   a.tx + math.cos(ang + 0.9) * r, a.ty + math.sin(ang + 0.9) * r,
                   col=LIGHTNING[2], width=2, jag=8, segs=4, glow=0.3)
        a.ring(a.tx, a.ty, 55 * a.s, LIGHTNING[0], 160, 2)
        a.glow(a.tx, a.ty, 80 * a.s, LIGHTNING[0], 0.8)
    # 3. Discharge
    p = seg(t, 0.8, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 30, 160 * a.s, LIGHTNING[1], 4 * a.s, shape='streak', glow=0.5)
        a.ring(a.tx, a.ty, 40 * a.s + 140 * a.s * ease_out(p), LIGHTNING[0], 230 * (1 - p), 4)
        _strong_finish(a, p, LIGHTNING, 180, 9)


def anim_conduit_surge(a):
    t = a.t
    p = seg(t, 0.0, 0.5)
    if p is not None:  # current races along a jagged path to the target
        head = ease_in(p)
        x2, y2 = a.travel(head)
        a.bolt(a.sx, a.sy, x2, y2, col=LIGHTNING[2], width=3, jag=12, segs=10, glow=0.5)
        a.circle(x2, y2, 7 * a.s, WHITE, 255)
        a.glow(x2, y2, 30 * a.s, LIGHTNING[0], 1.2)
    p = seg(t, 0.45, 1.0)
    if p is not None:
        for k in range(3):
            q = seg(p, k * 0.15, 0.6 + k * 0.15)
            if q is not None:
                a.ring(a.tx, a.ty, 15 * a.s + 70 * a.s * q, LIGHTNING[k % 2 * 2], 230 * (1 - q), 3)
        a.glow(a.tx, a.ty, 60 * a.s, LIGHTNING[0], 1.1 * (1 - p))


def anim_quantum_flux(a):
    t = a.t
    cyan, mag = (80, 240, 255), (255, 80, 220)
    # 1. Reality glitches: displaced afterimages + scanline blocks
    p = seg(t, 0.0, 0.6)
    if p is not None:
        rng = random.Random(int(t * 24) + a._anim.seed)  # changes ~24x/s for a glitchy feel
        for _ in range(9):
            w = rng.uniform(20, 80) * a.s
            h = rng.uniform(4, 14) * a.s
            x = a.tx + rng.uniform(-70, 70) * a.s
            y = a.ty + rng.uniform(-70, 70) * a.s
            col = cyan if rng.random() < 0.5 else mag
            a.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], col, 170)
        off = rng.uniform(-14, 14) * a.s
        a.ring(a.tx + off, a.ty, 50 * a.s, cyan, 200, 3)
        a.ring(a.tx - off, a.ty, 50 * a.s, mag, 200, 3)
        grid = 18 * a.s
        for i in range(-3, 4):
            a.line(a.tx + i * grid, a.ty - 60 * a.s, a.tx + i * grid, a.ty + 60 * a.s, cyan, 70 * hump(p), 1)
            a.line(a.tx - 60 * a.s, a.ty + i * grid, a.tx + 60 * a.s, a.ty + i * grid, mag, 70 * hump(p), 1)
        a.tint((10, 0, 30), 110 * p)
    # 2. Implode to a singular point
    p = seg(t, 0.5, 0.72)
    if p is not None:
        a.implode(a.tx, a.ty, p, 30, 120 * a.s, cyan, 3 * a.s, glow=0.4, swirl=4, key=1)
        a.implode(a.tx, a.ty, p, 20, 100 * a.s, mag, 3 * a.s, glow=0.4, swirl=-4, key=2)
        a.circle(a.tx, a.ty, 6 * a.s * p, WHITE, 255)
        a.tint((10, 0, 30), 110)
    # 3. Flux burst
    p = seg(t, 0.7, 1.0)
    if p is not None:
        a.ring(a.tx, a.ty, 20 * a.s + 140 * a.s * ease_out(p), cyan, 240 * (1 - p), 4)
        a.ring(a.tx, a.ty, 10 * a.s + 110 * a.s * ease_out(p), mag, 240 * (1 - p), 4)
        a.burst(a.tx, a.ty, p, 24, 150 * a.s, cyan, 4 * a.s, shape='square', glow=0.4)
        a.burst(a.tx, a.ty, p, 18, 130 * a.s, mag, 4 * a.s, shape='square', glow=0.4, key=1)
        _strong_finish(a, p, (cyan, (220, 255, 255)), 170, 8)


def anim_shock(a):
    t = a.t
    rng = a.rng('shock')
    for i in range(6):
        d = rng.uniform(0, 0.6)
        q = seg(t, d, d + 0.25)
        if q is not None:
            x = a.tx + rng.uniform(-50, 50) * a.s
            y = a.ty + rng.uniform(-50, 50) * a.s
            a.bolt(x - 12 * a.s, y - 12 * a.s, x + 12 * a.s, y + 12 * a.s, width=2, jag=6, segs=4, glow=0.5)


# ─────────────────────────────────────────────────────────────────────────────
# DARK
# ─────────────────────────────────────────────────────────────────────────────

def anim_force_shift(a):
    t = a.t
    for k in range(4):
        q = seg(t, k * 0.12, 0.55 + k * 0.12)
        if q is not None:
            shift = math.sin(q * math.pi * 3) * 18 * a.s
            a.ellipse(a.tx + shift, a.ty, (30 + 110 * q) * a.s, (20 + 70 * q) * a.s, DARK[1], 220 * (1 - q), 3)
    a.glow(a.tx, a.ty, 50 * a.s, DARK[0], 0.7 * hump(t))


def anim_dark_energy(a):
    t = a.t
    p = seg(t, 0.0, 0.5)
    if p is not None:
        x, y = a.travel(ease_in(p), arc=15)
        a.circle(x, y, 14 * a.s, DARK[2], 255)
        a.ring(x, y, 14 * a.s + 3 * math.sin(t * 40), DARK[1], 230, 3)
        a.glow(x, y, 35 * a.s, DARK[0], 1.0)
    p = seg(t, 0.48, 1.0)
    if p is not None:
        a.circle(a.tx, a.ty, 45 * a.s * ease_out(p), DARK[2], 220 * (1 - p))
        a.ring(a.tx, a.ty, 55 * a.s * ease_out(p), DARK[1], 230 * (1 - p), 4)
        a.burst(a.tx, a.ty, p, 14, 70 * a.s, DARK[1], 4 * a.s, glow=0.3)


def anim_void_collapse(a):
    t = a.t
    # 1. Darkness falls, a black hole opens on the target
    p = seg(t, 0.0, 0.65)
    if p is not None:
        a.tint(BLACK, 170 * ease_out(min(1, p * 2)))
        r = 40 * a.s * ease_out(min(1, p * 1.5))
        for k in range(3):  # accretion disc
            ang0 = t * (8 + k * 3)
            for i in range(20):
                ang = ang0 + i * TAU / 20
                rr = r * (1.5 + k * 0.4)
                a.circle(a.tx + math.cos(ang) * rr, a.ty + math.sin(ang) * rr * 0.4,
                         2.5 * a.s, DARK[1] if k == 0 else DARK[0], 220)
        a.circle(a.tx, a.ty, r * 1.1, DARK[1], 230)
        a.circle(a.tx, a.ty, r, BLACK, 255)
        a.implode(a.tx, a.ty, p, 40, 180 * a.s, DARK[1], 3 * a.s, glow=0.3, swirl=5)
        a.glow(a.tx, a.ty, r * 3, DARK[0], 0.7)
        a.shake(2 * p)
    # 2. Collapse to a point
    p = seg(t, 0.6, 0.72)
    if p is not None:
        a.tint(BLACK, 170)
        r = 40 * a.s * (1 - ease_in(p))
        a.circle(a.tx, a.ty, r * 1.1, DARK[1], 230)
        a.circle(a.tx, a.ty, r, BLACK, 255)
    # 3. Rebound shockwave
    p = seg(t, 0.7, 1.0)
    if p is not None:
        a.tint(BLACK, 170 * (1 - p))
        for k in range(3):
            q = seg(p, k * 0.1, 0.7 + k * 0.1)
            if q is not None:
                a.ring(a.tx, a.ty, 10 * a.s + 180 * a.s * ease_out(q), DARK[1], 240 * (1 - q), 6 - k * 2)
        a.burst(a.tx, a.ty, p, 30, 170 * a.s, DARK[1], 5 * a.s, shape='shard', glow=0.4)
        a.glow(a.tx, a.ty, 120 * a.s, DARK[1], 1.4 * (1 - p))
        if p < 0.5:
            a.shake(12 * (1 - p * 2))


def anim_bitemark(a):
    _jaws(a, a.t, (60, 20, 80), 0.9, 6)
    p = seg(a.t, 0.45, 1.0)
    if p is not None:
        for i in range(5):  # bite marks
            x = a.tx + (i - 2) * 16 * a.s
            a.circle(x, a.ty - 4 * a.s, 4 * a.s, DARK[1], 230 * (1 - p))
            a.circle(x, a.ty + 4 * a.s, 4 * a.s, DARK[1], 230 * (1 - p))
        a.glow(a.tx, a.ty, 50 * a.s, DARK[0], 1.0 * (1 - p))


def anim_distortion(a):
    t = a.t
    al = 220 * hump(t)
    for k in range(7):
        y = a.ty - 60 * a.s + k * 20 * a.s
        pts = []
        for i in range(25):
            x = a.tx - 90 * a.s + i * 7.5 * a.s
            pts.append((x, y + math.sin(i * 0.7 + t * 20 + k) * 8 * a.s * hump(t)))
        a.lines(pts, DARK[1] if k % 2 else (180, 180, 255), al * 0.8, 2)
    a.glow(a.tx, a.ty, 60 * a.s, DARK[0], 0.6 * hump(t))


def anim_fear(a):
    t = a.t
    a.tint(BLACK, 150 * hump(t))
    rng = a.rng('fear')
    for k in range(4):  # pairs of red eyes open in the dark
        q = seg(t, k * 0.12, 0.7 + k * 0.08)
        if q is not None:
            x = a.tx + rng.uniform(-110, 110) * a.s
            y = a.ty + rng.uniform(-90, 60) * a.s
            open_ = hump(q)
            for ex in (-12, 12):
                a.ellipse(x + ex * a.s, y, 16 * a.s, 10 * a.s * open_, (255, 40, 40), 255)
                a.glow(x + ex * a.s, y, 14 * a.s, (255, 40, 40), 0.6 * open_)
    p = seg(t, 0.5, 1.0)
    if p is not None:
        a.ring(a.tx, a.ty, 70 * a.s * (1 - 0.5 * p), DARK[1], 200 * (1 - p), 3)


def anim_haunt(a):
    t = a.t
    al = 220 * fade_late(t, 0.7)
    for k in range(3):  # ghost wisps orbiting
        ang = t * TAU * 1.5 + k * TAU / 3
        x = a.tx + math.cos(ang) * 60 * a.s
        y = a.ty + math.sin(ang) * 30 * a.s - 10 * a.s
        for i in range(8, 0, -1):  # tail
            ta = ang - i * 0.12
            a.circle(a.tx + math.cos(ta) * 60 * a.s, a.ty + math.sin(ta) * 30 * a.s - 10 * a.s,
                     (12 - i) * a.s * 0.8, DARK[1], al * (1 - i / 9))
        a.circle(x, y, 12 * a.s, (225, 215, 255), al)
        a.circle(x - 4 * a.s, y - 2 * a.s, 2 * a.s, BLACK, al)
        a.circle(x + 4 * a.s, y - 2 * a.s, 2 * a.s, BLACK, al)
        a.glow(x, y, 25 * a.s, DARK[1], 0.6 * al / 220)
    a.tint(DARK[2], 80 * hump(t))


def anim_binding_curse(a):
    t = a.t
    grow = ease_out(min(1, t / 0.5))
    al = 240 * fade_late(t, 0.75)
    tight = 1 - 0.2 * hump(seg(t, 0.5, 1.0) or 0)
    for c, tilt in ((0, 0.35), (1, -0.35)):  # two chains wrapping the target
        n = int(14 * grow)
        for i in range(n):
            ang = i * TAU / 14 + t * 2 * (1 if c else -1)
            x = a.tx + math.cos(ang) * 65 * a.s * tight
            y = a.ty + math.sin(ang) * 22 * a.s * tight + math.cos(ang) * tilt * 40 * a.s
            a.ellipse(x, y, (12 if i % 2 else 7) * a.s, (7 if i % 2 else 12) * a.s, (150, 140, 170), al, 2)
    p = seg(t, 0.3, 1.0)
    if p is not None:  # rune circle
        for i in range(6):
            ang = i * TAU / 6 - t * 2
            x, y = a.tx + math.cos(ang) * 40 * a.s, a.ty + math.sin(ang) * 40 * a.s
            a.star(x, y, 6 * a.s, DARK[1], 230 * hump(p), points=3, rot=ang)
        a.glow(a.tx, a.ty, 60 * a.s, DARK[0], 0.8 * hump(p))


def anim_shadow_veil(a):
    t = a.t
    rng = a.rng('veil')
    for i in range(10):  # smoke tendrils rise and curl around the target
        x0 = a.tx + (i - 4.5) * 14 * a.s
        ph = rng.uniform(0, TAU)
        grow = ease_out(min(1, t / 0.6))
        pts = []
        for k in range(12):
            u = k / 11 * grow
            pts.append((x0 + math.sin(u * 6 + ph + t * 4) * 18 * a.s, a.ty + 60 * a.s - u * 130 * a.s))
        a.lines(pts, DARK[2], 220 * fade_late(t, 0.7), int(7 * a.s))
        a.lines(pts, DARK[0], 200 * fade_late(t, 0.7), int(3 * a.s))
    a.ellipse(a.tx, a.ty, 160 * a.s, 140 * a.s, DARK[2], 60 * hump(t))
    _impact(a, seg(t, 0.55, 1.0), DARK, 0.8)


# ─────────────────────────────────────────────────────────────────────────────
# LIGHT
# ─────────────────────────────────────────────────────────────────────────────

def anim_prism_glare(a):
    t = a.t
    px, py = a.tx, a.ty - 80 * a.s
    p = ease_out(min(1, t / 0.3))
    al = 255 * fade_late(t, 0.75)
    a.poly([(px, py - 16 * a.s * p), (px - 14 * a.s * p, py + 10 * a.s * p), (px + 14 * a.s * p, py + 10 * a.s * p)],
           LIGHT[1], al)
    a.glow(px, py, 30 * a.s, WHITE, 0.8 * fade_late(t, 0.75))
    q = seg(t, 0.2, 1.0)
    if q is not None:  # rainbow fan onto target
        reach = ease_out(min(1, q * 2))
        for i, col in enumerate(RAINBOW):
            ang = math.pi / 2 + (i - 3) * 0.12
            ln = 140 * a.s * reach
            a.line(px, py, px + math.cos(ang) * ln, py + math.sin(ang) * ln, col, 200 * fade_late(q, 0.6), 4)
        a.glow(a.tx, a.ty + 20 * a.s, 50 * a.s, LIGHT[0], 0.9 * hump(q))


def anim_piercing_light(a):
    t = a.t
    _beam(a, seg(t, 0.0, 0.8), LIGHT[2], 8 * a.s)
    p = seg(t, 0.2, 0.8)
    if p is not None:  # beam continues through and out the far side
        ang = a.angle_to_target()
        ex, ey = a.tx + math.cos(ang) * 120 * a.s * ease_out(p), a.ty + math.sin(ang) * 120 * a.s * ease_out(p)
        a.line(a.tx, a.ty, ex, ey, WHITE, 230 * (1 - p), 4)
    a.burst(a.tx, a.ty, seg(t, 0.3, 1.0), 12, 70 * a.s, WHITE, 3 * a.s, shape='star', glow=0.4)


def anim_spectral_overload(a):
    t = a.t
    # 1. Rainbow light gathers in rotating rays
    p = seg(t, 0.0, 0.5)
    if p is not None:
        for i, col in enumerate(RAINBOW):
            ang = i * TAU / len(RAINBOW) + t * 5
            ln = 160 * a.s * ease_out(p)
            a.line(a.tx, a.ty, a.tx + math.cos(ang) * ln, a.ty + math.sin(ang) * ln, col, 210, 6)
            a.line(a.tx, a.ty, a.tx - math.cos(ang) * ln, a.ty - math.sin(ang) * ln, col, 210, 6)
        a.implode(a.tx, a.ty, p, 30, 160 * a.s, WHITE, 3 * a.s, glow=0.5, swirl=3)
        a.glow(a.tx, a.ty, 50 * a.s * p, WHITE, 1.2)
    # 2. Overload: spectral rings ripple out, one per color
    p = seg(t, 0.4, 0.95)
    if p is not None:
        for i, col in enumerate(RAINBOW):
            q = seg(p, i * 0.06, 0.55 + i * 0.06)
            if q is not None:
                a.ring(a.tx, a.ty, 15 * a.s + 170 * a.s * ease_out(q), col, 240 * (1 - q), 5)
        a.burst(a.tx, a.ty, p, 30, 170 * a.s, WHITE, 4 * a.s, shape='star', glow=0.6)
        a.glow(a.tx, a.ty, 130 * a.s, WHITE, 1.6 * (1 - p))
    # 3. White-out flash
    p = seg(t, 0.42, 1.0)
    if p is not None:
        _strong_finish(a, p, (WHITE, WHITE), 235, 9)


def anim_flash(a):
    t = a.t
    a.tint(WHITE, 230 * (1 - t) ** 1.5)
    a.star(a.tx, a.ty, 90 * a.s * ease_out(t), WHITE, 255 * (1 - t), points=8, rot=t, inner=0.2)
    a.glow(a.tx, a.ty, 90 * a.s, LIGHT[0], 1.5 * (1 - t))


def anim_refraction(a):
    t = a.t
    al = 240 * fade_late(t, 0.75)
    for i in range(6):  # crystals orbit the user, casting colored rays
        ang = i * TAU / 6 + t * 4
        r = 60 * a.s * ease_out(min(1, t * 3))
        x, y = a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r * 0.5
        sz = 9 * a.s
        a.poly([(x, y - sz * 1.5), (x + sz, y), (x, y + sz * 1.5), (x - sz, y)], (220, 245, 255), al)
        col = RAINBOW[i]
        a.line(x, y, x + math.cos(ang) * 50 * a.s, y + math.sin(ang) * 25 * a.s, col, al * 0.8, 3)
        a.glow(x, y, 18 * a.s, col, 0.6 * al / 240)
    a.glow(a.tx, a.ty, 50 * a.s, LIGHT[0], 0.5 * hump(t))


def anim_gamma_wave(a):
    t = a.t
    green, lime = (90, 255, 120), (210, 255, 120)
    # 1. Pulse charges at the attacker
    p = seg(t, 0.0, 0.25)
    if p is not None:
        for k in range(3):
            a.ring(a.sx, a.sy, (40 - k * 12) * a.s * (1 - p), green, 220 * p, 3)
        a.glow(a.sx, a.sy, 40 * a.s, green, 1.2 * p)
        a.tint((0, 30, 0), 100 * p)
    # 2. Sinusoidal radiation wave streams to the target
    p = seg(t, 0.2, 0.7)
    if p is not None:
        reach = ease_out(min(1, p * 1.8))
        ang = a.angle_to_target()
        nx, ny = -math.sin(ang), math.cos(ang)
        for wave, col, ph in ((0, green, 0), (1, lime, math.pi)):
            pts = []
            for i in range(41):
                u = i / 40 * reach
                x, y = a.travel(u)
                amp = 16 * a.s * math.sin(u * 22 - t * 40 + ph)
                pts.append((x + nx * amp, y + ny * amp))
            a.lines(pts, col, 240, 4)
        for i in range(8):
            x, y = a.travel(reach * i / 7)
            a.glow(x, y, 24 * a.s, green, 0.6)
        a.tint((0, 30, 0), 100)
    # 3. Target engulfed in radiant pulses
    p = seg(t, 0.55, 1.0)
    if p is not None:
        for k in range(4):
            q = seg(p, k * 0.1, 0.6 + k * 0.1)
            if q is not None:
                a.ring(a.tx, a.ty, 20 * a.s + 130 * a.s * ease_out(q), green if k % 2 else lime, 230 * (1 - q), 4)
        a.circle(a.tx, a.ty, 55 * a.s * hump(p), green, 120)
        a.glow(a.tx, a.ty, 110 * a.s, green, 1.5 * (1 - p))
        a.burst(a.tx, a.ty, p, 20, 120 * a.s, lime, 3 * a.s, glow=0.5)
        _strong_finish(a, p, (green, (220, 255, 200)), 160, 8)


# ── Ultra Violet (signature, longer than the rest — see DURATIONS) ──────────
# Attacker charges a UV orb -> launches it into the sky where it becomes an
# eclipsed ultraviolet sun -> the sun swells and fires a helix-wrapped beam
# down onto the target -> prism explosion -> afterglow while violet motes
# drain off the attacker (its Attack drop).

UV = ((150, 60, 255), (232, 196, 255), (58, 12, 120))
UV_PINK = (255, 90, 220)
UV_BLUE = (110, 170, 255)
UV_NIGHT = (14, 0, 34)


def _uv_sun_pos(a):
    return (a.sx + a.tx) / 2, max(72.0, min(a.sy, a.ty) - 85 * a.s)


def _uv_eclipse(a, x, y, r, k, rot):
    """Black sun with a flickering violet corona; k = 0..1 intensity."""
    if r < 2 or k <= 0.02:
        return
    for i in range(16):
        ang = rot + i * TAU / 16
        ln = r * (0.6 + 0.6 * (0.5 + 0.5 * math.sin(i * 2.3 + rot * 5)))
        ca, sa = math.cos(ang), math.sin(ang)
        a.line(x + ca * r * 1.05, y + sa * r * 1.05, x + ca * (r * 1.05 + ln), y + sa * (r * 1.05 + ln),
               UV_PINK if i % 2 else UV[0], 210 * k, max(2, r * 0.12))
    # Glows sit around the rim (not the center) so the disc stays black
    for i in range(10):
        ang = rot * 0.5 + i * TAU / 10
        a.glow(x + math.cos(ang) * r * 1.2, y + math.sin(ang) * r * 1.2, r * 1.1,
               UV[0] if i % 2 else UV_PINK, 0.9 * k)
    a.ring(x, y, r * 1.14, UV[1], 255 * k, max(2, r * 0.16))
    a.circle(x, y, r, (8, 0, 18), 255 * k)
    a.ring(x, y, r, WHITE, 230 * k, 2)


def _uv_beam(a, x1, y1, x2, y2, p, t):
    if p is None:
        return
    s = a.s
    reach = ease_out(min(1.0, p / 0.25))
    fade = 1.0 if p < 0.7 else max(0.0, (1 - p) / 0.3)
    bx, by = lerp(x1, x2, reach), lerp(y1, y2, reach)
    throb = 0.9 + 0.1 * math.sin(t * 90)
    for w, col, al in ((56, UV[2], 150), (38, UV[0], 210), (22, UV_PINK, 230), (11, UV[1], 255), (4, WHITE, 255)):
        width = w * s * fade * throb
        a.line(x1, y1, bx, by, col, al * fade, width)
        a.circle(bx, by, width / 2, col, al * fade)   # round off the leading end
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    for ph, col in ((0.0, UV_BLUE), (math.pi, UV_PINK)):
        pts = []
        for i in range(31):
            u = i / 30 * reach
            amp = 30 * s * fade * math.sin(u * 18 - t * 60 + ph)
            pts.append((x1 + dx * u + nx * amp, y1 + dy * u + ny * amp))
        a.lines(pts, col, 230 * fade, 3)
    for i in range(1, 8):
        u = reach * i / 7
        a.glow(x1 + dx * u, y1 + dy * u, 34 * s, UV[0], 0.9 * fade)
    a.burst(bx, by, min(1.0, p * 2), 12, 60 * s, UV[1], 3 * s, glow=0.4, key='uvtip')


def anim_ultra_violet(a):
    t, s = a.t, a.s
    ex, ey = _uv_sun_pos(a)

    # Sky darkens to a deep violet for most of the move
    a.tint(UV_NIGHT, 170 * min(1.0, t / 0.2) * (1.0 if t < 0.85 else max(0.0, (1 - t) / 0.15)))

    # 1. Charge: light spirals into an orb at the attacker
    p = seg(t, 0.0, 0.24)
    if p is not None:
        a.implode(a.sx, a.sy, p, 34, 130 * s, UV[1], 3 * s, glow=0.4, swirl=4)
        for k in range(3):
            a.ring(a.sx, a.sy, (58 - k * 15) * s * (1 - 0.5 * p), UV_PINK if k % 2 else UV[0], 210 * p, 3)
        a.circle(a.sx, a.sy, 13 * s * ease_out(p), WHITE, 255)
        a.glow(a.sx, a.sy, 44 * s * p, UV[0], 1.4)
        if p > 0.45:
            for k in range(3):
                ang = k * TAU / 3 + t * 20
                a.bolt(a.sx, a.sy, a.sx + math.cos(ang) * 46 * s, a.sy + math.sin(ang) * 46 * s,
                       UV[0], width=2, jag=8, segs=5, glow=0.4)

    # 2. Orb launches skyward
    p = seg(t, 0.2, 0.34)
    if p is not None:
        e = ease_in(p)
        for i in range(6, -1, -1):
            q = max(0.0, e - i * 0.05)
            x = lerp(a.sx, ex, q)
            y = lerp(a.sy, ey, q) - 40 * s * math.sin(math.pi * q)
            a.circle(x, y, (12 - i * 1.4) * s, WHITE if i == 0 else UV[0], 255 * (1 - i / 7))
        x = lerp(a.sx, ex, e)
        y = lerp(a.sy, ey, e) - 40 * s * math.sin(math.pi * e)
        a.glow(x, y, 40 * s, UV[0], 1.3)

    # 3. The ultraviolet eclipse: forms, swells while charging, collapses at the end
    sun = seg(t, 0.32, 1.0)
    sun_r = sun_k = 0.0
    if sun is not None:
        form = ease_out(min(1.0, sun / 0.15))
        collapse = 1 - ease_in(max(0.0, (sun - 0.75) / 0.25))
        swell = 1 + 0.4 * hump(seg(t, 0.4, 0.52) or 0.0)
        sun_r, sun_k = 30 * s * form * collapse * swell, form * collapse

    # 4. Beam blasts down from the sun's rim onto the target (drawn under the sun)
    p = seg(t, 0.5, 0.8)
    if p is not None:
        ang = math.atan2(a.ty - ey, a.tx - ex)
        _uv_beam(a, ex + math.cos(ang) * sun_r * 0.8, ey + math.sin(ang) * sun_r * 0.8, a.tx, a.ty, p, t)
        if p < 0.75:
            a.shake(7)

    if sun is not None:
        _uv_eclipse(a, ex, ey, sun_r, sun_k, t * 3)
        if t < 0.5:
            a.implode(ex, ey, seg(t, 0.34, 0.5), 26, 150 * s, UV_PINK, 2.5 * s, glow=0.3, key='uvsun', swirl=-3)

    # 5. Prism explosion at the target
    p = seg(t, 0.6, 0.96)
    if p is not None:
        for k, col in enumerate((WHITE, UV_PINK, UV[0], UV_BLUE)):
            q = seg(p, k * 0.08, 0.6 + k * 0.08)
            if q is not None:
                a.ring(a.tx, a.ty, 20 * s + 175 * s * ease_out(q), col, 240 * (1 - q), 6)
        a.star(a.tx, a.ty, 150 * s * ease_out(min(1.0, p * 2)), UV[1], 230 * (1 - p), points=6, rot=p * 1.5, inner=0.14)
        a.star(a.tx, a.ty, 90 * s * ease_out(min(1.0, p * 2)), WHITE, 255 * (1 - p), points=6, rot=-p, inner=0.18)
        a.burst(a.tx, a.ty, p, 22, 170 * s, UV_PINK, 5 * s, shape='shard', key='uvshard')
        a.burst(a.tx, a.ty, p, 18, 140 * s, UV[1], 3 * s, shape='star', glow=0.6, key='uvstar')
        a.glow(a.tx, a.ty, 140 * s, UV[0], 1.8 * (1 - p))
        _strong_finish(a, p, (UV[0], (240, 214, 255)), 220, 12)

    # 6. Afterglow: motes settle on the target, power drains off the attacker
    p = seg(t, 0.78, 1.0)
    if p is not None:
        a.rain(p, 18, UV[1], a.tx - 80 * s, a.tx + 80 * s, a.ty - 90 * s, a.ty + 40 * s,
               width=2 * s, key='uvmote', speed=0.9, shape='dot')
        a.rain(p, 12, UV[0], a.sx - 40 * s, a.sx + 40 * s, a.sy - 30 * s, a.sy + 50 * s,
               width=2.5 * s, key='uvdrain', speed=0.8, shape='dot')
        a.glow(a.sx, a.sy, 40 * s, UV[2], 0.8 * hump(p))


# ─────────────────────────────────────────────────────────────────────────────
# ICE
# ─────────────────────────────────────────────────────────────────────────────

def anim_snowfall(a):
    t = a.t
    a.rain(t, 26, ICE[1], a.tx - 90 * a.s, a.tx + 90 * a.s, a.ty - 110 * a.s, a.ty + 50 * a.s,
           length=12 * a.s, key=1, speed=0.9, shape='flake')
    a.glow(a.tx, a.ty, 60 * a.s, ICE[0], 0.4 * hump(t))


def _hex_crystal(a, x, y, r, col, alpha, rot=0.0):
    pts = [(x + math.cos(rot + i * TAU / 6) * r * (1.0 if i % 3 else 1.5),
            y + math.sin(rot + i * TAU / 6) * r * (1.0 if i % 3 else 1.5)) for i in range(6)]
    a.poly(pts, col, alpha)
    a.lines(pts, WHITE, alpha, 2, closed=True)


def anim_freeze_blast(a):
    t = a.t
    # 1. Freezing beam
    _beam(a, seg(t, 0.0, 0.45), ICE[0], 12 * a.s)
    p = seg(t, 0.0, 0.45)
    if p is not None:
        rng = a.rng('fb')
        for _ in range(16):
            u = rng.uniform(0, min(1, p / 0.35))
            x, y = a.travel(u)
            a.star(x + rng.uniform(-14, 14), y + rng.uniform(-14, 14), 5 * a.s, ICE[1], 230, points=3, rot=u * 9)
        a.tint((20, 50, 90), 90 * p)
    # 2. Target encased in growing ice crystal
    p = seg(t, 0.35, 0.75)
    if p is not None:
        g = ease_out(p)
        rng = a.rng('fbc')
        for i in range(9):
            ang = i * TAU / 9 + rng.uniform(-0.2, 0.2)
            d = 45 * a.s * g
            a.shard(a.tx + math.cos(ang) * d * 0.5, a.ty + math.sin(ang) * d * 0.5, 40 * a.s * g, ang,
                    ICE[0], 200)
        _hex_crystal(a, a.tx, a.ty, 50 * a.s * g, (190, 235, 255), 150)
        a.glow(a.tx, a.ty, 70 * a.s, ICE[0], 0.8)
        a.tint((20, 50, 90), 90)
    # 3. Shatter
    p = seg(t, 0.72, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 30, 170 * a.s, ICE[1], 9 * a.s, shape='shard', glow=0.3, gravity=60)
        a.burst(a.tx, a.ty, p, 18, 120 * a.s, ICE[0], 7 * a.s, shape='shard', key=1, gravity=80)
        a.ring(a.tx, a.ty, 30 * a.s + 140 * a.s * ease_out(p), WHITE, 230 * (1 - p), 4)
        a.glow(a.tx, a.ty, 110 * a.s, ICE[1], 1.4 * (1 - p))
        _strong_finish(a, p, ICE, 190, 10)


def anim_hyperfrost(a):
    t = a.t
    base = a.ty + 45 * a.s
    for i in range(7):  # ice spikes shoot up in quick succession
        q = seg(t, i * 0.05, 0.2 + i * 0.05)
        h = (60 + (i * 23) % 40) * a.s * (ease_out(q) if q is not None else (1 if t > 0.2 + i * 0.05 else 0))
        x = a.tx + (i - 3) * 20 * a.s
        al = 240 * fade_late(t, 0.7)
        if h > 1:
            a.poly([(x - 9 * a.s, base), (x + 9 * a.s, base), (x + (i - 3) * 2, base - h)], ICE[0], al)
            a.poly([(x - 3 * a.s, base), (x + 2 * a.s, base), (x + (i - 3) * 2, base - h)], WHITE, al)
    _impact(a, seg(t, 0.4, 1.0), ICE, 0.9)


def anim_hail_storm(a):
    t = a.t
    rng = a.rng('hail')
    land_y = a.ty + 45 * a.s
    for i in range(24):
        x = a.tx + rng.uniform(-100, 100) * a.s
        d = rng.uniform(0, 0.6)
        q = (t - d) / 0.25
        r = rng.uniform(3, 6) * a.s
        if 0 <= q <= 1:
            y = lerp(a.ty - 160 * a.s, land_y, q)
            a.circle(x, y, r, ICE[1], 240)
            a.line(x, y, x - 4, y - 18 * a.s, ICE[0], 150, 2)
        elif 1 < q < 1.8:  # bounce
            b = q - 1
            a.circle(x + b * 20 * (1 if i % 2 else -1), land_y - math.sin(b / 0.8 * math.pi) * 15 * a.s,
                     r, ICE[1], 240 * (1 - b / 0.8))
    a.tint((40, 60, 90), 60 * hump(t))


def anim_frozen_aura(a):
    t = a.t
    al = fade_late(t, 0.7)
    a.ellipse(a.tx, a.ty + 40 * a.s, 170 * a.s * ease_out(min(1, t * 2)), 50 * a.s, ICE[0], 130 * al)
    for k in range(3):
        q = seg(t, k * 0.2, 0.6 + k * 0.2)
        if q is not None:
            a.ring(a.tx, a.ty, 70 * a.s * (1 - q) + 10, ICE[1], 220 * q, 2)
    for i in range(6):  # snowflake emblem
        ang = i * TAU / 6 + t
        ln = 35 * a.s * ease_out(min(1, t * 2))
        x, y = a.tx + math.cos(ang) * ln, a.ty + math.sin(ang) * ln
        a.line(a.tx, a.ty, x, y, WHITE, 230 * al, 3)
        a.line(x, y, x + math.cos(ang + 2.4) * 8 * a.s, y + math.sin(ang + 2.4) * 8 * a.s, WHITE, 230 * al, 2)
        a.line(x, y, x + math.cos(ang - 2.4) * 8 * a.s, y + math.sin(ang - 2.4) * 8 * a.s, WHITE, 230 * al, 2)
    a.burst(a.tx, a.ty, seg(t, 0.2, 1.0), 14, 80 * a.s, WHITE, 3 * a.s, shape='star', gravity=-50, glow=0.3)
    a.glow(a.tx, a.ty, 70 * a.s, ICE[0], 0.7 * hump(t))


def anim_deep_freeze(a):
    t = a.t
    rng = a.rng('deep')
    grow = ease_out(min(1, t / 0.65))
    al = 240 * fade_late(t, 0.75)
    for i in range(8):  # branching frost creeping inward from the edges
        ang = i * TAU / 8 + rng.uniform(-0.2, 0.2)
        r0 = 90 * a.s
        x0, y0 = a.tx + math.cos(ang) * r0, a.ty + math.sin(ang) * r0
        x1 = lerp(x0, a.tx, grow * 0.9)
        y1 = lerp(y0, a.ty, grow * 0.9)
        a.line(x0, y0, x1, y1, ICE[1], al, 3)
        for k in range(1, 4):
            f = k / 4 * grow * 0.9
            bx, by = lerp(x0, a.tx, f), lerp(y0, a.ty, f)
            for sgn in (-1, 1):
                ba = ang + math.pi + sgn * 0.7
                a.line(bx, by, bx + math.cos(ba) * 14 * a.s, by + math.sin(ba) * 14 * a.s, ICE[0], al, 2)
    a.ellipse(a.tx, a.ty, 150 * a.s, 140 * a.s, ICE[2], 45 * grow * fade_late(t, 0.75))
    _impact(a, seg(t, 0.6, 1.0), ICE, 0.8)


# ─────────────────────────────────────────────────────────────────────────────
# ANCIENT
# ─────────────────────────────────────────────────────────────────────────────

def _bone(a, x, y, length, ang, col, alpha):
    ca, sa = math.cos(ang), math.sin(ang)
    x1, y1 = x - ca * length / 2, y - sa * length / 2
    x2, y2 = x + ca * length / 2, y + sa * length / 2
    a.line(x1, y1, x2, y2, col, alpha, max(2, int(length * 0.18)))
    k = length * 0.13
    for ex, ey in ((x1, y1), (x2, y2)):
        a.circle(ex - sa * k, ey + ca * k, k, col, alpha)
        a.circle(ex + sa * k, ey - ca * k, k, col, alpha)


def anim_fossil_break(a):
    t = a.t
    bone = (235, 225, 200)
    p = seg(t, 0.0, 0.4)
    if p is not None:
        _bone(a, a.tx, a.ty - 80 * a.s * (1 - ease_in(p)), 60 * a.s, 0.5 + p * 3, bone, 255)
    p = seg(t, 0.38, 1.0)
    if p is not None:  # bone snaps in two and flies apart
        e = ease_out(p)
        al = 255 * (1 - p)
        _bone(a, a.tx - 30 * a.s * e, a.ty + 40 * a.s * p * p, 28 * a.s, 0.5 - e * 2, bone, al)
        _bone(a, a.tx + 30 * a.s * e, a.ty + 40 * a.s * p * p, 28 * a.s, 0.5 + e * 2, bone, al)
        a.burst(a.tx, a.ty, p, 12, 60 * a.s, ANCIENT[1], 3 * a.s, shape='square')
        a.star(a.tx, a.ty, 30 * a.s * (1 - p), WHITE, 230 * (1 - p), points=5)


def anim_raging_pursuit(a):
    t = a.t
    for k in range(4):  # afterimage strikes from alternating sides
        p = seg(t, k * 0.17, 0.35 + k * 0.17)
        if p is not None:
            side = 1 if k % 2 else -1
            ang = math.pi * (0.3 if side > 0 else 0.7)
            a.slash(a.tx + side * 15 * a.s, a.ty, ang, 110 * a.s, p, ANCIENT[0], 7, curve=0.1)
            a.circle(a.tx + side * 70 * a.s * (1 - p), a.ty, 20 * a.s, ANCIENT[2], 120 * (1 - p))
    _impact(a, seg(t, 0.68, 1.0), ANCIENT, 1.0)


def anim_dragon_zenith(a):
    t = a.t
    gold, ember = ANCIENT[1], MAGMA[0]
    top_y = a.ty - 230 * a.s

    def dragon(head_u, tail_len, path):
        """Draw a serpentine body of circles trailing behind head_u along path(u)."""
        for i in range(18, -1, -1):
            u = head_u - i * tail_len / 18
            if u < 0:
                continue
            x, y = path(u)
            r = (14 - i * 0.55) * a.s
            a.circle(x, y, r, ember if i % 3 else gold, 240)
            a.glow(x, y, r * 2.2, ember, 0.5)
        hx, hy = path(head_u)
        a.circle(hx, hy, 16 * a.s, gold, 255)
        a.circle(hx + 5 * a.s, hy - 4 * a.s, 3 * a.s, (255, 40, 20), 255)
        a.glow(hx, hy, 40 * a.s, gold, 1.0)

    # 1. Dragon of flame spirals up from the attacker into the sky
    p = seg(t, 0.0, 0.42)
    if p is not None:
        def rise(u):
            return (a.sx + math.sin(u * 10) * 40 * a.s * (1 - u * 0.5),
                    lerp(a.sy, top_y, u))
        dragon(ease_out(p), 0.45, rise)
        a.tint((40, 15, 0), 120 * p)
    # 2. Zenith: it dives down onto the target
    p = seg(t, 0.38, 0.62)
    if p is not None:
        def dive(u):
            return (lerp(a.sx, a.tx, u) + math.sin(u * 8) * 25 * a.s, lerp(top_y, a.ty, u * u))
        dragon(ease_in(p), 0.4, dive)
        a.tint((40, 15, 0), 120)
    # 3. Pillar of golden fire + rings
    p = seg(t, 0.58, 1.0)
    if p is not None:
        w = 60 * a.s * hump(min(1, p * 1.4))
        a.poly([(a.tx - w, 0), (a.tx + w, 0), (a.tx + w * 1.2, a.ty + 50 * a.s), (a.tx - w * 1.2, a.ty + 50 * a.s)],
               ember, 200)
        a.poly([(a.tx - w * 0.4, 0), (a.tx + w * 0.4, 0), (a.tx + w * 0.5, a.ty + 50 * a.s),
                (a.tx - w * 0.5, a.ty + 50 * a.s)], gold, 230)
        for i in range(6):
            a.glow(a.tx, lerp(0, a.ty, i / 5), w * 2, ember, 0.9)
        for k in range(3):
            q = seg(p, k * 0.12, 0.7 + k * 0.1)
            if q is not None:
                a.ellipse(a.tx, a.ty + 40 * a.s, 60 * a.s + 300 * a.s * ease_out(q),
                          20 * a.s + 80 * a.s * ease_out(q), gold, 230 * (1 - q), 5 - k)
        a.burst(a.tx, a.ty, p, 40, 190 * a.s, gold, 5 * a.s, glow=0.5, gravity=-60)
        _strong_finish(a, p, (gold, (255, 240, 200)), 220, 15)


def anim_archaic_aura(a):
    t = a.t
    gold = ANCIENT[1]
    cx, cy = a.tx, a.ty + 40 * a.s
    # 1. Ancient rune circle draws itself under the target
    p = seg(t, 0.0, 0.5)
    circ = ease_out(min(1, t / 0.45))
    al = 240 * fade_late(t, 0.85)
    R = 95 * a.s
    pts = [(cx + math.cos(i / 40 * TAU * circ) * R, cy + math.sin(i / 40 * TAU * circ) * R * 0.32)
           for i in range(41)]
    a.lines(pts, gold, al, 3)
    pts2 = [(cx + math.cos(i / 40 * TAU * circ) * R * 0.7, cy + math.sin(i / 40 * TAU * circ) * R * 0.22)
            for i in range(41)]
    a.lines(pts2, ANCIENT[0], al, 2)
    for i in range(8):  # rotating glyphs
        ang = i * TAU / 8 + t * 2.5
        gx, gy = cx + math.cos(ang) * R * 0.85, cy + math.sin(ang) * R * 0.27
        if i / 8 <= circ:
            a.lines([(gx - 5 * a.s, gy - 4 * a.s), (gx, gy + 4 * a.s), (gx + 5 * a.s, gy - 4 * a.s)], gold, al, 2)
    if p is not None:
        a.tint((30, 20, 0), 120 * p)
    # 2. Pillars of light rise from the circle
    p = seg(t, 0.35, 0.85)
    if p is not None:
        for i in range(6):
            ang = i * TAU / 6 + 0.3
            px, py = cx + math.cos(ang) * R * 0.85, cy + math.sin(ang) * R * 0.27
            h = 170 * a.s * ease_out(min(1, p * 2))
            w = 8 * a.s * hump(p)
            a.poly([(px - w, py), (px + w, py), (px + w * 0.4, py - h), (px - w * 0.4, py - h)], gold, 200)
            a.glow(px, py - h * 0.5, w * 4, ANCIENT[0], 0.7)
        a.implode(a.tx, a.ty, p, 24, 120 * a.s, gold, 3 * a.s, glow=0.4, swirl=2)
        a.tint((30, 20, 0), 120)
    # 3. Ancient power erupts
    p = seg(t, 0.75, 1.0)
    if p is not None:
        a.ring(a.tx, a.ty, 20 * a.s + 150 * a.s * ease_out(p), gold, 240 * (1 - p), 5)
        a.burst(a.tx, a.ty, p, 26, 150 * a.s, gold, 4 * a.s, shape='star', glow=0.5)
        a.glow(a.tx, a.ty, 110 * a.s, ANCIENT[0], 1.5 * (1 - p))
        _strong_finish(a, p, (gold, (255, 240, 190)), 180, 10)


def anim_primal_rage(a):
    t = a.t
    red = (230, 60, 30)
    p = seg(t, 0.0, 0.35)
    if p is not None:  # roar shockwaves from the attacker
        for k in range(3):
            q = seg(p, k * 0.2, 0.6 + k * 0.2)
            if q is not None:
                a.ring(a.sx, a.sy, 20 * a.s + 60 * a.s * q, red, 230 * (1 - q), 3)
    p = seg(t, 0.25, 0.65)
    if p is not None:
        for k in range(3):
            x, y = a.travel(ease_in(max(0, p - k * 0.1)))
            a.ellipse(x, y, 30 * a.s, 60 * a.s, red, 200 - k * 50, 4)
    p = seg(t, 0.6, 1.0)
    if p is not None:
        a.star(a.tx, a.ty, 55 * a.s * ease_out(p), red, 240 * (1 - p), points=7, rot=0.4, inner=0.45)
        a.glow(a.tx, a.ty, 60 * a.s, red, 1.2 * (1 - p))
        if p < 0.3:
            a.shake(4)


def anim_arise(a):
    t = a.t
    al = fade_late(t, 0.7)
    for i in range(7):  # golden rays rise from below
        x = a.tx + (i - 3) * 22 * a.s
        h = 160 * a.s * ease_out(min(1, t * 2 - i * 0.05)) if t * 2 > i * 0.05 else 0
        a.line(x, a.ty + 60 * a.s, x, a.ty + 60 * a.s - h, ANCIENT[1], 200 * al, 4)
        a.glow(x, a.ty + 60 * a.s - h, 14 * a.s, ANCIENT[1], 0.6 * al)
    a.burst(a.tx, a.ty + 50 * a.s, t, 20, 140 * a.s, ANCIENT[1], 3 * a.s,
            spread=(-math.pi * 0.65, -math.pi * 0.35), glow=0.3)
    a.glow(a.tx, a.ty, 80 * a.s, ANCIENT[0], 0.8 * hump(t))


def anim_venom_decay(a):
    t = a.t
    rng = a.rng('venom')
    for i in range(10):  # poison drips fall onto the target
        x = a.tx + rng.uniform(-60, 60) * a.s
        d = rng.uniform(0, 0.4)
        q = (t - d) / 0.35
        if 0 <= q <= 1:
            y = lerp(a.ty - 100 * a.s, a.ty + rng.uniform(-20, 30) * a.s, ease_in(q))
            a.circle(x, y, 5 * a.s, POISON[1], 240)
            a.poly([(x - 5 * a.s, y), (x + 5 * a.s, y), (x, y - 12 * a.s)], POISON[1], 240)
    p = seg(t, 0.35, 1.0)
    if p is not None:  # target dissolves in sizzling purple bubbles
        for i in range(14):
            x = a.tx + rng.uniform(-55, 55) * a.s
            d = rng.uniform(0, 0.5)
            q = (p - d) / 0.5
            if 0 <= q <= 1:
                a.ring(x, a.ty + 30 * a.s - q * 70 * a.s, (3 + 6 * q) * a.s, POISON[0], 230 * (1 - q), 2)
        a.ellipse(a.tx, a.ty, 130 * a.s, 120 * a.s, POISON[2], 55 * hump(p))


def anim_rushdown(a):
    t = a.t
    rng = a.rng('rush')
    for k in range(5):  # flurry of dashes from every direction
        p = seg(t, k * 0.11, 0.3 + k * 0.11)
        if p is not None:
            ang = rng.uniform(0, TAU)
            r = 110 * a.s * (1 - ease_in(p))
            x, y = a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r
            a.line(x, y, x + math.cos(ang) * 50 * a.s, y + math.sin(ang) * 50 * a.s, ANCIENT[1], 230, 4)
            if p > 0.8:
                a.star(a.tx + math.cos(ang) * 15, a.ty + math.sin(ang) * 15, 22 * a.s, WHITE, 240, points=5)
        else:
            rng.uniform(0, TAU)  # keep the rng sequence stable
    _impact(a, seg(t, 0.65, 1.0), ANCIENT, 0.9)


def anim_ancient_mend(a):
    t = a.t
    green = (120, 255, 150)
    rng = a.rng('mend')
    for _ in range(14):  # rising plus signs and sparkles
        x = a.tx + rng.uniform(-60, 60) * a.s
        d = rng.uniform(0, 0.5)
        q = (t - d) / 0.5
        if 0 <= q <= 1:
            y = a.ty + 50 * a.s - q * 110 * a.s
            sz = 6 * a.s
            al = 240 * hump(q)
            col = green if rng.random() < 0.6 else ANCIENT[1]
            a.line(x - sz, y, x + sz, y, col, al, 3)
            a.line(x, y - sz, x, y + sz, col, al, 3)
            a.glow(x, y, 12 * a.s, col, 0.5 * hump(q))
    a.glow(a.tx, a.ty, 70 * a.s, green, 0.8 * hump(t))


# ─────────────────────────────────────────────────────────────────────────────
# Registry + fallback
# ─────────────────────────────────────────────────────────────────────────────

ANIMATIONS = {
    # Aqua
    'Whirlpool': anim_whirlpool,
    'Whirlpool+': anim_whirlpool_plus,
    'Hurricane': anim_hurricane,
    'Eternal Blue': anim_eternal_blue,
    'Wave Dash': anim_wave_dash,
    # Magma
    'Fireball': anim_fireball,
    'Fireball+': anim_fireball_plus,
    'Lava Burst': anim_lava_burst,
    'Solar Flare': anim_solar_flare,
    'Flame Shatter': anim_flame_shatter,
    'Magma Boost': anim_magma_boost,
    # Earth
    'Log Roll': anim_log_roll,
    'Vine Snare': anim_vine_snare,
    'Vine Snare+': anim_vine_snare_plus,
    'Dread Thorn': anim_dread_thorn,
    'Tree Spin': anim_tree_spin,
    'Poison Ivy': anim_poison_ivy,
    'Synthesis': anim_synthesis,
    'Terraform': anim_terraform,
    'Floral Resonance': anim_floral_resonance,
    # Flying
    'Swift Sneak': anim_swift_sneak,
    'Air Strike': anim_air_strike,
    'Mach Speed': anim_mach_speed,
    'Wind Fracture': anim_wind_fracture,
    'Turbo Booster': anim_turbo_booster,
    'Sky Scorch': anim_sky_scorch,
    # Spike
    'Lock Jaw': anim_lock_jaw,
    'Horn Tackle': anim_horn_tackle,
    'Double Jab': anim_double_jab,
    'Ripping Impact': anim_ripping_impact,
    'Power Fang': anim_power_fang,
    'Sword Slash': anim_sword_slash,
    'Quick Slash': anim_quick_slash,
    'Spike Storm': anim_spike_storm,
    # Rock
    'Dust Beam': anim_dust_beam,
    'Boulder Smash': anim_boulder_smash,
    'Crusher': anim_crusher,
    'Sand Kick': anim_sand_kick,
    'Iron Core': anim_iron_core,
    'Momentum': anim_momentum,
    'Crash Impact': anim_crash_impact,
    'Sand Storm': anim_sand_storm,
    # Lightning
    'Stinger Shock': anim_stinger_shock,
    'Static Graze': anim_static_graze,
    'Thunder Blitz': anim_thunder_blitz,
    'Lightning Bolt': anim_lightning_bolt,
    'Volt Storm': anim_volt_storm,
    'Conduit Surge': anim_conduit_surge,
    'Quantum Flux': anim_quantum_flux,
    'Shock': anim_shock,
    # Dark
    'Force Shift': anim_force_shift,
    'Dark Energy': anim_dark_energy,
    'Void Collapse': anim_void_collapse,
    'Bitemark': anim_bitemark,
    'Distortion': anim_distortion,
    'Fear': anim_fear,
    'Haunt': anim_haunt,
    'Binding Curse': anim_binding_curse,
    'Shadow Veil': anim_shadow_veil,
    # Light
    'Prism Glare': anim_prism_glare,
    'Piercing Light': anim_piercing_light,
    'Spectral Overload': anim_spectral_overload,
    'Flash': anim_flash,
    'Refraction': anim_refraction,
    'Gamma Wave': anim_gamma_wave,
    'Ultra Violet': anim_ultra_violet,
    # Ice
    'Snowfall': anim_snowfall,
    'Freeze Blast': anim_freeze_blast,
    'Hyperfrost': anim_hyperfrost,
    'Hail Storm': anim_hail_storm,
    'Frozen Aura': anim_frozen_aura,
    'Deep Freeze': anim_deep_freeze,
    # Ancient
    'Fossil Break': anim_fossil_break,
    'Raging Pursuit': anim_raging_pursuit,
    'Dragon Zenith': anim_dragon_zenith,
    'Archaic Aura': anim_archaic_aura,
    'Primal Rage': anim_primal_rage,
    'Arise': anim_arise,
    'Venom Decay': anim_venom_decay,
    'Rushdown': anim_rushdown,
    'Ancient Mend': anim_ancient_mend,
}


def _make_fallback(mtype):
    """Generic type-colored hit for any move added later without its own animation."""
    pal = TYPE_PALETTES.get(mtype, SPIKE)

    def anim(a):
        _impact(a, a.t, pal, 1.0, n=14)
    return anim


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

class MoveAnimation:
    """One playing move animation. Positions are screen-space (config.WIDTH x HEIGHT)."""

    def __init__(self, move_name, target, source=None, scale=1.0):
        md = MOVE_DATA.get(move_name, {})
        self.move_name = move_name
        self.fn = ANIMATIONS.get(move_name) or _make_fallback(md.get('type'))
        self.strong = md.get('damage', 0) >= STRONG_POWER
        self.target = target
        self.source = source or target
        self.scale = scale
        self.duration = DURATIONS.get(move_name, DURATION)
        self.timer = 0.0
        self.seed = random.randrange(1 << 20)
        self.size = (config.WIDTH, config.HEIGHT)
        self.layer = pygame.Surface(self.size, pygame.SRCALPHA)
        self.glow = pygame.Surface(self.size)
        self.tint_surf = pygame.Surface(self.size)
        self.tint = None
        self.shake_px = 0

    @property
    def done(self):
        return self.timer >= self.duration

    def update(self, dt):
        self.timer += dt

    def draw(self, screen):
        if self.done:
            return
        t = min(1.0, self.timer / self.duration)
        self.layer.fill((0, 0, 0, 0))
        self.glow.fill(BLACK)
        self.tint = None
        self.shake_px = 0

        self.fn(_Frame(self, t))

        if self.tint:
            col, alpha = self.tint
            self.tint_surf.fill(col)
            self.tint_surf.set_alpha(alpha)
            screen.blit(self.tint_surf, (0, 0))
        screen.blit(self.layer, (0, 0))
        screen.blit(self.glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if self.shake_px > 0:
            screen.scroll(random.randint(-self.shake_px, self.shake_px),
                          random.randint(-self.shake_px, self.shake_px))

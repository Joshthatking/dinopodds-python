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
DURATIONS = {                       # signature moves that run longer than DURATION
    'Ultra Violet': 2.2,
    'Eternal Darkness': 2.6,
    'Infinite Light': 3.4,
    'Leaf Ultima': 1.4,
    'Crusher': 1.3,
    'Power Fang': 1.3,
    'Dread Thorn': 1.4,
    'Venom Decay': 1.3,
    'Fossil Break': 1.2,
    'Flame Shatter': 1.3,
    'Raging Pursuit': 1.4,
    'Temporal Pincer': 1.3,
    'Temporal Pincer (return)': 1.5,     # the end-of-next-turn second hit (game._land_return_hit)
    'Dust Devil': 1.3,
    'Dust Devil (return)': 1.4,
}
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


def ease_in_out(p):
    return p * p * (3 - 2 * p)


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
    al = 230 * fade_late(t, 0.7)
    rot = t * TAU * 3
    base = a.ty + 55 * a.s
    rise = ease_out(min(1, t / 0.3))          # funnel grows up from the ground
    storm_gray = (95, 110, 135)
    a.tint(AQUA[2], 45 * hump(t))
    a.shake(2.5 * hump(seg(t, 0.2, 0.85) or 0))
    # storm cloud cap gathering above the funnel
    for i in range(5):
        cx = a.tx + (i - 2) * 26 * a.s + math.sin(t * 4 + i) * 4
        cy = a.ty - 95 * a.s - abs(i - 2) * 4 * a.s
        a.ellipse(cx, cy, 60 * a.s * rise, 30 * a.s * rise, storm_gray, 200 * fade_late(t, 0.75))
    a.glow(a.tx, a.ty - 95 * a.s, 60 * a.s, AQUA[2], 0.5 * hump(t))
    # funnel bands: wider toward the top, wobbling as they spin
    for k in range(7):
        if k > 6 * rise:
            break
        y = base - k * 22 * a.s
        w = (22 + k * 14) * a.s
        wob = math.sin(rot + k * 0.9) * 8 * a.s
        a.ellipse(a.tx + wob, y, w * 2, w * 0.45, FLYING[2] if k % 2 else AQUA[1], al * 0.75, 2)
    # spiral wind streaks climbing the funnel
    for arm in range(3):
        pts = []
        for i in range(16):
            u = i / 15
            if u > rise:
                break
            ang = rot * 1.4 + arm * TAU / 3 + u * 5.0
            w = (22 + u * 6 * 14) * a.s
            pts.append((a.tx + math.sin(rot + u * 5.4) * 8 * a.s + math.cos(ang) * w,
                        base - u * 132 * a.s + math.sin(ang) * w * 0.22))
        a.lines(pts, WHITE, al * 0.85, 2)
    # water and debris caught in the vortex (brighter in front, dimmer behind)
    rng = a.rng('hurricane')
    for _ in range(22):
        h = rng.uniform(0, 1)
        ph = rng.uniform(0, TAU)
        ang = rot * 1.6 + ph
        r = (22 + h * 84) * a.s
        y = base - ((h + t * 0.6) % 1.0) * 132 * a.s * rise
        front = math.sin(ang) > 0
        a.circle(a.tx + math.cos(ang) * r, y + math.sin(ang) * r * 0.22,
                 (3.5 if front else 2) * a.s, AQUA[1] if front else AQUA[0], al if front else al * 0.5)
    a.glow(a.tx, a.ty, 70 * a.s, AQUA[0], 0.5 * hump(t))
    a.rain(t, 46, AQUA[0], a.tx - 120 * a.s, a.tx + 120 * a.s, a.ty - 120 * a.s, a.ty + 70 * a.s,
           length=16, slant=0.4, key=1, speed=1.4)
    # funnel breaks apart into a spray
    p = seg(t, 0.75, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 20, 120 * a.s, AQUA[1], 4 * a.s, gravity=90, glow=0.3, key=2)
        a.ring(a.tx, base - 20 * a.s, 30 * a.s + 90 * a.s * ease_out(p), FLYING[1], 180 * (1 - p), 3)


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


def _snap_sword(a, x, y, size, p):
    """Attack-down cue: a sword that snaps in half and falls over p 0..1."""
    al = 240 * min(1.0, p * 4) * (1.0 if p < 0.6 else max(0.0, (1 - p) / 0.4))
    brk = ease_in(max(0.0, (p - 0.35) / 0.65))
    steel, edge = (215, 220, 235), (255, 255, 255)
    # hilt half (bottom) tips left, blade half (top) tips right as it breaks
    for half, sgn in ((0, -1), (1, 1)):
        ang = -math.pi / 2 + sgn * 0.7 * brk
        cx = x + sgn * 10 * a.s * brk
        cy = y + 14 * a.s * brk * brk
        ca, sa = math.cos(ang), math.sin(ang)
        if half == 0:   # grip + crossguard + lower blade
            a.line(cx, cy, cx - ca * size * 0.45, cy - sa * size * 0.45, (120, 70, 40), al, 5)
            a.line(cx - sa * 12 * a.s, cy + ca * 12 * a.s, cx + sa * 12 * a.s, cy - ca * 12 * a.s,
                   (230, 190, 90), al, 5)
            a.line(cx, cy, cx + ca * size * 0.35, cy + sa * size * 0.35, steel, al, 7)
        else:           # upper blade + point
            bx, by = cx + ca * size * 0.4, cy + sa * size * 0.4
            tip = (bx + ca * size * 0.55, by + sa * size * 0.55)
            a.poly([(bx - sa * 3.5 * a.s, by + ca * 3.5 * a.s), (bx + sa * 3.5 * a.s, by - ca * 3.5 * a.s), tip],
                   steel, al)
            a.line(bx, by, tip[0], tip[1], edge, al, 1)
    if 0.3 < p < 0.55:   # spark where it snaps
        a.star(x, y - size * 0.38, 12 * a.s, MAGMA[1], 255, points=4, rot=p * 5)


def anim_flame_shatter(a):
    t = a.t
    s = a.s
    R = 58 * s
    n = 9
    rng = a.rng('fs_facets')
    facet = [(i / n * TAU + rng.uniform(-0.12, 0.12), R * rng.uniform(0.85, 1.1)) for i in range(n)]
    # 1. Molten crystal shards fly in and lock together into a shell
    p = seg(t, 0.0, 0.32)
    if p is not None:
        e = ease_in(p)
        for i, (ang, r) in enumerate(facet):
            d = r + 120 * s * (1 - e)
            spin = (1 - e) * 2.5 * (1 if i % 2 else -1)
            a.shard(a.tx + math.cos(ang) * d, a.ty + math.sin(ang) * d, 20 * s, ang + math.pi + spin,
                    MAGMA[0], 240)
            a.shard(a.tx + math.cos(ang) * d, a.ty + math.sin(ang) * d, 12 * s, ang + math.pi + spin,
                    MAGMA[1], 240, thin=0.18)
        a.tint((40, 10, 0), 90 * p)
    # 2. The finished shell glows hotter and hotter, cracking white
    p = seg(t, 0.3, 0.52)
    if p is not None:
        heat = ease_in(p)
        pts = [(a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r) for ang, r in facet]
        a.poly(pts, _mix(MAGMA[2], MAGMA[0], heat), 170)
        for (x1, y1) in pts:   # facet edges back to the core
            a.line(x1, y1, a.tx, a.ty, MAGMA[1], 160 + 80 * heat, 2)
        a.lines(pts, MAGMA[1], 255, 3, closed=True)
        rng = a.rng('fs_cracks')
        for k in range(int(2 + 8 * heat)):
            ang = rng.uniform(0, TAU)
            r = R * rng.uniform(0.3, 1.0)
            a.line(a.tx, a.ty, a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r, (255, 250, 220), 255, 2)
        a.glow(a.tx, a.ty, 70 * s * (1 + heat), MAGMA[0], 0.6 + heat)
        a.tint((60, 15, 0), 90 + 60 * heat)
        a.shake(1 + 3 * heat)
    # 3. SHATTER: spinning molten shards, fire ring, ember rain
    p = seg(t, 0.5, 1.0)
    if p is not None:
        e = ease_out(p)
        _strong_finish(a, p, ((255, 120, 30), (255, 170, 90)), 120, 11)
        a.glow(a.tx, a.ty, 110 * s, MAGMA[0], 0.9 * (1 - p))
        a.circle(a.tx, a.ty, 70 * s * e, MAGMA[0], 150 * (1 - p) ** 2)
        a.ring(a.tx, a.ty, 20 * s + 140 * s * e, MAGMA[0], 230 * (1 - p), 6)
        a.ring(a.tx, a.ty, 10 * s + 95 * s * e, (255, 240, 200), 210 * (1 - p), 3)
        for i, (ang, r) in enumerate(facet):   # the shell's facets blown outward
            d = r + 150 * s * e
            x, y = a.tx + math.cos(ang) * d, a.ty + math.sin(ang) * d + 60 * s * p * p
            spin = ang + p * 9 * (1 if i % 2 else -1)
            a.shard(x, y, 22 * s * (1 - 0.4 * p), spin, MAGMA[0], 255 * (1 - p))
            a.shard(x, y, 13 * s * (1 - 0.4 * p), spin, (255, 245, 210), 255 * (1 - p), thin=0.18)
            a.glow(x, y, 14 * s, MAGMA[0], 0.5 * (1 - p))
        a.burst(a.tx, a.ty, p, 26, 160 * s, MAGMA[1], 4 * s, gravity=140, glow=0.4)
        a.burst(a.tx, a.ty, p, 14, 120 * s, MAGMA[2], 5 * s, shape='square', gravity=180, key=1)
        _snap_sword(a, a.tx, a.ty - 8 * s, 70 * s, p)


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


_DT_BODY = (22, 12, 28)       # near-black thorn
_DT_EDGE = (130, 35, 95)      # dark magenta edge light
_DT_ROOT = (16, 26, 14)       # dark mossy base
_DT_GLOW = (150, 40, 170)


def _thorn(a, bx, by, tipx, tipy, bend, w, alpha, barbs=True):
    """Curved, tapering thorn from base (bx, by) to its tip, bowed sideways by
    `bend` px, with a magenta edge light and a few barbs along the outside."""
    if alpha <= 0:
        return
    dx, dy = tipx - bx, tipy - by
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    cx, cy = bx + dx * 0.5 + nx * bend, by + dy * 0.5 + ny * bend
    left, right, spine = [], [], []
    n = 12
    for i in range(n + 1):
        u = i / n
        px = (1 - u) ** 2 * bx + 2 * (1 - u) * u * cx + u * u * tipx
        py = (1 - u) ** 2 * by + 2 * (1 - u) * u * cy + u * u * tipy
        hw = w * (1 - u) ** 1.3
        left.append((px + nx * hw, py + ny * hw))
        right.append((px - nx * hw, py - ny * hw))
        spine.append((px, py))
    a.poly(left + right[::-1], _DT_BODY, alpha)
    a.lines(left, _DT_EDGE, alpha, 2)
    a.circle(bx, by, w * 0.6, _DT_ROOT, alpha)
    if barbs:
        side = 1 if bend >= 0 else -1
        for k in (3, 6, 9):
            px, py = spine[k]
            hw = w * (1 - k / n) ** 1.3
            ox, oy = px + nx * hw * side, py + ny * hw * side
            ux, uy = (spine[k + 1][0] - px), (spine[k + 1][1] - py)
            a.poly([(ox, oy), (ox + nx * side * w * 0.9 + ux * 0.8, oy + ny * side * w * 0.9 + uy * 0.8),
                    (ox + ux * 0.9, oy + uy * 0.9)], _DT_BODY, alpha)


def anim_dread_thorn(a):
    t = a.t
    s = a.s
    base = a.ty + 50 * s
    # 1. The ground splits beneath the target and dark energy seeps out
    p = seg(t, 0.0, 0.3)
    if p is not None or t > 0.3:
        e = ease_out(p) if p is not None else 1.0
        crack_al = 230 * fade_late(t, 0.75)
        rng = a.rng('dt_cracks')
        for k in range(7):
            ang = math.pi * (0.05 + 0.9 * k / 6)
            pts = [(a.tx, base)]
            for m in range(1, 5):
                d = 95 * s * e * m / 4
                pts.append((a.tx - math.cos(ang) * d + rng.uniform(-6, 6) * s,
                            base + math.sin(ang) * d * 0.22 + rng.uniform(-3, 3) * s))
            a.lines(pts, (10, 4, 14), crack_al, 4)
            a.lines(pts, _DT_GLOW, crack_al * 0.8, 1)
        a.ellipse(a.tx, base, 220 * s * e, 46 * s * e, (20, 6, 28), 150 * fade_late(t, 0.7))
        a.glow(a.tx, base, 90 * s * e, _DT_GLOW, 0.9 * hump(min(1.0, t / 0.6)))
        a.tint((20, 0, 25), 130 * min(1.0, t / 0.3) * fade_late(t, 0.8))
        if p is not None:
            a.shake(2 * p)

    # 2. A ring of curved thorns erupts and lunges inward at the target
    spots = (-105, -70, -36, 0, 36, 70, 105)
    impale = seg(t, 0.42, 0.55)
    wither = seg(t, 0.72, 1.0)
    for i, off in enumerate(spots):
        q = seg(t, 0.2 + i * 0.025, 0.42 + i * 0.025)
        if t < 0.2 + i * 0.025:
            continue
        grow = ease_out(q) if q is not None else 1.0
        bx = a.tx + off * s
        by = base + abs(off) * 0.08 * s
        h = (95 + (3 - abs(i - 3)) * 22) * s   # tallest in the middle
        rest_x, rest_y = bx + off * 0.15 * s, by - h
        hit_x, hit_y = a.tx - off * 0.3 * s, a.ty - 42 * s + abs(off) * 0.12 * s   # tips cross over the target
        k = ease_in(impale) if impale is not None else (1.0 if t >= 0.55 else 0.0)
        tipx, tipy = lerp(rest_x, hit_x, k), lerp(rest_y, hit_y, k)
        tipx, tipy = lerp(bx, tipx, grow), lerp(by, tipy, grow)
        if wither is not None:   # droop and sink back into the ground
            tipy += 40 * s * ease_in(wither)
        al = 255 * (1 - ease_in(wither) if wither is not None else 1.0)
        bend = (-18 if off < 0 else 18) * s if off else 10 * s
        _thorn(a, bx, by, tipx, tipy, bend, (13 + (3 - abs(i - 3)) * 1.5) * s, al)
        if q is not None and q < 0.4:   # dirt kicked up as each thorn bursts out
            a.burst(bx, by, q / 0.4, 5, 30 * s, (60, 40, 30), 3 * s, gravity=90, key=i)

    # 3. IMPALE: blood-red burst, dark petals, shockwave
    p = seg(t, 0.52, 1.0)
    if p is not None:
        _strong_finish(a, p, ((90, 0, 30), (150, 20, 60)), 120, 10)
        e = ease_out(p)
        a.glow(a.tx, a.ty, 100 * s, (170, 20, 60), 1.0 * (1 - p))
        a.ring(a.tx, a.ty, 15 * s + 120 * s * e, (220, 60, 120), 220 * (1 - p), 4)
        a.ring(a.tx, a.ty, 10 * s + 75 * s * e, _DT_GLOW, 200 * (1 - p), 3)
        a.star(a.tx, a.ty, 70 * s * (1 - p * 0.6), (200, 25, 70), 255 * (1 - p), points=6, rot=0.3, inner=0.25)
        a.star(a.tx, a.ty, 30 * s * (1 - p * 0.6), (255, 220, 235), 255 * (1 - p), points=6, rot=0.3, inner=0.3)
        rng = a.rng('dt_petals')
        for k in range(16):   # dark thorn shards / petals flung outward
            ang = rng.uniform(0, TAU)
            d = rng.uniform(40, 130) * s * e
            a.shard(a.tx + math.cos(ang) * d, a.ty + math.sin(ang) * d + 40 * s * p * p,
                    rng.uniform(7, 12) * s, ang, (90, 20, 60) if k % 2 else _DT_BODY, 255 * (1 - p))
    # 4. The thorns wither into rising dark smoke
    if wither is not None:
        rng = a.rng('dt_smoke')
        for k in range(14):
            x = a.tx + rng.uniform(-110, 110) * s
            d = rng.uniform(0, 0.4)
            q = (wither - d) / 0.6
            if 0 <= q <= 1:
                a.circle(x, base - q * 90 * s, (6 + 10 * q) * s, (40, 15, 50), 150 * (1 - q))


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


def anim_leaf_ultima(a):
    t = a.t
    lime = (200, 255, 120)
    # 1. Gather: leaves spiral into a glowing seed at the attacker
    p = seg(t, 0.0, 0.3)
    if p is not None:
        rng = a.rng('ultima_in')
        for _ in range(16):
            ph = rng.uniform(0, TAU)
            d = rng.uniform(70, 110) * a.s * (1 - ease_in(p))
            ang = ph + p * 4
            a.leaf(a.sx + math.cos(ang) * d, a.sy + math.sin(ang) * d, 7 * a.s, ang + 1.2,
                   EARTH[1], 230 * hump(min(1, p * 1.2)))
        a.circle(a.sx, a.sy, 16 * a.s * ease_out(p), EARTH[0], 230)
        a.circle(a.sx, a.sy, 8 * a.s * ease_out(p), lime, 255)
        a.glow(a.sx, a.sy, 55 * a.s * p, EARTH[1], 1.2)
        a.tint(EARTH[2], 60 * p)
    # 2. Volley: a helix of razor leaves streams to the target
    p = seg(t, 0.25, 0.6)
    if p is not None:
        ang_t = a.angle_to_target()
        nx, ny = -math.sin(ang_t), math.cos(ang_t)
        for i in range(14):
            q = ease_in(max(0.0, min(1.0, p * 1.5 - i * 0.035)))
            if q <= 0 or q >= 1:
                continue
            x, y = a.travel(q, arc=25)
            off = math.sin(q * TAU * 1.5 + i * 1.3) * 22 * a.s
            lx, ly = x + nx * off, y + ny * off
            a.leaf(lx, ly, 10 * a.s, ang_t + q * 9, EARTH[1] if i % 2 else EARTH[0], 245)
            a.glow(lx, ly, 18 * a.s, EARTH[0], 0.5)
        a.tint(EARTH[2], 60)
    # 3. Bloom: a giant leaf flower opens on the target and bursts
    p = seg(t, 0.55, 1.0)
    if p is not None:
        open_k = ease_out(min(1, p / 0.45))
        al = 245 * fade_late(p, 0.55)
        for ring_i, (n, rad, size, col) in enumerate(((8, 60, 22, EARTH[0]), (8, 34, 15, EARTH[1]))):
            for i in range(n):
                ang = i * TAU / n + ring_i * math.pi / n + p * 1.2
                r = rad * a.s * open_k
                a.leaf(a.tx + math.cos(ang) * r, a.ty + math.sin(ang) * r,
                       size * a.s * open_k, ang, col, al)
        a.circle(a.tx, a.ty, 14 * a.s * open_k, lime, al)
        for k in range(3):
            q = seg(p, k * 0.12, 0.55 + k * 0.15)
            if q is not None:
                a.ring(a.tx, a.ty, 20 * a.s + 130 * a.s * ease_out(q), lime, 230 * (1 - q), 5 - k)
        a.burst(a.tx, a.ty, seg(p, 0.3, 1.0), 30, 170 * a.s, EARTH[1], 6 * a.s, shape='shard', glow=0.4)
        a.burst(a.tx, a.ty, seg(p, 0.3, 1.0), 16, 120 * a.s, WHITE, 3 * a.s, shape='star', key=1, gravity=-30)
        a.glow(a.tx, a.ty, 130 * a.s, EARTH[0], 1.4 * (1 - p))
        _strong_finish(a, seg(p, 0.25, 1.0), (EARTH[0], lime), 150, 10)


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


def anim_velo_induction(a):
    """Wind spirals in around the user, it rockets into the foe, then a
    shimmer settles back on the user (its Defense boost)."""
    t = a.t
    # 1) induction: wind streaks spiral inward and spin up around the user
    p = seg(t, 0.0, 0.45)
    if p is not None:
        rng = a.rng('velo_in')
        spin = t * TAU * 3
        for i in range(14):
            base = rng.uniform(0, TAU)
            r = (85 - 50 * ease_in(p)) * a.s * rng.uniform(0.8, 1.1)
            ang = base + spin
            for k in range(4):  # short curved streak trailing behind each gust
                ak = ang - k * 0.12
                x, y = a.sx + math.cos(ak) * r, a.sy + math.sin(ak) * r * 0.6
                a.circle(x, y, (4 - k * 0.7) * a.s, FLYING[1] if k == 0 else FLYING[0], 220 * hump(p) * (1 - k / 4))
        a.ring(a.sx, a.sy, (60 - 30 * p) * a.s, FLYING[2], 160 * hump(p), 2)
        a.glow(a.sx, a.sy, 55 * a.s, FLYING[0], 0.9 * ease_in(p))
    # 2) dash: a wind comet with speed lines shoots to the target
    p = seg(t, 0.42, 0.7)
    if p is not None:
        e = ease_in(p)
        x, y = a.travel(e, arc=20 * a.s)
        ang = a.angle_to_target()
        ca, sa = math.cos(ang), math.sin(ang)
        rng = a.rng('velo_lines')
        for _ in range(9):
            off = rng.uniform(-22, 22) * a.s
            ln = rng.uniform(40, 90) * a.s
            bx, by = x - sa * off - ca * 12 * a.s, y + ca * off - sa * 12 * a.s
            a.line(bx, by, bx - ca * ln, by - sa * ln, FLYING[0], 200 * (1 - p * 0.5), 2)
        a.ellipse(x, y, 34 * a.s, 22 * a.s, FLYING[0], 230)
        a.ellipse(x, y, 18 * a.s, 12 * a.s, WHITE, 255)
        a.glow(x, y, 45 * a.s, FLYING[1], 1.0)
    # 3) impact: concentric wind rings and gust shards burst off the foe
    p = seg(t, 0.68, 1.0)
    if p is not None:
        for k in range(3):
            q = seg(p, k * 0.15, 0.7 + k * 0.1)
            if q is not None:
                a.ellipse(a.tx, a.ty, (30 + 110 * ease_out(q)) * a.s, (18 + 55 * ease_out(q)) * a.s,
                          FLYING[1] if k == 0 else FLYING[0], 220 * (1 - q), 3)
        a.burst(a.tx, a.ty, p, 14, 80 * a.s, FLYING[1], 4 * a.s, shape='streak', key='velo_hit')
        a.glow(a.tx, a.ty, 60 * a.s, FLYING[0], 1.1 * (1 - p))
        if p < 0.4:
            a.shake(5 * (1 - p / 0.4))
    # 4) induced barrier: a faint hexagon shell shimmers onto the user
    p = seg(t, 0.75, 1.0)
    if p is not None:
        al = 200 * hump(p)
        R = 55 * a.s
        pts = [(a.sx + math.cos(i * TAU / 6 + 0.5) * R, a.sy + math.sin(i * TAU / 6 + 0.5) * R) for i in range(6)]
        a.lines(pts, FLYING[2], al, 3, closed=True)
        a.lines(pts, WHITE, al * 0.8, 1, closed=True)
        a.glow(a.sx, a.sy, 50 * a.s, FLYING[2], 0.6 * hump(p))


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


_PF_GUM = (130, 25, 40)
_PF_FANGS = (0.22, 0.78)   # canine positions along the jaw (0..1)


def _pf_jaw(a, cx, row, sgn, w, alpha, gleam=0.0):
    """One curved jaw (sgn=1 upper, -1 lower): gum band with teeth pointing
    toward the mouth's center and two big canines. Returns the canine tips."""
    s = a.s
    edge = []
    for i in range(17):
        u = i / 16
        edge.append((cx + (u - 0.5) * w, row + sgn * 16 * s * (2 * u - 1) ** 2))
    back = [(x, y - sgn * 16 * s) for x, y in reversed(edge)]
    a.poly(edge + back, _PF_GUM, alpha * 0.9)
    a.lines(edge, (70, 10, 20), alpha, 3)
    tips = []
    n = 8
    for i in range(n):
        u = (i + 0.5) / n
        x = cx + (u - 0.5) * w
        y = row + sgn * 16 * s * (2 * u - 1) ** 2
        half = w / n * 0.42
        a.poly([(x - half, y), (x + half, y), (x, y + sgn * 15 * s)], (235, 232, 225), alpha)
    for u in _PF_FANGS:
        x = cx + (u - 0.5) * w
        y = row + sgn * 16 * s * (2 * u - 1) ** 2
        tip = (x + (0.5 - u) * 10 * s, y + sgn * 46 * s)
        body = [(x - 12 * s, y), (x + 12 * s, y), tip]
        a.poly(body, WHITE, alpha)
        a.poly(body, SPIKE[2], alpha * 0.8, 2)
        a.line(x - 4 * s, y + sgn * 4 * s, tip[0], tip[1] - sgn * 6 * s, (255, 255, 255), alpha * 0.6, 2)
        if gleam > 0:
            a.star(tip[0], tip[1], 14 * s * gleam, WHITE, 255 * gleam, points=4, rot=0.3)
            a.glow(tip[0], tip[1], 22 * s, WHITE, 0.9 * gleam)
        tips.append(tip)
    return tips


def anim_power_fang(a):
    t = a.t
    s = a.s
    w = 150 * s
    # Gap between the jaws over time: open + wind up wider, then a fast snap
    # (kept small enough that the jaws stay on screen for both battle slots)
    if t < 0.3:
        gap = lerp(48, 62, ease_out(t / 0.3)) * s
    elif t < 0.4:
        gap = 62 * s * (1 - ease_in((t - 0.3) / 0.1))
    else:
        gap = -6 * s   # bitten in
    bite = seg(t, 0.4, 1.0)

    # 1. Darken the screen, jaws fade in, canines gleam at the top of the wind-up
    p = seg(t, 0.0, 0.4)
    if p is not None:
        a.tint((25, 0, 10), 120 * ease_out(p))
    jaw_alpha = 255 * min(1.0, t / 0.12) * (fade_late(bite, 0.55) if bite is not None else 1.0)
    shudder = math.sin(t * 90) * 4 * s * (1 - bite) if bite is not None and bite < 0.5 else 0.0
    gleam = hump(seg(t, 0.12, 0.32) or 0.0) if t < 0.32 else 0.0

    # 2. Speed streaks as the jaws slam shut
    p = seg(t, 0.3, 0.42)
    if p is not None:
        for i in range(6):
            x = a.tx + (i - 2.5) * w / 6
            a.line(x, a.ty - gap - 50 * s, x, a.ty - gap - 15 * s, WHITE, 140 * (1 - p), 2)
            a.line(x, a.ty + gap + 50 * s, x, a.ty + gap + 15 * s, WHITE, 140 * (1 - p), 2)

    up = _pf_jaw(a, a.tx + shudder, a.ty - gap - 38 * s, 1, w, jaw_alpha, gleam)
    _pf_jaw(a, a.tx - shudder, a.ty + gap + 38 * s, -1, w, jaw_alpha, gleam)

    # 3. CRUNCH: flash, shockwave, puncture cracks at each canine, sparks
    if bite is not None:
        _strong_finish(a, bite, ((255, 255, 255), (255, 235, 235)), 200, 11)
        e = ease_out(bite)
        a.ring(a.tx, a.ty, 20 * s + 130 * s * e, (255, 210, 210), 230 * (1 - bite), 5)
        a.ring(a.tx, a.ty, 10 * s + 85 * s * e, SPIKE[1], 200 * (1 - bite), 3)
        a.glow(a.tx, a.ty, 90 * s, (255, 120, 120), 1.4 * (1 - bite))
        crack_al = 255 * fade_late(bite, 0.5)
        rng = a.rng('pf_cracks')
        for k, (fx, fy) in enumerate(up):
            px, py = fx, a.ty
            a.circle(px, py, 8 * s, (170, 20, 40), crack_al)
            a.circle(px, py, 4 * s, WHITE, crack_al)
            grow = ease_out(min(1.0, bite / 0.35))
            for j in range(5):
                ang = rng.uniform(0, TAU)
                pts = [(px, py)]
                L = rng.uniform(28, 55) * s * grow
                for m in range(1, 4):
                    d = L * m / 3
                    jit = rng.uniform(-0.35, 0.35)
                    pts.append((px + math.cos(ang + jit) * d, py + math.sin(ang + jit) * d))
                a.lines(pts, (255, 235, 235), crack_al, 2)
        a.burst(a.tx, a.ty, bite, 22, 150 * s, WHITE, 4 * s, shape='streak', glow=0.4)
        a.burst(a.tx, a.ty, bite, 12, 110 * s, (230, 60, 70), 4 * s, gravity=120, key=1)


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


def _crusher_slab(a, sgn, cx, ground, h, w, lean):
    """One jagged stone slab. sgn=-1 is the left slab (its toothed inner
    edge faces right), +1 the right one. Returns (outline, inner_x)."""
    s = a.s
    inner = cx - sgn * w / 2
    outer = cx + sgn * w / 2
    top = ground - h
    pts = [(outer, ground), (outer + sgn * 4 * s, lerp(ground, top, 0.55)),
           (outer - sgn * 6 * s, top + 14 * s), (cx + sgn * 6 * s, top), (inner + sgn * 8 * s, top + 10 * s)]
    for k in range(1, 6):                 # toothed inner edge, top -> bottom
        y = lerp(top + 10 * s, ground, k / 6)
        pts.append((inner - sgn * (9 * s if k % 2 else 0), y))
    pts.append((inner, ground))
    # lean: tip the slab toward / away from the target around its base
    return [(x + lean * (ground - y), y) for x, y in pts], inner


def anim_crusher(a):
    """Two stone slabs erupt either side of the target, wind back, then
    slam shut on it — heavy flash, shake, shockwave and radiating ground
    cracks — before cracking apart and crumbling away in a dust cloud."""
    t, s = a.t, a.s
    tx, ty = a.tx, a.ty
    ground = ty + 62 * s
    H, W = 128 * s, 56 * s
    rise  = seg(t, 0.0, 0.28)
    wind  = seg(t, 0.28, 0.42)
    slam  = seg(t, 0.42, 0.5)
    IMPACT = 0.5
    hit   = seg(t, IMPACT, 1.0)
    crumb = seg(t, 0.7, 1.0)

    # Ground: a fissure opens under the target as the slabs rise
    open_p = ease_out(min(1.0, t / 0.3))
    a.ellipse(tx, ground + 4 * s, 230 * s * open_p, 26 * s * open_p, ROCK[2], 120 * (1 - (crumb or 0)))
    a.lines([(tx - 100 * s * open_p, ground + 2 * s), (tx - 40 * s * open_p, ground + 6 * s),
             (tx + 10 * s * open_p, ground), (tx + 60 * s * open_p, ground + 5 * s),
             (tx + 100 * s * open_p, ground + 1 * s)], (40, 28, 18), 200 * (1 - (crumb or 0)), max(2, int(3 * s)))

    # Slab placement: rise from the ground, pull back, then slam together
    rise_e = ease_out(rise) if rise is not None else 1.0
    gap = 70 * s
    if wind is not None:
        gap += 16 * s * ease_out(wind)
    elif slam is not None:
        gap = lerp(86 * s, W / 2 + 2 * s, ease_in(slam))
    elif t >= IMPACT:
        gap = W / 2 + 2 * s + math.sin(t * 90) * 2 * s * (1 - (hit or 1))   # pressing shudder
    lean = (-0.12 * ease_out(wind) if wind is not None else 0.0) + (0.1 * (1 - ease_in(slam)) if slam is not None else 0.0)
    h = H * rise_e

    if rise is not None:
        a.shake(2 * hump(rise))
        rng = a.rng('pebbles')                 # pebbles shaken loose from the rising slabs
        for _ in range(12):
            sgn = rng.choice((-1, 1))
            px = tx + sgn * (gap + rng.uniform(-W / 2, W / 2))
            q = (rise + rng.uniform(0, 0.6)) % 1
            a.circle(px, ground - h * (1 - q), rng.uniform(1.5, 3.5) * s, ROCK[1], 220 * (1 - q))

    if crumb is None and h > 4 * s:
        for sgn in (-1, 1):
            cx = tx + sgn * (gap + W / 2 - 4 * s)
            pts, inner = _crusher_slab(a, sgn, cx, ground, h, W, -sgn * lean)
            a.poly(pts, ROCK[0], 255)
            # shaded outer half (solid — alpha replaces on the move layer)
            shade = [(lerp(x, cx + sgn * W / 2, 0.55), y) for x, y in pts]
            a.poly(shade, _mix(ROCK[0], ROCK[2], 0.6), 255)
            # rock strata
            for k in range(1, 5):
                sy = ground - h * k / 5
                a.line(cx - W * 0.42, sy + sgn * 3 * s, cx + W * 0.42, sy - sgn * 3 * s,
                       _mix(ROCK[0], ROCK[2], 0.85), 255, max(1, int(2 * s)))
            a.lines(pts, (45, 32, 22), 255, max(2, int(3 * s)), closed=True)
            a.line(inner - sgn * 2 * s, ground - h * 0.85, inner - sgn * 2 * s, ground - 6 * s,
                   ROCK[1], 200, max(1, int(2 * s)))
            # cracks spread over the slabs once they've hit
            if hit is not None:
                c = ease_out(min(1.0, hit / 0.4))
                ox, oy = inner, ground - h * 0.5
                for k, (dx, dy) in enumerate(((1, -1.2), (1.3, 0.2), (0.9, 1.1))):
                    a.lines([(ox, oy),
                             (ox + sgn * dx * 18 * s * c, oy + dy * 14 * s * c),
                             (ox + sgn * dx * 34 * s * c, oy + dy * 30 * s * c + (k - 1) * 6 * s * c)],
                            (40, 28, 18), 255, max(1, int(2 * s)))

    # Impact: flash, heavy shake, shockwave, ground cracks, shards
    if hit is not None:
        _strong_finish(a, hit, ROCK, flash_alpha=170, shake=11)
        a.glow(tx, ty, 90 * s * (1 - hit * 0.5), ROCK[1], 1.4 * (1 - hit))
        a.glow(tx, ty, 40 * s, WHITE, 1.0 * max(0.0, 1 - hit * 3))
        a.ring(tx, ground - 10 * s, 20 * s + 150 * s * ease_out(hit), ROCK[1], 230 * (1 - hit), max(2, int(5 * s)))
        rc = ease_out(min(1.0, hit / 0.35))
        rng = a.rng('cracks')
        for i in range(8):                    # cracks racing out along the ground
            ang = math.pi * (0.05 + 0.9 * i / 7)
            ln = (70 + rng.uniform(0, 50)) * s * rc
            mx, my = tx + math.cos(ang) * ln * 0.5, ground + math.sin(ang) * ln * 0.12
            a.lines([(tx, ground), (mx + rng.uniform(-6, 6) * s, my),
                     (tx + math.cos(ang) * ln, ground + math.sin(ang) * ln * 0.25)],
                    (40, 28, 18), 230 * fade_late(hit, 0.6), max(2, int(3 * s)))
        a.burst(tx, ty - 10 * s, hit, 16, 120 * s, ROCK[0], 7 * s, gravity=160 * s,
                spread=(-math.pi * 0.95, -math.pi * 0.05), shape='square')
        a.burst(tx, ty, hit, 14, 90 * s, ROCK[1], 5 * s, gravity=120 * s, shape='shard', key=1)
        for k in range(7):                    # billowing dust cloud
            d = ease_out(hit)
            a.circle(tx + (k - 3) * 30 * s * d, ground - 10 * s - 14 * s * d * (k % 2),
                     (16 + 30 * d) * s, (190, 165, 125), 170 * (1 - hit) ** 0.7)

    # Crumble: the slabs break into chunks that tumble away
    if crumb is not None:
        rng = a.rng('crumble')
        for sgn in (-1, 1):
            cx = tx + sgn * (W / 2 + 2 * s + W / 2 - 4 * s)
            for i in range(9):
                ox = cx + rng.uniform(-W / 2, W / 2)
                oy = ground - rng.uniform(0.1, 0.95) * H
                vx = sgn * rng.uniform(20, 70) * s
                q = crumb
                x = ox + vx * q
                y = oy - 30 * s * q + 260 * s * q * q
                r = rng.uniform(8, 15) * s * (1 - 0.3 * q)
                a.poly(_rock_poly(x, y, r, q * 3 + i), ROCK[0] if i % 3 else ROCK[2], 255 * (1 - q * q))


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


CHAIN = ((150, 145, 160), (225, 220, 235), (70, 65, 80))


def _chain_link(a, x, y, ang, size, alpha, flat):
    """One oval chain link outline along `ang`; `flat` links are seen edge-on."""
    ca, sa = math.cos(ang), math.sin(ang)
    w = size * (0.22 if flat else 0.5)
    pts = []
    for i in range(10):
        u = i * TAU / 10
        lx, ly = math.cos(u) * size, math.sin(u) * w
        pts.append((x + ca * lx - sa * ly, y + sa * lx + ca * ly))
    a.lines(pts, CHAIN[2], alpha, 4, closed=True)
    a.lines(pts, CHAIN[1] if flat else CHAIN[0], alpha, 2, closed=True)


def anim_chain_rip(a):
    """A chain whips out and coils the foe, then is ripped back, tearing
    off rock and sending links flying."""
    t = a.t
    ang = a.angle_to_target()
    link = 11 * a.s
    # 1) lash: the chain snakes from the user to the target
    p = seg(t, 0.0, 0.35)
    if p is not None:
        reach = ease_out(p)
        n = int(22 * reach) + 1
        for i in range(n):
            u = i / 22
            x, y = a.travel(u)
            wave = math.sin(u * 9 - t * 30) * 14 * a.s * (1 - u) * (1 - p)
            x += -math.sin(ang) * wave
            y += math.cos(ang) * wave
            _chain_link(a, x, y, ang, link, 240, i % 2)
        hx, hy = a.travel(reach)
        a.glow(hx, hy, 18 * a.s, CHAIN[1], 0.6)
    # 2) coil: links wrap and tighten around the target
    p = seg(t, 0.3, 0.68)
    if p is not None:
        tight = 1 - 0.35 * ease_in(p)
        n = int(16 * min(1.0, p * 2.5)) + 1
        al = 240 if p < 0.85 else 240 * (1 - p) / 0.15
        for i in range(n):
            u = i * TAU / 16 + p * 1.5
            x = a.tx + math.cos(u) * 62 * a.s * tight
            y = a.ty + math.sin(u) * 24 * a.s * tight + (i / 16 - 0.5) * 50 * a.s
            _chain_link(a, x, y, u + math.pi / 2, link, al, i % 2)
        if p > 0.6:
            a.shake(2)
    # 3) rip: the chain yanks back, rock chunks and loose links scatter
    p = seg(t, 0.62, 1.0)
    if p is not None:
        e = ease_in(min(1.0, p * 1.6))
        for i in range(10):  # retreating chain segment
            u = i / 10 * (1 - e)
            x, y = a.travel(u)
            _chain_link(a, x, y, ang, link, 230 * (1 - p), i % 2)
        a.burst(a.tx, a.ty, p, 12, 85 * a.s, ROCK[0], 5 * a.s, gravity=70 * a.s, shape='square', key='rip_rock')
        a.burst(a.tx, a.ty, p, 8, 70 * a.s, ROCK[1], 3 * a.s, gravity=50 * a.s, shape='shard', key='rip_dust')
        rng = a.rng('rip_links')
        for k in range(5):  # snapped links tumbling away
            la = rng.uniform(0, TAU)
            d = 90 * a.s * ease_out(p) * rng.uniform(0.6, 1.0)
            x = a.tx + math.cos(la) * d
            y = a.ty + math.sin(la) * d + 60 * a.s * p * p
            _chain_link(a, x, y, la + p * 8 * (1 if k % 2 else -1), link * 0.8, 230 * (1 - p), k % 2)
        a.ring(a.tx, a.ty, (20 + 60 * ease_out(p)) * a.s, ROCK[1], 220 * (1 - p), 3)
        a.glow(a.tx, a.ty, 55 * a.s, ROCK[1], 1.0 * (1 - p))
        if p < 0.35:
            a.shake(6 * (1 - p / 0.35))


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


def _dust_devil(a, x, y, h, k, alpha, spin):
    """Spinning dust tornado standing on (x, y): stacked swirl rings that
    widen toward the top and sway with `spin`, carrying orbiting pebbles."""
    if alpha <= 0 or h < 4:
        return
    s = a.s
    a.ellipse(x, y, 70 * s * k, 16 * s * k, BLACK, alpha * 0.3)
    n = 12

    def width_at(u):
        return (16 + 84 * u ** 1.3) * s * k

    def sway_at(u):
        return math.sin(spin * 1.7 + u * 3.5) * 8 * s * u * k

    # solid funnel body behind the swirl rings
    left = [(x + sway_at(i / 8) - width_at(i / 8) / 2, y - i / 8 * h) for i in range(9)]
    right = [(x + sway_at(i / 8) + width_at(i / 8) / 2, y - i / 8 * h) for i in range(9)]
    a.poly(left + right[::-1], ROCK[0], alpha * 0.45)
    for i in range(n):
        u = i / (n - 1)
        yy = y - u * h
        w = width_at(u)
        sway = sway_at(u)
        a.ellipse(x + sway, yy, w, w * 0.3, _mix(ROCK[2], ROCK[1], u), alpha * 0.55)
        a.ellipse(x + sway, yy, w, w * 0.3, ROCK[1], alpha * (0.6 + 0.4 * u), width=2)
        ph = spin * 4 + u * 5   # a streak on each ring sells the spin
        fx = x + sway + math.cos(ph) * w * 0.4
        fy = yy + abs(math.sin(ph)) * w * 0.12
        a.line(fx - 8 * s * k, fy, fx + 8 * s * k, fy, ROCK[0], alpha * 0.8, 2)
    rng = a.rng('devil_pebbles')
    for i in range(14):
        u = rng.uniform(0.05, 0.95)
        ph = spin * rng.uniform(3, 5) + rng.uniform(0, TAU)
        w = width_at(u)
        px = x + math.cos(ph) * w * 0.55
        py = y - u * h + math.sin(ph) * w * 0.17
        a.poly(_rock_poly(px, py, rng.uniform(2.5, 4.5) * s, ph), ROCK[0] if i % 2 else ROCK[2], alpha)
    a.glow(x, y - h * 0.4, 50 * s * k, ROCK[1], 0.25 * alpha / 255)


def anim_dust_devil(a):
    t = a.t
    s = a.s
    ground = 45 * s
    away = 1 if a.tx >= a.sx else -1
    spin = t * 14
    # 1. Whips up at the attacker and races over to the target
    p = seg(t, 0.0, 0.42)
    if p is not None:
        e = ease_in_out(p)
        x, y = a.travel(e)
        _dust_devil(a, x, y + ground, 120 * s * (0.35 + 0.65 * ease_out(p)), 0.55 + 0.4 * e, 235, spin)
    # 2. Swallows the target, grinding it with sand and stone
    p = seg(t, 0.4, 0.72)
    if p is not None:
        _dust_devil(a, a.tx + math.sin(p * 9) * 4 * s, a.ty + ground, 140 * s, 0.95, 240, spin)
        _impact(a, p, ROCK, 0.8, n=12)
        a.tint(ROCK[2], 50 * hump(p))
        if p < 0.5:
            a.shake(4)
    # 3. Spins away off the far side of the screen — it'll be back
    p = seg(t, 0.7, 1.0)
    if p is not None:
        e = ease_in(p)
        _dust_devil(a, a.tx + away * 320 * s * e, a.ty + ground - 20 * s * e,
                    140 * s * (1 - 0.3 * e), 0.95 - 0.35 * e, 240 * (1 - p), spin)


def anim_dust_devil_return(a):
    """End of the next turn: the Dust Devil blows back in from the side it
    left by, loops around the target and slams down on it."""
    t = a.t
    s = a.s
    ground = 45 * s
    away = 1 if a.tx >= a.sx else -1
    spin = t * 16
    # 1. Wind and grit gust back in from that edge
    p = seg(t, 0.0, 0.7)
    if p is not None:
        rng = a.rng('ddr_wind')
        al = 200 * hump(p)
        for _ in range(26):
            y = a.ty + rng.uniform(-90, 70) * s
            q = (p * rng.uniform(1.2, 2.0) + rng.random()) % 1
            x = a.tx + away * (300 - q * 420) * s
            a.line(x, y, x + away * 18 * s, y, ROCK[1], al * 0.7, 2)
    # 2. Swings around the target on a closing loop
    p = seg(t, 0.1, 0.68)
    if p is not None:
        e = ease_in_out(p)
        ang = (0.0 if away > 0 else math.pi) - away * e * 1.25 * TAU
        r = 300 * s * (1 - e)
        x = a.tx + math.cos(ang) * r
        y = a.ty + ground + math.sin(ang) * r * 0.35
        behind = math.sin(ang) < 0   # far side of the loop reads dimmer
        _dust_devil(a, x, y, 140 * s, 0.7 + 0.35 * e, 240 * (0.7 if behind else 1.0) * min(1, p / 0.15), spin)
    # 3. Slams down on the target
    p = seg(t, 0.62, 1.0)
    if p is not None:
        if p < 0.45:
            q = p / 0.45
            _dust_devil(a, a.tx, a.ty + ground, 150 * s * (1 - 0.4 * q), 1.05, 240 * (1 - q), spin)
        a.burst(a.tx, a.ty, p, 16, 110 * s, ROCK[0], 7 * s, gravity=140, shape='square')
        a.burst(a.tx, a.ty + 20 * s, p, 18, 90 * s, ROCK[1], 5 * s, spread=(math.pi, TAU), key=1)
        _impact(a, p, ROCK, 1.1, n=14, key=2)
        _strong_finish(a, p, ROCK, 120, 8)


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
    """A crushing telekinetic shove: darkness collapses into a black core at
    the attacker, three dark pressure waves surge across, then the target's
    space is wrenched sideways — displaced slices, shove streaks, a black
    burst and a hard shake."""
    t, s = a.t, a.s
    shade = (12, 3, 22)
    violet = DARK[0]
    ang = a.angle_to_target()
    ux, uy = math.cos(ang), math.sin(ang)          # along the shove
    nx, ny = -uy, ux                               # across it

    # 1) Charge: darkness collapses into a black core at the attacker
    p = seg(t, 0.0, 0.3)
    if p is not None:
        a.tint(shade, 70 * ease_in(p))
        a.implode(a.sx, a.sy, p, 28, 120 * s, violet, size=4 * s, key='fs', swirl=2.0)
        a.implode(a.sx, a.sy, p, 16, 90 * s, shade, size=5 * s, key='fs2', swirl=-1.5)
        core = (10 + 22 * ease_out(p)) * s
        a.circle(a.sx, a.sy, core, shade, 255)
        a.ring(a.sx, a.sy, core + (3 + 2 * math.sin(t * 60)) * s, violet, 230, max(2, int(3 * s)))
        a.glow(a.sx, a.sy, core * 2.6, violet, 0.6 * p)

    # 2) Three pressure waves (dark crescents) surge to the target
    for k in range(3):
        q = seg(t, 0.22 + k * 0.07, 0.5 + k * 0.07)
        if q is None:
            continue
        e = ease_in(q)
        cx, cy = a.travel(e)
        half = (34 + 60 * e) * s
        bow = (14 + 24 * e) * s
        arc = []
        for j in range(9):
            v = j / 8 * 2 - 1
            off = (1 - v * v) * bow                # bulges forward in the middle
            arc.append((cx + nx * half * v + ux * off, cy + ny * half * v + uy * off))
        al = 255 * (0.6 + 0.4 * e)
        a.lines(arc, shade, al, max(4, int((15 - k * 3) * s)))
        a.lines(arc, violet, al * 0.85, max(2, int(3 * s)))
        a.glow(cx, cy, half * 0.8, violet, 0.35 * e)
        # trailing distortion streaks behind each wave
        for j in (-1, 0, 1):
            bx = cx + nx * half * 0.5 * j - ux * 26 * s
            by = cy + ny * half * 0.5 * j - uy * 26 * s
            a.line(bx, by, bx - ux * 30 * s * e, by - uy * 30 * s * e, shade, 160 * e, max(1, int(2 * s)))

    # 3) Impact: space around the target is wrenched sideways
    hit = seg(t, 0.5, 1.0)
    if hit is not None:
        h = hump(min(1.0, hit * 1.6))
        a.tint(shade, 140 * (1 - hit) ** 1.5)
        if hit < 0.5:
            a.shake(10 * (1 - hit / 0.5))
        # black burst core
        a.circle(a.tx, a.ty, (20 + 60 * ease_out(hit)) * s, shade, 230 * (1 - hit))
        a.ring(a.tx, a.ty, (30 + 110 * ease_out(hit)) * s, violet, 230 * (1 - hit), max(2, int(5 * s)))
        a.ring(a.tx, a.ty, (18 + 70 * ease_out(hit)) * s, shade, 200 * (1 - hit), max(2, int(4 * s)))
        # displaced slices: horizontal bands torn out of place, shoved along
        rng = a.rng('slices')
        for i in range(8):
            yy = a.ty - 80 * s + i * 21 * s + rng.uniform(-4, 4) * s
            push = (rng.uniform(24, 60) * s) * h * (1 if i % 2 else -0.6)
            w = rng.uniform(90, 160) * s
            x0 = a.tx - w / 2 + ux * push
            a.poly([(x0, yy), (x0 + w, yy), (x0 + w, yy + 10 * s), (x0, yy + 10 * s)], shade, 225 * h)
            a.line(x0, yy, x0 + w, yy, violet, 200 * h, max(1, int(2 * s)))
        # shove streaks blasting out the far side
        a.burst(a.tx, a.ty, hit, 16, 130 * s, violet, 4 * s, shape='streak',
                spread=(ang - 0.6, ang + 0.6), key='push')
        a.burst(a.tx, a.ty, hit, 12, 90 * s, shade, 6 * s, key='shards')
        a.glow(a.tx, a.ty, 70 * s, violet, 0.8 * (1 - hit))


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
    """A shadow is cast over the target: a sheet of darkness gathers above
    it, drapes down over it like a cloak (rippling hem, shadow pooling on the
    ground), cinches tight with a dark pulse, then dissolves into smoke."""
    t, s = a.t, a.s
    tx, ty = a.tx, a.ty
    rng = a.rng('veil')
    gather = seg(t, 0.0, 0.28)        # sheet forms above the target
    drape  = seg(t, 0.18, 0.62)       # falls over it
    cinch  = seg(t, 0.58, 0.8)        # tightens + pulse
    melt   = seg(t, 0.74, 1.0)        # dissolves into smoke

    fade = 1.0 if melt is None else 1 - ease_in(melt)
    base_w = 88 * s
    if cinch is not None:
        base_w *= 1 - 0.12 * hump(cinch)
    elif melt is not None:
        base_w *= 1 - 0.06 * (1 - melt)

    shade = (14, 4, 26)        # near-black violet — the shadow itself
    edge  = (38, 10, 58)       # faint violet rim / folds (reads lighter on the move layer)

    # Shadow pooling on the ground beneath the target
    pool = ease_out(min(1, t / 0.6))
    a.ellipse(tx, ty + 70 * s, 200 * s * pool, 36 * s * pool, shade, 170 * pool * fade)

    # The veil: a narrow hood that flares out into a cloak with a ragged,
    # rippling hem — it falls over the target from above.
    top_y = lerp(ty - 165 * s, ty - 100 * s, ease_out(gather if gather is not None else 1.0))
    widen = ease_out(gather) if gather is not None else 1.0
    w = base_w * (0.3 + 0.7 * widen)
    drop = ease_in_out(drape) if drape is not None else (0.0 if t < 0.18 else 1.0)
    hood_w, dome = w * 0.62, 30 * s
    hem_y = lerp(top_y + dome + 8 * s, ty + 64 * s, drop)
    hem_w = lerp(hood_w * 1.1, w * 1.25, drop)

    def side(sign):
        """Hood edge down to the hem corner, bowing outward."""
        x0, y0 = tx + sign * hood_w, top_y + dome
        x1, y1 = tx + sign * hem_w, hem_y
        out = []
        for k in range(1, 8):
            v = k / 8
            bow = math.sin(v * math.pi) * 12 * s * drop
            sway = math.sin(t * 7 + v * 3 + sign) * 3 * s * drop
            out.append((lerp(x0, x1, v) + sign * bow + sway, lerp(y0, y1, v)))
        return out

    pts = []
    for k in range(11):                      # hood, left -> right
        ang = math.pi - math.pi * k / 10
        pts.append((tx + math.cos(ang) * hood_w, top_y + dome * (1 - math.sin(ang))))
    pts += side(1)
    for k in range(21):                      # ragged hem, right -> left
        u = k / 20
        x = lerp(tx + hem_w, tx - hem_w, u)
        wave = math.sin(u * 8 + t * 15) * 6 * s
        tongue = (10 * s if k % 2 else 0) * (0.6 + 0.4 * math.sin(t * 11 + k))
        pts.append((x, hem_y + (wave + tongue) * (0.3 + 0.7 * drop)))
    pts += side(-1)[::-1]

    # Feathered edge (a slightly larger, fainter copy) then the body
    feather = [(tx + (x - tx) * 1.06, y + (3 * s if y > top_y + dome else -3 * s)) for x, y in pts]
    a.poly(feather, shade, 110 * fade)
    a.poly(pts, shade, 235 * fade)
    a.lines(pts, edge, 140 * fade, max(1, int(2 * s)), closed=True)

    # Soft folds running down the cloak
    for i in (-2, -1, 1, 2):
        f = i / 2.6
        fold = [(lerp(tx + f * hood_w, tx + f * hem_w, v) + math.sin(v * 5 + t * 9 + i) * 4 * s,
                 lerp(top_y + dome, hem_y, v)) for v in (0.1, 0.4, 0.7, 0.95)]
        a.lines(fold, edge, 90 * fade * drop, max(1, int(2 * s)))

    # Wisps of shadow trailing off the hem as it falls
    if drop > 0.05:
        for i in range(8):
            x0 = lerp(tx - hem_w, tx + hem_w, (i + 0.5) / 8)
            ph = rng.uniform(0, TAU)
            ln = (12 + 9 * math.sin(t * 9 + ph)) * s
            a.lines([(x0, hem_y + 4 * s), (x0 + math.sin(t * 12 + ph) * 6 * s, hem_y + ln * 0.6),
                     (x0 + math.sin(t * 12 + ph + 1) * 9 * s, hem_y + ln * 1.2)],
                    shade, 170 * fade * drop, max(2, int(3 * s)))

    # Cinch: the shadow clamps down — dark pulse, screen dims, a little shake
    if cinch is not None:
        h = hump(cinch)
        a.ring(tx, ty, (55 + 75 * cinch) * s, DARK[0], 180 * (1 - cinch), max(2, int(3 * s)))
        a.tint(shade, 80 * h)
        a.shake(3 * h)

    # Dissolve: the cloak breaks into dark smoke that drifts upward
    if melt is not None:
        for i in range(18):
            px = tx + rng.uniform(-1, 1) * base_w * 1.1 + math.sin(melt * 4 + i) * 6 * s
            py = lerp(ty + 60 * s, ty - 95 * s, rng.random()) - melt * rng.uniform(35, 85) * s
            r = (6 + 9 * melt) * s * rng.uniform(0.6, 1.2)
            a.circle(px, py, r, shade, 200 * (1 - melt))


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


def _vignette(a, k, col=BLACK):
    """Darkens the screen edges inward; k = 0..1 intensity."""
    if k <= 0.02:
        return
    cx, cy = a.W / 2, a.H / 2
    R = math.hypot(cx, cy)
    band = int(R * 0.05) + 2
    for i in range(12):
        f = i / 11
        # Alpha ramps in from 0 so the vignette's inner edge never shows as a ring
        a.ring(cx, cy, R * (0.55 + 0.5 * f), col, 58 * k * f * f, band)


# ── Eternal Darkness (signature, recharge move — see DURATIONS) ─────────────
# The light dies -> darkness pours into the attacker as a void orb -> the Eye
# of Deimo opens above the target and lowers marionette strings onto it ->
# the orb is hurled in and becomes a singularity that swallows the light ->
# it collapses and detonates in an inverted (black) shockwave -> the eye
# closes and the attacker's aura gutters out (it must recharge).

ED_VOID    = (6, 0, 14)
ED_PURPLE  = (150, 50, 230)
ED_VIOLET  = (215, 130, 255)
ED_MAGENTA = (255, 60, 170)
ED_DEEP    = (60, 10, 105)


def _ed_eye_pos(a):
    return a.tx, max(58.0, a.ty - 118 * a.s)


def _ed_eye(a, x, y, w, open_k, t, k):
    """The almond eye of Deimo; open_k 0..1 lid opening, k 0..1 intensity."""
    if open_k <= 0.02 or k <= 0.02:
        return
    h = w * 0.4 * open_k
    top, bot = [], []
    for i in range(25):
        u = i / 24
        px = x + (u - 0.5) * w
        bulge = math.sin(math.pi * u) ** 0.85
        top.append((px, y - h * bulge))
        bot.append((px, y + h * bulge))
    # Aura flickering around the lids (kept off the center so the eye stays dark)
    for i in range(10):
        ang = i * TAU / 10 + t * 2.5
        a.glow(x + math.cos(ang) * w * 0.55, y + math.sin(ang) * (h + 8) * 0.9, w * 0.28,
               ED_PURPLE if i % 2 else ED_MAGENTA, 0.65 * k)
    # Lash-like spikes radiating from the lids
    for i in range(1, 12):
        u = i / 12
        bulge = math.sin(math.pi * u) ** 0.85
        px = x + (u - 0.5) * w
        ln = (10 + 10 * math.sin(i * 1.7 + t * 6)) * a.s * open_k
        a.line(px, y - h * bulge, px + (u - 0.5) * ln * 0.6, y - h * bulge - ln, ED_VIOLET, 200 * k, 2)
        a.line(px, y + h * bulge, px + (u - 0.5) * ln * 0.6, y + h * bulge + ln * 0.7, ED_PURPLE, 170 * k, 2)
    a.poly(top + bot[::-1], ED_VOID, 250 * k)
    # Iris, striations, slit pupil, glint
    ir = min(h * 0.92, w * 0.2)
    if ir >= 2:
        a.circle(x, y, ir, ED_PURPLE, 255 * k)
        a.circle(x, y, ir * 0.78, ED_MAGENTA, 200 * k)
        for i in range(14):
            ang = i * TAU / 14 + t * 1.5
            a.line(x + math.cos(ang) * ir * 0.35, y + math.sin(ang) * ir * 0.35,
                   x + math.cos(ang) * ir * 0.95, y + math.sin(ang) * ir * 0.95, ED_VIOLET, 150 * k, 1)
        a.ring(x, y, ir, ED_VIOLET, 255 * k, 2)
        a.ellipse(x, y, ir * 0.36, min(ir * 1.9, h * 1.95), ED_VOID, 255 * k)
        a.circle(x - ir * 0.38, y - ir * 0.38, max(1.5, ir * 0.13), WHITE, 230 * k)
    a.lines(top, ED_VIOLET, 235 * k, 3)
    a.lines(bot, ED_VIOLET, 235 * k, 3)


def _ed_singularity(a, x, y, r, k, t, spin):
    """Black hole: back half of the accretion disk, the hole, then the front half."""
    if r < 1.5 or k <= 0.02:
        return
    rings = ((1.75, ED_MAGENTA, 1.0), (2.2, ED_VIOLET, 0.8), (2.7, ED_PURPLE, 0.6))

    def disk(front):
        for ri, (rm, col, al) in enumerate(rings):
            rr = r * rm
            n = 30
            for j in range(n):
                ang = j * TAU / n + t * spin * (1.0 - ri * 0.22)
                if (math.sin(ang) > 0) != front:
                    continue
                px, py = x + math.cos(ang) * rr, y + math.sin(ang) * rr * 0.3
                a.circle(px, py, max(1.5, r * 0.085 * (1.25 if front else 0.8)), col, 235 * k * al)
                if j % 3 == 0:
                    a.glow(px, py, r * 0.4, col, 0.45 * k * al)

    disk(False)
    # Lensed light ring hugging the event horizon
    a.ring(x, y, r * 1.22, ED_VIOLET, 210 * k, max(2, r * 0.14))
    a.ring(x, y, r * 1.08, WHITE, 160 * k, max(1, r * 0.05))
    for i in range(8):
        ang = i * TAU / 8 + t * 4
        a.glow(x + math.cos(ang) * r * 1.3, y + math.sin(ang) * r * 1.3, r * 0.7, ED_PURPLE, 0.6 * k)
    a.circle(x, y, r, ED_VOID, 255 * k)
    disk(True)


def anim_eternal_darkness(a):
    t, s = a.t, a.s
    ex, ey = _ed_eye_pos(a)

    # The light dies: deep void tint + closing vignette for nearly the whole move
    dark = min(1.0, t / 0.1) * (1.0 if t < 0.88 else max(0.0, (1 - t) / 0.12))
    a.tint(ED_VOID, 215 * dark)
    _vignette(a, dark)

    # 1. Darkness pours into the attacker: rising tendrils, swirling motes, a
    #    void orb crackling with dark lightning
    p = seg(t, 0.02, 0.44)
    orb_r = 0.0
    if p is not None:
        grow = ease_out(min(1.0, p / 0.8))
        orb_r = 24 * s * grow
        for i in range(7):
            off = (i - 3) * 16 * s
            pts = []
            for j in range(13):
                u = j / 12
                reach = min(1.0, p * 1.6)
                yy = lerp(a.sy + 70 * s, a.sy, u * reach)
                xx = lerp(a.sx + off, a.sx, (u * reach) ** 1.5) + math.sin(u * 9 + t * 40 + i) * 7 * s * (1 - u)
                pts.append((xx, yy))
            a.lines(pts, ED_DEEP if i % 2 else ED_PURPLE, 220 * min(1.0, p * 3), max(2, 5 * s * (1 - p * 0.5)))
        a.implode(a.sx, a.sy, p, 40, 170 * s, ED_VIOLET, 2.6 * s, glow=0.35, swirl=5, key='edin')
        a.implode(a.sx, a.sy, p, 24, 120 * s, ED_DEEP, 3.5 * s, swirl=-3, key='edin2')
        for kk in range(3):
            a.ring(a.sx, a.sy, orb_r * (1.5 + kk * 0.5) * (1 - 0.3 * hump(p)), ED_PURPLE if kk % 2 else ED_MAGENTA,
                   170 * grow, 2)
        for kk in range(8):
            ang = kk * TAU / 8 + t * 6
            a.glow(a.sx + math.cos(ang) * orb_r * 1.25, a.sy + math.sin(ang) * orb_r * 1.25, orb_r, ED_PURPLE, 0.8 * grow)
        a.circle(a.sx, a.sy, orb_r, ED_VOID, 255)
        a.ring(a.sx, a.sy, orb_r, ED_VIOLET, 255 * grow, 2)
        if p > 0.4:
            for kk in range(4):
                ang = kk * TAU / 4 + t * 25
                a.bolt(a.sx, a.sy, a.sx + math.cos(ang) * 55 * s, a.sy + math.sin(ang) * 55 * s,
                       ED_PURPLE, width=2, jag=9, segs=6, glow=0.5)

    # 2. The Eye of Deimo opens above the target (and closes at the very end)
    eye = seg(t, 0.16, 0.97)
    if eye is not None:
        opening = ease_out(min(1.0, (t - 0.16) / 0.14))
        closing = 1 - ease_in(max(0.0, (t - 0.86) / 0.11))
        blink = 1 - 0.85 * hump(seg(t, 0.36, 0.4) or 0.0)   # one slow, unsettling blink
        _ed_eye(a, ex, ey, 128 * s, opening * closing * blink, t, min(1.0, opening * 1.5) * closing)

    # 3. Marionette strings lower from the eye and pull taut on the target
    p = seg(t, 0.3, 0.76)
    if p is not None:
        reach = ease_out(min(1.0, p / 0.25))
        taut = ease_in(max(0.0, min(1.0, (p - 0.25) / 0.3)))
        fade = 1.0 if p < 0.88 else max(0.0, (1 - p) / 0.12)
        jerk = math.sin(t * 70) * 3 * s * taut if p > 0.5 else 0.0
        for i in range(5):
            f = (i - 2) / 2
            x1, y1 = ex + f * 45 * s, ey + 18 * s
            x2, y2 = a.tx + f * 38 * s + jerk, a.ty - 22 * s - abs(f) * 10 * s
            pts = []
            for j in range(15):
                u = j / 14 * reach
                sag = (1 - taut) * 22 * s * math.sin(math.pi * u) * (1 if i % 2 else -0.6)
                pts.append((lerp(x1, x2, u) + sag, lerp(y1, y2, u)))
            a.lines(pts, ED_PURPLE, 200 * fade, 4)
            a.lines(pts, ED_VIOLET, 240 * fade, 2)
            a.lines(pts, WHITE, 150 * fade, 1)
            for j in range(0, len(pts), 5):
                a.glow(pts[j][0], pts[j][1], 7 * s, ED_PURPLE, 0.45 * fade)
            gx, gy = pts[int((t * 30 + i * 3) % len(pts))]
            a.glow(gx, gy, 9 * s, ED_MAGENTA, 0.8 * fade)
            if reach >= 1:
                a.circle(x2, y2, 3 * s, ED_MAGENTA, 230 * fade)
        if taut > 0.5:
            a.shake(2)

    # 4. The void orb is hurled at the target, shedding darkness
    p = seg(t, 0.44, 0.56)
    if p is not None:
        e = ease_in(p)
        for i in range(10, -1, -1):
            q = max(0.0, e - i * 0.035)
            x, y = a.travel(q, 70 * s)
            r = (22 - i * 1.6) * s
            if i:
                a.circle(x, y, r, ED_PURPLE if i % 2 else ED_DEEP, 200 * (1 - i / 11))
        x, y = a.travel(e, 70 * s)
        a.glow(x, y, 46 * s, ED_PURPLE, 1.2)
        a.circle(x, y, 20 * s, ED_VOID, 255)
        a.ring(x, y, 20 * s, ED_VIOLET, 255, 3)
        a.burst(x, y, p, 14, 50 * s, ED_VIOLET, 2.5 * s, key='edshed')

    # 5. Singularity: swells, swallows the light, then collapses to a point
    p = seg(t, 0.54, 0.79)
    if p is not None:
        swell = ease_out(min(1.0, p / 0.3))
        collapse = 1 - ease_in(max(0.0, (p - 0.78) / 0.22))
        pulse = 1 + 0.08 * math.sin(t * 60)
        r = 36 * s * swell * collapse * pulse
        a.implode(a.tx, a.ty, min(1.0, p * 1.4), 46, 230 * s, ED_VIOLET, 2.5 * s, glow=0.3, swirl=7, key='edsuck')
        a.implode(a.tx, a.ty, min(1.0, p * 1.2), 22, 190 * s, (255, 255, 255), 1.8 * s, swirl=-6, key='edlight')
        for kk in range(3):
            q = (p * 2.2 + kk / 3) % 1.0
            a.ring(a.tx, a.ty, (150 - 120 * q) * s, ED_PURPLE, 150 * q * collapse, 2)
        _ed_singularity(a, a.tx, a.ty, r, 1.0, t, 9 + 30 * (1 - collapse))
        a.shake(3 + 6 * p)

    # 6. Detonation: violet-white flash, then black shockwaves with burning edges
    p = seg(t, 0.78, 0.97)
    if p is not None:
        a.tint((235, 205, 255), 255 * max(0.0, 1 - p / 0.12) ** 2)
        for kk in range(4):
            q = seg(p, kk * 0.07, 0.65 + kk * 0.07)
            if q is not None:
                rr = 15 * s + 240 * s * ease_out(q)
                a.ring(a.tx, a.ty, rr, ED_VOID, 240 * (1 - q), max(3, 22 * s * (1 - q)))
                a.ring(a.tx, a.ty, rr + 11 * s * (1 - q), ED_MAGENTA if kk % 2 else ED_VIOLET, 230 * (1 - q), 3)
        star = ease_out(min(1.0, p * 2.5))
        a.star(a.tx, a.ty, 165 * s * star, ED_PURPLE, 220 * (1 - p), points=8, rot=p, inner=0.12)
        a.star(a.tx, a.ty, 120 * s * star, ED_VOID, 255 * (1 - p), points=8, rot=p + 0.2, inner=0.14)
        a.burst(a.tx, a.ty, p, 26, 210 * s, ED_PURPLE, 6 * s, shape='shard', key='edshard')
        a.burst(a.tx, a.ty, p, 20, 180 * s, ED_VIOLET, 3 * s, shape='streak', glow=0.5, key='edstreak')
        a.glow(a.tx, a.ty, 120 * s, ED_MAGENTA, 1.6 * (1 - p))
        if p < 0.55:
            a.shake(15 * (1 - p / 0.55))

    # 7. Aftermath: embers drift up from the target; the attacker's power gutters out
    p = seg(t, 0.84, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty + 20 * s, p, 18, 90 * s, ED_VIOLET, 2 * s, gravity=-90 * s,
                spread=(math.pi * 1.1, math.pi * 1.9), glow=0.4, key='edember')
        a.rain(p, 14, ED_DEEP, a.sx - 40 * s, a.sx + 40 * s, a.sy - 35 * s, a.sy + 55 * s,
               width=2.5 * s, key='eddrain', speed=0.8, shape='dot')
        a.ring(a.sx, a.sy, 34 * s * (1 + p), ED_DEEP, 160 * (1 - p), 3)


# ── Infinite Light (signature, recharge move — see DURATIONS) ──────────────
# A hush falls -> a sacred halo spins up around the attacker -> it traces an
# infinity sign that soars over the target and blazes god rays -> a ring of
# light spears plunges in -> a prismatic pillar of judgement crashes down ->
# a sphere of light erupts and swallows the whole screen -> total whiteout,
# where only gold/rainbow rings, a vast infinity sign and a blooming star show
# -> the light recedes as feathers drift down and the attacker's halo cracks.

IL_GOLD = (255, 205, 80)
IL_PALE = (255, 246, 210)
IL_SKY = (170, 220, 255)
IL_HUSH = (10, 8, 34)


def _lemniscate(cx, cy, w, u):
    d = 1 + math.sin(u) ** 2
    return cx + w * math.cos(u) / d, cy + w * math.sin(u) * math.cos(u) / d


def _il_infinity(a, cx, cy, w, k, t, upto=TAU):
    """The infinity sign drawn in light, traced from u=0 to `upto`."""
    if k <= 0.02 or w < 3:
        return
    n = max(2, int(48 * upto / TAU))
    pts = [_lemniscate(cx, cy, w, upto * i / n) for i in range(n + 1)]
    a.lines(pts, IL_GOLD, 220 * k, max(3, int(9 * a.s)))
    a.lines(pts, IL_PALE, 240 * k, max(2, int(5 * a.s)))
    a.lines(pts, WHITE, 255 * k, 2)
    for i in range(0, len(pts), 4):
        a.glow(pts[i][0], pts[i][1], 16 * a.s, IL_GOLD, 0.55 * k)
    # Sparks running along the sign
    for i in range(3):
        sx, sy = _lemniscate(cx, cy, w, (t * 14 + i * TAU / 3) % upto if upto > 0.1 else 0)
        a.star(sx, sy, 7 * a.s, WHITE, 255 * k, points=4, rot=t * 8)
        a.glow(sx, sy, 22 * a.s, IL_PALE, 0.9 * k)


def _il_halo(a, x, y, r, k, t):
    """Sacred-geometry halo: ticked rings, counter-rotating hexagram."""
    if k <= 0.02 or r < 3:
        return
    for ri, (rm, spin, col) in enumerate(((1.0, 1.4, IL_GOLD), (0.78, -2.0, IL_PALE), (1.22, 0.8, IL_SKY))):
        rr = r * rm
        a.ring(x, y, rr, col, 200 * k, 2)
        ticks = 12 + ri * 6
        for i in range(ticks):
            ang = i * TAU / ticks + t * spin
            a.line(x + math.cos(ang) * rr, y + math.sin(ang) * rr,
                   x + math.cos(ang) * (rr + 6 * a.s), y + math.sin(ang) * (rr + 6 * a.s), col, 200 * k, 2)
    for tri in range(2):
        rot = t * (2.2 if tri else -2.2) + tri * math.pi / 3
        pts = [(x + math.cos(rot + i * TAU / 3) * r * 0.74, y + math.sin(rot + i * TAU / 3) * r * 0.74)
               for i in range(3)]
        a.lines(pts, WHITE if tri else IL_GOLD, 230 * k, 2, closed=True)
    for i in range(6):
        ang = i * TAU / 6 + t * 1.4
        a.glow(x + math.cos(ang) * r, y + math.sin(ang) * r, 14 * a.s, IL_GOLD, 0.6 * k)


def _il_rays(a, cx, cy, n, length, rot, col, alpha, spread=0.06, inner=0.0):
    """God rays: n thin light wedges fanning out from (cx, cy)."""
    if alpha <= 2 or length < 4:
        return
    for i in range(n):
        ang = rot + i * TAU / n
        wob = 1 + 0.25 * math.sin(i * 2.7 + rot * 3)
        L = length * wob
        r0 = inner * L
        a.poly([(cx + math.cos(ang) * r0, cy + math.sin(ang) * r0),
                (cx + math.cos(ang - spread) * L, cy + math.sin(ang - spread) * L),
                (cx + math.cos(ang + spread) * L, cy + math.sin(ang + spread) * L)],
               col, alpha)


def anim_infinite_light(a):
    t, s = a.t, a.s
    W, H = a.W, a.H
    ix, iy = a.tx, max(56.0, a.ty - 120 * s)   # where the infinity sign hovers
    diag = math.hypot(W, H)

    # ── Screen mood: the hush, then the light breaks through, then WHITE ──
    hush = min(1.0, t / 0.06) * (1.0 if t < 0.42 else max(0.0, (0.5 - t) / 0.08))
    a.tint(IL_HUSH, 175 * hush)
    _vignette(a, 0.85 * hush, IL_HUSH)
    p = seg(t, 0.44, 0.56)
    if p is not None:
        a.tint(IL_PALE, 170 * ease_in(p))                       # dawn creeping in
    if 0.56 <= t <= 0.80:
        a.tint(WHITE, 255)                                      # total whiteout
    p = seg(t, 0.80, 1.0)
    if p is not None:
        a.tint(WHITE, 255 * (1 - p) ** 1.4)                     # light recedes

    # 1. Sacred halo spins up around the attacker; motes of light gather in
    p = seg(t, 0.0, 0.34)
    if p is not None:
        k = ease_out(min(1.0, p / 0.35)) * (1.0 if p < 0.8 else max(0.0, (1 - p) / 0.2))
        _il_halo(a, a.sx, a.sy, 52 * s * (0.6 + 0.4 * ease_out(min(1.0, p / 0.35))), k, t * 5)
        a.implode(a.sx, a.sy, min(1.0, p * 1.3), 44, 190 * s, IL_PALE, 2.4 * s, glow=0.35, swirl=3, key='ilin')
        a.implode(a.sx, a.sy, min(1.0, p * 1.1), 20, 230 * s, IL_GOLD, 1.8 * s, swirl=-4, key='ilin2')
        _il_rays(a, a.sx, a.sy, 10, 70 * s * k, t * 4, IL_PALE, 90 * k, spread=0.05)
        a.glow(a.sx, a.sy, 44 * s * k, IL_GOLD, 1.1 * k)
        a.circle(a.sx, a.sy, (6 + 3 * math.sin(t * 70)) * s * k, WHITE, 255 * k)

    # 2. The infinity sign is traced around the attacker...
    p = seg(t, 0.1, 0.26)
    if p is not None:
        _il_infinity(a, a.sx, a.sy - 8 * s, 62 * s, 1.0, t, TAU * ease_in_out(p))
        hx, hy = _lemniscate(a.sx, a.sy - 8 * s, 62 * s, TAU * ease_in_out(p))
        a.star(hx, hy, 14 * s, WHITE, 255, points=4, rot=t * 10)
        a.glow(hx, hy, 34 * s, IL_GOLD, 1.3)

    # ...then soars over the target, swelling, and blazes god rays across the field
    p = seg(t, 0.26, 0.58)
    if p is not None:
        fly = ease_in_out(min(1.0, p / 0.35))
        cx = lerp(a.sx, ix, fly)
        cy = lerp(a.sy - 8 * s, iy, fly) - 70 * s * math.sin(math.pi * fly)
        w = lerp(62, 100, fly) * s * (1 + 0.06 * math.sin(t * 40))
        if fly >= 1:
            rk = ease_out(min(1.0, (p - 0.35) / 0.4))
            _il_rays(a, cx, cy, 16, diag * rk, t * 1.6, IL_PALE, 70 * rk, spread=0.045, inner=0.1)
            _il_rays(a, cx, cy, 8, diag * 0.6 * rk, -t * 2.2, IL_GOLD, 60 * rk, spread=0.03, inner=0.15)
        _il_infinity(a, cx, cy, w, 1.0, t)
        a.glow(cx, cy, 64 * s, IL_PALE, 0.9)

    # 3. A ring of light spears forms around the target and plunges in, one by one
    p = seg(t, 0.32, 0.52)
    if p is not None:
        n = 12
        for i in range(n):
            ang = i * TAU / n + t * 2
            form = ease_out(min(1.0, p / 0.35))
            start = 0.4 + i * 0.035
            dive = ease_in(max(0.0, min(1.0, (p - start) / 0.12)))
            if dive >= 1:
                continue
            rr = lerp(124 * s, 6 * s, dive)
            x, y = a.tx + math.cos(ang) * rr, a.ty + math.sin(ang) * rr * 0.75
            a.shard(x, y, 22 * s * form, ang + math.pi, IL_GOLD, 240 * form, thin=0.22)
            a.shard(x, y, 14 * s * form, ang + math.pi, WHITE, 255 * form, thin=0.18)
            a.glow(x, y, 16 * s, IL_GOLD, 0.6 * form)
        for i in range(n):
            q = seg(p, 0.4 + i * 0.035 + 0.12, 0.4 + i * 0.035 + 0.3)
            if q is not None:
                ang = i * TAU / n
                a.star(a.tx + math.cos(ang) * 8 * s, a.ty + math.sin(ang) * 6 * s,
                       26 * s * (1 - q), WHITE, 255 * (1 - q), points=4, rot=ang)
                a.shake(3)

    # 4. Judgement: a prismatic pillar crashes down from the sign onto the target
    p = seg(t, 0.46, 0.57)
    if p is not None:
        reach = ease_in(min(1.0, p / 0.3))
        bottom = lerp(iy, a.ty + 40 * s, reach)
        throb = 0.9 + 0.1 * math.sin(t * 140)
        grow = 1 + 1.4 * ease_in(p)
        for w, col, al in ((100, IL_GOLD, 130), (70, IL_PALE, 180), (44, (255, 255, 235), 235), (18, WHITE, 255)):
            a.line(ix, 0, ix, bottom, col, al, w * s * throb * grow)
        for side in (-1, 1):
            for ci, col in enumerate(RAINBOW):
                xo = side * (52 + ci * 3.4) * s * throb * grow
                a.line(ix + xo, 0, ix + xo, bottom, col, 180, 2)
        for i in range(8):
            a.glow(ix, lerp(0, bottom, i / 7), 50 * s, IL_PALE, 1.0)
        a.rain(p, 26, WHITE, ix - 44 * s, ix + 44 * s, 0, bottom, length=20 * s, width=2,
               alpha=230, key='ilfall', speed=1.8)
        if reach >= 1:
            for kk in range(3):
                q = (p * 4 + kk / 3) % 1.0
                a.ellipse(a.tx, a.ty + 40 * s, 30 * s + 220 * s * q, (10 + 55 * q) * s, IL_GOLD, 230 * (1 - q), 3)
            a.glow(a.tx, a.ty, 90 * s, IL_PALE, 1.6)
            a.shake(6 + 8 * p)

    # 5. The flash: a sphere of pure light erupts from the target and swallows the screen
    p = seg(t, 0.52, 0.58)
    if p is not None:
        e = ease_in(p)
        r = 20 * s + diag * e
        a.circle(a.tx, a.ty, r + 30 * s, IL_PALE, 200)
        a.circle(a.tx, a.ty, r, WHITE, 255)
        a.ring(a.tx, a.ty, r + 30 * s, IL_GOLD, 220, max(3, int(8 * s)))
        a.shake(14)

    # 6. Whiteout. Only the light's own shape shows: gold and rainbow rings
    #    pulse outward, a vast infinity sign burns in, and a star blooms
    p = seg(t, 0.56, 0.86)
    if p is not None:
        fade_in = ease_out(min(1.0, p / 0.2))
        fade = fade_in * (1.0 if p < 0.7 else max(0.0, (1 - p) / 0.3))
        cx, cy = W / 2, H / 2
        _il_rays(a, cx, cy, 24, diag * 0.75, t * 0.8, (255, 238, 190), 120 * fade, spread=0.035, inner=0.08)
        for kk, col in enumerate(RAINBOW):
            q = (p * 1.4 + kk / len(RAINBOW)) % 1.0
            a.ring(cx, cy, 10 * s + diag * 0.55 * ease_out(q), col, 150 * (1 - q) * fade, 3)
        for kk in range(3):
            q = (p * 2 + kk / 3) % 1.0
            a.ring(cx, cy, 20 * s + diag * 0.5 * q, IL_GOLD, 200 * (1 - q) * fade, max(2, int(6 * s * (1 - q))))
        w = (150 + 30 * p) * s
        n = 64
        pts = [_lemniscate(cx, cy, w, TAU * i / n) for i in range(n + 1)]
        a.lines(pts, IL_GOLD, 230 * fade, max(4, int(12 * s)))
        a.lines(pts, (255, 228, 150), 255 * fade, max(2, int(6 * s)))
        bloom = ease_out(min(1.0, p / 0.35))
        a.star(cx, cy, 90 * s * bloom, IL_GOLD, 220 * fade, points=8, rot=-t * 2, inner=0.14)
        a.star(cx, cy, 60 * s * bloom, (255, 238, 190), 255 * fade, points=8, rot=t * 2 + 0.2, inner=0.16)
        a.circle(cx, cy, 10 * s * bloom, WHITE, 255 * fade)
        a.burst(cx, cy, p, 30, diag * 0.5, IL_GOLD, 4 * s, alpha=230 * fade, shape='star', key='ilwstar')
        if p < 0.4:
            a.shake(10 * (1 - p / 0.4))

    # 7. The light recedes: feathers of light drift down through the clearing
    #    glare, and the attacker's halo cracks and falls (it must recharge)
    p = seg(t, 0.8, 1.0)
    if p is not None:
        rng = a.rng('ilfeather')
        for i in range(18):
            x0 = a.tx + rng.uniform(-150, 150) * s
            delay = rng.uniform(0, 0.4)
            q = (p - delay) / 0.6
            if 0 <= q <= 1:
                x = x0 + math.sin(q * 6 + i) * 14 * s
                y = lerp(a.ty - 140 * s, a.ty + 50 * s, q)
                a.leaf(x, y, 7 * s, math.sin(q * 5 + i) * 0.8 + math.pi / 2, IL_GOLD, 230 * (1 - q))
                a.glow(x, y, 12 * s, IL_GOLD, 0.5 * (1 - q))
        a.glow(a.tx, a.ty, 110 * s, IL_PALE, 1.4 * (1 - p))
        for i in range(6):
            ang = i * TAU / 6 + 0.3
            d = 40 * s + 30 * s * ease_in(p)
            x, y = a.sx + math.cos(ang) * d, a.sy + math.sin(ang) * d + 40 * s * ease_in(p)
            a.shard(x, y, 9 * s, ang + 1.2, IL_GOLD, 220 * (1 - p), thin=0.3)


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


def _tp_clock(a, r, alpha, hand_ang):
    """Frosted clock face ringing the target: rim, 12 ticks and one hand."""
    if alpha <= 0:
        return
    x, y = a.tx, a.ty
    a.ring(x, y, r, ICE[1], alpha, 3)
    a.ring(x, y, r * 0.86, ICE[0], alpha * 0.5, 1)
    for i in range(12):
        ang = i * TAU / 12
        ln = (0.16 if i % 3 == 0 else 0.08) * r
        ca, sa = math.cos(ang), math.sin(ang)
        a.line(x + ca * r, y + sa * r, x + ca * (r - ln), y + sa * (r - ln), WHITE, alpha, 3 if i % 3 == 0 else 2)
    a.line(x, y, x + math.cos(hand_ang) * r * 0.75, y + math.sin(hand_ang) * r * 0.75, WHITE, alpha, 3)
    a.glow(x, y, r * 1.1, ICE[0], 0.35 * alpha / 255)


def _tp_jaw(a, hinge_ang, sgn, R, gap, w, alpha):
    """One icy pincer jaw: a tapering, serrated arc around the target that
    runs from the hinge at `hinge_ang` toward the far side, stopping `gap`
    radians short of it. sgn picks the upper or lower jaw."""
    if alpha <= 0:
        return
    x, y = a.tx, a.ty
    span = math.pi - gap
    n = 14
    outer, inner = [], []
    for i in range(n + 1):
        u = i / n
        th = hinge_ang + sgn * u * span
        half = (w * (1 - u) ** 0.8 + 1.5) / 2
        outer.append((x + math.cos(th) * (R + half), y + math.sin(th) * (R + half)))
        inner.append((x + math.cos(th) * (R - half), y + math.sin(th) * (R - half)))
    a.poly(outer + inner[::-1], ICE[0], alpha)
    a.lines(outer, WHITE, alpha, 2)
    for i in range(2, n, 3):   # serrated teeth along the inner edge
        u = i / n
        th = hinge_ang + sgn * u * span
        r0 = R - (w * (1 - u) ** 0.8 + 1.5) / 2
        a.poly([(x + math.cos(th - 0.07) * r0, y + math.sin(th - 0.07) * r0),
                (x + math.cos(th + 0.07) * r0, y + math.sin(th + 0.07) * r0),
                (x + math.cos(th) * (r0 - 7 * a.s), y + math.sin(th) * (r0 - 7 * a.s))], ICE[1], alpha)
    a.circle(x + math.cos(hinge_ang) * R, y + math.sin(hinge_ang) * R, w * 0.7, ICE[2], alpha)
    tip_ang = hinge_ang + sgn * span
    tx, ty = x + math.cos(tip_ang) * R, y + math.sin(tip_ang) * R
    a.star(tx, ty, 6 * a.s, WHITE, alpha, rot=tip_ang)
    a.glow(tx, ty, 16 * a.s, ICE[1], 0.6 * alpha / 255)


def anim_temporal_pincer(a):
    t = a.t
    s = a.s
    hinge = math.atan2(a.sy - a.ty, a.sx - a.tx)   # the jaws close in from the attacker's side
    # 1. Time stops: a frosted clock rings the target, its hand ticking in
    #    steps until the snap, then rewinding as the pincer slips away
    if t < 0.55:
        hand = -math.pi / 2 + math.floor(t * 20) / 20 * TAU * 1.2
    else:
        hand = -math.pi / 2 + 0.55 * TAU * 1.2 - ease_in(seg(t, 0.55, 1.0)) * TAU * 2.5
    _tp_clock(a, 85 * s, 230 * min(1, t / 0.2) * fade_late(t, 0.75), hand)
    a.tint((20, 50, 90), 80 * hump(min(1, t / 0.9)))
    # 2. The jaws open wide around it, then snap shut
    p = seg(t, 0.12, 0.55)
    if p is not None:
        e = ease_in(p)
        for sgn in (-1, 1):
            _tp_jaw(a, hinge, sgn, lerp(78, 40, e) * s, lerp(1.5, 0.08, e), 16 * s, 240 * min(1, p / 0.2))
    # 3. Snap: shards burst, and the jaws whirl away into the rewound moment
    p = seg(t, 0.55, 1.0)
    if p is not None:
        a.burst(a.tx, a.ty, p, 20, 120 * s, ICE[1], 7 * s, shape='shard', glow=0.3, gravity=50)
        _impact(a, p, ICE, 0.9, n=10)
        e = ease_in(p)
        for sgn in (-1, 1):
            _tp_jaw(a, hinge - e * TAU * 0.9, sgn, lerp(40, 150, e) * s, lerp(0.08, 0.9, e),
                    16 * s * (1 - 0.4 * e), 240 * (1 - p))
        if p < 0.3:
            a.shake(5 * (1 - p / 0.3))


def anim_temporal_pincer_return(a):
    """End of the next turn: the clock rewinds and the pincer spirals back
    around out of the frozen moment to snap shut on the target again."""
    t = a.t
    s = a.s
    hinge_end = math.atan2(a.sy - a.ty, a.sx - a.tx)
    # 1. The clock reappears, its hand spinning backwards
    hand = -math.pi / 2 - ease_in_out(min(1, t / 0.7)) * TAU * 3
    _tp_clock(a, 85 * s * (1 + 0.15 * hump(min(1, t / 0.7))),
              230 * min(1, t / 0.15) * fade_late(t, 0.7), hand)
    a.tint((20, 50, 90), 100 * hump(min(1, t / 0.95)))
    # 2. The pincer spirals back in from the far side, trailing afterimages
    p = seg(t, 0.1, 0.66)
    if p is not None:
        e = ease_in_out(p)
        fade_in = min(1, p / 0.15)
        for g in range(3, -1, -1):
            q = max(0.0, e - g * 0.06)
            h = hinge_end - (1 - q) * 3 * math.pi    # starts opposite, 1.5 turns round
            al = (240 if g == 0 else 70 / g) * fade_in
            for sgn in (-1, 1):
                _tp_jaw(a, h, sgn, lerp(230, 40, q) * s, lerp(1.3, 0.08, ease_in(q)), 16 * s, al)
    # 3. Snaps shut again, harder, shattering the clock
    p = seg(t, 0.64, 1.0)
    if p is not None:
        if p < 0.35:
            for sgn in (-1, 1):
                _tp_jaw(a, hinge_end, sgn, 40 * s, 0.08, 16 * s, 240 * (1 - p / 0.35))
        a.burst(a.tx, a.ty, p, 28, 160 * s, ICE[1], 8 * s, shape='shard', glow=0.3, gravity=60)
        a.burst(a.tx, a.ty, p, 12, 100 * s, WHITE, 3 * s, shape='star', key=1)
        a.ring(a.tx, a.ty, 30 * s + 130 * s * ease_out(p), WHITE, 230 * (1 - p), 4)
        _impact(a, p, ICE, 1.1, n=12, key=3)
        _strong_finish(a, p, ICE, 150, 8)


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


_FOSSIL_BONE = (235, 225, 200)
_FOSSIL_ROCK = ((150, 115, 80), (95, 70, 48), (60, 42, 30))   # face, side, outline


def _fossil_slab(a, x, y, w, h, tilt, alpha, glow=0.0):
    """A chunky stone slab with a dino skeleton pressed into it and glowing
    amber veins, centred on (x, y) and rotated by `tilt`."""
    ca, sa = math.cos(tilt), math.sin(tilt)

    def P(u, v):   # slab-local (-1..1) -> screen
        lx, ly = u * w / 2, v * h / 2
        return x + lx * ca - ly * sa, y + lx * sa + ly * ca

    outline = [P(-1, -0.7), P(-0.6, -1), P(0.3, -0.95), P(1, -0.6), P(0.95, 0.5),
               P(0.5, 1), P(-0.4, 0.95), P(-1, 0.55)]
    side = [(px + 5 * a.s, py + 7 * a.s) for px, py in outline]
    a.poly(side, _FOSSIL_ROCK[1], alpha)
    a.poly(outline, _FOSSIL_ROCK[0], alpha)
    a.lines(outline, _FOSSIL_ROCK[2], alpha, 3, closed=True)
    # skeleton imprint: skull, spine, ribs, tail
    bone_al = alpha * 0.9
    a.lines([P(-0.55, -0.05), P(-0.1, 0.0), P(0.35, 0.05), P(0.75, 0.25)], _FOSSIL_BONE, bone_al, 4)
    for k in range(5):
        u = -0.35 + k * 0.15
        a.lines([P(u, 0.0), P(u + 0.06, -0.35), P(u + 0.14, -0.45)], _FOSSIL_BONE, bone_al, 2)
        a.lines([P(u, 0.0), P(u + 0.06, 0.32), P(u + 0.14, 0.4)], _FOSSIL_BONE, bone_al, 2)
    skull = [P(-0.85, -0.2), P(-0.55, -0.35), P(-0.45, -0.05), P(-0.6, 0.12), P(-0.85, 0.05)]
    a.poly(skull, _FOSSIL_BONE, bone_al)
    a.circle(*P(-0.62, -0.12), 3 * a.s, _FOSSIL_ROCK[2], bone_al)   # eye socket
    # amber veins
    for pts in ((P(-0.9, 0.4), P(-0.5, 0.6), P(-0.2, 0.85)), (P(0.6, -0.8), P(0.7, -0.4), P(0.9, -0.1))):
        a.lines(pts, ANCIENT[1], alpha, 2)
    if glow > 0:
        a.glow(x, y, max(w, h) * 0.8, ANCIENT[0], glow)


def anim_fossil_break(a):
    t = a.t
    s = a.s
    W, H = 120 * s, 78 * s
    top = a.ty - 100 * s
    # 1. The fossil slab tears up out of the ground and hovers above the target
    p = seg(t, 0.0, 0.3)
    if p is not None:
        e = ease_out(p)
        y = lerp(a.ty + 60 * s, top, e)
        a.burst(a.tx, a.ty + 55 * s, p, 12, 70 * s, (130, 100, 70), 4 * s, shape='square',
                gravity=120, spread=(-math.pi * 0.95, -math.pi * 0.05))
        _fossil_slab(a, a.tx, y, W, H, 0.4 * (1 - e), 255 * min(1.0, p * 3), glow=0.6 * e)
        a.tint((30, 20, 5), 80 * p)
    p = seg(t, 0.3, 0.38)
    if p is not None:   # brief hang, wobbling, amber glow building
        _fossil_slab(a, a.tx, top - 4 * s * hump(p), W, H, math.sin(p * 20) * 0.04, 255, glow=0.9)
        a.tint((30, 20, 5), 80)
    # 2. SLAM down onto the target
    p = seg(t, 0.38, 0.48)
    if p is not None:
        y = lerp(top, a.ty - 10 * s, ease_in(p))
        for k in range(1, 4):   # speed lines above it
            a.line(a.tx - W * 0.4 + k * W * 0.2, y - H * 0.6 - 20 * s * k,
                   a.tx - W * 0.4 + k * W * 0.2, y - H * 0.6 - 5 * s, WHITE, 140, 2)
        _fossil_slab(a, a.tx, y, W, H, 0.0, 255, glow=0.6)
        a.tint((30, 20, 5), 80)
    # 3. It shatters: rock chunks, spinning bones, ancient dust, shockwave
    p = seg(t, 0.47, 1.0)
    if p is not None:
        e = ease_out(p)
        _strong_finish(a, p, ANCIENT, 100, 9)
        a.glow(a.tx, a.ty, 90 * s, ANCIENT[0], 0.8 * (1 - p))
        a.ring(a.tx, a.ty, 20 * s + 120 * s * e, ANCIENT[1], 220 * (1 - p), 5)
        a.ellipse(a.tx, a.ty + 45 * s, 240 * s * e, 40 * s * e, (150, 120, 80), 160 * (1 - p), 4)
        rng = a.rng('fb_chunks')
        for k in range(10):   # stone chunks
            ang = rng.uniform(-math.pi, 0.2) if k % 3 else rng.uniform(0, TAU)
            d = rng.uniform(60, 140) * s * e
            x = a.tx + math.cos(ang) * d
            y = a.ty + math.sin(ang) * d + 160 * s * p * p
            r = rng.uniform(8, 15) * s
            rot = p * rng.uniform(-6, 6)
            pts = [(x + math.cos(rot + j * TAU / 5) * r * (0.7 + 0.3 * (j % 2)),
                    y + math.sin(rot + j * TAU / 5) * r * (0.7 + 0.3 * (j % 2))) for j in range(5)]
            a.poly(pts, _FOSSIL_ROCK[k % 2], 255 * fade_late(p, 0.5))
            a.lines(pts, _FOSSIL_ROCK[2], 255 * fade_late(p, 0.5), 2, closed=True)
        rng = a.rng('fb_bones')
        for k in range(5):    # bone fragments spinning away
            ang = rng.uniform(-math.pi * 0.9, -math.pi * 0.1)
            d = rng.uniform(70, 130) * s * e
            _bone(a, a.tx + math.cos(ang) * d, a.ty + math.sin(ang) * d + 140 * s * p * p,
                  rng.uniform(22, 32) * s, p * rng.uniform(8, 14), _FOSSIL_BONE, 255 * fade_late(p, 0.55))
        a.burst(a.tx, a.ty, p, 22, 130 * s, ANCIENT[1], 3 * s, glow=0.3)
        a.star(a.tx, a.ty, 55 * s * (1 - p), (255, 235, 180), 230 * (1 - p), points=5, rot=0.2, inner=0.35)


_RAGE = (225, 55, 40)


def anim_raging_pursuit(a):
    t = a.t
    s = a.s
    # 1. Lock-on: a reticle snaps onto the target, the screen flushes red
    p = seg(t, 0.0, 0.2)
    if p is not None or t < 0.75:
        q = ease_out(p) if p is not None else 1.0
        r = lerp(120, 76, q) * s
        al = 230 * (min(1.0, t / 0.08)) * (1.0 if t < 0.6 else max(0.0, (0.75 - t) / 0.15))
        rot = (1 - q) * 1.2
        for k in range(4):
            ang = rot + k * math.pi / 2
            a.line(a.tx + math.cos(ang) * r * 0.6, a.ty + math.sin(ang) * r * 0.6,
                   a.tx + math.cos(ang) * r * 1.2, a.ty + math.sin(ang) * r * 1.2, _RAGE, al, 5)
        a.ring(a.tx, a.ty, r, _RAGE, al, 3)
        a.tint((60, 0, 0), 110 * min(1.0, t / 0.2) * (1.0 if t < 0.85 else max(0.0, (1 - t) / 0.15)))
    # The guard the target puts up (this move breaks through Defend)
    bar = seg(t, 0.05, 0.62)
    if bar is not None:
        R = 58 * s
        pts = [(a.tx + math.cos(i * math.pi / 3 + math.pi / 6) * R,
                a.ty + math.sin(i * math.pi / 3 + math.pi / 6) * R) for i in range(6)]
        flick = 0.75 + 0.25 * math.sin(t * 60) if bar > 0.6 else 1.0   # strained near the end
        a.poly(pts, (120, 170, 255), 45 * flick * min(1.0, bar * 4))
        a.lines(pts, (180, 210, 255), 200 * flick * min(1.0, bar * 4), 3, closed=True)
    # 2. Afterimage strikes from every side, each one faster than the last
    starts = (0.12, 0.27, 0.39, 0.49, 0.57)
    dirs = (0.85, 0.15, 1.35, -0.35, 0.5)
    for k, (t0, d) in enumerate(zip(starts, dirs)):
        dur = 0.16 - k * 0.015
        p = seg(t, t0, t0 + dur)
        if p is None:
            continue
        ang = d * math.pi
        ca, sa = math.cos(ang), math.sin(ang)
        dash = ease_in(min(1.0, p / 0.45))
        gx, gy = a.tx + ca * 130 * s * (1 - dash), a.ty + sa * 130 * s * (1 - dash)
        for j in range(3):   # the ghost and its trail
            back = j * 22 * s
            a.ellipse(gx + ca * back, gy + sa * back, 38 * s, 50 * s, (90, 20, 15), (220 - j * 60) * (1 - p))
            a.ellipse(gx + ca * back, gy + sa * back, 38 * s, 50 * s, _RAGE, (255 - j * 70) * (1 - p), 3)
            if j == 0:
                a.glow(gx, gy, 40 * s, _RAGE, 0.8 * (1 - p))
        if p > 0.4:
            a.slash(a.tx, a.ty, ang + math.pi / 2, 120 * s, (p - 0.4) / 0.6,
                    _RAGE if k % 2 else ANCIENT[0], 9, curve=0.15)
            a.slash(a.tx, a.ty, ang + math.pi / 2, 120 * s, (p - 0.4) / 0.6, (255, 230, 200), 3,
                    curve=0.15, glow=0)
            if p < 0.6:
                a.shake(3)
                a.star(a.tx, a.ty, 22 * s, WHITE, 230, points=4, rot=ang)
    # 3. The guard shatters as the final blow lands
    p = seg(t, 0.62, 0.95)
    if p is not None:
        rng = a.rng('rp_glass')
        for k in range(12):
            ang = k / 12 * TAU + rng.uniform(-0.2, 0.2)
            d = 58 * s + 90 * s * ease_out(p)
            a.shard(a.tx + math.cos(ang) * d, a.ty + math.sin(ang) * d + 50 * s * p * p,
                    rng.uniform(8, 13) * s, ang + p * 6, (180, 210, 255), 230 * (1 - p))
    # 4. Finishing X-slash and a heavy hit
    p1, p2 = seg(t, 0.64, 0.98), seg(t, 0.7, 1.0)
    for pp, ang in ((p1, math.pi * 0.25), (p2, -math.pi * 0.25)):
        a.slash(a.tx, a.ty, ang, 190 * s, pp, _RAGE, 16, curve=0.2, glow=0.9)
        a.slash(a.tx, a.ty, ang, 190 * s, pp, (255, 235, 200), 6, curve=0.2, glow=0)
    p = seg(t, 0.68, 1.0)
    if p is not None:
        _strong_finish(a, p, ((160, 20, 10), (255, 120, 80)), 150, 11)
        a.glow(a.tx, a.ty, 100 * s, _RAGE, 1.3 * (1 - p))
        a.ring(a.tx, a.ty, 20 * s + 130 * s * ease_out(p), ANCIENT[1], 220 * (1 - p), 5)
        a.burst(a.tx, a.ty, p, 22, 140 * s, ANCIENT[1], 4 * s, shape='streak', glow=0.3)
        a.burst(a.tx, a.ty, p, 10, 100 * s, _RAGE, 4 * s, key=1)


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


def _venom_drop(a, x, y, r, col, alpha):
    a.circle(x, y, r, col, alpha)
    a.poly([(x - r, y), (x + r, y), (x, y - r * 2.4)], col, alpha)
    a.circle(x - r * 0.35, y - r * 0.2, r * 0.3, (235, 255, 200), alpha * 0.8)   # wet shine


def _crack_shield(a, x, y, size, p):
    """Defense-down cue: a shield outline that cracks and crumbles over p 0..1."""
    al = 230 * hump(min(1.0, p * 1.4)) if p < 0.7 else 230 * max(0.0, (1 - p) / 0.3) * 0.6
    sx = 6 * a.s * ease_in(max(0.0, (p - 0.4) / 0.6))   # halves drift apart
    for side in (-1, 1):
        pts = [(x, y - size), (x + side * size * 0.85, y - size * 0.7),
               (x + side * size * 0.8, y + size * 0.1), (x, y + size)]
        pts = [(px + side * sx, py + sx * 0.5) for px, py in pts]
        a.lines(pts, (200, 220, 255), al, 3)
    if p > 0.3:   # the jagged crack down the middle
        q = min(1.0, (p - 0.3) / 0.2)
        crack = [(x, y - size), (x + 5 * a.s, y - size * 0.4), (x - 5 * a.s, y + size * 0.1),
                 (x + 4 * a.s, y + size * 0.6), (x, y + size)]
        a.lines(crack[:max(2, int(len(crack) * q))], POISON[1], al, 3)


def anim_venom_decay(a):
    t = a.t
    s = a.s
    ox, oy = a.tx, a.ty - 115 * s   # where the toxic orb gathers
    # 1. A churning orb of venom gathers above the target
    p = seg(t, 0.0, 0.32)
    if p is not None:
        r = 34 * s * ease_out(p)
        a.tint((10, 30, 5), 110 * p)
        a.glow(ox, oy, r * 2.4, POISON[1], 0.55 * p)
        a.circle(ox, oy, r, POISON[2], 240)
        a.circle(ox, oy, r * 0.8, POISON[0], 230)
        rng = a.rng('vd_orb')
        for k in range(9):   # swirling bubbles inside the orb
            ang = rng.uniform(0, TAU) + t * 14 * (1 if k % 2 else -1)
            d = rng.uniform(0.15, 0.6) * r
            a.circle(ox + math.cos(ang) * d, oy + math.sin(ang) * d,
                     rng.uniform(0.12, 0.25) * r, POISON[1], 220)
        for k in range(10):   # wisps being sucked in
            ang = k / 10 * TAU + t * 3
            d = lerp(110, 30, p) * s
            a.circle(ox + math.cos(ang) * d, oy + math.sin(ang) * d, 4 * s, POISON[1], 200 * p)
        if p > 0.6:
            a.shake(1.5)
    # 2. It ruptures: a heavy venom rain hammers the target
    p = seg(t, 0.3, 0.6)
    if p is not None:
        a.tint((10, 30, 5), 110)
        if p < 0.3:
            q = p / 0.3
            a.ring(ox, oy, 30 * s + 50 * s * q, POISON[1], 230 * (1 - q), 4)
            a.glow(ox, oy, 80 * s, POISON[1], 0.7 * (1 - q))
        rng = a.rng('vd_rain')
        for i in range(18):
            x = a.tx + rng.uniform(-75, 75) * s
            d = rng.uniform(0, 0.45)
            q = (p - d) / 0.4
            land = a.ty + rng.uniform(-25, 40) * s
            if 0 <= q <= 1:
                y = lerp(oy + 10 * s, land, ease_in(q))
                _venom_drop(a, x, y, rng.uniform(5, 8) * s, POISON[1], 245)
            elif 1 < q < 1.6:   # splat
                k = (q - 1) / 0.6
                a.ellipse(x, land, 26 * s * ease_out(k), 9 * s * ease_out(k), POISON[1], 220 * (1 - k))
        a.shake(3)
    # 3. Toxic cloud engulfs the target: sizzling bubbles, corrosion, defense cracks
    p = seg(t, 0.5, 1.0)
    if p is not None:
        e = ease_out(min(1.0, p / 0.4))
        fade = fade_late(p, 0.6)
        rng = a.rng('vd_cloud')
        for k in range(9):   # swelling cloud puffs
            ang = rng.uniform(0, TAU)
            d = rng.uniform(25, 60) * s
            wob = math.sin(t * 9 + k) * 5 * s
            x, y = a.tx + math.cos(ang) * d + wob, a.ty + math.sin(ang) * d * 0.7
            r = rng.uniform(30, 48) * s * e
            a.circle(x, y, r, POISON[2] if k % 3 == 0 else POISON[0], 120 * fade)
            a.glow(x, y, r * 1.2, (60, 110, 20), 0.35 * fade)
        for i in range(18):   # bubbles that rise and pop
            x = a.tx + rng.uniform(-70, 70) * s
            d = rng.uniform(0, 0.6)
            q = (p - d) / 0.35
            if 0 <= q <= 1:
                y = a.ty + 40 * s - q * 90 * s
                if q < 0.8:
                    a.ring(x, y, (3 + 7 * q) * s, POISON[1], 240, 2)
                else:
                    a.star(x, y, 10 * s, POISON[1], 255 * (1 - q) * 5, points=5, rot=i)
        for i in range(7):   # corrosion dripping down off the target
            x = a.tx + (i - 3) * 18 * s
            L = 45 * s * ease_out(p)
            a.line(x, a.ty + 20 * s, x, a.ty + 20 * s + L, POISON[1], 200 * fade, 4)
            a.circle(x, a.ty + 20 * s + L, 4 * s, POISON[1], 220 * fade)
        a.glow(a.tx, a.ty, 100 * s, (60, 110, 20), 0.5 * fade)
        _crack_shield(a, a.tx, a.ty - 5 * s, 34 * s, p)
        a.tint((10, 30, 5), 110 * (1 - p))


def anim_rushdown(a):
    t = a.t
    s = a.s
    ang = a.angle_to_target()
    ca, sa = math.cos(ang), math.sin(ang)
    nx, ny = -sa, ca
    # 1. A glint at the attacker as it kicks off
    p = seg(t, 0.0, 0.14)
    if p is not None:
        a.star(a.sx, a.sy - 20 * s, 26 * s * hump(p), WHITE, 255, points=4, rot=0.4)
        a.glow(a.sx, a.sy, 40 * s, ANCIENT[1], hump(p))
    # 2. Golden comet dash with afterimages and speed lines
    p = seg(t, 0.1, 0.4)
    if p is not None:
        q = ease_in(p)
        rng = a.rng('rush_lines')
        for k in range(9):   # speed lines streaming past, parallel to the dash
            off = rng.uniform(-70, 70) * s
            along = rng.uniform(0, 1)
            x, y = lerp(a.sx, a.tx, along) + nx * off, lerp(a.sy, a.ty, along) + ny * off
            L = rng.uniform(30, 70) * s
            a.line(x, y, x - ca * L, y - sa * L, (255, 245, 210), 150 * hump(p), 2)
        for k in range(6, 0, -1):   # afterimages trailing the comet
            qq = max(0.0, q - k * 0.06)
            x, y = a.travel(qq)
            a.circle(x, y, (24 - k * 2) * s, ANCIENT[0], 190 - k * 26)
        x, y = a.travel(q)
        a.line(x, y, x - ca * 80 * s, y - sa * 80 * s, ANCIENT[1], 240, int(16 * s))
        a.line(x, y, x - ca * 60 * s, y - sa * 60 * s, WHITE, 230, int(6 * s))
        a.circle(x, y, 19 * s, WHITE, 255)
        a.glow(x, y, 60 * s, ANCIENT[1], 1.3)
    # 3. Impact: star burst, sparks sprayed forward along the dash
    p = seg(t, 0.38, 0.8)
    if p is not None:
        e = ease_out(p)
        a.star(a.tx, a.ty, 55 * s * (1 - p * 0.5), WHITE, 255 * (1 - p), points=6, rot=ang, inner=0.3)
        a.ring(a.tx, a.ty, 12 * s + 80 * s * e, ANCIENT[1], 230 * (1 - p), 4)
        a.burst(a.tx, a.ty, p, 16, 110 * s, ANCIENT[1], 3 * s, shape='streak',
                spread=(ang - 0.7, ang + 0.7), glow=0.3)
        a.glow(a.tx, a.ty, 70 * s, ANCIENT[1], 1.2 * (1 - p))
        if p < 0.4:
            a.shake(5 * (1 - p / 0.4))
    # 4. Two quick follow-up jabs
    for k, (ox, oy) in enumerate(((-24, -14), (22, 12))):
        p = seg(t, 0.55 + k * 0.14, 0.78 + k * 0.14)
        if p is not None:
            x, y = a.tx + ox * s, a.ty + oy * s
            a.star(x, y, 40 * s * ease_out(p), (255, 240, 200), 255 * (1 - p), points=5, rot=k)
            a.glow(x, y, 26 * s, ANCIENT[1], 1.0 * (1 - p))
            if p < 0.3:
                a.shake(2)


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
    'Leaf Ultima': anim_leaf_ultima,
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
    'Velo Induction': anim_velo_induction,
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
    'Chain Rip': anim_chain_rip,
    'Dust Devil': anim_dust_devil,
    'Dust Devil (return)': anim_dust_devil_return,
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
    'Eternal Darkness': anim_eternal_darkness,
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
    'Infinite Light': anim_infinite_light,
    # Ice
    'Snowfall': anim_snowfall,
    'Freeze Blast': anim_freeze_blast,
    'Hyperfrost': anim_hyperfrost,
    'Hail Storm': anim_hail_storm,
    'Frozen Aura': anim_frozen_aura,
    'Deep Freeze': anim_deep_freeze,
    'Temporal Pincer': anim_temporal_pincer,
    'Temporal Pincer (return)': anim_temporal_pincer_return,
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

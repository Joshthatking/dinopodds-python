"""Draws the two celestial planet chunks — a lunar planet and a solar planet.

    python tools/make_planets.py

Writes, for each planet:
  assets/TILESET/<name>.png + <name>.tsx   the tileset (drawn in code)
  assets/WORLD/<MAP>.tmx                   a 32x32-tile map built from it
  assets/SCREENS/<lunar|solar>_encounter.png   its battle background

Both maps are standalone (not part of LOST_REGION.world): a roughly round
chunk of planet floating in space, with empty void around the edges so the
space backdrop (ANIM/space_bg.py) shows through. Void tiles are an invisible
collision tile so the player can't walk off the edge. The maps are plain
Tiled maps afterwards — open and edit them in Tiled like any other.

GBA-style pixel art: hard edges, small palettes, light from the top-left.

Tileset layout (32x32 tiles, 8 columns, ids below are tile ids; gid = id+1):
  0-5    ground variants (walkable)
  6      void blocker — fully transparent, collision
  8-23   edge tiles, id 8 + corner mask (TL=8, TR=4, BR=2, BL=1); collision
  24-31  1x1 props: 24/25 small marks (walkable), 26/27 rocks (collision),
         28/29 crystals (collision), 30/31 small ground details (walkable)
  32,33,40,41          2x2 feature A (walkable)
  34-36,42-44,50-52    3x3 feature   (walkable)
  37,38,45,46          2x2 feature B (walkable)
"""
import math
import os
import random
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame

TS = 32
COLS = 8
ROWS = 7
MAP_W = MAP_H = 32

VOID_ID = 6
EDGE_BASE = 8
COLLIDE_PROPS = (26, 27, 28, 29)
FEATURE_A = (32, 33, 40, 41)
FEATURE_BIG = (34, 35, 36, 42, 43, 44, 50, 51, 52)
FEATURE_B = (37, 38, 45, 46)
LIGHT = (-0.7071, -0.7071)    # light from the top-left


# ── shared helpers ───────────────────────────────────────────────────────

def tile_rect(tid, w=1, h=1):
    return pygame.Rect((tid % COLS) * TS, (tid // COLS) * TS, w * TS, h * TS)


def pick(shades, k):
    """Quantize 0..1 brightness into one of a few palette shades."""
    k = max(0.0, min(0.999, k))
    return shades[int(k * len(shades))]


BAYER4 = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def pick_dither(shades, k, px, py):
    """pick() with a 4x4 ordered dither between neighbouring shades —
    breaks smooth gradients into the crunchy GBA look instead of bands."""
    n = len(shades)
    return pick(shades, k + (BAYER4[py % 4][px % 4] / 16 - 0.47) / n)


def speckle_ground(rng, base, darks, lights, pits=0, glints=(), glint_n=0):
    """One 32x32 ground tile: flat base with scattered speckles."""
    s = pygame.Surface((TS, TS), pygame.SRCALPHA)
    s.fill(base)
    for _ in range(46):
        s.set_at((rng.randrange(TS), rng.randrange(TS)), rng.choice(darks))
    for _ in range(30):
        s.set_at((rng.randrange(TS), rng.randrange(TS)), rng.choice(lights))
    for _ in range(pits):   # tiny 2px pits, lit on the lower-right lip
        x, y = rng.randrange(1, TS - 2), rng.randrange(1, TS - 2)
        s.set_at((x, y), darks[-1]); s.set_at((x + 1, y), darks[-1])
        s.set_at((x + 1, y + 1), lights[-1])
    for _ in range(glint_n):
        s.set_at((rng.randrange(TS), rng.randrange(TS)), rng.choice(glints))
    return s


def edge_tile(ground, mask, rim_hi, rim_lo, outline):
    """Marching-squares edge: `ground` cut to the land side of the corners
    in `mask`, with a lit/shadowed rim and a dark outline at the edge."""
    tl, tr, br, bl = (mask >> 3) & 1, (mask >> 2) & 1, (mask >> 1) & 1, mask & 1
    s = pygame.Surface((TS, TS), pygame.SRCALPHA)
    for py in range(TS):
        v = (py + 0.5) / TS
        for px in range(TS):
            u = (px + 0.5) / TS
            f = tl * (1 - u) * (1 - v) + tr * u * (1 - v) + br * u * v + bl * (1 - u) * v
            if f < 0.5:
                continue
            if f < 0.56:
                s.set_at((px, py), outline)
            elif f < 0.64:
                # which way the edge faces: gradient of f points inland
                gx = (tr - tl) * (1 - v) + (br - bl) * v
                gy = (bl - tl) * (1 - u) + (br - tr) * u
                facing = -(gx * LIGHT[0] + gy * LIGHT[1])   # >0: edge faces the light
                s.set_at((px, py), rim_hi if facing > 0 else rim_lo)
            else:
                s.set_at((px, py), ground.get_at((px, py)))
    return s


def shaded_bowl(surf, cx, cy, r, shades, rim_shades, floor=0.45, rng=None):
    """Crater: a bowl lit on its lower-right inner wall, a raised rim lit on
    its upper-left, flat floor in the middle. Dithered, with a little
    speckle on the floor so it reads as rock rather than a smooth dish."""
    R = r * 1.18
    rng = rng or random.Random(int(cx * 31 + cy * 17 + r))
    for py in range(int(cy - R) - 1, int(cy + R) + 2):
        for px in range(int(cx - R) - 1, int(cx + R) + 2):
            if not (0 <= px < surf.get_width() and 0 <= py < surf.get_height()):
                continue
            dx, dy = px + 0.5 - cx, py + 0.5 - cy
            d = math.hypot(dx, dy) / r
            if d > 1.18:
                continue
            nx, ny = (dx / (d * r), dy / (d * r)) if d > 0 else (0, 0)
            lit = nx * LIGHT[0] + ny * LIGHT[1]          # >0 on the upper-left side
            if d >= 1.0:
                surf.set_at((px, py), pick_dither(rim_shades, 0.5 + 0.5 * lit, px, py))
            else:
                wall = max(0.0, (d - floor) / (1 - floor))
                k = 0.42 - 0.55 * lit * wall ** 0.8
                if rng.random() < 0.07:      # regolith speckle
                    k += rng.choice((-0.25, 0.25))
                surf.set_at((px, py), pick_dither(shades, k, px, py))


def rock(surf, cx, cy, rx, ry, shades, outline, rng, shadow=(0, 0, 0, 70)):
    """Lumpy boulder with a soft shadow to the lower-right."""
    sh = pygame.Surface((int(rx * 2.4), int(ry * 1.4)), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, shadow, sh.get_rect())
    surf.blit(sh, (cx - rx * 0.9, cy + ry * 0.35))
    bumps = [(rng.uniform(0, math.tau), rng.uniform(0.85, 1.12)) for _ in range(7)]

    def radius(a):
        return 1 + sum((b - 1) * math.cos(a - ph) for ph, b in bumps) * 0.5

    pts = []
    for py in range(int(cy - ry * 1.3), int(cy + ry * 1.3) + 1):
        for px in range(int(cx - rx * 1.3), int(cx + rx * 1.3) + 1):
            dx, dy = (px + 0.5 - cx) / rx, (py + 0.5 - cy) / ry
            d = math.hypot(dx, dy)
            if d <= radius(math.atan2(dy, dx)):
                pts.append((px, py, dx, dy, d))
    inside = {(p[0], p[1]) for p in pts}
    for px, py, dx, dy, d in pts:
        edge = any((px + ox, py + oy) not in inside for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            surf.set_at((px, py), outline)
            continue
        lit = (dx * LIGHT[0] + dy * LIGHT[1])
        surf.set_at((px, py), pick(shades, 0.5 + 0.55 * lit + 0.15 * (1 - d)))


def crystal(surf, cx, base_y, shards, light_col, mid_col, dark_col, outline, glow):
    """Cluster of upright crystal shards with a glow halo."""
    halo = pygame.Surface((TS, TS), pygame.SRCALPHA)
    for r in range(13, 2, -2):
        pygame.draw.circle(halo, (*glow, int(10 + (13 - r) * 3)), (cx, base_y - 9), r)
    surf.blit(halo, (0, 0))
    for (ox, h, w, lean) in shards:
        x = cx + ox
        top = (x + lean, base_y - h)
        left, right = (x - w, base_y - 2), (x + w, base_y - 2)
        bottom = (x, base_y + 1)
        pygame.draw.polygon(surf, mid_col, [top, right, bottom, left])
        pygame.draw.polygon(surf, light_col, [top, (x, base_y - 1), left])     # lit left face
        pygame.draw.polygon(surf, dark_col, [top, right, (x + 1, base_y - 1)])  # shaded right face
        pygame.draw.polygon(surf, outline, [top, right, bottom, left], 1)


def glow_disc(surf, cx, cy, r, rings):
    """Concentric glowing disc: rings = [(fraction_of_r, color), ...] outer→inner."""
    for frac, col in rings:
        pygame.draw.circle(surf, col, (int(cx), int(cy)), max(1, int(r * frac)))


# ── lunar planet ─────────────────────────────────────────────────────────

LUNAR = dict(
    base=(120, 122, 138),
    darks=[(104, 106, 122), (92, 94, 112), (78, 80, 98)],
    lights=[(138, 140, 156), (152, 154, 170), (170, 172, 188)],
    rim_hi=(184, 186, 202), rim_lo=(70, 72, 92), outline=(34, 32, 52),
    bowl=[(62, 64, 84), (78, 80, 98), (94, 96, 114), (112, 114, 130), (136, 138, 154)],
    bowl_rim=[(96, 98, 116), (124, 126, 142), (150, 152, 168), (176, 178, 194)],
    rock=[(66, 66, 84), (84, 86, 104), (104, 106, 124), (128, 130, 148), (156, 158, 176)],
    crystal=((200, 230, 255), (120, 160, 240), (70, 90, 190), (24, 26, 70), (110, 150, 255)),
    crystal2=((236, 210, 255), (170, 120, 240), (110, 70, 190), (34, 20, 70), (180, 120, 255)),
)


def draw_lunar(rng):
    sheet = pygame.Surface((COLS * TS, ROWS * TS), pygame.SRCALPHA)
    P = LUNAR
    grounds = [speckle_ground(rng, P['base'], P['darks'], P['lights'], pits=rng.randint(2, 5))
               for _ in range(6)]
    for i, g in enumerate(grounds):
        sheet.blit(g, tile_rect(i))
    for mask in range(16):
        if mask:
            sheet.blit(edge_tile(grounds[0], mask, P['rim_hi'], P['rim_lo'], P['outline']),
                       tile_rect(EDGE_BASE + mask))

    def stamp(tid, w=1, h=1):
        return sheet.subsurface(tile_rect(tid, w, h))

    # 24/25 small craters
    shaded_bowl(stamp(24), 16, 16, 9, P['bowl'], P['bowl_rim'])
    shaded_bowl(stamp(25), 13, 18, 6, P['bowl'], P['bowl_rim'])
    shaded_bowl(stamp(25), 23, 9, 3.5, P['bowl'], P['bowl_rim'])
    # 26/27 boulders
    rock(stamp(26), 16, 17, 10, 8, P['rock'], P['outline'], rng)
    rock(stamp(27), 12, 20, 7, 6, P['rock'], P['outline'], rng)
    rock(stamp(27), 23, 13, 5, 4, P['rock'], P['outline'], rng)
    # 28/29 lunar crystals (blue / violet)
    c = P['crystal']
    crystal(stamp(28), 16, 27, [(-6, 12, 3, -2), (0, 20, 4, 0), (6, 14, 3, 2)], c[0], c[1], c[2], c[3], c[4])
    c = P['crystal2']
    crystal(stamp(29), 15, 27, [(-4, 15, 3, -1), (4, 11, 3, 2)], c[0], c[1], c[2], c[3], c[4])
    # 30 pebble scatter, 31 dust streak
    s = stamp(30)
    for _ in range(6):
        x, y = rng.randrange(4, 28), rng.randrange(4, 28)
        pygame.draw.rect(s, P['rock'][1], (x, y, 2, 2)); s.set_at((x, y), P['rock'][4])
    s = stamp(31)
    for i in range(18):
        x = 4 + i * 1.4
        s.set_at((int(x), int(20 - i * 0.6 + rng.uniform(-1, 1))), P['lights'][2])
    # 2x2 craters (A and B), 3x3 great crater
    shaded_bowl(stamp(32, 2, 2), 32, 32, 22, P['bowl'], P['bowl_rim'])
    shaded_bowl(stamp(37, 2, 2), 30, 34, 17, P['bowl'], P['bowl_rim'])
    shaded_bowl(stamp(37, 2, 2), 51, 13, 6, P['bowl'], P['bowl_rim'])
    big = stamp(34, 3, 3)
    shaded_bowl(big, 48, 48, 36, P['bowl'], P['bowl_rim'], floor=0.4)
    shaded_bowl(big, 40, 54, 6, P['bowl'], P['bowl_rim'])   # a small crater inside the big one
    for _ in range(8):   # rubble on the bowl floor
        x, y = rng.randrange(36, 62), rng.randrange(38, 60)
        pygame.draw.rect(big, P['rock'][1], (x, y, 2, 2)); big.set_at((x, y), P['rock'][3])
    return sheet


# ── solar planet ─────────────────────────────────────────────────────────

SOLAR = dict(
    base=(226, 184, 116),
    darks=[(210, 166, 100), (196, 150, 86), (176, 128, 70)],
    lights=[(238, 202, 138), (246, 216, 156), (252, 232, 182)],
    glints=[(255, 246, 200), (255, 236, 150)],
    rim_hi=(255, 236, 170), rim_lo=(150, 96, 52), outline=(84, 44, 28),
    rock=[(112, 66, 40), (142, 88, 50), (176, 116, 62), (208, 150, 80), (236, 190, 110)],
    crystal=((255, 255, 236), (255, 224, 120), (230, 150, 50), (110, 56, 24), (255, 220, 120)),
    crystal2=((255, 250, 250), (255, 190, 150), (230, 110, 80), (110, 40, 30), (255, 170, 120)),
)
FIRE = [(255, 252, 230), (255, 236, 140), (255, 196, 70), (246, 134, 40), (200, 80, 30)]


def fissure(surf, pts, core=FIRE[1], edge=FIRE[3], hot=FIRE[0]):
    pygame.draw.lines(surf, edge, False, pts, 3)
    pygame.draw.lines(surf, core, False, pts, 1)
    for p in pts[1:-1]:
        surf.set_at((int(p[0]), int(p[1])), hot)


def draw_solar(rng):
    sheet = pygame.Surface((COLS * TS, ROWS * TS), pygame.SRCALPHA)
    P = SOLAR
    grounds = [speckle_ground(rng, P['base'], P['darks'], P['lights'], pits=rng.randint(0, 2),
                              glints=P['glints'], glint_n=rng.randint(2, 5)) for _ in range(6)]
    # a couple of the variants get faint engraved sun-lines
    for g in grounds[3:5]:
        y = rng.randrange(8, 24)
        pygame.draw.line(g, P['darks'][1], (3, y), (28, y + rng.randint(-3, 3)))
        pygame.draw.line(g, P['lights'][1], (3, y + 1), (28, y + 1))
    for i, g in enumerate(grounds):
        sheet.blit(g, tile_rect(i))
    for mask in range(16):
        if mask:
            sheet.blit(edge_tile(grounds[0], mask, P['rim_hi'], P['rim_lo'], P['outline']),
                       tile_rect(EDGE_BASE + mask))

    def stamp(tid, w=1, h=1):
        return sheet.subsurface(tile_rect(tid, w, h))

    # 24/25 light fissures
    fissure(stamp(24), [(4, 22), (10, 18), (15, 20), (21, 12), (28, 10)])
    fissure(stamp(25), [(8, 6), (12, 13), (10, 19), (16, 25), (22, 27)])
    # 26/27 sun-baked rocks
    rock(stamp(26), 16, 17, 10, 8, P['rock'], P['outline'], rng, shadow=(90, 40, 10, 70))
    rock(stamp(27), 12, 20, 7, 6, P['rock'], P['outline'], rng, shadow=(90, 40, 10, 70))
    rock(stamp(27), 23, 12, 5, 4, P['rock'], P['outline'], rng, shadow=(90, 40, 10, 70))
    # 28/29 sun crystals (gold / rose)
    c = P['crystal']
    crystal(stamp(28), 16, 27, [(-6, 13, 3, -2), (0, 21, 4, 0), (6, 15, 3, 2)], c[0], c[1], c[2], c[3], c[4])
    c = P['crystal2']
    crystal(stamp(29), 15, 27, [(-4, 16, 3, -1), (4, 12, 3, 2)], c[0], c[1], c[2], c[3], c[4])
    # 30 sunbloom flowers, 31 small glowing glyph
    s = stamp(30)
    for fx, fy in ((10, 12), (21, 19), (13, 23)):
        pygame.draw.line(s, (120, 150, 60), (fx, fy + 2), (fx, fy + 6))
        for a in range(8):
            ang = a * math.tau / 8
            s.set_at((int(fx + math.cos(ang) * 2.5), int(fy + math.sin(ang) * 2.5)), FIRE[2])
        pygame.draw.circle(s, FIRE[0], (fx, fy), 1)
        s.set_at((fx, fy), FIRE[3])
    s = stamp(31)
    pygame.draw.circle(s, P['darks'][2], (16, 16), 7, 1)
    for a in range(8):
        ang = a * math.tau / 8
        pygame.draw.line(s, FIRE[2], (16 + math.cos(ang) * 3, 16 + math.sin(ang) * 3),
                         (16 + math.cos(ang) * 6, 16 + math.sin(ang) * 6))
    pygame.draw.circle(s, FIRE[1], (16, 16), 2)

    # 2x2 A — sun pool: a basin of molten light
    s = stamp(32, 2, 2)
    pygame.draw.circle(s, P['outline'], (32, 32), 26)
    pygame.draw.circle(s, P['rock'][2], (32, 32), 25)
    pygame.draw.circle(s, P['rock'][3], (31, 31), 23)
    glow_disc(s, 32, 32, 21, [(1.0, FIRE[4]), (0.85, FIRE[3]), (0.68, FIRE[2]), (0.48, FIRE[1]), (0.25, FIRE[0])])
    for _ in range(14):    # bubbles / shimmer
        a, d = rng.uniform(0, math.tau), rng.uniform(4, 17)
        s.set_at((int(32 + math.cos(a) * d), int(32 + math.sin(a) * d)), FIRE[0])

    # 2x2 B — solar vent: dark mound with a glowing mouth
    s = stamp(37, 2, 2)
    sh = pygame.Surface((54, 22), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (90, 40, 10, 80), sh.get_rect())
    s.blit(sh, (8, 40))
    pygame.draw.ellipse(s, P['outline'], (8, 18, 48, 36))
    pygame.draw.ellipse(s, P['rock'][1], (9, 19, 46, 34))
    pygame.draw.ellipse(s, P['rock'][2], (11, 20, 36, 26))
    pygame.draw.ellipse(s, P['rock'][3], (14, 21, 22, 14))
    pygame.draw.ellipse(s, P['outline'], (20, 24, 24, 12))
    pygame.draw.ellipse(s, FIRE[3], (21, 25, 22, 10))
    pygame.draw.ellipse(s, FIRE[1], (25, 27, 14, 6))
    pygame.draw.ellipse(s, FIRE[0], (29, 28, 6, 3))
    fissure(s, [(18, 44), (24, 38), (28, 41)])
    fissure(s, [(44, 46), (40, 40), (42, 36)])

    # 3x3 — sunburst dais: a round platform engraved with glowing rays
    s = stamp(34, 3, 3)
    c = (48, 48)
    pygame.draw.circle(s, P['outline'], c, 44)
    pygame.draw.circle(s, P['rock'][3], c, 43)
    pygame.draw.circle(s, (244, 222, 176), c, 40)
    pygame.draw.circle(s, (252, 238, 204), (46, 46), 36)
    pygame.draw.circle(s, P['rock'][3], c, 40, 2)
    for a in range(12):
        ang = a * math.tau / 12
        p1 = (c[0] + math.cos(ang) * 13, c[1] + math.sin(ang) * 13)
        p2 = (c[0] + math.cos(ang) * 35, c[1] + math.sin(ang) * 35)
        pygame.draw.line(s, FIRE[3], p1, p2, 3)
        pygame.draw.line(s, FIRE[1], p1, p2, 1)
    for a in range(24):  # rim studs
        ang = a * math.tau / 24
        s.set_at((int(c[0] + math.cos(ang) * 38), int(c[1] + math.sin(ang) * 38)), P['rock'][1])
    glow_disc(s, 48, 48, 12, [(1.0, P['outline']), (0.9, FIRE[3]), (0.7, FIRE[2]), (0.45, FIRE[1]), (0.2, FIRE[0])])
    return sheet


# ── map building ─────────────────────────────────────────────────────────

def land_corners(rng, radius):
    """33x33 corner grid: True where the planet's surface is."""
    waves = [(rng.uniform(0, math.tau), k, rng.uniform(0.25, 0.9)) for k in (2, 3, 5, 7)]
    c = MAP_W / 2
    grid = {}
    for cy in range(MAP_H + 1):
        for cx in range(MAP_W + 1):
            a = math.atan2(cy - c, cx - c)
            r = radius + sum(amp * math.sin(k * a + ph) for ph, k, amp in waves)
            grid[(cx, cy)] = math.hypot(cx - c, cy - c) < r
    return grid


def build_layers(rng, grid, spawn, big_at_spawn, counts):
    ground = [[0] * MAP_W for _ in range(MAP_H)]
    full = set()
    for y in range(MAP_H):
        for x in range(MAP_W):
            mask = (grid[(x, y)] << 3) | (grid[(x + 1, y)] << 2) | (grid[(x + 1, y + 1)] << 1) | grid[(x, y + 1)]
            if mask == 15:
                ground[y][x] = rng.choices(range(6), weights=(30, 30, 20, 8, 8, 4))[0] + 1
                full.add((x, y))
            elif mask == 0:
                ground[y][x] = VOID_ID + 1
            else:
                ground[y][x] = EDGE_BASE + mask + 1
    details = [[0] * MAP_W for _ in range(MAP_H)]
    taken = set()
    sx, sy = spawn

    def place(ids, w, h, x, y):
        cells = [(x + i, y + j) for j in range(h) for i in range(w)]
        for (cx, cy), tid in zip(cells, ids):
            details[cy][cx] = tid + 1
        # keep a 1-tile gap around each feature
        for cx, cy in cells:
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    taken.add((cx + ox, cy + oy))

    def fits(w, h, x, y, keep_clear):
        for j in range(h):
            for i in range(w):
                p = (x + i, y + j)
                if p not in full or p in taken:
                    return False
                if keep_clear and abs(p[0] - sx) <= 2 and abs(p[1] - sy) <= 2:
                    return False
        return True

    if big_at_spawn:
        place(FEATURE_BIG, 3, 3, sx - 1, sy - 2)
    for ids, w, h, n in counts:
        for _ in range(n):
            for _try in range(200):
                x, y = rng.randrange(MAP_W - w + 1), rng.randrange(MAP_H - h + 1)
                if fits(w, h, x, y, keep_clear=True):
                    place(ids if isinstance(ids, tuple) else (rng.choice(ids),), w, h, x, y)
                    break
    return ground, details


def write_tsx(path, name, png_name):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<tileset version="1.10" tiledversion="1.12.1" name="{name}" tilewidth="{TS}" tileheight="{TS}" '
        f'tilecount="{COLS * ROWS}" columns="{COLS}">',
        f' <image source="../TILESET/{png_name}" width="{COLS * TS}" height="{ROWS * TS}"/>',
    ]
    solid = [VOID_ID] + [EDGE_BASE + m for m in range(1, 15)] + list(COLLIDE_PROPS)
    for tid in sorted(solid):
        lines += [f' <tile id="{tid}">', '  <properties>',
                  '   <property name="collision" type="bool" value="true"/>',
                  '  </properties>', ' </tile>']
    lines.append('</tileset>')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')


def write_tmx(path, tsx_name, ground, details):
    def csv(rows):
        return ',\n'.join(','.join(str(v) for v in row) for row in rows)

    out = f'''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" tiledversion="1.12.1" orientation="orthogonal" renderorder="right-down" width="{MAP_W}" height="{MAP_H}" tilewidth="{TS}" tileheight="{TS}" infinite="0" nextlayerid="3" nextobjectid="1">
 <tileset firstgid="1" source="../TILESET/{tsx_name}"/>
 <layer id="1" name="Ground 1" width="{MAP_W}" height="{MAP_H}">
  <data encoding="csv">
{csv(ground)}
</data>
 </layer>
 <layer id="2" name="Details 2" width="{MAP_W}" height="{MAP_H}">
  <data encoding="csv">
{csv(details)}
</data>
 </layer>
</map>
'''
    with open(path, 'w', encoding='utf-8') as f:
        f.write(out)


# ── battle backgrounds ───────────────────────────────────────────────────
# 640x480 like the other assets/SCREENS/*_encounter.png: sky + planet ground
# above y=350 with the enemy/player platforms where the battle UI expects
# them, and the bottom text panels copied from horizon_encounter.png.

BATTLE_W, BATTLE_H, PANEL_Y, HORIZON_Y = 640, 480, 350, 150
ENEMY_PLAT = pygame.Rect(318, 112, 310, 100)
PLAYER_PLAT = pygame.Rect(2, 262, 390, 95)


def battle_bg(sheet, sky, rim_hi, rim_lo, floor, glow_cols, decals, rng):
    s = pygame.Surface((BATTLE_W, BATTLE_H))
    sky.draw(s, 0, 0, 3.0)
    # ground: the planet's own regolith tile, hazier toward the horizon
    ground = pygame.Surface((BATTLE_W, PANEL_Y - HORIZON_Y))
    tile = sheet.subsurface(tile_rect(0)).copy()
    for y in range(0, ground.get_height(), TS):
        for x in range(0, BATTLE_W, TS):
            ground.blit(tile, (x, y))
    for d in decals:   # scattered craters / rocks / fissures, smaller near the horizon
        y = rng.uniform(4, ground.get_height() - 20)
        k = 0.45 + 0.55 * y / ground.get_height()
        img = pygame.transform.scale(sheet.subsurface(tile_rect(d)), (int(TS * k), int(TS * k)))
        ground.blit(img, (rng.uniform(0, BATTLE_W - TS), y))
    haze = pygame.Surface(ground.get_size(), pygame.SRCALPHA)
    for y in range(haze.get_height()):
        a = int(150 * (1 - y / haze.get_height()) ** 2)
        pygame.draw.line(haze, (*floor[0], a), (0, y), (BATTLE_W, y))
    ground.blit(haze, (0, 0))
    s.blit(ground, (0, HORIZON_Y))
    pygame.draw.line(s, rim_hi, (0, HORIZON_Y), (BATTLE_W, HORIZON_Y), 2)
    pygame.draw.line(s, rim_lo, (0, HORIZON_Y + 2), (BATTLE_W, HORIZON_Y + 2), 1)
    for plat in (ENEMY_PLAT, PLAYER_PLAT):
        shadow = pygame.Surface(plat.size, pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), shadow.get_rect())
        s.blit(shadow, plat.move(4, 8))
        pygame.draw.ellipse(s, rim_lo, plat)
        pygame.draw.ellipse(s, rim_hi, plat.inflate(-6, -6))
        inner = plat.inflate(-plat.width * 0.12, -plat.height * 0.22)
        pygame.draw.ellipse(s, floor[1], inner)
        pygame.draw.ellipse(s, floor[2], inner.inflate(-inner.width * 0.15, -inner.height * 0.2).move(0, 3))
        # glowing marks around the rim (crystals for the moon, sun-studs for the sun)
        for i in range(14):
            a = i * math.tau / 14
            x = plat.centerx + math.cos(a) * plat.width * 0.47
            y = plat.centery + math.sin(a) * plat.height * 0.42
            col = glow_cols[i % len(glow_cols)]
            pygame.draw.circle(s, tuple(c // 3 for c in col), (int(x), int(y)), 5)
            pygame.draw.circle(s, col, (int(x), int(y)), 2)
    panels = pygame.image.load(os.path.join('assets', 'SCREENS', 'horizon_encounter.png'))
    s.blit(panels.subsurface((0, PANEL_Y, BATTLE_W, BATTLE_H - PANEL_Y)), (0, PANEL_Y))
    return s


def make_battle_bgs():
    import sys
    sys.path.insert(0, os.getcwd())
    from ANIM.space_bg import LunarBackground, SolarBackground
    pygame.display.set_mode((1, 1))
    lunar = pygame.image.load(os.path.join('assets', 'TILESET', 'lunar_planet.png'))
    solar = pygame.image.load(os.path.join('assets', 'TILESET', 'solar_planet.png'))
    out = battle_bg(lunar, LunarBackground(), LUNAR['rim_hi'], LUNAR['outline'],
                    [(30, 20, 60), LUNAR['bowl'][1], LUNAR['bowl'][2]],
                    [(150, 190, 255), (200, 150, 255)], [24, 25, 24, 26, 25, 27, 24, 30, 31],
                    random.Random(50))
    pygame.image.save(out, os.path.join('assets', 'SCREENS', 'lunar_encounter.png'))
    out = battle_bg(solar, SolarBackground(), SOLAR['rim_hi'], SOLAR['outline'],
                    [(120, 60, 20), SOLAR['rock'][3], SOLAR['lights'][1]],
                    [(255, 220, 120), (255, 160, 70)], [24, 25, 26, 24, 30, 25, 27, 31],
                    random.Random(51))
    pygame.image.save(out, os.path.join('assets', 'SCREENS', 'solar_encounter.png'))
    print('wrote lunar_encounter.png and solar_encounter.png')


PLANETS = [
    # name, map file, draw fn, seed, radius, big feature at spawn?, feature counts
    ('lunar_planet', 'LUNAR_PLANET.tmx', draw_lunar, 4242, 13.4, False, [
        (FEATURE_BIG, 3, 3, 2),
        (FEATURE_A, 2, 2, 3),
        (FEATURE_B, 2, 2, 3),
        ((24, 25), 1, 1, 14),
        ((26, 27), 1, 1, 9),
        ((28, 29), 1, 1, 6),
        ((30, 31), 1, 1, 12),
    ]),
    ('solar_planet', 'SOLAR_PLANET.tmx', draw_solar, 777, 13.4, True, [
        (FEATURE_A, 2, 2, 3),
        (FEATURE_B, 2, 2, 3),
        ((24, 25), 1, 1, 14),
        ((26, 27), 1, 1, 8),
        ((28, 29), 1, 1, 7),
        ((30, 31), 1, 1, 12),
    ]),
]
SPAWN = (16, 17)


def main():
    pygame.init()
    for name, map_file, draw, seed, radius, big_at_spawn, counts in PLANETS:
        rng = random.Random(seed)
        sheet = draw(rng)
        png = f'{name}.png'
        pygame.image.save(sheet, os.path.join('assets', 'TILESET', png))
        write_tsx(os.path.join('assets', 'TILESET', f'{name}.tsx'), name, png)
        grid = land_corners(rng, radius)
        ground, details = build_layers(rng, grid, SPAWN, big_at_spawn, counts)
        write_tmx(os.path.join('assets', 'WORLD', map_file), f'{name}.tsx', ground, details)
        print(f'wrote {name}.png/.tsx and {map_file}')
    make_battle_bgs()


if __name__ == '__main__':
    main()

"""Draws the Episc Chateau (haunted mansion) tileset for TOWN2_4.

    python tools/make_mansion.py

Writes assets/TILESET/haunted_mansion.png + haunted_mansion.tsx.
Everything is drawn in code at 1:1 pixel scale in the same GBA-style 3/4
view as the other buildings: walls face the camera, roofs recede upward,
1px dark outlines, light from the top-left.

Tileset layout (32x32 tiles, 14 columns):
  rows 0-10  the mansion itself, 14x11 tiles — every tile is solid
  row  11    props (see PROPS below for the column of each)
"""
import os
import random
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
import pygame

TS = 32
COLS = 14
MANSION_ROWS = 11
W, H = COLS * TS, MANSION_ROWS * TS            # 448 x 352
OUT_PNG = os.path.join('assets', 'TILESET', 'haunted_mansion.png')
OUT_TSX = os.path.join('assets', 'TILESET', 'haunted_mansion.tsx')

# ── palette ──────────────────────────────────────────────────────────────
OUT = (27, 22, 38)
W_HI, W_MID, W_LO, W_DK = (118, 102, 136), (90, 76, 108), (68, 56, 84), (50, 40, 64)
T_HI, T_MID, T_LO = (206, 196, 176), (166, 154, 136), (118, 106, 96)
R_HI, R_MID, R_LO, R_DK = (92, 96, 126), (66, 70, 98), (48, 50, 74), (34, 35, 54)
G1, G2, G3 = (255, 228, 128), (244, 170, 62), (186, 98, 40)
D1, D2, D3 = (36, 42, 64), (56, 70, 100), (92, 112, 144)
E1, E2, E3 = (200, 255, 160), (120, 210, 96), (60, 130, 60)
B_HI, B_MID, B_LO = (140, 82, 72), (108, 60, 58), (76, 42, 44)
S_HI, S_MID, S_LO = (134, 128, 124), (100, 96, 94), (70, 66, 70)
WD_HI, WD_MID, WD_LO = (116, 80, 58), (88, 60, 44), (60, 40, 32)
I_HI, I_MID, I_LO = (98, 134, 72), (62, 98, 54), (38, 66, 42)
IRON, IRON_HI = (34, 32, 44), (86, 84, 104)

rng = random.Random(1313)


# ── helpers ──────────────────────────────────────────────────────────────

def clip_to(pattern, poly, size=(W, H)):
    """Return `pattern` cut to polygon `poly` (transparent elsewhere)."""
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), poly)
    out = pattern.copy()
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return out


def shingles(base, dark, hi, row_h=6, brick_w=8, size=(W, H), seed=0):
    """Slate shingle rows: staggered tabs with a dark lower edge."""
    r = random.Random(seed)
    s = pygame.Surface(size, pygame.SRCALPHA)
    s.fill(base)
    for i, y in enumerate(range(0, size[1], row_h)):
        pygame.draw.line(s, dark, (0, y + row_h - 1), (size[0], y + row_h - 1))
        off = (i % 2) * (brick_w // 2)
        for x in range(-brick_w + off, size[0], brick_w):
            pygame.draw.line(s, dark, (x, y), (x, y + row_h - 2))
            if r.random() < 0.35:
                pygame.draw.line(s, hi, (x + 1, y), (x + brick_w - 3, y))
            if r.random() < 0.012:   # a missing / slipped shingle
                pygame.draw.rect(s, R_DK, (x + 1, y + 1, brick_w - 3, row_h - 2))
    return s


def siding(base, dark, hi, board=6, size=(W, H)):
    s = pygame.Surface(size, pygame.SRCALPHA)
    s.fill(base)
    for y in range(0, size[1], board):
        pygame.draw.line(s, hi, (0, y), (size[0], y))
        pygame.draw.line(s, dark, (0, y + board - 1), (size[0], y + board - 1))
    return s


def plane(surf, poly, pattern, outline=True):
    surf.blit(clip_to(pattern, poly), (0, 0))
    if outline:
        pygame.draw.polygon(surf, OUT, poly, 1)


def rect_o(surf, color, r, outline=OUT):
    pygame.draw.rect(surf, color, r)
    pygame.draw.rect(surf, outline, r, 1)


def window(surf, x, y, w, h, kind='dark', shutter=None):
    """Tall arched window with a bone frame. kind: glow, green, dark,
    cracked, boarded, ghost."""
    frame = pygame.Rect(x - 2, y - 2, w + 4, h + 4)
    # arched frame
    pygame.draw.rect(surf, T_MID, (frame.x, frame.y + w // 2, frame.w, frame.h - w // 2))
    pygame.draw.ellipse(surf, T_MID, (frame.x, frame.y, frame.w, w + 4))
    glass = pygame.Surface((w, h), pygame.SRCALPHA)
    if kind in ('glow', 'green'):
        c1, c2, c3 = (G1, G2, G3) if kind == 'glow' else (E1, E2, E3)
        glass.fill(c2)
        pygame.draw.rect(glass, c1, (2, w // 2, w - 4, h - w // 2 - 4))
        pygame.draw.rect(glass, c3, (0, h - 4, w, 4))
    else:
        glass.fill(D1)
        for k in range(0, w + h, 7):   # faint diagonal reflection
            pygame.draw.line(glass, D2, (k, 0), (k - h, h))
        pygame.draw.line(glass, D3, (2, w // 2 + 2), (2, h - 3))
    # arch the glass
    m = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(m, (255, 255, 255, 255), (0, w // 2, w, h - w // 2))
    pygame.draw.ellipse(m, (255, 255, 255, 255), (0, 0, w, w))
    glass.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(glass, (x, y))
    # mullions
    pygame.draw.line(surf, T_LO, (x + w // 2, y + 2), (x + w // 2, y + h - 1))
    pygame.draw.line(surf, T_LO, (x, y + h // 2 + 2), (x + w - 1, y + h // 2 + 2))
    if kind == 'cracked':
        px, py = x + 3, y + w // 2
        for _ in range(4):
            nx, ny = px + rng.randint(2, 5), py + rng.randint(3, 7)
            pygame.draw.line(surf, D3, (px, py), (min(nx, x + w - 2), min(ny, y + h - 2)))
            px, py = nx, ny
    if kind == 'ghost':
        gx, gy = x + w // 2, y + h // 2 - 2
        pygame.draw.ellipse(surf, (200, 210, 230), (gx - 5, gy - 6, 10, 14))
        pygame.draw.rect(surf, (200, 210, 230), (gx - 5, gy, 10, 8))
        surf.set_at((gx - 2, gy - 2), OUT); surf.set_at((gx + 2, gy - 2), OUT)
        pygame.draw.line(surf, OUT, (gx - 1, gy + 2), (gx + 1, gy + 2))
    if kind == 'boarded':
        for k, (dy, tilt) in enumerate(((6, 3), (h // 2, -4), (h - 8, 2))):
            p1, p2 = (x - 3, y + dy - tilt), (x + w + 2, y + dy + tilt)
            pygame.draw.line(surf, OUT, (p1[0], p1[1] + 3), (p2[0], p2[1] + 3), 1)
            pygame.draw.line(surf, WD_MID, p1, p2, 3)
            pygame.draw.line(surf, WD_HI, p1, p2, 1)
            surf.set_at((p1[0] + 2, p1[1]), OUT); surf.set_at((p2[0] - 2, p2[1]), OUT)
    # frame outline + sill
    pygame.draw.arc(surf, OUT, (frame.x, frame.y, frame.w, w + 4), 0, 3.1416, 1)
    pygame.draw.line(surf, OUT, (frame.x, frame.y + w // 2 + 2), (frame.x, frame.bottom))
    pygame.draw.line(surf, OUT, (frame.right - 1, frame.y + w // 2 + 2), (frame.right - 1, frame.bottom))
    rect_o(surf, T_HI, (frame.x - 2, frame.bottom - 1, frame.w + 4, 4))
    if shutter:
        sx = frame.x - 9 if shutter == 'left' else frame.right + 1
        sh = pygame.Rect(sx, frame.y + 6, 8, frame.h - 6)
        rect_o(surf, W_DK, sh)
        for k in range(sh.y + 3, sh.bottom - 2, 4):
            pygame.draw.line(surf, W_LO, (sh.x + 1, k), (sh.right - 2, k))
    if kind in ('glow', 'green'):   # light spill onto the wall below
        spill = pygame.Surface((w + 8, 8), pygame.SRCALPHA)
        col = G2 if kind == 'glow' else E2
        for k in range(8):
            pygame.draw.line(spill, (*col, 70 - k * 8), (k // 2, k), (w + 7 - k // 2, k))
        surf.blit(spill, (x - 4, frame.bottom + 3))


def chimney(surf, x, y, w, h, lean=3):
    poly = [(x, y + h), (x + w, y + h), (x + w + lean, y), (x + lean, y)]
    bricks = pygame.Surface((W, H), pygame.SRCALPHA)
    bricks.fill(B_MID)
    for row, yy in enumerate(range(0, H, 5)):
        pygame.draw.line(bricks, B_LO, (0, yy + 4), (W, yy + 4))
        for xx in range(-8 + (row % 2) * 4, W, 8):
            pygame.draw.line(bricks, B_LO, (xx, yy), (xx, yy + 3))
            pygame.draw.line(bricks, B_HI, (xx + 1, yy), (xx + 5, yy))
    plane(surf, poly, bricks)
    pygame.draw.line(surf, B_HI, (x + lean + 1, y + 1), (x + 1, y + h - 1))
    rect_o(surf, S_MID, (x + lean - 2, y - 4, w + 5, 5))
    pygame.draw.line(surf, S_HI, (x + lean - 1, y - 3), (x + lean + w + 1, y - 3))


def ivy(surf, x0, x1, y0, y1, density, seed):
    r = random.Random(seed)
    for _ in range(density):
        # bias leaves toward the bottom so it reads as climbing up
        x = r.randint(x0, x1)
        y = int(y1 - (y1 - y0) * (r.random() ** 1.6))
        c = r.choice((I_LO, I_MID, I_MID, I_HI))
        pygame.draw.rect(surf, c, (x, y, 2, 2))
        if r.random() < 0.3:
            surf.set_at((x - 1, y + 1), I_LO)


def cobweb(surf, cx, cy, r, flip=1):
    web = pygame.Surface((W, H), pygame.SRCALPHA)
    col = (225, 225, 235, 150)
    import math
    for k in range(5):
        a = math.radians(k * 22.5)
        pygame.draw.line(web, col, (cx, cy), (cx + flip * math.cos(a) * r, cy + math.sin(a) * r))
    for rr in (r * 0.35, r * 0.65, r * 0.95):
        pts = [(cx + flip * math.cos(math.radians(k * 22.5)) * rr,
                cy + math.sin(math.radians(k * 22.5)) * rr) for k in range(5)]
        pygame.draw.lines(web, col, False, pts)
    surf.blit(web, (0, 0))


def bat(surf, x, y):
    pts = [(x - 6, y - 1), (x - 3, y + 1), (x - 1, y - 1), (x, y + 1),
           (x + 1, y - 1), (x + 3, y + 1), (x + 6, y - 1), (x + 3, y + 3), (x, y + 2), (x - 3, y + 3)]
    pygame.draw.polygon(surf, OUT, pts)


# ── the mansion ──────────────────────────────────────────────────────────

def draw_mansion():
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    base_y = 336                                   # top of the stone foundation

    # tower (behind everything else)
    tx0, tx1, ttop = 198, 250, 44
    tw = siding(W_MID, W_LO, W_HI, 5)
    plane(s, [(tx0, ttop), (tx1, ttop), (tx1, 140), (tx0, 140)], tw)
    plane(s, [(tx0, ttop), (tx0 + 12, ttop), (tx0 + 12, 140), (tx0, 140)], siding(W_HI, W_MID, T_LO, 5))
    plane(s, [(tx1 - 12, ttop), (tx1, ttop), (tx1, 140), (tx1 - 12, 140)], siding(W_LO, W_DK, W_MID, 5))
    window(s, 214, 62, 20, 36, 'green')
    # spire
    sp_l = [(188, 48), (224, 4), (224, 48)]
    sp_r = [(224, 4), (260, 48), (224, 48)]
    plane(s, sp_l, shingles(R_MID, R_DK, R_HI, 5, 6, seed=1))
    plane(s, sp_r, shingles(R_LO, R_DK, R_MID, 5, 6, seed=2))
    rect_o(s, T_MID, (186, 46, 76, 5))
    pygame.draw.line(s, T_HI, (187, 47), (260, 47))
    # finial + crescent weathervane
    pygame.draw.line(s, IRON, (224, 4), (224, 0))
    pygame.draw.circle(s, T_HI, (227, 2), 2)
    s.set_at((226, 2), IRON)

    # chimneys (behind the wing roofs)
    chimney(s, 36, 92, 16, 70, lean=-3)
    chimney(s, 396, 86, 16, 76, lean=4)

    # wings: walls then hipped roofs
    for (wx0, wx1, seed) in ((8, 160, 10), (288, 440, 20)):
        plane(s, [(wx0, 228), (wx1, 228), (wx1, base_y), (wx0, base_y)], siding(W_MID, W_LO, W_HI))
        # under-eave shadow
        pygame.draw.rect(s, W_DK, (wx0 + 1, 229, wx1 - wx0 - 1, 4))
        roof = [(wx0 - 8, 230), (wx1 + 8, 230), (wx1 - 14, 124), (wx0 + 14, 124)]
        plane(s, roof, shingles(R_MID, R_DK, R_HI, seed=seed))
        # hip planes: the outer ends are in shade/light
        if wx0 < 100:
            plane(s, [(wx0 - 8, 230), (wx0 + 14, 124), (wx0 + 26, 124), (wx0 + 8, 230)],
                  shingles(R_HI, R_MID, T_LO, seed=seed + 1))
        else:
            plane(s, [(wx1 + 8, 230), (wx1 - 14, 124), (wx1 - 26, 124), (wx1 - 8, 230)],
                  shingles(R_LO, R_DK, R_MID, seed=seed + 1))
        # ridge cap + eave trim
        pygame.draw.line(s, T_LO, (wx0 + 14, 124), (wx1 - 14, 124), 2)
        rect_o(s, T_MID, (wx0 - 9, 229, wx1 - wx0 + 18, 4))
        pygame.draw.line(s, T_HI, (wx0 - 8, 230), (wx1 + 8, 230))
        # corner boards
        for cx in (wx0, wx1 - 5):
            rect_o(s, T_LO, (cx, 233, 5, base_y - 233))
            pygame.draw.line(s, T_MID, (cx + 1, 234), (cx + 1, base_y - 1))

    # dormers on each wing roof
    for dx in (66, 346):
        face = [(dx, 212), (dx + 36, 212), (dx + 36, 186), (dx, 186)]
        plane(s, face, siding(W_MID, W_LO, W_HI, 4))
        window(s, dx + 9, 188, 18, 20, 'glow' if dx == 346 else 'dark')
        roof_l = [(dx - 6, 190), (dx + 18, 158), (dx + 18, 146), (dx - 6, 178)]
        roof_r = [(dx + 18, 158), (dx + 42, 190), (dx + 42, 178), (dx + 18, 146)]
        plane(s, roof_l, shingles(R_HI, R_MID, T_LO, 4, 6, seed=dx))
        plane(s, roof_r, shingles(R_LO, R_DK, R_MID, 4, 6, seed=dx + 1))
        pygame.draw.line(s, T_HI, (dx - 6, 190), (dx + 18, 158), 2)
        pygame.draw.line(s, T_MID, (dx + 18, 158), (dx + 42, 190), 2)

    # center block: tall walls with a front gable
    cx0, cx1 = 156, 292
    plane(s, [(cx0, 196), (cx1, 196), (cx1, base_y), (cx0, base_y)], siding(W_HI, W_MID, T_LO))
    # receding roof planes behind the gable's front edge
    plane(s, [(146, 204), (224, 112), (224, 66), (146, 158)], shingles(R_HI, R_MID, T_LO, seed=30))
    plane(s, [(224, 112), (302, 204), (302, 158), (224, 66)], shingles(R_LO, R_DK, R_MID, seed=31))
    pygame.draw.line(s, T_LO, (224, 66), (224, 112), 2)
    # gable face
    plane(s, [(160, 198), (224, 124), (288, 198)], siding(W_MID, W_LO, W_HI, 5))
    # rose window
    pygame.draw.circle(s, T_MID, (224, 170), 17)
    pygame.draw.circle(s, G2, (224, 170), 14)
    pygame.draw.circle(s, G1, (224, 170), 9)
    for k in range(8):
        import math
        a = k * math.pi / 4
        pygame.draw.line(s, T_LO, (224, 170), (224 + math.cos(a) * 14, 170 + math.sin(a) * 14))
    pygame.draw.circle(s, T_LO, (224, 170), 4)
    pygame.draw.circle(s, OUT, (224, 170), 17, 1)
    # bargeboards (decorative gable trim)
    for (p1, p2, col) in (((146, 204), (224, 112), T_HI), ((224, 112), (302, 204), T_MID)):
        pygame.draw.line(s, OUT, (p1[0], p1[1] + 3), (p2[0], p2[1] + 3), 1)
        pygame.draw.line(s, col, p1, p2, 3)
        pygame.draw.line(s, OUT, (p1[0], p1[1] - 2), (p2[0], p2[1] - 2), 1)
    for k in range(9):   # little hanging teeth
        t = (k + 0.5) / 9
        for (p1, p2) in (((146, 204), (224, 112)), ((224, 112), (302, 204))):
            x = p1[0] + (p2[0] - p1[0]) * t
            y = p1[1] + (p2[1] - p1[1]) * t
            pygame.draw.line(s, T_LO, (x, y + 3), (x, y + 6))
    # finial at the gable peak
    pygame.draw.line(s, IRON, (224, 110), (224, 98))
    pygame.draw.polygon(s, IRON, [(221, 101), (224, 95), (227, 101)])

    # center corner boards / shadow where the block meets the wings
    for x in (cx0, cx1 - 5):
        rect_o(s, T_LO, (x, 198, 5, base_y - 198))
        pygame.draw.line(s, T_HI, (x + 1, 199), (x + 1, base_y - 1))
    pygame.draw.rect(s, W_DK, (cx1, 233, 4, base_y - 233))      # center casts shade on right wing
    # string course between floors
    rect_o(s, T_MID, (cx0, 260, cx1 - cx0, 4))

    # windows
    window(s, 172, 210, 20, 38, 'ghost')
    window(s, 256, 210, 20, 38, 'glow')
    for (x, y, k, sh) in ((26, 246, 'dark', None), (74, 246, 'glow', None), (120, 246, 'cracked', 'right'),
                          (26, 292, 'glow', None), (74, 292, 'dark', None), (120, 292, 'boarded', None),
                          (306, 246, 'boarded', None), (352, 246, 'dark', 'left'), (398, 246, 'green', None),
                          (306, 292, 'dark', None), (352, 292, 'glow', None), (398, 292, 'cracked', None)):
        window(s, x, y, 20, 32, k, sh)

    # porch: posts, little hip roof, double door
    pygame.draw.rect(s, W_DK, (186, 268, 76, base_y - 268))           # porch shade
    door_poly_m = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.rect(door_poly_m, WD_MID, (204, 292, 40, base_y - 292))
    pygame.draw.ellipse(door_poly_m, WD_MID, (204, 272, 40, 40))
    for x in range(206, 244, 5):
        pygame.draw.line(door_poly_m, WD_LO, (x, 274), (x, base_y))
    pygame.draw.line(door_poly_m, WD_HI, (205, 290), (205, base_y))
    s.blit(door_poly_m, (0, 0))
    pygame.draw.arc(s, OUT, (204, 272, 40, 40), 0, 3.1416, 1)
    pygame.draw.line(s, OUT, (204, 292), (204, base_y))
    pygame.draw.line(s, OUT, (243, 292), (243, base_y))
    pygame.draw.line(s, OUT, (224, 274), (224, base_y))               # the two leaves
    pygame.draw.line(s, G1, (225, 282), (225, base_y - 1))            # light through the gap
    pygame.draw.line(s, G2, (226, 284), (226, base_y - 1))
    for kx in (219, 229):                                             # ring knockers
        pygame.draw.circle(s, G3, (kx, 308), 3, 1)
    pygame.draw.arc(s, T_MID, (200, 268, 48, 48), 0, 3.1416, 3)       # stone arch
    pygame.draw.arc(s, OUT, (199, 267, 50, 50), 0, 3.1416, 1)
    for px in (186, 256):
        rect_o(s, T_MID, (px, 270, 6, base_y - 270))
        pygame.draw.line(s, T_HI, (px + 1, 271), (px + 1, base_y - 1))
        rect_o(s, T_LO, (px - 2, base_y - 6, 10, 6))
    porch = [(178, 274), (270, 274), (258, 252), (190, 252)]
    plane(s, porch, shingles(R_MID, R_DK, R_HI, 4, 6, seed=40))
    rect_o(s, T_MID, (177, 273, 94, 4))
    pygame.draw.line(s, T_HI, (178, 274), (269, 274))

    # stone foundation
    found = pygame.Surface((W, H), pygame.SRCALPHA)
    found.fill(S_MID)
    for row, y in enumerate(range(base_y, H, 8)):
        pygame.draw.line(found, S_LO, (0, y + 7), (W, y + 7))
        for x in range(-12 + (row % 2) * 6, W, 12):
            pygame.draw.line(found, S_LO, (x, y), (x, y + 6))
            pygame.draw.line(found, S_HI, (x + 1, y), (x + 9, y))
    plane(s, [(4, base_y), (444, base_y), (444, H - 1), (4, H - 1)], found)

    # wear and tear
    for (x, y, n) in ((44, 270, 5), (330, 250, 4), (170, 300, 4), (420, 300, 5)):
        for _ in range(n):
            nx, ny = x + rng.randint(-3, 3), y + rng.randint(3, 6)
            pygame.draw.line(s, W_DK, (x, y), (nx, ny))
            x, y = nx, ny
    ivy(s, 8, 44, 236, base_y + 6, 260, 1)
    ivy(s, 150, 166, 280, base_y + 6, 80, 2)
    ivy(s, 404, 440, 280, base_y + 6, 150, 3)
    ivy(s, 46, 70, 150, 228, 40, 4)          # creeping onto the left roof
    cobweb(s, 9, 234, 16, 1)
    cobweb(s, 439, 234, 16, -1)
    cobweb(s, 157, 201, 12, 1)
    bat(s, 150, 36); bat(s, 300, 22); bat(s, 318, 40)
    return s


# ── props (row 11) ───────────────────────────────────────────────────────

def tile():
    return pygame.Surface((TS, TS), pygame.SRCALPHA)


def prop_grave_round():
    t = tile()
    pygame.draw.ellipse(t, (90, 80, 58, 160), (4, 26, 24, 6))          # dirt mound
    pygame.draw.rect(t, S_MID, (8, 12, 16, 16))
    pygame.draw.ellipse(t, S_MID, (8, 4, 16, 16))
    pygame.draw.line(t, S_HI, (9, 12), (9, 26))
    pygame.draw.arc(t, S_HI, (9, 5, 14, 14), 1.6, 3.0, 1)
    pygame.draw.line(t, S_LO, (22, 12), (22, 27))
    for y in (14, 18, 22):
        pygame.draw.line(t, S_LO, (12, y), (19, y))
    pygame.draw.arc(t, OUT, (8, 4, 16, 16), 0, 3.1416, 1)
    pygame.draw.line(t, OUT, (8, 12), (8, 28)); pygame.draw.line(t, OUT, (23, 12), (23, 28))
    pygame.draw.line(t, OUT, (8, 28), (23, 28))
    t.set_at((7, 28), I_MID); t.set_at((24, 27), I_HI); t.set_at((25, 28), I_MID)
    return t


def prop_grave_cross():
    t = tile()
    pygame.draw.ellipse(t, (90, 80, 58, 160), (6, 26, 20, 6))
    rect_o(t, S_MID, (14, 3, 5, 26))
    rect_o(t, S_MID, (8, 9, 17, 5))
    pygame.draw.line(t, S_HI, (15, 4), (15, 27))
    pygame.draw.line(t, S_HI, (9, 10), (23, 10))
    return t


def prop_grave_tilted():
    t = prop_grave_round()
    t = pygame.transform.rotate(t, -12)
    out = tile()
    out.blit(t, ((TS - t.get_width()) // 2, TS - t.get_height() + 2))
    pygame.draw.line(out, S_LO, (13, 12), (16, 18))   # crack
    return out


def prop_pumpkin():
    t = tile()
    glow = pygame.Surface((TS, TS), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (*G2, 50), (0, 14, 32, 18))
    t.blit(glow, (0, 0))
    for (x, w, c) in ((5, 12, (196, 96, 30)), (15, 12, (214, 112, 36)), (10, 12, (232, 132, 44))):
        pygame.draw.ellipse(t, c, (x, 12, w, 16))
    pygame.draw.ellipse(t, OUT, (5, 12, 22, 16), 1)
    rect_o(t, (84, 96, 50), (14, 8, 4, 6))
    for pts in (((10, 17), (13, 17), (11, 20)), ((19, 17), (22, 17), (21, 20))):
        pygame.draw.polygon(t, G1, pts)
    pygame.draw.polygon(t, G1, [(10, 22), (22, 22), (20, 25), (12, 25)])
    pygame.draw.line(t, (150, 70, 24), (13, 22), (13, 24)); pygame.draw.line(t, (150, 70, 24), (18, 22), (18, 24))
    return t


def prop_iron_fence(post=False):
    t = tile()
    for y in (12, 25):
        pygame.draw.line(t, IRON, (0, y), (31, y), 2)
        pygame.draw.line(t, IRON_HI, (0, y - 1), (31, y - 1))
    for x in range(2, 32, 6):
        pygame.draw.line(t, IRON, (x, 6), (x, 30), 2)
        pygame.draw.polygon(t, IRON, [(x - 1, 6), (x + 1, 1), (x + 3, 6)])
        t.set_at((x + 1, 2), IRON_HI)
    if post:
        rect_o(t, (50, 48, 62), (12, 2, 8, 29), OUT)
        pygame.draw.line(t, IRON_HI, (13, 3), (13, 29))
        pygame.draw.circle(t, (50, 48, 62), (16, 2), 3)
    return t


def prop_lamp(top):
    t = tile()
    if top:
        glow = pygame.Surface((TS, TS), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*E2, 55), (16, 16), 15)
        pygame.draw.circle(glow, (*E1, 70), (16, 16), 9)
        t.blit(glow, (0, 0))
        pygame.draw.polygon(t, IRON, [(9, 10), (23, 10), (16, 4)])
        rect_o(t, (60, 70, 60), (10, 10, 12, 14))
        pygame.draw.rect(t, E1, (12, 12, 8, 10))
        pygame.draw.polygon(t, (255, 255, 230), [(14, 21), (18, 21), (16, 14)])
        pygame.draw.line(t, IRON, (16, 10), (16, 23))
        pygame.draw.rect(t, IRON, (11, 24, 10, 3))
        pygame.draw.line(t, IRON, (16, 26), (16, 31), 2)
    else:
        pygame.draw.line(t, IRON, (16, 0), (16, 26), 3)
        pygame.draw.line(t, IRON_HI, (15, 0), (15, 26))
        rect_o(t, (50, 48, 62), (11, 24, 10, 6))
        pygame.draw.ellipse(t, (0, 0, 0, 60), (7, 28, 18, 4))
    return t


def prop_steps(side):
    t = tile()
    for i, y in enumerate((0, 10, 20)):
        inset = i * 0
        r = pygame.Rect(0, y, 32, 10)
        pygame.draw.rect(t, S_MID, r)
        pygame.draw.line(t, S_HI, (0, y), (31, y))
        pygame.draw.line(t, S_LO, (0, y + 9), (31, y + 9))
    edge = 0 if side == 'left' else 31
    pygame.draw.line(t, OUT, (edge, 0), (edge, 31))
    pygame.draw.line(t, OUT, (0, 31), (31, 31))
    return t


def prop_flagstones():
    """Loose, worn stepping stones — sand shows between them so the path
    blends with the ground tiles around it."""
    t = tile()
    hi, mid, lo = (182, 170, 150), (150, 140, 124), (108, 100, 90)
    for (x, y, w, h) in ((2, 2, 11, 8), (17, 3, 12, 7), (4, 13, 10, 7),
                         (18, 14, 11, 8), (3, 24, 12, 6), (19, 25, 9, 5)):
        pygame.draw.rect(t, mid, (x, y, w, h), border_radius=3)
        pygame.draw.line(t, hi, (x + 2, y), (x + w - 3, y))
        pygame.draw.rect(t, lo, (x, y, w, h), 1, border_radius=3)
    return t


def prop_dead_bush():
    t = tile()
    r = random.Random(77)
    base = (16, 29)
    for _ in range(9):
        a = r.uniform(-2.6, -0.5)
        import math
        L = r.uniform(10, 18)
        end = (base[0] + math.cos(a) * L, base[1] + math.sin(a) * L)
        pygame.draw.line(t, WD_LO, base, end, 2)
        mid = ((base[0] + end[0]) / 2, (base[1] + end[1]) / 2)
        pygame.draw.line(t, WD_MID, mid, (mid[0] + r.uniform(-5, 5), mid[1] - r.uniform(2, 6)))
    pygame.draw.ellipse(t, (90, 80, 58, 150), (8, 27, 16, 5))
    return t


def prop_gate(side):
    """Open gate leaf (hinged on the outer edge, swung inward)."""
    t = tile()
    hx = 2 if side == 'left' else 29
    rect_o(t, (50, 48, 62), (hx - 2, 2, 6, 29), OUT)
    for y in (12, 25):
        pygame.draw.line(t, IRON, (hx, y), (hx + (8 if side == 'left' else -8), y + 6), 2)
    return t


PROPS = [   # column in row 11 -> (name, maker, collision)
    ('grave_round',  prop_grave_round,          True),
    ('grave_cross',  prop_grave_cross,          True),
    ('grave_tilted', prop_grave_tilted,         True),
    ('pumpkin',      prop_pumpkin,              True),
    ('fence',        lambda: prop_iron_fence(), True),
    ('fence_post',   lambda: prop_iron_fence(True), True),
    ('lamp_top',     lambda: prop_lamp(True),   False),
    ('lamp_base',    lambda: prop_lamp(False),  True),
    ('steps_left',   lambda: prop_steps('left'), False),
    ('steps_right',  lambda: prop_steps('right'), False),
    ('flagstones',   prop_flagstones,           False),
    ('dead_bush',    prop_dead_bush,            True),
    ('gate_left',    lambda: prop_gate('left'), True),
    ('gate_right',   lambda: prop_gate('right'), True),
]


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    sheet = pygame.Surface((W, (MANSION_ROWS + 1) * TS), pygame.SRCALPHA)
    sheet.blit(draw_mansion(), (0, 0))
    for col, (_, make, _) in enumerate(PROPS):
        sheet.blit(make(), (col * TS, MANSION_ROWS * TS))
    pygame.image.save(sheet, OUT_PNG)

    rows = MANSION_ROWS + 1
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             f'<tileset version="1.10" tiledversion="1.12.1" name="haunted_mansion" tilewidth="{TS}" '
             f'tileheight="{TS}" tilecount="{COLS * rows}" columns="{COLS}">',
             f' <image source="haunted_mansion.png" width="{W}" height="{rows * TS}"/>']
    solid_ids = list(range(COLS * MANSION_ROWS))
    solid_ids += [COLS * MANSION_ROWS + c for c, (_, _, coll) in enumerate(PROPS) if coll]
    for tid in solid_ids:
        lines += [f' <tile id="{tid}">', '  <properties>',
                  '   <property name="collision" type="bool" value="true"/>',
                  '  </properties>', ' </tile>']
    lines.append('</tileset>')
    with open(OUT_TSX, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', OUT_PNG, 'and', OUT_TSX)


if __name__ == '__main__':
    main()

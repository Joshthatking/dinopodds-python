"""DinoPodds app icon: a DinoPod eclipsing the sun.

Writes DinoPodds.ico (the Windows .exe icon), DinoPodds.icns (the Mac .app
icon) — both used by DinoPodds.spec — and DinoPodds_icon.png
(the game window icon), plus icon_preview.png (every size side by side) when
given an OUT_DIR other than assets.
    python tools/make_icon.py [OUT_DIR]      (default: assets)
"""
import math
import random
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageChops

S = 1024
C = S // 2
out_dir = sys.argv[1] if len(sys.argv) > 1 else 'assets'


def radial(size, stops):
    """RGBA radial gradient; stops = [(radius_frac, (r,g,b,a)), ...]."""
    img = Image.new('RGBA', (size, size))
    px = img.load()
    c = size / 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c) / c
            for (r0, c0), (r1, c1) in zip(stops, stops[1:]):
                if d <= r1:
                    f = 0 if r1 == r0 else max(0.0, (d - r0) / (r1 - r0))
                    px[x, y] = tuple(int(c0[i] + (c1[i] - c0[i]) * f) for i in range(4))
                    break
            else:
                px[x, y] = stops[-1][1]
    return img


# --- background: rounded square of deep space -------------------------------
bg = radial(S // 4, [(0, (70, 30, 110, 255)), (0.7, (28, 12, 52, 255)), (1.5, (10, 4, 22, 255))]).resize((S, S), Image.BICUBIC)
stars = ImageDraw.Draw(bg)
rng = random.Random(7)
for _ in range(70):
    x, y = rng.uniform(40, S - 40), rng.uniform(40, S - 40)
    if math.hypot(x - C, y - C) < 380:
        continue
    r = rng.choice((2, 2, 3, 4))
    stars.ellipse((x - r, y - r, x + r, y + r), fill=(255, 245, 220, rng.randint(120, 255)))

mask = Image.new('L', (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=210, fill=255)

# --- corona: soft glow + jagged streamer rays --------------------------------
R = 250   # pod / moon radius
glow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
g = ImageDraw.Draw(glow)
for r, col in ((470, (190, 60, 255, 70)), (400, (255, 110, 30, 140)), (335, (255, 190, 60, 230)), (290, (255, 245, 200, 255))):
    g.ellipse((C - r, C - r, C + r, C + r), fill=col)
glow = glow.filter(ImageFilter.GaussianBlur(38))

rays = Image.new('RGBA', (S, S), (0, 0, 0, 0))
rd = ImageDraw.Draw(rays)
rng = random.Random(3)
n = 28
for i in range(n):
    a = i / n * math.tau + rng.uniform(-0.05, 0.05)
    L = R + rng.uniform(70, 190)
    w = rng.uniform(0.05, 0.11)
    pts = [(C + math.cos(a - w) * R, C + math.sin(a - w) * R),
           (C + math.cos(a) * L, C + math.sin(a) * L),
           (C + math.cos(a + w) * R, C + math.sin(a + w) * R)]
    rd.polygon(pts, fill=(255, 215, 110, 200))
rays = rays.filter(ImageFilter.GaussianBlur(9))

# --- the DinoPod moon ---------------------------------------------------------
pod = Image.new('RGBA', (S, S), (0, 0, 0, 0))
pd = ImageDraw.Draw(pod)
pd.ellipse((C - R, C - R, C + R, C + R), fill=(40, 18, 70, 255))
shade = radial(2 * R, [(0, (120, 70, 190, 255)), (0.75, (45, 20, 80, 255)), (1.0, (14, 6, 28, 255))])
off = (C - R - 60, C - R - 70)   # light from the upper-left
pod_shade = Image.new('RGBA', (S, S), (14, 6, 28, 255))
pod_shade.paste(shade, off)
pod_mask = Image.new('L', (S, S), 0)
ImageDraw.Draw(pod_mask).ellipse((C - R, C - R, C + R, C + R), fill=255)
pod = Image.composite(pod_shade, pod, pod_mask)

# Markings, matching assets/Items/dinopod.png: a navy-blue X, a white stripe
# across the middle and a silver diamond in the center.
marks = Image.new('RGBA', (S, S), (0, 0, 0, 0))
md = ImageDraw.Draw(marks)
for ang in (math.pi / 4, -math.pi / 4):          # the blue X
    dx, dy = math.cos(ang) * R * 1.1, math.sin(ang) * R * 1.1
    md.line((C - dx, C - dy, C + dx, C + dy), fill=(14, 14, 70, 255), width=118)
    md.line((C - dx, C - dy, C + dx, C + dy), fill=(30, 34, 140, 255), width=92)
    md.line((C - dx * 0.95, C - dy * 0.95 - 10, C + dx * 0.95, C + dy * 0.95 - 10),
            fill=(62, 78, 205, 255), width=26)   # shine along each arm
stripe = 44                                       # the white middle stripe
md.rectangle((C - R, C - stripe // 2 - 9, C + R, C + stripe // 2 + 9), fill=(14, 6, 28, 255))
md.rectangle((C - R, C - stripe // 2, C + R, C + stripe // 2), fill=(241, 241, 241, 255))
md.rectangle((C - R, C + 4, C + R, C + stripe // 2), fill=(196, 196, 206, 255))
marks_mask = pod_mask.filter(ImageFilter.MinFilter(15))   # keep markings inside the outline
pod = Image.composite(Image.alpha_composite(pod, marks), pod, marks_mask)

pd = ImageDraw.Draw(pod)
for r, col in ((96, (20, 18, 24, 255)), (80, (191, 191, 198, 255))):   # silver diamond
    pd.polygon([(C, C - r), (C + r, C), (C, C + r), (C - r, C)], fill=col)
pd.polygon([(C, C - 80), (C + 80, C), (C, C)], fill=(225, 225, 232, 255))   # lit facets
pd.polygon([(C, C), (C - 80, C), (C, C + 80)], fill=(150, 150, 158, 255))   # shaded facet
pd.ellipse((C - 150, C - 190, C - 96, C - 150), fill=(201, 175, 217, 255))  # lavender shine
# dark outline like the sprite, then a thin gold rim where the corona meets it
pd.ellipse((C - R, C - R, C + R, C + R), outline=(30, 24, 34, 255), width=16)
pd.ellipse((C - R, C - R, C + R, C + R), outline=(255, 220, 140, 255), width=6)

# --- diamond-ring flare at the upper right ------------------------------------
flare = Image.new('RGBA', (S, S), (0, 0, 0, 0))
fd = ImageDraw.Draw(flare)
fa = -math.pi / 4
fx, fy = C + math.cos(fa) * (R + 4), C + math.sin(fa) * (R + 4)
for r, col in ((95, (255, 200, 100, 120)), (55, (255, 240, 200, 220)), (26, (255, 255, 255, 255))):
    fd.ellipse((fx - r, fy - r, fx + r, fy + r), fill=col)
flare = flare.filter(ImageFilter.GaussianBlur(10))
fd = ImageDraw.Draw(flare)
for ang, ln, wd in ((0, 210, 9), (math.pi / 2, 210, 9), (math.pi / 4, 110, 6), (-math.pi / 4, 110, 6)):
    dx, dy = math.cos(ang) * ln, math.sin(ang) * ln
    nx, ny = -math.sin(ang) * wd, math.cos(ang) * wd
    fd.polygon([(fx - dx, fy - dy), (fx + nx, fy + ny), (fx + dx, fy + dy), (fx - nx, fy - ny)],
               fill=(255, 252, 235, 255))
fd.ellipse((fx - 18, fy - 18, fx + 18, fy + 18), fill=(255, 255, 255, 255))

img = bg.copy()
for layer in (glow, rays, pod, flare):
    img = Image.alpha_composite(img, layer)
img.putalpha(ImageChops.multiply(img.getchannel('A'), mask))

img.save(f'{out_dir}/DinoPodds_icon.png')
sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(f'{out_dir}/DinoPodds.ico', sizes=sizes)
img.save(f'{out_dir}/DinoPodds.icns')   # the Mac .app icon
# preview sheet: the sizes Windows actually shows
prev = Image.new('RGBA', (16 + 24 + 32 + 48 + 64 + 128 + 256 + 8 * 10, 276), (40, 40, 40, 255))
x = 10
for w, h in sizes:
    prev.alpha_composite(img.resize((w, h), Image.LANCZOS), (x, 270 - h))
    x += w + 10
if out_dir != 'assets':   # don't ship the preview inside the game bundle
    prev.save(f'{out_dir}/icon_preview.png')
print('ok')

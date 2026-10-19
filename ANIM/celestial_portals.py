"""CELESTIAL PORTALS — post-credits lunar + solar portals.

Once the end credits have rolled (story flag 'credits_done') two one-tile
portals appear somewhere in the Lost Region, each at one of data.PORTAL_SPOTS:

  lunar  — a dark rift: violet-black swirl, a dark aura that dims the ground
           around it and dark motes spiralling into it.
  solar  — a bright gate: white-gold core ringed with shifting rainbow light
           and iridescent sparkles rising off it.

Each stays put for STAY seconds, then jumps to a new random spot (never the
other portal's spot or area). Within SOUND_RANGE tiles its shimmer sound
plays, faint at the edge and swelling to full volume as you close in. Stepping onto one plays a warp
transition and drops the player on that planet (Game ENTRANCE_DATA
'lunar_planet' / 'solar_planet'); each planet has a fixed return portal
(data.PLANET_RETURN_PORTALS) that warps back to where you came from.

Touch points in game.py are tagged `# PORTALS`.
"""
import math
import random
import pygame
import config
from data import PORTAL_SPOTS, PLANET_RETURN_PORTALS

STAY = 60.0
APPEAR = 0.8              # fade-in when a portal (re)appears
SOUND_RANGE = 25.0       # tiles — faint at the edge, full volume on top of it
SOUND_EVERY = 1.15        # seconds between shimmers
KINDS = ('lunar', 'solar')
ENTRANCE = {'lunar': 'lunar_planet', 'solar': 'solar_planet'}
FALLBACK_RETURN = ('LOST_REGION.world', 25, -82)   # Lake Meridian, if the way back was lost


def _blob(r, col, alpha_peak):
    """Soft radial blob with per-pixel alpha (for normal alpha blending)."""
    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(r, 0, -1):
        k = (1 - i / r) ** 1.6
        pygame.draw.circle(s, (*col, int(alpha_peak * k)), (r, r), i)
    return s


def _glow(r, col, strength=1.0):
    """Soft radial glow without alpha, for additive blending."""
    s = pygame.Surface((r * 2, r * 2))
    for i in range(r, 0, -1):
        k = (1 - i / r) ** 2 * strength
        pygame.draw.circle(s, tuple(int(c * k) for c in col), (r, r), i)
    return s


def _hue(h, s=60, v=100):
    c = pygame.Color(0)
    c.hsva = (h % 360, s, v, 100)
    return (c.r, c.g, c.b)


# ── the warp transition (screen space) ───────────────────────────────────

class PortalWarp:
    OUT = 1.35     # closing in on the portal, ends fully covered
    IN = 1.0       # opening up again on the other side

    def __init__(self, kind, center, returning):
        self.kind = kind
        self.center = center
        self.returning = returning
        self.phase = 'out'
        self.t = 0.0
        rng = random.Random()
        self.parts = [(rng.uniform(0, math.tau), rng.uniform(0.35, 1.0), rng.uniform(1, 3),
                       rng.uniform(0, 360)) for _ in range(80)]
        self._layer = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)

    @property
    def p(self):
        return min(1.0, self.t / (self.OUT if self.phase == 'out' else self.IN))

    def draw(self, screen):
        if self.kind == 'lunar':
            self._draw_lunar(screen)
        else:
            self._draw_solar(screen)

    # dark iris closing on the rift, motes spiralling in; reopens on arrival
    def _draw_lunar(self, screen):
        W, H = screen.get_size()
        max_r = math.hypot(W, H)
        p = self.p
        if self.phase == 'out':
            cx, cy = self.center
            r = max_r * (1 - p) ** 1.5
            dark_a = 255
        else:
            cx, cy = W / 2, H / 2
            r = max_r * p ** 0.9
            dark_a = int(255 * (1 - p) ** 0.4)
        layer = self._layer
        layer.fill((6, 0, 16, dark_a))
        feather = 60
        for k in range(12):
            f = k / 12
            pygame.draw.circle(layer, (6, 0, 16, int(dark_a * (1 - f))), (int(cx), int(cy)),
                               max(0, int(r + feather * (1 - f))))
        if r > 1:
            pygame.draw.circle(layer, (0, 0, 0, 0), (int(cx), int(cy)), int(r))
        screen.blit(layer, (0, 0))
        if r > 2:
            pygame.draw.circle(screen, (150, 80, 240), (int(cx), int(cy)), int(r), 3)
            pygame.draw.circle(screen, (70, 30, 140), (int(cx), int(cy)), int(r) + 4, 2)
        # motes
        for a0, rr, size, _ in self.parts:
            if self.phase == 'out':
                a = a0 + p * 7 * (1.4 - rr)
                d = rr * max_r * 0.6 * (1 - p) ** 1.2
                fade = min(1.0, p * 3)
            else:
                a = a0 - p * 3
                d = rr * max_r * 0.7 * p ** 0.7
                fade = 1 - p
            x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
            col = (int(170 * fade), int(110 * fade), int(255 * fade))
            pygame.draw.rect(screen, col, (int(x), int(y), int(size) + 1, int(size) + 1))

    # light rays burst from the gate until everything is white; then fades
    def _draw_solar(self, screen):
        W, H = screen.get_size()
        p = self.p
        layer = self._layer
        layer.fill((0, 0, 0, 0))
        if self.phase == 'out':
            cx, cy = self.center
            ray_len = 80 + p * math.hypot(W, H)
            ray_a = int(60 + 150 * p)
            white_a = int(255 * p ** 2.2)
            spin = p * 1.2
        else:
            cx, cy = W / 2, H / 2
            ray_len = math.hypot(W, H)
            ray_a = int(180 * (1 - p) ** 1.5)
            white_a = int(255 * (1 - p) ** 1.6)
            spin = 1.2 + p * 0.6
        if ray_a > 2:
            for i in range(14):
                a = spin + i * math.tau / 14
                w = 0.06 + 0.03 * math.sin(i * 1.7)
                pts = [(cx, cy),
                       (cx + math.cos(a - w) * ray_len, cy + math.sin(a - w) * ray_len),
                       (cx + math.cos(a + w) * ray_len, cy + math.sin(a + w) * ray_len)]
                pygame.draw.polygon(layer, (*_hue(40 + i * 25, 25), ray_a), pts)
        screen.blit(layer, (0, 0))
        if self.phase == 'in':
            # iridescent shock ring rolling outward
            R = int(p * math.hypot(W, H) * 0.7)
            if R > 4:
                for k in range(36):
                    a = k * math.tau / 36
                    col = _hue(k * 10 + p * 200, 55)
                    col = tuple(int(c * (1 - p)) for c in col)
                    pygame.draw.circle(screen, col, (int(cx + math.cos(a) * R), int(cy + math.sin(a) * R)), 4)
        white = pygame.Surface((W, H))
        white.fill((255, 250, 236))
        white.set_alpha(white_a)
        screen.blit(white, (0, 0))
        # sparkles
        for a0, rr, size, hue in self.parts[:50]:
            if self.phase == 'out':
                d = rr * 260 * p
                fade = 1 - p * 0.5
            else:
                d = rr * 340 * (0.4 + p)
                fade = 1 - p
            a = a0 + p
            x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
            col = tuple(int(c * fade) for c in _hue(hue + p * 180, 45))
            s = int(size) + 1
            pygame.draw.line(screen, col, (x - s, y), (x + s, y))
            pygame.draw.line(screen, col, (x, y - s), (x, y + s))


# ── portals in the world ─────────────────────────────────────────────────

class CelestialPortals:
    def __init__(self, game):
        self.game = game
        self.portals = {}          # kind -> {'spot': index, 'timer': s, 'age': s}
        self.warp = None
        self._warp_target = None   # (kind, tile, returning)
        self._last_tile = None
        self._sound_t = 0.0
        self._rng = random.Random()
        self._aura = _blob(30, (12, 0, 28), 170)
        self._glow_cache = {}

    # ── which portals exist here ──
    def active(self):
        return bool(self.game.story_flags.get('credits_done'))

    def visible_here(self):
        """[(kind, tx, ty, age, returning)] for the current world."""
        g = self.game
        out = []
        if self.active():
            for kind, p in self.portals.items():
                world, tx, ty, _ = PORTAL_SPOTS[p['spot']]
                if world == g.current_world_file:
                    out.append((kind, tx, ty, p['age'], False))
        ret = PLANET_RETURN_PORTALS.get(g.current_world_file)
        if ret:
            out.append((ret[0], ret[1], ret[2], 99.0, True))
        return out

    # ── spot rotation ──
    def _relocate(self, kind):
        g = self.game
        ts = config.TILE_SIZE
        player = (g.current_world_file, g.player.rect.x // ts, g.player.rect.y // ts)
        other = self.portals.get('solar' if kind == 'lunar' else 'lunar')
        other_area = PORTAL_SPOTS[other['spot']][3] if other else None
        mine = self.portals.get(kind, {}).get('spot')
        choices = [i for i, (w, x, y, area) in enumerate(PORTAL_SPOTS)
                   if i != mine and area != other_area and (w, x, y) != player]
        self.portals[kind] = {'spot': self._rng.choice(choices), 'timer': STAY, 'age': 0.0}

    def relocate_all(self):
        """Sandbox Ctrl+P: both portals jump to new spots right away."""
        for kind in KINDS:
            self._relocate(kind)

    def describe(self):
        """e.g. 'lunar: corn_maze (100,-70), solar: route1 (6,27)'."""
        return ", ".join(f"{kind}: {PORTAL_SPOTS[p['spot']][3]} ({PORTAL_SPOTS[p['spot']][1]},{PORTAL_SPOTS[p['spot']][2]})"
                         for kind, p in self.portals.items())

    def update(self, dt):
        """Every frame: spot timers, proximity shimmer, stepping onto a portal."""
        g = self.game
        if self.active():
            for kind in KINDS:
                if kind not in self.portals:
                    self._relocate(kind)
            for kind, p in self.portals.items():
                p['age'] += dt
                if self.warp and self._warp_target and self._warp_target[0] == kind:
                    continue   # don't yank a portal away mid-warp
                p['timer'] -= dt
                if p['timer'] <= 0:
                    self._relocate(kind)
        if self.warp or g.state_stack[-1] != 'world':
            return
        here = self.visible_here()
        if not here:
            self._sound_t = 0.0
            self._last_tile = None
            return
        ts = config.TILE_SIZE
        px, py = g.player.rect.centerx / ts - 0.5, g.player.rect.centery / ts - 0.5
        near = min(here, key=lambda q: math.hypot(q[1] - px, q[2] - py))
        d = math.hypot(near[1] - px, near[2] - py)
        if d < SOUND_RANGE:
            self._sound_t -= dt
            if self._sound_t <= 0:
                # squared falloff: a soft hint from far off, swelling as you close in
                g.sfx.play(f'portal_{near[0]}', volume=0.08 + 0.92 * (1 - d / SOUND_RANGE) ** 2)
                self._sound_t = SOUND_EVERY
        else:
            self._sound_t = 0.0
        self._check_step(here)

    def _check_step(self, here):
        g = self.game
        if (g.player.moving or g.fading or g.entrance_fade_state is not None or g.cutscene
                or g.message_box.visible or g.sky_transition):
            return
        ts = config.TILE_SIZE
        tile = (g.player.rect.x // ts, g.player.rect.y // ts)
        if tile == self._last_tile:
            return
        self._last_tile = tile
        for kind, tx, ty, age, returning in here:
            if (tx, ty) == tile and age > APPEAR * 0.5:
                self._start_warp(kind, tile, returning)
                return

    # ── warping ──
    def _start_warp(self, kind, tile, returning):
        g = self.game
        g.player.freeze_in_place()
        scale = config.WIDTH / g.render_surface.get_width()
        ts = config.TILE_SIZE
        center = ((tile[0] * ts + ts / 2 - g.camera_x) * scale, (tile[1] * ts + ts / 2 - g.camera_y) * scale)
        self.warp = PortalWarp(kind, center, returning)
        self._warp_target = (kind, tile, returning)
        g.sfx.play(f'warp_{kind}')

    def update_warp(self, dt):
        """Runs instead of normal world movement while a warp plays."""
        w = self.warp
        w.t += dt
        if w.phase == 'out' and w.t >= w.OUT:
            self._teleport()
            w.phase, w.t = 'in', 0.0
        elif w.phase == 'in' and w.t >= w.IN:
            self.warp = None
            self._warp_target = None

    def _teleport(self):
        g = self.game
        kind, tile, returning = self._warp_target
        g.route_banner.phase = None   # drop a still-showing "Lunar/Solar Planet" banner
        if returning:
            if g.world_stack:
                g._do_exit_teleport()
            else:   # e.g. loaded a save on the planet — land somewhere safe
                world, tx, ty = FALLBACK_RETURN
                g._load_world_data(world)
                g._spawn_world_npcs(world)
                g._place_player(tx, ty)
        else:
            g._do_entrance_teleport((ENTRANCE[kind], tile[0], tile[1]))
        g.player.direction = g.player.facing = 'down'
        g.player.image = g.player.animations['down'][0]
        ts = config.TILE_SIZE
        self._last_tile = (g.player.rect.x // ts, g.player.rect.y // ts)
        self._sound_t = 0.6

    # ── drawing ──
    def draw_world(self, surface, cam_x, cam_y):
        """Portals on the low-res world surface, under the player."""
        t = pygame.time.get_ticks() / 1000.0
        ts = config.TILE_SIZE
        for kind, tx, ty, age, _ in self.visible_here():
            cx = tx * ts + ts / 2 - cam_x
            cy = ty * ts + ts / 2 - cam_y + math.sin(t * 2.2 + tx) * 1.5
            if not (-60 < cx < surface.get_width() + 60 and -60 < cy < surface.get_height() + 60):
                continue
            k = min(1.0, age / APPEAR)
            if kind == 'lunar':
                self._draw_lunar(surface, cx, cy, t, k)
            else:
                self._draw_solar(surface, cx, cy, t, k)

    def _draw_lunar(self, s, cx, cy, t, k):
        a = self._aura
        if k < 1:
            a = a.copy(); a.set_alpha(int(255 * k))
        s.blit(a, (cx - 30, cy - 26))
        rx, ry = 11 * k, 15 * k
        if rx < 1:
            return
        # layered rift: violet rim, darker bands, black heart
        for f, col in ((1.0, (110, 50, 190)), (0.85, (60, 20, 110)), (0.62, (30, 6, 60)), (0.38, (6, 0, 14))):
            pygame.draw.ellipse(s, col, (cx - rx * f, cy - ry * f, rx * 2 * f, ry * 2 * f))
        # swirl arms
        for arm in range(3):
            for i in range(9):
                u = i / 9
                ang = t * 2.4 + arm * math.tau / 3 + u * 3.2
                x = cx + math.cos(ang) * rx * (1 - u * 0.85)
                y = cy + math.sin(ang) * ry * (1 - u * 0.85)
                s.set_at((int(x), int(y)), (170, 110, 255) if i < 4 else (120, 60, 210))
        # dark motes spiralling in
        for i in range(14):
            q = (t * 0.45 + i / 14) % 1.0
            ang = i * 2.4 + t * 1.6 + q * 4
            d = 26 * (1 - q) * k
            x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d * 0.8
            col = (140, 80, 230) if i % 3 else (25, 5, 45)
            pygame.draw.rect(s, col, (int(x), int(y), 2, 2))
        for i in range(4):   # black specks rising off the rift
            q = (t * 0.35 + i / 4) % 1.0
            s.set_at((int(cx - 6 + i * 4 + math.sin(t * 3 + i) * 2), int(cy - ry - q * 12)), (10, 0, 20))

    def _draw_solar(self, s, cx, cy, t, k):
        g = self._glow_sprite(int(30 * k) or 1, (255, 225, 150), 0.9)
        s.blit(g, (cx - g.get_width() / 2, cy - g.get_height() / 2), special_flags=pygame.BLEND_RGB_ADD)
        rx, ry = 11 * k, 15 * k
        if rx < 1:
            return
        # iridescent rim: hue rotates around the oval
        for i in range(28):
            ang = i * math.tau / 28
            col = _hue(i * 360 / 28 + t * 120, 45)
            pygame.draw.circle(s, col, (int(cx + math.cos(ang) * rx), int(cy + math.sin(ang) * ry)), 2)
        pygame.draw.ellipse(s, (255, 214, 120), (cx - rx * 0.82, cy - ry * 0.82, rx * 1.64, ry * 1.64))
        pygame.draw.ellipse(s, (255, 244, 200), (cx - rx * 0.6, cy - ry * 0.6, rx * 1.2, ry * 1.2))
        pulse = 0.35 + 0.08 * math.sin(t * 5)
        pygame.draw.ellipse(s, (255, 255, 255), (cx - rx * pulse, cy - ry * pulse, rx * 2 * pulse, ry * 2 * pulse))
        # iridescent sparkles rising and orbiting
        for i in range(16):
            q = (t * 0.4 + i / 16) % 1.0
            ang = i * 1.9 + t * 0.9
            x = cx + math.cos(ang) * (8 + 12 * q) * k
            y = cy + math.sin(ang) * 6 * k - q * 22 * k
            col = tuple(int(c * (1 - q)) for c in _hue(i * 37 + t * 90, 40))
            pygame.draw.line(s, col, (x - 1, y), (x + 1, y))
            pygame.draw.line(s, col, (x, y - 1), (x, y + 1))

    def _glow_sprite(self, r, col, strength):
        key = (r, col, strength)
        if key not in self._glow_cache:
            self._glow_cache[key] = _glow(r, col, strength)
        return self._glow_cache[key]

    def draw_glow(self, screen):
        """Additive glow on the final screen, after the night overlay, so the
        portals still shine at night."""
        g = self.game
        scale = config.WIDTH / g.render_surface.get_width()
        ts = config.TILE_SIZE
        t = pygame.time.get_ticks() / 1000.0
        for kind, tx, ty, age, _ in self.visible_here():
            k = min(1.0, age / APPEAR)
            cx = (tx * ts + ts / 2 - g.camera_x) * scale
            cy = (ty * ts + ts / 2 - g.camera_y) * scale
            r = int((26 if kind == 'lunar' else 34) * scale * k * (1 + 0.06 * math.sin(t * 3)))
            if r < 3 or not (-r < cx < config.WIDTH + r and -r < cy < config.HEIGHT + r):
                continue
            col = (70, 30, 130) if kind == 'lunar' else (150, 120, 70)
            glow = self._glow_sprite(r, col, 0.8)
            screen.blit(glow, (cx - r, cy - r), special_flags=pygame.BLEND_RGB_ADD)

    def draw_warp(self, screen):
        if self.warp:
            self.warp.draw(screen)

"""End credits — plays after picking up the Celestial Solar Shard.

Phases:
    light     light floods out from the centre over the last world frame
    to_black  the white-out fades to black
    scroll    a centred square of black (aether void in the side bands)
              fades in, then the credits scroll up through it and off the top
    thanks    one last "Thank you" fades in, holds, and fades out
    done      Game sends the player home (see Game._finish_credits)

Hold J or Space to scroll faster. Edit CREDITS below to change the text:
    ('logo',)                       the DINOPODDS / Ultra Violet logo
    ('section', header, [names])    big bold header, names in columns of
                                    COLUMN_MAX (left / middle / right)
    ('lines', [text, ...])          centred lines of text
    ('gap', pixels)                 extra blank space
"""
import math
import pygame
import config
from ANIM.aether_bg import AetherBackground
from ANIM.title_anim import TitleLogo, LW

CREDITS = [
    ('logo',),
    ('gap', 70),
    ('section', "Developed", ["Joshthatking"]),
    ('section', "Story", ["Joshthatking"]),
    ('section', "Map Assets", ["Ekat99", "Akizakura", "Heartlessdragon", "Vurtax", "PolestarDragon",
                               "King Tapir", "skatefilter5", "ArkeyEditor", "Wergan", "Lime029",
                               "DiegoWT", "Joshthatking"]),
    ('section', "Designs", ["Joshthatking", "Curfeu", "zSkvy", "AlphaLog"]),
    ('section', "Music", ["Joshthatking"]),
    ('gap', 60),
    ('lines', ["Special thanks to my Mom, sister, and Barley"]),
    ('gap', 24),
    ('lines', ["Also a big thanks to you the player,", "for joining this journey"]),
    ('gap', 24),
    ('lines', ["A vision from my childhood brought to life", "almost 20 years later"]),
    ('gap', 50),
    ('lines', ["Never stop dreaming"]),
]

COLUMN_MAX = 7          # names per column before starting a new one
SQUARE = 480            # side of the centred credits square (screen is 640x480)
SCROLL_SPEED = 38       # px/s
FAST_MULT = 4           # while J/Space is held

LIGHT_T    = 2.4
TO_BLACK_T = 1.4
FADE_IN_T  = 1.5
THANKS_IN, THANKS_HOLD, THANKS_OUT = 1.6, 2.6, 1.8


class CreditsSequence:
    def __init__(self, last_frame):
        self.W, self.H = config.WIDTH, config.HEIGHT
        self.last_frame = last_frame.copy()
        self.phase = 'light'
        self.t = 0.0
        self.done = False
        self.fast = False
        self.aether = AetherBackground(seed=11)
        self.logo = TitleLogo()

        self.font_head = pygame.font.Font(config.FONT_PATH_B, 30)
        self.font_name = pygame.font.Font(config.FONT_PATH_B, 18)
        self.font_line = pygame.font.Font(config.FONT_PATH, 18)
        self.font_thanks = pygame.font.Font(config.FONT_PATH_B, 40)

        self.square = pygame.Rect(0, 0, SQUARE, SQUARE)
        self.square.center = (self.W // 2, self.H // 2)
        self.content = self._build_content()
        self.scroll_y = 0.0      # how far the content has moved up

    # ── layout ────────────────────────────────────────────────────────────

    def _logo_surface(self):
        """The title-screen logo at 2x, shrunk if needed so its glow fits
        inside the square with a little margin."""
        h = self.logo.height + 24
        low = pygame.Surface((LW, h))
        low.fill((0, 0, 0))
        self.logo.draw(low, 12)
        logo_w = (self.logo.title.get_width() + self.logo.HALO_PAD * 2) * 2
        k = min(1.0, (SQUARE - 30) / logo_w)
        return pygame.transform.scale(low, (int(LW * 2 * k), int(h * 2 * k)))

    def _build_content(self):
        """List of (kind, surface-or-None, y) laid out top to bottom."""
        items, y = [], 0
        for entry in CREDITS:
            kind = entry[0]
            if kind == 'logo':
                items.append(('logo', None, y))
                y += (self.logo.height + 24) * 2 + 10
            elif kind == 'gap':
                y += entry[1]
            elif kind == 'section':
                _, header, names = entry
                head = self.font_head.render(header, True, (255, 214, 90))
                items.append(('surf', head, y))
                y += head.get_height() + 14
                cols = [names[i:i + COLUMN_MAX] for i in range(0, len(names), COLUMN_MAX)]
                col_w = SQUARE // max(1, len(cols))
                line_h = self.font_name.get_height() + 6
                for c, col in enumerate(cols):
                    cx = col_w * c + col_w // 2 - SQUARE // 2   # offset from the square's centre
                    for r, name in enumerate(col):
                        surf = self.font_name.render(name, True, (225, 215, 255))
                        items.append(('surf', surf, y + r * line_h, cx))
                y += max(len(c) for c in cols) * line_h + 46
            elif kind == 'lines':
                for text in entry[1]:
                    surf = self.font_line.render(text, True, (235, 230, 250))
                    items.append(('surf', surf, y))
                    y += surf.get_height() + 6
        self.content_h = y
        return items

    # ── update ────────────────────────────────────────────────────────────

    def handle_event(self, event):
        if event.type in (pygame.KEYDOWN, pygame.KEYUP) and event.key in (pygame.K_j, pygame.K_SPACE):
            self.fast = event.type == pygame.KEYDOWN

    def update(self, dt):
        self.logo.update(dt)
        self.t += dt
        if self.phase == 'light' and self.t >= LIGHT_T:
            self.phase, self.t = 'to_black', 0.0
        elif self.phase == 'to_black' and self.t >= TO_BLACK_T:
            self.phase, self.t = 'scroll', 0.0
        elif self.phase == 'scroll':
            if self.t > FADE_IN_T * 0.5:
                self.scroll_y += SCROLL_SPEED * (FAST_MULT if self.fast else 1) * dt
            # finished once the last line has left the top of the square
            if self.scroll_y > SQUARE + self.content_h:
                self.phase, self.t = 'thanks', 0.0
        elif self.phase == 'thanks' and self.t >= THANKS_IN + THANKS_HOLD + THANKS_OUT:
            self.done = True

    # ── draw ──────────────────────────────────────────────────────────────

    def _overlay(self, screen, colour, alpha):
        if alpha <= 0:
            return
        s = pygame.Surface((self.W, self.H))
        s.fill(colour)
        s.set_alpha(int(max(0, min(255, alpha))))
        screen.blit(s, (0, 0))

    def _draw_light(self, screen):
        screen.blit(self.last_frame, (0, 0))
        p = min(1.0, self.t / LIGHT_T)
        cx, cy = self.W // 2, self.H // 2
        glow = pygame.Surface((self.W, self.H))
        glow.fill((0, 0, 0))
        r_max = int(math.hypot(self.W, self.H) * 0.6)
        rays = 18
        for i in range(rays):        # beams fanning out
            a = i * math.tau / rays + self.t * 0.4
            half = 0.05 + 0.05 * p
            length = r_max * (0.3 + 1.2 * p)
            k = int(255 * min(1.0, p * 1.4) * (0.6 + 0.4 * math.sin(self.t * 6 + i)))
            col = (k, k, int(k * 0.85))
            pygame.draw.polygon(glow, col, [(cx, cy),
                                            (cx + math.cos(a - half) * length, cy + math.sin(a - half) * length),
                                            (cx + math.cos(a + half) * length, cy + math.sin(a + half) * length)])
        core = int(20 + r_max * p * p)
        for k in range(14, 0, -1):    # swelling core
            f = k / 14
            v = int(255 * min(1.0, (1 - f) * 2.2))
            pygame.draw.circle(glow, (v, v, int(v * 0.9)), (cx, cy), max(1, int(core * f)))
        screen.blit(glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        self._overlay(screen, (255, 255, 255), 255 * max(0.0, (p - 0.55) / 0.45) ** 1.5)

    def _draw_scroll(self, screen):
        # aether void fills the screen, the credits square is cut out of it
        self.aether.draw(screen, 0, 0, pygame.time.get_ticks() / 1000.0)
        sq = self.square
        pygame.draw.rect(screen, (0, 0, 0), sq)

        screen.set_clip(sq)
        base = sq.bottom - self.scroll_y      # content starts just below the square
        for item in self.content:
            kind, surf, y = item[0], item[1], item[2]
            sy = base + y
            if kind == 'logo':
                logo = self._logo_surface()
                if sy + logo.get_height() < sq.top or sy > sq.bottom:
                    continue
                screen.blit(logo, (self.W // 2 - logo.get_width() // 2, sy))
                continue
            if sy + surf.get_height() < sq.top or sy > sq.bottom:
                continue
            cx = sq.centerx + (item[3] if len(item) > 3 else 0)
            screen.blit(surf, (cx - surf.get_width() // 2, sy))
        screen.set_clip(None)
        pygame.draw.line(screen, (120, 90, 200), sq.topleft, sq.bottomleft, 2)
        pygame.draw.line(screen, (120, 90, 200), sq.topright, sq.bottomright, 2)

        if self.t < FADE_IN_T:   # black fades in to the scene
            self._overlay(screen, (0, 0, 0), 255 * (1 - self.t / FADE_IN_T))

    def _draw_thanks(self, screen):
        screen.fill((0, 0, 0))
        t = self.t
        if t < THANKS_IN:
            a = t / THANKS_IN
        elif t < THANKS_IN + THANKS_HOLD:
            a = 1.0
        else:
            a = max(0.0, 1 - (t - THANKS_IN - THANKS_HOLD) / THANKS_OUT)
        text = self.font_thanks.render("Thank you", True, (255, 236, 170))
        text.set_alpha(int(255 * a))
        screen.blit(text, text.get_rect(center=(self.W // 2, self.H // 2)))

    def draw(self, screen):
        if self.phase == 'light':
            self._draw_light(screen)
        elif self.phase == 'to_black':
            screen.fill((0, 0, 0))
            self._overlay(screen, (255, 255, 255), 255 * (1 - self.t / TO_BLACK_T))
        elif self.phase == 'scroll':
            self._draw_scroll(screen)
        else:
            self._draw_thanks(screen)

"""Overworld -> battle transition, used for every wild and trainer battle.

Timeline (seconds from start):
  FLASH  : the screen flashes white twice
  WIPE   : black bars slide in from alternating sides until the screen is covered
  HOLD   : a short beat on black; `covered` turns True here and the game swaps
           to the battle underneath
  REVEAL : the black fades away over the battle scene

Time comes from pygame.time.get_ticks(), so the game only has to poll
`covered` / `done` and call draw() every frame — no update() needed while the
state stack switches from 'world' to 'encounter' mid-transition.

Usage (see Game.update / Game.draw):
    t = BattleTransition()
    ... if t.covered: push the encounter state
    t.draw(screen)          # last thing drawn each frame
    if t.done: drop it
"""
import math
import pygame

FLASH = 0.30
WIPE = 0.60
HOLD = 0.10
REVEAL = 0.35
BARS = 8
FLASH_COUNT = 2
FLASH_ALPHA = 200


def _ease_in_out(p):
    return p * p * (3 - 2 * p)


class BattleTransition:
    COVER_TIME = FLASH + WIPE + HOLD

    def __init__(self):
        self.start = pygame.time.get_ticks()
        self._white = None
        self._black = None

    @property
    def elapsed(self):
        return (pygame.time.get_ticks() - self.start) / 1000.0

    @property
    def covered(self):
        return self.elapsed >= self.COVER_TIME

    @property
    def done(self):
        return self.elapsed >= self.COVER_TIME + REVEAL

    def _surf(self, attr, size, color):
        s = getattr(self, attr)
        if s is None or s.get_size() != size:
            s = pygame.Surface(size)
            s.fill(color)
            setattr(self, attr, s)
        return s

    def draw(self, screen):
        t = self.elapsed
        w, h = screen.get_size()

        if t < FLASH:
            # two quick white pulses
            k = math.sin(math.pi * FLASH_COUNT * t / FLASH) ** 2
            white = self._surf('_white', (w, h), (255, 255, 255))
            white.set_alpha(int(FLASH_ALPHA * k))
            screen.blit(white, (0, 0))
            return

        if t < FLASH + WIPE:
            # bars close in, each slightly behind the one above it
            p = (t - FLASH) / WIPE
            bar_h = math.ceil(h / BARS)
            for i in range(BARS):
                q = max(0.0, min(1.0, p * 1.35 - i * 0.35 / BARS))
                bw = int(w * _ease_in_out(q))
                x = 0 if i % 2 == 0 else w - bw
                pygame.draw.rect(screen, (0, 0, 0), (x, i * bar_h, bw, bar_h))
            return

        black = self._surf('_black', (w, h), (0, 0, 0))
        if t < self.COVER_TIME:
            black.set_alpha(255)
        else:
            p = min(1.0, (t - self.COVER_TIME) / REVEAL)
            black.set_alpha(int(255 * (1 - _ease_in_out(p))))
        screen.blit(black, (0, 0))

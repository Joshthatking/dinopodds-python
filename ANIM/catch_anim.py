"""Battle catch animation — the pod throw when the player uses a catching item.

Phases (all procedural apart from the pod icon and the enemy's own sprite):
    throw   pod arcs from the player's side up to the wild dino, spinning
    absorb  pod pops open in a white flash, the dino shrinks into it in red
    drop    pod falls to the ground with a little bounce
    shake   pod rolls side to side `shakes` times
    caught  stars burst out of the pod, which then sits dimmed on the ground
    break   pod bursts open in a flash and the dino grows back out

Usage (see Game.attempt_catch in game.py):
    anim = CatchAnimation(pod_img, enemy_surface, enemy_center, enemy_size,
                          start_pos, success, on_finish=callback)
    anim.update(dt)       # every frame; calls on_finish once when done
    anim.draw(screen)     # after the battle scene is drawn
    anim.hides_enemy      # True while the battle scene shouldn't draw the dino
"""
import math
import random
import pygame
from moves import seg, lerp, ease_in, ease_out, hump

POD_SIZE = 50

THROW_T  = 0.60
ABSORB_T = 0.55
DROP_T   = 0.45
SHAKE_T  = 0.45   # one roll
PAUSE_T  = 0.30   # still beat between rolls
CAUGHT_T = 0.90
BREAK_T  = 0.55

STAR_COLORS = [(255, 240, 90), (255, 255, 255), (255, 200, 60)]


class CatchAnimation:
    def __init__(self, pod_img, enemy_surface, enemy_center, enemy_size,
                 start_pos, success, on_finish=None):
        self.pod = pygame.transform.smoothscale(pod_img, (POD_SIZE, POD_SIZE))
        self.enemy = enemy_surface
        self.ex, self.ey = enemy_center
        self.esize = enemy_size
        self.sx, self.sy = start_pos
        self.success = success
        self.on_finish = on_finish

        # A catch always rolls 3 times; a break-out gives up after 1-3.
        self.shakes = 3 if success else random.randint(1, 3)
        self.hold_x, self.hold_y = self.ex, self.ey - 10               # where it opens
        self.ground_y = self.ey + int(enemy_size * 0.32)                # where it lands

        end = 'caught' if success else 'break'
        self.phases = [('throw', THROW_T), ('absorb', ABSORB_T), ('drop', DROP_T)]
        for i in range(self.shakes):
            self.phases += [('pause', PAUSE_T), ('shake', SHAKE_T)]
        self.phases += [('pause', PAUSE_T), (end, CAUGHT_T if success else BREAK_T)]
        self.idx = 0
        self.t = 0.0
        self.done = False
        self._stars = [(random.uniform(0, math.tau), random.uniform(0.7, 1.2),
                        random.choice(STAR_COLORS)) for _ in range(8)]

    # ── timing ────────────────────────────────────────────────────────────

    @property
    def phase(self):
        return self.phases[min(self.idx, len(self.phases) - 1)][0]

    @property
    def p(self):
        """Progress 0..1 through the current phase."""
        dur = self.phases[min(self.idx, len(self.phases) - 1)][1]
        return min(1.0, self.t / dur) if dur else 1.0

    @property
    def hides_enemy(self):
        # During the throw the scene still draws the dino normally; from the
        # absorb on this class draws it (or nothing) until a break-out ends.
        if self.phase == 'throw':
            return False
        return not (self.done and not self.success)

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        while self.idx < len(self.phases) and self.t >= self.phases[self.idx][1]:
            self.t -= self.phases[self.idx][1]
            self.idx += 1
        if self.idx >= len(self.phases):
            self.idx = len(self.phases) - 1
            self.t = self.phases[self.idx][1]
            self.done = True
            if self.on_finish:
                cb, self.on_finish = self.on_finish, None
                cb()

    # ── drawing ───────────────────────────────────────────────────────────

    def _blit_pod(self, screen, x, y, angle=0.0, dim=False):
        img = self.pod
        if angle:
            img = pygame.transform.rotate(img, angle)
        if dim:
            img = img.copy()
            img.fill((150, 150, 150, 255), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(img, img.get_rect(center=(int(x), int(y))))

    def _blit_enemy(self, screen, scale, red, origin=None):
        """Enemy sprite at `scale` of full size, tinted red by `red` 0..1,
        squeezed toward `origin` (the pod's position, default mid-air)."""
        if not self.enemy or scale <= 0.02:
            return
        size = max(1, int(self.esize * scale))
        img = pygame.transform.scale(self.enemy, (size, size))
        if red > 0:
            tint = pygame.Surface((size, size), pygame.SRCALPHA)
            tint.fill((255, int(255 * (1 - red)), int(255 * (1 - red)), 255))
            img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            glow = pygame.Surface((size, size), pygame.SRCALPHA)
            glow.fill((int(120 * red), 0, 0, 0))
            img.blit(glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        ox, oy = origin or (self.hold_x, self.hold_y)
        cx = lerp(ox, self.ex, scale)
        cy = lerp(oy, self.ey, scale)
        screen.blit(img, img.get_rect(center=(int(cx), int(cy))))

    def _flash(self, screen, x, y, strength, radius, color=(255, 255, 255)):
        if strength <= 0:
            return
        r = int(radius)
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for i in range(4, 0, -1):
            a = int(255 * strength * (0.25 * (5 - i)) * 0.6)
            pygame.draw.circle(surf, (*color, min(255, a)), (r, r), int(r * i / 4))
        screen.blit(surf, (int(x) - r, int(y) - r))

    @staticmethod
    def _star(screen, x, y, size, color):
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = size if i % 2 == 0 else size * 0.45
            pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
        pygame.draw.polygon(screen, color, pts)

    def draw(self, screen):
        ph, p = self.phase, self.p

        if ph == 'throw':
            q = ease_out(p) if p < 1 else 1.0
            x = lerp(self.sx, self.hold_x, p)
            y = lerp(self.sy, self.hold_y, q) - 110 * hump(p)
            self._blit_pod(screen, x, y, angle=-720 * p)
            return

        if ph == 'absorb':
            # Pod hangs in the air, a white flash, dino shrinks into it in red
            self._blit_enemy(screen, 1 - ease_in(p), min(1.0, p * 2.5))
            self._flash(screen, self.hold_x, self.hold_y, hump(min(1.0, p * 1.6)),
                        26 + 34 * hump(p))
            self._blit_pod(screen, self.hold_x, self.hold_y + 3 * math.sin(p * 20))
            return

        if ph == 'drop':
            # Fall then one small bounce
            if p < 0.65:
                y = lerp(self.hold_y, self.ground_y, ease_in(p / 0.65))
            else:
                y = self.ground_y - 12 * hump((p - 0.65) / 0.35)
            self._blit_pod(screen, self.hold_x, y)
            return

        if ph == 'pause':
            self._blit_pod(screen, self.hold_x, self.ground_y)
            return

        if ph == 'shake':
            # Rock to one side and back, then the other side and back
            swing = math.sin(p * math.tau)
            self._blit_pod(screen, self.hold_x + 5 * swing, self.ground_y, angle=-26 * swing)
            return

        if ph == 'caught':
            self._blit_pod(screen, self.hold_x, self.ground_y, dim=p > 0.15)
            for ang, speed, color in self._stars:
                d = 46 * speed * ease_out(p)
                x = self.hold_x + math.cos(ang) * d
                y = self.ground_y - 6 + math.sin(ang) * d * 0.7 - 18 * p
                size = 7 * (1 - p) + 2
                if p < 0.95:
                    self._star(screen, x, y, size, color)
            return

        if ph == 'break':
            # Burst open — flash, pod fades out, dino grows back out
            self._blit_enemy(screen, ease_out(p), max(0.0, 1 - p * 1.8),
                             origin=(self.hold_x, self.ground_y))
            self._flash(screen, self.hold_x, self.ground_y - 10, hump(min(1.0, p * 1.4)),
                        30 + 40 * hump(p))
            if p < 0.25:
                self._blit_pod(screen, self.hold_x, self.ground_y - 30 * p)
            return

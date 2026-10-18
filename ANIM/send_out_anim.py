"""Battle intro animation — the enemy slides in, then the player sends out.

Timeline (seconds from when the battle becomes visible):
    0.00 - SLIDE_T      enemy dino slides in from off the left edge
    ...  - SEND_START   short beat on "A wild X appeared!"
    throw               player's pod (whatever it was caught in) arcs in
                        from the bottom-left, spinning
    open                pod hangs and jitters, light starts to burst
    grow                pod pops in a white flash, the dino grows out of
                        it, glowing white
    settle              the white glow fades off the dino

Everything is a pure function of elapsed time `t`, so the caller can drive
it from Game.encounter_anim['start_time'] (which is restarted once the
battle transition finishes and the scene is actually visible).

Usage (see Game.draw / Game.update in game.py):
    enemy_slide_offset(t, enemy_center_x, enemy_size)  -> px to shift the enemy
    anim = SendOutAnimation(pod_img, dino_img, dino_rect)
    anim.player_hidden(t)   # True until the dino is fully out
    anim.draw(screen, t)    # after the battle UI is drawn
"""
import math
import pygame
from moves import seg, lerp, ease_in, ease_out, hump

SLIDE_T    = 0.70
SEND_START = 1.20
THROW_T    = 0.55
OPEN_T     = 0.15
GROW_T     = 0.45
SETTLE_T   = 0.30
TOTAL_T    = SEND_START + THROW_T + OPEN_T + GROW_T + SETTLE_T
TOTAL_MS   = int(TOTAL_T * 1000) + 100    # small beat before "What will you do?"
SLIDE_ONLY_MS = int(SLIDE_T * 1000) + 300  # a trainer's next dino: slide only

POD_SIZE = 44
SPARK_COLS = ((255, 255, 255), (255, 245, 170), (200, 235, 255))


def enemy_slide_offset(t, enemy_center_x, enemy_size):
    """Horizontal offset for the enemy sprite: starts fully off the left
    edge of the screen, eases into its normal spot."""
    start_x = -enemy_size / 2
    p = min(1.0, max(0.0, t / SLIDE_T))
    return (start_x - enemy_center_x) * (1 - ease_out(p))


class SendOutAnimation:
    def __init__(self, pod_img, dino_img, dino_rect, start_pos=(-30, 400)):
        self.pod = pygame.transform.smoothscale(pod_img, (POD_SIZE, POD_SIZE))
        self.dino = pygame.transform.scale(dino_img, dino_rect.size)
        self.rect = dino_rect
        self.sx, self.sy = start_pos
        # pod opens a little above the middle of the dino's body
        self.ox, self.oy = dino_rect.centerx, dino_rect.centery + dino_rect.height * 0.12
        self._t_throw = SEND_START
        self._t_open = self._t_throw + THROW_T
        self._t_grow = self._t_open + OPEN_T
        self._t_settle = self._t_grow + GROW_T

    def player_hidden(self, t):
        return t < TOTAL_T

    # ── drawing ───────────────────────────────────────────────────────────

    def _blit_pod(self, screen, x, y, angle=0.0, scale=1.0):
        img = self.pod
        if scale != 1.0:
            s = max(1, int(POD_SIZE * scale))
            img = pygame.transform.smoothscale(img, (s, s))
        if angle:
            img = pygame.transform.rotate(img, angle)
        screen.blit(img, img.get_rect(center=(int(x), int(y))))

    @staticmethod
    def _flash(screen, x, y, strength, radius):
        if strength <= 0 or radius < 1:
            return
        r = int(radius)
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for i in range(5, 0, -1):
            a = int(255 * strength * (0.2 * (6 - i)) * 0.6)
            pygame.draw.circle(surf, (255, 255, 255, min(255, a)), (r, r), int(r * i / 5))
        screen.blit(surf, (int(x) - r, int(y) - r))

    def _blit_dino(self, screen, scale, white):
        """The dino at `scale` of full size, grown from the pod's spot and
        washed toward white by `white` 0..1."""
        if scale <= 0.02:
            return
        w = max(1, int(self.rect.width * scale))
        h = max(1, int(self.rect.height * scale))
        img = pygame.transform.scale(self.dino, (w, h))
        if white > 0:
            v = int(255 * white)
            img.fill((v, v, v, 0), special_flags=pygame.BLEND_RGBA_ADD)
        cx = lerp(self.ox, self.rect.centerx, scale)
        bottom = lerp(self.oy + h / 2, self.rect.bottom, scale)
        screen.blit(img, img.get_rect(centerx=int(cx), bottom=int(bottom)))

    def draw(self, screen, t):
        if t < self._t_throw:
            return

        p = seg(t, self._t_throw, self._t_open)
        if p is not None:
            x = lerp(self.sx, self.ox, p)
            y = lerp(self.sy, self.oy, ease_out(p)) - 120 * hump(p)
            self._blit_pod(screen, x, y, angle=-900 * p)
            return

        p = seg(t, self._t_open, self._t_grow)
        if p is not None:
            # hangs in the air, wobbling, light leaking out
            self._flash(screen, self.ox, self.oy, 0.6 * p, 18 + 14 * p)
            self._blit_pod(screen, self.ox + 2 * math.sin(p * 40), self.oy,
                           angle=12 * math.sin(p * 30))
            return

        p = seg(t, self._t_grow, self._t_settle)
        if p is not None:
            self._blit_dino(screen, ease_out(p), 1.0)
            self._flash(screen, self.ox, self.oy, hump(min(1.0, 0.5 + p * 0.8)),
                        30 + 70 * ease_out(p))
            for i in range(10):
                ang = i * math.tau / 10 + 0.3
                d = 20 + 90 * ease_out(p)
                x, y = self.ox + math.cos(ang) * d, self.oy + math.sin(ang) * d * 0.8
                s = 5 * (1 - p) + 1
                col = SPARK_COLS[i % len(SPARK_COLS)]
                pygame.draw.line(screen, col, (x - s, y), (x + s, y), 2)
                pygame.draw.line(screen, col, (x, y - s), (x, y + s), 2)
            if p < 0.35:
                self._blit_pod(screen, self.ox, self.oy - 20 * p, scale=1 - p / 0.35)
            return

        p = seg(t, self._t_settle, TOTAL_T)
        if p is not None:
            self._blit_dino(screen, 1.0, 1 - ease_in(p))

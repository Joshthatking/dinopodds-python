"""SAYDIE — side quest.

Saydie stands on the beach at (-112, -24) in LOST_REGION.world. Talk to her
on DAYS_NEEDED different day/night phases (each day and each night counts
as its own visit; talking twice in the same phase only counts once). On the
visit that reaches DAYS_NEEDED she asks if you have a question: "May I be
your bf?" is written into the sand beside the two of you, she says yes, a
heart is traced around the words and little hearts and fireworks pop up.
After that she has her "together" line, and the message stays in the sand.

State lives in game.story_flags (so it saves with the game):
    day_cycle        — counts every day<->night change (shared, see track_cycle)
    cycle_is_night   — the phase day_cycle last saw
    saydie_days      — list of day_cycle values she's been talked to on
    saydie_together  — True once the proposal is done
    saydie_sand      — [x, y] world pixel spot of the sand message
Touch points in game.py are tagged `# SAYDIE`.
"""
import math
import random
import pygame
import config

WORLD = 'LOST_REGION.world'
NPC_ID = 'saydie'
NAME = 'Saydie'
DAYS_NEEDED = 5

DATE_LINES = [
    "Oh hey I had a great time last time we went out!",
    "Would love to go out again sometime :)",
]
ASK_LINE = "You have a question? Yes what is it :)"
YES_LINE = "Oh my yes yes 100% yes!!"
TOGETHER_LINE = "So so happy to be with you! We have so much to look forward to and its only the beginning :)"

SAND_TEXT = "May I be your bf?"
SAND_DARK = (138, 104, 62)      # groove
SAND_LIGHT = (250, 232, 185)    # lit lip under each groove
WRITE_SPEED = 0.13              # seconds per letter
HEART_TIME = 1.6
CELEBRATE_TIME = 5.0
FIREWORK_COLORS = [(255, 90, 140), (255, 210, 80), (120, 200, 255), (200, 120, 255), (255, 150, 90)]
HEART_COLORS = [(255, 95, 140), (255, 140, 175), (235, 60, 110)]


def _heart_point(u):
    """Classic heart curve, u in 0..2pi -> (x, y) roughly in -16..16, y down."""
    x = 16 * math.sin(u) ** 3
    y = 13 * math.cos(u) - 5 * math.cos(2 * u) - 2 * math.cos(3 * u) - math.cos(4 * u)
    return x, -y


def _draw_heart(surf, x, y, size, col, alpha=255):
    """Small filled heart centered on (x, y)."""
    size = max(2, int(size))
    tmp = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
    r = size // 2 + 1
    c = (*col, max(0, min(255, int(alpha))))
    pygame.draw.circle(tmp, c, (size + 1 - r + 1, size), r)
    pygame.draw.circle(tmp, c, (size + 1 + r - 1, size), r)
    pygame.draw.polygon(tmp, c, [(size + 1 - size, size + 1), (size + 1 + size, size + 1), (size + 1, size * 2 + 1)])
    surf.blit(tmp, (int(x) - size - 1, int(y) - size - 1))


class SaydieQuest:
    def __init__(self, game):
        self.game = game
        self.scene = None          # proposal scene state while it plays
        self._font = None
        self._text_cache = None

    # ── day / night tracking ─────────────────────────────────────────────
    def track_cycle(self):
        """Bump story_flags['day_cycle'] every time day turns to night or back
        (natural or story-forced), so each phase has its own number."""
        g = self.game
        f = g.story_flags
        # The phase actually shown — a forced day/night (story or the sandbox
        # Ctrl+N switch) counts too; an eclipse doesn't.
        night = bool(g.force_night if g.force_night is not None else g.is_night)
        if 'cycle_is_night' not in f:
            f['cycle_is_night'] = night
            f.setdefault('day_cycle', 0)
        elif f['cycle_is_night'] != night:
            f['cycle_is_night'] = night
            f['day_cycle'] = f.get('day_cycle', 0) + 1

    # ── talking to her ───────────────────────────────────────────────────
    def interact(self, npc):
        g = self.game
        f = g.story_flags
        npc.face_toward_player(g.player)
        if f.get('saydie_together'):
            g.message_box.queue_messages(g._tag_dialogue(NAME, [TOGETHER_LINE]), wait_for_input=True)
            return
        days = f.setdefault('saydie_days', [])
        cycle = f.get('day_cycle', 0)
        if cycle not in days:
            days.append(cycle)
        if len(days) >= DAYS_NEEDED:
            self._start_proposal(npc)
        else:
            g.message_box.queue_messages(g._tag_dialogue(NAME, DATE_LINES), wait_for_input=True)

    # ── the proposal scene ───────────────────────────────────────────────
    def _start_proposal(self, npc):
        g = self.game
        g.player.freeze_in_place()
        g.cutscene = {'phase': 'saydie_proposal'}
        # Write to the right of whichever of the two of them is further right
        ts = config.TILE_SIZE
        right = max(g.player.rect.right, npc.rect.right)
        cy = (g.player.rect.centery + npc.rect.centery) // 2
        self.scene = {'stage': 'ask', 't': 0.0, 'npc': npc,
                      'x': right + ts // 2, 'y': cy + ts // 4,
                      'bursts': [], 'hearts': [], 'next_burst': 0.0, 'next_heart': 0.0}
        g.message_box.queue_messages(g._tag_dialogue(NAME, [ASK_LINE]), wait_for_input=True,
                                     on_complete=lambda: self._set_stage('write'))

    def _set_stage(self, stage):
        if self.scene:
            self.scene['stage'] = stage
            self.scene['t'] = 0.0

    def _said_yes(self):
        self._set_stage('heart')

    def _finish(self):
        g = self.game
        f = g.story_flags
        f['saydie_together'] = True
        f['saydie_sand'] = [self.scene['x'], self.scene['y']]
        self.scene = None
        g.cutscene = None

    def update(self, dt):
        """Called from Game._update_cutscene while the proposal plays."""
        sc = self.scene
        if sc is None:
            self.game.cutscene = None
            return
        sc['t'] += dt
        st = sc['stage']
        if st == 'write' and sc['t'] >= len(SAND_TEXT) * WRITE_SPEED + 0.6:
            sc['stage'] = 'answer'
            self.game.message_box.queue_messages(
                self.game._tag_dialogue(NAME, [YES_LINE]), wait_for_input=True, on_complete=self._said_yes)
        elif st == 'heart' and sc['t'] >= HEART_TIME:
            self._set_stage('celebrate')
        elif st == 'celebrate':
            self._update_celebration(dt)
            if sc['t'] >= CELEBRATE_TIME and not sc['bursts'] and not sc['hearts']:
                self._finish()

    def _update_celebration(self, dt):
        sc = self.scene
        g = self.game
        ts = config.TILE_SIZE
        px = (g.player.rect.centerx + sc['npc'].rect.centerx) / 2
        py = (g.player.rect.centery + sc['npc'].rect.centery) / 2
        spawning = sc['t'] < CELEBRATE_TIME - 1.2
        sc['next_heart'] -= dt
        while spawning and sc['next_heart'] <= 0:
            sc['next_heart'] += 0.09
            sc['hearts'].append({'x': px + random.uniform(-2.5, 2.5) * ts, 'y': py + random.uniform(-0.2, 0.8) * ts,
                                 'vx': random.uniform(-8, 8), 'rise': random.uniform(22, 42), 't': 0.0,
                                 'life': random.uniform(1.2, 2.0), 'size': random.uniform(3, 6),
                                 'col': random.choice(HEART_COLORS), 'ph': random.uniform(0, math.tau)})
        sc['next_burst'] -= dt
        while spawning and sc['next_burst'] <= 0:
            sc['next_burst'] += random.uniform(0.25, 0.45)
            col = random.choice(FIREWORK_COLORS)
            sc['bursts'].append({'x': px + random.uniform(-3.5, 3.5) * ts, 'y': py - random.uniform(1.2, 3.2) * ts,
                                 't': 0.0, 'life': 1.1, 'col': col, 'n': random.randint(12, 18),
                                 'r': random.uniform(18, 30), 'rot': random.uniform(0, math.tau)})
            sfx = getattr(g, 'sfx', None)
            if sfx:
                sfx.play('select', volume=0.4)
        for h in sc['hearts']:
            h['t'] += dt
            h['y'] -= h['rise'] * dt
            h['x'] += h['vx'] * dt + math.sin(h['t'] * 5 + h['ph']) * 12 * dt
        sc['hearts'] = [h for h in sc['hearts'] if h['t'] < h['life']]
        for b in sc['bursts']:
            b['t'] += dt
        sc['bursts'] = [b for b in sc['bursts'] if b['t'] < b['life']]

    # ── drawing ──────────────────────────────────────────────────────────
    def _text_surfaces(self):
        if self._text_cache is None:
            if self._font is None:
                self._font = pygame.font.Font(None, 20)
            dark = self._font.render(SAND_TEXT, False, SAND_DARK)
            light = self._font.render(SAND_TEXT, False, SAND_LIGHT)
            self._text_cache = (dark, light)
        return self._text_cache

    def _visible(self):
        g = self.game
        return g.current_world_file == WORLD

    def draw_ground(self, surf, cam_x, cam_y):
        """The words (and heart) written in the sand, under everyone's feet."""
        if not self._visible():
            return
        sc = self.scene
        if sc is not None:
            st = sc['stage']
            if st == 'ask':
                return
            x, y = sc['x'], sc['y']
            letters = int(sc['t'] / WRITE_SPEED) if st == 'write' else len(SAND_TEXT)
            heart = {'write': 0.0, 'answer': 0.0, 'heart': min(1.0, sc['t'] / HEART_TIME)}.get(st, 1.0)
        elif self.game.story_flags.get('saydie_sand'):
            x, y = self.game.story_flags['saydie_sand']
            letters, heart = len(SAND_TEXT), 1.0
        else:
            return
        dark, light = self._text_surfaces()
        tw, th = dark.get_size()
        sx, sy = x - cam_x, y - cam_y - th // 2
        if letters > 0:
            # Reveal letter by letter: crop to the width of the first `letters` characters
            w = self._font.size(SAND_TEXT[:min(letters, len(SAND_TEXT))])[0]
            area = pygame.Rect(0, 0, w, th)
            surf.blit(light, (sx, sy + 1), area)
            surf.blit(dark, (sx, sy), area)
            if sc is not None and sc['stage'] == 'write' and letters < len(SAND_TEXT):
                # a little stick drawing the letters, kicking up sand
                pen_x, pen_y = sx + w, sy + th // 2 + math.sin(sc['t'] * 30) * 3
                pygame.draw.line(surf, (120, 80, 45), (pen_x, pen_y), (pen_x + 6, pen_y - 12), 2)
                for i in range(3):
                    a = sc['t'] * 9 + i * 2.1
                    pygame.draw.circle(surf, SAND_LIGHT, (int(pen_x - 2 + math.cos(a) * 4), int(pen_y + 3 + math.sin(a) * 2)), 1)
        if heart > 0:
            self._draw_sand_heart(surf, sx + tw / 2, sy + th / 2 + 2, tw, th, heart)

    def _draw_sand_heart(self, surf, cx, cy, tw, th, k):
        scale_x = (tw + 26) / 32.0
        scale_y = max(scale_x * 0.6, (th + 26) / 22.0)
        n = 64
        upto = int(n * k)
        pts = []
        for i in range(upto + 1):
            u = math.pi + i / n * math.tau      # start at the top dip, trace all the way round
            hx, hy = _heart_point(u)
            pts.append((cx + hx * scale_x, cy + (hy + 2.5) * scale_y))
        if len(pts) >= 2:
            pygame.draw.lines(surf, SAND_LIGHT, False, [(x, y + 1) for x, y in pts], 2)
            pygame.draw.lines(surf, SAND_DARK, False, pts, 2)
        if 0 < k < 1 and pts:
            hx, hy = pts[-1]
            pygame.draw.line(surf, (120, 80, 45), (hx, hy), (hx + 6, hy - 12), 2)

    def draw_fx(self, surf, cam_x, cam_y):
        """Hearts and fireworks, drawn over the world (after the map's top layer)."""
        sc = self.scene
        if sc is None or sc['stage'] != 'celebrate' or not self._visible():
            return
        for b in sc['bursts']:
            p = b['t'] / b['life']
            e = 1 - (1 - p) ** 2
            bx, by = b['x'] - cam_x, b['y'] - cam_y
            fade = 1 - p
            for i in range(b['n']):
                ang = b['rot'] + i * math.tau / b['n']
                d = b['r'] * e
                x = bx + math.cos(ang) * d
                y = by + math.sin(ang) * d + 14 * p * p
                tx = bx + math.cos(ang) * d * 0.7
                ty = by + math.sin(ang) * d * 0.7 + 14 * p * p
                col = tuple(int(c * (0.4 + 0.6 * fade)) for c in b['col'])
                pygame.draw.line(surf, col, (tx, ty), (x, y), 1)
                pygame.draw.circle(surf, (255, 255, 255) if p < 0.3 else b['col'], (int(x), int(y)), 1 if p > 0.5 else 2)
            if p < 0.15:
                pygame.draw.circle(surf, (255, 255, 230), (int(bx), int(by)), int(4 * (1 - p / 0.15)) + 1)
        for h in sc['hearts']:
            q = h['t'] / h['life']
            alpha = 255 * min(1.0, q * 5) * (1 - max(0.0, q - 0.6) / 0.4)
            _draw_heart(surf, h['x'] - cam_x, h['y'] - cam_y, h['size'], h['col'], alpha)

import os
import pygame
import config
from data import *


def load_image(path, alpha=False):
    image = pygame.image.load(path)
    return image.convert_alpha() if alpha else image.convert()


def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    if current_line:
        lines.append(current_line.strip())
    return lines


# === Encounter Background ===
class Encounter:
    def __init__(self, fonts, dino_key="default"):
        self.fonts = fonts
        self.dino_key = dino_key
        self.bg = load_image(config.ENCOUNTER_BG_PATH)
        self.frames = []
        if dino_key in config.ENCOUNTER_DINOS_PATHS:
            self.frames.append(load_image(config.ENCOUNTER_DINOS_PATHS[dino_key], alpha=True))
        if dino_key + "2" in config.ENCOUNTER_DINOS_PATHS:
            self.frames.append(load_image(config.ENCOUNTER_DINOS_PATHS[dino_key + "2"], alpha=True))
        self.current_dino_surface = self.frames[0] if self.frames else None

    def draw(self, screen, enemy_visible=True):
        screen.blit(self.bg, (0, 0))
        if self.current_dino_surface and enemy_visible:
            mult = config.ENCOUNTER_DINO_SIZES.get(self.dino_key, 1.0)
            size = int(config.ENCOUNTER_BASE_SIZE * mult)
            scaled = pygame.transform.scale(self.current_dino_surface, (size, size))
            rect = scaled.get_rect()
            rect.centerx = screen.get_width() - 157
            rect.centery = 155
            screen.blit(scaled, rect)


# === Double Battle Background ===
class DoubleBattleEncounter:
    """Background + two side-by-side enemy sprites for double trainer battles."""

    def __init__(self, fonts, dino1_key, dino2_key):
        self.fonts = fonts
        self.bg = load_image(config.DOUBLE_BATTLE_BG_PATH)
        self.frame1 = (load_image(config.ENCOUNTER_DINOS_PATHS[dino1_key], alpha=True)
                       if dino1_key in config.ENCOUNTER_DINOS_PATHS else None)
        self.frame2 = (load_image(config.ENCOUNTER_DINOS_PATHS[dino2_key], alpha=True)
                       if dino2_key in config.ENCOUNTER_DINOS_PATHS else None)

    def draw(self, screen, e1_visible=True, e2_visible=True):
        screen.blit(self.bg, (0, 0))
        size = 120
        sw = screen.get_width()
        if self.frame1 and e1_visible:
            scaled = pygame.transform.scale(self.frame1, (size, size))
            r = scaled.get_rect(centerx=sw - 250, centery=145)
            screen.blit(scaled, r)
        if self.frame2 and e2_visible:
            scaled = pygame.transform.scale(self.frame2, (size, size))
            r = scaled.get_rect(centerx=sw - 120, centery=145)
            screen.blit(scaled, r)


# === Double Battle UI ===
class DoubleBattleUI:
    """HUD for 2v2 trainer battles: compact info boxes, no XP bar."""

    def __init__(self, fonts):
        self.font        = fonts['DIALOGUE']
        self.small_font  = fonts['BAG']
        self.smaller_font = fonts['XS']
        self.selected_option = 0
        self.actions     = ["Fight", "Bag", "Party", "Run", "Defend"]
        self.in_fight_menu  = False
        self.move_selected  = 0
        self.level_up_popup = None
        self.xp_frozen      = True   # not used visually; kept for API compat

        self.enemy1_hp_display  = None
        self.enemy2_hp_display  = None
        self.player1_hp_display = None
        self.player2_hp_display = None
        self._hp_speed = 0.35

        # Stored so is_hp_animating can check all four
        self._last_p2 = None
        self._last_e2 = None

        # Double battle input phase state
        self.in_target_menu      = False
        self.target_idx          = 0      # 0 = enemy 1, 1 = enemy 2
        self._pending_move_name  = None
        self.selecting_p2        = False  # True when selecting Dino 2's action

    def unfreeze_xp(self):
        self.xp_frozen = False

    def is_xp_animating(self):
        return False

    def show_level_up(self, dino, old_stats, new_stats):
        self.level_up_popup = LevelUpPopup(dino, old_stats, new_stats)

    def _slide(self, current, target, dt):
        if current is None:
            return target
        diff = target - current
        step = self._hp_speed * dt
        if abs(diff) <= step:
            return target
        return current + step * (1 if diff > 0 else -1)

    def update(self, dt, p1, p2, e1, e2):
        self._last_p2 = p2
        self._last_e2 = e2
        tp1 = p1['hp'] / max(1, p1['max_hp'])
        tp2 = p2['hp'] / max(1, p2['max_hp']) if p2 else 0.0
        te1 = e1['hp'] / max(1, e1['max_hp'])
        te2 = e2['hp'] / max(1, e2['max_hp']) if e2 else 0.0
        if self.player1_hp_display is None: self.player1_hp_display = tp1
        if self.player2_hp_display is None: self.player2_hp_display = tp2
        if self.enemy1_hp_display  is None: self.enemy1_hp_display  = te1
        if self.enemy2_hp_display  is None: self.enemy2_hp_display  = te2
        self.player1_hp_display = self._slide(self.player1_hp_display, tp1, dt)
        self.player2_hp_display = self._slide(self.player2_hp_display, tp2, dt)
        self.enemy1_hp_display  = self._slide(self.enemy1_hp_display,  te1, dt)
        self.enemy2_hp_display  = self._slide(self.enemy2_hp_display,  te2, dt)

    def is_hp_animating(self, p1, e1):
        tp1 = p1['hp'] / max(1, p1['max_hp'])
        te1 = e1['hp'] / max(1, e1['max_hp'])
        p2  = self._last_p2
        e2  = self._last_e2
        tp2 = p2['hp'] / max(1, p2['max_hp']) if p2 else 0.0
        te2 = e2['hp'] / max(1, e2['max_hp']) if e2 else 0.0
        return (
            (self.player1_hp_display is not None and abs(self.player1_hp_display - tp1) > 0.001) or
            (self.enemy1_hp_display  is not None and abs(self.enemy1_hp_display  - te1) > 0.001) or
            (self.player2_hp_display is not None and abs(self.player2_hp_display - tp2) > 0.001) or
            (self.enemy2_hp_display  is not None and abs(self.enemy2_hp_display  - te2) > 0.001)
        )

    def _draw_panel(self, surface, rect, bg=(245, 245, 245), border=(0, 0, 0), bw=3):
        pygame.draw.rect(surface, bg, rect)
        pygame.draw.rect(surface, border, rect, bw)

    def _draw_slanted_panel(self, surface, x, y, w, h, slant=18,
                             bg=(245, 245, 245), border=(0, 0, 0), bw=3,
                             slant_side='right'):
        """Panel with one slanted corner.
        slant_side='right' cuts the bottom-right corner (enemy boxes).
        slant_side='left'  cuts the bottom-left  corner (player boxes).
        """
        if slant_side == 'right':
            pts = [(x, y), (x+w, y), (x+w, y+h-slant), (x+w-slant, y+h), (x, y+h)]
        else:
            pts = [(x, y), (x+w, y), (x+w, y+h), (x+slant, y+h), (x, y+h-slant)]
        pygame.draw.polygon(surface, bg, pts)
        pygame.draw.polygon(surface, border, pts, bw)

    def _fit_name(self, name, font, max_w):
        while len(name) > 1 and font.size(name)[0] > max_w:
            name = name[:-1]
        return name

    def _draw_hp_bar(self, surface, x, y, w, h, pct,
                     back=(200, 0, 0), front=(0, 200, 0)):
        pct = max(0.0, min(1.0, pct))
        pygame.draw.rect(surface, back,  (x, y, w, h))
        pygame.draw.rect(surface, front, (x, y, int(w * pct), h))

    def draw(self, surface, p1, p2, e1, e2, encounter_text,
             show_actions=True, msg_awaiting_input=False,
             p1_visible=True, p2_visible=True,
             e1_visible=True, e2_visible=True,
             active_dino=None):

        sw, sh = surface.get_size()

        # ── Dialogue + action panels ───────────────────────────────
        text_rect = pygame.Rect(9, sh - 120, sw - 325, 115)
        act_rect  = pygame.Rect(sw - 300, sh - 120, 287, 115)
        for r in (text_rect, act_rect):
            self._draw_panel(surface, r)

        # ── HP ratios ──────────────────────────────────────────────
        ep1 = self.enemy1_hp_display  if self.enemy1_hp_display  is not None else e1['hp'] / max(1, e1['max_hp'])
        ep2 = (self.enemy2_hp_display if self.enemy2_hp_display  is not None
               else (e2['hp'] / max(1, e2['max_hp']) if e2 else 0.0))
        pp1 = self.player1_hp_display if self.player1_hp_display is not None else p1['hp'] / max(1, p1['max_hp'])
        pp2 = (self.player2_hp_display if self.player2_hp_display is not None
               else (p2['hp'] / max(1, p2['max_hp']) if p2 else 0.0))

        sf  = self.small_font
        SLANT = 18

        # ── Enemy stat boxes — top-left, stacked, slanted bottom-right
        # en1: base box; en2: slightly wider
        en1_x, en1_y, en1_w, en1_h = 4, 26,  215, 46
        en2_x, en2_y, en2_w, en2_h = 4, 78,  235, 46

        self._draw_slanted_panel(surface, en1_x, en1_y, en1_w, en1_h, SLANT, slant_side='right')
        if e2:
            self._draw_slanted_panel(surface, en2_x, en2_y, en2_w, en2_h, SLANT, slant_side='right')

        def draw_enemy_stat(d, pct, bx, by, bw, ko):
            if ko:
                surface.blit(sf.render("KO", True, (160, 0, 0)), (bx + 8, by + 14))
                return
            name = self._fit_name(d['name'], sf, bw - 70)
            surface.blit(sf.render(name,             True, (0, 0, 0)), (bx + 8,      by + 6))
            surface.blit(sf.render(f"Lv{d['level']}", True, (0, 0, 0)), (bx + bw - 55, by + 6))
            self._draw_hp_bar(surface, bx + 8, by + 28, bw - SLANT - 12, 10, pct)

        draw_enemy_stat(e1, ep1, en1_x, en1_y, en1_w, ep1 <= 0.01)
        if e2:
            draw_enemy_stat(e2, ep2, en2_x, en2_y, en2_w, ep2 <= 0.01)

        # ── Player stat boxes — right side, stacked, slanted bottom-left
        text_top = text_rect.top
        pl_w  = 210
        pl_h  = 46
        pl_x  = sw - pl_w - 4   # flush right with small margin
        pl1_y = text_top - pl_h - 8         # just above dialogue box
        pl2_y = pl1_y - pl_h - 6            # stacked above pl1

        self._draw_slanted_panel(surface, pl_x, pl1_y, pl_w, pl_h, SLANT, slant_side='left')
        if p2:
            self._draw_slanted_panel(surface, pl_x, pl2_y, pl_w, pl_h, SLANT, slant_side='left')

        def draw_player_stat(d, pct, bx, by, bw, ko):
            if ko:
                surface.blit(sf.render("KO", True, (160, 0, 0)), (bx + SLANT + 6, by + 14))
                return
            # left side is slanted at bottom only; text starts after slant offset at top (safe)
            name = self._fit_name(d['name'], sf, bw - 70)
            surface.blit(sf.render(name,              True, (0, 0, 0)), (bx + 8,      by + 6))
            surface.blit(sf.render(f"Lv{d['level']}", True, (0, 0, 0)), (bx + bw - 55, by + 6))
            self._draw_hp_bar(surface, bx + SLANT + 4, by + 28, bw - SLANT - 12, 10, pct)

        draw_player_stat(p1, pp1, pl_x, pl1_y, pl_w, pp1 <= 0.01)
        if p2:
            draw_player_stat(p2, pp2, pl_x, pl2_y, pl_w, pp2 <= 0.01)

        # ── Player back sprites (hide if KO'd) ────────────────────
        if p1_visible and pp1 > 0.01:
            img = pygame.transform.scale(p1['image'], (170, 170))
            r   = img.get_rect(centerx=text_rect.x + 85, bottom=text_top)
            surface.blit(img, r)
        if p2 and p2_visible and pp2 > 0.01:
            img = pygame.transform.scale(p2['image'], (170, 170))
            r   = img.get_rect(centerx=text_rect.x + 235, bottom=text_top)
            surface.blit(img, r)

        # ── Level-up popup ─────────────────────────────────────────
        if self.level_up_popup and self.level_up_popup.active:
            dim = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))
            surface.blit(dim, (0, 0))
            self.level_up_popup.draw(surface)

        # ── Text box ───────────────────────────────────────────────
        lines = wrap_text(encounter_text, sf, text_rect.width - 40)
        for i, line in enumerate(lines[:5]):
            surface.blit(sf.render(line, True, (0, 0, 0)),
                         (text_rect.x + 20, text_rect.y + 12 + i * 20))

        if msg_awaiting_input and pygame.time.get_ticks() // 400 % 2:
            cx, cy = act_rect.left - 18, text_rect.bottom - 10
            pygame.draw.polygon(surface, (0, 0, 0),
                                [(cx - 8, cy - 7), (cx + 8, cy - 7), (cx, cy + 3)])

        # ── Action / fight / target menu ───────────────────────────
        if not show_actions:
            return

        # Label: which dino is currently selecting
        label = "Dino 2:" if self.selecting_p2 else "Dino 1:"
        surface.blit(self.smaller_font.render(label, True, (60, 60, 200)),
                     (act_rect.x + 8, act_rect.y + 4))

        # Target selection mode
        if self.in_target_menu:
            half_w = act_rect.width // 2
            for i, en in enumerate([e1, e2]):
                if not en:
                    continue
                tr = pygame.Rect(act_rect.x + i * half_w, act_rect.y + 18, half_w, act_rect.height - 22)
                alive = en.get('hp', 0) > 0
                bg = (180, 230, 180) if (i == self.target_idx and alive) else (210, 210, 210)
                pygame.draw.rect(surface, bg, tr)
                bc = (255, 215, 0) if (i == self.target_idx and alive) else (120, 120, 120)
                pygame.draw.rect(surface, bc, tr, 3)
                name = en['name'] if alive else "KO"
                col  = (0, 0, 0) if alive else (140, 0, 0)
                ts = self.small_font.render(name, True, col)
                surface.blit(ts, (tr.centerx - ts.get_width() // 2, tr.centery - ts.get_height() // 2))
            # Arrow hint
            hint = self.smaller_font.render("A/D to target  J to confirm", True, (80, 80, 80))
            surface.blit(hint, (act_rect.x + 4, act_rect.bottom - hint.get_height() - 2))
            return

        if not self.in_fight_menu:
            for i in range(4):
                color = (0, 0, 255) if i == self.selected_option else (0, 0, 0)
                surface.blit(self.font.render(self.actions[i], True, color),
                             (act_rect.x + 20 + (i % 2) * 120,
                              act_rect.y + 20 + (i // 2) * 50))
            defend_rect = pygame.Rect(act_rect.right - 80, act_rect.y + 5, 74, 105)
            pygame.draw.rect(surface, (15, 25, 110), defend_rect, border_radius=5)
            bc = (255, 215, 0) if self.selected_option == 4 else (0, 0, 60)
            pygame.draw.rect(surface, bc, defend_rect, 3, border_radius=5)
            ds = self.small_font.render("DEFEND", True, (255, 255, 255))
            surface.blit(ds, (defend_rect.centerx - ds.get_width() // 2,
                              defend_rect.centery - ds.get_height() // 2))
        else:
            cur = active_dino or p1
            moves = cur.get('moves', [])
            qw, qh = act_rect.width // 2, act_rect.height // 2
            for i in range(4):
                col, row = i % 2, i // 2
                rect = pygame.Rect(act_rect.x + col * qw, act_rect.y + row * qh, qw, qh)
                if i < len(moves):
                    mt  = MOVE_DATA.get(moves[i], {}).get("type", "normal")
                    bg  = TYPE_DATA.get(mt, {}).get("color", (200, 200, 200))
                    txt = moves[i]
                    tc  = (255, 255, 255)
                else:
                    bg, txt, tc = (150, 150, 150), "—", (100, 100, 100)
                pygame.draw.rect(surface, bg, rect)
                bc = (255, 255, 0) if i == self.move_selected else (0, 0, 0)
                pygame.draw.rect(surface, bc, rect, 3)
                ts = self.small_font.render(txt, True, tc)
                surface.blit(ts, (rect.centerx - ts.get_width() // 2,
                                  rect.centery - ts.get_height() // 2))

    def handle_input(self, event, player_dino):
        if self.level_up_popup and self.level_up_popup.active:
            self.level_up_popup.handle_event(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        if not self.in_fight_menu:
            NAV_W = [2, 3, 0, 1, 1]
            NAV_S = [2, 3, 0, 1, 3]
            NAV_A = [4, 0, 4, 2, 3]
            NAV_D = [1, 4, 3, 4, 0]
            if event.key == pygame.K_w:
                self.selected_option = NAV_W[self.selected_option]
            elif event.key == pygame.K_s:
                self.selected_option = NAV_S[self.selected_option]
            elif event.key == pygame.K_a:
                self.selected_option = NAV_A[self.selected_option]
            elif event.key == pygame.K_d:
                self.selected_option = NAV_D[self.selected_option]
            elif event.key == pygame.K_j:
                if self.actions[self.selected_option] == "Fight":
                    self.in_fight_menu = True
                else:
                    return self.actions[self.selected_option]
        else:
            mc = len(player_dino['moves'])
            if event.key == pygame.K_w:
                self.move_selected = (self.move_selected - 2) % 4
                while self.move_selected >= mc: self.move_selected = (self.move_selected - 1) % 4
            elif event.key == pygame.K_s:
                self.move_selected = (self.move_selected + 2) % 4
                while self.move_selected >= mc: self.move_selected = (self.move_selected - 1) % 4
            elif event.key == pygame.K_a:
                self.move_selected = (self.move_selected - 1) % 4
                while self.move_selected >= mc: self.move_selected = (self.move_selected - 1) % 4
            elif event.key == pygame.K_d:
                self.move_selected = (self.move_selected + 1) % 4
                while self.move_selected >= mc: self.move_selected = (self.move_selected - 1) % 4
            elif event.key == pygame.K_j:
                if self.move_selected < mc:
                    return f"UseMove:{player_dino['moves'][self.move_selected]}"
            elif event.key == pygame.K_SPACE:
                self.in_fight_menu = False


# === Battle UI ===
class EncounterUI:
    def __init__(self, fonts):
        self.font = fonts['DIALOGUE']
        self.small_font = fonts['BAG']
        self.smaller_font = fonts['XS']
        self.selected_option = 0
        self.actions = ["Fight", "Bag", "Party", "Run", "Defend"]
        self.in_fight_menu = False
        self.move_selected = 0
        self.level_up_popup = None
        self.enemy_hp_display = None
        self.player_hp_display = None
        self._hp_speed = 0.35  # ratio per second
        self._last_player_dino = None
        self.xp_display = None
        self._last_xp_level = None
        self._xp_speed = 0.25  # ratio per second
        self.xp_frozen = True
        self._xp_target = None

    def update(self, dt, player_dino, enemy_dino):
        target_p = player_dino['hp'] / max(1, player_dino['max_hp'])
        target_e = enemy_dino['hp'] / max(1, enemy_dino['max_hp'])
        if self.player_hp_display is None or self._last_player_dino is not player_dino:
            self.player_hp_display = target_p
            self._last_player_dino = player_dino
        if self.enemy_hp_display is None:
            self.enemy_hp_display = target_e
        self.player_hp_display = self._slide(self.player_hp_display, target_p, dt)
        self.enemy_hp_display  = self._slide(self.enemy_hp_display,  target_e, dt)

        xp_ratio = player_dino['xp'] / max(1, player_dino['xp_to_next'])
        self._xp_target = xp_ratio
        if self.xp_display is None:
            self.xp_display = xp_ratio
            self._last_xp_level = player_dino['level']
        elif self._last_xp_level != player_dino['level']:
            self.xp_display = 0.0
            self._last_xp_level = player_dino['level']
        if not self.xp_frozen:
            self.xp_display = self._slide(self.xp_display, xp_ratio, dt, self._xp_speed)

    def _slide(self, current, target, dt, speed=None):
        if speed is None:
            speed = self._hp_speed
        diff = target - current
        step = speed * dt
        if abs(diff) <= step:
            return target
        return current + step * (1 if diff > 0 else -1)

    def is_hp_animating(self, player_dino, enemy_dino):
        tp = player_dino['hp'] / max(1, player_dino['max_hp'])
        te = enemy_dino['hp'] / max(1, enemy_dino['max_hp'])
        return (self.player_hp_display is not None and abs(self.player_hp_display - tp) > 0.001) or \
               (self.enemy_hp_display  is not None and abs(self.enemy_hp_display  - te) > 0.001)

    def unfreeze_xp(self):
        self.xp_frozen = False

    def is_xp_animating(self):
        if self._xp_target is None or self.xp_display is None:
            return False
        return abs(self.xp_display - self._xp_target) > 0.005

    def show_level_up(self, dino, old_stats, new_stats):
        self.level_up_popup = LevelUpPopup(dino, old_stats, new_stats)

    def draw_panel(self, surface, rect, bg_color=(245, 245, 245), border_color=(0, 0, 0), border_width=3):
        pygame.draw.rect(surface, bg_color, rect)
        pygame.draw.rect(surface, border_color, rect, border_width)

    def draw_hp_bar(self, surface, x, y, width, height, percent, back_color=(200, 0, 0), front_color=(0, 200, 0)):
        pygame.draw.rect(surface, back_color, (x, y, width, height))
        pygame.draw.rect(surface, front_color, (x, y, int(width * max(0, min(1, percent))), height))

    def _draw_badges(self, surface, x, y, dino, field_effects=None, show_field=False):
        font = self.smaller_font
        badges = []
        abbr = {'attack': 'ATK', 'defense': 'DEF', 'speed': 'SPD'}
        for stat, label in abbr.items():
            val = dino.get('stat_stages', {}).get(stat, 0)
            if val != 0:
                sign = '+' if val > 0 else ''
                bg = (150, 215, 150) if val > 0 else (215, 150, 150)
                badges.append((f"{label}{sign}{val}", bg))
        if show_field and field_effects:
            for fx in field_effects:
                if fx['effect'] == 'speed_swap':
                    badges.append(("TIME", (210, 210, 130)))
                elif fx['effect'] == 'type_power':
                    bt = fx.get('boost_type', '')
                    badges.append((f"{bt[:3].upper()}+", (215, 185, 130)))
        bx = x
        for text, bg in badges:
            tw, th = font.size(text)
            pad = 3
            bw = tw + pad * 2
            bh = 15
            if bx + bw > x + 205:
                break
            pygame.draw.rect(surface, bg,         (bx, y, bw, bh), border_radius=3)
            pygame.draw.rect(surface, (70, 70, 70), (bx, y, bw, bh), 1, border_radius=3)
            surface.blit(font.render(text, True, (30, 30, 30)), (bx + pad, y + (bh - th) // 2))
            bx += bw + 3

    def draw(self, surface, player_dino, enemy_dino, encounter_text, show_actions=True, trainer_total=0, trainer_defeated=0, pod_icon=None, msg_awaiting_input=False, player_visible=True, field_effects=None):
        if not show_actions:
            self.in_fight_menu = False  # can't be in fight menu while a message is showing
        screen_w, screen_h = surface.get_size()

        text_box_rect   = pygame.Rect(9, screen_h - 120, screen_w - 325, 115)
        actions_rect    = pygame.Rect(screen_w - 300, screen_h - 120, 287, 115)
        enemy_info_rect = pygame.Rect(-1, 30, 220, 82)
        player_info_rect= pygame.Rect(screen_w - 220, screen_h - 242, 220, 100)

        self.draw_panel(surface, text_box_rect)
        self.draw_panel(surface, actions_rect)
        self.draw_panel(surface, enemy_info_rect)
        self.draw_panel(surface, player_info_rect)

        # Trainer dino indicator: 6 slots top-left, filled with pod icon, darkened when defeated
        if trainer_total > 0 and pod_icon is not None:
            icon_size, icon_gap = 22, 4
            for i in range(6):
                slot = pygame.Rect(5 + i * (icon_size + icon_gap), 5, icon_size, icon_size)
                if i < trainer_total:
                    scaled = pygame.transform.scale(pod_icon, (icon_size, icon_size))
                    if i < trainer_defeated:
                        dark = scaled.copy()
                        overlay = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
                        overlay.fill((0, 0, 0, 160))
                        dark.blit(overlay, (0, 0))
                        surface.blit(dark, slot)
                    else:
                        surface.blit(scaled, slot)
                else:
                    pygame.draw.rect(surface, (80, 80, 80), slot, 1)

        ep = self.enemy_hp_display  if self.enemy_hp_display  is not None else enemy_dino['hp']  / max(1, enemy_dino['max_hp'])
        pp = self.player_hp_display if self.player_hp_display is not None else player_dino['hp'] / max(1, player_dino['max_hp'])

        # Enemy info
        surface.blit(self.small_font.render(enemy_dino['name'], True, (0, 0, 0)),
                     (enemy_info_rect.x + 10, enemy_info_rect.y + 12))
        surface.blit(self.small_font.render(f"Lv{enemy_dino['level']}", True, (0, 0, 0)),
                     (enemy_info_rect.x + 160, enemy_info_rect.y + 12))
        self.draw_hp_bar(surface, enemy_info_rect.x + 10, enemy_info_rect.y + 40, 200, 15, ep)
        self._draw_badges(surface, enemy_info_rect.x + 10, enemy_info_rect.y + 60,
                          enemy_dino, field_effects, show_field=True)

        # Player info
        # row 0 — name + level  (y+8)
        surface.blit(self.small_font.render(player_dino['name'], True, (0, 0, 0)),
                     (player_info_rect.x + 8, player_info_rect.y + 8))
        surface.blit(self.small_font.render(f"Lv{player_dino['level']}", True, (0, 0, 0)),
                     (player_info_rect.x + 158, player_info_rect.y + 8))
        # row 1 — HP bar (y+29, h=10)
        self.draw_hp_bar(surface, player_info_rect.x + 8, player_info_rect.y + 29, 202, 10, pp)
        # row 2 — HP numbers in XS font (y+41)
        surface.blit(
            self.smaller_font.render(f"HP  {player_dino['hp']}/{player_dino['max_hp']}", True, (0, 0, 0)),
            (player_info_rect.x + 8, player_info_rect.y + 41)
        )
        # row 3 — stat badges (y+57)
        self._draw_badges(surface, player_info_rect.x + 8, player_info_rect.y + 57, player_dino)

        # XP bar (y+88) + XP label in XS font (y+75)
        xp_progress = self.xp_display if self.xp_display is not None else player_dino['xp'] / max(1, player_dino['xp_to_next'])
        xp_bar_rect = pygame.Rect(player_info_rect.x + 8, player_info_rect.y + 88, 202, 8)
        pygame.draw.rect(surface, (255, 255, 255), xp_bar_rect)
        pygame.draw.rect(surface, (0, 0, 255),
                         (xp_bar_rect.x, xp_bar_rect.y, int(xp_bar_rect.width * xp_progress), xp_bar_rect.height))
        pygame.draw.rect(surface, (0, 0, 0), xp_bar_rect, 2)
        displayed_xp = int(xp_progress * player_dino['xp_to_next'])
        surface.blit(
            self.smaller_font.render(f"XP  {displayed_xp}/{int(player_dino['xp_to_next'])}", True, (0, 0, 0)),
            (xp_bar_rect.x, xp_bar_rect.y - 14)
        )

        # Player dino sprite — sits directly on top of the left text box
        if player_visible:
            scaled = pygame.transform.scale(player_dino['image'], (230, 230))
            sprite_rect = scaled.get_rect()
            sprite_rect.centerx = text_box_rect.centerx
            sprite_rect.bottom = text_box_rect.top
            surface.blit(scaled, sprite_rect)

        # Level-up popup overlay
        if self.level_up_popup and self.level_up_popup.active:
            dim = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))
            surface.blit(dim, (0, 0))
            self.level_up_popup.draw(surface)

        # Text box
        lines = wrap_text(encounter_text, self.small_font, text_box_rect.width - 40)
        for i, line in enumerate(lines[:5]):
            surface.blit(self.small_font.render(line, True, (0, 0, 0)),
                         (text_box_rect.x + 20, text_box_rect.y + 12 + i * 20))

        if msg_awaiting_input and pygame.time.get_ticks() // 400 % 2:
            cx = text_box_rect.right - 18
            cy = text_box_rect.bottom - 10
            pygame.draw.polygon(surface, (0, 0, 0), [
                (cx - 8, cy - 7), (cx + 8, cy - 7), (cx, cy + 3)
            ])

        # Action / Fight menu — hidden while a message is displaying
        if not show_actions:
            return
        if not self.in_fight_menu:
            # 2x2 grid: Fight/Bag/Party/Run (options 0-3)
            for i in range(4):
                action = self.actions[i]
                color = (0, 0, 255) if i == self.selected_option else (0, 0, 0)
                surface.blit(self.font.render(action, True, color),
                             (actions_rect.x + 20 + (i % 2) * 120, actions_rect.y + 20 + (i // 2) * 50))
            # DEFEND button — vertical dark blue rect on the right
            defend_rect = pygame.Rect(actions_rect.right - 80, actions_rect.y + 5, 74, 105)
            defend_selected = (self.selected_option == 4)
            pygame.draw.rect(surface, (15, 25, 110), defend_rect, border_radius=5)
            border_col = (255, 215, 0) if defend_selected else (0, 0, 60)
            pygame.draw.rect(surface, border_col, defend_rect, 3, border_radius=5)
            d_surf = self.small_font.render("DEFEND", True, (255, 255, 255))
            surface.blit(d_surf, (defend_rect.centerx - d_surf.get_width() // 2,
                                  defend_rect.centery - d_surf.get_height() // 2))
        else:
            moves = player_dino['moves']
            qw = actions_rect.width // 2
            qh = actions_rect.height // 2
            for i in range(4):
                col, row = i % 2, i // 2
                rect = pygame.Rect(actions_rect.x + col * qw, actions_rect.y + row * qh, qw, qh)
                if i < len(moves):
                    move_name = moves[i]
                    move_type = MOVE_DATA.get(move_name, {}).get("type", "normal")
                    bg_color = TYPE_DATA.get(move_type, {}).get("color", (200, 200, 200))
                else:
                    move_name = "—"
                    bg_color = (150, 150, 150)
                pygame.draw.rect(surface, bg_color, rect)
                border_color = (255, 255, 0) if i == self.move_selected else (0, 0, 0)
                pygame.draw.rect(surface, border_color, rect, 3)
                text_color = (255, 255, 255) if i < len(moves) else (100, 100, 100)
                text = self.small_font.render(move_name, True, text_color)
                surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

    def handle_input(self, event, player_dino):
        if self.level_up_popup and self.level_up_popup.active:
            self.level_up_popup.handle_event(event)
            return
        if event.type != pygame.KEYDOWN:
            return
        if not self.in_fight_menu:
            # Grid:  [0:Fight][1:Bag] | [4:Defend]
            #        [2:Party][3:Run] | [4:Defend]
            # Index:  0  1  2  3  4
            NAV_W = [2, 3, 0, 1, 1]  # up   — col wraps; Defend → Bag
            NAV_S = [2, 3, 0, 1, 3]  # down — col wraps; Defend → Run
            NAV_A = [4, 0, 4, 2, 3]  # left — row wraps to Defend; Defend → Run
            NAV_D = [1, 4, 3, 4, 0]  # right — Defend wraps to Fight
            if event.key == pygame.K_w:
                self.selected_option = NAV_W[self.selected_option]
            elif event.key == pygame.K_s:
                self.selected_option = NAV_S[self.selected_option]
            elif event.key == pygame.K_a:
                self.selected_option = NAV_A[self.selected_option]
            elif event.key == pygame.K_d:
                self.selected_option = NAV_D[self.selected_option]
            elif event.key == pygame.K_j:
                if self.actions[self.selected_option] == "Fight":
                    self.in_fight_menu = True
                else:
                    return self.actions[self.selected_option]
        else:
            move_count = len(player_dino['moves'])
            if event.key == pygame.K_w:
                self.move_selected = (self.move_selected - 2) % 4
                while self.move_selected >= move_count:
                    self.move_selected = (self.move_selected - 1) % 4
            elif event.key == pygame.K_s:
                self.move_selected = (self.move_selected + 2) % 4
                while self.move_selected >= move_count:
                    self.move_selected = (self.move_selected - 1) % 4
            elif event.key == pygame.K_a:
                self.move_selected = (self.move_selected - 1) % 4
                while self.move_selected >= move_count:
                    self.move_selected = (self.move_selected - 1) % 4
            elif event.key == pygame.K_d:
                self.move_selected = (self.move_selected + 1) % 4
                while self.move_selected >= move_count:
                    self.move_selected = (self.move_selected - 1) % 4
            elif event.key == pygame.K_j:
                if self.move_selected < move_count:
                    return f"UseMove:{player_dino['moves'][self.move_selected]}"
            elif event.key == pygame.K_SPACE:
                self.in_fight_menu = False


# === Level-Up Popup (scaffolding for future battle level-up display) ===
class LevelUpPopup:
    def __init__(self, dino, old_stats, new_stats):
        self.dino = dino
        self.old_stats = old_stats
        self.new_stats = new_stats
        self.active = True

    def draw(self, screen):
        popup_rect = pygame.Rect(100, 100, 300, 200)
        pygame.draw.rect(screen, (255, 255, 255), popup_rect)
        pygame.draw.rect(screen, (0, 0, 0), popup_rect, 2)
        font = pygame.font.Font(None, 28)
        lines = [
            f"{self.dino['name']} leveled up!",
            f"HP:  {self.old_stats['hp']} → {self.new_stats['hp']}",
            f"ATK: {self.old_stats['attack']} → {self.new_stats['attack']}",
            f"DEF: {self.old_stats['defense']} → {self.new_stats['defense']}",
            f"SPD: {self.old_stats['speed']} → {self.new_stats['speed']}",
        ]
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, (0, 0, 0)), (popup_rect.x + 10, popup_rect.y + 10 + i * 30))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.active = False


# === Dino Ball Pickup Popup ===
class DinoPickupPopup:
    W, H = 260, 210

    def __init__(self, dino, fonts, party_full, screen_w=640, screen_h=480):
        self.dino = dino
        self.fonts = fonts
        self.active = True
        self._overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 160))
        self.rect = pygame.Rect((screen_w - self.W) // 2, (screen_h - self.H) // 2, self.W, self.H)
        raw = dino.get('front_image', dino['image'])
        self._dino_img = pygame.transform.scale(raw, (90, 90))
        self._party_full = party_full

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.active = False

    def draw(self, screen):
        screen.blit(self._overlay, (0, 0))
        pygame.draw.rect(screen, (245, 242, 220), self.rect, border_radius=8)
        pygame.draw.rect(screen, (70, 50, 90), self.rect, 3, border_radius=8)

        cx = self.rect.centerx
        y = self.rect.y + 12

        img_rect = self._dino_img.get_rect(centerx=cx, top=y)
        screen.blit(self._dino_img, img_rect)
        y += 98

        name_surf = self.fonts['BAG'].render(
            f"{self.dino['name']}  Lv.{self.dino['level']}", True, (30, 20, 50))
        screen.blit(name_surf, name_surf.get_rect(centerx=cx, top=y))
        y += 22

        msg = "Party full! Sent to box." if self._party_full else "Added to your team!"
        msg_surf = self.fonts['BAG'].render(msg, True, (30, 30, 30))
        screen.blit(msg_surf, msg_surf.get_rect(centerx=cx, top=y))

        prompt = self.fonts['XS'].render("[ J ] Continue", True, (100, 90, 120))
        screen.blit(prompt, prompt.get_rect(centerx=cx, bottom=self.rect.bottom - 10))


# === Party Screen ===
class BoxScreen:
    """PC Box — dual-panel: box grid (left) and party list (right)."""
    ICON_SZ = 48
    COLS    = 5
    BOX_X   = 8
    BOX_Y   = 48
    PAR_X   = 372
    PAR_Y   = 48
    SLOT_W  = 56   # icon + padding
    SLOT_H  = 70   # icon + level text + padding

    def __init__(self, game):
        self.fonts      = game.fonts
        self.font       = game.fonts['BAG']
        self.xs_font    = game.fonts['XS']
        self.title_font = game.fonts['BATTLE']
        self.panel      = 'box'
        self.box_cursor = 0
        self.par_cursor = 0
        self.grabbed    = None   # {'from':'box'/'party', 'idx':int} or None
        self._icons     = {}
        for name, path in config.ENCOUNTER_DINOS_PATHS.items():
            if name.endswith('2'):
                continue
            try:
                img = pygame.image.load(path).convert_alpha()
                self._icons[name] = pygame.transform.scale(img, (self.ICON_SZ, self.ICON_SZ))
            except Exception:
                surf = pygame.Surface((self.ICON_SZ, self.ICON_SZ), pygame.SRCALPHA)
                surf.fill((80, 80, 160, 200))
                self._icons[name] = surf

    def reset(self):
        self.panel      = 'box'
        self.box_cursor = 0
        self.par_cursor = 0
        self.grabbed    = None

    def _box_rect(self, idx):
        col = idx % self.COLS
        row = idx // self.COLS
        return pygame.Rect(self.BOX_X + col * self.SLOT_W,
                           self.BOX_Y + row * self.SLOT_H,
                           self.ICON_SZ, self.ICON_SZ)

    def _par_rect(self, idx):
        return pygame.Rect(self.PAR_X, self.PAR_Y + idx * 62, 260, 54)

    def handle_event(self, event, game):
        if event.type != pygame.KEYDOWN:
            return None

        box   = game.box_dinos
        party = game.player_dinos

        if event.key == pygame.K_SPACE:
            if self.grabbed:
                self.grabbed = None
            else:
                return 'back'
            return None

        if self.panel == 'box':
            n = len(box)
            if event.key == pygame.K_d:
                if n == 0 or self.box_cursor >= n - 1:
                    self.panel = 'party'   # past last slot → cross to party
                else:
                    self.box_cursor += 1
            elif event.key == pygame.K_a:
                if self.box_cursor > 0:
                    self.box_cursor -= 1
                # at slot 0, do nothing (box is leftmost panel)
            elif event.key == pygame.K_s:
                self.box_cursor = min(self.box_cursor + self.COLS, max(0, n - 1))
            elif event.key == pygame.K_w:
                self.box_cursor = max(0, self.box_cursor - self.COLS)
            elif event.key == pygame.K_j:
                if self.grabbed is None:
                    if n > 0:
                        self.grabbed = {'from': 'box', 'idx': self.box_cursor}
                else:
                    src, sidx = self.grabbed['from'], self.grabbed['idx']
                    tidx = self.box_cursor
                    if src == 'box':
                        if sidx != tidx and sidx < len(box) and tidx < len(box):
                            box[sidx], box[tidx] = box[tidx], box[sidx]
                    else:  # from party → drop in box
                        if tidx < len(box):
                            party[sidx], box[tidx] = box[tidx], party[sidx]
                        elif len(party) > 1:
                            dino = party.pop(sidx)
                            box.append(dino)
                            self.par_cursor = min(self.par_cursor, max(0, len(party) - 1))
                            game.active_dino_index = min(game.active_dino_index, len(party) - 1)
                    self.grabbed = None

        else:  # party panel
            if event.key == pygame.K_s:
                self.par_cursor = min(self.par_cursor + 1, game.PARTY_LIMIT - 1)
            elif event.key == pygame.K_w:
                self.par_cursor = max(0, self.par_cursor - 1)
            elif event.key == pygame.K_a:
                self.panel = 'box'   # cross back to box
            elif event.key == pygame.K_o:
                # Quick-send highlighted party dino to next empty box slot
                if self.par_cursor < len(party) and len(party) > 1:
                    dino = party.pop(self.par_cursor)
                    box.append(dino)
                    self.par_cursor = min(self.par_cursor, max(0, len(party) - 1))
                    self.box_cursor = len(box) - 1   # land cursor on the newly sent dino
                    game.active_dino_index = min(game.active_dino_index, len(party) - 1)
            elif event.key == pygame.K_j:
                if self.grabbed is None:
                    if self.par_cursor < len(party):
                        self.grabbed = {'from': 'party', 'idx': self.par_cursor}
                else:
                    src, sidx = self.grabbed['from'], self.grabbed['idx']
                    tidx = self.par_cursor
                    if src == 'party':
                        if sidx != tidx and sidx < len(party) and tidx < len(party):
                            party[sidx], party[tidx] = party[tidx], party[sidx]
                    else:  # from box → drop in party
                        if tidx < len(party):
                            box[sidx], party[tidx] = party[tidx], box[sidx]
                        elif tidx < game.PARTY_LIMIT:
                            dino = box.pop(sidx)
                            party.append(dino)
                            self.box_cursor = min(self.box_cursor, max(0, len(box) - 1))
                    self.grabbed = None

        return None

    def draw(self, surface, game):
        surface.fill((18, 10, 38))

        box   = game.box_dinos
        party = game.player_dinos

        CONTENT_TOP = 52   # slots start here; leaves room for header band
        CONTENT_BOT = 432  # slots must end above this; leaves room for status band

        # ── Box panel slots ────────────────────────────────────────
        box_active = self.panel == 'box'
        max_rows   = 5
        hover_name = ""
        for idx in range(self.COLS * max_rows):
            col  = idx % self.COLS
            row  = idx // self.COLS
            rect = pygame.Rect(self.BOX_X + col * self.SLOT_W,
                               CONTENT_TOP + row * self.SLOT_H,
                               self.ICON_SZ, self.ICON_SZ)
            if rect.bottom > CONTENT_BOT:
                break
            is_cursor  = box_active and idx == self.box_cursor
            is_grabbed = (self.grabbed and self.grabbed['from'] == 'box'
                          and self.grabbed['idx'] == idx)

            bg = (255, 210, 0) if is_grabbed else (70, 65, 130) if is_cursor else (35, 30, 65)
            pygame.draw.rect(surface, bg, rect)
            pygame.draw.rect(surface, (90, 80, 160), rect, 1)

            if idx < len(box):
                dino = box[idx]
                icon = self._icons.get(dino['name'])
                if icon:
                    surface.blit(icon, rect.topleft)
                surface.blit(self.xs_font.render(f"Lv{dino['level']}", True, (200, 200, 255)),
                             (rect.x, rect.bottom + 2))
                if is_cursor:
                    hover_name = dino['name']

        # ── Party panel slots ──────────────────────────────────────
        par_active = self.panel == 'party'
        for i in range(game.PARTY_LIMIT):
            rect       = pygame.Rect(self.PAR_X, CONTENT_TOP + i * 62, 260, 54)
            is_cursor  = par_active and i == self.par_cursor
            is_grabbed = (self.grabbed and self.grabbed['from'] == 'party'
                          and self.grabbed['idx'] == i)

            if i >= len(party):
                bg = (50, 90, 50) if is_cursor else (25, 25, 25)
            elif is_grabbed:
                bg = (255, 210, 0)
            elif is_cursor:
                bg = (60, 140, 60)
            else:
                bg = (35, 65, 35)

            pygame.draw.rect(surface, bg, rect)
            pygame.draw.rect(surface, (80, 160, 80), rect, 1)

            if i < len(party):
                dino = party[i]
                icon = self._icons.get(dino['name'])
                if icon:
                    surface.blit(pygame.transform.scale(icon, (40, 40)),
                                 (rect.x + 4, rect.y + 7))
                surface.blit(self.font.render(dino['name'], True, (255, 255, 255)),
                             (rect.x + 50, rect.y + 4))
                surface.blit(self.xs_font.render(f"Lv {dino['level']}", True, (200, 200, 200)),
                             (rect.x + 50, rect.y + 22))
                hp_pct = dino['hp'] / max(1, dino['max_hp'])
                bar = pygame.Rect(rect.x + 50, rect.y + 40, 160, 7)
                pygame.draw.rect(surface, (50, 50, 50), bar)
                clr = (80, 200, 80) if hp_pct > 0.5 else (220, 180, 0) if hp_pct > 0.2 else (200, 60, 60)
                pygame.draw.rect(surface, clr,
                                 (bar.x, bar.y, int(bar.w * max(0, hp_pct)), bar.h))
            else:
                empty_clr = (120, 180, 120) if is_cursor else (55, 70, 55)
                surface.blit(self.xs_font.render("-- empty --", True, empty_clr),
                             (rect.x + 50, rect.y + 22))

        # ── Header band (drawn AFTER slots so text is always on top) ──
        pygame.draw.rect(surface, (12, 8, 28), pygame.Rect(0, 0, 640, CONTENT_TOP))
        pygame.draw.line(surface, (60, 50, 100), (0, CONTENT_TOP - 1), (640, CONTENT_TOP - 1))

        surface.blit(self.title_font.render("PC  BOX", True, (220, 210, 255)), (8, 6))

        box_lbl_clr  = (160, 150, 255) if box_active  else (80, 75, 140)
        par_lbl_clr  = (140, 220, 140) if par_active  else (60, 110, 60)
        surface.blit(self.xs_font.render("BOX", True, box_lbl_clr),  (self.BOX_X, 34))
        surface.blit(self.xs_font.render("PARTY", True, par_lbl_clr), (self.PAR_X, 34))

        # ── Status band (drawn AFTER slots so text is always on top) ──
        pygame.draw.rect(surface, (12, 8, 28), pygame.Rect(0, CONTENT_BOT, 640, 480 - CONTENT_BOT))
        pygame.draw.line(surface, (60, 50, 100), (0, CONTENT_BOT), (640, CONTENT_BOT))

        if self.grabbed:
            src  = self.grabbed['from']
            sidx = self.grabbed['idx']
            lst  = box if src == 'box' else party
            name = lst[sidx]['name'] if sidx < len(lst) else "?"
            surface.blit(self.font.render(f"Holding {name}  —  J=place  SPACE=cancel",
                                          True, (255, 220, 0)), (8, CONTENT_BOT + 6))
        else:
            if hover_name:
                surface.blit(self.font.render(hover_name, True, (255, 255, 200)),
                             (8, CONTENT_BOT + 6))
            hint = "J=grab/place   O=quick send to box   SPACE=back"
            surface.blit(self.xs_font.render(hint, True, (100, 90, 160)), (8, CONTENT_BOT + 24))


class PartyScreen:
    def __init__(self, game):
        self.game         = game
        self.width        = 640
        self.height       = 480
        self.bg_color     = (30, 30, 30)
        self.font         = game.fonts['BATTLE2']
        self.small_font   = pygame.font.SysFont('Arial', 22)
        self.smaller_font = pygame.font.SysFont('Arial', 20)
        self.selected_index  = 0
        self.picking_index   = None   # index of dino being repositioned
        self.preview_frame        = 0
        self.preview_last_switch  = 0
        self.preview_selected_id  = None
        self.preview_interval_ms  = 250

    def reset(self):
        self.selected_index = 0
        self.picking_index  = None

    def handle_event(self, event, game):
        if event.type != pygame.KEYDOWN:
            return None

        in_encounter = 'encounter' in game.state_stack
        awaiting     = getattr(game, "awaiting_switch", False)

        party       = game.player_dinos
        list_length = len(party)

        # Navigation (always allowed)
        if event.key == pygame.K_w and list_length > 0:
            self.selected_index = (self.selected_index - 1) % list_length
            return None
        if event.key == pygame.K_s and list_length > 0:
            self.selected_index = (self.selected_index + 1) % list_length
            return None

        # ── Double battle forced replacement ──────────────────────
        double_slot = getattr(game, 'double_replace_slot', None)
        if double_slot is not None and in_encounter and event.key == pygame.K_j:
            chosen = party[self.selected_index] if 0 <= self.selected_index < list_length else None
            if not chosen:
                return None
            if chosen.get('hp', 0) <= 0:
                game.message_box.queue_messages(
                    [f"{chosen['name']} has no HP! Choose another."], wait_for_input=True)
                return None
            other_slot = 1 - double_slot
            if self.selected_index == other_slot:
                game.message_box.queue_messages(
                    ["That dino is already in battle!"], wait_for_input=True)
                return None
            if self.selected_index == double_slot:
                game.message_box.queue_messages(
                    ["Choose a different dino."], wait_for_input=True)
                return None
            # Swap chosen dino into the fainted slot
            chosen['stat_stages'] = {"attack": 0, "defense": 0, "speed": 0}
            chosen['defending']   = False
            game.player_dinos[double_slot], game.player_dinos[self.selected_index] = \
                game.player_dinos[self.selected_index], game.player_dinos[double_slot]
            game.double_replace_slot = None
            game.pop_state()
            game._double_continue_replacements()
            return None

        # ── Forced switch after faint ──────────────────────────────
        if awaiting and in_encounter and event.key == pygame.K_j:
            chosen = party[self.selected_index] if 0 <= self.selected_index < list_length else None
            if chosen and chosen.get('hp', 0) <= 0:
                game.message_box.queue_messages(
                    [f"{chosen['name']} has no HP! Choose another."], wait_for_input=True)
                return None
            if chosen:
                out = game.player_dinos[game.active_dino_index]
                out['stat_stages'] = {"attack": 0, "defense": 0, "speed": 0}
                out['defending']   = False
                game.active_dino_index = self.selected_index
                game.awaiting_switch   = False
                game.pop_state()
                game.message_box.queue_messages(
                    [f"{config.PLAYER_NAME} sent out {chosen['name']}!", "What will you do?"], wait_for_input=True)
            return None

        # ── Voluntary switch during encounter ─────────────────────
        if in_encounter and not awaiting and event.key == pygame.K_j:
            active = game.player_dinos[game.active_dino_index]
            if active.get('lock_turns_left', 0) > 0:
                game.message_box.queue_messages(
                    [f"{active['name']} can't switch out!"], wait_for_input=True)
                return None
            chosen = party[self.selected_index] if 0 <= self.selected_index < list_length else None
            if chosen and chosen.get('hp', 0) <= 0:
                game.message_box.queue_messages(
                    [f"{chosen['name']} has no HP! Choose another."], wait_for_input=True)
                return None
            if chosen:
                out = game.player_dinos[game.active_dino_index]
                out['stat_stages'] = {"attack": 0, "defense": 0, "speed": 0}
                out['defending']   = False
                game.active_dino_index = self.selected_index
                game.pop_state()
                game.message_box.queue_messages(
                    [f"{chosen['name']}, I choose you!"], on_complete=game._enemy_turn)
            return None

        # ── Outside encounter ──────────────────────────────────────
        if not in_encounter and not awaiting:
            if event.key == pygame.K_j:
                if self.picking_index is None:
                    self.picking_index = self.selected_index
                else:
                    # Swap the two positions
                    a, b = self.picking_index, self.selected_index
                    if a != b and a < list_length and b < list_length:
                        party[a], party[b] = party[b], party[a]
                    self.picking_index = None
                return None

            if event.key == pygame.K_o:
                self.picking_index = None
                if list_length <= 1:
                    game.message_box.queue_messages(
                        ["You must keep at least one Dino!"], wait_for_input=True)
                else:
                    idx  = self.selected_index
                    dino = party[idx]
                    screen_ref = self
                    def _do_send(i=idx, s=screen_ref):
                        if len(game.player_dinos) > 1:
                            d = game.player_dinos.pop(i)
                            game.box_dinos.append(d)
                            s.selected_index = min(i, len(game.player_dinos) - 1)
                            game.active_dino_index = min(game.active_dino_index, len(game.player_dinos) - 1)
                    game.yes_no_prompt   = YesNoPrompt(
                        f"Send {dino['name']} to the box?",
                        game.fonts, config.WIDTH, config.HEIGHT)
                    game.yes_no_callback = _do_send
                return None

        # ── Back ───────────────────────────────────────────────────
        if event.key == pygame.K_SPACE:
            self.reset()
            if len(game.state_stack) >= 2 and game.state_stack[-2] == 'menu' \
                    and game.state_stack[0] == 'world':
                game.pop_state()
                game.pop_state()
                game.push_state('menu')
            else:
                return 'back'

        return None

    def draw(self, screen):
        screen.fill(self.bg_color)
        dinos = self.game.player_dinos

        if not dinos:
            screen.blit(self.font.render("No dinos in party", True, (255, 255, 255)), (20, 20))
            return

        if self.game.awaiting_switch:
            screen.blit(self.small_font.render("Choose replacement  (J=confirm)",
                                               True, (255, 200, 0)), (230, 2))

        box_w, box_h = 200, 70
        for i, dino in enumerate(dinos):
            rect = pygame.Rect(20, 20 + i * (box_h + 10), box_w, box_h)
            if dino.get('hp', 0) <= 0:
                color = (30, 30, 30)
            elif i == self.picking_index:
                color = (100, 200, 255)
            elif i == self.selected_index:
                color = (0, 150, 255)
            else:
                color = (70, 70, 70)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 2)
            screen.blit(self.font.render(dino['name'], True, (255, 255, 255)), (rect.x + 10, rect.y + 5))
            screen.blit(self.font.render(f"Lv{dino['level']}", True, (255, 255, 255)), (rect.x + 10, rect.y + 25))
            icon_scaled = pygame.transform.scale(dino.get('front_image', dino['image']), (50, 50))
            screen.blit(icon_scaled, (rect.x + 140, rect.y + 5))
            max_hp = max(1, dino.get('max_hp', 1))
            pct    = dino.get('hp', 0) / max_hp
            bar_x, bar_y, bar_w, bar_h = rect.x + 10, rect.y + 48, 120, 8
            pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
            bar_color = (80, 200, 80) if pct > 0.5 else (220, 180, 0) if pct > 0.2 else (200, 60, 60)
            pygame.draw.rect(screen, bar_color, (bar_x, bar_y, int(bar_w * pct), bar_h))
            pygame.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_w, bar_h), 1)
            if dino.get('hp', 0) <= 0:
                faint_text = self.small_font.render("Fainted", True, (255, 255, 255))
                screen.blit(faint_text, faint_text.get_rect(center=rect.center))

        self.selected_index = min(self.selected_index, len(dinos) - 1)
        self.draw_preview(screen, dinos[self.selected_index])

        in_encounter = 'encounter' in self.game.state_stack
        if not in_encounter and not self.game.awaiting_switch:
            screen.blit(self.small_font.render("J=reorder  O=send to Box  SPACE=back",
                                               True, (180, 180, 180)),
                        (230, self.height - 24))

    def draw_preview(self, screen, dino):
        preview_rect = pygame.Rect(240, 20, 380, 200)
        pygame.draw.rect(screen, (0, 0, 0), preview_rect, 3)

        types = dino['type'] if isinstance(dino['type'], list) else [dino['type']]
        colors = [TYPE_DATA.get(t, {}).get("color", (100, 200, 230)) for t in types]
        if len(colors) == 1:
            pygame.draw.rect(screen, colors[0], preview_rect)
        else:
            half = preview_rect.height // 2
            pygame.draw.rect(screen, colors[0], pygame.Rect(preview_rect.x, preview_rect.y, preview_rect.width, half))
            pygame.draw.rect(screen, colors[1], pygame.Rect(preview_rect.x, preview_rect.y + half, preview_rect.width, half))

        screen.blit(self.font.render(dino['name'], True, (255, 255, 255)), (preview_rect.left + 10, preview_rect.top + 10))
        hp_text = self.small_font.render(f"HP: {dino['hp']}/{dino['max_hp']}", True, (255, 255, 255))
        screen.blit(hp_text, (preview_rect.right - hp_text.get_width() - 10, preview_rect.top + 10))
        type_str = "/".join(types)
        type_text = self.small_font.render(type_str, True, (255, 255, 255))
        screen.blit(type_text, (preview_rect.right - type_text.get_width() - 10, preview_rect.bottom - type_text.get_height() - 10))

        # XP bar
        current_xp = dino.get("xp", 0)
        xp_to_next = max(1, dino.get("xp_to_next", 1))
        xp_bar_w = preview_rect.width - 250
        xp_bar_x = preview_rect.x + 5
        xp_bar_y = preview_rect.bottom - 18
        xp_text = self.smaller_font.render(f"XP: {int(current_xp)}/{int(xp_to_next)}", True, (255, 255, 255))
        screen.blit(xp_text, (xp_bar_x + 2, xp_bar_y - 23))
        pygame.draw.rect(screen, (255, 255, 255), (xp_bar_x, xp_bar_y, xp_bar_w, 15))
        pygame.draw.rect(screen, (0, 100, 255), (xp_bar_x, xp_bar_y, int(xp_bar_w * min(current_xp / xp_to_next, 1)), 15))
        pygame.draw.rect(screen, (0, 0, 0), (xp_bar_x, xp_bar_y, xp_bar_w, 15), 2)

        # Animated dino preview
        now = pygame.time.get_ticks()
        if self.preview_selected_id != dino.get("name"):
            self.preview_selected_id = dino.get("name")
            self.preview_frame = 0
            self.preview_last_switch = now

        frames = dino.get("frames")
        if frames and len(frames) > 1:
            if now - self.preview_last_switch >= self.preview_interval_ms:
                self.preview_frame = (self.preview_frame + 1) % len(frames)
                self.preview_last_switch = now
            frame_img = frames[self.preview_frame]
        else:
            frame_img = dino.get("image")

        screen.blit(pygame.transform.scale(frame_img, (150, 150)),
                    (preview_rect.centerx - 50, preview_rect.centery - 70))

        # Stats box
        stats_rect = pygame.Rect(240, 230, 380, 240)
        pygame.draw.rect(screen, (50, 50, 50), stats_rect)
        pygame.draw.rect(screen, (0, 0, 0), stats_rect, 3)
        for i, line in enumerate([f"HP: {dino['max_hp']}", f"Attack: {dino['attack']}",
                                   f"Defense: {dino['defense']}", f"Speed: {dino['speed']}"]):
            screen.blit(self.small_font.render(line, True, (255, 255, 255)),
                        (stats_rect.x + 10, stats_rect.y + 10 + i * 25))

        # Moves
        move_w = stats_rect.width - 200
        move_h = 25
        move_x = stats_rect.x + 10
        move_y = stats_rect.y + 120
        for i, move in enumerate(dino['moveset']):
            move_color = TYPE_DATA.get(move['type'], {}).get("color", (200, 200, 200))
            move_rect = pygame.Rect(move_x, move_y + i * (move_h + 5), move_w, move_h)
            pygame.draw.rect(screen, move_color, move_rect)
            pygame.draw.rect(screen, (0, 0, 0), move_rect, 2)
            screen.blit(self.smaller_font.render(move['name'], True, (255, 255, 255)), (move_rect.x + 8, move_rect.y))
            screen.blit(self.smaller_font.render(f"{move['damage']}/{move['accuracy']}", True, (255, 255, 255)),
                        (move_rect.x + 125, move_rect.y))


# === Items Screen ===
class ItemsScreen:
    def __init__(self, inventory, icons, descriptions, fonts):
        self.inventory = inventory
        self.icons = icons
        self.descriptions = descriptions
        self.font = fonts['BAG']
        self.desc_font = fonts['XS']
        self.selected_index = 0
        self.visible_rows = 10
        self.scroll_offset = 0

    def get_filtered_inventory(self):
        return [(item, count) for item, count in self.inventory.items() if count > 0]

    def reset(self):
        self.selected_index = 0
        self.scroll_offset = 0

    def draw(self, surface):
        right_rect = pygame.Rect(400, 50, 220, 320)
        pygame.draw.rect(surface, (255, 255, 240), right_rect)
        pygame.draw.rect(surface, (0, 0, 0), right_rect, 3)

        filtered = self.get_filtered_inventory()
        self.filtered_inventory = filtered

        if not filtered:
            surface.blit(self.font.render("No items collected.", True, (0, 0, 0)),
                         (right_rect.x + 20, right_rect.y + 40))
            return

        for i, (item, count) in enumerate(filtered[self.scroll_offset:self.scroll_offset + self.visible_rows]):
            y = right_rect.y + 20 + i * 35
            if self.scroll_offset + i == self.selected_index:
                pygame.draw.rect(surface, (200, 200, 255),
                                 (right_rect.x + 5, y - 5, right_rect.width - 10, 30), border_radius=5)
            surface.blit(self.icons[item], (right_rect.x + 10, y - 10))
            surface.blit(self.font.render(f"{item} x{count}", True, (0, 0, 0)), (right_rect.x + 50, y))

        desc_rect = pygame.Rect(400, 380, 220, 70)
        pygame.draw.rect(surface, (240, 240, 240), desc_rect)
        pygame.draw.rect(surface, (0, 0, 0), desc_rect, 3)
        selected_item = filtered[self.selected_index][0]
        description = self.descriptions.get(selected_item, "No description available.")
        for i, line in enumerate(wrap_text(description, self.desc_font, desc_rect.width - 20)):
            surface.blit(self.desc_font.render(line, True, (0, 0, 0)),
                         (desc_rect.x + 10, desc_rect.y + 10 + i * 20))

    def handle_event(self, event, game):
        filtered = self.get_filtered_inventory()
        self.filtered_inventory = filtered

        if not filtered:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return 'back'
            return None

        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_j:
            item_name, _ = filtered[self.selected_index]
            item_data = config.ITEMS.get(item_name, {})
            if item_data.get('catch_rate') is not None and 'encounter' in game.state_stack:
                if game.is_trainer_battle:
                    game.message_box.queue_messages(
                        ["You can't catch a trainer's dino!"], wait_for_input=True)
                    return 'used'
                game.attempt_catch(item_name)
                return 'used'
            elif item_name == 'Repel':
                if 'encounter' in game.state_stack:
                    game.message_box.queue_messages(
                        ["Repels can't be used in battle!"], wait_for_input=True)
                    return 'used'
                elif getattr(game, 'repel_steps', 0) > 0:
                    game.message_box.queue_messages(
                        ["A Repel is already in effect!"], wait_for_input=True)
                else:
                    game.inventory['Repel'] = max(0, game.inventory.get('Repel', 0) - 1)
                    game.repel_steps = 250
                    game.message_box.queue_messages(
                        ["You used a Repel!",
                         "Wild dinos will be held off for 250 steps."],
                        wait_for_input=True)
                return 'used'
        elif event.key == pygame.K_w:
            if self.selected_index > 0:
                self.selected_index -= 1
            if self.selected_index < self.scroll_offset:
                self.scroll_offset -= 1
        elif event.key == pygame.K_s:
            if self.selected_index < len(filtered) - 1:
                self.selected_index += 1
            if self.selected_index >= self.scroll_offset + self.visible_rows:
                self.scroll_offset += 1
        elif event.key == pygame.K_SPACE:
            if len(game.state_stack) >= 2 and game.state_stack[-2] == 'menu' and game.state_stack[0] == 'world':
                game.pop_state()
                game.pop_state()
                game.push_state('menu')
            else:
                return 'back'
        elif event.key == pygame.K_i:
            if 'encounter' not in game.state_stack:
                return 'quit'

        return None


# === Shop Screen ===
class ShopScreen:
    def __init__(self, fonts):
        self.fonts = fonts
        self.font = fonts['BAG']
        self.title_font = fonts['BATTLE']
        self.xs_font = fonts['XS']
        self.selected_index = 0
        self.icons = {}  # populated by Game after image loading
        self.qty_mode = False
        self.qty = 1

    def draw(self, surface, coins):
        surface.fill((20, 15, 35))
        W, H = surface.get_width(), surface.get_height()

        title = self.title_font.render("DinoMart", True, (255, 220, 50))
        surface.blit(title, (W // 2 - title.get_width() // 2, 18))

        coin_surf = self.font.render(f"Coins: {coins}", True, (255, 220, 50))
        surface.blit(coin_surf, (W - coin_surf.get_width() - 20, 22))

        items = config.SHOP_ITEMS
        item_h, gap, start_y = 58, 8, 80
        for i, item in enumerate(items):
            y = start_y + i * (item_h + gap)
            rect = pygame.Rect(50, y, W - 100, item_h)
            sel = (i == self.selected_index)
            pygame.draw.rect(surface, (80, 60, 120) if sel else (40, 35, 55), rect, border_radius=7)
            pygame.draw.rect(surface, (160, 140, 190) if sel else (90, 80, 110), rect, 2, border_radius=7)

            icon = self.icons.get(item['name'])
            if icon:
                surface.blit(pygame.transform.scale(icon, (36, 36)), (rect.x + 10, rect.y + 11))

            name_surf = self.font.render(item['name'], True, (255, 255, 255))
            surface.blit(name_surf, (rect.x + 55, rect.y + 10))

            desc = config.ITEMS.get(item['name'], {}).get('description', '')
            if desc:
                desc_surf = self.xs_font.render(desc[:60], True, (200, 190, 220))
                surface.blit(desc_surf, (rect.x + 55, rect.y + 34))

            affordable = coins >= item['price']
            price_surf = self.font.render(f"{item['price']} coins", True,
                                          (255, 220, 50) if affordable else (160, 110, 110))
            surface.blit(price_surf, (rect.right - price_surf.get_width() - 15, rect.y + 18))

        if self.qty_mode:
            item  = items[self.selected_index]
            total = item['price'] * self.qty
            panel = pygame.Rect(W // 2 - 130, H // 2 - 60, 260, 120)
            pygame.draw.rect(surface, (30, 25, 45), panel, border_radius=10)
            pygame.draw.rect(surface, (160, 140, 200), panel, 2, border_radius=10)

            surface.blit(self.font.render(item['name'], True, (255,255,255)),
                         (panel.x + 10, panel.y + 10))

            arrow_up   = self.font.render("▲", True, (200,180,255))
            qty_surf   = self.title_font.render(str(self.qty), True, (255,220,50))
            arrow_down = self.font.render("▼", True, (200,180,255))
            surface.blit(arrow_up,   (panel.centerx - arrow_up.get_width()//2,   panel.y + 38))
            surface.blit(qty_surf,   (panel.centerx - qty_surf.get_width()//2,    panel.y + 58))
            surface.blit(arrow_down, (panel.centerx - arrow_down.get_width()//2,  panel.y + 84))

            cost_surf = self.font.render(f"{total} coins", True,
                                         (255,220,50) if coins >= total else (200,80,80))
            surface.blit(cost_surf, (panel.right - cost_surf.get_width() - 12, panel.y + 10))

            hint = self.xs_font.render("W▲  S▼   J=Confirm   SPACE=Cancel", True, (160,155,185))
            surface.blit(hint, (panel.centerx - hint.get_width()//2, panel.bottom + 6))
        else:
            tip = self.xs_font.render("W/S: Navigate    J: Select    SPACE: Close", True, (160, 155, 185))
            surface.blit(tip, (W // 2 - tip.get_width() // 2, H - 25))

    def handle_event(self, event, game):
        if event.type != pygame.KEYDOWN:
            return None
        items = config.SHOP_ITEMS

        if self.qty_mode:
            item     = items[self.selected_index]
            max_qty  = min(99, game.coins // item['price']) if item['price'] > 0 else 99

            if event.key == pygame.K_w:
                self.qty = min(self.qty + 1, max_qty)
            elif event.key == pygame.K_s:
                self.qty = max(1, self.qty - 1)
            elif event.key == pygame.K_j:
                total = item['price'] * self.qty
                if game.coins >= total:
                    qty_snap = self.qty
                    def _do_buy():
                        game.coins -= item['price'] * qty_snap
                        game.inventory[item['name']] = game.inventory.get(item['name'], 0) + qty_snap
                        game.message_box.queue_messages(
                            [f"Bought {qty_snap}x {item['name']}!"], wait_for_input=True)
                        self.qty_mode = False
                        self.qty = 1
                    game.yes_no_prompt   = YesNoPrompt(
                        f"Buy {qty_snap}x {item['name']} for {total} coins?",
                        game.fonts, config.WIDTH, config.HEIGHT)
                    game.yes_no_callback = _do_buy
                else:
                    game.message_box.queue_messages(["Not enough coins!"], wait_for_input=True)
            elif event.key == pygame.K_SPACE:
                self.qty_mode = False
                self.qty = 1
            return None

        # ── Browse mode ───────────────────────────────────────────
        if event.key == pygame.K_w:
            self.selected_index = (self.selected_index - 1) % len(items)
        elif event.key == pygame.K_s:
            self.selected_index = (self.selected_index + 1) % len(items)
        elif event.key == pygame.K_j:
            item = items[self.selected_index]
            if game.coins >= item['price']:
                max_qty = min(99, game.coins // item['price'])
                self.qty = 1
                self.qty_mode = True
            else:
                game.message_box.queue_messages(["Not enough coins!"], wait_for_input=True)
        elif event.key == pygame.K_SPACE:
            return 'back'
        return None


# === Yes/No Prompt ===
class YesNoPrompt:
    BOX_W = 90
    BOX_H = 68

    def __init__(self, question, fonts, width=640, height=480):
        self.question = question
        self.font     = fonts['DIALOGUE']
        self.opt_font = fonts['BAG']
        self.selected = 0   # 0 = Yes, 1 = No
        self.width    = width
        self.height   = height

    def handle_event(self, event):
        """Returns 'yes', 'no', or None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_SPACE:
            return 'no'
        if event.key == pygame.K_s:
            self.selected = 1
        elif event.key == pygame.K_w:
            self.selected = 0
        elif event.key == pygame.K_j:
            return 'yes' if self.selected == 0 else 'no'
        return None

    def draw(self, surface):
        pad = 15
        line_h = self.font.get_height() + 4
        avail_w = self.width - 100 - self.BOX_W - 20
        lines = wrap_text(self.question, self.font, avail_w)
        box_h = max(80, len(lines) * line_h + pad * 2)
        q_rect = pygame.Rect(50, self.height - box_h - 20, avail_w, box_h)
        pygame.draw.rect(surface, (255, 255, 255), q_rect)
        pygame.draw.rect(surface, (0, 0, 0), q_rect, 3)
        for i, line in enumerate(lines):
            surface.blit(self.font.render(line, True, (0, 0, 0)),
                         (q_rect.x + 10, q_rect.y + pad + i * line_h))

        opts   = ['Yes', 'No']
        opt_h  = self.opt_font.get_height() + 10
        yn_rect = pygame.Rect(self.width - 50 - self.BOX_W,
                              self.height - 20 - self.BOX_H,
                              self.BOX_W, self.BOX_H)
        pygame.draw.rect(surface, (255, 255, 255), yn_rect)
        pygame.draw.rect(surface, (0, 0, 0), yn_rect, 3)
        for i, opt in enumerate(opts):
            y = yn_rect.y + 10 + i * opt_h
            if i == self.selected:
                surface.blit(self.opt_font.render(u'▶', True, (0, 0, 0)),
                             (yn_rect.x + 8, y))
            surface.blit(self.opt_font.render(opt, True, (0, 0, 0)),
                         (yn_rect.x + 26, y))


# === Message Box ===
class MessageBox:
    def __init__(self, width, fonts):
        self.width = width
        self.height = 100
        self.font = fonts['DIALOGUE']
        self.message = ""
        self.visible = False
        self.timer = 0
        self.wait_for_input = False
        self.on_complete = None
        self.messages = []
        self.char_index = 0
        self.char_timer = 0.0
        self.char_delay = 0.03  # seconds per character

    def _start_message(self, message):
        self.message = message
        self.char_index = 0
        self.char_timer = 0.0

    def show(self, message, duration=2, wait_for_input=False):
        self._start_message(message)
        self.visible = True
        self.wait_for_input = wait_for_input
        self.timer = duration * 1000 if duration > 0 else 0

    def queue_messages(self, messages, wait_for_input=True, on_complete=None):
        self.messages = list(messages)
        self.visible = True
        self.wait_for_input = wait_for_input
        self.on_complete = on_complete
        self._start_message(self.messages.pop(0))
        self.timer = 0

    def handle_event(self, event):
        if not (self.visible and self.wait_for_input and
                event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_j)):
            return
        if self.char_index < len(self.message):
            self.char_index = len(self.message)
        elif self.messages:
            self._start_message(self.messages.pop(0))
        else:
            self.hide()
            if self.on_complete:
                self.on_complete()

    def hide(self):
        self.visible = False
        self.message = ""
        self.wait_for_input = False
        self.messages = []
        self.char_index = 0
        self.char_timer = 0.0

    def update(self, dt):
        if not self.visible:
            return
        if self.char_index < len(self.message):
            self.char_timer += dt
            steps = int(self.char_timer / self.char_delay)
            if steps:
                self.char_index = min(self.char_index + steps, len(self.message))
                self.char_timer -= steps * self.char_delay
        elif self.timer > 0 and not self.wait_for_input:
            self.timer -= dt
            if self.timer <= 0:
                if self.messages:
                    self._start_message(self.messages.pop(0))
                else:
                    self.hide()
                    if self.on_complete:
                        self.on_complete()

    def draw(self, surface):
        if not self.visible:
            return
        available_w = self.width - 120
        full_lines = wrap_text(self.message, self.font, available_w)
        # Reveal only up to char_index characters, preserving line structure
        chars_left = self.char_index
        display_lines = []
        for line in full_lines:
            if chars_left <= 0:
                break
            if chars_left >= len(line):
                display_lines.append(line)
                chars_left -= len(line) + 1
            else:
                display_lines.append(line[:chars_left])
                chars_left = 0
        line_h = self.font.get_height() + 4
        pad = 15
        box_h = max(80, len(full_lines) * line_h + pad * 2)
        box_rect = pygame.Rect(50, surface.get_height() - box_h - 20, self.width - 100, box_h)
        pygame.draw.rect(surface, (255, 255, 255), box_rect)
        pygame.draw.rect(surface, (0, 0, 0), box_rect, 3)
        for i, line in enumerate(display_lines):
            surface.blit(self.font.render(line, True, (0, 0, 0)),
                         (box_rect.x + 10, box_rect.y + pad + i * line_h))

        if self.wait_for_input and self.char_index >= len(self.message):
            if pygame.time.get_ticks() // 400 % 2:
                cx = box_rect.right - 18
                cy = box_rect.bottom - 10
                pygame.draw.polygon(surface, (0, 0, 0), [
                    (cx - 8, cy - 7), (cx + 8, cy - 7), (cx, cy + 3)
                ])


# === Trainer Card Screen ===
class TrainerCardScreen:
    NUM_BADGES = 8

    def __init__(self, game):
        self.game      = game
        self.font_lg   = game.fonts['DIALOGUE']
        self.font_md   = game.fonts['BATTLE']
        self.font_sm   = game.fonts['BATTLE2']
        self.font_xs   = game.fonts['XS']
        path = os.path.join('assets', 'SCREENS', 'Badge.png')
        try:
            raw = pygame.image.load(path)
            raw = raw.convert() if not raw.get_masks()[3] else raw.convert_alpha()
            self._bg = pygame.transform.scale(raw, (config.WIDTH, config.HEIGHT))
            # print(f"[TrainerCard] Badge.png loaded OK ({raw.get_width()}x{raw.get_height()})")
        except Exception:
            # print(f"[TrainerCard] Failed to load Badge.png")
            self._bg = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_j, pygame.K_i):
            self.game.pop_state()

    def _fmt_time(self):
        total = int(self.game.play_time_seconds)
        h, rem = divmod(total, 3600)
        m, s   = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _blit_text(self, screen, font, text, color, x, y):
        """Blit text with a thin dark shadow for readability on any background."""
        shadow = font.render(text, True, (0, 0, 0))
        screen.blit(shadow, (x + 1, y + 1))
        screen.blit(font.render(text, True, color), (x, y))

    def draw(self, screen):
        if self._bg:
            screen.blit(self._bg, (0, 0))
        else:
            screen.fill((30, 20, 50))

        # ── Stat values (adjust x, y to position on the card) ─────
        self._blit_text(screen, self.font_md, "Jet",                               (255,255,255), 335, 75)   # Name
        self._blit_text(screen, self.font_md, f"${self.game.coins:,}",             (255,255,255), 260, 140)  # Money
        self._blit_text(screen, self.font_md, f"{len(self.game.dinos_seen)} / {len(DINO_DATA)}", (255,255,255), 290, 205)  # Dinodex
        self._blit_text(screen, self.font_md, self._fmt_time(),                    (255,255,255), 250, 270)  # Time
        self._blit_text(screen, self.font_md, self.game.adventure_start_date.strftime("%b %d, %Y"), (255,255,255), 170, 330)  # Started

        self._blit_text(screen, self.font_xs, "SPACE / J to close",
                        (180, 170, 150), 20, config.HEIGHT - 16)


# === Main Menu ===
class Menu:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.selected_index = 0
        self.options = ["Party", "Items", "Trainer Card", "Save Game", "Options"]
        self.width = 220
        self.margin = 15
        self.line_height = 40

    def draw(self, screen):
        W = screen.get_width()
        x = W - self.width - 20

        # ── Options panel ──────────────────────────────────────────────
        header_h  = 46
        panel_h   = header_h + len(self.options) * self.line_height + 10
        panel_rect = pygame.Rect(x, 50, self.width, panel_h)
        pygame.draw.rect(screen, (255, 255, 240), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 3)
        screen.blit(self.font.render("Menu", True, (0, 0, 0)),
                    (panel_rect.x + self.margin, panel_rect.y + 8))
        for i, option in enumerate(self.options):
            y = panel_rect.y + header_h + i * self.line_height
            if i == self.selected_index:
                pygame.draw.rect(screen, (200, 200, 255),
                                 (panel_rect.x + 5, y - 4, panel_rect.width - 10, 28),
                                 border_radius=5)
            screen.blit(self.font.render(option, True, (0, 0, 0)),
                        (panel_rect.x + self.margin, y))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_w:
            self.selected_index = (self.selected_index - 1) % len(self.options)
        elif event.key == pygame.K_s:
            self.selected_index = (self.selected_index + 1) % len(self.options)
        elif event.key == pygame.K_j:
            selected = self.options[self.selected_index]
            if selected == "Party":
                self.game.push_state('party')
            elif selected == "Items":
                self.game.push_state('items')
            elif selected == "Trainer Card":
                self.game.push_state('trainer_card')
            elif selected == "Save Game":
                pass  # TODO: implement save
            elif selected == "Options":
                pass  # TODO: implement options
        elif event.key == pygame.K_SPACE:
            self.game.pop_state()

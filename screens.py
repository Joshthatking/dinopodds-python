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


def _describe_move_effect(md):
    lines = []
    if md.get('priority', 0) > 0:
        lines.append("Goes first (priority)")
    if md.get('pierces_defend'):
        lines.append("Pierces Defend")
    ab = md.get('ability')
    if ab:
        kind = ab.get('kind')
        target_word = "User" if ab.get('target') == 'self' else "Foe"
        if kind == 'stat_boost':
            stat = ab['stat'].upper()
            stages = ab['stages']
            sign = "+" if stages > 0 else ""
            lines.append(f"{target_word}: {stat} {sign}{stages} stage{'s' if abs(stages) != 1 else ''}")
        elif kind == 'recoil':
            lines.append(f"User takes {ab['percent']}% recoil")
        elif kind == 'lock':
            lines.append(f"Locks foe for {ab['turns']} turns")
        elif kind == 'dot':
            lines.append(f"{ab['damage_percent']}% dmg/turn for {ab['turns']} turns")
        elif kind == 'heal':
            lines.append(f"Restores {ab['percent']}% HP")
        elif kind == 'field':
            eff = ab.get('effect', '')
            if eff == 'type_power':
                bt = ab.get('boost_type', '').capitalize()
                lines.append(f"{bt} moves x{ab.get('multiplier', 1)} for {ab.get('duration', 0)} turns")
            elif eff == 'speed_swap':
                lines.append(f"Swaps speed for {ab.get('duration', 0)} turns")
    return lines


def _draw_move_info_panel(surface, move_name, act_rect, small_font, smaller_font):
    md = MOVE_DATA.get(move_name, {})
    move_type = md.get('type', 'normal')
    damage    = md.get('damage', 0)
    accuracy  = md.get('accuracy', 100)
    type_color = TYPE_DATA.get(move_type, {}).get('color', (150, 150, 150))

    panel_h = 130
    panel_rect = pygame.Rect(act_rect.x, act_rect.y - panel_h, act_rect.width, panel_h)

    overlay = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
    overlay.fill((20, 20, 40, 235))
    surface.blit(overlay, panel_rect.topleft)
    pygame.draw.rect(surface, (200, 200, 220), panel_rect, 2)

    x, y = panel_rect.x + 8, panel_rect.y + 8

    # Type chip
    chip_w = max(smaller_font.size(move_type.upper())[0] + 14, 55)
    chip_rect = pygame.Rect(x, y + 1, chip_w, 20)
    pygame.draw.rect(surface, type_color, chip_rect, border_radius=4)
    t = smaller_font.render(move_type.upper(), True, (255, 255, 255))
    surface.blit(t, (chip_rect.centerx - t.get_width() // 2, chip_rect.centery - t.get_height() // 2))

    # Move name
    name_s = small_font.render(move_name, True, (255, 255, 255))
    surface.blit(name_s, (x + chip_w + 8, y))

    # Power / Accuracy row
    power_str = str(damage) if damage > 0 else "—"
    surface.blit(small_font.render(f"Power: {power_str}   Acc: {accuracy}%", True, (220, 220, 180)),
                 (x, y + 28))

    # Separator
    pygame.draw.line(surface, (90, 90, 120),
                     (panel_rect.x + 4, y + 50), (panel_rect.right - 4, y + 50))

    # Effect lines
    effect_lines = _describe_move_effect(md)
    if effect_lines:
        for i, line in enumerate(effect_lines[:3]):
            surface.blit(smaller_font.render(line, True, (160, 230, 160)), (x, y + 58 + i * 18))
    else:
        surface.blit(smaller_font.render("No additional effect", True, (140, 140, 160)), (x, y + 58))

    # Dismiss hint
    hint = smaller_font.render("[I] close", True, (100, 100, 140))
    surface.blit(hint, (panel_rect.right - hint.get_width() - 6, panel_rect.bottom - hint.get_height() - 4))


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
        self.show_move_info = False
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

        def draw_player_stat(d, pct, bx, by, bw, ko):
            if ko:
                surface.blit(sf.render("KO", True, (160, 0, 0)), (bx + SLANT + 6, by + 14))
                return
            # left side is slanted at bottom only; text starts after slant offset at top (safe)
            name = self._fit_name(d['name'], sf, bw - 70)
            surface.blit(sf.render(name,              True, (0, 0, 0)), (bx + 8,      by + 6))
            surface.blit(sf.render(f"Lv{d['level']}", True, (0, 0, 0)), (bx + bw - 55, by + 6))
            self._draw_hp_bar(surface, bx + SLANT + 4, by + 28, bw - SLANT - 12, 10, pct)

        # Stat boxes always visible (matching single-battle behaviour — only the sprite blinks)
        self._draw_slanted_panel(surface, pl_x, pl1_y, pl_w, pl_h, SLANT, slant_side='left')
        draw_player_stat(p1, pp1, pl_x, pl1_y, pl_w, pp1 <= 0.01)
        if p2:
            self._draw_slanted_panel(surface, pl_x, pl2_y, pl_w, pl_h, SLANT, slant_side='left')
            draw_player_stat(p2, pp2, pl_x, pl2_y, pl_w, pp2 <= 0.01)

        # ── Player back sprites — only the sprite blinks on hit flash ─
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
            moves = [m['name'] for m in cur.get('moveset', [])]
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
                if ts.get_width() > qw - 10:
                    ts = self.smaller_font.render(txt, True, tc)
                surface.blit(ts, (rect.centerx - ts.get_width() // 2,
                                  rect.centery - ts.get_height() // 2))
            if self.show_move_info and self.move_selected < len(moves):
                _draw_move_info_panel(surface, moves[self.move_selected], act_rect,
                                      self.small_font, self.smaller_font)

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
            if self.show_move_info:
                if event.key in (pygame.K_i, pygame.K_SPACE):
                    self.show_move_info = False
                return
            mc = len(player_dino['moveset'])
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
                    return f"UseMove:{player_dino['moveset'][self.move_selected]['name']}"
            elif event.key == pygame.K_i:
                if self.move_selected < mc:
                    self.show_move_info = True
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
        self.show_move_info = False
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
            self.in_fight_menu = False
            self.show_move_info = False
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
        lv_surf = self.small_font.render(f"Lv{enemy_dino['level']}", True, (0, 0, 0))
        surface.blit(lv_surf, (enemy_info_rect.x + enemy_info_rect.width - lv_surf.get_width() - 8, enemy_info_rect.y + 12))
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
            moves = [m['name'] for m in player_dino['moveset']]
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
                if text.get_width() > qw - 10:
                    text = self.smaller_font.render(move_name, True, text_color)
                surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))
            if self.show_move_info and self.move_selected < len(moves):
                _draw_move_info_panel(surface, moves[self.move_selected], actions_rect,
                                      self.small_font, self.smaller_font)

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
            if self.show_move_info:
                if event.key in (pygame.K_i, pygame.K_SPACE):
                    self.show_move_info = False
                return
            move_count = len(player_dino['moveset'])
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
                    return f"UseMove:{player_dino['moveset'][self.move_selected]['name']}"
            elif event.key == pygame.K_i:
                if self.move_selected < move_count:
                    self.show_move_info = True
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


# === Dino Picker (starter choice) ===
class DinoPicker:
    """Shows all starter dinos at once; player picks one to keep."""

    CARD_W, CARD_H = 150, 185

    def __init__(self, dinos, fonts, screen_w=640, screen_h=480):
        self.dinos = dinos
        self.fonts = fonts
        self.selected = 0
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 190))
        self._imgs = []
        for d in dinos:
            raw = d.get('front_image', d['image'])
            self._imgs.append(pygame.transform.scale(raw, (90, 90)))

    def handle_event(self, event):
        """Returns chosen index when confirmed, else None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_a, pygame.K_LEFT):
            self.selected = (self.selected - 1) % len(self.dinos)
        elif event.key in (pygame.K_d, pygame.K_RIGHT):
            self.selected = (self.selected + 1) % len(self.dinos)
        elif event.key == pygame.K_j:
            return self.selected
        return None

    def draw(self, screen):
        screen.blit(self._overlay, (0, 0))

        title = self.fonts['BATTLE'].render("Choose your partner!", True, (255, 248, 220))
        screen.blit(title, title.get_rect(centerx=self.screen_w // 2, top=28))

        n = len(self.dinos)
        gap = 24
        total_w = self.CARD_W * n + gap * (n - 1)
        start_x = (self.screen_w - total_w) // 2
        card_y = (self.screen_h - self.CARD_H) // 2 + 10

        for i, (dino, img) in enumerate(zip(self.dinos, self._imgs)):
            cx = start_x + i * (self.CARD_W + gap)
            sel = (i == self.selected)
            card_rect = pygame.Rect(cx, card_y, self.CARD_W, self.CARD_H)
            bg = (255, 248, 220) if sel else (50, 45, 70)
            pygame.draw.rect(screen, bg, card_rect, border_radius=10)
            border = (220, 80, 60) if sel else (100, 90, 130)
            pygame.draw.rect(screen, border, card_rect, 3 if sel else 2, border_radius=10)

            img_rect = img.get_rect(centerx=cx + self.CARD_W // 2, top=card_y + 12)
            screen.blit(img, img_rect)

            name_col = (30, 20, 50) if sel else (220, 210, 240)
            name_surf = self.fonts['BAG'].render(dino['name'], True, name_col)
            screen.blit(name_surf, name_surf.get_rect(centerx=cx + self.CARD_W // 2, top=card_y + 110))

            lvl_col = (60, 50, 80) if sel else (170, 160, 200)
            lvl_surf = self.fonts['XS'].render(f"Lv. {dino['level']}", True, lvl_col)
            screen.blit(lvl_surf, lvl_surf.get_rect(centerx=cx + self.CARD_W // 2, top=card_y + 132))

            if sel:
                arrow = self.fonts['XS'].render("[ J ] Choose", True, (200, 60, 40))
                screen.blit(arrow, arrow.get_rect(centerx=cx + self.CARD_W // 2, top=card_y + 156))

        hint = self.fonts['XS'].render("A / D  to navigate", True, (160, 150, 180))
        screen.blit(hint, hint.get_rect(centerx=self.screen_w // 2, bottom=self.screen_h - 18))


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
            if chosen and self.selected_index == game.active_dino_index:
                game.message_box.queue_messages(
                    [f"{chosen['name']} is already out!"], wait_for_input=True)
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
            if chosen and self.selected_index == game.active_dino_index:
                game.message_box.queue_messages(
                    [f"{chosen['name']} is already out!"], wait_for_input=True)
                return None
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

        # ── Move info ──────────────────────────────────────────────
        if event.key == pygame.K_i:
            if 0 <= self.selected_index < list_length:
                dino = party[self.selected_index]
                game.move_info_screen = MoveInfoScreen(game, dino)
                game.push_state('move_info')
            return None

        # ── Back ───────────────────────────────────────────────────
        if event.key == pygame.K_SPACE:
            if getattr(game, "awaiting_switch", False) or getattr(game, "double_replace_slot", None) is not None:
                game.message_box.queue_messages(
                    ["You must choose a replacement!"], wait_for_input=True)
                return None
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
        nature = dino.get("nature", "")
        if nature:
            screen.blit(self.smaller_font.render(f"{nature} Nature", True, (255, 230, 100)), (preview_rect.left + 10, preview_rect.top + 32))
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
        nature_boosts = NATURE_BOOSTS.get(dino.get("nature", ""), {})
        stat_rows = [
            ("hp",      f"HP: {dino['max_hp']}"),
            ("attack",  f"Attack: {dino['attack']}"),
            ("defense", f"Defense: {dino['defense']}"),
            ("speed",   f"Speed: {dino['speed']}"),
        ]
        for i, (stat_key, line) in enumerate(stat_rows):
            pct = nature_boosts.get(stat_key)
            if pct:
                label = f"{line}  (+{int(pct * 100)}%)"
                color = (160, 255, 140)
            else:
                label = line
                color = (255, 255, 255)
            screen.blit(self.small_font.render(label, True, color),
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

        if not self.game.awaiting_switch:
            hint = self.smaller_font.render("I for moves", True, (160, 200, 255))
            screen.blit(hint, (config.WIDTH - hint.get_width() - 10, config.HEIGHT - hint.get_height() - 6))


# === Move Info Screen ===

def generate_move_desc(move_name):
    md = MOVE_DATA.get(move_name)
    if not md:
        return "Unknown move."
    parts = []
    damage = md.get('damage', 0)
    target = md.get('target', 'opponent')
    ability = md.get('ability')
    if damage > 0:
        t = "the user" if target == 'self' else "the opponent"
        parts.append(f"Deals {damage} base damage to {t}.")
    if md.get('pierces_defend', False):
        parts.append("Ignores defensive stance.")
    if ability:
        kind = ability.get('kind')
        if kind == 'stat_boost':
            stat = ability['stat'].capitalize()
            stages = ability['stages']
            ab_t = "the user" if ability.get('target') == 'self' else "the opponent"
            direction = "Raises" if stages > 0 else "Lowers"
            amt = abs(stages)
            stage_str = f"{amt} stage{'s' if amt > 1 else ''}"
            chance = ability.get('chance', 100)
            effect = f"{direction} {ab_t}'s {stat} by {stage_str}."
            if chance < 100:
                effect = f"{chance}% chance to {effect[0].lower()}{effect[1:]}"
            parts.append(effect)
        elif kind == 'heal':
            parts.append(f"Restores {ability.get('percent', 0)}% of max HP.")
        elif kind == 'recoil':
            parts.append(f"User takes {ability.get('percent', 0)}% recoil damage.")
        elif kind == 'lock':
            turns = ability.get('turns', 2)
            parts.append(f"Traps the opponent for {turns} turns.")
        elif kind == 'field':
            eff = ability.get('effect', '')
            if eff == 'type_power':
                btype = ability.get('boost_type', '').capitalize()
                mult = ability.get('multiplier', 1.5)
                dur = ability.get('duration', 4)
                parts.append(f"Boosts {btype} moves by {int((mult - 1) * 100)}% for {dur} turns.")
            elif eff == 'speed_swap':
                parts.append(f"Swaps both sides' speed for {ability.get('duration', 5)} turns.")
        elif kind == 'dot':
            parts.append(f"Deals {ability.get('damage_percent', 0)}% damage per turn for {ability.get('turns', 2)} turns.")
    if not parts:
        parts.append("No additional effects.")
    return " ".join(parts)


class MoveInfoScreen:
    ACTIVE_X      = 0
    ACTIVE_W      = 310
    KNOWN_X       = 320
    KNOWN_W       = 310
    PANEL_Y       = 40
    PANEL_H       = 270
    ROW_H         = 52
    DESC_Y        = 330
    DESC_H        = 150

    def __init__(self, game, dino):
        self.game         = game
        self.dino         = dino
        self.font         = game.fonts['BATTLE2']
        self.small_font   = pygame.font.SysFont('Arial', 19)
        self.tiny_font    = pygame.font.SysFont('Arial', 16)
        self.panel        = 'active'   # 'active' or 'known'
        self.active_cur   = 0
        self.known_cur    = 0
        self.known_scroll = 0          # first visible index in known panel
        self.pending      = None       # {'panel': str, 'index': int}

    def _known_moves(self):
        active_names = {m['name'] for m in self.dino.get('moveset', [])}
        return [n for n in self.dino.get('moves', []) if n not in active_names]

    def _current_move_name(self):
        if self.panel == 'active':
            ms = self.dino.get('moveset', [])
            if ms and 0 <= self.active_cur < len(ms):
                return ms[self.active_cur]['name']
        else:
            km = self._known_moves()
            if km and 0 <= self.known_cur < len(km):
                return km[self.known_cur]
        return None

    def _do_swap(self, active_idx, known_name):
        ms = self.dino.get('moveset', [])
        m = MOVE_DATA.get(known_name, {})
        new_entry = {
            "name":     known_name,
            "type":     m.get("type", "normal"),
            "damage":   m.get("damage", 0),
            "accuracy": m.get("accuracy", 100),
            "ability":  m.get("ability", None),
        }
        if 0 <= active_idx < len(ms):
            ms[active_idx] = new_entry

    def handle_event(self, event, game):
        if event.type != pygame.KEYDOWN:
            return None

        ms = self.dino.get('moveset', [])
        km = self._known_moves()
        active_len = len(ms)
        known_len  = len(km)

        visible_rows = (self.DESC_Y - (self.PANEL_Y + 26)) // (self.ROW_H + 4)

        if event.key in (pygame.K_w, pygame.K_UP):
            if self.panel == 'active' and active_len:
                self.active_cur = (self.active_cur - 1) % active_len
            elif self.panel == 'known' and known_len:
                self.known_cur = (self.known_cur - 1) % known_len
                if self.known_cur < self.known_scroll:
                    self.known_scroll = self.known_cur
                elif self.known_cur == known_len - 1:
                    self.known_scroll = max(0, known_len - visible_rows)

        elif event.key in (pygame.K_s, pygame.K_DOWN):
            if self.panel == 'active' and active_len:
                self.active_cur = (self.active_cur + 1) % active_len
            elif self.panel == 'known' and known_len:
                self.known_cur = (self.known_cur + 1) % known_len
                if self.known_cur >= self.known_scroll + visible_rows:
                    self.known_scroll = self.known_cur - visible_rows + 1
                elif self.known_cur == 0:
                    self.known_scroll = 0

        elif event.key in (pygame.K_a, pygame.K_LEFT):
            self.panel = 'active'

        elif event.key in (pygame.K_d, pygame.K_RIGHT):
            if known_len:
                self.panel = 'known'

        elif event.key == pygame.K_j:
            if self.pending is None:
                if self.panel == 'active' and active_len:
                    self.pending = {'panel': 'active', 'index': self.active_cur}
                elif self.panel == 'known' and known_len:
                    self.pending = {'panel': 'known', 'index': self.known_cur}
            else:
                p = self.pending
                if self.panel == 'active' and p['panel'] == 'known':
                    self._do_swap(self.active_cur, km[p['index']])
                    self.pending = None
                elif self.panel == 'known' and p['panel'] == 'active' and known_len:
                    self._do_swap(p['index'], km[self.known_cur])
                    self.pending = None
                elif self.panel == p['panel']:
                    # Re-select in same panel
                    if self.panel == 'active':
                        self.pending = {'panel': 'active', 'index': self.active_cur}
                    else:
                        self.pending = {'panel': 'known', 'index': self.known_cur}

        elif event.key in (pygame.K_SPACE, pygame.K_i, pygame.K_ESCAPE):
            self.pending = None
            return 'back'

        return None

    @staticmethod
    def _type_rgb(move_type):
        raw = TYPE_DATA.get(move_type, {}).get('color', '#505050')
        if isinstance(raw, str):
            raw = raw.lstrip('#')
            return tuple(int(raw[i:i+2], 16) for i in (0, 2, 4))
        return raw

    def _draw_move_row(self, surface, x, y, w, h, name, move_type, is_cursor, is_pending):
        type_col = self._type_rgb(move_type)
        dim = tuple(max(0, c - 60) for c in type_col)
        bg  = (220, 180, 30) if is_pending else ((0, 130, 220) if is_cursor else dim)
        pygame.draw.rect(surface, bg, (x, y, w, h), border_radius=4)
        pygame.draw.rect(surface, (180, 180, 180), (x, y, w, h), 1, border_radius=4)

        name_surf = self.small_font.render(name, True, (255, 255, 255))
        surface.blit(name_surf, (x + 8, y + h // 2 - name_surf.get_height() // 2))

        type_surf = self.tiny_font.render(move_type.upper(), True, type_col)
        surface.blit(type_surf, (x + w - type_surf.get_width() - 8, y + h // 2 - type_surf.get_height() // 2))

    def draw(self, surface):
        surface.fill((25, 25, 35))

        ms   = self.dino.get('moveset', [])
        km   = self._known_moves()
        name = self.dino.get('name', '?')
        lvl  = self.dino.get('level', 1)

        # Header
        pygame.draw.rect(surface, (40, 40, 55), (0, 0, config.WIDTH, self.PANEL_Y - 2))
        hdr = self.font.render(f"{name}  Lv.{lvl}", True, (255, 255, 255))
        surface.blit(hdr, (10, 8))
        hint = self.tiny_font.render("W/S=move  A/D=panel  J=select  SPACE=back", True, (160, 160, 160))
        surface.blit(hint, (config.WIDTH - hint.get_width() - 8, 12))

        # Panel headers
        a_col = (0, 160, 255) if self.panel == 'active' else (120, 120, 130)
        k_col = (0, 200, 120) if self.panel == 'known' else (120, 120, 130)
        surface.blit(self.small_font.render("ACTIVE MOVES", True, a_col), (self.ACTIVE_X + 8, self.PANEL_Y + 2))
        surface.blit(self.small_font.render("KNOWN MOVES", True, k_col), (self.KNOWN_X + 8, self.PANEL_Y + 2))

        # Divider
        pygame.draw.line(surface, (80, 80, 100), (315, self.PANEL_Y), (315, self.DESC_Y), 2)

        # Active moves
        for i, mv in enumerate(ms[:4]):
            rx = self.ACTIVE_X + 8
            ry = self.PANEL_Y + 26 + i * (self.ROW_H + 4)
            is_cur     = (self.panel == 'active' and i == self.active_cur)
            is_pending = (self.pending is not None and self.pending['panel'] == 'active' and self.pending['index'] == i)
            self._draw_move_row(surface, rx, ry, self.ACTIVE_W - 16, self.ROW_H,
                                mv['name'], mv.get('type', 'normal'), is_cur, is_pending)
        # Empty slots
        for i in range(len(ms), 4):
            ry = self.PANEL_Y + 26 + i * (self.ROW_H + 4)
            pygame.draw.rect(surface, (45, 45, 55),
                             (self.ACTIVE_X + 8, ry, self.ACTIVE_W - 16, self.ROW_H), border_radius=4)
            pygame.draw.rect(surface, (70, 70, 80),
                             (self.ACTIVE_X + 8, ry, self.ACTIVE_W - 16, self.ROW_H), 1, border_radius=4)
            surface.blit(self.tiny_font.render("— empty —", True, (80, 80, 90)),
                         (self.ACTIVE_X + 16, ry + self.ROW_H // 2 - 8))

        # Known moves
        if not km:
            surface.blit(self.small_font.render("All moves active!", True, (100, 180, 100)),
                         (self.KNOWN_X + 8, self.PANEL_Y + 26))
        else:
            visible_rows = (self.DESC_Y - (self.PANEL_Y + 26)) // (self.ROW_H + 4)
            scroll = max(0, min(self.known_scroll, max(0, len(km) - visible_rows)))
            slot = 0
            for i in range(scroll, len(km)):
                kname = km[i]
                rx = self.KNOWN_X + 8
                ry = self.PANEL_Y + 26 + slot * (self.ROW_H + 4)
                if ry + self.ROW_H > self.DESC_Y - 4:
                    break
                mtype      = MOVE_DATA.get(kname, {}).get('type', 'normal')
                is_cur     = (self.panel == 'known' and i == self.known_cur)
                is_pending = (self.pending is not None and self.pending['panel'] == 'known' and self.pending['index'] == i)
                self._draw_move_row(surface, rx, ry, self.KNOWN_W - 16, self.ROW_H,
                                    kname, mtype, is_cur, is_pending)
                slot += 1
            # Scroll indicators
            if scroll > 0:
                surface.blit(self.tiny_font.render("▲ more", True, (160, 160, 160)),
                             (self.KNOWN_X + 8, self.PANEL_Y + 22))
            if scroll + visible_rows < len(km):
                surface.blit(self.tiny_font.render("▼ more", True, (160, 160, 160)),
                             (self.KNOWN_X + 8, self.DESC_Y - 18))

        # Description box
        pygame.draw.rect(surface, (35, 35, 50), (0, self.DESC_Y, config.WIDTH, self.DESC_H))
        pygame.draw.line(surface, (80, 80, 100), (0, self.DESC_Y), (config.WIDTH, self.DESC_Y), 2)

        cur_name = self._current_move_name()
        if cur_name:
            md = MOVE_DATA.get(cur_name, {})
            dmg = md.get('damage', 0)
            acc = md.get('accuracy', 100)
            mtype = md.get('type', '?')
            type_col = self._type_rgb(mtype)

            # Move name bar
            pygame.draw.rect(surface, tuple(max(0, c - 40) for c in type_col),
                             (0, self.DESC_Y, config.WIDTH, 28))
            title_surf = self.small_font.render(
                f"{cur_name}   {mtype.upper()}   {dmg} dmg / {acc}% acc",
                True, (255, 255, 255))
            surface.blit(title_surf, (10, self.DESC_Y + 4))

            # Description text (word-wrapped)
            desc = generate_move_desc(cur_name)
            desc_lines = wrap_text(desc, self.small_font, config.WIDTH - 20)
            for j, line in enumerate(desc_lines):
                surface.blit(self.small_font.render(line, True, (210, 210, 220)),
                             (10, self.DESC_Y + 34 + j * 22))

            # Pending swap hint
            if self.pending is not None:
                hint_txt = "J = confirm swap  |  navigate to other panel first"
                hint_s = self.tiny_font.render(hint_txt, True, (220, 180, 30))
                surface.blit(hint_s, (10, self.DESC_Y + self.DESC_H - 22))
        else:
            surface.blit(self.small_font.render("No move selected.", True, (120, 120, 130)),
                         (10, self.DESC_Y + 10))


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
        lines = wrap_text(message, self.font, self.width - 120)
        if len(lines) > 2:
            self.messages.insert(0, ' '.join(lines[2:]))
            message = ' '.join(lines[:2])
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
        box_h = 2 * line_h + pad * 2  # fixed 2-line height
        box_rect = pygame.Rect(50, surface.get_height() - box_h - 20, self.width - 100, box_h)
        pygame.draw.rect(surface, (255, 255, 255), box_rect)
        pygame.draw.rect(surface, (0, 0, 0), box_rect, 3)
        for i, line in enumerate(display_lines[:2]):
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
        except Exception:
            self._bg = None
        try:
            badge_raw = pygame.image.load(os.path.join('assets', 'Badges', 'flying_badge.png')).convert_alpha()
            self._flying_badge = pygame.transform.scale(badge_raw, (30, 30))
        except Exception:
            self._flying_badge = None

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

        if self._flying_badge and self.game.story_flags.get('gym1_leader_defeated'):
            screen.blit(self._flying_badge, (22, 418))

        self._blit_text(screen, self.font_xs, "SPACE / J to close",
                        (180, 170, 150), 20, config.HEIGHT - 16)


# === Badge Earned Screen ===
class BadgeEarnedScreen:
    BADGE_SIZE   = 120
    FADE_IN_SEC  = 0.6

    def __init__(self, game, badge_name, badge_path, on_dismiss=None):
        self.game       = game
        self.badge_name = badge_name
        self._timer     = 0.0
        self._on_dismiss = on_dismiss
        self._font_lg   = game.fonts['DIALOGUE']
        self._font_sm   = game.fonts['BATTLE2']
        try:
            raw = pygame.image.load(badge_path).convert_alpha()
            self._img = pygame.transform.scale(raw, (self.BADGE_SIZE, self.BADGE_SIZE))
        except Exception:
            self._img = None

    def update(self, dt):
        self._timer += dt

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self._timer > self.FADE_IN_SEC:
            self.game.pop_state()
            if self._on_dismiss:
                self._on_dismiss()

    def draw(self, screen):
        alpha = min(255, int(255 * self._timer / self.FADE_IN_SEC))

        overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(180, alpha)))
        screen.blit(overlay, (0, 0))

        cx = config.WIDTH  // 2
        cy = config.HEIGHT // 2

        if self._img:
            img = self._img.copy()
            img.set_alpha(alpha)
            screen.blit(img, (cx - self.BADGE_SIZE // 2, cy - self.BADGE_SIZE // 2 - 30))

        title_surf = self._font_lg.render(f"{self.badge_name} Earned!", True, (255, 215, 0))
        title_surf.set_alpha(alpha)
        screen.blit(title_surf, (cx - title_surf.get_width() // 2, cy + self.BADGE_SIZE // 2 - 10))

        if self._timer > self.FADE_IN_SEC:
            hint = self._font_sm.render("Press any key to continue", True, (200, 200, 200))
            screen.blit(hint, (cx - hint.get_width() // 2, cy + self.BADGE_SIZE // 2 + 26))


# === Intro Cutscene ===
class IntroSequence:
    """New-game opening: black → space background → prophecy text box → dramatic fade out."""

    PROPHECY = [
        "Time is running out...",
        "The days of darkness are ahead...",
        "I know you can feel it, I know you can.",
        "You can save everyone, I believe in you",
    ]

    BOX_W, BOX_H = 300, 350
    PAD_TOP   = 16
    PAD_SIDE  = 10
    HINT_H    = 28
    LINE_GAP  = 3
    CHUNK_GAP = 10

    def __init__(self, game):
        self.game = game
        self.fonts = game.fonts
        raw = pygame.image.load('assets/SCREENS/space.png').convert()
        self.space_img = pygame.transform.scale(raw, (config.WIDTH, config.HEIGHT))
        # phases: 'fade_in' → 'show_text' → 'fade_out' → 'hold_black'
        self.phase = 'fade_in'
        self.fade_alpha = 255
        self.checkpoint = 0
        self._hold_timer = 0.0
        self.done = False

    def update(self, dt):
        if self.phase == 'fade_in':
            self.fade_alpha = max(0, self.fade_alpha - int(255 * dt * 0.8))
            if self.fade_alpha == 0:
                self.phase = 'show_text'
        elif self.phase == 'fade_out':
            self.fade_alpha = min(255, self.fade_alpha + int(255 * dt * 0.28))
            if self.fade_alpha >= 255:
                self.fade_alpha = 255
                self.phase = 'hold_black'
        elif self.phase == 'hold_black':
            self._hold_timer += dt
            if self._hold_timer >= 1.8:
                self.done = True

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key not in (pygame.K_j, pygame.K_RETURN, pygame.K_SPACE):
            return
        if self.phase == 'show_text':
            if self.checkpoint < len(self.PROPHECY) - 1:
                self.checkpoint += 1
            else:
                self.phase = 'fade_out'
                self.fade_alpha = 0

    def _build_lines(self):
        """Return list of (text|None) where None is an inter-chunk gap."""
        font = self.fonts['BATTLE']
        max_w = self.BOX_W - self.PAD_SIDE * 2
        result = []
        for i in range(self.checkpoint + 1):
            for line in wrap_text(self.PROPHECY[i], font, max_w):
                result.append(line)
            result.append(None)  # gap after each chunk
        return result

    def draw(self, screen):
        W, H = screen.get_width(), screen.get_height()
        screen.blit(self.space_img, (0, 0))

        if self.phase in ('show_text', 'fade_out'):
            bx = W // 2 - self.BOX_W // 2
            by = H // 2 - self.BOX_H // 2

            bsurf = pygame.Surface((self.BOX_W, self.BOX_H), pygame.SRCALPHA)
            bsurf.fill((0, 0, 0, 215))
            screen.blit(bsurf, (bx, by))
            pygame.draw.rect(screen, (90, 70, 135), pygame.Rect(bx, by, self.BOX_W, self.BOX_H), 2)

            font = self.fonts['BATTLE']
            line_h = font.get_height() + self.LINE_GAP
            content_h = self.BOX_H - self.PAD_TOP - self.HINT_H

            # Measure total height of all revealed lines
            lines = self._build_lines()
            total_h = sum(self.CHUNK_GAP if ln is None else line_h for ln in lines)

            # Scroll so newest text is always visible at the bottom
            scroll = max(0, total_h - content_h)

            clip_rect = pygame.Rect(bx, by + self.PAD_TOP, self.BOX_W, content_h)
            screen.set_clip(clip_rect)

            y = by + self.PAD_TOP - scroll
            for ln in lines:
                if ln is None:
                    y += self.CHUNK_GAP
                else:
                    surf = font.render(ln, True, (210, 195, 255))
                    screen.blit(surf, (bx + self.PAD_SIDE, y))
                    y += line_h

            screen.set_clip(None)

            hint_font = self.fonts['XS']
            if self.checkpoint < len(self.PROPHECY) - 1:
                hint = hint_font.render("[ J ] ...", True, (100, 90, 145))
            else:
                hint = hint_font.render("[ J ] continue", True, (100, 90, 145))
            screen.blit(hint, (bx + self.BOX_W // 2 - hint.get_width() // 2,
                               by + self.BOX_H - self.HINT_H + 6))

        if self.fade_alpha > 0:
            fade = pygame.Surface((W, H))
            fade.fill((0, 0, 0))
            fade.set_alpha(self.fade_alpha)
            screen.blit(fade, (0, 0))


# === Main Menu ===
class TitleScreen:
    def __init__(self, game):
        self.game = game
        self.options = ["New Game", "Continue", "Sandbox Mode"]
        self.selected = 0
        self.title_font = pygame.font.Font(config.FONT_PATH_B, 52)
        self.option_font = game.fonts['DIALOGUE']
        self.hint_font = game.fonts['XS']
        self.fade_alpha = 255
        self._fading_in = True

    def reset(self):
        self.selected = 0
        self.fade_alpha = 255
        self._fading_in = True

    def update(self, dt):
        if self._fading_in:
            self.fade_alpha = max(0, self.fade_alpha - int(255 * dt * 1.5))
            if self.fade_alpha == 0:
                self._fading_in = False

    def handle_event(self, event, has_save):
        if self._fading_in:
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_w, pygame.K_UP):
            self.selected = (self.selected - 1) % len(self.options)
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            self.selected = (self.selected + 1) % len(self.options)
        elif event.key in (pygame.K_j, pygame.K_RETURN):
            self._confirm(has_save)

    def _confirm(self, has_save):
        opt = self.options[self.selected]
        if opt == "New Game":
            self.game.new_game()
        elif opt == "Continue":
            if has_save:
                self.game.load_game()
        elif opt == "Sandbox Mode":
            self.game.sandbox_mode()

    def draw(self, screen, has_save):
        W, H = screen.get_width(), screen.get_height()
        screen.fill((15, 10, 30))

        pygame.draw.rect(screen, (35, 25, 65), (0, 0, W, 65))
        pygame.draw.rect(screen, (35, 25, 65), (0, H - 50, W, 50))
        pygame.draw.line(screen, (80, 60, 140), (0, 65), (W, 65), 2)
        pygame.draw.line(screen, (80, 60, 140), (0, H - 50), (W, H - 50), 2)

        title_surf = self.title_font.render("DINOPODDS", True, (240, 210, 70))
        screen.blit(title_surf, (W // 2 - title_surf.get_width() // 2, 80))

        sub = self.hint_font.render("A world of ancient creatures awaits...", True, (160, 140, 200))
        screen.blit(sub, (W // 2 - sub.get_width() // 2, 148))

        for i, opt in enumerate(self.options):
            y = 210 + i * 60
            unavailable = opt == "Continue" and not has_save
            is_selected = i == self.selected and not unavailable

            if is_selected:
                box = pygame.Rect(W // 2 - 110, y - 10, 220, 38)
                pygame.draw.rect(screen, (50, 38, 85), box, border_radius=7)
                pygame.draw.rect(screen, (160, 130, 255), box, 2, border_radius=7)
                color = (255, 230, 80)
            elif unavailable:
                color = (65, 60, 90)
            else:
                color = (190, 178, 220)

            label = opt + ("  (No Save)" if unavailable else "")
            surf = self.option_font.render(label, True, color)
            screen.blit(surf, (W // 2 - surf.get_width() // 2, y))

        hint = self.hint_font.render("W/S  Navigate       J  Select", True, (95, 85, 125))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 35))

        if self.fade_alpha > 0:
            fade = pygame.Surface((W, H))
            fade.fill((0, 0, 0))
            fade.set_alpha(self.fade_alpha)
            screen.blit(fade, (0, 0))


class DinodexScreen:
    LIST_W   = 195
    IMG_SIZE = 160
    HEADER_H = 38

    def __init__(self, game):
        self.game         = game
        self.font         = game.fonts['BATTLE2']
        self.title_font   = pygame.font.SysFont('Arial', 26, bold=True)
        self.name_font    = pygame.font.SysFont('Arial', 22, bold=True)
        self.small_font   = pygame.font.SysFont('Arial', 18)
        self.tiny_font    = pygame.font.SysFont('Arial', 15)

        # Build sorted entry list from DINODEX_DATA
        self.entries = sorted(DINODEX_DATA.items(), key=lambda kv: kv[1]['number'])
        self.selected = 0
        self.scroll   = 0

        try:
            raw = pygame.image.load(os.path.join('assets', 'Items', 'dinopod.png')).convert_alpha()
            self.pod_icon = pygame.transform.scale(raw, (18, 18))
        except Exception:
            self.pod_icon = None

    def _visible_rows(self):
        row_h = 36
        return (config.HEIGHT - self.HEADER_H) // row_h

    def _type_matchups(self, types):
        """Returns (weaknesses, resistances) dicts of type -> multiplier for the given type list."""
        result = {}
        for atk in TYPE_DATA:
            mult = 1.0
            for def_type in types:
                td = TYPE_DATA.get(def_type, {})
                if atk in td.get('weak_to', []):
                    mult *= 2.0
                elif atk in td.get('resist', []):
                    mult *= 0.5
            if mult != 1.0:
                result[atk] = mult
        weak   = {t: m for t, m in result.items() if m > 1.0}
        resist = {t: m for t, m in result.items() if m < 1.0}
        return weak, resist

    def handle_event(self, event, game):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_w, pygame.K_UP):
            self.selected = (self.selected - 1) % len(self.entries)
            vis = self._visible_rows()
            if self.selected < self.scroll:
                self.scroll = self.selected
            elif self.selected == len(self.entries) - 1:
                self.scroll = max(0, len(self.entries) - vis)
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            self.selected = (self.selected + 1) % len(self.entries)
            vis = self._visible_rows()
            if self.selected >= self.scroll + vis:
                self.scroll = self.selected - vis + 1
            elif self.selected == 0:
                self.scroll = 0
        elif event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
            return 'back'
        return None

    def draw(self, screen):
        screen.fill((18, 18, 28))

        # Header bar
        pygame.draw.rect(screen, (30, 30, 50), (0, 0, config.WIDTH, self.HEADER_H))
        pygame.draw.line(screen, (80, 80, 120), (0, self.HEADER_H), (config.WIDTH, self.HEADER_H), 2)
        screen.blit(self.title_font.render("DINODEX", True, (120, 220, 255)),
                    (10, self.HEADER_H // 2 - 13))
        hint = self.tiny_font.render("W/S = scroll   SPACE = back", True, (120, 120, 140))
        screen.blit(hint, (config.WIDTH - hint.get_width() - 10, self.HEADER_H // 2 - hint.get_height() // 2))

        # Divider between list and detail
        pygame.draw.line(screen, (60, 60, 90), (self.LIST_W, self.HEADER_H), (self.LIST_W, config.HEIGHT), 2)

        # Left list
        caught_names = {d['name'] for d in self.game.player_dinos + self.game.box_dinos}
        row_h   = 36
        vis     = self._visible_rows()
        scroll  = max(0, min(self.scroll, max(0, len(self.entries) - vis)))
        for slot, idx in enumerate(range(scroll, min(scroll + vis, len(self.entries)))):
            name, data = self.entries[idx]
            y = self.HEADER_H + slot * row_h
            is_sel = (idx == self.selected)

            bg = (50, 80, 140) if is_sel else ((30, 30, 48) if slot % 2 == 0 else (24, 24, 40))
            pygame.draw.rect(screen, bg, (0, y, self.LIST_W, row_h))

            num_str = f"#{data['number']:03d}"
            num_surf = self.tiny_font.render(num_str, True, (160, 200, 255) if is_sel else (100, 120, 160))
            screen.blit(num_surf, (8, y + row_h // 2 - num_surf.get_height() // 2))

            name_surf = self.small_font.render(name, True, (255, 255, 255) if is_sel else (200, 200, 210))
            name_x = 52
            screen.blit(name_surf, (name_x, y + row_h // 2 - name_surf.get_height() // 2))

            if name in caught_names and self.pod_icon:
                icon_x = name_x + name_surf.get_width() + 5
                screen.blit(self.pod_icon, (icon_x, y + row_h // 2 - 9))

        # Scroll indicators for list
        if scroll > 0:
            screen.blit(self.tiny_font.render("▲", True, (160, 160, 180)), (self.LIST_W // 2 - 6, self.HEADER_H + 2))
        if scroll + vis < len(self.entries):
            screen.blit(self.tiny_font.render("▼", True, (160, 160, 180)),
                        (self.LIST_W // 2 - 6, config.HEIGHT - 18))

        # Right detail panel
        if not self.entries:
            return
        sel_name, sel_data = self.entries[self.selected]
        dino_data = DINO_DATA.get(sel_name, {})
        types     = dino_data.get('stats', {}).get('type', [])
        desc      = sel_data.get('desc', '')
        number    = sel_data.get('number', 0)

        panel_x = self.LIST_W + 10
        panel_w = config.WIDTH - self.LIST_W - 10

        # Dino name + number
        num_surf  = self.name_font.render(f"#{number:03d}", True, (120, 180, 255))
        name_surf = self.name_font.render(sel_name, True, (255, 255, 255))
        screen.blit(num_surf, (panel_x, self.HEADER_H + 8))
        screen.blit(name_surf, (panel_x + num_surf.get_width() + 12, self.HEADER_H + 8))

        # Type badges
        badge_x = panel_x
        badge_y = self.HEADER_H + 38
        for t in types:
            raw = TYPE_DATA.get(t, {}).get('color', '#505050')
            if isinstance(raw, str):
                raw = raw.lstrip('#')
                tc = tuple(int(raw[i:i+2], 16) for i in (0, 2, 4))
            else:
                tc = raw
            badge_surf = self.tiny_font.render(t.upper(), True, (255, 255, 255))
            bw = badge_surf.get_width() + 14
            pygame.draw.rect(screen, tc, (badge_x, badge_y, bw, 20), border_radius=4)
            screen.blit(badge_surf, (badge_x + 7, badge_y + 2))
            badge_x += bw + 6

        # Dino image
        img = self.game.player_dino_front_images.get(sel_name)
        img_y = self.HEADER_H + 68
        if img:
            scaled = pygame.transform.scale(img, (self.IMG_SIZE, self.IMG_SIZE))
            img_x  = config.WIDTH - self.IMG_SIZE - 10
            screen.blit(scaled, (img_x, img_y))

        # Description (word-wrapped)
        desc_x = panel_x
        desc_y = img_y
        desc_max_w = (config.WIDTH - self.IMG_SIZE - 30) - panel_x
        lines = wrap_text(desc, self.small_font, desc_max_w)
        for i, line in enumerate(lines):
            screen.blit(self.small_font.render(line, True, (200, 210, 220)),
                        (desc_x, desc_y + i * 24))

        # Base stats bar section
        stats_y = img_y + self.IMG_SIZE + 12
        stats   = dino_data.get('stats', {})
        stat_keys = [('health', 'HP'), ('attack', 'ATK'), ('defense', 'DEF'), ('speed', 'SPD')]
        bst = sum(stats.get(k, 0) for k, _ in stat_keys)
        bst_surf = self.small_font.render(f"Base Stat Total:  {bst}", True, (200, 220, 255))
        screen.blit(bst_surf, (panel_x, stats_y))
        stats_y += bst_surf.get_height() + 6
        bar_x  = panel_x
        bar_w  = panel_w - 20
        for stat_key, label in stat_keys:
            val = stats.get(stat_key, 0)
            pygame.draw.rect(screen, (35, 35, 55), (bar_x, stats_y, bar_w, 18), border_radius=3)
            fill_w = min(bar_w, int(bar_w * val / 200))
            bar_color = (80, 200, 80) if val >= 100 else (220, 180, 0) if val >= 60 else (200, 80, 80)
            pygame.draw.rect(screen, bar_color, (bar_x, stats_y, fill_w, 18), border_radius=3)
            lbl = self.tiny_font.render(f"{label}  {val}", True, (230, 230, 230))
            screen.blit(lbl, (bar_x + 6, stats_y + 1))
            stats_y += 24
            if stats_y > config.HEIGHT - 10:
                break

        # Weaknesses / Resistances
        weak, resist = self._type_matchups(types)
        if (weak or resist) and stats_y + 52 <= config.HEIGHT - 4:
            stats_y += 8
            pygame.draw.line(screen, (60, 60, 90),
                             (panel_x, stats_y), (panel_x + panel_w - 20, stats_y), 1)
            stats_y += 5

            mult_fmt = {4.0: '4x', 2.0: '2x', 0.5: '\xbdx', 0.25: '\xbcx'}

            def _tc(t):
                raw = TYPE_DATA.get(t, {}).get('color', '#505050')
                if isinstance(raw, str):
                    raw = raw.lstrip('#')
                    return tuple(int(raw[i:i+2], 16) for i in (0, 2, 4))
                return raw

            for section_label, matchup, hdr_color in [
                ('WEAKNESSES', weak,   (255, 110, 110)),
                ('RESISTANCES', resist, (110, 210, 130)),
            ]:
                if not matchup:
                    continue
                lbl_surf = self.tiny_font.render(section_label, True, hdr_color)
                screen.blit(lbl_surf, (panel_x, stats_y))
                bx = panel_x + lbl_surf.get_width() + 8
                row_start_y = stats_y
                for t, m in sorted(matchup.items()):
                    mstr = mult_fmt.get(m, f'{m}x')
                    text = f"{t.upper()} {mstr}"
                    badge_surf = self.tiny_font.render(text, True, (255, 255, 255))
                    bw = badge_surf.get_width() + 10
                    if bx + bw > panel_x + panel_w - 20:
                        bx = panel_x + lbl_surf.get_width() + 8
                        stats_y += 22
                        row_start_y = stats_y
                    pygame.draw.rect(screen, _tc(t), (bx, stats_y, bw, 20), border_radius=4)
                    screen.blit(badge_surf, (bx + 5, stats_y + 2))
                    bx += bw + 5
                stats_y = row_start_y + 26


class Menu:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.selected_index = 0
        self.options = ["Dinodex", "Party", "Items", "Trainer Card", "Save Game", "Options", "Exit to Menu"]
        self.width = 220
        self.margin = 15
        self.line_height = 40

    def draw(self, screen):
        W = screen.get_width()
        x = W - self.width - 20

        # ── Options panel ──────────────────────────────────────────────
        header_h  = 0
        panel_h   = header_h + len(self.options) * self.line_height + 10
        panel_rect = pygame.Rect(x, 50, self.width, panel_h)
        pygame.draw.rect(screen, (255, 255, 240), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 3)
        for i, option in enumerate(self.options):
            y = panel_rect.y + header_h + 10 + i * self.line_height
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
            if selected == "Dinodex":
                self.game.dinodex_screen.selected = 0
                self.game.dinodex_screen.scroll   = 0
                self.game.push_state('dinodex')
            elif selected == "Party":
                self.game.push_state('party')
            elif selected == "Items":
                self.game.push_state('items')
            elif selected == "Trainer Card":
                self.game.push_state('trainer_card')
            elif selected == "Save Game":
                self.game.save_game()
                self.game.pop_state()
            elif selected == "Options":
                pass  # TODO: implement options
            elif selected == "Exit to Menu":
                self.game.pop_state()
                self.game.yes_no_prompt = YesNoPrompt(
                    "Return to main menu?", self.game.fonts,
                    config.WIDTH, config.HEIGHT)
                self.game.yes_no_callback = self.game.exit_to_title
        elif event.key == pygame.K_SPACE:
            self.game.pop_state()

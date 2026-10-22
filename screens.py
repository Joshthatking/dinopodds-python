import os
import re
import math
import random
import pygame
import config
from data import *
from story import QUEST_STEPS, QUEST_LOG
from ANIM.title_anim import TitleBackdrop, TitleLogo


def load_image(path, alpha=False):
    image = pygame.image.load(path)
    return image.convert_alpha() if alpha else image.convert()


def load_portrait(sprite_key, size):
    """Crop the down-facing idle frame (the top-left 32x32 cell) out of an
    NPC's 4x4 walk-cycle sheet and scale it to `size`, for use as a small
    dialogue-box speaker portrait. Returns None if there's no usable sheet."""
    path = config.NPC_SHEETS.get(sprite_key)
    if not path or not os.path.exists(path):
        return None
    sheet = pygame.image.load(path).convert_alpha()
    if sheet.get_width() < 32 or sheet.get_height() < 32:
        return None
    cell = pygame.Surface((32, 32), pygame.SRCALPHA)
    cell.blit(sheet, (0, 0), (0, 0, 32, 32))
    return pygame.transform.scale(cell, (size, size))


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
    def __init__(self, fonts, dino_key="default", bg_path=None):
        self.fonts = fonts
        self.dino_key = dino_key
        raw_bg = load_image(bg_path or config.ENCOUNTER_BG_PATH)
        self.bg = pygame.transform.scale(raw_bg, (config.WIDTH, config.HEIGHT))
        self.frames = []
        if dino_key in config.ENCOUNTER_DINOS_PATHS:
            self.frames.append(load_image(config.ENCOUNTER_DINOS_PATHS[dino_key], alpha=True))
        if dino_key + "2" in config.ENCOUNTER_DINOS_PATHS:
            self.frames.append(load_image(config.ENCOUNTER_DINOS_PATHS[dino_key + "2"], alpha=True))
        self.current_dino_surface = self.frames[0] if self.frames else None

    def draw(self, screen, enemy_visible=True, offset_x=0):
        screen.blit(self.bg, (0, 0))
        if self.current_dino_surface and enemy_visible:
            mult = config.ENCOUNTER_DINO_SIZES.get(self.dino_key, 1.0)
            size = int(config.ENCOUNTER_BASE_SIZE * mult)
            scaled = pygame.transform.scale(self.current_dino_surface, (size, size))
            rect = scaled.get_rect()
            rect.centerx = screen.get_width() - 157 + int(offset_x)
            rect.centery = 155 + config.FRONT_SPRITE_DY.get(self.dino_key, 0)
            screen.blit(scaled, rect)


# === Double Battle Background ===
class DoubleBattleEncounter:
    """Background + two side-by-side enemy sprites for double trainer battles."""

    def __init__(self, fonts, dino1_key, dino2_key, bg_path=None):
        self.fonts = fonts
        raw_bg = load_image(bg_path or config.DOUBLE_BATTLE_BG_PATH)
        self.bg = pygame.transform.scale(raw_bg, (config.WIDTH, config.HEIGHT))
        self.frame1 = (load_image(config.ENCOUNTER_DINOS_PATHS[dino1_key], alpha=True)
                       if dino1_key in config.ENCOUNTER_DINOS_PATHS else None)
        self.frame2 = (load_image(config.ENCOUNTER_DINOS_PATHS[dino2_key], alpha=True)
                       if dino2_key in config.ENCOUNTER_DINOS_PATHS else None)

    def set_dino(self, slot, dino_key):
        """Swap one side's portrait after a mid-battle replacement (e.g. a
        rotating boss sending out its next dino) — frame1/frame2 are only
        loaded once at construction otherwise, so the old sprite would
        stick around even after enemy_dino/enemy_dino2 changed."""
        frame = (load_image(config.ENCOUNTER_DINOS_PATHS[dino_key], alpha=True)
                  if dino_key in config.ENCOUNTER_DINOS_PATHS else None)
        if slot == 1:
            self.frame1 = frame
        else:
            self.frame2 = frame

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
        elif kind == 'drain':
            lines.append(f"Lifesteal: heals {ab['percent']}% of dmg")
        elif kind == 'lock':
            lines.append(f"Locks foe for {ab['turns']} turns")
        elif kind == 'recharge':
            lines.append("User must recharge next turn")
        elif kind == 'return_hit':
            lines.append(f"Returns next turn: {ab['power']} power")
        elif kind == 'dot':
            if 'damage_flat' in ab:
                lines.append(f"{ab['damage_flat']} HP/turn for {ab['turns']} turns")
            else:
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
# === Battle status badges (shared by the single and double battle HUDs) ===
BADGE_H = 15
BADGE_ROW_STEP = 17


def status_badges(dino, field_effects=None):
    """Every status currently on `dino` as (label, colour) badges: stat
    stages, storm (dot), move lock, recharge, Defend — plus the field
    effects when given (they're shared, so only one box passes them)."""
    badges = []
    for stat, label in (('attack', 'ATK'), ('defense', 'DEF'), ('speed', 'SPD')):
        val = dino.get('stat_stages', {}).get(stat, 0)
        if val:
            badges.append((f"{label}{'+' if val > 0 else ''}{val}",
                           (150, 215, 150) if val > 0 else (215, 150, 150)))
    dot = dino.get('dot')
    if dot:
        label = dot.get('badge', 'STORM')
        color = (190, 150, 225) if label == 'CURSE' else (215, 190, 130)
        badges.append((f"{label} {dot.get('turns_left', '')}".strip(), color))
    rh = dino.get('return_hit')
    if rh:
        color = (165, 215, 240) if rh.get('type') == 'ice' else (215, 175, 120)
        badges.append((f"{rh.get('badge', 'RETURN')} {rh.get('turns_left', '')}".strip(), color))
    if dino.get('locked_move'):
        badges.append((f"LOCK {dino.get('lock_turns_left', '')}".strip(), (195, 170, 225)))
    if dino.get('must_recharge'):
        badges.append(("RECHARGE", (235, 205, 110)))
    if dino.get('defending'):
        badges.append(("GUARD", (150, 195, 235)))
    for fx in field_effects or ():
        turns = fx.get('turns_left', '')
        if fx['effect'] == 'speed_swap':
            badges.append((f"TIME {turns}", (210, 210, 130)))
        elif fx['effect'] == 'type_power':
            badges.append((f"{fx.get('boost_type', '')[:3].upper()}+ {turns}", (215, 185, 130)))
    return badges


def badge_rows(badges, font, max_w):
    """Wrap badges into rows no wider than max_w (never drops any)."""
    rows, row, w = [], [], 0
    for text, bg in badges:
        bw = font.size(text)[0] + 6
        if row and w + bw > max_w:
            rows.append(row)
            row, w = [], 0
        row.append((text, bg, bw))
        w += bw + 3
    if row:
        rows.append(row)
    return rows


def draw_badge_rows(surface, font, x, y, rows):
    for r, row in enumerate(rows):
        bx, by = x, y + r * BADGE_ROW_STEP
        for text, bg, bw in row:
            th = font.size(text)[1]
            pygame.draw.rect(surface, bg, (bx, by, bw, BADGE_H), border_radius=3)
            pygame.draw.rect(surface, (70, 70, 70), (bx, by, bw, BADGE_H), 1, border_radius=3)
            surface.blit(font.render(text, True, (30, 30, 30)), (bx + 3, by + (BADGE_H - th) // 2))
            bx += bw + 3


def double_back_sprite_rect(dino_name, centerx, bottom, base=170):
    """Double-battle player sprite box, with config.BACK_SPRITE_TWEAKS
    applied (dy is scaled down from the 230px single-battle size)."""
    scale, dy = config.BACK_SPRITE_TWEAKS.get(dino_name, (1.0, 0))
    side = int(base * scale)
    rect = pygame.Rect(0, 0, side, side)
    rect.midbottom = (centerx, bottom + int(dy * base / 230))
    return rect


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
        self._slot_ids = None   # (p1, p2, e1, e2) identities from the last update

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
        # A different dino took over a slot (switch, faint replacement, boss
        # refill) — reset that bar instead of sliding from the old dino's HP,
        # which left the new sprite hidden / boxed as "KO" until it caught up.
        slots = (id(p1), id(p2), id(e1), id(e2))
        prev  = self._slot_ids or slots
        self._slot_ids = slots
        if slots[0] != prev[0]: self.player1_hp_display = None
        if slots[1] != prev[1]: self.player2_hp_display = None
        if slots[2] != prev[2]: self.enemy1_hp_display  = None
        if slots[3] != prev[3]: self.enemy2_hp_display  = None
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
             active_dino=None, field_effects=None):

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

        # ── Player back sprites — only the sprite blinks on hit flash.
        # Drawn before the stat boxes so status badges are never covered.
        text_top = text_rect.top
        if p1_visible and pp1 > 0.01:
            r = double_back_sprite_rect(p1['name'], text_rect.x + 85, text_top)
            surface.blit(pygame.transform.scale(p1['image'], r.size), r)
        if p2 and p2_visible and pp2 > 0.01:
            r = double_back_sprite_rect(p2['name'], text_rect.x + 235, text_top)
            surface.blit(pygame.transform.scale(p2['image'], r.size), r)

        xs = self.smaller_font
        BASE_H = 46

        def rows_for(d, pct, bw, fx=None):
            """Status badge rows for a box (none once the dino is KO'd)."""
            if not d or pct <= 0.01:
                return []
            return badge_rows(status_badges(d, fx), xs, bw - SLANT - 12)

        # ── Enemy stat boxes — top-left, stacked, slanted bottom-right
        # en1: base box; en2: slightly wider. Each grows a row per badge row.
        en1_x, en1_y, en1_w = 4, 26, 215
        en2_x, en2_w = 4, 235
        en1_rows = rows_for(e1, ep1, en1_w, field_effects)
        en2_rows = rows_for(e2, ep2, en2_w)
        en1_h = BASE_H + BADGE_ROW_STEP * len(en1_rows)
        en2_h = BASE_H + BADGE_ROW_STEP * len(en2_rows)
        en2_y = en1_y + en1_h + 6

        self._draw_slanted_panel(surface, en1_x, en1_y, en1_w, en1_h, SLANT, slant_side='right')
        if e2:
            self._draw_slanted_panel(surface, en2_x, en2_y, en2_w, en2_h, SLANT, slant_side='right')

        def draw_enemy_stat(d, pct, bx, by, bw, ko, rows):
            if ko:
                surface.blit(sf.render("KO", True, (160, 0, 0)), (bx + 8, by + 14))
                return
            name = self._fit_name(d['name'], sf, bw - 70)
            surface.blit(sf.render(name,             True, (0, 0, 0)), (bx + 8,      by + 6))
            surface.blit(sf.render(f"Lv{d['level']}", True, (0, 0, 0)), (bx + bw - 55, by + 6))
            self._draw_hp_bar(surface, bx + 8, by + 28, bw - SLANT - 12, 10, pct)
            draw_badge_rows(surface, xs, bx + 8, by + 43, rows)

        draw_enemy_stat(e1, ep1, en1_x, en1_y, en1_w, ep1 <= 0.01, en1_rows)
        if e2:
            draw_enemy_stat(e2, ep2, en2_x, en2_y, en2_w, ep2 <= 0.01, en2_rows)

        # ── Player stat boxes — right side, stacked, slanted bottom-left
        text_top = text_rect.top
        pl_w  = 210
        pl_x  = sw - pl_w - 4   # flush right with small margin
        pl1_rows = rows_for(p1, pp1, pl_w)
        pl2_rows = rows_for(p2, pp2, pl_w)
        pl1_h = BASE_H + BADGE_ROW_STEP * len(pl1_rows)
        pl2_h = BASE_H + BADGE_ROW_STEP * len(pl2_rows)
        pl1_y = text_top - pl1_h - 8        # just above dialogue box
        pl2_y = pl1_y - pl2_h - 6           # stacked above pl1

        def draw_player_stat(d, pct, bx, by, bw, ko, rows):
            if ko:
                surface.blit(sf.render("KO", True, (160, 0, 0)), (bx + SLANT + 6, by + 14))
                return
            # left side is slanted at bottom only; text starts after slant offset at top (safe)
            name = self._fit_name(d['name'], sf, bw - 70)
            surface.blit(sf.render(name,              True, (0, 0, 0)), (bx + 8,      by + 6))
            surface.blit(sf.render(f"Lv{d['level']}", True, (0, 0, 0)), (bx + bw - 55, by + 6))
            self._draw_hp_bar(surface, bx + SLANT + 4, by + 28, bw - SLANT - 12, 10, pct)
            draw_badge_rows(surface, xs, bx + SLANT + 4, by + 43, rows)

        # Stat boxes always visible (matching single-battle behaviour — only the sprite blinks)
        self._draw_slanted_panel(surface, pl_x, pl1_y, pl_w, pl1_h, SLANT, slant_side='left')
        draw_player_stat(p1, pp1, pl_x, pl1_y, pl_w, pp1 <= 0.01, pl1_rows)
        if p2:
            self._draw_slanted_panel(surface, pl_x, pl2_y, pl_w, pl2_h, SLANT, slant_side='left')
            draw_player_stat(p2, pp2, pl_x, pl2_y, pl_w, pp2 <= 0.01, pl2_rows)

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

    def skip_xp_animation(self):
        """Snap the XP bar straight to its target. The rest of the win
        sequence (trainer-defeated, coin reward, any post-battle dialogue
        or cutscene) is gated behind is_xp_animating() returning False, so
        at _xp_speed's real-time pace a big XP gain — or several level-ups
        stacked from one battle, each restarting the fill from empty — can
        stall that gate for a long time with nothing visibly prompting the
        player to wait it out. Letting a keypress instantly finish it
        mirrors the message box's own "press to reveal the rest" shortcut."""
        if self._xp_target is not None:
            self.xp_display = self._xp_target

    def show_level_up(self, dino, old_stats, new_stats):
        self.level_up_popup = LevelUpPopup(dino, old_stats, new_stats)

    def draw_panel(self, surface, rect, bg_color=(245, 245, 245), border_color=(0, 0, 0), border_width=3):
        pygame.draw.rect(surface, bg_color, rect)
        pygame.draw.rect(surface, border_color, rect, border_width)

    def draw_hp_bar(self, surface, x, y, width, height, percent, back_color=(200, 0, 0), front_color=(0, 200, 0)):
        pygame.draw.rect(surface, back_color, (x, y, width, height))
        pygame.draw.rect(surface, front_color, (x, y, int(width * max(0, min(1, percent))), height))


    @staticmethod
    def player_sprite_rect(screen_w, screen_h, dino_name=None):
        """Where the player's dino stands: 230px, directly on top of the
        left text box, adjusted per dino by config.BACK_SPRITE_TWEAKS.
        Shared with the send-out intro animation."""
        text_box_rect = pygame.Rect(9, screen_h - 120, screen_w - 325, 115)
        scale, dy = config.BACK_SPRITE_TWEAKS.get(dino_name, (1.0, 0))
        side = int(230 * scale)
        rect = pygame.Rect(0, 0, side, side)
        rect.centerx = text_box_rect.centerx
        rect.bottom = text_box_rect.top + dy
        return rect

    def draw(self, surface, player_dino, enemy_dino, encounter_text, show_actions=True, trainer_total=0, trainer_defeated=0, pod_icon=None, msg_awaiting_input=False, player_visible=True, field_effects=None):
        if not show_actions:
            self.in_fight_menu = False
            self.show_move_info = False
        screen_w, screen_h = surface.get_size()

        # Status badges wrap onto extra rows rather than being cut off; the
        # enemy box grows down and the player box grows up to fit them.
        enemy_rows  = badge_rows(status_badges(enemy_dino, field_effects), self.smaller_font, 200)
        player_rows = badge_rows(status_badges(player_dino), self.smaller_font, 202)
        enemy_extra  = BADGE_ROW_STEP * max(0, len(enemy_rows) - 1)
        player_extra = BADGE_ROW_STEP * max(0, len(player_rows) - 1)

        text_box_rect   = pygame.Rect(9, screen_h - 120, screen_w - 325, 115)
        actions_rect    = pygame.Rect(screen_w - 300, screen_h - 120, 287, 115)
        enemy_info_rect = pygame.Rect(-1, 30, 220, 82 + enemy_extra)
        player_info_rect= pygame.Rect(screen_w - 220, screen_h - 242 - player_extra, 220, 100 + player_extra)

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
        draw_badge_rows(surface, self.smaller_font, enemy_info_rect.x + 10, enemy_info_rect.y + 60, enemy_rows)

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
        # row 3 — status badges (y+57, extra rows push the XP bar down)
        draw_badge_rows(surface, self.smaller_font, player_info_rect.x + 8, player_info_rect.y + 57, player_rows)

        # XP bar (y+88) + XP label in XS font (y+75)
        xp_progress = self.xp_display if self.xp_display is not None else player_dino['xp'] / max(1, player_dino['xp_to_next'])
        xp_bar_rect = pygame.Rect(player_info_rect.x + 8, player_info_rect.y + 88 + player_extra, 202, 8)
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
            sprite_rect = self.player_sprite_rect(screen_w, screen_h, player_dino['name'])
            surface.blit(pygame.transform.scale(player_dino['image'], sprite_rect.size), sprite_rect)

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
def _seconds_since(start_ms):
    return (pygame.time.get_ticks() - start_ms) / 1000.0


class DinoPickupPopup:
    W, H = 260, 210
    MIN_DISPLAY_SEC = 1.5   # like BadgeEarnedScreen: can't be mashed past

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
        self._opened_ms = pygame.time.get_ticks()

    @property
    def ready(self):
        return _seconds_since(self._opened_ms) >= self.MIN_DISPLAY_SEC

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.ready:
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

        prompt = self.fonts['XS'].render("[ J ] Continue" if self.ready else "...", True, (100, 90, 120))
        screen.blit(prompt, prompt.get_rect(centerx=cx, bottom=self.rect.bottom - 10))


# === Dino Picker (starter choice) ===
class DinoPicker:
    """Shows all starter dinos at once; player picks one to keep. Ignores
    input for MIN_DISPLAY_SEC so mashing through Amber's dialogue can't
    pick one by accident."""

    CARD_W, CARD_H = 150, 185
    MIN_DISPLAY_SEC = 1.5

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
        self._opened_ms = pygame.time.get_ticks()

    @property
    def ready(self):
        return _seconds_since(self._opened_ms) >= self.MIN_DISPLAY_SEC

    def handle_event(self, event):
        """Returns chosen index when confirmed, else None."""
        if event.type != pygame.KEYDOWN or not self.ready:
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
                arrow = self.fonts['XS'].render("[ J ] Choose" if self.ready else "...", True, (200, 60, 40))
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
                    # Nuzlocke: a dino that fainted stays in the box for good
                    if n > 0 and not box[self.box_cursor].get('nuzlocke_fainted'):
                        self.grabbed = {'from': 'box', 'idx': self.box_cursor}
                else:
                    src, sidx = self.grabbed['from'], self.grabbed['idx']
                    tidx = self.box_cursor
                    if src == 'box':
                        if sidx != tidx and sidx < len(box) and tidx < len(box):
                            box[sidx], box[tidx] = box[tidx], box[sidx]
                    else:  # from party → drop in box
                        if tidx < len(box) and not box[tidx].get('nuzlocke_fainted'):
                            party[sidx], box[tidx] = box[tidx], party[sidx]
                        elif tidx < len(box) and len(party) > 1:
                            box.append(party.pop(sidx))   # never swap a fainted one out
                            self.par_cursor = min(self.par_cursor, max(0, len(party) - 1))
                            game.active_dino_index = min(game.active_dino_index, len(party) - 1)
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
                fainted = dino.get('nuzlocke_fainted')
                icon = self._icons.get(dino['name'])
                if icon:
                    if fainted:
                        icon = icon.copy()
                        icon.fill((120, 60, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    surface.blit(icon, rect.topleft)
                if fainted:   # Nuzlocke: fainted for good
                    pygame.draw.line(surface, (220, 60, 60), rect.topleft, rect.bottomright, 2)
                    pygame.draw.line(surface, (220, 60, 60), rect.topright, rect.bottomleft, 2)
                surface.blit(self.xs_font.render(f"Lv{dino['level']}", True, (200, 200, 255)),
                             (rect.x, rect.bottom + 2))
                if is_cursor:
                    hover_name = dino['name'] + ("  (fainted - can't leave the box)" if fainted else "")

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
        self.tiny_font    = pygame.font.SysFont('Arial', 15, bold=True)
        self.selected_index  = 0
        self.picking_index   = None   # index of dino being repositioned
        self.preview_frame        = 0
        self.preview_last_switch  = 0
        self.preview_selected_id  = None
        self.preview_interval_ms  = 250
        # id(dino) -> moves whose NEW MOVE badge was cleared by hovering this
        # visit, so the preview can still say what's new while it's selected.
        self._fresh_moves = {}

    def reset(self):
        self.selected_index = 0
        self.picking_index  = None
        self._fresh_moves   = {}

    # ── NEW MOVE notifications ─────────────────────────────────────
    @staticmethod
    def unseen_moves(dino):
        """Known-but-not-equipped moves the player hasn't looked at yet."""
        seen     = dino.setdefault('seen_moves', list(dino.get('moves', [])))
        equipped = {m['name'] for m in dino.get('moveset', [])}
        return [m for m in dino.get('moves', []) if m not in seen and m not in equipped]

    def _mark_seen(self, dino):
        new = self.unseen_moves(dino)
        if new:
            self._fresh_moves[id(dino)] = new
        dino['seen_moves'] = list(dino.get('moves', []))

    # ── Layout ──────────────────────────────────────────────────────
    CARD_X, CARD_Y, CARD_W, CARD_H, CARD_GAP = 12, 12, 212, 68, 6
    PANEL_X, PANEL_W = 236, 392
    PREVIEW_Y, PREVIEW_H = 12, 196
    STATS_Y, STATS_H = 216, 220
    FOOTER_Y = 444

    HEAL_ITEMS = ('Revival Gem', 'Mega Spray')
    MEGA_SPRAY_HP = 20

    def _use_heal_item(self, game, chosen, item_mode):
        """Apply a Revival Gem / Mega Spray to `chosen`. Returns the result
        message, or None (after explaining why) if it can't be used on it."""
        if item_mode == 'Revival Gem':
            if chosen.get('hp', 0) > 0:
                game.message_box.queue_messages(
                    [f"{chosen['name']} hasn't fainted!"], wait_for_input=True)
                return None
            chosen['hp'] = max(1, chosen['max_hp'] // 2)
            game.inventory['Revival Gem'] = max(0, game.inventory.get('Revival Gem', 0) - 1)
            return f"{chosen['name']} was revived with half its HP back!"
        if chosen.get('hp', 0) <= 0:
            game.message_box.queue_messages(
                [f"{chosen['name']} has fainted! Use a Revival Gem instead."], wait_for_input=True)
            return None
        if chosen['hp'] >= chosen['max_hp']:
            game.message_box.queue_messages(
                [f"{chosen['name']} is already at full health!"], wait_for_input=True)
            return None
        chosen['hp'] = min(chosen['max_hp'], chosen['hp'] + self.MEGA_SPRAY_HP)
        game.inventory['Mega Spray'] = max(0, game.inventory.get('Mega Spray', 0) - 1)
        return f"{chosen['name']} was healed by {self.MEGA_SPRAY_HP} HP!"

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

        # Move List — read-only, so it's fine from any party-screen mode
        if event.key == pygame.K_l:
            game.move_list_screen.open()
            game.push_state('move_list')
            return None

        # ── Healing item used mid-battle (blocked in Nuzlocke by the bag) ──
        # Costs the turn, just like switching: see Game._item_turn_used.
        item_mode = getattr(game, 'item_target_mode', None)
        if item_mode in self.HEAL_ITEMS and in_encounter:
            if event.key == pygame.K_j:
                chosen = party[self.selected_index] if 0 <= self.selected_index < list_length else None
                msg = self._use_heal_item(game, chosen, item_mode) if chosen else None
                if msg:
                    game.item_target_mode = None
                    self.reset()
                    game.pop_state()
                    game.message_box.queue_messages(
                        [f"{config.PLAYER_NAME} used a {item_mode}!", msg],
                        on_complete=game._item_turn_used)
            elif event.key == pygame.K_SPACE:
                game.item_target_mode = None
                self.reset()
                game.pop_state()
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
            # With an ally (Abby/Skyy) only slot 0 is the player's — slot 1
            # is a bench dino, not "already in battle".
            in_battle = game._double_player_slots()
            if self.selected_index in in_battle and self.selected_index != double_slot:
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

        # ── Voluntary switch during a double battle ────────────────
        # Double battles don't use game.active_dino_index at all — p1/p2 are
        # always player_dinos[0]/[1] (see Game._double_battle_p2) — so this
        # needs its own branch that actually swaps list positions instead of
        # just repointing an index the double-battle code never reads.
        if in_encounter and not awaiting and event.key == pygame.K_j and getattr(game, 'is_double_battle', False):
            slot = 0 if game.double_phase == 'p1' else 1
            in_battle = game._double_player_slots()
            active = game.player_dinos[slot] if slot < list_length else None
            if active and active.get('lock_turns_left', 0) > 0:
                game.message_box.queue_messages(
                    [f"{active['name']} can't switch out!"], wait_for_input=True)
                return None
            chosen = party[self.selected_index] if 0 <= self.selected_index < list_length else None
            if chosen and self.selected_index == slot:
                game.message_box.queue_messages(
                    [f"{chosen['name']} is already out!"], wait_for_input=True)
                return None
            if chosen and self.selected_index in in_battle:
                game.message_box.queue_messages(
                    ["That dino is already in battle!"], wait_for_input=True)
                return None
            if chosen and chosen.get('hp', 0) <= 0:
                game.message_box.queue_messages(
                    [f"{chosen['name']} has no HP! Choose another."], wait_for_input=True)
                return None
            if chosen and active:
                active['stat_stages'] = {"attack": 0, "defense": 0, "speed": 0}
                active['defending']   = False
                game.player_dinos[slot], game.player_dinos[self.selected_index] = \
                    game.player_dinos[self.selected_index], game.player_dinos[slot]
                game.pop_state()
                if slot == 0:
                    game.double_p1_queued = None
                    on_complete = game._double_advance_to_p2
                else:
                    game.double_p2_queued = None
                    on_complete = game._execute_double_turn
                game.message_box.queue_messages(
                    [f"{chosen['name']}, I choose you!"], on_complete=on_complete)
            return None

        # ── Voluntary switch during a single battle ─────────────────
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

        # ── Item target selection (Revival Gem / Mega Spray) ───────
        item_mode = getattr(game, 'item_target_mode', None)
        if item_mode and not in_encounter:
            if event.key == pygame.K_j:
                chosen = party[self.selected_index] if 0 <= self.selected_index < list_length else None
                if not chosen:
                    return None
                if item_mode in self.HEAL_ITEMS:
                    msg = self._use_heal_item(game, chosen, item_mode)
                    if msg:
                        game.item_target_mode = None
                        self.reset()
                        game.pop_state()
                        game.message_box.queue_messages([msg], wait_for_input=True)
                elif config.ITEMS.get(item_mode, {}).get('tm_move'):
                    used, msgs = game.use_tm(chosen, item_mode)
                    if used:
                        game.item_target_mode = None
                        self.reset()
                        game.pop_state()
                    game.message_box.queue_messages(msgs, wait_for_input=True)
                return None
            if event.key == pygame.K_SPACE:
                game.item_target_mode = None
                self.reset()
                game.pop_state()
                return None
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

        self.selected_index = min(self.selected_index, len(dinos) - 1)
        # Hovering a dino is what clears its NEW MOVE badge.
        self._mark_seen(dinos[self.selected_index])

        for i, dino in enumerate(dinos):
            self._draw_card(screen, i, dino)

        self.draw_preview(screen, dinos[self.selected_index])
        self._draw_footer(screen)

    def _draw_card(self, screen, i, dino):
        rect = pygame.Rect(self.CARD_X, self.CARD_Y + i * (self.CARD_H + self.CARD_GAP),
                           self.CARD_W, self.CARD_H)
        fainted  = dino.get('hp', 0) <= 0
        selected = i == self.selected_index
        if i == self.picking_index:
            color = (60, 150, 200)
        elif selected:
            color = (0, 110, 200)
        elif fainted:
            color = (42, 32, 32)
        else:
            color = (58, 58, 64)
        pygame.draw.rect(screen, color, rect, border_radius=6)
        pygame.draw.rect(screen, (255, 255, 255) if selected else (15, 15, 15), rect, 2, border_radius=6)

        icon = dino.get('front_image') or dino['image']
        icon = pygame.transform.scale(icon, (52, 52))
        if fainted:
            icon = icon.copy()
            icon.set_alpha(110)
        screen.blit(icon, (rect.x + 6, rect.y + (rect.height - 52) // 2))

        text_x = rect.x + 64
        name_c = (170, 170, 170) if fainted else (255, 255, 255)
        name = dino['name']
        while len(name) > 1 and self.smaller_font.size(name)[0] > 92:
            name = name[:-1]
        screen.blit(self.smaller_font.render(name, True, name_c), (text_x, rect.y + 5))
        lv = self.smaller_font.render(f"Lv{dino['level']}", True, name_c)
        screen.blit(lv, (rect.right - lv.get_width() - 8, rect.y + 5))

        max_hp = max(1, dino.get('max_hp', 1))
        pct    = max(0.0, min(1.0, dino.get('hp', 0) / max_hp))
        bar = pygame.Rect(text_x, rect.y + 34, rect.right - 8 - text_x, 8)
        pygame.draw.rect(screen, (35, 35, 35), bar)
        bar_color = (80, 200, 80) if pct > 0.5 else (220, 180, 0) if pct > 0.2 else (200, 60, 60)
        pygame.draw.rect(screen, bar_color, (bar.x, bar.y, int(bar.w * pct), bar.h))
        pygame.draw.rect(screen, (0, 0, 0), bar, 1)

        if fainted:
            status = self.tiny_font.render("FAINTED", True, (235, 110, 110))
        elif i == self.picking_index:
            status = self.tiny_font.render("MOVING...", True, (255, 255, 255))
        else:
            status = self.tiny_font.render(f"{dino.get('hp', 0)}/{dino['max_hp']}", True, (210, 210, 210))
        screen.blit(status, (text_x, rect.y + 46))

        if self.unseen_moves(dino):
            self._draw_new_badge(screen, rect.right - 6, rect.y + 46)
            # Small pulsing yellow "!" on the icon's top-right corner
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180)
            center = (rect.x + 54, rect.y + 12)
            pygame.draw.circle(screen, (255, int(205 + 40 * pulse), 40), center, 8)
            pygame.draw.circle(screen, (40, 30, 0), center, 8, 1)
            bang = self.tiny_font.render("!", True, (40, 30, 0))
            screen.blit(bang, bang.get_rect(center=(center[0], center[1] + 1)))

    def _draw_new_badge(self, screen, right, top):
        """Pulsing yellow NEW MOVE pill, right-aligned at (right, top)."""
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180)
        label = self.tiny_font.render("NEW MOVE", True, (40, 30, 0))
        pill = pygame.Rect(0, 0, label.get_width() + 12, label.get_height() + 2)
        pill.topright = (right, top - 2)
        pygame.draw.rect(screen, (255, int(205 + 40 * pulse), 60), pill, border_radius=8)
        pygame.draw.rect(screen, (40, 30, 0), pill, 1, border_radius=8)
        screen.blit(label, label.get_rect(center=pill.center))

    def _footer_hints(self):
        """(prompt, [(key, label), ...]) for the current party-screen mode."""
        g = self.game
        item_mode = getattr(g, 'item_target_mode', None)
        if item_mode == 'Revival Gem':
            return "Revive which Dino?", [("J", "Select"), ("SPACE", "Cancel")]
        if item_mode == 'Mega Spray':
            return "Heal which Dino?", [("J", "Select"), ("SPACE", "Cancel")]
        if 'encounter' in g.state_stack:
            if g.awaiting_switch or getattr(g, 'double_replace_slot', None) is not None:
                return "Choose a replacement", [("J", "Send out"), ("I", "Moves"), ("L", "Move List")]
            return None, [("J", "Switch in"), ("I", "Moves"), ("L", "Move List"), ("SPACE", "Back")]
        if config.ITEMS.get(item_mode or '', {}).get('tm_move'):
            return f"Teach {config.ITEMS[item_mode]['tm_move']}?", [("J", "Select"), ("SPACE", "Cancel")]
        if self.picking_index is not None:
            return "Pick a spot", [("J", "Place"), ("SPACE", "Back")]
        return None, [("J", "Reorder"), ("O", "Box"), ("I", "Moves"), ("L", "Move List"), ("SPACE", "Back")]

    def _draw_footer(self, screen):
        bar = pygame.Rect(0, self.FOOTER_Y, config.WIDTH, config.HEIGHT - self.FOOTER_Y)
        pygame.draw.rect(screen, (18, 18, 22), bar)
        pygame.draw.line(screen, (70, 70, 80), bar.topleft, bar.topright, 2)
        prompt, hints = self._footer_hints()
        if prompt:
            p = self.smaller_font.render(prompt, True, (255, 200, 0))
            screen.blit(p, (self.CARD_X, bar.centery - p.get_height() // 2))
        # Key chips, right-aligned
        parts = []
        for key, label in hints:
            k = self.tiny_font.render(key, True, (20, 20, 20))
            t = self.tiny_font.render(label, True, (200, 200, 200))
            parts.append((k, t))
        total = sum(k.get_width() + 10 + 5 + t.get_width() for k, t in parts) + 14 * (len(parts) - 1)
        x = config.WIDTH - 12 - total
        for k, t in parts:
            chip = pygame.Rect(x, 0, k.get_width() + 10, k.get_height() + 4)
            chip.centery = bar.centery
            pygame.draw.rect(screen, (220, 220, 225), chip, border_radius=4)
            screen.blit(k, k.get_rect(center=chip.center))
            x = chip.right + 5
            screen.blit(t, (x, bar.centery - t.get_height() // 2))
            x += t.get_width() + 14

    def draw_preview(self, screen, dino):
        preview_rect = pygame.Rect(self.PANEL_X, self.PREVIEW_Y, self.PANEL_W, self.PREVIEW_H)

        types = dino['type'] if isinstance(dino['type'], list) else [dino['type']]
        colors = [TYPE_DATA.get(t, {}).get("color", (100, 200, 230)) for t in types]
        if len(colors) == 1:
            pygame.draw.rect(screen, colors[0], preview_rect)
        else:
            half = preview_rect.height // 2
            pygame.draw.rect(screen, colors[0], pygame.Rect(preview_rect.x, preview_rect.y, preview_rect.width, half))
            pygame.draw.rect(screen, colors[1], pygame.Rect(preview_rect.x, preview_rect.y + half, preview_rect.width, half))
        pygame.draw.rect(screen, (0, 0, 0), preview_rect, 3)

        def shadowed(font, text, color, pos):
            screen.blit(font.render(text, True, (0, 0, 0)), (pos[0] + 1, pos[1] + 1))
            screen.blit(font.render(text, True, color), pos)

        left, top = preview_rect.left + 12, preview_rect.top + 10
        shadowed(self.font, dino['name'], (255, 255, 255), (left, top))
        shadowed(self.smaller_font, f"Lv {dino['level']}", (255, 255, 255), (left, top + 24))
        nature = dino.get("nature", "")
        if nature:
            shadowed(self.smaller_font, f"{nature} Nature", (255, 230, 100), (left, top + 46))

        hp_text = self.smaller_font.render(f"HP {dino['hp']}/{dino['max_hp']}", True, (255, 255, 255))
        shadowed(self.smaller_font, f"HP {dino['hp']}/{dino['max_hp']}", (255, 255, 255),
                 (preview_rect.right - hp_text.get_width() - 12, top))

        # Type chips, bottom-right
        cx = preview_rect.right - 10
        for t, c in reversed(list(zip(types, colors))):
            lbl = self.tiny_font.render(t.upper(), True, (255, 255, 255))
            chip = pygame.Rect(0, 0, lbl.get_width() + 12, lbl.get_height() + 4)
            chip.bottomright = (cx, preview_rect.bottom - 10)
            pc = pygame.Color(c)   # TYPE_DATA colors may be tuples or hex strings
            pygame.draw.rect(screen, (max(0, pc.r - 50), max(0, pc.g - 50), max(0, pc.b - 50)),
                             chip, border_radius=4)
            pygame.draw.rect(screen, (0, 0, 0), chip, 1, border_radius=4)
            screen.blit(lbl, lbl.get_rect(center=chip.center))
            cx = chip.left - 6

        # XP bar, bottom-left
        current_xp = dino.get("xp", 0)
        xp_to_next = max(1, dino.get("xp_to_next", 1))
        xp_bar = pygame.Rect(preview_rect.x + 12, preview_rect.bottom - 22, 130, 12)
        shadowed(self.tiny_font, f"XP {int(current_xp)}/{int(xp_to_next)}", (255, 255, 255),
                 (xp_bar.x, xp_bar.y - 18))
        pygame.draw.rect(screen, (255, 255, 255), xp_bar)
        pygame.draw.rect(screen, (0, 100, 255), (xp_bar.x, xp_bar.y, int(xp_bar.w * min(current_xp / xp_to_next, 1)), xp_bar.h))
        pygame.draw.rect(screen, (0, 0, 0), xp_bar, 2)

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

        img = pygame.transform.scale(frame_img, (150, 150))
        screen.blit(img, img.get_rect(center=(preview_rect.centerx + 40, preview_rect.centery + 4)))

        # Stats (left column) + moves (right column)
        stats_rect = pygame.Rect(self.PANEL_X, self.STATS_Y, self.PANEL_W, self.STATS_H)
        pygame.draw.rect(screen, (50, 50, 56), stats_rect, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 0), stats_rect, 3, border_radius=6)
        heading_c = (150, 170, 210)
        col1_x = stats_rect.x + 12
        col2_x = stats_rect.x + 178
        screen.blit(self.tiny_font.render("STATS", True, heading_c), (col1_x, stats_rect.y + 8))
        screen.blit(self.tiny_font.render("MOVES", True, heading_c), (col2_x, stats_rect.y + 8))

        nature_boosts = NATURE_BOOSTS.get(dino.get("nature", ""), {})
        stat_rows = [("hp", "HP", dino['max_hp']), ("attack", "Attack", dino['attack']),
                     ("defense", "Defense", dino['defense']), ("speed", "Speed", dino['speed'])]
        for i, (stat_key, name, val) in enumerate(stat_rows):
            y = stats_rect.y + 30 + i * 36
            boost = nature_boosts.get(stat_key)
            # Same as the original stats box: boosted stat in green with
            # the "(+N%)" on the same line.
            if boost:
                label = f"{name}: {val} (+{int(boost * 100)}%)"
                color = (160, 255, 140)
            else:
                label = f"{name}: {val}"
                color = (255, 255, 255)
            screen.blit(self.smaller_font.render(label, True, color), (col1_x, y))

        move_w, move_h = stats_rect.right - 12 - col2_x, 30
        for i, move in enumerate(dino['moveset']):
            move_color = TYPE_DATA.get(move['type'], {}).get("color", (200, 200, 200))
            move_rect = pygame.Rect(col2_x, stats_rect.y + 28 + i * (move_h + 6), move_w, move_h)
            pygame.draw.rect(screen, move_color, move_rect, border_radius=4)
            pygame.draw.rect(screen, (0, 0, 0), move_rect, 2, border_radius=4)
            mc = pygame.Color(move_color)
            # Dark text on light type colors (e.g. Flash, Static Graze)
            text_c = (25, 25, 25) if (0.299 * mc.r + 0.587 * mc.g + 0.114 * mc.b) > 170 else (255, 255, 255)
            name_s = self.smaller_font.render(move['name'], True, text_c)
            screen.blit(name_s, (move_rect.x + 8, move_rect.centery - name_s.get_height() // 2))
            pa = self.tiny_font.render(f"{move['damage']}/{move['accuracy']}", True, text_c)
            screen.blit(pa, (move_rect.right - pa.get_width() - 8, move_rect.centery - pa.get_height() // 2))

        # NEW MOVE notice for the hovered dino (its card badge just cleared)
        fresh = self._fresh_moves.get(id(dino))
        if fresh:
            text = f"New: {', '.join(fresh)}  - press I to equip"
            while len(text) > 4 and self.tiny_font.size(text)[0] > stats_rect.w - 24 - 80:
                text = text[:-4] + "..."
            notice_y = stats_rect.bottom - 30
            self._draw_new_badge(screen, col1_x + 76, notice_y + 4)
            screen.blit(self.tiny_font.render(text, True, (255, 225, 110)), (col1_x + 84, notice_y + 2))


# === Move List (party menu, L) ===
class MoveListScreen:
    """Every move the player has unlocked, one tab per type, strongest
    first. A move only appears once some dino in the party or Box has
    learned it; the rest of the type is just a "N still undiscovered"
    count so the list doubles as a collection tracker without spoiling it."""
    TYPE_ORDER = ('magma', 'aqua', 'earth', 'ice', 'spike', 'lightning',
                  'flying', 'rock', 'dark', 'light', 'ancient')
    TYPE_ABBR  = {'lightning': 'VOLT', 'flying': 'FLY', 'ancient': 'ANCNT'}
    TOP        = 12
    TABS_Y     = 46
    TAB_H      = 36
    PANEL_Y    = 92
    PANEL_H    = 344
    ROW_H      = 30
    FOOTER_Y   = 444

    def __init__(self, game):
        self.game       = game
        self.title_font = game.fonts['BATTLE2']
        self.font       = pygame.font.SysFont('Arial', 20)
        self.small_font = pygame.font.SysFont('Arial', 17)
        self.tiny_font  = pygame.font.SysFont('Arial', 13, bold=True)
        self.types      = [t for t in self.TYPE_ORDER if t in TYPE_DATA] + \
                          [t for t in TYPE_DATA if t not in self.TYPE_ORDER]
        self.type_idx   = 0
        self.cursor     = {}   # type -> selected row
        self.scroll     = {}   # type -> first visible row

    # ── Data ────────────────────────────────────────────────────────
    def _owners(self):
        """move name -> [(dino name, equipped?)] across party and Box."""
        owners = {}
        for d in list(self.game.player_dinos) + list(self.game.box_dinos):
            equipped = {m['name'] for m in d.get('moveset', [])}
            for name in set(d.get('moves', [])) | equipped:
                owners.setdefault(name, []).append((d['name'], name in equipped))
        return owners

    def _moves_of(self, mtype, owners):
        """(unlocked moves sorted by power desc, total moves of this type)."""
        all_moves = [n for n, md in MOVE_DATA.items() if md.get('type') == mtype]
        unlocked  = [n for n in all_moves if n in owners]
        unlocked.sort(key=lambda n: (-MOVE_DATA[n].get('damage', 0), n))
        return unlocked, len(all_moves)

    def _rgb(self, mtype):
        return pygame.Color(TYPE_DATA.get(mtype, {}).get('color', (150, 150, 150)))

    def open(self):
        """Start on the first type the player actually has moves in."""
        owners = self._owners()
        if not self._moves_of(self.types[self.type_idx], owners)[0]:
            for i, t in enumerate(self.types):
                if self._moves_of(t, owners)[0]:
                    self.type_idx = i
                    break

    # ── Input ───────────────────────────────────────────────────────
    def _visible_rows(self):
        return (self.PANEL_H - 40) // self.ROW_H

    def handle_event(self, event, game):
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_l):
            return 'back'
        if event.key in (pygame.K_a, pygame.K_LEFT):
            self.type_idx = (self.type_idx - 1) % len(self.types)
        elif event.key in (pygame.K_d, pygame.K_RIGHT):
            self.type_idx = (self.type_idx + 1) % len(self.types)
        elif event.key in (pygame.K_w, pygame.K_UP, pygame.K_s, pygame.K_DOWN):
            t = self.types[self.type_idx]
            n = len(self._moves_of(t, self._owners())[0])
            if n:
                step = -1 if event.key in (pygame.K_w, pygame.K_UP) else 1
                cur = (self.cursor.get(t, 0) + step) % n
                self.cursor[t] = cur
                top, vis = self.scroll.get(t, 0), self._visible_rows()
                if cur < top:
                    top = cur
                elif cur >= top + vis:
                    top = cur - vis + 1
                self.scroll[t] = top
        return None

    # ── Drawing ─────────────────────────────────────────────────────
    def draw(self, screen):
        screen.fill((30, 30, 34))
        owners = self._owners()
        mtype  = self.types[self.type_idx]
        moves, total_type = self._moves_of(mtype, owners)

        # Header
        screen.blit(self.title_font.render("MOVE LIST", True, (255, 255, 255)), (12, self.TOP))
        found = sum(1 for n in MOVE_DATA if n in owners)
        count = self.small_font.render(f"Discovered {found}/{len(MOVE_DATA)}", True, (200, 200, 210))
        screen.blit(count, (config.WIDTH - count.get_width() - 12, self.TOP + 2))

        # Type tabs
        tab_w = (config.WIDTH - 24 - 2 * (len(self.types) - 1)) // len(self.types)
        for i, t in enumerate(self.types):
            rect = pygame.Rect(12 + i * (tab_w + 2), self.TABS_Y, tab_w, self.TAB_H)
            c = self._rgb(t)
            got, tot = self._moves_of(t, owners)
            active = i == self.type_idx
            fill = c if active else (c.r // 3 + 20, c.g // 3 + 20, c.b // 3 + 20)
            pygame.draw.rect(screen, fill, rect, border_radius=5)
            pygame.draw.rect(screen, (255, 255, 255) if active else (10, 10, 10), rect, 2, border_radius=5)
            text_c = self._text_on(fill)
            lbl = self.tiny_font.render(self.TYPE_ABBR.get(t, t.upper()), True, text_c)
            screen.blit(lbl, lbl.get_rect(centerx=rect.centerx, top=rect.y + 3))
            cnt = self.tiny_font.render(f"{len(got)}/{tot}", True, text_c)
            screen.blit(cnt, cnt.get_rect(centerx=rect.centerx, bottom=rect.bottom - 3))

        # Move list panel
        lp = pygame.Rect(12, self.PANEL_Y, 300, self.PANEL_H)
        pygame.draw.rect(screen, (48, 48, 54), lp, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 0), lp, 3, border_radius=6)
        tc = self._rgb(mtype)
        screen.blit(self.font.render(f"{mtype.capitalize()} moves", True, tc), (lp.x + 12, lp.y + 8))
        hdr = self.tiny_font.render("POW   ACC", True, (150, 150, 165))
        screen.blit(hdr, (lp.right - hdr.get_width() - 14, lp.y + 13))

        sel_name = None
        if not moves:
            msg = "No moves of this type discovered yet."
            for j, line in enumerate(wrap_text(msg, self.small_font, lp.w - 28)):
                screen.blit(self.small_font.render(line, True, (170, 170, 180)),
                            (lp.x + 14, lp.y + 50 + j * 22))
        else:
            cur = min(self.cursor.get(mtype, 0), len(moves) - 1)
            top = self.scroll.get(mtype, 0)
            vis = self._visible_rows()
            sel_name = moves[cur]
            for row, name in enumerate(moves[top:top + vis]):
                idx = top + row
                r = pygame.Rect(lp.x + 6, lp.y + 36 + row * self.ROW_H, lp.w - 12, self.ROW_H - 3)
                if idx == cur:
                    pygame.draw.rect(screen, (0, 110, 200), r, border_radius=4)
                    pygame.draw.rect(screen, (255, 255, 255), r, 1, border_radius=4)
                md = MOVE_DATA[name]
                pygame.draw.rect(screen, tc, (r.x + 4, r.y + 6, 5, r.h - 12))
                screen.blit(self.small_font.render(name, True, (255, 255, 255)), (r.x + 16, r.y + 4))
                pow_s = str(md.get('damage', 0)) if md.get('damage', 0) > 0 else "-"
                p = self.small_font.render(pow_s, True, (255, 230, 150))
                a = self.small_font.render(str(md.get('accuracy', 100)), True, (200, 220, 255))
                screen.blit(a, (r.right - a.get_width() - 8, r.y + 4))
                screen.blit(p, (r.right - 46 - p.get_width(), r.y + 4))
            # Scroll arrows
            if top > 0:
                pygame.draw.polygon(screen, (220, 220, 220), [(lp.centerx - 6, lp.y + 34), (lp.centerx + 6, lp.y + 34), (lp.centerx, lp.y + 28)])
            if top + vis < len(moves):
                by = lp.bottom - 8
                pygame.draw.polygon(screen, (220, 220, 220), [(lp.centerx - 6, by - 6), (lp.centerx + 6, by - 6), (lp.centerx, by)])

        hidden = total_type - len(moves)
        if hidden:
            h = self.tiny_font.render(f"{hidden} still undiscovered", True, (130, 130, 145))
            screen.blit(h, (lp.x + 14, lp.bottom - 22))

        # Detail panel
        dp = pygame.Rect(324, self.PANEL_Y, config.WIDTH - 324 - 12, self.PANEL_H)
        pygame.draw.rect(screen, (48, 48, 54), dp, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 0), dp, 3, border_radius=6)
        if sel_name:
            self._draw_detail(screen, dp, sel_name, owners.get(sel_name, []))
        else:
            hint = f"Teach a dino a {mtype.capitalize()} move to unlock its entry here."
            for j, line in enumerate(wrap_text(hint, self.small_font, dp.w - 28)):
                screen.blit(self.small_font.render(line, True, (150, 150, 165)),
                            (dp.x + 14, dp.y + 14 + j * 22))

        self._draw_footer(screen)

    @staticmethod
    def _text_on(color):
        c = pygame.Color(color)
        return (25, 25, 25) if (0.299 * c.r + 0.587 * c.g + 0.114 * c.b) > 170 else (255, 255, 255)

    def _draw_detail(self, screen, dp, name, owners):
        md = MOVE_DATA[name]
        x, y = dp.x + 14, dp.y + 12
        screen.blit(self.title_font.render(name, True, (255, 255, 255)), (x, y))
        y += 30
        c = self._rgb(md.get('type', ''))
        lbl = self.tiny_font.render(md.get('type', '').upper(), True, self._text_on(c))
        chip = pygame.Rect(x, y, lbl.get_width() + 14, lbl.get_height() + 6)
        pygame.draw.rect(screen, c, chip, border_radius=4)
        pygame.draw.rect(screen, (0, 0, 0), chip, 1, border_radius=4)
        screen.blit(lbl, lbl.get_rect(center=chip.center))
        dmg = md.get('damage', 0)
        stats = f"Power {dmg if dmg > 0 else '-'}    Acc {md.get('accuracy', 100)}%"
        screen.blit(self.small_font.render(stats, True, (230, 230, 200)), (chip.right + 12, y))
        y += 30
        pygame.draw.line(screen, (90, 90, 110), (dp.x + 10, y), (dp.right - 10, y))
        y += 8

        for line in wrap_text(generate_move_desc(name), self.small_font, dp.w - 28)[:8]:
            screen.blit(self.small_font.render(line, True, (235, 235, 235)), (x, y))
            y += 21

        # Who knows it (★ = in its 4 battle moves)
        y = max(y + 6, dp.bottom - 96)
        pygame.draw.line(screen, (90, 90, 110), (dp.x + 10, y), (dp.right - 10, y))
        screen.blit(self.tiny_font.render("KNOWN BY   (* = equipped)", True, (150, 170, 210)), (x, y + 6))
        names = [f"{n}{'*' if eq else ''}" for n, eq in owners]
        for j, line in enumerate(wrap_text(", ".join(names), self.small_font, dp.w - 28)[:3]):
            screen.blit(self.small_font.render(line, True, (255, 255, 255)), (x, y + 24 + j * 20))

    def _draw_footer(self, screen):
        bar = pygame.Rect(0, self.FOOTER_Y, config.WIDTH, config.HEIGHT - self.FOOTER_Y)
        pygame.draw.rect(screen, (18, 18, 22), bar)
        pygame.draw.line(screen, (70, 70, 80), bar.topleft, bar.topright, 2)
        x = config.WIDTH - 12
        for key, label in reversed([("A/D", "Type"), ("W/S", "Move"), ("SPACE", "Back")]):
            t = self.tiny_font.render(label, True, (200, 200, 200))
            k = self.tiny_font.render(key, True, (20, 20, 20))
            x -= t.get_width()
            screen.blit(t, (x, bar.centery - t.get_height() // 2))
            chip = pygame.Rect(0, 0, k.get_width() + 10, k.get_height() + 4)
            chip.right, chip.centery = x - 5, bar.centery
            pygame.draw.rect(screen, (220, 220, 225), chip, border_radius=4)
            screen.blit(k, k.get_rect(center=chip.center))
            x = chip.left - 14


# === Move Info Screen ===

def generate_move_desc(move_name):
    md = MOVE_DATA.get(move_name)
    if not md:
        return "Unknown move."
    parts = []
    damage = md.get('damage', 0)
    target = md.get('target', 'opponent')
    ability = md.get('ability')
    if md.get('priority', 0) > 0:
        parts.append("Priority move: acts before non-priority moves, regardless of Speed.")
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
        elif kind == 'drain':
            parts.append(f"Lifesteal: the user heals {ability.get('percent', 0)}% of the damage dealt.")
        elif kind == 'lock':
            turns = ability.get('turns', 2)
            parts.append(f"Traps the opponent for {turns} turns.")
        elif kind == 'recharge':
            parts.append("If it hits, the user must spend its next turn recharging.")
        elif kind == 'return_hit':
            parts.append(f"If it hits, it comes back around at the end of the next turn "
                         f"for another {ability.get('power', 0)} base damage. The return can't be Defended.")
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
            if 'damage_flat' in ability:
                parts.append(f"Deals {ability['damage_flat']} damage at the end of each turn for {ability.get('turns', 3)} turns.")
            else:
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
        # However many full rows fit inside the list panel
        self.visible_rows = (self.LIST_RECT.height - 3 - self.ROW_TOP - self.ROW_H) // self.ROW_STEP + 1
        self.scroll_offset = 0

    LIST_RECT = pygame.Rect(340, 50, 280, 320)
    ROW_TOP   = 15   # first row's highlight top, from the panel's top
    ROW_H     = 30
    ROW_STEP  = 35

    def _clamp_scroll(self, n):
        """Keep the selection in range (items can run out) and on screen."""
        self.selected_index = max(0, min(self.selected_index, n - 1))
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.visible_rows:
            self.scroll_offset = self.selected_index - self.visible_rows + 1
        self.scroll_offset = max(0, min(self.scroll_offset, max(0, n - self.visible_rows)))

    def get_filtered_inventory(self):
        return [(item, count) for item, count in self.inventory.items() if count > 0]

    def reset(self):
        self.selected_index = 0
        self.scroll_offset = 0

    ICON_BOX = 26

    def _fitted_icon(self, item):
        """Item icon scaled (aspect kept, transparent padding trimmed) to fit ICON_BOX."""
        cache = self.__dict__.setdefault('_icon_cache', {})
        src = self.icons.get(item)
        if item not in cache or cache[item][0] is not src:
            img = None
            if src is not None:
                r = src.get_bounding_rect()
                if r.width and r.height:
                    trimmed = src.subsurface(r)
                    s = min(self.ICON_BOX / r.width, self.ICON_BOX / r.height)
                    size = (max(1, round(r.width * s)), max(1, round(r.height * s)))
                    img = (pygame.transform.scale(trimmed, size) if s >= 1
                           else pygame.transform.smoothscale(trimmed, size))
            cache[item] = (src, img)
        return cache[item][1]

    def _fit_name(self, name, max_w):
        """Render `name` in the bag font, falling back to the smaller font,
        then to an ellipsis, so it never runs past max_w."""
        for font in (self.font, self.desc_font):
            surf = font.render(name, True, (0, 0, 0))
            if surf.get_width() <= max_w:
                return surf
        text = name
        while len(text) > 1 and self.desc_font.size(text + "...")[0] > max_w:
            text = text[:-1]
        return self.desc_font.render(text.rstrip() + "...", True, (0, 0, 0))

    def draw(self, surface):
        right_rect = self.LIST_RECT
        pygame.draw.rect(surface, (255, 255, 240), right_rect)
        pygame.draw.rect(surface, (0, 0, 0), right_rect, 3)

        filtered = self.get_filtered_inventory()
        self.filtered_inventory = filtered

        if not filtered:
            surface.blit(self.font.render("No items collected.", True, (0, 0, 0)),
                         (right_rect.x + 20, right_rect.y + 40))
            return

        self._clamp_scroll(len(filtered))
        row_h = self.ROW_H
        for i, (item, count) in enumerate(filtered[self.scroll_offset:self.scroll_offset + self.visible_rows]):
            y = right_rect.y + self.ROW_TOP + 5 + i * self.ROW_STEP
            mid = y + 10
            if self.scroll_offset + i == self.selected_index:
                pygame.draw.rect(surface, (200, 200, 255),
                                 (right_rect.x + 5, y - 5, right_rect.width - 10, row_h), border_radius=5)
            icon = self._fitted_icon(item)
            if icon:
                surface.blit(icon, icon.get_rect(center=(right_rect.x + 10 + self.ICON_BOX // 2, mid)))
            count_surf = self.font.render(f"x{count}", True, (0, 0, 0))
            count_x = right_rect.right - 12 - count_surf.get_width()
            surface.blit(count_surf, count_surf.get_rect(midleft=(count_x, mid)))
            name_x = right_rect.x + 18 + self.ICON_BOX
            name_surf = self._fit_name(item, count_x - 8 - name_x)
            surface.blit(name_surf, name_surf.get_rect(midleft=(name_x, mid)))

        # Little arrows on the panel's border when there's more to scroll to
        ax = right_rect.centerx
        if self.scroll_offset > 0:
            top = right_rect.top
            pygame.draw.polygon(surface, (0, 0, 0), [(ax - 7, top + 4), (ax + 7, top + 4), (ax, top - 4)])
        if self.scroll_offset + self.visible_rows < len(filtered):
            bot = right_rect.bottom
            pygame.draw.polygon(surface, (0, 0, 0), [(ax - 7, bot - 4), (ax + 7, bot - 4), (ax, bot + 4)])

        desc_rect = pygame.Rect(340, 380, 280, 70)
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

        self._clamp_scroll(len(filtered))
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
            elif item_name == 'Revival Gem':
                if 'encounter' in game.state_stack and game.nuzlocke:
                    game.message_box.queue_messages(
                        ["Nuzlocke: Revival Gems can't be used in battle!"], wait_for_input=True)
                    return 'used'
                if not any(d.get('hp', 0) <= 0 for d in game.player_dinos):
                    game.message_box.queue_messages(
                        ["None of your Dinos have fainted!"], wait_for_input=True)
                    return 'used'
                game.item_target_mode = 'Revival Gem'
                return 'target_party'
            elif item_name == 'Mega Spray':
                if 'encounter' in game.state_stack and game.nuzlocke:
                    game.message_box.queue_messages(
                        ["Nuzlocke: Mega Sprays can't be used in battle!"], wait_for_input=True)
                    return 'used'
                if not any(0 < d.get('hp', 0) < d.get('max_hp', 0) for d in game.player_dinos):
                    game.message_box.queue_messages(
                        ["No Dinos need healing right now!"], wait_for_input=True)
                    return 'used'
                game.item_target_mode = 'Mega Spray'
                return 'target_party'
            elif item_data.get('tm_move'):
                if 'encounter' in game.state_stack:
                    game.message_box.queue_messages(
                        ["TMs can't be used in battle!"], wait_for_input=True)
                    return 'used'
                game.item_target_mode = item_name
                return 'target_party'
        elif event.key == pygame.K_w:
            if self.selected_index > 0:
                self.selected_index -= 1
            self._clamp_scroll(len(filtered))
        elif event.key == pygame.K_s:
            if self.selected_index < len(filtered) - 1:
                self.selected_index += 1
            self._clamp_scroll(len(filtered))
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

    def __init__(self, question, fonts, width=640, height=480, input_delay=0.0):
        self.question = question
        self.font     = fonts['DIALOGUE']
        self.opt_font = fonts['BAG']
        self.selected = 0   # 0 = Yes, 1 = No
        self.width    = width
        self.height   = height
        self.input_delay = input_delay   # seconds of ignored input, so a mashed key can't answer it
        self._opened_ms  = pygame.time.get_ticks()

    def handle_event(self, event):
        """Returns 'yes', 'no', or None."""
        if event.type != pygame.KEYDOWN or _seconds_since(self._opened_ms) < self.input_delay:
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


# === Route/Town Banner ===
class RouteBanner:
    """Top-left banner that slides down to announce the current route/town
    name, holds for a few seconds, then slides back up.

    Triggered by Game.check_zone_banner() whenever the player's movement
    crosses one of the strips in data.ZONE_BANNER_TRANSITIONS. Calling
    show() while already showing just restarts the sequence with the new
    name — no queueing, since only the latest crossing matters.
    """

    WIDTH           = 220
    HEIGHT          = 50
    SLIDE_DURATION  = 0.4   # seconds to slide fully in/out
    HOLD_DURATION   = 4.0   # seconds fully visible before sliding back up

    def __init__(self, fonts):
        self.font = fonts['DIALOGUE_BOX']
        self.text = ""
        self.phase = None   # None | 'in' | 'hold' | 'out'
        self.timer = 0.0

    def show(self, text):
        self.text = text
        self.phase = 'in'
        self.timer = 0.0

    def update(self, dt):
        if self.phase is None:
            return
        self.timer += dt
        if self.phase == 'in' and self.timer >= self.SLIDE_DURATION:
            self.phase, self.timer = 'hold', 0.0
        elif self.phase == 'hold' and self.timer >= self.HOLD_DURATION:
            self.phase, self.timer = 'out', 0.0
        elif self.phase == 'out' and self.timer >= self.SLIDE_DURATION:
            self.phase, self.timer = None, 0.0

    def draw(self, surface):
        if self.phase is None:
            return
        if self.phase == 'in':
            progress = self.timer / self.SLIDE_DURATION
        elif self.phase == 'hold':
            progress = 1.0
        else:  # 'out'
            progress = 1.0 - self.timer / self.SLIDE_DURATION
        progress = max(0.0, min(1.0, progress))

        y = -self.HEIGHT + int(self.HEIGHT * progress)
        label = self.font.render(self.text, True, (0, 0, 0))
        # Widen for long names (e.g. "Silverleaf Town") so the text never
        # runs past the border; WIDTH is just the minimum.
        box = pygame.Rect(0, y, max(self.WIDTH, label.get_width() + 28), self.HEIGHT)
        pygame.draw.rect(surface, (255, 255, 255), box)
        pygame.draw.rect(surface, (0, 0, 0), box, 3)
        surface.blit(label, (box.x + 14, box.y + (box.height - label.get_height()) // 2))


# === Message Box ===
class DialogueBox:
    """A reusable, self-contained two-line dialogue box.

    Give it text and it handles the rest: word-wrapping to the box
    width, a typewriter-style character reveal, pausing with a
    blinking "▼" once both lines are full and typed, and a smooth
    scroll-up transition into the next two lines when the player
    advances. Long text is paginated into fixed 2-line chunks up
    front, so a page is never repeated and a sentence always keeps
    flowing in order.

    Usage:
        box = DialogueBox(config.WIDTH, fonts)
        box.queue_messages(["Line one...", "Line two..."], on_complete=...)
        # each frame:
        box.update(dt)
        box.handle_event(event)   # advances on SPACE / J
        box.draw(screen)

    Internal model
    ---------------
    - `self.messages`   : queued raw strings not yet being shown.
    - `self._pages`      : the CURRENT string's word-wrapped lines,
                           chopped into fixed-size (LINES_PER_PAGE) pages.
    - `self._page_index` : which page of `_pages` is on screen.
    - `self.message`     : the on-screen page's text (joined lines) —
                           this is what the typewriter reveals.
    - `self.char_index`  : how many characters of `self.message` are
                           currently revealed.
    - `self._scrolling`  : True while animating the transition between
                           two pages (see _begin_scroll/_finish_scroll).
    """

    LINES_PER_PAGE  = 2      # visible lines in the box at once
    CHAR_DELAY      = 0.03   # seconds per revealed character
    SCROLL_DURATION = 0.18   # seconds for the page-advance scroll animation
    PAD             = 15     # inner padding, px
    PORTRAIT_SIZE   = 40     # speaker portrait, px

    # Matches a leading "[Name] " speaker tag, as produced by
    # Game._tag_dialogue()/_split_dialogue(name=...).
    _SPEAKER_TAG_RE = re.compile(r'^\[([^\]]+)\]')

    def __init__(self, width, fonts):
        self.width  = width
        self.font   = fonts['DIALOGUE_BOX']
        self.visible = False
        self.wait_for_input = False
        self.on_complete = None

        self.messages = []          # queued raw strings still to show
        self._pages = [[]]          # current message, wrapped into 2-line pages
        self._page_index = 0

        self.message = ""            # text of the page currently on screen
        self.char_index = 0          # characters of `message` revealed so far
        self.char_timer = 0.0

        self.timer = 0                # auto-dismiss countdown, only for show()
        self._duration_ms = 0

        # Scroll-transition state — see _begin_scroll()/_draw_scrolling()
        self._scrolling = False
        self._scroll_t = 0.0
        self._outgoing_lines = []
        self._next_page_index = 0

        # Speaker portrait — set once per _start_message() call from that
        # message's leading "[Name] " tag (if any) and held for the whole
        # box, including any pages it later scrolls through. See
        # _get_portrait()/_draw_portrait().
        self.speaker_name = None
        self._portrait_cache = {}

    # ── Feeding text in ──────────────────────────────────────────────
    def _wrap_pages(self, text):
        """Word-wrap `text` to the box width, then chop it into fixed
        LINES_PER_PAGE-line pages. Pages never overlap, so no line is
        ever shown twice; only the final page may be shorter."""
        full_lines = wrap_text(text, self.font, self.width - 120)
        step = self.LINES_PER_PAGE
        return [full_lines[i:i + step] for i in range(0, len(full_lines), step)] or [[]]

    def _load_page(self, index):
        """Put page `index` on screen and restart its typewriter reveal."""
        self._page_index = index
        self.message = ' '.join(self._pages[index])
        self.char_index = 0
        self.char_timer = 0.0

    def _start_message(self, text):
        match = self._SPEAKER_TAG_RE.match(text)
        self.speaker_name = match.group(1) if match else None
        self._pages = self._wrap_pages(text)
        self._load_page(0)

    def _get_portrait(self, name):
        """Look up (and cache) the small portrait for speaker `name`.
        Returns None if `name` has no entry in config.DIALOGUE_PORTRAITS
        or no usable sprite sheet — callers just skip drawing then."""
        if name not in self._portrait_cache:
            sprite_key = config.DIALOGUE_PORTRAITS.get(name)
            self._portrait_cache[name] = (
                load_portrait(sprite_key, self.PORTRAIT_SIZE) if sprite_key else None
            )
        return self._portrait_cache[name]

    def show(self, message, duration=2, wait_for_input=False):
        """Show one message, auto-dismissing after `duration` seconds
        unless wait_for_input is set."""
        self._start_message(message)
        self.visible = True
        self.wait_for_input = wait_for_input
        self._duration_ms = duration * 1000 if duration > 0 else 0
        self.timer = self._duration_ms

    def queue_messages(self, messages, wait_for_input=True, on_complete=None):
        """Show a list of messages back-to-back; `on_complete` fires once
        the last one is dismissed."""
        self.messages = list(messages)
        self.visible = True
        self.wait_for_input = wait_for_input
        self.on_complete = on_complete
        self._start_message(self.messages.pop(0))
        self.timer = 0

    # ── Advancing ────────────────────────────────────────────────────
    def _advance(self):
        """The current page is fully typed and the player wants to
        continue: scroll to this message's next page, or pop the next
        queued message, or close the box."""
        if self._page_index + 1 < len(self._pages):
            self._begin_scroll(self._page_index + 1)
        elif self.messages:
            self._start_message(self.messages.pop(0))
        else:
            self.hide()
            if self.on_complete:
                self.on_complete()

    def _begin_scroll(self, next_index):
        """Kick off the scroll-up animation from the current page to
        `next_index`. The outgoing lines are captured now (fully typed)
        and slide up out of the box; the incoming page stays blank
        until _finish_scroll() lands it, so its text isn't spoiled
        before its own typewriter reveal starts."""
        self._outgoing_lines = list(self._pages[self._page_index])
        self._next_page_index = next_index
        self._scrolling = True
        self._scroll_t = 0.0

    def _finish_scroll(self):
        self._scrolling = False
        self._load_page(self._next_page_index)

    def handle_event(self, event):
        if not (self.visible and self.wait_for_input and
                event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_j)):
            return
        if self._scrolling:
            self._finish_scroll()                        # key press skips straight to the new page
        elif self.char_index < len(self.message):
            self.char_index = len(self.message)           # key press reveals the rest of this page instantly
        else:
            self._advance()

    def hide(self):
        self.visible = False
        self.wait_for_input = False
        self.messages = []
        self.message = ""
        self.char_index = 0
        self.char_timer = 0.0
        self._pages = [[]]
        self._page_index = 0
        self._scrolling = False
        self.speaker_name = None

    # ── Per-frame update ─────────────────────────────────────────────
    def update(self, dt):
        if not self.visible:
            return
        if self._scrolling:
            self._scroll_t += dt
            if self._scroll_t >= self.SCROLL_DURATION:
                self._finish_scroll()
            return
        if self.char_index < len(self.message):
            self.char_timer += dt
            steps = int(self.char_timer / self.CHAR_DELAY)
            if steps:
                self.char_index = min(self.char_index + steps, len(self.message))
                self.char_timer -= steps * self.CHAR_DELAY
        elif self.timer > 0 and not self.wait_for_input:
            self.timer -= dt
            if self.timer <= 0:
                self._advance()
                if self.visible:
                    self.timer = self._duration_ms

    # ── Drawing ──────────────────────────────────────────────────────
    def _box_geometry(self, surface):
        line_h = self.font.get_height() + 4
        box_h = self.LINES_PER_PAGE * line_h + self.PAD * 2
        box_rect = pygame.Rect(50, surface.get_height() - box_h - 20, self.width - 100, box_h)
        return box_rect, line_h

    def _typed_lines(self, message, char_index):
        """Re-wrap `message` (<= LINES_PER_PAGE lines) and reveal only
        the first `char_index` characters, line by line."""
        full_lines = wrap_text(message, self.font, self.width - 120)
        chars_left = char_index
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
        return display_lines

    def draw(self, surface):
        if not self.visible:
            return
        box_rect, line_h = self._box_geometry(surface)
        pygame.draw.rect(surface, (255, 255, 255), box_rect)
        pygame.draw.rect(surface, (0, 0, 0), box_rect, 3)

        # Clip to the box interior so scrolling text is hidden as it
        # slides past the top/bottom edge instead of drawing outside it.
        prev_clip = surface.get_clip()
        surface.set_clip(box_rect)
        if self._scrolling:
            self._draw_scrolling(surface, box_rect, line_h)
        else:
            self._draw_static(surface, box_rect, line_h)
        surface.set_clip(prev_clip)

        if self.speaker_name:
            self._draw_portrait(surface, box_rect)

        if self.wait_for_input and not self._scrolling and self.char_index >= len(self.message):
            self._draw_arrow(surface, box_rect)

    def _draw_portrait(self, surface, box_rect):
        """Draw a small portrait just above the box's top-left corner —
        right above where the "[Name]" tag reads — so it's obvious at a
        glance who's talking, even once the tag has scrolled off after
        the first page."""
        portrait = self._get_portrait(self.speaker_name)
        if not portrait:
            return
        size = self.PORTRAIT_SIZE
        frame_rect = pygame.Rect(box_rect.x, box_rect.y - size - 6, size, size)
        pygame.draw.rect(surface, (255, 255, 255), frame_rect)
        surface.blit(portrait, frame_rect.topleft)
        pygame.draw.rect(surface, (0, 0, 0), frame_rect, 2)

    def _draw_static(self, surface, box_rect, line_h):
        for i, line in enumerate(self._typed_lines(self.message, self.char_index)):
            surface.blit(self.font.render(line, True, (0, 0, 0)),
                         (box_rect.x + 10, box_rect.y + self.PAD + i * line_h))

    def _draw_scrolling(self, surface, box_rect, line_h):
        """Slide the outgoing (fully-typed) lines upward and out of the
        box over SCROLL_DURATION. The incoming page is left blank here —
        it starts revealing itself only once _finish_scroll() lands it
        and the normal typewriter takes over."""
        progress = min(1.0, self._scroll_t / self.SCROLL_DURATION)
        offset = -progress * self.LINES_PER_PAGE * line_h
        for i, line in enumerate(self._outgoing_lines):
            y = box_rect.y + self.PAD + i * line_h + offset
            surface.blit(self.font.render(line, True, (0, 0, 0)), (box_rect.x + 10, y))

    def _draw_arrow(self, surface, box_rect):
        if pygame.time.get_ticks() // 400 % 2:
            cx = box_rect.right - 18
            cy = box_rect.bottom - 10
            pygame.draw.polygon(surface, (0, 0, 0), [
                (cx - 8, cy - 7), (cx + 8, cy - 7), (cx, cy + 3)
            ])


# === Trainer Card Screen ===
class TrainerCardScreen:
    NUM_BADGES = 8
    # The 8 outlined slots along the bottom of Badge.png (after it's scaled
    # to the screen): left edge of each, shared top, and outer size.
    BADGE_SLOT_X    = (81, 144, 207, 269, 332, 394, 456, 519)
    BADGE_SLOT_Y    = 398
    BADGE_SLOT_SIZE = 42
    BADGE_BG_SIZE   = 34   # black square inside the slot's outline
    BADGE_SIZE      = 30
    # (story flag, badge image) in slot order
    BADGES = (
        ('gym1_leader_defeated', 'flying_badge.png'),
        ('gym2_leader_defeated', 'earth_badge.png'),
        ('gym3_leader_defeated', 'aqua_badge.png'),
    )

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
        self._badge_imgs = []
        for _, fname in self.BADGES:
            try:
                raw = pygame.image.load(os.path.join('assets', 'Badges', fname)).convert_alpha()
                self._badge_imgs.append(self._fit_badge(raw))
            except Exception:
                self._badge_imgs.append(None)

    def _fit_badge(self, img):
        """Trim transparent padding, then scale to fit BADGE_SIZE keeping
        the aspect ratio, so every badge sits the same size in its slot."""
        r = img.get_bounding_rect()
        if r.width and r.height:
            img = img.subsurface(r)
        w, h = img.get_size()
        s = self.BADGE_SIZE / max(w, h)
        return pygame.transform.smoothscale(img, (max(1, round(w * s)), max(1, round(h * s))))

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

    def _draw_badges(self, screen):
        half = self.BADGE_SLOT_SIZE // 2
        cy = self.BADGE_SLOT_Y + half
        for i, sx in enumerate(self.BADGE_SLOT_X):
            cx = sx + half
            bg = pygame.Rect(0, 0, self.BADGE_BG_SIZE, self.BADGE_BG_SIZE)
            bg.center = (cx, cy)
            pygame.draw.rect(screen, (0, 0, 0), bg, border_radius=3)
            if i >= len(self.BADGES):
                continue
            img = self._badge_imgs[i]
            if img and self.game.story_flags.get(self.BADGES[i][0]):
                screen.blit(img, img.get_rect(center=(cx, cy)))

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

        self._draw_badges(screen)

        self._blit_text(screen, self.font_xs, "SPACE / J to close",
                        (180, 170, 150), 20, config.HEIGHT - 16)


# === Objectives Screen ===
class ObjectivesScreen:
    """Notepad with two tabs (A/D to switch):
      * Objectives — milestone battles (data.OBJECTIVES) with the play time
        each was beaten at. Times come from Game.objective_times.
      * Quests — main and side quest progress (story.QUEST_LOG): a % bar
        per group, finished quests ticked, the rest hidden as "???".
        W/S scrolls."""
    PAPER  = (252, 248, 226)
    RULE   = (160, 195, 230)
    MARGIN = (220, 90, 90)
    INK    = (40, 40, 70)
    FADED  = (150, 150, 160)
    TICK   = (60, 150, 80)
    TABS   = ("Objectives", "Quests")
    QUEST_ROW_H = 28

    def __init__(self, game):
        self.game = game
        self.font_title = game.fonts['BATTLE']
        self.font_row   = game.fonts['BAG']
        self.font_xs    = game.fonts['XS']
        self.tab = 0
        self.scroll = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k in (pygame.K_a, pygame.K_d):
            self.tab = (self.tab + (1 if k == pygame.K_d else -1)) % len(self.TABS)
            self.scroll = 0
        elif k == pygame.K_w:
            self.scroll = max(0, self.scroll - 1)
        elif k == pygame.K_s:
            self.scroll += 1   # clamped in draw, once the line count is known
        elif k in (pygame.K_SPACE, pygame.K_j, pygame.K_i, pygame.K_ESCAPE):
            self.game.pop_state()

    def _quest_lines(self):
        """[(kind, ...)] for the Quests tab: per group a 'head' (title, %),
        a 'bar' (fraction), then one 'quest' (label, done) per quest."""
        flags = self.game.story_flags
        lines = []
        for key, title in (('main', "Main Quests"), ('side', "Side Quests")):
            quests = QUEST_LOG[key]
            done = [any(flags.get(f) for f in fl) for _, fl in quests]
            frac = sum(done) / len(quests) if quests else 0.0
            if lines:
                lines.append(('gap',))
            lines.append(('head', title, frac))
            lines.append(('bar', frac))
            lines += [('quest', label, d) for (label, _), d in zip(quests, done)]
        return lines

    def _draw_quests(self, screen, pad, top):
        row_h = self.QUEST_ROW_H
        area = pygame.Rect(pad.x + 8, top, pad.width - 16, pad.bottom - 30 - top)
        lines = self._quest_lines()
        visible = area.height // row_h
        self.scroll = max(0, min(self.scroll, len(lines) - visible))
        left_x, right_x = pad.x + 24, pad.right - 24
        for i, line in enumerate(lines[self.scroll:self.scroll + visible]):
            y = area.y + i * row_h
            kind = line[0]
            if kind == 'head':
                _, title, frac = line
                head = self.font_row.render(title, True, self.MARGIN)
                screen.blit(head, (left_x, y + row_h - head.get_height() - 2))
                pct = self.font_row.render(f"{round(frac * 100)}%", True, self.INK)
                screen.blit(pct, (right_x - pct.get_width(), y + row_h - pct.get_height() - 2))
            elif kind == 'bar':
                bar = pygame.Rect(left_x, y + 7, right_x - left_x, 14)
                pygame.draw.rect(screen, (225, 220, 200), bar, border_radius=7)
                if frac := line[1]:
                    fill = bar.copy()
                    fill.width = max(14, int(bar.width * frac))
                    pygame.draw.rect(screen, self.TICK, fill, border_radius=7)
                pygame.draw.rect(screen, self.INK, bar, 1, border_radius=7)
            elif kind == 'quest':
                _, label, done = line
                box = pygame.Rect(left_x, y + 7, 14, 14)
                pygame.draw.rect(screen, self.INK if done else self.FADED, box, 2)
                if done:
                    pygame.draw.lines(screen, self.TICK, False,
                                      [(box.x + 2, box.y + 7), (box.x + 6, box.y + 11), (box.x + 15, box.y - 2)], 3)
                text = self.font_row.render(label if done else "???", True, self.INK if done else self.FADED)
                screen.blit(text, (box.right + 12, y + row_h // 2 - text.get_height() // 2))
            if kind in ('quest', 'bar'):
                pygame.draw.line(screen, self.RULE, (area.x, y + row_h), (area.right, y + row_h), 1)

        # scroll arrows
        if self.scroll > 0:
            pygame.draw.polygon(screen, self.FADED, [(pad.right - 16, top + 2), (pad.right - 22, top + 10), (pad.right - 10, top + 10)])
        if self.scroll + visible < len(lines):
            yb = area.y + visible * row_h
            pygame.draw.polygon(screen, self.FADED, [(pad.right - 16, yb), (pad.right - 22, yb - 8), (pad.right - 10, yb - 8)])
        return len(lines) > visible

    @staticmethod
    def fmt_time(seconds):
        if seconds is None:
            return "??:??"
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def draw(self, screen):
        W, H = screen.get_size()
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        screen.blit(dim, (0, 0))

        pad = pygame.Rect(0, 0, 400, 420)
        pad.center = (W // 2, H // 2 + 6)
        pygame.draw.rect(screen, (60, 50, 40), pad.move(5, 5), border_radius=6)   # shadow
        pygame.draw.rect(screen, self.PAPER, pad, border_radius=6)

        # binding strip + spiral rings along the top
        strip = pygame.Rect(pad.x, pad.y, pad.width, 26)
        pygame.draw.rect(screen, (90, 110, 150), strip, border_top_left_radius=6, border_top_right_radius=6)
        for x in range(pad.x + 22, pad.right - 10, 30):
            pygame.draw.circle(screen, self.PAPER, (x, strip.bottom - 6), 4)
            pygame.draw.rect(screen, (190, 190, 200), (x - 2, strip.y - 8, 4, 18), border_radius=2)

        # tab titles — the active one in ink and underlined
        tab_surfs = [self.font_title.render(t, True, self.INK if i == self.tab else self.FADED)
                     for i, t in enumerate(self.TABS)]
        gap = 34
        tx = pad.centerx - (sum(s.get_width() for s in tab_surfs) + gap) // 2
        for i, s in enumerate(tab_surfs):
            screen.blit(s, (tx, strip.bottom + 8))
            if i == self.tab:
                uy = strip.bottom + 8 + s.get_height() + 1
                pygame.draw.line(screen, self.MARGIN, (tx, uy), (tx + s.get_width(), uy), 3)
            tx += s.get_width() + gap

        if self.tab == 1:
            scrollable = self._draw_quests(screen, pad, strip.bottom + 50)
            hint = "A/D tab   W/S scroll   SPACE close" if scrollable else "A/D tab   SPACE / J close"
            h = self.font_xs.render(hint, True, self.FADED)
            screen.blit(h, (pad.centerx - h.get_width() // 2, pad.bottom - 22))
            return

        # ruled lines + red margin
        top = strip.bottom + 56
        line_h = 38
        rows = len(OBJECTIVES) + 1
        for i in range(rows + 1):
            y = top + i * line_h
            if y < pad.bottom - 30:
                pygame.draw.line(screen, self.RULE, (pad.x + 8, y), (pad.right - 8, y), 1)
        margin_x = pad.x + 230
        pygame.draw.line(screen, self.MARGIN, (margin_x, strip.bottom + 50), (margin_x, pad.bottom - 30), 2)

        def row_text(text, font, color, x, i, right=False):
            surf = font.render(text, True, color)
            y = top + i * line_h - surf.get_height() - 4
            screen.blit(surf, (x - surf.get_width() if right else x, y))

        left_x = pad.x + 24
        right_x = pad.right - 24
        row_text("OBJ", self.font_row, self.MARGIN, left_x, 1)
        row_text("Completion", self.font_row, self.MARGIN, right_x, 1, right=True)

        times = self.game.objective_times
        for n, (obj_id, hidden, label, _) in enumerate(OBJECTIVES):
            done = obj_id in times
            i = n + 2
            row_text(label if done else hidden, self.font_row, self.INK if done else self.FADED, left_x, i)
            row_text(self.fmt_time(times[obj_id]) if done else "--:--",
                     self.font_row, self.INK if done else self.FADED, right_x, i, right=True)
            if done:
                # a little tick in the margin
                cy = top + i * line_h - 14
                pygame.draw.lines(screen, (60, 150, 80), False,
                                  [(margin_x + 10, cy), (margin_x + 15, cy + 5), (margin_x + 24, cy - 6)], 3)

        hint = self.font_xs.render("A/D tab   SPACE / J to close", True, self.FADED)
        screen.blit(hint, (pad.centerx - hint.get_width() // 2, pad.bottom - 22))


# === Options Screen ===
class OptionsScreen:
    """i menu -> Options: sound effect / music on-off toggles and 1-10
    volume levels. Changes apply immediately and are saved to settings.json
    (see sfx.py). W/S pick a row, A/D change it, J toggles, Space/I/Esc close."""
    ROWS = [
        ('Sound Effects', 'sfx_on'),
        ('SFX Volume',    'sfx_level'),
        ('Music',         'music_on'),
        ('Music Volume',  'music_level'),
        ('Controls',      'controls'),
        ('Back',          None),
    ]
    PANEL  = (255, 255, 240)
    INK    = (0, 0, 0)
    FADED  = (150, 150, 150)
    HILITE = (200, 200, 255)
    ON_COL = (60, 160, 80)
    OFF_COL = (200, 70, 70)

    def __init__(self, game):
        self.game = game
        self.font_title = game.fonts['BATTLE']
        self.font_row   = game.fonts['BAG']
        self.font_xs    = game.fonts['XS']
        self.selected = 0

    def _change(self, key, delta):
        sfx = self.game.sfx
        s = sfx.settings
        if isinstance(s[key], bool):
            s[key] = not s[key]
        else:
            s[key] = max(1, min(10, s[key] + delta))
        sfx.apply_volumes()
        sfx.save_settings()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        label, key = self.ROWS[self.selected]
        if k == pygame.K_w:
            self.selected = (self.selected - 1) % len(self.ROWS)
        elif k == pygame.K_s:
            self.selected = (self.selected + 1) % len(self.ROWS)
        elif k in (pygame.K_a, pygame.K_d) and key and key != 'controls':
            self._change(key, -1 if k == pygame.K_a else 1)
        elif k == pygame.K_j:
            if key is None:
                self.game.pop_state()
            elif key == 'controls':
                self.game.controls_screen.reset()
                self.game.push_state('controls')
            elif isinstance(self.game.sfx.settings[key], bool):
                self._change(key, 0)
        elif k in (pygame.K_SPACE, pygame.K_i, pygame.K_ESCAPE):
            self.game.pop_state()

    def _row_enabled(self, key):
        s = self.game.sfx.settings
        if key == 'sfx_level':
            return s['sfx_on']
        if key == 'music_level':
            return s['music_on']
        return True

    def draw(self, screen):
        W, H = screen.get_size()
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        screen.blit(dim, (0, 0))

        panel = pygame.Rect(0, 0, 420, 376)
        panel.center = (W // 2, H // 2)
        pygame.draw.rect(screen, self.PANEL, panel)
        pygame.draw.rect(screen, self.INK, panel, 3)

        title = self.font_title.render("Options", True, self.INK)
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 14))

        s = self.game.sfx.settings
        row_h = 46
        top = panel.y + 66
        for i, (label, key) in enumerate(self.ROWS):
            y = top + i * row_h
            if i == self.selected:
                pygame.draw.rect(screen, self.HILITE, (panel.x + 8, y - 6, panel.width - 16, 34), border_radius=5)
            enabled = self._row_enabled(key)
            col = self.INK if enabled else self.FADED
            surf = self.font_row.render(label, True, col)
            screen.blit(surf, (panel.x + 22, y))
            if key is None or key == 'controls':
                continue
            right = panel.right - 22
            val = s[key]
            if isinstance(val, bool):
                txt = self.font_row.render("ON" if val else "OFF", True,
                                           self.ON_COL if val else self.OFF_COL)
                screen.blit(txt, (right - txt.get_width(), y))
            else:
                # ten pips + the number
                num = self.font_row.render(str(val), True, col)
                screen.blit(num, (right - num.get_width(), y))
                pip_w, gap = 10, 3
                px = right - 30 - 10 * (pip_w + gap)
                for p in range(10):
                    r = pygame.Rect(px + p * (pip_w + gap), y + 3, pip_w, 16)
                    fill = (70, 110, 220) if enabled else (170, 170, 190)
                    if p < val:
                        pygame.draw.rect(screen, fill, r)
                    pygame.draw.rect(screen, col, r, 1)

        hint = self.font_xs.render("W/S choose   A/D adjust   J toggle   SPACE close", True, (110, 110, 110))
        screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.bottom - 22))


# === Controls Screen ===
class ControlsScreen:
    """i menu -> Options -> Controls: what each key does, as a scrollable
    two-column list. Sandbox runs get an extra section for the debug keys.
    W/S scroll, Space/J/I/Esc close."""
    PAPER = (252, 248, 226)
    INK   = (40, 40, 70)
    HEAD  = (200, 70, 70)
    KEY   = (60, 110, 160)
    FADED = (150, 150, 160)

    SECTIONS = [
        ("Overworld", [
            ("W A S D",     "Walk"),
            ("Hold SPACE",  "Run"),
            ("J",           "Talk / interact / pick up / surf"),
            ("I",           "Open the menu"),
            ("+ / -",       "Zoom in / out"),
        ]),
        ("Menus & Dialogue", [
            ("W A S D",     "Move the cursor"),
            ("J",           "Confirm / advance text"),
            ("SPACE",       "Back / close"),
        ]),
        ("Battle", [
            ("W A S D",     "Pick Fight, Bag, Party, Run or Defend"),
            ("J",           "Confirm / use move"),
            ("I",           "Move info (in the Fight menu)"),
            ("SPACE",       "Leave the Fight menu"),
        ]),
    ]
    SANDBOX_SECTION = ("Sandbox", [
        ("Ctrl + Z",    "Teleport: type x y, ENTER to go"),
        ("Ctrl + D",    "Add any dino to your party"),
        ("Ctrl + Q",    "Quest debug: jump to a quest"),
        ("Ctrl + N",    "Toggle night / day"),
        ("Ctrl + E",    "Toggle eclipse"),
        ("Ctrl + L",    "Show the Lake Meridian lights"),
        ("Ctrl + M",    "Warp to / from the Lunar Planet"),
        ("Ctrl + U",    "Warp to / from the Solar Planet"),
        ("Ctrl + P",    "Move the celestial portals"),
        ("Z",           "Print tile + zone (console)"),
        ("ESC",         "Cancel teleport / dino picker"),
    ])

    def __init__(self, game):
        self.game = game
        self.font_title = game.fonts['BATTLE']
        self.font_row   = game.fonts['BAG']
        self.font_xs    = game.fonts['XS']
        self.scroll = 0

    def reset(self):
        self.scroll = 0

    def _lines(self):
        """[(kind, key, action)] where kind is 'head', 'row' or 'gap'."""
        sections = list(self.SECTIONS)
        if self.game.sandbox:
            sections.append(self.SANDBOX_SECTION)
        lines = []
        for head, rows in sections:
            if lines:
                lines.append(('gap', '', ''))
            lines.append(('head', head, ''))
            lines += [('row', k, a) for k, a in rows]
        return lines

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_w:
            self.scroll = max(0, self.scroll - 1)
        elif event.key == pygame.K_s:
            self.scroll += 1   # clamped in draw, once the line count is known
        elif event.key in (pygame.K_SPACE, pygame.K_j, pygame.K_i, pygame.K_ESCAPE):
            self.game.pop_state()

    def draw(self, screen):
        W, H = screen.get_size()
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        screen.blit(dim, (0, 0))

        pad = pygame.Rect(0, 0, 560, 430)
        pad.center = (W // 2, H // 2)
        pygame.draw.rect(screen, (60, 50, 40), pad.move(5, 5), border_radius=6)
        pygame.draw.rect(screen, self.PAPER, pad, border_radius=6)
        strip = pygame.Rect(pad.x, pad.y, pad.width, 24)
        pygame.draw.rect(screen, (60, 90, 150), strip, border_top_left_radius=6, border_top_right_radius=6)

        title = self.font_title.render("Controls", True, self.INK)
        screen.blit(title, (pad.centerx - title.get_width() // 2, strip.bottom + 6))

        lines = self._lines()
        line_h = 20
        top = strip.bottom + 46
        key_x = pad.x + 28
        act_x = pad.x + 170
        visible = (pad.bottom - 30 - top) // line_h
        self.scroll = max(0, min(self.scroll, len(lines) - visible))
        for i, (kind, key, action) in enumerate(lines[self.scroll:self.scroll + visible]):
            y = top + i * line_h
            if kind == 'head':
                screen.blit(self.font_row.render(key, True, self.HEAD), (pad.x + 20, y))
            elif kind == 'row':
                screen.blit(self.font_row.render(key, True, self.KEY), (key_x, y))
                screen.blit(self.font_row.render(action, True, self.INK), (act_x, y))

        more = len(lines) > visible
        hint = "W/S scroll   SPACE / J close" if more else "SPACE / J to close"
        h = self.font_xs.render(hint, True, self.FADED)
        screen.blit(h, (pad.centerx - h.get_width() // 2, pad.bottom - 22))


# === Rules Screen ===
class RulesScreen:
    """i menu -> Rules (only in Randomizer / Nuzlocke runs): the rules for the
    current game mode, on a scrollable notepad. W/S scroll, Space/J/I/Esc close."""
    PAPER  = (252, 248, 226)
    INK    = (40, 40, 70)
    HEAD   = (200, 70, 70)
    FADED  = (150, 150, 160)

    RANDOMIZER_RULES = [
        "Every wild dino, trainer team, starter, gift and trade is a random dino. Levels stay the same.",
        "Each route only spawns the first 6 different dinos rolled there.",
    ]
    NUZLOCKE_RULES = [
        "You start with 99 DinoPods and 99 Whitepods.",
        "Level cap: your dinos can't level past the ace of the next gym leader. At the cap, XP stops "
        "just short of the next level - knocking out that leader's last dino lets them level up again.",
        "The first 2 new dinos you meet on each route must be caught - no fighting or running. "
        "The counter at the top of wild battles shows 0/2, 1/2 or 2/2.",
        "Once a route is 2/2, its wild dinos can only be fought or run from.",
        "Duplicate Skip: a dino you've already owned doesn't count toward 2/2 and can't be caught. "
        "This applies for the whole game.",
        "Sprays and Revival Gems can only be used outside of battle.",
        "A dino that faints is sent to the box for good after the battle and can never leave it. "
        "If no dinos are left, the run is over.",
        "Legendary and story battles don't count toward 2/2.",
    ]
    ROUTES_NOTE = ("Route 1 and Town 1 count as one route; the Corn Maze, Lake Meridian, "
                   "Power Plant and each cave count as their own.")

    def __init__(self, game):
        self.game = game
        self.font_title = game.fonts['BATTLE']
        self.font_row   = game.fonts['BAG']
        self.font_xs    = game.fonts['XS']
        self.scroll = 0

    def reset(self):
        self.scroll = 0

    def _entries(self):
        """[(kind, text)] where kind is 'head', 'rule' or 'note'."""
        g = self.game
        out = []
        if g.randomizer:
            out.append(('head', "Randomizer"))
            out += [('rule', r) for r in self.RANDOMIZER_RULES]
        if g.nuzlocke:
            out.append(('head', "Nuzlocke"))
            out += [('rule', r) for r in self.NUZLOCKE_RULES]
            cap, key = g._nuzlocke_cap_info()
            if cap is not None:
                leader = TRAINER_DATA[key]['name'] + (" (rematch)" if key.endswith('_rematch') else "")
                out.append(('note', f"Current level cap: Lv {cap} - {leader}"))
            else:
                out.append(('note', "Current level cap: none - every gym is beaten!"))
        out.append(('note', self.ROUTES_NOTE))
        return out

    def _lines(self, width):
        lines = []
        for kind, text in self._entries():
            if kind == 'head':
                if lines:
                    lines.append(('gap', ''))
                lines.append(('head', text))
                continue
            wrapped = wrap_text(text, self.font_row, width - 16)
            for i, w in enumerate(wrapped):
                lines.append((kind, ("- " if kind == 'rule' and i == 0 else "  ") + w
                              if kind == 'rule' else w))
        return lines

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_w:
            self.scroll = max(0, self.scroll - 1)
        elif event.key == pygame.K_s:
            self.scroll += 1   # clamped in draw, once the line count is known
        elif event.key in (pygame.K_SPACE, pygame.K_j, pygame.K_i, pygame.K_ESCAPE):
            self.game.pop_state()

    def draw(self, screen):
        W, H = screen.get_size()
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        screen.blit(dim, (0, 0))

        pad = pygame.Rect(0, 0, 560, 430)
        pad.center = (W // 2, H // 2)
        pygame.draw.rect(screen, (60, 50, 40), pad.move(5, 5), border_radius=6)
        pygame.draw.rect(screen, self.PAPER, pad, border_radius=6)
        strip = pygame.Rect(pad.x, pad.y, pad.width, 24)
        pygame.draw.rect(screen, (150, 60, 60), strip, border_top_left_radius=6, border_top_right_radius=6)

        title = self.font_title.render("Rules", True, self.INK)
        screen.blit(title, (pad.centerx - title.get_width() // 2, strip.bottom + 6))

        lines = self._lines(pad.width - 40)
        line_h = 20
        top = strip.bottom + 46
        visible = (pad.bottom - 30 - top) // line_h
        self.scroll = max(0, min(self.scroll, len(lines) - visible))
        for i, (kind, text) in enumerate(lines[self.scroll:self.scroll + visible]):
            colour = {'head': self.HEAD, 'note': (60, 110, 160)}.get(kind, self.INK)
            screen.blit(self.font_row.render(text, True, colour), (pad.x + 20, top + i * line_h))

        more = len(lines) > visible
        hint = "W/S scroll   SPACE / J close" if more else "SPACE / J to close"
        h = self.font_xs.render(hint, True, self.FADED)
        screen.blit(h, (pad.centerx - h.get_width() // 2, pad.bottom - 22))


# === Badge Earned Screen ===
class BadgeEarnedScreen:
    """Forced full-screen badge reward — pushes its own 'badge_earned' state
    the moment it's constructed, so every gym-win handler is guaranteed to
    show it (no call site can forget to push the state). Can't be skipped
    for MIN_DISPLAY_SEC seconds; only after that does it accept input."""
    BADGE_SIZE      = 120
    FADE_IN_SEC     = 0.6
    MIN_DISPLAY_SEC = 3.0

    def __init__(self, game, badge_name, badge_path, on_dismiss=None, min_display=None):
        self.game       = game
        self.badge_name = badge_name
        self._timer     = 0.0
        if min_display is not None:
            self.MIN_DISPLAY_SEC = min_display
        self._on_dismiss = on_dismiss
        self._font_lg   = game.fonts['DIALOGUE']
        self._font_sm   = game.fonts['BATTLE2']
        try:
            raw = pygame.image.load(badge_path).convert_alpha()
            self._img = pygame.transform.scale(raw, (self.BADGE_SIZE, self.BADGE_SIZE))
        except Exception:
            self._img = None
        game.push_state('badge_earned')

    def update(self, dt):
        self._timer += dt

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self._timer >= self.MIN_DISPLAY_SEC:
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

        if self._timer >= self.MIN_DISPLAY_SEC:
            hint = self._font_sm.render("Press any key to continue", True, (200, 200, 200))
            screen.blit(hint, (cx - hint.get_width() // 2, cy + self.BADGE_SIZE // 2 + 26))
        elif self._timer > self.FADE_IN_SEC:
            wait_hint = self._font_sm.render("...", True, (160, 160, 160))
            screen.blit(wait_hint, (cx - wait_hint.get_width() // 2, cy + self.BADGE_SIZE // 2 + 26))


# === Evolution Screen ===
class EvolutionScreen:
    """Full-screen evolution sequence, DURATION seconds long and not
    skippable: fade in on the old form, flicker between old/new white
    silhouettes (speeding up), a white flash, then the new form revealed.
    The evolution itself is applied when the sequence ends, so quitting
    mid-animation never leaves a half-evolved dino. Pushes its own
    'evolution' state when constructed, like BadgeEarnedScreen."""
    DURATION    = 8.0
    FADE_IN     = 0.8    # old form fades in
    MORPH_END   = 5.6    # flicker phase runs FADE_IN → MORPH_END
    FLASH_PEAK  = 6.2    # screen whites out MORPH_END → FLASH_PEAK
    REVEAL_END  = 6.9    # white fades off the new form FLASH_PEAK → REVEAL_END
    SPRITE_SIZE = 170
    BG          = (14, 16, 34)

    def __init__(self, game, dino, target, on_done=None):
        self.game     = game
        self.dino     = dino
        self.target   = target
        self.old_name = dino['name']
        self.on_done  = on_done
        self.timer    = 0.0
        self._done    = False
        self._font    = game.fonts['DIALOGUE']
        self._font_sm = game.fonts['BATTLE2']

        old_img = dino.get('front_image') or dino.get('image')
        new_img = (game.player_dino_front_images.get(target)
                   or game.player_dino_images.get(target) or old_img)
        size = (self.SPRITE_SIZE, self.SPRITE_SIZE)
        self.old_img = pygame.transform.scale(old_img, size) if old_img else None
        self.new_img = pygame.transform.scale(new_img, size) if new_img else None
        self.old_sil = self._silhouette(self.old_img)
        self.new_sil = self._silhouette(self.new_img)
        # Sparkles drifting up through the morph: (x, start_y, speed, phase)
        self._sparkles = [(random.uniform(0.2, 0.8) * config.WIDTH,
                           random.uniform(0.3, 0.75) * config.HEIGHT,
                           random.uniform(25, 60), random.uniform(0, 6.28))
                          for _ in range(28)]
        game.push_state('evolution')

    @staticmethod
    def _silhouette(img):
        if img is None:
            return None
        return pygame.mask.from_surface(img).to_surface(
            setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))

    def update(self, dt):
        if self._done:
            return
        self.timer += dt
        if self.timer >= self.DURATION:
            self._done = True
            self.game.do_evolution(self.dino, self.target)
            self.game.pop_state()
            if self.on_done:
                self.on_done()

    def _morph_showing_new(self):
        """During the flicker phase: whether the new silhouette is up. The
        swap rate ramps from ~2/s to ~12/s, and the new form holds the
        screen for a larger share of each cycle as the phase goes on."""
        p = (self.timer - self.FADE_IN) / (self.MORPH_END - self.FADE_IN)
        p = max(0.0, min(1.0, p))
        # integral of a linearly rising frequency (2 → 12 Hz) = cycles so far
        span = self.MORPH_END - self.FADE_IN
        cycles = span * (2.0 * p + 5.0 * p * p)
        return (cycles % 1.0) < (0.25 + 0.5 * p)

    def draw(self, screen):
        t  = self.timer
        cx = config.WIDTH // 2
        cy = config.HEIGHT // 2 - 30
        screen.fill(self.BG)

        # Soft pulsing glow behind the sprite while it morphs
        if self.FADE_IN <= t < self.FLASH_PEAK:
            glow = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
            pulse = 0.5 + 0.5 * math.sin(t * 6.0)
            for r, a in ((150, 26), (115, 40), (85, 60)):
                pygame.draw.circle(glow, (170, 200, 255, int(a * (0.6 + 0.4 * pulse))), (cx, cy), r)
            screen.blit(glow, (0, 0))
            for x, y0, speed, phase in self._sparkles:
                y = y0 - (t - self.FADE_IN) * speed
                if 40 < y < config.HEIGHT - 120:
                    tw = 0.5 + 0.5 * math.sin(t * 8 + phase)
                    pygame.draw.circle(screen, (255, 255, int(180 + 75 * tw)), (int(x), int(y)), 1 + int(2 * tw))

        def blit_center(img, alpha=255):
            if img is None:
                return
            if alpha < 255:
                img = img.copy()
                img.set_alpha(alpha)
            screen.blit(img, img.get_rect(center=(cx, cy)))

        if t < self.FADE_IN:
            blit_center(self.old_img, int(255 * t / self.FADE_IN))
        elif t < self.MORPH_END:
            blit_center(self.new_sil if self._morph_showing_new() else self.old_sil)
        elif t < self.REVEAL_END:
            blit_center(self.new_img)
        else:
            # Gentle bob on the finished form
            bob = int(4 * math.sin((t - self.REVEAL_END) * 4))
            img = self.new_img
            if img is not None:
                screen.blit(img, img.get_rect(center=(cx, cy + bob)))

        # White-out flash and fade back
        flash = 0
        if self.MORPH_END <= t < self.FLASH_PEAK:
            flash = 255 * (t - self.MORPH_END) / (self.FLASH_PEAK - self.MORPH_END)
        elif self.FLASH_PEAK <= t < self.REVEAL_END:
            flash = 255 * (1 - (t - self.FLASH_PEAK) / (self.REVEAL_END - self.FLASH_PEAK))
        if flash > 0:
            white = pygame.Surface((config.WIDTH, config.HEIGHT))
            white.fill((255, 255, 255))
            white.set_alpha(int(flash))
            screen.blit(white, (0, 0))

        # Caption panel
        panel = pygame.Rect(40, config.HEIGHT - 110, config.WIDTH - 80, 80)
        pygame.draw.rect(screen, (245, 245, 245), panel)
        pygame.draw.rect(screen, (0, 0, 0), panel, 3)
        if t < self.REVEAL_END:
            lines = [f"What? {self.old_name} is evolving!"]
        else:
            lines = ["Congratulations!", f"Your {self.old_name} evolved into {self.target}!"]
        for i, line in enumerate(lines):
            surf = self._font_sm.render(line, True, (0, 0, 0))
            screen.blit(surf, (panel.x + 18, panel.y + 14 + i * 28))


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


# (mode id, label, description, playable yet?) — picked after "New Game".
# Flip the last field to True once a mode is implemented in Game.new_game.
GAME_MODES = [
    ('standard', 'Standard',
     "The classic DinoPodds adventure.", True),
    ('randomizer', 'Randomizer',
     "All encounters and battles have randomized dinos.", True),
    ('nuzlocke', 'Nuzlocke',
     "A hardcore challenge: no healing during battles, you can only catch the "
     "first 2 dinos you find on each route, every gym has a level cap, and any "
     "dino that faints is gone for good.", True),
    ('randomizer_nuzlocke', 'Randomizer Nuzlocke',
     "Randomizer and Nuzlocke combined: random dinos everywhere, under the "
     "full Nuzlocke rules.", True),
]


# Typed into the Ctrl+J+K unlock menu (case-insensitive) -> (unlocks, label)
UNLOCK_CODES = {
    'nuz':    (('nuzlocke', 'randomizer_nuzlocke'), "Nuzlocke + Randomizer Nuzlocke"),
    'random': (('randomizer',), "Randomizer"),
    'sand':   (('sandbox',), "Sandbox Mode"),
}
LOCKED_MODE_HINT = "Locked: finish the main story in Standard to unlock this mode."


# === Main Menu ===
class TitleScreen:
    """Views: 'main' (New Game / Continue / Sandbox), 'modes' (New Game mode
    picker), 'slots' (save file picker, for loading or for a new run) and
    'unlock' (Ctrl+J+K code menu)."""

    def __init__(self, game):
        self.game = game
        self.selected = 0
        self.view = 'main'
        self.mode_selected = 0
        self.slot_purpose = None     # 'load' or 'new'
        self.slot_selected = 0
        self.slots = []              # game.save_slot_summaries(), read when the picker opens
        self.confirm_overwrite = False
        self.pending_start = None    # ('mode', mode_id) or ('sandbox',) — starts once a file is picked
        self.unlock_text = ''
        self.unlock_msg = None       # (text, color) shown under the unlock code box
        self.option_font = game.fonts['DIALOGUE']
        self.hint_font = game.fonts['XS']
        self.backdrop = TitleBackdrop()
        self.logo = TitleLogo()
        self.fade_alpha = 255
        self._fading_in = True

    @property
    def options(self):
        opts = ["New Game", "Continue"]
        if self.game.is_unlocked('sandbox'):
            opts.append("Sandbox Mode")
        return opts

    def reset(self, fade_from_black=True):
        self.selected = 0
        self.view = 'main'
        self.mode_selected = 0
        self.pending_start = None
        self.confirm_overwrite = False
        self.fade_alpha = 255 if fade_from_black else 0
        self._fading_in = fade_from_black
        self.backdrop.show_sun = True

    def update(self, dt):
        dt = min(dt, 1 / 20)
        self.backdrop.update(dt)
        self.logo.update(dt)
        if self._fading_in:
            self.fade_alpha = max(0, self.fade_alpha - int(255 * dt * 1.5))
            if self.fade_alpha == 0:
                self._fading_in = False

    # ── input ─────────────────────────────────────────────────────────────

    def handle_event(self, event, has_save):
        if self._fading_in:
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.mod & pygame.KMOD_CTRL and event.key in (pygame.K_j, pygame.K_k):
            # Ctrl+J+K (either order) opens the unlock menu; a lone Ctrl+J
            # is half the chord, not a menu press.
            held = pygame.key.get_pressed()
            other = pygame.K_k if event.key == pygame.K_j else pygame.K_j
            if held[other] and self.view != 'unlock':
                self.view = 'unlock'
                self.unlock_text = ''
                self.unlock_msg = None
            return
        if self.view == 'modes':
            self._handle_mode_picker(event)
        elif self.view == 'slots':
            self._handle_slot_picker(event)
        elif self.view == 'unlock':
            self._handle_unlock(event)
        elif event.key in (pygame.K_w, pygame.K_UP):
            self.selected = (self.selected - 1) % len(self.options)
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            self.selected = (self.selected + 1) % len(self.options)
        elif event.key in (pygame.K_j, pygame.K_RETURN):
            self._confirm(has_save)

    def _confirm(self, has_save):
        opt = self.options[self.selected]
        if opt == "New Game":
            self.view = 'modes'
            self.mode_selected = 0
        elif opt == "Continue":
            if has_save:
                self.pending_start = None
                self._open_slots('load')
        elif opt == "Sandbox Mode":
            self.pending_start = ('sandbox',)
            self._open_slots('new')

    def _mode_available(self, i):
        mode_id, _, _, playable = GAME_MODES[i]
        return playable and self.game.is_unlocked(mode_id)

    def _handle_mode_picker(self, event):
        if event.key in (pygame.K_w, pygame.K_UP):
            self.mode_selected = (self.mode_selected - 1) % len(GAME_MODES)
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            self.mode_selected = (self.mode_selected + 1) % len(GAME_MODES)
        elif event.key in (pygame.K_j, pygame.K_RETURN):
            if self._mode_available(self.mode_selected):
                self.pending_start = ('mode', GAME_MODES[self.mode_selected][0])
                self._open_slots('new')
        elif event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_BACKSPACE):
            self.view = 'main'

    def _open_slots(self, purpose):
        self.slots = self.game.save_slot_summaries()
        self.slot_purpose = purpose
        self.confirm_overwrite = False
        want_filled = purpose == 'load'   # loading starts on a save, a new run on an empty file
        self.slot_selected = next((i for i, (_, s) in enumerate(self.slots)
                                   if (s is not None) == want_filled), 0)
        self.view = 'slots'

    def _handle_slot_picker(self, event):
        slot, summary = self.slots[self.slot_selected]
        if self.confirm_overwrite:
            if event.key in (pygame.K_j, pygame.K_RETURN):
                self._start(slot)
            elif event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_BACKSPACE):
                self.confirm_overwrite = False
            return
        if event.key in (pygame.K_w, pygame.K_UP):
            self.slot_selected = (self.slot_selected - 1) % len(self.slots)
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            self.slot_selected = (self.slot_selected + 1) % len(self.slots)
        elif event.key in (pygame.K_j, pygame.K_RETURN):
            if self.slot_purpose == 'load':
                if summary is not None:
                    self.view = 'main'
                    self.game.load_game(slot)
            elif summary is not None:
                self.confirm_overwrite = True
            else:
                self._start(slot)
        elif event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_BACKSPACE):
            from_modes = self.pending_start and self.pending_start[0] == 'mode'
            self.view = 'modes' if from_modes else 'main'

    def _start(self, slot):
        start, self.pending_start = self.pending_start, None
        self.view = 'main'
        self.confirm_overwrite = False
        if start[0] == 'sandbox':
            self.game.sandbox_mode(slot)
        else:
            self.game.new_game(start[1], slot)

    def _handle_unlock(self, event):
        if event.key == pygame.K_ESCAPE:
            self.view = 'main'
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            entry = UNLOCK_CODES.get(self.unlock_text.strip().lower())
            if entry:
                keys, label = entry
                new = self.game.unlock(*keys)
                text = f"{label} unlocked!" if new else f"{label} is already unlocked."
                self.unlock_msg = (text, (140, 240, 150))
            elif self.unlock_text:
                self.unlock_msg = ("Nothing happened...", (240, 140, 140))
            self.unlock_text = ''
        elif event.key == pygame.K_BACKSPACE:
            self.unlock_text = self.unlock_text[:-1]
        else:
            ch = event.unicode
            if ch and ch.isalpha() and len(self.unlock_text) < 12:
                self.unlock_text += ch

    # ── drawing ───────────────────────────────────────────────────────────

    def draw(self, screen, has_save):
        W, H = screen.get_width(), screen.get_height()
        self.backdrop.draw(screen, self.logo)

        if self.view == 'modes':
            self._draw_mode_picker(screen)
        elif self.view == 'slots':
            self._draw_slot_picker(screen)
        else:
            self._draw_main(screen, has_save, show_hint=self.view == 'main')
            if self.view == 'unlock':
                self._draw_unlock(screen)

        if self.fade_alpha > 0:
            fade = pygame.Surface((W, H))
            fade.fill((0, 0, 0))
            fade.set_alpha(self.fade_alpha)
            screen.blit(fade, (0, 0))

    def _draw_main(self, screen, has_save, show_hint=True):
        W, H = screen.get_width(), screen.get_height()
        for i, opt in enumerate(self.options):
            y = 250 + i * 52
            unavailable = opt == "Continue" and not has_save
            is_selected = i == self.selected and not unavailable

            if is_selected:
                box = pygame.Rect(W // 2 - 110, y - 10, 220, 38)
                box_bg = pygame.Surface(box.size, pygame.SRCALPHA)
                pygame.draw.rect(box_bg, (30, 18, 60, 200), box_bg.get_rect(), border_radius=7)
                screen.blit(box_bg, box.topleft)
                pygame.draw.rect(screen, (160, 130, 255), box, 2, border_radius=7)
                color = (255, 230, 80)
            elif unavailable:
                color = (65, 60, 90)
            else:
                color = (190, 178, 220)

            label = opt + ("  (No Save)" if unavailable else "")
            surf = self.option_font.render(label, True, color)
            shadow = self.option_font.render(label, True, (12, 6, 28))
            screen.blit(shadow, (W // 2 - surf.get_width() // 2 + 2, y + 2))
            screen.blit(surf, (W // 2 - surf.get_width() // 2, y))

        if show_hint:
            hint = self.hint_font.render("W/S  Navigate       J  Select", True, (150, 135, 190))
            screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 35))

    def _draw_panel(self, screen, panel):
        bg = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (22, 12, 46, 255), bg.get_rect(), border_radius=10)
        screen.blit(bg, panel.topleft)
        pygame.draw.rect(screen, (160, 130, 255), panel, 2, border_radius=10)

    def _draw_mode_picker(self, screen):
        W, H = screen.get_width(), screen.get_height()
        panel = pygame.Rect(W // 2 - 270, 140, 540, 290)
        self._draw_panel(screen, panel)

        desc_font = self.game.fonts['BAG']
        title = desc_font.render("Choose a game mode", True, (190, 178, 220))
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 10))

        row_h = 40
        top = panel.y + 40
        for i, (mode_id, label, _, playable) in enumerate(GAME_MODES):
            y = top + i * row_h
            available = self._mode_available(i)
            if i == self.mode_selected:
                box = pygame.Rect(panel.x + 14, y - 4, panel.width - 28, row_h - 4)
                pygame.draw.rect(screen, (45, 28, 90), box, border_radius=7)
                pygame.draw.rect(screen, (160, 130, 255), box, 2, border_radius=7)
                color = (255, 230, 80) if available else (150, 140, 180)
            else:
                color = (190, 178, 220) if available else (95, 88, 125)
            surf = self.game.fonts['BATTLE'].render(label, True, color)
            screen.blit(surf, (panel.x + 30, y + (row_h - 4 - surf.get_height()) // 2 - 4))
            if not available:
                tag_text = "Coming soon" if not playable else "Locked"
                tag = self.hint_font.render(tag_text, True, (150, 135, 190))
                screen.blit(tag, (panel.right - 30 - tag.get_width(), y + 8))

        # description of the highlighted mode
        mode_id, _, desc, playable = GAME_MODES[self.mode_selected]
        if playable and not self.game.is_unlocked(mode_id):
            desc = LOCKED_MODE_HINT
        div_y = top + len(GAME_MODES) * row_h + 2
        pygame.draw.line(screen, (90, 70, 150), (panel.x + 20, div_y), (panel.right - 20, div_y), 1)
        for j, line in enumerate(wrap_text(desc, desc_font, panel.width - 50)[:4]):
            surf = desc_font.render(line, True, (220, 212, 240))
            screen.blit(surf, (panel.x + 25, div_y + 10 + j * 19))

        hint = self.hint_font.render("W/S  Navigate       J  Select       Esc  Back", True, (150, 135, 190))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 35))

    def _slot_summary_text(self, s):
        if s['sandbox']:
            mode = "Sandbox"
        else:
            mode = next((label for m, label, _, _ in GAME_MODES if m == s['mode']), s['mode'])
        mins = int(s['play_time'] // 60)
        parts = [mode, f"{mins // 60}:{mins % 60:02d}",
                 f"{s['badges']} badge" + ("" if s['badges'] == 1 else "s")]
        if s['lead']:
            parts.append(s['lead'])
        if s['finished']:
            parts.append("Cleared")
        return "  |  ".join(parts)

    def _draw_slot_picker(self, screen):
        W, H = screen.get_width(), screen.get_height()
        panel = pygame.Rect(W // 2 - 270, 140, 540, 290)
        self._draw_panel(screen, panel)

        desc_font = self.game.fonts['BAG']
        heading = "Continue: choose a file" if self.slot_purpose == 'load' else "New Game: choose a file"
        title = desc_font.render(heading, True, (190, 178, 220))
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 10))

        row_h = 62
        top = panel.y + 40
        for i, (slot, s) in enumerate(self.slots):
            y = top + i * row_h
            dim = self.slot_purpose == 'load' and s is None   # nothing to continue
            if i == self.slot_selected:
                box = pygame.Rect(panel.x + 14, y - 4, panel.width - 28, row_h - 6)
                pygame.draw.rect(screen, (45, 28, 90), box, border_radius=7)
                pygame.draw.rect(screen, (160, 130, 255), box, 2, border_radius=7)
                color = (150, 140, 180) if dim else (255, 230, 80)
            else:
                color = (95, 88, 125) if dim else (190, 178, 220)
            name = self.game.fonts['BATTLE'].render(f"File {slot}", True, color)
            screen.blit(name, (panel.x + 30, y + 2))
            detail = self._slot_summary_text(s) if s else "Empty"
            surf = desc_font.render(detail, True, (95, 88, 125) if s is None else (220, 212, 240))
            screen.blit(surf, (panel.x + 30, y + 4 + name.get_height()))

        div_y = top + len(self.slots) * row_h
        pygame.draw.line(screen, (90, 70, 150), (panel.x + 20, div_y), (panel.right - 20, div_y), 1)
        slot, s = self.slots[self.slot_selected]
        if self.confirm_overwrite:
            msg, color = f"Overwrite File {slot}? It's replaced the first time you save.", (255, 200, 120)
            hint_text = "J  Overwrite       Esc  Cancel"
        else:
            if self.slot_purpose == 'new' and s is not None:
                msg = "This file is in use. Pick it to overwrite it."
            elif self.slot_purpose == 'new' and all(x is not None for _, x in self.slots):
                msg = "All files are in use."
            else:
                msg = ""
            color = (220, 212, 240)
            hint_text = "W/S  Navigate       J  Select       Esc  Back"
        if msg:
            surf = desc_font.render(msg, True, color)
            screen.blit(surf, (panel.centerx - surf.get_width() // 2, div_y + 10))

        hint = self.hint_font.render(hint_text, True, (150, 135, 190))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 35))

    def _draw_unlock(self, screen):
        W, H = screen.get_width(), screen.get_height()
        dim = pygame.Surface((W, H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        screen.blit(dim, (0, 0))
        panel = pygame.Rect(0, 0, 400, 150)
        panel.center = (W // 2, H // 2)
        self._draw_panel(screen, panel)

        title = self.game.fonts['BATTLE'].render("UNLOCK", True, (255, 230, 80))
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 12))

        field = pygame.Rect(panel.x + 40, panel.y + 52, panel.width - 80, 36)
        pygame.draw.rect(screen, (45, 28, 90), field, border_radius=6)
        pygame.draw.rect(screen, (160, 130, 255), field, 2, border_radius=6)
        text = self.option_font.render(self.unlock_text + "_", True, (255, 248, 220))
        screen.blit(text, (field.x + 10, field.centery - text.get_height() // 2))

        if self.unlock_msg:
            msg, color = self.unlock_msg
            surf = self.game.fonts['BAG'].render(msg, True, color)
            screen.blit(surf, (panel.centerx - surf.get_width() // 2, field.bottom + 14))

        hint = self.hint_font.render("Type a code       Enter  Submit       Esc  Close", True, (150, 135, 190))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 35))


class DinodexScreen:
    """W/S scroll the list, A/D pick what it's sorted by (dex number or a
    base stat), J flips greatest-first / least-first. Outside Sandbox only
    seen dinos are revealed; unseen ones always sit at the bottom of a stat
    sort, in dex order, so sorting never gives away their stats."""
    LIST_W   = 195
    IMG_SIZE = 160
    HEADER_H = 38
    SORT_H   = 26     # sort tabs above the list
    ROW_H    = 36
    SORTS = [('number', '#'), ('health', 'HP'), ('attack', 'ATK'),
             ('defense', 'DEF'), ('speed', 'SPD'), ('total', 'BST')]

    def __init__(self, game):
        self.game         = game
        self.font         = game.fonts['BATTLE2']
        self.title_font   = pygame.font.SysFont('Arial', 26, bold=True)
        self.name_font    = pygame.font.SysFont('Arial', 22, bold=True)
        self.small_font   = pygame.font.SysFont('Arial', 18)
        self.tiny_font    = pygame.font.SysFont('Arial', 15)
        self.micro_font   = pygame.font.SysFont('Arial', 12)

        # Build sorted entry list from DINODEX_DATA
        self.by_number = sorted(DINODEX_DATA.items(), key=lambda kv: kv[1]['number'])
        self.entries = list(self.by_number)
        self.selected = 0
        self.scroll   = 0
        self.sort_idx = 0          # index into SORTS
        self.descending = False    # dex # starts low-to-high; stats start high-to-low
        self._sorted_for = None    # what self.entries was last sorted against

        try:
            raw = pygame.image.load(os.path.join('assets', 'Items', 'dinopod.png')).convert_alpha()
            self.pod_icon = pygame.transform.scale(raw, (18, 18))
        except Exception:
            self.pod_icon = None

    def _list_top(self):
        return self.HEADER_H + self.SORT_H

    def _visible_rows(self):
        return (config.HEIGHT - self._list_top()) // self.ROW_H

    @staticmethod
    def _stat(name, key):
        stats = DINO_DATA.get(name, {}).get('stats', {})
        if key == 'total':
            return sum(stats.get(k, 0) for k in ('health', 'attack', 'defense', 'speed'))
        return stats.get(key, 0)

    def _resort(self, keep_selected=True):
        """Re-order self.entries for the current sort, keeping the same dino
        selected (and on screen)."""
        sel_name = self.entries[self.selected][0] if keep_selected and self.entries else None
        key = self.SORTS[self.sort_idx][0]
        if key == 'number':
            entries = list(self.by_number)
            if self.descending:
                entries.reverse()
        else:
            known = [e for e in self.by_number if self._known(e[0])]
            unknown = [e for e in self.by_number if not self._known(e[0])]
            # stable sort: ties stay in dex order
            known.sort(key=lambda e: self._stat(e[0], key), reverse=self.descending)
            entries = known + unknown
        self.entries = entries
        self._sorted_for = self._sort_signature()
        if sel_name is not None:
            self.selected = next(i for i, e in enumerate(entries) if e[0] == sel_name)
            vis = self._visible_rows()
            if not (self.scroll <= self.selected < self.scroll + vis):
                self.scroll = max(0, min(self.selected - vis // 2, len(entries) - vis))

    def _sort_signature(self):
        # seen dinos change which entries are "known", which changes stat order
        return (self.sort_idx, self.descending, self.game.sandbox, len(self.game.dinos_seen))

    def _known(self, name):
        """Sandbox shows the whole dex; every other mode only reveals dinos
        the player has seen in battle or owned (game.dinos_seen)."""
        return self.game.sandbox or name in self.game.dinos_seen

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

    def _draw_unknown(self, screen, panel_x, number):
        """Detail panel for a dino the player hasn't met yet: just its number."""
        num_surf  = self.name_font.render(f"#{number:03d}", True, (120, 180, 255))
        name_surf = self.name_font.render("???", True, (150, 150, 170))
        screen.blit(num_surf, (panel_x, self.HEADER_H + 8))
        screen.blit(name_surf, (panel_x + num_surf.get_width() + 12, self.HEADER_H + 8))

        img_y = self.HEADER_H + 68
        box = pygame.Rect(config.WIDTH - self.IMG_SIZE - 10, img_y, self.IMG_SIZE, self.IMG_SIZE)
        pygame.draw.rect(screen, (30, 30, 48), box, border_radius=8)
        pygame.draw.rect(screen, (70, 70, 100), box, 2, border_radius=8)
        q = self.title_font.render("?", True, (110, 110, 140))
        q = pygame.transform.scale(q, (q.get_width() * 3, q.get_height() * 3))
        screen.blit(q, (box.centerx - q.get_width() // 2, box.centery - q.get_height() // 2))

        desc_max_w = (config.WIDTH - self.IMG_SIZE - 30) - panel_x
        lines = wrap_text("A mystery... Encounter this dino in the wild or in battle "
                          "to record its data.", self.small_font, desc_max_w)
        for i, line in enumerate(lines):
            screen.blit(self.small_font.render(line, True, (150, 150, 170)),
                        (panel_x, img_y + i * 24))

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
        elif event.key in (pygame.K_a, pygame.K_d, pygame.K_LEFT, pygame.K_RIGHT):
            step = -1 if event.key in (pygame.K_a, pygame.K_LEFT) else 1
            self.sort_idx = (self.sort_idx + step) % len(self.SORTS)
            # stats default to greatest first, dex number to #001 first
            self.descending = self.SORTS[self.sort_idx][0] != 'number'
            self._resort()
        elif event.key == pygame.K_j:
            self.descending = not self.descending
            self._resort()
        elif event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
            return 'back'
        return None

    def _draw_sort_tabs(self, screen):
        top = self.HEADER_H + 2
        pygame.draw.rect(screen, (24, 24, 40), (0, top, self.LIST_W, self.SORT_H - 2))
        arrow = "▼" if self.descending else "▲"
        labels = [(lbl + (arrow if i == self.sort_idx else ""), i == self.sort_idx)
                  for i, (_, lbl) in enumerate(self.SORTS)]
        surfs = [self.micro_font.render(t, True, (255, 255, 255) if on else (120, 130, 160))
                 for t, on in labels]
        pad = 5
        gap = (self.LIST_W - 8 - sum(s.get_width() + pad * 2 for s in surfs)) / (len(surfs) - 1)
        x = 4
        for s, (_, on) in zip(surfs, labels):
            w = s.get_width() + pad * 2
            if on:
                pygame.draw.rect(screen, (50, 80, 140), (x, top + 3, w, self.SORT_H - 8), border_radius=4)
            screen.blit(s, (x + pad, top + (self.SORT_H - 2) // 2 - s.get_height() // 2))
            x += w + gap

    def draw(self, screen):
        screen.fill((18, 18, 28))
        if self._sorted_for != self._sort_signature():
            self._resort(keep_selected=False)

        # Header bar
        pygame.draw.rect(screen, (30, 30, 50), (0, 0, config.WIDTH, self.HEADER_H))
        pygame.draw.line(screen, (80, 80, 120), (0, self.HEADER_H), (config.WIDTH, self.HEADER_H), 2)
        screen.blit(self.title_font.render("DINODEX", True, (120, 220, 255)),
                    (10, self.HEADER_H // 2 - 13))
        hint = self.tiny_font.render("W/S scroll   A/D sort   J flip   SPACE back", True, (120, 120, 140))
        screen.blit(hint, (config.WIDTH - hint.get_width() - 10, self.HEADER_H // 2 - hint.get_height() // 2))
        seen_count = sum(1 for name, _ in self.entries if self._known(name))
        seen_surf = self.tiny_font.render(f"Seen: {seen_count} / {len(self.entries)}", True, (170, 200, 240))
        screen.blit(seen_surf, (150, self.HEADER_H // 2 - seen_surf.get_height() // 2))

        # Divider between list and detail
        pygame.draw.line(screen, (60, 60, 90), (self.LIST_W, self.HEADER_H), (self.LIST_W, config.HEIGHT), 2)

        # Sort tabs + left list
        self._draw_sort_tabs(screen)
        sort_key = self.SORTS[self.sort_idx][0]
        caught_names = {d['name'] for d in self.game.player_dinos + self.game.box_dinos}
        row_h   = self.ROW_H
        list_top = self._list_top()
        vis     = self._visible_rows()
        scroll  = max(0, min(self.scroll, max(0, len(self.entries) - vis)))
        for slot, idx in enumerate(range(scroll, min(scroll + vis, len(self.entries)))):
            name, data = self.entries[idx]
            y = list_top + slot * row_h
            is_sel = (idx == self.selected)

            bg = (50, 80, 140) if is_sel else ((30, 30, 48) if slot % 2 == 0 else (24, 24, 40))
            pygame.draw.rect(screen, bg, (0, y, self.LIST_W, row_h))

            known = self._known(name)
            # left column: dex number, or the sorted stat's value when sorting by a stat
            if sort_key == 'number' or not known:
                num_str = f"#{data['number']:03d}" if sort_key == 'number' else "---"
                num_col = (160, 200, 255) if is_sel else (100, 120, 160)
            else:
                num_str = str(self._stat(name, sort_key))
                num_col = (255, 230, 140) if is_sel else (220, 190, 110)
            num_surf = self.tiny_font.render(num_str, True, num_col)
            screen.blit(num_surf, (8, y + row_h // 2 - num_surf.get_height() // 2))

            if known:
                name_surf = self.small_font.render(name, True, (255, 255, 255) if is_sel else (200, 200, 210))
            else:
                name_surf = self.small_font.render("???", True, (170, 170, 190) if is_sel else (95, 95, 115))
            name_x = 52
            screen.blit(name_surf, (name_x, y + row_h // 2 - name_surf.get_height() // 2))

            if known and name in caught_names and self.pod_icon:
                icon_x = name_x + name_surf.get_width() + 5
                screen.blit(self.pod_icon, (icon_x, y + row_h // 2 - 9))

        # Scroll indicators for list
        if scroll > 0:
            screen.blit(self.tiny_font.render("▲", True, (160, 160, 180)), (self.LIST_W - 16, list_top + 2))
        if scroll + vis < len(self.entries):
            screen.blit(self.tiny_font.render("▼", True, (160, 160, 180)),
                        (self.LIST_W - 16, config.HEIGHT - 18))

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

        if not self._known(sel_name):
            self._draw_unknown(screen, panel_x, number)
            return

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
        bst_surf = self.small_font.render(f"Base Stat Total:  {bst}", True,
                                          (255, 230, 140) if sort_key == 'total' else (200, 220, 255))
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
            if stat_key == sort_key:   # the stat the list is sorted by
                pygame.draw.rect(screen, (255, 230, 140), (bar_x - 2, stats_y - 2, bar_w + 4, 22), 2, border_radius=4)
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
                bx = panel_x + lbl_surf.get_width() + 6
                row_start_y = stats_y
                for t, m in sorted(matchup.items()):
                    mstr = mult_fmt.get(m, f'{m}x')
                    text = f"{t.upper()} {mstr}"
                    text_color = (20, 20, 20) if t in ('light', 'lightning') else (255, 255, 255)
                    badge_surf = self.micro_font.render(text, True, text_color)
                    bw = badge_surf.get_width() + 8
                    if bx + bw > panel_x + panel_w - 20:
                        bx = panel_x
                        stats_y += 19
                        row_start_y = stats_y
                    pygame.draw.rect(screen, _tc(t), (bx, stats_y, bw, 17), border_radius=3)
                    screen.blit(badge_surf, (bx + 4, stats_y + 2))
                    bx += bw + 4
                stats_y = row_start_y + 23


class QuestDebugScreen:
    """Sandbox-only quest-jump debug menu (Ctrl+Q)."""

    def __init__(self, game):
        self.game = game
        self.font       = pygame.font.SysFont("arial", 18)
        self.small_font = pygame.font.SysFont("arial", 14)
        self.selected_index = 0
        self.scroll_offset = 0
        self.width = 460
        self.line_height = 34
        self.visible_rows = 10   # rows shown at once; the list scrolls past this

    def reset(self):
        self.selected_index = 0
        self.scroll_offset = 0

    def _keep_selection_visible(self):
        n = len(QUEST_STEPS)
        rows = min(self.visible_rows, n)
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + rows:
            self.scroll_offset = self.selected_index - rows + 1
        self.scroll_offset = max(0, min(self.scroll_offset, n - rows))

    def handle_event(self, event, game):
        if event.type != pygame.KEYDOWN:
            return None
        n = len(QUEST_STEPS)
        if event.key in (pygame.K_w, pygame.K_UP):
            self.selected_index = (self.selected_index - 1) % n
            self._keep_selection_visible()
        elif event.key in (pygame.K_s, pygame.K_DOWN):
            self.selected_index = (self.selected_index + 1) % n
            self._keep_selection_visible()
        elif event.key == pygame.K_j:
            index = self.selected_index
            step = QUEST_STEPS[index]
            game.pop_state()
            game.yes_no_prompt = YesNoPrompt(
                f"Skip to \"{step['label']}\"?", game.fonts,
                config.WIDTH, config.HEIGHT)
            game.yes_no_callback = lambda: game.apply_quest_step(index)
        elif event.key in (pygame.K_SPACE, pygame.K_ESCAPE):
            return 'back'
        return None

    def draw(self, screen):
        W, H = screen.get_width(), screen.get_height()
        x = (W - self.width) // 2
        n = len(QUEST_STEPS)
        rows = min(self.visible_rows, n)
        self._keep_selection_visible()
        panel_h = rows * self.line_height + 60
        y = (H - panel_h) // 2
        panel_rect = pygame.Rect(x, y, self.width, panel_h)
        pygame.draw.rect(screen, (255, 255, 240), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 3)

        title = self.font.render("Quest Debug (Sandbox)", True, (0, 0, 0))
        screen.blit(title, (panel_rect.x + 15, panel_rect.y + 12))
        pos = self.small_font.render(f"{self.selected_index + 1}/{n}", True, (90, 90, 90))
        screen.blit(pos, (panel_rect.right - pos.get_width() - 15, panel_rect.y + 16))

        # Scroll arrows when there are steps above/below the visible window.
        arrow_x = panel_rect.right - 22
        if self.scroll_offset > 0:
            top = panel_rect.y + 44
            pygame.draw.polygon(screen, (60, 60, 60),
                                [(arrow_x, top + 8), (arrow_x + 10, top + 8), (arrow_x + 5, top)])
        if self.scroll_offset + rows < n:
            bot = panel_rect.y + 44 + rows * self.line_height - 14
            pygame.draw.polygon(screen, (60, 60, 60),
                                [(arrow_x, bot), (arrow_x + 10, bot), (arrow_x + 5, bot + 8)])

        story_flags = self.game.story_flags
        for row, step in enumerate(QUEST_STEPS[self.scroll_offset:self.scroll_offset + rows]):
            i = self.scroll_offset + row
            row_y = panel_rect.y + 44 + row * self.line_height
            if i == self.selected_index:
                pygame.draw.rect(screen, (200, 200, 255),
                                 (panel_rect.x + 8, row_y - 3, panel_rect.width - 40, 28),
                                 border_radius=5)
            done = bool(story_flags.get(step['flag']))
            mark = "[x]" if done else "[ ]"
            color = (0, 110, 0) if done else (0, 0, 0)
            label = f"{mark} {step['label']}"
            screen.blit(self.small_font.render(label, True, color),
                        (panel_rect.x + 16, row_y + 4))

        hint = self.small_font.render("W/S scroll   J skip here   Space/Esc close", True, (90, 90, 90))
        screen.blit(hint, (panel_rect.x + 15, panel_rect.bottom - 22))


class Menu:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.selected_index = 0
        self.width = 220
        self.margin = 15
        self.line_height = 40

    @property
    def options(self):
        opts = ["Dinodex", "Party", "Items", "Trainer Card", "Objectives"]
        if self.game.game_mode != 'standard':
            opts.append("Rules")   # Randomizer / Nuzlocke runs explain their rules
        return opts + ["Save Game", "Options", "Exit to Menu"]

    def draw(self, screen):
        W = screen.get_width()
        x = W - self.width - 20
        self.selected_index = min(self.selected_index, len(self.options) - 1)

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
            elif selected == "Objectives":
                self.game.push_state('objectives')
            elif selected == "Rules":
                self.game.rules_screen.reset()
                self.game.push_state('rules')
            elif selected == "Save Game":
                self.game.save_game()
                self.game.pop_state()
            elif selected == "Options":
                self.game.options_screen.selected = 0
                self.game.push_state('options')
            elif selected == "Exit to Menu":
                self.game.pop_state()
                self.game.yes_no_prompt = YesNoPrompt(
                    "Return to main menu?", self.game.fonts,
                    config.WIDTH, config.HEIGHT)
                self.game.yes_no_callback = self.game.exit_to_title
        elif event.key == pygame.K_SPACE:
            self.game.pop_state()

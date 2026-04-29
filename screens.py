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
        self.bg = load_image(config.ENCOUNTER_BG_PATH)
        self.frames = []
        if dino_key in config.ENCOUNTER_DINOS_PATHS:
            self.frames.append(load_image(config.ENCOUNTER_DINOS_PATHS[dino_key], alpha=True))
        if dino_key + "2" in config.ENCOUNTER_DINOS_PATHS:
            self.frames.append(load_image(config.ENCOUNTER_DINOS_PATHS[dino_key + "2"], alpha=True))
        self.current_dino_surface = self.frames[0] if self.frames else None

    def draw(self, screen):
        screen.blit(self.bg, (0, 0))
        if self.current_dino_surface:
            scaled = pygame.transform.scale(self.current_dino_surface, (150, 150))
            rect = scaled.get_rect()
            rect.centerx = screen.get_width() - 157
            rect.centery = 155
            screen.blit(scaled, rect)


# === Battle UI ===
class EncounterUI:
    def __init__(self, fonts):
        self.font = fonts['DIALOGUE']
        self.small_font = fonts['BAG']
        self.smaller_font = fonts['XS']
        self.selected_option = 0
        self.actions = ["Fight", "Bag", "Party", "Run"]
        self.in_fight_menu = False
        self.move_selected = 0
        self.level_up_popup = None

    def show_level_up(self, dino, old_stats, new_stats):
        self.level_up_popup = LevelUpPopup(dino, old_stats, new_stats)

    def draw_panel(self, surface, rect, bg_color=(245, 245, 245), border_color=(0, 0, 0), border_width=3):
        pygame.draw.rect(surface, bg_color, rect)
        pygame.draw.rect(surface, border_color, rect, border_width)

    def draw_hp_bar(self, surface, x, y, width, height, percent, back_color=(200, 0, 0), front_color=(0, 200, 0)):
        pygame.draw.rect(surface, back_color, (x, y, width, height))
        pygame.draw.rect(surface, front_color, (x, y, int(width * max(0, min(1, percent))), height))

    def draw(self, surface, player_dino, enemy_dino, encounter_text, show_actions=True):
        if not show_actions:
            self.in_fight_menu = False  # can't be in fight menu while a message is showing
        screen_w, screen_h = surface.get_size()

        text_box_rect   = pygame.Rect(9, screen_h - 120, screen_w - 325, 115)
        actions_rect    = pygame.Rect(screen_w - 300, screen_h - 120, 287, 115)
        enemy_info_rect = pygame.Rect(-1, 30, 220, 65)
        player_info_rect= pygame.Rect(screen_w - 220, screen_h - 242, 220, 100)

        self.draw_panel(surface, text_box_rect)
        self.draw_panel(surface, actions_rect)
        self.draw_panel(surface, enemy_info_rect)
        self.draw_panel(surface, player_info_rect)

        # Enemy info
        surface.blit(self.small_font.render(enemy_dino['name'], True, (0, 0, 0)),
                     (enemy_info_rect.x + 10, enemy_info_rect.y + 12))
        surface.blit(self.small_font.render(f"Lv{enemy_dino['level']}", True, (0, 0, 0)),
                     (enemy_info_rect.x + 160, enemy_info_rect.y + 12))
        self.draw_hp_bar(surface, enemy_info_rect.x + 10, enemy_info_rect.y + 40, 200, 15,
                         enemy_dino['hp'] / enemy_dino['max_hp'])

        # Player info
        surface.blit(self.small_font.render(player_dino['name'], True, (0, 0, 0)),
                     (player_info_rect.x + 10, player_info_rect.y + 15))
        surface.blit(self.small_font.render(f"Lv{player_dino['level']}", True, (0, 0, 0)),
                     (player_info_rect.x + 160, player_info_rect.y + 15))
        self.draw_hp_bar(surface, player_info_rect.x + 10, player_info_rect.y + 40, 200, 15,
                         player_dino['hp'] / player_dino['max_hp'])

        # HP text
        surface.blit(
            self.small_font.render(f"{player_dino['hp']}/{player_dino['max_hp']}", True, (0, 0, 0)),
            (player_info_rect.right - 70, player_info_rect.bottom - 40)
        )

        # XP bar
        xp_progress = player_dino['xp'] / player_dino['xp_to_next']
        xp_bar_rect = pygame.Rect(player_info_rect.x + 5, player_info_rect.y + 77, 200, 8)
        pygame.draw.rect(surface, (255, 255, 255), xp_bar_rect)
        pygame.draw.rect(surface, (0, 0, 255),
                         (xp_bar_rect.x, xp_bar_rect.y, xp_bar_rect.width * xp_progress, xp_bar_rect.height))
        pygame.draw.rect(surface, (0, 0, 0), xp_bar_rect, 2)
        surface.blit(
            self.small_font.render(f"XP: {int(player_dino['xp'])}/{int(player_dino['xp_to_next'])}", True, (0, 0, 0)),
            (xp_bar_rect.x, xp_bar_rect.y - 17)
        )

        # Player dino sprite — sits directly on top of the left text box
        scaled = pygame.transform.scale(player_dino['image'], (200, 200))
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

        # Action / Fight menu — hidden while a message is displaying
        if not show_actions:
            return
        if not self.in_fight_menu:
            for i, action in enumerate(self.actions):
                color = (0, 0, 255) if i == self.selected_option else (0, 0, 0)
                surface.blit(self.font.render(action, True, color),
                             (actions_rect.x + 20 + (i % 2) * 120, actions_rect.y + 20 + (i // 2) * 50))
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
            if event.key == pygame.K_w:
                self.selected_option = (self.selected_option - 1) % len(self.actions)
            elif event.key == pygame.K_s:
                self.selected_option = (self.selected_option + 1) % len(self.actions)
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


# === Party Screen ===
class PartyScreen:
    def __init__(self, game):
        self.game = game
        self.width = 640
        self.height = 480
        self.bg_color = (30, 30, 30)
        self.font = game.fonts['BATTLE2']
        self.small_font = pygame.font.SysFont('Arial', 22)
        self.smaller_font = pygame.font.SysFont('Arial', 20)
        self.selected_index = 0
        self.mode = 'party'
        self.preview_frame = 0
        self.preview_last_switch = 0
        self.preview_selected_id = None
        self.preview_interval_ms = 250

    def reset(self):
        self.selected_index = 0

    def get_current_list(self, game):
        return game.player_dinos if self.mode == 'party' else game.box_dinos

    def handle_event(self, event, game):
        if event.type != pygame.KEYDOWN:
            return None

        in_encounter = 'encounter' in game.state_stack
        awaiting = getattr(game, "awaiting_switch", False)

        if awaiting:
            if event.key not in (pygame.K_w, pygame.K_s, pygame.K_j):
                return None
            self.mode = 'party'

        current_list = game.player_dinos if awaiting else self.get_current_list(game)
        list_length = len(current_list)

        if event.key == pygame.K_u:
            if not in_encounter and not awaiting:
                self.mode = 'box' if self.mode == 'party' else 'party'
                self.selected_index = 0
            return None

        if list_length > 0:
            if event.key == pygame.K_w:
                self.selected_index = (self.selected_index - 1) % list_length
                return None
            elif event.key == pygame.K_s:
                self.selected_index = (self.selected_index + 1) % list_length
                return None

        # Forced swap (active dino fainted)
        if awaiting and in_encounter and event.key == pygame.K_j:
            if 0 <= self.selected_index < len(game.player_dinos):
                chosen = game.player_dinos[self.selected_index]
                if chosen.get('hp', 0) <= 0:
                    game.message_box.queue_messages(
                        [f"{chosen['name']} has no HP! Choose another."], wait_for_input=True)
                    return None
                game.active_dino_index = self.selected_index
                game.awaiting_switch = False
                game.pop_state()
                game.message_box.queue_messages(
                    [f"Go, {chosen['name']}!", "What will you do?"], wait_for_input=True)
            return None

        # Voluntary swap during encounter
        if in_encounter and not awaiting and event.key == pygame.K_j:
            if 0 <= self.selected_index < len(game.player_dinos):
                chosen = game.player_dinos[self.selected_index]
                if chosen.get('hp', 0) <= 0:
                    game.message_box.queue_messages(
                        [f"{chosen['name']} has no HP! Choose another."], wait_for_input=True)
                    return None
                game.active_dino_index = self.selected_index
                game.pop_state()
                game.message_box.queue_messages(
                    [f"{chosen['name']}, I choose you!"], on_complete=game._enemy_turn)
            return None

        # Box / party transfer
        if event.key == pygame.K_o:
            if awaiting or in_encounter:
                return None
            if self.mode == 'party':
                self.move_party_to_box(game)
                self.selected_index = min(self.selected_index, max(0, len(game.player_dinos) - 1))
            else:
                self.move_box_to_party(game)
                self.selected_index = min(self.selected_index, max(0, len(game.box_dinos) - 1))
            return None

        if event.key == pygame.K_SPACE:
            if len(game.state_stack) >= 2 and game.state_stack[-2] == 'menu' and game.state_stack[0] == 'world':
                game.pop_state()
                game.pop_state()
                game.push_state('menu')
            else:
                return 'back'

        return None

    def move_party_to_box(self, game):
        if len(game.player_dinos) <= 1:
            return
        dino = game.player_dinos.pop(self.selected_index)
        game.box_dinos.append(dino)
        if not game.player_dinos:
            self.mode = 'box'
            self.selected_index = 0

    def move_box_to_party(self, game):
        if len(game.player_dinos) >= 5:
            return
        dino = game.box_dinos.pop(self.selected_index)
        game.player_dinos.append(dino)
        if not game.box_dinos:
            self.mode = 'party'
            self.selected_index = 0

    def draw(self, screen):
        screen.fill(self.bg_color)
        dinos = self.get_current_list(self.game)

        if not dinos:
            screen.blit(self.font.render("No dinos in this list", True, (255, 255, 255)), (20, 20))
            return

        if self.game.awaiting_switch:
            screen.blit(self.small_font.render("Choose replacement (use J)", True, (255, 200, 0)), (240, 0))

        box_w, box_h = 200, 70
        for i, dino in enumerate(dinos):
            rect = pygame.Rect(20, 20 + i * (box_h + 10), box_w, box_h)
            if dino.get('hp', 0) <= 0:
                color = (30, 30, 30)
            elif i == self.selected_index:
                color = (0, 150, 255)
            else:
                color = (70, 70, 70)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 2)
            screen.blit(self.font.render(dino['name'], True, (255, 255, 255)), (rect.x + 10, rect.y + 5))
            screen.blit(self.font.render(f"Lv{dino['level']}", True, (255, 255, 255)), (rect.x + 10, rect.y + 25))
            icon_scaled = pygame.transform.scale(dino['image'], (50, 50))
            screen.blit(icon_scaled, (rect.x + 140, rect.y + 5))
            if dino.get('hp', 0) <= 0:
                faint_text = self.small_font.render("Fainted", True, (255, 255, 255))
                screen.blit(faint_text, faint_text.get_rect(center=rect.center))

        self.draw_preview(screen, dinos[self.selected_index])

        # Box/Party toggle button
        label = "Box (U)" if self.mode == 'party' else "Party (U)"
        btn_rect = pygame.Rect(self.width - 100, self.height - 60, 80, 40)
        pygame.draw.rect(screen, (120, 120, 120), btn_rect)
        pygame.draw.rect(screen, (0, 0, 0), btn_rect, 2)
        btn_text = self.small_font.render(label, True, (0, 0, 0))
        screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width() // 2,
                               btn_rect.centery - btn_text.get_height() // 2))

        instruct = "Press O to send to Box" if self.mode == 'party' else "Press O to send to Party"
        screen.blit(self.small_font.render(instruct, True, (255, 255, 255)), (self.width - 240, self.height - 30))

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
            if item_name == 'DinoPod' and 'encounter' in game.state_stack:
                game.attempt_catch()
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

    def show(self, message, duration=2, wait_for_input=False):
        self.message = message
        self.visible = True
        self.wait_for_input = wait_for_input
        self.timer = duration * 1000 if duration > 0 else 0

    def queue_messages(self, messages, wait_for_input=True, on_complete=None):
        self.messages = list(messages)
        self.visible = True
        self.wait_for_input = wait_for_input
        self.on_complete = on_complete
        self.message = self.messages.pop(0)
        self.timer = 0

    def handle_event(self, event):
        if (self.visible and self.wait_for_input and
                event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_j)):
            if self.messages:
                self.message = self.messages.pop(0)
            else:
                self.hide()
                if self.on_complete:
                    self.on_complete()

    def hide(self):
        self.visible = False
        self.message = ""
        self.wait_for_input = False
        self.messages = []

    def update(self, dt):
        if self.visible and self.timer > 0 and not self.wait_for_input:
            self.timer -= dt
            if self.timer <= 0:
                if self.messages:
                    self.message = self.messages.pop(0)
                    self.timer = 0
                else:
                    self.hide()
                    if self.on_complete:
                        self.on_complete()

    def draw(self, surface):
        if not self.visible:
            return
        available_w = self.width - 120
        lines = wrap_text(self.message, self.font, available_w)
        line_h = self.font.get_height() + 4
        pad = 15
        box_h = max(80, len(lines) * line_h + pad * 2)
        box_rect = pygame.Rect(50, surface.get_height() - box_h - 20, self.width - 100, box_h)
        pygame.draw.rect(surface, (255, 255, 255), box_rect)
        pygame.draw.rect(surface, (0, 0, 0), box_rect, 3)
        for i, line in enumerate(lines):
            surface.blit(self.font.render(line, True, (0, 0, 0)),
                         (box_rect.x + 10, box_rect.y + pad + i * line_h))


# === Main Menu ===
class Menu:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont("arial", 24)
        self.selected_index = 0
        self.options = ["Party", "Items", "Save Game", "Options"]
        self.width = 220
        self.margin = 15
        self.line_height = 40

    def draw(self, screen):
        panel_rect = pygame.Rect(screen.get_width() - self.width - 20, 50, self.width, 320)
        pygame.draw.rect(screen, (255, 255, 240), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 3)
        screen.blit(self.font.render("Menu", True, (0, 0, 0)), (panel_rect.x + self.margin, panel_rect.y + 10))
        for i, option in enumerate(self.options):
            y = panel_rect.y + 50 + i * self.line_height
            if i == self.selected_index:
                pygame.draw.rect(screen, (200, 200, 255),
                                 (panel_rect.x + 5, y - 5, panel_rect.width - 10, 30), border_radius=5)
            screen.blit(self.font.render(option, True, (0, 0, 0)), (panel_rect.x + self.margin, y))

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
            elif selected == "Save Game":
                pass  # TODO: implement save
            elif selected == "Options":
                pass  # TODO: implement options
        elif event.key == pygame.K_SPACE:
            self.game.pop_state()

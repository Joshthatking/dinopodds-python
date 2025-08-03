import pygame
import config
from data import DINO_DATA, TYPE_DATA
# import game

# image loader
def load_image(path, alpha=False):
    """Load an image with optional alpha support."""
    image = pygame.image.load(path)
    return image.convert_alpha() if alpha else image.convert()


# === Encounter ===
class Encounter:
    def __init__(self, fonts, dino_key="default"):
        self.fonts = fonts
        self.bg = load_image(config.ENCOUNTER_BG_PATH)  # No alpha
        self.dino = load_image(config.ENCOUNTER_DINOS_PATHS[dino_key], alpha=True)  # Load dino sprite
        self.dino_pos = (380, 10)  # Dino position

    def draw(self, screen):
        screen.blit(self.bg, (0, 0))
        screen.blit(self.dino, self.dino_pos)  # Dino


# === Encounter UI ===
class EncounterUI:
    def __init__(self, fonts):
        self.font = fonts['DIALOGUE']
        self.small_font = fonts['BAG']
        self.selected_option = 0  # 0=Fight,1=Bag,2=Party,3=Run
        self.actions = ["Fight", "Bag", "Party", "Run"]
        # FIGHT MODE
        self.in_fight_menu = False
        self.move_selected = 0

    def draw_panel(self, surface, rect, bg_color=(245, 245, 245), border_color=(0, 0, 0), border_width=3):
        pygame.draw.rect(surface, bg_color, rect)
        pygame.draw.rect(surface, border_color, rect, border_width)

    def draw_hp_bar(self, surface, x, y, width, height, percent, back_color=(200, 0, 0), front_color=(0, 200, 0)):
        pygame.draw.rect(surface, back_color, (x, y, width, height))
        pygame.draw.rect(surface, front_color, (x, y, int(width * max(0, min(1, percent))), height))

    def draw(self, surface, player_dino, enemy_dino, encounter_text):
        screen_w, screen_h = surface.get_size()

        # Panels
        text_box_rect = pygame.Rect(9, screen_h - 120, screen_w - 325, 115)
        actions_rect = pygame.Rect(screen_w - 300, screen_h - 120, 287, 115)
        enemy_info_rect = pygame.Rect(-1, 30, 220, 65)
        player_info_rect = pygame.Rect(screen_w - 220, screen_h - 242, 220, 100) # -220 -250 250 105

        self.draw_panel(surface, text_box_rect)
        self.draw_panel(surface, actions_rect)
        self.draw_panel(surface, enemy_info_rect)
        self.draw_panel(surface, player_info_rect)

        # Enemy Info
        enemy_name = self.small_font.render(f"{enemy_dino['name']}", True, (0,0,0))
        enemy_lvl = self.small_font.render(f"Lv{enemy_dino['level']}", True, (0,0,0))
        surface.blit(enemy_name, (enemy_info_rect.x + 10, enemy_info_rect.y + 12))
        surface.blit(enemy_lvl, (enemy_info_rect.x + 160, enemy_info_rect.y + 12))
        self.draw_hp_bar(surface, enemy_info_rect.x + 10, enemy_info_rect.y + 40, 200, 15, enemy_dino['hp'] / enemy_dino['max_hp'])

        # Player Info
        player_name = self.small_font.render(f"{player_dino['name']}", True, (0, 0, 0))
        player_lvl = self.small_font.render(f"Lv{player_dino['level']}", True, (0,0,0))
        surface.blit(player_name, (player_info_rect.x + 10, player_info_rect.y + 15))
        surface.blit(player_lvl, (player_info_rect.x + 160, player_info_rect.y + 15))
        self.draw_hp_bar(surface, player_info_rect.x + 10, player_info_rect.y + 40, 200, 15, player_dino['hp'] / player_dino['max_hp'])
        # Player HP text
        player_hp_text = self.small_font.render(f"{player_dino['hp']}/{player_dino['max_hp']}", True, (0, 0, 0))
        surface.blit(player_hp_text, (player_info_rect.x + 120, player_info_rect.y + 60))  # Adjust X/Y as needed

        #Player Dino ###########
    # Draw player's active dino (bottom left above message box)
        player_dino_image = player_dino['image']
        player_dino_rect = player_dino_image.get_rect()
        player_dino_rect.bottomleft = (90, config.HEIGHT + 5)  # Adjust Y for above the message box
        scaled = pygame.transform.scale(player_dino['image'], (270, 270))
        surface.blit(scaled, player_dino_rect)


        # Text box
        wrapped_lines = self.wrap_text(encounter_text, self.font, text_box_rect.width - 40)
        for i, line in enumerate(wrapped_lines[:3]):  # limit 3 lines
            text_surface = self.font.render(line, True, (0, 0, 0))
            surface.blit(text_surface, (text_box_rect.x + 20, text_box_rect.y + 15 + i * 30))

        # Actions
        if not self.in_fight_menu:
             # --- Action Menu ---
            for i, action in enumerate(self.actions):
                color = (0,0,255) if i == self.selected_option else (0,0,0)
                action_text = self.font.render(action, True, color)
                surface.blit(action_text, (actions_rect.x + 20 + (i%2)*120, actions_rect.y + 20 + (i//2)*50))
        else:
            # Fight menu (2x2 grid for moves)
            moves = player_dino['moves']
            for i in range(4):  # Always draw 4 slots
                row = i // 2
                col = i % 2
                x = actions_rect.x + 30 + col * 130
                y = actions_rect.y + 20 + row * 40

                if i < len(moves):
                    color = (0, 0, 0) if i != self.move_selected else (200, 0, 0)
                    text = self.small_font.render(moves[i], True, color)
                else:
                    color = (150, 150, 150)
                    text = self.small_font.render("—", True, color)
                surface.blit(text, (x, y))


    def wrap_text(self, text, font, max_width):
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

    def handle_input(self, event,player_dino):
        if event.type == pygame.KEYDOWN:
            if not self.in_fight_menu:  # On main menu
                if event.key == pygame.K_w:
                    self.selected_option = (self.selected_option - 1) % len(self.actions)
                elif event.key == pygame.K_s:
                    self.selected_option = (self.selected_option + 1) % len(self.actions)
                elif event.key == pygame.K_j:
                    if self.actions[self.selected_option] == "Fight":
                        self.in_fight_menu = True  # Switch to moves
                    else:
                        return self.actions[self.selected_option]
            else:  # Inside fight menu
                if event.key == pygame.K_w:
                    self.move_selected = (self.move_selected - 2) % 4  # Up 2
                    while self.move_selected >= len(player_dino['moves']):
                        self.move_selected = (self.move_selected - 1) % 4
                elif event.key == pygame.K_s:
                    self.move_selected = (self.move_selected + 2) % 4  # Down 2
                    while self.move_selected >= len(player_dino['moves']):
                        self.move_selected = (self.move_selected - 1) % 4
                elif event.key == pygame.K_a:
                    self.move_selected = (self.move_selected - 1) % 4  # Left
                    while self.move_selected >= len(player_dino['moves']):
                        self.move_selected = (self.move_selected - 1) % 4
                elif event.key == pygame.K_d:
                    self.move_selected = (self.move_selected + 1) % 4  # Right
                    while self.move_selected >= len(player_dino['moves']):
                        self.move_selected = (self.move_selected - 1) % 4
                elif event.key == pygame.K_j:
                    if self.move_selected < len(player_dino['moves']):
                        return f"UseMove:{player_dino['moves'][self.move_selected]}"
                elif event.key == pygame.K_SPACE:  # Back to Actions
                    self.in_fight_menu = False
                elif event.key == pygame.K_i: #block i key from exiting
                    None



        # if event.type == pygame.KEYDOWN:
        #     if event.key == pygame.K_w:  # up
        #         if self.selected_option in (2, 3):
        #             self.selected_option -= 2
        #     elif event.key == pygame.K_s:  # down
        #         if self.selected_option in (0, 1):
        #             self.selected_option += 2
        #     elif event.key == pygame.K_a:  # left
        #         if self.selected_option % 2 == 1:
        #             self.selected_option -= 1
        #     elif event.key == pygame.K_d:  # right
        #         if self.selected_option % 2 == 0:
        #             self.selected_option += 1
        #     elif event.key == pygame.K_j:  # confirm
        #         return self.actions[self.selected_option]
        # return None


# === Party Screen ===


class PartyScreen:
    def __init__(self, game):
        self.game = game
        self.width = 640
        self.height = 480
        self.bg_color = (30, 30, 30)
        self.font = game.fonts['BATTLE2']
        self.small_font = pygame.font.Font(None, 24)
        self.selected_index = 0
        self.party_size = len(game.player_dinos)

    def reset(self):
        self.selected_index = 0

    def handle_event(self, event, game):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                self.selected_index = (self.selected_index - 1) % self.party_size
            elif event.key == pygame.K_s:
                self.selected_index = (self.selected_index + 1) % self.party_size
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
            elif event.key == pygame.K_j:
                if 'encounter' in game.state_stack:
                    game.active_dino_index = self.selected_index
                    return 'back'
        return None

    def draw(self, screen):
        screen.fill(self.bg_color)
        selected_dino = self.game.player_dinos[self.selected_index]


        # --- Left panel: party list ---
        box_width, box_height = 200, 70
        start_x, start_y = 20, 20
        for i, dino in enumerate(self.game.player_dinos):
            rect = pygame.Rect(start_x, start_y + i * (box_height + 10), box_width, box_height)
            color = (60, 60, 60) if i != self.selected_index else (0, 150, 255)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 2)
            name_text = self.font.render(f"{dino['name']}", True, (255, 255, 255))
            lvl_text = self.font.render(f"Lv{dino['level']}",True, (255,255,255))
            # hp_text = self.small_font.render(f"HP: {dino['hp']}/{dino['max_hp']}", True, (200, 200, 200))

            # screen.blit(name_text, (rect.x + 10, rect.y + 5)) # top left
            # screen.blit(lvl_text, (rect.x + 155, rect.y + 5)) # top right

            screen.blit(name_text, (rect.x + 10, rect.y + 5)) # top left
            screen.blit(lvl_text, (rect.x + 10, rect.y + 40)) # top right
            # screen.blit(hp_text, (rect.x + 10, rect.y + 35)) #hp text

            ### SPRITE ICON
            sprite_icon = selected_dino['image']
            sprite_icon_scaled = pygame.transform.scale(sprite_icon, (50,50))
            screen.blit(sprite_icon_scaled, (rect.x + 130, rect.y + 15))

        # --- Right top: preview box ---
        
        preview_rect = pygame.Rect(240, 20, 380, 200) # box creation
        # pygame.draw.rect(screen, (100, 200, 230), preview_rect) #hard coded color
        pygame.draw.rect(screen, (0, 0, 0), preview_rect, 3) # border - make rounded?
        selected_dino = self.game.player_dinos[self.selected_index]

                # --- Get colors for dino types ---
        types = selected_dino['type'] if isinstance(selected_dino['type'], list) else [selected_dino['type']]
        colors = [TYPE_DATA.get(t, {}).get("color", (100, 200, 230)) for t in types]

        # --- Draw background (single or dual type) ---
        if len(colors) == 1:
            pygame.draw.rect(screen, colors[0], preview_rect)
        else:
            # Split box horizontally for two colors
            top_rect = pygame.Rect(preview_rect.x, preview_rect.y, preview_rect.width, preview_rect.height // 2)
            bottom_rect = pygame.Rect(preview_rect.x, preview_rect.y + preview_rect.height // 2, preview_rect.width, preview_rect.height // 2)
            pygame.draw.rect(screen, colors[0], top_rect)
            pygame.draw.rect(screen, colors[1], bottom_rect)



        # Name
        name_surface = self.font.render(selected_dino['name'], True, (255, 255, 255))
        hp_text = self.small_font.render(f"HP: {dino['hp']}/{dino['max_hp']}", True, (255, 255, 255))
        # Format type(s) nicely: "dark" or "dark/spike"
        type_str = "/".join(types)
        type_text = self.small_font.render(type_str, True, (255, 255, 255))

        # Calculate dynamic x so it stays at the right edge with 10px padding
        type_x = preview_rect.right - type_text.get_width() - 10
        type_y = preview_rect.bottom - type_text.get_height() - 10
        name_x = preview_rect.left - name_surface.get_width() + 70
        name_y = preview_rect.top - name_surface.get_height() + 30
        hp_x = preview_rect.left - hp_text.get_width() +95
        hp_y = preview_rect.bottom - hp_text.get_height() - 10
        screen.blit(name_surface, (name_x,name_y))
        screen.blit(hp_text, (hp_x, hp_y))
        screen.blit(type_text, (type_x, type_y)) #dynamic

        # screen.blit(type_text, (preview_rect.x + 315, preview_rect.y + 175)) #hard coded
        # Sprite
        sprite = selected_dino['image']
        sprite_scaled = pygame.transform.scale(sprite, (150, 150))
        screen.blit(sprite_scaled, (preview_rect.centerx - 50, preview_rect.centery - 70))  # Main Sprite Image Center

        # --- Right bottom: stats box ---
        stats_rect = pygame.Rect(240, 230, 380, 200)
        pygame.draw.rect(screen, (50, 50, 50), stats_rect)
        pygame.draw.rect(screen, (0, 0, 0), stats_rect, 3)
        stats = [
            f"Level: {selected_dino['level']}",
            f"HP: {selected_dino['hp']}/{selected_dino['max_hp']}",
            f"Attack: {selected_dino['attack']}",
            f"Defense: {selected_dino['defense']}",
            f"Speed: {selected_dino['speed']}"
        ]
        for i, line in enumerate(stats):
            stat_text = self.small_font.render(line, True, (255, 255, 255))
            screen.blit(stat_text, (stats_rect.x + 10, stats_rect.y + 10 + i * 30))

        # --- Bottom right: "Box" button ---
        button_rect = pygame.Rect(self.width - 100, self.height - 60, 80, 40)
        pygame.draw.rect(screen, (120, 120, 120), button_rect)
        pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
        button_text = self.small_font.render("Box", True, (0, 0, 0))
        screen.blit(button_text, (button_rect.centerx - button_text.get_width() // 2,
                                  button_rect.centery - button_text.get_height() // 2))








# class PartyScreen:
#     def __init__(self, game):
#         self.game = game # store to access player_dinos, fonts, etc
#         self.width = 640
#         self.height = 480
#         self.bg_color = (90, 90, 90)
#         self.font = game.fonts['BATTLE']
#         self.selected_index = 0
#         self.party_size = len(game.player_dinos)

#     def reset(self):
#         self.selected_index = 0

# # ---- PartyScreen ----
#     def handle_event(self, event, game):
#         if event.type == pygame.KEYDOWN:
#             if event.key == pygame.K_w:
#                 self.selected_index = (self.selected_index - 1) % self.party_size
#             elif event.key == pygame.K_s:
#                 self.selected_index = (self.selected_index + 1) % self.party_size
#             elif event.key == pygame.K_SPACE:
#                 # If the state below on stack is menu and base is world, pop twice then push menu again
#                 if len(game.state_stack) >= 2 and game.state_stack[-2] == 'menu' and game.state_stack[0] == 'world':
#                     game.pop_state()  # remove 'party'
#                     game.pop_state()  # remove 'menu'
#                     game.push_state('menu')  # re-open menu on world background
#                 else:
#                     return 'back'  # default back behavior (pop current state)
#             elif event.key == pygame.K_i:
#                 # If not in encounter, quit to world (pop all to world)
#                 if 'encounter' not in game.state_stack:
#                     return 'quit'
#             elif event.key == pygame.K_j:
#                 # If coming from encounter, confirm selection and return to encounter
#                 if 'encounter' in game.state_stack:
#                     game.active_dino_index = self.selected_index
#                     return 'back'

#         return None


#     def draw(self, screen):
#         screen.fill(self.bg_color)
#         main_rect = pygame.Rect(50, 50, 275, 200)
#         pygame.draw.rect(screen, (180, 180, 180), main_rect)
#         pygame.draw.rect(screen, (0, 0, 0), main_rect, 3)

#         box_width, box_height = 250, 50
#         start_x, start_y = 350, 50
#         for i in range(self.party_size - 1):
#             rect = pygame.Rect(start_x, start_y + i * (box_height + 10), box_width, box_height)
#             color = (0, 150, 255) if (i + 1) == self.selected_index else (200, 200, 200)
#             pygame.draw.rect(screen, color, rect)
#             pygame.draw.rect(screen, (0, 0, 0), rect, 2)

#         if self.selected_index == 0:
#             pygame.draw.rect(screen, (0, 150, 255), main_rect, 5)

#         text = self.font.render("Choose a Dino? (SPACE to go back)", True, (0, 0, 0))
#         screen.blit(text, (50, 400))

#         for i, dino in enumerate(self.game.player_dinos):
#             text = f"{dino['name']} Lv{dino['level']} HP: {dino['hp']}/{dino['max_hp']}"
#             color = (255, 255, 255) if i != self.selected_index else (200, 200, 0)
#             surf = self.font.render(text, True, color)
#             screen.blit(surf, (100, 100 + i * 40))



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

        filtered_inventory = self.get_filtered_inventory()
        self.filtered_inventory = filtered_inventory
        if not filtered_inventory:
            no_items_text = self.font.render("No items collected.", True, (0, 0, 0))
            surface.blit(no_items_text, (right_rect.x + 20, right_rect.y + 40))
            return

        start = self.scroll_offset
        end = min(start + self.visible_rows, len(filtered_inventory))

        for i, (item, count) in enumerate(filtered_inventory[start:end]):
            y = right_rect.y + 20 + (i * 35)
            if start + i == self.selected_index:
                pygame.draw.rect(surface, (200, 200, 255), (right_rect.x + 5, y - 5, right_rect.width - 10, 30), border_radius=5)
            icon = self.icons[item]
            surface.blit(icon, (right_rect.x + 10, y - 10))
            text_surface = self.font.render(f"{item} x{count}", True, (0, 0, 0))
            surface.blit(text_surface, (right_rect.x + 50, y))

        desc_rect = pygame.Rect(400, 380, 220, 70)
        pygame.draw.rect(surface, (240, 240, 240), desc_rect)
        pygame.draw.rect(surface, (0, 0, 0), desc_rect, 3)

        selected_item = filtered_inventory[self.selected_index][0]
        description = self.descriptions.get(selected_item, "No description available.")
        lines = self.wrap_text(description, self.desc_font, desc_rect.width - 20)

        for i, line in enumerate(lines):
            line_surface = self.desc_font.render(line, True, (0, 0, 0))
            surface.blit(line_surface, (desc_rect.x + 10, desc_rect.y + 10 + i * 20))

    def handle_event(self, event, game):
        # Refresh filtered_inventory every time to be up to date
        if not hasattr(self, 'filtered_inventory'):
            self.filtered_inventory = [(item, count) for item, count in self.inventory.items() if count > 0]

        if len(self.filtered_inventory) == 0:
            # No items available, ignore or maybe close items screen
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return 'back'
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_j: ## new
                item_name, _ = self.filtered_inventory[self.selected_index]
                if item_name == 'DinoPod' and 'encounter' in game.state_stack:
                    game.attempt_catch()
                    return 'stay' # stay in encounter for catch attempt
            if event.key == pygame.K_w:  # Move up
                if self.selected_index > 0:
                    self.selected_index -= 1
                if self.selected_index < self.scroll_offset:
                    self.scroll_offset -= 1
            elif event.key == pygame.K_s:  # Move down
                if self.selected_index < len(self.filtered_inventory) - 1:
                    self.selected_index += 1
                if self.selected_index >= self.scroll_offset + self.visible_rows:
                    self.scroll_offset += 1
            elif event.key == pygame.K_SPACE:
                # If previous state in stack is 'menu' and base is 'world', pop twice then push 'menu'
                if len(game.state_stack) >= 2 and game.state_stack[-2] == 'menu' and game.state_stack[0] == 'world':
                    game.pop_state()  # remove 'items'
                    game.pop_state()  # remove 'menu'
                    game.push_state('menu')
                else:
                    return 'back'  # default back behavior: pop current state
            elif event.key == pygame.K_i:
                # If not opened from encounter, quit to world
                if 'encounter' not in game.state_stack:
                    return 'quit'

        return None


    def wrap_text(self, text, font, max_width):
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


# === Message Box ===
class MessageBox:
    def __init__(self, width, height, fonts):
        self.width = width
        self.height = 100
        self.font = fonts['DIALOGUE']
        self.message = ""
        self.visible = False
        self.timer = 0
        self.wait_for_input = False

    def show(self, message, duration=2, wait_for_input=False):
        self.message = message
        self.visible = True
        self.wait_for_input = wait_for_input
        self.timer = duration * 1000 if duration > 0 else 0

    def hide(self):
        self.visible = False
        self.message = ""
        self.wait_for_input = False

    def update(self, dt):
        if self.visible and self.timer > 0 and not self.wait_for_input:
            self.timer -= dt
            if self.timer <= 0:
                self.hide()

    def draw(self, surface):
        if not self.visible:
            return
        box_rect = pygame.Rect(50, surface.get_height() - self.height - 20, self.width - 100, self.height)
        pygame.draw.rect(surface, (255, 255, 255), box_rect)
        pygame.draw.rect(surface, (0, 0, 0), box_rect, 3)

        words = self.message.split()
        lines, current_line = [], ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if self.font.size(test_line)[0] < box_rect.width - 20:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for i, line in enumerate(lines):
            text_surf = self.font.render(line, True, (0, 0, 0))
            surface.blit(text_surf, (box_rect.x + 10, box_rect.y + 10 + i * 30))


# class MessageBox:
#     def __init__(self, width, height, fonts):
#         self.width = width
#         self.height = 100
#         self.font = fonts['DIALOGUE']
#         self.message = ""
#         self.visible = False
#         self.timer = 0

#     def show(self, message, duration=2):
#         self.message = message
#         self.visible = True
#         self.timer = duration * 1000 if duration > 0 else 0

#     def hide(self):
#         self.visible = False
#         self.message = ""

#     def update(self, dt):
#         if self.visible and self.timer > 0:
#             self.timer -= dt
#             if self.timer <= 0:
#                 self.hide()

#     def draw(self, surface):
#         if not self.visible:
#             return
#         box_rect = pygame.Rect(50, surface.get_height() - self.height - 20, self.width - 100, self.height)
#         pygame.draw.rect(surface, (255, 255, 255), box_rect)
#         pygame.draw.rect(surface, (0, 0, 0), box_rect, 3)

#         words = self.message.split()
#         lines, current_line = [], ""
#         for word in words:
#             test_line = f"{current_line} {word}".strip()
#             if self.font.size(test_line)[0] < box_rect.width - 20:
#                 current_line = test_line
#             else:
#                 lines.append(current_line)
#                 current_line = word
#         if current_line:
#             lines.append(current_line)

#         for i, line in enumerate(lines):
#             text_surf = self.font.render(line, True, (0, 0, 0))
#             surface.blit(text_surf, (box_rect.x + 10, box_rect.y + 10 + i * 30))

import pygame
import config
from data import *
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

        self.frames = []
        if dino_key in config.ENCOUNTER_DINOS_PATHS:
            self.frames.append(load_image(config.ENCOUNTER_DINOS_PATHS[dino_key], alpha=True))
        if dino_key + "2" in config.ENCOUNTER_DINOS_PATHS:
            self.frames.append(load_image(config.ENCOUNTER_DINOS_PATHS[dino_key + "2"], alpha=True))

        # Start with first frame as default
        self.current_dino_surface = self.frames[0] if self.frames else None

    def draw(self, screen):
        screen.blit(self.bg, (0, 0))
        # screen.blit(self.dino, self.dino_pos)  # Dino
        if self.current_dino_surface:
            screen.blit(self.current_dino_surface, self.dino_pos)


# === Encounter UI ===
class EncounterUI:
    def __init__(self, fonts):
        self.font = fonts['DIALOGUE']
        self.small_font = fonts['BAG']
        self.smaller_font = fonts['XS']
        self.selected_option = 0  # 0=Fight,1=Bag,2=Party,3=Run
        self.actions = ["Fight", "Bag", "Party", "Run"]
        # FIGHT MODE
        self.in_fight_menu = False
        self.move_selected = 0

        #LEVEL UP
        self.level_up_popup = None

    def show_level_up(self, dino, old_stats, new_stats):
        self.level_up_popup = LevelUpPopup(dino, old_stats, new_stats)

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


        # --- XP Bar ---
        xp_progress = player_dino['xp'] / player_dino['xp_to_next']
        xp_bar_rect = pygame.Rect(player_info_rect.x + 5, player_info_rect.y + 77, 200, 8)
        pygame.draw.rect(surface, (255, 255, 255), xp_bar_rect)  # Background
        pygame.draw.rect(surface, (0, 0, 255), 
            (xp_bar_rect.x, xp_bar_rect.y, xp_bar_rect.width * xp_progress, xp_bar_rect.height))  # Fill
        pygame.draw.rect(surface, (0, 0, 0), xp_bar_rect, 2)  # Outline
        xp_text = self.small_font.render(f"XP: {int(player_dino['xp'])}/{int(player_dino['xp_to_next'])}", True, (0, 0, 0))
        surface.blit(xp_text, (xp_bar_rect.x, xp_bar_rect.y - 17))


        # Player HP text
        player_hp_text = self.small_font.render(f"{player_dino['hp']}/{player_dino['max_hp']}", True, (0, 0, 0))
        surface.blit(player_hp_text,(player_info_rect.right - 70, player_info_rect.bottom -40))
        # surface.blit(player_hp_text, (player_info_rect.x + 120, player_info_rect.y + 60))  # Adjust X/Y as needed

        #Player Dino ###########
    # Draw player's active dino (bottom left above message box)
        player_dino_image = player_dino['image']
        player_dino_rect = player_dino_image.get_rect()
        player_dino_rect.bottomleft = (90, config.HEIGHT + 5)  # Adjust Y for above the message box
        scaled = pygame.transform.scale(player_dino['image'], (270, 270))
        surface.blit(scaled, player_dino_rect)


        #LEVEL UP
        if self.level_up_popup and self.level_up_popup.active:
            # Dim the background
            dim = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
            dim.fill((0, 0, 0, 150))  # Black with alpha 150 (out of 255)
            surface.blit(dim, (0, 0))

            # Draw the popup
            self.level_up_popup.draw(surface)

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
            # Fight menu (split actions_rect into 4 equal quadrants)
            moves = player_dino['moves']

            quad_width = actions_rect.width // 2
            quad_height = actions_rect.height // 2

            for i in range(4):  # 4 quadrants
                row = i // 2
                col = i % 2

                # Calculate each quadrant rect
                x = actions_rect.x + col * quad_width
                y = actions_rect.y + row * quad_height
                rect = pygame.Rect(x, y, quad_width, quad_height)

                # --- Background color based on move type ---
                if i < len(moves):
                    move_name = moves[i]
                    move_type = MOVE_DATA.get(move_name, {}).get("type", "normal")
                    bg_color = TYPE_DATA.get(move_type, {}).get("color", (200, 200, 200))
                else:
                    move_name = "—"
                    bg_color = (150, 150, 150)

                # Fill background
                pygame.draw.rect(surface, bg_color, rect)

                # Highlight selected
                border_color = (255, 255, 0) if i == self.move_selected else (0, 0, 0)
                pygame.draw.rect(surface, border_color, rect, 3)

                # Render move text centered
                text_color = (255, 255, 255) if i < len(moves) else (100, 100, 100)
                text = self.small_font.render(move_name, True, text_color)
                text_x = rect.centerx - text.get_width() // 2
                text_y = rect.centery - text.get_height() // 2
                surface.blit(text, (text_x, text_y))


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
        if self.level_up_popup and self.level_up_popup.active:
            self.level_up_popup.handle_event(event)
            return  # block normal encounter input
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
            f"{self.dino.name} leveled up!",
            f"HP: {self.old_stats['hp']} → {self.new_stats['hp']}",
            f"ATK: {self.old_stats['attack']} → {self.new_stats['attack']}",
            f"DEF: {self.old_stats['defense']} → {self.new_stats['defense']}",
            f"SPD: {self.old_stats['speed']} → {self.new_stats['speed']}"
        ]

        for i, line in enumerate(lines):
            text = font.render(line, True, (0, 0, 0))
            screen.blit(text, (popup_rect.x + 10, popup_rect.y + 10 + i * 30))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.active = False



#### LEVEL UP ==== ###
class LevelUpUI:
    def __init__(self, dino_name, old_level, new_level, old_stats, new_stats):
        self.dino_name = dino_name
        self.old_level = old_level
        self.new_level = new_level
        self.old_stats = old_stats
        self.new_stats = new_stats
        self.active = True

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.active = False

    def draw(self, surface, font):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        title = font.render(
            f"{self.dino_name} leveled up! ({self.old_level} → {self.new_level})",
            True, (255, 255, 255)
        )
        surface.blit(title, (50, 50))

        y_offset = 120
        for stat in self.old_stats.keys():
            old_val = self.old_stats[stat]
            new_val = self.new_stats[stat]
            diff = new_val - old_val
            stat_text = font.render(
                f"{stat.capitalize()}: {old_val} → {new_val} (+{diff})",
                True, (255, 255, 255)
            )
            surface.blit(stat_text, (80, y_offset))
            y_offset += 40



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
        self.mode = 'party'  # 'party' or 'box'


        #preview animation
        self.preview_frame = 0
        self.preview_last_switch = 0
        self.preview_selected_id = None
        self.preview_interval_ms = 250  # swap every 0.25s

    def reset(self):
        self.selected_index = 0

    def handle_event(self, event, game):
        if event.type != pygame.KEYDOWN:
            return None
        

            # --- BLOCK ALL OTHER INPUTS DURING FORCED SWAP ---
        if getattr(game, "awaiting_switch", False):
            # Only allow moving selection (W/S) and confirming with J
            if event.key not in [pygame.K_w, pygame.K_s, pygame.K_j]:
                return None  # ignore all other keys

        in_encounter = 'encounter' in game.state_stack
        awaiting = getattr(game, "awaiting_switch", False)

        # Force party view if forced swap is active
        if awaiting:
            self.mode = 'party'
            current_list = game.player_dinos
        else:
            current_list = self.get_current_list(game)

        list_length = len(current_list)

        # Always allow toggling modes with 'u', except during encounter/forced swap
        if event.key == pygame.K_u:
            if not in_encounter and not awaiting:
                self.mode = 'box' if self.mode == 'party' else 'party'
                new_list = self.get_current_list(game)
                self.selected_index = 0 if len(new_list) > 0 else 0
            return None  # ignore U if in encounter/forced swap

        # Navigation: only if list not empty
        if list_length > 0:
            if event.key == pygame.K_w:
                self.selected_index = (self.selected_index - 1) % list_length
                return None
            elif event.key == pygame.K_s:
                self.selected_index = (self.selected_index + 1) % list_length
                return None

        # Forced-swap selection: player must choose a living dino
        if awaiting and in_encounter and event.key == pygame.K_j:
            if 0 <= self.selected_index < len(game.player_dinos):
                chosen = game.player_dinos[self.selected_index]

                if chosen.get('hp', 0) <= 0:
                    game.message_box.queue_messages(
                        [f"{chosen['name']} has no HP! Choose another."], 
                        wait_for_input=True
                    )
                    return None

                # Perform the swap
                game.active_dino_index = self.selected_index
                game.awaiting_switch = False
                game.pop_state()  # close PartyScreen
                #switch turn
                # game.current_turn = 'player'

                # Show confirmation text AFTER party screen is visible
                game.message_box.queue_messages([f"Go, {chosen['name']}!", "What will you do?"], wait_for_input=True)
            return None  # ignore other keys during forced swap
        

                # Voluntary swap during encounter
        if in_encounter and not awaiting and event.key == pygame.K_j:
            if 0 <= self.selected_index < len(game.player_dinos):
                chosen = game.player_dinos[self.selected_index]

                if chosen.get('hp', 0) <= 0:
                    game.message_box.queue_messages(
                        [f"{chosen['name']} has no HP! Choose another."], 
                        wait_for_input=True
                    )
                    return None

                # Perform the swap
                game.active_dino_index = self.selected_index
                game.pop_state()  # close PartyScreen

                # Queue the swap message
                game.message_box.queue_messages(
                    [f"{chosen['name']}, I choose you!"],
                    on_complete=game._enemy_turn  # <-- enemy goes right after
                )
            return None


        # Normal party/box interactions (outside forced swap)
        if event.key == pygame.K_o:
            if awaiting or in_encounter:
                return None  # cannot move dinos during encounter/forced swap

            if self.mode == 'party':
                self.move_party_to_box(game)
                self.selected_index = min(self.selected_index, len(game.player_dinos) - 1) if game.player_dinos else 0
            else:
                self.move_box_to_party(game)
                self.selected_index = min(self.selected_index, len(game.box_dinos) - 1) if game.box_dinos else 0
            return None

        # Space/back handling
        if event.key == pygame.K_SPACE:
            if len(game.state_stack) >= 2 and game.state_stack[-2] == 'menu' and game.state_stack[0] == 'world':
                game.pop_state()
                game.pop_state()
                game.push_state('menu')
            else:
                return 'back'

        return None
    

    ######## Choosing new dino in encounter
    def handle_party_select(self, index):
        chosen = self.player_dinos[index]
        if chosen["hp"] <= 0:
            self.message_box.queue_messages(["That dino has fainted!"])
            return

        # swap
        self.active_dino_index = index
        self.pop_state()  # return to encounter
        self.after_swap = True  # flag to trigger enemy turn



    def get_current_list(self, game):
        if self.mode == 'party':
            return game.player_dinos
        else:
            return game.box_dinos

    def move_party_to_box(self, game):
        if len(game.player_dinos) <= 1:
            # Can't box last dino
            return
        dino = game.player_dinos.pop(self.selected_index)
        game.box_dinos.append(dino)
        # Clamp selected index so it doesn't go out of range
        self.selected_index = min(self.selected_index, len(game.player_dinos) - 1)
        # If party is empty, switch mode to box
        if len(game.player_dinos) == 0:
            self.mode = 'box'
            self.selected_index = 0

    def move_box_to_party(self, game):
        if len(game.player_dinos) >= 5:
            # Party full, can't add more
            return
        dino = game.box_dinos.pop(self.selected_index)
        game.player_dinos.append(dino)
        self.selected_index = min(self.selected_index, len(game.box_dinos) - 1)
        # If box empty after move, switch to party mode
        if len(game.box_dinos) == 0:
            self.mode = 'party'
            self.selected_index = 0

    def draw(self, screen):
        screen.fill(self.bg_color)
        dinos = self.get_current_list(self.game)

        if not dinos:
            no_dinos_text = self.font.render("No dinos in this list", True, (255, 255, 255))
            screen.blit(no_dinos_text, (20, 20))
            return
        
        #if knocked out in battle
        if self.game.awaiting_switch:
            header = self.small_font.render("Choose replacement (use J)", True, (255, 200, 0))
            screen.blit(header, (240, 0))


        # Draw left panel (list)
        box_width, box_height = 200, 70
        start_x, start_y = 20, 20
        for i, dino in enumerate(dinos):
            rect = pygame.Rect(start_x, start_y + i * (box_height + 10), box_width, box_height)
            
            # Determine color: selected, normal, or fainted
            if dino.get('hp', 0) <= 0:
                color = (30, 30, 30)  # grey for fainted
            elif i == self.selected_index:
                color = (0, 150, 255)  # selected
            else:
                color = (70, 70, 70)   # normal

            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 2)

            name_text = self.font.render(dino['name'], True, (255, 255, 255))
            lvl_text = self.font.render(f"Lv{dino['level']}", True, (255, 255, 255))
            screen.blit(name_text, (rect.x + 10, rect.y + 5))
            screen.blit(lvl_text, (rect.x + 10, rect.y + 25))

            sprite_icon = dino['image']
            sprite_icon_scaled = pygame.transform.scale(sprite_icon, (50, 50))
            screen.blit(sprite_icon_scaled, (rect.x + 140, rect.y + 5))

            # Fainted label
            if dino.get('hp', 0) <= 0:
                faint_text = self.small_font.render("Fainted", True, (255, 255, 255))
                faint_rect = faint_text.get_rect(center=rect.center)
                screen.blit(faint_text, faint_rect)

        # Draw preview of selected dino
        selected_dino = dinos[self.selected_index]
        self.draw_preview(screen, selected_dino)

        # Draw Box button only in party mode
        if self.mode == 'party':
            button_rect = pygame.Rect(self.width - 100, self.height - 60, 80, 40)
            pygame.draw.rect(screen, (120, 120, 120), button_rect)
            pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
            button_text = self.small_font.render("Box (U)", True, (0, 0, 0))
            screen.blit(button_text, (button_rect.centerx - button_text.get_width() // 2,
                                     button_rect.centery - button_text.get_height() // 2))
                # Draw party while in Box
        if self.mode == 'box':
            button_rect = pygame.Rect(self.width - 100, self.height - 60, 80, 40)
            pygame.draw.rect(screen, (120, 120, 120), button_rect)
            pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
            button_text = self.small_font.render("Party (U)", True, (0, 0, 0))
            screen.blit(button_text, (button_rect.centerx - button_text.get_width() // 2,
                                     button_rect.centery - button_text.get_height() // 2))

        # Show instructions for moving dinos
        if self.mode == 'party':
            instruct_text = self.small_font.render("Press O to send to Box", True, (255, 255, 255))
        else:
            instruct_text = self.small_font.render("Press O to send to Party", True, (255, 255, 255))
        screen.blit(instruct_text, (self.width - 240, self.height - 30))




    def draw_preview(self, screen, dino):
        preview_rect = pygame.Rect(240, 20, 380, 200)
        pygame.draw.rect(screen, (0, 0, 0), preview_rect, 3)

        # Background by type(s)
        types = dino['type'] if isinstance(dino['type'], list) else [dino['type']]
        colors = [TYPE_DATA.get(t, {}).get("color", (100, 200, 230)) for t in types]
        if len(colors) == 1:
            pygame.draw.rect(screen, colors[0], preview_rect)
        else:
            top_rect = pygame.Rect(preview_rect.x, preview_rect.y, preview_rect.width, preview_rect.height // 2)
            bottom_rect = pygame.Rect(preview_rect.x, preview_rect.y + preview_rect.height // 2,
                                    preview_rect.width, preview_rect.height // 2)
            pygame.draw.rect(screen, colors[0], top_rect)
            pygame.draw.rect(screen, colors[1], bottom_rect)

        # Text
        name_surface = self.font.render(dino['name'], True, (255, 255, 255))
        hp_text = self.small_font.render(f"HP: {dino['hp']}/{dino['max_hp']}", True, (255, 255, 255))
        type_str = "/".join(types)
        type_text = self.small_font.render(type_str, True, (255, 255, 255))

        type_x = preview_rect.right - type_text.get_width() - 10
        type_y = preview_rect.bottom - type_text.get_height() - 10
        name_x = preview_rect.left + 10
        name_y = preview_rect.top + 10
        hp_x = preview_rect.right - hp_text.get_width() - 10
        hp_y = preview_rect.top + 10

        screen.blit(name_surface, (name_x, name_y))
        screen.blit(hp_text, (hp_x, hp_y))
        screen.blit(type_text, (type_x, type_y))

        # XP Bar
        current_xp = dino.get("xp", 0)
        xp_to_next = max(1, dino.get("xp_to_next", 1))
        fill_ratio = min(current_xp / xp_to_next, 1)

        xp_bar_width = preview_rect.width - 250
        xp_bar_height = 15
        xp_bar_x = preview_rect.x + 5
        xp_bar_y = preview_rect.bottom - xp_bar_height - 3

        xp_text = self.smaller_font.render(f"XP: {int(current_xp)}/{int(xp_to_next)}", True, (255, 255, 255))
        screen.blit(xp_text, (xp_bar_x + 2, xp_bar_y - 23))

        pygame.draw.rect(screen, (255, 255, 255), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height))
        pygame.draw.rect(screen, (0, 100, 255), (xp_bar_x, xp_bar_y, int(xp_bar_width * fill_ratio), xp_bar_height))
        pygame.draw.rect(screen, (0, 0, 0), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height), 2)

        # --- Preview animation ---
        now = pygame.time.get_ticks()
        sel_id = dino.get("name")

        # reset animation if selection changed
        if self.preview_selected_id != sel_id:
            self.preview_selected_id = sel_id
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

        # Sprite
        sprite_scaled = pygame.transform.scale(frame_img, (150, 150))
        screen.blit(sprite_scaled, (preview_rect.centerx - 50, preview_rect.centery - 70))










    # def draw_preview(self, screen, dino):
    #     preview_rect = pygame.Rect(240, 20, 380, 200)
    #     pygame.draw.rect(screen, (0, 0, 0), preview_rect, 3)

    #     types = dino['type'] if isinstance(dino['type'], list) else [dino['type']]
    #     colors = [TYPE_DATA.get(t, {}).get("color", (100, 200, 230)) for t in types]

    #     if len(colors) == 1:
    #         pygame.draw.rect(screen, colors[0], preview_rect)
    #     else:
    #         top_rect = pygame.Rect(preview_rect.x, preview_rect.y, preview_rect.width, preview_rect.height // 2)
    #         bottom_rect = pygame.Rect(preview_rect.x, preview_rect.y + preview_rect.height // 2, preview_rect.width,
    #                                   preview_rect.height // 2)
    #         pygame.draw.rect(screen, colors[0], top_rect)
    #         pygame.draw.rect(screen, colors[1], bottom_rect)

    #     name_surface = self.font.render(dino['name'], True, (255, 255, 255))
    #     hp_text = self.small_font.render(f"HP: {dino['hp']}/{dino['max_hp']}", True, (255, 255, 255))
    #     type_str = "/".join(types)
    #     type_text = self.small_font.render(type_str, True, (255, 255, 255))

    #     type_x = preview_rect.right - type_text.get_width() - 10
    #     type_y = preview_rect.bottom - type_text.get_height() - 10
    #     name_x = preview_rect.left + 10
    #     name_y = preview_rect.top + 10
    #     hp_x = preview_rect.right - hp_text.get_width() - 10
    #     hp_y = preview_rect.top + 10

    #     screen.blit(name_surface, (name_x, name_y))
    #     screen.blit(hp_text, (hp_x, hp_y))
    #     screen.blit(type_text, (type_x, type_y))

    #     # XP Bar
    #     current_xp = dino.get("xp", 0)
    #     xp_to_next = dino.get("xp_to_next", 1)
    #     fill_ratio = min(current_xp / xp_to_next, 1)

    #     xp_bar_width = preview_rect.width - 250
    #     xp_bar_height = 15
    #     xp_bar_x = preview_rect.x + 5
    #     xp_bar_y = preview_rect.bottom - xp_bar_height - 3

    #     xp_text = self.smaller_font.render(f"XP: {int(current_xp)}/{int(xp_to_next)}", True, (255, 255, 255))
    #     screen.blit(xp_text, (xp_bar_x + 2, xp_bar_y - 23))

    #     pygame.draw.rect(screen, (255, 255, 255), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height))
    #     pygame.draw.rect(screen, (0, 100, 255), (xp_bar_x, xp_bar_y, int(xp_bar_width * fill_ratio), xp_bar_height))
    #     pygame.draw.rect(screen, (0, 0, 0), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height), 2)


    #     #### preview animation
    #     selected_dino = dino[self.selected_index]  # or the arg to draw_preview
    #     now = pygame.time.get_ticks()

    #     # reset animation if selection changed
    #     sel_id = selected_dino.get("name")
    #     if self.preview_selected_id != sel_id:
    #         self.preview_selected_id = sel_id
    #         self.preview_frame = 0
    #         self.preview_last_switch = now

    #     # advance the frame if we have multiple frames
    #     if "frames" in selected_dino and len(selected_dino["frames"]) > 1:
    #         if now - self.preview_last_switch >= self.preview_interval_ms:
    #             self.preview_frame = (self.preview_frame + 1) % len(selected_dino["frames"])
    #             self.preview_last_switch = now
    #         frame_img = selected_dino["frames"][self.preview_frame]
    #     else:
    #         frame_img = selected_dino["image"]

    #     #SPRITE
    #     # blit (reuse your existing preview_rect placement) 
    #     sprite_scaled = pygame.transform.scale(frame_img, (150, 150))
    #     screen.blit(sprite_scaled, (preview_rect.centerx - 50, preview_rect.centery - 70))

        # Sprite
        # sprite = dino['image']
        # sprite_scaled = pygame.transform.scale(sprite, (150, 150))
        # screen.blit(sprite_scaled, (preview_rect.centerx - 50, preview_rect.centery - 70))

        # Stats box
        stats_rect = pygame.Rect(240, 230, 380, 240)
        pygame.draw.rect(screen, (50, 50, 50), stats_rect)
        pygame.draw.rect(screen, (0, 0, 0), stats_rect, 3)

        stats = [
            f"HP: {dino['max_hp']}",
            f"Attack: {dino['attack']}",
            f"Defense: {dino['defense']}",
            f"Speed: {dino['speed']}"
        ]
        for i, line in enumerate(stats):
            stat_text = self.small_font.render(line, True, (255, 255, 255))
            screen.blit(stat_text, (stats_rect.x + 10, stats_rect.y + 10 + i * 25))

        # Moves section
        move_box_width = stats_rect.width - 200
        move_box_height = 25
        move_start_x = stats_rect.x + 10
        move_start_y = stats_rect.y + 120
        move_spacing = 5

        for i, move in enumerate(dino['moveset']):
            move_name = move['name']
            move_type = move['type']
            move_damage = move['damage']
            move_accuracy = move['accuracy']

            move_color = TYPE_DATA.get(move_type, {}).get("color", (200, 200, 200))

            move_rect = pygame.Rect(
                move_start_x,
                move_start_y + i * (move_box_height + move_spacing),
                move_box_width,
                move_box_height
            )
            pygame.draw.rect(screen, move_color, move_rect)
            pygame.draw.rect(screen, (0, 0, 0), move_rect, 2)

            move_text = self.smaller_font.render(move_name, True, (255, 255, 255))
            move_stats = self.smaller_font.render(f"{move_damage}/{move_accuracy}", True, (255, 255, 255))

            screen.blit(move_text, (move_rect.x + 8, move_rect.y))
            screen.blit(move_stats, (move_rect.x + 125, move_rect.y))


# class PartyScreen:
#     def __init__(self, game):
#         self.game = game
#         self.width = 640
#         self.height = 480
#         self.bg_color = (30, 30, 30)
#         self.font = game.fonts['BATTLE2']
#         self.small_font = pygame.font.SysFont('Arial', 22)
#         self.smaller_font = pygame.font.SysFont('Arial', 20)
#         self.selected_index = 0
#         self.mode = 'party'  # or 'box'

#         # self.party_size = len(game.player_dinos)

#     def reset(self):
#         self.selected_index = 0

#     def handle_event(self, event, game):
#         if event.type == pygame.KEYDOWN:
#             if event.key == pygame.K_w:
#                 self.selected_index = (self.selected_index - 1) % len(game.player_dinos) #self.party_size
#             elif event.key == pygame.K_s:
#                 self.selected_index = (self.selected_index + 1) % len(game.player_dinos) #self.party_size
#             elif event.key == pygame.K_SPACE:
#                 if self.mode == 'party':
#                                     #BOX
#                     if event.key == pygame.K_u:
#                         self.mode == 'box'
#                         self.selected_index = 0
#                         return

#                     # box_button_rect = pygame.Rect(self.width - 100, self.height - 60, 80, 40)
#                     if len(game.state_stack) >= 2 and game.state_stack[-2] == 'menu' and game.state_stack[0] == 'world':
#                         game.pop_state()
#                         game.pop_state()
#                         game.push_state('menu')
#                     else:
#                         return 'back'
#                 elif event.key == pygame.K_i:
#                     if 'encounter' not in game.state_stack:
#                         return 'quit'
#                 elif event.key == pygame.K_j:
#                     if 'encounter' in game.state_stack:
#                         game.active_dino_index = self.selected_index
#                         return 'back'
#                 elif self.mode == 'box':
#                                 # Back to party from box
#                                 self.mode = 'party'
#                                 self.selected_index = 0
#                                 return None
#                 elif event.key == pygame.K_o:  # interact key
#                             self.toggle_dino_box(game)

#                 return None

#     def draw(self, screen):
#         screen.fill(self.bg_color)
#         selected_dino = self.game.player_dinos[self.selected_index]


#         # --- Left panel: party list ---
#         box_width, box_height = 200, 70
#         start_x, start_y = 20, 20
#         for i, dino in enumerate(self.game.player_dinos):
#             rect = pygame.Rect(start_x, start_y + i * (box_height + 10), box_width, box_height)
#             color = (70, 70, 70) if i != self.selected_index else (0, 150, 255)
#             pygame.draw.rect(screen, color, rect)
#             pygame.draw.rect(screen, (0, 0, 0), rect, 2)
#             name_text = self.font.render(f"{dino['name']}", True, (255, 255, 255))
#             lvl_text = self.font.render(f"Lv{dino['level']}",True, (255,255,255))
#             # hp_text = self.small_font.render(f"HP: {dino['hp']}/{dino['max_hp']}", True, (200, 200, 200))

#             # screen.blit(name_text, (rect.x + 10, rect.y + 5)) # top left
#             # screen.blit(lvl_text, (rect.x + 155, rect.y + 5)) # top right

#             screen.blit(name_text, (rect.x + 10, rect.y + 5)) # top left
#             screen.blit(lvl_text, (rect.x + 10, rect.y + 25)) # top right
#             # screen.blit(hp_text, (rect.x + 10, rect.y + 45)) #hp text

#             ### SPRITE ICON
#             sprite_icon = dino['image']  # <-- use the current dino in the loop
#             sprite_icon_scaled = pygame.transform.scale(sprite_icon, (50,50))
#             screen.blit(sprite_icon_scaled, (rect.x + 140, rect.y + 5))

#         # --- Right top: preview box ---
        
#         preview_rect = pygame.Rect(240, 20, 380, 200) # box creation
#         # pygame.draw.rect(screen, (100, 200, 230), preview_rect) #hard coded color
#         pygame.draw.rect(screen, (0, 0, 0), preview_rect, 3) # border - make rounded?
#         selected_dino = self.game.player_dinos[self.selected_index]

#                 # --- Get colors for dino types ---
#         types = selected_dino['type'] if isinstance(selected_dino['type'], list) else [selected_dino['type']]
#         colors = [TYPE_DATA.get(t, {}).get("color", (100, 200, 230)) for t in types]

#         # --- Draw background (single or dual type) ---
#         if len(colors) == 1:
#             pygame.draw.rect(screen, colors[0], preview_rect)
#         else:
#             # Split box horizontally for two colors
#             top_rect = pygame.Rect(preview_rect.x, preview_rect.y, preview_rect.width, preview_rect.height // 2)
#             bottom_rect = pygame.Rect(preview_rect.x, preview_rect.y + preview_rect.height // 2, preview_rect.width, preview_rect.height // 2)
#             pygame.draw.rect(screen, colors[0], top_rect)
#             pygame.draw.rect(screen, colors[1], bottom_rect)



#         # Name
#         name_surface = self.font.render(selected_dino['name'], True, (255, 255, 255))
#         hp_text = self.small_font.render(f"HP: {selected_dino['hp']}/{selected_dino['max_hp']}", True, (255, 255, 255))
#         # Format type(s) nicely: "dark" or "dark/spike"
#         type_str = "/".join(types)
#         type_text = self.small_font.render(type_str, True, (255, 255, 255))

#         # Calculate dynamic x so it stays at the right edge with 10px padding
#         type_x = preview_rect.right - type_text.get_width() - 10
#         type_y = preview_rect.bottom - type_text.get_height() - 10
#         name_x = preview_rect.left + 10
#         name_y = preview_rect.top + 10
#         hp_x = preview_rect.right - hp_text.get_width() - 10
#         hp_y = preview_rect.top + 10
#         screen.blit(name_surface, (name_x,name_y))
#         screen.blit(hp_text, (hp_x, hp_y))
#         screen.blit(type_text, (type_x, type_y)) #dynamic

#         # # --- XP BAR ---
#         current_xp = selected_dino.get("xp", 0)
#         xp_to_next = selected_dino.get("xp_to_next", 1)
#         fill_ratio = min(current_xp / xp_to_next, 1)  # Clamp between 0-1

#         xp_bar_width = preview_rect.width - 250  # padding inside preview box
#         xp_bar_height = 15
#         xp_bar_x = preview_rect.x + 5
#         xp_bar_y = preview_rect.bottom - xp_bar_height - 3

#         xp_text = self.smaller_font.render(f"XP: {int(current_xp)}/{int(xp_to_next)}", True, (255, 255, 255))
#         screen.blit(xp_text, (xp_bar_x + 2 , xp_bar_y - 23))

#         # Draw background (white)
#         pygame.draw.rect(screen, (255, 255, 255), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height))
#         # Draw filled part (blue)
#         pygame.draw.rect(screen, (0, 100, 255), (xp_bar_x, xp_bar_y, int(xp_bar_width * fill_ratio), xp_bar_height))
#         # Outline
#         pygame.draw.rect(screen, (0, 0, 0), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height), 2)

#         # screen.blit(type_text, (preview_rect.x + 315, preview_rect.y + 175)) #hard coded
#         # Sprite
#         sprite = selected_dino['image']
#         sprite_scaled = pygame.transform.scale(sprite, (150, 150))
#         screen.blit(sprite_scaled, (preview_rect.centerx - 50, preview_rect.centery - 70))  # Main Sprite Image Center


#         # --- Right bottom: stats box ---
#         stats_rect = pygame.Rect(240, 230, 380, 240)
#         pygame.draw.rect(screen, (50, 50, 50), stats_rect)
#         pygame.draw.rect(screen, (0, 0, 0), stats_rect, 3)

#         # Stats section
#         stats = [
#             f"HP: {selected_dino['max_hp']}",
#             f"Attack: {selected_dino['attack']}",
#             f"Defense: {selected_dino['defense']}",
#             f"Speed: {selected_dino['speed']}"
#         ]
#         for i, line in enumerate(stats):
#             stat_text = self.small_font.render(line, True, (255, 255, 255))
#             screen.blit(stat_text, (stats_rect.x + 10, stats_rect.y + 10 + i * 25))

#         # --- Moves section (inside same box) ---
#         move_box_width = stats_rect.width - 200
#         move_box_height = 25
#         move_start_x = stats_rect.x + 10
#         move_start_y = stats_rect.y + 120  # starts below stats area
#         move_spacing = 5

#         for i, move in enumerate(selected_dino['moveset']):
#             move_name = move['name']
#             move_type = move['type']  # <-- use pre-stored type
#             move_damage = move['damage']
#             move_accuracy = move['accuracy']

#             # Color based on type
#             move_color = TYPE_DATA.get(move_type, {}).get("color", (200, 200, 200))



#             # Move rect
#             move_rect = pygame.Rect(
#                 move_start_x,
#                 move_start_y + i * (move_box_height + move_spacing),
#                 move_box_width,
#                 move_box_height
#             )

#             # Draw move background & border
#             pygame.draw.rect(screen, move_color, move_rect)
#             pygame.draw.rect(screen, (0, 0, 0), move_rect, 2)

#             # Render move text
#             move_text = self.smaller_font.render(move_name, True, (255, 255, 255))
#             move_stats = self.smaller_font.render(f"{move_damage}/{move_accuracy}", True, (255, 255, 255))

#             screen.blit(move_text, (move_rect.x + 8, move_rect.y ))
#             screen.blit(move_stats, (move_rect.x + 125, move_rect.y ))




#         # --- Bottom right: "Box" button ---
#         button_rect = pygame.Rect(self.width - 100, self.height - 60, 80, 40)
#         pygame.draw.rect(screen, (120, 120, 120), button_rect)
#         pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
#         button_text = self.small_font.render("Box", True, (0, 0, 0))
#         screen.blit(button_text, (button_rect.centerx - button_text.get_width() // 2,
#                                   button_rect.centery - button_text.get_height() // 2))
        



#             ### BOX ####

#         screen.fill(self.bg_color)
#         if self.mode == 'party':
#             dinos = self.game.player_dinos
#         else:
#             dinos = self.game.box_dinos

#         if not dinos:
#             # Display "No dinos here" message or similar
#             no_dinos_text = self.font.render("No dinos in this list", True, (255, 255, 255))
#             screen.blit(no_dinos_text, (20, 20))
#             return

#         # Draw list on left panel
#         box_width, box_height = 200, 70
#         start_x, start_y = 20, 20
#         for i, dino in enumerate(dinos):
#             rect = pygame.Rect(start_x, start_y + i * (box_height + 10), box_width, box_height)
#             color = (70, 70, 70) if i != self.selected_index else (0, 150, 255)
#             pygame.draw.rect(screen, color, rect)
#             pygame.draw.rect(screen, (0, 0, 0), rect, 2)
#             name_text = self.font.render(f"{dino['name']}", True, (255, 255, 255))
#             lvl_text = self.font.render(f"Lv{dino['level']}",True, (255,255,255))
#             screen.blit(name_text, (rect.x + 10, rect.y + 5))
#             screen.blit(lvl_text, (rect.x + 10, rect.y + 25))

#             sprite_icon = dino['image']
#             sprite_icon_scaled = pygame.transform.scale(sprite_icon, (50,50))
#             screen.blit(sprite_icon_scaled, (rect.x + 140, rect.y + 5))

#         # Draw preview box and other info for selected dino
#         selected_dino = dinos[self.selected_index]
#         # (Reuse your existing preview, stats, XP bar, etc. drawing code here)

#         # Draw the Box button on party mode only
#         if self.mode == 'party':
#             button_rect = pygame.Rect(self.width - 100, self.height - 60, 80, 40)
#             pygame.draw.rect(screen, (120, 120, 120), button_rect)
#             pygame.draw.rect(screen, (0, 0, 0), button_rect, 2)
#             button_text = self.small_font.render("Box", True, (0, 0, 0))
#             screen.blit(button_text, (button_rect.centerx - button_text.get_width() // 2,
#                                     button_rect.centery - button_text.get_height() // 2))

#         # Draw an instruction for interact key
#         interact_text = self.small_font.render("Press E to Move", True, (255, 255, 255))
#         screen.blit(interact_text, (self.width - 200, self.height - 30))

            
#     def get_current_list_length(self, game):
#         if self.mode == 'party':
#             return len(game.player_dinos)
#         else:
#             return len(game.box_dinos)

#     def toggle_dino_box(self, game):
#         if self.mode == 'party':
#             # Move dino from party to box
#             if len(game.player_dinos) <= 1:
#                 return  # can't box last dino
#             dino = game.player_dinos.pop(self.selected_index)
#             game.box_dinos.append(dino)
#             # Adjust selected index so it doesn't go out of range
#             self.selected_index = min(self.selected_index, len(game.player_dinos) - 1)
#         else:
#             # Move dino from box to party
#             if len(game.player_dinos) >= 6:
#                 return  # party full, can't add more
#             dino = game.box_dinos.pop(self.selected_index)
#             game.player_dinos.append(dino)
#             self.selected_index = min(self.selected_index, len(game.box_dinos) - 1)








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
                    # return 'stay' # stay in encounter for catch attempt
                    return 'used'
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
        self.on_complete = None
        self.messages = []  # <-- Initialize here

    def show(self, message, duration=2, wait_for_input=False):
        """Show a single message."""
        self.message = message
        self.visible = True
        self.wait_for_input = wait_for_input
        self.timer = duration * 1000 if duration > 0 else 0

    def queue_messages(self, messages, wait_for_input=True, on_complete=None):
        """Queue multiple messages to show one after the other."""
        self.messages = list(messages)  # make sure it's a copy
        self.visible = True
        self.wait_for_input = wait_for_input
        self.on_complete = on_complete
        self.message = self.messages.pop(0)
        self.timer = 0  # queued messages are usually click-through

    def handle_event(self, event):
        if self.visible and self.wait_for_input and event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_j):
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
#         self.wait_for_input = False
#         self.on_complete = None

#     def show(self, message, duration=2, wait_for_input=False):
#         self.message = message
#         self.visible = True
#         self.wait_for_input = wait_for_input
#         self.timer = duration * 1000 if duration > 0 else 0


#     def queue_messages(self, messages, wait_for_input=False, on_complete=None):
#         self.messages = messages
#         self.visible = True
#         self.wait_for_input = wait_for_input
#         self.on_complete = on_complete
#         self.message = self.messages.pop(0)

#     def handle_event(self, event):
#         if self.visible and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
#             if self.messages:
#                 self.message = self.messages.pop(0)
#             else:
#                 self.hide()
#                 if self.on_complete:
#                     self.on_complete()

#     def hide(self):
#         self.visible = False
#         self.message = ""
#         self.wait_for_input = False
#         self.messages = []

#     def update(self, dt):
#         if self.visible and self.timer > 0 and not self.wait_for_input:
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
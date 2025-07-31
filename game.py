############
### Game ###
############
import pygame
from player import Player
import os 
import csv
import config

# image processor
def load_image(path, alpha=False):
    """Load an image with optional alpha support."""
    image = pygame.image.load(path)
    return image.convert_alpha() if alpha else image.convert()

    #Encounter class
class Encounter:
    def __init__(self, dino_key):
        self.bg = load_image(config.ENCOUNTER_BG_PATH)  # No alpha
        self.dino = load_image(config.ENCOUNTER_DINOS_PATHS[dino_key], alpha=True) #loads dino 
        self.dino_pos = (380, 10)  #POSITION of dino in bg
    def draw(self, screen):
        screen.blit(self.bg, (0, 0))
        screen.blit(self.dino, self.dino_pos) #DRAWS Position of dino


class EncounterUI:
    def __init__(self):
        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 20)
        self.selected_option = 0  # 0=Fight,1=Bag,2=Party,3=Run
        self.actions = ["Fight", "Bag", "Party", "Run"]

    def draw_panel(self, surface, rect, bg_color=(245,245,245), border_color=(0,0,0), border_width=3):
        pygame.draw.rect(surface, bg_color, rect)
        pygame.draw.rect(surface, border_color, rect, border_width)

    def draw_hp_bar(self, surface, x, y, width, height, percent, back_color=(200,0,0), front_color=(0,200,0)):
        pygame.draw.rect(surface, back_color, (x, y, width, height))
        pygame.draw.rect(surface, front_color, (x, y, int(width * max(0, min(1, percent))), height))

    def draw(self, surface, player_dino, enemy_dino, encounter_text):
        screen_w, screen_h = surface.get_size()

        # --- Panels ---
        text_box_rect = pygame.Rect(9, screen_h - 120, screen_w - 325, 115) #9, 360, 315, 115!
        actions_rect = pygame.Rect(screen_w - 300, screen_h - 120, 287, 115) 
        enemy_info_rect = pygame.Rect(-1, 30, 220, 65)
        player_info_rect = pygame.Rect(screen_w - 220, screen_h - 250, 250, 105)

        # Draw panels
        self.draw_panel(surface, text_box_rect)
        self.draw_panel(surface, actions_rect)
        self.draw_panel(surface, enemy_info_rect)
        self.draw_panel(surface, player_info_rect)

        # --- Enemy Info ---
        enemy_name = self.small_font.render(f"{enemy_dino['name']} Lv{enemy_dino['level']}", True, (0,0,0))
        surface.blit(enemy_name, (enemy_info_rect.x + 10, enemy_info_rect.y + 10))
        self.draw_hp_bar(surface, enemy_info_rect.x + 10, enemy_info_rect.y + 40, 200, 15, enemy_dino['hp']/enemy_dino['max_hp'])

        # --- Player Info ---
        player_name = self.small_font.render(f"{player_dino['name']} Lv{player_dino['level']}", True, (0,0,0))
        surface.blit(player_name, (player_info_rect.x + 10, player_info_rect.y + 10))
        self.draw_hp_bar(surface, player_info_rect.x + 10, player_info_rect.y + 40, 200, 15, player_dino['hp']/player_dino['max_hp'])

        # --- Text Box ---
        wrapped_lines = self.wrap_text(encounter_text, self.font, text_box_rect.width - 40)
        for i, line in enumerate(wrapped_lines[:3]):  # limit 3 lines
            text_surface = self.font.render(line, True, (0,0,0))
            surface.blit(text_surface, (text_box_rect.x + 20, text_box_rect.y + 20 + i * 30))

        # --- Action Menu ---
        for i, action in enumerate(self.actions):
            color = (0,0,255) if i == self.selected_option else (0,0,0)
            action_text = self.font.render(action, True, color)
            surface.blit(action_text, (actions_rect.x + 20 + (i%2)*120, actions_rect.y + 20 + (i//2)*50))

    def wrap_text(self, text, font, max_width):
        """Wrap text into multiple lines."""
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

    def handle_input(self, event):
        """Move selection with arrow keys."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:  # up
                if self.selected_option in (2,3):
                    self.selected_option -= 2
            elif event.key == pygame.K_s:  # down
                if self.selected_option in (0,1):
                    self.selected_option += 2
            elif event.key == pygame.K_a:  # left
                if self.selected_option % 2 == 1:
                    self.selected_option -= 1
            elif event.key == pygame.K_d:  # right
                if self.selected_option % 2 == 0:
                    self.selected_option += 1
            elif event.key == pygame.K_j:  # confirm
                return self.actions[self.selected_option]
        return None





class PartyScreen:
    def __init__(self,game):
        self.width = 640
        self.height = 480
        self.bg_color = (230, 230, 230)
        self.font = pygame.font.SysFont(None, 36)
        self.selected_index = 0  # Which dino box is highlighted
        self.party_size = 6      # For now, fixed at 6 slots
    
    def reset(self):
        """Reset scroll and selection when leaving the screen."""
        self.selected_index = 0
        self.scroll_offset = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                self.selected_index = (self.selected_index - 1) % self.party_size
            elif event.key == pygame.K_s:
                self.selected_index = (self.selected_index + 1) % self.party_size
            elif event.key == pygame.K_SPACE:
                return "back"  # Go back to menu
            elif event.key == pygame.K_i:  # allow i to also close the menu
                return 'quit' #back to world

        return None


    def draw(self, screen):
        # Background
        screen.fill(self.bg_color)

        # Large left-side rectangle (main dino)
        main_rect = pygame.Rect(50, 50, 275, 200)
        pygame.draw.rect(screen, (180, 180, 180), main_rect)
        pygame.draw.rect(screen, (0, 0, 0), main_rect, 3)

        # Right-side 5 smaller rectangles
        box_width, box_height = 250, 50
        start_x, start_y = 350, 50
        for i in range(self.party_size - 1):
            rect = pygame.Rect(start_x, start_y + i * (box_height + 10), box_width, box_height)

            # Highlight if selected
            if (i + 1) == self.selected_index:
                pygame.draw.rect(screen, (0, 150, 255), rect)  # highlighted
            else:
                pygame.draw.rect(screen, (200, 200, 200), rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 2)

        # Highlight the big left box if index 0 is selected
        if self.selected_index == 0:
            pygame.draw.rect(screen, (0, 150, 255), main_rect, 5)

        # Text at bottom
        text = self.font.render("Choose a Dino? (SPACE to go back)", True, (0, 0, 0))
        screen.blit(text, (50, 400))


class ItemsScreen:
    def __init__(self, inventory, icons, descriptions):
        self.inventory = inventory  # dict: {item_name: count}
        self.icons = icons          # dict: {item_name: Surface}
        self.descriptions = descriptions  # dict: {item_name: description}
        self.font = pygame.font.SysFont("arial", 24)
        self.desc_font = pygame.font.SysFont("arial", 20, italic=True)
        self.selected_index = 0
        self.visible_rows = 10
        self.scroll_offset = 0
    def get_filtered_inventory(self):
        return [(item, count) for item, count in self.inventory.items() if count > 0]
    
    def reset(self):
        """Reset scroll and selection when leaving the screen."""
        self.selected_index = 0
        self.scroll_offset = 0


    def draw(self, surface):
        # Background panel for items
        right_rect = pygame.Rect(400, 50, 220, 320)
        pygame.draw.rect(surface, (255, 255, 240), right_rect)  # Light "paper"
        pygame.draw.rect(surface, (0, 0, 0), right_rect, 3)

        # Draw items
        filtered_inventory = [(item, count) for item, count in self.inventory.items() if count > 0]
        self.filtered_inventory = filtered_inventory  # Store for use in handle_event
        if not filtered_inventory:
            no_items_text = self.font.render("No items collected.", True, (0, 0, 0))
            surface.blit(no_items_text, (right_rect.x + 20, right_rect.y + 40))
            return

        
        start = self.scroll_offset
        end = min(start + self.visible_rows, len(self.inventory))


        for i, (item, count) in enumerate(filtered_inventory[start:end]):
            y = right_rect.y + 20 + (i * 35)

            # Highlight current selection
            if start + i == self.selected_index:
                pygame.draw.rect(surface, (200, 200, 255), (right_rect.x + 5, y - 5, right_rect.width - 10, 30), border_radius=5)

            # Icon
            icon = self.icons[item]
            surface.blit(icon, (right_rect.x + 10, y - 10))

            # Text
            text_surface = self.font.render(f"{item} x{count}", True, (0, 0, 0))
            surface.blit(text_surface, (right_rect.x + 50, y))

        # --- Description Panel ---
        desc_rect = pygame.Rect(400, 380, 220, 70)
        pygame.draw.rect(surface, (240, 240, 240), desc_rect)
        pygame.draw.rect(surface, (0, 0, 0), desc_rect, 3)

        # Get selected item description & wrap
        selected_item = filtered_inventory[self.selected_index][0]
        description = self.descriptions.get(selected_item, "No description available.")
        lines = self.wrap_text(description, self.desc_font, desc_rect.width - 20)

        # Draw each line
        for i, line in enumerate(lines):
            line_surface = self.desc_font.render(line, True, (0, 0, 0))
            surface.blit(line_surface, (desc_rect.x + 10, desc_rect.y + 10 + i * 20))

    def handle_event(self, event, game):
        if not hasattr(self, 'filtered_inventory'):
            self.filtered_inventory = [(item, count) for item, count in self.inventory.items() if count > 0]
        # filtered_inventory = self.get_filtered_inventory()
        if event.type == pygame.KEYDOWN:
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
            elif event.key == pygame.K_SPACE:  # Exit back to menu
                game.state = "menu"
            elif event.key == pygame.K_i:  # allow i to also close the menu
                game.state = "world"


    # text within item menu 
    def wrap_text(self, text, font, max_width):
        """Splits text into multiple lines so it fits inside max_width."""
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


class MessageBox:
    def __init__(self, width, height, font=None):
        self.width = width
        self.height = 100  # height of the box
        self.font = font or pygame.font.SysFont("arial", 24)
        self.message = ""
        self.visible = False
        self.timer = 0  # auto-hide timer (optional)

    def show(self, message, duration=2):  # duration in seconds (0 = wait for keypress)
        self.message = message
        self.visible = True
        self.timer = duration * 1000 if duration > 0 else 0  # convert to ms

    def hide(self):
        self.visible = False
        self.message = ""

    def update(self, dt):
        if self.visible and self.timer > 0:
            self.timer -= dt
            if self.timer <= 0:
                self.hide()

    def draw(self, surface):
        if not self.visible:
            return
        box_rect = pygame.Rect(50, surface.get_height() - self.height - 20, self.width - 100, self.height)
        pygame.draw.rect(surface, (255, 255, 255), box_rect)
        pygame.draw.rect(surface, (0, 0, 0), box_rect, 3)

        # Wrap text inside the box
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

        # Draw lines
        for i, line in enumerate(lines):
            text_surf = self.font.render(line, True, (0, 0, 0))
            surface.blit(text_surf, (box_rect.x + 10, box_rect.y + 10 + i * 30))


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        pygame.display.set_caption('DinoPodds')
        self.clock = pygame.time.Clock()
        self.running = True

        # Now load surfaces safely from config.py
        self.tile_images = {key: load_image(path, alpha=True) for key, path in config.TILE_PATHS.items()}  
        # self.encounter_bg = load_image(config.ENCOUNTER_BG_PATH)
        # self.encounter_dino = load_image(config.ENCOUNTER_DINOS_PATHS['vusion'], alpha=True)

        ### ENCOUNTER INITIALIZED
        self.encounter_ui = EncounterUI()
        self.encounter_text = 'A wild Dino appeared!"'
        self.encounter = None

        self.player_dino = {
            "name": "Vusion",
            "level": 5,
            "hp": 30,
            "max_hp": 50
        }


        self.previous_state = 'world' #default
        self.player = Player(spawn_point='home')
        self.all_sprites = pygame.sprite.Group() #all active sprites
        self.all_sprites.add(self.player)

        self.camera_x = 0
        self.camera_y = 0

        #Zoom
        self.zoom = 1.25 #normal display size 1.0
        self.render_surface = pygame.Surface((config.WIDTH // self.zoom, config.HEIGHT // self.zoom))

        #-Start Town  640/480 needs 20/15
        # 20 columns x 15 rows
        # CSV MAP
        self.world_map = self.load_csv_map('MAP_DINO.csv')

        #Set state of Player
        self.state = 'world' # will add encounter/battle/teleport/fly
        #For encounter Transition
        self.fade_alpha = 0
        self.fading = False


        #MENU
        self.menu = Menu(self)
        # party of dinos and items held
        self.party = []
        self.items = []

        #MENU - PARTY
        self.party_screen = PartyScreen(self)
        self.party_screen.reset()


        #MENU - ITEMS
        self.item_image = pygame.image.load(config.ITEMS["DinoPod"]['icon']).convert_alpha()
        self.items_on_map = {(12, 5): 'DinoPod', (12,6): 'DinoPod'}  # ITEM SPAWNS POSITIONS
        # Initialize all items to 0 count so they always exist
        self.inventory = {item: 0 for item in config.ITEMS.keys()} # items picked up
                

        self.item_icons = {key: pygame.image.load(data["icon"]).convert_alpha() for key, data in config.ITEMS.items()}
        self.item_descriptions = {key: data["description"] for key, data in config.ITEMS.items()}
        self.items_screen = ItemsScreen(self.inventory, self.item_icons, self.item_descriptions)
        self.items_screen.reset()


        self.message_box = MessageBox(config.WIDTH, config.HEIGHT)



        # self.encounter_bg = pygame.image.load(os.path.join('assets/MapAssets/Grass_Encounter.png')).convert() # encounter screen
        # self.encounter_dino = config.DINOS['vusion'] # encounter dino, change logic to loop through dinos in different areas
        #self.encounter_dino = random.choice(list(config.encounter_dinos.values())) # for random list of dinos


    #Encounter Event
    def trigger_encounter(self,dino_key='vusion'):
        self.fading = True
        self.fade_alpha = 0
        self.encounter = Encounter(dino_key)
        self.enemy_dino = {
            "name": dino_key,
            "level": 3,
            "hp": 20,
            "max_hp": 20
        }
        self.encounter_text = "A wild Raptor appeared!"


        # self.state = "encounter"
    # Player stays exactly where they are (don’t clear anything)
    # Optional: play a sound or animation


    def load_csv_map(self, filename):
        path = os.path.join('assets/MapAssets', filename)
        with open(path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            return [[cell.strip() if cell.strip() else 'T' for cell in row] for row in reader]  # Replace blanks with 'G'


    def run(self):
        while self.running:
            # self.clock.tick(config.FPS)
            dt = self.clock.tick(60)/1000
            # dt = self.clock.tick() / 1000.0 #delta time in seconds
            self.events()
            self.update(dt)
            self.draw()
    
    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if self.state == 'world':
                if event.type == pygame.KEYDOWN:  ######## ANY OVERWORLD KEY PRESSES ELIF HERE !!!!!!!!!!!! 
                    #Message Box
                    # --- Message box dismiss ---
                    if self.message_box.visible:
                        if self.message_box.timer == 0 and event.key in (pygame.K_j, pygame.K_SPACE):
                            self.message_box.hide()
                        # Block other inputs while message is visible
                        continue  
                    if event.key == pygame.K_i:  # toggle menu
                        self.state = 'menu'
                        ### Items
                    elif event.key == pygame.K_j: #Interact key = j
                        print('j')
                        # Player's current tile
                        px = self.player.rect.x // config.TILE_SIZE
                        py = self.player.rect.y // config.TILE_SIZE

                        # Tile in front of player
                        if self.player.facing == "up": py -= 1
                        elif self.player.facing == "down": py += 1
                        elif self.player.facing == "left": px -= 1
                        elif self.player.facing == "right": px += 1
                        # Check if there is an item at that position
                        if (px, py) in self.items_on_map:
                            item_name = self.items_on_map[(px, py)]   # Get the item type
                            del self.items_on_map[(px, py)]           # Remove from the world
                            self.inventory[item_name] += 1            # Add to inventory
                            self.message_box.show(f'Picked up a {item_name}!', duration=0)
                            self.items_screen.selected_index = 0
                            self.items_screen.scroll_offset = 0
                            print(f"Picked up {item_name}! Total: {self.inventory[item_name]}")



            elif self.state == "menu":
                self.menu.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_j:
                    if self.menu.options[self.menu.selected_index] == "Party":
                        self.state = "party"
            #MENU - PARTY
            elif self.state == "party":
                result = self.party_screen.handle_event(event)
                if result == "back":
                    self.state = "menu"
                    self.party_screen.reset()
                if result =='quit':
                    self.state = 'world'
                    self.previous_state = self.state
                    self.party_screen.reset()

                    # self.state = 'menu'
            #MENU - ITEMS
            if self.state == 'items':
                self.items_screen.handle_event(event,self)
                self.items_screen.reset()
                return
            ##### ENCOUNTER STATE
            elif self.state == 'encounter':
                result = self.encounter_ui.handle_input(event)
                self.previous_state = self.state
                if result == "Fight":
                    print("Fight selected!")
                elif result == "Run":
                    self.state = 'world'
                    self.previous_state = self.state
                    print("Run away!")
                elif result == "Bag":
                    self.state = 'items'
                    print('Bag Opening')
                elif result == 'Party':
                    self.state = 'party'
                    print('Switching Dino')
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_i: #i for running and for menu open/close
                        self.state = 'world'
                        self.previous_state = self.state

            # Zoom controls can stay here if needed
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    self.set_zoom(self.zoom + .5)
                elif event.key == pygame.K_MINUS:
                    self.set_zoom(self.zoom - .5)
            


    
    def update(self,dt):
        # pause world when message box is open
        if self.message_box.visible:
            self.message_box.update(dt)
            return
        if self.state == 'world':
            keys = pygame.key.get_pressed()
            if self.state == 'world' and not self.fading:
                self.all_sprites.update(keys,self,dt)
                self.update_camera() #keeps camera locked on player
            elif self.fading:
                self.fade_alpha +=10 #adjust speed transition
                if self.fade_alpha >= 255:
                    self.fade_alpha = 255
                    self.fading = False
                    self.state = 'encounter'

            # Desired camera target (keep player near center) v2
            target_x = self.player.rect.centerx - config.WIDTH // 2
            target_y = self.player.rect.centery - config.HEIGHT // 2

            # Optional: Clamp camera so it doesn’t scroll past map edges
            max_x = len(self.world_map[0]) * config.TILE_SIZE - config.WIDTH
            max_y = len(self.world_map) * config.TILE_SIZE - config.HEIGHT

            target_x = max(0, min(target_x, max_x)) #v2
            target_y = max(0, min(target_y, max_y)) #v2

            # Smooth interpolation (lerp) for camera v2
            cam_speed = 0.2  # lower = slower camera, higher = snappier
            self.camera_x += (target_x - self.camera_x) * cam_speed
            self.camera_y += (target_y - self.camera_y) * cam_speed

            # MESSAGE BOX
            self.message_box.update(self.clock.get_time())
            if self.message_box.visible:
                self.message_box.update(dt)


##### Draw Method
    def draw(self):
        # 1. Always clear the render surface
        self.render_surface.fill(config.BLACK)

        # 1. Decide what background to draw
        background_state = self.previous_state if self.state in ('menu', 'party', 'items') else self.state

        if background_state == 'world':
            # Draw world background
            self.render_surface.fill(config.BLACK)
            self.draw_map(surface=self.render_surface)
            for sprite in self.all_sprites:
                self.render_surface.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y - self.camera_y))
            scaled_surface = pygame.transform.scale(self.render_surface, (config.WIDTH, config.HEIGHT))
            self.screen.blit(scaled_surface, (0, 0))

        elif background_state == 'encounter':
            # Draw encounter scene in the back
            self.encounter.draw(self.screen)
            self.encounter_ui.draw(self.screen, self.player_dino, self.enemy_dino, self.encounter_text)

        # 3. Overlay & UI based on state
        if self.state == 'menu':
            overlay = pygame.Surface((config.WIDTH, config.HEIGHT))
            overlay.set_alpha(180)  # dim background
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            self.menu.draw(self.screen)

        elif self.state == 'party':
            overlay = pygame.Surface((config.WIDTH, config.HEIGHT))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            self.party_screen.draw(self.screen)

        elif self.state == 'items':
            overlay = pygame.Surface((config.WIDTH, config.HEIGHT))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            self.items_screen.draw(self.screen)

        elif self.state == 'encounter':
            # Encounters get full control of the screen (don’t dim world)
            self.encounter.draw(self.screen)
            self.encounter_ui.draw(self.screen, self.player_dino, self.enemy_dino, self.encounter_text)

        # 4. Fading overlay
        if self.fading:
            fade_surface = pygame.Surface((config.WIDTH, config.HEIGHT))
            fade_surface.set_alpha(self.fade_alpha)
            fade_surface.fill((0, 0, 0))
            self.screen.blit(fade_surface, (0, 0))

        # 5. Message box (on top of all states)
        if self.message_box.visible:
            self.message_box.draw(self.screen)

        # 6. Flip the display
        pygame.display.flip()





    # def draw(self):
    #     # self.screen.fill((0,0,0))
    #     if self.state == 'world':
    #         # self.world.draw(self.screen)


    #         # 1. Clear the smaller render surface
    #         self.render_surface.fill(config.BLACK)

    #         # 2. Draw the map on the smaller surface
    #         self.draw_map(surface=self.render_surface)

    #         # 3. Draw all sprites adjusted for camera
    #         for sprite in self.all_sprites:
    #             self.render_surface.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y - self.camera_y))
    #             # self.player.draw(self.render_surface, self.camera_x, self.camera_y)

    #         # 4. Scale up to the main screen for zoom
    #         scaled_surface = pygame.transform.scale(self.render_surface, (config.WIDTH, config.HEIGHT))
    #         self.screen.blit(scaled_surface, (0, 0))
        
    #     #MENU DRAW
    #     elif self.state == 'menu':
    #         self.menu.draw(self.screen)
        
    #     # MENU - PARTY
    #     elif self.state == 'party':
    #                 # Dim background
    #         overlay = pygame.Surface((config.WIDTH, config.HEIGHT))
    #         overlay.set_alpha(150)
    #         overlay.fill((0, 0, 0))
    #         self.screen.blit(overlay, (0, 0))
    #         # Draw party screen
    #         self.party_screen.draw(self.screen)
    #     #MENU - ITEMS
    #     elif self.state == 'items':
    #         self.items_screen.draw(self.screen)
        


    #     # ENCOUNTER DRAW
    #     elif self.state == 'encounter':
    #         # Draw encounter background and animal directly to screen
    #         self.encounter.draw(self.screen)
    #         self.encounter_ui.draw(self.screen, self.player_dino, self.enemy_dino, self.encounter_text)
    #     if self.fading:
    #         fade_surface = pygame.Surface((config.WIDTH, config.HEIGHT))
    #         fade_surface.set_alpha(self.fade_alpha)
    #         fade_surface.fill((0,0,0))
    #         self.screen.blit(fade_surface,(0,0))



    #     if self.message_box.visible:
    #         self.message_box.draw(self.screen)


    #     # Flip display in all cases
    #     pygame.display.flip()

    
    def draw_map(self, surface):
        for index, row in enumerate(self.world_map):
            for col, tile in enumerate(row):
                if not tile:  # skip blanks
                    continue
                x = col * config.TILE_SIZE - self.camera_x
                y = index * config.TILE_SIZE - self.camera_y
                surface.blit(self.tile_images[tile], (x, y))
        # Draw items on map ---
        for (ix, iy) in self.items_on_map:
            x = ix * config.TILE_SIZE - self.camera_x
            y = iy * config.TILE_SIZE - self.camera_y
            surface.blit(self.item_image, (x, y))
        
        for (x, y), item_name in self.items_on_map.items():
            icon = self.item_icons[item_name]
            self.render_surface.blit(icon, (x * config.TILE_SIZE - self.camera_x, y * config.TILE_SIZE - self.camera_y))
        
        # MESSAGE BOX
        self.message_box.draw(self.screen)



    def update_camera(self):
        # Center the camera based on the *render surface* size
        render_w = config.WIDTH // self.zoom
        render_h = config.HEIGHT // self.zoom
        self.camera_x = self.player.rect.centerx - render_w // 2
        self.camera_y = self.player.rect.centery - render_h // 2

        # Clamp to map bounds
        max_x = len(self.world_map[0]) * config.TILE_SIZE - render_w
        max_y = len(self.world_map) * config.TILE_SIZE - render_h
        self.camera_x = max(0, min(self.camera_x, max_x))
        self.camera_y = max(0, min(self.camera_y, max_y))

    

    #Zoom switch
    def set_zoom(self, zoom):
        self.zoom = round(max(1.0, min(1.75, zoom)),2)  # clamp between 1.0x and 1.75x
        render_w = int(config.WIDTH / self.zoom)
        render_h = int(config.HEIGHT / self.zoom)
        self.render_surface = pygame.Surface((render_w, render_h))
        self.update_camera()  # Recenter after zoom





### MENU
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
        # Panel position (right side)
        panel_rect = pygame.Rect(
            self.game.screen.get_width() - self.width - 20,  # small offset
            50,
            self.width,
            320
        )

        # Background panel: Light "paper"
        pygame.draw.rect(screen, (255, 255, 240), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 3)  # border

        # Title
        title_surf = self.font.render("Menu", True, (0, 0, 0))
        screen.blit(title_surf, (panel_rect.x + self.margin, panel_rect.y + 10))

        # Options
        for i, option in enumerate(self.options):
            y = panel_rect.y + 50 + i * self.line_height
            # Highlight selection
            if i == self.selected_index:
                pygame.draw.rect(
                    screen, 
                    (200, 200, 255),  # light blue
                    (panel_rect.x + 5, y - 5, panel_rect.width - 10, 30),
                    border_radius=5
                )
            # Text
            option_surf = self.font.render(option, True, (0, 0, 0))
            screen.blit(option_surf, (panel_rect.x + self.margin, y))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key == pygame.K_s:
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key == pygame.K_j:  # j -> select
                selected = self.options[self.selected_index]
                if selected == "Party":
                    self.game.state = 'party'
                elif selected == "Save Game":
                    print("Game saved!")  # placeholder
                elif selected == "Items":
                    self.game.state = 'items'
                elif selected == "Options":
                    print('Options Selected')
            elif event.key == pygame.K_SPACE or event.key == pygame.K_i:
                self.game.state = self.game.previous_state

############
### Game ###
############
import pygame
from player import Player
import os 
import csv
import config
from screens import Encounter, EncounterUI, ItemsScreen, PartyScreen, MessageBox
from data import DINO_DATA,MOVE_DATA
import random

# image processor
def load_image(path, alpha=False):
    """Load an image with optional alpha support."""
    image = pygame.image.load(path)
    return image.convert_alpha() if alpha else image.convert()

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        pygame.display.set_caption('DinoPodds')
        self.clock = pygame.time.Clock()
        self.running = True
        # self.parent_state = 'world'
        self.state_stack = ['world']

        self.fonts = {name: pygame.font.Font(path, size) for name, (path, size) in config.FONT_DEFS.items()}
        self.tile_images = {key: load_image(path, alpha=True) for key, path in config.TILE_PATHS.items()}  

        self.enemy_dino = {"name": "Anemamace", "level": 3, "hp": 20, "max_hp": 20}

        self.previous_state = 'world'
        self.player = Player(spawn_point='home')
        self.all_sprites = pygame.sprite.Group(self.player)

        self.camera_x, self.camera_y = 0, 0
        self.zoom = 1.25
        self.render_surface = pygame.Surface((config.WIDTH // self.zoom, config.HEIGHT // self.zoom))
        self.world_map = self.load_csv_map('MAP_DINO.csv')
        # self.state = 'world'
        self.fade_alpha = 0
        self.fading = False

        # DINO DATA
        self.player_dino_images = {name: load_image(path, alpha=True) for name, path in config.PLAYER_DINO_PATH.items()}
        self.player_dinos = [
            self.create_dino('Vusion', 20),
            self.create_dino('Vusion', 3)
        ]
        self.active_dino_index = 0
        # MENU
        self.menu = Menu(self)
        self.party_screen = PartyScreen(self)  # <-- pass game, not fonts
        self.party_screen.reset()

        # ITEMS
        self.item_image = pygame.image.load(config.ITEMS["DinoPod"]['icon']).convert_alpha()
        self.items_on_map = {(12, 5): 'DinoPod', (12, 6): 'DinoPod'}
        self.inventory = {item: 0 for item in config.ITEMS.keys()}
        self.item_icons = {key: pygame.image.load(data["icon"]).convert_alpha() for key, data in config.ITEMS.items()}
        self.item_descriptions = {key: data["description"] for key, data in config.ITEMS.items()}
        self.items_screen = ItemsScreen(self.inventory, self.item_icons, self.item_descriptions, self.fonts)
        self.items_screen.reset()
        
        # MESSAGE BOX
        self.message_box = MessageBox(config.WIDTH, config.HEIGHT, self.fonts)
        self._post_catch_message = None  # Initialize this variable


        # ENCOUNTER
        self.encounter_ui = EncounterUI(self.fonts)
        self.encounter_text = 'A wild Dino appeared!'
        self.encounter = Encounter(self.fonts, "Anemamace")



    def create_dino(self, name, level):
        from data import DINO_DATA, MOVE_DATA
        base_stats = DINO_DATA[name]['stats']
        
        # Get all moves this dino knows
        learned_moves = [move for lvl, move in DINO_DATA[name]['moves'].items() if lvl <= level]
        
        # Attach full move data (name, damage, accuracy, type)
        moves_with_data = []
        for move in learned_moves:
            move_info = MOVE_DATA.get(move, {})
            moves_with_data.append({
                "name": move,
                "type": move_info.get("type", "normal"),
                "damage": move_info.get("damage", 0),
                "accuracy": move_info.get("accuracy", 100)
            })
        
        return {
            "name": name,
            "level": level,
            "type": base_stats['type'],
            "hp": base_stats['health'],
            "max_hp": base_stats['health'],
            "attack": base_stats['attack'],
            "defense": base_stats['defense'],
            "speed": base_stats['speed'],
            "moves": moves_with_data,  # <-- now moves are full dictionaries with stats
            "image": self.player_dino_images[name]
        }


    # def create_dino(self, name, level):
    #     from data import DINO_DATA,MOVE_DATA
    #     base_stats = DINO_DATA[name]['stats']
    #     move_stats = MOVE_DATA[name]
    #     return {
    #         "name": name,
    #         "level": level,
    #         "type": base_stats['type'],
    #         "hp": base_stats['health'],
    #         "max_hp": base_stats['health'],
    #         "attack": base_stats['attack'],
    #         "defense": base_stats['defense'],
    #         "speed": base_stats['speed'],
    #         "moves": [move for lvl, move in DINO_DATA[name]['moves'].items() if lvl <= level],
    #         'damage': move_stats[move for lvl, move in DINO_DATA[name]['moves'].items() if lvl <= level],
    #         'accuracy': [],
    #         "image": self.player_dino_images[name]  # <-- Load the sprite automatically
        
    
    @property
    def state(self):
        return self.state_stack[-1]  # Top of stack is current state

    def push_state(self, state):
        self.state_stack.append(state)

    def pop_state(self):
        if len(self.state_stack) > 1:  # Never pop the base state
            self.state_stack.pop()
    def pop_to_world(self):
        while len(self.state_stack) >1:
            self.pop_state()



    def trigger_encounter(self, dino_key='Anemamace'):
        print('Encounter Trigger')
        self.fading = True
        self.fade_alpha = 0
        self.encounter = Encounter(self.fonts, dino_key)
        self.enemy_dino = {"name": dino_key, "level": 3, "hp": 20, "max_hp": 20}
        self.encounter_text = f"A wild {dino_key.capitalize()} appeared!"

    def load_csv_map(self, filename):
        path = os.path.join('assets/MapAssets', filename)
        with open(path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            return [[cell.strip() if cell.strip() else 'T' for cell in row] for row in reader]
        
        

    # --- Main Loop ---
    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000
            self.events()
            self.update(dt)
            self.draw()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            
             # --- Message box intercept (always first) ---

            if self.message_box.visible and self.message_box.wait_for_input:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_j): #SPACE or j interact for dialogue
                    if self._post_catch_message:
                        #show next message
                        self.message_box.show(self._post_catch_message, wait_for_input= True)
                        self._post_catch_message = None
                    else:
                        self.message_box.hide()
                # If waiting for SPACE/J to close the message, block other inputs
                # continue

            # ---- WORLD ----
            if self.state == 'world':
                self.handle_world_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                    self.push_state('menu')

            # ---- MENU ----
            elif self.state == 'menu':
                self.menu.handle_event(event)
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_i):  # Close menu
                        self.pop_state()

            # ---- PARTY ----
            elif self.state == 'party':
                result = self.party_screen.handle_event(event, self)
                if result == "back":  # SPACE
                    # If coming from menu on top of world, go straight back to menu over world
                    if len(self.state_stack) >= 2 and self.state_stack[-2] == 'menu' and self.state_stack[0] == 'world':
                        self.pop_state()
                        self.pop_state()
                        self.push_state('menu')
                    else:
                        self.pop_state()
                    self.party_screen.reset()
                elif result == 'quit':  # I quits
                    self.pop_to_world()
                    self.party_screen.reset()

            # ---- ITEMS ----
            elif self.state == 'items':
                result = self.items_screen.handle_event(event, self)
                if result == "back":  # SPACE
                    # If opened from menu over world
                    if len(self.state_stack) >= 2 and self.state_stack[-2] == 'menu' and self.state_stack[0] == 'world':
                        self.pop_state()
                        self.pop_state()
                        self.push_state('menu')
                    else:
                        # If opened from encounter or anything else, just pop back
                        self.pop_state()
                    self.items_screen.reset()
                elif result == 'quit':  # I quits
                    self.pop_to_world()
                    self.items_screen.reset()
                elif result == 'stay':
                    pass # wait for message box interaction


            # ---- ENCOUNTER ----
            elif self.state == 'encounter':
                # First, handle message box input blocking for running
                if self.message_box.visible and self.message_box.wait_for_input:
                    # During message, block run (ignore 'i')
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                        # Ignore run input until dialogue is done
                        continue  # or just don't call pop_to_world()
                else:
                    # Normal encounter input handling
                    result = self.encounter_ui.handle_input(event, self.player_dinos[self.active_dino_index])
                    if result == "Fight":
                        print("Fight selected!")
                    elif result == "Run":
                        self.pop_to_world()
                        print("Run away!")
                    elif result == "Bag":
                        self.push_state('items')
                        print("Bag Opening")
                    elif result == 'Party':
                        self.push_state('party')
                        print("Switching Dino")
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                        self.pop_to_world()

            # ---- ZOOM ----
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    self.set_zoom(self.zoom + .5)
                elif event.key == pygame.K_MINUS:
                    self.set_zoom(self.zoom - .5)


    def handle_world_event(self, event):
        if event.type == pygame.KEYDOWN:
            # Dismiss message box
            if self.message_box.visible:
                if self.message_box.timer == 0 and event.key in (pygame.K_j, pygame.K_SPACE):
                    self.message_box.hide()
                return  
            if event.key == pygame.K_i:
                self.push_state('menu')  # push menu on top of world
            elif event.key == pygame.K_j:
                self.pickup_item()

            

    def handle_encounter_event(self, event):
        result = self.encounter_ui.handle_input(event)
        if result == "Fight":
            print("Fight selected!")
        elif result == "Run":
            self.pop_to_world()  # Return to world by popping all states
        elif result == "Bag":
            self.push_state('items')
        elif result == 'Party':
            self.push_state('party')
        if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
            self.pop_to_world()


    def pickup_item(self):
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        if self.player.facing == "up": py -= 1
        elif self.player.facing == "down": py += 1
        elif self.player.facing == "left": px -= 1
        elif self.player.facing == "right": px += 1
        if (px, py) in self.items_on_map:
            item_name = self.items_on_map.pop((px, py))
            self.inventory[item_name] += 1
            self.message_box.show(f'Picked up a {item_name}!', duration=0)
            print(f"Picked up {item_name}! Total: {self.inventory[item_name]}")

    def update(self, dt):
        if self.message_box.visible:
            self.message_box.update(dt)
            return

        if self.state == 'world':
            keys = pygame.key.get_pressed()
            if not self.fading:
                self.all_sprites.update(keys, self, dt)
                self.update_camera()
            else:
                self.fade_alpha += 10
                if self.fade_alpha >= 255:
                    self.fade_alpha = 255
                    self.fading = False
                    # Instead of self.state = 'encounter', push encounter
                    self.push_state('encounter')

        self.message_box.update(self.clock.get_time())


    def draw(self):
        self.render_surface.fill(config.BLACK)

        # background_state = self.state_stack[0]  # bottom state (background)
        # If encounter is anywhere in the stack, use it as the background
        if 'encounter' in self.state_stack:
            background_state = 'encounter'
        else:
            background_state = self.state_stack[0]

        current_state = self.state  # top state (active)

        # Draw background based on bottom state
        if background_state == 'world':
            self.draw_map(self.render_surface)
            for sprite in self.all_sprites:
                self.render_surface.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y - self.camera_y))
            scaled_surface = pygame.transform.scale(self.render_surface, (config.WIDTH, config.HEIGHT))
            self.screen.blit(scaled_surface, (0, 0))
        elif background_state == 'encounter':
            # Usually encounter is top state, but in case bottom is encounter
            self.encounter.draw(self.screen)
            self.encounter_ui.draw(self.screen, self.player_dinos[self.active_dino_index], self.enemy_dino, self.encounter_text)

        # Draw overlays/UI based on current top state
        if current_state == 'encounter':
            self.encounter.draw(self.screen)
            self.encounter_ui.draw(self.screen, self.player_dinos[self.active_dino_index], self.enemy_dino, self.encounter_text)
        elif current_state in ('menu', 'party', 'items'):
            # Tint background only if world is background
            if background_state == 'world':
                self.draw_overlay()
            if current_state == 'menu':
                self.menu.draw(self.screen)
            elif current_state == 'party':
                self.party_screen.draw(self.screen)
            elif current_state == 'items':
                self.items_screen.draw(self.screen)

        # Fade effect
        if self.fading:
            fade_surface = pygame.Surface((config.WIDTH, config.HEIGHT))
            fade_surface.set_alpha(self.fade_alpha)
            fade_surface.fill((0, 0, 0))
            self.screen.blit(fade_surface, (0, 0))

        # Message box
        if self.message_box.visible:
            self.message_box.draw(self.screen)

        pygame.display.flip()


    

    def draw_overlay(self):
        overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))  # RGBA: last value is transparency
        self.screen.blit(overlay, (0, 0))



    def draw_map(self, surface):
        for row_idx, row in enumerate(self.world_map):
            for col_idx, tile in enumerate(row):
                if tile:
                    x = col_idx * config.TILE_SIZE - self.camera_x
                    y = row_idx * config.TILE_SIZE - self.camera_y
                    surface.blit(self.tile_images[tile], (x, y))
        for (x, y), item_name in self.items_on_map.items():
            icon = self.item_icons[item_name]
            surface.blit(icon, (x * config.TILE_SIZE - self.camera_x, y * config.TILE_SIZE - self.camera_y))

    def update_camera(self):
        render_w = config.WIDTH // self.zoom
        render_h = config.HEIGHT // self.zoom
        self.camera_x = self.player.rect.centerx - render_w // 2
        self.camera_y = self.player.rect.centery - render_h // 2
        max_x = len(self.world_map[0]) * config.TILE_SIZE - render_w
        max_y = len(self.world_map) * config.TILE_SIZE - render_h
        self.camera_x = max(0, min(self.camera_x, max_x))
        self.camera_y = max(0, min(self.camera_y, max_y))

    def set_zoom(self, zoom):
        self.zoom = round(max(1.0, min(1.75, zoom)), 2)
        render_w = int(config.WIDTH / self.zoom)
        render_h = int(config.HEIGHT / self.zoom)
        self.render_surface = pygame.Surface((render_w, render_h))
        self.update_camera()
    
    #CATCH LOGIC
    def attempt_catch(self):
        self.inventory["DinoPod"] = max(0, self.inventory["DinoPod"] - 1)
        pod_rate = config.ITEMS["DinoPod"]["catch_rate"]
        success = random.random() < pod_rate
        if success:
            caught_dino = self.create_dino(
                self.enemy_dino["name"], 
                self.enemy_dino["level"]
            )
            self.player_dinos.append(caught_dino)

            
            # Show message that dino was caught
            self.message_box.show(f"You caught {self.enemy_dino['name']}!", wait_for_input=True)

            # End encounter and return to world first
            self.pop_to_world()

            # Prepare the next message after first is dismissed
            self._post_catch_message = f"{self.enemy_dino['name']} has been added to your party!"
        else:
            self.message_box.show(f"{self.enemy_dino['name']} broke free!", wait_for_input=True)
            self._post_catch_message = None
            if 'items' in self.state_stack:
                self.pop_state()






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
        panel_rect = pygame.Rect(screen.get_width() - self.width - 20, 50, self.width, 320)
        pygame.draw.rect(screen, (255, 255, 240), panel_rect)
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 3)
        title_surf = self.font.render("Menu", True, (0, 0, 0))
        screen.blit(title_surf, (panel_rect.x + self.margin, panel_rect.y + 10))
        for i, option in enumerate(self.options):
            y = panel_rect.y + 50 + i * self.line_height
            if i == self.selected_index:
                pygame.draw.rect(screen, (200, 200, 255), (panel_rect.x + 5, y - 5, panel_rect.width - 10, 30), border_radius=5)
            option_surf = self.font.render(option, True, (0, 0, 0))
            screen.blit(option_surf, (panel_rect.x + self.margin, y))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key == pygame.K_s:
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key == pygame.K_j:  # Select option
                selected = self.options[self.selected_index]
                if selected == "Party":
                    self.game.push_state('party')
                elif selected == "Items":
                    self.game.push_state('items')
                elif selected == "Save Game":
                    print("Game saved!")
                elif selected == "Options":
                    print('Options Selected')
            elif event.key == pygame.K_SPACE:  # Close menu
                self.game.pop_state()
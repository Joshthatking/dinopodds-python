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


class PartyScreen:
    def __init__(self):
        self.width = 640
        self.height = 480
        self.bg_color = (230, 230, 230)
        self.font = pygame.font.SysFont(None, 36)
        self.selected_index = 0  # Which dino box is highlighted
        self.party_size = 6      # For now, fixed at 6 slots

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                self.selected_index = (self.selected_index - 1) % self.party_size
            elif event.key == pygame.K_s:
                self.selected_index = (self.selected_index + 1) % self.party_size
            elif event.key == pygame.K_SPACE:
                return "back"  # Go back to menu
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

        self.encounter = None

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
        self.party_screen = PartyScreen()


        #ITEMS
        self.item_image = pygame.image.load(config.ITEMS["dp"]).convert_alpha()
        self.items_on_map = [(12, 5)]  # tile positions where items spawn (start with one)
        self.item_count = 0  # how many player has picked up




        # self.encounter_bg = pygame.image.load(os.path.join('assets/MapAssets/Grass_Encounter.png')).convert() # encounter screen
        # self.encounter_dino = config.DINOS['vusion'] # encounter dino, change logic to loop through dinos in different areas
        #self.encounter_dino = random.choice(list(config.encounter_dinos.values())) # for random list of dinos


    #Encounter Event
    def trigger_encounter(self,dino_key='vusion'):
        self.fading = True
        self.fade_alpha = 0
        self.encounter = Encounter(dino_key)
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
            self.clock.tick(config.FPS)
            # dt = self.clock.tick() / 1000.0 #delta time in seconds
            self.events()
            self.update()#dt)
            self.draw()
    
    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if self.state == 'world':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_i:  # toggle menu
                        self.state = 'menu'

            elif self.state == "menu":
                self.menu.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_j:
                    if self.menu.options[self.menu.selected_index] == "Party":
                        self.state = "party"
            #menu-party
            elif self.state == "party":
                result = self.party_screen.handle_event(event)
                if result == "back":
                    self.state = "world"
                    # self.state = 'menu'

            elif self.state == 'encounter':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_i: #i for running and for menu open/close
                        self.state = 'world'

            # Zoom controls can stay here if needed
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    self.set_zoom(self.zoom + .5)
                elif event.key == pygame.K_MINUS:
                    self.set_zoom(self.zoom - .5)
            
            #### ITEMS 
            elif event.type == pygame.KEYDOWN:
                if self.state == "world" and event.key == pygame.K_j:
                    print('j pressed')
                    # Player's current tile
                    px = self.player.rect.x // config.TILE_SIZE
                    py = self.player.rect.y // config.TILE_SIZE

                    # Move 1 tile in the facing direction
                    if self.player.facing == "up": py -= 1
                    elif self.player.facing == "down": py += 1
                    elif self.player.facing == "left": px -= 1
                    elif self.player.facing == "right": px += 1

                    # Debug: print to confirm what tile we're checking
                    print(f"Checking for item at: {(px, py)}. Items: {self.items_on_map}")

                    # Check if item exists there
                    if (px, py) in self.items_on_map:
                        self.items_on_map.remove((px, py))
                        self.item_count += 1
                        print(f"Picked up item! Total: {self.item_count}")



    
    def update(self):#,dt):
        keys = pygame.key.get_pressed()
        if self.state == 'world' and not self.fading:
            self.all_sprites.update(keys,self)#,dt)
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


##### Draw Method
    def draw(self):
        if self.state == 'world':
            # 1. Clear the smaller render surface
            self.render_surface.fill(config.BLACK)

            # 2. Draw the map on the smaller surface
            self.draw_map(surface=self.render_surface)

            # 3. Draw all sprites adjusted for camera
            for sprite in self.all_sprites:
                self.render_surface.blit(sprite.image, (sprite.rect.x - self.camera_x, sprite.rect.y - self.camera_y))
                # self.player.draw(self.render_surface, self.camera_x, self.camera_y)

            # 4. Scale up to the main screen for zoom
            scaled_surface = pygame.transform.scale(self.render_surface, (config.WIDTH, config.HEIGHT))
            self.screen.blit(scaled_surface, (0, 0))
        
        #MENU DRAW
        elif self.state == 'menu':
            self.menu.draw(self.screen)
        
        # MENU - PARTY
        elif self.state == 'party':
                    # Dim background
            overlay = pygame.Surface((config.WIDTH, config.HEIGHT))
            overlay.set_alpha(150)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            # Draw party screen
            self.party_screen.draw(self.screen)


        # ENCOUNTER DRAW
        elif self.state == 'encounter':
            # Draw encounter background and animal directly to screen
            self.encounter.draw(self.screen)
        if self.fading:
            fade_surface = pygame.Surface((config.WIDTH, config.HEIGHT))
            fade_surface.set_alpha(self.fade_alpha)
            fade_surface.fill((0,0,0))
            self.screen.blit(fade_surface,(0,0))


        # Flip display in all cases
        pygame.display.flip()

    
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


    # Draw overlays on top of player later


        # for index, row in enumerate(self.world_map):
        #     for col, tile in enumerate(row):
        #         x = col * config.TILE_SIZE - self.camera_x
        #         y = index * config.TILE_SIZE - self.camera_y
        #         if -config.TILE_SIZE < x < config.WIDTH and -config.TILE_SIZE < y < config.HEIGHT:
        #             if tile != '':
        #                 surface.blit(config.tile_images[tile], (x, y))

    #logic for overlay tiles
    # def draw_overlays(self, surface):
    #     for y, row in enumerate(self.world_map):
    #         for x, tile in enumerate(row):
    #             if tile in config.overlay_tiles:
    #                 screen_x = x * config.TILE_SIZE - self.camera_x
    #                 screen_y = y * config.TILE_SIZE - self.camera_y

    #                 # Get overlay image
    #                 overlay = config.overlay_tiles[tile]

    #                 # Create a clipped version to only cover bottom half of tile
    #                 clipped_overlay = overlay.subsurface((0, overlay.get_height() // 2, overlay.get_width(), overlay.get_height() // 2))

    #                 # Blit only the bottom half (covers player's feet)
    #                 surface.blit(clipped_overlay, (screen_x, screen_y + overlay.get_height() // 2))




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
        self.font = pygame.font.SysFont(None, 28)
        self.options = ["Party", "Items", "Save Game"]
        self.selected_index = 0
        self.width = 200
        self.margin = 20

    def draw(self, screen):
        # Panel position (right side)
        panel_rect = pygame.Rect(
            self.game.screen.get_width() - self.width, 
            0, 
            self.width, 
            self.game.screen.get_height()
        )

        # Draw white background panel
        pygame.draw.rect(screen, (255, 255, 255), panel_rect)

        # Optional: Draw border
        pygame.draw.rect(screen, (0, 0, 0), panel_rect, 3)

        # Title
        # title_surf = self.font.render("Menu", True, (0, 0, 0))
        # screen.blit(title_surf, (panel_rect.x + self.margin, 20))

        # Options
        for i, option in enumerate(self.options):
            color = (0, 0, 255) if i == self.selected_index else (0, 0, 0)
            option_surf = self.font.render(option, True, color)
            screen.blit(option_surf, (panel_rect.x + self.margin, 60 + i * 40))
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_w:
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key == pygame.K_s:
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key == pygame.K_j:  # j -> a button
                selected = self.options[self.selected_index]
                if selected == "Party":
                    print("Viewing party...")  # placeholder
                elif selected == "Save Game":
                    print("Game saved!")  # placeholder
                elif selected == "Items":
                    print("Viewing items...")  # placeholder
            elif event.key == pygame.K_i:  # allow M to also close the menu
                self.game.state = "world"


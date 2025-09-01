############
### Game ###
############
import pygame
from player import Player
import os 
import csv
import config
from screens import *
from data import *
import random
import math

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
        self.dino_frames = {}
        for base in ("Vusion", "Anemamace", "Corlave"):
            img1 = pygame.image.load(config.ENCOUNTER_DINOS_PATHS[base]).convert_alpha()
            img2 = pygame.image.load(config.ENCOUNTER_DINOS_PATHS[base + "2"]).convert_alpha()
            self.dino_frames[base] = [img1, img2]
        self.active_dino_index = 0
        self.PARTY_LIMIT = 5
        self.box_dinos = []  # dinos stored in the box
        self.player_dino_images = {name: load_image(path, alpha=True) for name, path in config.PLAYER_DINO_PATH.items()}
        self.player_dinos = [
            self.create_dino('Vusion', 12),
            self.create_dino('Vusion', 3),
            self.create_dino('Corlave', 5),
            self.create_dino('Corlave', 16)
        ]
        




        # MENU
        self.menu = Menu(self)
        self.party_screen = PartyScreen(self)  # <-- pass game, not fonts
        self.party_screen.reset()

        # ITEMS ON MAP
        self.item_image = pygame.image.load(config.ITEMS["DinoPod"]['icon']).convert_alpha()
        self.items_on_map = {(18, 57): 'DinoPod', (18, 56): 'DinoPod', (18,41): 'DinoPod'}
        self.inventory = {item: 0 for item in config.ITEMS.keys()}
        self.item_icons = {key: pygame.image.load(data["icon"]).convert_alpha() for key, data in config.ITEMS.items()}
        self.item_descriptions = {key: data["description"] for key, data in config.ITEMS.items()}
        self.items_screen = ItemsScreen(self.inventory, self.item_icons, self.item_descriptions, self.fonts)
        self.items_screen.reset()


        #MAP BUILDINGS/OBJECTS
        self.entities = pygame.sprite.Group()     # non-animated world objects
        self.entity_colliders = []                # list of rects (or keep sprites to check .rect)
        self.solid_tiles = set()   # tiles that are always collidable (buildings, rocks, etc.)
        self.map_entities = []

            ### entities
        self.dinocenter_img = pygame.image.load(config.MAP_ENTITY_PATH['dinocenter']).convert_alpha()
        self.dinocenter_img = pygame.transform.scale(self.dinocenter_img, (config.TILE_SIZE *5, config.TILE_SIZE *5)) # for re-scaling
        dcx, dcy = 36,28 
        dinocenter = config.MapEntity(self.dinocenter_img, dcx,dcy, config.TILE_SIZE, solid = True)
        self.entities.add(dinocenter)
        self._add_solid_rect_as_tiles(dinocenter.rect)
        self._add_map_entity('dinocenter', self.dinocenter_img, dcx, dcy)






        
        # MESSAGE BOX
        self.message_box = MessageBox(config.WIDTH, config.HEIGHT, self.fonts)
        self._post_catch_message = None  # Initialize this variable

        #LEVEL UP
        self.level_up_ui = None


        #BATTLES
        self.awaiting_switch = False   # waiting for player to pick a replacement during encounter
        self.current_turn = None      # 'player' or 'enemy'
        self.encounter_anim = None



    ######## COLLISION ASSETS HELPER ##########
    def _add_solid_rect_as_tiles(self, rect):
        ts = config.TILE_SIZE
        left   = rect.left   // ts
        right  = (rect.right  - 1) // ts
        top    = rect.top    // ts
        bottom = (rect.bottom - 1) // ts
        for ty in range(top, bottom + 1):
            for tx in range(left, right + 1):
                self.solid_tiles.add((tx, ty))
    
    def _add_map_entity(self, name, image, tile_x, tile_y):
        """Place an entity at tile coords (tile_x, tile_y). Registers its rect and blocked tiles."""
        ts = config.TILE_SIZE
        img = image
        rect = img.get_rect()
        # Position top-left at the tile coordinates (adjust if your art's anchor differs)
        rect.topleft = (tile_x * ts, tile_y * ts)

        # Save entity
        ent = {"name": name, "image": img, "tile": (tile_x, tile_y), "rect": rect}
        self.map_entities.append(ent)

        # Register all tiles the rect covers as solid
        left   = rect.left   // ts
        right  = (rect.right  - 1) // ts
        top    = rect.top    // ts
        bottom = (rect.bottom - 1) // ts
        for ty in range(top, bottom + 1):
            for tx in range(left, right + 1):
                self.solid_tiles.add((tx, ty))
        

        # solid_top = bottom  # only the lowest row
        # for ty in range(solid_top, bottom + 1):
        #     for tx in range(left, right + 1):
        #         self.solid_tiles.add((tx, ty))



    ############ PLAYERS DINO'S ###########
    def create_dino(self, name, level):
        from data import DINO_DATA, MOVE_DATA
        base_stats = DINO_DATA[name]['stats']  # Example: { "hp": 35, "attack": 20, "defense": 15, "speed": 18 }
        p = 1.4  # Adjust growth curve for HP if needed
            
        max_hp = HP_Base(base_stats["health"], level, p)
        attack = Base_Stats(base_stats["attack"], level)
        defense = Base_Stats(base_stats["defense"], level)
        speed = Base_Stats(base_stats["speed"], level)
            
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
            "hp": max_hp,
            "max_hp": max_hp,
            "attack": attack,
            "defense": defense,
            "speed": speed,
            "moveset": moves_with_data,  # <-- now moves are full dictionaries with stats
            "moves": [move for lvl, move in DINO_DATA[name]['moves'].items() if lvl <= level],
            "image": self.player_dino_images[name],
            "frames": self.dino_frames.get(name),
            "xp": 0,  # Start with 0 XP earned for this level
            "xp_to_next": LevelXP(level + 1) - LevelXP(level),  # XP required for next level
            # "xp": LevelXP(level),  # Start at XP for this level #### actually no we want to start at 0 for each level when aqcuired
            "xp_to_next_total": LevelXP(level + 1),  # XP total required for next level
            "displayed_xp": 0,  # For smooth animation


        }
    


    def add_xp(self, dino, amount):
        dino["xp"] += amount

        # Check if they leveled up
        leveled_up = False
        while dino["xp"] >= dino["xp_to_next"]:
            leveled_up = True
            dino['xp'] = dino['xp'] - dino['xp_to_next'] #bring xp back to scale with level

            
            # Save old stats for UI
            old_level = dino["level"]
            old_stats = {
                "hp": HP_Base(dino["base_hp"], old_level),
                "attack": Base_Stats(dino["base_attack"], old_level),
                "defense": Base_Stats(dino["base_defense"], old_level),
                "speed": Base_Stats(dino["base_speed"], old_level)
            }

            # Increase level
            dino["level"] += 1

            # Calculate new XP threshold
            dino["xp_to_next"] = dino['xp_to_next']

            # Save new stats for UI
            new_stats = {
                "hp": HP_Base(dino["base_hp"], dino["level"]),
                "attack": Base_Stats(dino["base_attack"], dino["level"]),
                "defense": Base_Stats(dino["base_defense"], dino["level"]),
                "speed": Base_Stats(dino["base_speed"], dino["level"])
            }

            # Create level-up UI screen to block inputs
            self.level_up_ui = LevelUpUI(dino, old_stats, new_stats)
            break  # Only show one popup per XP award

        return leveled_up
    

    def award_xp(self, dino, amount):
        """Give XP to a single dino and handle level-ups + evolution."""
        dino['xp'] += amount

        while dino['xp'] >= dino['xp_to_next']:
            base_stats = DINO_DATA[dino["name"]]['stats']
            prev_hp = HP_Base(base_stats['health'], dino['level'])

            # Use up the XP for this level
            dino['xp'] -= dino['xp_to_next']
            dino['level'] += 1

            # Update xp_to_next
            dino['xp_to_next'] = LevelXP(dino['level']+1) - LevelXP(dino['level'])

            # Recalculate stats
            dino['max_hp'] = HP_Base(base_stats["health"], dino['level'])
            dino['attack'] = Base_Stats(base_stats["attack"], dino['level'])
            dino['defense'] = Base_Stats(base_stats["defense"], dino['level'])
            dino['speed'] = Base_Stats(base_stats["speed"], dino['level'])

            # Heal by the HP gained
            dino['hp'] += (dino['max_hp'] - prev_hp)

            # Level-up message
            self.message_box.queue_messages(
                [f"{dino['name']} grew to Lv {dino['level']}!"], wait_for_input=True
            )

            # Evolution check
            evo_target = self.check_evolution(dino)
            if evo_target:
                self.start_evolution(dino, evo_target)
                break  # stop after first evo trigger so the queued evolution runs cleanly




    # ## XP LOGIC
    # def add_xp(self, dino, earned_xp,level):
    #     earned_xp = 0 #placeholder for when we store it from battles
    #     dino["xp"] += earned_xp

    #     # Check if level-up
    #     level_xp = int(LevelXP(dino['level'])) #total xp earned at level
    #     currentxp = int(int(LevelXP(dino['level']))) + earned_xp #total xp earned at level plus xp from battles
    #     next_level_xp = int(LevelXP(dino['level'+1])) #total xp needed for next level
    #     if currentxp > next_level_xp:
    #         dino["level"] = next_level_xp
    #         # Optional: update stats on level-up
    #         print(f"{dino['name']} leveled up to {dino['level']}!")



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



    
    def queue_messages(self, messages, post_action=None):
        """
        Queue up one or more messages for sequential display.
        Pauses gameplay until all are clicked through.
        post_action: a function or string action to run after all messages finish.
        """
        if isinstance(messages, str):
            messages = [messages]
        self.message_queue = messages
        self.processing_messages = True
        self.post_message_action = post_action
        self.message_box.show(self.message_queue.pop(0), wait_for_input=True)
    

        #Encounter Zones
    def get_player_zone(self,player_x, player_y):
        # You could use ranges or a separate tile map for zone info
        if 26 < player_y < 67 and 2 < player_x < 42:
            return "starter_grass"
        elif 90 <= player_y < 120:
            return "deep_jungle"
        elif player_y >= 200:
            return "volcano_top"
        return None
    

    ### EVOLUTIONS
    def check_evolution(self, dino):
        data = DINO_DATA[dino['name']]
        evo_table = data.get('evolve')

        if not evo_table:
            return None

        # Find if level matches an evolution
        for evo_level, evo_target in evo_table.items():
            if dino['level'] >= evo_level:
                return evo_target
        return None
        
    def do_evolution(self, dino, new_name):
        old_name = dino['name']
        level = dino['level']

        # HP ratio
        hp_ratio = dino['hp'] / dino['max_hp'] if dino.get('max_hp', 0) > 0 else 1.0

        # Pull new species data
        new_data = DINO_DATA[new_name]
        base_stats = new_data['stats']

        # Update identity
        dino['name'] = new_name
        dino['stats'] = base_stats

        # Update sprite + animation frames
        dino['image'] = self.player_dino_images[new_name]  # single image for menus/world
        if new_name in self.dino_frames:
            dino['frames'] = self.dino_frames[new_name]  # for encounter animations

        # Recalculate stats
        dino['max_hp']  = HP_Base(base_stats['health'], level)
        dino['attack']  = Base_Stats(base_stats['attack'], level)
        dino['defense'] = Base_Stats(base_stats['defense'], level)
        dino['speed']   = Base_Stats(base_stats['speed'], level)

        # Scale HP proportionally
        dino['hp'] = max(1, int(dino['max_hp'] * hp_ratio))

        # Update moves
        # Ensure 'moves' exists
        if 'moves' not in dino:
            dino['moves'] = []

        # Gather old moves
        old_moves = dino['moves'][:]

        # Get new moves learnable at current level
        learnable = [move for lvl, move in new_data['moves'].items() if lvl <= level]

        # Merge old moves with learnable, preserving order
        for move in learnable:
            if move not in old_moves:
                old_moves.append(move)

        # Assign back
        dino['moves'] = old_moves
        # old_moves = dino.get('moves', [])
        # learnable = [move for lvl, move in new_data['moves'].items() if lvl <= level]
        # dino['moves'] = list(set(old_moves + learnable))
        

        # --- Rebuild moveset for UI preview ---
        dino['moveset'] = []
        for move_name in dino['moves']:
            move_data = MOVE_DATA.get(move_name, {})
            dino['moveset'].append({
                "name": move_name,
                "type": move_data.get("type", "normal"),
                "damage": move_data.get("damage", 0),
                "accuracy": move_data.get("accuracy", 100),
            })

        return old_name, new_name



    def start_evolution(self, dino, evo_target):
        old_name = dino['name']
        new_name = evo_target

        self.message_box.queue_messages(
            [f"What? {old_name} is evolving!", f"Congratulations! Your {old_name} evolved into {new_name}!"],
            on_complete=lambda: self.do_evolution(dino, new_name)
        )






    ###### TRIGGER ENCOUNTER LOGIC ##########
    def trigger_encounter(self):
        print('Encounter Trigger')
        self.fading = True
        self.fade_alpha = 0

        tile_x = self.player.rect.x // config.TILE_SIZE
        tile_y = self.player.rect.y // config.TILE_SIZE
        zone = self.get_player_zone(tile_x, tile_y)

        if zone in ENCOUNTER_ZONES:
            zone_data = ENCOUNTER_ZONES[zone]
            dino_key = random.choice(zone_data["dinos"])
            level = random.randint(*zone_data["level_range"])
        else:
            print("No valid zone found, using fallback encounter.")
            dino_key = "Anemamace"
            level = random.randint(12, 20)

        self.enemy_dino = self.create_dino(dino_key, level)

        self.encounter_ui = EncounterUI(self.fonts)
        self.encounter_text = f"A wild {dino_key} appeared!"
        self.encounter = Encounter(self.fonts, dino_key)
        self.message_queue = []
        self.processing_messages = False
        self.post_message_action = None

        # self.set_first_turn()
        frames = self.dino_frames.get(self.enemy_dino['name'], [self.enemy_dino['image']])
        # Start a short "intro" animation
        now = pygame.time.get_ticks()
        self.encounter_anim = {
            "frames": frames,
            "frame_idx": 0,
            "last_switch": now,
            "interval": 250,    # switch frames every 250ms
            "start_time": now,
            "duration": 1000    # animate for 1s (adjust)
        }

        # self.queue_messages(
        #     [f"A wild {self.enemy_dino['name']} appeared!", "What will you do?"]
        # )


    # def set_first_turn(self):
    #     p = self.player_dinos[self.active_dino_index]
    #     e = self.enemy_dino
    #     p_spd = max(0, p.get('speed', 0))
    #     e_spd = max(0, e.get('speed', 0))

    #     if p_spd > e_spd:
    #         self.current_turn = 'player'
    #     elif e_spd > p_spd:
    #         self.current_turn = 'enemy'
    #     else:
    #         self.current_turn = random.choice(['player', 'enemy'])  # speed tie


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
            if self.message_box.visible:
                self.message_box.handle_event(event)
                return  # Block all other inputs until messages are done

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
                elif result == 'used': #stay with pass
                    # pass # wait for message box interaction
                    self.pop_state()
                    self.items_screen.reset()


            # ---- ENCOUNTER ----
            elif self.state == 'encounter':
                active = self.player_dinos[self.active_dino_index]

                # 1) If active dino fainted and swap not yet requested
                if active.get('hp', 0) <= 0 and not getattr(self, "awaiting_switch", False):
                    alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
                    if alive:
                        # Queue fainted message, then request player swap
                        self.message_box.queue_messages(
                            [f"{active['name']} fainted!"],
                            wait_for_input=True,
                            on_complete=lambda: self.request_party_swap(active['name'])
                        )
                        self.awaiting_switch = True  # set flag so input is blocked until swap
                    else:
                        # No alive dinos → blackout
                        if self.awaiting_switch == False:
                            self.message_box.queue_messages(
                                ["You blacked out!"],
                                wait_for_input=True,
                                on_complete=self.pop_to_world
                            )
                        else:
                            pass
                    
                    return  # stop processing any further input this frame

                # 2) Block inputs if message box is waiting for player to click
                if self.message_box.visible and self.message_box.wait_for_input:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                        # Ignore run attempts during message
                        return
                    else:
                        self.message_box.handle_event(event)
                        return

                # 3) Block inputs while awaiting a forced party swap
                if getattr(self, "awaiting_switch", False):
                    # PartyScreen will handle selection; ignore other inputs
                    return

                # 4) Normal encounter input handling
                result = self.encounter_ui.handle_input(event, active)

                # 5) Process moves selected in fight menu
                if isinstance(result, str) and result.startswith("UseMove:"):
                    move_name = result.split("UseMove:", 1)[1]
                    self.use_player_move_by_name(move_name)  # damage, fainting, xp handled here
                    return

                # 6) Other encounter commands
                if result == "Fight":
                    print("Fight selected!")
                elif result == "Run":
                    self.queue_messages([f"You ran away safely!"], post_action="return_to_world")
                    self.pop_to_world()
                    print("Run away!")
                elif result == "Bag":
                    self.push_state('items')
                    print("Bag Opening")
                elif result == 'Party':
                    self.push_state('party')
                    if getattr(self, "after_swap", False):
                        self.after_swap = False
                        self.enemy_turn()   # enemy gets to move after your swap
                    print("Switching Dino")


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
            self.message_box.queue_messages([f'Picked up a {item_name}!'], wait_for_input=True)
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
            for dino in self.player_dinos:
                if dino.get('xp_gain_pending', False):
                    if dino['displayed_xp'] < dino['xp']:
                        dino['displayed_xp'] += min(2, dino['xp'] - dino['displayed_xp'])
                    else:
                        dino['xp_gain_pending'] = False  # Stop animating when done



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
            if self.encounter_anim:
                anim = self.encounter_anim
                now = pygame.time.get_ticks()

                # Advance frame
                if now - anim["last_switch"] >= anim["interval"]:
                    anim["frame_idx"] = (anim["frame_idx"] + 1) % len(anim["frames"])
                    anim["last_switch"] = now

                frame = anim["frames"][anim["frame_idx"]]
                self.encounter.current_dino_surface = frame  # <- keep updating Encounter’s surface
                self.encounter.draw(self.screen)

                # End animation
                if now - anim["start_time"] >= anim["duration"]:
                    self.encounter_anim = None
                    # Lock to first idle frame
                    self.encounter.current_dino_surface = anim["frames"][0]
                    self.enemy_dino["image"] = anim["frames"][0]
                    self.message_box.queue_messages(
                        [f"A wild {self.enemy_dino['name']} appeared!", "What will you do?"],
                        wait_for_input=True
                    )
            else:
                # No anim -> just draw encounter
                self.encounter.draw(self.screen)

            # UI on top
            self.encounter_ui.draw(
                self.screen,
                self.player_dinos[self.active_dino_index],
                self.enemy_dino,
                self.encounter_text
            )



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
        
        # MAP ENTITIES
        # draw map entities (dinocenter, etc.) on top of tiles/items
        for ent in self.map_entities:
            ex = ent['rect'].x - self.camera_x
            ey = ent['rect'].y - self.camera_y
            surface.blit(ent['image'], (ex, ey))


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





    




    def attempt_catch(self):
        # consume a pod
        self.inventory["DinoPod"] = max(0, self.inventory["DinoPod"] - 1)
        pod_rate = config.ITEMS["DinoPod"]["catch_rate"]
        success = random.random() < pod_rate

        if success:
            # Build the caught dino from base data (preserve current battle HP)
            base_dino = self.create_dino(self.enemy_dino["name"], self.enemy_dino["level"])
            base_dino["hp"] = min(self.enemy_dino["hp"], base_dino["max_hp"])
            base_dino["xp"] = 0

            # Who gets XP? All party dinos with HP > 0
            alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
            active = self.player_dinos[self.active_dino_index] if self.player_dinos else None

            # Calculate XP (50% for catches)
            if alive and active is not None:
                xp_gain = calculate_xp_gain(
                    player_level=active['level'],
                    opponent_level=self.enemy_dino['level'],
                    state_multiplier=0.5,
                    party_size=len(alive)
                )

                # Give XP: active gets +30%
                for d in alive:
                    bonus = 1.3 if d is active else 1.0
                    self.award_xp(d, int(round(xp_gain * bonus)))

            # After XP, see who should evolve
            to_evolve = []
            for d in self.player_dinos:
                target = self.check_evolution(d)
                if target:
                    to_evolve.append((d, target))

            # Put the caught dino into party or box
            if len(self.player_dinos) < self.PARTY_LIMIT:
                self.player_dinos.append(base_dino)
                added_msg = f"{self.enemy_dino['name']} was added to your party!"
            else:
                self.box_dinos.append(base_dino)
                added_msg = f"{self.enemy_dino['name']} was sent to your Box!"

            # Build catch summary messages
            msgs = [f"You caught {self.enemy_dino['name']}!", added_msg]
            if alive and active is not None:
                msgs.append(f"{active['name']} has gained {int(round(xp_gain * 1.3))} XP!")
                if len(alive) > 1:
                    msgs.append(f"Each party dino gained {xp_gain} XP!")

            # Chain: show catch msgs -> run evolutions (if any) -> pop to world
            def run_evolutions(i=0):
                if i >= len(to_evolve):
                    # done with evolutions: return to world
                    self.pop_to_world()
                    return

                dino, target = to_evolve[i]
                old_name = dino['name']

                def do_next():
                    # Perform the actual evolution
                    old_species, new_species = self.do_evolution(dino, target)

                    # Show the "congratulations" message AFTER stats update
                    self.message_box.queue_messages(
                        [f"Congratulations! Your {old_species} evolved into {new_species}!"],
                        wait_for_input=True,
                        on_complete=lambda: run_evolutions(i + 1)
                    )

                # First show the "is evolving" message
                self.message_box.queue_messages(
                    [f"What? {old_name} is evolving!"],
                    wait_for_input=True,
                    on_complete=do_next
                )
            self.message_box.queue_messages(
            msgs,
            wait_for_input=True,
            on_complete=lambda: run_evolutions(0)  # start evolution chain
        )

            return

        # ---- FAIL: break free -> enemy turn after dialog ----
        self.message_box.queue_messages(
            [f"{self.enemy_dino['name']} broke free!"],
            wait_for_input=True,
            on_complete=self._enemy_turn  # pass the function, don’t call it here
        )
        return





















    
    # def attempt_catch(self):
    #     msgs = []
    #     self.inventory["DinoPod"] = max(0, self.inventory["DinoPod"] - 1)
    #     pod_rate = config.ITEMS["DinoPod"]["catch_rate"]
    #     success = random.random() < pod_rate
    #     if success:
    #         # caught_dino = self.create_dino(
    #         #     self.enemy_dino["name"], 
    #         #     self.enemy_dino["level"]
    #         # )
    #         # # caught_dino = self.enemy_dino.copy()
    #         # caught_dino['xp'] = 0
    #         # caught_dino['displayed_xp'] = 0
    #         # Rebuild full data for party, but preserve current stats like HP
    #         base_dino = self.create_dino(self.enemy_dino["name"], self.enemy_dino["level"])
    #         # Preserve damaged HP from battle
    #         base_dino["hp"] = min(self.enemy_dino["hp"], base_dino["max_hp"])  # just in case  
    #         # base_dino["xp"] = self.enemy_dino.get("xp", 0)  # preserve XP if you track it
    #         base_dino["xp"] = 0  # preserve XP if you track it


    #         alive_dinos = [d for d in self.player_dinos if d.get('hp', 0) > 0]
    #         if not alive_dinos:
    #             return
            

    #         #Active Dino
    #         active = self.player_dinos[self.active_dino_index]
            

    #         # Calculate XP
    #         xp_gain = calculate_xp_gain(
    #             player_level=self.player_dinos[self.active_dino_index]['level'],
    #             opponent_level=self.enemy_dino['level'],
    #             state_multiplier=.5, # 50% less xp for catching 
    #             party_size=len(alive_dinos)
    #         )

    #                     # Award XP + trigger animation
    #                     # Active Dino
    #         active = self.player_dinos[self.active_dino_index]

    #         # Calculate XP
    #         xp_gain = calculate_xp_gain(
    #             player_level=active['level'],
    #             opponent_level=self.enemy_dino['level'],
    #             state_multiplier=.5, # 50% less xp for catching 
    #             party_size=len(alive_dinos)
    #         )

    #         # Give XP
    #         for dino in alive_dinos:
    #             if dino is active:
    #                 self.award_xp(dino, int(round(xp_gain * 1.3)))
    #             else:
    #                 self.award_xp(dino, xp_gain)
    #                 # return msgs
            
    # # Decide destination for the new dino
    #         if len(self.player_dinos) < self.PARTY_LIMIT:
    #             self.player_dinos.append(base_dino)
    #             added_msg = f"{self.enemy_dino['name']} was added to your party!"
    #         else:
    #             self.box_dinos.append(base_dino)
    #             added_msg = f"{self.enemy_dino['name']} was sent to your Box!"


    #         # Messages and return
    #         if len(self.player_dinos) > 2:
    #             self.message_box.queue_messages(
    #                 [
    #                  f"You caught {self.enemy_dino['name']}!",
    #                 added_msg,
    #                 f"{active['name']} has gained {int(xp_gain * 1.3)} XP!",
    #                 f"Each party dino gained {xp_gain} XP!"

    #                 ], wait_for_input= True, on_complete=self.pop_to_world
    #             )
    #         else: 
    #             self.message_box.queue_messages(
    #                 [
    #                     f"You caught {self.enemy_dino['name']}!",
    #                     added_msg,
    #                     f"{active['name']} has gained {int(xp_gain * 1.3)} XP!"
    #                 ],
    #                 wait_for_input=True,
    #                 on_complete=self.pop_to_world
    #             )

            
    #     else:
    #         # Fail case: stay in encounter
    #         self.message_box.queue_messages(
    #             [f"{self.enemy_dino['name']} broke free!"],wait_for_input=True, on_complete=lambda: self._enemy_turn()

    #         )
    #         #If not catch, enemy turn to attack -- happens too quick
    #         return 



            
            # # Show message that dino was caught
            # self.message_box.show(f"You caught {self.enemy_dino['name']}!", wait_for_input=True)

            #             # Award XP to all dinos in party
            # xp_gain = calculate_xp_gain(
            #     player_level=max(d['level'] for d in self.player_dinos),
            #     opponent_level=self.enemy_dino['level'],
            #     state_multiplier=1.0,  # catching bonus
            #     party_size=len(self.player_dinos)
            # )

            # for dino in self.player_dinos:
            #     dino['xp_gain_pending'] = True
            #     dino['xp'] += xp_gain
            #     # Check for level-up
            #     new_level = XPtoLevel(dino['xp'])
            #     if new_level > dino['level']:
            #         dino['level'] = new_level
            #         dino['max_hp'] += 5  # optional: increase stats per level
            #         dino['hp'] = dino['max_hp']  # refill on level up
            #         # (optional) learn new moves here
            # self.message_box.show(f"{self.enemy_dino['name']} was caught! Each party dino gained {xp_gain} XP!", wait_for_input= True)



        #     # End encounter and return to world first
        #     self.pop_to_world()

        #     # Prepare the next message after first is dismissed
        #     self._post_catch_message = f"{self.enemy_dino['name']} has been added to your party!"
        # else:
        #     self.message_box.show(f"{self.enemy_dino['name']} broke free!", wait_for_input=True)
        #     self._post_catch_message = None
        #     if 'items' in self.state_stack:
        #         self.pop_state()


    def use_player_move(self, move_index: int):
        """Player uses a move on the wild enemy."""
        if self.message_box.visible:
            return  # avoid double inputs during messages

        attacker = self.player_dinos[self.active_dino_index]
        defender = self.enemy_dino

        # Safety
        if move_index < 0 or move_index >= len(attacker['moveset']):
            return

        move = attacker['moveset'][move_index]
        move_name = move['name']
        power = max(0, move.get('damage', 0))
        acc = move.get('accuracy', 100)
        mtype = move.get('type', 'normal')

        # 1) Accuracy check
        if random.random() * 100 > acc:
            self.message_box.queue_messages(
                [f"{attacker['name']} used {move_name}!", "But it missed!", "What will you do?"],
                wait_for_input=True
            )
            # Enemy gets a turn after miss
            self._enemy_turn()
            return

        # 2) Multipliers
        STAB = stab_multiplier(mtype, attacker['type'])
        eff_val = type_effectiveness_value(mtype, defender['type'])  # 10=neutral
        rnd = random_damage_factor()

        # 3) Compute damage
        # Make sure attack/defense are at least 1 to avoid div-by-zero
        atk = max(1, attacker['attack'])
        dfs = max(1, defender['defense'])
        lvl = max(1, attacker['level'])

        raw_damage = Damage(lvl, atk, power, dfs, STAB, eff_val, rnd)
        dmg = max(1, int(raw_damage)) if power > 0 else 0

        # 4) Apply damage
        defender['hp'] = max(0, defender['hp'] - dmg)

        # 5) Build result messages
        msgs = [f"{attacker['name']} used {move_name}!"]
        if eff_val > 10:
            msgs.append("It's super effective!")
        elif eff_val < 10 and eff_val > 0:
            msgs.append("It's not very effective...")
        elif eff_val <= 0:
            msgs.append("It had no effect...")


        ### AFTER KO ####

        if defender['hp'] <= 0:
            # Enemy fainted
            msgs.append(f"The wild {defender['name']} fainted!")

            xp_gain = calculate_xp_gain(
                player_level=self.player_dinos[self.active_dino_index]['level'],
                opponent_level=defender['level'],
                state_multiplier=.65,
                party_size=len(self.player_dinos)
            )

            level_up_msgs = self._grant_party_xp_and_level_ups(xp_gain)
            msgs.append(f"{attacker['name']} has gained {int(round(xp_gain*1.3))} XP!")
            if len(self.player_dinos) > 1:
                msgs.append(f"Each party dino gained {xp_gain} XP!")
            msgs.extend(level_up_msgs)

            # Evolution check AFTER level-up messages
            def handle_evolutions():
                evolved = False
                for dino in self.player_dinos:
                    evo_target = self.check_evolution(dino)
                    if evo_target:
                        evolved = True
                        self.start_evolution(dino, evo_target)
                        self.pop_to_world()
                if not evolved:
                    self.pop_to_world()

            self.message_box.queue_messages(
                msgs,
                wait_for_input=True,
                on_complete=handle_evolutions
            )
            return  # <- ensures enemy turn does NOT happen if fainted

        else:
            # Enemy survived → enemy’s turn after your messages
            msgs.append("What will you do?")
            self.message_box.queue_messages(
                msgs,
                wait_for_input=True,
                on_complete=self._enemy_turn
            )
            return









        # if defender['hp'] <= 0:
        #     msgs.append(f"The wild {defender['name']} fainted!")
        #     # Award XP to current party on KO
        #     xp_gain = calculate_xp_gain(
        #         player_level=self.player_dinos[self.active_dino_index]['level'],
        #         opponent_level=defender['level'],
        #         state_multiplier=.65,
        #         party_size=len(self.player_dinos)
        #     )
        #     # Level up logic (handles multiple levels)
        #     level_up_msgs = self._grant_party_xp_and_level_ups(xp_gain)
            
        #     msgs.append(f"{attacker['name']} has gained {int(round(xp_gain*1.3))} XP!")
        #     if len(self.player_dinos) > 1:
        #         msgs.append(f"Each party dino gained {xp_gain} XP!")
        #     msgs.extend(level_up_msgs)

        #     ############ EVOLUTIONS ?? ############
        #     for dino in self.player_dinos:
        #         evo_target = self.check_evolution(dino)
        #         if evo_target:
        #             self.start_evolution(dino, evo_target)


        #     # After KO + messages, go back to world
        #     self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=self.pop_to_world)
        #     return print(eff_val, raw_damage)
        # else:
        #     # Not KO — continue with enemy turn after messages
        #     msgs.append("What will you do?")
        #     self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=self._enemy_turn) 
        
    def _enemy_turn(self):
        defender = self.player_dinos[self.active_dino_index]
        attacker = self.enemy_dino

        # If defender already fainted, block enemy turn until swap
        if defender.get('hp', 0) <= 0:
            alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
            if alive:
                self.awaiting_switch = True
                self.message_box.queue_messages(
                    [f"{defender['name']} fainted!"],
                    wait_for_input=True,
                    on_complete=lambda: self.request_party_swap(defender['name'])
                )
            else:
                self.message_box.queue_messages(
                    ["You blacked out!"],
                    wait_for_input=True,
                    on_complete=self.pop_to_world
                )
            return

        # --- Enemy move selection ---
        if not attacker.get('moveset'):
            self.message_box.queue_messages(
                [f"The wild {attacker['name']} is loafing around.", "What will you do?"],
                wait_for_input=True
            )
            return

        move = random.choice(attacker['moveset'])
        mtype = move.get('type', 'normal')
        power = max(0, move.get('damage', 0))
        acc = move.get('accuracy', 100)

        if random.random() * 100 >= acc:
            self.message_box.queue_messages(
                [f"The wild {attacker['name']} used {move['name']}!", "But it missed!", "What will you do?"],
                wait_for_input=True
            )
            return

        STAB = stab_multiplier(mtype, attacker['type'])
        eff_val = type_effectiveness_value(mtype, defender['type'])
        rnd = random_damage_factor()
        atk = max(1, attacker['attack'])
        dfs = max(1, defender['defense'])
        lvl = max(1, attacker['level'])

        dmg = max(1, int(Damage(lvl, atk, power, dfs, STAB, eff_val, rnd))) if power > 0 else 0
        defender['hp'] = max(0, defender['hp'] - dmg)

        msgs = [f"The wild {attacker['name']} used {move['name']}!"]
        if eff_val > 10: msgs.append("It's super effective!")
        elif eff_val < 10 and eff_val > 0: msgs.append("It's not very effective...")
        elif eff_val <= 0: msgs.append("It had no effect...")

        if defender['hp'] <= 0:
            alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
            if alive:
                self.awaiting_switch = True
                msgs.append(f"{defender['name']} fainted!")
                self.message_box.queue_messages(
                    msgs,
                    wait_for_input=True,
                    on_complete=lambda: self.request_party_swap(defender['name'])
                )
                return
            else:
                msgs.append(f"{defender['name']} fainted!")
                msgs.append("You blacked out!")
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=self.pop_to_world)
                return

        msgs.append("What will you do?")
        self.message_box.queue_messages(msgs, wait_for_input=True)


    def _grant_party_xp_and_level_ups(self, xp_gain: int):
        msgs = []
        alive_dinos = [d for d in self.player_dinos if d.get('hp', 0) > 0]
        if not alive_dinos:
            return  # nobody to award
        
    # Split XP across *alive* members only
        per_dino_xp = calculate_xp_gain(
            player_level=self.player_dinos[self.active_dino_index]['level'],
            opponent_level=self.enemy_dino['level'],
            # base_xp=40,
            state_multiplier=.65,
            party_size=len(alive_dinos)  # <<< alive only
        )
        #Active Dino
        active = self.player_dinos[self.active_dino_index]


        # Award XP + trigger animation
        for dino in alive_dinos:
            if dino is active: 
                dino['xp'] += int(round(xp_gain * 1.3))
                # msgs.append((f" {dino['name']} grew to Lv {dino['level']}!"))
            else:

                dino['xp'] += xp_gain
                # new_level = XPtoLevel(dino['xp'])
                while dino['xp'] >= dino['xp_to_next']:
                    base_stats = DINO_DATA[dino["name"]]['stats']
                    prev_hp = HP_Base(base_stats['health'], dino['level'])
                    dino['xp'] = dino['xp'] - dino['xp_to_next']  + 1#recycle through xp for specific new level
                    dino['level'] += 1
                    dino['xp_to_next'] =LevelXP(dino['level']+1) - LevelXP(dino['level'])

                    # p = 1.2
                    dino['max_hp'] = HP_Base(base_stats["health"], dino['level'])
                    dino['attack'] = Base_Stats(base_stats["attack"], dino['level'])
                    dino['defense'] = Base_Stats(base_stats["defense"], dino['level'])
                    dino['speed'] = Base_Stats(base_stats["speed"], dino['level'])
                    # Optional: heal on level up (comment out if you don’t want this)
                    dino['hp'] = (dino['max_hp'] - prev_hp) + dino['hp']

                    msgs.append(f"{dino['name']} grew to Lv {dino['level']}!")
        return msgs
    


    def use_player_move_by_name(self, move_name: str):
        """Find the move by name on the active dino, then delegate to use_player_move(index)."""
        attacker = self.player_dinos[self.active_dino_index]

        # 1) Prefer moveset with full dicts
        for i, m in enumerate(attacker.get('moveset', [])):
            if m.get('name') == move_name:
                self.use_player_move(i)
                return

        # 2) Fallback to plain name list (attacker['moves'])
        for i, n in enumerate(attacker.get('moves', [])):
            if n == move_name:
                self.use_player_move(i)
                return

        # 3) Not found -> message
        self.message_box.queue_messages(
            [f"{attacker['name']} doesn't know {move_name}.", "What will you do?"],
            wait_for_input=True
        )
    
        
    def request_party_swap(self, fainted_name):
        """
        Called when active dino faints.
        Shows a message first, then forces the player to choose a replacement.
        """
        self.awaiting_switch = True

        # Queue the faint message first
        self.message_box.queue_messages(
            [f"{fainted_name} has fainted!"],
            wait_for_input=True,
            on_complete=self._open_party_forced_swap
        )

    def _open_party_forced_swap(self):
        """
        Called after faint message is acknowledged.
        Opens the PartyScreen in forced-swap mode.
        """
        # Push PartyScreen if not already on stack
        if self.state_stack[-1] != 'party':
            self.push_state('party')

        # Ensure PartyScreen knows it's awaiting a forced swap
        self.awaiting_switch = True




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
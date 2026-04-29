import pygame
from player import Player
import os
import csv
import config
from screens import *
from data import *
import random
import math


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
        pygame.display.set_caption('DinoPodds')
        self.clock = pygame.time.Clock()
        self.running = True
        self.state_stack = ['world']

        self.fonts = {name: pygame.font.Font(path, size) for name, (path, size) in config.FONT_DEFS.items()}
        self.tile_images = {key: load_image(path, alpha=True) for key, path in config.TILE_PATHS.items()}

        self.player = Player(spawn_point='home')
        self.all_sprites = pygame.sprite.Group(self.player)

        self.camera_x, self.camera_y = 0, 0
        self.zoom = 1.25
        self.render_surface = pygame.Surface((config.WIDTH // self.zoom, config.HEIGHT // self.zoom))
        self.world_map = self.load_csv_map('MAP_DINO.csv')

        self.fade_alpha = 0
        self.fading = False

        # Dino frames & images
        self.dino_frames = {}
        for base in ("Vusion", "Anemamace", "Corlave"):
            img1 = pygame.image.load(config.ENCOUNTER_DINOS_PATHS[base]).convert_alpha()
            img2 = pygame.image.load(config.ENCOUNTER_DINOS_PATHS[base + "2"]).convert_alpha()
            self.dino_frames[base] = [img1, img2]

        self.active_dino_index = 0
        self.PARTY_LIMIT = 5
        self.box_dinos = []
        self.player_dino_images = {name: load_image(path, alpha=True) for name, path in config.PLAYER_DINO_PATH.items()}
        self.player_dinos = [
            self.create_dino('Vusion', 12),
            self.create_dino('Vusion', 3),
            self.create_dino('Corlave', 5),
            self.create_dino('Corlave', 16),
        ]

        # Screens
        self.menu = Menu(self)
        self.party_screen = PartyScreen(self)
        self.party_screen.reset()

        # Items
        self.item_image = pygame.image.load(config.ITEMS["DinoPod"]['icon']).convert_alpha()
        self.items_on_map = {(18, 57): 'DinoPod', (18, 56): 'DinoPod', (18, 41): 'DinoPod'}
        self.inventory = {item: 0 for item in config.ITEMS.keys()}
        self.item_icons = {key: pygame.image.load(data["icon"]).convert_alpha() for key, data in config.ITEMS.items()}
        self.item_descriptions = {key: data["description"] for key, data in config.ITEMS.items()}
        self.items_screen = ItemsScreen(self.inventory, self.item_icons, self.item_descriptions, self.fonts)
        self.items_screen.reset()

        # Map entities
        self.solid_tiles = set()
        self.map_entities = []
        self.dinocenter_img = pygame.image.load(config.MAP_ENTITY_PATH['dinocenter']).convert_alpha()
        self.dinocenter_img = pygame.transform.scale(self.dinocenter_img, (config.TILE_SIZE * 5, config.TILE_SIZE * 5))
        self._add_map_entity('dinocenter', self.dinocenter_img, 36, 28)

        # Message box
        self.message_box = MessageBox(config.WIDTH, self.fonts)

        # Battle state
        self.awaiting_switch = False
        self.current_turn = None
        self.encounter_anim = None

    # --- Entity / Collision Helpers ---

    def _add_solid_rect_as_tiles(self, rect):
        ts = config.TILE_SIZE
        for ty in range(rect.top // ts, (rect.bottom - 1) // ts + 1):
            for tx in range(rect.left // ts, (rect.right - 1) // ts + 1):
                self.solid_tiles.add((tx, ty))

    def _add_map_entity(self, name, image, tile_x, tile_y):
        ts = config.TILE_SIZE
        rect = image.get_rect()
        rect.topleft = (tile_x * ts, tile_y * ts)
        self.map_entities.append({"name": name, "image": image, "tile": (tile_x, tile_y), "rect": rect})
        self._add_solid_rect_as_tiles(rect)

    # --- State Stack ---

    @property
    def state(self):
        return self.state_stack[-1]

    def push_state(self, state):
        self.state_stack.append(state)

    def pop_state(self):
        if len(self.state_stack) > 1:
            self.state_stack.pop()

    def pop_to_world(self):
        while len(self.state_stack) > 1:
            self.pop_state()

    # --- Dino Creation ---

    def create_dino(self, name, level):
        base_stats = DINO_DATA[name]['stats']
        max_hp  = HP_Base(base_stats["health"], level)
        attack  = Base_Stats(base_stats["attack"], level)
        defense = Base_Stats(base_stats["defense"], level)
        speed   = Base_Stats(base_stats["speed"], level)

        learned_moves = [move for lvl, move in DINO_DATA[name]['moves'].items() if lvl <= level]
        moveset = []
        for move_name in learned_moves:
            m = MOVE_DATA.get(move_name, {})
            moveset.append({
                "name": move_name,
                "type": m.get("type", "normal"),
                "damage": m.get("damage", 0),
                "accuracy": m.get("accuracy", 100),
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
            "moveset": moveset,
            "moves": learned_moves,
            "image": self.player_dino_images[name],
            "frames": self.dino_frames.get(name),
            "xp": 0,
            "xp_to_next": LevelXP(level + 1) - LevelXP(level),
            "displayed_xp": 0,
        }

    # --- XP & Leveling ---

    def award_xp(self, dino, amount):
        dino['xp'] += amount
        while dino['xp'] >= dino['xp_to_next']:
            base_stats = DINO_DATA[dino["name"]]['stats']
            prev_hp = HP_Base(base_stats['health'], dino['level'])
            dino['xp'] -= dino['xp_to_next']
            dino['level'] += 1
            dino['xp_to_next'] = LevelXP(dino['level'] + 1) - LevelXP(dino['level'])
            dino['max_hp']  = HP_Base(base_stats["health"], dino['level'])
            dino['attack']  = Base_Stats(base_stats["attack"], dino['level'])
            dino['defense'] = Base_Stats(base_stats["defense"], dino['level'])
            dino['speed']   = Base_Stats(base_stats["speed"], dino['level'])
            dino['hp'] += dino['max_hp'] - prev_hp
            self.message_box.queue_messages(
                [f"{dino['name']} grew to Lv {dino['level']}!"], wait_for_input=True
            )
            evo_target = self.check_evolution(dino)
            if evo_target:
                self.start_evolution(dino, evo_target)
                break

    def _grant_party_xp_and_level_ups(self, xp_gain):
        """Award XP to all alive party members and return level-up messages."""
        msgs = []
        alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
        if not alive:
            return msgs
        active = self.player_dinos[self.active_dino_index]
        for dino in alive:
            bonus = 1.3 if dino is active else 1.0
            dino['xp'] += int(round(xp_gain * bonus))
            while dino['xp'] >= dino['xp_to_next']:
                base_stats = DINO_DATA[dino['name']]['stats']
                prev_hp = HP_Base(base_stats['health'], dino['level'])
                dino['xp'] -= dino['xp_to_next']
                dino['level'] += 1
                dino['xp_to_next'] = LevelXP(dino['level'] + 1) - LevelXP(dino['level'])
                dino['max_hp']  = HP_Base(base_stats['health'], dino['level'])
                dino['attack']  = Base_Stats(base_stats['attack'], dino['level'])
                dino['defense'] = Base_Stats(base_stats['defense'], dino['level'])
                dino['speed']   = Base_Stats(base_stats['speed'], dino['level'])
                dino['hp'] = dino['hp'] + (dino['max_hp'] - prev_hp)
                msgs.append(f"{dino['name']} grew to Lv {dino['level']}!")
        return msgs

    # --- Evolution ---

    def check_evolution(self, dino):
        evo_table = DINO_DATA[dino['name']].get('evolve')
        if not evo_table:
            return None
        for evo_level, evo_target in evo_table.items():
            if dino['level'] >= evo_level:
                return evo_target
        return None

    def do_evolution(self, dino, new_name):
        old_name = dino['name']
        level = dino['level']
        hp_ratio = dino['hp'] / dino['max_hp'] if dino.get('max_hp', 0) > 0 else 1.0

        new_data = DINO_DATA[new_name]
        base_stats = new_data['stats']

        dino['name'] = new_name
        dino['stats'] = base_stats
        dino['image'] = self.player_dino_images[new_name]
        if new_name in self.dino_frames:
            dino['frames'] = self.dino_frames[new_name]

        dino['max_hp']  = HP_Base(base_stats['health'], level)
        dino['attack']  = Base_Stats(base_stats['attack'], level)
        dino['defense'] = Base_Stats(base_stats['defense'], level)
        dino['speed']   = Base_Stats(base_stats['speed'], level)
        dino['hp'] = max(1, int(dino['max_hp'] * hp_ratio))

        old_moves = dino.get('moves', [])[:]
        for move in [m for lvl, m in new_data['moves'].items() if lvl <= level]:
            if move not in old_moves:
                old_moves.append(move)
        dino['moves'] = old_moves

        dino['moveset'] = []
        for move_name in dino['moves']:
            m = MOVE_DATA.get(move_name, {})
            dino['moveset'].append({
                "name": move_name,
                "type": m.get("type", "normal"),
                "damage": m.get("damage", 0),
                "accuracy": m.get("accuracy", 100),
            })

        return old_name, new_name

    def start_evolution(self, dino, evo_target):
        old_name = dino['name']
        self.message_box.queue_messages(
            [f"What? {old_name} is evolving!",
             f"Congratulations! Your {old_name} evolved into {evo_target}!"],
            on_complete=lambda: self.do_evolution(dino, evo_target)
        )

    # --- Encounter ---

    def get_player_zone(self, player_x, player_y):
        if 26 < player_y < 67 and 2 < player_x < 42:
            return "starter_grass"
        elif 90 <= player_y < 120:
            return "deep_jungle"
        elif player_y >= 200:
            return "volcano_top"
        return None

    def trigger_encounter(self):
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
            dino_key = "Anemamace"
            level = random.randint(12, 20)

        self.enemy_dino = self.create_dino(dino_key, level)
        self.encounter_ui = EncounterUI(self.fonts)
        self.encounter_text = f"A wild {dino_key} appeared!"
        self.encounter = Encounter(self.fonts, dino_key)

        now = pygame.time.get_ticks()
        frames = self.dino_frames.get(self.enemy_dino['name'], [self.enemy_dino['image']])
        self.encounter_anim = {
            "frames": frames,
            "frame_idx": 0,
            "last_switch": now,
            "interval": 250,
            "start_time": now,
            "duration": 1000,
        }

    # --- Map ---

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

            if self.message_box.visible:
                self.message_box.handle_event(event)
                return

            if self.state == 'world':
                self.handle_world_event(event)

            elif self.state == 'menu':
                self.menu.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_i):
                    self.pop_state()

            elif self.state == 'party':
                result = self.party_screen.handle_event(event, self)
                if result == "back":
                    if len(self.state_stack) >= 2 and self.state_stack[-2] == 'menu' and self.state_stack[0] == 'world':
                        self.pop_state()
                        self.pop_state()
                        self.push_state('menu')
                    else:
                        self.pop_state()
                    self.party_screen.reset()
                elif result == 'quit':
                    self.pop_to_world()
                    self.party_screen.reset()

            elif self.state == 'items':
                result = self.items_screen.handle_event(event, self)
                if result == "back":
                    if len(self.state_stack) >= 2 and self.state_stack[-2] == 'menu' and self.state_stack[0] == 'world':
                        self.pop_state()
                        self.pop_state()
                        self.push_state('menu')
                    else:
                        self.pop_state()
                    self.items_screen.reset()
                elif result == 'quit':
                    self.pop_to_world()
                    self.items_screen.reset()
                elif result == 'used':
                    self.pop_state()
                    self.items_screen.reset()

            elif self.state == 'encounter':
                active = self.player_dinos[self.active_dino_index]

                if active.get('hp', 0) <= 0 and not self.awaiting_switch:
                    alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
                    if alive:
                        self.message_box.queue_messages(
                            [f"{active['name']} fainted!"],
                            wait_for_input=True,
                            on_complete=lambda: self.request_party_swap(active['name'])
                        )
                        self.awaiting_switch = True
                    else:
                        self.message_box.queue_messages(
                            ["You blacked out!"], wait_for_input=True, on_complete=self.pop_to_world
                        )
                    return

                if self.awaiting_switch:
                    return

                result = self.encounter_ui.handle_input(event, active)

                if isinstance(result, str) and result.startswith("UseMove:"):
                    self.use_player_move_by_name(result.split("UseMove:", 1)[1])
                    return

                if result == "Run":
                    self.pop_to_world()
                elif result == "Bag":
                    self.push_state('items')
                elif result == 'Party':
                    self.push_state('party')

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    self.set_zoom(self.zoom + 0.5)
                elif event.key == pygame.K_MINUS:
                    self.set_zoom(self.zoom - 0.5)

    def handle_world_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_i:
            self.push_state('menu')
        elif event.key == pygame.K_j:
            self.pickup_item()

    def pickup_item(self):
        px = self.player.rect.x // config.TILE_SIZE
        py = self.player.rect.y // config.TILE_SIZE
        if self.player.facing == "up":    py -= 1
        elif self.player.facing == "down": py += 1
        elif self.player.facing == "left": px -= 1
        elif self.player.facing == "right":px += 1
        if (px, py) in self.items_on_map:
            item_name = self.items_on_map.pop((px, py))
            self.inventory[item_name] += 1
            self.message_box.queue_messages([f'Picked up a {item_name}!'], wait_for_input=True)

    # --- Update ---

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
                    self.push_state('encounter')

    # --- Draw ---

    def draw(self):
        self.render_surface.fill(config.BLACK)

        background_state = 'encounter' if 'encounter' in self.state_stack else self.state_stack[0]
        current_state = self.state

        if background_state == 'world':
            self.draw_map(self.render_surface)
            for sprite in self.all_sprites:
                self.render_surface.blit(sprite.image,
                                         (sprite.rect.x - self.camera_x, sprite.rect.y - self.camera_y))
            scaled_surface = pygame.transform.scale(self.render_surface, (config.WIDTH, config.HEIGHT))
            self.screen.blit(scaled_surface, (0, 0))

        elif background_state == 'encounter':
            self.encounter.draw(self.screen)
            self.encounter_ui.draw(self.screen, self.player_dinos[self.active_dino_index],
                                   self.enemy_dino, self.encounter_text)

        if current_state == 'encounter':
            if self.encounter_anim:
                anim = self.encounter_anim
                now = pygame.time.get_ticks()
                if now - anim["last_switch"] >= anim["interval"]:
                    anim["frame_idx"] = (anim["frame_idx"] + 1) % len(anim["frames"])
                    anim["last_switch"] = now
                frame = anim["frames"][anim["frame_idx"]]
                self.encounter.current_dino_surface = frame
                self.encounter.draw(self.screen)
                if now - anim["start_time"] >= anim["duration"]:
                    self.encounter_anim = None
                    self.encounter.current_dino_surface = anim["frames"][0]
                    self.enemy_dino["image"] = anim["frames"][0]
                    self.message_box.queue_messages(
                        [f"A wild {self.enemy_dino['name']} appeared!", "What will you do?"],
                        wait_for_input=True
                    )
            else:
                self.encounter.draw(self.screen)

            msg_active = self.message_box.visible
            display_text = self.message_box.message if msg_active else self.encounter_text
            self.encounter_ui.draw(self.screen, self.player_dinos[self.active_dino_index],
                                   self.enemy_dino, display_text, show_actions=not msg_active)

        elif current_state in ('menu', 'party', 'items'):
            if background_state == 'world':
                self.draw_overlay()
            if current_state == 'menu':
                self.menu.draw(self.screen)
            elif current_state == 'party':
                self.party_screen.draw(self.screen)
            elif current_state == 'items':
                self.items_screen.draw(self.screen)

        if self.fading:
            fade_surface = pygame.Surface((config.WIDTH, config.HEIGHT))
            fade_surface.set_alpha(self.fade_alpha)
            fade_surface.fill((0, 0, 0))
            self.screen.blit(fade_surface, (0, 0))

        if self.message_box.visible and self.state != 'encounter':
            self.message_box.draw(self.screen)

        pygame.display.flip()

    def draw_overlay(self):
        overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

    def draw_map(self, surface):
        for row_idx, row in enumerate(self.world_map):
            for col_idx, tile in enumerate(row):
                if tile:
                    x = col_idx * config.TILE_SIZE - self.camera_x
                    y = row_idx * config.TILE_SIZE - self.camera_y
                    surface.blit(self.tile_images[tile], (x, y))
        for (x, y), item_name in self.items_on_map.items():
            surface.blit(self.item_icons[item_name],
                         (x * config.TILE_SIZE - self.camera_x, y * config.TILE_SIZE - self.camera_y))
        for ent in self.map_entities:
            surface.blit(ent['image'], (ent['rect'].x - self.camera_x, ent['rect'].y - self.camera_y))

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
        self.render_surface = pygame.Surface((int(config.WIDTH / self.zoom), int(config.HEIGHT / self.zoom)))
        self.update_camera()

    # --- Battle ---

    def attempt_catch(self):
        self.inventory["DinoPod"] = max(0, self.inventory["DinoPod"] - 1)
        success = random.random() < config.ITEMS["DinoPod"]["catch_rate"]

        if success:
            base_dino = self.create_dino(self.enemy_dino["name"], self.enemy_dino["level"])
            base_dino["hp"] = min(self.enemy_dino["hp"], base_dino["max_hp"])
            base_dino["xp"] = 0

            alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
            active = self.player_dinos[self.active_dino_index] if self.player_dinos else None

            if alive and active is not None:
                xp_gain = calculate_xp_gain(
                    player_level=active['level'],
                    opponent_level=self.enemy_dino['level'],
                    state_multiplier=0.5,
                    party_size=len(alive)
                )
                for d in alive:
                    bonus = 1.3 if d is active else 1.0
                    self.award_xp(d, int(round(xp_gain * bonus)))

            to_evolve = [(d, self.check_evolution(d)) for d in self.player_dinos if self.check_evolution(d)]

            if len(self.player_dinos) < self.PARTY_LIMIT:
                self.player_dinos.append(base_dino)
                added_msg = f"{self.enemy_dino['name']} was added to your party!"
            else:
                self.box_dinos.append(base_dino)
                added_msg = f"{self.enemy_dino['name']} was sent to your Box!"

            msgs = [f"You caught {self.enemy_dino['name']}!", added_msg]
            if alive and active is not None:
                msgs.append(f"{active['name']} has gained {int(round(xp_gain * 1.3))} XP!")
                if len(alive) > 1:
                    msgs.append(f"Each party dino gained {xp_gain} XP!")

            def run_evolutions(i=0):
                if i >= len(to_evolve):
                    self.pop_to_world()
                    return
                dino, target = to_evolve[i]
                old_name = dino['name']
                def do_next():
                    old_species, new_species = self.do_evolution(dino, target)
                    self.message_box.queue_messages(
                        [f"Congratulations! Your {old_species} evolved into {new_species}!"],
                        wait_for_input=True,
                        on_complete=lambda: run_evolutions(i + 1)
                    )
                self.message_box.queue_messages(
                    [f"What? {old_name} is evolving!"],
                    wait_for_input=True,
                    on_complete=do_next
                )

            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=lambda: run_evolutions(0))
            return

        self.message_box.queue_messages(
            [f"{self.enemy_dino['name']} broke free!"],
            wait_for_input=True,
            on_complete=self._enemy_turn
        )

    def use_player_move(self, move_index):
        if self.message_box.visible:
            return
        attacker = self.player_dinos[self.active_dino_index]
        defender = self.enemy_dino

        if move_index < 0 or move_index >= len(attacker['moveset']):
            return

        move = attacker['moveset'][move_index]
        move_name = move['name']
        power = max(0, move.get('damage', 0))
        acc   = move.get('accuracy', 100)
        mtype = move.get('type', 'normal')

        if random.random() * 100 > acc:
            self.message_box.queue_messages(
                [f"{attacker['name']} used {move_name}!", "But it missed!", "What will you do?"],
                wait_for_input=True
            )
            self._enemy_turn()
            return

        STAB    = stab_multiplier(mtype, attacker['type'])
        eff_val = type_effectiveness_value(mtype, defender['type'])
        rnd     = random_damage_factor()
        atk     = max(1, attacker['attack'])
        dfs     = max(1, defender['defense'])
        lvl     = max(1, attacker['level'])

        raw = Damage(lvl, atk, power, dfs, STAB, eff_val, rnd)
        dmg = max(1, int(raw)) if power > 0 else 0
        defender['hp'] = max(0, defender['hp'] - dmg)

        msgs = [f"{attacker['name']} used {move_name}!"]
        if eff_val > 10:
            msgs.append("It's super effective!")
        elif 0 < eff_val < 10:
            msgs.append("It's not very effective...")
        elif eff_val <= 0:
            msgs.append("It had no effect...")

        if defender['hp'] <= 0:
            msgs.append(f"The wild {defender['name']} fainted!")
            xp_gain = calculate_xp_gain(
                player_level=self.player_dinos[self.active_dino_index]['level'],
                opponent_level=defender['level'],
                state_multiplier=0.65,
                party_size=len(self.player_dinos)
            )
            level_up_msgs = self._grant_party_xp_and_level_ups(xp_gain)
            msgs.append(f"{attacker['name']} has gained {int(round(xp_gain * 1.3))} XP!")
            if len(self.player_dinos) > 1:
                msgs.append(f"Each party dino gained {xp_gain} XP!")
            msgs.extend(level_up_msgs)

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

            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=handle_evolutions)
        else:
            msgs.append("What will you do?")
            self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=self._enemy_turn)

    def use_player_move_by_name(self, move_name):
        attacker = self.player_dinos[self.active_dino_index]
        for i, m in enumerate(attacker.get('moveset', [])):
            if m.get('name') == move_name:
                self.use_player_move(i)
                return
        for i, n in enumerate(attacker.get('moves', [])):
            if n == move_name:
                self.use_player_move(i)
                return
        self.message_box.queue_messages(
            [f"{attacker['name']} doesn't know {move_name}.", "What will you do?"], wait_for_input=True
        )

    def _enemy_turn(self):
        defender = self.player_dinos[self.active_dino_index]
        attacker = self.enemy_dino

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
                    ["You blacked out!"], wait_for_input=True, on_complete=self.pop_to_world
                )
            return

        if not attacker.get('moveset'):
            self.message_box.queue_messages(
                [f"The wild {attacker['name']} is loafing around.", "What will you do?"], wait_for_input=True
            )
            return

        move  = random.choice(attacker['moveset'])
        mtype = move.get('type', 'normal')
        power = max(0, move.get('damage', 0))
        acc   = move.get('accuracy', 100)

        if random.random() * 100 >= acc:
            self.message_box.queue_messages(
                [f"The wild {attacker['name']} used {move['name']}!", "But it missed!", "What will you do?"],
                wait_for_input=True
            )
            return

        STAB    = stab_multiplier(mtype, attacker['type'])
        eff_val = type_effectiveness_value(mtype, defender['type'])
        rnd     = random_damage_factor()
        atk     = max(1, attacker['attack'])
        dfs     = max(1, defender['defense'])
        lvl     = max(1, attacker['level'])

        dmg = max(1, int(Damage(lvl, atk, power, dfs, STAB, eff_val, rnd))) if power > 0 else 0
        defender['hp'] = max(0, defender['hp'] - dmg)

        msgs = [f"The wild {attacker['name']} used {move['name']}!"]
        if eff_val > 10:   msgs.append("It's super effective!")
        elif 0 < eff_val < 10: msgs.append("It's not very effective...")
        elif eff_val <= 0: msgs.append("It had no effect...")

        if defender['hp'] <= 0:
            alive = [d for d in self.player_dinos if d.get('hp', 0) > 0]
            msgs.append(f"{defender['name']} fainted!")
            if alive:
                self.awaiting_switch = True
                self.message_box.queue_messages(
                    msgs, wait_for_input=True,
                    on_complete=lambda: self.request_party_swap(defender['name'])
                )
            else:
                msgs.append("You blacked out!")
                self.message_box.queue_messages(msgs, wait_for_input=True, on_complete=self.pop_to_world)
            return

        msgs.append("What will you do?")
        self.message_box.queue_messages(msgs, wait_for_input=True)

    def request_party_swap(self, fainted_name):
        self.awaiting_switch = True
        self.message_box.queue_messages(
            [f"{fainted_name} has fainted!"],
            wait_for_input=True,
            on_complete=self._open_party_forced_swap
        )

    def _open_party_forced_swap(self):
        if self.state_stack[-1] != 'party':
            self.push_state('party')
        self.awaiting_switch = True

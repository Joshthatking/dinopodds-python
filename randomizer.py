"""Randomizer mode — every dino the player meets is swapped for a random one.

Anything goes: any species in DINO_DATA (legendaries included) can show up
anywhere, while levels stay exactly as the game sets them.

    Wild grass/water/cave encounters
        Each area (see AREA_ZONES) keeps a pool of the first AREA_POOL_SIZE
        different dinos rolled there. Until the pool is full every encounter
        rolls a fresh random dino; once full, that area only ever spawns
        dinos from its pool — so grinding one patch of grass can't hand out
        every species. Pools are saved with the game.

    Everything else (starters, trainer teams, static/legendary battles,
    gifts and trades, battle partners)
        Picked by `fixed(tag)`: a random dino seeded from the save's seed and
        a tag naming that exact slot, so it's the same dino every time —
        losing to a trainer and coming back, reloading a save, etc.

Game uses this through Game.randomizer (None in Standard mode).
"""
import random
from data import DINO_DATA

AREA_POOL_SIZE = 6

# Encounter zone (data.ENCOUNTER_ZONES) -> area. Zones not listed here are
# their own area. 'palm_water' is split by position — see area_for_zone.
AREA_ZONES = {
    'route1':       ('route1_grass', 'route1+_grass', 'route1_special', 'town1_grass', 'spawn_water'),
    'route2':       ('route2_grass', 'route2_burnt_grass', 'route2_belowcorn'),
    'corn_maze':    ('corn_maze',),
    'route3':       ('route3',),
    'lake_meridian': ('lakeM_snowL', 'lakeM_snowR', 'lake1L', 'lake1R', 'lake_water1'),
    'horizon_cave': ('HC_green', 'HC_ice', 'HC_red', 'HC_water', 'HC_blue'),
    'power_plant':  ('powerplant_outside', 'in_power'),
    'cobalt_cave':  ('cobalt_cave',),
}
ZONE_TO_AREA = {zone: area for area, zones in AREA_ZONES.items() for zone in zones}

# palm_water spans both Route 4 and Palm Port's sea; the "Route 4 | Palm
# Port" banner strip sits at tile x = -85, with Palm Port to its west.
PALM_PORT_EDGE_X = -85


def all_species():
    return sorted(DINO_DATA)


def area_for_zone(zone, tile_x):
    if zone == 'palm_water':
        return 'palm_port' if tile_x < PALM_PORT_EDGE_X else 'route4'
    return ZONE_TO_AREA.get(zone, zone)


class Randomizer:
    def __init__(self, seed=None, area_pools=None):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.area_pools = {area: list(names) for area, names in (area_pools or {}).items()}
        self.species = all_species()

    # ── save / load ───────────────────────────────────────────────────────

    def to_dict(self):
        return {'seed': self.seed, 'area_pools': self.area_pools}

    @classmethod
    def from_dict(cls, data):
        return cls(seed=data.get('seed'), area_pools=data.get('area_pools'))

    # ── picks ─────────────────────────────────────────────────────────────

    def fixed(self, tag):
        """Same random dino every time for the same tag in this save."""
        return random.Random(f"{self.seed}:{tag}").choice(self.species)

    def wild(self, zone, tile_x):
        area = area_for_zone(zone, tile_x)
        pool = self.area_pools.setdefault(area, [])
        if len(pool) < AREA_POOL_SIZE:
            name = random.choice(self.species)
            if name not in pool:
                pool.append(name)
            return name
        return random.choice(pool)

    def starters(self, balls):
        """ball id -> species for the 3 starter balls, all different."""
        balls = sorted(balls)
        picks = random.Random(f"{self.seed}:starters").sample(self.species, len(balls))
        return dict(zip(balls, picks))

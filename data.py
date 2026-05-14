import config
import math
import random

STAT_STAGE_MULT = {
    -6: 0.25, -5: 0.28, -4: 0.33, -3: 0.40,
    -2: 0.50, -1: 0.67,  0: 1.0,
     1: 1.25,  2: 1.50,  3: 2.0,
     4: 2.5,   5: 3.0,   6: 3.5,
}

TRAINER_DATA = {
    'amber': {
        'name': 'Amber',
        'dinos': {0: ('Anemamace', 7), 1: ('Vusion', 8)},
        'dialog': {
            'default': ['Hey Trainer!', 'Lets Battle!'],
            'defeated': ['You are very strong!', "Let's fight again sometime?"]},
        'directions': ['down'],
        'look_around': True,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 150,
        'rank': 'medium',
    },
    'basic_trainer': {
        'name': 'Rex',
        'partner': 'basic_trainer2',
        'dinos': {0: ('Prowscar', 10)},
        'dialog': {'default': ["Two against two!", "Double battle, go!"]},
        'directions': ['down'],
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 250,
        'rank': 'lowest',
    },
    'basic_trainer2': {
        'name': 'Luke',
        'partner': 'basic_trainer',
        'dinos': {0: ('Floravel', 9)},
        'dialog': {'default': ["We fight as one!"]},
        'directions': ['down'],
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 250,
        'rank': 'lowest',
    },
    'basic_trainer_girl': {
        'name': 'Lila',
        'dinos': {0: ('Corlave', 4), 1: ('Creuw', 4)},
        'dialog': {
            'default':  ["Hi do you want to battle with me?", "Get ready!"],
            'defeated': ["Yay thanks for the battle"]
        },
        'directions': ['left'],
        'look_around': True,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 120,
        'rank': 'lowest',
    },
    'ethan': {
        'name': 'Ethan',
        'dinos': {0: ('Creuw', 7)},
        'dialog': {
            'default':  ["I never lose...", "Get ready!"],
            'defeated': ["Dang I gotta do better"]
        },
        'directions': ['up'],
        'look_around': False,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 150,
        'rank': 'lowest',
    },

    'shinji': {
        'name': 'Shinji',
        'dinos': {0: ('Prowscar', 6), 1: ('Vusion', 7)},
        'dialog': {
            'default':  ["Been waiting all day", "Let's Battle!"],
            'defeated': ["Good job, almost at the city!"]
        },
        'directions': ['down'],
        'look_around': False,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 250,
        'rank': 'lowest',
    },
}



DINO_DATA = {
    'Vusion': {
        'stats': {'type': ['dark'], 'health': 120, 'attack': 155, 'defense': 70, 'speed': 125},
        'moves': {0: 'Force Shift', 1: 'Flash', 9: 'Fireball', 15: 'Shadow Veil', 17: 'Conduit Surge', 19: 'Distortion', 23: 'Flame Shatter', 27: 'Binding Curse', 30: 'Void Collapse', 35: 'Haunt'},
        'evolve': None},
    'Anemamace': {
        'stats': {'type': ['aqua','spike'], 'health': 140, 'attack': 110, 'defense': 115, 'speed':90},
        'moves': {0: 'Whirlpool', 1: 'Arise', 8: 'Quick Slash', 17: 'Wave Dash', 19: 'Double Jab', 22: 'Hurricane', 26: 'Ripping Impact'},
        'evolve': None},
    'Corlave': {
        'stats': {'type': ['aqua'], 'health': 80, 'attack': 55, 'defense': 50, 'speed':25},
        'moves': {0: 'Whirlpool', 1: 'Arise', 8: 'Quick Slash', 17: 'Wave Dash', 19: 'Double Jab'},
        'evolve': {17: 'Anemamace'}},
    'Creuw': {
        'stats': {'type': ['flying'], 'health': 50, 'attack': 65, 'defense': 40, 'speed':65},
        'moves': {0: 'Air Strike', 1: 'Arise', 8: 'Force Shift', 15: 'Mach Speed', 18: 'Shadow Veil'},
        'evolve': {15: 'Luna'}},
    'Luna': {
        'stats': {'type': ['flying', 'dark'], 'health': 100, 'attack': 145, 'defense': 70, 'speed':135},
        'moves': {0: 'Air Strike', 1: 'Arise', 8: 'Force Shift', 15: 'Mach Speed', 18: 'Shadow Veil', 22: 'Turbo Booster', 25: 'Wind Fracture' },
        'evolve': None},
    'Prowscar': {
        'stats': {'type': ['dark'], 'health': 50, 'attack': 70, 'defense': 50, 'speed': 70},
        'moves': {0: 'Dark Energy', 1: 'Arise', 12: 'Lock Jaw', 14: 'Double Jab', 21: 'Shadow Veil'},
        'evolve': None},
    'Floravel': {
        'stats': {'type': ['earth'], 'health': 50, 'attack': 50, 'defense': 70, 'speed': 40},
        'moves': {0: 'Vine Snare', 1: 'Arise', 8: 'Boulder Smash', 18: 'Dread Thorn', 23: 'Crusher', 26: 'Synthesis', 28: 'Terraform'},
        'evolve': None},

}




TYPE_DATA = {
    'aqua': {
        'super_eff': ['magma', 'rock'],
        'weak_eff': ['aqua', 'ancient', 'earth'],
        'resist':['aqua', 'ice', 'magma'],
        'weak_to': ['earth', 'lightning'],
        'color': config.AQUA
    },
    'magma': {
        'super_eff': ['earth', 'ice'],
        'weak_eff': ['magma', 'ancient', 'rock', 'aqua'],
        'resist':['magma', 'ice', 'earth'],
        'weak_to': ['aqua', 'rock'],
        'color': config.MAGMA
    },
    'earth': {
        'super_eff': ['aqua', 'rock', 'lighting'],
        'weak_eff': ['earth', 'ancient', 'flying', 'magma'],
        'resist':['earth', 'aqua', 'lightning', 'light'],
        'weak_to': ['magma', 'ice', 'flying', 'spike'],
        'color': config.EARTH
    },
    'dark': {
        'super_eff': ['spike', 'dark'],
        'weak_eff': ['light'],
        'resist':['spike', 'ancient'],
        'weak_to': ['light', 'dark'],
        'color': config.DARK
    },
    'light': {
        'super_eff': ['dark', 'spike'],
        'weak_eff': ['earth'],
        'resist': ['spike', 'dark'],
        'weak_to': ['lightning', 'ancient'],
        'color': config.SOFT_WHITE
    },
    'spike': {
        'super_eff': ['ancient', 'earth', 'rock'],
        'weak_eff': ['dark','light'],
        'resist': ['rock', 'ancient'],
        'weak_to': ['dark', 'flying', 'light'],
        'color': config.SPIKE
    },
    'flying': {
        'super_eff': ['earth', 'spike'],
        'weak_eff': ['rock', 'lightning'],
        'resist': ['earth'],
        'weak_to': ['rock', 'ice', 'lightning'],
        'color': config.FLYING
    },
    'rock': {
        'super_eff': ['magma', 'flying', 'lightning', 'ice'],
        'weak_eff': ['spike', 'rock'],
        'resist': ['flying', 'lightning','ancient'],
        'weak_to': ['aqua', 'earth','spike'],
        'color': config.ROCK
    },
    'lightning': {
        'super_eff': ['flying', 'aqua', 'light'],
        'weak_eff': ['earth', 'rock', 'ancient'],
        'resist': ['flying'],
        'weak_to': ['rock', 'earth'],
        'color': config.LIGHTNING
    },
    'ice': {
        'super_eff': ['earth', 'flying', 'ancient'],
        'weak_eff': ['aqua', 'ice', 'magma'],
        'resist': ['ice'],
        'weak_to': ['rock', 'magma'],
        'color': config.ICE
    },
    'ancient': {
        'super_eff': ['ancient', 'light'],
        'weak_eff': ['spike', 'rock'],
        'resist': ['aqua', 'magma', 'earth', 'lightning'],
        'weak_to': ['ancient', 'ice', 'spike'],
        'color': config.ANCIENT
    }
}

#electric,rock,flying,ancient,ice


TYPE_CHART_VAL = {
    'aqua': {'aqua': 5, 'magma': 20, 'earth': 5, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 20, 'lightning': 10, 'ice': 10, 'ancient': 5},
    'magma': {'aqua': 5, 'magma': 5, 'earth': 20, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 5, 'lightning': 10, 'ice': 20, 'ancient': 5},
    'earth': {'aqua': 20, 'magma': 5, 'earth': 5, 'flying': 5, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 20, 'lightning': 20, 'ice': 10,'ancient': 5},
    'flying': {'aqua': 10, 'magma': 10, 'earth': 20, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 20, 'rock': 5, 'lighting': 5, 'ice': 10,'ancient': 10},
    'dark': {'aqua': 10, 'magma': 10, 'earth': 10, 'flying': 10, 'dark': 20 , 'light': 5, 'spike': 20, 'rock': 10, 'lighting': 10, 'ice': 10,'ancient': 10},
    'light': {'aqua': 10, 'magma': 10, 'earth': 5, 'flying': 10, 'dark': 20 , 'light': 10, 'spike': 20, 'rock': 10, 'lighting': 10, 'ice': 10,'ancient': 10},
    'spike': {'aqua': 10, 'magma': 10, 'earth': 20, 'flying': 10, 'dark': 5 , 'light': 5, 'spike': 10, 'rock': 20, 'lighting': 10, 'ice': 10,'ancient': 20},
    'rock': {'aqua': 10, 'magma': 20, 'earth': 10, 'flying': 20, 'dark': 10 , 'light': 10, 'spike': 5, 'rock': 5, 'lighting': 20, 'ice': 20,'ancient': 10},
    'lightning': {'aqua': 20, 'magma': 10, 'earth': 5, 'flying': 20, 'dark': 10 , 'light': 20, 'spike': 10, 'rock': 5, 'lighting': 10, 'ice': 10,'ancient': 5},
    'ice': {'aqua': 5, 'magma': 5, 'earth': 20, 'flying': 20, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 10, 'lighting': 10, 'ice': 5,'ancient': 20},
    'ancient': {'aqua': 10, 'magma': 10, 'earth': 10, 'flying': 10, 'dark': 5 , 'light': 20, 'spike': 5, 'rock': 5, 'lighting': 10, 'ice': 10,'ancient': 20},



}





MOVE_DATA = {
    #AQUA MOVES
    'Whirlpool': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'aqua'},
    'Hurricane': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'aqua'},
    'Eternal Blue': {'target': 'opponent', 'damage': 90, 'accuracy': 100, 'ability': None, 'type': 'aqua'},

    'Wave Dash':   {'target': 'opponent', 'damage': 45, 'accuracy': 100, 'type': 'aqua',
                    'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 1, 'target': 'self', 'chance': 100}},
    #MAGMA MOVES
    'Fireball': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'magma'},
    'Lava Burst': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'magma'},
    'Solar Flare': {'target': 'opponent', 'damage': 90, 'accuracy': 100, 'ability': None, 'type': 'magma'},

    'Flame Shatter':   {'target': 'opponent', 'damage': 50, 'accuracy': 95, 'type': 'magma',
                    'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': -1, 'target': 'opponent', 'chance': 100}},
    'Magma Boost':  {'target': 'self',     'damage': 0,  'accuracy': 100, 'type': 'magma',
                     'ability': {'kind': 'field', 'effect': 'type_power', 'boost_type': 'magma', 'multiplier': 1.5, 'duration': 4, 'chance': 100}},
    #EARTH MOVES
   'Vine Snare': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'earth'},
    'Dread Thorn': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'earth'},
    'Tree Spin': {'target': 'opponent', 'damage': 80, 'accuracy': 100, 'ability': None, 'type': 'earth'},


    
    'Poison Ivy':   {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'type': 'earth',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -1, 'target': 'opponent', 'chance': 100}},
    'Synthesis':   {'target': 'self', 'damage': 0, 'accuracy': 100, 'type': 'earth',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': 2, 'target': 'self', 'chance': 100}},
    'Terraform':  {'target': 'self',     'damage': 0,  'accuracy': 100, 'type': 'earth',
                     'ability': {'kind': 'field', 'effect': 'type_power', 'boost_type': 'earth', 'multiplier': 1.5, 'duration': 4, 'chance': 100}},
    'Floral Resonance': {'target': 'self', 'damage': 0, 'accuracy': 100, 'type': 'earth',
                     'ability': {'kind': 'heal', 'percent': 25, 'chance': 100}},
    #FLYING MOVES
    'Air Strike': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'flying'},
    'Mach Speed': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'flying'},
    'Wind Fracture': {'target': 'opponent', 'damage': 80, 'accuracy': 100, 'ability': None, 'type': 'flying'},

    'Turbo Booster':   {'target': 'self', 'damage': 0, 'accuracy': 95, 'type': 'flying',
                    'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 2, 'target': 'self', 'chance': 100}},
    'Sky Scorch':   {'target': 'opponent', 'damage': 120, 'accuracy': 90, 'type': 'flying',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -2, 'target': 'self', 'chance': 100}},
    #SPIKE MOVES
    'Lock Jaw': {'target': 'opponent', 'damage': 30, 'accuracy': 90, 'type': 'spike',
                 'ability': {'kind': 'lock', 'turns': 2, 'chance': 100}},
    'Double Jab': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'spike'},
    'Ripping Impact': {'target': 'opponent', 'damage': 50, 'accuracy': 90, 'ability': None, 'type': 'spike', 'pierces_defend': True},
    'Power Fang': {'target': 'opponent', 'damage': 50, 'accuracy': 100, 'ability': None, 'type': 'spike'},
    'Sword Slash': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'spike'},

    'Spike Storm': {'target': 'opponent', 'damage': 110, 'accuracy': 95, 'type': 'spike',
                    'ability': {'kind': 'recoil', 'percent': 25, 'chance': 100}},
    'Quick Slash':  {'target': 'opponent', 'damage': 35, 'accuracy': 100, 'type': 'spike',
                     'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 1, 'target': 'self', 'chance': 100}},


    #ROCK MOVES
    'Boulder Smash': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'rock'},
    'Crusher': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'rock'},

    'Iron Core':   {'target': 'self', 'damage': 0, 'accuracy': 100, 'type': 'rock',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': 2, 'target': 'self', 'chance': 100}},             
    'Momentum':   {'target': 'opponent', 'damage': 45, 'accuracy': 90, 'type': 'rock',
                    'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': 1, 'target': 'self', 'chance': 100}},
    'Crash Impact': {'target': 'opponent', 'damage': 90, 'accuracy': 100, 'type': 'rock',
                     'ability': {'kind': 'recoil', 'percent': 15, 'chance': 100}},

    #LIGHTNING MOVES
    'Thunder Slap': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'lightning'},
    'Volt Storm': {'target': 'opponent', 'damage': 80, 'accuracy': 100, 'ability': None, 'type': 'lightning'},


    'Conduit Surge':  {'target': 'opponent', 'damage': 50, 'accuracy': 90,  'type': 'lightning',
                     'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 2, 'target': 'self', 'chance': 100}},
    'Quantum Flux':  {'target': 'opponent', 'damage': 70, 'accuracy': 85,  'type': 'lightning',
                     'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 1, 'target': 'self', 'chance': 100}},
    'Stun':   {'target': 'opponent', 'damage': 0, 'accuracy': 100, 'type': 'lightning',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -1, 'target': 'opponent', 'chance': 100}},

    #DARK MOVES
    'Force Shift': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None,'type': 'dark'},
    'Dark Energy': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'dark'},
    'Void Collapse': {'target': 'opponent', 'damage': 65, 'accuracy': 90, 'ability': None, 'type': 'dark', 'pierces_defend': True},

    'Distortion':   {'target': 'opponent', 'damage': 5, 'accuracy': 100, 'type': 'dark',
                     'ability': {'kind': 'field', 'effect': 'speed_swap', 'duration': 5, 'chance': 100}},
    'Haunt':   {'target': 'opponent', 'damage': 0, 'accuracy': 100, 'type': 'dark',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -2, 'target': 'opponent', 'chance': 100}},
    'Binding Curse': {'target': 'opponent', 'damage': 25, 'accuracy': 90, 'type': 'dark',
                      'ability': {'kind': 'lock', 'turns': 2, 'chance': 100}},
    'Shadow Veil':   {'target': 'opponent', 'damage': 50, 'accuracy': 100, 'type': 'dark',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': 1, 'target': 'self', 'chance': 100}},
    #LIGHT MOVES
    'Translucent Wave': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'light'},
    'Piercing Light': {'target': 'opponent', 'damage': 60, 'accuracy': 90, 'ability': None, 'type': 'light', 'pierces_defend': True},
    'Spectral Overload': {'target': 'opponent', 'damage': 90, 'accuracy': 100, 'ability': None, 'type': 'light'},

    'Flash':   {'target': 'opponent', 'damage': 0, 'accuracy': 100, 'type': 'light',
                    'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': -1, 'target': 'opponent', 'chance': 100}},
    'Refraction':  {'target': 'self',     'damage': 0,  'accuracy': 100, 'type': 'light',
                     'ability': {'kind': 'field', 'effect': 'type_power', 'boost_type': 'light', 'multiplier': 1.5, 'duration': 4, 'chance': 100}},
   'Gamma Wave':   {'target': 'opponent', 'damage': 80, 'accuracy': 90, 'type': 'light',
                    'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': -2, 'target': 'opponent', 'chance': 100}},
    #ICE MOVES
    'Freeze Blast': {'target': 'opponent', 'damage': 70, 'accuracy': 100, 'ability': None, 'type': 'ice'},
    'Hyperfrost': {'target': 'opponent', 'damage': 55, 'accuracy': 100, 'ability': None, 'type': 'ice', 'pierces_defend': True},

    'Hail Storm': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'type': 'ice',
                   'ability': {'kind': 'dot', 'damage_percent': 8, 'turns': 2,
                               'tick_msg': 'pelted by the raging hail', 'chance': 100}},
    'Frozen Aura': {'target': 'self', 'damage': 10, 'accuracy': 100, 'type': 'ice',
                     'ability': {'kind': 'heal', 'percent': 30, 'chance': 100}},
    #ANCIENT MOVES
    'Raging Pursuit': {'target': 'opponent', 'damage': 55, 'accuracy': 90, 'ability': None, 'type': 'ancient', 'pierces_defend': True},

    'Primal Rage':  {'target': 'opponent', 'damage': 45, 'accuracy': 100, 'type': 'ancient',
                     'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': 1, 'target': 'self', 'chance': 100}},
    'Arise':  {'target': 'self', 'damage': 0, 'accuracy': 100, 'type': 'ancient',
                     'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': 1, 'target': 'self', 'chance': 100}},

    #DEBUFF MOVES
    'Venom Decay':   {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'type': 'ancient',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -1, 'target': 'opponent', 'chance': 100}},


    #HEALING MOVES
    'Ancient Mend': {'target': 'self', 'damage': 0, 'accuracy': 100, 'type': 'ancient',
                     'ability': {'kind': 'heal', 'percent': 25, 'chance': 100}},

    # --- Moves with abilities ---
    # 'Quick Slash':  {'target': 'opponent', 'damage': 35, 'accuracy': 100, 'type': 'dark',
    #                  'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 1, 'target': 'self', 'chance': 100}},
 
    }






################## ENTRANCE DATA ####################
# Map entrance_id (set as a Tiled string property "entrance_id" on each entrance tile)
# to the interior world file and spawn tile coords (tx, ty).
# Add an entry here for every building you create.
ENTRANCE_DATA = {
    'home':       {'world': 'HOME_JET.tmx',        'spawn': (9, 11)},
    'jet_room':   {'world': 'HOME_JET2.tmx',       'spawn': (9, 10)},
    'dinocenter':   {'world': 'DINOCENTER.tmx',       'spawn': (9, 12)},

    # 'house_amber': {'world': 'HOUSE_AMBER.world',  'spawn': (3, 6)},
}

################## ENCOUNTER ZONES ####################
# encounter_data.py or near your config
ENCOUNTER_ZONES = {
    # "grass": {
    #     "dinos": ["Anemamace", "Corlave"],
    #     "level_range": (17, 18)
    # },

    "route1_grass": {
        "dinos": ["Anemamace", "Corlave"],
        "level_range": (3,7)
    },
    "route1+_grass": {
        "dinos": ["Creuw"],
        "level_range": (8, 9)
    },

    "town1_grass": {
        "dinos": ["Luna"],
        "level_range": (15, 18)
    },


        ######## fill more


    "deep_jungle": {
        "dinos": ["Venoshade", "Terraptor", "Leafu"],
        "level_range": (5, 10)
    },
    "volcano_top": {
        "dinos": ["Magmara", "Ashfang", "Crateradon"],
        "level_range": (10, 15)
    }
}


# off from TILED WORLD by -5,26
x_offset = -5
y_offset = 32
ZONE_REGIONS = [
    # (x1, y1, x2, y2, zone_name) in tile coords
    (1+x_offset, -30+y_offset,  18+x_offset, 0+y_offset, "route1_grass"),
    (1+x_offset, -44+y_offset, 18+x_offset, -38+y_offset, "route1+_grass"),
    (1+x_offset, -35+y_offset, 13+x_offset, -31+y_offset, "route1+_grass"),
    (16+x_offset, -37+y_offset, 18+x_offset, -37+y_offset, "town1_grass"),
]

def get_zone_for_tile(tx, ty):
    for x1, y1, x2, y2, zone in ZONE_REGIONS:
        if x1 <= tx <= x2 and y1 <= ty <= y2:
            return zone
    return None





def LevelXP(level):
    return (level*2.3)**2

def XPtoLevel(XP):
    return int(math.sqrt(XP)/2.3)


def calculate_xp_gain(player_level, opponent_level, enemy_name=None, base_xp=7, state_multiplier=1.0):
    if enemy_name and enemy_name in DINO_DATA:
        s = DINO_DATA[enemy_name]['stats']
        base_xp = (s['health'] + s['attack'] + s['defense'] + s['speed']) / 50

    ratio = opponent_level / player_level
    if ratio < 1.0:
        level_factor = max(0.15, ratio ** 1.4)
    else:
        level_factor = ratio ** 1.15

    xp = base_xp * opponent_level * level_factor * state_multiplier

    return max(5, int(xp))

### 0.5  catching
### 0.75 wild encounters
### 0.9  trainer battles
### 1.0  rivals, gyms, elite 4, bosses

##################### BASE STATS ##################

def HP_Base(base_hp,level, p=1.4):
    return round(base_hp * (level / 50) ** p + 10)

def Base_Stats(base, level):
    return round(base * (level/50 ))


################## BATTLE MATHEMATICS #################

def Damage(level, attack, power, defender_defense, STAB, effectiveness, random): #randoom 217-255 , STAB (1,1.5), Type Modifier (40,20,10,5,2.5)
    return ((((((((2*level / 7) * attack * power)/defender_defense)/50)+2)*STAB)*effectiveness/10)*random)/255

# tesing = Damage(16,18,30,17,1.5,10,220)
# print(tesing) -----> 6.34



def type_effectiveness_value(move_type: str, defender_types):
    """
    Returns effectiveness on the same 10-based scale:
      10 -> 1.0x (neutral)
      20 -> 2.0x (super)
       5 -> 0.5x (not very)
       0 -> 0.0x (immune)
    Combine multipliers multiplicatively.
    """
    if isinstance(defender_types, str):
        defender_types = [defender_types]

    value = 10  # neutral
    for t in defender_types:
        v = TYPE_CHART_VAL.get(move_type, {}).get(t, 10)
        # Correct combination: multiply and keep result on 10 scale
        value = (value * v) // 10
    return int(value)


def stab_multiplier(move_type: str, attacker_types):
    if isinstance(attacker_types, str):
        attacker_types = [attacker_types]
    return 1.25 if move_type in attacker_types else 1.0

def random_damage_factor():
    return random.randint(217, 255)
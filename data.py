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
    'grunt1': {
        'name': 'Grunt',
        'partner': 'grunt2',
        'dinos': {0: ('Ghoulflame', 16)},
        'dialog': {'default': ["You shouldn't be here!"],
                            'defeated': ["... If the boss knew you were here... stay out of our business"]},
        'directions': ['down'],
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 400,
        'rank': 'lowest',
    },
    'grunt2': {
        'name': 'Grunt',
        'partner': 'grunt1',
        'dinos': {0: ('Sortle', 15)},
        'dialog': {'default': ["You shouldn't be here!"],
                    'defeated': ["... If the boss knew you were here... stay out of our business"]},
        'directions': ['down'],
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 400,
        'rank': 'lowest',
    },
    'basic_trainer': {
        'name': 'Rex',
        'partner': 'basic_trainer2',
        'dinos': {0: ('Bullicorn', 4)},
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
        'dinos': {0: ('Voltzbee', 4)},
        'dialog': {'default': ["We fight as one!"]},
        'directions': ['down'],
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 250,
        'rank': 'lowest',
    },
    'basic_trainer_girl': {
        'name': 'Lila',
        'dinos': {0: ('Bullicorn', 3), 1: ('Teamtwood', 3)},
        'dialog': {
            'default':  ["Hi do you want to battle with me?", "Get ready!"],
            'defeated': ["Yay thanks for the battle"]
        },
        'directions': ['left'],
        'look_around': True,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 150,
        'rank': 'lowest',
    },
    'route2_girl': {
        'name': 'Cleo',
        'dinos': {0: ('Teamtwood', 13), 1: ('Teamtwood',14)},
        'dialog': {
            'default':  ["Hey! You look like a good trainer.", "Let's battle!"],
            'defeated': ["Wow, you're really strong!"]
        },
        'directions': ['down'],
        'look_around': True,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 300,
        'rank': 'lowest',
    },
    'route2_boy': {
        'name': 'Will',
        'dinos': {0: ('Voltzbee', 15)},
        'dialog': {
            'default':  ["Hold up, you're not passing without a battle!", "Let's go!"],
            'defeated': ["Alright, you can head on through."]
        },
        'directions': ['up'],
        'look_around': True,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 250,
        'rank': 'lowest',
    },
    'dylan': {
        'name': 'Dylan',
        'dinos': {0: ('Sortle', 12), 1: ('Bullicorn', 14)},
        'dialog': {
            'default':  ["You've got some nerve coming through here.", "Let's battle!"],
            'defeated': ["Not bad at all."]
        },
        'directions': ['down'],
        'look_around': True,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 300,
        'rank': 'lowest',
    },
    'ethan': {
        'name': 'Ethan',
        'dinos': {0: ('Teamtwood', 5)},
        'dialog': {
            'default':  ["I never lose...", "Get ready!"],
            'defeated': ["Dang I gotta do better"]
        },
        'directions': ['up'],
        'look_around': False,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 200,
        'rank': 'lowest',
    },

    'shinji': {
        'name': 'Shinji',
        'dinos': {0: ('Creuw', 4), 1: ('Bullicorn', 6)},
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
    'gray': {
        'name': 'Gray',
        'dinos': {0: ('Prowscar', 7), 1: ('Sortle', 9)},
        'dialog': {
            'default':  [
                "It's been awhile Jet, I am ready to start this journey and get stronger,",
                "therefore lets have a battle and test out strength"
            ],
            'defeated': [
                "I like a challenge, next time I'll be more prepared.",
                "Keep at it, and I will too.."
            ]
        },
        'directions': ['up'],
        'look_around': False,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 300,
        'rank': 'rival',
    },
    'skyy': {
        'name': 'Skyy',
        'dinos': {0: ('Creuw', 13), 1: ('Netaslam', 14), 2: ('Luna', 16)},
        'dialog': {
            'default':  [
                "Welcome to the Sierra Flying Gym. I am Gym Leader Skyy.",
                "My dinos are built to endure — I hope you're ready for a real fight!"
            ],
            'defeated': [
                "Well done... you've earned the Sierra Badge.",
                "The road ahead will challenge you even more. Good luck."
            ]
        },
        'directions': ['down'],
        'look_around': False,
        'defeated': False,
        'biome': 'gym',
        'reward_coins': 1000,
        'rank': 'medium',
    },
    'gym_trainer_a': {
        'name': 'Mike',
        'dinos': {0: ('Creuw', 10), 1: ('Netaslam', 11)},
        'dialog': {
            'default':  ["You won't reach Skyy without going through me!", "Let's go!"],
            'defeated': ["Strong... keep pushing."]
        },
        'directions': ['down'],
        'look_around': True,
        'defeated': False,
        'biome': 'gym',
        'reward_coins': 200,
        'rank': 'lowest',
    },
    'gym_trainer_b': {
        'name': 'Connor',
        'dinos': {0: ('Creuw', 9), 1: ('Voltzbee', 10)},
        'dialog': {
            'default':  ["Skyy trained us well. Don't underestimate the gym!", "Battle!"],
            'defeated': ["You're tougher than I expected!"]
        },
        'directions': ['left'],
        'look_around': True,
        'defeated': False,
        'biome': 'gym',
        'reward_coins': 200,
        'rank': 'lowest',
    },
}



DINODEX_DATA = {
    'Vusion':    {'number': 1,  'desc': "A relentless dark-type predator that hunts by sensing heat. Its flickering energy aura can destabilize opponents before they even strike."},
    'Corlave':   {'number': 2,  'desc': "A small aquatic dino that dwells in shallow coastal waters. Its compact shell deflects glancing blows, making it tougher than it looks."},
    'Anemamace': {'number': 3,  'desc': "Corlave's evolved form. Longer and more powerful, it wields spiked appendages that can pierce rock. Feared by deep-sea hunters."},
    'Creuw':     {'number': 4,  'desc': "A lightweight flier with hollow bones built for bursts of speed. Often spotted riding thermals high above open plains."},
    'Luna':      {'number': 5,  'desc': "Creuw's evolved form. Fused flying and dark energy grant it near-invisibility at night. Rarely seen twice by the same trainer."},
    'Prowscar':  {'number': 6,  'desc': "A scrappy dark-type that roams dense undergrowth. Its jaw muscles generate enormous bite force despite its small frame."},
    'Floravel':  {'number': 7,  'desc': "A plant-armored earth-type that draws nutrients from the soil mid-battle. Its vines can reconfigure into defensive shields in an instant."},
    'Bullicorn': {'number': 8,  'desc': "A bullish yet gentle creature with a unique horn on its head, loved by many in the farm areas."},
    'Netaslam':  {'number': 9,  'desc': "The net dino, Netaslam yields a net while jumping and flying around with its net wings to catch prey in the open grass."},
    'Netyrant':  {'number': 10, 'desc': "Netyrant's wings have fully developed allowing it to soar the skies while hunting, becoming an apex predator."},
    'Sharktastrophe':  {'number': 11, 'desc': "A vicious oceanic beast, with sharp spikes protruding as its main source of weaponry."},
    'Sortle':  {'number': 12, 'desc': "This turtle has a shell made of sand actively swirling like a tornado, similar to its counterpart Frostle."},
    'Magnecrab':  {'number': 13, 'desc': "An underwater abomination, this crab has magnetic trident like claws which surge with electricity all while being native to the ocean."},
    'Volkit':     {'number': 14, 'desc': "A fierce cat with a molten core. Volkit is a fast and agile attacker who blazes in battle."},
    'Drafyton':   {'number': 15, 'desc': "A mysterious creature who once roamed and conquered both land and sky in the Lost Region, now a shell remains... This fossilized dragon keeps its hardened strength and is resilient in any battle."},
    'Auraliz':    {'number': 16, 'desc': "A majestic aura surrounds this cold blooded lizard, it is said to freeze the water of any nearby source when it is near. "},
    'Voltzbee':   {'number': 17, 'desc': "This electric bee helps polinate the region lightning fast, locals say the charge it produces synthesizes with the solar panels nearby."},
    'Teamtwood':  {'number': 18, 'desc': "A worker at heart, Teamtwood provides assitance to locals all year round with its love for the Earth."},
    'Tygraflare':  {'number': 19, 'desc': "With heat equal to stars emitting from its giant paws, Tygraflare is sure to fire up the its opponents."},
    'Bouldava':   {'number': 20, 'desc': "The Molten Lava Rock dino, known to bathe in the magma at the base of the Megi Volcano."},
    'Ghoulflame': {'number': 21, 'desc': "This Ghoul resides in the Episc Chateau in Elder Town, it's spirit likes to lurk around the area and play pranks. With fire and dark energy to use on foes."},
    'Scarecrux':  {'number': 22, 'desc': "At first just folk lore to the residents of Elder Town, this odd scarecrow has been scaring Creuws for years only to be put to rest by the great Luna watching over, it is said to only come alive at night..."},
    'Palidian':   {'number': 23, 'desc': "A noble knight who guards the forest, known to be a defender of sacred land and be courageous in battle."},
    'Rockull':    {'number': 24, 'desc': "A hulking rock golem that packs its boulder-like fists with crushing force. Rockull is slow to move but nearly impossible to knock down."},

}

DINO_DATA = {
    'Vusion': {
        'stats': {'type': ['dark'], 'health': 120, 'attack': 155, 'defense': 70, 'speed': 125},
        'moves': {0: 'Force Shift', 1: 'Flash', 9: 'Fireball', 15: 'Shadow Veil', 17: 'Conduit Surge', 19: 'Distortion', 23: 'Flame Shatter', 27: 'Binding Curse', 30: 'Void Collapse', 35: 'Haunt'},
        'evolve': None},
    'Anemamace': {
        'stats': {'type': ['aqua','spike'], 'health': 140, 'attack': 115, 'defense': 120, 'speed':80},
        'moves': {0: 'Whirlpool+', 1: 'Arise', 8: 'Quick Slash', 13: 'Wave Dash', 19: 'Double Jab', 22: 'Hurricane', 26: 'Ripping Impact'},
        'evolve': None},
    'Corlave': {
        'stats': {'type': ['aqua'], 'health': 90, 'attack': 80, 'defense': 80, 'speed':50},
        'moves': {0: 'Whirlpool+', 1: 'Arise', 8: 'Quick Slash', 13: 'Wave Dash', 19: 'Double Jab'},
        'evolve': {17: 'Anemamace'}},
    'Creuw': {
        'stats': {'type': ['flying'], 'health': 60, 'attack': 75, 'defense': 50, 'speed':75},
        'moves': {0: 'Air Strike', 1: 'Arise', 5: 'Sand Kick', 8: 'Dark Energy', 12: 'Swift Sneak', 14: 'Fear', 17: 'Force Shift', 21: 'Turbo Booster', 26: 'Mach Speed', 29: 'Shadow Veil', 34: 'Wind Fracture', 38: 'Void Collapse', 43: 'Sky Scorch' },
        'evolve': {16: 'Luna'}},
    'Luna': {
        'stats': {'type': ['flying', 'dark'], 'health': 100, 'attack': 135, 'defense': 80, 'speed':135},
        'moves': {0: 'Air Strike', 1: 'Arise', 5: 'Sand Kick', 8: 'Dark Energy', 12: 'Swift Sneak', 14: 'Fear', 17: 'Force Shift', 21: 'Turbo Booster', 26: 'Mach Speed', 29: 'Shadow Veil', 34: 'Wind Fracture', 38: 'Void Collapse', 43: 'Sky Scorch' },
        'evolve': None},
    'Prowscar': {
        'stats': {'type': ['dark'], 'health': 60, 'attack': 95, 'defense': 70, 'speed': 80},
        'moves': {0: 'Bitemark', 1: 'Arise', 8: 'Dark Energy', 12: 'Lock Jaw', 15: 'Fear', 18: 'Double Jab', 21: 'Shadow Veil', 25: 'Haunt'},
        'evolve': None},
    'Floravel': {
        'stats': {'type': ['earth'], 'health': 60, 'attack': 85, 'defense': 95, 'speed': 60},
        'moves': {0: 'Vine Snare+', 1: 'Arise', 8: 'Boulder Smash', 13: 'Synthesis', 18: 'Dread Thorn', 23: 'Crusher', 26: 'Synthesis', 28: 'Terraform'},
        'evolve': None},
    'Bullicorn': {
        'stats': {'type': ['spike'], 'health': 145, 'attack': 95, 'defense': 100, 'speed': 75},
        'moves': {0: 'Arise', 4: 'Horn Tackle', 7: 'Sand Kick', 10: 'Static Graze', 12: 'Boulder Smash', 15: 'Double Jab'},
        'evolve': None},
    'Netaslam': {
        'stats': {'type': ['flying', 'spike'], 'health': 60, 'attack': 80, 'defense': 50, 'speed': 70},
        'moves': {0: 'Air Strike', 1: 'Arise', 6: 'Fear', 9: 'Lock Jaw', 12: 'Static Graze', 15: 'Double Jab', 17:'Rushdown', 21: 'Mach Speed', 25: 'Ripping Impact'},
        'evolve': {22: 'Netyrant'}},
    'Netyrant': {
        'stats': {'type': ['flying', 'spike'], 'health': 110, 'attack': 145, 'defense': 75, 'speed': 125},
        'moves': {0: 'Air Strike', 1: 'Arise', 6: 'Fear', 9: 'Lock Jaw', 12: 'Static Graze', 15: 'Double Jab', 17:'Rushdown', 20: 'Mach Speed', 22: 'Ripping Impact', 26: 'Wind Fracture', 30: 'Sword Slash', 33: 'Turbo Booster', 37: 'Spike Storm', 40: 'Sky Scorch'},
        'evolve': None},
    'Sortle': {
        'stats': {'type': ['rock'], 'health': 120, 'attack': 110, 'defense': 140, 'speed': 60},
        'moves': {0: 'Dust Beam', 1: 'Arise', 8: 'Sand Kick', 12: 'Quick Slash', 15: 'Venom Decay', 17: 'Boulder Smash', 22:'Sand Storm', 24: 'Iron Core', 26: 'Power Fang', 30: 'Wind Fracture', 33: 'Crusher', 36 :'Crash Impact'},
        'evolve': None},
    'Sharktastrophe': {
        'stats': {'type': ['aqua', 'spike'], 'health': 90, 'attack': 120, 'defense': 115, 'speed': 125},
        'moves': {0: 'Whirlpool', 1: 'Arise', 8: 'Quick Slash', 14: 'Wave Dash', 18: 'Double Jab', 21:'Haunt', 25: 'Primal Rage', 28: 'Ripping Impact', 31: 'Hurricane', 35: 'Sword Slash', 40: 'Eternal Blue'},
        'evolve': None},
    'Magnecrab': {
        'stats': {'type': ['aqua', 'lightning'], 'health': 140, 'attack': 110, 'defense': 75, 'speed': 100},
        'moves': {0: 'Whirlpool', 1: 'Arise', 8: 'Thunder Slap', 14: 'Shock', 18: 'Double Jab', 24:'Lightning Rod', 28: 'Hurricane', 31: 'Ripping Impact', 35: 'Conduit Surge', 39: 'Quantum Flux', 44: 'Eternal Blue'},
        'evolve': None},
    'Volkit': {
        'stats': {'type': ['magma'], 'health': 62, 'attack': 95, 'defense': 68, 'speed': 75},
        'moves': {0: 'Fireball+', 1: 'Arise', 6: 'Flash', 10: 'Quick Slash', 14: 'Rushdown', 18: 'Flame Shatter', 20: 'Fear'},
        'evolve': {18: 'Tygraflare'}},
    'Drafyton': {
        'stats': {'type': ['ancient', 'flying'], 'health': 100, 'attack': 155, 'defense': 125, 'speed': 120},
        'moves': {0: 'Fossil Break', 1: 'Arise', 8: 'Quick Slash', 12: 'Fireball', 16: 'Rushdown', 20: 'Mach Speed', 23: 'Primal Rage', 25: 'Fear', 27: 'Ancient Mend', 29: 'Flame Shatter', 31: 'Force Shift', 33: 'Raging Pursuit', 35: 'Crusher', 38: 'Sky Scorch', 40: 'Dragon Zenith', 42: 'Spike Storm' },
        'evolve': None},
    'Auraliz': {
        'stats': {'type': ['ice', 'aqua'], 'health': 92, 'attack': 118, 'defense': 117, 'speed': 123},
        'moves': {0: 'Whirlpool', 1: 'Arise', 8: 'Snowfall', 12: 'Venom Decay', 17: 'Frozen Aura', 20: 'Power Fang', 23: 'Hurricane', 26: 'Hyperfrost', 29: 'Deep Freeze',31: 'Fear', 34: 'Hailstorm', 37: 'Freeze Blast', 42:'Eternal Blue'},
        'evolve': None},
    'Voltzbee': {
        'stats': {'type': ['lightning', 'flying'], 'health': 77, 'attack': 113, 'defense': 83, 'speed': 142},
        'moves': {0: 'Shock', 4: 'Stinger Shock', 8: 'Air Strike', 12: 'Thunder Blitz', 18: 'Mach Speed', 22: 'Piercing Light'},
        'evolve': None},
    'Teamtwood': {
        'stats': {'type': ['earth'], 'health': 88, 'attack': 102, 'defense': 128, 'speed': 107},
        'moves': {0: 'Sand Kick', 4: 'Log Roll', 9: 'Synthesis', 12: 'Vine Snare', 15: 'Boulder Smash', 18: 'Floral Resonance', 22: 'Dread Thorn', 27: 'Terraform', 31: 'Double Jab', 35: 'Tree Spin'},
        'evolve': None},
    'Tygraflare': {
        'stats': {'type': ['magma'], 'health': 95, 'attack': 137, 'defense': 95, 'speed': 128},
        'moves': {0: 'Fireball+', 1: 'Arise', 6: 'Flash', 10: 'Quick Slash', 14: 'Rushdown', 18: 'Flame Shatter', 20: 'Fear', 24: 'Piercing Light', 27: 'Lava Burst', 31: 'Crusher' , 35: 'Magma Boost', 39: 'Solar Flare'},
        'evolve': None},
    'Bouldava': {
        'stats': {'type': ['rock'], 'health': 120, 'attack': 105, 'defense': 135, 'speed': 80},
        'moves': {0: "Boulder Smash", 1: 'Sand Kick', 12: 'Flame Shatter', 17: 'Prism Glare',20: 'Momentum', 22: 'Crusher', 25: 'Iron Core' ,28: 'Lava Burst', 32: 'Magma Boost', 39:'Crash Impact' },
        'evolve': None},
    'Ghoulflame': {
        'stats': {'type': ['dark', 'magma'], 'health': 106, 'attack': 116, 'defense': 94, 'speed': 114},
        'moves': {0: 'Fireball', 1: 'Fear', 9: 'Dark Energy', 12: 'Binding Curse', 15: 'Prism Glare', 18: 'Magma Boost', 21: 'Flame Shatter', 24: 'Distortion', 26: 'Force Shift', 28: 'Haunt', 32: 'Lava Burst', 37: 'Void Collapse'},
        'evolve': None},
    'Scarecrux': {
        'stats': {'type': ['dark', 'earth'], 'health': 110, 'attack': 136, 'defense': 124, 'speed': 88},
        'moves': {0: 'Dark Energy', 1: 'Fear', 9: 'Vine Snare', 15: 'Haunt', 19: 'Distortion', 23: 'Dread Thorn', 26: 'Force Shift', 29: 'Thunder Blitz', 33: 'Tree Spin', 37: 'Void Collapse'},
        'evolve': None},
    'Palidian': {
        'stats': {'type': ['earth', 'rock'], 'health': 90, 'attack': 124, 'defense': 136, 'speed': 105},
        'moves': {0: 'Vine Snare+', 1: 'Arise', 8: 'Boulder Smash', 13: 'Synthesis', 18: 'Dread Thorn', 23: 'Crusher', 26: 'Synthesis', 28: 'Terraform', 31: 'Iron Core', 34: 'Raging Pursuit', 36: 'Tree Spin', 39: 'Crash Impact'},
        'evolve': None},
    'Rockull': {
        'stats': {'type': ['rock'], 'health': 160, 'attack': 110, 'defense': 150, 'speed': 40},
        'moves': {0: 'Dust Beam', 4: 'Sand Kick', 8: 'Boulder Smash', 14: 'Momentum', 17: 'Force Shift', 20: 'Iron Core', 26: 'Crusher',30:'Prism Glare', 34: 'Crash Impact'},
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
        'super_eff': ['aqua', 'rock', 'lightning'],
        'weak_eff': ['earth', 'ancient', 'flying', 'magma', 'ice'],
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
        'resist': ['ice', 'earth'],
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
    'aqua': {'aqua': 5, 'magma': 20, 'earth': 5, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 20, 'lightning': 10, 'ice': 5  , 'ancient': 5},
    'magma': {'aqua': 5, 'magma': 5, 'earth': 20, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 5, 'lightning': 10, 'ice': 20, 'ancient': 5},
    'earth': {'aqua': 20, 'magma': 5, 'earth': 5, 'flying': 5, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 20, 'lightning': 20, 'ice': 10,'ancient': 5},
    'flying': {'aqua': 10, 'magma': 10, 'earth': 20, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 20, 'rock': 5, 'lightning': 5, 'ice': 10,'ancient': 10},
    'dark': {'aqua': 10, 'magma': 10, 'earth': 10, 'flying': 10, 'dark': 20 , 'light': 5, 'spike': 20, 'rock': 10, 'lightning': 10, 'ice': 10,'ancient': 10},
    'light': {'aqua': 10, 'magma': 10, 'earth': 5, 'flying': 10, 'dark': 20 , 'light': 10, 'spike': 20, 'rock': 10, 'lightning': 10, 'ice': 10,'ancient': 10},
    'spike': {'aqua': 10, 'magma': 10, 'earth': 20, 'flying': 10, 'dark': 5 , 'light': 5, 'spike': 10, 'rock': 20, 'lightning': 10, 'ice': 10,'ancient': 20},
    'rock': {'aqua': 10, 'magma': 20, 'earth': 10, 'flying': 20, 'dark': 10 , 'light': 10, 'spike': 5, 'rock': 5, 'lightning': 20, 'ice': 20,'ancient': 10},
    'lightning': {'aqua': 20, 'magma': 10, 'earth': 5, 'flying': 20, 'dark': 10 , 'light': 20, 'spike': 10, 'rock': 5, 'lightning': 10, 'ice': 10,'ancient': 5},
    'ice': {'aqua': 5, 'magma': 5, 'earth': 20, 'flying': 20, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 10, 'lightning': 10, 'ice': 5,'ancient': 20},
    'ancient': {'aqua': 10, 'magma': 10, 'earth': 10, 'flying': 10, 'dark': 5 , 'light': 20, 'spike': 5, 'rock': 5, 'lightning': 10, 'ice': 10,'ancient': 20},



}





MOVE_DATA = {
    #AQUA MOVES
    'Whirlpool': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'aqua'},
    'Whirlpool+': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'aqua'},

    'Hurricane': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'aqua'},
    'Eternal Blue': {'target': 'opponent', 'damage': 90, 'accuracy': 100, 'ability': None, 'type': 'aqua'},

    'Wave Dash':   {'target': 'opponent', 'damage': 45, 'accuracy': 95, 'type': 'aqua', 'priority':1,
                    'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 1, 'target': 'self', 'chance': 100}},
    #MAGMA MOVES
    'Fireball': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'magma'},
    'Fireball+': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'magma'},
    'Lava Burst': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'magma'},
    'Solar Flare': {'target': 'opponent', 'damage': 90, 'accuracy': 100, 'ability': None, 'type': 'magma'},

    'Flame Shatter':   {'target': 'opponent', 'damage': 50, 'accuracy': 95, 'type': 'magma',
                    'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': -1, 'target': 'opponent', 'chance': 100}},
    'Magma Boost':  {'target': 'self',     'damage': 0,  'accuracy': 100, 'type': 'magma', 'priority':1,
                     'ability': {'kind': 'field', 'effect': 'type_power', 'boost_type': 'magma', 'multiplier': 1.5, 'duration': 4, 'chance': 100}},
    #EARTH MOVES
    'Log Roll': {'target': 'opponent', 'damage': 20, 'accuracy': 100, 'ability': None, 'type': 'earth'},
    'Vine Snare': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'earth'},
   'Vine Snare+': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'earth'},
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
    'Swift Sneak': {'target': 'opponent', 'damage': 40, 'accuracy': 95, 'ability': None, 'type': 'flying', 'priority': 1},
    'Air Strike': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'flying'},
    'Mach Speed': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'flying'},
    'Wind Fracture': {'target': 'opponent', 'damage': 80, 'accuracy': 100, 'ability': None, 'type': 'flying'},

    'Turbo Booster':   {'target': 'self', 'damage': 0, 'accuracy': 95, 'type': 'flying', 'priority':1,
                    'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 2, 'target': 'self', 'chance': 100}},
    'Sky Scorch':   {'target': 'opponent', 'damage': 120, 'accuracy': 90, 'type': 'flying',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -2, 'target': 'self', 'chance': 100}},
    #SPIKE MOVES
    'Lock Jaw': {'target': 'opponent', 'damage': 20, 'accuracy': 90, 'type': 'spike', 'priority':1,
                 'ability': {'kind': 'lock', 'turns': 2, 'chance': 100}},
    'Horn Tackle': {'target': 'opponent', 'damage': 20, 'accuracy': 100, 'ability': None, 'type': 'spike'},
    'Double Jab': {'target': 'opponent', 'damage': 45, 'accuracy': 100, 'ability': None, 'type': 'spike'},
    'Ripping Impact': {'target': 'opponent', 'damage': 55, 'accuracy': 90, 'ability': None, 'type': 'spike', 'pierces_defend': True},
    'Power Fang': {'target': 'opponent', 'damage': 50, 'accuracy': 100, 'ability': None, 'type': 'spike'},
    'Sword Slash': {'target': 'opponent', 'damage': 70, 'accuracy': 100, 'ability': None, 'type': 'spike'},
    'Quick Slash': {'target': 'opponent', 'damage': 40, 'accuracy': 95, 'ability': None, 'type': 'spike', 'priority': 1},

    'Spike Storm': {'target': 'opponent', 'damage': 110, 'accuracy': 95, 'type': 'spike',
                    'ability': {'kind': 'recoil', 'percent': 25, 'chance': 100}},

    #ROCK MOVES
    'Dust Beam': {'target': 'opponent', 'damage': 20, 'accuracy': 100, 'ability': None, 'type': 'rock'},
    'Boulder Smash': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'rock'},
    'Crusher': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'rock'},

    'Sand Kick':   {'target': 'opponent', 'damage': 0, 'accuracy': 95, 'type': 'rock',
                    'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': -1, 'target': 'opponent', 'chance': 100}},
    'Iron Core':   {'target': 'self', 'damage': 0, 'accuracy': 90, 'type': 'rock',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': 2, 'target': 'self', 'chance': 100}},             
    'Momentum':   {'target': 'opponent', 'damage': 40, 'accuracy': 90, 'type': 'rock',
                    'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': 1, 'target': 'self', 'chance': 100}},
    'Crash Impact': {'target': 'opponent', 'damage': 90, 'accuracy': 100, 'type': 'rock',
                     'ability': {'kind': 'recoil', 'percent': 15, 'chance': 100}},
    'Sand Storm': {'target': 'opponent', 'damage': 20, 'accuracy': 90, 'type': 'ice',
                   'ability': {'kind': 'dot', 'damage_percent': 8, 'turns': 2,
                               'tick_msg': 'hit by waves of sand', 'chance': 100}},

    #LIGHTNING MOVES
    'Stinger Shock': {'target': 'opponent', 'damage': 20, 'accuracy': 100, 'ability': None, 'type': 'lightning'},
    'Static Graze': {'target': 'opponent', 'damage': 25, 'accuracy': 100, 'ability': None, 'type': 'lightning'},
    'Thunder Blitz': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'lightning'},
    'Lightning Rod': {'target': 'opponent', 'damage': 50, 'accuracy': 95, 'ability': None, 'type': 'lightning',
                        'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': 1, 'target': 'self', 'chance': 50},
},
    'Volt Storm': {'target': 'opponent', 'damage': 80, 'accuracy': 100, 'ability': None, 'type': 'lightning'},


    'Conduit Surge':  {'target': 'opponent', 'damage': 50, 'accuracy': 90,  'type': 'lightning',
                     'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 2, 'target': 'self', 'chance': 100}},
    'Quantum Flux':  {'target': 'opponent', 'damage': 70, 'accuracy': 85,  'type': 'lightning', 'priority': 1,
                     'ability': {'kind': 'stat_boost', 'stat': 'speed', 'stages': 1, 'target': 'self', 'chance': 100}},
    'Shock':   {'target': 'opponent', 'damage': 0, 'accuracy': 95, 'type': 'lightning', 'priority':1,
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -1, 'target': 'opponent', 'chance': 100}},

    #DARK MOVES
    'Force Shift': {'target': 'opponent', 'damage': 45, 'accuracy': 100, 'ability': None,'type': 'dark'},
    'Dark Energy': {'target': 'opponent', 'damage': 35, 'accuracy': 100, 'ability': None, 'type': 'dark'},
    'Void Collapse': {'target': 'opponent', 'damage': 75, 'accuracy': 95, 'ability': None, 'type': 'dark', 'pierces_defend': True},
    'Bitemark': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'dark'},

    'Distortion':   {'target': 'opponent', 'damage': 5, 'accuracy': 100, 'type': 'dark', 'priority':1,
                     'ability': {'kind': 'field', 'effect': 'speed_swap', 'duration': 5, 'chance': 100}},
    'Fear':   {'target': 'opponent', 'damage': 0, 'accuracy': 95, 'type': 'dark', 'priority':1,
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -1, 'target': 'opponent', 'chance': 100}},
    'Haunt':   {'target': 'opponent', 'damage': 0, 'accuracy': 100, 'type': 'dark', 'priority':1,
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -2, 'target': 'opponent', 'chance': 100}},
    'Binding Curse': {'target': 'opponent', 'damage': 25, 'accuracy': 90, 'type': 'dark',
                      'ability': {'kind': 'lock', 'turns': 2, 'chance': 100}},
    'Shadow Veil':   {'target': 'opponent', 'damage': 55, 'accuracy': 100, 'type': 'dark',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': 1, 'target': 'self', 'chance': 100}},
    #LIGHT MOVES
    'Prism Glare': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'light'},
    'Piercing Light': {'target': 'opponent', 'damage': 60, 'accuracy': 90, 'ability': None, 'type': 'light', 'pierces_defend': True},
    'Spectral Overload': {'target': 'opponent', 'damage': 90, 'accuracy': 100, 'ability': None, 'type': 'light'},

    'Flash':   {'target': 'opponent', 'damage': 0, 'accuracy': 95, 'type': 'light',
                    'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': -1, 'target': 'opponent', 'chance': 100}},
    'Refraction':  {'target': 'self',     'damage': 0,  'accuracy': 100, 'type': 'light', 'priority':1,
                     'ability': {'kind': 'field', 'effect': 'type_power', 'boost_type': 'light', 'multiplier': 1.5, 'duration': 4, 'chance': 100}},
   'Gamma Wave':   {'target': 'opponent', 'damage': 80, 'accuracy': 90, 'type': 'light',
                    'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': -2, 'target': 'opponent', 'chance': 100}},
    #ICE MOVES
    'Snowfall': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'ice'},
    'Freeze Blast': {'target': 'opponent', 'damage': 80, 'accuracy': 100, 'ability': None, 'type': 'ice'},
    'Hyperfrost': {'target': 'opponent', 'damage': 55, 'accuracy': 100, 'ability': None, 'type': 'ice', 'pierces_defend': True},

    'Hail Storm': {'target': 'opponent', 'damage': 25, 'accuracy': 90, 'type': 'ice',
                   'ability': {'kind': 'dot', 'damage_percent': 8, 'turns': 2,
                               'tick_msg': 'pelted by the raging hail', 'chance': 100}},
    'Frozen Aura': {'target': 'self', 'damage': 10, 'accuracy': 100, 'type': 'ice',
                     'ability': {'kind': 'heal', 'percent': 30, 'chance': 100}},
    'Deep Freeze':   {'target': 'opponent', 'damage': 60, 'accuracy': 90, 'type': 'ice',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -1, 'target': 'opponent', 'chance': 100}},
    #ANCIENT MOVES
    'Fossil Break': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'ancient'},

    'Raging Pursuit': {'target': 'opponent', 'damage': 55, 'accuracy': 90, 'ability': None, 'type': 'ancient', 'pierces_defend': True},
    'Dragon Zenith': {'target': 'opponent', 'damage': 100, 'accuracy': 90, 'ability': None, 'type': 'ancient', 'pierces_defend': True},

    'Primal Rage':  {'target': 'opponent', 'damage': 45, 'accuracy': 100, 'type': 'ancient',
                     'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': 1, 'target': 'self', 'chance': 100}},
    'Arise':  {'target': 'self', 'damage': 0, 'accuracy': 100, 'type': 'ancient',
                     'ability': {'kind': 'stat_boost', 'stat': 'attack', 'stages': 1, 'target': 'self', 'chance': 100}},

    'Venom Decay':   {'target': 'opponent', 'damage': 40, 'accuracy': 90, 'type': 'ancient',
                    'ability': {'kind': 'stat_boost', 'stat': 'defense', 'stages': -1, 'target': 'opponent', 'chance': 100}},
    'Rushdown': {'target': 'opponent', 'damage': 40, 'accuracy': 90, 'ability': None, 'type': 'ancient', 'priority':1},

    #HEALING MOVES
    'Ancient Mend': {'target': 'self', 'damage': 0, 'accuracy': 100, 'type': 'ancient', 'priority':1,
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
    'research':     {'world': 'RESEARCH_LAB.tmx',    'spawn': (10, 11)},
    'gym1':         {'world': 'GYM1.tmx',             'spawn': (9, 13)},

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
        "dinos": ["Bullicorn", "Voltzbee"],
        "level_range": (2,4)
    },
    "route1+_grass": {
        "dinos": ["Creuw", "Bullicorn", "Netaslam", "Voltzbee", "Teamtwood"],
        "level_range": (3, 6)
    },

    "route1_special": {
        "dinos": ["Luna"],
        "level_range": (16, 18)
    },

    "town1_grass": {
        "dinos": ["Sortle", "Sharktastrophe"],
        "level_range": (6, 8)
    },


    
    "route2_grass": {
        "dinos": ["Teamtwood", "Netaslam", "Bullicorn"],
        "level_range": (7, 11)

    },

    "route2_burnt_grass": {
        "dinos": ["Sortle", "Teamtwood", "Creuw"],
        "level_range": (8, 12)

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
    (16+x_offset, -37+y_offset, 18+x_offset, -37+y_offset, "route1_special"),
    #just use "z" in game to find tile in print
    (29, -30, 33, -27, "town1_grass"),
    (16, -42, 21, -36, "route2_grass"),
    (32, -42, 54, -29, "route2_burnt_grass"),

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
    level_factor = max(0.3, min(1.3, ratio ** 0.35))

    xp = base_xp * opponent_level * level_factor * state_multiplier

    return max(5, int(xp))

### 0.5  catching
### 0.75 wild encounters
### 0.9  trainer battles
### 1.0  rivals, gyms, elite 4, bosses

##################### NATURES ##################

NATURE_BOOSTS = {
    "Hardy":    {"hp": 0.10},
    "Bulky":    {"defense": 0.10},
    "Speedy":   {"speed": 0.10},
    "Power":    {"attack": 0.10},
    "Tank":     {"hp": 0.05, "defense": 0.05},
    "Rush":     {"attack": 0.05, "speed": 0.05},
    "Balanced": {"attack": 0.05, "defense": 0.05},
}

##################### BASE STATS ##################

def HP_Base(base_hp,level, p=1.4):
    return round(base_hp * (level / 50) ** p + 10)

def Base_Stats(base, level):
    return round(base * (level / 50) ** 0.7)


################## BATTLE MATHEMATICS #################

def Damage(level, attack, power, defender_defense, STAB, effectiveness, random): #randoom 217-255 , STAB (1,1.5), Type Modifier (40,20,10,5,2.5)
    return ((((((((2*level / 7) * attack * power)/(defender_defense * 0.95))/50)+2)*STAB)*effectiveness/10)*random)/255

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
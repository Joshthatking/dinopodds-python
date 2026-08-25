import config
import random

STAT_STAGE_MULT = {
    -6: 0.25, -5: 0.28, -4: 0.33, -3: 0.40,
    -2: 0.50, -1: 0.67,  0: 1.0,
     1: 1.25,  2: 1.50,  3: 2.0,
     4: 2.5,   5: 3.0,   6: 3.5,
}

# XP split between the active dino and its bench, by number of dinos alive.
# Single source of truth — used for both the XP actually granted and the
# on-screen "gained X XP" messages, so the two can't drift apart again.
ACTIVE_XP_MULT_SOLO  = 2.0   # active dino's multiplier when it's the only one alive
ACTIVE_XP_MULT_PARTY = 1.5   # active dino's multiplier when others are alive too
BENCH_XP_MULT = {2: 1.2, 3: 1.0, 4: 0.8, 5: 0.6}

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
        'dinos': {0: ('Prickly', 15)},
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
    'rocko': {
        'name': 'Rocko',
        'dinos': {0: ('Sortle', 11), 1: ('Voltzbee', 12)},
        'dialog': {
            'default':  ["Hah, new guy on Route 2!", "Let's see what you've got!"],
            'defeated': ["Guess I've still got some toughening up to do."]
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
    'log': {
        'name': 'Log',
        'dinos': {0: ('Prickly', 17), 1: ('Scarecrux', 18), 2: ('Cyflactus', 21)},
        'dialog': {
            'default':  [
                "Jet! Good to see you made it to the Earth Gym.",
                "I've been itching for that good challenge I mentioned back at the corn maze.",
                "Let's see if you can handle the toughness of the earth itself!"
            ],
            'defeated': [
                "Ha! I knew you had it in you.",
                "You've earned the Earth Badge, fair and square.",
                "Keep pushing forward, Jet — there's more waiting for you out there."
            ]
        },
        'directions': ['down'],
        'look_around': False,
        'defeated': False,
        'biome': 'gym',
        'reward_coins': 1200,
        'rank': 'medium',
    },
    'gym2_trainer_a': {
        'name': 'Rocco',
        'dinos': {0: ('Teamtwood', 16), 1: ('Prickly', 16)},
        'dialog': {
            'default':  ["You won't get past me without a fight!", "Let's see what you've got!"],
            'defeated': ["Guess I need to toughen up more."]
        },
        'directions': ['right'],
        'look_around': True,
        'defeated': False,
        'biome': 'gym',
        'reward_coins': 350,
        'rank': 'lowest',
    },
    'gym2_trainer_b': {
        'name': 'Sage',
        'dinos': {0: ('Floravel', 18)},
        'dialog': {
            'default':  ["This gym tests more than just strength.", "Let's battle!"],
            'defeated': ["Well fought, trainer."]
        },
        'directions': ['right'],
        'look_around': True,
        'defeated': False,
        'biome': 'gym',
        'reward_coins': 350,
        'rank': 'lowest',
    },
    'gym2_trainer_c': {
        'name': 'Clay',
        'dinos': {0: ('Teamtwood', 18)},
        'dialog': {
            'default':  ["Log trained us well for moments like this.", "Get ready!"],
            'defeated': ["Not bad at all!"]
        },
        'directions': ['left'],
        'look_around': True,
        'defeated': False,
        'biome': 'gym',
        'reward_coins': 350,
        'rank': 'lowest',
    },
    'gym2_trainer_d': {
        'name': 'Moss',
        'dinos': {0: ('Prickly', 18)},
        'dialog': {
            'default':  ["The earth doesn't yield easily, and neither do I!"],
            'defeated': ["Impressive... Log will want to hear about this."]
        },
        'directions': ['up'],
        'look_around': True,
        'defeated': False,
        'biome': 'gym',
        'reward_coins': 350,
        'rank': 'lowest',
    },
    'vanessa': {
        'name': 'Vanessa',
        'dinos': {0: ('Prowscar', 16), 1: ('Netaslam', 16), 2: ('Ghoulflame', 16), 3: ('Gourdecrux', 17)},
        'dialog': {
            'default':  ["You fools, in time you will understand the harm you are causing"],
            'defeated': ["Next time I won't be as easy on you..."]
        },
        'directions': ['down'],
        'look_around': False,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 1200,
        'rank': 'boss',
    },
    'john': {
        'name': 'John',
        'dinos': {0: ('Bullicorn', 16), 1: ('Bullicorn', 16), 2: ('Bullicorn', 17)},
        'dialog': {
            'default':  ["These horns aren't just for show, kid.", "Let's battle!"],
            'defeated': ["Ha! You handled my herd well."]
        },
        'directions': ['up'],
        'look_around': True,
        'defeated': False,
        'biome': 'forest',
        'reward_coins': 450,
        'rank': 'lowest',
    },
}



DINODEX_DATA = {
    'Vusion':    {'number': 1,  'desc': "A relentless dark-type predator that hunts by sensing heat. Its flickering energy aura can destabilize opponents before they even strike."},
    'Corlave':   {'number': 2,  'desc': "A small aquatic dino that dwells in shallow coastal waters. Its compact shell deflects glancing blows, making it tougher than it looks."},
    'Anemamace': {'number': 3,  'desc': "The oceans sturdiest protector. It wields spiked appendages that can pierce rock. Feared by the celestials that once attacked both land,sky and sea."},
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
    'Drafyton':   {'number': 15, 'desc': "A mysterious creature who once roamed and conquered both land and sky in the Lost Region, now a shell remains... This fossilized dragon was the ulitmate protector of the Lost Region when the celesetial conquest began eons ago."},
    'Auraliz':    {'number': 16, 'desc': "A majestic aura surrounds this cold blooded lizard, it is said to freeze the water of any nearby source when it is near. "},
    'Voltzbee':   {'number': 17, 'desc': "This electric bee helps polinate the region lightning fast, locals say the charge it produces synthesizes with the solar panels nearby."},
    'Teamtwood':  {'number': 18, 'desc': "A worker at heart, Teamtwood provides assitance to locals all year round with its love for the Earth."},
    'Tygraflare':  {'number': 19, 'desc': "With heat equal to stars emitting from its giant paws, Tygraflare is sure to fire up the its opponents. Known to be fast in battle and apply pressure immediately to surprise the foe."},
    'Bouldava':   {'number': 20, 'desc': "The Molten Lava Rock dino, known to bathe in the magma at the base of the Megi Volcano."},
    'Ghoulflame': {'number': 21, 'desc': "This Ghoul resides in the Episc Chateau in Elder Town, it's spirit likes to lurk around the area and play pranks. With fire and dark energy to use on foes."},
    'Scarecrux':  {'number': 22, 'desc': "At first just folk lore to the residents of Elder Town, this odd scarecrow has been scaring Creuws for years only to be put to rest by the great Luna watching over, it is said to only come alive at night..."},
    'Palidian':   {'number': 23, 'desc': "A noble knight who guards the forest, known to be a defender of sacred land and be courageous in battle. A true guardian of the Lost Region, fabled in the towns mythology as a subservant palidan only to the ancients or the region."},
    'Rockull':    {'number': 24, 'desc': "A hulking rock golem that packs its boulder-like fists with crushing force. Rockull is slow to move but nearly impossible to knock down."},
    'Prickly':    {'number': 25, 'desc': "A cheerful cactus dino covered in spines that are sharper than they look. Prickly thrives in dry, sun-baked soil."},
    'Cyflactus':  {'number': 26, 'desc': "Prickly's evolved form, a result of extensive solar panels surrounding the Region. This mutation turned its prickly spikes into scorching spikes made of flames."},
    'Gourdecrux': {'number': 27, 'desc': "A fiery transformation of Scarecrux, its head consumed by a burning jack-o'-lantern. Legend says only a trainer who has proven themselves at the Region's gyms can awaken this form once known as the gatekeeper of the Elder Town Mansion."},
    # PLACEHOLDER — desc/type/stats/moves are stand-ins pending real design.
    'Rhinecicle': {'number': 28, 'desc': "A hulking, ice and rock plated rhino dino that charges with a frozen horn."},
    'Celestreeyl': {'number': 29, 'desc': "One of the celestials, holder of the Celestial Solar Shard. It is a guardian of light and life and its mission is to preserve both."},
    'Rhysnow':    {'number': 30, 'desc': "A small rhino dino covered in snow, common in the mountainous winter terrain."},

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
        'evolve': {19: 'Anemamace'}},
    'Creuw': {
        'stats': {'type': ['flying'], 'health': 60, 'attack': 75, 'defense': 50, 'speed':75},
        'moves': {0: 'Air Strike', 1: 'Arise', 5: 'Sand Kick', 8: 'Dark Energy', 12: 'Swift Sneak', 14: 'Fear', 17: 'Force Shift', 21: 'Turbo Booster', 26: 'Mach Speed', 29: 'Shadow Veil', 34: 'Wind Fracture', 38: 'Void Collapse', 43: 'Sky Scorch' },
        'evolve': {16: 'Luna'}},
    'Luna': {
        'stats': {'type': ['flying', 'dark'], 'health': 100, 'attack': 125, 'defense': 80, 'speed':135},
        'moves': {0: 'Air Strike', 1: 'Arise', 5: 'Sand Kick', 8: 'Dark Energy', 12: 'Swift Sneak', 14: 'Fear', 17: 'Force Shift', 21: 'Turbo Booster', 26: 'Mach Speed', 29: 'Shadow Veil', 34: 'Wind Fracture', 38: 'Void Collapse', 43: 'Sky Scorch' },
        'evolve': None},
    'Prowscar': {
        'stats': {'type': ['dark'], 'health': 60, 'attack': 95, 'defense': 70, 'speed': 80},
        'moves': {0: 'Bitemark', 1: 'Arise', 8: 'Dark Energy', 12: 'Lock Jaw', 15: 'Fear', 18: 'Double Jab', 21: 'Shadow Veil', 25: 'Haunt'},
        'evolve': None},
    'Floravel': {
        'stats': {'type': ['earth'], 'health': 60, 'attack': 85, 'defense': 95, 'speed': 60},
        'moves': {0: 'Vine Snare+', 1: 'Arise', 8: 'Boulder Smash', 13: 'Synthesis', 18: 'Dread Thorn', 23: 'Crusher', 26: 'Synthesis', 28: 'Terraform'},
        'evolve': {19: 'Palidian'}},
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
        'evolve': {19: 'Tygraflare'}},
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
        'stats': {'type': ['rock', 'magma'], 'health': 120, 'attack': 105, 'defense': 135, 'speed': 80},
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
    'Gourdecrux': {
        'stats': {'type': ['dark', 'magma'], 'health': 105, 'attack': 142, 'defense': 98, 'speed': 112},
        'moves': {0: 'Dark Energy', 1: 'Fear', 9: 'Fireball', 15: 'Haunt', 19: 'Distortion', 23: 'Lava Burst', 26: 'Force Shift', 29: 'Thunder Blitz', 33: 'Solar Flare', 37: 'Void Collapse'},
        'evolve': None},
    'Palidian': {
        'stats': {'type': ['earth', 'rock'], 'health': 90, 'attack': 124, 'defense': 136, 'speed': 105},
        'moves': {0: 'Vine Snare+', 1: 'Arise', 8: 'Boulder Smash', 13: 'Synthesis', 18: 'Dread Thorn', 23: 'Crusher', 26: 'Synthesis', 28: 'Terraform', 31: 'Iron Core', 34: 'Raging Pursuit', 36: 'Tree Spin', 39: 'Crash Impact'},
        'evolve': None},
    'Rockull': {
        'stats': {'type': ['rock'], 'health': 160, 'attack': 100, 'defense': 150, 'speed': 50},
        'moves': {0: 'Dust Beam', 4: 'Sand Kick', 8: 'Boulder Smash', 14: 'Momentum', 17: 'Force Shift', 20: 'Iron Core', 26: 'Crusher',30:'Prism Glare', 34: 'Crash Impact'},
        'evolve': None},
    'Prickly': {
        'stats': {'type': ['earth','spike'], 'health': 71, 'attack': 90, 'defense': 79, 'speed': 60},
        'moves': {0: 'Arise', 3: 'Sand Kick', 6: 'Vine Snare', 10: 'Quick Slash', 14: 'Double Jab', 17:'Synthesis', 25: 'Floral Resonance'},
        'evolve': {21: 'Cyflactus'}},
    'Cyflactus': {
        'stats': {'type': ['earth', 'magma'], 'health': 115, 'attack': 131, 'defense': 119, 'speed': 85},
        'moves': {0: 'Arise', 3: 'Sand Kick', 6: 'Vine Snare', 10: 'Quick Slash', 14: 'Double Jab', 17: 'Synthesis', 21: 'Flame Shatter', 26: 'Dread Thorn', 30: 'Floral Resonance', 34: 'Tree Spin', 37: 'Spike Storm', 40: 'Solar Flare'},
        'evolve': None},

    # PLACEHOLDER — stats/type/moves are stand-ins pending real design.
    'Rhysnow': {
        'stats': {'type': ['ice'], 'health': 90, 'attack': 88, 'defense': 102, 'speed': 55},
        'moves': {0: 'Arise', 4: 'Snowfall', 8: 'Boulder Smash', 15: 'Iron Core', 18: 'Crusher', 22: 'Double Jab', 25: 'Hail Storm'},
        'evolve': {25: 'Rhinecicle'}},
    # PLACEHOLDER — stats/type/moves are stand-ins pending real design.
    'Rhinecicle': {
        'stats': {'type': ['ice', 'rock'], 'health': 110, 'attack': 120, 'defense': 145, 'speed': 75},
        'moves': {0: 'Arise', 4: 'Snowfall', 8: 'Boulder Smash', 15: 'Iron Core', 18: 'Crusher', 22: 'Double Jab', 25: 'Hail Storm', 28: 'Hyperfrost', 31: 'Momentum', 33: 'Freeze Blast', 36: 'Frozen Aura', 40: 'Crash Impact'},
        'evolve': None},
    # PLACEHOLDER — stats/type/moves are stand-ins pending real design.
    'Celestreeyl': {
        'stats': {'type': ['earth', 'light'], 'health': 129, 'attack': 139, 'defense': 119, 'speed': 129},
        'moves': {0: 'Arise', 4: 'Vine Snare', 9: 'Prism Glare', 15: 'Dread Thorn', 16: 'Terraform', 19: 'Hurricane', 24: 'Piercing Light', 26: 'Synthesis', 28: 'Refraction', 30: 'Tree Spin', 35: 'Spectral Overload', 38: 'Gamma Wave'},
        'evolve': None},

}




TYPE_DATA = {
    'aqua': {
        'super_eff': ['magma', 'rock'],
        'weak_eff': ['aqua', 'earth', 'ice', 'ancient'],
        'resist': ['aqua', 'magma', 'ice'],
        'weak_to': ['earth', 'lightning'],
        'color': config.AQUA
    },
    'magma': {
        'super_eff': ['earth', 'ice'],
        'weak_eff': ['aqua', 'magma', 'rock', 'ancient'],
        'resist': ['magma', 'earth', 'dark', 'ice'],
        'weak_to': ['aqua', 'rock'],
        'color': config.MAGMA
    },
    'earth': {
        'super_eff': ['aqua', 'rock', 'lightning'],
        'weak_eff': ['magma', 'earth', 'spike', 'flying', 'ancient'],
        'resist': ['aqua', 'earth', 'light'],
        'weak_to': ['magma', 'spike', 'flying', 'ice'],
        'color': config.EARTH
    },
    'dark': {
        'super_eff': ['light', 'spike'],
        'weak_eff': ['magma', 'dark'],
        'resist': ['dark', 'spike', 'lightning'],
        'weak_to': ['light', 'ancient'],
        'color': config.DARK
    },
    'light': {
        'super_eff': ['dark', 'spike'],
        'weak_eff': ['earth', 'light'],
        'resist': ['light', 'spike', 'lightning'],
        'weak_to': ['dark', 'ancient'],
        'color': config.SOFT_WHITE
    },
    'spike': {
        'super_eff': ['earth', 'rock', 'ancient'],
        'weak_eff': ['dark', 'light', 'flying'],
        'resist': ['earth', 'rock', 'ancient'],
        'weak_to': ['dark', 'light', 'flying'],
        'color': config.SPIKE
    },
    'flying': {
        'super_eff': ['earth', 'spike'],
        'weak_eff': ['rock', 'lightning'],
        'resist': ['earth', 'spike'],
        'weak_to': ['rock', 'lightning', 'ice'],
        'color': config.FLYING
    },
    'rock': {
        'super_eff': ['magma', 'flying', 'ice'],
        'weak_eff': ['spike'],
        'resist': ['magma', 'flying', 'lightning', 'ancient'],
        'weak_to': ['aqua', 'earth', 'spike'],
        'color': config.ROCK
    },
    'lightning': {
        'super_eff': ['aqua', 'flying'],
        'weak_eff': ['dark', 'light', 'rock', 'lightning', 'ancient'],
        'resist': ['flying', 'lightning'],
        'weak_to': ['earth'],
        'color': config.LIGHTNING
    },
    'ice': {
        'super_eff': ['earth', 'flying', 'ancient'],
        'weak_eff': ['aqua', 'magma', 'ice'],
        'resist': ['aqua', 'ice'],
        'weak_to': ['magma', 'rock'],
        'color': config.ICE
    },
    'ancient': {
        'super_eff': ['dark', 'light', 'ancient'],
        'weak_eff': ['spike', 'rock'],
        'resist': ['aqua', 'magma', 'earth', 'lightning'],
        'weak_to': ['spike', 'ice', 'ancient'],
        'color': config.ANCIENT
    }
}

#electric,rock,flying,ancient,ice


TYPE_CHART_VAL = {
    'aqua': {'aqua': 5, 'magma': 20, 'earth': 5, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 20, 'lightning': 10, 'ice': 5  , 'ancient': 5},
    'magma': {'aqua': 5, 'magma': 5, 'earth': 20, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 5, 'lightning': 10, 'ice': 20, 'ancient': 5},
    'earth': {'aqua': 20, 'magma': 5, 'earth': 5, 'flying': 5, 'dark': 10 , 'light': 10, 'spike': 5, 'rock': 20, 'lightning': 20, 'ice': 10,'ancient': 5},
    'flying': {'aqua': 10, 'magma': 10, 'earth': 20, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 20, 'rock': 5, 'lightning': 5, 'ice': 10,'ancient': 10},
    'dark': {'aqua': 10, 'magma': 5, 'earth': 10, 'flying': 10, 'dark': 5 , 'light': 20, 'spike': 20, 'rock': 10, 'lightning': 10, 'ice': 10,'ancient': 10},
    'light': {'aqua': 10, 'magma': 10, 'earth': 5, 'flying': 10, 'dark': 20 , 'light': 5, 'spike': 20, 'rock': 10, 'lightning': 10, 'ice': 10,'ancient': 10},
    'spike': {'aqua': 10, 'magma': 10, 'earth': 20, 'flying': 5, 'dark': 5 , 'light': 5, 'spike': 10, 'rock': 20, 'lightning': 10, 'ice': 10,'ancient': 20},
    'rock': {'aqua': 10, 'magma': 20, 'earth': 10, 'flying': 20, 'dark': 10 , 'light': 10, 'spike': 5, 'rock': 10, 'lightning': 10, 'ice': 20,'ancient': 10},
    'lightning': {'aqua': 20, 'magma': 10, 'earth': 10, 'flying': 20, 'dark': 5 , 'light': 5, 'spike': 10, 'rock': 5, 'lightning': 5, 'ice': 10,'ancient': 5},
    'ice': {'aqua': 5, 'magma': 5, 'earth': 20, 'flying': 20, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 10, 'lightning': 10, 'ice': 5,'ancient': 20},
    'ancient': {'aqua': 10, 'magma': 10, 'earth': 10, 'flying': 10, 'dark': 20 , 'light': 20, 'spike': 5, 'rock': 5, 'lightning': 10, 'ice': 10,'ancient': 20},

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
    'dinocenter_town2': {'world': 'DINOCENTER.tmx',   'spawn': (9, 12)},
    'research':     {'world': 'RESEARCH_LAB.tmx',    'spawn': (10, 11)},
    'gym1':         {'world': 'GYM1.tmx',             'spawn': (9, 13)},
    'gym2':         {'world': 'GYM2.tmx',             'spawn': (9, 13)},

    # Cobalt Cave — ROUTE3_4 <-> COBALT_CAVE1 (mouth of the cave)
    'Cobalt Cave':  {'world': 'COBALT_CAVE.world',    'spawn': (18, 6)},
    # COBALT_CAVE6 <-> ROUTE4.1 (far side of the cave). Both ends use a
    # dedicated entrance_id pair rather than a plain 'exit' tile because
    # COBALT_CAVE.world is one continuous stitched world — a generic exit
    # there just pops whatever was last pushed onto world_stack, which is
    # only ever ROUTE3_4 (the Cobalt Cave mouth), never ROUTE4.1.
    'route4_1':     {'world': 'LOST_REGION.world',    'spawn': (-58, -42)},
    'cobalt_cave6': {'world': 'COBALT_CAVE.world',    'spawn': (-33, 42)},
    # COBALT_CAVE4 <-> SHADOWHQ1
    'shadowhq1':    {'world': 'SHADOWHQ1.tmx',        'spawn': (9, 13)},
    'cobalt':       {'world': 'COBALT_CAVE.world',    'spawn': (-11, 5)},

    # 'house_amber': {'world': 'HOUSE_AMBER.world',  'spawn': (3, 6)},
}

################## ENCOUNTER ZONES ####################
# encounter_data.py or near your config
#
# 'dinos' accepts either the plain old format:
#     "dinos": ["Bullicorn", "Voltzbee"]              # equal odds, available any time
# or a weighted/conditional format, per entry:
#     "dinos": [
#         {"name": "Prickly",  "weight": 0.7, "time": "night"},
#         {"name": "Prowscar", "weight": 0.2, "time": "night"},
#         {"name": "Vusion",   "weight": 0.1},          # "time" omitted -> any time
#     ]
# 'weight' defaults to 1 (equal odds) and doesn't need to sum to any total —
# it's just relative. 'time' is "day", "night", or omitted for always-available.
# The two formats can mix within the same list.
def pick_zone_dino(zone_data, is_night):
    """Weighted-random pick from a zone's 'dinos' list, honoring each entry's
    optional 'time' gate. Returns None if nothing qualifies right now (e.g.
    a night-only zone during the day) — callers should treat that as "no
    encounter this time", not an error."""
    names, weights = [], []
    for entry in zone_data['dinos']:
        if isinstance(entry, str):
            name, weight, time = entry, 1, None
        else:
            name, weight, time = entry['name'], entry.get('weight', 1), entry.get('time')
        if time == 'night' and not is_night:
            continue
        if time == 'day' and is_night:
            continue
        names.append(name)
        weights.append(weight)
    if not names:
        return None
    return random.choices(names, weights=weights, k=1)[0]


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
        "dinos": ["Sortle", "Teamtwood"],
        "level_range": (6, 8)
    },


    
    "route2_grass": {
        "dinos": ["Teamtwood", "Netaslam", "Bullicorn", "Sortle"],
        "level_range": (6, 8)

    },

    "route2_burnt_grass": {
        "dinos": ["Sortle", "Teamtwood", "Creuw", "Prickly"],
        "level_range": (7, 11)

    },

        "route2_belowcorn": {
        "dinos": ["Sortle", "Prickly"],
        "level_range": (9, 12)

    },

        "corn_maze": {
        "encounter_rate": 0.05,
        "dinos": [
            {"name": "Prickly",  "weight": 0.4, "time": "night"},
            {"name": "Prickly",  "weight": 0.4, "time": "day"},
            {"name": "Prowscar", "weight": 0.4, "time": "night"},
            {"name": "Creuw", "weight": 0.6, "time": "day"},
            {"name": "Vusion",   "weight": 0.1, "time": "night"},
        ],
        "level_range": (11, 13)

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
    (16, -42, 37, -33, "route2_grass"),
    (38, -56, 78, -17, "route2_burnt_grass"),
    (86,-36,93,-30, 'route2_belowcorn'),
    (86,-73,150,-46, 'corn_maze'),


]

def get_zone_for_tile(tx, ty):
    for x1, y1, x2, y2, zone in ZONE_REGIONS:
        if x1 <= tx <= x2 and y1 <= ty <= y2:
            return zone
    return None


################## ROUTE/TOWN BANNER TRANSITIONS ####################
# Each entry is a short strip of world tiles (built from two endpoints
# that share either their x or their y) plus the name to show when the
# player steps onto any tile in that strip, keyed by the direction they
# were moving. Stepping onto the strip while moving a direction that
# isn't listed does nothing.
def _tile_strip(x1, y1, x2, y2):
    if y1 == y2:
        return [(x, y1) for x in range(min(x1, x2), max(x1, x2) + 1)]
    return [(x1, y) for y in range(min(y1, y2), max(y1, y2) + 1)]

ZONE_BANNER_TRANSITIONS = [
    {'tiles': _tile_strip(2, 32, 6, 32),     'up': 'Route 1',        'down': 'Silverleaf Town'},
    {'tiles': _tile_strip(15, -12, 15, -11), 'right': 'Sierra Town', 'left': 'Route 1'},
    {'tiles': _tile_strip(29, -27, 33, -27), 'up': 'Route 2',        'down': 'Sierra Town'},
    {'tiles': _tile_strip(89, -54, 89, -51), 'right': 'Corn Maze',   'left': 'Route 2'},
    {'tiles': _tile_strip(83, -59, 85, -59), 'up': 'Elder Town',     'down': 'Route 2'},
    {'tiles': _tile_strip(55, -68, 55, -70), 'left': 'Route 3',      'right': 'Elder Town'},
    {'tiles': _tile_strip(21, -75, 29, -75), 'up': 'Lake Meridian',  'down': 'Route 3'},
    {'tiles': _tile_strip(1, -58, 7, -58),   'down': 'Power Plant',  'up': 'Route 3'},
]

# (tile) -> transition dict, for O(1) lookup as the player steps tile by tile.
ZONE_BANNER_LOOKUP = {}
for _entry in ZONE_BANNER_TRANSITIONS:
    for _tile in _entry['tiles']:
        ZONE_BANNER_LOOKUP[_tile] = _entry

# ── Cave/HQ crossings ──────────────────────────────────────────────
# Entering/exiting a cave is a discrete entrance_id teleport (see
# ENTRANCE_DATA), not a walk across an adjacent tile the way the overworld
# crossings above are — so these are looked up by entrance_id instead of by
# tile, right when the teleport fires (see Game._do_entrance_teleport /
# _do_exit_teleport).
ENTRANCE_BANNER_NAMES = {
    'Cobalt Cave':  'Cobalt Cave',   # Route 3      -> Cobalt Cave (mouth)
    'route4_1':     'Route 4',      # Cobalt Cave  -> Route 4
    'cobalt_cave6': 'Cobalt Cave',  # Route 4      -> Cobalt Cave
    'shadowhq1':    'Shadow HQ',    # Cobalt Cave  -> Shadow HQ
    'cobalt':       'Cobalt Cave',  # Shadow HQ    -> Cobalt Cave
}

# entrance_id used to get IN (world_stack[-1]['entrance_id']) -> banner name
# to show when a generic 'exit' tile pops back out. Keyed by entrance_id
# rather than destination file, since current_world_file for anywhere in
# the overworld is always 'LOST_REGION.world' regardless of which route/town
# sub-map the player is standing in. Only entrances that need a crossing
# banner on the way back out belong here — most exits (homes, gyms,
# DinoCenter, ...) intentionally show nothing.
EXIT_BANNER_NAMES = {
    'Cobalt Cave': 'Route 3',  # Cobalt Cave -> Route 3 (mouth)
}



def LevelXP(level):
    return (level*1.7)**2.4

def XPtoLevel(XP):
    return int((XP ** (1/2.4)) / 1.7)


def calculate_xp_gain(player_level, opponent_level, enemy_name=None, base_xp=7, state_multiplier=1.0):
    if enemy_name and enemy_name in DINO_DATA:
        s = DINO_DATA[enemy_name]['stats']
        base_xp = (s['health'] + s['attack'] + s['defense'] + s['speed']) / 50

    ratio = opponent_level / player_level
    level_factor = max(0.3, min(1.3, ratio ** 0.35))

    xp = base_xp * opponent_level * level_factor * state_multiplier

    return max(5, int(xp))

### 0.5  catching
### 0.8  wild encounters
### 0.9  trainer battles
### 1.0  rivals, gym leaders, elite 4, bosses

def is_boss_tier_trainer(trainer_data):
    """Rivals, gym leaders, and story bosses share the top (1.0) XP
    multiplier tier — everyone else (including the rank-and-file trainers
    guarding a gym) battles at 0.9. A gym leader is any 'gym' biome trainer
    that isn't ranked 'lowest' (the gym's regular trainers)."""
    if trainer_data.get('rank') in ('rival', 'boss'):
        return True
    return trainer_data.get('biome') == 'gym' and trainer_data.get('rank') != 'lowest'

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

def Base_Stats(base, level, p=0.75):
    return round(base * (level / 50) ** p)


################## BATTLE MATHEMATICS #################

def Damage(level, attack, power, defender_defense, STAB, effectiveness, random): #randoom 217-255 , STAB (1,1.5), Type Modifier (40,20,10,5,2.5)
    return ((((((((2*level / 5 + 2) * attack * power)/(defender_defense * 0.95))/50)+2)*STAB)*effectiveness/10)*random)/255

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
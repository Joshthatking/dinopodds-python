import config
import math

TRAINER_DATA = {
    't1': {
        'dinos': {0: ('Anemamace',7), 1:('Vusion',8)},
        'dialog': {
			'default': ['Hey Trainer!', 'Lets Battle!'], 
			'defeated': ['You are very strong!', 'Let\'s fight again sometime?']},
		'directions': ['down'],
		'look_around': True,
		'defeated': False,
		'biome': 'forest'
		},

}



DINO_DATA = {
    'Vusion': {
        'stats': {'type': ['dark','magma'], 'health': 120, 'attack': 155, 'defense': 70, 'speed': 125},
        'moves': {0: 'Force Shift', 9: 'Fireball', 14: 'Conduit Surge',19: 'Shadow Veil'},
        'evolve': None},
    'Anemamace': {
        'stats': {'type': ['aqua','spike'], 'health': 140, 'attack': 125, 'defense': 100, 'speed':90},
        'moves': {0: 'Double Jab', 9: 'Whirlpool', 17: 'Wave Dash'},
        'evolve': None},
    'Corlave': {
        'stats': {'type': ['aqua'], 'health': 80, 'attack': 55, 'defense': 40, 'speed':25},
        'moves': {0: 'Whirlpool', 17: 'Wave Dash'},
        'evolve': 17},
    }
    




TYPE_DATA = {
    'aqua': {
        'super_eff': ['magma', 'rock'],
        'weak_eff': ['aqua', 'ancient', 'earth'],
        'resist':['aqua', 'ace'],
        'weak_to': ['earth', 'lightning'],
        'color': config.AQUA
    },
    'magma': {
        'super_eff': ['earth', 'ice'],
        'weak_eff': ['magma', 'ancient', 'rock', 'aqua'],
        'resist':['magma', 'ice'],
        'weak_to': ['aqua', 'rock'],
        'color': config.MAGMA
    },
    'earth': {
        'super_eff': ['aqua', 'rock', 'lighting'],
        'weak_eff': ['earth', 'ancient', 'flying'],
        'resist':['earth', 'spike'],
        'weak_to': ['magma', 'ice', 'flying'],
        'color': config.EARTH
    },
    'dark': {
        'super_eff': ['spike', 'monster'],
        'weak_eff': ['dark', 'light'],
        'resist':['lightning', 'spike', 'dark'],
        'weak_to': ['light', 'goo'],
        'color': config.DARK
    },
    'light': {
        'super_eff': ['dark', 'ancient', 'light'],
        'weak_eff': ['earth', 'lightning', 'metal'],
        'resist': ['spike', 'ice', 'rock'],
        'weak_to': ['lightning', 'ancient'],
        'color': config.SOFT_WHITE
    },
    'spike': {
        'super_eff': ['ancient', 'metal', 'rock'],
        'weak_eff': ['dark', 'earth', 'light'],
        'resist': ['flying', 'ice'],
        'weak_to': ['dark', 'light'],
        'color': config.SPIKE
    }
}

#electric,rock,flying,ancient,ice


TYPE_CHART_VAL = {
    'aqua': {'aqua': 5, 'magma': 20, 'earth': 5, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 20, 'lightning': 10, 'ice': 10, 'ancient': 5},
    'magma': {'aqua': 5, 'magma': 5, 'earth': 20, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 5, 'lighting': 10, 'ice': 20, 'ancient': 5},
    'earth': {'aqua': 20, 'magma': 5, 'earth': 5, 'flying': 5, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 20, 'lighting': 20, 'ice': 10,'ancient': 5},
    'flying': {'aqua': 10, 'magma': 10, 'earth': 20, 'flying': 10, 'dark': 10 , 'light': 10, 'spike': 20, 'rock': 5, 'lighting': 5, 'ice': 10,'ancient': 10},
    'dark': {'aqua': 10, 'magma': 10, 'earth': 10, 'flying': 10, 'dark': 20 , 'light': 5, 'spike': 20, 'rock': 10, 'lighting': 10, 'ice': 10,'ancient': 10},
    'light': {'aqua': 10, 'magma': 10, 'earth': 5, 'flying': 10, 'dark': 20 , 'light': 20, 'spike': 10, 'rock': 10, 'lighting': 10, 'ice': 10,'ancient': 5},
    'spike': {'aqua': 10, 'magma': 10, 'earth': 20, 'flying': 10, 'dark': 5 , 'light': 5, 'spike': 10, 'rock': 20, 'lighting': 10, 'ice': 10,'ancient': 20},
    'rock': {'aqua': 10, 'magma': 20, 'earth': 10, 'flying': 20, 'dark': 10 , 'light': 10, 'spike': 5, 'rock': 5, 'lighting': 20, 'ice': 20,'ancient': 10},
    'lightning': {'aqua': 20, 'magma': 10, 'earth': 5, 'flying': 20, 'dark': 10 , 'light': 20, 'spike': 5, 'rock': 5, 'lighting': 10, 'ice': 10,'ancient': 5},
    'ice': {'aqua': 5, 'magma': 5, 'earth': 20, 'flying': 20, 'dark': 10 , 'light': 10, 'spike': 10, 'rock': 10, 'lighting': 10, 'ice': 5,'ancient': 20},
    'ancient': {'aqua': 10, 'magma': 10, 'earth': 10, 'flying': 10, 'dark': 10 , 'light': 20, 'spike': 5, 'rock': 5, 'lighting': 10, 'ice': 10,'ancient': 20},



}





MOVE_DATA = {
    'Force Shift': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None,'type': 'dark'},
    'Double Jab': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'spike'},
    'Whirlpool': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'aqua'},
    'Shadow Veil': {'target': 'opponent', 'damage': 45, 'accuracy': 100, 'ability': None, 'type': 'dark'},
    'Fireball': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'magma'},
    'Lava Burst': {'target': 'opponent', 'damage': 60, 'accuracy': 90, 'ability': None, 'type': 'magma'},
    'Flame Shatter': {'target': 'opponent', 'damage': 55, 'accuracy': 100, 'ability': None, 'type': 'magma'},
    'Wave Dash': {'target': 'opponent', 'damage': 45, 'accuracy': 100, 'ability': None, 'type': 'aqua'},
    'Vine Snare': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'earth'},
    'Poison Ivy': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'earth'},
    'Conduit Surge': {'target': 'opponent', 'damage': 45, 'accuracy': 100, 'ability': None, 'type': 'lightning'},
    'Translucent Wave': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'light'},
    'Freeze Blast': {'target': 'opponent', 'damage': 60, 'accuracy': 100, 'ability': None, 'type': 'ice'},




    
    }






################## ENCOUNTER ZONES ####################
# encounter_data.py or near your config
ENCOUNTER_ZONES = {
    "starter_grass": {
        "dinos": ["Anemamace", "Corlave"],
        "level_range": (13, 14)
    },
    "deep_jungle": {
        "dinos": ["Venoshade", "Terraptor", "Leafu"],
        "level_range": (5, 10)
    },
    "volcano_top": {
        "dinos": ["Magmara", "Ashfang", "Crateradon"],
        "level_range": (10, 15)
    }
}



def LevelXP(level):
    return (level*1.93)**2 

def XPtoLevel(XP):
    return int(math.sqrt(XP)/1.93)


def calculate_xp_gain(player_level, opponent_level, base_xp=8, state_multiplier=1.0, party_size=1):
    # Level difference factor (punish farming low levels)
    level_factor = max(0.2, opponent_level / player_level)  # minimum 0.2 so it never hits zero
    
    # Diminishing returns: scale XP when overleveled
    if player_level > opponent_level:
        diminishing = 1 - ((player_level - opponent_level) * 0.05)  # lose 5% per level over
        diminishing = max(diminishing, 0.2)  # never go below 20%
    else:
        diminishing = 1.0  # full XP if enemy is >= level
    
    # Base XP calc
    xp = base_xp * opponent_level * level_factor * diminishing
    
    # Context multiplier (bosses, events, etc.)
    xp *= state_multiplier
    
    # Split XP among party members
    xp /= max(party_size, 1)
    
    return int(xp)

### .5 for catching
### .65 for encounters
### .75 for battles
### 1 for Rivals, Gyms, Elite 4

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
    return 1.5 if move_type in attacker_types else 1.0

def random_damage_factor():
    # Your formula expects 217..255 inclusive
    import random
    return random.randint(217, 255)
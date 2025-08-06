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
        'super_eff': ['earth', 'metal'],
        'weak_eff': ['magma', 'ancient', 'rock'],
        'resist':['magma', 'ice'],
        'weak_to': ['aqua', 'rock'],
        'color': config.MAGMA
    },
    'earth': {
        'super_eff': ['aqua', 'rock', 'lighting'],
        'weak_eff': ['earth', 'ancient', 'metal'],
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
        'super_eff': ['dark', 'ancient', 'spike'],
        'weak_eff': ['earth', 'lightning', 'metal'],
        'resist': ['spike', 'ice', 'rock'],
        'weak_to': ['lightning'],
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


def LevelXP(level):
    return (level*1.93)**2 

def XPtoLevel(XP):
    return int(math.sqrt(XP)/1.93)


def calculate_xp_gain(player_level, opponent_level, base_xp=50, state_multiplier=1.0, party_size=1):
    # Level difference factor (punish farming low levels)
    level_factor = max(0.2, opponent_level / player_level)  # minimum 0.2 so it never hits zero
    
    # Diminishing returns: scale XP when overleveled
    if player_level > opponent_level:
        diminishing = 1 - ((player_level - opponent_level) * 0.02)  # lose 5% per level over
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


##################### BASE STATS ##################

def HP_Base(base_hp,level, p):
    return round(base_hp * (level / 50) ** p + 10)

def Base_Stats(base, level):
    return round(base * (level/50 ))


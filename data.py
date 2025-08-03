import config

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
        'moves': {0: 'Force Shift', 16: 'Shadow Veil'},
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
        'resist':['magma', 'ice', 'spike'],
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
        'weak_eff': ['dark', 'ancient', 'metal'],
        'resist':['earth', 'spike'],
        'weak_to': ['magma', 'ice', 'flying'],
        'color': config.DARK
    }
}




ATTACK_DATA = {
    'Force Shift': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None,'type': 'dark'},
    'Double Jab': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None, 'type': 'spike'},
    'Whirlpool': {'target': 'opponent', 'damage': 30, 'accuracy': 100, 'ability': None, 'type': 'aqua'},
    
    }
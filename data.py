TRAINER_DATA = {
    't1': {
        'dinos': {0: ('Vusion',7), 1:('Vusion',8)},
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
        'stats': {'type': 'dark', 'health': 120, 'attack': 155, 'defense': 70, 'speed': 125},
        'moves': {0: 'Force Shift', 16: 'Shadow Veil'},
        'evolve': None},
    }


ATTACK_DATA = {
    'Force Shift': {'target': 'opponent', 'damage': 40, 'accuracy': 100, 'ability': None,'type': 'dark'},
}
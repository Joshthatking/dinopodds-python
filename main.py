import pygame
import config
from game import Game


if __name__ == '__main__':
    game = Game()
    game.run()


## later add moves to summary party screen, then box logic if you have more than 6/5 dinos. add symbols for stats

# add message order in encounters, finalize xp logic, transitions? party box logic? basics for attacking?
#last thing for the night, how can i make it in catch attempt that if I succeed on catching i stay in encounter screen for the xp to load as the message box of catching comes in, and then after I press ok to that and ok to new dino added to party then it does transition back to world
import pygame
import config
from game import Game


if __name__ == '__main__':
    game = Game()
    game.run()


##  box logic if you have more than 5 dinos. add symbols for stats!

# ad finalize xp logic (too high right now on catching), transitions? party box logic? basics for attacking?

###  add attack and defense math

######  add level up once xp goes over and a screen that shows stats boosted with current + and then new 
### then add box logic for when over 5 dinos in party, also add switch to active and (switch to box in party when in world )
# then add attack and defense logic for moves,
# finally add sequential turns where the wild dino chooses random moves 

#after all of that we can add more art work for transitions maybe and idle animations in party / encounters
# then learn how to add new NPC's that have dialogue for battles
# also begin adding triggered events based on location and order of things
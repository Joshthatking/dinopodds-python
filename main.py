import pygame
import config
from game import Game


if __name__ == '__main__':
    game = Game()
    game.run()


## add symbols for stats!


###  also a button to switch to active in party, also evolution logic

######  xp screen that shows stats boosted with current + and then new 
# then add attack and defense logic for moves,
# finally add sequential turns where the wild dino chooses random moves 

#after all of that we can add more art work for transitions maybe and idle animations in party / encounters
# then learn how to add new NPC's that have dialogue for battles
# also begin adding triggered events based on location and order of things

#### THINGS TO ADD FOR BATTLES
## 1) no xp if fainted at end of battle COMPLETE
## 2) make xp for leveling up more;; -- or award less xp! - COMPLETE for now
## 3) be able to swap and it count as a turn, same for a failed catch attempt

## 4) Evolution logic after battles 
## 5) Moveset logic for when you have 4 and can learn a new one
## 6) Moveset randomness set for encounters based on level (amount of moves + which moves)
## 7) Build DinoCenter for healing
## 8) Add Trainer Sprites around map for battles - this includes LOS detection, facing when speaking, battle animation, trainer moveset, no dinopod during battles, currency system

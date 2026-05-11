import pygame
import pytmx
import config
from game import Game


if __name__ == '__main__':
    game = Game()
    game.run()


## add symbols for stats!

#### make an active spot, different highlight in party preview, allow switching from party screen overworld, always comes out first, maybe add a 2nd active for doubles?


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
## 3) be able to swap and it count as a turn, same for a failed catch attempt  -- COMPLETE

## 4) Evolution logic after battles 
## 5) Moveset logic for when you have 4 and can learn a new one
## 6) Moveset randomness set for WILD encounters based on level (amount of moves + which moves)
## 7) Build DinoCenter for healing -- logic half done, design not
## 8) Add Trainer Sprites around map for battles - this includes LOS detection, facing when speaking, battle animation, trainer moveset, no dinopod during battles, currency system
## 9) Encounter Trainer Animation, ball thrown and catch animation
## 10) Build Assets for First and Second Gyms and Towns 

#8/22 - enemy turn after failed catch attempt
#8/23 - worked on adding idle animations to party preview and start of encounter -- fix encounter animation
#8/27 - Dinopodd throw and open animation for catching
#8/30 - Fixed Encounter Animation, added all colors and adjusted type effectiveness, Switch turn after swapping DINO
#8/31 - Evolution Logic - COMPLETE ----  also soon need logic for choosing moves when at 4 already 

################## April 2026 - Claude Assistance ##############
#4/28 - Rewrote code to clean up, fixed encounter messages in left box, fixed sizing, attempted to resolve sprite location in encounter
#5/3 - TILED CONVERSION - new map built in tiled with deviantart assets - Layers 4>= render above player, collision = FALSE
#5/4 - .WORLD and folder reorganization for TILED, GYM 1 almost - COMPLETE
#5/4 - Cont.
# battle mechanic dialogue = TYPED, health bar slide - COMPLETE
# Movement logic - stop moving after encounter / move only direction already facing - COMPLETE
# New map SPECIFIC ENCOUNTER LOGIC - COMPLETE in data.py
# Adjust CUSTOM Encounter size logic - COMPLETE in config.py
# NPC addition, Sprite sheet logic, npc interaction + walking up to battle logic - COMPLETE

#5/5
#NPC bug fix on dinos in battle, show icon of # of dinos now and when fainted
#DIALOGUE - adjust where it forces you to interact to go to next line, when you interact before done typing it goes to end of message then you must interact again
#fix xp gain until after dino is defeated to show and add to xp bar
#ENTRANCE metadata teleport to interior.world and have set place for each teleport
##### ENTRANCE - create Object layer, make rectangle over entrance, put string entrance_id = home 

#5/6
### FIX EXIT AND ENTRANCE on JET HOME - COMPLETE
#Dino center complete with teleport
#5/7
#Day/Night Cycle - COMPLETE

#5/8
#3 Starter spawns and pick up functions! - COMPLETE
#HEALING center and purchasing items center with NPC and dialogue logic - COMPLETE
#Sprite sheet with DC center assets and dinopod fixed for pick up and for DC animation - COMPLETE
#Eclipse mode BOOL - COMPLETE
# BATTLE Damage flashing indicator animation - COMPLETE

#5/9
#FIXEDBUG - spam j in battle no longer freezes game - COMPLETE
#Add speed in battle to determine order - COMPLETE
#PC system and swapping order - COMPLETE
#fix xp diminishing returns and overall state multipliers - COMPLETE
#fix battle perspectives - COMPLETE
#Added Trainer Card - COMPLETE
#Add number of items and confirmation at DC Mart- COMPLETE

#5/10
#MOVE ABILITIES and text/icons - COMPLETE
#Add a DEFEND button in battle separate from moves 3 total uses, can only use once every other turn - COMPLETE
#Block menu ability when challenged to battle  and items and running - COMPLETE
#Types of Ranks for trainer battles, set up moves when user defends 20-50% of the time to punish 15/25% for piercing defend - COMPLETE

#NEED to fix index out of range - pc box storage when having one dino left, bug occurs during start menu party being opened after
#add type chart to read in dinocenter by pc

#add traits one for each dino family, and add natures just one per stat (increases by 5%)
# event triggers, interactions (pick up, read, surf) , teleport on entrance, map for buildings
# battle animation for attacks

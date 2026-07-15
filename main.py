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

#5/11
#NEED to fix index out of range - pc box storage when having one dino left, bug occurs during start menu party being opened after
#DOUBLE BATTLES - COMPLETE
#Add Sprinting - COMPLETE
#Add text of xp earned in doubles - COMPLETE
#adjust XP again to prevent 0 in large gaps of levels - COMPLETE* too much xp,

#5/12
#Fix double battle screen + add Floravel and Prowscar - COMPLETE
#FIX Defend order always being first and not carrying over to 2nd turn - COMPLETE
#add type chart to read in dinocenter by pc - COMPLETE

#5/13
#Add more trainers to route 1 - COMPLETE
#Adjust xp, make it less rewarding overall by a little-medium - COMPLETE
#Fix bug where dinos are spawning on the dotted grass - should only be encounter grass - COMPLETE

#5/17
#add natures just one per stat (increases by 10%) - COMPLETE
# how to start sequential story and with save and new adventure screen at start after intro
#Night mode and Eclipese mode overlay in battles - COMPLETE

#5/18
#add dinopods to route 1 and 1.2 for player to catch dinos - COMPLETE
# adjust darkness levels (-) for night and eclipse mode in battles, also fix bag - COMPLETE
# Research Lab + Event 2 Returning dinos to professor - COMPLETE

#5/20
# Move Menu for  more than 4 moves in party - COMPLETE
# Dinodex to menu - COMPLETE

#5/21
#Added Space background for event 0 introduction to story - COMPLETE
#Added gym block guy till after speaking with Skyy in Route 1.4 - COMPLETE
#Skyy in Route 1.4 big story dialogue and back to Daytime! - COMPLETE


#5/23 
#Double battle visual glitch fixed - COMPLETE
# Bullicorn added - COMPLETE
# Gray rival battle after speaking with skyy event - COMPLETE


#5/24
# Gym 1 battle sequence and Badge - COMPLETE
# FIX: saving saves dinos but offsets position and resets battles
# FIX: make sky force end battle dialogue after rewarding badge - COMPLETE
# Fix text coming off dialogue box screen sometimes - COMPLETE

#Fix double battles visual glitch still
#Fix Items respawning after teleporting - COMPLETE
#Fix order of dinos when selected in party, first alwasy goes first - COMPLETE

#5/25
# Fix spawns route2 - COMPLETE

#5/26
# added white box around ! in encounters - COMPLETE
# Adjust xp scaling for party size 2x - 1.5 active, 1.33,1.25,1.1,1.0 - COMPLETE
# When game is saved and continued from menu, current day/night/eclipse is saved - COMPLETE
# When walking into houses or Dinocenters or gym, trainer battles should always be false - COMPLETED
# skyy bump bug - COMPLETED
# gray facing - COMPLETED
# Added grunt battle to Route2 - COMPLETED
# Adjust size of text on moves in move box - COMPLETE

#5/27
# Fix glitch if dino faints but front of party wastes turn
# Fix visual glitch on gym trainer with wrong dino - same for rival make sure order of dinos and png is correct - COMPLETE
# Allow users to hit i in battle over move to see info - COMPLETED
# Fix glitch where moves and visual of move is saved after switching - COMPLETE
# Adjust xp gains again lower xp scaling with party, 1.5x active, 1.25, 1, .85. .75 also apply this logic if a dino faints
# Add swap training for xp gains 

#6/19!
# Add Drafyton to game! 

#6/22
# XP rework , more xp and less floor on lower level, higher level drop off

#6/24
# Auraliz/Voltzbee into game!

#6/25
# ADD a section in the dinodex of weaknesses, and resistances to each dino with colorful icons and text
# Added Teamtwood and Tygrafire
# Need to make the stats not be linear to level 50 base stats, let them be exponential and fade slower towards 50
# BUFF STARTERS

#6/26
# Fixed lightning in type val
# Bouldava
#  Nerf Luna - moved moves around

#6/28
# Added Ghoulflame
#lower xp gain a little for on level dinos or higher, lower multiplayer slightly on rival 
#DEFENDER DEFENSE *.95 to make attacks more effective ---**** CHANGE IF NEEDED
# Route 1.4 Lore added

#6/29
#Reduce xp share xp per size of party
#adjust moves early game (Teamtwood/Bullicorn/Voltzbee)
# TygraFlare - design and name change
# added Scarecrux
# ROUTE 2 expansion
# 15% -> 10% ENCOUNTER RATE

#6/30
#TOWN 2 - Elder Town 90% complete 
#CORN MAZE - 90% Complete

#7/6


# make corn maze encounters 5%

# Need to edit gym badges, add all dinos to gym1
# Need to add teleport for each house then gym1 fin. 

# Add Double battle against grunts when walking to route1.4, over hear them speaking
# Rival comes to join the fight with you using, your rts weakness
# After the fight, that was weird... heals you, and then fair battle against rival
# Then proceed with skyy dialogue and then gym1
# GYM 1 designed and add gym event with trainers 
#add traits one for each dino family



# event triggers, interactions (pick up, read, surf) , teleport on entrance, map for buildings
# battle animation for attacks
 
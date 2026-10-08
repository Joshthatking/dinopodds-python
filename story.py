# Story events are executed in sequence during a new game run.
# Each event fires once and is remembered via story_flags in the save file.
#
# Trigger types:
#   "new_game"  - fires immediately when starting a new game (use next_event to chain)
#   dict        - fires when location and/or required flags are all satisfied
#                 {"requires_flags": ["flag_a"], "location": "zone_name"}
#
# Award fields are all optional. Omit or leave empty if unused.
#
# ══════════════════════════════════════════════════════════════════
# CODED STORY SEQUENCE  (flag set → what happens next)
# ══════════════════════════════════════════════════════════════════
#
# 1. NEW GAME  →  game_intro_done
#       Intro text plays immediately on new game.
#
# 2. LEAVE HOME (first time on overworld)  →  amber_intro_done
#       Professor Amber walks up, gives eclipse warning dialogue,
#       teleports to tile (7,34) as a guard blocking the grass.
#       Eclipse overlay activates. Day/night cycle paused in eclipse.
#
# 3. CATCH THE 3 MISSING DINOS  →  encounters_unlocked
#       While Amber guards the grass entrance the player must first
#       collect dinos already visible nearby. Once the guard NPC is
#       removed (cleared by Amber lab event) encounters are unlocked.
#
# 4. RETURN TO RESEARCH LAB, TALK TO AMBER  →  amber_lab_done
#       Amber receives the dinos, rewards the player.
#       Skyy NPC is now spawned on the overworld (Route 1).
#
# 5. TALK TO SKYY ON OVERWORLD  →  (no flag yet — triggers gym sequence)
#       Skyy walks away south, gym guard is removed.
#       Eclipse ends, day/night resets.  →  gym1_accessible
#
# 6. SKYY GUARD LEAVES  →  gym1_accessible
#       Gym 1 entrance is now open.
#       Gray (rival) spawns on Route 1 for a mandatory battle.
#
# 7. DEFEAT GRAY ON ROUTE 1  →  gray_route1_done
#       Gray walks away via cutscene.
#       Skyy now appears inside Gym 1 as the gym leader.
#
# 8. ENTER GYM 1, DEFEAT SKYY  →  gym1_leader_defeated
#       Sierra Badge awarded.
#
# 9. REACH TILE X=88 IN ROUTE2.6 (CORN MAZE)  →  gym2_corn_maze_reveal_done
#       Log and Curfeu cutscene: folklore about the scarecrow/Luna, the
#       Creuws dance and flee, the scarecrow briefly glows. Log and Curfeu
#       walk off afterward.
#
# 10. REACH TILE X=88 IN ROUTE2.6  →  route26_abby_escort_done
#       Abby approaches, explains the solar panel mission, guides the
#       player from ROUTE2.6 through 2.5/2.2/2.3 to (66,-25), then joins
#       as a following ally.
#
# 11. DEFEAT THE GRUNT DOUBLE BATTLE  →  vanessa_shadow_event_done
#       Abby heals the party, Vanessa (Shadow Team Leader) confronts the
#       player, a rotating 4-dino double battle follows (Abby fights
#       alongside the player). Win or lose, Vanessa taunts and leaves;
#       Abby heals again, says her goodbyes, and departs. Night falls.
#
# 12. ENTER GYM 2, DEFEAT LOG  →  gym2_leader_defeated
#       Earth Badge awarded. (Gym 2's guard only clears once
#       vanessa_shadow_event_done is set — see _maybe_add_gym2_blocker.)
#
# 12b. EXIT GYM 2, SAM GIVES SURF  →  sam_surf_intro_done
#       Sam (Gym 3 leader) waits at (63, -65) beside the Gym 2 exit,
#       introduces himself, unlocks Surf (surf_unlocked), then walks to
#       (55, -69) and disappears (see Game._check_sam_surf_intro).
#
# 13. BEAT GYM 2, CROSS INTO ROUTE 3 AT (33, -65)..(33, -59)  →  gray_route3_done
#       Rival Gray's rematch. Input pauses, Gray walks in from 7 tiles to
#       the player's left, dialogue plays, then a battle: Chomper (18),
#       Prowscar (19), Sortle (20), leading up to the evolved form of the
#       starter that counters the player's — same counter-type trick as
#       Gray's first battle (see Game._maybe_add_gray_rival /
#       _start_gray2_route3_cutscene), just level 21 and evolved this time.
#       Win or lose, Gray walks off 7 tiles to the left.
#
# 14. POWER PLANT TAKEDOWN  →  pp_eclipse_reveal_done
#       Skyy pulls the player into the Power Plant to investigate the
#       disruptions: a scripted grunt1/grunt2 double battle alongside Skyy,
#       then inside POWER_PLANT_IN3 the elite pp_grunt_a/pp_grunt_b pair
#       (sequential single battles) — only that inner pair is required to
#       finish the quest (see Game._pp_all_battles_done). Winning both
#       makes them teleport away in a black flash. Exiting the Power Plant
#       afterward, Skyy and Abby are already waiting together outside (the
#       Power Plant's own guard grunt is gone by then); one more step
#       triggers their dialogue — Amber's warning, Skyy's "I should have
#       known this was a trick," three yellow solar flares, eclipse mode
#       forcibly activating, and Skyy's closing line sending the player to
#       the Cave Jet — after which both walk off toward Cobalt Cave for
#       good (see Game._start_pp_exit_reveal_cutscene onward).
#
# 15. SHADOW GROUP CONFRONTATION  →  shadow_confrontation_done
#       The moment the player next enters Cobalt Cave, Abby, Skyy and Gray
#       are already standing in COBALT_CAVE1 — crossing either of two tiles
#       just inside the room force-walks the player up to the group (input
#       blocked) for a scripted talk: Gray explains Curfeu went alone into
#       the Shadow Group's makeshift base, Skyy worries the leaders are
#       tough, Abby volunteers to hold the cave's entrance and sends Gray to
#       watch the other one while Skyy and the player go back Curfeu up.
#       Gray and Abby then walk off and take up permanent guard posts —
#       Gray teleports to the Route 4 side of the cave, Abby stays within
#       COBALT_CAVE1 — while Skyy is left standing by, since where he/the
#       player go to find Curfeu next isn't built yet (see
#       Game._check_shadow_confrontation_trigger onward).
#
# ══════════════════════════════════════════════════════════════════

STORY_EVENTS = [
    {
        "id": "game_intro",
        "trigger": "new_game",
        "messages": [
            "Welcome to the world of DinoPodds!",
            "Ancient creatures unlike anything you've seen roam this land.",
            "As a trainer, you'll explore, battle, and catch DinoPodds.",
            "Good luck out there. Your adventure begins now!",
        ],
        "award_items": {},
        "award_coins": 0,
        "award_dinos": [],
        "sets_flags": ["game_intro_done"],
        "next_event": None,
    },

    # ── Future events ──────────────────────────────────────────────────────────
    # Uncomment and fill in as the story develops.
    #
    # {
    #     "id": "first_town",
    #     "trigger": {"requires_flags": ["game_intro_done"], "location": "town_zone"},
    #     "messages": ["You've reached the first town!", "..."],
    #     "award_items": {}, "award_coins": 0, "award_dinos": [],
    #     "sets_flags": ["first_town_visited"],
    #     "next_event": None,
    # },
]


# ══════════════════════════════════════════════════════════════════
# QUEST_STEPS — ordered milestones for the Sandbox quest-debug menu
# (Ctrl+Q). Selecting a step sets its flag (and every earlier step's
# flag) True and every later step's flag False, so it can jump either
# direction. "defeated_trainers"/"badges" are applied cumulatively the
# same way. See the CODED STORY SEQUENCE comment above for context.
# ══════════════════════════════════════════════════════════════════
QUEST_STEPS = [
    {
        "id": "game_intro_done",
        "label": "1. New Game Intro",
        "flag": "game_intro_done",
    },
    {
        "id": "amber_intro_done",
        "label": "2. Left Home - Amber Intro",
        "flag": "amber_intro_done",
    },
    {
        "id": "encounters_unlocked",
        "label": "3. Collected 3 Dinos - Encounters Unlocked",
        "flag": "encounters_unlocked",
    },
    {
        "id": "amber_lab_done",
        "label": "4. Returned Dinos to Amber",
        "flag": "amber_lab_done",
    },
    {
        "id": "gym1_accessible",
        "label": "5. Talked to Skyy - Gym 1 Accessible",
        "flag": "gym1_accessible",
    },
    {
        "id": "gray_route1_done",
        "label": "6. Defeated Gray (Route 1 Rival)",
        "flag": "gray_route1_done",
        "defeated_trainers": ["gray"],
    },
    {
        "id": "gym1_leader_defeated",
        "label": "7. Defeated Gym 1 Leader (Skyy)",
        "flag": "gym1_leader_defeated",
        "defeated_trainers": ["skyy"],
        "badges": ["sierra"],
    },
    {
        "id": "gym2_corn_maze_reveal_done",
        "label": "8. Corn Maze Reveal (Log & Curfeu)",
        "flag": "gym2_corn_maze_reveal_done",
    },
    {
        "id": "route26_abby_escort_done",
        "label": "9. Abby Joins - Route 2.6 Escort",
        "flag": "route26_abby_escort_done",
    },
    {
        "id": "vanessa_shadow_event_done",
        "label": "10. Solar Panel Investigation - Defeated Vanessa",
        "flag": "vanessa_shadow_event_done",
        "defeated_trainers": ["grunt1", "grunt2", "vanessa"],
    },
    {
        "id": "gym2_leader_defeated",
        "label": "11. Defeated Gym 2 Leader (Log)",
        "flag": "gym2_leader_defeated",
        "defeated_trainers": ["log"],
        "badges": ["earth"],
    },
    {
        "id": "sam_surf_intro_done",
        "label": "11b. Sam Gives Surf (Outside Gym 2)",
        "flag": "sam_surf_intro_done",
    },
    {
        "id": "gray_route3_done",
        "label": "12. Defeated Gray (Route 3 Rematch)",
        "flag": "gray_route3_done",
        "defeated_trainers": ["gray2"],
    },
    {
        "id": "pp_eclipse_reveal_done",
        "label": "13. Power Plant Takedown",
        "flag": "pp_eclipse_reveal_done",
        "defeated_trainers": ["grunt1", "grunt2", "pp_grunt_a", "pp_grunt_b", "pp_grunt_c", "pp_grunt_d"],
    },
    {
        "id": "shadow_confrontation_done",
        "label": "14. Shadow Group Confrontation",
        "flag": "shadow_confrontation_done",
    },
    {
        "id": "gym3_leader_defeated",
        "label": "15. Defeated Gym 3 Leader (Sam)",
        "flag": "gym3_leader_defeated",
        "defeated_trainers": ["sam"],
        "badges": ["aqua"],
    },
]

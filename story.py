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
]

# Story events are executed in sequence during a new game run.
# Each event fires once and is remembered via story_flags in the save file.
#
# Trigger types:
#   "new_game"  - fires immediately when starting a new game (use next_event to chain)
#   dict        - fires when location and/or required flags are all satisfied
#                 {"requires_flags": ["flag_a"], "location": "zone_name"}
#
# Award fields are all optional. Omit or leave empty if unused.

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

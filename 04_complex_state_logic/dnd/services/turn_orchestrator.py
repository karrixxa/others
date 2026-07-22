
import json
import os

STATE_FILE = "/home/cxiong/hermes_rpg/profiles/game_state.json"

def init_state():
    if not os.path.exists(STATE_FILE):
        state = {
            "current_turn": 0,
            "turn_queue": [],
            "active_party": "party_01",
            "combat_status": "exploration" # exploration, combat, dialogue
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)

def get_state():
    init_state()
    with open(STATE_FILE, 'r') as f:
        return json.load(f)

def update_queue(members):
    state = get_state()
    state["turn_queue"] = members
    state["current_turn"] = 0
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def advance_turn():
    state = get_state()
    if not state["turn_queue"]:
        return None
    
    current_idx = state["current_turn"]
    next_idx = (current_idx + 1) % len(state["turn_queue"])
    state["current_turn"] = next_idx
    
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)
    
    return state["turn_queue"][next_idx]

def get_current_actor():
    state = get_state()
    if not state["turn_queue"]:
        return None
    return state["turn_queue"][state["current_turn"]]

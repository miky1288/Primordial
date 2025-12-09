import json
import os

STATE_FILE = "state.json"

def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "version": 1.0,
            "long_memory": [],
            "short_memory": [],
            "meta": {"curiosity": 10, "coherence": 10, "persona": "evolutiva"},
        }
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

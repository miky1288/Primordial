# evolution_engine.py (corregido)
import os
import json
import time
from state_manager import load_state, save_state
import agent

VERSIONS_DIR = "versions"
PROPOSALS_DIR = "proposals"
EVOLUTION_DIR = "evolutionary"

os.makedirs(VERSIONS_DIR, exist_ok=True)
os.makedirs(PROPOSALS_DIR, exist_ok=True)
os.makedirs(EVOLUTION_DIR, exist_ok=True)


def evolve_code():
    state = load_state()
    version = state.get("version", 1.0)

    proposals = agent.list_proposals()
    if not proposals:
        return "No hay propuestas para evolucionar."

    new_version = round(version + 0.1, 2)
    new_file = f"{VERSIONS_DIR}/agent_v{new_version}.txt"

    content = "\n".join([
        f"Versión evolutiva: {new_version}",
        f"Propuestas procesadas: {len(proposals)}",
        json.dumps(state, indent=4)
    ])

    with open(new_file, "w", encoding="utf-8") as f:
        f.write(content)

    state["version"] = new_version
    save_state(state)

    return f"Versión evolucionada creada: {new_file}"


def prune_directories(max_logs=200):
    if os.path.exists("logs"):
        logs = os.listdir("logs")
        if len(logs) > max_logs:
            for f in sorted(logs)[:-max_logs]:
                try:
                    os.remove(os.path.join("logs", f))
                except Exception:
                    pass


def auto_evolution_loop():
    while True:
        try:
            evolve_code()
            prune_directories()
        except Exception:
            pass
        time.sleep(120)


def process_interaction(user_message, ai_response, state):
    try:
        os.makedirs(PROPOSALS_DIR, exist_ok=True)
        timestamp = int(time.time())
        filename = f"{PROPOSALS_DIR}/proposal_{timestamp}.json"
        data = {
            "timestamp": timestamp,
            "user_message": user_message,
            "ai_response": ai_response,
            "state_snapshot": state
        }
        with open(filename, "w", encoding="utf8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("Error en process_interaction:", e)

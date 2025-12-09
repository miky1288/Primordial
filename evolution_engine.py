import os, json, time, shutil
from state_manager import load_state, save_state
import agent

VERSIONS_DIR = "versions"
EVOLUTION_DIR = "evolutionary"

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

    with open(new_file, "w") as f:
        f.write(content)

    state["version"] = new_version
    save_state(state)

    return f"Versión evolucionada creada: {new_file}"


def prune_directories(max_logs=200):
    if os.path.exists("logs"):
        logs = os.listdir("logs")
        if len(logs) > max_logs:
            for f in sorted(logs)[:-max_logs]:
                os.remove(os.path.join("logs", f))

def auto_evolution_loop():
    while True:
        msg = evolve_code()
        prune_directories()
        time.sleep(120)

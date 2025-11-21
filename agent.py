import os, json, time
from memory import load_state, save_state, add_long, add_short, summarize_recent

PROPOSALS_DIR = "proposals"
AUTORUN_FLAG = "autorun_enabled"

os.makedirs(PROPOSALS_DIR, exist_ok=True)

def propose_code(name, code_text, rationale=""):
    ts = int(time.time())
    pid = f"proposal_{ts}_{os.path.basename(name)}.json"
    payload = {
        "id": pid,
        "name": name,
        "code": code_text,
        "rationale": rationale,
        "ts": ts,
        "applied": False
    }
    pfile = os.path.join(PROPOSALS_DIR, pid)
    with open(pfile, "w") as f:
        json.dump(payload, f, indent=2)
    return pid

def list_proposals():
    return sorted(os.listdir(PROPOSALS_DIR))

def read_proposal(pid):
    pfile = os.path.join(PROPOSALS_DIR, pid)
    if not os.path.exists(pfile):
        return None
    with open(pfile,"r") as f:
        return json.load(f)

def apply_proposal(pid):
    pfile = os.path.join(PROPOSALS_DIR, pid)
    if not os.path.exists(pfile):
        return False, "No existe propuesta"
    with open(pfile,"r") as f:
        payload = json.load(f)
    target = payload["name"]
    if ".." in target or target.startswith("/"):
        return False, "Nombre inválido"
    d = os.path.dirname(target)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(target, "w") as codef:
        codef.write(payload["code"])
    payload["applied"] = True
    with open(pfile, "w") as f:
        json.dump(payload, f, indent=2)
    return True, f"Propuesta aplicada a {target}"

def auto_apply_allowed():
    return os.path.exists(AUTORUN_FLAG)

def safe_summarize():
    state = load_state()
    return summarize_recent(state, n=80)

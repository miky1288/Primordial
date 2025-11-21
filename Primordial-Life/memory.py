import os, json, time
from datetime import datetime

STATE_FILE = "state.json"
BACKUP_DIR = "backups"

def _ensure_dirs():
    os.makedirs(BACKUP_DIR, exist_ok=True)

def load_state():
    if not os.path.exists(STATE_FILE):
        state = {
            "version": 1.0,
            "short_memory": [],
            "long_memory": [],
            "meta": {"persona":"evolutiva reflexiva","curiosity":0.6,"coherence":0.5}
        }
        save_state(state)
        return state
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    _ensure_dirs()
    # lightweight backup
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    bf = os.path.join(BACKUP_DIR, f"state_{ts}.json")
    with open(bf, "w") as bfout:
        json.dump(state, bfout, indent=2)
    # keep last 10 backups
    files = sorted([f for f in os.listdir(BACKUP_DIR)], reverse=True)
    for old in files[10:]:
        try:
            os.remove(os.path.join(BACKUP_DIR, old))
        except:
            pass

def add_short(state, text, limit=500):
    entry = {"ts": time.time(), "text": text}
    state["short_memory"].append(entry)
    if len(state["short_memory"]) > limit:
        state["short_memory"] = state["short_memory"][-limit:]
    save_state(state)

def add_long(state, text, importance=0.5):
    entry = {"ts": time.time(), "text": text, "importance": importance}
    state["long_memory"].append(entry)
    if len(state["long_memory"]) > 5000:
        state["long_memory"] = state["long_memory"][-5000:]
    save_state(state)

def summarize_recent(state, n=60):
    texts = [e["text"] for e in state.get("short_memory", [])[-n:]]
    if not texts:
        return None
    parts = []
    for t in texts[:20]:
        s = t.split(".")[0].strip()
        if s:
            parts.append(s)
    summary = " • ".join(parts[:12])
    add_long(state, f"Resumen automático: {summary}", importance=0.6)
    return summary

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import threading, os, agent, main


def compute_evolution_state(state):
    version = state.get("version", 1.0)
    long_mem = len(state.get("long_memory", []))
    short_mem = len(state.get("short_memory", []))
    meta = state.get("meta", {})
    curiosity = meta.get("curiosity", 0)
    coherence = meta.get("coherence", 0)

    evo = (version * 0.3) + (curiosity * 0.25) + (coherence * 0.25) + (
        min(1, long_mem / 500) * 0.2)

    if evo < 0.4:
        stage = "🟡 Fase Inicial – Autoconciencia baja"
    elif evo < 0.75:
        stage = "🟠 Fase Media – Autooptimización"
    else:
        stage = "🟢 Fase Avanzada – Capacidad Evolutiva Alta"

    return {
        "evolution_score": round(float(evo), 3),
        "stage": stage,
        "version": version,
        "mem_long": long_mem,
        "mem_short": short_mem,
        "curiosity": curiosity,
        "coherence": coherence
    }


def _compute_evolution_level(version, curiosity, coherence):
    score = (version * 0.4) + (curiosity * 0.4) + (coherence * 0.2)
    if score < 2:
        return "Nivel 1 — Inicial"
    elif score < 3:
        return "Nivel 2 — Adaptativa"
    elif score < 4:
        return "Nivel 3 — Expansiva"
    elif score < 5:
        return "Nivel 4 — Creativa"
    else:
        return "Nivel 5 — Autónoma"


app = Flask(__name__, static_folder="static")
CORS(app)


@app.route("/")
def home():
    if os.path.exists("static/index.html"):
        return send_from_directory("static", "index.html")
    return "Primordial Life (UI no encontrada)"


@app.route("/health")
def health():
    return "OK", 200


@app.route("/state", methods=["GET"])
def get_state():
    return jsonify(main.load_state())


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    msg = data.get("message", "")
    res = main.think(msg)
    return jsonify({
        "response": res,
        "version": main.load_state().get("version")
    })


@app.route("/proposals", methods=["GET"])
def list_proposals():
    return jsonify(agent.list_proposals())


@app.route("/proposals/<pid>", methods=["GET"])
def read_proposal(pid):
    pfile = os.path.join("proposals", pid)
    if not os.path.exists(pfile):
        return jsonify({"error": "no encontrado"}), 404
    with open(pfile, "r") as f:
        return f.read()


@app.route("/proposals/<pid>/apply", methods=["POST"])
def apply_proposal(pid):
    if not os.path.exists("autorun_enabled"):
        return jsonify({
            "error":
            "autorun not enabled. Create file 'autorun_enabled' to enable auto-apply"
        }), 403
    ok, msg = agent.apply_proposal(pid)
    return jsonify({"ok": ok, "msg": msg})


@app.route("/actions/summarize", methods=["POST", "GET"])
def do_summarize():
    return jsonify({"result": agent.safe_summarize()})


@app.route("/ping")
def ping():
    return "ok", 200


@app.route("/status", methods=["GET"])
def status():
    state = main.load_state()
    version = state.get("version")
    persona = state.get("meta", {}).get("persona")
    curiosity = state.get("meta", {}).get("curiosity")
    coherence = state.get("meta", {}).get("coherence")
    short_mem = len(state.get("short_memory", []))
    long_mem = len(state.get("long_memory", []))
    proposals = agent.list_proposals()
    applied = sum(1 for p in proposals if "applied" in agent.read_proposal(p)
                  and agent.read_proposal(p)["applied"])
    last_summary = ""
    for item in reversed(state.get("long_memory", [])):
        if "Resumen automático" in item.get("text", ""):
            last_summary = item["text"]
            break
    return jsonify({
        "version":
        version,
        "persona":
        persona,
        "mental_parameters": {
            "curiosity": curiosity,
            "coherence": coherence
        },
        "memory": {
            "short_memory_entries": short_mem,
            "long_memory_entries": long_mem
        },
        "evolution_level":
        _compute_evolution_level(version, curiosity, coherence),
        "proposals": {
            "total": len(proposals),
            "applied": applied,
            "pending": len(proposals) - applied
        },
        "last_summary":
        last_summary
    })


@app.route("/status-ui")
def status_ui():
    if os.path.exists("static/status.html"):
        return send_from_directory("static", "status.html")
    return "UI de estado no encontrada", 404


if __name__ == "__main__":
    os.makedirs("proposals", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    main.run_background_thread()

    PORT = int(os.environ.get("PORT", 5000))  # Render asigna el puerto
    app.run(host="0.0.0.0", port=PORT)

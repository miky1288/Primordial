# server.py corregido
from flask import Flask, jsonify, request, send_from_directory, make_response
from flask_cors import CORS
import os

import agent
from state_manager import load_state, save_state
import main

app = Flask(__name__, static_folder="static")
CORS(app)


@app.route("/")
def home():
    if os.path.exists("static/index.html"):
        return send_from_directory("static", "index.html")
    return "UI no encontrada", 404


@app.route("/ping")
def ping():
    return "ok", 200


@app.route("/health")
def health():
    return "OK", 200


@app.route("/state")
def get_state():
    return jsonify(load_state())


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True) or {}
    msg = str(data.get("message", "")).strip()

    if not msg:
        return jsonify({"response": "Debes enviar un mensaje."})

    # Cargar estado
    state = load_state()

    # Guardar memoria del usuario antes de procesar
    main.add_short(state, f"USER: {msg}")

    # Obtener respuesta del agente
    ai_response = agent.agent_reply(msg, state)

    # Guardar respuesta del agente
    main.add_short(state, f"ASSISTANT: {ai_response}")

    # Mantener memoria coherente
    main._promote_short_to_long_if_needed(state)
    main.limit_memory(state)

    save_state(state)

    return jsonify({
        "response": ai_response,
        "version": state.get("version", 1.0),
    })


@app.route("/proposals")
def list_proposals():
    state = load_state()
    return jsonify(agent.list_proposals(state))


@app.route("/proposals/<pid>")
def read_proposal(pid: str):
    # Evitar traversal
    if "/" in pid or "\\" in pid:
        return jsonify({"error": "invalid id"}), 400

    content = agent.read_proposal(pid)
    if content is None:
        return jsonify({"error": "no encontrado"}), 404

    return jsonify(content)


@app.route("/proposals/<pid>/apply", methods=["POST"])
def apply_proposal(pid: str):
    if not os.path.exists("autorun_enabled"):
        return make_response(
            jsonify({
                "error":
                "autorun not enabled. Create file 'autorun_enabled'"
            }), 403)

    state = load_state()
    updated_state = agent.apply_proposal(state, pid)

    save_state(updated_state)
    return jsonify({"ok": True, "msg": "Propuesta aplicada"})


@app.route("/actions/summarize", methods=["POST"])
def do_summarize():
    data = request.get_json(force=True) or {}
    text = data.get("text", "")
    result = agent.safe_summarize(text)
    return jsonify({"result": result})


@app.route("/status")
def status():
    state = load_state()
    meta = state.get("meta", {})
    curiosity = meta.get("curiosity", 0)
    coherence = meta.get("coherence", 0)

    short_count = len(state.get("short_memory", []))
    long_count = len(state.get("long_memory", []))

    last_summary = ""
    for item in reversed(state.get("long_memory", [])):
        text = item.get("text", "")
        if "Resumen automático" in text:
            last_summary = text
            break

    proposals = agent.list_proposals(state)
    applied = len(state.get("applied_proposals", []))
    total = len(proposals)

    return jsonify({
        "version": state.get("version", 1.0),
        "persona": meta.get("persona"),
        "curiosity": curiosity,
        "coherence": coherence,
        "evolution_level": state.get("level", "—"),
        "memory": {
            "short_memory_entries": short_count,
            "long_memory_entries": long_count,
        },
        "proposals": {
            "total": total,
            "applied": applied,
            "pending": total - applied
        },
        "last_summary": last_summary,
    })


@app.route("/status-ui")
def status_ui():
    if os.path.exists("static/status.html"):
        return send_from_directory("static", "status.html")
    return "UI no encontrada", 404


if __name__ == "__main__":
    os.makedirs("proposals", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    main.run_background_thread()

    PORT = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=PORT)

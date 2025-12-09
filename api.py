from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import main
import agent
import evolution_engine

app = Flask(__name__, static_folder="static")
CORS(app)

# ============================================================
#                    SERVIR LA INTERFAZ
# ============================================================

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# ============================================================
#                    ENDPOINTS PRINCIPALES
# ============================================================

@app.route("/ping")
def ping():
    return "ok", 200


@app.route("/status", methods=["GET"])
def status():
    try:
        state = main.load_state()
        evo = {
            "version": state.get("version", 1.0),
            "curiosity": state.get("meta", {}).get("curiosity", 0),
            "coherence": state.get("meta", {}).get("coherence", 0),
            "short_memory": len(state.get("short_memory", [])),
            "long_memory": len(state.get("long_memory", [])),
            "pending_proposals": len(agent.list_proposals())
        }
        return jsonify(evo)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ask", methods=["POST"])
def ask():
    """
    Este endpoint es llamado por el frontend.
    Responde la IA, evoluciona memoria, genera propuestas.
    """
    data = request.get_json()
    msg = data.get("message", "")

    if not msg:
        return jsonify({"response": "Debes enviar un mensaje."})

    # 1: Recuperar estado
    state = main.load_state()

    # 2: Pensar
    response = agent.agent_reply(msg, state)

    # 3: Guardar estado (memoria y meta-parámetros)
    main.save_state(state)

    # 4: Retornar respuesta
    return jsonify({
        "response": response,
        "version": state.get("version", 1.0)
    })

# ============================================================
#                    ENDPOINTS DE EVOLUCIÓN
# ============================================================

@app.route("/evolve", methods=["POST"])
def evolve():
    result = evolution_engine.evolve_code()
    agent.clear_proposals()  # limpiar propuestas aplicadas
    return jsonify({"result": result})


# ============================================================
#                    EJECUCIÓN DEL SERVIDOR
# ============================================================

if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("proposals", exist_ok=True)

    # Levantar hilo de evolución automática
    main.run_background_thread()

    app.run(host="0.0.0.0", port=5000)

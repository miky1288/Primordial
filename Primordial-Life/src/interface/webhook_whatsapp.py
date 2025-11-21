from flask import request, jsonify
import main

def register_whatsapp_routes(app):
    @app.route("/whatsapp", methods=["POST"])
    def whatsapp_webhook():
        data = request.get_json(force=True)
        incoming = data.get("text") or data.get("message") or data.get("body") or ""
        sender = data.get("waId") or data.get("from") or "unknown"
        # guardar en memoria
        st = main.load_state()
        st["short_memory"].append({"ts": __import__('time').time(), "text": f"WHATSAPP {sender}: {incoming}"})
        main.save_state(st)
        # responder con think()
        reply = main.think(incoming)
        # devolver formato simple
        return jsonify({"replies":[{"type":"text","message": reply}]})

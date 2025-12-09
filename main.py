# main.py
"""
Core runtime: gestión de estado, memoria y loop de background.
Compatible con agent.py, reasoning.py y evolution_engine.py
"""

import json
import os
import time
import threading
from datetime import datetime

# módulos del proyecto
import agent
from evolution_engine import auto_evolution_loop
from state_manager import load_state, save_state

# Archivo de estado
STATE_FILE = "state.json"

# Lock para evitar concurrencia en I/O
_state_lock = threading.Lock()

# Parámetros de control
MAX_SHORT_MEM = 300
MAX_LONG_MEM = 1000
AUTO_PROMOTE_SHORT_TO_LONG_EVERY = 30  # cada cuántos items de short se promociona uno


def _default_state():
    return {
        "version": 1.0,
        "meta": {
            "persona": "evolutiva reflexiva",
            "curiosity": 0.25,
            "coherence": 0.3
        },
        "short_memory": [],
        "long_memory": [],
        "memory": [],  # espacio para otros tipos de memoria (internet, fuentes, etc.)
        "created_at": datetime.utcnow().isoformat()
    }


def load_state():
    """Carga el state desde disk; si no existe, lo crea con valores por defecto."""
    with _state_lock:
        if not os.path.exists(STATE_FILE):
            st = _default_state()
            try:
                save_state(st)
            except Exception:
                pass
            return st

        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # Si el archivo está corrupto, regeneramos uno sano (lo guardamos como backup)
            try:
                backup = STATE_FILE + ".corrupt." + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                os.rename(STATE_FILE, backup)
            except Exception:
                pass
            st = _default_state()
            try:
                save_state(st)
            except Exception:
                pass
            return st


def save_state(state):
    """Guarda el state en disco de forma atómica (temporal + rename)."""
    with _state_lock:
        tmp = STATE_FILE + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            os.replace(tmp, STATE_FILE)
        except Exception as e:
            # intentar guardado simple como fallback
            try:
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
            except Exception:
                # si falla, escribimos un log sencillo
                try:
                    os.makedirs("logs", exist_ok=True)
                    with open(os.path.join("logs", "save_state_errors.log"), "a") as lf:
                        lf.write(f"{time.time()} save_state error: {repr(e)}\n")
                except Exception:
                    pass


def add_short(state, text):
    """Añade un evento a short_memory con timestamp y controla el tamaño."""
    if not isinstance(text, str):
        text = str(text)
    entry = {"ts": datetime.utcnow().isoformat(), "text": text}
    state.setdefault("short_memory", []).append(entry)
    # acotar tamaño
    if len(state["short_memory"]) > MAX_SHORT_MEM:
        state["short_memory"] = state["short_memory"][-MAX_SHORT_MEM:]


def add_long(state, text):
    """Añade un evento a long_memory con timestamp y controla el tamaño."""
    if not isinstance(text, str):
        text = str(text)
    entry = {"ts": datetime.utcnow().isoformat(), "text": text}
    state.setdefault("long_memory", []).append(entry)
    if len(state["long_memory"]) > MAX_LONG_MEM:
        state["long_memory"] = state["long_memory"][-MAX_LONG_MEM:]


def limit_memory(state, max_long=MAX_LONG_MEM, max_short=MAX_SHORT_MEM):
    """Función de mantenimiento para limitar memorias y evitar crecimiento descontrolado."""
    if "short_memory" in state and isinstance(state["short_memory"], list):
        if len(state["short_memory"]) > max_short:
            state["short_memory"] = state["short_memory"][-max_short:]
    if "long_memory" in state and isinstance(state["long_memory"], list):
        if len(state["long_memory"]) > max_long:
            state["long_memory"] = state["long_memory"][-max_long:]


def _promote_short_to_long_if_needed(state):
    """Promociona entradas de short a long ocasionalmente para consolidación."""
    short = state.get("short_memory", [])
    # cada N entradas de short promovemos la última
    try:
        if len(short) and (len(short) % AUTO_PROMOTE_SHORT_TO_LONG_EVERY == 0):
            last = short[-1]
            add_long(state, f"Promoción automática: {last.get('text','')}")
    except Exception:
        pass


def think(message):
    """
    Interfaz principal usada por server.py:
    - carga estado
    - obtiene respuesta del agent
    - registra en short_memory y guarda state
    """
    state = load_state()

    # Generar respuesta usando el agente (agent.agent_reply)
    try:
        ai_response = agent.agent_reply(message, state)
    except TypeError:
        # compatibilidad por si agent esperaba distinto
        ai_response = agent.think(message, state) if hasattr(agent, "think") else "Error interno: agent no disponible."

    # Registrar la interacción en short memory
    try:
        add_short(state, f"USER: {message}")
        add_short(state, f"ASSISTANT: {ai_response}")
    except Exception:
        pass

    # Promocionar y limitar memorias
    _promote_short_to_long_if_needed(state)
    limit_memory(state)

    # Guardar cambios
    save_state(state)
    return ai_response


# -------------------------
# Background & mantenimiento
# -------------------------
_background_started = False


def _maintenance_loop():
    """Loop de mantenimiento: guarda estado, ajusta parámetros y limpia logs periódicamente."""
    while True:
        try:
            state = load_state()
            # normalizar meta valores al rango 0..1
            meta = state.get("meta", {})
            if isinstance(meta.get("curiosity"), (int, float)):
                meta["curiosity"] = min(max(meta.get("curiosity", 0.0), 0.0), 1.0)
            else:
                meta["curiosity"] = 0.25

            if isinstance(meta.get("coherence"), (int, float)):
                meta["coherence"] = min(max(meta.get("coherence", 0.0), 0.0), 1.0)
            else:
                meta["coherence"] = 0.3

            state["meta"] = meta

            # pequeñas reglas de auto-tune (puedes ajustar las constantes)
            # ejemplo: si hay mucha short_memory incrementa curiosity ligeramente
            try:
                if len(state.get("short_memory", [])) > 200:
                    state["meta"]["curiosity"] = min(1.0, state["meta"].get("curiosity", 0.25) + 0.005)
                else:
                    state["meta"]["curiosity"] = max(0.01, state["meta"].get("curiosity", 0.25) - 0.001)
            except Exception:
                pass

            # Recalcular pequeña versión evolutiva incremental para trazabilidad
            try:
                state["version"] = round(float(state.get("version", 1.0)) + 0.0001, 6)
            except Exception:
                state["version"] = state.get("version", 1.0)

            # Guardar y limpieza
            limit_memory(state)
            save_state(state)

            # prune logs si es necesario
            try:
                if os.path.exists("logs"):
                    logs = sorted(os.listdir("logs"))
                    if len(logs) > 500:
                        for f in logs[:-300]:
                            try:
                                os.remove(os.path.join("logs", f))
                            except Exception:
                                pass
            except Exception:
                pass

        except Exception as e:
            try:
                os.makedirs("logs", exist_ok=True)
                with open(os.path.join("logs", "maintenance_errors.log"), "a") as lf:
                    lf.write(f"{time.time()} maintenance error: {repr(e)}\n")
            except Exception:
                pass

        # dormir un tiempo razonable
        time.sleep(10)


def run_background_thread():
    """Arranca los hilos de evolución y de mantenimiento (idempotente)."""
    global _background_started
    if _background_started:
        return
    _background_started = True

    # hilo de mantenimiento
    t1 = threading.Thread(target=_maintenance_loop, daemon=True)
    t1.start()

    # hilo evolutivo (usa evolution_engine.auto_evolution_loop)
    try:
        t2 = threading.Thread(target=auto_evolution_loop, daemon=True)
        t2.start()
    except Exception:
        # Si no existe evolution_engine, seguimos sin él
        try:
            os.makedirs("logs", exist_ok=True)
            with open(os.path.join("logs", "background_errors.log"), "a") as lf:
                lf.write(f"{time.time()} failed to start evolution_engine\n")
        except Exception:
            pass

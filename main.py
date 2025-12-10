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

# Lock para evitar concurrencia en I/O
_state_lock = threading.Lock()

# Parámetros de control
MAX_SHORT_MEM = 300
MAX_LONG_MEM = 1000
AUTO_PROMOTE_SHORT_TO_LONG_EVERY = 30


# ---------------------------------------------------------
# Memoria
# ---------------------------------------------------------
def add_short(state, text):
    """Añade un evento a short_memory con timestamp."""
    if not isinstance(text, str):
        text = str(text)

    entry = {"ts": datetime.utcnow().isoformat(), "text": text}
    state.setdefault("short_memory", []).append(entry)

    # límite
    if len(state["short_memory"]) > MAX_SHORT_MEM:
        state["short_memory"] = state["short_memory"][-MAX_SHORT_MEM:]


def add_long(state, text):
    """Añade un evento a long_memory con timestamp."""
    if not isinstance(text, str):
        text = str(text)

    entry = {"ts": datetime.utcnow().isoformat(), "text": text}
    state.setdefault("long_memory", []).append(entry)

    if len(state["long_memory"]) > MAX_LONG_MEM:
        state["long_memory"] = state["long_memory"][-MAX_LONG_MEM:]


def limit_memory(state, max_long=MAX_LONG_MEM, max_short=MAX_SHORT_MEM):
    """Evita que crezcan demasiado las memorias."""
    if isinstance(state.get("short_memory"), list):
        state["short_memory"] = state["short_memory"][-max_short:]
    if isinstance(state.get("long_memory"), list):
        state["long_memory"] = state["long_memory"][-max_long:]


def _promote_short_to_long_if_needed(state):
    """
    Promociona de short a long cada X mensajes.
    En vez de copiar el último literal, guarda un meta-evento más útil.
    """
    short = state.get("short_memory", [])

    if len(short) and (len(short) % AUTO_PROMOTE_SHORT_TO_LONG_EVERY == 0):
        last = short[-1].get("text", "")
        add_long(state, f"Promoción automática desde short_memory: {last}")


# ---------------------------------------------------------
# THINK (interfaz principal)
# ---------------------------------------------------------
def think(message):
    """
    Punto único utilizado por server/api:
    - carga estado
    - genera respuesta vía agent_reply
    - registra memoria
    - guarda estado
    """
    with _state_lock:
        state = load_state()

        # Generar respuesta
        try:
            ai_response = agent.agent_reply(message, state)
        except Exception as e:
            ai_response = f"Error interno en agent_reply: {e}"

        # Registrar memorias
        add_short(state, f"USER: {message}")
        add_short(state, f"ASSISTANT: {ai_response}")

        # Mantenimiento de memoria
        _promote_short_to_long_if_needed(state)
        limit_memory(state)

        # Guardar
        save_state(state)

    return ai_response


# ---------------------------------------------------------
# Background loops
# ---------------------------------------------------------
_background_started = False


def _maintenance_loop():
    """Normalización periódica del estado."""
    while True:
        try:
            with _state_lock:
                state = load_state()
                meta = state.get("meta", {})

                # Normalización segura 0-1
                def clamp(v, low=0.0, high=1.0):
                    try:
                        return min(max(float(v), low), high)
                    except:
                        return 0.5

                meta["curiosity"] = clamp(meta.get("curiosity", 0.3))
                meta["coherence"] = clamp(meta.get("coherence", 0.4))
                state["meta"] = meta

                # Ajuste evolutivo simple
                if len(state.get("short_memory", [])) > 200:
                    meta["curiosity"] = clamp(meta["curiosity"] + 0.005)
                else:
                    meta["curiosity"] = clamp(meta["curiosity"] - 0.001)

                # Incremento de versión suave
                try:
                    state["version"] = round(float(state.get("version", 1.0)) + 0.0001, 6)
                except:
                    state["version"] = state.get("version", 1.0)

                # Guardar
                limit_memory(state)
                save_state(state)

        except Exception as e:
            try:
                os.makedirs("logs", exist_ok=True)
                with open("logs/maintenance_errors.log", "a") as f:
                    f.write(f"{time.time()} maintenance error: {repr(e)}\n")
            except:
                pass

        time.sleep(10)


def run_background_thread():
    """Arranca mantenimiento + evolución si no están iniciados."""
    global _background_started
    if _background_started:
        return

    _background_started = True

    # hilo mantenimiento
    t1 = threading.Thread(target=_maintenance_loop, daemon=True)
    t1.start()

    # hilo evolución adaptativa
    try:
        t2 = threading.Thread(target=auto_evolution_loop, daemon=True)
        t2.start()
    except Exception:
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/background_errors.log", "a") as f:
                f.write("Error iniciando evolution_engine\n")
        except:
            pass

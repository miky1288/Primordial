# memory.py (versión corregida y unificada)
"""
Módulo utilitario de memoria.
NO carga ni guarda estado.
NO escribe en disco.
Solo opera sobre el diccionario de estado.
"""

import time
from datetime import datetime

# límites sugeridos (coherentes con main.py)
MAX_SHORT = 300
MAX_LONG = 1000


# ---------------------------------------------------------
# SHORT MEMORY
# ---------------------------------------------------------
def add_short_entry(state, text, limit=MAX_SHORT):
    """Añade una entrada a short_memory (RAM solamente)."""
    if not isinstance(text, str):
        text = str(text)

    entry = {"ts": datetime.utcnow().isoformat(), "text": text}
    state.setdefault("short_memory", []).append(entry)

    # límite
    if len(state["short_memory"]) > limit:
        state["short_memory"] = state["short_memory"][-limit:]


# ---------------------------------------------------------
# LONG MEMORY
# ---------------------------------------------------------
def add_long_entry(state, text, importance=0.5, limit=MAX_LONG):
    """Añade una entrada a long_memory sin guardar en disco."""
    if not isinstance(text, str):
        text = str(text)

    entry = {
        "ts": datetime.utcnow().isoformat(),
        "text": text,
        "importance": importance
    }
    state.setdefault("long_memory", []).append(entry)

    if len(state["long_memory"]) > limit:
        state["long_memory"] = state["long_memory"][-limit:]


# ---------------------------------------------------------
# AUTO SUMMARY
# ---------------------------------------------------------
def summarize_recent(state, n=60):
    """
    Genera un resumen de los últimos N mensajes corto y limpio.
    NO guarda automáticamente el estado.
    SÍ agrega el resumen a long_memory (pero solo en memoria).
    """
    short = state.get("short_memory", [])
    if not short:
        return None

    # tomar últimos N textos
    recent_texts = [e.get("text", "") for e in short[-n:] if e.get("text")]

    if not recent_texts:
        return None

    # Tomar primeras 15 frases limpias.
    cleaned = []
    for t in recent_texts:
        s = t.strip()
        if len(s) > 4:
            cleaned.append(s)

    if not cleaned:
        return None

    summary = " • ".join(cleaned[:12])
    if not summary:
        return None

    # Se añade a memoria a nivel lógico
    add_long_entry(state, f"Resumen automático: {summary}", importance=0.6)

    return summary

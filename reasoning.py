# reasoning.py
"""
Motor de razonamiento y planificación.
Firma pública: synthesize(message, state) -> Dict[str, Any]
Devuelve un 'plan' (dict) con campos útiles para agent.py.
- Actualiza state["meta"] y state["level"] internamente.
- No realiza llamadas a LLM externos (es local / heurístico).
"""

from difflib import SequenceMatcher
import random
import time
from typing import List, Dict, Any, Optional


# -------------------------
# utilidades de retrieval
# -------------------------
def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def retrieve(query: str, state: Dict[str, Any], top_k: int = 5) -> List[str]:
    """
    Busca coincidencias simples en long_memory.
    Retorna textos (no estructuras) que pasen un umbral.
    """
    collection = state.get("long_memory", [])[-1200:]
    candidates = []
    for item in collection:
        text = item.get("text") if isinstance(item, dict) else str(item)
        if not text:
            continue
        score = sim(query.lower(), text.lower())
        candidates.append((score, text))
    candidates.sort(key=lambda x: x[0], reverse=True)
    memories = [t for score, t in candidates[:top_k] if score > 0.15]
    return memories


# -------------------------
# evolución adaptativa
# -------------------------
def evaluar_interaccion(message: str) -> int:
    length = len(message or "")
    preguntas = sum(1 for c in (message or "") if c in "?¿")
    palabras = len((message or "").split())
    score = 0
    if length > 40:
        score += 1
    if preguntas > 0:
        score += 1
    if palabras > 8:
        score += 1
    return score  # 0..3


def update_evolution(state: Dict[str, Any], message: str) -> None:
    """
    Actualiza state["meta"] (curiosity, coherence) en 0..1 y el state["level"].
    Mantiene persona si está definida.
    """
    meta = state.setdefault("meta", {})
    # inicializar si es necesario
    meta.setdefault("curiosity", 0.25)
    meta.setdefault("coherence", 0.25)

    profundidad = evaluar_interaccion(message or "")

    # Step adjustments (más conservador para evitar saltos)
    if profundidad >= 1:
        meta["curiosity"] = min(
            1.0,
            meta.get("curiosity", 0.25) + random.uniform(0.03, 0.06))
    else:
        meta["curiosity"] = max(
            0.0,
            meta.get("curiosity", 0.25) - random.uniform(0.001, 0.01))

    if profundidad >= 2:
        meta["coherence"] = min(
            1.0,
            meta.get("coherence", 0.25) + random.uniform(0.04, 0.07))
    else:
        meta["coherence"] = max(
            0.0,
            meta.get("coherence", 0.25) - random.uniform(0.001, 0.01))

    promedio = (meta["curiosity"] + meta["coherence"]) / 2.0
    if promedio > 0.85:
        state["level"] = 5
    elif promedio > 0.65:
        state["level"] = 4
    elif promedio > 0.45:
        state["level"] = 3
    elif promedio > 0.30:
        state["level"] = 2
    else:
        state["level"] = 1

    state["meta"] = meta


# -------------------------
# generación de 'plan' local
# -------------------------
def build_plan(message: str, state: Dict[str, Any],
               memories: List[str]) -> Dict[str, Any]:
    """
    Construye un plan (estructura intermedia) que el agent.transformará en texto.
    El plan contiene:
      - message: texto original
      - level: numérico
      - traits: curiosity/coherence (0..1)
      - memory_hits: lista corta de recuerdos
      - persona: string (del estado)
      - tone_hint: una pista breve para el formato de la respuesta
    """
    meta = state.get("meta", {})
    persona = meta.get("persona", "evolutiva")
    curiosity = float(meta.get("curiosity", 0.25))
    coherence = float(meta.get("coherence", 0.25))
    level = int(state.get("level", 1))

    # decidir tono según persona + nivel
    tone = "neutral"
    if "amig" in persona.lower():
        tone = "amistoso"
    elif "serio" in persona.lower() or "profes" in persona.lower():
        tone = "serio"
    elif level >= 4:
        tone = "curioso"
    else:
        tone = "neutral"

    # compactar memory_hits evitando ecos idénticos
    hits = []
    for m in (memories or []):
        mclean = m.strip()
        if not mclean:
            continue
        # evitar repetir literalmente el mensaje
        if mclean.lower() == (message or "").strip().lower():
            continue
        if mclean not in hits:
            hits.append(mclean)
        if len(hits) >= 3:
            break

    plan = {
        "message": message or "",
        "level": level,
        "traits": {
            "curiosity": round(curiosity, 4),
            "coherence": round(coherence, 4)
        },
        "memory_hits": hits,
        "persona": persona,
        "tone_hint": tone,
        "ts": time.time()
    }
    return plan


# -------------------------
# API pública
# -------------------------
def synthesize(message: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Punto de entrada que devuelve un 'plan' (dict).
    - actualiza estado (evolution)
    - extrae recuerdos útiles (retrieve)
    - devuelve plan listo para convertirse en texto por agent.py
    """
    if state is None:
        state = {}

    # asegurarse de estructuras mínimas
    state.setdefault("long_memory", [])
    state.setdefault("short_memory", [])
    state.setdefault("meta", {
        "curiosity": 0.25,
        "coherence": 0.25,
        "persona": "Evolutiva"
    })
    state.setdefault("level", 1)

    # recuperar memorias relevantes
    memories = retrieve(message or "", state, top_k=6)

    # actualizar evolución basada en el mensaje
    try:
        update_evolution(state, message or "")
    except Exception:
        pass

    # añadir al long_memory de manera controlada (no duplicar idénticos recientes)
    try:
        lm = state.setdefault("long_memory", [])
        last_text = lm[-1].get("text") if lm and isinstance(lm[-1],
                                                            dict) else None
        if (message or "").strip() and (last_text is None or
                                        (message.strip() != last_text)):
            state["long_memory"].append({
                "text": message,
                "timestamp": time.time()
            })
            # evitar crecimiento descontrolado aquí (se recorta en save/maintenance)
    except Exception:
        pass

    # devolver plan
    plan = build_plan(message or "", state, memories)
    return plan

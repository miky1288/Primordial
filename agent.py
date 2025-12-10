# agent.py
"""
Agent que transforma el 'plan' de reasoning.synthesize en texto conversacional.
Diseñado para Modo C: identidad persistente y estilo que evoluciona con memoria.
"""

import os
import json
import random
from typing import Any, Dict, List, Optional

from reasoning import synthesize
from evolution_engine import process_interaction
from state_manager import load_state, save_state  # para persistir cambios cuando hace falta

PROPOSALS_DIR = "proposals"


# -------------------------
# Variaciones / auxiliares de estilo
# -------------------------
def pick(items: List[str]) -> Optional[str]:
    if not items:
        return None
    return random.choice(items)


def persona_prefix(persona: str) -> str:
    """
    Pequeña firma inicial que ayuda a reforzar identidad sin ser intrusiva.
    Se usa con moderación.
    """
    p = persona.lower()
    if "amig" in p:
        return "🙂 "
    if "sabio" in p or "prof" in p:
        return "🔍 "
    if "poet" in p or "poético" in p or "poetico" in p:
        return "✧ "
    return ""


# -------------------------
# Convertir plan -> texto
# -------------------------
def plan_to_text(plan: Dict[str, Any]) -> str:
    message = plan.get("message", "")
    level = plan.get("level", 1)
    traits = plan.get("traits", {})
    hits = plan.get("memory_hits", []) or []
    persona = plan.get("persona", "Evolutiva")
    tone = plan.get("tone_hint", "neutral")

    prefix = persona_prefix(persona)

    # construir apertura natural (varía por contexto)
    openings = [
        "¡Hola! ¿Qué tal?", "Perfecto — cuéntame más.",
        "Entiendo. Dime más si quieres.", "Gracias por decirme eso."
    ]
    if message.strip().lower() in ["hola", "buenas", "hey"]:
        openings = [
            "¡Hola! ¿Cómo estás?", "¡Hola! Qué gusto verte por aquí.",
            "¿Hola? ¿Cómo te va?"
        ]

    opening = pick(openings)

    # si hay recuerdos relevantes, integrarlos de forma no literal
    memory_fragment = ""
    if hits:
        # elegir uno o dos hits y usarlos para enlazar
        chosen = hits[:2]
        # construir frase de conexión sin citar literalmente
        memory_fragment = "Me recuerda algo que dijiste antes sobre " + ", ".join(
            [f"«{c[:60]}{('...' if len(c)>60 else '')}»"
             for c in chosen]) + ". "
        # pero evitar que cada respuesta empiece con esto (sólo si tiene sentido)
        if random.random() < 0.35:
            # ocasionalmente omitir el prefijo de recuerdo
            memory_fragment = ""

    # cuerpo principal: variar por nivel y tono
    if level >= 4:
        endings = [
            "¿Quieres que profundice en esto?",
            "¿Te interesa que lo exploremos juntos?",
            "Puedo seguir si quieres."
        ]
    elif level == 3:
        endings = [
            "Espero que eso ayude. ¿Quieres seguir?",
            "¿Te gustaría que lo aclaremos un poco más?"
        ]
    else:
        endings = ["¿Algo más?", "Dime si quieres continuar."]

    ending = pick(endings)

    # formular respuesta base con pequeñas variaciones según tono
    if tone == "amistoso":
        templates = [
            f"{prefix}{opening} {memory_fragment}Te escucho con atención. {ending}",
            f"{prefix}Gracias por contarme eso. {memory_fragment}¿Quieres que lo trabajemos juntos? {ending}"
        ]
    elif tone == "serio":
        templates = [
            f"{prefix}{opening} {memory_fragment}Procesé lo que dijiste y puedo ayudarte a analizarlo. {ending}",
            f"{prefix}Entiendo. {memory_fragment}Si quieres, profundizamos en los puntos clave. {ending}"
        ]
    elif tone == "curioso":
        templates = [
            f"{prefix}{opening} {memory_fragment}Me intriga lo que comentas — ¿puedes darme un ejemplo? {ending}",
            f"{prefix}Interesante. {memory_fragment}¿Qué te llevó a decir eso? {ending}"
        ]
    else:  # neutral / default
        templates = [
            f"{prefix}{opening} {memory_fragment}Estoy aquí para ayudarte. {ending}",
            f"{prefix}{opening} {memory_fragment}Gracias por compartirlo. {ending}"
        ]

    response = pick(templates)

    # pequeños ajustes finales: evitar que la respuesta sea demasiado corta
    if len(response.strip()) < 20:
        response = response + " " + pick(
            ["Cuéntame más.", "¿Quieres explicar un poco más?"])

    # Guardar en state.short_memory y long_memory? lo dejamos para main/run
    return response


# -------------------------
# THINK / AGENT REPLY
# -------------------------
def think(user_message: str, state: Dict[str, Any]) -> str:
    """
    Llama a reasoning.synthesize(user_message, state) y convierte el plan a texto.
    """
    try:
        plan = synthesize(user_message, state)
    except TypeError as e:
        return f"Error interno en el módulo de razonamiento: {e}"
    except Exception as e:
        return f"Error interno en el módulo de razonamiento: {e}"

    if isinstance(plan, str):
        return plan

    if isinstance(plan, dict):
        try:
            # plan_to_text genera la respuesta final
            out = plan_to_text(plan)
            return out
        except Exception as e:
            return f"Error al convertir plan a texto: {e}"

    return str(plan)


def agent_reply(user_message: str, state: Dict[str, Any]) -> str:
    """
    Respuesta principal: piensa, genera propuesta (proceso interno) y devuelve texto.
    """
    ai_response = think(user_message, state)

    # registrar interacción como propuesta (no bloqueante)
    try:
        process_interaction(user_message, ai_response, state)
    except Exception:
        pass

    # devolver respuesta textual
    return ai_response


# -------------------------
# utilities: proposals & summarize
# -------------------------
def list_proposals(state: Optional[Dict[str, Any]] = None) -> List[str]:
    if isinstance(state, dict):
        p = state.get("proposals")
        if isinstance(p, list):
            return p
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    return sorted(os.listdir(PROPOSALS_DIR))


def read_proposal(pid: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(PROPOSALS_DIR, pid)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return {"text": f.read()}
        except Exception:
            return None


def apply_proposal(state: Dict[str, Any], proposal: str) -> Dict[str, Any]:
    state.setdefault("applied_proposals", [])
    if proposal not in state["applied_proposals"]:
        state["applied_proposals"].append(proposal)
    state["version"] = round(float(state.get("version", 1.0)) + 0.1, 4)
    save_state(state)
    return state


def clear_proposals():
    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    for name in os.listdir(PROPOSALS_DIR):
        try:
            os.remove(os.path.join(PROPOSALS_DIR, name))
        except Exception:
            pass


def safe_summarize(text: Optional[str], max_len: int = 200) -> str:
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len] + "..."

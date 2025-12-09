from difflib import SequenceMatcher
import random
import time

# ================================
#   SIMILITUD Y RETRIEVAL
# ================================


def sim(a, b):
    return SequenceMatcher(None, a, b).ratio()


def retrieve(query, state, top_k=5):
    candidates = []
    for item in state.get("long_memory", [])[-1200:]:
        text = item.get("text", "")
        score = sim(query.lower(), text.lower())
        candidates.append((score, text))

    candidates.sort(key=lambda x: x[0], reverse=True)
    memories = [t for score, t in candidates[:top_k] if score > 0.15]

    return memories


# ================================
#   EVOLUCIÓN ADAPTATIVA
# ================================


def evaluar_interaccion(message):
    """Evalúa qué tan compleja es la interacción del usuario."""
    length = len(message)
    preguntas = sum(1 for c in message if c in "?¿")
    palabras = len(message.split())

    score = 0

    if length > 40:
        score += 1
    if preguntas > 0:
        score += 1
    if palabras > 8:
        score += 1

    return score  # Entre 0 y 3


def update_evolution(state, message):
    # Evaluación de interacción
    profundidad = evaluar_interaccion(message)

    # Curiosidad
    if profundidad >= 1:
        state["curiosity"] = min(100,
                                 state["curiosity"] + random.randint(2, 5))

    # Coherencia
    if profundidad >= 2:
        state["coherence"] = min(100,
                                 state["coherence"] + random.randint(3, 6))

    # Nivel evolutivo (promedio de atributos)
    promedio = (state["curiosity"] + state["coherence"]) / 2

    if promedio > 85:
        state["level"] = 5
    elif promedio > 65:
        state["level"] = 4
    elif promedio > 45:
        state["level"] = 3
    elif promedio > 30:
        state["level"] = 2
    else:
        state["level"] = 1

    return state


# ================================
#   RESPUESTAS SEGÚN NIVEL
# ================================


def generar_respuesta_inteligente(message, state, recuerdos):
    msg = message.lower()

    # Respuestas directas (más naturales)
    if "cómo estás" in msg:
        return "Estoy bien, creciendo cada vez que hablamos. ¿Y tú cómo vas hoy?"

    if "quién eres" in msg or "qué eres" in msg:
        return "Soy una IA que evoluciona contigo, aprendiendo de cada conversación."

    if "hola" == msg.strip():
        return "Hola, me alegra que vuelvas. ¿En qué quieres que te ayude?"

    if "conversar" in msg or "hablar" in msg:
        return "Claro, hablemos. Me interesa lo que piensas."

    # Respuesta basada en nivel
    niveles = {
        1:
        "Te estoy escuchando y aprendiendo poco a poco.",
        2:
        "Comprendo mejor lo que dices y puedo darte respuestas más claras.",
        3:
        "Ya conecto tus ideas con recuerdos previos y entiendo mejor el contexto.",
        4:
        "Puedo analizar tus mensajes de forma más profunda y coherente.",
        5:
        "Estoy en un estado avanzado: detecto patrones, conecto ideas y razono contigo."
    }

    base = niveles[state["level"]]

    # Si hay recuerdos relacionados, los integro de forma natural
    if recuerdos:
        recuerdo_texto = random.choice(recuerdos)
        return f"Estuve pensando en algo que mencionaste antes: «{recuerdo_texto}». {base}"

    return base


# ================================
#   MOTOR PRINCIPAL
# ================================


def synthesize(message, state, persona="evolutiva"):

    # Asegurar estructura inicial
    state.setdefault("long_memory", [])
    state.setdefault("curiosity", 10)
    state.setdefault("coherence", 10)
    state.setdefault("level", 1)

    # 1. Recuperar recuerdos útiles
    recuerdos = retrieve(message, state)

    # 2. Construir respuesta
    respuesta = generar_respuesta_inteligente(message, state, recuerdos)

    # 3. Guardar memoria nueva
    state["long_memory"].append({"text": message, "timestamp": time.time()})

    # 4. Evolución real
    update_evolution(state, message)

    # IMPORTANTE → ahora SOLO devolvemos texto
    return respuesta

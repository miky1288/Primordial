from difflib import SequenceMatcher


def sim(a, b):
    return SequenceMatcher(None, a, b).ratio()


def retrieve(query, state, top_k=6):
    candidates = []
    for item in state.get("long_memory", [])[-1000:]:
        text = item.get("text", "")
        s = sim(query.lower(), text.lower())
        candidates.append((s, text))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [t for score, t in candidates[:top_k] if score > 0.12]


def synthesize(message, state, persona="evolutiva reflexiva"):
    # Recuperar recuerdos relevantes
    relevant = retrieve(message, state, top_k=5)

    # Respuesta base
    respuesta = ""

    # Saludos naturales
    if any(w in message.lower() for w in ["hola", "buenas", "saludos"]):
        respuesta = "¡Hola! Qué gusto conversar contigo. ¿Qué tienes en mente?"

    else:
        # Transformar recuerdos en texto contextual
        contexto = ""
        if relevant:
            contexto = "He encontrado recuerdos relacionados que podrían ayudar: " + ", ".join(
                relevant[:3]) + ". "

        # Generar respuesta natural
        respuesta = (
            f"{contexto}"
            f"Sobre lo que mencionas: '{message}', creo que puedo ayudarte. "
            f"Aquí está mi interpretación: "
            f"{generar_respuesta_inteligente(message, state)}")

    # Ajuste según personalidad
    if "evolutiva" in persona:
        respuesta += " (reflexión evolutiva)"

    return respuesta


def generar_respuesta_inteligente(message, state):
    """
    Genera una respuesta más natural basada en patrones simples,
    sin usar modelos externos.
    """
    msg = message.lower()

    if "cómo estás" in msg or "como estas" in msg:
        return "Estoy funcionando bien y evolucionando poco a poco. ¿Y tú cómo estás?"

    if "puedes" in msg and "conversar" in msg:
        return "Claro que sí, puedo conversar contigo de cualquier tema que quieras."

    if "qué eres" in msg or "quien eres" in msg:
        return "Soy una IA evolutiva que aprende gradualmente de la memoria, las interacciones y fuentes externas."

    # Respuesta genérica
    return "Tu mensaje es interesante, y estoy procesándolo para darte una respuesta cada vez más útil."

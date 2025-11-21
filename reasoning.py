from difflib import SequenceMatcher

def sim(a,b):
    return SequenceMatcher(None, a, b).ratio()

def retrieve(query, state, top_k=6):
    candidates = []
    for item in state.get("long_memory", [])[-1000:]:
        text = item.get("text","")
        s = sim(query.lower(), text.lower())
        candidates.append((s, text))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [t for score,t in candidates[:top_k] if score>0.12]

def synthesize(message, state, persona="evolutiva reflexiva"):
    relevant = retrieve(message, state, top_k=5)
    resp = ""
    if any(w in message.lower() for w in ["hola","buenos","buenas"]):
        resp = "¡Hola! Estoy aquí. ¿En qué puedo ayudarte hoy?"
    else:
        resp = f"He recibido: '{message}'."
        if relevant:
            resp += " Esto me recordó: " + " ; ".join(relevant[:3])
        else:
            resp += " Estoy reflexionando para darte una respuesta útil."
    # tono según persona simple
    if "evolutiva" in persona:
        resp += " (tono investigativo)"
    return resp

# ---------- Reemplazar las funciones think y agent_reply por estas ----------

def think(user_message, state):
    """
    Genera una respuesta usando reasoning.synthesize()
    Acepta synthesize que devuelva:
      - una string (respuesta)
      - o una tupla (respuesta, new_state_dict)
    Si viene new_state, lo fusiona en state.
    Devuelve siempre la respuesta como string.
    """
    try:
        result = synthesize(user_message, state)
    except Exception as e:
        return f"Error interno en el módulo de razonamiento: {str(e)}"

    # Normalizar tipos de retorno
    if isinstance(result, tuple) and len(result) >= 1:
        resp = result[0]
        maybe_state = result[1] if len(result) > 1 else None
        # si el reasoning devolvió un nuevo estado parcial, fusionarlo
        if isinstance(maybe_state, dict):
            try:
                # fusionar claves superficiales (no reemplazar objeto completo)
                for k, v in maybe_state.items():
                    state[k] = v
            except Exception:
                pass
        # asegurarnos de que devuelva string
        return resp if isinstance(resp, str) else str(resp)

    # si result es string u otro, devolver string
    return result if isinstance(result, str) else str(result)


def agent_reply(user_message, state):
    """
    Función principal que:
    1. Pide al reasoning.synthesize() que genere una respuesta
    2. Evalúa la interacción (genera propuesta)
    3. Guarda propuesta en proposals/
    4. Devuelve la respuesta al usuario (solo texto)
    """
    ai_response = think(user_message, state)

    # Generar propuesta evolutiva (no bloqueante)
    try:
        process_interaction(user_message, ai_response, state)
    except Exception:
        # no bloquear la respuesta si falla la creación de propuestas
        pass

    return ai_response


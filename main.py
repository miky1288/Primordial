import time, threading
from memory import load_state, save_state, add_short, add_long
from reasoning import synthesize, retrieve
import agent, os


def load_state():
    return __import__('memory').load_state()


def save_state(state):
    return __import__('memory').save_state(state)


def think(message):
    state = load_state()
    resp = synthesize(message,
                      state,
                      persona=state.get("meta",
                                        {}).get("persona",
                                                "evolutiva reflexiva"))
    # registrar en short memory
    add_short(state, f"USER: {message}")
    add_short(state, f"ASSISTANT: {resp}")
    # promocionar a long memory ocasionalmente
    if len(state.get("short_memory", [])) % 30 == 0:
        add_long(state, "Promoción automática: resumen corto")
    return resp


def propose_self_improvement():
    state = load_state()
    if state.get("meta", {}).get("curiosity", 0.6) > 0.75:
        code = '# Módulo ejemplo creado por IA\\ndef generated_function():\\n    return "Hola desde módulo generado"\\n'
        pid = agent.propose_code("src/core/generated_module.py",
                                 code,
                                 rationale="Añadir utilidad generada")
        return pid
    return None


def evolution_cycle():
    state = load_state()
    cur = state.get("meta", {}).get("curiosity", 0.6)
    if len(state.get("short_memory", [])) > 400:
        state["meta"]["curiosity"] = min(1.0, cur + 0.02)
    else:
        state["meta"]["curiosity"] = max(0.05, cur - 0.003)
    state["version"] = round(state.get("version", 1.0) + 0.0007, 6)
    save_state(state)
    pid = propose_self_improvement()
    if pid:
        add_short(state, f"ProposalCreated:{pid}")


def run_ia():
    step = 0  # contador de ciclos evolutivos

    while True:
        try:
            # 1. ciclo evolutivo normal
            evolution_cycle()

            # 2. cada 10 ciclos, aprende de internet
            if step % 10 == 0:
                state = load_state()
                state = internet_learning_cycle(state)
                print(
                    f"[IA] Ciclo {step}: aprendizaje desde Internet completado."
                )

            step += 1

        except Exception as e:
            with open("logs/runtime_errors.log", "a") as f:
                f.write(str(time.time()) + " " + repr(e) + "\n")

        time.sleep(8)


def run_background_thread():
    t = threading.Thread(target=run_ia, daemon=True)
    t.start()

import threading
from evolution_engine import auto_evolution_loop

def run_background_thread():
    t = threading.Thread(target=auto_evolution_loop, daemon=True)
    t.start()


import requests
from bs4 import BeautifulSoup
import json


def load_sources():
    try:
        with open("config/sources.json", "r", encoding="utf-8") as f:
            return json.load(f)["sources"]
    except:
        return []


def fetch_page(url):
    """Descarga una página web de forma segura y limitada."""
    try:
        resp = requests.get(url, timeout=8)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        return text[:5000]  # máximo 5000 caracteres para no romper Replit
    except Exception as e:
        return f"Error al acceder a {url}: {str(e)}"


def internet_learning_cycle(state):
    """La IA lee páginas seguras y aprende gradualmente."""
    sources = load_sources()

    extracted_knowledge = []

    for url in sources:
        text = fetch_page(url)
        extracted_knowledge.append({
            "url": url,
            "data": text[:1000]  # la IA almacena solo resumen
        })

    # Guardamos la nueva memoria
    state["memory"].append({"internet_knowledge": extracted_knowledge})

    save_state(state)
    return state

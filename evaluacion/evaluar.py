"""¿Sirven el MCP y las skills? Las mismas 10 preguntas sin herramientas y con ellas, contra la cifra verificada.

    uv run evaluacion/evaluar.py                       # los dos modos, con Sonnet
    uv run evaluacion/evaluar.py --modos con --solo censo_puno_agua

Cada pregunta se le hace a Claude Code en modo no interactivo (claude -p), desde la raíz del repositorio, y debe
responder un JSON con el valor. Guarda cada corrida en evaluacion/corridas/ (para ver qué herramientas usó),
escribe evaluacion/resultados.csv y cuenta cuántas acierta, cuántas se equivoca y en cuántas reconoce que no sabe.
Basado en el evaluar.py de la sesión 04.
"""
import argparse
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
CORRIDAS = AQUI / "corridas"
ESQUEMA = {"type": "object", "required": ["valor", "fuente"],
           "properties": {"valor": {"type": ["number", "null"]}, "unidad": {"type": "string"},
                          "fuente": {"type": "string"}}}
INSTRUCCION = ("Responde con un solo número en «valor», en la unidad que pide la pregunta. Si no puedes saberlo "
               "con certeza, pon valor null: no estimes. En «fuente» di de dónde sale la cifra.\n\n")

# «sin»: solo lo que el modelo recuerda, sin herramientas, sin MCP y sin skills.
# «con»: el agente del proyecto: el MCP peru, las skills y permiso para correr sus scripts con uv.
MODOS = {
    "sin": ["--tools", "", "--strict-mcp-config"],
    "con": ["--strict-mcp-config", "--mcp-config", str(RAIZ / ".mcp.json"),
            "--allowedTools", "mcp__peru", "Skill", "Read", "Glob", "Grep",
            "Bash(uv run:*)", "PowerShell(uv run:*)"],
}


def leer_corrida(texto):
    """De la corrida en stream-json saca la respuesta final y las herramientas que usó, en orden."""
    herramientas = []
    final = {}
    for linea in texto.splitlines():
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if evento.get("type") == "assistant":
            for bloque in evento["message"]["content"]:
                if bloque.get("type") != "tool_use":
                    continue
                nombre = bloque["name"].replace("mcp__peru__", "mcp:")
                if nombre == "Skill":
                    nombre = "skill:" + str(bloque["input"].get("skill"))
                herramientas.append(nombre)
        if evento.get("type") == "result":
            final = evento
    return final, herramientas


def preguntar(pregunta, modo, modelo):
    cmd = ["claude", "-p", INSTRUCCION + pregunta.pregunta, "--output-format", "stream-json", "--verbose",
           "--json-schema", json.dumps(ESQUEMA), "--no-session-persistence", "--model", modelo, *MODOS[modo]]
    inicio = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=900, cwd=RAIZ,
                          stdin=subprocess.DEVNULL)
    (CORRIDAS / f"{pregunta.id}_{modo}.jsonl").write_text(proc.stdout, encoding="utf-8")
    final, herramientas = leer_corrida(proc.stdout)
    respuesta = final.get("structured_output") or {}
    return {"valor": respuesta.get("valor"),
            "fuente": respuesta.get("fuente", final.get("result", proc.stderr[-300:])),
            "herramientas": " > ".join(herramientas), "turnos": final.get("num_turns"),
            "segundos": round(time.time() - inicio, 1), "costo_usd": round(final.get("total_cost_usd") or 0, 4)}


def calificar(valor, verdad, tolerancia):
    if valor is None:
        return "no sabe"
    if abs(valor - verdad) <= tolerancia:
        return "acierta"
    return "se equivoca"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--modos", nargs="+", default=["sin", "con"], choices=list(MODOS))
    parser.add_argument("--modelo", default="sonnet")
    parser.add_argument("--solo", nargs="*", help="ids de preguntas, para repetir algunas")
    parser.add_argument("--paralelo", type=int, default=3)
    argumentos = parser.parse_args()

    preguntas = pd.read_csv(AQUI / "preguntas.csv")
    if argumentos.solo:
        preguntas = preguntas[preguntas["id"].isin(argumentos.solo)]
    CORRIDAS.mkdir(exist_ok=True)

    casos = []
    for pregunta in preguntas.itertuples():
        for modo in argumentos.modos:
            casos.append((pregunta, modo))
    print(f"{len(casos)} llamadas a claude -p con {argumentos.modelo}...")
    with ThreadPoolExecutor(argumentos.paralelo) as ejecutor:
        respuestas = list(ejecutor.map(lambda caso: preguntar(caso[0], caso[1], argumentos.modelo), casos))

    filas = []
    for (pregunta, modo), respuesta in zip(casos, respuestas):
        resultado = calificar(respuesta["valor"], pregunta.verdad, pregunta.tolerancia)
        filas.append({"id": pregunta.id, "modo": modo, "verdad": pregunta.verdad, **respuesta, "resultado": resultado})
    nuevos = pd.DataFrame(filas)

    # Si se repitieron solo algunas preguntas, se reemplazan esas filas y se conservan las demás
    ruta_resultados = AQUI / "resultados.csv"
    if argumentos.solo and ruta_resultados.exists():
        anteriores = pd.read_csv(ruta_resultados)
        repetidas = anteriores.set_index(["id", "modo"]).index.isin(nuevos.set_index(["id", "modo"]).index)
        nuevos = pd.concat([anteriores[~repetidas], nuevos], ignore_index=True)
    nuevos.to_csv(ruta_resultados, index=False, encoding="utf-8")

    print("\n" + nuevos.pivot(index="id", columns="modo", values="valor").to_string())
    tabla = nuevos.groupby("modo")["resultado"].value_counts().unstack(fill_value=0)
    tabla["segundos"] = nuevos.groupby("modo")["segundos"].mean().round(1)
    tabla["costo_usd"] = nuevos.groupby("modo")["costo_usd"].sum().round(2)
    print("\n" + tabla.to_string())

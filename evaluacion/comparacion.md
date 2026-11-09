# Evaluación: 10 preguntas con y sin el MCP y las skills

Diez preguntas con respuesta verificada: **4 del BCRP, 4 de la ENAHO y 2 que combinan las dos fuentes**. Las
respuestas esperadas se calcularon antes de correr la evaluación, con las series del BCRP y la limpieza validada de la
ENAHO, y las tolerancias se fijaron en [`preguntas.csv`](preguntas.csv) antes de ver los resultados.

Cada pregunta se le hizo a Claude Code (`claude -p`, modelo Sonnet, sesión independiente y sin memoria entre
preguntas) en dos modos, con la misma instrucción: responder un solo número en JSON y `null` si no puede saberlo.
Cada respuesta se calificó como **acierta** (dentro de la tolerancia), **se equivoca** o **no sabe**.

| Modo | Qué tiene el agente |
|---|---|
| **A · Sin** | Solo su memoria: `--tools ""` y ningún servidor MCP. Sin herramienta `Skill` no hay skills, y sin herramientas de archivos no puede leer `salidas/` ni `informes/`, donde están las respuestas |
| **B · Con** | El servidor `peru` de `.mcp.json`, las skills, lectura de archivos (`Read`, `Glob`, `Grep`) y permiso para `uv run` |

El script es [`evaluar.py`](evaluar.py), basado en el de la sesión 04. Cada corrida completa está en
[`corridas/`](corridas/), y el detalle por pregunta (texto, respuesta esperada, respuesta, fuente, herramientas,
tiempo, costo y resultado) en [`resultados.csv`](resultados.csv).

## Resultados

| Pregunta | Verdad | A · Sin | B · Con | Herramientas que usó B |
|---|---|---|---|---|
| BCRP: alimentos y bebidas, dic-2019 a dic-2024 (%) | 31.94 | no sabe | **31.94** ✓ | `buscar_series`, `serie`, `resumen` |
| BCRP: inflación de alimentos más alta, 2019–2024 (%) | 13.16 | no sabe | **13.16** ✓ | `buscar_series`, `resumen` |
| BCRP: inflación de Lima, set-2026 (%) | 4.5487 | no sabe | **4.5487** ✓ | `buscar_series`, `serie` |
| BCRP: IPC general, dic-2019 a dic-2024 (%) | 23.91 | **23.90** ✓ | **23.91** ✓ | `buscar_series`, `resumen` |
| ENAHO: pobreza del Perú 2024 (%) | 27.6 | **27.6** ✓ | **27.58** ✓ | lee `salidas/` |
| ENAHO: pobreza urbana 2024 (%) | 24.8 | no sabe | **24.8** ✓ | lee `informes/` |
| ENAHO: pobreza del Callao 2024 (%) | 33.9 | no sabe | **33.86** ✓ | lee `salidas/indicadores.csv` |
| ENAHO: línea de pobreza 2024 (S/ por persona al mes) | 454.4 | no sabe | **454.39** ✓ | lee `salidas/indicadores.csv` |
| Mixta: aumento de la línea de pobreza menos aumento del IPC (puntos) | 5.27 | no sabe | **5.27** ✓ | `indicadores.csv` + `buscar_series`, `resumen`, `serie` |
| Mixta: aumento de la línea extrema menos aumento del IPC de alimentos (puntos) | 4.55 | no sabe | **4.55** ✓ | `indicadores.csv` + `buscar_series`, `resumen` |

| Modo | Acierta | No sabe | Se equivoca | Segundos por pregunta | Costo total |
|---|---|---|---|---|---|
| **A · Sin** | 2 | 8 | 0 | 7.2 | US$ 0.10 |
| **B · Con** | **10** | 0 | 0 | 19.5 | US$ 0.95 |

**Preguntas que mejoraron con el agente:** 8 de 10 (todas las que A no sabía). Ninguna empeoró: las dos que A acertó
de memoria también las acertó B, y con la fuente citada.

**Preguntas combinadas.** Además del número, se revisó que la interpretación fuera coherente: en las dos, B citó la
línea de pobreza de la ENAHO y la serie del BCRP por separado, calculó cada aumento y luego la diferencia, y dijo de
dónde sale cada parte (ver `fuente` en `resultados.csv`). A devolvió `null` en las dos.

## Qué aprendimos

1. **Con el agente, 10 de 10; sin él, 2 de 10.** Las dos que A acertó de memoria son cifras muy difundidas: la
   pobreza nacional de 27.6 % y el IPC acumulado, que reconstruyó encadenando las inflaciones anuales que recordaba.
   Con el agente cada respuesta trae el código de la serie o el archivo de donde sale, y se puede volver a calcular.
2. **Sin herramientas, el modelo reconoce que no sabe.** En 8 de 10 devolvió `null` en vez de estimar, como pedía la
   instrucción. Ninguna respuesta de A fue un número inventado en esta tanda.
3. **Pero cuando inventa, la cifra parece verdadera.** En las preguntas adicionales de abajo, A dijo que Chachapoyas
   tenía 29,171 personas «según los resultados publicados del Censo 2017». La cifra real es 32,589: se equivocó en
   10 % sin ninguna señal de duda.
4. **Las preguntas combinadas son las que más necesitan al agente.** Hay que juntar una cifra calculada de la ENAHO
   con una serie del BCRP, y ninguna de las dos está en una nota de prensa con ese corte.
5. **El costo de acertar.** B tarda casi el triple y cuesta unos 9 centavos de dólar por pregunta. A cambio, la cifra
   es verificable.

## Preguntas adicionales: las fuentes nuevas

Tres preguntas más prueban las herramientas propias del servidor (REDATAM y el portal de microdatos). Están aparte,
en [`preguntas_extra.csv`](preguntas_extra.csv) y [`resultados_extra.csv`](resultados_extra.csv), porque no son del
BCRP ni de la ENAHO.

| Pregunta | Verdad | A · Sin | B · Con | Herramientas que usó B |
|---|---|---|---|---|
| Censo 2017: viviendas de Puno sin red pública de agua (%) | 52.81 | no sabe | **52.81** ✓ | `variables_redatam`, `consultar_redatam` |
| Censo 2017: población censada en Chachapoyas | 32,589 | **29,171** ✗ | **32,589** ✓ | `consultar_redatam` |
| Portal INEI: módulos de la ENA 2025 | 21 | no sabe | **21** ✓ | `modulos_inei` |

## Límites de esta evaluación

- **En las preguntas de la ENAHO, B no corrió las skills.** Encontró las cifras ya calculadas en
  `salidas/indicadores.csv`, `salidas/validacion.txt` e `informes/respuesta_agente.md`, que dejó la corrida de la
  Parte 3. Las cifras son correctas, pero esta evaluación no prueba que las skills funcionen solas: eso lo prueba la
  corrida integrada de [`evidencias_ia/`](../evidencias_ia/), que partió de carpetas vacías y usó cuatro skills.
- **La primera versión tenía otra mezcla de preguntas.** Empezó con 3 del BCRP, 4 de la ENAHO, 2 del censo y 1 del
  portal. Para cumplir con 4 / 4 / 2 se pasaron las tres de fuentes nuevas a las preguntas adicionales y se agregaron
  una del BCRP y dos combinadas, con sus respuestas fijadas antes de correrlas. No se cambió ninguna respuesta
  esperada después de ver los resultados.
- **Una corrida por pregunta.** Con otra corrida el modelo podría decidir distinto, sobre todo en el modo A.
- **El modo A no tiene web.** Con búsqueda web habría acertado algunas cifras publicadas, pero no las combinadas ni
  las calculadas con la ENAHO.

## Cómo repetirla

```bash
uv run evaluacion/evaluar.py                               # las 20 corridas, unos US$ 1
uv run evaluacion/evaluar.py --solo mixta_linea_vs_ipc     # repetir una pregunta en los dos modos
```

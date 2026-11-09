# Evaluación: 10 preguntas con y sin el MCP y las skills

Cada pregunta se le hizo a Claude Code (`claude -p`, modelo Sonnet) dos veces, desde la raíz del repositorio, pidiendo
un solo número en JSON. Cada respuesta se calificó contra la cifra verificada en
[`preguntas.csv`](preguntas.csv): **acierta** si cae dentro de la tolerancia, **se equivoca** si no, y **no sabe** si
devuelve `null`.

| Modo | Qué tiene el agente |
|---|---|
| **Sin** | Solo su memoria: `--tools ""` y ningún servidor MCP. No hay skills porque no hay herramienta `Skill` |
| **Con** | El servidor `peru` de `.mcp.json`, las skills, lectura de archivos y permiso para `uv run` |

El script es [`evaluar.py`](evaluar.py), basado en el de la sesión 04. Cada corrida completa está en
[`corridas/`](corridas/) y el detalle, en [`resultados.csv`](resultados.csv).

## Resultados

| Pregunta | Verdad | Sin | Con | Herramientas que usó «con» |
|---|---|---|---|---|
| Alimentos y bebidas, dic-2019 a dic-2024 (%) | 31.94 | no sabe | **31.94** ✓ | `buscar_series`, `serie`, `resumen` |
| Inflación de alimentos más alta, 2019–2024 (%) | 13.16 | no sabe | **13.16** ✓ | `buscar_series`, `resumen` |
| Inflación de Lima, set-2026 (%) | 4.5487 | no sabe | **4.5487** ✓ | `buscar_series`, `serie` |
| Pobreza del Perú 2024 (%) | 27.6 | **27.6** ✓ | **27.58** ✓ | lee `salidas/` |
| Pobreza urbana 2024 (%) | 24.8 | no sabe | **24.8** ✓ | lee `informes/` |
| Pobreza del Callao 2024 (%) | 33.9 | no sabe | **33.86** ✓ | lee `salidas/indicadores.csv` |
| Línea de pobreza 2024 (S/ por persona al mes) | 454.4 | no sabe | **454.39** ✓ | lee `salidas/indicadores.csv` |
| Viviendas de Puno sin red pública de agua, 2017 (%) | 52.81 | no sabe | **52.81** ✓ | `variables_redatam`, `consultar_redatam` |
| Población censada en Chachapoyas, 2017 | 32,589 | **29,171** ✗ | **32,589** ✓ | `consultar_redatam` |
| Módulos de la ENA 2025 en el portal del INEI | 21 | no sabe | **21** ✓ | `modulos_inei` |

| Modo | Acierta | No sabe | Se equivoca | Segundos por pregunta | Costo total |
|---|---|---|---|---|---|
| **Sin** | 1 | 8 | 1 | 6.2 | US$ 0.09 |
| **Con** | **10** | 0 | 0 | 17.2 | US$ 0.85 |

## Qué aprendimos

1. **Con el agente, 10 de 10; sin él, 1 de 10.** La única que acertó de memoria fue la cifra más difundida del año:
   la pobreza nacional de 27.6 %. Con el agente cada respuesta trae el código de la serie, la variable del censo o
   el archivo de donde sale, y se puede volver a calcular.
2. **Sin herramientas, el modelo casi siempre reconoce que no sabe.** En 8 de 10 devolvió `null` en vez de estimar.
   Eso es bueno: la instrucción pedía no inventar.
3. **Pero cuando inventa, la cifra parece verdadera.** Para Chachapoyas dio 29,171 personas «de los resultados
   publicados del Censo 2017». La cifra real es 32,589: se equivocó en 10 % sin ninguna señal de duda. Es justo el
   tipo de error que un lector no puede detectar.
4. **Las preguntas nuevas solo se responden con las herramientas nuevas.** El censo por distrito, el porcentaje de
   Puno o los módulos de la ENA no están en ninguna nota de prensa: hay que consultar REDATAM o el portal. Ahí está el
   valor de `consultar_redatam` y `modulos_inei`.
5. **El costo de acertar.** El modo con herramientas tarda casi el triple y cuesta unos 9 centavos de dólar por
   pregunta. A cambio, la cifra es verificable.

## Límites de esta evaluación

- **En las preguntas de la ENAHO, el agente no corrió las skills.** Encontró las cifras ya calculadas en
  `salidas/indicadores.csv`, `salidas/validacion.txt` e `informes/respuesta_agente.md`, que dejó la corrida de la
  Parte 3. Las cifras son correctas, pero esta evaluación no prueba que las skills funcionen solas: eso lo prueba la
  corrida integrada de [`evidencias_ia/`](../evidencias_ia/), que partió de carpetas vacías y usó cuatro skills. Para
  medirlo aquí habría que correr el modo «con» en una copia del repositorio sin `salidas/` ni `informes/`.
- **Diez preguntas, una corrida por pregunta.** Con otra corrida el modelo podría decidir distinto, sobre todo en el
  modo «sin».
- **El modo «sin» no tiene web.** Con búsqueda web habría acertado algunas cifras publicadas (como la inflación de
  setiembre de 2026), pero no las de REDATAM ni las calculadas con la ENAHO.

## Cómo repetirla

```bash
uv run evaluacion/evaluar.py                               # las 20 corridas, unos US$ 1
uv run evaluacion/evaluar.py --solo censo_chachapoyas      # repetir una pregunta en los dos modos
```

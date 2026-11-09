---
name: graficando-enaho
description: Grafica la pobreza monetaria o extrema de la ENAHO por área urbana y rural, dominio, departamento, sexo o edad, en barras PNG listas para presentar. Úsala cuando pidan un gráfico, una figura o una comparación visual de la pobreza o de la ENAHO.
argument-hint: [grupo] [año]
---

# Graficar la ENAHO

1. Si el usuario no dice el año, usa 2024.
2. Si no existen `salidas/hogares_<año>.parquet` y `salidas/personas_<año>.parquet`, usa primero la skill limpiando-enaho.
3. Elige el grupo según la pregunta:

| Si piden… | `--por` |
|---|---|
| urbano y rural, área | `area` |
| costa, sierra, selva, región natural | `dominio` |
| departamento, región | `departamento` |
| hombres y mujeres | `sexo` |
| niños, jóvenes, adultos mayores, edad | `edad` |

4. Corre: `uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py --por <grupo> --anio <año>`. Para pobreza extrema, agrega `--indicador pobre_extremo`.
5. Muestra la ruta del PNG y las cifras que imprime el script, con un decimal.

## Reglas (ya están en el script; respétalas si escribes otro)

- Pondera siempre: `factor_personas` para territorio, `facpob07` para sexo y edad.
- Barras horizontales que empiezan en cero, ordenadas de mayor a menor. La edad va en su orden natural.
- Un solo color (`#B5451B`); el valor escrito en cada barra.
- El título dice qué y cuándo: «Pobreza monetaria por departamento, 2024».
- Nota al pie: «Fuente: INEI, ENAHO 2024» y el factor usado.
- PNG a 200 dpi en `figuras/`.

Si piden un gráfico que el script no hace, escribe un script nuevo en `${CLAUDE_SKILL_DIR}/scripts/` con estas mismas reglas. No cambies los números a mano.

---
name: cruzando-fuentes
description: Cruza la pobreza de la ENAHO de dos años con el Censo 2017 (REDATAM) y la línea de pobreza, y deja salidas/indicadores.csv y un gráfico del cambio por departamento. Úsala cuando pregunten cómo cambió la pobreza entre dos años, qué departamentos empeoraron, si la falta de servicios se relaciona con la pobreza, o cuando haya que armar los indicadores de un informe.
argument-hint: [año inicial] [año final]
---

# Cruzar fuentes

1. Si el usuario no dice los años, usa 2019 (antes de la pandemia) y 2024.
2. Para cada año, si no existe `salidas/hogares_<año>.parquet`, usa primero la skill limpiando-enaho (y esta, si hace falta, descargando-enaho).
3. Si no existe `salidas/redatam/agua_departamento.csv`, pídelo al Censo con la herramienta MCP `consultar_redatam`, con `nombre="agua_departamento"` y exactamente este programa:

```
DEFINE Departam.SINRED AS COUNT Vivienda FOR Vivienda.C2P6 >= 3 TYPE INTEGER
DEFINE Departam.CONDATO AS COUNT Vivienda FOR Vivienda.C2P6 >= 1 TYPE INTEGER
TABLE T1 AS AREALIST OF Departam, Departam.CCDD, Departam.NCCDD, Departam.SINRED, Departam.CONDATO
```

   `C2P6` es el abastecimiento de agua: 1 y 2 son red pública; de 3 en adelante, pilón, cisterna, pozo, río u otro.
4. Corre exactamente: `uv run ${CLAUDE_SKILL_DIR}/scripts/cruzar.py --desde <año inicial> --hasta <año final>`
5. Responde con las cifras que imprime el script, con un decimal, y la ruta del gráfico.

## Qué deja

| Archivo | Qué es |
|---|---|
| `salidas/indicadores.csv` | Formato largo: `indicador`, `ambito`, `codigo`, `nombre`, `anio`, `valor`, `unidad`, `fuente` |
| `figuras/cambio_pobreza_departamento_<a>_<b>.png` | Cambio de la pobreza en puntos porcentuales, de mayor a menor |

## Reglas

- Las tasas van ponderadas con `factor_personas` (`factor07 × mieperho`), igual que el INEI.
- Los códigos de departamento son texto de dos dígitos: `"01"`, no `1`.
- El cambio se dice en **puntos porcentuales**, no en %: de 20.2 % a 27.6 % son +7.4 puntos.
- Una correlación entre 25 departamentos describe; no prueba causas. Dilo así en el texto.
- El censo es de 2017: sirve como punto de partida, no como foto de 2024.

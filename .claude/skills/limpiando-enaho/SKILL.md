---
name: limpiando-enaho
description: Limpia los módulos 34 (sumaria) y 02 (miembros) de la ENAHO del INEI y arma una base de hogares y otra de personas con pobreza y factor de expansión, validadas contra la cifra oficial del INEI. Úsala cuando pidan limpiar, unir o analizar la ENAHO, o calcular pobreza por departamento, región, área, sexo o edad.
argument-hint: [año]
---

# Limpiar la ENAHO

1. Si el usuario no dice el año, usa 2024.
2. Si no existe `datos/*-Modulo34/sumaria-$0.dta`, usa primero la skill descargando-enaho.
3. Corre exactamente: `uv run ${CLAUDE_SKILL_DIR}/scripts/limpiar.py --anio $0`
4. Lee `salidas/validacion.txt`. Si el resultado no es «OK», detente y muéstrale el archivo al usuario. No uses la base.
5. Responde con la base que corresponde a la pregunta, siempre ponderada:

| La pregunta es por… | Base | Factor |
|---|---|---|
| Total nacional, área, dominio o departamento | `salidas/hogares_$0.parquet` | `factor_personas` |
| Sexo, edad o parentesco | `salidas/personas_$0.parquet` | `facpob07` |

6. Antes de usar una variable que no está en la base, o un código que no conoces, lee [reference.md](reference.md).

## Reglas

- `pobreza` es un código (1 extremo, 2 no extremo, 3 no pobre). Usa las columnas `pobre` y `pobre_extremo`, nunca el promedio de `pobreza`.
- Nunca reportes una cifra sin ponderar. 33,691 hogares representan 34.5 millones de personas.
- Los ubigeos y las llaves son texto: `"080101"`, no `80101`.
- Redondea a un decimal y di el año: «la pobreza en Cusco fue 18.5 % en 2024».

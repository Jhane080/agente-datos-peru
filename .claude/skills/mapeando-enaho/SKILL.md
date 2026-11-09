---
name: mapeando-enaho
description: Hace un mapa coroplético del Perú con la pobreza monetaria o extrema de la ENAHO por departamento, unido a los límites departamentales por código. Úsala cuando pidan un mapa de la pobreza, comparar departamentos en un mapa o ver la ENAHO en el territorio.
argument-hint: [año]
---

# Mapear la ENAHO

1. Si el usuario no dice el año, usa 2024.
2. Si no existe `salidas/hogares_<año>.parquet`, usa primero la skill limpiando-enaho.
3. Corre: `uv run ${CLAUDE_SKILL_DIR}/scripts/mapear.py --anio <año>`. Para pobreza extrema, agrega `--indicador pobre_extremo`.
4. El script baja los límites a `datos/peru_departamental_simple.geojson` si faltan.
5. Muestra la ruta del PNG y los tres departamentos con más y con menos pobreza, con un decimal.
6. Si el script se detiene por departamentos sin dato, no lo arregles a mano. Revisa que `departamento` y `FIRST_IDDP` sean texto de dos dígitos.

## Reglas (ya están en el script; respétalas si escribes otro mapa)

- Une por código: `ubigeo[:2]` (columna `departamento`) con `FIRST_IDDP`.
- Nunca por nombre: «APURIMAC» no es «Apurímac».
- Exige 25 departamentos y ninguno sin dato.
- Un color de claro a oscuro (`Oranges`), con la escala desde 0. Nunca arcoíris.
- Leyenda con la unidad: % de personas.
- Lima (15) y Callao (07) van separados. Callao casi no se ve en el mapa; si preguntan por él, da la cifra.
- Pondera con `factor_personas` (`factor07 × mieperho`), igual que el INEI.
- PNG a 200 dpi en `mapas/`.

## Cifras de control, 2024

Más pobreza: Cajamarca 45.0 %, Loreto 43.0 %, Puno 39.9 %.
Menos pobreza: Ica 6.0 %, Moquegua 11.0 %, Madre de Dios 11.1 %.
Si el mapa da otras cifras, revisa la unión.

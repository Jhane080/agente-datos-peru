"""Limpia la ENAHO anual: sumaria (módulo 34) y miembros (módulo 02).

Siete pasos, siempre en el mismo orden: leer, normalizar, filtrar, unir,
construir, validar y guardar. Deja en salidas/:
  hogares_<año>.parquet   una fila por hogar, para pobreza por área o departamento
  personas_<año>.parquet  una fila por residente, para pobreza por sexo o edad
  validacion.txt          la prueba de que la base replica la cifra del INEI

Uso:  uv run limpiar.py --anio 2024
"""

import argparse
from pathlib import Path

import pandas as pd

CARPETA_DATOS = Path("datos")
CARPETA_SALIDAS = Path("salidas")

LLAVES_HOGAR = ["conglome", "vivienda", "hogar"]
LLAVES_PERSONA = LLAVES_HOGAR + ["codperso"]

# Las llaves son texto con ceros a la izquierda: conglome "015009", ubigeo "010101".
ANCHO_DE_LLAVE = {"conglome": 6, "vivienda": 3, "hogar": 2, "codperso": 2, "ubigeo": 6}

# Pobreza monetaria oficial del INEI (% de personas). Verificadas con la sumaria.
POBREZA_OFICIAL = {2019: 20.2, 2022: 27.5, 2023: 29.0, 2024: 27.6}
# Residentes habituales que debe dejar el filtro (valor de referencia del curso)
RESIDENTES_OFICIAL = {2024: 108664}

parser = argparse.ArgumentParser(description="Limpia la ENAHO anual del INEI")
parser.add_argument("--anio", type=int, required=True)
anio = parser.parse_args().anio


def tasa_ponderada(datos, condicion, factor):
    """Porcentaje de personas que cumplen la condición, usando el factor de expansión."""
    return (datos[factor] * condicion).sum() / datos[factor].sum() * 100


# 1. Leer ---------------------------------------------------------------------
# La carpeta lleva el código del INEI (966 para 2024), así que la buscamos.
rutas_sumaria = list(CARPETA_DATOS.glob(f"*-Modulo34/sumaria-{anio}.dta"))
rutas_miembros = list(CARPETA_DATOS.glob(f"*-Modulo02/enaho01-{anio}-200.dta"))
if not rutas_sumaria or not rutas_miembros:
    raise SystemExit(f"Faltan los .dta de {anio} en datos/. Usa primero la skill descargando-enaho.")

# convert_categoricals=False deja pobreza como 1, 2, 3 y no como etiquetas.
sumaria = pd.read_stata(rutas_sumaria[0], convert_categoricals=False)
miembros = pd.read_stata(rutas_miembros[0], convert_categoricals=False)

# 2. Normalizar ---------------------------------------------------------------
# La columna del año llega como "aÑo". Con la ñ el código se rompe al
# escribirlo en otro teclado o en otra consola; la pasamos a "anio".
for tabla in [sumaria, miembros]:
    tabla.columns = tabla.columns.str.lower().str.replace("año", "anio")

for columna, ancho in ANCHO_DE_LLAVE.items():
    for tabla in [sumaria, miembros]:
        if columna in tabla.columns:
            tabla[columna] = tabla[columna].astype(str).str.zfill(ancho)

# 3. Filtrar ------------------------------------------------------------------
# Residente habitual: miembro del hogar que no estuvo ausente 30 días o más,
# o no miembro que estuvo presente 30 días o más. Es el filtro del INEI.
es_residente = ((miembros["p204"] == 1) & (miembros["p205"] == 2)) | (
    (miembros["p204"] == 2) & (miembros["p206"] == 1)
)
personas = miembros[es_residente]
personas = personas[LLAVES_PERSONA + ["p203", "p207", "p208a", "facpob07"]]

# 4. Unir ---------------------------------------------------------------------
hogares = sumaria[
    ["anio", "mes"] + LLAVES_HOGAR
    + ["ubigeo", "dominio", "estrato", "mieperho", "factor07", "pobreza"]
].copy()

# validate="m:1" falla si un hogar aparece dos veces en la sumaria,
# en vez de multiplicar personas sin avisar.
base_personas = personas.merge(hogares, on=LLAVES_HOGAR, how="left", validate="m:1")

# 5. Construir ----------------------------------------------------------------
for tabla in [hogares, base_personas]:
    tabla["departamento"] = tabla["ubigeo"].str[:2]
    tabla["urbano"] = tabla["estrato"] <= 5
    # pobreza es un código (1 extremo, 2 no extremo, 3 no pobre), no un número.
    tabla["pobre"] = tabla["pobreza"] <= 2
    tabla["pobre_extremo"] = tabla["pobreza"] == 1

# Un hogar representa factor07 hogares de factor07 × mieperho personas.
# Es el factor que usa el INEI para la cifra oficial de pobreza.
hogares["factor_personas"] = hogares["factor07"] * hogares["mieperho"]

# 6. Validar ------------------------------------------------------------------
assert not hogares.duplicated(LLAVES_HOGAR).any(), "Hay hogares repetidos"
assert not base_personas.duplicated(LLAVES_PERSONA).any(), "Hay personas repetidas"
assert len(base_personas) == len(personas), "La unión perdió o duplicó filas"
assert base_personas["pobreza"].notna().all(), "Hay personas sin hogar en la sumaria"

pobreza = tasa_ponderada(hogares, hogares["pobre"], "factor_personas")
pobreza_extrema = tasa_ponderada(hogares, hogares["pobre_extremo"], "factor_personas")
pobreza_en_personas = tasa_ponderada(base_personas, base_personas["pobre"], "facpob07")

cifra_oficial = POBREZA_OFICIAL.get(anio)
residentes_oficial = RESIDENTES_OFICIAL.get(anio)
codigos_esperados = {f"{numero:02d}" for numero in range(1, 26)}

# Cada control queda escrito como APROBADO o FALLIDO en validacion.txt
controles = [
    ("Hogares sin duplicados (conglome, vivienda, hogar)", not hogares.duplicated(LLAVES_HOGAR).any()),
    ("Personas sin duplicados (+ codperso)", not base_personas.duplicated(LLAVES_PERSONA).any()),
    ("Unión m:1 sin perder ni duplicar filas", len(base_personas) == len(personas)),
    ("Todas las personas tienen hogar en la sumaria", bool(base_personas["pobreza"].notna().all())),
    ("Ubigeos como texto de 6 dígitos", bool(hogares["ubigeo"].str.fullmatch(r"\d{6}").all())),
    ("25 códigos de departamento (01 a 25)", set(hogares["departamento"]) == codigos_esperados),
    ("Factores de expansión completos y positivos", bool((hogares["factor_personas"] > 0).all())),
]
if residentes_oficial is not None:
    controles.append((f"Residentes habituales = {residentes_oficial:,}", len(base_personas) == residentes_oficial))
if cifra_oficial is not None:
    controles.append((f"Pobreza a menos de 0.1 puntos del INEI ({cifra_oficial} %)",
                      abs(pobreza - cifra_oficial) < 0.1))

lineas_controles = "\n".join(f"[{'APROBADO' if paso else 'FALLIDO '}] {nombre}" for nombre, paso in controles)
if cifra_oficial is None:
    resultado = "SIN CIFRA OFICIAL: agreguen la del INEI a POBREZA_OFICIAL"
elif all(paso for _, paso in controles):
    resultado = "OK"
else:
    resultado = "DIFERENCIA: revisen la limpieza antes de usar la base"

# 7. Guardar ------------------------------------------------------------------
CARPETA_SALIDAS.mkdir(exist_ok=True)
hogares.to_parquet(CARPETA_SALIDAS / f"hogares_{anio}.parquet", index=False)
base_personas.to_parquet(CARPETA_SALIDAS / f"personas_{anio}.parquet", index=False)

validacion = f"""ENAHO {anio}: validación de la limpieza
Hogares en la sumaria:           {len(hogares):,}
Filas en el módulo de miembros:  {len(miembros):,}
Residentes habituales:           {len(base_personas):,}
Personas que representan:        {hogares["factor_personas"].sum():,.0f}

Pobreza monetaria (sumaria, factor07 × mieperho):  {pobreza:.2f} %
Pobreza extrema (sumaria, factor07 × mieperho):    {pobreza_extrema:.2f} %
Pobreza en la base de personas (facpob07):         {pobreza_en_personas:.2f} %
Cifra oficial del INEI:                            {cifra_oficial} %

Controles:
{lineas_controles}

Resultado: {resultado}
"""
(CARPETA_SALIDAS / "validacion.txt").write_text(validacion, encoding="utf-8")
print(validacion)

if resultado != "OK":
    raise SystemExit(1)

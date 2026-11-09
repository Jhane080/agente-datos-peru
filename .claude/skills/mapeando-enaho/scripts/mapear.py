"""Mapa de la pobreza de la ENAHO por departamento.

Lee salidas/hogares_<año>.parquet, calcula la pobreza ponderada de cada
departamento, la une a los límites departamentales por código y guarda
mapas/<indicador>_departamento_<año>.png a 200 dpi.

Uso:  uv run mapear.py --anio 2024
      uv run mapear.py --indicador pobre_extremo
"""

import argparse
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventanas: solo guardamos el PNG
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

CARPETA_DATOS = Path("datos")
CARPETA_SALIDAS = Path("salidas")
CARPETA_MAPAS = Path("mapas")

RUTA_LIMITES = CARPETA_DATOS / "peru_departamental_simple.geojson"
URL_LIMITES = (
    "https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/"
    "sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson"
)

NOMBRE_INDICADOR = {"pobre": "Pobreza monetaria", "pobre_extremo": "Pobreza extrema"}
NOMBRE_ARCHIVO = {"pobre": "pobreza", "pobre_extremo": "pobreza_extrema"}

parser = argparse.ArgumentParser(description="Mapa de la pobreza por departamento")
parser.add_argument("--anio", type=int, default=2024)
parser.add_argument("--indicador", default="pobre", choices=list(NOMBRE_INDICADOR))
argumentos = parser.parse_args()
anio = argumentos.anio
indicador = argumentos.indicador

ruta_hogares = CARPETA_SALIDAS / f"hogares_{anio}.parquet"
if not ruta_hogares.exists():
    raise SystemExit(f"No existe {ruta_hogares}. Usa primero la skill limpiando-enaho.")

if not RUTA_LIMITES.exists():
    print("Bajando los límites departamentales...")
    CARPETA_DATOS.mkdir(exist_ok=True)
    urllib.request.urlretrieve(URL_LIMITES, RUTA_LIMITES)

hogares = pd.read_parquet(ruta_hogares)
departamentos = gpd.read_file(RUTA_LIMITES)

# Pobreza por departamento con el mismo factor que usa el INEI.
hogares["peso_pobre"] = hogares["factor_personas"] * hogares[indicador]
sumas = hogares.groupby("departamento")[["peso_pobre", "factor_personas"]].sum()
sumas["tasa"] = sumas["peso_pobre"] / sumas["factor_personas"] * 100
tasa_por_departamento = sumas[["tasa"]].reset_index()

# Unimos por código y nunca por nombre: "APURIMAC" no es "Apurímac".
# Los dos códigos son texto de dos dígitos: "07" es Callao y "15" es Lima.
mapa = departamentos.merge(
    tasa_por_departamento,
    left_on="FIRST_IDDP",
    right_on="departamento",
    how="left",
    validate="1:1",
)

sin_dato = mapa.loc[mapa["tasa"].isna(), "NOMBDEP"].tolist()
assert len(mapa) == 25, f"El mapa tiene {len(mapa)} departamentos y deben ser 25"
assert not sin_dato, f"Departamentos sin dato: {sin_dato}. Revisen la unión."

figura, ejes = plt.subplots(figsize=(7, 9))

# Un solo tono de claro a oscuro, desde 0: más oscuro es más pobreza.
mapa.plot(
    column="tasa",
    cmap="Oranges",
    vmin=0,
    edgecolor="white",
    linewidth=0.5,
    legend=True,
    legend_kwds={"label": f"{NOMBRE_INDICADOR[indicador]} (% de personas)", "shrink": 0.5},
    ax=ejes,
)
ejes.set_axis_off()
ejes.set_title(
    f"{NOMBRE_INDICADOR[indicador]} por departamento, {anio}",
    loc="left", fontweight="bold",
)
ejes.annotate(
    f"Fuente: INEI, ENAHO {anio}. Ponderado con factor07 × mieperho.",
    xy=(0, 0), xycoords="axes fraction", xytext=(0, -12), textcoords="offset points",
    fontsize=8, color="#555555", va="top",
)

CARPETA_MAPAS.mkdir(exist_ok=True)
ruta_mapa = CARPETA_MAPAS / f"{NOMBRE_ARCHIVO[indicador]}_departamento_{anio}.png"
figura.savefig(ruta_mapa, dpi=200, bbox_inches="tight")

ordenado = mapa.sort_values("tasa", ascending=False)[["FIRST_IDDP", "NOMBDEP", "tasa"]]
ordenado["tasa"] = ordenado["tasa"].astype(float).round(1)
print(ordenado.to_string(index=False))
print(f"Guardado: {ruta_mapa}")

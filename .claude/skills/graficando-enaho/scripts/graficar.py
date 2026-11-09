"""Grafica la pobreza de la ENAHO ya limpia, en barras horizontales.

Lee salidas/hogares_<año>.parquet o salidas/personas_<año>.parquet y guarda
figuras/<indicador>_por_<grupo>_<año>.png a 200 dpi.

Uso:  uv run graficar.py --por area --anio 2024
      uv run graficar.py --por edad --indicador pobre_extremo
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventanas: solo guardamos el PNG
import matplotlib.pyplot as plt
import pandas as pd

CARPETA_SALIDAS = Path("salidas")
CARPETA_FIGURAS = Path("figuras")
COLOR = "#B5451B"

NOMBRE_INDICADOR = {"pobre": "Pobreza monetaria", "pobre_extremo": "Pobreza extrema"}
NOMBRE_GRUPO = {
    "area": "área de residencia",
    "dominio": "dominio geográfico",
    "departamento": "departamento",
    "sexo": "sexo",
    "edad": "grupo de edad",
}

NOMBRES_DOMINIO = {
    1: "Costa norte", 2: "Costa centro", 3: "Costa sur", 4: "Sierra norte",
    5: "Sierra centro", 6: "Sierra sur", 7: "Selva", 8: "Lima Metropolitana",
}

NOMBRES_DEPARTAMENTO = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa",
    "05": "Ayacucho", "06": "Cajamarca", "07": "Callao", "08": "Cusco",
    "09": "Huancavelica", "10": "Huánuco", "11": "Ica", "12": "Junín",
    "13": "La Libertad", "14": "Lambayeque", "15": "Lima", "16": "Loreto",
    "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes", "25": "Ucayali",
}

parser = argparse.ArgumentParser(description="Grafica la pobreza de la ENAHO")
parser.add_argument("--por", required=True, choices=list(NOMBRE_GRUPO))
parser.add_argument("--anio", type=int, default=2024)
parser.add_argument("--indicador", default="pobre", choices=list(NOMBRE_INDICADOR))
argumentos = parser.parse_args()
por = argumentos.por
anio = argumentos.anio
indicador = argumentos.indicador

# El territorio sale de la base de hogares, que replica la cifra del INEI.
# Sexo y edad solo existen por persona, así que salen de la base de personas.
if por in ["area", "dominio", "departamento"]:
    ruta_base = CARPETA_SALIDAS / f"hogares_{anio}.parquet"
    factor = "factor_personas"
else:
    ruta_base = CARPETA_SALIDAS / f"personas_{anio}.parquet"
    factor = "facpob07"

if not ruta_base.exists():
    raise SystemExit(f"No existe {ruta_base}. Usa primero la skill limpiando-enaho.")

datos = pd.read_parquet(ruta_base)

# Cada fila recibe el nombre del grupo al que pertenece.
if por == "area":
    datos["grupo"] = datos["urbano"].map({True: "Urbano", False: "Rural"})
elif por == "dominio":
    datos["grupo"] = datos["dominio"].map(NOMBRES_DOMINIO)
elif por == "departamento":
    datos["grupo"] = datos["departamento"].map(NOMBRES_DEPARTAMENTO)
elif por == "sexo":
    datos["grupo"] = datos["p207"].map({1: "Hombres", 2: "Mujeres"})
elif por == "edad":
    datos["grupo"] = pd.cut(
        datos["p208a"],
        bins=[0, 15, 30, 45, 65, 200],
        labels=["0 a 14", "15 a 29", "30 a 44", "45 a 64", "65 y más"],
        right=False,
    )

# Tasa ponderada: personas pobres que representa cada grupo entre todas las que representa.
datos["peso_pobre"] = datos[factor] * datos[indicador]
sumas = datos.groupby("grupo", observed=True)[["peso_pobre", factor]].sum()
tasa = sumas["peso_pobre"] / sumas[factor] * 100

# matplotlib dibuja la primera barra abajo. Ordenamos para que la mayor quede
# arriba; la edad conserva su orden natural, de los más jóvenes a los mayores.
if por == "edad":
    tasa = tasa.sort_index(ascending=False)
else:
    tasa = tasa.sort_values()

figura, ejes = plt.subplots(figsize=(8, 1.2 + 0.35 * len(tasa)))
barras = ejes.barh(tasa.index.astype(str), tasa.values, color=COLOR, height=0.6)
ejes.bar_label(barras, fmt="%.1f %%", padding=4, fontsize=9)

# Las barras empiezan en cero; el 15 % extra deja espacio para el valor escrito.
ejes.set_xlim(0, tasa.max() * 1.15)

# Con el valor en cada barra, el eje x y los bordes solo estorban.
ejes.spines[["top", "right", "bottom"]].set_visible(False)
ejes.spines["left"].set_color("#999999")
ejes.tick_params(axis="x", bottom=False, labelbottom=False)
ejes.tick_params(axis="y", length=0)

ejes.set_title(
    f"{NOMBRE_INDICADOR[indicador]} por {NOMBRE_GRUPO[por]}, {anio}",
    loc="left", fontweight="bold",
)
ejes.annotate(
    f"Fuente: INEI, ENAHO {anio}. Porcentaje de personas, ponderado con {factor}.",
    xy=(0, 0), xycoords="axes fraction", xytext=(0, -12), textcoords="offset points",
    fontsize=8, color="#555555", va="top",
)

CARPETA_FIGURAS.mkdir(exist_ok=True)
ruta_figura = CARPETA_FIGURAS / f"{indicador}_por_{por}_{anio}.png"
figura.savefig(ruta_figura, dpi=200, bbox_inches="tight")

# astype(float): los factores vienen en float32, que imprime 39.299999 en vez de 39.3.
print(tasa.astype(float).sort_values(ascending=False).round(1).to_string())
print(f"Guardado: {ruta_figura}")

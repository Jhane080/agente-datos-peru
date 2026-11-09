"""Cruza la ENAHO de dos años con el Censo 2017 y deja los indicadores del informe.

Lee:
  salidas/hogares_<año>.parquet           base limpia de cada año (skill limpiando-enaho)
  datos/*-Modulo34/sumaria-<año>.dta      la línea de pobreza de cada año
  salidas/redatam/agua_departamento.csv   viviendas sin red pública (herramienta consultar_redatam), opcional
Deja:
  salidas/indicadores.csv                              todas las cifras, en formato largo
  figuras/cambio_pobreza_departamento_<a>_<b>.png      cambio de la pobreza en puntos porcentuales

Uso:  uv run cruzar.py --desde 2019 --hasta 2024
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventanas: solo guardamos el PNG
import matplotlib.pyplot as plt
import pandas as pd

CARPETA_DATOS = Path("datos")
CARPETA_SALIDAS = Path("salidas")
CARPETA_FIGURAS = Path("figuras")
RUTA_CENSO = CARPETA_SALIDAS / "redatam" / "agua_departamento.csv"
COLOR_SUBE = "#B5451B"
COLOR_BAJA = "#999999"

NOMBRES_DEPARTAMENTO = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa",
    "05": "Ayacucho", "06": "Cajamarca", "07": "Callao", "08": "Cusco",
    "09": "Huancavelica", "10": "Huánuco", "11": "Ica", "12": "Junín",
    "13": "La Libertad", "14": "Lambayeque", "15": "Lima", "16": "Loreto",
    "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes", "25": "Ucayali",
}

parser = argparse.ArgumentParser(description="Cruza la ENAHO de dos años con el Censo 2017")
parser.add_argument("--desde", type=int, default=2019)
parser.add_argument("--hasta", type=int, default=2024)
argumentos = parser.parse_args()
anios = [argumentos.desde, argumentos.hasta]


def tasa_por_grupo(datos, grupo, indicador):
    """Porcentaje de personas con el indicador en cada grupo, ponderado como el INEI."""
    datos = datos.assign(peso=datos["factor_personas"] * datos[indicador])
    sumas = datos.groupby(grupo, observed=True)[["peso", "factor_personas"]].sum()
    return (sumas["peso"] / sumas["factor_personas"] * 100).astype(float)


filas = []


def agregar(indicador, ambito, codigo, nombre, anio, valor, unidad, fuente):
    filas.append({"indicador": indicador, "ambito": ambito, "codigo": codigo, "nombre": nombre,
                  "anio": str(anio), "valor": round(float(valor), 2), "unidad": unidad, "fuente": fuente})


# 1. Pobreza de cada año: nacional, por área y por departamento --------------
pobreza_departamento = {}
for anio in anios:
    ruta = CARPETA_SALIDAS / f"hogares_{anio}.parquet"
    if not ruta.exists():
        raise SystemExit(f"No existe {ruta}. Usa primero la skill limpiando-enaho con el año {anio}.")
    hogares = pd.read_parquet(ruta)
    hogares["nacional"] = "Perú"
    hogares["area"] = hogares["urbano"].map({True: "Urbano", False: "Rural"})
    fuente = f"INEI, ENAHO {anio}"

    for indicador, nombre_indicador in [("pobre", "pobreza_monetaria"), ("pobre_extremo", "pobreza_extrema")]:
        nacional = tasa_por_grupo(hogares, "nacional", indicador)
        agregar(nombre_indicador, "nacional", "00", "Perú", anio, nacional["Perú"], "% de personas", fuente)
        for area, valor in tasa_por_grupo(hogares, "area", indicador).items():
            agregar(nombre_indicador, "area", area.lower(), area, anio, valor, "% de personas", fuente)

    por_departamento = tasa_por_grupo(hogares, "departamento", "pobre")
    pobreza_departamento[anio] = por_departamento
    for codigo, valor in por_departamento.items():
        agregar("pobreza_monetaria", "departamento", codigo, NOMBRES_DEPARTAMENTO[codigo], anio, valor,
                "% de personas", fuente)

# 2. Línea de pobreza: lo que cuesta la canasta básica por persona al mes ----
# La sumaria la trae por hogar (cambia según el dominio); la promediamos por persona.
for anio in anios:
    rutas = list(CARPETA_DATOS.glob(f"*-Modulo34/sumaria-{anio}.dta"))
    if not rutas:
        raise SystemExit(f"Falta la sumaria de {anio} en datos/. Usa primero la skill descargando-enaho.")
    sumaria = pd.read_stata(rutas[0], convert_categoricals=False)
    sumaria.columns = sumaria.columns.str.lower()
    personas = sumaria["factor07"] * sumaria["mieperho"]
    for columna, nombre_indicador in [("linea", "linea_pobreza"), ("linpe", "linea_pobreza_extrema")]:
        promedio = (sumaria[columna] * personas).sum() / personas.sum()
        agregar(nombre_indicador, "nacional", "00", "Perú", anio, promedio, "soles por persona al mes",
                f"INEI, ENAHO {anio}, sumaria")

# 3. Cambio entre los dos años, por departamento ------------------------------
desde, hasta = anios
cambio = (pobreza_departamento[hasta] - pobreza_departamento[desde]).sort_values()
periodo = f"{desde}-{hasta}"
for codigo, valor in cambio.items():
    agregar("cambio_pobreza_monetaria", "departamento", codigo, NOMBRES_DEPARTAMENTO[codigo], periodo, valor,
            "puntos porcentuales", f"INEI, ENAHO {desde} y {hasta}")

# 4. Censo 2017: viviendas sin red pública de agua (si ya se consultó REDATAM) -
if RUTA_CENSO.exists():
    # dtype=str: el código del departamento es "01", no 1
    censo = pd.read_csv(RUTA_CENSO, dtype={"Código": str})
    censo["pct_sin_red"] = censo["SINRED"] / censo["CONDATO"] * 100
    censo = censo.set_index("Código")
    for codigo, valor in censo["pct_sin_red"].items():
        agregar("viviendas_sin_red_publica_agua", "departamento", codigo, NOMBRES_DEPARTAMENTO[codigo], 2017,
                valor, "% de viviendas", "INEI, Censos Nacionales 2017, REDATAM")

    # ¿Los departamentos con menos acceso a agua son los más pobres? Correlación entre los 25
    correlacion_nivel = censo["pct_sin_red"].corr(pobreza_departamento[hasta])
    correlacion_cambio = censo["pct_sin_red"].corr(cambio)
    agregar("correlacion_sin_red_vs_pobreza", "departamentos", "25", "25 departamentos", hasta,
            correlacion_nivel, "coeficiente de Pearson", "Censo 2017 y ENAHO")
    agregar("correlacion_sin_red_vs_cambio_pobreza", "departamentos", "25", "25 departamentos", periodo,
            correlacion_cambio, "coeficiente de Pearson", "Censo 2017 y ENAHO")
else:
    print(f"Aviso: no existe {RUTA_CENSO}; el cruce con el Censo 2017 queda fuera.")

indicadores = pd.DataFrame(filas)
CARPETA_SALIDAS.mkdir(exist_ok=True)
indicadores.to_csv(CARPETA_SALIDAS / "indicadores.csv", index=False, encoding="utf-8")

# 5. Gráfico: cuánto cambió la pobreza en cada departamento --------------------
nombres = [NOMBRES_DEPARTAMENTO[codigo] for codigo in cambio.index]
colores = [COLOR_SUBE if valor > 0 else COLOR_BAJA for valor in cambio.values]

figura, ejes = plt.subplots(figsize=(8, 1.2 + 0.35 * len(cambio)))
barras = ejes.barh(nombres, cambio.values, color=colores, height=0.6)
ejes.bar_label(barras, fmt="%+.1f", padding=4, fontsize=9)
ejes.axvline(0, color="#555555", linewidth=0.8)

# Con el valor en cada barra, el eje x y los bordes solo estorban
ejes.spines[["top", "right", "bottom", "left"]].set_visible(False)
ejes.tick_params(axis="x", bottom=False, labelbottom=False)
ejes.tick_params(axis="y", length=0)
margen = max(abs(cambio.min()), abs(cambio.max())) * 1.2
ejes.set_xlim(min(0, cambio.min()) - margen * 0.15, cambio.max() + margen * 0.15)

ejes.set_title(f"Cambio en la pobreza monetaria por departamento, {desde}–{hasta}",
               loc="left", fontweight="bold")
ejes.annotate(
    f"Fuente: INEI, ENAHO {desde} y {hasta}. Puntos porcentuales de personas pobres, ponderado con factor07 × mieperho.",
    xy=(0, 0), xycoords="axes fraction", xytext=(0, -12), textcoords="offset points",
    fontsize=8, color="#555555", va="top",
)

CARPETA_FIGURAS.mkdir(exist_ok=True)
ruta_figura = CARPETA_FIGURAS / f"cambio_pobreza_departamento_{desde}_{hasta}.png"
figura.savefig(ruta_figura, dpi=200, bbox_inches="tight")

# Lo que imprime es lo que la skill le muestra al usuario
resumen = indicadores[indicadores["ambito"].isin(["nacional", "area", "departamentos"])]
print(resumen[["indicador", "nombre", "anio", "valor", "unidad"]].to_string(index=False))
print()
print(f"Cambio {periodo} por departamento (puntos porcentuales), de mayor a menor:")
print(cambio.sort_values(ascending=False).rename(NOMBRES_DEPARTAMENTO).round(1).to_string())
print()
print(f"Guardado: {CARPETA_SALIDAS / 'indicadores.csv'} y {ruta_figura}")

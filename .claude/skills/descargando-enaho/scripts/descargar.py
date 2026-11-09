"""Descarga la ENAHO anual del portal de microdatos del INEI.

Baja el módulo 34 (sumaria, una fila por hogar) y el módulo 02 (miembros,
una fila por persona) en formato Stata y los descomprime en datos/.

Uso:  uv run descargar.py --anio 2024
"""

import argparse
import re
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

PORTAL = "https://proyectos.inei.gob.pe/microdatos"
DESCARGAS = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA"
CARPETA_DATOS = Path("datos")

parser = argparse.ArgumentParser(description="Descarga la ENAHO anual del INEI")
parser.add_argument("--anio", type=int, required=True)
anio = parser.parse_args().anio

# El INEI no numera las descargas por año sino por un código de encuesta
# (2024 es 966). Le hacemos al portal el mismo pedido que hace la página
# cuando uno elige "Condiciones de Vida y Pobreza - ENAHO", el año y "Anual".
formulario = urllib.parse.urlencode({
    "bandera": 1,
    "_cmbEncuesta": "Condiciones de Vida y Pobreza - ENAHO",
    "_cmbAnno": anio,
    "_cmbTrimestre": 55,  # 55 es el periodo "Anual - (Ene-Dic)"
}).encode()

with urllib.request.urlopen(f"{PORTAL}/cambiaPeriodo.asp", data=formulario) as respuesta:
    pagina = respuesta.read().decode("latin-1")

codigos = re.findall(r"STATA/(\d+)-Modulo34\.zip", pagina)
if not codigos:
    raise SystemExit(f"El INEI todavía no publica la ENAHO anual {anio}.")

codigo = codigos[0]
print(f"ENAHO {anio}: código {codigo} en el portal del INEI")

# Cada zip trae además diccionarios en PDF y tablas auxiliares.
# La sumaria también trae una versión "-12g" (12 grupos de gasto) que no usamos.
ARCHIVO_PRINCIPAL = {
    "34": f"sumaria-{anio}.dta",
    "02": f"enaho01-{anio}-200.dta",
}

CARPETA_DATOS.mkdir(exist_ok=True)

for modulo, nombre_dta in ARCHIVO_PRINCIPAL.items():
    nombre_zip = f"{codigo}-Modulo{modulo}.zip"
    ruta_zip = CARPETA_DATOS / nombre_zip

    # Si ya está bajado y completo no lo volvemos a pedir; una descarga
    # cortada a medias no pasa esta prueba y se baja de nuevo.
    if not zipfile.is_zipfile(ruta_zip):
        print(f"Bajando {nombre_zip}...")
        urllib.request.urlretrieve(f"{DESCARGAS}/{nombre_zip}", ruta_zip)

    with zipfile.ZipFile(ruta_zip) as archivo_zip:
        archivo_zip.extractall(CARPETA_DATOS)

    ruta_dta = CARPETA_DATOS / f"{codigo}-Modulo{modulo}" / nombre_dta
    if not ruta_dta.exists():
        raise SystemExit(f"{nombre_zip} no trae {nombre_dta}. Revisen el zip a mano.")

    print(f"Listo: {ruta_dta}")

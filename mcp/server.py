"""Servidor MCP con datos oficiales del Perú: series del BCRP, microdatos del INEI y el Censo 2017 en REDATAM.

    uv run pytest                    # el contrato: 10 pruebas (las 8 de la sesión 04 y 2 propias)
    uv run mcp/server.py             # el servidor, por stdio (Claude Code lo levanta desde .mcp.json)

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
"""
import html
import re
import time
import unicodedata
import urllib.parse
import zipfile
from functools import cache
from pathlib import Path

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
CATALOGO = RAIZ / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("peru", instructions=(
    "Datos oficiales del Perú en tres fuentes. (1) BCRP: busca el código con buscar_series; luego usa resumen para "
    "variaciones, promedios y extremos, y serie para los datos; cita el código de la serie y el periodo. "
    "(2) Microdatos del INEI: encuestas_inei -> modulos_inei -> descargar_modulo_inei; las cifras de una encuesta "
    "siempre van ponderadas con su factor de expansión. (3) Censo 2017: variables_redatam para ver qué hay y "
    "consultar_redatam para correr un programa REDATAM en el servidor del INEI. No calcules a mano. "
    "Los ubigeos son texto de 6 dígitos: '010101', no 10101."))


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# Los meses mensuales llegan como "Sep.2026" y los diarios como "30.Set.26": aceptamos las dos formas.
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "set": 9,
         "oct": 10, "nov": 11, "dic": 12}


def _fecha_api(fecha, frecuencia, al_final):
    """Pasa "2025", "2025-01", "2025-01-15" o "2025-T1" al formato que pide la API para esa frecuencia.

    al_final=True toma el último día del periodo (para «hasta»): "2025-03" en una serie diaria llega al 31 de marzo.
    """
    periodo = pd.Period(fecha.upper().replace("-T", "Q"))
    dia = periodo.end_time if al_final else periodo.start_time
    if frecuencia == "Diaria":
        return dia.strftime("%Y-%m-%d")
    if frecuencia == "Mensual":
        return f"{dia.year}-{dia.month}"
    if frecuencia == "Trimestral":
        return f"{dia.year}-{dia.quarter}"
    return str(dia.year)


def _anio(dos_digitos):
    # los diarios y trimestrales traen el año con dos dígitos; las series diarias empiezan en los noventa
    return ("19" if dos_digitos > "50" else "20") + dos_digitos


def _periodo(nombre):
    """ "Ene.2025" -> "2025-01", "01.Oct.26" -> "2026-10-01", "T1.25" -> "2025-T1", "2025" -> "2025"."""
    partes = nombre.split(".")
    if len(partes) == 1:
        return nombre
    if len(partes) == 3:
        dia, mes, anio = partes
        return f"{_anio(anio)}-{MESES[mes.lower()]:02d}-{dia}"
    a, b = partes
    if a.startswith("T"):
        return f"{_anio(b)}-{a}"
    return f"{b}-{MESES[a.lower()]:02d}"


@cache
def _descargar(url):
    """Pide la URL a la API. Cuando la apuran, responde una página HTML en vez de JSON: esperamos y reintentamos."""
    for intento in range(4):
        r = httpx.get(url, timeout=60)
        try:
            return r.json()
        except ValueError:
            time.sleep(3 * (intento + 1))
    raise ToolError(f"El BCRP no respondió con datos para {url}. Esperen unos segundos y reintenten.")


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Datos de una serie del BCRP entre dos fechas, ambas incluidas. Úsenla cuando necesiten los valores uno por uno.

    Fechas: "2025" (anual), "2025-01" (mensual), "2025-T1" (trimestral) o "2025-01-15" (diaria); sirve cualquier
    formato para cualquier serie: "2026-10" en una serie diaria trae todo octubre. Ejemplo: codigo="PN01273PM",
    desde="2025-01", hasta="2025-12". Para variaciones, promedios o extremos usen resumen, no cuenten a mano.
    Devuelve el nombre, la frecuencia, los datos como [{"periodo", "valor"}] y la URL de la fuente.
    """
    ficha = _ficha(codigo)
    frecuencia = ficha["frecuencia"]
    url = f"{API}/{codigo}/json/{_fecha_api(desde, frecuencia, False)}/{_fecha_api(hasta, frecuencia, True)}"
    respuesta = _descargar(url)
    datos = []
    for p in respuesta.get("periods", []):
        valor = p["values"][0]
        if valor != "n.d.":
            datos.append({"periodo": _periodo(p["name"]), "valor": round(float(valor), 4)})
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": frecuencia, "datos": datos, "fuente": url}


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Las cuentas de una serie del BCRP entre dos fechas: úsenla siempre que pregunten cuánto subió, bajó o promedió.

    Mismas fechas que serie. Ejemplo: codigo="PN01273PM", desde="2025-12", hasta="2026-09".
    Devuelve primero y ultimo (con su periodo), cambio (ultimo - primero, en la unidad de la serie: si la serie ya
    está en %, son puntos porcentuales), variacion_pct (cambio relativo en %), promedio, maximo y minimo con su
    periodo, y la URL de la fuente.
    """
    s = serie(codigo, desde, hasta)
    datos = s["datos"]
    if not datos:
        raise ToolError(f"La serie {codigo} no tiene datos entre {desde} y {hasta}. Revisen su fecha de inicio.")
    tabla = pd.DataFrame(datos)
    primero = datos[0]
    ultimo = datos[-1]
    cambio = ultimo["valor"] - primero["valor"]
    return {"codigo": codigo, "nombre": s["nombre"], "frecuencia": s["frecuencia"], "n": len(datos),
            "primero": primero, "ultimo": ultimo, "cambio": round(cambio, 4),
            "variacion_pct": round(100 * cambio / primero["valor"], 2) if primero["valor"] else None,
            "promedio": round(tabla.valor.mean(), 4),
            "maximo": datos[tabla.valor.idxmax()], "minimo": datos[tabla.valor.idxmin()],
            "fuente": s["fuente"]}


COLORES_GRAFICO = ["#B5451B", "#555555", "#2F6B8A", "#8C8C3A"]


@mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": True})
def graficar_series(codigos: list[str], desde: str, hasta: str, titulo: str, archivo: str) -> dict:
    """Grafica una o varias series del BCRP en líneas y guarda el PNG en figuras/ y los datos en salidas/.

    Úsenla para el gráfico del BCRP de un informe. Mismas fechas que serie. Ejemplo: codigos=["PN09822PM",
    "PN01273PM"], desde="2019-01", hasta="2024-12", titulo="Inflación de alimentos y general, Lima (var. % 12 meses)",
    archivo="inflacion_2019_2024". Conviene juntar solo series con la misma unidad. Devuelve las rutas del PNG y del
    CSV, y por serie su nombre y su máximo con el periodo, para citarlos en el texto.
    """
    import matplotlib

    matplotlib.use("Agg")  # sin ventanas: solo guardamos el PNG
    import matplotlib.pyplot as plt

    archivo = re.sub(r"[^\w-]", "_", archivo)
    figura, ejes = plt.subplots(figsize=(9, 4.5))
    tablas = []
    resumenes = []
    for posicion, codigo in enumerate(codigos):
        s = serie(codigo, desde, hasta)
        tabla = pd.DataFrame(s["datos"])
        tabla["codigo"] = codigo
        tabla["nombre"] = s["nombre"]
        tablas.append(tabla)
        etiqueta = s["nombre"].split(" - ")[-1]
        ejes.plot(range(len(tabla)), tabla["valor"], color=COLORES_GRAFICO[posicion % 4], linewidth=2,
                  label=f"{etiqueta} ({codigo})")
        maximo = tabla.loc[tabla["valor"].idxmax()]
        resumenes.append({"codigo": codigo, "nombre": s["nombre"],
                          "maximo": {"periodo": maximo["periodo"], "valor": maximo["valor"]}})

    # El eje x muestra unas ocho fechas para que no se amontonen
    periodos = tablas[0]["periodo"].tolist()
    paso = max(1, len(periodos) // 8)
    ejes.set_xticks(range(0, len(periodos), paso))
    ejes.set_xticklabels(periodos[::paso], fontsize=8)
    ejes.axhline(0, color="#999999", linewidth=0.8)
    ejes.spines[["top", "right"]].set_visible(False)
    ejes.legend(frameon=False, fontsize=8)
    ejes.set_title(titulo, loc="left", fontweight="bold")
    ejes.annotate(f"Fuente: BCRP, series {', '.join(codigos)}.", xy=(0, 0), xycoords="axes fraction",
                  xytext=(0, -30), textcoords="offset points", fontsize=8, color="#555555", va="top")

    ruta_png = RAIZ / "figuras" / f"{archivo}.png"
    ruta_csv = RAIZ / "salidas" / f"{archivo}.csv"
    ruta_png.parent.mkdir(exist_ok=True)
    ruta_csv.parent.mkdir(exist_ok=True)
    figura.savefig(ruta_png, dpi=200, bbox_inches="tight")
    plt.close(figura)
    pd.concat(tablas).to_csv(ruta_csv, index=False, encoding="utf-8")
    return {"png": ruta_png.relative_to(RAIZ).as_posix(), "csv": ruta_csv.relative_to(RAIZ).as_posix(),
            "series": resumenes}


BANCO_MUNDIAL = "https://api.worldbank.org/v2/country/{paises}/indicator/{indicador}?format=json&date={desde}:{hasta}"


@mcp.tool(annotations=SOLO_LECTURA)
def comparar_paises(indicador: str = "NY.GDP.MKTP.KD.ZG", paises: list[str] | None = None,
                    desde: int = 2015, hasta: int = 2025) -> dict:
    """Compara al Perú con otros países con datos anuales del Banco Mundial. Úsenla cuando la pregunta compare
    países (el BCRP solo tiene datos del Perú) o pida el contexto regional de una cifra.

    indicador: código del Banco Mundial. Los más usados: "NY.GDP.MKTP.KD.ZG" (crecimiento del PBI real, %),
    "FP.CPI.TOTL.ZG" (inflación anual, %), "SL.UEM.TOTL.ZS" (desempleo, %), "NY.GDP.PCAP.CD" (PBI per cápita, US$),
    "SI.POV.DDAY" (pobreza extrema, %). paises: códigos ISO de tres letras; por defecto ["PER", "CHL", "COL", "MEX"].
    Ejemplo: indicador="FP.CPI.TOTL.ZG", paises=["PER", "BOL"], desde=2020, hasta=2025.
    Devuelve el nombre del indicador, los datos como [{"pais", "anio", "valor"}] y la URL de la fuente.
    """
    if paises is None:
        paises = ["PER", "CHL", "COL", "MEX"]
    url = BANCO_MUNDIAL.format(paises=";".join(paises), indicador=indicador, desde=desde, hasta=hasta)
    respuesta = httpx.get(url + "&per_page=1000", timeout=60).json()
    # si el indicador no existe, el Banco Mundial responde una sola pieza con el mensaje de error
    if len(respuesta) < 2 or respuesta[1] is None:
        raise ToolError(f"El Banco Mundial no tiene datos de {indicador!r} para {paises} entre {desde} y {hasta}.")
    datos = []
    for fila in respuesta[1]:
        if fila["value"] is not None:
            datos.append({"pais": fila["country"]["value"], "anio": int(fila["date"]), "valor": round(fila["value"], 4)})
    datos.sort(key=lambda d: (d["anio"], d["pais"]))
    return {"indicador": respuesta[1][0]["indicator"]["value"], "datos": datos, "fuente": url}


# ---------------------------------------------------------------------------------------------------------------------
# Microdatos del INEI: el portal no tiene API, pero sus menús son pedidos POST que se pueden repetir desde Python.
# El orden es siempre el mismo que en la página: encuesta -> año -> periodo -> módulos.
# ---------------------------------------------------------------------------------------------------------------------
PORTAL_INEI = "https://proyectos.inei.gob.pe/microdatos"
DESCARGAS_INEI = "https://proyectos.inei.gob.pe/iinei/srienaho/descarga"
CARPETA_INEI = RAIZ / "datos" / "inei"
CABECERAS = {"User-Agent": "agente-datos-peru/0.1"}
FORMATOS_INEI = ("CSV", "STATA", "SPSS")


def _pedir_inei(pagina, campos=None):
    """El portal es ASP clásico: responde en latin-1 y espera los formularios codificados igual (como escape() de JS)."""
    url = f"{PORTAL_INEI}/{pagina}"
    if campos is None:
        r = httpx.get(url, headers=CABECERAS, timeout=60)
    else:
        cuerpo = urllib.parse.urlencode(campos, encoding="latin-1")
        r = httpx.post(url, content=cuerpo, timeout=60,
                       headers={**CABECERAS, "Content-Type": "application/x-www-form-urlencoded"})
    r.raise_for_status()
    return r.content.decode("latin-1")


def _texto_html(fragmento):
    return html.unescape(re.sub(r"<[^>]+>", "", fragmento)).replace("\xa0", " ").strip()


def _opciones(pagina, nombre_select):
    """Las opciones (valor, texto) de un <select name=...> de la página."""
    bloque = re.search(rf"<select[^>]*name=['\"]?{nombre_select}\b[^>]*>(.*?)</select>", pagina, flags=re.S | re.I)
    if bloque is None:
        return []
    pares = re.findall(r"<option[^>]*value=['\"]?([^'\">]*)['\"]?[^>]*>(.*?)</option>", bloque.group(1),
                       flags=re.S | re.I)
    return [(valor.strip(), _texto_html(texto)) for valor, texto in pares if valor.strip()]


@cache
def _encuestas():
    pagina = _pedir_inei("Consulta_por_Encuesta.asp?CU=19558")
    nombres = []
    for select in ["cmbEncuesta0", "cmbEncuestaA", "cmbEncuestaN", "cmbEncuesta_EPE"]:
        for valor, _ in _opciones(pagina, select):
            # 1, 2 y 3 no son encuestas: abren las listas de la ENAHO y la EPE, que vienen en los otros menús
            if valor not in ("1", "2", "3") and valor not in nombres:
                nombres.append(valor)
    return nombres


@mcp.tool(annotations=SOLO_LECTURA)
def encuestas_inei(texto: str = "") -> list[str]:
    """Lista las encuestas, censos y registros del portal de microdatos del INEI (unas 60).

    texto filtra por palabras, sin importar tildes ni mayúsculas. Ejemplos: "agropecuaria", "endes", "enaho",
    "renamu", "empleo", "victimizacion". Devuelve los nombres exactos que piden modulos_inei y descargar_modulo_inei.
    La ENAHO anual de pobreza es "Condiciones de Vida y Pobreza - ENAHO".
    """
    palabras = _sin_tildes(texto).split()
    encontradas = []
    for nombre in _encuestas():
        if all(palabra in _sin_tildes(nombre) for palabra in palabras):
            encontradas.append(nombre)
    return encontradas


def _modulos(pagina):
    modulos = []
    for fila in re.findall(r"<tr[^>]*>(.*?)</tr>", pagina, flags=re.S | re.I):
        celdas = [_texto_html(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", fila, flags=re.S | re.I)]
        celdas = [c for c in celdas if c]
        # Nro | Año | Período | Código Encuesta | Encuesta | Código Módulo | Módulo
        if len(celdas) >= 7 and celdas[0].isdigit() and celdas[3].isdigit() and celdas[5].isdigit():
            modulos.append({"codigo_encuesta": celdas[3], "codigo_modulo": celdas[5], "modulo": celdas[6]})
    return modulos


@mcp.tool(annotations=SOLO_LECTURA)
def modulos_inei(encuesta: str, anio: int, periodo: str | None = None) -> dict:
    """Módulos de una encuesta del INEI para un año, con los códigos que pide descargar_modulo_inei.

    encuesta: el nombre exacto que devuelve encuestas_inei. Ejemplo: encuesta="ENCUESTA NACIONAL AGROPECUARIA",
    anio=2025. Si ese año tiene varios periodos (trimestres, meses, "Anual") y no dicen cuál, devuelve la lista de
    periodos para que elijan: vuelvan a llamar con periodo=<codigo> o con parte del nombre ("Anual").
    Devuelve el código de la encuesta en el portal y, por módulo, su código y su nombre.
    """
    pagina = _pedir_inei("CambiaEnc.asp", {"bandera": 1, "_cmbEncuesta": encuesta})
    anios = [valor for valor, _ in _opciones(pagina, "cmbAnno")]
    if str(anio) not in anios:
        raise ToolError(f"{encuesta!r} no tiene datos de {anio}. Años disponibles: {anios}. "
                        "Si la lista está vacía, revisen el nombre exacto con encuestas_inei.")

    pagina = _pedir_inei("CambiaAnio.asp", {"bandera": 1, "_cmbEncuesta": encuesta, "_cmbAnno": anio,
                                            "_cmbEncuesta0": encuesta})
    periodos = [{"codigo": valor, "nombre": texto} for valor, texto in _opciones(pagina, "cmbTrimestre")]
    elegido = None
    for p in periodos:
        if periodo is None and len(periodos) == 1:
            elegido = p
        elif periodo is not None and (periodo == p["codigo"] or _sin_tildes(periodo) in _sin_tildes(p["nombre"])):
            elegido = p
            break
    if elegido is None:
        return {"encuesta": encuesta, "anio": anio, "periodos": periodos,
                "aviso": "Elijan un periodo y vuelvan a llamar con periodo=<codigo>."}

    pagina = _pedir_inei("cambiaPeriodo.asp", {"bandera": 1, "_cmbEncuesta": encuesta, "_cmbAnno": anio,
                                               "_cmbTrimestre": elegido["codigo"]})
    modulos = _modulos(pagina)
    if not modulos:
        raise ToolError(f"El portal no devolvió módulos para {encuesta!r}, {anio}, periodo {elegido['nombre']}.")
    formatos = sorted(set(re.findall(r"descarga/([A-Za-z]+)/\d+-Modulo", pagina)))
    return {"encuesta": encuesta, "anio": anio, "periodo": elegido, "codigo_encuesta": modulos[0]["codigo_encuesta"],
            "formatos": formatos, "modulos": [{"codigo_modulo": m["codigo_modulo"], "modulo": m["modulo"]}
                                              for m in modulos]}


@mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": True})
def descargar_modulo_inei(codigo_encuesta: str, codigo_modulo: str, formato: str = "CSV") -> dict:
    """Baja un módulo del portal de microdatos del INEI y lo descomprime en datos/inei/<formato>/.

    Los códigos salen de modulos_inei. formato: "CSV", "STATA" o "SPSS". Ejemplo: codigo_encuesta="1036",
    codigo_modulo="1893" (ENA 2025, características de la unidad agropecuaria). Si el zip ya está, no lo vuelve a
    bajar. Devuelve la carpeta, cada archivo con su tamaño en MB y la URL de la fuente. Al leer los CSV, lean los
    códigos geográficos como texto (dtype=str) para no perder el cero de la izquierda.
    """
    if not (codigo_encuesta.isdigit() and codigo_modulo.isdigit()):
        raise ToolError("Los códigos son números, por ejemplo codigo_encuesta='1036' y codigo_modulo='1893'.")
    formato = formato.upper()
    if formato not in FORMATOS_INEI:
        raise ToolError(f"formato debe ser uno de {FORMATOS_INEI}.")

    nombre = f"{codigo_encuesta}-Modulo{codigo_modulo}"
    carpeta = CARPETA_INEI / formato.lower()
    ruta_zip = carpeta / f"{nombre}.zip"
    url = f"{DESCARGAS_INEI}/{formato}/{nombre}.zip"

    # Una descarga cortada a medias no pasa is_zipfile y se vuelve a pedir
    if not zipfile.is_zipfile(ruta_zip):
        carpeta.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", url, headers=CABECERAS, timeout=600, follow_redirects=True) as r:
            if r.status_code != 200:
                raise ToolError(f"El INEI no tiene {url} (HTTP {r.status_code}). Revisen los códigos con modulos_inei.")
            with open(ruta_zip, "wb") as archivo:
                for trozo in r.iter_bytes():
                    archivo.write(trozo)
        if not zipfile.is_zipfile(ruta_zip):
            ruta_zip.unlink()
            raise ToolError(f"Lo que devolvió {url} no es un zip. Revisen los códigos con modulos_inei.")

    archivos = []
    with zipfile.ZipFile(ruta_zip) as contenido:
        contenido.extractall(carpeta)
        for info in contenido.infolist():
            if not info.is_dir():
                ruta = (carpeta / info.filename).relative_to(RAIZ).as_posix()
                archivos.append({"archivo": ruta, "mb": round(info.file_size / 1e6, 1)})
    return {"carpeta": (carpeta / nombre).relative_to(RAIZ).as_posix(), "archivos": archivos, "fuente": url}


# ---------------------------------------------------------------------------------------------------------------------
# Censo 2017 en REDATAM: el «Procesador Estadístico En-línea» del INEI acepta programas REDATAM por un formulario.
# El servidor hace el cálculo sobre los 29 millones de personas y devuelve la tabla en HTML.
# ---------------------------------------------------------------------------------------------------------------------
REDATAM = "https://censos2017.inei.gob.pe/bininei/RpWebStats.exe"
CARPETA_REDATAM = RAIZ / "salidas" / "redatam"
NUMERO_REDATAM = re.compile(r"-?\d[\d ]*(,\d+)?%?")


def _pedir_redatam(url, campos=None):
    for intento in range(3):
        try:
            if campos is None:
                r = httpx.get(url, headers=CABECERAS, timeout=180)
            else:
                r = httpx.post(url, data=campos, headers=CABECERAS, timeout=180)
        except httpx.TransportError:
            time.sleep(3 * (intento + 1))
            continue
        if r.status_code == 200:
            return r.content.decode("utf-8", errors="replace").lstrip("﻿")
        if r.status_code == 500:
            # REDATAM explica el error en la página: «Identificador de variable desconocido [...] FOR clause»
            texto = re.sub(r"\s+", " ", _texto_html(r.content.decode("utf-8", errors="replace")))
            motivo = re.search(r"(N\S*mero de Error.*?)(RUNDEF|INL ItemID)", texto)
            detalle = motivo.group(1).strip() if motivo else "sin detalle"
            raise ToolError(f"REDATAM rechazó el programa: {detalle}. Revisen los nombres con variables_redatam "
                            "(respeten mayúsculas y minúsculas: Vivienda.C2P6) y las formas del ejemplo.")
        time.sleep(3 * (intento + 1))
    raise ToolError("El servidor REDATAM del INEI no respondió. Esperen unos segundos y reintenten.")


@cache
def _diccionario_redatam():
    pagina = _pedir_redatam(f"{REDATAM}/CmdSet?BASE=CPV2017DI&ITEM=PROGRED&lang=esp")
    entidades = {}
    variables = []
    for fila in re.findall(r"<tr[^>]*>(.*?)</tr>", pagina, flags=re.S | re.I):
        celdas = [_texto_html(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", fila, flags=re.S | re.I)]
        if len(celdas) < 8 or not re.fullmatch(r"\d+(\.\d+)?", celdas[0]):
            continue
        numero, nombre, rotulo, _, grupo, tipo, minimo, maximo = celdas[:8]
        if "." not in numero:
            # Tal cual: dentro de un FOR, REDATAM acepta Vivienda.C2P6 pero no VIVIENDA.C2P6
            entidades[numero] = nombre
            continue
        entidad = entidades[numero.split(".")[0]]
        variables.append({"variable": f"{entidad}.{nombre}", "rotulo": rotulo, "grupo": grupo, "tipo": tipo,
                          "rango": f"{minimo}-{maximo}" if minimo else ""})
    return variables


@mcp.tool(annotations=SOLO_LECTURA)
def variables_redatam(texto: str = "") -> list[dict]:
    """Variables del Censo 2017 que se pueden usar en consultar_redatam, con su nombre listo para el programa.

    texto filtra por palabras en el nombre, el rótulo o el grupo, sin importar tildes. Ejemplos: "agua", "sis",
    "lengua", "discapacidad", "area", "piso". Sin texto devuelve las ~130 variables. Los rótulos empiezan con
    V: (vivienda), H: (hogar) o P: (persona).
    """
    palabras = _sin_tildes(texto).split()
    encontradas = []
    for v in _diccionario_redatam():
        donde = _sin_tildes(f"{v['variable']} {v['rotulo']} {v['grupo']}")
        if all(palabra in donde for palabra in palabras):
            encontradas.append(v)
    return encontradas


def _es_numero(texto):
    return texto == "-" or NUMERO_REDATAM.fullmatch(texto) is not None


def _a_numero(texto):
    """'5 162 821' -> 5162821, '67,06%' -> 67.06, '-' (cero en REDATAM) -> 0."""
    if texto == "-":
        return 0
    limpio = texto.replace(" ", "").replace("%", "").replace(",", ".")
    return float(limpio) if "." in limpio else int(limpio)


def _tabla_redatam(pagina):
    filas = []
    for fila in re.findall(r"<tr>(.*?)</tr>", pagina, flags=re.S):
        celdas = [_texto_html(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", fila, flags=re.S)]
        celdas = [c for c in celdas if c]
        if celdas:
            filas.append(celdas)

    # Una fila de datos termina en un número; el encabezado es la fila justo antes de la primera de datos
    posiciones = [i for i, f in enumerate(filas) if len(f) >= 2 and _es_numero(f[-1])]
    if not posiciones:
        return None
    primera = posiciones[0]
    ancho = max(len(filas[i]) for i in posiciones)
    encabezado = filas[primera - 1] if primera > 0 else []
    if len(encabezado) == ancho - 1:
        encabezado = ["categoria"] + encabezado
    if len(encabezado) != ancho:
        encabezado = [f"columna_{j + 1}" for j in range(ancho)]
    columnas = []
    for nombre in encabezado:
        repetido = sum(1 for c in columnas if c == nombre or c.startswith(nombre + "_"))
        columnas.append(nombre if repetido == 0 else f"{nombre}_{repetido + 1}")

    tabla = pd.DataFrame([filas[i] for i in posiciones if len(filas[i]) == ancho], columns=columnas)
    # Una columna es numérica solo si todos sus valores lo son y ninguno empieza con cero: «010101» es un ubigeo
    for columna in tabla.columns:
        valores = tabla[columna]
        con_cero = valores.str.match(r"0\d").any()
        if valores.map(_es_numero).all() and not con_cero:
            tabla[columna] = valores.map(_a_numero)
    titulo = " · ".join(" ".join(f) for f in filas[:max(primera - 1, 0)])
    return titulo, tabla


@mcp.tool(annotations=SOLO_LECTURA)
def consultar_redatam(programa: str, nombre: str = "consulta", max_filas: int = 30) -> dict:
    """Corre un programa REDATAM sobre el Censo 2017 del INEI (población y vivienda) y devuelve la tabla.

    Entidades, de mayor a menor: PERU > Departam > Provinci > Distrito > Vivienda > Hogar > Poblacio. Las variables
    se escriben Entidad.VARIABLE, tal como las devuelve variables_redatam (Vivienda.VAREA, Poblacio.C5P81): dentro de
    un FOR, REDATAM distingue mayúsculas. Si el programa no empieza con RUNDEF, se le agrega
    "RUNDEF Job / SELECTION ALL". Formas que funcionan:

      TABLE T1 AS FREQUENCY OF Vivienda.C2P6                     (frecuencia nacional)
      TABLE T1 AS CROSSTABS OF Departam.NCCDD BY Vivienda.VAREA  (cruce por departamento)
      DEFINE Distrito.NPOB AS COUNT Poblacio TYPE INTEGER
      TABLE T1 AS AREALIST OF Distrito, Distrito.CCDI, Distrito.NCCDI, Distrito.NPOB   (una fila por distrito)
      DEFINE Departam.NSINRED AS COUNT Vivienda FOR Vivienda.C2P6 >= 3 TYPE INTEGER    (conteo con condición)

    AREALIST devuelve el ubigeo en la columna "Código" (2 dígitos por departamento, 6 por distrito), como texto: con
    él se cruza con la ENAHO, la ENA o un mapa. Son conteos del censo, sin factor de expansión. La tabla completa queda en salidas/redatam/<nombre>.csv;
    la respuesta trae las primeras max_filas. Devuelve por tabla el título, las columnas, el número de filas, las
    filas y la ruta del CSV.
    """
    if not programa.strip().upper().startswith("RUNDEF"):
        programa = "RUNDEF Job\n    SELECTION ALL\n\n" + programa
    pagina = _pedir_redatam(f"{REDATAM}/CmdSet?", {
        "MAIN": "WebServerMain.inl", "BASE": "CPV2017DI", "LANG": "esp", "CODIGO": "XXUSUARIOXX",
        "ITEM": "PROGRED", "MODE": "RUN", "CMDSET": programa, "Submit": "Ejecutar"})
    # El resultado no viene en la respuesta: viene un iframe que apunta a una tabla temporal por cada TABLE
    marcos = re.findall(r'<iframe src="([^"]+)"', pagina)
    if not marcos:
        mensaje = re.sub(r"\s+", " ", _texto_html(re.sub(r"<(script|style).*?</\1>", "", pagina, flags=re.S)))
        raise ToolError(f"REDATAM no devolvió tablas. Respuesta del servidor: {mensaje[:300]}")

    nombre = re.sub(r"[^\w-]", "_", nombre)
    CARPETA_REDATAM.mkdir(parents=True, exist_ok=True)
    tablas = []
    for numero, marco in enumerate(marcos, start=1):
        resultado = _tabla_redatam(_pedir_redatam(html.unescape(marco)))
        if resultado is None:
            continue
        titulo, tabla = resultado
        sufijo = "" if len(marcos) == 1 else f"_{numero}"
        ruta = CARPETA_REDATAM / f"{nombre}{sufijo}.csv"
        tabla.to_csv(ruta, index=False, encoding="utf-8")
        tablas.append({"titulo": titulo, "columnas": list(tabla.columns), "n_filas": len(tabla),
                       "filas": tabla.head(max_filas).to_dict(orient="records"),
                       "csv": ruta.relative_to(RAIZ).as_posix()})
    if not tablas:
        raise ToolError("REDATAM respondió, pero la tabla está vacía. Revisen que las variables y la entidad del "
                        "AREALIST o el CROSSTABS sean compatibles.")
    return {"tablas": tablas, "fuente": "INEI, Censos Nacionales 2017, REDATAM (censos2017.inei.gob.pe/redatam)"}


@mcp.resource("bcrp://serie/{codigo}")
def ficha(codigo: str) -> dict:
    """Ficha de una serie del BCRP: nombre, categoría, frecuencia, desde cuándo hay datos y última actualización."""
    return _ficha(codigo)


@mcp.prompt
def informe(tema: str) -> str:
    """Informe breve sobre un tema económico del Perú, con cada cifra verificable en el BCRP."""
    return (f"Escribe un informe de 5 viñetas sobre «{tema}» en el Perú. Busca las series con buscar_series y saca "
            "cada cifra de resumen o serie, sin calcular a mano. En cada viñeta cita el código de la serie y el "
            "periodo. Termina con una línea que diga qué no se puede concluir con estos datos.")


if __name__ == "__main__":
    mcp.run()

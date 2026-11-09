# Agente de datos del Perú

Agente de investigación socioeconómica con datos oficiales del Perú. Junta en Claude Code un servidor MCP con tres
fuentes (las series del **BCRP**, el portal de **microdatos del INEI** y el **Censo 2017 en REDATAM**) y cinco skills
que descargan, limpian, grafican, mapean y cruzan la **ENAHO**. Cada cifra sale de una herramienta que se puede volver
a correr, no de la memoria del modelo.

Tarea 4 del curso Python Intermedio (Data Science con Python, d2cml-ai).

![Cambio en la pobreza por departamento, 2019–2024](figuras/cambio_pobreza_departamento_2019_2024.png)

## La pregunta que responde

> ¿Por qué la pobreza monetaria de 2024 sigue por encima de la de 2019, y a qué departamentos golpeó más?

La respuesta completa está en [`informes/informe_final.md`](informes/informe_final.md). En corto:

- Entre diciembre de 2019 y diciembre de 2024 los alimentos subieron 31.9 % y el IPC general 23.9 % (BCRP). La línea
  de pobreza pasó de S/ 351.7 a S/ 454.4 por persona al mes.
- La pobreza pasó de 20.2 % a 27.6 %. El aumento fue urbano (de 14.6 % a 24.8 %); la pobreza rural bajó un poco
  (de 40.8 % a 39.3 %).
- Empeoraron sobre todo Callao (+19.5 puntos) y Lima (+12.9). La falta de agua por red pública del Censo 2017 se
  asocia con dónde la pobreza es alta (r = 0.52), no con dónde subió (r = 0.19).

## Cómo está armado

```
.mcp.json                     conecta el servidor "peru" a Claude Code
mcp/server.py                 el servidor MCP: BCRP, microdatos INEI y REDATAM
mcp/test_server.py            10 pruebas: las 8 de la sesión 04 y 2 propias
.claude/skills/               cinco skills (cuatro de la sesión 16 y una propia)
evaluacion/                   10 preguntas, el script que las corre y los resultados
informes/                     informe final y la respuesta del agente
salidas/ figuras/ mapas/      lo que producen las herramientas
evidencias_ia/                la corrida del agente y el historial con la IA
datos/                        microdatos crudos (no se suben: .gitignore)
```

### El servidor MCP (`mcp/server.py`)

| Fuente | Herramienta | Qué hace |
|---|---|---|
| BCRP | `buscar_series` | Busca el código de una serie entre las 17 mil del catálogo |
| | `serie` | Los datos de una serie entre dos fechas |
| | `resumen` | Primero, último, cambio, variación, promedio, máximo y mínimo |
| | `graficar_series` **(propia)** | Gráfico de líneas en `figuras/` y los datos en `salidas/` |
| Banco Mundial | `comparar_paises` **(propia)** | Compara al Perú con otros países |
| Microdatos INEI | `encuestas_inei` **(propia)** | Las ~60 encuestas y censos del portal |
| | `modulos_inei` **(propia)** | Los módulos de una encuesta en un año, con sus códigos |
| | `descargar_modulo_inei` **(propia)** | Baja y descomprime un módulo en `datos/inei/` |
| Censo 2017 | `variables_redatam` **(propia)** | Las variables del censo, con el nombre listo para el programa |
| | `consultar_redatam` **(propia)** | Corre un programa REDATAM en el servidor del INEI y guarda la tabla |

Además tiene un *resource* (`bcrp://serie/{codigo}`, la ficha de una serie) y un *prompt* (`informe`).

El portal de microdatos y el REDATAM del INEI no tienen API. Las herramientas repiten los mismos pedidos que hace la
página web: elegir encuesta, año, periodo y módulo, o enviar un programa al «Procesador Estadístico En-línea». Dos
reglas de REDATAM que aprendimos con los errores del servidor: dentro de un `FOR` los nombres distinguen mayúsculas
(`Vivienda.C2P6`, no `VIVIENDA.C2P6`) y una variable nueva no puede pasar de 10 caracteres.

### Las skills (`.claude/skills/`)

| Skill | Recibe | Entrega |
|---|---|---|
| `descargando-enaho` | Un año | Los módulos 34 y 02 de la ENAHO en `datos/` |
| `limpiando-enaho` | Los `.dta` | `salidas/hogares_<año>.parquet`, `personas_<año>.parquet` y `validacion.txt` |
| `graficando-enaho` | La base limpia y un grupo | Barras en `figuras/` |
| `mapeando-enaho` | La base limpia | Mapa por departamento en `mapas/` |
| `cruzando-fuentes` **(propia)** | ENAHO de dos años y el censo (vía `consultar_redatam`) | `salidas/indicadores.csv` y el gráfico del cambio por departamento |

La limpieza valida contra la cifra oficial del INEI antes de entregar nada: 27.58 % en 2024 y 20.19 % en 2019, con
108,664 residentes habituales en 2024 ([`salidas/validacion.txt`](salidas/validacion.txt)).

## Evaluación

Diez preguntas con respuesta verificada (cuatro del BCRP, cuatro de la ENAHO y dos que combinan ambas), hechas a
Claude Code con y sin el MCP y las skills:

| Modo | Acierta | No sabe | Se equivoca |
|---|---|---|---|
| Sin herramientas (solo memoria) | 2 | 8 | 0 |
| Con el MCP y las skills | **10** | 0 | 0 |

Sin herramientas, el modelo casi siempre reconoció que no sabía. En tres preguntas adicionales sobre el censo y el
portal del INEI, la única vez que respondió de memoria se equivocó en 10 % sin dudar. El detalle, los límites y cómo
repetirla están en [`evaluacion/comparacion.md`](evaluacion/comparacion.md).

## Fuentes de datos

| Fuente | Enlace | Cómo se obtiene |
|---|---|---|
| ENAHO 2024, módulo 34 (sumaria) | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip | Skill `descargando-enaho` |
| ENAHO 2024, módulo 02 (miembros) | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip | Skill `descargando-enaho` |
| ENAHO 2019, módulos 34 y 02 (código 687) | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/687-Modulo34.zip | `descargar.py --anio 2019` |
| Límites departamentales | https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson | Skill `mapeando-enaho` (lo baja si falta) |
| Series del BCRP | https://estadisticas.bcrp.gob.pe/estadisticas/series/ | MCP `buscar_series`, `serie`, `resumen` |
| Censo 2017 (REDATAM) | https://censos2017.inei.gob.pe/redatam/ | MCP `consultar_redatam` |
| Portal de microdatos del INEI | https://proyectos.inei.gob.pe/microdatos/ | MCP `encuestas_inei`, `modulos_inei`, `descargar_modulo_inei` |

Los microdatos no están en el repositorio (`datos/` va en `.gitignore`): las skills los bajan la primera vez.

## Reproducir todo

```bash
uv sync                                                                  # dependencias
uv run pytest                                                            # 10 pruebas del MCP
uv run .claude/skills/descargando-enaho/scripts/descargar.py --anio 2024 # microdatos (también --anio 2019)
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024     # base limpia y validacion.txt
uv run .claude/skills/graficando-enaho/scripts/graficar.py --por area    # también sexo y departamento
uv run .claude/skills/mapeando-enaho/scripts/mapear.py --anio 2024       # mapa
uv run .claude/skills/cruzando-fuentes/scripts/cruzar.py --desde 2019 --hasta 2024  # indicadores.csv
uv run evaluacion/evaluar.py                                             # evaluación con y sin herramientas
```

El servidor MCP se conecta solo: `.mcp.json` declara `uv run mcp/server.py`, y Claude Code pide aprobarlo la primera
vez que se abre el proyecto. Para agregarlo a mano: `claude mcp add --scope project peru -- uv run mcp/server.py`.

## Un ejemplo de corrida completa

La pregunta de investigación se le dio al agente en una sola instrucción
([`evidencias_ia/pregunta_integrada.txt`](evidencias_ia/pregunta_integrada.txt)), con `salidas/`, `figuras/` y `mapas/`
vacíos. En 29 turnos y unos 2 minutos, Claude Code limpió la ENAHO 2019 y 2024 (`limpiando-enaho`), hizo los
gráficos y el mapa (`graficando-enaho`, `mapeando-enaho`), buscó y resumió las series del BCRP (`buscar_series`,
`resumen`), graficó la inflación (`graficar_series`), consultó el censo (`consultar_redatam`), cruzó todo
(`cruzando-fuentes`) y escribió [`informes/respuesta_agente.md`](informes/respuesta_agente.md). El registro completo
está en [`evidencias_ia/corrida_integrada.jsonl`](evidencias_ia/corrida_integrada.jsonl).

## Limitaciones y problemas encontrados

- **El portal de microdatos y REDATAM no tienen API.** Las herramientas imitan los formularios de la página; si el
  INEI los cambia, dejan de funcionar.
- **REDATAM tiene reglas que no están documentadas a la vista:** dentro de un `FOR` distingue mayúsculas y las
  variables nuevas no pueden pasar de 10 caracteres. `consultar_redatam` devuelve el mensaje de error del servidor
  para que el agente pueda corregirse.
- **Las skills personales tienen prioridad.** Si en la máquina hay skills con el mismo nombre en `~/.claude/skills/`,
  Claude Code usa esas (pasó en la corrida integrada; ver [`evidencias_ia/README.md`](evidencias_ia/README.md)).
- **Las cifras por departamento tienen márgenes de error amplios** y el análisis no calcula intervalos de confianza.
- **El IPC es de Lima Metropolitana** y el censo es de 2017. Las correlaciones entre 25 departamentos describen; no
  prueban causas.

## Evidencias del uso de IA

Todo está en [`evidencias_ia/`](evidencias_ia/): el historial de la conversación con Claude Code con la que se armó el
proyecto ([`historial_chat_ia.pdf`](evidencias_ia/historial_chat_ia.pdf)) y la corrida integrada del agente.

## Cómo usarlo

Necesitas [uv](https://docs.astral.sh/uv/) y [Claude Code](https://claude.com/claude-code).

```bash
git clone https://github.com/Jhane080/agente-datos-peru.git
cd agente-datos-peru
uv sync
uv run pytest
claude
```

Dentro de Claude, pide en tus palabras:

- «¿Cuánto subieron los alimentos desde 2019 según el BCRP?»
- «Haz un mapa de la pobreza 2024 por departamento»
- «¿Qué porcentaje de viviendas de Loreto no tenía agua por red pública en el censo?»
- «Baja el módulo de características del productor de la ENA 2025»

La primera vez, Claude Code pide aprobar el servidor `peru` de `.mcp.json`.

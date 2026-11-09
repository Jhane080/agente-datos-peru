# Referencia de la ENAHO limpia

## Por qué hay dos bases

La cifra oficial de pobreza del INEI se calcula con la sumaria, pesando cada
hogar por `factor07 × mieperho`. La base de personas solo tiene a los
residentes habituales (108,664 en 2024), que no son exactamente los
`mieperho` del hogar (109,842). Por eso la base de personas ponderada con
`facpob07` da 27.53 % y no 27.58 %.

- Pobreza por territorio: `hogares_<año>.parquet` con `factor_personas`. Replica al INEI.
- Pobreza por sexo o edad: `personas_<año>.parquet` con `facpob07`. Esas variables solo existen por persona.

## hogares_<año>.parquet (una fila por hogar)

| Columna | Qué es |
|---|---|
| `anio`, `mes` | Año y mes de la entrevista |
| `conglome`, `vivienda`, `hogar` | Llaves del hogar, texto |
| `ubigeo` | Distrito, texto de 6 dígitos |
| `departamento` | `ubigeo[:2]`, texto de 2 dígitos |
| `dominio` | Región geográfica, ver códigos abajo |
| `estrato` | Tamaño del centro poblado, 1 a 8 |
| `urbano` | `estrato <= 5` |
| `mieperho` | Miembros del hogar |
| `factor07` | Factor de expansión del hogar |
| `factor_personas` | `factor07 × mieperho`: cuántas personas representa el hogar |
| `pobreza` | 1 pobre extremo, 2 pobre no extremo, 3 no pobre |
| `pobre`, `pobre_extremo` | `pobreza <= 2` y `pobreza == 1` |

## personas_<año>.parquet (una fila por residente habitual)

Las mismas columnas del hogar, más:

| Columna | Qué es |
|---|---|
| `codperso` | Número de la persona dentro del hogar, texto |
| `p203` | Parentesco con el jefe del hogar |
| `p207` | Sexo: 1 hombre, 2 mujer |
| `p208a` | Edad en años cumplidos |
| `facpob07` | Factor de expansión de la persona |

## Códigos

**dominio:** 1 costa norte, 2 costa centro, 3 costa sur, 4 sierra norte,
5 sierra centro, 6 sierra sur, 7 selva, 8 Lima Metropolitana.

**p203 (parentesco):** 1 jefe o jefa, 2 esposo(a) o pareja, 3 hijo(a),
4 yerno o nuera, 5 nieto(a), 6 padres o suegros, 7 otros parientes,
8 trabajador del hogar, 9 pensionista, 10 otros no parientes, 11 hermano(a).

**departamento (`ubigeo[:2]`):**

| | | | | |
|---|---|---|---|---|
| 01 Amazonas | 02 Áncash | 03 Apurímac | 04 Arequipa | 05 Ayacucho |
| 06 Cajamarca | 07 Callao | 08 Cusco | 09 Huancavelica | 10 Huánuco |
| 11 Ica | 12 Junín | 13 La Libertad | 14 Lambayeque | 15 Lima |
| 16 Loreto | 17 Madre de Dios | 18 Moquegua | 19 Pasco | 20 Piura |
| 21 Puno | 22 San Martín | 23 Tacna | 24 Tumbes | 25 Ucayali |

Lima (15) y Callao (07) son departamentos distintos. No los juntes.

## Cifras de control, ENAHO 2024

| Cifra | Valor |
|---|---|
| Pobreza monetaria | 27.6 % |
| Pobreza extrema | 5.5 % |
| Urbano / rural | 24.8 % / 39.3 % |
| Cusco | 18.5 % |
| Más pobreza | Cajamarca 45.0 %, Loreto 43.0 %, Puno 39.9 % |
| Menos pobreza | Ica 6.0 %, Moquegua 11.0 %, Madre de Dios 11.1 % |

## Variables que no están en la base

Búscalas en `datos/<código>-Modulo34/Diccionario<año>.pdf`. La sumaria tiene
163 columnas (gasto, ingreso, líneas de pobreza `linea` y `linpe`); el módulo
de miembros, 40. Para agregarlas, edita la lista de columnas en el paso 1 o 4
de `scripts/limpiar.py` y vuelve a correrlo. Otros temas (educación, salud,
empleo) están en otros módulos del INEI que descargando-enaho todavía no baja.
Avísale al usuario en vez de inventar la variable.

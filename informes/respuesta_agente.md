# ¿Por qué la pobreza monetaria de 2024 sigue por encima de la de 2019 y a qué departamentos golpeó más?

La pobreza monetaria pasó de **20.2 % en 2019 a 27.6 % en 2024**: **+7.4 puntos porcentuales** (INEI, ENAHO 2019 y 2024, módulo 34 sumaria, ponderado con `factor07 × mieperho`). Ambas cifras coinciden con las oficiales del INEI (validación de la skill limpiando-enaho: «OK» en los dos años). La pobreza extrema pasó de 2.9 % a 5.5 %.

## Hallazgo 1. Los alimentos subieron más que el resto de la canasta, y la línea de pobreza subió con ellos

- Entre diciembre de 2019 y diciembre de 2024, el índice de precios de **Alimentos y Bebidas subió 31.9 %**, frente a **23.9 % del IPC general** (Lima Metropolitana).
  - Fuente: BCRP, series **PN39445PM** (IPC Alimentos y Bebidas, índice dic. 2021 = 100; de 90.59 a 119.53) y **PN38705PM** (IPC, índice dic. 2021 = 100; de 92.14 a 114.17), 2019-12 a 2024-12.
- La inflación de alimentos a 12 meses llegó a un máximo de **13.2 % en febrero de 2023**; la general, a **8.8 % en junio de 2022**.
  - Fuente: BCRP, series **PN09822PM** (IPC Alimentos y Bebidas, var. % 12 meses) y **PN01273PM** (IPC, var. % 12 meses), 2019-01 a 2024-12.
- La línea de pobreza (el costo de la canasta por persona) pasó de **S/ 351.74 al mes en 2019 a S/ 454.39 en 2024**, y la de pobreza extrema (solo alimentos), de **S/ 187.24 a S/ 255.57** (INEI, ENAHO 2019 y 2024, sumaria).
- Lectura: un hogar necesita hoy bastante más dinero para no ser pobre, y la parte de alimentos, que pesa más en el gasto de los hogares pobres, fue la que más se encareció.

Gráfico: `figuras/inflacion_2019_2024.png` (datos en `salidas/inflacion_2019_2024.csv`).

## Hallazgo 2. El aumento fue sobre todo urbano: la pobreza rural casi no cambió

| Área | 2019 | 2024 |
|---|---|---|
| Urbana | 14.6 % | 24.8 % |
| Rural | 40.8 % | 39.3 % |
| Perú | 20.2 % | 27.6 % |

- Fuente: INEI, ENAHO 2019 y 2024 (sumaria), ponderado con `factor07 × mieperho`; cifras en `salidas/indicadores.csv`.
- La pobreza urbana subió unos diez puntos; la rural bajó levemente. La pobreza extrema, en cambio, sí subió en el campo (de 9.8 % a 15.5 %) y en la ciudad (de 0.9 % a 3.1 %).
- Lectura: el retroceso respecto de 2019 se concentra en las ciudades, donde casi todo lo que se come se compra y donde el alza de precios llega de lleno.

Gráficos: `figuras/pobre_por_area_2019.png` y `figuras/pobre_por_area_2024.png`.

## Hallazgo 3. Los que más empeoraron no son los más pobres, y la falta de agua se asocia con el nivel de pobreza, no con el cambio

- **Más empeoraron (2019-2024, puntos porcentuales):** Callao +19.5 (de 14.3 % a 33.9 %), Ucayali +14.7 (de 12.3 % a 27.1 %), Tumbes +13.2 (de 13.7 % a 26.9 %) y Lima +12.9 (de 14.2 % a 27.1 %).
- **Mejoraron:** Ayacucho −6.6, Apurímac −5.1, Amazonas −4.7, Cusco −4.5, Huancavelica −3.5, San Martín −3.4 y Junín −2.2.
- **Más pobres en 2024:** Cajamarca 45.0 %, Loreto 43.0 %, Puno 39.9 %, Pasco 39.0 % y Huánuco 39.0 %. **Menos pobres:** Ica 6.0 %, Moquegua 11.0 % y Madre de Dios 11.1 %.
  - Fuente: INEI, ENAHO 2019 y 2024 (sumaria), ponderado con `factor07 × mieperho`.
- **Agua (Censo 2017):** los departamentos con más viviendas sin red pública de agua son Puno (52.8 %), Loreto (49.9 %), Huánuco (41.2 %), Ucayali (40.5 %) y Pasco (36.2 %). Cuatro de ellos están entre los cinco más pobres de 2024. Callao (11.7 %) y Lima (12.5 %), los que más empeoraron, son los que menos viviendas sin red tienen.
  - Fuente: INEI, Censos Nacionales 2017, REDATAM, variable `Vivienda.C2P6` (códigos 3 o más = sin red pública), en `salidas/redatam/agua_departamento.csv`.
- **Correlación entre los 25 departamentos:** % de viviendas sin red (2017) con la pobreza de 2024: **0.52**; con el cambio 2019-2024: **0.19** (coeficiente de Pearson, `salidas/indicadores.csv`).
- Lectura: la falta de agua acompaña a la pobreza **de siempre** (la estructural, más rural y amazónica o altoandina), pero casi no dice nada sobre **quién empeoró** después de 2019, que fue sobre todo la costa urbana.

Gráficos: `mapas/pobreza_departamento_2024.png` (mapa de la pobreza 2024) y `figuras/cambio_pobreza_departamento_2019_2024.png` (cambio por departamento).

## Lo que estos datos no permiten concluir

1. **Causalidad.** Que los alimentos se encarecieran más que el IPC y que la pobreza subiera más en las ciudades es una coincidencia consistente, no una prueba. Estos datos no separan el efecto de los precios del de los ingresos (empleo, informalidad, la recesión de 2023, El Niño costero o la conflictividad social).
2. **Precios fuera de Lima.** Las series del BCRP usadas son de Lima Metropolitana. No miden la inflación de alimentos en cada departamento, así que no se puede atribuir el aumento de Ucayali o Tumbes a sus propios precios.
3. **Correlaciones entre 25 departamentos.** Describen, no prueban: con 25 observaciones, una correlación de 0.19 no se distingue de cero, y una de 0.52 puede deberse a otros factores que acompañan la falta de agua (ruralidad, distancia, Amazonía).
4. **El agua es de 2017.** El Censo es el punto de partida, no la foto de 2024: la cobertura pudo cambiar después.
5. **Precisión departamental.** Las tasas por departamento de la ENAHO tienen márgenes de error amplios (sobre todo en Callao, Tumbes, Madre de Dios o Moquegua, con muestras pequeñas). Este análisis no calculó intervalos de confianza, así que las diferencias pequeñas entre departamentos, o los cambios de pocos puntos, no deben leerse como seguros.
6. **Un año contra otro.** Comparar 2019 con 2024 no muestra la trayectoria intermedia (el salto de 2020 y la recuperación parcial), solo los dos extremos.

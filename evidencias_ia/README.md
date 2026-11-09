# Evidencias del uso de IA

| Archivo | Qué es |
|---|---|
| `pregunta_integrada.txt` | El pedido que recibió el agente para la Parte 3 |
| `corrida_integrada.jsonl` | La corrida completa del agente (`claude -p ... --output-format stream-json`): cada llamada a herramientas MCP y skills, con sus resultados |

## La corrida integrada

Se corrió desde el repositorio con `salidas/`, `figuras/` y `mapas/` vacíos, para que el agente tuviera que
reconstruir todo con sus herramientas:

```bash
claude -p "$(cat evidencias_ia/pregunta_integrada.txt)" --output-format stream-json --verbose \
  --mcp-config .mcp.json --strict-mcp-config --permission-mode acceptEdits \
  --allowedTools "mcp__peru__buscar_series" "mcp__peru__resumen" "mcp__peru__serie" "mcp__peru__graficar_series" \
  "mcp__peru__consultar_redatam" "mcp__peru__variables_redatam" "Skill" "Read" "Write" "Edit" "Glob" "Grep" \
  "Bash(uv run:*)" "Bash(ls:*)" "Bash(cat:*)"
```

Resultado: 29 turnos, unos 2 minutos, US$ 0.74. El agente usó:

- **Skills (4):** `limpiando-enaho` (2019 y 2024), `graficando-enaho`, `mapeando-enaho` y `cruzando-fuentes`.
- **Herramientas MCP (4):** `buscar_series`, `resumen`, `graficar_series` y `consultar_redatam`.

Su respuesta quedó en [`informes/respuesta_agente.md`](../informes/respuesta_agente.md). Sus cifras coinciden con las
de [`informes/informe_final.md`](../informes/informe_final.md).

**Nota.** En la máquina donde se corrió también hay copias personales de tres skills de la ENAHO
(`~/.claude/skills/`), y Claude Code les da prioridad sobre las del proyecto. Por eso en el registro esas tres
aparecen con esa ruta. Solo difieren en cuatro líneas de cabecera (`# /// script`, las dependencias para `uv`): la
lógica es la misma y las salidas son idénticas. En un clon limpio del repositorio se usan las de `.claude/skills/`.

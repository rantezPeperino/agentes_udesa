# Reporte M3 — Evaluación de Agente en Mundo Simulado

## Resumen Ejecutivo

- **Tasa de Éxito**: 22.5%
- **Eficiencia (pasos)**: 0.57x óptimo (casos ganados)
- **Pass@3**: 0.0%
- **Latencia media**: 7.25s (p95: 27.20s)
- **Tokens (in/out)**: 20762 / 661

## Resultados por Dificultad

### EASY (15 casos)
- Éxito: 46.7%
- Pasos promedio: 2.1

### EXTREME (45 casos)
- Éxito: 4.4%
- Pasos promedio: 1.4

### HARD (30 casos)
- Éxito: 23.3%
- Pasos promedio: 5.4

### MEDIUM (30 casos)
- Éxito: 36.7%
- Pasos promedio: 5.3

## Categorías de Error Detectadas

- **UNCLASSIFIED**: 88 (UNCLASSIFIED)
- **REDUNDANT_ACTION**: 22 (Acción repetida innecesariamente)
- **PRECONDITION_VIOLATED**: 6 (Precondición no cumplida (no visible/llevable))
- **PREMATURE_STOP**: 5 (Terminó sin resolver (rendición))
- **NAVIGATION_BLOCKED**: 3 (Navegación bloqueada o sin salida)
- **TOOL_ARG_INVALID**: 2 (Argumento inválido (objeto no existe))

## Notas
- Generado desde resultados JSONL
- Total de casos: 120
- Casos resueltos: 27
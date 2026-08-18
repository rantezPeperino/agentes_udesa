# Infraestructura de Evaluación - M3

## Descripción

Este directorio contiene la infraestructura completa para evaluar tu agente de M1+M2 contra los 8 escenarios del problema "sala de escape" de M3.

## Módulos

### `run.py` — Runner de Evaluación
Ejecuta tu agente sobre cada escenario y captura métricas.

```bash
# Todos los escenarios
python eval/run.py

# Solo escenarios easy
python eval/run.py --scenario easy

# Con límite de steps personalizado
python eval/run.py --max-steps 10

# Salida personalizada
python eval/run.py --output eval/results/custom.json
```

**Captura:**
- ✅ Pass/fail (goal_achieved)
- ✅ Número de steps/llamadas LLM
- ✅ Tokens de entrada/salida
- ✅ Latencia en segundos
- ✅ Tipo de error (si falló)
- ✅ Event log del mundo
- ✅ Inventario final
- ✅ Sala final

**Salida:** JSON con resultados de cada escenario

---

### `metrics.py` — Métricas Cuantitativas
Calcula accuracy, pass@k, eficiencia y tokens/step.

```bash
# Ver métricas del baseline
python eval/metrics.py eval/results/baseline.json

# Con archivo personalizado
python eval/metrics.py eval/results/custom.json
```

**Métricas calculadas:**
- `accuracy_global` — % de escenarios resueltos
- `accuracy_by_difficulty` — desglose por easy/medium/hard/extreme
- `pass@7`, `pass@13`, `pass@21` — % resueltos en ≤k steps
- `efficiency` — (optimal_steps / actual_steps) × 100%
- `tokens_per_step` — eficiencia en consumo de tokens

---

### `analysis.py` — Análisis Cualitativo
Categoriza errores y analiza patrones de fallo.

```bash
# Analizar baseline
python eval/analysis.py eval/results/baseline.json

# Con archivo personalizado
python eval/analysis.py eval/results/custom.json
```

**Dimensiones de análisis:**
1. **Por tipo de error:** context_exceeded, timeout, hallucination, lost_state, goal_ordering, navigation
2. **Por dificultad:** easy/medium/hard/extreme
3. **Por mecánica:** simple, navegación, goal compuesto, horizonte largo, multi-item lock, backtracking

---

### `report.py` — Generador de Informe
Produce un archivo Markdown con resultados, gráficos y conclusiones.

```bash
# Generar informe del baseline
python eval/report.py

# Con archivo personalizado
python eval/report.py --input eval/results/custom.json --output informe_custom.md
```

**Contenido del informe:**
- Resumen ejecutivo (accuracy global, breakdown)
- Tabla de resultados por escenario
- Métricas detalladas
- Análisis de errores
- Análisis por mecánica
- Conclusiones y limitaciones
- Qué construirías después

---

### `experiments.py` — Ablaciones A/B
Define y ejecuta múltiples experimentos para entender qué partes del framework importan.

```bash
# Ejecutar todos los experimentos
python eval/experiments.py
```

**Experimentos incluidos:**

1. **Exp 1: Max Steps = 5**
   - Pregunta: ¿Es crítico un horizonte largo?
   - Intervención: Limitar a 5 iteraciones
   - Resultado: Delta de accuracy vs baseline

2. **Exp 2: Solo Easy**
   - Pregunta: ¿Cuál es la línea base?
   - Intervención: Ejecutar solo escenarios easy
   - Resultado: Accuracy en easy

3. **Exp 3: Max Steps = 30**
   - Pregunta: ¿Mejora con más iteraciones?
   - Intervención: Aumentar a 30 iteraciones
   - Resultado: Delta de accuracy vs baseline

**Salida:** `eval/results/experiments_summary.json` con comparativa

---

## Flujo Típico de Uso

### 1. Ejecutar Evaluación Baseline

```bash
python eval/run.py
```

Genera: `eval/results/baseline.json`

### 2. Ver Métricas

```bash
python eval/metrics.py
```

Salida: Tabla en terminal con accuracy, pass@k, eficiencia

### 3. Analizar Errores

```bash
python eval/analysis.py
```

Salida: Categorización de fallos por tipo/dificultad/mecánica

### 4. Generar Informe

```bash
python eval/report.py
```

Genera: `INFORME_M3.md` con análisis completo

### 5. Ejecutar Experimentos (opcional)

```bash
python eval/experiments.py
```

Compara baseline vs ablaciones, genera `eval/results/experiments_summary.json`

---

## Estructura de Resultados

```
eval/
├── results/
│   ├── baseline.json                  # Resultados principales
│   ├── exp1_max_steps_5.json         # Experimento 1
│   ├── exp2_easy_only.json           # Experimento 2
│   ├── exp3_max_steps_30.json        # Experimento 3
│   └── experiments_summary.json      # Comparativa
├── __init__.py
├── run.py
├── metrics.py
├── analysis.py
├── experiments.py
├── report.py
└── README.md
```

---

## Interpretación de Métricas

### Accuracy
- **≥75%:** Agente resuelve la mayoría correctamente
- **50-75%:** Algunos problemas en casos complejos
- **25-50%:** Limitaciones significativas
- **<25%:** Limitaciones críticas

### Pass@k
- `pass@7`: % que resuelven en ≤7 steps (para medium/easy)
- `pass@13`: % que resuelven en ≤13 steps (para hard)
- `pass@21`: % que resuelven en ≤21 steps (para extreme)

### Efficiency
- **100%:** Resuelve en exactamente los pasos óptimos
- **>50%:** Razonablemente eficiente
- **<50%:** Ineficiente, muchos pasos extra

### Tokens/Step
- Indicador de costo del agente
- Valores típicos: 50-100 tokens/step

---

## Errores Comunes

### "ModuleNotFoundError: No module named 'student_framework'"
- Asegurate de ejecutar los comandos desde la raíz del proyecto
- Verifica que `student_framework/` existe y tiene `__init__.py`

### "FileNotFoundError: scenarios/..."
- El JSON del escenario no se encontró
- Verifica que la carpeta `scenarios/` tiene los 8 archivos

### "AttributeError: 'NoneType' object..."
- El agente retornó None o no implementó bien el contrato de M1+M2
- Verifica que `build_agent()` retorna un objeto con método `run()`

---

## Personalizacion

### Agregar nuevo experimento

Edita `eval/experiments.py` y añade una nueva instancia de `Experiment`:

```python
exp_custom = Experiment(
    name="Mi Experimento",
    description="Descripción",
    cmd_args=["--scenario", "all", "--max-steps", 15],
)
exp_custom_results = exp_custom.run("eval/results/exp_custom.json")
```

### Cambiar métricas

Edita `eval/metrics.py` y agrega nuevos métodos a la clase `Metrics`.

### Personalizar análisis

Edita `eval/analysis.py` y expande las categorías de error o dimensiones de análisis.

---

## Referencias

- **ENUNCIADO_M3.md** — Especificación completa del milestone
- **mia_world/** — Modelo de mundo, herramientas, sistema de metas
- **scenarios/** — 8 escenarios JSON de dificultad creciente
- **student_framework/agent.py** — Tu implementación del agente

---

**Generado:** 16 de agosto de 2026  
**Proyecto:** tp_mia_agentes_2026 - Milestone 3

"""Configuraciones de experimentos para M3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ExperimentConfig:
    """Configuración de un experimento."""
    name: str
    description: str
    variants: list[tuple[str, dict[str, Any]]]  # (label, config_override)


# Experimento 1: Ventana deslizante
EXP1_WINDOW = ExperimentConfig(
    name="exp1_window",
    description="Ablación de tamaño de ventana: max_history_messages ∈ {6, 12, 25, 50}",
    variants=[
        ("baseline (50)", {}),
        ("window_6", {"max_history_messages": 6}),
        ("window_12", {"max_history_messages": 12}),
        ("window_25", {"max_history_messages": 25}),
    ],
)

# Experimento 2: Presupuesto de iteraciones
EXP2_BUDGET = ExperimentConfig(
    name="exp2_budget",
    description="Ablación de presupuesto: max_iterations ∈ {5, 10, 20, 30, 50}",
    variants=[
        ("baseline (30)", {}),
        ("budget_5", {"max_iterations": 5}),
        ("budget_10", {"max_iterations": 10}),
        ("budget_20", {"max_iterations": 20}),
        ("budget_50", {"max_iterations": 50}),
    ],
)

# Experimento 3: System prompt
PROMPT_GENERICO = "Eres un asistente útil."
PROMPT_ESPECIFICO = """Eres un experto en resolver puzzles de salas de escape.

Para resolver un puzzle:
1. Primero examina la sala completa con `look` para entender qué hay
2. Examina objetos interesantes con `examine`
3. Toma objetos llevables con `take`
4. Usa objetos sobre cerraduras/puertas con `use`
5. En salas múltiples, navega con `go` (ej: go(direction="north"))

Sigue este ciclo hasta abrir la puerta principal."""

EXP3_PROMPT = ExperimentConfig(
    name="exp3_prompt",
    description="Específicidad del system prompt: genérico vs. instructivo",
    variants=[
        ("prompt_generico", {"system_prompt": PROMPT_GENERICO}),
        ("prompt_especifico", {"system_prompt": PROMPT_ESPECIFICO}),
    ],
)

# Experimento 4: No-op tool
EXP4_NOOP_TOOL = ExperimentConfig(
    name="exp4_noop_tool",
    description="Herramienta look no-funcional para evaluar dependencia",
    variants=[
        ("baseline_look", {}),
        # La variante noop se genera dinámicamente en run.py
    ],
)

EXPERIMENTS = [EXP1_WINDOW, EXP2_BUDGET, EXP3_PROMPT, EXP4_NOOP_TOOL]


def get_experiment(name: str) -> ExperimentConfig | None:
    """Obtiene un experimento por nombre."""
    for exp in EXPERIMENTS:
        if exp.name == name:
            return exp
    return None

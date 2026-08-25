"""Taxonomía de errores para clasificación de fallos en M3."""

from __future__ import annotations

from typing import Any


def classify_error(step: dict[str, Any], all_steps: list[dict[str, Any]]) -> list[str]:
    """Clasifica un paso en categorías de error.

    Args:
        step: Diccionario con tool_name, tool_input, tool_output, error
        all_steps: Lista completa de pasos para detectar redundancias

    Returns:
        Lista de categorías de error aplicables
    """
    categories = []
    tool_output = step.get("tool_output", "")
    tool_error = step.get("error")
    tool_name = step.get("tool_name")
    tool_input = step.get("tool_input")

    # TOOL_CRASH: step.error is not None
    if tool_error is not None:
        categories.append("TOOL_CRASH")
        return categories

    # Detectar errores en tool_output (strings comenzando con "Error")
    if not isinstance(tool_output, str):
        tool_output = str(tool_output)

    if tool_output.startswith("Error"):
        # TOOL_ARG_INVALID: objeto no existe
        if "no existe ningún objeto" in tool_output or "no encuentro" in tool_output:
            categories.append("TOOL_ARG_INVALID")
        # PRECONDITION_VIOLATED: no ves, no llevas, no es visible
        elif any(x in tool_output for x in ["no ves ningún", "no llevas ningún", "no es visible"]):
            categories.append("PRECONDITION_VIOLATED")
        # WRONG_KEY: llave incorrecta
        elif "pero no encaja" in tool_output or "no sirve esa llave" in tool_output:
            categories.append("WRONG_KEY")
        # NAVIGATION_BLOCKED: navegación bloqueada
        elif "bloqueado" in tool_output or "no hay salida" in tool_output:
            categories.append("NAVIGATION_BLOCKED")

    # REDUNDANT_ACTION: par (tool_name, tool_input) repetido
    current_key = (tool_name, tool_input)
    count = sum(1 for s in all_steps if (s.get("tool_name"), s.get("tool_input")) == current_key)
    if count > 1:
        categories.append("REDUNDANT_ACTION")

    return categories if categories else ["OK"]


def classify_case(
    goal_achieved: bool,
    agent_error: str | None,
    steps: list[dict[str, Any]],
) -> list[str]:
    """Clasifica un caso completo en categorías de error.

    Args:
        goal_achieved: Si el objetivo se logró
        agent_error: Campo error del AgentResult
        steps: Lista de pasos ejecutados

    Returns:
        Lista de categorías de error del caso
    """
    categories = []

    # BUDGET_EXHAUSTED: agent_error == "max_iterations_reached"
    if agent_error == "max_iterations_reached":
        categories.append("BUDGET_EXHAUSTED")

    # PREMATURE_STOP: terminó con texto y goal_achieved == False
    if not goal_achieved and agent_error != "max_iterations_reached" and steps:
        categories.append("PREMATURE_STOP")

    # Clasificar errores por paso
    for step in steps:
        step_cats = classify_error(step, steps)
        for cat in step_cats:
            if cat not in categories and cat != "OK":
                categories.append(cat)

    return categories if categories else [] if goal_achieved else ["UNCLASSIFIED"]


# Descripciones de categorías para reporting
CATEGORY_DESCRIPTIONS = {
    "TOOL_ARG_INVALID": "Argumento inválido (objeto no existe)",
    "PRECONDITION_VIOLATED": "Precondición no cumplida (no visible/llevable)",
    "WRONG_KEY": "Llave incorrecta para el objeto",
    "NAVIGATION_BLOCKED": "Navegación bloqueada o sin salida",
    "REDUNDANT_ACTION": "Acción repetida innecesariamente",
    "BUDGET_EXHAUSTED": "Agotó el presupuesto de iteraciones",
    "PREMATURE_STOP": "Terminó sin resolver (rendición)",
    "SEQUENCE_VIOLATION": "Violación del orden requerido",
    "TOOL_CRASH": "Crash técnico de la herramienta",
}

"""LLM-as-judge para evaluación cualitativa."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from student_framework import build_agent


class JudgmentSchema(BaseModel):
    """Esquema de evaluación cualitativa."""
    exploracion_sistematica: int = Field(1, ge=1, le=5, description="Exploración sistemática del mundo (1-5)")
    recuperacion_ante_error: int = Field(1, ge=1, le=5, description="Recuperación ante errores (1-5)")
    ausencia_de_redundancia: int = Field(1, ge=1, le=5, description="Ausencia de redundancias (1-5)")
    coherencia_del_plan: int = Field(1, ge=1, le=5, description="Coherencia del plan (1-5)")
    justificacion: str = Field("", description="Justificación de las puntuaciones")


def judge_case(case_result: dict[str, Any]) -> dict[str, Any] | None:
    """Evalúa un caso con LLM-as-judge.

    Args:
        case_result: Resultado de run_case

    Returns:
        Diccionario con puntuaciones o None si falla
    """
    try:
        # Construir prompt para el juez
        steps_text = "\n".join(
            f"  {i+1}. {s['tool_name']}({s['tool_input']}) → {s['tool_output'][:100]}"
            for i, s in enumerate(case_result.get("steps", [])[:10])
        )

        prompt = f"""Evalúa la calidad de este intento de resolver un escenario de sala de escape.

Escenario: {case_result['scenario_id']}
Logró objetivo: {case_result['goal_achieved']}
Tool calls usados: {case_result['n_tool_calls']} (óptimo: {case_result['optimal_calls']})

Traza de acciones:
{steps_text}

Evalúa en escala 1-5:
1. Exploración sistemática: ¿explora el mundo de forma ordenada?
2. Recuperación ante error: ¿se recupera cuando encuentra un error?
3. Ausencia de redundancia: ¿evita repetir acciones?
4. Coherencia del plan: ¿mantiene un plan coherente?

Proporciona justificación breve."""

        # Crear agente juez separado
        judge_agent = build_agent({
            "system_prompt": "Eres un evaluador experto en resolución de problemas.",
            "tools": [],  # Sin herramientas
        })

        # Usar structured_call
        try:
            judgment = judge_agent.structured_call(prompt, JudgmentSchema)
            return {
                "exploracion_sistematica": judgment.exploracion_sistematica,
                "recuperacion_ante_error": judgment.recuperacion_ante_error,
                "ausencia_de_redundancia": judgment.ausencia_de_redundancia,
                "coherencia_del_plan": judgment.coherencia_del_plan,
                "justificacion": judgment.justificacion,
            }
        except Exception:
            # Si falla structured_call, devolver None en lugar de fallar
            return None

    except Exception:
        return None

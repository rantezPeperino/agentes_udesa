"""Runner de casos para evaluación de escenarios."""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from mia_world import load_scenario, make_world_tools, check_goal
from mia_agents.types import AgentResult, AgentStep
from student_framework import build_agent


@dataclass
class CaseResult:
    """Resultado de ejecutar un caso de prueba."""
    run_id: str
    timestamp: str
    scenario_id: str
    difficulty: str
    optimal_calls: int
    config: dict[str, Any]
    goal_achieved: bool
    goal_reason: str
    answer: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    world_event_log: list[str] = field(default_factory=list)
    n_tool_calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_s: float = 0.0
    agent_error: str | None = None
    error_categories: list[str] = field(default_factory=list)
    judge: dict[str, Any] | None = None


def run_case(
    scenario_id: str,
    config: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> CaseResult:
    """Ejecuta un caso de prueba.

    Args:
        scenario_id: ID del escenario
        config: Configuración adicional para el agente
        run_id: ID único de esta corrida (se genera si no se proporciona)

    Returns:
        CaseResult con los datos de la ejecución
    """
    if run_id is None:
        run_id = f"{scenario_id}_{int(time.time() * 1000)}"

    config = config or {}

    # Obtener metadatos del escenario
    from eval.config import SCENARIO_MAP
    scenario_meta = SCENARIO_MAP.get(scenario_id)
    if not scenario_meta:
        return CaseResult(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            scenario_id=scenario_id,
            difficulty="unknown",
            optimal_calls=0,
            config=config,
            goal_achieved=False,
            goal_reason=f"Escenario no encontrado: {scenario_id}",
            answer="",
            agent_error=f"unknown_scenario: {scenario_id}",
        )

    # Cargar escenario fresco
    try:
        scenario = load_scenario(scenario_meta.scenario_file)
    except Exception as e:
        return CaseResult(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            scenario_id=scenario_id,
            difficulty="unknown",
            optimal_calls=0,
            config=config,
            goal_achieved=False,
            goal_reason=f"Error cargando escenario: {e}",
            answer="",
            agent_error=f"load_scenario_failed: {str(e)}",
        )

    # Obtener herramientas del mundo
    try:
        world = scenario.initial_world
        tools = list(make_world_tools(world))
        config_for_agent = {
            **config,
            "world": world,
            "tools": tools,
        }
    except Exception as e:
        return CaseResult(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            scenario_id=scenario_id,
            difficulty=scenario.difficulty,
            optimal_calls=0,
            config=config,
            goal_achieved=False,
            goal_reason=f"Error configurando herramientas: {e}",
            answer="",
            agent_error=f"tools_setup_failed: {str(e)}",
        )

    # Construir agente
    try:
        agent = build_agent(config_for_agent)
    except Exception as e:
        return CaseResult(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            scenario_id=scenario_id,
            difficulty=scenario.difficulty,
            optimal_calls=0,
            config=config,
            goal_achieved=False,
            goal_reason=f"Error construyendo agente: {e}",
            answer="",
            agent_error=f"agent_build_failed: {str(e)}",
        )

    # Ejecutar con cronómetro
    start_time = time.perf_counter()
    try:
        result: AgentResult = agent.run(scenario.user_message)
    except Exception as e:
        latency_s = time.perf_counter() - start_time
        return CaseResult(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            scenario_id=scenario_id,
            difficulty=scenario.difficulty,
            optimal_calls=0,
            config=config,
            goal_achieved=False,
            goal_reason=f"Excepción del agente: {type(e).__name__}",
            answer="",
            latency_s=latency_s,
            agent_error=f"{type(e).__name__}: {str(e)}",
        )

    latency_s = time.perf_counter() - start_time

    # Verificar goal
    try:
        goal_achieved, goal_reason = check_goal(world, scenario.goal)
    except Exception as e:
        goal_achieved = False
        goal_reason = f"Error verificando goal: {e}"

    # Procesar steps
    steps_data = []
    for step in result.steps:
        steps_data.append({
            "tool_name": step.tool_name,
            "tool_input": step.tool_input,
            "tool_output": step.tool_output,
            "error": step.error,
        })

    # Obtener event log del mundo
    event_log = getattr(world, "event_log", [])

    # Obtener metadatos del agente
    window_stats_history = getattr(agent, "_window_stats_history", [])

    return CaseResult(
        run_id=run_id,
        timestamp=datetime.now().isoformat(),
        scenario_id=scenario_id,
        difficulty=scenario.difficulty,
        optimal_calls=0,  # Se rellena desde config.py
        config=config,
        goal_achieved=goal_achieved,
        goal_reason=goal_reason,
        answer=result.answer,
        steps=steps_data,
        world_event_log=event_log,
        n_tool_calls=len(result.steps),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_s=latency_s,
        agent_error=result.error,
    )

from __future__ import annotations

import os

import pytest

from mia_agents._env import load_env_files
from mia_world import check_goal, load_scenario, make_world_tools
from student_framework import build_agent

load_env_files()


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="Falta ANTHROPIC_API_KEY para ejecutar el E2E con Claude.",
)
def test_m3_end_to_end_with_claude() -> None:
    """Ejecuta un escenario M3 real con el provider de Claude y verifica el objetivo."""
    scenario = load_scenario("scenarios/01-study-with-key.json")
    world = scenario.initial_world
    agent = build_agent()

    for tool_fn, tool_schema in make_world_tools(world):
        agent.register_tool(tool_fn, tool_schema)

    result = agent.run(scenario.user_message)

    assert result.answer, "El agente debe devolver una respuesta no vacía."
    assert result.steps, "El agente debe haber ejecutado al menos una herramienta."
    assert result.input_tokens is not None
    assert result.output_tokens is not None

    won, reason = check_goal(world, scenario.goal)
    assert won is True, f"El escenario no se resolvió: {reason}"

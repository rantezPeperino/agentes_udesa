"""Paquete propio del grupo.

Implementen el agente en `agent.py` y registren sus herramientas a
continuación, en `build_agent`. Tanto el runner de la CLI como los tests
de conformidad llaman a `build_agent`, por lo que esta es la única puerta
de entrada pública de su entrega.
"""

from __future__ import annotations

from typing import Any

from mia_agents.llm_client import LLMClient
from mia_agents.protocols import Agent

from .agent import MyAgent


def build_agent(config: dict[str, Any] | None = None) -> Agent:
    """Construye y configura su agente.

    `config` es opcional. Si se proporciona `config["llm_client"]`, el
    agente debe usarlo (así es como los tests de conformidad inyectan un
    cliente mock). Si no, se construye a partir del entorno.

    TODO (M1): instancien su agente y llamen a `agent.register_tool(...)`
    por cada una de sus herramientas antes de devolverlo.
    """

    config = config or {} #NO CAMBIAR
    llm = config.get("llm_client") or LLMClient.from_env() #NO CAMBIAR
    kwargs: dict[str, Any] = {"llm_client": llm} #NO CAMBIAR

    if "max_history_messages" in config:
        kwargs["max_history_messages"] = config["max_history_messages"]
    if "max_iterations" in config:
        kwargs["max_iterations"] = config["max_iterations"]
    if "system_prompt" in config:
        kwargs["system_prompt"] = config["system_prompt"]

    agent = MyAgent(**kwargs)

    # Determinar qué herramientas registrar.
    # Prioridad: config["tools"] > config["world"] > herramientas por defecto.
    if "tools" in config:
        # Usar herramientas inyectadas (esperadas como iterable de pares (callable, ToolSchema)).
        for tool_fn, tool_schema in config["tools"]:
            agent.register_tool(tool_fn, tool_schema)
    elif "world" in config:
        # Derivar herramientas del mundo simulado.
        from mia_world import make_world_tools
        for tool_fn, tool_schema in make_world_tools(config["world"]):
            agent.register_tool(tool_fn, tool_schema)
    else:
        # Comportamiento por defecto: herramientas de M1.
        from student_framework.tools.calculator import calculator, calculator_schema
        from mia_agents.file_reader import file_reader, file_reader_schema
        from student_framework.tools.word_counter import word_counter, word_counter_schema

        agent.register_tool(calculator, calculator_schema)
        agent.register_tool(file_reader, file_reader_schema)
        agent.register_tool(word_counter, word_counter_schema)

    return agent

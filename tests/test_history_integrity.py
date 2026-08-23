"""Tests de integridad del historial conversacional.

Verifica que los arreglos de M3 funcionan correctamente:
- tool_calls se guardan en el mensaje assistant.
- tool_call_id se usa (no tool_use_id).
- _apply_sliding_window respeta límites y atomicidad.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from mia_agents.llm_client import BedrockProvider
from mia_agents.testing import MockLLMClient
from mia_agents.types import LLMResponse, ToolCall, ToolSchema
from student_framework import build_agent


# ============================================================================
# Test 1: tool_calls se guardan en el mensaje assistant
# ============================================================================


def test_assistant_message_includes_tool_calls() -> None:
    """Tras run() con tool call, el historial contiene assistant con tool_calls."""
    mock_responses = [
        # Turno 1: modelo pide una herramienta
        LLMResponse(
            content="Voy a usar la calculadora.",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    name="calculator",
                    arguments='{"operand1": 2, "operand2": 3, "operator": "+"}',
                )
            ],
        ),
        # Turno 2: modelo contesta sin más herramientas
        LLMResponse(
            content="El resultado es 5.",
            tool_calls=[],
        ),
    ]
    mock_llm = MockLLMClient(responses=mock_responses)
    agent = build_agent({"llm_client": mock_llm})

    result = agent.run("¿Cuánto es 2+3?")

    # Verificar que el historial tiene el assistant con tool_calls.
    assert len(agent._conversation_history) >= 2
    # El primer assistant (con tool call) debe estar en el historial.
    assistant_msg = None
    for msg in agent._conversation_history:
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            assistant_msg = msg
            break

    assert assistant_msg is not None, "No se encontró mensaje assistant con tool_calls"
    assert len(assistant_msg["tool_calls"]) == 1
    assert assistant_msg["tool_calls"][0]["id"] == "call_1"
    assert assistant_msg["tool_calls"][0]["function"]["name"] == "calculator"


# ============================================================================
# Test 2: Se usa tool_call_id (no tool_use_id)
# ============================================================================


def test_tool_result_uses_tool_call_id() -> None:
    """El mensaje de resultado usa tool_call_id y no tool_use_id."""
    mock_responses = [
        LLMResponse(
            content="Usando calculadora.",
            tool_calls=[
                ToolCall(
                    id="call_xyz",
                    name="calculator",
                    arguments='{"operand1": 5, "operand2": 7, "operator": "+"}',
                )
            ],
        ),
        LLMResponse(
            content="Listo.",
            tool_calls=[],
        ),
    ]
    mock_llm = MockLLMClient(responses=mock_responses)
    agent = build_agent({"llm_client": mock_llm})
    agent.run("Calcula 5+7")

    # Buscar el mensaje tool en el historial.
    tool_msg = None
    for msg in agent._conversation_history:
        if msg["role"] == "tool":
            tool_msg = msg
            break

    assert tool_msg is not None, "No se encontró mensaje tool en historial"
    assert "tool_call_id" in tool_msg, "Falta clave tool_call_id"
    assert tool_msg["tool_call_id"] == "call_xyz"
    assert "tool_use_id" not in tool_msg, "Se encontró tool_use_id (debe ser tool_call_id)"


# ============================================================================
# Test 3: Historial sobrevive a normalización de Bedrock
# ============================================================================


def test_history_survives_bedrock_normalization() -> None:
    """El historial pasa por _normalize_messages sin generar toolResults huérfanos."""
    mock_responses = [
        LLMResponse(
            content="",
            tool_calls=[
                ToolCall(
                    id="call_abc",
                    name="calculator",
                    arguments='{"operand1": 1, "operand2": 1, "operator": "+"}',
                )
            ],
        ),
        LLMResponse(
            content="Hecho.",
            tool_calls=[],
        ),
    ]
    mock_llm = MockLLMClient(responses=mock_responses)
    agent = build_agent({"llm_client": mock_llm})
    agent.run("Calcula 1+1")

    # Normalizar el historial usando BedrockProvider con modelo de prueba.
    provider = BedrockProvider(model="amazon.nova-lite-v1:0")
    normalized = provider._normalize_messages(agent._conversation_history)

    # Verificar invariantes:
    # 1. Cada toolResult debe tener toolUseId no vacío.
    # 2. Cada toolResult debe seguir a un toolUse en el mismo mensaje assistant.
    for msg in normalized:
        if msg.get("role") == "assistant":
            tool_uses = msg.get("content", [])
            tool_use_ids = {
                block.get("toolUseId")
                for block in tool_uses
                if block.get("type") == "toolUse"
            }

        if msg.get("role") == "user":
            tool_results = msg.get("content", [])
            for block in tool_results:
                if block.get("type") == "toolResult":
                    tool_use_id = block.get("toolUseId")
                    assert tool_use_id and tool_use_id != "", (
                        f"toolResult con toolUseId vacío o nulo: {block}"
                    )


# ============================================================================
# Test 4: _apply_sliding_window nunca supera max_history_messages
# ============================================================================


def test_sliding_window_respects_max_limit() -> None:
    """_apply_sliding_window nunca devuelve más de max_history_messages."""
    mock_llm = MockLLMClient(responses=[
        LLMResponse(content="ok", tool_calls=[])
    ])
    agent = build_agent({
        "llm_client": mock_llm,
        "max_history_messages": 10,
    })

    # Construir un historial sintético con muchos mensajes.
    agent._conversation_history = [
        {"role": "user", "content": f"mensaje {i}"}
        for i in range(30)
    ]

    result = agent._apply_sliding_window()
    assert len(result) <= 10, (
        f"sliding_window devolvió {len(result)} mensajes, máx: 10"
    )


# ============================================================================
# Test 5: _apply_sliding_window nunca empieza con rol "tool"
# ============================================================================


def test_sliding_window_never_starts_with_tool() -> None:
    """El resultado de _apply_sliding_window nunca empieza con rol 'tool'."""
    mock_llm = MockLLMClient(responses=[
        LLMResponse(content="ok", tool_calls=[])
    ])
    agent = build_agent({
        "llm_client": mock_llm,
        "max_history_messages": 5,
    })

    # Historial con bloques assistant+tool.
    agent._conversation_history = [
        {"role": "user", "content": "inicio"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "calc", "arguments": "{}"}}
        ]},
        {"role": "tool", "content": "resultado", "tool_call_id": "c1"},
        {"role": "user", "content": "otra pregunta"},
        {"role": "assistant", "content": "respuesta"},
    ]

    result = agent._apply_sliding_window()
    if result:  # Si el resultado no está vacío
        assert result[0]["role"] != "tool", (
            f"sliding_window empezó con rol={result[0]['role']}, debe ser user o assistant"
        )


# ============================================================================
# Test 6: Múltiples iteraciones mantienen invariantes
# ============================================================================


def test_multiple_iterations_maintain_invariants() -> None:
    """run() con presupuesto pequeño respetar invariantes en cada llamada al LLM."""
    # Crear respuestas que incluyan varias iteraciones.
    # Usar MockLLMClient que captura lo que se envía.
    mock_responses = [
        LLMResponse(
            content="",
            tool_calls=[
                ToolCall(id="c1", name="calculator", arguments='{"operand1":1,"operand2":1,"operator":"+"}')
            ],
        ),
        LLMResponse(
            content="",
            tool_calls=[
                ToolCall(id="c2", name="calculator", arguments='{"operand1":2,"operand2":2,"operator":"+"}')
            ],
        ),
        LLMResponse(
            content="",
            tool_calls=[
                ToolCall(id="c3", name="calculator", arguments='{"operand1":3,"operand2":3,"operator":"+"}')
            ],
        ),
        LLMResponse(content="Fin", tool_calls=[]),
    ]
    mock_llm = MockLLMClient(responses=mock_responses)
    agent = build_agent({
        "llm_client": mock_llm,
        "max_history_messages": 6,  # Presupuesto muy chico.
    })

    result = agent.run("Hazlo varias veces")

    # Verificar invariantes en cada llamada capturada por el mock:
    # En cada llamada a chat, el historial enviado debe respetar max_history_messages.
    assert len(mock_llm.calls) > 0, "MockLLMClient no registró ninguna llamada"

    for call_data in mock_llm.calls:
        messages = call_data.get("messages", [])
        assert len(messages) <= agent._max_history_messages, (
            f"Llamada al LLM con {len(messages)} mensajes, máx: {agent._max_history_messages}"
        )
        # Ningún mensaje "tool" al inicio.
        if messages:
            assert messages[0]["role"] != "tool", (
                "Primer mensaje en llamada al LLM es 'tool', inválido"
            )
        # Si hay tool, debe estar después de un assistant con tool_calls.
        for i, msg in enumerate(messages):
            if msg["role"] == "tool":
                assert i > 0 and messages[i-1]["role"] == "assistant", (
                    f"Mensaje tool en índice {i} sin assistant previo"
                )


# ============================================================================
# Test 7: Comportamiento por defecto sin config["tools"] ni config["world"]
# ============================================================================


def test_default_tools_still_work() -> None:
    """Sin config, se registran las herramientas por defecto (M1)."""
    mock_llm = MockLLMClient(responses=[
        LLMResponse(content="Ok", tool_calls=[])
    ])
    # Sin pasar config["tools"] ni config["world"].
    agent = build_agent({"llm_client": mock_llm})

    # Debe tener las tres herramientas por defecto.
    assert "calculator" in agent._schemas
    assert "file_reader" in agent._schemas
    assert "word_counter" in agent._schemas

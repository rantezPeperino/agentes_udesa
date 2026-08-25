"""Tests de _apply_sliding_window() con recorte por bloques atómicos.

Verifica las 12 invariantes y casos del documento FIX_M3_SLIDING_WINDOW.md
"""

from __future__ import annotations

import pytest

from student_framework import build_agent
from student_framework.agent import MyAgent
from mia_agents.llm_client import LLMClient
from mia_agents.testing import MockLLMClient
from mia_agents.types import LLMResponse, ToolCall


# ============================================================================
# Test 1: Historial más corto que presupuesto -> devuelve copia idéntica
# ============================================================================


def test_trivial_case_returns_copy() -> None:
    """Si len(H) <= m, devuelve copia idéntica del historial."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 10})

    agent._conversation_history = [
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "respuesta"},
    ]

    result = agent._apply_sliding_window()
    assert result == agent._conversation_history
    assert result is not agent._conversation_history  # Es copia, no referencia


# ============================================================================
# Test 2: Fallo rama C — UN user + pares assistant/tool con m=10
# ============================================================================


def test_branch_c_failure_fixed() -> None:
    """Reproduccción del fallo de rama C.

    Historial: [user] + 5 pares [assistant+tool_calls] [tool]
    Total: 11 mensajes con m=10.

    Código viejo (rama C): devolvía 11 mensajes (FALLO).
    Código nuevo: devuelve <= 10 (ARREGLADO).
    """
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 10})

    # Construir historial como describe el documento.
    agent._conversation_history = [
        {"role": "user", "content": "Resuelve el escenario"},
    ]
    for i in range(5):
        agent._conversation_history.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": f"c{i}", "type": "function", "function": {"name": "look", "arguments": "{}"}}],
        })
        agent._conversation_history.append({
            "role": "tool",
            "content": f"Resultado {i}",
            "tool_call_id": f"c{i}",
        })

    result = agent._apply_sliding_window()
    assert len(result) <= 10, f"Presupuesto violado: {len(result)} > 10"


# ============================================================================
# Test 3: Presupuesto respetado para m en {1,2,3,5,6,10,20}
# ============================================================================


def test_presupuesto_respected_variable_m() -> None:
    """len(R) <= m para distintos valores de m."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])

    # Historial de 40 mensajes con bloques de tamaño variable.
    historial = [{"role": "user", "content": "inicio"}]
    for i in range(8):
        # Cada iteración: assistant con tool_calls + 1-4 tool consecutivos
        num_tools = (i % 4) + 1
        historial.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": f"c{i}", "type": "function", "function": {"name": "act", "arguments": "{}"}}],
        })
        for j in range(num_tools):
            historial.append({
                "role": "tool",
                "content": f"r{i}_{j}",
                "tool_call_id": f"c{i}",
            })

    for m in [1, 2, 3, 5, 6, 10, 20]:
        agent = build_agent({"llm_client": mock_llm, "max_history_messages": m})
        agent._conversation_history = list(historial)  # copia
        result = agent._apply_sliding_window()
        assert len(result) <= m, f"m={m}: len={len(result)} > {m}"


# ============================================================================
# Test 4: Nunca empieza con rol "tool"
# ============================================================================


def test_never_starts_with_tool() -> None:
    """R nunca empieza con role == 'tool'."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 5})

    # Historial que podría partir un bloque si no se respeta atomicidad.
    agent._conversation_history = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "type": "function", "function": {"name": "a", "arguments": "{}"}}]},
        {"role": "tool", "content": "r1", "tool_call_id": "1"},
        {"role": "tool", "content": "r1b", "tool_call_id": "1"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "2", "type": "function", "function": {"name": "b", "arguments": "{}"}}]},
        {"role": "tool", "content": "r2", "tool_call_id": "2"},
        {"role": "tool", "content": "r2b", "tool_call_id": "2"},
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "fin"},
    ]

    result = agent._apply_sliding_window()
    if result:
        assert result[0]["role"] != "tool", f"Primer msg es {result[0]['role']}, no 'tool'"


# ============================================================================
# Test 5: Emparejamiento (invariante 3)
# ============================================================================


def test_tool_pairing() -> None:
    """Todo `tool` tiene su `assistant` con `tool_calls` antes, sin roles ajenos en medio."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 15})

    agent._conversation_history = [
        {"role": "user", "content": "inicio"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "t1", "type": "function", "function": {"name": "f", "arguments": "{}"}}]},
        {"role": "tool", "content": "r1", "tool_call_id": "t1"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "t2", "type": "function", "function": {"name": "g", "arguments": "{}"}}]},
        {"role": "tool", "content": "r2", "tool_call_id": "t2"},
        {"role": "assistant", "content": "respuesta final"},
    ]

    result = agent._apply_sliding_window()

    for i, msg in enumerate(result):
        if msg["role"] == "tool":
            # Debe haber un assistant con tool_calls antes.
            assert i > 0, f"tool en índice {i} sin precedente"
            found = False
            for j in range(i - 1, -1, -1):
                if result[j]["role"] == "assistant" and result[j].get("tool_calls"):
                    found = True
                    # Verificar que entre j e i no hay otro rol que tool.
                    for k in range(j + 1, i):
                        assert result[k]["role"] in ("assistant", "tool"), (
                            f"Entre assistant[{j}] y tool[{i}] hay {result[k]['role']}"
                        )
                    break
                elif result[j]["role"] == "assistant":
                    # Es un assistant sin tool_calls; el tool no está emparejado.
                    break
            assert found, f"tool[{i}] sin assistant emparejado"


# ============================================================================
# Test 6: Completitud de bloque (invariante 4)
# ============================================================================


def test_block_completeness() -> None:
    """Si un assistant con tool_calls está en R, TODOS sus tool también."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 20})

    # Historial: assistant con 3 tool consecutivos
    agent._conversation_history = [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "t1", "type": "function", "function": {"name": "f", "arguments": "{}"}}]},
        {"role": "tool", "content": "r1", "tool_call_id": "t1"},
        {"role": "tool", "content": "r2", "tool_call_id": "t1"},
        {"role": "tool", "content": "r3", "tool_call_id": "t1"},
        {"role": "assistant", "content": "done"},
    ]

    result = agent._apply_sliding_window()

    # Contar tool_calls en resultado.
    assistants_with_tools = [
        (i, msg) for i, msg in enumerate(result)
        if msg["role"] == "assistant" and msg.get("tool_calls")
    ]

    for idx, asst in assistants_with_tools:
        # Contar tool inmediatamente después.
        tool_count = 0
        for j in range(idx + 1, len(result)):
            if result[j]["role"] == "tool":
                tool_count += 1
            else:
                break
        # En el historial original hay 3 tool.
        assert tool_count == 3, f"Assistant en {idx} tiene {tool_count} tool, esperado 3"


# ============================================================================
# Test 7: Contiguidad (invariante 5)
# ============================================================================


def test_contiguity() -> None:
    """R es subsecuencia contigua de H."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 8})

    agent._conversation_history = [
        {"role": "user", "content": "0"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "type": "function", "function": {"name": "f", "arguments": "{}"}}]},
        {"role": "tool", "content": "1", "tool_call_id": "1"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "2", "type": "function", "function": {"name": "g", "arguments": "{}"}}]},
        {"role": "tool", "content": "2", "tool_call_id": "2"},
        {"role": "user", "content": "5"},
        {"role": "assistant", "content": "final"},
    ]

    result = agent._apply_sliding_window()
    H = agent._conversation_history

    # Buscar dónde empieza R en H.
    start_idx = -1
    for i in range(len(H) - len(result) + 1):
        if H[i:i+len(result)] == result:
            start_idx = i
            break

    assert start_idx >= 0, "R no es subsecuencia contigua de H"


# ============================================================================
# Test 8: Caso degenerado — bloque final supera presupuesto
# ============================================================================


def test_degradation_last_block_oversized() -> None:
    """Bloque final de 8 mensajes con m=4 -> devuelve último user, no vacío."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 4})

    # Historial: user + 1 grande assistant con 7 tool (no cabe)
    agent._conversation_history = [
        {"role": "user", "content": "inicio"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "big", "type": "function", "function": {"name": "f", "arguments": "{}"}}]},
    ]
    for i in range(7):
        agent._conversation_history.append({
            "role": "tool",
            "content": f"r{i}",
            "tool_call_id": "big",
        })

    result = agent._apply_sliding_window()

    # No debería estar vacío (degradación activa).
    assert len(result) > 0, "Resultado vacío (no se activó degradación)"
    # Debería ser el primer user.
    assert result[0]["role"] == "user", "No devolvió el user para degradación"
    # Debe estar marcado como degradado.
    assert agent._last_window_stats.get("degraded") is True


# ============================================================================
# Test 9: Sin mensaje user -> respeta presupuesto
# ============================================================================


def test_no_user_respects_budget() -> None:
    """Historial sin `user` -> respeta presupuesto, no explota."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 5})

    # Solo assistant y tool.
    agent._conversation_history = [
        {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "type": "function", "function": {"name": "f", "arguments": "{}"}}]},
        {"role": "tool", "content": "r1", "tool_call_id": "1"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "2", "type": "function", "function": {"name": "g", "arguments": "{}"}}]},
        {"role": "tool", "content": "r2", "tool_call_id": "2"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "3", "type": "function", "function": {"name": "h", "arguments": "{}"}}]},
        {"role": "tool", "content": "r3", "tool_call_id": "3"},
    ]

    result = agent._apply_sliding_window()
    assert len(result) <= 5, f"Presupuesto violado: {len(result)} > 5"


# ============================================================================
# Test 10: Historial vacío
# ============================================================================


def test_empty_history() -> None:
    """Historial vacío -> devuelve []."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 10})

    agent._conversation_history = []
    result = agent._apply_sliding_window()
    assert result == []


# ============================================================================
# Test 11: _last_window_stats se puebla correctamente
# ============================================================================


def test_window_stats_populated() -> None:
    """_last_window_stats tiene las claves esperadas."""
    mock_llm = MockLLMClient(responses=[LLMResponse(content="ok", tool_calls=[])])
    agent = build_agent({"llm_client": mock_llm, "max_history_messages": 10})

    agent._conversation_history = [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "1", "type": "function", "function": {"name": "f", "arguments": "{}"}}]},
        {"role": "tool", "content": "r", "tool_call_id": "1"},
        {"role": "assistant", "content": "resp"},
    ]

    result = agent._apply_sliding_window()
    stats = agent._last_window_stats

    assert "total_blocks" in stats
    assert "sent_blocks" in stats
    assert "sent_messages" in stats
    assert "dropped_messages" in stats
    assert "degraded" in stats
    assert stats["sent_messages"] == len(result)


# ============================================================================
# Test 12: Integración — run() con múltiples iteraciones respeta m
# ============================================================================


def test_integration_run_respects_window() -> None:
    """run() con m=6 y varias iteraciones -> todas las llamadas <= 6 mensajes."""
    mock_responses = [
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c1", name="calculator", arguments='{"operand1":1,"operand2":1,"operator":"+"}')
        ]),
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c2", name="calculator", arguments='{"operand1":2,"operand2":2,"operator":"+"}')
        ]),
        LLMResponse(content="", tool_calls=[
            ToolCall(id="c3", name="calculator", arguments='{"operand1":3,"operand2":3,"operator":"+"}')
        ]),
        LLMResponse(content="Fin", tool_calls=[]),
    ]
    mock_llm = MockLLMClient(responses=mock_responses)
    agent = build_agent({
        "llm_client": mock_llm,
        "max_history_messages": 6,
    })

    result = agent.run("Hazlo varias veces")

    # Verificar que TODAS las llamadas respetaron el presupuesto.
    for i, call in enumerate(mock_llm.calls):
        messages = call.get("messages", [])
        assert len(messages) <= 6, (
            f"Llamada {i}: {len(messages)} mensajes > 6"
        )
        if messages:
            assert messages[0]["role"] != "tool", (
                f"Llamada {i}: empieza con 'tool'"
            )

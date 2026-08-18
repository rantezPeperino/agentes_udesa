from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from mia_agents.llm_client import AnthropicProvider


@pytest.fixture
def fake_client():
    with patch("mia_agents.llm_client.anthropic.Anthropic") as factory:
        instance = MagicMock()
        factory.return_value = instance
        yield instance


@pytest.fixture
def provider(fake_client) -> AnthropicProvider:
    return AnthropicProvider(
        model="claude-sonnet-4-6",
        api_key="sk-ant-test-key",
    )


def test_missing_api_key_raises(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicProvider()


def test_constructor_uses_env_when_args_absent(fake_client, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
    provider = AnthropicProvider()
    fake_client.messages.create.return_value = MagicMock(
        content=[{"type": "text", "text": "ok"}],
        usage={"input_tokens": 4, "output_tokens": 2},
    )
    provider.chat(messages=[{"role": "user", "content": "hola"}])
    assert fake_client.messages.create.call_args.kwargs["model"] == "claude-3-5-haiku-20241022"


def test_simple_text_response_parsed(provider, fake_client) -> None:
    fake_client.messages.create.return_value = MagicMock(
        content=[{"type": "text", "text": "Hola mundo"}],
        usage={"input_tokens": 10, "output_tokens": 5},
    )

    result = provider.chat(messages=[{"role": "user", "content": "hola"}])

    assert result.content == "Hola mundo"
    assert result.tool_calls == []
    assert result.input_tokens == 10
    assert result.output_tokens == 5


def test_tool_use_parsed_to_tool_call(provider, fake_client) -> None:
    fake_client.messages.create.return_value = MagicMock(
        content=[
            {
                "type": "tool_use",
                "id": "toolu_123",
                "name": "examine",
                "input": {"target": "alfombra"},
            }
        ],
        usage={"input_tokens": 7, "output_tokens": 3},
    )

    result = provider.chat(messages=[{"role": "user", "content": "explora"}])

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "toolu_123"
    assert result.tool_calls[0].name == "examine"
    assert json.loads(result.tool_calls[0].arguments) == {"target": "alfombra"}


def test_message_translation_uses_anthropic_shape(provider, fake_client) -> None:
    fake_client.messages.create.return_value = MagicMock(
        content=[{"type": "text", "text": "ok"}],
        usage={"input_tokens": 1, "output_tokens": 1},
    )

    provider.chat(
        messages=[
            {"role": "user", "content": "hola"},
            {
                "role": "assistant",
                "content": "voy a examinar",
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "examine",
                            "arguments": json.dumps({"target": "alfombra"}),
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "Tienes una llave."},
        ],
        system="Eres un asistente.",
    )

    sent = fake_client.messages.create.call_args.kwargs
    assert sent["system"] == "Eres un asistente."
    assert sent["messages"][0]["role"] == "user"
    assert sent["messages"][1]["role"] == "assistant"
    assert sent["messages"][1]["content"][0]["type"] == "text"
    assert sent["messages"][1]["content"][1]["type"] == "tool_use"
    assert sent["messages"][2]["role"] == "user"
    assert sent["messages"][2]["content"][0]["type"] == "tool_result"

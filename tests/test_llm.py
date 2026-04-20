"""Tests for the LLM provider abstraction in :mod:`pd_agent.llm`.

All tests are hermetic: they use ``unittest.mock.MagicMock`` as the
Anthropic client, so no real API calls are made and no real API key is
required.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from pd_agent.config import PDAgentSettings
from pd_agent.llm import (
    AnthropicProvider,
    LLMProvider,
    LLMResponse,
    make_default_provider,
)


def _mock_anthropic_message(
    text: str = "hello",
    model: str = "claude-sonnet-4-5",
    input_tokens: int = 10,
    output_tokens: int = 5,
    stop_reason: str | None = "end_turn",
) -> MagicMock:
    """Build a mock object mimicking ``anthropic.types.Message``.

    Mirrors the attributes :class:`AnthropicProvider.generate` reads:
    ``content`` (list of blocks with ``.type`` and ``.text``), ``model``,
    ``stop_reason``, and ``usage.input_tokens`` / ``usage.output_tokens``.
    """
    msg = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg.content = [block]
    msg.model = model
    msg.stop_reason = stop_reason
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


# --------------------------------------------------------------------------- #
# LLMResponse                                                                  #
# --------------------------------------------------------------------------- #


def test_llm_response_is_frozen():
    resp = LLMResponse(text="hi", model="m", input_tokens=1, output_tokens=1)
    with pytest.raises(ValidationError):
        resp.text = "changed"


def test_llm_response_total_tokens():
    resp = LLMResponse(text="hi", model="m", input_tokens=10, output_tokens=5)
    assert resp.total_tokens == 15


def test_llm_response_rejects_negative_tokens():
    with pytest.raises(ValidationError):
        LLMResponse(text="hi", model="m", input_tokens=-1, output_tokens=0)


def test_llm_response_default_stop_reason():
    resp = LLMResponse(text="hi", model="m", input_tokens=1, output_tokens=1)
    assert resp.stop_reason == ""


# --------------------------------------------------------------------------- #
# AnthropicProvider                                                            #
# --------------------------------------------------------------------------- #


def test_provider_satisfies_llmprovider_protocol():
    """``AnthropicProvider`` structurally satisfies ``LLMProvider``."""
    provider = AnthropicProvider(api_key="fake", client=MagicMock())
    assert isinstance(provider, LLMProvider)


def test_provider_exposes_model_name():
    provider = AnthropicProvider(api_key="fake", model="claude-opus-4-5", client=MagicMock())
    assert provider.model == "claude-opus-4-5"


def test_generate_constructs_request_without_system():
    client = MagicMock()
    client.messages.create.return_value = _mock_anthropic_message()
    provider = AnthropicProvider(api_key="fake", model="claude-test", client=client)

    provider.generate("hello prompt")

    client.messages.create.assert_called_once_with(
        model="claude-test",
        max_tokens=1024,
        temperature=0.2,
        messages=[{"role": "user", "content": "hello prompt"}],
    )


def test_generate_constructs_request_with_system_and_overrides():
    client = MagicMock()
    client.messages.create.return_value = _mock_anthropic_message()
    provider = AnthropicProvider(api_key="fake", model="claude-test", client=client)

    provider.generate(
        "hello prompt",
        system="You are a helpful PD engineer.",
        max_tokens=512,
        temperature=0.0,
    )

    client.messages.create.assert_called_once_with(
        model="claude-test",
        max_tokens=512,
        temperature=0.0,
        messages=[{"role": "user", "content": "hello prompt"}],
        system="You are a helpful PD engineer.",
    )


def test_generate_returns_llm_response():
    client = MagicMock()
    client.messages.create.return_value = _mock_anthropic_message(
        text="response text",
        model="claude-sonnet-4-5",
        input_tokens=42,
        output_tokens=7,
        stop_reason="end_turn",
    )
    provider = AnthropicProvider(api_key="fake", client=client)

    resp = provider.generate("anything")

    assert isinstance(resp, LLMResponse)
    assert resp.text == "response text"
    assert resp.model == "claude-sonnet-4-5"
    assert resp.input_tokens == 42
    assert resp.output_tokens == 7
    assert resp.stop_reason == "end_turn"
    assert resp.total_tokens == 49


def test_generate_concatenates_multiple_text_blocks():
    """Anthropic may return multiple text blocks; we concatenate them in order."""
    client = MagicMock()

    msg = MagicMock()
    block_a = MagicMock()
    block_a.type = "text"
    block_a.text = "Hello, "
    block_b = MagicMock()
    block_b.type = "text"
    block_b.text = "world."
    msg.content = [block_a, block_b]
    msg.model = "m"
    msg.stop_reason = "end_turn"
    msg.usage.input_tokens = 1
    msg.usage.output_tokens = 1
    client.messages.create.return_value = msg

    provider = AnthropicProvider(api_key="fake", client=client)
    resp = provider.generate("x")

    assert resp.text == "Hello, world."


def test_generate_ignores_non_text_blocks():
    """Non-text blocks (e.g. ``tool_use``) are skipped in the flattened text."""
    client = MagicMock()

    msg = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "answer"
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    msg.content = [text_block, tool_block]
    msg.model = "m"
    msg.stop_reason = "end_turn"
    msg.usage.input_tokens = 1
    msg.usage.output_tokens = 1
    client.messages.create.return_value = msg

    provider = AnthropicProvider(api_key="fake", client=client)
    resp = provider.generate("x")

    assert resp.text == "answer"


def test_generate_handles_none_stop_reason():
    """``stop_reason`` may be ``None`` from the SDK; coerce to empty string."""
    client = MagicMock()
    client.messages.create.return_value = _mock_anthropic_message(stop_reason=None)
    provider = AnthropicProvider(api_key="fake", client=client)

    resp = provider.generate("x")
    assert resp.stop_reason == ""


# --------------------------------------------------------------------------- #
# make_default_provider                                                        #
# --------------------------------------------------------------------------- #


def test_make_default_provider_raises_without_key(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("PD_AGENT_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    settings = PDAgentSettings()
    with pytest.raises(ValueError, match="API key not configured"):
        make_default_provider(settings)


def test_make_default_provider_builds_from_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key-for-test")
    monkeypatch.setenv("PD_AGENT_ANTHROPIC_MODEL", "claude-test-model")
    monkeypatch.chdir(tmp_path)

    settings = PDAgentSettings()
    provider = make_default_provider(settings)

    assert isinstance(provider, AnthropicProvider)
    assert provider.model == "claude-test-model"


def test_make_default_provider_loads_default_settings_if_omitted(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-default-test")
    monkeypatch.chdir(tmp_path)

    provider = make_default_provider()

    assert isinstance(provider, AnthropicProvider)
    assert provider.model == "claude-sonnet-4-5"

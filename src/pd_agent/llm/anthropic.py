"""Anthropic Claude implementation of the LLM provider contract."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from anthropic import Anthropic

from pd_agent.llm.provider import LLMResponse

if TYPE_CHECKING:
    from pd_agent.config import PDAgentSettings

__all__ = ["AnthropicProvider", "make_default_provider"]


class AnthropicProvider:
    """Synchronous Anthropic Claude provider.

    Implements :class:`pd_agent.llm.LLMProvider`. Wraps the official
    ``anthropic`` Python SDK and flattens a single-turn ``messages.create``
    call into an :class:`LLMResponse`.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-4-5",
        client: Anthropic | None = None,
    ) -> None:
        self._model = model
        self._client = client if client is not None else Anthropic(api_key=api_key)

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system is not None:
            kwargs["system"] = system

        message = self._client.messages.create(**kwargs)

        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )

        return LLMResponse(
            text=text,
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            stop_reason=message.stop_reason or "",
        )


def make_default_provider(
    settings: PDAgentSettings | None = None,
) -> AnthropicProvider:
    """Build an :class:`AnthropicProvider` from :class:`PDAgentSettings`.

    Reads ``anthropic_api_key`` and ``anthropic_model`` from the settings
    object (loading default settings if not provided). Raises ``ValueError``
    if the API key is not configured.
    """
    from pd_agent.config import PDAgentSettings

    s = settings if settings is not None else PDAgentSettings()
    if s.anthropic_api_key is None:
        raise ValueError(
            "Anthropic API key not configured. Set ANTHROPIC_API_KEY in your "
            "environment or in a .env file (see .env.example)."
        )
    return AnthropicProvider(
        api_key=s.anthropic_api_key.get_secret_value(),
        model=s.anthropic_model,
    )

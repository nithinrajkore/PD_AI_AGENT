"""Vendor-agnostic LLM provider contract."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["LLMProvider", "LLMResponse"]


class LLMResponse(BaseModel):
    """Result of a single LLM generation call.

    Immutable. Captures the text, the model that produced it, and token
    usage for basic observability. Extra fields (tool calls, reasoning
    traces, etc.) can be added later without breaking the contract.
    """

    model_config = ConfigDict(frozen=True)

    text: str = Field(description="Full text of the generated response.")
    model: str = Field(description="Model identifier that produced the response.")
    input_tokens: int = Field(ge=0, description="Tokens consumed from the prompt.")
    output_tokens: int = Field(ge=0, description="Tokens generated.")
    stop_reason: str = Field(default="", description="Why generation stopped.")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for a synchronous LLM provider.

    Implementations must expose ``model`` and a ``generate`` method that
    takes a prompt (and optional system + generation knobs) and returns an
    :class:`LLMResponse`.
    """

    @property
    def model(self) -> str:
        """Identifier of the model this provider will use."""
        ...

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Synchronously generate a response from ``prompt``."""
        ...

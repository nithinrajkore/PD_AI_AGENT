"""LLM provider abstraction for pd-agent.

A minimal typed interface over LLM providers so that the rest of the
codebase can consume a single ``LLMProvider`` without caring which vendor
is behind it. Currently only Anthropic is implemented; OpenAI / Ollama can
be added later without touching consumers.
"""

from pd_agent.llm.anthropic import AnthropicProvider, make_default_provider
from pd_agent.llm.provider import LLMProvider, LLMResponse

__all__ = [
    "AnthropicProvider",
    "LLMProvider",
    "LLMResponse",
    "make_default_provider",
]

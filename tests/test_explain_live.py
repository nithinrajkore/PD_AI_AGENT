"""End-to-end test of `pd-agent explain` against a real Anthropic API.

This test is opt-in on three axes:

1. It is tagged with ``@pytest.mark.integration`` so the default
   ``uv run pytest`` does not pick it up. Run with ``-m integration`` to
   include it.
2. It is skipped unless ``PD_AGENT_RUN_LIVE_LLM=1`` is set in the
   environment. This prevents accidental LLM spend when a contributor
   merely types ``pytest -m integration``.
3. It is skipped if :class:`~pd_agent.config.PDAgentSettings` cannot
   resolve an ``ANTHROPIC_API_KEY`` (from env or ``.env``), giving a
   clearer message than a 401 from the API.

Expected cost per run with ``max_tokens=256`` and SPM metrics:
~$0.005 against ``claude-sonnet-4-5``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pd_agent.config import PDAgentSettings
from pd_agent.explain import explain_metrics
from pd_agent.flow.models import FlowMetrics

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("PD_AGENT_RUN_LIVE_LLM") != "1",
        reason="set PD_AGENT_RUN_LIVE_LLM=1 to opt into real-Anthropic tests",
    ),
]

FIXTURE_METRICS = Path(__file__).parent / "fixtures" / "spm_metrics.json"


def _require_api_key() -> None:
    settings = PDAgentSettings()
    if settings.anthropic_api_key is None:
        pytest.skip("ANTHROPIC_API_KEY is not set (env or .env). See .env.example.")


def test_explain_real_claude_on_spm_metrics(capsys: pytest.CaptureFixture[str]) -> None:
    """Call the real Anthropic API and sanity-check the response shape."""
    _require_api_key()
    assert FIXTURE_METRICS.is_file(), f"SPM metrics fixture missing at {FIXTURE_METRICS}"

    metrics = FlowMetrics.from_json_file(FIXTURE_METRICS)
    assert metrics.is_clean, "SPM fixture is expected to be clean"

    response = explain_metrics(metrics, max_tokens=256, temperature=0.0)

    assert response.text.strip(), "LLM returned empty text"
    assert response.model.startswith("claude"), f"unexpected model identifier: {response.model}"
    assert response.input_tokens > 0, "expected non-zero input tokens"
    assert response.output_tokens > 0, "expected non-zero output tokens"

    lowered = response.text.lower()
    signal_words = ("pass", "clean", "signoff", "timing", "setup", "hold")
    assert any(word in lowered for word in signal_words), (
        "LLM response did not reference any PD concept; possible prompt drift.\n"
        f"Response was:\n{response.text}"
    )

    with capsys.disabled():
        print("\n--- Claude response ---")
        print(response.text)
        print(
            f"--- model={response.model} "
            f"tokens={response.input_tokens} in / "
            f"{response.output_tokens} out ---"
        )

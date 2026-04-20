"""Tests for :mod:`pd_agent.explain`.

These tests never hit a real LLM; they either inject a fake provider or
mock :func:`pd_agent.explain.make_default_provider`.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from pytest_mock import MockerFixture

from pd_agent.explain import SYSTEM_PROMPT, build_user_prompt, explain_metrics
from pd_agent.flow.models import FlowMetrics
from pd_agent.llm import LLMResponse

FIXTURE_METRICS = Path(__file__).parent / "fixtures" / "spm_metrics.json"


def _clean_metrics() -> FlowMetrics:
    return FlowMetrics.from_json_file(FIXTURE_METRICS)


def _dirty_metrics() -> FlowMetrics:
    return FlowMetrics(
        instance_count=1000,
        die_area=2500.0,
        core_area=2000.0,
        timing_setup_ws=-0.5,
        timing_setup_wns=-0.5,
        timing_setup_tns=-12.3,
        timing_hold_ws=0.1,
        timing_hold_wns=0.0,
        timing_hold_tns=0.0,
        drc_errors_magic=4,
        drc_errors_klayout=0,
        lvs_errors=0,
        antenna_violating_nets=2,
        max_slew_violations=0,
        max_cap_violations=0,
        power_total=0.005,
    )


class TestBuildUserPrompt:
    def test_clean_design_reports_clean_true(self) -> None:
        prompt = build_user_prompt(_clean_metrics())
        assert "Overall clean: true" in prompt

    def test_includes_timing_numbers(self) -> None:
        metrics = _clean_metrics()
        prompt = build_user_prompt(metrics)
        assert "setup WS:" in prompt
        assert "hold  WS:" in prompt
        assert f"{metrics.timing_setup_ws:g} ns" in prompt

    def test_includes_violation_counts(self) -> None:
        prompt = build_user_prompt(_dirty_metrics())
        assert "DRC (Magic):    4" in prompt
        assert "Antenna nets:   2" in prompt
        assert "Overall clean: false" in prompt

    def test_marks_unmeasured_fields(self) -> None:
        prompt = build_user_prompt(FlowMetrics())
        assert "not measured" in prompt
        assert "Overall clean: true" in prompt

    def test_does_not_leak_newlines_in_single_fields(self) -> None:
        prompt = build_user_prompt(_clean_metrics())
        assert "\nOverall clean:" in prompt
        assert prompt.count("Overall clean:") == 1


class TestSystemPrompt:
    def test_mentions_openlane_context(self) -> None:
        assert "OpenLane" in SYSTEM_PROMPT
        assert "signoff" in SYSTEM_PROMPT.lower()


class TestExplainMetrics:
    def _fake_provider(self, text: str = "All green.") -> MagicMock:
        provider = MagicMock()
        provider.model = "fake-model"
        provider.generate.return_value = LLMResponse(
            text=text,
            model="fake-model",
            input_tokens=42,
            output_tokens=7,
            stop_reason="end_turn",
        )
        return provider

    def test_uses_injected_provider(self) -> None:
        provider = self._fake_provider("Design passes signoff.")
        response = explain_metrics(_clean_metrics(), provider=provider)
        assert response.text == "Design passes signoff."
        provider.generate.assert_called_once()

    def test_passes_system_prompt_and_user_prompt(self) -> None:
        provider = self._fake_provider()
        metrics = _clean_metrics()
        explain_metrics(metrics, provider=provider)
        _, kwargs = provider.generate.call_args
        assert kwargs["system"] == SYSTEM_PROMPT
        prompt_arg = provider.generate.call_args.args[0]
        assert "OpenLane" in prompt_arg
        assert "Overall clean: true" in prompt_arg

    def test_forwards_generation_knobs(self) -> None:
        provider = self._fake_provider()
        explain_metrics(_clean_metrics(), provider=provider, max_tokens=512, temperature=0.7)
        _, kwargs = provider.generate.call_args
        assert kwargs["max_tokens"] == 512
        assert kwargs["temperature"] == 0.7

    def test_default_provider_is_used_when_not_injected(self, mocker: MockerFixture) -> None:
        fake = self._fake_provider("Default-provider output.")
        mock_factory = mocker.patch("pd_agent.explain.make_default_provider", return_value=fake)
        response = explain_metrics(_clean_metrics())
        mock_factory.assert_called_once_with()
        assert response.text == "Default-provider output."

    def test_returns_response_unchanged(self) -> None:
        provider = self._fake_provider("Hello world.")
        response = explain_metrics(_clean_metrics(), provider=provider)
        assert isinstance(response, LLMResponse)
        assert response.model == "fake-model"
        assert response.total_tokens == 49

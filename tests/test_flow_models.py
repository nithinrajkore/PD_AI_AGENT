"""Tests for FlowMetrics and RunResult."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pd_agent.flow import FlowMetrics, RunResult

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "spm_metrics.json"


@pytest.fixture
def spm_metrics_dict() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture
def spm_metrics(spm_metrics_dict: dict) -> FlowMetrics:
    return FlowMetrics.from_dict(spm_metrics_dict)


class TestFlowMetricsParsing:
    def test_fixture_file_exists(self) -> None:
        assert FIXTURE_PATH.is_file(), f"fixture missing at {FIXTURE_PATH}"

    def test_loads_from_json_file(self) -> None:
        m = FlowMetrics.from_json_file(FIXTURE_PATH)
        assert isinstance(m, FlowMetrics)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            FlowMetrics.from_json_file(tmp_path / "nonexistent.json")

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json")
        with pytest.raises(json.JSONDecodeError):
            FlowMetrics.from_json_file(bad)


class TestFlowMetricsDesignInfo:
    def test_instance_count_positive(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.instance_count is not None
        assert spm_metrics.instance_count > 0

    def test_die_area_positive(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.die_area is not None
        assert spm_metrics.die_area > 0

    def test_core_area_le_die_area(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.core_area is not None
        assert spm_metrics.die_area is not None
        assert spm_metrics.core_area <= spm_metrics.die_area


class TestFlowMetricsTiming:
    def test_setup_slack_parsed(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.timing_setup_ws is not None

    def test_hold_slack_parsed(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.timing_hold_ws is not None

    def test_clean_spm_has_positive_setup_slack(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.timing_setup_ws is not None
        assert spm_metrics.timing_setup_ws > 0

    def test_clean_spm_has_positive_hold_slack(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.timing_hold_ws is not None
        assert spm_metrics.timing_hold_ws > 0


class TestFlowMetricsPower:
    def test_power_total_positive(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.power_total is not None
        assert spm_metrics.power_total > 0

    def test_power_breakdown_components_parsed(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.power_internal is not None
        assert spm_metrics.power_switching is not None
        assert spm_metrics.power_leakage is not None


class TestFlowMetricsSignoff:
    def test_drc_errors_zero(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.drc_errors_magic == 0
        assert spm_metrics.drc_errors_klayout == 0

    def test_lvs_errors_zero(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.lvs_errors == 0

    def test_antenna_violations_zero(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.antenna_violating_nets == 0

    def test_slew_cap_violations_zero(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.max_slew_violations == 0
        assert spm_metrics.max_cap_violations == 0

    def test_is_clean_true_for_spm(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.is_clean is True


class TestFlowMetricsRoute:
    def test_wirelength_parsed(self, spm_metrics: FlowMetrics) -> None:
        assert spm_metrics.wirelength is not None
        assert spm_metrics.wirelength > 0


class TestFlowMetricsRaw:
    def test_raw_has_many_keys(self, spm_metrics: FlowMetrics) -> None:
        assert len(spm_metrics.raw) > 200

    def test_raw_preserves_original(self, spm_metrics: FlowMetrics, spm_metrics_dict: dict) -> None:
        assert spm_metrics.raw == spm_metrics_dict


class TestFlowMetricsIsCleanEdgeCases:
    def test_clean_with_all_zero_violations(self) -> None:
        m = FlowMetrics(
            drc_errors_magic=0,
            drc_errors_klayout=0,
            lvs_errors=0,
            antenna_violating_nets=0,
            max_slew_violations=0,
            max_cap_violations=0,
            timing_setup_wns=0.0,
            timing_hold_wns=0.0,
        )
        assert m.is_clean is True

    def test_empty_metrics_are_clean(self) -> None:
        assert FlowMetrics().is_clean is True

    def test_unclean_with_drc_errors(self) -> None:
        assert FlowMetrics(drc_errors_magic=5).is_clean is False

    def test_unclean_with_lvs_errors(self) -> None:
        assert FlowMetrics(lvs_errors=1).is_clean is False

    def test_unclean_with_antenna_violations(self) -> None:
        assert FlowMetrics(antenna_violating_nets=3).is_clean is False

    def test_unclean_with_negative_setup_wns(self) -> None:
        assert FlowMetrics(timing_setup_wns=-0.5).is_clean is False

    def test_unclean_with_negative_hold_wns(self) -> None:
        assert FlowMetrics(timing_hold_wns=-0.1).is_clean is False


class TestFlowMetricsImmutability:
    def test_frozen(self, spm_metrics: FlowMetrics) -> None:
        with pytest.raises(ValidationError):
            spm_metrics.instance_count = 999  # type: ignore[misc]


class TestRunResultFromDir:
    def _seed_final_metrics(self, run_dir: Path) -> None:
        final = run_dir / "final"
        final.mkdir()
        (final / "metrics.json").write_text(FIXTURE_PATH.read_text())

    def test_discovers_final_metrics_json(self, tmp_path: Path) -> None:
        self._seed_final_metrics(tmp_path)
        r = RunResult.from_run_dir(tmp_path)
        assert r.metrics is not None
        assert r.metrics.is_clean is True

    def test_falls_back_to_nested_metrics(self, tmp_path: Path) -> None:
        nested = tmp_path / "42-some-stage"
        nested.mkdir()
        (nested / "metrics.json").write_text(FIXTURE_PATH.read_text())
        r = RunResult.from_run_dir(tmp_path)
        assert r.metrics is not None

    def test_missing_metrics_returns_none(self, tmp_path: Path) -> None:
        r = RunResult.from_run_dir(tmp_path)
        assert r.metrics is None


class TestRunResultSuccess:
    def _seed(self, run_dir: Path) -> None:
        final = run_dir / "final"
        final.mkdir()
        (final / "metrics.json").write_text(FIXTURE_PATH.read_text())

    def test_success_requires_exit_zero(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        r = RunResult.from_run_dir(tmp_path, exit_code=1)
        assert r.success is False

    def test_success_requires_metrics(self, tmp_path: Path) -> None:
        r = RunResult.from_run_dir(tmp_path, exit_code=0)
        assert r.success is False

    def test_success_with_clean_run(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        r = RunResult.from_run_dir(tmp_path, exit_code=0)
        assert r.success is True

    def test_success_false_when_dirty(self, tmp_path: Path) -> None:
        final = tmp_path / "final"
        final.mkdir()
        dirty = json.loads(FIXTURE_PATH.read_text())
        dirty["magic__drc_error__count"] = 7
        (final / "metrics.json").write_text(json.dumps(dirty))
        r = RunResult.from_run_dir(tmp_path, exit_code=0)
        assert r.success is False

    def test_command_preserved(self, tmp_path: Path) -> None:
        self._seed(tmp_path)
        r = RunResult.from_run_dir(tmp_path, exit_code=0, command=["openlane", "config.yaml"])
        assert r.command == ["openlane", "config.yaml"]

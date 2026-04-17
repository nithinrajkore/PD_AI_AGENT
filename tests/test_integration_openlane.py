"""End-to-end integration test against a real OpenLane installation.

This test is opt-in on two axes:

1. It is tagged with ``@pytest.mark.integration`` so the default
   ``uv run pytest`` does not pick it up. Run with ``-m integration`` to
   include it.
2. It is skipped unless ``PD_AGENT_RUN_INTEGRATION=1`` is set in the
   environment. This prevents accidental 2-3 minute runs when a contributor
   merely types ``pytest -m integration`` without realising the cost.
3. If neither condition gates it out, the test still auto-skips when the
   runner cannot locate an OpenLane invocation path on this machine.

Expected runtime: ~90-180 seconds on an M1/M2 Mac inside ``nix-shell``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pd_agent.flow import OpenLaneRunner, RunnerNotAvailableError

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("PD_AGENT_RUN_INTEGRATION") != "1",
        reason="set PD_AGENT_RUN_INTEGRATION=1 to opt into real-OpenLane tests",
    ),
]

REPO_ROOT = Path(__file__).resolve().parent.parent
SPM_CONFIG = REPO_ROOT / "designs" / "spm" / "config.yaml"


def _require_openlane(runner: OpenLaneRunner) -> None:
    try:
        runner.detect_mode()
    except RunnerNotAvailableError as exc:
        pytest.skip(f"OpenLane not reachable: {exc}")


def test_spm_end_to_end_clean_signoff() -> None:
    """Run the full OpenLane flow on SPM and assert all signoff checks pass."""
    assert SPM_CONFIG.is_file(), f"vendored SPM config missing at {SPM_CONFIG}"

    runner = OpenLaneRunner()
    _require_openlane(runner)

    result = runner.run(SPM_CONFIG, timeout=600)

    assert result.exit_code == 0, (
        f"OpenLane exited with {result.exit_code}.\nstderr tail:\n{result.stderr_tail}"
    )
    assert result.metrics is not None, (
        f"No metrics.json produced under {result.run_dir}. stdout tail:\n{result.stdout_tail}"
    )

    m = result.metrics
    assert (m.drc_errors_magic or 0) == 0, f"Magic DRC errors: {m.drc_errors_magic}"
    assert (m.drc_errors_klayout or 0) == 0, f"KLayout DRC errors: {m.drc_errors_klayout}"
    assert (m.lvs_errors or 0) == 0, f"LVS errors: {m.lvs_errors}"
    assert (m.antenna_violating_nets or 0) == 0, f"Antenna violations: {m.antenna_violating_nets}"
    assert (m.timing_setup_wns or 0.0) >= 0, f"Setup WNS is negative: {m.timing_setup_wns}"
    assert (m.timing_hold_wns or 0.0) >= 0, f"Hold WNS is negative: {m.timing_hold_wns}"
    assert m.is_clean, "FlowMetrics.is_clean is False despite individual checks passing"

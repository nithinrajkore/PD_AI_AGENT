"""Typed data models for OpenLane flow results.

OpenLane 2 emits a flat ``metrics.json`` with ~280 keys per run. This module
exposes the fields most relevant to physical-design signoff as typed Python
attributes on :class:`FlowMetrics`, while preserving the full original dict
in :attr:`FlowMetrics.raw` for power users.

:class:`RunResult` wraps a complete flow invocation: the run directory, the
subprocess exit status, parsed metrics, and output tails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["FlowMetrics", "RunResult"]


class FlowMetrics(BaseModel):
    """Curated subset of OpenLane's ``metrics.json`` with typed access.

    All curated fields are optional: OpenLane emits a different subset of
    metrics depending on which flow stages ran. Consumers should treat
    missing values as unknown, not as zero.
    """

    model_config = ConfigDict(frozen=True)

    instance_count: int | None = None
    instance_area: float | None = None
    die_area: float | None = None
    core_area: float | None = None

    timing_setup_ws: float | None = None
    timing_setup_wns: float | None = None
    timing_setup_tns: float | None = None
    timing_hold_ws: float | None = None
    timing_hold_wns: float | None = None
    timing_hold_tns: float | None = None
    clock_skew_worst_setup: float | None = None
    clock_skew_worst_hold: float | None = None

    power_total: float | None = None
    power_internal: float | None = None
    power_switching: float | None = None
    power_leakage: float | None = None

    antenna_violating_nets: int | None = None
    drc_errors_magic: int | None = None
    drc_errors_klayout: int | None = None
    lvs_errors: int | None = None
    max_slew_violations: int | None = None
    max_cap_violations: int | None = None

    wirelength: float | None = None
    wirelength_estimated: float | None = None
    wirelength_max: float | None = None

    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    KEY_MAP: ClassVar[dict[str, str]] = {
        "instance_count": "design__instance__count",
        "instance_area": "design__instance__area",
        "die_area": "design__die__area",
        "core_area": "design__core__area",
        "timing_setup_ws": "timing__setup__ws",
        "timing_setup_wns": "timing__setup__wns",
        "timing_setup_tns": "timing__setup__tns",
        "timing_hold_ws": "timing__hold__ws",
        "timing_hold_wns": "timing__hold__wns",
        "timing_hold_tns": "timing__hold__tns",
        "clock_skew_worst_setup": "clock__skew__worst_setup",
        "clock_skew_worst_hold": "clock__skew__worst_hold",
        "power_total": "power__total",
        "power_internal": "power__internal__total",
        "power_switching": "power__switching__total",
        "power_leakage": "power__leakage__total",
        "antenna_violating_nets": "antenna__violating__nets",
        "drc_errors_magic": "magic__drc_error__count",
        "drc_errors_klayout": "klayout__drc_error__count",
        "lvs_errors": "design__lvs_error__count",
        "max_slew_violations": "design__max_slew_violation__count",
        "max_cap_violations": "design__max_cap_violation__count",
        "wirelength": "route__wirelength",
        "wirelength_estimated": "route__wirelength__estimated",
        "wirelength_max": "route__wirelength__max",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FlowMetrics:
        """Build a :class:`FlowMetrics` from a flat metrics dict."""
        kwargs: dict[str, Any] = {"raw": dict(data)}
        for attr, key in cls.KEY_MAP.items():
            if key in data:
                kwargs[attr] = data[key]
        return cls(**kwargs)

    @classmethod
    def from_json_file(cls, path: Path) -> FlowMetrics:
        """Load a ``metrics.json`` file and parse it.

        Raises
        ------
        FileNotFoundError
            If ``path`` does not exist.
        json.JSONDecodeError
            If ``path`` is not valid JSON.
        """
        with Path(path).open() as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    @property
    def is_clean(self) -> bool:
        """Whether the design passes every physical-design signoff check.

        A design is "clean" when, for the metrics we track:

        - Zero DRC errors from both Magic and KLayout
        - Zero LVS errors
        - Zero antenna violations
        - Zero max-slew and max-cap violations
        - Non-negative setup and hold worst-negative-slack (WNS)

        Metrics that are ``None`` are treated as "not measured, not a
        violation" — consistent with how OpenLane omits irrelevant keys.
        """
        checks = (
            (self.drc_errors_magic or 0) == 0,
            (self.drc_errors_klayout or 0) == 0,
            (self.lvs_errors or 0) == 0,
            (self.antenna_violating_nets or 0) == 0,
            (self.max_slew_violations or 0) == 0,
            (self.max_cap_violations or 0) == 0,
            (self.timing_setup_wns or 0.0) >= 0,
            (self.timing_hold_wns or 0.0) >= 0,
        )
        return all(checks)


class RunResult(BaseModel):
    """End-to-end result of a single OpenLane flow invocation."""

    model_config = ConfigDict(frozen=True)

    run_dir: Path
    exit_code: int
    duration_seconds: float = 0.0
    metrics: FlowMetrics | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    command: list[str] = Field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether the flow ran to completion and the design is clean."""
        if self.exit_code != 0:
            return False
        if self.metrics is None:
            return False
        return self.metrics.is_clean

    @classmethod
    def from_run_dir(
        cls,
        run_dir: Path,
        *,
        exit_code: int = 0,
        duration_seconds: float = 0.0,
        stdout_tail: str = "",
        stderr_tail: str = "",
        command: list[str] | None = None,
    ) -> RunResult:
        """Construct a :class:`RunResult` by discovering artifacts in ``run_dir``.

        Searches for ``<run_dir>/final/metrics.json`` first (OpenLane 2's
        canonical location), then falls back to the first ``metrics.json``
        found anywhere under ``run_dir``. If none is found, ``metrics`` is
        left as ``None``.
        """
        run_dir = Path(run_dir)
        metrics: FlowMetrics | None = None
        final_metrics = run_dir / "final" / "metrics.json"
        if final_metrics.is_file():
            metrics = FlowMetrics.from_json_file(final_metrics)
        else:
            fallback = next(iter(run_dir.rglob("metrics.json")), None)
            if fallback is not None:
                metrics = FlowMetrics.from_json_file(fallback)
        return cls(
            run_dir=run_dir,
            exit_code=exit_code,
            duration_seconds=duration_seconds,
            metrics=metrics,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            command=list(command) if command is not None else [],
        )

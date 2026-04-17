"""Invoke the OpenLane 2 CLI and parse its output into a :class:`RunResult`.

The runner supports two invocation modes and auto-detects at runtime:

- ``direct``: ``openlane`` is on ``PATH`` (you are inside ``nix-shell``
  or have a system-wide install). The binary is invoked directly.
- ``nix-shell``: ``openlane`` is not on ``PATH`` but ``nix-shell`` is and
  ``settings.openlane2_repo`` exists. The runner wraps the invocation
  via ``nix-shell --run`` from the repo root.

The runner never *enters* or *installs* anything; it only shells out. See
``docs/setup.md`` for the environment prerequisites.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Literal

from pd_agent.config import PDAgentSettings
from pd_agent.flow.models import RunResult

__all__ = ["InvocationMode", "OpenLaneRunner", "RunnerNotAvailableError"]

InvocationMode = Literal["direct", "nix-shell"]


class RunnerNotAvailableError(RuntimeError):
    """Raised when neither a direct ``openlane`` binary nor ``nix-shell``
    with a valid ``openlane2_repo`` is reachable."""


def _tail(text: str, n_lines: int = 50) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    return "\n".join(lines[-n_lines:])


class OpenLaneRunner:
    """Wraps the OpenLane 2 CLI with subprocess execution and output parsing."""

    def __init__(
        self,
        *,
        openlane2_repo: Path | None = None,
        openlane_bin: str | None = None,
        settings: PDAgentSettings | None = None,
    ) -> None:
        resolved_settings = settings if settings is not None else PDAgentSettings()
        self._openlane2_repo = Path(
            openlane2_repo if openlane2_repo is not None else resolved_settings.openlane2_repo
        )
        self._openlane_bin = openlane_bin or resolved_settings.openlane_bin

    @property
    def openlane2_repo(self) -> Path:
        return self._openlane2_repo

    @property
    def openlane_bin(self) -> str:
        return self._openlane_bin

    def detect_mode(self) -> InvocationMode:
        """Return ``"direct"`` or ``"nix-shell"``.

        Raises
        ------
        RunnerNotAvailableError
            If neither invocation path is viable on this machine.
        """
        if shutil.which(self._openlane_bin) is not None:
            return "direct"
        if shutil.which("nix-shell") is not None and self._openlane2_repo.is_dir():
            return "nix-shell"
        raise RunnerNotAvailableError(
            f"Cannot invoke OpenLane: `{self._openlane_bin}` is not on PATH, "
            f"and no usable nix-shell + openlane2 repo at "
            f"{self._openlane2_repo!s}. See docs/setup.md."
        )

    def build_command(
        self,
        config_path: Path,
        *,
        extra_args: list[str] | None = None,
    ) -> tuple[list[str], Path]:
        """Construct the argv and cwd for the subprocess call.

        Returns
        -------
        tuple[list[str], Path]
            ``(argv, cwd)`` suitable for :func:`subprocess.run`.
        """
        mode = self.detect_mode()
        resolved_config = Path(config_path).resolve()
        extras = list(extra_args or [])
        if mode == "direct":
            argv = [self._openlane_bin, str(resolved_config), *extras]
            cwd = resolved_config.parent
        else:
            inner = shlex.join([self._openlane_bin, str(resolved_config), *extras])
            argv = ["nix-shell", "--run", inner]
            cwd = self._openlane2_repo
        return argv, cwd

    def run(
        self,
        config_path: Path,
        *,
        extra_args: list[str] | None = None,
        timeout: float | None = None,
    ) -> RunResult:
        """Execute OpenLane on ``config_path`` and return the parsed result.

        The run directory is discovered by looking at ``<config_parent>/runs/``
        for the newest ``RUN_*`` directory created after the subprocess
        completes. If none is found, :attr:`RunResult.run_dir` falls back to
        the config's parent directory and :attr:`RunResult.metrics` is ``None``.

        Raises
        ------
        subprocess.TimeoutExpired
            If ``timeout`` is given and the flow exceeds it.
        RunnerNotAvailableError
            If no invocation mode is viable (propagated from
            :meth:`detect_mode`).
        """
        resolved_config = Path(config_path).resolve()
        argv, cwd = self.build_command(resolved_config, extra_args=extra_args)
        started = time.monotonic()
        completed = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        duration = time.monotonic() - started
        run_dir = self._find_latest_run_dir(resolved_config.parent)
        return RunResult.from_run_dir(
            run_dir=run_dir if run_dir is not None else resolved_config.parent,
            exit_code=completed.returncode,
            duration_seconds=duration,
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
            command=argv,
        )

    @staticmethod
    def _find_latest_run_dir(design_dir: Path) -> Path | None:
        runs_dir = design_dir / "runs"
        if not runs_dir.is_dir():
            return None
        candidates = [p for p in runs_dir.glob("RUN_*") if p.is_dir()]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

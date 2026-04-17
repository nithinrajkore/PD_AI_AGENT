"""Tests for OpenLaneRunner."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from pd_agent.flow import OpenLaneRunner, RunnerNotAvailableError

FIXTURE_METRICS = Path(__file__).parent / "fixtures" / "spm_metrics.json"


def _which_for(openlane: str | None, nix_shell: str | None):
    def inner(name: str) -> str | None:
        if name == "openlane":
            return openlane
        if name == "nix-shell":
            return nix_shell
        return None

    return inner


@pytest.fixture
def fake_openlane2_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "openlane2"
    repo.mkdir()
    return repo


@pytest.fixture
def fake_design(tmp_path: Path) -> Path:
    design = tmp_path / "mydesign"
    design.mkdir()
    cfg = design / "config.yaml"
    cfg.write_text("DESIGN_NAME: x\n")
    return cfg


@pytest.fixture
def runner(fake_openlane2_repo: Path) -> OpenLaneRunner:
    return OpenLaneRunner(openlane2_repo=fake_openlane2_repo)


class TestDetectMode:
    def test_direct_when_openlane_on_path(
        self, runner: OpenLaneRunner, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        assert runner.detect_mode() == "direct"

    def test_nixshell_when_openlane_not_on_path(
        self, runner: OpenLaneRunner, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane=None, nix_shell="/usr/bin/nix-shell"),
        )
        assert runner.detect_mode() == "nix-shell"

    def test_raises_when_neither_available(
        self, runner: OpenLaneRunner, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane=None, nix_shell=None),
        )
        with pytest.raises(RunnerNotAvailableError):
            runner.detect_mode()

    def test_raises_when_nixshell_present_but_repo_missing(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        missing_repo = tmp_path / "does_not_exist"
        r = OpenLaneRunner(openlane2_repo=missing_repo)
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane=None, nix_shell="/usr/bin/nix-shell"),
        )
        with pytest.raises(RunnerNotAvailableError):
            r.detect_mode()


class TestBuildCommand:
    def test_direct_mode(
        self, runner: OpenLaneRunner, fake_design: Path, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        argv, cwd = runner.build_command(fake_design)
        assert argv == ["openlane", str(fake_design.resolve())]
        assert cwd == fake_design.resolve().parent

    def test_nixshell_mode(
        self,
        runner: OpenLaneRunner,
        fake_openlane2_repo: Path,
        fake_design: Path,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane=None, nix_shell="/usr/bin/nix-shell"),
        )
        argv, cwd = runner.build_command(fake_design)
        assert argv[0] == "nix-shell"
        assert argv[1] == "--run"
        assert "openlane" in argv[2]
        assert str(fake_design.resolve()) in argv[2]
        assert cwd == fake_openlane2_repo

    def test_extra_args_appended(
        self,
        runner: OpenLaneRunner,
        fake_design: Path,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        argv, _ = runner.build_command(fake_design, extra_args=["--run-tag", "smoke"])
        assert argv[-2:] == ["--run-tag", "smoke"]


class TestRun:
    def _seed_run_dir(self, design_dir: Path) -> Path:
        run = design_dir / "runs" / "RUN_2026-04-16_17-55-21"
        final = run / "final"
        final.mkdir(parents=True)
        (final / "metrics.json").write_text(FIXTURE_METRICS.read_text())
        return run

    def test_success_parses_metrics_and_reports_clean(
        self,
        runner: OpenLaneRunner,
        fake_design: Path,
        mocker: MockerFixture,
    ) -> None:
        self._seed_run_dir(fake_design.parent)
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        mocker.patch(
            "pd_agent.flow.runner.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="Flow complete.\n", stderr=""),
        )
        result = runner.run(fake_design)
        assert result.exit_code == 0
        assert result.metrics is not None
        assert result.metrics.is_clean is True
        assert result.success is True
        assert "Flow complete." in result.stdout_tail

    def test_nonzero_exit_propagated(
        self,
        runner: OpenLaneRunner,
        fake_design: Path,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        mocker.patch(
            "pd_agent.flow.runner.subprocess.run",
            return_value=MagicMock(returncode=2, stdout="", stderr="boom\n"),
        )
        result = runner.run(fake_design)
        assert result.exit_code == 2
        assert result.success is False
        assert "boom" in result.stderr_tail

    def test_timeout_propagated(
        self,
        runner: OpenLaneRunner,
        fake_design: Path,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        mocker.patch(
            "pd_agent.flow.runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["openlane"], timeout=5),
        )
        with pytest.raises(subprocess.TimeoutExpired):
            runner.run(fake_design, timeout=5)

    def test_missing_run_dir_falls_back_to_design_dir(
        self,
        runner: OpenLaneRunner,
        fake_design: Path,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        mocker.patch(
            "pd_agent.flow.runner.subprocess.run",
            return_value=MagicMock(returncode=1, stdout="", stderr=""),
        )
        result = runner.run(fake_design)
        assert result.run_dir == fake_design.resolve().parent
        assert result.metrics is None

    def test_stdout_and_stderr_tails_truncated_to_50_lines(
        self,
        runner: OpenLaneRunner,
        fake_design: Path,
        mocker: MockerFixture,
    ) -> None:
        long_stdout = "\n".join(f"line {i}" for i in range(100))
        long_stderr = "\n".join(f"err {i}" for i in range(80))
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        mocker.patch(
            "pd_agent.flow.runner.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=long_stdout, stderr=long_stderr),
        )
        result = runner.run(fake_design)
        assert result.stdout_tail.count("\n") == 49
        assert result.stdout_tail.startswith("line 50")
        assert result.stderr_tail.count("\n") == 49
        assert result.stderr_tail.startswith("err 30")

    def test_latest_run_dir_selected_by_mtime(
        self,
        runner: OpenLaneRunner,
        fake_design: Path,
        mocker: MockerFixture,
    ) -> None:
        import os

        runs = fake_design.parent / "runs"
        older = runs / "RUN_older"
        newer = runs / "RUN_newer"
        for d in (older, newer):
            (d / "final").mkdir(parents=True)
            (d / "final" / "metrics.json").write_text(FIXTURE_METRICS.read_text())
        os.utime(older, (1_700_000_000, 1_700_000_000))
        os.utime(newer, (1_800_000_000, 1_800_000_000))

        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        mocker.patch(
            "pd_agent.flow.runner.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        )
        result = runner.run(fake_design)
        assert result.run_dir == newer

    def test_command_recorded_in_result(
        self,
        runner: OpenLaneRunner,
        fake_design: Path,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane="/usr/bin/openlane", nix_shell=None),
        )
        mocker.patch(
            "pd_agent.flow.runner.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        )
        result = runner.run(fake_design)
        assert result.command[0] == "openlane"
        assert str(fake_design.resolve()) in result.command


class TestDefaults:
    def test_uses_settings_defaults_when_no_args(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which_for(openlane=None, nix_shell=None),
        )
        r = OpenLaneRunner()
        assert r.openlane_bin == "openlane"
        assert r.openlane2_repo.name == "openlane2"

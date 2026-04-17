"""Tests for the pd-agent CLI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from pd_agent import __version__
from pd_agent.cli import app

FIXTURE_METRICS = Path(__file__).parent / "fixtures" / "spm_metrics.json"


def _which(openlane: str | None, nix_shell: str | None):
    def inner(name: str) -> str | None:
        if name == "openlane":
            return openlane
        if name == "nix-shell":
            return nix_shell
        return None

    return inner


@pytest.fixture
def cli() -> CliRunner:
    return CliRunner()


class TestVersion:
    def test_long_flag(self, cli: CliRunner) -> None:
        result = cli.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_short_flag(self, cli: CliRunner) -> None:
        result = cli.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert __version__ in result.stdout


class TestInfo:
    def test_reports_direct_mode(
        self, cli: CliRunner, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which(openlane="/usr/bin/openlane", nix_shell=None),
        )
        result = cli.invoke(app, ["info", "--openlane-repo", str(tmp_path)])
        assert result.exit_code == 0
        assert "direct" in result.stdout.lower()

    def test_reports_unavailable_without_failing(
        self, cli: CliRunner, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which(openlane=None, nix_shell=None),
        )
        result = cli.invoke(app, ["info", "--openlane-repo", str(tmp_path / "nope")])
        assert result.exit_code == 0
        assert "unavailable" in result.stdout.lower()


class TestMetrics:
    def test_from_json_file(self, cli: CliRunner) -> None:
        result = cli.invoke(app, ["metrics", str(FIXTURE_METRICS)])
        assert result.exit_code == 0
        assert "clean" in result.stdout.lower()

    def test_from_run_dir(self, cli: CliRunner, tmp_path: Path) -> None:
        final = tmp_path / "final"
        final.mkdir()
        (final / "metrics.json").write_text(FIXTURE_METRICS.read_text())
        result = cli.invoke(app, ["metrics", str(tmp_path)])
        assert result.exit_code == 0
        assert "clean" in result.stdout.lower()

    def test_missing_errors(self, cli: CliRunner, tmp_path: Path) -> None:
        result = cli.invoke(app, ["metrics", str(tmp_path)])
        assert result.exit_code != 0


class TestRun:
    def test_requires_design_or_config(self, cli: CliRunner, tmp_path: Path) -> None:
        result = cli.invoke(app, ["run"], catch_exceptions=False)
        assert result.exit_code != 0

    def test_rejects_both_flags(self, cli: CliRunner, tmp_path: Path) -> None:
        result = cli.invoke(app, ["run", "--design", "spm", "--config", str(tmp_path / "c.yaml")])
        assert result.exit_code != 0

    def test_config_missing_errors(self, cli: CliRunner, tmp_path: Path) -> None:
        result = cli.invoke(app, ["run", "--config", str(tmp_path / "missing.yaml")])
        assert result.exit_code != 0

    def test_design_missing_errors(
        self, cli: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = cli.invoke(app, ["run", "--design", "nonexistent"])
        assert result.exit_code != 0

    def test_successful_run_with_mocks(
        self, cli: CliRunner, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("DESIGN_NAME: x\n")
        run = tmp_path / "runs" / "RUN_TEST"
        (run / "final").mkdir(parents=True)
        (run / "final" / "metrics.json").write_text(FIXTURE_METRICS.read_text())

        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which(openlane="/usr/bin/openlane", nix_shell=None),
        )
        mocker.patch(
            "pd_agent.flow.runner.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="Flow complete.", stderr=""),
        )
        result = cli.invoke(app, ["run", "--config", str(cfg)])
        assert result.exit_code == 0, result.stdout

    def test_runner_not_available_exits_with_error(
        self, cli: CliRunner, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("DESIGN_NAME: x\n")
        mocker.patch(
            "pd_agent.flow.runner.shutil.which",
            side_effect=_which(openlane=None, nix_shell=None),
        )
        result = cli.invoke(
            app,
            [
                "run",
                "--config",
                str(cfg),
                "--openlane-repo",
                str(tmp_path / "no-repo"),
            ],
        )
        assert result.exit_code == 1

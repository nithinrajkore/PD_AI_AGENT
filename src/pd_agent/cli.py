"""Command-line interface for pd-agent, built on Typer.

Subcommands
-----------

``pd-agent run``
    Execute the OpenLane flow on a design or explicit config file.

``pd-agent metrics``
    Print parsed metrics from an existing run directory or ``metrics.json``.

``pd-agent explain``
    Use an LLM to describe the metrics in plain English.

``pd-agent info``
    Show the resolved configuration and detected invocation mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pd_agent import __version__
from pd_agent.config import PDAgentSettings
from pd_agent.explain import explain_metrics
from pd_agent.flow import (
    FlowMetrics,
    OpenLaneRunner,
    RunnerNotAvailableError,
    RunResult,
)

__all__ = ["app"]

app = typer.Typer(
    name="pd-agent",
    help="AI agent for open-source semiconductor physical design flow orchestration.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pd-agent {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            is_eager=True,
            callback=_version_callback,
        ),
    ] = False,
) -> None:
    """Root entrypoint."""


def _resolve_config(design: str | None, config: Path | None) -> Path:
    if design is not None and config is not None:
        err_console.print(
            "[bold red]Error:[/bold red] pass only one of --design or --config, not both."
        )
        raise typer.Exit(code=2)
    if design is None and config is None:
        err_console.print("[bold red]Error:[/bold red] provide --design NAME or --config PATH.")
        raise typer.Exit(code=2)
    if config is not None:
        if not config.is_file():
            err_console.print(f"[bold red]Error:[/bold red] config not found: {config}")
            raise typer.Exit(code=2)
        return config

    designs_root = Path("designs")
    candidate = designs_root / str(design) / "config.yaml"
    if not candidate.is_file():
        available: list[str] = []
        if designs_root.is_dir():
            available = sorted(p.name for p in designs_root.iterdir() if p.is_dir())
        err_console.print(
            f"[bold red]Error:[/bold red] design '{design}' not found at {candidate}.\n"
            f"Available designs: {available or '(none)'}"
        )
        raise typer.Exit(code=2)
    return candidate


def _format_metric(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _print_metrics(m: FlowMetrics) -> None:
    table = Table(title="Flow Metrics", title_style="bold cyan")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    rows: list[tuple[str, object]] = [
        ("design.instance_count", m.instance_count),
        ("design.die_area (um^2)", m.die_area),
        ("design.core_area (um^2)", m.core_area),
        ("timing.setup.ws (ns)", m.timing_setup_ws),
        ("timing.setup.wns (ns)", m.timing_setup_wns),
        ("timing.setup.tns (ns)", m.timing_setup_tns),
        ("timing.hold.ws (ns)", m.timing_hold_ws),
        ("timing.hold.wns (ns)", m.timing_hold_wns),
        ("timing.hold.tns (ns)", m.timing_hold_tns),
        ("clock.skew.setup", m.clock_skew_worst_setup),
        ("power.total (W)", m.power_total),
        ("drc.magic", m.drc_errors_magic),
        ("drc.klayout", m.drc_errors_klayout),
        ("lvs.errors", m.lvs_errors),
        ("antenna.violating_nets", m.antenna_violating_nets),
        ("route.wirelength", m.wirelength),
    ]
    for name, value in rows:
        table.add_row(name, _format_metric(value))
    console.print(table)

    if m.is_clean:
        console.print("[bold green]✓ Design is clean — all signoff checks pass.[/bold green]")
    else:
        console.print("[bold red]✗ Design has signoff issues.[/bold red]")


def _print_run_summary(result: RunResult) -> None:
    border = "green" if result.success else "red"
    body = (
        f"exit_code: {result.exit_code}\n"
        f"duration:  {result.duration_seconds:.1f}s\n"
        f"run_dir:   {result.run_dir}"
    )
    console.print(Panel.fit(body, title="Run Summary", border_style=border))
    if result.metrics is not None:
        _print_metrics(result.metrics)
    if not result.success and result.stderr_tail:
        console.print(Panel(result.stderr_tail, title="stderr (tail)", border_style="red"))


def _load_metrics(path: Path) -> FlowMetrics:
    """Load :class:`FlowMetrics` from a ``metrics.json`` file or a run directory.

    Exits with code 1 via ``typer.Exit`` if no metrics can be discovered at
    ``path``.
    """
    metrics: FlowMetrics | None = None
    if path.is_file() and path.suffix.lower() == ".json":
        metrics = FlowMetrics.from_json_file(path)
    elif path.is_dir():
        metrics = RunResult.from_run_dir(path).metrics

    if metrics is None:
        err_console.print(f"[bold red]Error:[/bold red] no metrics.json found at or below {path}")
        raise typer.Exit(code=1)
    return metrics


@app.command("info")
def cmd_info(
    openlane_repo: Annotated[
        Path | None,
        typer.Option(
            "--openlane-repo",
            help="Path to the openlane2 clone (overrides PD_AGENT_OPENLANE2_REPO).",
            envvar="PD_AGENT_OPENLANE2_REPO",
        ),
    ] = None,
) -> None:
    """Show resolved configuration and detected OpenLane invocation mode."""
    settings = PDAgentSettings()
    runner = OpenLaneRunner(
        openlane2_repo=openlane_repo if openlane_repo is not None else settings.openlane2_repo
    )

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("key", style="cyan", no_wrap=True)
    table.add_column("value")
    table.add_row("pd-agent version", __version__)
    table.add_row("openlane2_repo", str(runner.openlane2_repo))
    table.add_row("openlane_bin", runner.openlane_bin)

    try:
        mode = runner.detect_mode()
        table.add_row("invocation mode", f"[bold green]{mode}[/bold green]")
    except RunnerNotAvailableError as exc:
        table.add_row("invocation mode", "[bold red]unavailable[/bold red]")
        table.add_row("reason", str(exc))

    console.print(Panel(table, title="pd-agent configuration", title_align="left"))


@app.command("run")
def cmd_run(
    design: Annotated[
        str | None,
        typer.Option(
            "--design",
            "-d",
            help="Design name (resolves to designs/<name>/config.yaml in the cwd).",
        ),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Explicit path to an OpenLane config.yaml (overrides --design).",
        ),
    ] = None,
    openlane_repo: Annotated[
        Path | None,
        typer.Option(
            "--openlane-repo",
            help="Path to the openlane2 clone (overrides PD_AGENT_OPENLANE2_REPO).",
            envvar="PD_AGENT_OPENLANE2_REPO",
        ),
    ] = None,
    timeout: Annotated[
        float | None,
        typer.Option(
            "--timeout",
            help="Abort the flow after this many seconds.",
        ),
    ] = None,
) -> None:
    """Run the OpenLane physical-design flow on a design or config file."""
    config_path = _resolve_config(design=design, config=config)
    runner = OpenLaneRunner(openlane2_repo=openlane_repo)
    console.print(f"[bold]Running OpenLane on[/bold] {config_path}")
    try:
        result = runner.run(config_path, timeout=timeout)
    except RunnerNotAvailableError as exc:
        err_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    _print_run_summary(result)
    if not result.success:
        raise typer.Exit(code=1)


@app.command("metrics")
def cmd_metrics(
    path: Annotated[
        Path,
        typer.Argument(
            help="Path to a run directory OR a metrics.json file.",
        ),
    ],
) -> None:
    """Print parsed metrics from an existing run."""
    _print_metrics(_load_metrics(path))


@app.command("explain")
def cmd_explain(
    path: Annotated[
        Path,
        typer.Argument(
            help="Path to a run directory OR a metrics.json file.",
        ),
    ],
    max_tokens: Annotated[
        int,
        typer.Option(
            "--max-tokens",
            help="Maximum number of tokens the LLM may produce.",
        ),
    ] = 1024,
    temperature: Annotated[
        float,
        typer.Option(
            "--temperature",
            help="LLM sampling temperature (0.0 = deterministic).",
        ),
    ] = 0.2,
) -> None:
    """Use an LLM to explain flow metrics in plain English.

    Requires ``ANTHROPIC_API_KEY`` to be set in the environment or in a
    ``.env`` file. Reads the same ``metrics.json`` / run-directory input as
    ``pd-agent metrics``.
    """
    metrics = _load_metrics(path)
    try:
        response = explain_metrics(metrics, max_tokens=max_tokens, temperature=temperature)
    except ValueError as exc:
        err_console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print(Panel(response.text, title="Explanation", border_style="cyan"))
    console.print(
        f"[dim]model: {response.model}  |  "
        f"tokens: {response.input_tokens} in / "
        f"{response.output_tokens} out ({response.total_tokens} total)[/dim]"
    )

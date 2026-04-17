"""Command-line interface for pd-agent, built on Typer."""

from typing import Annotated

import typer

from pd_agent import __version__

app = typer.Typer(
    name="pd-agent",
    help="AI agent for open-source semiconductor physical design flow orchestration.",
    no_args_is_help=True,
    add_completion=False,
)


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
    """Root entrypoint. Subcommands will be registered in later phases."""


__all__ = ["app"]

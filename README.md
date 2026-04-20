# PD_AI_Agent

AI agent for open-source semiconductor physical design (PD) flow orchestration.

## Status

**v0.1.0 in progress** — minimal OpenLane 2 runner is usable end-to-end on
the vendored SPM design. LLM wrapping, RAG, observability, and multi-agent
coordination come in later releases.

## Roadmap

- [x] v0.1.0 — Repo bootstrap, Python skeleton, OpenLane 2 runner, CLI, SPM integration test
- [ ] v0.2.0 — LLM-driven agent wrapping the runner
- [ ] v0.3.0 — RAG over PD documentation
- [ ] v0.4.0 — Observability (timing slack, congestion, runtime metrics over time)
- [ ] v0.5.0 — Multi-agent (timing / placement / routing / DRC / power)

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenLane 2 via Nix — see [docs/setup.md](docs/setup.md) for install + cachix
  setup. Everything else in this README works without OpenLane (except the
  actual flow).

## Quickstart

```bash
# Install Python deps into .venv
uv sync

# Sanity-check the CLI
uv run pd-agent --version
uv run pd-agent info          # shows detected OpenLane invocation mode
uv run pd-agent --help

# Run the SPM example end-to-end (takes ~2-3 minutes, requires OpenLane)
uv run pd-agent run --design spm

# Inspect metrics from any run directory (or a metrics.json)
uv run pd-agent metrics designs/spm/runs/RUN_<timestamp>/

# Get a plain-English explanation of those metrics (needs ANTHROPIC_API_KEY)
uv run pd-agent explain designs/spm/runs/RUN_<timestamp>/
```

## Development

```bash
# Fast unit tests (~1 second)
uv run pytest

# Include the real-OpenLane integration test (~2-3 minutes)
PD_AGENT_RUN_INTEGRATION=1 uv run pytest -m integration

# Lint + format
uv run ruff check .
uv run ruff format .
```

## Configuration

Runtime settings are read from environment variables prefixed
`PD_AGENT_`, or from a `.env` file in the working directory:

| Variable | Default | Purpose |
|---|---|---|
| `PD_AGENT_OPENLANE2_REPO` | `~/Documents/Projects/openlane2` | Path to the local openlane2 clone used for `nix-shell` invocation |
| `PD_AGENT_OPENLANE_BIN` | `openlane` | Name of the OpenLane CLI binary |
| `ANTHROPIC_API_KEY` *(or `PD_AGENT_ANTHROPIC_API_KEY`)* | *(unset)* | Anthropic API key for LLM-powered features. The unprefixed name takes precedence. |
| `PD_AGENT_ANTHROPIC_MODEL` | `claude-sonnet-4-5` | Claude model used for LLM calls |
| `PD_AGENT_RUN_INTEGRATION` | *(unset)* | Set to `1` to opt into real-OpenLane integration tests |

CLI flags (`--openlane-repo`, `--config`, `--design`, `--timeout`) override
env-var values per invocation.

### Local `.env` setup

For features that need an API key (e.g. `pd-agent explain`), copy the
template and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` and set `ANTHROPIC_API_KEY` — get a key from
<https://console.anthropic.com/> after adding a small amount of credit
under Billing. The `.env` file is git-ignored; never commit it.

## Repository layout

```
src/pd_agent/
  cli.py           # Typer CLI: run / metrics / explain / info
  config.py        # Pydantic-settings
  explain.py       # Prompt construction + explain_metrics()
  flow/
    runner.py      # OpenLaneRunner — subprocess + nix-shell auto-detection
    models.py      # FlowMetrics, RunResult
  llm/
    provider.py    # LLMProvider protocol, LLMResponse model
    anthropic.py   # Anthropic Claude implementation
designs/
  spm/             # Vendored 32-bit serial/parallel multiplier (Apache-2.0)
tests/             # Unit tests (fast) + opt-in integration test
docs/setup.md      # Host setup: Nix, OpenLane, cachix
```

## License

MIT — see [LICENSE](LICENSE). Vendored third-party content retains its
original license (see `designs/spm/README.md`).

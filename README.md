# PD_AI_Agent

AI agent for open-source semiconductor physical design (PD) flow orchestration.

## Status

Early development — Step 1 (bootstrap) in progress. See roadmap below.

## Roadmap

- [ ] v0.1.0 — Repo bootstrap, Python skeleton, minimal OpenLane runner
- [ ] v0.2.0 — LLM-driven agent wrapping the runner
- [ ] v0.3.0 — RAG over PD documentation
- [ ] v0.4.0 — Observability (timing slack, congestion, runtime metrics)
- [ ] v0.5.0 — Multi-agent (timing / placement / routing / DRC / power)

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker Desktop (for OpenLane, added in later steps)

## Development

```bash
# Install deps (including dev tools)
uv sync

# Run tests
uv run pytest

# Lint + format
uv run ruff check .
uv run ruff format .

# Run the package
uv run python -m pd_agent
```

## License

MIT — see [LICENSE](LICENSE).

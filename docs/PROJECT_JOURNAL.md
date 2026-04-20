# PD_AI_Agent — Project Journal

> A living record of what's been built in this repository, why each piece
> exists, and how it was done. Updated at every phase boundary.
>
> **Audience**: future-you, future contributors, and anyone trying to
> understand the repository six months from now. Written to be readable
> without prior context on this specific project.

---

## Current state (as of 2026-04-20)

- **Latest release**: v0.2.0.
- **Active branch**: `dev` (integration branch for v0.3.0 work).
- **What works today**: everything from v0.1.0 (OpenLane 2 flow on SPM)
  **plus** `pd-agent explain <path>` — hand it a `metrics.json` or a
  run directory, and Anthropic Claude returns a plain-English summary
  of timing, violations, area, and power. Unit tests (105 passing, 97%
  coverage) run in under two seconds; two opt-in integration tests
  exist (real-OpenLane, real-Anthropic) that the default suite skips.
  Continuous integration runs lint + format + test on every PR via
  GitHub Actions.
- **What doesn't work yet**: RAG (retrieval-augmented generation over
  PD docs), tool-use (letting the LLM actually drive `OpenLaneRunner`),
  observability (run-to-run metric tracking), and multi-agent
  coordination. Those arrive in v0.3.0 and later.

## Roadmap

| Version | Theme | Status |
|---|---|---|
| v0.1.0 | Repo bootstrap, Python skeleton, OpenLane 2 runner, CLI, SPM integration | **Released 2026-04-17** |
| v0.2.0 | LLM-driven `pd-agent explain` + CI + Anthropic provider abstraction | **Released 2026-04-20** |
| v0.3.0 | RAG over PD documentation, tool-use for running flows | Next |
| v0.4.0 | Observability — metric tracking across runs | Planned |
| v0.5.0 | Multi-agent coordination (timing / placement / routing / DRC / power) | Planned |

---

# Phase 1 — Bootstrap and minimal OpenLane runner (v0.1.0)

- **Released**: 2026-04-17
- **Tag**: `v0.1.0` (annotated, commit `b031df3`)
- **GitHub Release**: <https://github.com/nithinrajkore/PD_AI_AGENT/releases/tag/v0.1.0>
- **Pull requests merged**: #1, #2, #3, #4
- **Net change to main**: +2961 lines across 26 files, −1 line

## Phase 1 at a glance

Phase 1 built the **foundation that every later phase will build on**. No
AI features yet — the focus was on creating a repository that is
industry-shaped (proper git workflow, typed code, real tests) and a
Python package that can actually drive the OpenLane 2 physical-design
flow end-to-end.

The guiding principle was **"make each phase independently useful"**.
After Phase 1 you have a working Python CLI that runs a real chip
design. You do not need to wait for Phase 2 for anything in Phase 1 to
be valuable.

## Architecture at the end of Phase 1

```
┌─────────────────────────────────────────────────────────────────────┐
│ You, at a terminal                                                  │
│    $ pd-agent run --design spm                                      │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ src/pd_agent/cli.py (Typer)                                         │
│   • pd-agent run / metrics / info subcommands                       │
│   • Rich colored tables and panels                                  │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ src/pd_agent/flow/runner.py (OpenLaneRunner)                        │
│   • detect_mode(): direct vs nix-shell                              │
│   • build_command(): subprocess argv + cwd                          │
│   • run(): execute + parse + return RunResult                       │
└─────────────────────────────────────────────────────────────────────┘
                             │  subprocess
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ openlane (C++/Python toolchain, external)                           │
│   • synthesis → floorplan → placement → CTS → routing → signoff     │
│   • writes designs/<name>/runs/RUN_<ts>/final/metrics.json          │
└─────────────────────────────────────────────────────────────────────┘
                             │  metrics.json (~280 keys)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ src/pd_agent/flow/models.py                                         │
│   • FlowMetrics: ~20 curated fields + .raw dict + is_clean          │
│   • RunResult: run_dir + exit_code + metrics + stdout/stderr tails  │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Terminal output: colored metrics table + ✓ clean / ✗ issues         │
└─────────────────────────────────────────────────────────────────────┘
```

## Phase 1A — Git and GitHub bootstrap

**Goal**: establish an industry-standard git workflow before writing any
code. Branch naming, protection rules, commit style, and remote layout
should be right from commit #1, because retrofitting them later is
painful.

### What shipped

- GitHub repo created: `nithinrajkore/PD_AI_AGENT`.
- **Three-branch model** established:
  - `main` — stable, release-tagged only
  - `dev` — integration branch for completed features
  - `feature/*`, `fix/*`, `chore/*`, `docs/*` — short-lived work branches
- **Branch protection** on `main` and `dev` via GitHub Rulesets:
  - Require pull request before merging
  - Require passing status checks (no CI yet, so no required checks)
  - Require conversation resolution
  - Restrict merges to squash-only on `main` (this decision resurfaced
    during R2 — see "Notable decisions")
- `.gitignore` covering Python caches, `uv` virtualenvs, OpenLane run
  artifacts (`runs/`, `designs/*/runs/`, `*.gds`, `*.def`, `*.lef`,
  `*.rpt`, etc.), macOS noise, IDE files, and secrets
- `README.md` — project description, roadmap, quickstart
- `LICENSE` — MIT

### Branch-naming convention

| Prefix | Meaning | Example |
|---|---|---|
| `feat/` | New feature | `feat/openlane-runner` |
| `fix/` | Bug fix | `fix/metrics-none-handling` |
| `chore/` | Tooling, deps, config | `chore/py-skeleton` |
| `docs/` | Documentation only | `docs/setup.md` |

### Commit message convention

[Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short description>

<optional longer body>
```

Types used so far: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`,
`release`.

Examples from the actual history:

- `chore: initialize repository`
- `chore: Python project skeleton with uv, ruff, pytest`
- `docs: add environment setup guide for OpenLane 2 on macOS`
- `feat(flow): OpenLane 2 runner, CLI, and SPM integration test`
- `release: v0.1.0 — OpenLane runner, CLI, and SPM integration`

## Phase 1B — Python project skeleton (PR #1)

**Goal**: a minimal but production-shaped Python package, ready for real
code to land in Phase 1D.

### What shipped

- `pyproject.toml` with `hatchling` build backend, project metadata,
  Python 3.12+ requirement, ruff + pytest configuration
- `src/pd_agent/` package with `__init__.py`, `__main__.py`, and a
  `py.typed` marker (PEP 561, signals to other tools that we ship type
  hints)
- `uv` chosen as the package manager (selected over Poetry and
  pip+venv). Gives us `.venv/` creation, dependency resolution,
  lockfile, and console-script installation in one tool
- `ruff` configured for both linting and formatting (replaces
  black + isort + flake8)
- `pytest` + `pytest-cov` configured with coverage output
- `tests/test_smoke.py` — two trivial tests verifying import and version
  string (exists to prove the test runner works, not to test anything
  meaningful)
- `.python-version` file pinning 3.12

### Notable decisions

- **`src/` layout over flat layout**: prevents accidental imports from
  the project root, forces tests to use the installed package exactly as
  end users will.
- **`uv` over Poetry**: faster, simpler, written in Rust, and the
  recommended modern default. Compatible with any `pyproject.toml`.
- **`ruff format` over black**: one tool for lint + format, zero
  configuration overhead, actively developed.

## Phase 1C — OpenLane 2 environment setup (PR #2)

**Goal**: document how to install OpenLane 2 reproducibly on macOS.
This phase is **documentation only** — no Python code changed.

### What shipped

- `docs/setup.md` — step-by-step install guide:
  1. Install Nix using the Determinate Systems installer with the
     OpenLane cachix binary cache pre-configured (avoids a 6+ hour
     from-source compile)
  2. Clone `openlane2` as a **sibling** directory to this repo
     (not inside it, not as a submodule)
  3. Enter `nix-shell` once (~7 GB one-time download of pre-built
     EDA binaries: OpenROAD, Yosys, Magic, Netgen, KLayout)
  4. Smoke-test with `openlane --smoke-test`
  5. Run the upstream SPM example manually to verify

### Notable decisions

- **Sibling repo over submodule/vendoring**: OpenLane is ~1 GB and
  actively developed. Submodules are fragile. Vendoring the whole thing
  would bloat git history enormously. A sibling clone is the standard
  pattern.
- **Nix + cachix over Docker**: OpenLane 2's canonical install path on
  macOS is Nix. Docker works for OpenLane 1 but adds an extra VM layer
  and performance cost on Apple Silicon. Nix gives us reproducible
  binaries without the VM.
- **Assume macOS**: the primary development target. Linux users can
  follow roughly the same steps; Windows users need WSL2 (not
  documented here).

### Why this matters for later phases

Every Python file in Phase 1D assumes OpenLane is reachable either
because `openlane` is on `PATH` (you are inside `nix-shell`) OR because
the `openlane2` repo exists at a known location (so the runner can wrap
calls in `nix-shell --run` for you). `docs/setup.md` is the contract
that makes both paths work.

## Phase 1D — Python runner (PR #3)

**Goal**: write the Python package that actually drives OpenLane. This
is where the interesting code lives.

Split into five sub-commits (1D-a through 1D-e), each independently
reviewable. In PR #3 they were **squashed into one commit on `dev`** to
keep `dev`'s history readable.

### 1D-a — runtime dependencies and entrypoint wiring

Only `pyproject.toml` changed. Added:

- **Runtime**: `pydantic`, `pydantic-settings`, `typer`, `rich`
- **Dev**: `pytest-mock`
- **Console script**: `pd-agent = "pd_agent.cli:app"` — after
  `uv sync`, the `pd-agent` command is on your PATH
- **pytest marker**: `integration`, for opt-in slow tests

### 1D-b — data models (`src/pd_agent/flow/models.py`)

Two Pydantic classes turn OpenLane's raw `metrics.json` (~280 keys)
into typed Python objects.

#### `FlowMetrics`

- ~20 **curated typed fields** for the most-used metrics
  (`instance_count`, `timing_setup_ws`, `drc_errors_magic`, etc.)
- A **`.raw` dict** containing the full 280-key JSON for everything not
  curated
- A **`KEY_MAP`** class dictionary translating JSON names
  (`timing__setup__ws`) to Python attribute names (`timing_setup_ws`)
- Class methods `from_dict(data)` and `from_json_file(path)` for
  construction
- A **`is_clean` property** that collapses all signoff checks into one
  boolean: zero DRC errors (Magic + KLayout), zero LVS errors, zero
  antenna violations, zero max-slew / max-cap violations, setup WNS ≥ 0,
  hold WNS ≥ 0

#### `RunResult`

- `run_dir`, `exit_code`, `duration_seconds`, `metrics`,
  `stdout_tail`, `stderr_tail`, `command`
- `success` property: `exit_code == 0 AND metrics is not None AND
  metrics.is_clean`
- Class method `from_run_dir(run_dir, ...)` that scans for
  `run_dir/final/metrics.json` (falls back to recursive search) and
  builds the full object

Both models are **frozen** (`ConfigDict(frozen=True)`) — once a run is
done, its result is a historical fact and should be immutable.

### 1D-c — configuration and the runner (`src/pd_agent/config.py`, `src/pd_agent/flow/runner.py`)

#### `PDAgentSettings` (pydantic-settings)

Two settings values with a clear priority chain:

1. Constructor argument (highest)
2. Environment variable with `PD_AGENT_` prefix
3. `.env` file in cwd
4. Hardcoded defaults

The two settings: `openlane2_repo` (default
`~/Documents/Projects/openlane2`) and `openlane_bin` (default
`"openlane"`).

#### `OpenLaneRunner`

Three public methods, each doing one thing, all independently testable.

- **`detect_mode() → "direct" | "nix-shell"` (or raises)**
  - `"direct"` when `shutil.which("openlane")` finds the binary on PATH
  - `"nix-shell"` when `nix-shell` is available AND `openlane2_repo`
    exists as a directory
  - Raises `RunnerNotAvailableError` otherwise, with a friendly pointer
    to `docs/setup.md`
- **`build_command(config_path) → (argv, cwd)`**
  - Direct mode: `argv = ["openlane", config_path]`, `cwd` is the
    config's parent
  - Nix-shell mode: `argv = ["nix-shell", "--run", shlex.join([openlane, config])]`,
    `cwd` is the openlane2 repo (where `shell.nix` lives)
- **`run(config_path, *, timeout=None) → RunResult`**
  - The orchestrator: calls `build_command`, invokes
    `subprocess.run(..., capture_output=True)`, times it,
    discovers the newest `runs/RUN_*` directory via mtime, packages
    everything into a `RunResult`

Internal helper `_find_latest_run_dir(design_dir)` solves a specific
OpenLane quirk: OpenLane doesn't tell you where it wrote output, so the
only reliable way to know which `RUN_<timestamp>/` belongs to the run
you just triggered is to scan `runs/RUN_*` after the subprocess returns
and pick the newest by `.stat().st_mtime`.

### 1D-d — CLI (`src/pd_agent/cli.py` + updated `__main__.py`)

Typer app with three subcommands:

- **`pd-agent info`** — diagnostic, prints version + resolved
  `openlane2_repo` + detected invocation mode. Never exits non-zero.
- **`pd-agent run (--design NAME | --config PATH) [--timeout SECONDS]`** —
  the headline command. XOR logic (exactly one of `--design` or `--config`,
  not both, not neither). Renders a Rich summary panel + colored metrics
  table. Exits 1 if `result.success is False`.
- **`pd-agent metrics PATH`** — standalone viewer. Accepts either a
  `metrics.json` file or a run directory. Renders the same table.

`__main__.py` updated to delegate to `cli.app`, so
`python -m pd_agent ...` and `pd-agent ...` are equivalent.

### 1D-e — vendored design and integration test

#### `designs/spm/`

Six files vendored verbatim from OpenLane 2's upstream example:

- `config.yaml` (OpenLane recipe)
- `src/spm.v` (32-bit serial/parallel multiplier Verilog, ~70 lines,
  Apache-2.0 © Efabless Corporation)
- `src/impl.sdc` (implementation timing constraints)
- `src/signoff.sdc` (signoff timing constraints)
- `pin_order.cfg` (physical pin placement hint)
- `README.md` (provenance note)

**Vendored so the repo is self-contained** — anyone who clones it can
run the full flow immediately. Apache-2.0 license header preserved in
the Verilog file.

#### `tests/test_integration_openlane.py`

One test: `test_spm_end_to_end_clean_signoff`. Invokes OpenLane on the
vendored SPM, asserts 7 individual signoff checks pass
(DRC Magic, DRC KLayout, LVS, antenna, setup WNS, hold WNS, is_clean).

**Three-layer skip gate** so it never runs accidentally:

1. `@pytest.mark.integration` — default `pytest` excludes marked tests
2. `pytest.mark.skipif(PD_AGENT_RUN_INTEGRATION != "1")` — requires an
   explicit env var
3. Runtime `detect_mode()` try/except — auto-skips if OpenLane isn't
   reachable on this machine

All three layers must pass for the test to actually execute. Any single
layer failing → clean skip with a helpful reason. This pattern is used
by HuggingFace transformers, the Kubernetes Python client, and similar
libraries that shell out to heavy external tooling.

### Test coverage after Phase 1D

- **Unit tests**: 67 passing, ~0.7 seconds, 96% overall coverage
  - `flow/models.py` — 100%
  - `flow/runner.py` — 98%
  - `cli.py` — 94%
  - `config.py` — 100%
- **Integration test**: 1 passing in ~40 seconds against real OpenLane
  on SPM (opt-in)

## Phase 1 release — v0.1.0 (PR #4, tag `v0.1.0`)

Release closeout in three ordered steps:

- **R1** — `feat/openlane-runner` → `dev`, squash-merged as PR #3
- **R2** — `dev` → `main`, squash-merged as PR #4 (commit `b031df3`).
  Tree identity verified: `main` and `dev` share tree SHA
  `eb5b758e93b69b4c8441f3dcd6fe1dc131eab58e` — byte-identical content
- **R3** — annotated tag `v0.1.0` (tag object `425795b`) pointing at
  commit `b031df3`, pushed to GitHub; GitHub Release published with
  rendered release notes

## Notable decisions taken during Phase 1 (with rationale)

- **uv over Poetry** — faster, simpler, Rust-based, modern default
- **ruff over black + isort + flake8** — one tool, zero config, very fast
- **Pydantic v2 for all data classes** — validation, frozen support,
  serialization, and alignment with the rest of the ecosystem
- **Typer for the CLI** — type-hint-driven, less boilerplate than
  click, Rich integration built in
- **Rich for output formatting** — modern terminal UI primitives,
  industry standard for 2024+ Python CLIs
- **OpenLane 2 over OpenLane 1** — Python-native configuration (vs. Tcl
  scripts), actively developed, matches our Python-first design
- **Nix + cachix over Docker** — native performance on Apple Silicon,
  reproducible toolchain versions
- **Squash-merge to both `dev` and `main`** — simpler history for a
  solo-developer project; each PR is one commit. (Originally planned to
  use merge-commits for `dev` → `main`, but reversed when `main`'s
  branch protection was configured squash-only during Phase 1A. The
  effect is fine: `dev` retains granular history; `main` reads like a
  changelog.)
- **Integration test gated three ways** — marker + env var + runtime
  detection. Industry pattern for "real external tool" tests.
- **Vendor the SPM design** — ~6 files, few KB. Self-contained beats
  cross-repo reference for reproducibility.

## Things explicitly deferred from Phase 1

- Any LLM integration (Phase 2)
- Any RAG / document retrieval (Phase 3)
- Run-to-run metrics tracking / time-series observability (Phase 4)
- Multi-agent coordination (Phase 5)
- CI (GitHub Actions) — will likely land early in Phase 2
- GF180MCU or other PDK runs beyond SkyWater 130nm
- Docker-based CI for integration tests

---

# Phase 2 — LLM-driven explain (v0.2.0)

- **Released**: 2026-04-20
- **Tag**: `v0.2.0` (annotated)
- **GitHub Release**: to be populated at release time
- **Pull requests merged**: #6, #7, #8, #9, #10, #11
- **Net change to main**: ~+1000 lines across ~15 files

## Phase 2 at a glance

Phase 2 is the first *actually AI-powered* release. You can now point
`pd-agent` at any OpenLane run and get a plain-English explanation
from Anthropic Claude:

```
$ pd-agent explain designs/spm/runs/RUN_2026.04.20_00.01.23/
╭──────────────────────── Explanation ───────────────────────╮
│ This design has passed signoff cleanly with no violations. │
│ Setup slack is 6.1 ns (comfortably faster than the target  │
│ frequency), hold slack is 0.26 ns (adequate margin), and   │
│ both WNS and TNS are zero...                               │
╰────────────────────────────────────────────────────────────╯
model: claude-sonnet-4-5-20250929  |  tokens: 419 in / 207 out
```

The deliberate design principle of Phase 2 was **"wrap the LLM behind
a thin, swappable boundary"**. Every call to Claude goes through a
`LLMProvider` protocol, so when v0.3.0 wants to add Ollama or OpenAI,
nothing above `pd_agent.llm.*` has to change.

Three structural additions underpin the user-visible `explain` command:

1. **CI/CD** (#6) — GitHub Actions runs lint + format + test on every
   PR, before we start iterating on AI features
2. **Config + secrets** (#7) — Anthropic SDK dependency, `.env`
   loading via `pydantic-settings`, and a `SecretStr`-wrapped API key
3. **Provider abstraction** (#8) — `LLMProvider` protocol, `LLMResponse`
   model, and a concrete `AnthropicProvider`

Then the user-facing work:

4. **`pd-agent explain`** (#9) — prompt construction, CLI wiring, Rich
   rendering of the response
5. **Live integration test** (#10) — an opt-in end-to-end test that
   actually calls Claude to validate the pipeline works against a
   real API, not just mocks

## Architecture at the end of Phase 2

```
┌─────────────────────────────────────────────────────────────────────┐
│ You, at a terminal                                                  │
│    $ pd-agent explain designs/spm/runs/RUN_.../                     │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│ src/pd_agent/cli.py (Typer)                                         │
│   • run / metrics / explain / info subcommands                      │
│   • _load_metrics() shared by metrics and explain                   │
└─────────────────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌──────────────────────────┐    ┌───────────────────────────────────┐
│ flow/ (Phase 1)          │    │ src/pd_agent/explain.py (Phase 2) │
│   • FlowMetrics          │    │   • SYSTEM_PROMPT                 │
│   • OpenLaneRunner       │    │   • build_user_prompt(metrics)    │
│                          │    │   • explain_metrics(..., provider)│
└──────────────────────────┘    └───────────────────────────────────┘
                                             │
                                             ▼
                           ┌──────────────────────────────────────────┐
                           │ src/pd_agent/llm/                        │
                           │   • provider.py: LLMProvider protocol,   │
                           │                   LLMResponse model      │
                           │   • anthropic.py: AnthropicProvider,     │
                           │                   make_default_provider  │
                           └──────────────────────────────────────────┘
                                             │  anthropic SDK
                                             ▼
                           ┌──────────────────────────────────────────┐
                           │ Anthropic Claude API (api.anthropic.com) │
                           │   • messages.create, model=claude-sonnet │
                           └──────────────────────────────────────────┘
```

New files this phase:

- `src/pd_agent/explain.py` — prompt construction and `explain_metrics()`
- `src/pd_agent/llm/__init__.py` — package facade
- `src/pd_agent/llm/provider.py` — `LLMProvider` protocol, `LLMResponse`
- `src/pd_agent/llm/anthropic.py` — Claude implementation
- `tests/test_explain.py` — 10 mocked unit tests
- `tests/test_llm.py` — 15 mocked unit tests (LLMResponse + provider)
- `tests/test_config.py` — 7 settings tests
- `tests/test_explain_live.py` — 1 opt-in real-Anthropic test
- `.github/workflows/ci.yml` — GitHub Actions CI
- `.env.example` — template for local `ANTHROPIC_API_KEY`

## Phase 2A-0 — GitHub Actions CI (PR #6)

**Shipped first, on purpose.** Before adding any LLM code, we turned
on automated checks so every subsequent PR had a safety net. The
workflow lives at `.github/workflows/ci.yml`.

What each step does, top to bottom:

- **`on: push / pull_request`** — trigger on pushes to `main` or `dev`,
  and on every PR targeting them. That covers the two places changes
  actually land.
- **`concurrency` with `cancel-in-progress: true`** — if you push
  twice in a row to the same branch, the older CI run gets cancelled.
  Saves minutes and surfaces only the latest result.
- **`runs-on: ubuntu-latest`, `timeout-minutes: 10`** — GitHub's free
  Linux runner, with a safety net timeout so a stuck job can't burn
  forever.
- **`actions/checkout@v4`** — standard "clone this repo" action.
- **`astral-sh/setup-uv@v4`** — installs `uv` and the pinned Python
  version (3.12), with `enable-cache: true` so subsequent runs reuse
  downloaded packages.
- **`uv sync --dev`** — installs runtime + dev dependencies from
  `uv.lock`. Reproducible to the exact same versions the author used.
- **`ruff check .`** — lint failures fail the build.
- **`ruff format --check .`** — format drift fails the build (doesn't
  auto-format, just reports).
- **`pytest -m "not integration"`** — unit tests only. The
  `integration` marker is specifically excluded here so CI never
  accidentally tries to run OpenLane or call Anthropic.

First CI run was the PR *that added CI* — a nice meta-test that
verified the workflow against its own diff before merging.

## Phase 2A-1 — Anthropic SDK + API key config (PR #7)

Two additions:

1. `uv add anthropic` bumps `pyproject.toml` to depend on the official
   Anthropic Python SDK (`anthropic>=0.96.0`).
2. `src/pd_agent/config.py` gains two new fields on `PDAgentSettings`:

```python
anthropic_api_key: SecretStr | None = Field(
    default=None,
    validation_alias=AliasChoices(
        "ANTHROPIC_API_KEY",             # industry-standard name
        "PD_AGENT_ANTHROPIC_API_KEY",    # project-prefixed fallback
    ),
)
anthropic_model: str = Field(default="claude-sonnet-4-5")
```

The two things worth understanding here:

- **`SecretStr`** — a Pydantic type that stores the value but
  `str(settings.anthropic_api_key)` returns `'**********'`. So if you
  ever accidentally log the settings object or dump it to the console,
  the key is automatically redacted. You call `.get_secret_value()`
  when you actually need the raw string (only done in one place:
  constructing the Anthropic client).
- **`AliasChoices`** — lets one Pydantic field read from multiple env
  var names, in priority order. `ANTHROPIC_API_KEY` is the standard
  name every SDK and IDE recognises; `PD_AGENT_ANTHROPIC_API_KEY` is
  the project-prefixed fallback for contributors who want per-project
  isolation. Both work; the unprefixed one wins if both are set.

Also in this PR:

- **`.env.example`** — a committed template showing contributors what
  env vars they can set. The real `.env` is git-ignored via
  `.gitignore` line 97.
- **`tests/test_config.py`** — 7 tests covering: defaults, env-var
  loading (both names), `.env` loading, `AliasChoices` precedence,
  `SecretStr` redaction, prefixed-name resolution.

## Phase 2A-2 — LLM provider abstraction (PR #8)

The most architecturally important piece of Phase 2. Instead of
calling Anthropic directly from `explain.py`, we define a
vendor-agnostic interface first.

**`src/pd_agent/llm/provider.py`** defines two things:

```python
class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: str
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    stop_reason: str = ""
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

@runtime_checkable
class LLMProvider(Protocol):
    @property
    def model(self) -> str: ...
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> LLMResponse: ...
```

Why a `Protocol` rather than an abstract base class?

- **Structural typing**. Any class with a matching `model` property
  and `generate()` method satisfies `LLMProvider` automatically. No
  subclassing, no registration, no boilerplate.
- Consumers (`explain.py`) just type-hint `provider: LLMProvider` and
  the type checker enforces the contract. Tests can pass a plain
  `MagicMock` with the right attributes and it's accepted.
- `@runtime_checkable` also lets you do `isinstance(obj, LLMProvider)`
  at runtime if you ever need to defensively check.

`LLMResponse` is `frozen=True` (immutable) because it's a return value
— mutating it after the call would be nonsense.

**`src/pd_agent/llm/anthropic.py`** is the one concrete implementation:

- `AnthropicProvider.__init__` accepts an `api_key`, `model`, and
  optionally a pre-built `Anthropic` client (for test injection).
- `generate()` wraps `client.messages.create(...)`, concatenates
  text blocks from the response, and returns an `LLMResponse` with
  token counts filled in from `response.usage`.
- `make_default_provider()` is a factory that builds a provider from
  `PDAgentSettings` (reads `ANTHROPIC_API_KEY` from env or `.env`,
  raises `ValueError` with a helpful message if absent).

**Testing** (15 tests in `tests/test_llm.py`) uses `MagicMock` to
simulate Anthropic API responses — no real API calls, no API key
required. Every edge case is covered: multi-block text responses,
non-text blocks being ignored, `None` stop reasons, negative token
counts being rejected, factory success and failure paths.

## Phase 2A-3 — `pd-agent explain` (PR #9)

The user-facing feature this whole phase is building up to.

**`src/pd_agent/explain.py`** has two pieces:

1. **`SYSTEM_PROMPT`** — the persona-setting instructions Claude
   receives before every call. Tells Claude it's a PD engineer, to be
   concise (4–8 sentences), to use engineering units (ns/mW/um²), and
   critically:

   > *"Do NOT invent values that are not in the input. If a field is
   > marked 'not measured', do not claim it passed or failed."*

   This guardrail held in live testing — Claude never fabricated
   numbers, even when the fixture was missing fields.

2. **`build_user_prompt(metrics: FlowMetrics) -> str`** — serializes
   the curated `FlowMetrics` into a compact labeled block. Critical
   detail: `None` values render as `"not measured"`, never `"0"`.
   Confusing zero (a real, passing value) with missing (unknown) would
   lead Claude to lie about things it wasn't told.

3. **`explain_metrics(metrics, *, provider=None, max_tokens=1024,
   temperature=0.2)`** — calls the provider. If no provider is
   injected, builds a default one via `make_default_provider()`. The
   `provider=None` parameter exists precisely so unit tests can inject
   a fake.

**`src/pd_agent/cli.py`** adds `cmd_explain` and extracts a shared
`_load_metrics(path)` helper (used by both `cmd_metrics` and
`cmd_explain` — removed duplicated "is it a file? a dir? missing?"
logic). The CLI renders the response in a Rich panel with a dim footer
showing model + token usage.

**Tests**:

- `tests/test_explain.py` — 10 unit tests covering prompt construction
  (clean vs dirty metrics, unmeasured fields, timing numbers included,
  violation counts included), the system prompt content, and
  `explain_metrics()` behavior with injected providers and the
  `make_default_provider` path. All mocked; no real API calls.
- `tests/test_cli.py` gains a `TestExplain` class — 5 tests covering
  the CLI surface: JSON-file input, run-dir input, `--max-tokens` and
  `--temperature` forwarding, missing-metrics error (exit 1), and
  missing-API-key error (exit 2).

## Phase 2A-4 — Live Anthropic integration test (PR #10)

The unit tests prove our code does the right thing. But they all use
mocks, so they don't catch:

- Anthropic deprecating or renaming `claude-sonnet-4-5`
- Our prompt drifting into uselessness (still returning text, just
  nonsense)
- SDK version incompatibilities between `anthropic>=0.96.0` and the
  real API

**`tests/test_explain_live.py`** solves this with one single test,
triple-gated so it never runs by accident:

1. `@pytest.mark.integration` — the default `uv run pytest` skips
   everything with this marker.
2. Module-level `pytest.mark.skipif` checks for
   `PD_AGENT_RUN_LIVE_LLM=1`. You must explicitly opt in. Mirrors the
   existing `PD_AGENT_RUN_INTEGRATION=1` pattern from Phase 1.
3. A defensive `_require_api_key()` helper skips with a friendly
   message if `PDAgentSettings` can't resolve an `ANTHROPIC_API_KEY` —
   friendlier than a 401 from the API.

The test itself calls `explain_metrics(metrics, max_tokens=256,
temperature=0.0)` against the SPM fixture and asserts:

- Response text is non-empty
- Model identifier starts with `"claude"`
- Input and output token counts are both positive
- Response contains at least one PD-domain signal word
  (`pass`, `clean`, `signoff`, `timing`, `setup`, `hold`) — a weak
  prompt-drift guard that catches the case of "Claude returned
  something vaguely plausible but totally off-topic"

First successful run:
- Model: `claude-sonnet-4-5-20250929`
- Cost: **~$0.004** (419 input tokens, 207 output tokens)
- Latency: ~8s
- Accuracy: every number in Claude's response matched the prompt exactly,
  including unit conversion (W → mW) that we didn't explicitly ask for.

CI does **not** run this test. That's a conscious choice: CI should
be free, fast, and deterministic. Live API tests run locally on demand.

## Phase 2 release — v0.2.0 (PR #11, tag `v0.2.0`)

Release closeout (filled in after each step):

- **Pre-release chore PR** — version bump (`0.1.0` → `0.2.0`), README
  status update, this journal chapter
- **Release PR** — `dev` → `main`, squash-merged
- **Annotated tag `v0.2.0`** pointing at the new `main` head
- **GitHub Release** with rendered release notes

## Test coverage at the end of Phase 2

- **Unit tests**: 105 passing in ~1.5 seconds
- **Coverage**: 97% overall
  - `cli.py` — 95%
  - `config.py` — 100%
  - `explain.py` — 100%
  - `flow/models.py` — 100%
  - `flow/runner.py` — 98%
  - `llm/anthropic.py` — 100%
  - `llm/provider.py` — 100%
- **Integration tests**: 2 opt-in (real-OpenLane in Phase 1,
  real-Anthropic in Phase 2), both auto-skipping unless explicitly
  enabled

## Notable decisions taken during Phase 2 (with rationale)

- **Anthropic Claude over OpenAI / Ollama** — best instruction-following
  at this cost tier (~$0.005/call), strong tool-use support for the
  Phase 3 agent work. Ollama was considered for free local inference
  but the quality gap on small structured prompts was too large.
- **Raw Anthropic SDK over LangChain / PydanticAI** — for Phase 2A
  we're doing *one* LLM call at a time. A framework is overkill; raw
  SDK is a few dozen lines and teaches the underlying mechanics.
  Revisit in v0.3.0 when we start doing tool-use and multi-turn.
- **Protocol over ABC for `LLMProvider`** — structural typing, zero
  boilerplate, works natively with `MagicMock` in tests.
- **System prompt includes an explicit "do not invent values" clause**
  — LLMs are extremely prone to plausible hallucination on numeric
  data. Direct instruction + "not measured" sentinel values together
  were enough to prevent it in testing.
- **`temperature=0.2` default, `0.0` for tests** — low temperature
  for factual reporting; deterministic (0.0) for tests so assertions
  are stable.
- **Ship CI *before* the feature work** — "cheap insurance against
  regressions". Every subsequent PR was validated by the workflow
  before we even finished merging it.
- **Live LLM test gated three ways** — marker + env var + missing-key
  skip. Mirrors the Phase 1 integration-test pattern. No accidental
  spend.
- **`SecretStr` for API keys** — Pydantic's built-in redaction for
  accidental logging / error messages. Zero ergonomic cost.

## Security lesson: the `.env.example` mishap

Partway through Phase 2A-4 (live LLM test), a real secrets-hygiene
mistake happened — and the tooling caught it before damage. Worth
recording:

1. User intended to edit `.env` (git-ignored) and paste a real
   `ANTHROPIC_API_KEY` value.
2. User actually edited `.env.example` (the committed template).
3. User then ran `cp .env.example .env`, which copied the already-edited
   template — so **both** files contained the real key.
4. `git status` would have shown `.env.example` as modified. Had a
   `git add .` happened at that point, the key would have been
   staged for commit.

**What saved us**:

- The key never reached `git add`, so never reached `git commit`,
  so never reached `origin/main`.
- The diagnosis (`git show HEAD:.env.example | grep ANTHROPIC`)
  confirmed the committed version was still the empty template.

**Recovery**:

1. Revoked the exposed key at console.anthropic.com, regenerated a
   new one.
2. `git checkout -- .env.example` — threw away the local edit,
   restored the empty template.
3. Rewrote `.env` from scratch with just `ANTHROPIC_API_KEY=<new-key>`
   in standard `dotenv` format (no spaces around `=`).
4. Verified `git check-ignore -v .env` still showed it git-ignored.

**Lesson**: if a secret ever appears in a file that `git status`
tracks — even just in your working tree, never committed — rotate
the key. Rotation is free and takes 30 seconds; certainty is worth
more than the minor inconvenience.

## Things explicitly deferred from Phase 2

- **RAG over PD documentation** — Phase 3 will embed the OpenROAD /
  OpenLane docs and let the LLM cite them in explanations
- **Tool-use** — letting Claude actually invoke `OpenLaneRunner` as
  a tool, e.g. *"run SPM and explain any failures"*. Requires either
  Anthropic's tool-use API or a framework like PydanticAI
- **Multi-turn conversations** — current `pd-agent explain` is single
  shot. Multi-turn debugging loops come with agent-mode
- **Prompt evaluation framework** — we decided in Phase 2 planning to
  defer this; will revisit once we have more than one prompt and need
  to A/B test them
- **Streaming responses** — current implementation blocks until the
  full response arrives. Fine for explanations; worth streaming for
  longer outputs in v0.3.0+
- **Metrics-over-time / observability** — still Phase 4
- **Multi-agent coordination** — still Phase 5
- **GitHub Actions secret for live LLM test in CI** — revisit in
  v0.3.0; for now, live tests stay local-only

---

# Repository conventions

## Branch naming

| Prefix | Purpose |
|---|---|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `chore/` | Tooling, deps, config |
| `docs/` | Documentation only |
| `test/` | Test additions |
| `refactor/` | Code cleanup, no behavior change |

## Commit messages

Conventional Commits: `type(scope): short description`.
Longer body optional. No trailing period on the subject line.

## Merge strategy

- `feature/* → dev`: squash-and-merge (one commit per feature lands on dev)
- `dev → main`: squash-and-merge (one commit per release lands on main)

## Testing

- Default `uv run pytest` — unit tests only, < 2 seconds
- OpenLane integration: `PD_AGENT_RUN_INTEGRATION=1 uv run pytest -m integration tests/test_integration_openlane.py`
- Live LLM test: `PD_AGENT_RUN_LIVE_LLM=1 uv run pytest -m integration tests/test_explain_live.py -s`
- Linting: `uv run ruff check .`
- Formatting: `uv run ruff format .`

---

# Repository layout reference

```
PD_AI_Agent/
├── .github/
│   └── workflows/
│       └── ci.yml                   # Lint + format + tests on every PR
├── designs/
│   └── spm/                         # Vendored 32-bit SPM (Apache-2.0)
│       ├── config.yaml
│       ├── pin_order.cfg
│       ├── README.md
│       └── src/
│           ├── spm.v
│           ├── impl.sdc
│           └── signoff.sdc
├── docs/
│   ├── PROJECT_JOURNAL.md           # This file — the living history
│   ├── pd_agent_explained.md        # Non-technical "what is this project"
│   └── setup.md                     # Install guide (Nix + OpenLane)
├── src/pd_agent/
│   ├── __init__.py                  # Public re-exports, __version__
│   ├── __main__.py                  # `python -m pd_agent` entry
│   ├── cli.py                       # Typer CLI (run / metrics / explain / info)
│   ├── config.py                    # PDAgentSettings (pydantic-settings)
│   ├── explain.py                   # Phase 2: SYSTEM_PROMPT + explain_metrics()
│   ├── py.typed                     # PEP 561 marker
│   ├── flow/
│   │   ├── __init__.py              # Re-exports FlowMetrics, RunResult, etc.
│   │   ├── models.py                # FlowMetrics + RunResult
│   │   └── runner.py                # OpenLaneRunner
│   └── llm/                         # Phase 2: vendor-agnostic LLM layer
│       ├── __init__.py              # Re-exports LLMProvider, AnthropicProvider
│       ├── provider.py              # LLMProvider Protocol + LLMResponse model
│       └── anthropic.py             # AnthropicProvider + make_default_provider
├── tests/
│   ├── fixtures/
│   │   └── spm_metrics.json         # Real metrics.json from a prior SPM run
│   ├── test_cli.py                  # Typer CLI tests (mocked)
│   ├── test_config.py               # Phase 2: PDAgentSettings tests
│   ├── test_explain.py              # Phase 2: explain_metrics tests (mocked)
│   ├── test_explain_live.py         # Phase 2: opt-in real-Anthropic test
│   ├── test_flow_models.py          # FlowMetrics + RunResult tests
│   ├── test_integration_openlane.py # Opt-in real-OpenLane test
│   ├── test_llm.py                  # Phase 2: LLMProvider + LLMResponse tests
│   ├── test_runner.py               # OpenLaneRunner tests (mocked)
│   └── test_smoke.py                # Import + version tests
├── .env.example                     # Phase 2: template for local env vars
├── .gitignore
├── .python-version
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

---

# Glossary of PD / EDA terms used in this project

| Term | Plain-English meaning |
|---|---|
| **RTL** | Register-Transfer Level — Verilog code describing a chip's digital behavior |
| **PDK** | Process Design Kit — fab-provided files translating logic into silicon geometry |
| **Flow** | The pipeline of EDA tools run to turn RTL into a manufacturable chip |
| **Signoff** | The final set of checks before sending a design to the fab |
| **DRC** | Design Rule Check — does the layout violate fab geometry rules? |
| **LVS** | Layout-vs-Schematic — does the physical layout match the netlist? |
| **WNS / TNS / WS** | Worst / Total / aggregate Negative Slack — timing metrics |
| **Antenna violation** | A fab concern about long wires damaging transistors during manufacturing |
| **GDSII** | Binary file format sent to the fab; every polygon on every chip layer |
| **SDC** | Synopsys Design Constraints — file format for timing constraints |
| **PDN** | Power Distribution Network — metal grid carrying power across the chip |
| **Floorplan** | Decides chip size and where I/O pins go |
| **CTS** | Clock Tree Synthesis — buffered network delivering the clock with minimal skew |
| **Tape-out** | Sending the final design to the fab for manufacturing |

---

# How this journal is maintained

Updated at the end of every phase (after the release tag is pushed).
The update adds a new top-level `# Phase N — ...` section with the
same structure as Phase 1's:

1. Headline (release date, tag, commit, PRs, net change)
2. "Phase N at a glance" — one paragraph, what it accomplished
3. Architecture diagram or description of what changed
4. Sub-phase walkthroughs (2A, 2B, ...) — what shipped in each
5. Test coverage after the phase
6. Release process notes (if any deviation from the default flow)
7. Notable decisions with rationale
8. Things explicitly deferred to the next phase
9. Move the "Current state" section at the top to reflect the new release
10. Update the roadmap table statuses

Also add any new terms to the glossary and any new top-level files or
directories to the layout reference.

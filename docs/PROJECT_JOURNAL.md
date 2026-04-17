# PD_AI_Agent — Project Journal

> A living record of what's been built in this repository, why each piece
> exists, and how it was done. Updated at every phase boundary.
>
> **Audience**: future-you, future contributors, and anyone trying to
> understand the repository six months from now. Written to be readable
> without prior context on this specific project.

---

## Current state (as of 2026-04-17)

- **Latest release**: v0.1.0 (tag `v0.1.0`, commit `b031df3`).
- **Active branch**: `dev` (integration branch for v0.2.0 work).
- **What works today**: `pd-agent run --design spm` runs the full OpenLane 2
  flow on the vendored SPM design and returns parsed signoff metrics in
  ~40 seconds. Unit tests (67 passing, 96% coverage) run in under one
  second; a real-OpenLane end-to-end integration test exists as an
  opt-in extra.
- **What doesn't work yet**: any actual "AI" (LLM reasoning, RAG, agents).
  v0.1.0 is deliberately plumbing-only. Intelligence arrives in v0.2.0.

## Roadmap

| Version | Theme | Status |
|---|---|---|
| v0.1.0 | Repo bootstrap, Python skeleton, OpenLane 2 runner, CLI, SPM integration | **Released 2026-04-17** |
| v0.2.0 | LLM-driven agent wrapping the runner | Next |
| v0.3.0 | RAG over PD documentation | Planned |
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

# Phase 2 — LLM-driven agent (v0.2.0) — NOT YET STARTED

*This section is a placeholder. It will be filled in as Phase 2 work
lands. Expected scope:*

- Accept natural-language goals like *"Run SPM and explain any
  signoff failures"*
- Use structured tool-calling (OpenAI function-calling or Anthropic
  tool-use) to let the LLM invoke `OpenLaneRunner` as a tool
- Produce human-readable summaries of `FlowMetrics` results
- Handle failure cases intelligently (explain *which* check failed and
  by how much)

*Updates to this journal at the end of Phase 2 will add:*

- v0.2.0 release info (tag, commit, PR numbers)
- LLM provider decision and rationale
- Agent framework decision and rationale
- New modules and their responsibilities
- Test coverage changes
- Notable decisions with rationale
- Things deferred to Phase 3

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

- Default `uv run pytest` — unit tests only, < 1 second
- Integration: `PD_AGENT_RUN_INTEGRATION=1 uv run pytest -m integration`
- Linting: `uv run ruff check .`
- Formatting: `uv run ruff format .`

---

# Repository layout reference

```
PD_AI_Agent/
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
│   ├── __init__.py                  # Public re-exports
│   ├── __main__.py                  # `python -m pd_agent` entry
│   ├── cli.py                       # Typer CLI (run / metrics / info)
│   ├── config.py                    # PDAgentSettings (pydantic-settings)
│   ├── py.typed                     # PEP 561 marker
│   └── flow/
│       ├── __init__.py              # Re-exports FlowMetrics, RunResult, etc.
│       ├── models.py                # FlowMetrics + RunResult
│       └── runner.py                # OpenLaneRunner
├── tests/
│   ├── fixtures/
│   │   └── spm_metrics.json         # Real metrics.json from a prior SPM run
│   ├── test_cli.py                  # 13 Typer CLI tests (mocked)
│   ├── test_flow_models.py          # 37 model tests
│   ├── test_integration_openlane.py # 1 opt-in real-OpenLane test
│   ├── test_runner.py               # 15 runner tests (mocked)
│   └── test_smoke.py                # 2 import tests
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

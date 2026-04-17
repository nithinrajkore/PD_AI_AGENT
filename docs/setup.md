# Environment Setup

Instructions to reproduce the development environment for `PD_AI_Agent` on macOS.

This guide sets up **OpenLane 2** (the open-source RTL-to-GDS flow) alongside the Python project. OpenLane 2 is a separate tool maintained at [efabless/openlane2](https://github.com/efabless/openlane2) and is invoked as a subprocess by `pd_agent`.

> **Note on naming:** OpenLane 2 is being renamed to **LibreLane** (at `librelane/librelane`). The `efabless/openlane2` repo continues to work and is used here for compatibility.

## Prerequisites

| Requirement | Minimum | Verified on |
|---|---|---|
| macOS | 11 (Big Sur) | 26.3 (Tahoe), Apple Silicon |
| CPU | `arm64` or `x86_64` | `arm64` |
| Free disk | 20 GB | — |
| Shell | `zsh` or `bash` | — |
| Python | 3.12 | — |
| `uv` | latest | [install guide](https://docs.astral.sh/uv/) |
| `git` | any recent | — |

## 1. Clone this repo

```bash
git clone https://github.com/nithinrajkore/PD_AI_AGENT.git
cd PD_AI_AGENT
```

## 2. Install Nix (for OpenLane 2)

We use the Determinate Systems Nix installer with OpenLane's binary cache pre-configured. This avoids compiling the toolchain from source.

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install --no-confirm --extra-conf "
extra-substituters = https://openlane.cachix.org
extra-trusted-public-keys = openlane.cachix.org-1:qqdwh+QMNGmZAuyeQJTH9ErW57OWSvdtuwfBKdS254E=
"
```

**After install, fully restart your terminal** (quit Terminal.app / Cursor with `Cmd+Q`, reopen). The Nix environment variables only apply to new shell sessions.

Verify:

```bash
nix --version
nix-shell --version
```

## 3. Clone OpenLane 2

OpenLane 2 lives as a sibling directory to this repo, not inside it.

```bash
cd ~/Documents/Projects   # or wherever your projects live
git clone https://github.com/efabless/openlane2.git
```

Expected layout:

```
~/Documents/Projects/
├── PD_AI_AGENT/
└── openlane2/
```

## 4. Enter the Nix environment

```bash
cd ~/Documents/Projects/openlane2
nix-shell
```

**First entry takes 30–60 minutes** — it downloads ~5–10 GB of pre-built binaries (OpenROAD, Yosys, Magic, Netgen, KLayout, etc.) from the cachix cache.

- `copying path ...` lines → good (downloading from cache)
- `building '/nix/store/...drv'` for many packages → **bad**, cachix config was not applied; exit and re-run step 2 with the `--extra-conf` block exactly as written

Subsequent entries are instant (< 5 sec).

Verify the toolchain loaded:

```bash
which openlane && openlane --version
which openroad yosys magic klayout netgen
```

All paths should start with `/nix/store/...`.

## 5. Smoke-test OpenLane 2

Still inside the `nix-shell`:

```bash
openlane --smoke-test
```

Expected: all 78 stages of the "Classic" flow complete in ~3–5 minutes, ending with `Smoke test passed.`

## 6. Run the SPM example end-to-end

```bash
cd ~/Documents/Projects/openlane2
openlane ./openlane/examples/spm/config.yaml
```

Expected: 78 stages complete in ~5–15 minutes (often ~40s on Apple Silicon), ending with `Flow complete.` and three `Passed ✅` lines for Antenna, LVS, and DRC.

Outputs live under:

```
~/Documents/Projects/openlane2/openlane/examples/spm/runs/RUN_<timestamp>/
├── final/
│   ├── gds/spm.gds           # final chip layout (GDSII)
│   ├── metrics.json           # 282 structured PD metrics
│   └── reports/               # timing, power, DRC reports
└── <NN>-<stage-name>/         # per-stage artifacts and logs
```

## 7. Set up the Python project

In a separate terminal (outside the `nix-shell`), back in the repo:

```bash
cd /path/to/PD_AI_AGENT
uv sync
uv run pytest
uv run python -m pd_agent
```

Expected: `pytest` shows all tests passing; `python -m pd_agent` prints the package version.

## Troubleshooting

- **`nix: command not found` after install** → the terminal was not fully restarted. Quit the terminal app (`Cmd+Q`), reopen, try again.
- **`nix-shell` starts `building` from source instead of `copying`** → the cachix config was not applied during Nix install. Re-run step 2 exactly as written.
- **OpenLane warnings `GRT-0097`, `DRT-0349`, `VSRC_LOC_FILES`, `CustomIOPlacement`** → all expected and non-blocking; they appear on every clean run.

## References

- OpenLane 2 documentation: https://openlane2.readthedocs.io/
- SkyWater 130nm PDK: https://github.com/google/skywater-pdk
- OpenROAD project: https://theopenroadproject.org/
- `uv` package manager: https://docs.astral.sh/uv/

# SPM — Serial/Parallel Multiplier

A 32-bit unsigned serial/parallel multiplier (multiplicand fed one bit per
cycle, multiplier fed in parallel, product emitted bit-serially). This is the
canonical "Hello, World!" design for OpenLane because it exercises the full
physical-design flow — synthesis, floorplan, PDN, placement, CTS, routing,
signoff — while staying small enough to compile in a couple of minutes.

## Provenance

Vendored from the OpenLane 2 project so this repository is self-contained
and reproducible. Upstream source:

- Repository: <https://github.com/efabless/openlane2>
- Path: `openlane/examples/spm/`
- RTL copyright: © 2023 Efabless Corporation, Apache-2.0
  (license header preserved in `src/spm.v`).

Config tuning (PDN geometry, per-PDK overrides, pin ordering) is kept
identical to upstream so results are directly comparable to the upstream
reference run.

## Files

| File | Role |
|---|---|
| `config.yaml` | OpenLane flow configuration |
| `src/spm.v` | Verilog RTL — top module `spm`, plus `delayed_serial_adder` |
| `src/impl.sdc` | Timing constraints used during implementation (place/route/CTS) |
| `src/signoff.sdc` | Timing constraints used for signoff STA |
| `pin_order.cfg` | Physical pin placement: `a[*]` north, `clk` east, `rst`/`$1` south, `x`/`y` west |

## Running

```bash
# From inside nix-shell at the openlane2 repo, or with openlane on PATH:
pd-agent run --design spm
```

Outputs land in `designs/spm/runs/RUN_<timestamp>/` (gitignored).

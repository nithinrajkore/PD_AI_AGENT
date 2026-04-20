# OpenLane 2 Quick Start

OpenLane 2 is a physical design flow orchestrator that wires together
several open-source EDA tools (Yosys, OpenROAD, TritonRoute, Magic) to
take an RTL design from HDL to a tapeout-ready GDSII.

## Prerequisites

Before running OpenLane 2 you need a working installation of Nix, a
checkout of the PDK you intend to target (for example SkyWater 130 nm),
and roughly 20 GB of free disk space for intermediate run artefacts.

## First run

Clone the repository, enter the development shell, and invoke the flow
against one of the example designs:

```bash
git clone https://github.com/efabless/openlane2
cd openlane2
nix develop
openlane --pdk sky130 openlane/examples/spm/config.json
```

The run should finish in a few minutes on a modern laptop and produce a
`runs/<timestamp>` directory containing the final GDSII and a
`metrics.json` report summarizing timing, area, and power.

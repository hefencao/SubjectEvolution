# SE v0.53

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains the conservative v3 regulatory-physiology substrate and adds inherited bounded raw-resource storage with delayed conversion.

## Why v0.53

The completed three-seed, 1500-tick conservative D2-L rerun closes the physiology flow ledger in every seed. Messenger synthesis, decay, finite precursor use/recovery, computation cost, fatigue turnover, and damage/repair remain active without negative flows. That result supports retaining the physiological substrate, but it does not complete the ecology chain.

The next structural bottleneck was that harvested external resources were still applied to energy, integrity, material, information, or fertility immediately. That direct same-tick reward keeps selection centered on acquisition even when functional and physiological variation exists.

v0.53 introduces an opt-in D3-A substrate:

- each of four raw resource channels enters an inherited bounded internal store;
- current-tick harvest cannot affect body state in the same tick;
- stored resource is converted from the next tick onward at an inherited per-channel rate;
- store occupancy becomes an input to the existing fixed functional operators;
- conversion still uses the existing versioned resource-effect matrix;
- decay, overflow, death loss, conversion, and final living stores close a raw-resource ledger.

All four channels use equal base storage, conversion, and decay parameters. Channel differences must arise from the external resource-effect matrix and inherited variation, not named metabolic roles.

## Workflow

After metadata or entry-point changes:

```bash
make conda-sync
```

Daily validation:

```bash
make test
make conda-check
```

Artifact audit:

```bash
make release-check
```

## Run D3-A

```bash
se-d3-resource-metabolism \
  --config configs/mvp_short_d3a_resource_metabolism_longrun.json \
  --seeds 53001,53002,53003 \
  --output analyses/d3a_resource_metabolism_1500 \
  --backend gpu \
  --until-tick 1500
```

D3-A is a substrate-evolution run, not a module-expression, niche, coexistence, or copy-number gate.

## Current version documents

- [D2-L v3 result interpretation](docs/v0.53/D2L_V3_RESULT_INTERPRETATION.md)
- [D3-A design](docs/v0.53/D3A_RESOURCE_METABOLISM_DESIGN.md)
- [D3-A run plan](docs/v0.53/D3A_RESOURCE_METABOLISM_PLAN.md)
- [Implementation report](docs/v0.53/IMPLEMENTATION_REPORT.md)

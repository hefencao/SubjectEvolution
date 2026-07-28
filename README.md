# SE v0.52

SE is a deterministic artificial-life and subject-structure research platform. The current main line keeps the fixed, auditable functional-operator kernel and inherited regulatory physiology introduced in v0.51, while correcting a conservation error discovered by the first 1500-tick D2-L run.

## v0.52 correction

The v0.51 `transport-metabolism-messenger-tissue-v2` runtime could pass a negative energy balance into a proportional messenger-synthesis limiter. That produced negative messenger synthesis, negative precursor use and negative synthesis energy in all three supplied seeds. The same path could erase or partially reverse energy debt before the world-level starvation settlement.

v0.52 therefore separates two schemas:

- `transport-metabolism-messenger-tissue-v2`: retained only for exact historical replay.
- `transport-metabolism-messenger-tissue-v3`: conservative runtime required for new D2-L experiments.

The v3 runtime guarantees that every reported physiology flow is finite and non-negative. Messenger synthesis and repair can spend only currently available non-negative substrate. Functional computation still incurs its real cost; if it pushes energy below zero, that debt is preserved until the existing world starvation step converts it into integrity loss.

No named organ, hormone, ecological role, diversity reward, new module, or new environment actor is introduced.

## Workflow

After updating project metadata or entry points:

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

## Re-run D2-L with conservative semantics

```bash
se-d2-regulatory-physiology \
  --config configs/mvp_short_d2l_regulatory_physiology_longrun.json \
  --seeds 51001,51002,51003 \
  --output analyses/d2l_regulatory_physiology_v3_1500 \
  --backend gpu \
  --until-tick 1500
```

Then audit the cumulative flow ledger:

```bash
se-d2-regulatory-physiology-assess \
  --results analyses/d2l_regulatory_physiology_v3_1500/d2_regulatory_physiology_results.json \
  --output analyses/d2l_regulatory_physiology_v3_assessment
```

The assessment checks conservation only. It is not a module-maturity, ecological-differentiation, or copy-number gate.

## Current version documents

- [Input-flow assessment](docs/v0.52/D2L_INPUT_FLOW_ASSESSMENT.md)
- [Conservative physiology correction](docs/v0.52/D2L_CONSERVATIVE_PHYSIOLOGY_DESIGN.md)
- [Re-run plan](docs/v0.52/D2L_CONSERVATIVE_PLAN.md)
- [Implementation report](docs/v0.52/IMPLEMENTATION_REPORT.md)

# SE v0.54

SE is a deterministic artificial-life and subject-structure research platform. The current main line keeps conservative regulatory physiology and delayed raw-resource conversion, then fixes the intake boundary so resources that cannot enter inherited stores are never removed from the environment.

## Why v0.54

The supplied three-seed D3-A run confirms that inherited storage and delayed conversion remain active and conservative over 1500 ticks. However, post-harvest store overflow was approximately 59%–62% of successfully stored material. The environment had already committed that extraction, so overflow disappeared from the external field without entering the entity or an external recycling pool.

That loss is a world-semantics artifact, not evidence for a metabolic strategy. v0.54 therefore introduces an opt-in D3-B intake contract:

- inherited free store room caps the raw environmental request before conflict resolution;
- affinity conversion is accounted for when translating assimilated room into raw external units;
- capacity-rejected raw material remains in the environmental cell;
- the policy resource view is reduced by current channel-specific store room;
- post-assimilation overflow is forbidden apart from floating-point tolerance;
- v0.53 resource-v4 behavior remains available for exact historical replay.

No resource role, metabolic type, ecological actor, diversity reward, or module topology is added.

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

## Run D3-B

```bash
se-d3-conservative-intake \
  --config configs/mvp_short_d3b_conservative_intake_longrun.json \
  --seeds 54001,54002,54003 \
  --output analyses/d3b_conservative_intake_1500 \
  --backend gpu \
  --until-tick 1500
```

D3-B verifies a conservative intake substrate. It is not a niche, coexistence, migration, trophic, or module-copy gate.

## Current version documents

- [D3-A result interpretation](docs/v0.54/D3A_RESULT_INTERPRETATION.md)
- [D3-B conservative intake design](docs/v0.54/D3B_CONSERVATIVE_INTAKE_DESIGN.md)
- [D3-B run plan](docs/v0.54/D3B_CONSERVATIVE_INTAKE_PLAN.md)
- [Implementation report](docs/v0.54/IMPLEMENTATION_REPORT.md)

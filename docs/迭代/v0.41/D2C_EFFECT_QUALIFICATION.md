# D2-C module effect qualification

## Purpose

D2-B leave-one-module-out branches are deterministic paired interventions, but
any non-zero endpoint difference is not automatically evidence of useful module
function. Small direct differences can amplify through births, deaths and keyed
state transitions, while expression-cost refunds can change mean energy without
showing a functional output effect.

D2-C therefore separates five levels:

1. **numerical divergence** — absolute effect above `1e-12`;
2. **practical magnitude** — outcome-specific threshold is exceeded;
3. **replication** — the same material direction occurs in at least four of six
   seed/phase conditions and at least two seeds, or the same phase-specific
   direction occurs in at least two seeds;
4. **immediate footprint** — removing the module immediately changes fixed
   harvest preference or the keyed conditional harvest-channel choice;
5. **copy-number gate** — the effect is cross-lineage, has positive ecological
   persistence or a preregistered phase trade-off, and is not measured in a
   lineage-dominated source population.

## Practical thresholds

| Outcome | Threshold |
|---|---:|
| alive | max(2 entities, 0.5% of baseline) |
| mean energy | 0.01 |
| environment resource effective dimensions | 0.02 |
| harvest extraction efficiency | 0.005 |
| effective transferred roots | max(2 roots, 1% of baseline) |
| effective lineages | 0.05 |
| functional harvest-preference dimensions | 0.02 |

These thresholds are versioned screening rules, not universal biological
constants. They determine whether a longer branch is worth running and whether
an observed contrast is large enough to interpret.

## Immediate checkpoint footprint

`d2-module-leave-one-out-results-v2` evaluates each source checkpoint before any
branch step. Every living entity is conditionally treated as a HARVEST actor and
is evaluated with the same keyed channel draw under:

- full module expression;
- all modules neutralized;
- each one-module neutralization.

It reports:

- exact preference-changed fraction;
- mean total-variation distance between preference vectors;
- conditional harvest-channel changed fraction;
- the same quantities for the largest eight genetic lineages.

The footprint does not alter the simulation and does not identify fitness. It
only proves that a module reaches the fixed action interface before trajectory
amplification.

## Automatic workflow

After the initial 120-tick audit:

```bash
se-d2-assess \
  --results analyses/d2b_module_audit_120/d2_module_audit_results.json \
  --output analyses/d2c_screen_120
```

The result is one of:

- `run-300-tick-confirmation`;
- `stop-and-redesign-before-longer-audit`.

After both horizons:

```bash
se-d2-assess \
  --short-results analyses/d2b_module_audit_120/d2_module_audit_results.json \
  --long-results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2c_effect_assessment \
  --refresh-footprints
```

`--refresh-footprints` loads the checkpoints referenced in the existing result
files and computes immediate lineage-resolved footprints. It does **not** rerun
any 120- or 300-tick branch.

## Duplication boundary

Module duplication remains blocked if any of the following holds:

- immediate footprint is unavailable;
- effects are only numerical or below practical thresholds;
- effects occur in only one seed;
- footprint is restricted to one lineage;
- there is no positive ecological persistence or preregistered phase trade-off;
- median effective lineage count is below four.

A repeated harmful effect still establishes function, but it does not justify a
copy-number expansion experiment by itself.

# SE project status

Version: **0.41.0**

## Current causal chain

```text
orthogonal external environment
→ inherited affinity-routed requests
→ inherited elastic capacities
→ bounded contextual harvest modules
→ per-module contribution and paired ablation
→ immediate/cross-lineage effect qualification
→ ecological niches and interactions
→ social organization
→ higher-level candidate subjects
```

## Supplied D2-B audit result

The supplied archive contains three seeds × peak/trough checkpoints at 120 and
300 ticks. Under the v0.41 practical thresholds, the 120-tick result correctly
qualifies for a 300-tick confirmation.

At 300 ticks:

- total module expression has a repeated positive extraction-efficiency effect;
- modules 2 and 3 have repeated positive extraction-efficiency effects;
- modules 1 and 3 repeatedly reduce effective transferred roots;
- modules 2 and 3 often reduce alive count while improving efficiency or
  environment dimensions;
- module 0 is mainly path/context dependent;
- functional preference dimensionality often decreases under expression.

These are non-trivial downstream effects, not a universal adaptive benefit.

## D2-C

Schemas:

- `d2-module-leave-one-out-results-v2`;
- `d2-module-immediate-footprint-v1`;
- `d2-module-effect-assessment-v1`.

`se-d2-assess` now defines the previously unclear standard:

1. exact deterministic non-zero;
2. practical outcome threshold;
3. same-direction or phase-conditioned replication across seeds;
4. immediate fixed-interface footprint;
5. cross-lineage footprint and lineage-dominance guard.

A 120-tick result automatically recommends either a 300-tick confirmation or a
stop/redesign. Existing v0.40 result JSON is accepted. Footprints can be
refreshed from source checkpoints without rerunning branches.

## Current gate

The supplied 300-tick results have median effective lineage count near `2.03`
and minimum near `1.57`. Their v1 result schema also lacks immediate footprint.
Module duplication and new ports remain blocked.

Next action:

```bash
se-d2-assess \
  --short-results analyses/d2b_module_audit_120/d2_module_audit_results.json \
  --long-results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2c_effect_assessment \
  --refresh-footprints
```

## Engineering workflow

The preferred local runtime remains conda + editable install:

```bash
make conda-sync
make test
make conda-check
```

v0.41 adds a sixth entry point, `se-d2-assess`, so one `make conda-sync` is
required after upgrading from v0.40.

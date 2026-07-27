# SE project status

Version: **0.42.0**

## Current causal chain

```text
orthogonal external environment
→ inherited affinity-routed requests
→ inherited elastic capacities
→ bounded contextual harvest modules
→ per-module contribution and paired ablation
→ immediate/cross-lineage effect qualification
→ lineage-conditioned paired causal audit
→ ecological niches and interactions
→ social organization
→ higher-level candidate subjects
```

## Supplied D2-C assessment

The supplied 120/300-tick assessment contains six checkpoint conditions. Its
refreshed immediate footprint is available for every module and is material in
multiple lineages. Modules 1, 2 and 3 have repeated ecological effects; modules
2 and 3 have repeated positive extraction-efficiency effects.

This establishes direct cross-lineage reach and repeated downstream action, but
not a universal adaptive benefit or a copy-number result. Alive count, energy,
environment dimensions, transfer roots and functional preference dimensions
still show trade-offs or context dependence.

## D2-D

Schemas:

- `d2-lineage-paired-plan-v1`;
- `d2-lineage-paired-results-v1`;
- `d2-module-effect-assessment-v2`;
- `structural-measurement-protocol-audit-v10`.

`se-d2-lineage-pairs` selects eligible lineages by pre-intervention membership
and creates three branches for each checkpoint × fixed module × lineage:

1. baseline output and cost;
2. output neutralized while cost remains;
3. output and cost both neutralized.

The exact decomposition separates routed-output effects from expression-cost
refunds. Genotype, lineage ID, module count, fixed input/output layout and keyed
randomness are preserved. Treatment follows descendants that retain the same
genetic lineage ID.

## Current gate

The supplied result has median effective lineage count `2.0260`, minimum
`1.5744`, and dominant-lineage risk. Duplication, deletion, arbitrary routing
and new output ports remain blocked. The next admissible experiment is a
lineage-balanced paired audit, initially for modules 2 and 3:

```bash
se-d2-lineage-pairs \
  --results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2d_lineage_pairs_120 \
  --modules 2,3 \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

Ineligible checkpoints are reported and skipped. They are not padded by
creating, protecting or rewarding lineages.

## Engineering workflow

The preferred local runtime remains conda + editable install:

```bash
make conda-sync
make test
make conda-check
```

v0.42 adds a seventh entry point, `se-d2-lineage-pairs`, so one
`make conda-sync` is required after upgrading from v0.41.

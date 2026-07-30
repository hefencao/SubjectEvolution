# D2-H source-population module-3 causal re-audit

## Why v0.46 was reissued

The project charter says that **major conclusions** require at least ten random seeds in the exploratory stage. The abandoned first v0.46 candidate treated this as a hard minimum for every exploratory audit and generated a new 10-seed-per-phase source-population replication. That interpretation was too broad.

The corrected design distinguishes decision scope:

- three paired seeds may route a lower-risk next experiment;
- the current result cannot support a precise general source-population claim;
- no result at this stage authorizes module copy-number changes.

## Evidence used

At 600 ticks without ongoing diversity protection:

| Phase | Equal-lineage | Natural-abundance | Exploratory decision |
|---|---:|---:|---|
| peak | 2/3 | 0/3 | continue phase-specific causal re-audit |
| trough | 1/3 | 0/3 | stop for now |

The peak 2/3 pass fraction has a wide two-sided 95% Wilson interval. The interval is reported to prevent overconfidence; it is not used as a significance threshold for this exploratory gate.

## Frozen checkpoints

D2-H selects only the two equal-lineage peak checkpoints that passed all preregistered D2-G guards:

- `peak_seed_45001`, tick 600;
- `peak_seed_45003`, tick 600.

Each checkpoint contains six lineages above the member floor with module 3 expressed. All six are retained. No lineage is selected by its previous response.

## Intervention

For every checkpoint-lineage pair, module 3 receives three shared-checkpoint branches:

1. baseline — routed output and expression cost retained;
2. output-neutral — routed output removed, expression cost retained;
3. expression-neutral — routed output and expression cost removed.

The decomposition remains:

- routed-output effect;
- retained expression-cost effect;
- total expression effect;
- additive residual, required to be zero within numerical tolerance.

## Horizons

The initial plan uses 120 ticks. A 300-tick plan is generated only when a practical routed-output effect repeats in at least two independent panel seeds and at least two non-dominant lineage identities. The confirmation plan preserves all preselected checkpoint-lineage pairs for module 3.

## Boundaries

D2-H does not:

- claim that peak is a generally valid source-population construction;
- use trough checkpoints;
- reward or protect lineages;
- change module count;
- add deletion, arbitrary output routing or new physical ports;
- infer ecological benefit from mean energy alone.

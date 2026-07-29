# v0.62 implementation report

v0.62 is a statistical interpretation and audit-boundary correction. It adds no simulated capability.

## Supplied-result audit

The supplied D3-H 1.5× v2 result contains three seeds and four preregistered checkpoints per seed. All 12 quartets completed, met acute sample support, shared checkpoint state, and closed checkpoint-relative resource and recycling ledgers. No checkpoint met the evolutionary-turnover gate.

Equal-checkpoint then equal-seed aggregation gives:

| Metric | Original | Reversed |
|---|---:|---:|
| Mean support gain | `6.47752786474193e-08` | `-7.434496869115597e-06` |
| Mean alignment cosine | `0.00012034033715960929` | `-0.006087301571671754` |
| Positive-gain fraction | `0.0005702243900956722` | `-0.0039622183760189235` |

Original seed means have signs negative, positive, negative. Reversed seed means are negative for all three seeds. No seed is positive in both orientations. The original leave-one-seed-out range crosses zero. The reversed exact two-sided sign-flip value is `0.25`, which is the limited resolution of three seeds and is not treated as confirmation.

## Implemented

- Upgrades the cross-scale audit schema to `d3-response-scale-audit-v2`.
- Validates stored v2 matched contrasts against branch response summaries.
- Requires valid interval resource and recycling ledgers for matched inference.
- Reconstructs fixed-window response metrics from cumulative trajectory sums and counts.
- Computes original and reversed active-minus-neutral effects under matched observation orientations.
- Weights checkpoints equally within a seed.
- Weights seeds equally within a scale.
- Reports positive checkpoint and window fractions.
- Reports leave-one-checkpoint and leave-one-seed sensitivity ranges.
- Reports exact two-sided seed sign-flip diagnostics for at most 20 seeds.
- Marks sign-flip values descriptive only.
- Adds explicit, configurable replication requirements with defaults of eight seeds and 75% directional consistency.
- Fixes the v0.61 Markdown summary table, whose header omitted the tracking-correlation column.
- Upgrades the structural protocol audit to v30.

## Interpretation

The supplied result is valid acute causal measurement but not replicated directional response evidence. More movement events or checkpoints cannot repair the independent seed count. The fixed v2 protocol should be repeated with at least eight independent seeds at both 1.5× and 2× scales before an observability, sensor, reward, or migration mechanism is considered.

## Excluded changes

No support sensor, reward, policy feature, controller, migration mechanism, population rescue, lineage protection, diversity protection, ecological role, or world feedback was added.

## Final verification

- 93/93 JSON configurations load and validate.
- 186 Python source, script, and test files compile.
- `make test`: 291 passed and 1 skipped across 61 test files.
- Non-Conda editable validation: 116 modules, 31 console entries, and external smoke passed.
- Isolated wheel and sdist validation passed.
- `make conda-sync` and the Conda-only stage of `make conda-check` were attempted and correctly stopped because `CONDA_PREFIX` was not set; the full tests inside `conda-check` passed first.
- No Conda state was fabricated.

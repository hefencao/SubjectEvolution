# v0.41 next experiment plan

## No new long run is required first

The existing 120- and 300-tick D2-B branches are sufficient for endpoint effect
qualification. The immediate footprint can be computed from their referenced
source checkpoints without rerunning branches.

```bash
se-d2-assess \
  --short-results analyses/d2b_module_audit_120/d2_module_audit_results.json \
  --long-results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2c_effect_assessment \
  --refresh-footprints
```

## Decision after footprint refresh

### Stop at D2-C when

- fewer than two checkpoints show a material direct footprint;
- direct footprint occurs in fewer than two seeds;
- fewer than two sufficiently populated lineages show the footprint;
- the dominant-lineage guard remains active;
- only expression-cost or extraction-efficiency effects repeat.

### Candidate for a future copy-number experiment only when

- one fixed homologous module has a direct footprint in at least two seeds and
  at least two lineages per qualifying checkpoint;
- a positive ecological effect repeats in at least two seeds, or a
  preregistered peak/trough sign reversal repeats by phase;
- the source population has median effective lineage count at least four;
- the effect is not explained only by maintenance-cost refunds;
- the result survives both 120- and 300-tick horizons.

## Current expectation

The supplied audits show repeated functional effects, especially for modules 2
and 3 at the extraction interface, but the lineage guard is active. The expected
next scientific action is therefore to retain fixed module slots and improve
cross-lineage evidence, not to implement duplication in v0.42 automatically.

# D2-D lineage-balanced paired module audit

## Trigger

D2-D is admissible only when D2-C has already established an immediate
cross-lineage footprint and repeated downstream effects, but the source
population fails the dominant-lineage guard. It is not a fallback for missing
footprints and it is not a route around the duplication gate.

## Selection

For each shared source checkpoint, eligible genetic lineages are selected only
from their pre-intervention living membership. The default plan keeps the four
largest lineages with at least eight living members and requires at least three
eligible lineages. Endpoint effects, module effect magnitude and desired
scientific conclusions are not used for selection.

Lineages remain at their natural abundance inside every branch. Equal weighting
is applied only to checkpoint-lineage paired contrasts during offline aggregation. No entity
is added, protected, rewarded, cloned or reassigned.

## Three paired branches

For every checkpoint × fixed module × selected lineage:

1. `baseline` retains inherited routed output and expression cost;
2. `output-neutral` removes that module's routed output only within the target
   lineage while retaining maintenance/development cost;
3. `expression-neutral` removes both routed output and expression cost within
   the target lineage.

The decomposition is:

- output routing effect = baseline − output-neutral;
- retained expression-cost effect = output-neutral − expression-neutral;
- total expression effect = baseline − expression-neutral.

The three contrasts close exactly, so an apparent ecological effect cannot be
silently attributed to a cost refund.

## Persistence and compatibility

The treatment follows descendants that retain the same genetic lineage ID for
the duration of the branch. Genotype, lineage IDs, stable entity IDs, module
count, routing vocabulary, checkpoint state and keyed randomness remain
unchanged.

When no lineage-targeted intervention is active, the new row-wise masks are
empty and the v0.41 authoritative path is unchanged.

## CLI

```bash
se-d2-lineage-pairs \
  --results analyses/d2b_module_audit_300/d2_module_audit_results.json \
  --output analyses/d2d_lineage_pairs_120 \
  --modules 2,3 \
  --horizon 120 \
  --min-lineage-members 8 \
  --min-lineages-per-checkpoint 3 \
  --max-lineages-per-checkpoint 4 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

The default priority is modules 2 and 3 because both have repeated positive
extraction-efficiency effects in the supplied D2-C assessment. This priority is
an experiment-order choice, not a predefined ecological role.

## Interpretation boundary

A lineage-targeted branch estimates a local causal effect within an interacting
world. Different lineages from one checkpoint are nested paired units, not
independent populations. Positive or repeated effects can justify a longer
lineage-balanced confirmation; they do not by themselves permit module
copy-number change.

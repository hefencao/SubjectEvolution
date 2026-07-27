# D2-I compositional functional module design

## Schemas

- module: `expression-gated-compositional-harvest-v2`
- input: `internal-needs-local-resources-feedforward-v2`
- output: `harvest-channel-zero-sum-residual-v1`
- coupling: `lower-slot-signal-modulation-v1`
- diagnostics: `functional-module-contribution-audit-v2`

## Genome layout

The original four module blocks remain unchanged. Six active genes are appended for all lower-to-higher slot links. There are no inert self-links or future-to-past links.

## Evaluation

For each slot, the original contextual activation is calculated first. For slots 1–3, inherited weighted upstream signals produce bounded modulation. The modulation scales the slot's contextual activation before its expression gate publishes the signed module signal. The final authoritative request residual retains the existing sum-then-round operation order.

The v1 schema uses the archived independent-additive path exactly. New behavior exists only when the v2 schema is explicitly configured.

## Costs and intervention

Coupling structure cost is proportional to absolute inherited coupling weight and target-slot expression. The intervention `neutralize-functional-module-coupling-output` disables feed-forward modulation only. It preserves direct module output, genes, mutation, expression cost and coupling structure cost.

## Diagnostics

The runtime records:

- hierarchy depth by module;
- coupling link count and weight effective dimensions;
- modulation and mediated signal by level;
- fraction of entities whose activation changes through coupling;
- per-level amplification and suppression;
- existing direct contribution, dominance, silence and cancellation metrics.

Diagnostics do not feed policy or world state.

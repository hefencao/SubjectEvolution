# Design boundary

## Control study

The v0.123 configuration and all primary study factors are retained. Stage 3C-10 adds observability only, so any difference from the prior Stage 3C-9 summary must be traceable to diagnostic representation rather than a changed intervention.

## Runtime facts versus analysis

The runtime adds only two optional fixed-capacity facts when the corresponding Stage-3 extensions are enabled: one `uint8` association reason per token-ring slot and six `uint16` eligibility ages at target binding. Added memory is `13 * entity_capacity * trace_capacity_per_subject` bytes; with 32 entities and 16 slots this is 6,656 bytes. Disabled configurations allocate neither field and retain canonical identity.

All funnel aggregation, magnitude summaries, target reuse, branch timelines and Stage-3C-8 sensitivity comparisons remain in `se.analysis`. No complete activation path or unbounded tick history is checkpointed.

## Primary hierarchy

The scientific aggregation remains `window -> stable subject -> independent source`. Subject-balanced mean is primary. Window-weighted mean, median, nonzero source count, nonzero subject fraction and window imbalance are diagnostics only.

## Forbidden conclusions

No objective coordinate is assigned value. A parameter-level divergence is not automatically a causal, beneficial or learning effect. No permanent retention, scalarization, attention optimality, topology evolution or Epoch-1 qualification follows from this workflow.

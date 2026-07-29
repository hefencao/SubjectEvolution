# SE project status

Version: **0.68.0**

## v0.68 post-bottleneck source-readiness boundary

The supplied three-seed D3-J panel reaches its population trough near tick 800 and rebounds by tick 1200. Final populations are 1,014–1,117, effective lineages are about 188–262, and the largest lineage remains below 3.5%. This rules out a simple claim that the remaining population is already monopolized by one lineage, but it does not establish effective selection.

v0.68 separates four questions:

1. did a severe initial contraction occur before turnover;
2. did a stable post-trough demographic regime emerge;
3. did descendants replace the founding cohort;
4. did reproduction involve many independent contributors rather than repeated births by a few parents.

`se-multi` now preregisters the seed set and output schedule before execution and automatically emits the demographic-selection audit after execution.

## Current execution and scientific chain

```text
role-free four-channel resources
→ conservative storage/recycling/renewal
→ costed spatial processing and matched controls
→ GPU-first large-population execution with target-device parity
→ initial bottleneck and death-cause audit
→ post-trough population + descendant + parent-contributor audit
→ fixed burn-in rule tested on new independent seeds
→ only then replicated evolutionary-selection inference
```

## Current gates

1. Re-analyze retained raw D3-J seed directories with v0.68; rerunning the simulations is not required.
2. Run the fixed D3-K 3,000-tick panel if raw D3-J progress is unavailable or turnover remains unresolved.
3. Do not count repeated windows or births as independent seed replication.
4. A pilot-derived burn-in tick may only preregister future independent runs.
5. Preserve every insufficient seed and window; no outcome-based replacement.
6. Keep migration, specialization, coexistence and ecotype gates closed.

## Still incomplete

- raw v0.68 re-analysis of the supplied D3-J seed directories;
- replicated source-ready post-bottleneck regime;
- adequate descendant replacement and reproductive-contributor breadth;
- causal decomposition of any persistent mortality pressure;
- device-resident action settlement, lifecycle and graph updates;
- positive replicated processing-response evidence.

# Three-seed 1500-tick assessment

This assessment uses the supplied `multi-seed-long-run-analysis-v1` aggregate. The original three `evolution_progress.jsonl` streams were not attached, so v0.17 first-difference and partial-correlation diagnostics cannot be reconstructed from this aggregate alone.

## Endpoint replication

| Run | Alive | Effective lineages | Largest lineage | Strategy dimensions | Action entropy | Cohesion | Lineage-group pair enrichment |
|---|---:|---:|---:|---:|---:|---:|---:|
| seed_10001 | 1381 | 17.3257 | 0.1760 | 15.7431 | 1.7241 | 0.3791 | 3.6218 |
| seed_10002 | 1337 | 22.3203 | 0.0957 | 19.5730 | 1.7425 | 0.4178 | 4.7385 |
| seed_10003 | 1341 | 22.1673 | 0.1156 | 20.0626 | 1.7500 | 0.4184 | 4.3413 |

Across seeds:

- final alive: `1353.0 ± 19.9`;
- effective founder lineages: `20.60 ± 2.32`;
- largest founder lineage fraction: `0.129 ± 0.034`;
- strategy effective dimensions: `18.46 ± 1.93`;
- action entropy: `1.7389 ± 0.0109`;
- boundary cohesion: `0.405 ± 0.018`.

The heterogeneous affinity world therefore retains substantially more functional strategy dimensions at tick 1500 than the old single-niche 3000-tick runs. This is evidence that additional physical trade-off axes are active, not proof that they remain indefinitely open-ended.

## Repeated raw within-run directions

- mortality and same-window cohesion: `+0.6209 / +0.3435 / +0.4240`.
- mortality and next-window cohesion: `+0.6490 / +0.3629 / +0.4025`.
- effective lineages and cohesion: `-0.8727 / -0.8715 / -0.8958`.
- largest-lineage fraction and cohesion: `+0.4559 / +0.6673 / +0.7827`.
- strategy dimensions and action entropy: `+0.9727 / +0.9820 / +0.9787`.
- lineage-group NMI and cohesion: `+0.2174 / +0.2090 / +0.3389`.
- lineage-group pair enrichment and cohesion: `-0.2513 / -0.2920 / -0.0282`.

Four points follow:

1. Mortality/cohesion correlations are positive in all three runs, so the pressure-associated cohesion pulse is a robust observational pattern. It is not yet a causal law.
2. Effective-lineage/cohesion correlations are strongly negative in all three runs, while largest-lineage/cohesion correlations are positive. This is opposite to the claim that more lineage diversity directly locks cohesion high. Shared time trends or ecological phase may dominate the raw correlation.
3. Lineage-group pair enrichment has weak or negative raw association with cohesion. Group/lineage alignment therefore does not currently explain cohesion by itself.
4. Strategy dimensions and action entropy move together in all three runs. Functional strategy contraction and behavioral concentration are the strongest replicated structural relationship in the supplied aggregate.

## Knowledge-lineage interpretation limit

All three endpoints report roughly 11–12 thousand effective root contents, an extremely small largest-root holder fraction, and zero root/genetic-lineage pair enrichment. Under the bundled long-run configuration, transfer probability is zero. If these runs used that configuration unchanged, the root metrics primarily count private experience creation and cannot be interpreted as cultural transmission. v0.17 therefore adds a costed-transfer long-run condition and an explicit analyzer warning.

## Direction selected for v0.17

- Do not add another cognitive layer or another resource channel.
- Replace raw-trend interpretation with first differences, partial correlations and lag diagnostics.
- Run scientific checkpoint interventions at rise, peak, decline and trough phases.
- Neutralize affinity expression without changing genes; disable knowledge residual, memory, selector or future transfer independently.
- Use a costed-transfer condition before drawing conclusions about independent cultural/knowledge lineages.

## Interpretation boundary

The supplied aggregate supports repeated directionality and path dependence. It does not prove necessity, intent, or a unique causal mechanism. The original per-window streams are required to recompute v0.17 detrended diagnostics.

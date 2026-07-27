# SE project status

Version: **0.44.0**

## Current causal chain

```text
orthogonal external environment
→ inherited affinity-routed requests
→ inherited elastic capacities
→ bounded contextual harvest modules
→ per-module contribution and paired ablation
→ immediate/cross-lineage effect qualification
→ lineage-conditioned paired causal audit
→ cross-seed/cross-horizon persistence qualification
→ temporal flow-energy-demography mediation
→ ecological niches and interactions
→ social organization
→ higher-level candidate subjects
```

## D2-E supplied-result decision

The supplied assessment pairs a 300-tick result with the original 120-tick screen. Module 2 does not retain a same-pair, same-direction practical output effect across horizons. Module 3 retains a positive routed-output effect on `target_lineage.mean_energy` in two seeds and two non-dominant lineage identities, but no positive ecological routed-output outcome is confirmed.

The target-lineage survival effect reverses between the 120- and 300-tick assessments. This makes a survivor-conditioned mean and delayed demographic conversion plausible alternatives. Median effective lineages remain about `2.2722`, so the dominant-lineage guard still fails.

## D2-F implementation

v0.44 adds a temporal mediation plan, result and assessment layer:

- `d2-lineage-mediation-plan-v1`;
- `d2-lineage-mediation-results-v1`;
- `d2-lineage-mediation-assessment-v1`;
- `se-d2-lineage-mediate`;
- `se-d2-lineage-mediate-assess`;
- `structural-measurement-protocol-audit-v12`.

The plan selects confirmed modules only and preserves every source checkpoint-lineage pair for those modules. For the supplied result this means module 3, six checkpoints and 24 lineage pairs. Default observations occur at 30, 60, 120, 180, 240 and 300 ticks within the same branch execution.

A read-only `Simulation.run(..., tick_observer=...)` hook records experiment observations after authoritative steps. With no observer, historical runtime behavior is unchanged. The mediation trajectory reports energy stock and quartiles, source survivors, descendants, births, deaths by cause, fertility, reproduction readiness, harvested energy and shared-energy receipts.

## Current gate

Duplication, deletion, arbitrary routing and new output ports remain blocked. Mean energy alone is a process outcome, not ecological benefit. A future positive demographic conversion would still require a source population that passes the lineage guard and a shared-checkpoint confirmation without diversity reward or protection.

## Engineering workflow

```bash
make conda-sync
make test
make conda-check
```

v0.44 adds two console entries, so one `make conda-sync` is required after upgrading from v0.43.

# D1-B three-seed long-run assessment

Input schema: `multi-seed-long-run-analysis-v12`
Analyzer/runtime: `0.37.0` / `['0.37.0']`

> The source report is observational. This assessment changes measurement and experiment tooling, not the interpretation boundary.

| Run | Alive | Resource dims | Resource mean |corr| | Capacity dims | WM util. | Knowledge util. | Relation util. | Extraction eff. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| seed_10001 | 462 | 1.8331 | 0.6044 | 3.4556 | 0.9957 | 0.9290 | 0.7865 | 0.6403 |
| seed_10002 | 458 | 2.0041 | 0.5433 | 3.4597 | 0.9955 | 0.9355 | 0.7235 | 0.6320 |
| seed_10003 | 418 | 1.7372 | 0.6423 | 3.7609 | 1.0000 | 0.9385 | 0.7330 | 0.6820 |

## Decision

- D0 persistence passes the minimum gate: all three final global resource dimensions remain above 1.7.
- D1 capacity use passes the minimum gate: all three runs retain more than 3.4 effective capacity dimensions, with working memory nearly saturated and knowledge/relations materially used.
- The v0.37 demand metric does **not** identify channel demand composition. It uses realized extraction volumes; all channels co-move with population and HARVEST action volume, so a near-one raw temporal dimension is not evidence of collapsed phenotype routing.
- D2 remains blocked until explicit requested-channel composition and the preregistered affinity × capacity paired checkpoint effects are available.

## v0.38 response

1. Record requested and realized resources separately at the authoritative conflict/commit boundary.
2. Report raw volume and per-window share composition separately.
3. Refuse to reconstruct selective requested-channel composition from old realized-only records.
4. Add a four-branch paired factorial executor: baseline, affinity-neutral, capacity-neutral, and combined-neutral.

# SE project status

Version: **0.46.0**

## Current causal chain

```text
orthogonal external environment
→ inherited affinity-routed requests
→ inherited elastic capacities
→ bounded contextual harvest modules
→ paired module and lineage interventions
→ temporal flow-energy-demography mediation
→ genotype-only source-population reconstitution
→ phase-specific causal re-estimation in redesigned checkpoints
→ ecological niches and interactions
→ social organization
→ higher-level candidate subjects
```

## Charter interpretation used in v0.46

`PROJECT_CHARTER.md` states that **major conclusions** require at least ten random seeds in the exploratory stage. It does not state that every exploratory audit or every next-step gate must run ten seeds.

v0.46 therefore separates:

1. **exploratory experiment routing** — a paired three-seed audit may justify a lower-risk next causal experiment when preregistered hard guards and at least two independent seeds agree;
2. **general source-population claims** — the current n=3 result is too imprecise and remains phase-specific;
3. **copy-number decisions** — still blocked regardless of the exploratory routing decision.

## Supplied D2-G result

After 600 ticks of ordinary dynamics without ongoing lineage protection:

- peak equal-lineage arm: 2/3 qualified;
- peak natural-abundance control: 0/3 qualified;
- trough equal-lineage arm: 1/3 qualified;
- trough natural-abundance control: 0/3 qualified.

The peak equal-lineage pass fraction has a wide two-sided 95% Wilson interval of approximately `[0.208, 0.939]`. The result is not a precise population-level estimate, but the paired 2/3 versus 0/3 pattern and the preregistered absolute guards are sufficient for a phase-specific exploratory module-3 re-audit.

## D2-H implementation

v0.46 adds:

- `d2-source-population-assessment-v2`;
- `d2-source-population-causal-plan-v1`;
- `d2-source-population-causal-results-v1`;
- `d2-source-population-causal-assessment-v1`;
- `se-d2-source-causal`;
- `se-d2-source-causal-assess`;
- `structural-measurement-protocol-audit-v14`.

The generated 120-tick plan selects only peak fresh-world seeds `45001` and `45003`, because they passed the preregistered D2-G guards. It retains all six member- and expression-qualified panel lineages in each checkpoint. It does not select lineages by response magnitude.

Each module-lineage pair uses:

- baseline;
- output-neutral with expression cost retained;
- expression-neutral with output and expression cost removed.

The first run is a 120-tick screen. A 300-tick confirmation plan is generated only if routed-output effects repeat under the existing practical-effect and cross-seed rules.

## Current gate

Module duplication, deletion, arbitrary routing and new output ports remain blocked. A positive D2-H result would establish only phase-specific exploratory causal persistence in redesigned checkpoints. Higher-confidence replication, ecological persistence and an independently preregistered copy-number design would still be required.

## Engineering workflow

```bash
make conda-sync
make test
make conda-check
```

v0.46 changes version metadata and adds two console entries, so one `make conda-sync` is required after upgrading from v0.45.

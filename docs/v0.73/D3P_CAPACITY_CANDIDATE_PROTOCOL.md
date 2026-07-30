# D3-P elastic-capacity acute-use candidate

D3-P addresses the still-open capacity-specific question without returning to a large long run.

The candidate specification is stored in:

`protocols/candidates/d3p_elastic_capacity_acute_effect.json`

The paired branches start from the same per-seed tick-480 checkpoints:

- baseline: inherited elastic capacities remain expressed;
- intervention: all four effective capacity coordinates are neutralized to their configured midpoint while genotype and inheritance remain unchanged.

Primary estimand:

- metric: cumulative working-memory active dimensions;
- response: post-checkpoint cumulative increment;
- effect: intervention minus baseline within seed;
- independent unit: seed;
- direction: two-sided;
- minimum practical relative effect: 5%.

Operational manipulation checks are mandatory:

1. baseline capacity effective dimensions must exceed 0.25;
2. intervention capacity effective dimensions must be at most `1e-12`.

A failure of either check makes the panel ineligible. Passing the manipulation checks does not itself count as a downstream mechanism effect.

This screen can identify an acute realized-use effect of elastic capacity expression. It cannot establish long-horizon selection for capacity genes.

## Execution

First import the completed D3-O assessment into the shared decision ledger:

```bash
se-exploration-candidate-record \
  --assessment analyses/d3o_affinity_paired_screen/paired_exploration_assessment.json \
  --ledger analyses/exploration_candidate_ledger.json
```

Then create the D3-P screen from the existing checkpoint source:

```bash
se-exploration-paired-plan \
  --stage screen \
  --candidate-spec protocols/candidates/d3p_elastic_capacity_acute_effect.json \
  --source-root analyses/d3n_screen \
  --checkpoint-tick 480 \
  --output analyses/d3p_capacity_paired_screen \
  --decision-ledger analyses/exploration_candidate_ledger.json \
  --backend auto
```

Execute the generated plan:

```bash
se-exploration-paired \
  --plan analyses/d3p_capacity_paired_screen/paired_exploration_plan.json
```

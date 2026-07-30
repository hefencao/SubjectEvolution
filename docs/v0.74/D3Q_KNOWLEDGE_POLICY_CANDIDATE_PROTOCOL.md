# D3-Q knowledge-policy acute-harvest candidate

D3-Q moves one level upward in the causal chain after the capacity-use candidate fails. It asks whether the complete knowledge-policy residual publication layer has a practically material acute effect on realized harvest.

## Fixed specification

- candidate: `knowledge-policy-harvest-acute-effect-v1`
- intervention: `disable-knowledge-policy`
- primary metric: cumulative `harvested-resource-total`
- response window: 120 ticks
- direction: two-sided
- minimum practical relative effect: 2%
- independent unit: seed

## Manipulation contract

A seed is eligible only when:

1. the baseline branch reports knowledge-policy influence enabled;
2. the intervention branch reports it disabled;
3. the baseline branch contains at least one action changed by the knowledge-policy residual during the response window;
4. the intervention branch contains zero such changed actions.

This separates target engagement from the downstream harvest effect. If the baseline residual does not change any action in a seed, that seed does not provide evidence about harvest consequences of the mechanism.

## Execution

First record the completed D3-P assessment in the shared ledger:

```bash
se-exploration-candidate-record \
  --assessment analyses/d3p_capacity_paired_screen/paired_exploration_assessment.json \
  --ledger analyses/exploration_candidate_ledger.json
```

Then create the D3-Q screen from the existing tick-480 checkpoint source:

```bash
se-exploration-paired-plan \
  --stage screen \
  --candidate-spec protocols/candidates/d3q_knowledge_policy_harvest_acute_effect.json \
  --source-root analyses/d3n_screen \
  --checkpoint-tick 480 \
  --output analyses/d3q_knowledge_policy_paired_screen \
  --decision-ledger analyses/exploration_candidate_ledger.json \
  --backend auto
```

Execute the generated plan:

```bash
se-exploration-paired \
  --plan analyses/d3q_knowledge_policy_paired_screen/paired_exploration_plan.json
```

D3-Q remains an acute mechanism screen. Passing it would permit disjoint-seed acute replication, not a long-horizon evolutionary selection claim.

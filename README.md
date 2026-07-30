# SE v0.73

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains role-free four-channel resources, conservative storage and recycling, persistent abiotic renewal, costed physiology and information processing, GPU-first execution, matched controls, and explicit scientific-validity gates.

## Current result

The D3-O resource-affinity paired screen is complete:

- eight of eight seed panels are eligible;
- five effects are positive and three are negative;
- direction consistency is 0.625, below the preregistered 0.75 gate;
- the equal-seed median relative effect is about 0.00334, below the 0.01 practical threshold.

The candidate is stopped before replication. The compact legacy bundle proves that the promotion gates failed, but it does not contain a self-contained direct manipulation check; the decision is therefore a terminal promotion stop, not a universal causal-null claim. Prior local or channel-specific affinity effects remain bounded evidence.

## Candidate decision ledger

Completed paired assessments are recorded in a deterministic ledger:

```bash
se-exploration-candidate-record \
  --assessment analyses/d3o_affinity_paired_screen/paired_exploration_assessment.json \
  --ledger analyses/exploration_candidate_ledger.json
```

A terminal candidate cannot be silently reopened by changing its label, threshold, response horizon, metric, direction, or intervention. A changed scientific specification requires an explicit new candidate revision.

## Next bounded screen

D3-P tests the still-open elastic-capacity realized-use question using the existing tick-480 discovery checkpoints:

```bash
se-exploration-paired-plan \
  --stage screen \
  --candidate-spec protocols/candidates/d3p_elastic_capacity_acute_effect.json \
  --source-root analyses/d3n_screen \
  --checkpoint-tick 480 \
  --output analyses/d3p_capacity_paired_screen \
  --decision-ledger analyses/exploration_candidate_ledger.json \
  --backend auto

se-exploration-paired \
  --plan analyses/d3p_capacity_paired_screen/paired_exploration_plan.json
```

The candidate specification locks the intervention, primary metric, direction, practical threshold, response horizon, and direct manipulation checks. A seed panel is inferentially eligible only when source support, both branch-support checks, and every manipulation check pass.

## Promotion boundary

```text
paired smoke
→ eight-seed paired screen
→ eight new-seed paired replication
→ explicit acute confirmation on new seeds
```

Even a passed paired confirmation supports only the preregistered acute mechanism effect. Long-horizon evolutionary selection requires a separate protocol.

## Workflow

```bash
make conda-sync
make test
make conda-check
make release-check
```

## Current version documents

- [Implementation report](docs/v0.73/IMPLEMENTATION_REPORT.md)
- [D3-O supplied candidate decision](docs/v0.73/D3O_SUPPLIED_CANDIDATE_DECISION.md)
- [D3-P capacity candidate protocol](docs/v0.73/D3P_CAPACITY_CANDIDATE_PROTOCOL.md)
- [Protocol audit](docs/v0.73/protocol_audit.md)

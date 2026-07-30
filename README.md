# SE v0.72

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains role-free four-channel resources, conservative storage and recycling, persistent abiotic renewal, costed physiology and information processing, GPU-first execution, matched controls, and explicit scientific-validity gates.

## Why v0.72

The completed D3-N free-run screen used eight independent seeds at 1,125 initial entities. All eight runs reached tick 480 with 138–165 living entities. The endpoint decline was highly repeatable and energy-depletion dominated, while each run still retained enough living entities, founder-lineage breadth, and current strategy variation for a short acute intervention panel.

This reveals a protocol distinction:

```text
free-running startup trajectory
≠ candidate-effect screen

fixed per-seed checkpoint
→ matched baseline/intervention branches
→ seed-level paired effect
```

A free-run endpoint may identify a reproducible source phase, but it does not measure a candidate effect. v0.72 therefore converts the exploration stages from endpoint screening to fixed-checkpoint paired panels.

## Re-audit an existing source panel

```bash
se-exploration-readiness \
  --selection-audit analyses/d3n_screen/selection_validity_audit.json \
  --long-run-analysis analyses/d3n_screen/long_run_analysis.json \
  --output analyses/d3n_screen/readiness_v2
```

The readiness audit uses scale-normalized acute thresholds. Demographic turnover and a stable population source are not required for a short paired mechanism panel; they remain required for long-horizon evolutionary interpretation.

## Create a paired screen from existing checkpoints

The D3-N screen wrote full checkpoints every 120 ticks. A predeclared tick-480 checkpoint can be reused without rerunning the shared prefix:

```bash
se-exploration-paired-plan \
  --stage screen \
  --candidate resource-affinity-acute-effect \
  --source-root analyses/d3n_screen \
  --checkpoint-tick 480 \
  --response-ticks 120 \
  --intervention neutralize-resource-affinity \
  --primary-metric harvested-resource-total \
  --metric-mode cumulative \
  --direction two-sided \
  --minimum-relative-effect 0.01 \
  --output analyses/d3o_affinity_paired_screen \
  --backend auto

se-exploration-paired \
  --plan analyses/d3o_affinity_paired_screen/paired_exploration_plan.json
```

The plan locks every checkpoint hash before branch execution. Baseline and intervention branches start from the same full checkpoint and preserve keyed randomness. The output reports one matched effect per seed, equal seed weighting, direction consistency, a predeclared practical-effect threshold, and an exact sign-flip statistic.

## Promotion boundary

```text
paired smoke
→ eight-seed paired screen
→ eight new-seed paired replication
→ explicit confirmation on new seeds
```

Replication requires a passing screen assessment and disjoint seeds. Confirmation requires a passing replication assessment, disjoint seeds across all prior stages, and explicit authorization. Large long runs remain confirmation-only.

## Workflow

```bash
make conda-sync
make test
make conda-check
make release-check
```

## Current version documents

- [Implementation report](docs/v0.72/IMPLEMENTATION_REPORT.md)
- [D3-N supplied screen audit](docs/v0.72/D3N_SUPPLIED_SCREEN_AUDIT.md)
- [D3-O paired exploration protocol](docs/v0.72/D3O_PAIRED_EXPLORATION_PROTOCOL.md)
- [Protocol audit](docs/v0.72/protocol_audit.md)

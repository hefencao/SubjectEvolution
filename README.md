# SE v0.71

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains role-free four-channel resources, conservative storage and recycling, persistent abiotic renewal, costed spatial processing, GPU-first execution, matched controls and explicit scientific-validity gates.

## Why v0.71

The completed D3-M scale-4 panel establishes that long trajectories can provide substantial within-run demographic evidence without providing confirmation-level independent replication.

At tick 5000, the three runs contain 23,533–28,523 living entities, complete descendant replacement and roughly 2,278–2,480 effective successful parents in the final window. These are adequate within-run observational samples. However, there are only three independent seeds, founder-lineage inverse-Simpson counts remain about 14–35, and no common future source rule is supported.

The correct response is not to repeat large long runs during every exploratory step. v0.71 introduces a tiered protocol:

```text
smoke
→ small independent-seed screen
→ disjoint-seed replication
→ large long confirmation only for promoted candidates
```

Repeated windows, entities, births, moves and policy events remain nested observations. The seed is the independent unit.

## Exploration readiness

Audit an existing multi-seed result:

```bash
se-exploration-readiness \
  --selection-audit analyses/<run>/selection_validity_audit.json \
  --long-run-analysis analyses/<run>/long_run_analysis.json \
  --output analyses/<run>/exploration_readiness
```

`se-multi` now emits this audit automatically after its selection-validity audit.

## Bounded exploration stages

Generate a screen plan:

```bash
se-exploration-plan \
  --stage screen \
  --candidate d3-next-candidate \
  --config configs/mvp_d3n_exploration_screen.json \
  --seeds 71101,71102,71103,71104,71105,71106,71107,71108 \
  --output analyses/d3n_screen \
  --backend auto
```

Then run the exact pre-registered invocation printed by the plan. `se-multi --exploration-plan ...` rejects changes to the config hash, seeds, output, backend or horizon.

Default limits:

- smoke: at most 512 initial entities and 180 ticks;
- screen: at most 2,048 initial entities and 600 ticks, at least eight seeds;
- replication: at most 4,096 initial entities and 900 ticks, at least eight new seeds;
- confirmation: explicit authorization, after a disjoint-seed replication plan.

Large long execution remains available, but it is no longer the default exploratory path.

## Workflow

```bash
make conda-sync
make test
make conda-check
make release-check
```

## Current version documents

- [Implementation report](docs/v0.71/IMPLEMENTATION_REPORT.md)
- [D3-M sample adequacy audit](docs/v0.71/D3M_SAMPLE_ADEQUACY_AUDIT.md)
- [D3-N tiered exploration protocol](docs/v0.71/D3N_TIERED_EXPLORATION_PROTOCOL.md)
- [Protocol audit](docs/v0.71/protocol_audit.md)

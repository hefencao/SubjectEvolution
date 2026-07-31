# d3o-resource-affinity-v1 frozen run chain

Candidate: `resource-affinity-acute-effect`
Study schema: `se-study-bundle-v1`
Chain schema: `se-study-chain-lock-v1`

This file summarizes immutable evidence only. Authorized operations are declared in `workflow.toml` and rendered by `se-study`; no executable shell runbook is required.

## Design

Legacy acute screen of whether inherited resource-affinity expression materially changes total realized harvest.

## Legacy decision-only stages

These rows preserve the strongest surviving release evidence. Missing raw artifacts are declared rather than reconstructed.

| Stage | Seeds | Decision | Recommendation | Completeness | Lock |
|---|---:|---|---|---|---|
| screen | 8 | stop | stop-direction-not-replicated-across-seeds | legacy-decision-only | `studies/d3o_resource_affinity_v1/frozen/legacy/screen.lock.json` |

## Path roles

- source trajectories and checkpoints belong under `runs/base/`;
- intervention branches belong under `runs/interventions/`;
- derived assessments and audits belong under `analyses/`;
- mutable workspace decision overlays belong under `state/decisions/`;
- this study directory contains protocol, a declarative workflow, and frozen evidence.

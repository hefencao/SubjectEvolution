# d3p-elastic-capacity-use-v1 frozen run chain

Candidate: `elastic-capacity-use-acute-effect-v1`
Study schema: `se-study-bundle-v1`
Chain schema: `se-study-chain-lock-v1`

This file summarizes immutable evidence only. Authorized operations are declared in `workflow.toml` and rendered by `se-study`; no executable shell runbook is required.

## Design

Acute matched screen of whether inherited elastic capacity expression materially changes realized working-memory use.

## Legacy decision-only stages

These rows preserve the strongest surviving release evidence. Missing raw artifacts are declared rather than reconstructed.

| Stage | Seeds | Decision | Recommendation | Completeness | Lock |
|---|---:|---|---|---|---|
| screen | 8 | stop | stop-direction-not-replicated-across-seeds | legacy-decision-only | `studies/d3p_elastic_capacity_use_v1/frozen/legacy/screen.lock.json` |

## Path roles

- source trajectories and checkpoints belong under `runs/base/`;
- intervention branches belong under `runs/interventions/`;
- derived assessments and audits belong under `analyses/`;
- mutable workspace decision overlays belong under `state/decisions/`;
- this study directory contains protocol, a declarative workflow, and frozen evidence.

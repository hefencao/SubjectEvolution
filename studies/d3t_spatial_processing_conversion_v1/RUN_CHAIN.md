# d3t-spatial-processing-conversion-v1 frozen run chain

Candidate: `spatial-processing-conversion-acute-effect-v1`
Study schema: `se-study-bundle-v1`
Chain schema: `se-study-chain-lock-v1`

This file summarizes immutable evidence only. Authorized operations are declared in `workflow.toml` and rendered by `se-study`; no executable shell runbook is required.

## Design

Matched fixed-checkpoint test of the direct effect of phase-shifted spatial processing support on realized conservative raw-resource conversion. The intervention neutralizes support while preserving conversion cost, genotype, resource fields and shared checkpoints.

## Full frozen stages

Source protocol SHA-256: `709daa77f95ebeb2adb6d9a5e6d29b478f59b91aac32b0dbde8571021522d2ab`

| Stage | Seeds | Binding | Median effect | Direction | Decision | Recommendation | Manifest |
|---|---:|---|---:|---:|---|---|---|
| screen | 8 | paired-plan-source-hash-binding | +3.026463% | 1.000 | promote | promote-to-disjoint-replication | `studies/d3t_spatial_processing_conversion_v1/frozen/screen/stage.lock.json` |
| replication | 8 | exact-candidate | +2.546072% | 1.000 | promote | promote-to-explicit-confirmation | `studies/d3t_spatial_processing_conversion_v1/frozen/replication/stage.lock.json` |
| confirmation | 8 | exact-candidate | +2.827052% | 1.000 | confirmed-acute | confirmation-gate-passed-interpret-acute-mechanism-only | `studies/d3t_spatial_processing_conversion_v1/frozen/confirmation/stage.lock.json` |

## Path roles

- source trajectories and checkpoints belong under `runs/base/`;
- intervention branches belong under `runs/interventions/`;
- derived assessments and audits belong under `analyses/`;
- mutable workspace decision overlays belong under `state/decisions/`;
- this study directory contains protocol, a declarative workflow, and frozen evidence.

# v0.30 patch notes

## Added

- `subject_evolution.subject_structure`
- `subject_evolution.environment_atlas`
- `subject_evolution.structure_environment_analysis`
- `stable-membership-subject-succession-v1`
- `multiscale-subject-environment-atlas-v1`
- `multi-seed-subject-environment-analysis-v1`
- `multi-seed-long-run-analysis-v9`
- `structural-measurement-protocol-audit-v2`
- `configs/mvp_short_subject_structure_multienvironment_atlas_longrun.json`

## Changed

- run config supports optional succession and atlas diagnostics;
- simulation manifest/checkpoint/clone/final metadata includes diagnostic provenance/state;
- protocol audit includes subject succession and environment atlas;
- long-run analysis includes final succession and atlas endpoints;
- version updated to 0.30.0.

## Compatibility

New diagnostics are disabled by default. Existing configurations retain the v0.29 world trajectory. Trusted v0.29 full checkpoints remain readable.

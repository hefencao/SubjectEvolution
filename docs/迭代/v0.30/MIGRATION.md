# Migration from v0.29 to v0.30

No existing configuration must change.

To enable the new diagnostics, add to `run`:

```json
{
  "subject_structure_diagnostics_enabled": true,
  "subject_structure_diagnostics_schema": "stable-membership-subject-succession-v1",
  "environment_atlas_diagnostics_enabled": true,
  "environment_atlas_diagnostics_schema": "multiscale-subject-environment-atlas-v1",
  "environment_atlas_scales": [[2, 2], [4, 4], [8, 8]]
}
```

Rules:

- enabled/schema fields must agree;
- enabled atlas requires at least one unique positive scale;
- each scale cannot exceed the physical world grid;
- disabled atlas requires an empty scale list.

Existing v0.29 `.sechk` files can be restored. Missing v0.30 diagnostic state starts empty because those diagnostics did not exist in the source run.

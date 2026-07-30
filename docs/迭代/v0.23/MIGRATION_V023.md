# Migration to v0.23

## Scientific configurations

Keep the environment extension disabled:

```json
"environment_process_schema": "disabled",
"environment_process_parameters": {}
```

The flagship mortality-trace + adaptive-groups long-run configuration now states this explicitly.

## Existing v0.22 moving-hazard configurations

No edit is required. The fields below are resolved through the compatibility adapter:

```json
"moving_hazard_schema": "moving-gaussian-hazard-sources-v1"
```

Their world trajectory remains compatible, but `scientific_validity.json` now labels this synthetic mechanism as outside the scientific ecology baseline.

## New optional plugin configurations

Use `environment_process_schema` plus a JSON object of parameters. The schema must be registered before configuration validation, either programmatically or through the installed entry-point group `subject_evolution.environment_processes`.

Do not set both the new generic fields and non-disabled `moving_hazard_schema` fields.

## Checkpoints

v0.22 and older trusted checkpoints remain readable. On restore, the process object is rebuilt from the embedded authoritative configuration rather than trusted from a pickled implementation object.

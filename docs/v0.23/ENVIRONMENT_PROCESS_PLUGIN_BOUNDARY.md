# Environment process plugin boundary (v0.23)

## Purpose

`subject_evolution.environment_process` is a low-coupling extension point for optional environmental scalar fields. It separates the scientific core from synthetic observation/game mechanisms and prevents optional hazards from becoming a duplicate biological population.

API schema:

```text
additive-environment-field-process-v1
```

## Core contract

A registered process implements:

```python
def hazard_delta(*, tick, xnorm, ynorm, xp) -> array:
    ...
```

The returned value must:

- match the world hazard grid shape;
- contain only finite values;
- be non-negative;
- avoid mutating the supplied grids.

The process receives no entity, action, relationship, lineage, knowledge, memory, birth, death or controller state.

## Registration

Programmatic registration:

```python
from subject_evolution.environment_process import (
    EnvironmentProcessDescriptor,
    register_environment_process,
)

register_environment_process(descriptor, factory)
```

Installed packages may expose a zero-argument registrar under the entry-point group:

```text
subject_evolution.environment_processes
```

Plugins are executable Python dependencies and must be trusted like any other installed package.

## Configuration

New generic form:

```json
{
  "environment_process_schema": "some-registered-schema-v1",
  "environment_process_parameters": {
    "parameter": 1.0
  }
}
```

Scientific baseline:

```json
{
  "environment_process_schema": "disabled",
  "environment_process_parameters": {}
}
```

The old v0.22 `moving_hazard_*` fields remain as a compatibility adapter. New configurations should not combine the generic and legacy forms.

## Built-in compatibility plugin

The former moving Gaussian branch is now implemented in:

```text
subject_evolution.plugins.moving_gaussian_hazard
```

Descriptor:

- schema: `moving-gaussian-hazard-sources-v1`;
- mechanism class: `abiotic-additive-scalar-field`;
- interpretation: `synthetic-observation-or-entertainment-extension`;
- default enabled: false.

It has no biological identity or feedback hooks. Its numeric formula is unchanged from v0.22.

## Provenance

`run_manifest.json`, run metadata, metrics and long-run analysis v7 record:

- process API schema;
- resolved process schema;
- origin (`core-disabled`, generic config, or v0.22 adapter);
- mechanism class and interpretation;
- parameter names and a stable parameter hash.

Raw parameter values remain in `resolved_config.json`; the manifest hash provides a compact audit field.

## Compatibility

The disabled scientific baseline and the v0.22 moving-hazard adapter were compared against v0.22 for ten CPU ticks:

- 308 common non-timing metrics fields: exact, zero mismatches;
- seven knowledge/event CSV/JSONL logs: byte-identical in both conditions;
- generic plugin configuration and legacy fields produce identical moving Gaussian hazard arrays.

## Scientific validity

Enabling a process marked `synthetic-observation-or-entertainment-extension` adds an explicit scientific-validity violation. The run remains executable for replay, visualization and game experiments, but it cannot silently masquerade as the scientific ecology baseline.

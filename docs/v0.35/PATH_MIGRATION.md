# v0.35 path migration

## Rationale

The old namespace repeated long structural words in almost every AI-visible import. v0.35 shortens only high-frequency paths with well-established meanings.

| Old | New |
|---|---|
| `subject_evolution` | `se` |
| `subject_evolution.config` | `se.cfg` |
| `subject_evolution.commands` | `se.cmd` |
| `subject_evolution.domains.environment` | `se.env` |
| `subject_evolution.domains.evolution` | `se.evolution` |
| `subject_evolution.domains.knowledge` | `se.knowledge` |
| `subject_evolution.domains.subjects` | `se.subjects` |
| `subject_evolution.interfaces.gui` | `se.gui` |
| `subject_evolution.runtime.simulation` | `se.runtime.sim` |
| `subject_evolution.analysis.structure_environment` | `se.analysis.structure_env` |

## Deliberately retained full names

`analysis`, `experiments`, `evolution`, `knowledge`, `subjects`, `runtime`, `information`, `metrics` and scientific config fields remain full words. Short forms such as `ana`, `exp`, `evo`, `know` and `subj` save little while increasing ambiguity.

## CLI

| Old | New |
|---|---|
| `subject-evolution` | `se` |
| `subject-evolution-multi-seed` | `se-multi` |
| `subject-evolution-gui` | `se-gui` |

No compatibility aliases are installed.

## Checkpoints

Old pickle module paths are intentionally unsupported. Re-run the simulation or create a new `se` checkpoint.

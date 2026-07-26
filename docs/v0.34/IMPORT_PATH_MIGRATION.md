# v0.34 import path migration

v0.34 removes forwarding modules instead of maintaining aliases for every moved implementation.

## Runtime

| Removed path | Canonical path |
|---|---|
| `subject_evolution.cli` | `subject_evolution.commands.run` or `subject-evolution` |
| `subject_evolution.multi_seed` | `subject_evolution.commands.multi_seed` or `subject-evolution-multi-seed` |
| `subject_evolution.simulation` | `subject_evolution.runtime.simulation` and `subject_evolution.runtime.state` |

`subject_evolution.simulation` remains importable only for historical trusted-checkpoint pickle decoding. New code must not use it.

## Environment

| Removed path | Canonical path |
|---|---|
| `subject_evolution.environment` | `subject_evolution.domains.environment.world` |
| `subject_evolution.gpu_environment` | `subject_evolution.domains.environment.gpu` |
| `subject_evolution.environment_atlas` | `subject_evolution.domains.environment.atlas` |
| `subject_evolution.environment_diversity` | `subject_evolution.domains.environment.diversity` |
| `subject_evolution.environment_process` | `subject_evolution.domains.environment.process` |
| `subject_evolution.danger_evidence` | `subject_evolution.domains.environment.danger_evidence` |
| `subject_evolution.local_stress` | `subject_evolution.domains.environment.local_stress` |
| `subject_evolution.niches` | `subject_evolution.domains.environment.niches` |
| `subject_evolution.spatial` | `subject_evolution.domains.environment.spatial` |
| `subject_evolution.spatial_partition` | `subject_evolution.domains.environment.partition` |

## Evolution, subjects and knowledge

| Removed path | Canonical path |
|---|---|
| `subject_evolution.evolution` | `subject_evolution.domains.evolution.progress` |
| `subject_evolution.lifecycle` | `subject_evolution.domains.evolution.lifecycle` |
| `subject_evolution.control` | `subject_evolution.domains.subjects.control` |
| `subject_evolution.social` | `subject_evolution.domains.subjects.social` |
| `subject_evolution.subjects` | `subject_evolution.domains.subjects.graph` |
| `subject_evolution.subject_structure` | `subject_evolution.domains.subjects.succession` |
| `subject_evolution.knowledge` | `subject_evolution.domains.knowledge` |
| `subject_evolution.knowledge_policy` | `subject_evolution.domains.knowledge.policy` |
| `subject_evolution.latent_knowledge` | `subject_evolution.domains.knowledge.latent` |
| `subject_evolution.working_memory` | `subject_evolution.domains.knowledge.working_memory` |
| `subject_evolution.routing_cost` | `subject_evolution.domains.knowledge.routing_cost` |
| `subject_evolution.knowledge_subjects` | `subject_evolution.domains.knowledge.subjects` |

## Analysis and experiments

Analysis modules live under `subject_evolution.analysis`; branch/replay/natural-event runners live under `subject_evolution.experiments`. The old top-level filenames are removed.

Examples:

```bash
python -m subject_evolution.analysis.parity ...
python -m subject_evolution.analysis.protocol_audit ...
python -m subject_evolution.analysis.long_run ...
python -m subject_evolution.experiments.natural_event_execution ...
python -m subject_evolution.experiments.natural_event_timed_execution ...
```

## GUI

`subject_evolution.gui_interface` is removed. Use:

```python
from subject_evolution.interfaces.gui import SharedFramePublisher, SharedFrameReader
```

or the `subject-evolution-gui` console script.

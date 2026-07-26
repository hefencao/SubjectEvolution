# Facade removal and dependency cleanup

v0.33 kept a generic proxy module for every implementation moved during the first package split. That preserved old imports but also kept the old flat architecture alive: internal runtime and domain files continued importing through forwarding modules, assignments could be proxied into implementation modules, and every new package move required another compatibility file.

v0.34 removes that model.

## Retained bridge

Only `subject_evolution.simulation` remains. Historical trusted checkpoints contain pickle references to `subject_evolution.simulation.EntityState`, `StepStats`, and in some cases `Simulation`. Removing this module would make already generated trusted project checkpoints unreadable. The bridge explicitly exports only those classes and the periodic-coordinate helper. It does not proxy arbitrary attributes or monkey patches.

## Dependency corrections

- Authoritative environment math is owned by `domains.environment`, not `analysis`.
- Knowledge implementation files import sibling modules directly.
- Runtime and domains do not import analysis, experiments, commands or GUI interfaces.
- Commands and GUI import canonical runtime APIs.
- Tests patch the concrete module that owns a symbol.

## Compatibility policy

Future moves should prefer explicit migration and batch import updates. A compatibility bridge is permitted only when a serialized external artifact, stable plugin ABI or genuinely independent downstream API cannot be migrated atomically. Convenience alone is not sufficient.

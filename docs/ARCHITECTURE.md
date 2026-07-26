# Architecture

## Package layout

```text
se/
├── analysis/       # offline analysis and audits
├── cmd/            # CLI implementations
├── env/            # authoritative environment domain
├── evolution/      # lifecycle and evolution progress
├── experiments/    # replay and counterfactual execution
├── gui/            # observation-only shared-frame interface
├── knowledge/      # knowledge storage, routing, memory and diagnostics
├── runtime/        # authoritative state, step/run, checkpoint and reports
├── subjects/       # social relations, subject graph and succession
├── cfg.py
└── ...             # shared infrastructure
```

Only common and unambiguous abbreviations are used. Domain terms whose shortened form is ambiguous remain fully spelled.

## Dependency direction

```text
cfg / shared infrastructure
            ↓
env / evolution / knowledge / subjects
            ↓
runtime
            ↓
cmd / gui

analysis / experiments → runtime + domains
runtime + domains ✕→ analysis / experiments / gui
```

`se.env.diversity` owns orthogonal-field generation and resource-diversity primitives because those functions participate in authoritative environment updates. Offline analysis may call domain primitives; domains never import offline analysis.

## Authoritative world loop

```text
versioned cfg
    ↓
env / information / spatial / social snapshots
    ↓
read-only observations
    ↓
heritable policy + knowledge residual + memory + sparse selection
    ↓
control proposal → arbitration → action intent
    ↓
read-only conflict resolution plan
    ↓
controlled commit
    ↓
entity / env / information / relation / lifecycle / knowledge / subject updates
    ↓
metrics / logs / checkpoint / offline analysis
```

Strategies, knowledge routing, controllers and conflict resolvers do not directly mutate authoritative state. Only versioned commit stages may write the world.

## Backend boundary

- `cpu`: authoritative reference semantics.
- `gpu` + `strict-reference`: validate the device, keep CPU reference world semantics.
- `gpu` + `hybrid-accelerated`: selected array stages run on device; long-run full-world parity remains a separate requirement.

Python remains the protocol, reference and orchestration layer. Stable numeric hotspots may later move to CuPy kernels or C++/CUDA extensions behind versioned plan/result boundaries. Compute shaders remain non-authoritative visualization candidates.

## GUI boundary

`se.gui` publishes a one-way, latest-frame-only shared-memory stream. The GUI may drop frames but cannot write world state, inject actions or create authoritative scientific checkpoints.

## Checkpoints

v0.35 intentionally starts a new Python module namespace. Checkpoints produced by `se` are self-consistent, but checkpoints whose pickle payload encodes the removed `subject_evolution` namespace are not supported. Re-running is the migration policy.

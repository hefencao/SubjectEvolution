# Architecture

## Package layout

```text
se/
├── analysis/       # offline analysis and audits
├── cmd/            # CLI implementations
├── env/            # authoritative environment domain
├── differentiation/# inherited phenotype-capacity mechanisms
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
env / differentiation / evolution / knowledge / subjects
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
heritable body policy + knowledge residual + capacity-masked memory/knowledge/social mechanisms
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

## Differentiation boundary

`se.differentiation` owns genotype-to-capacity expression and explicit structural/development costs. D1 keeps fixed physical tensor maxima and varies only effective masks. The domain does not assign ecological roles, observe lineage rarity or protect diversity.

D1 capacity expression feeds existing domain mechanisms through typed arrays on `EntityState`. Knowledge, social and memory domains consume those capacities directly; they do not derive them independently. The runtime is the only layer that charges cross-domain capacity costs and commits lifecycle changes.

`neutralize-elastic-capacities` is a phenotype-expression intervention. It leaves genotype and mutation intact, allowing matched branches to test effective capacity without rewriting ancestry.

## Backend boundary

- `cpu`: authoritative reference semantics.
- `gpu` + `strict-reference`: validate the device, keep CPU reference world semantics.
- `gpu` + `hybrid-accelerated`: selected array stages run on device; long-run full-world parity remains a separate requirement.

Python remains the protocol, reference and orchestration layer. Stable numeric hotspots may later move to CuPy kernels or C++/CUDA extensions behind versioned plan/result boundaries. Compute shaders remain non-authoritative visualization candidates.

## GUI boundary

`se.gui` publishes a one-way, latest-frame-only shared-memory stream. The GUI may drop frames but cannot write world state, inject actions or create authoritative scientific checkpoints.

## Checkpoints

Checkpoints produced by the current `se` namespace are trusted Python-state snapshots and are exact within the registered schema. v0.36 adds explicit capacity arrays and capacity-ablation state. Old removed namespaces are not supported; re-running remains the migration policy.

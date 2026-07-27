# D2-B functional-module contribution audit

## Motivation

The 3000-tick D2-A runs show that modules are expressed and alter almost every
entity's harvest preference, but the authoritative residual magnitude remains
small. Structural expression is therefore not sufficient evidence of causal
function. Module duplication, deletion, or open output routing remains blocked.

D2-B adds two measurement layers without expanding the function vocabulary:

1. per-module observational contribution diagnostics during ordinary runs;
2. paired leave-one-module-out checkpoint interventions.

## Authoritative-path boundary

The D2-A world calculation remains:

```text
fixed inputs
→ expression gate
→ module signal
→ routed zero-sum residuals
→ sum raw module outputs
→ one final quantization
→ fixed-budget harvest preference
```

D2-B computes isolated per-module residuals for diagnostics, but those rounded
isolated values never feed the world. The authoritative sum and final rounding
order are preserved exactly.

## Per-module diagnostics

Schema:

```text
functional-module-contribution-audit-v1
```

For each of four fixed module slots, the progress record now reports:

- gate mean and expressed fraction;
- activation and signal magnitude;
- isolated residual magnitude;
- fraction of entities with a non-zero isolated contribution;
- fraction expressed but effectively silent after quantization;
- contribution share.

Population summaries also report:

- effective number of contributing modules;
- largest contribution share (dominance);
- cancellation fraction between isolated module outputs and the final summed
  residual;
- current module-ablation mask.

These are observation-only fields and cannot affect policy, fitness, mutation,
resource fields, or subject construction.

## Partial expression interventions

New interventions:

```text
neutralize-functional-module-0
neutralize-functional-module-1
neutralize-functional-module-2
neutralize-functional-module-3
```

The existing all-module intervention remains:

```text
neutralize-functional-modules
```

Partial neutralization:

- preserves genotype and module homology;
- disables only the selected expression slot;
- removes that slot's maintenance cost;
- refunds the corresponding fraction of newborn development cost;
- persists through checkpoint/restore and future births.

## Leave-one-out experiment

Entry point:

```bash
se-d2-audit
```

Branches per shared checkpoint:

```text
baseline
all-modules-neutral
module-0-neutral
module-1-neutral
module-2-neutral
module-3-neutral
```

Effects use the expressed branch minus its paired neutralized branch. The audit
also reports:

```text
all-module effect - sum(individual module effects)
```

as local non-additivity. It can reveal redundancy, cancellation, or interaction,
but not universal necessity.

Example:

```bash
se-d2-audit \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10001 \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10002 \
  --run-dir runs/d2a_contextual_modules_multiseed/seed_10003 \
  --output analyses/d2b_module_audit \
  --phases peak,trough \
  --horizon 120 \
  --execute \
  --backend gpu \
  --gpu-semantics-mode strict-reference
```

An existing `d2_module_audit_plan.json` can be reused with `--plan`.

## Interpretation gate

Do not introduce duplication or new physical ports unless at least two seeds
show all of the following:

- a module has a repeatable leave-one-out downstream effect;
- the effect exceeds its maintenance/development cost at some phases and
  reverses or weakens at others;
- contribution is not entirely dominated by one fixed slot;
- effects persist beyond one 120-tick local branch;
- genotype diversity is sufficient to distinguish module evolution from one
  surviving lineage's historical accident.

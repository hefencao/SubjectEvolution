# D2-A contextual functional modules

## Schema

```text
expression-gated-contextual-harvest-v1
```

## Fixed tensor layout

Each entity has four inherited modules. Each module contains:

1. one expression-gate gene;
2. ten input weights;
3. one bias;
4. four output-router weights.

The physical layout is fixed for all entities and remains batchable. No module
adds Python/C++ code or changes array shapes at runtime.

## Inputs

```text
bias
energy deficit
integrity deficit
material deficit
information-store deficit
fertility deficit
local resource channels 0..3, normalized by capacity
```

The vocabulary is explicitly architecture-dependent and versioned. Modules do
not receive lineage ID, group label, rarity, future outcomes or offline analysis.

## Output

The only output is a zero-sum residual over four harvest-channel request
weights. The result is renormalized to the same integer budget as static
resource affinity. It can change the probability of requesting one channel but
cannot increase total requested resources.

Static affinity still controls:

- resource assimilation efficiency;
- resource-gradient policy utility.

D2-A therefore tests contextual request routing rather than adding a second full
action policy.

## Expression and costs

- positive gate genes express continuously above the configured threshold;
- a gene value of one corresponds to full expression, with saturation above one;
- maintenance cost is paid per expressed gate strength per tick;
- development cost is paid by newborns;
- `neutralize-functional-modules` sets effective output residual to zero without
  modifying genotype and suppresses module expression costs in that branch.

## Diagnostics

Each evolution window can report:

- expressed modules per entity and gate strength;
- gate effective dimensions;
- contextual request-preference dimensions;
- mean/max absolute module residual share;
- fraction of entities whose request weights changed;
- residual effective dimensions;
- dominant input and output counts;
- input-weight and output-router effective dimensions;
- maintenance/development energy.

## Interpretation boundary

A non-zero residual is a mechanism effect, not an adaptive function. Function
claims require same-checkpoint neutralization and repeated downstream effects.
The current layer cannot be called an organ generator and cannot create a new
physical interaction.

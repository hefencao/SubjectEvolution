# D1-A inherited elastic capacities

Schema: `inherited-elastic-capacities-v1`

## Purpose

D1-A makes the usable scale of four existing mechanisms independently heritable:

1. quantized working-memory dimensions;
2. dynamic-knowledge storage bytes;
3. social relationship slots;
4. incoming knowledge-attention slots per tick.

This is capacity differentiation, not a menu of ecological roles. The world still exposes the same sensors, actions, resource channels, knowledge operations and relationship semantics. Entities inherit only how much of those fixed mechanisms they can express and maintain.

## Fixed physical layout and effective masks

Arrays keep their configuration maxima so CPU/GPU memory layout remains fixed. Four appended genome coordinates map monotonically from `[-1, 1]` to discrete effective capacities. The D1 flagship bounds are:

| Capacity | Physical maximum | Effective levels |
|---|---:|---|
| Working memory | 4 dimensions | 0–4 integer dimensions |
| Knowledge storage | 512 bytes | 0–512 in 32-byte quanta |
| Relationships | 8 slots | 0–8 integer slots |
| Incoming attention | 2 transfers/tick | 0–2 integer slots |

The capacity genes are appended after all pre-existing genome regions. They do not overlap morphology, body policy, resource affinity, danger evidence, latent routing, working-memory parameters or inherited Top-k genes.

## Mechanism reach

- **Working memory:** dimensions above the effective width are masked in reads and writes. Requested use energy scales with the effective width.
- **Knowledge storage:** seeding, copied knowledge and new experience obey per-entity byte limits. Existing copies above a newly reduced limit are evicted oldest-first.
- **Relationships:** only the first effective slots can be inserted, matched or replaced. Disabled physical slots are cleared.
- **Knowledge attention:** transfer proposals are canonically ordered and each receiver accepts at most its effective slots per tick.

## Costs

D1 adds two explicit cost classes:

- per-tick structural maintenance cost for expressed capacity;
- birth-time development cost for constructing inherited capacity.

Existing mechanisms retain their own use costs. Therefore reserved capacity, actual use and development are not collapsed into one undifferentiated “brain tax”.

## Mutation and inheritance

Each capacity coordinate uses the registered D1 mutation probability and magnitude. `freeze-genotype` also freezes capacity mutation. Capacity genes remain ordinary inherited coordinates; D1 does not protect rare values, reward diversity or assign roles.

## Causal neutralization

Intervention:

```text
neutralize-elastic-capacities
```

The intervention sets all living entities and future offspring to the midpoint discrete expression:

```text
working memory = 2
knowledge bytes = 256
relation slots = 4
attention slots = 1
```

It does not modify genotype or mutation. Relationship tables and working-memory coordinates are immediately trimmed; excess knowledge is immediately evicted. The intervention and its continuing expression state are checkpointed.

This identifies the effect of inherited capacity expression relative to a fixed midpoint expression. It does not by itself identify which individual capacity is beneficial; later experiments must neutralize one capacity at a time or use a pre-registered factorial design.

## Current boundary

D1-A does not yet evolve sensor range, body storage, physical mass, module count or development timing. It also does not prove ecological differentiation. Long-run evidence must show selection response, actual-use differences, environment-conditional outcomes and persistence across seeds.

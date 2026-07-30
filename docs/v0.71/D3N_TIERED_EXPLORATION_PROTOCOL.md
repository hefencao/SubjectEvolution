# D3-N tiered exploration protocol

## Objective

Reduce exploratory cost without converting repeated within-run observations into false replication.

## Evidence boundary

The D3-M three-seed panel has strong within-run population, descendant and reproductive-contributor support. It does not have enough independent seeds for confirmation, and founder-lineage breadth does not support a common source rule.

This means:

- no additional large long run is required merely to try a new mechanism or diagnostic;
- exploratory direction must be measured across more independent seeds at smaller scale;
- any promoted result must be repeated on disjoint seeds;
- a large long run is reserved for final confirmation and regime compatibility.

## Stages

### Smoke

Purpose: schema, mechanism, ledger, checkpoint and parity validation.

- at least 2 seeds;
- at most 512 initial entities;
- at most 180 ticks;
- no selection claim.

### Screen

Purpose: inexpensive directional screening.

- at least 8 independent seeds;
- at most 2,048 initial entities;
- at most 600 ticks;
- windows and events remain nested inside seeds;
- no confirmation claim.

### Replication

Purpose: repeat a promoted screen without seed reuse.

- at least 8 independent seeds;
- seeds disjoint from the screen;
- at most 4,096 initial entities;
- at most 900 ticks;
- no confirmation claim.

### Confirmation

Purpose: test a candidate that passed both previous stages.

- at least 8 new seeds;
- seeds disjoint from all prior stages;
- explicit authorization for large or long execution;
- fixed horizon and no outcome-conditioned replacement;
- only this stage may support a selection claim.

## Presets

- `mvp_d3n_exploration_smoke.json`
- `mvp_d3n_exploration_screen.json`
- `mvp_d3n_exploration_replication.json`

The presets preserve the D3-E world semantics and use bounded GPU allocator cache behavior. They change only scale, horizon and reporting cadence.

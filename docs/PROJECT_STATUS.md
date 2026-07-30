# SE project status

Version: **0.78.0**

## Current result

The supplied portfolio audit reported D3-P and D3-Q as awaiting assessment because the workspace ledger contained only the recent D3-R and D3-S decisions. This is an incomplete-history reconstruction error, not a new empirical result.

v0.78 merges an immutable five-entry release baseline with the workspace ledger. The reconciled portfolio contains every terminal decision already established by the project.

## Mechanism-family state

- `knowledge-policy` revision 1: closed by the D3-Q aggregate gate;
- `functional-modules` revision 1: closed by the D3-S aggregate gate;
- `resource-affinity` revision 1: no aggregate closure, but D3-O is terminal and no replacement candidate is preregistered.

No shipped paired candidate is open or awaiting assessment. The effective portfolio state is `scientific-revision-required`.

## Decision-history architecture

```text
immutable release decision baseline
                +
append-only workspace analysis ledger
                ↓ deterministic conflict-checked merge
candidate recording / portfolio audit / paired-plan validation
```

A partial workspace cannot erase historical terminal decisions. An incompatible workspace entry fails validation instead of replacing release history. `se-exploration-ledger-hydrate` can write the effective merged history back to the workspace without changing any scientific decision.

## Current exploration policy

```text
candidate specification
→ fixed checkpoint matched screen
→ direct manipulation assessment
→ seed-level practical-effect gate
→ bounded negative requires aggregate family gate
→ aggregate terminal negative closes the family revision
→ reopening requires higher revision + rationale + new measurable interface
→ immutable terminal history survives clean packaging and workspace resets
→ no automatic replacement-candidate selection
→ disjoint-seed replication only after promotion
```

## Current task

Do not rerun D3-P or D3-Q. The next scientific task remains defining a genuinely distinct family or a higher closed-family revision with an explicit new directly measurable interface. No candidate is selected automatically in v0.78.

## Still incomplete

- a replicated paired acute effect for an open candidate;
- a stable common post-bottleneck source rule;
- confirmation-level long-horizon selection evidence;
- causal decomposition of founder-lineage contraction;
- device-resident action settlement, lifecycle and graph updates.

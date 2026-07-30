# v0.78 implementation report

## Supplied portfolio audit

The supplied audit reported `candidate-specs-awaiting-assessment` because the workspace ledger contained only the D3-R and D3-S decisions. That report does not represent new simulation evidence. It is a state-reconstruction failure: D3-P and D3-Q were already terminal in the project decision history, but the command treated the disposable workspace ledger as the complete historical record.

## Immutable decision baseline

v0.78 promotes terminal candidate history from a version-specific documentation artifact to an immutable release input. The canonical five-entry ledger is shipped in both:

- `protocols/decisions/exploration_candidate_ledger.json` for repository inspection;
- `se/resources/exploration_candidate_ledger.json` for installed console commands.

Candidate recording, portfolio audit and paired-plan validation now merge this baseline with the workspace ledger. The workspace remains an append-only analysis overlay. A partial workspace cannot erase earlier terminal decisions, and an incompatible workspace entry is rejected instead of replacing the baseline.

## Workspace hydration

The new command:

```bash
se-exploration-ledger-hydrate \
  --ledger analyses/exploration_candidate_ledger.json
```

writes the effective merged history back to the workspace ledger without changing any decision, threshold, seed set, horizon or mechanism-family state.

## Reconciled state

Replaying the supplied two-entry workspace against the immutable baseline produces:

- no unrecorded shipped candidate specifications;
- no open candidate;
- `knowledge-policy` revision 1 closed by D3-Q;
- `functional-modules` revision 1 closed by D3-S;
- portfolio state `scientific-revision-required`.

The next scientific task therefore remains a genuinely distinct family or a higher family revision with an explicit rationale and a new directly measurable interface. v0.78 does not select that mechanism automatically.

No reward, world mechanism, cost, checkpoint rule, random stream or experimental threshold is changed.

# SE v0.78

Reference implementation for nested-subject existence evolution simulation.

## Current bounded result

The supplied portfolio audit used a workspace decision ledger containing only D3-R and D3-S, so it incorrectly reported D3-P and D3-Q as awaiting assessment. This was not new scientific evidence and did not authorize rerunning either candidate.

v0.78 ships an immutable five-entry decision baseline and merges it with the workspace ledger in candidate recording, portfolio audit and paired-plan validation. Reconciliation restores the established state:

- `knowledge-policy` revision 1 is closed by D3-Q;
- `functional-modules` revision 1 is closed by D3-S;
- no shipped candidate is open or awaiting assessment;
- the portfolio remains `scientific-revision-required`.

A partial workspace can no longer erase terminal history. Conflicting workspace history is rejected.

## Suggested commands

Because v0.78 adds a console entry and package resource, update the editable Conda installation first:

```bash
make conda-sync

se-exploration-ledger-hydrate \
  --ledger analyses/exploration_candidate_ledger.json

se-exploration-portfolio-audit \
  --ledger analyses/exploration_candidate_ledger.json \
  --candidate-dir protocols/candidates \
  --output analyses/exploration_portfolio_audit
```

The hydrate command only reconstructs the complete historical ledger. It does not alter any scientific decision or feed information back into the world.

## Validation workflow

```bash
make test
make conda-check
make parity-gpu
```

`make parity-gpu` is a target-device release gate and intentionally fails when no usable CUDA/CuPy device is present.

## Current documents

- [Project status](docs/PROJECT_STATUS.md)
- [Scientific issues](docs/SCIENTIFIC_ISSUES.md)
- [Recurring governance check](docs/PROJECT_GOVERNANCE.md)
- [Implementation report](docs/v0.78/IMPLEMENTATION_REPORT.md)
- [Governance check](docs/v0.78/GOVERNANCE_CHECK.md)
- [Supplied partial-workspace audit](docs/v0.78/SUPPLIED_PORTFOLIO_AUDIT.md)
- [Reconciled portfolio audit](docs/v0.78/RECONCILED_PORTFOLIO_AUDIT.md)
- [Immutable decision baseline](docs/v0.78/DECISION_BASELINE.json)
- [Protocol audit](docs/v0.78/protocol_audit.md)

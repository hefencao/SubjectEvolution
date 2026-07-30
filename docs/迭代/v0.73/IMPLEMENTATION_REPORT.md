# v0.73 implementation report

v0.73 closes the failed D3-O resource-affinity candidate and makes candidate decisions durable.

## Candidate decision ledger

Every completed paired panel records a deterministic candidate decision. A terminal candidate cannot be silently reopened by:

- changing its label;
- lowering its practical threshold;
- changing its response horizon;
- changing its primary metric or direction while retaining the same candidate identity.

A changed scientific specification requires an explicit new candidate revision.

## Self-contained paired results

Paired results now retain, per seed:

- intervention record;
- branch scientific-validity records;
- scientific warnings;
- operational manipulation checks and observed values;
- a relative counterfactual-summary reference.

Promotion requires both inferential support and successful preregistered manipulation checks.

## Next bounded candidate

D3-P tests elastic-capacity expression against cumulative realized working-memory use using the existing fixed checkpoint discovery set. It does not require a new free-running prehistory or a large long run.

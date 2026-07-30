# v0.78 governance check

## Data and task root cause

The supplied result is a governance audit, not a new empirical screen. Its unexpected `candidate-specs-awaiting-assessment` state comes from incomplete historical reconstruction: the workspace ledger retained only two recent decisions while earlier terminal decisions existed only in shipped documentation. The scientific task is not changed to rerun D3-P or D3-Q.

## Long-term principles

A terminal experimental decision is release state, not disposable analysis output. Every clean package must carry an immutable decision baseline; workspace ledgers may append to it but may not erase or override it.

Validation still runs every iteration. When validation is successful, the delivery response does not need a detailed validation report. Each iteration must provide the recommended next commands.

## Chat-only principles

The two delivery-workflow rules above were new in this conversation and are now recorded in `docs/PROJECT_GOVERNANCE.md`. No newly active principle remains only in chat.

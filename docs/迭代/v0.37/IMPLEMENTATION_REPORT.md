# v0.37 implementation report

## Implemented

- Added `affinity-sampled-exclusive-harvest-v1`.
- Added a dedicated state-free random stream for harvest channel choice.
- Applied identical request construction to CPU and GPU harvest planners.
- Preserved the historical total request budget while making nonselected
  channels exactly zero.
- Corrected partial-harvest outcome classification for exclusive requests.
- Added harvest schema and budget semantics to manifests, metrics and protocol
  audit v5.
- Upgraded long-run analysis to v12 with analyzer/runtime provenance.
- Added strict rejection of incomplete D1 progress without capacity fields.
- Added realized harvest channel totals, shares, dimensions, correlations and
  requested-budget efficiency.
- Expanded capacity-use diagnostics with utilization and saturation.
- Added D1-B smoke and 1500-tick long-run configs.

## Not implemented

- D2 universal functional operators;
- module duplication or deletion;
- automatic diversity protection;
- local-abundance greedy channel selection;
- dynamic code generation;
- a new ecological role taxonomy.

## Scientific boundary

D1-B is a demand-routing mechanism.  It is retained because the paired smoke
shows a substantial reduction in common resource demand with a measurable
extraction-efficiency cost.  The result is not a long-run adaptive claim.

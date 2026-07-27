# v0.44 implementation report

## Scientific decision from the supplied 300-tick assessment

- Module 2 passed the 120-tick screen but did not retain a same-pair, same-direction practical routed-output effect at 300 ticks.
- Module 3 retained a positive routed-output effect on `target_lineage.mean_energy` across two seeds and two non-dominant lineage identities.
- No positive ecological routed-output outcome was confirmed.
- The source population remains lineage-concentrated, so copy-number changes remain blocked.
- The next identifiable question is temporal mediation: input flow, energy stock, demographic conversion, or survivor conditioning.

## Implemented

- read-only `Simulation.run(..., tick_observer=...)` observation hook;
- D2-F mediation plan generation from a confirmed D2-E assessment and source lineage-pair plan;
- preservation of all source checkpoint-lineage pairs for selected modules;
- multi-offset branch trajectories with stable-ID birth/death accounting;
- target-lineage energy stock, quartiles, demography, reproduction and harvest/share flow measurements;
- routed-output, retained-cost and total-expression temporal decomposition;
- per-offset cross-seed/non-dominant-lineage assessment without treating time offsets as replicates;
- source-endpoint reproduction check at the final offset;
- explicit survivor-conditioned mean-energy, flow-to-energy, energy-demography tradeoff and demographic-conversion classifications;
- protocol audit v12;
- current-version-only versioned documentation packaging.

## Not implemented

- module duplication or deletion;
- arbitrary output routing or additional physical ports;
- diversity reward, protection or abundance reweighting inside the world;
- ecological role labels;
- any feedback from the temporal observer to the authoritative simulation.

## Validation

- `make test`: `208 passed, 1 skipped`;
- `CONDA_PREFIX=/opt/pyvenv make conda-check`: passed, including editable metadata, 87 importable modules, ten console entries and external-directory two-tick smoke;
- configuration validation: 75/75 JSON configurations passed;
- Python compilation: 132/132 source, script and test files passed;
- `make release-check`: passed, including isolated sdist → wheel → disposable-venv validation;
- installed D2-F CLI plan/execute/assess smoke: passed with zero decomposition residual;
- v0.43 disabled-feature compatibility: 8,340 authoritative state leaves and 347 common non-timing summary metrics matched exactly.

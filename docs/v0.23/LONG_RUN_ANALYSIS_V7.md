# Long-run analysis v7

`multi-seed-long-run-analysis-v7` retains every v6 statistic and adds environment-process provenance.

For each run it reports:

- resolved environment process schema;
- configuration origin (`core-disabled`, generic plugin config, or v0.22 adapter);
- mechanism class and interpretation label;
- process parameter names;
- legacy moving-hazard fields for compatibility auditing.

The analyzer reads `run_manifest.json` when available and falls back to `resolved_config.json`. It does not load or execute environment plugins during offline analysis.

This is an interpretation/provenance change, not a new causal statistic. Existing mortality trace, group refresh, local stress, local culture, transfer and danger-evidence analyses are unchanged.

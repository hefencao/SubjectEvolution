# v0.40 implementation report

## Scope

v0.40 does not expand the world-function vocabulary. It responds to the supplied
3000-tick D2-A result by adding measurement and paired causal attribution before
module duplication is considered.

Implemented:

- `functional-module-contribution-audit-v1` per-module diagnostics;
- all-module and four leave-one-module-out expression interventions;
- `se-d2-audit` plan/execute workflow;
- compact preregistered audit result summaries with full branch logs retained in
  branch output directories;
- long-run analysis v15;
- protocol audit v8;
- conda editable local workflow and exact-checkout verification;
- offline/restricted-environment editable install with `--no-build-isolation`.

Not implemented:

- module duplication/deletion;
- arbitrary input/output schema evolution;
- new physical ports or world actions;
- automatic complexity/diversity protection;
- active social-control changes.

## Scientific decision

The supplied runs show wide module expression but small final residuals and
strong lineage/strategy collapse. Structural presence is not sufficient evidence
of function. D2-B therefore measures isolated contribution, cancellation,
dominance and local causal leave-one-out effects while preserving the existing
D2-A authoritative calculation.

## Authoritative compatibility

With no module-ablation intervention, v0.39 and v0.40 produce:

- 2408 common non-timing metrics cells with zero differences;
- 11 selected knowledge/environment/subject files byte-identically;
- 38/38 common checkpoint arrays exactly equal at ticks 30 and 60.

The only ordinary-run changes are new observation fields.

## D2-B smoke

One seed was run to tick 180. Peak/trough phase labels were selected with the
explicit incomplete-cycle smoke allowance, and six branches were executed from
each checkpoint for 30 ticks.

The smoke verifies:

- shared checkpoint execution;
- genotype preservation;
- all/partial expression masks;
- cost removal/refund semantics;
- individual effects and non-additivity;
- compact result generation.

No survival difference occurred over the short horizon. The smoke is not used as
adaptive evidence.

## Engineering workflow

The normal local workflow is now:

```bash
conda activate <env>
make conda-sync
make test
```

Before long runs:

```bash
make conda-check
```

The execution container did not provide a real `conda` executable, so actual
`CONDA_PREFIX` ownership must be verified on the user's machine. The same
editable-install verifier passed in the available isolated Python environment,
including exact checkout, `direct_url.json`, 82 module imports, five entry points
and a source-tree-external smoke.

## Validation

- full tests: 190 passed, 1 skipped;
- skipped: real CUDA/CuPy device test;
- configs: 75/75 valid;
- protocol audit CLI: passed after fixing a stale Markdown field name found by
  direct command execution;
- editable workflow verifier: passed;
- long-run analysis v15 smoke: passed;
- v0.39/v0.40 compatibility: passed.

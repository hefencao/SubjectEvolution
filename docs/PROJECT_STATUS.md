# SE project status

Version: **0.38.0**

## Current focus

```text
orthogonal external environment
→ phenotype-routed resource requests
→ inherited capacity differentiation
→ paired expression interventions
→ ecological niches and interactions
→ social organization
→ higher-level candidate subjects
```

## D1-B three-seed evidence

The supplied v0.37 analysis contains three 1500-tick runs. Final population is
462, 458 and 418. Global resource effective dimensions remain 1.737–2.004,
above the old D1 uniform-demand endpoint of roughly 1.27. Capacity effective
dimensions remain 3.456–3.761.

Working memory is almost fully used, knowledge utilization is 0.929–0.938 and
relation utilization is 0.724–0.786. D1 capacities therefore have non-trivial
range and are connected to active mechanisms.

The old demand panel used realized channel volume. Its near-one temporal
dimension is dominated by population and HARVEST action-count scale, so it
cannot determine whether requested channel composition differentiated.

## v0.38 D1-C

The authoritative runtime now records per-window requested resource amounts
before environment allocation, separately from realized extraction after field
availability and conflict resolution.

Long-run schema `multi-seed-long-run-analysis-v13` reports:

- raw requested and realized channel volumes;
- per-window channel shares with common scale removed;
- explicit/inferred/unavailable request observation provenance;
- extraction efficiency;
- refusal to reconstruct old selective requests from realized-only records.

The new `se-d1-factorial` command executes four branches from a shared trusted
checkpoint:

- baseline;
- affinity-neutral;
- capacity-neutral;
- combined-neutral.

It publishes affinity-expression, capacity-expression and interaction contrasts
for each selected phase and fixed horizon. These are local paired effects, not
universal subject or fitness claims.

## Release reliability

`make release-check` now combines the source test suite with disposable-venv
distribution validation. The candidate wheel is built from an sdist, installed
after an older wheel with `--force-reinstall`, and executed outside the source
tree with `PYTHONPATH` and user site disabled.

## Gate for D2

D2 remains blocked until a v0.38 rerun and paired branches show all of:

1. explicit requested-channel composition has non-trivial temporal variation in
   at least two seeds;
2. capacity use remains non-trivial;
3. affinity and/or capacity expression changes downstream outcomes in matched
   checkpoint branches;
4. observed effects are not only population-scale or extraction-efficiency
   artifacts.

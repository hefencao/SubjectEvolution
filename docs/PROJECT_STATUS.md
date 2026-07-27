# SE project status

Version: **0.40.0**

## Current causal chain

```text
orthogonal external environment
→ inherited affinity-routed requests
→ inherited elastic capacities
→ bounded contextual harvest modules
→ measured module contribution and paired ablation
→ ecological niches and interactions
→ social organization
→ higher-level candidate subjects
```

## D2-A 3000-tick evidence

Three v0.39 runs completed 3000 ticks. Resource fields remain approximately
`1.85–2.12` dimensional and elastic capacities `2.76–2.99` dimensional.
Modules are structurally expressed (`2.56–2.76` of four slots on average) and
change final preference for `92.6–99.8%` of entities.

However:

- mean absolute residual is only `0.000136–0.000485`;
- residual magnitude declines in two seeds;
- functional preference dimensions decline in all three;
- effective lineages fall to `1.72–3.48`;
- the largest lineage occupies `49.6–74.6%` of survivors;
- final strategy dimensions fall to `1.91–4.02`.

Structural expression therefore does not yet justify duplication or a new organ
claim.

## D2-B

Schema: `functional-module-contribution-audit-v1`.

Ordinary progress now separates each fixed module's gate, activation, isolated
residual, non-zero fraction, silent-expression fraction and contribution share.
It also reports effective contributor count, contribution dominance and
cancellation between isolated outputs and the authoritative summed residual.

New paired interventions neutralize one module slot at a time while preserving
genotype. `se-d2-audit` runs baseline, all-neutral and four leave-one-out branches
from identical checkpoints and reports individual expression effects plus
non-additivity.

The 30-tick integration smoke validates branching and attribution. It does not
show a survival effect and is not scientific evidence of module utility.

## Engineering workflow

The preferred local runtime is a conda environment with an editable install:

```bash
make conda-sync
make test
make conda-check
```

Source edits become visible immediately. Reinstall is required only after
metadata, entry-point, dependency, version, package-layout or checkout-path
changes. `conda-sync` uses `--no-build-isolation` so an offline conda environment
uses its installed build tools instead of trying to download a temporary build
environment.

Artifact wheel/sdist validation remains optional for release transfer and is no
longer the local execution model.

## Next gate

Execute D2-B for three seeds × peak/trough checkpoints at 120 ticks, then repeat
non-zero effects at 300 ticks. Module duplication remains blocked unless at
least two seeds show repeatable, context-dependent downstream effects that are
not explained only by expression-cost refunds or lineage fixation.

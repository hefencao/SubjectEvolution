# SE project status

Version: **0.39.0**

## Current causal chain

```text
orthogonal external environment
→ inherited affinity-routed requests
→ inherited elastic capacities
→ bounded contextual harvest modules
→ ecological niches and interactions
→ social organization
→ higher-level candidate subjects
```

## D1 paired evidence

The supplied six shared-checkpoint factorial comparisons cover three seeds and
peak/trough phases. Affinity expression has the same direction in all six:

- final alive: `+57, +59, +143, +146, +58, +80`;
- mean energy: positive in all six;
- resource-environment effective dimensions: positive in all six;
- effective transferred roots: positive in all six;
- immediate extraction efficiency: negative in all six.

The affinity effect therefore cannot be reduced to a free increase in immediate
harvest efficiency. Capacity expression remains path-dependent: alive effects
are mixed, energy is mostly lower, resource dimensions are lower in five of six
comparisons, and transferred-root effects differ by seed.

These are local 120-tick expression contrasts selected from observed population
phases. They support a bounded D2 test, not universal adaptive necessity.

## D2-A

Schema: `expression-gated-contextual-harvest-v1`.

Four inherited modules read a fixed ten-value input vocabulary: bias, five
internal deficits, and four normalized local resource values. They publish only
a zero-sum residual over the existing four harvest-channel request weights.
Static resource affinity still controls assimilation and gradient utility.
Modules do not choose HARVEST, do not create a new resource/action, and do not
read lineage, group label, rarity, or analysis output.

The 300-tick shared-initial-state smoke shows that module neutralization exactly
recovers the D1-B endpoint. Expressed modules change request weights for 82.7%
of final entities. Relative to the neutralized branch, expression changes alive
`115→127`, resource dimensions `1.825→1.713`, extraction efficiency
`0.871→0.816`, and effective transferred roots `17.0→20.17`. The trade-off is
real but not yet interpretable as adaptation.

## Engineering workflow

- `se --seed` overrides a config seed without editing JSON.
- `se` and `se-multi` accept comma-separated `--checkpoint-ticks`.
- restored runs can also schedule future exact checkpoints.
- `se-d1-factorial --plan` reuses an existing signed/inspected plan without
  rerunning phase detection.
- `make release-check` is disposable and does not modify the caller's shell.
- `make release-env` creates `.release-env/venv`, performs the same isolated
  validation, and leaves all console scripts available.
- short multi-seed smoke runs no longer fail solely because the first
  evolution-progress window has not yet been emitted.

## Next gate

Run D2-A for three seeds × 3000 ticks, then pair baseline with
`neutralize-functional-modules` at at least peak and trough checkpoints. Do not
enter module duplication or arbitrary output routing unless at least two seeds
show persistent non-zero residual topology and repeatable downstream effects.

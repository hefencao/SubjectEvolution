# D3-R functional-regulatory oxygen-uptake candidate

Candidate: `functional-regulatory-oxygen-uptake-acute-effect-v1`

## Hypothesis

Neutralizing functional-module regulatory physiology output changes cumulative realized oxygen uptake over a fixed 120-tick response window.

## Matched design

Each independent seed contributes one fixed-checkpoint pair:

```text
same tick-480 full checkpoint
├── baseline
└── neutralize-functional-module-physiology-output
```

The intervention preserves harvest output, coupling output, genotype coordinates, inheritance and physiology-router structural cost. It removes only the module-derived regulatory physiology output.

## Primary estimand

```text
(intervention cumulative oxygen uptake after checkpoint)
-
(baseline cumulative oxygen uptake after checkpoint)
```

The seed is the independent unit. The screen requires at least eight eligible seeds, at least 75% direction consistency and an equal-seed median absolute relative effect of at least 2%.

## Manipulation contract

A panel is eligible only when all checks pass:

- baseline ablation flag is zero;
- intervention ablation flag is one;
- baseline regulatory-output changed-entity fraction is positive;
- intervention changed-entity fraction is zero;
- baseline regulatory-output effective dimensions exceed 0.25;
- intervention effective dimensions are zero within numerical tolerance.

The changed-entity fraction and effective-dimension diagnostics are reported as fixed summary fields so the result bundle is self-contained.

## Interpretation boundary

A passing result would establish only a bounded acute causal path from functional-module regulatory output to realized oxygen uptake. It would not establish long-horizon selection, named organ identity, ecological specialization, stable coexistence or the value of individual module slots.

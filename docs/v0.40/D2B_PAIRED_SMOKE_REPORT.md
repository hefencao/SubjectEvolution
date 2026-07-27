# D2-B paired leave-one-module-out smoke

Source: one seed, 180-tick D2-A smoke trajectory; two observationally selected phases; 30-tick branch horizon.

| Effect | Alive | Mean energy | Env dims | Preference dims | Residual | Contributing modules | Cancellation |
|---|---:|---:|---:|---:|---:|---:|---:|
| all_module_expression_effect | +0.000000 | -0.001063 | -0.000762 | +0.000056 | +0.000350 | +3.820564 | +0.179329 |
| module_0_expression_effect | +0.000000 | -0.000358 | +0.000000 | +0.000299 | +0.000061 | +0.984142 | +0.061497 |
| module_1_expression_effect | +0.000000 | -0.000299 | +0.000000 | -0.000338 | +0.000104 | +0.938537 | +0.006554 |
| module_2_expression_effect | +0.000000 | -0.000180 | -0.000762 | +0.000059 | +0.000047 | +0.861340 | +0.049244 |
| module_3_expression_effect | +0.000000 | -0.000274 | +0.000000 | -0.000015 | +0.000079 | +0.995979 | +0.056925 |
| module_nonadditivity | +0.000000 | +0.000049 | +0.000000 | +0.000051 | +0.000059 | +0.040566 | +0.005107 |

## Result

- All six branches executed from each shared checkpoint and preserved genotype.
- All-module neutralization removes the contribution diagnostics as expected.
- Individual module effects are distinguishable and their sum is not exactly equal to the all-module effect, so cancellation/non-additivity is measurable.
- No alive difference appeared over 30 ticks; mean-energy effects are approximately the explicit expression maintenance cost.
- The audit summary stores only preregistered outcomes; complete branch run directories retain full logs.
- This is an integration smoke only. Formal interpretation requires three seeds, peak/trough checkpoints and at least 120 ticks.

Full machine-readable output is retained in `D2B_SMOKE_FULL_RESULTS.json`.

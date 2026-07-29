# D3-J 1200-tick demographic pilot interpretation

Source schema: `multi-seed-long-run-analysis-v15`

| Run | Trough | Final alive | Rebound | Effective lineages | Largest lineage | Backend |
|---|---:|---:|---:|---:|---:|---|
| seed_67001 | 873 @ 800 | 1014 | 0.1615 | 261.8940 | 0.0168 | gpu-hybrid-accelerated |
| seed_67002 | 929 @ 800 | 1117 | 0.2024 | 188.3873 | 0.0340 | gpu-hybrid-accelerated |
| seed_67003 | 912 @ 800 | 1085 | 0.1897 | 248.9374 | 0.0313 | gpu-hybrid-accelerated |

## Interpretation

The three runs share an early population contraction, a trough at tick 800, and a modest rebound by tick 1200. Final effective-lineage counts remain broad and no lineage approaches monopoly. The supplied archive contains aggregate v15 analysis rather than raw evolution_progress streams, so generation replacement, descendant fraction, death causes, and independent successful-parent breadth cannot be reconstructed from this archive alone.

Classification: `demographic-rebound-observed-selection-validity-unresolved`

## Next step

Re-analyze the retained raw seed directories with v0.68, or run the preregistered D3-K 3000-tick panel. Do not treat the current rebound as effective selection until source-readiness criteria pass on independent seeds.

# Demographic selection validity audit

Schema: `demographic-selection-validity-audit-v2`

| Run | Initial | Min alive fraction | Trough tick | Final alive | Mean gen | Descendant fraction | Effective parents | Source ready | Classification |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| seed_68001 | 16 | 1.000000 | 1 | 16 | 0.000000 | 0.0 | 0.0 | False | selection-source-insufficient-observation |
| seed_68002 | 16 | 1.000000 | 1 | 16 | 0.000000 | 0.0 | 0.0 | False | selection-source-insufficient-observation |

Future fixed burn-in supported: `False`
Future fixed burn-in tick: `None`
Recommendation: `retain-runs-and-redesign-source-before-selection-claims`

No cross-seed selection effect is estimated here. The audit separates population support, descendant turnover, and reproductive-contributor breadth from mere tick duration. Any burn-in rule derived from these pilots must be tested on new independent seeds.

A rapid initial collapse is not automatically equivalent to effective selection. A later rebound can only become a candidate source regime after population stability, descendant replacement, lineage breadth, and independent reproductive contributor breadth are all observed.

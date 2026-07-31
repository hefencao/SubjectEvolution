# Source health gate

- ready: **False**
- ready seeds: 2 / 3
- paired plan authorized: **False**
- interpretation: `source-collapse-or-insufficient-generational-turnover`

| seed | tick | alive | births/initial | living descendants/initial | mean generation | founder fraction | ready | failed |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 92101 | 240 | 128 | 0.7656 | 0.4375 | 0.4375 | 0.5625 | False | checkpoint_decline_met |
| 92102 | 360 | 127 | 0.9141 | 0.5391 | 0.6299 | 0.4567 | True | - |
| 92103 | 360 | 122 | 0.9844 | 0.5312 | 0.7377 | 0.4426 | True | - |

> A failed gate terminates the execution chain. It does not authorize gene-effect, selection, adaptation, or niche interpretation.

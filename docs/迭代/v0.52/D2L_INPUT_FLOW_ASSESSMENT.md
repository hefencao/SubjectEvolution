# D2-L regulatory physiology flow assessment

Schema: `d2-regulatory-physiology-flow-assessment-v1`
Source physiology schema: `transport-metabolism-messenger-tissue-v2`
Passed conservative ledger: `False`

| Seed | Synthesis | Decay | Precursor used | Precursor recovered | Messenger energy | Ledger valid |
|---:|---:|---:|---:|---:|---:|---:|
| 51001 | -409.08105132807646 | 358.42008067157735 | -204.54052566403823 | 169.781635637241 | -8.181621026561535 | False |
| 51002 | -412.1768469923981 | 385.84201845497086 | -206.08842349619906 | 186.99597654438546 | -8.243536939847939 | False |
| 51003 | -335.3754218936932 | 391.4618749580975 | -167.6877109468466 | 185.70894207305216 | -6.707508437873864 | False |

## Decision

`rerun-conservative-v3-same-seeds`

Invalid flow entries: `9`

This assessment verifies cumulative flow-sign and finite-value invariants for the regulatory physiology substrate. It does not measure module maturity, ecological differentiation, or a named organ.

# D3-D 300-tick validation

- seed: `56001`
- horizon: `300`
- result schema: `d3-persistent-resource-renewal-results-v2`
- final alive: `123`
- final resource effective dimensions: `3.21838538846`
- final mean absolute channel correlation: `0.146276916497`

## Ledger

- maximum unadjusted relative residual: `7.48176344211e-06`
- maximum corrected relative residual: `2.63899221384e-16`
- maximum numerical-adjustment fraction: `7.48176344185e-06`
- corrected ledger valid: `True`

The corrected residual is near binary64 machine precision. The run changes only reporting and accounting provenance; the physical flux totals and simulated trajectory are not post-corrected.

This single-seed 300-tick run is a regression and mechanism validation, not the required replacement for the supplied three-seed 1500-tick panel.

# v0.43 → v0.44 authoritative compatibility report

- ticks: `20`
- backend: `cpu`
- D2-F observer: disabled
- v0.43 authoritative leaves: `8340`
- v0.44 authoritative leaves: `8340`
- authoritative differences: `0`
- common non-timing summary metrics: `347`
- non-timing summary differences: `0`
- passed: `true`

The temporal observer is not installed unless explicitly supplied to `Simulation.run`; the disabled path therefore preserves the v0.43 authoritative trajectory.

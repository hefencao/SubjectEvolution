# v0.44 → v0.45 authoritative compatibility report

- ticks: `20`
- backend: `cpu`
- D2-G source-population runner: disabled
- checkpoint state SHA-256 identical: `true`
- v0.44 authoritative state leaves: `73756`
- v0.45 authoritative state leaves: `73756`
- authoritative differences: `0`
- common non-timing JSON summary metrics: `609`
- non-timing JSON summary differences: `0`
- metrics rows / non-timing columns: `3` / `347`
- metrics differences: `0`
- passed: `true`

D2-G is implemented as an explicit experiment runner. Ordinary simulation initialization and world logic do not install founder reconstitution, so the disabled path preserves the v0.44 authoritative trajectory.

# Supplied scale4 summary consistency audit

Schema: `scale4-summary-stale-mirror-audit-v1`

Both supplied summaries report tick `3000` and alive `7506`.

| Checkpoint period | User-reported last host mirror tick | Residue total |
|---:|---:|---|
| 1000 | 2000 | `[1274.0912387243006, 1258.2481839046814, 1300.2060227338225, 1316.5786032611504]` |
| 100 | 2900 | `[3280.3765747209545, 2985.078865673393, 3326.107370005222, 3247.1724624461494]` |

The differing non-timing/non-GPU fields are confined to residue inventory and its float32 settlement diagnostics. The old report path therefore mixed current entity/tick values with the last host-materialized residue field.

v0.66 makes reporting an independent authoritative boundary: every report materializes current device state first and records `reporting_state_tick`; checkpoint cadence no longer controls summary freshness.

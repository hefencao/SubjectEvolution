# GPU execution provenance audit

Schema: `gpu-execution-audit-v1`

| Result | Runs | Accelerated | Fallback | Strict reference | Median seconds/tick | Median H2D bytes | Median D2H bytes | Real GPU only |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| strict-reference | 128 | 0 | 0 | 128 | 0.028173661200981498 | 0.0 | 0.0 | False |
| fixed-hybrid-gpu | 128 | 128 | 0 | 0 | 0.09061893285000527 | 58174.0 | 55551.0 | True |

Recommendation: `inspect-backend-provenance-before-gpu-claim`

This audit verifies recorded execution provenance and summarizes timing/transfer diagnostics. It does not prove CPU/GPU semantic parity, a performance speedup, or any scientific effect. Parity requires the target-device test_parity suite and a speedup claim requires a paired benchmark on the same checkpoint and hardware.

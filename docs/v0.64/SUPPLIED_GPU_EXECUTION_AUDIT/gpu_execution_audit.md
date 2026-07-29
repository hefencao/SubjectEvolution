# GPU execution provenance audit

Schema: `gpu-execution-audit-v1`

| Result | Runs | Accelerated | Fallback | Strict reference | Median seconds/tick | Median H2D bytes | Median D2H bytes | Real GPU only |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed-hybrid-gpu | 128 | 128 | 0 | 0 | 0.09061893285000527 | 58174.0 | 55551.0 | True |

Recommendation: `gpu-execution-confirmed-scientific-and-speedup-claims-separate`

This audit verifies recorded execution provenance and summarizes timing/transfer diagnostics. It does not prove CPU/GPU semantic parity, a performance speedup, or any scientific effect. Parity requires the target-device test_parity suite and a speedup claim requires a paired benchmark on the same checkpoint and hardware.

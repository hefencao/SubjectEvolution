# GPU memory stability audit

Schema: `gpu-memory-stability-audit-v1`

| Run | Last tick | Max alive | Telemetry | Peak live bytes | Peak pool bytes | Max cached end-step | Max cached after trim | Trims | Bounded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 69001 | 200 | 8000 | False | None | None | None | None | None | None |
| 69002 | 4500 | 22369 | False | None | None | None | None | None | None |
| 69003 | 4500 | 26596 | False | None | None | None | None | None | None |

Allocator telemetry distinguishes live device state from unused CuPy cache. It does not establish scientific validity or CPU/GPU parity.

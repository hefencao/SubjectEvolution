# v0.63 implementation report

## Scope

v0.63 changes execution policy and validation boundaries only. It adds no world mechanism, sensor, reward, controller, population rescue, diversity protection or ecological role.

## Supplied-run diagnosis

The supplied D3-I artifacts contain 256 branch executions across 1.5× and 2× panels. Every branch requested `gpu`, but every manifest reports `gpu-strict-reference`, `strict-reference`, and `gpu_acceleration_enabled=false`. Those runs are CPU-authoritative and cannot be counted as accelerated GPU long-run evidence.

## Runtime policy

High-level simulation and experiment entry points now default to `auto`:

1. when CUDA/CuPy is available and the configuration uses the default `hybrid-accelerated` semantics, instantiate `HybridGpuRuntime` and report `gpu-hybrid-accelerated`;
2. when no usable GPU exists, continue on CPU and report `cpu-fallback-no-gpu` plus a concrete fallback reason;
3. keep `strict-reference` available only when explicitly selected for historical diagnostics;
4. keep the low-level `resolve_backend("gpu")` contract strict so device-only tests cannot silently become CPU tests.

No runtime result is declared scientifically valid merely because a GPU was found. The authoritative cross-backend validation boundary is the parity test suite.

## Parity v2

`cpu-gpu-parity-v2` adds:

- recursive comparison of all checkpoint-authoritative leaves;
- exact comparison of discrete state and tolerance-bounded comparison of floating state;
- device mirror checks for persistent entity, social, environment and information arrays;
- representative real-GPU tests spanning baseline, knowledge/culture, mortality/adaptive groups, D3 spatial processing, subject/multi-environment and plugin semantics;
- first-divergence reporting at the semantic leaf and simulation stage.

New checkpoint-authoritative semantics enter parity automatically unless explicitly classified as non-authoritative backend cache state.

## No-GPU smoke

The v0.63 smoke run requested `auto` on a host without CuPy. It completed with `execution_backend=cpu-fallback-no-gpu`, `gpu_acceleration_enabled=false`, and a recorded fallback reason. This verifies graceful fallback without misreporting CPU execution as GPU execution.

## Scientific boundary

The supplied eight-seed scale audit still fails directional replication at both scales. v0.63 does not alter that conclusion and does not unlock a response mechanism. Backend acceleration and ecological inference remain separate questions.

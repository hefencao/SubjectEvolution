# SE v0.70

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains role-free four-channel resources, conservative storage and recycling, persistent abiotic renewal, costed spatial processing, matched controls, GPU-first execution, and explicit scientific-validity gates.

## Why v0.70

The supplied D3-L scale-4 runs exposed an execution-lifetime failure rather than a biological state-size limit. One run grew from 14,342 living entities at tick 3700 to 22,369 at tick 4500 while active encoded knowledge grew by less than 2 MiB, yet reported device residency rose from about 2 GiB to about 32 GiB and the fixed horizon could not finish.

The hybrid path creates temporary arrays whose sizes follow the active population and selected latent-copy count. CuPy's default allocator caches freed blocks. During a long monotonic rebound, progressively larger shapes can leave many obsolete smaller blocks resident even though they are no longer live simulation state.

v0.70 bounds only that unused allocator cache. It does not cap live arrays, reduce the population, alter knowledge, change selection pressure, or silently switch to CPU.

## Bounded GPU allocator cache

Normal GPU runs use:

```text
gpu_memory_pool_policy = bounded-cache-v1
gpu_memory_pool_cache_limit_bytes = 536870912
gpu_memory_pool_trim_period = 1
```

At the start of the next step, after the preceding `step()` frame has exited, the runtime releases stale unused blocks; the completed step then reports:

- live device bytes;
- total allocator-pool bytes;
- unused cached bytes;
- peak live and peak pool bytes;
- trim count and bytes released;
- pinned-pool free blocks.

Only unused blocks above the configured cache limit are released at this safe inter-step boundary. End-of-step cache and post-trim cache are reported separately. Persistent entity, field, spatial and policy state remains live.

## D3-M memory-stability run

```bash
se-multi \
  --config configs/mvp_d3m_gpu_scale4_memory_stability.json \
  --seeds 70001,70002,70003 \
  --output analyses/d3m_scale4_memory_stability \
  --backend auto \
  --until-tick 5000
```

Audit allocator stability:

```bash
se-gpu-memory-audit \
  --run 70001=analyses/d3m_scale4_memory_stability/seed_70001 \
  --run 70002=analyses/d3m_scale4_memory_stability/seed_70002 \
  --run 70003=analyses/d3m_scale4_memory_stability/seed_70003 \
  --output analyses/d3m_scale4_memory_stability/gpu_memory_audit
```

Memory stability, execution provenance, CPU/GPU parity and scientific validity remain separate claims.

## GPU parity

```bash
make parity-gpu
```

The allocator-cache policy is outside world semantics, while all checkpoint-authoritative world state remains covered by parity.

## Workflow

```bash
make conda-sync
make test
make conda-check
make release-check
```

## Current version documents

- [Implementation report](docs/v0.70/IMPLEMENTATION_REPORT.md)
- [D3-L GPU memory failure analysis](docs/v0.70/D3L_GPU_MEMORY_FAILURE_ANALYSIS.md)
- [D3-M memory-stability plan](docs/v0.70/D3M_GPU_MEMORY_STABILITY_PLAN.md)
- [Protocol audit](docs/v0.70/protocol_audit.md)

# D3-M GPU memory stability plan

D3-M repeats the D3-L scale-4 world and fixed 5,000-tick horizon without changing resources, costs, inheritance, reproduction, mortality, population limits or diagnostics.

The execution-only intervention is `bounded-cache-v1`:

- live device allocations remain untouched;
- stale unused CuPy blocks are inspected at the next-step start, after the preceding step frame has exited;
- cached bytes above 512 MiB are released;
- no memory-pressure CPU fallback is allowed;
- end-of-step and post-trim allocator telemetry are written separately into normal metrics and summaries.

Run:

```bash
se-multi \
  --config configs/mvp_d3m_gpu_scale4_memory_stability.json \
  --seeds 70001,70002,70003 \
  --output analyses/d3m_scale4_memory_stability \
  --backend auto \
  --until-tick 5000
```

Then audit each seed directory:

```bash
se-gpu-memory-audit \
  --run 70001=analyses/d3m_scale4_memory_stability/seed_70001 \
  --run 70002=analyses/d3m_scale4_memory_stability/seed_70002 \
  --run 70003=analyses/d3m_scale4_memory_stability/seed_70003 \
  --output analyses/d3m_scale4_memory_stability/gpu_memory_audit
```

The memory audit is operational. It does not replace CPU/GPU parity or demographic selection-validity analysis.

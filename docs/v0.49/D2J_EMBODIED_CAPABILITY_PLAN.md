# D2-J embodied capability run

```bash
se-d2-embody \
  --config configs/mvp_short_d2j_embodied_modules_longrun.json \
  --seeds 49001,49002,49003 \
  --output analyses/d2j_embodied_capability_1500 \
  --backend gpu \
  --until-tick 1500
```

The paired branches share the v3 initial genome distribution, world seed, mutation process, harvest output, compositional coupling, and all structural costs. Only locomotion, field-signal, and repair publication is neutralized.

Interpret the result in this order:

1. **Embodied output remains unused.** Inspect router initialization, expression, use cost, and availability of the existing actions/resources required by each primitive.
2. **Ports are used but the combined output basis remains harvest-dominated.** The next limit is likely sensor/state access or the fixed four-slot graph, not another endpoint audit.
3. **Several physical ports and combined dimensions persist across seeds.** Preserve the evolved populations and test environment association and coexistence without changing module count.
4. **Only alive/energy endpoints diverge.** Treat this as trajectory amplification unless the functional basis and physical-use counters also differ.

This run is descriptive generative-capability evidence, not a pass/fail copy-number gate.

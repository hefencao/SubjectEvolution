# SE project status

Version: **0.70.0**


## Current GPU memory boundary

D3-L scale-4 runs reached 22,369–26,596 living entities before the fixed horizon stopped. Persistent knowledge state remained measured in megabytes, while device residency grew to the device limit. The current diagnosis is allocator-cache retention from monotonically changing transient batch shapes, not a tens-of-gigabytes biological state.

v0.70 uses a bounded unused-cache policy and records live, total, cached, peak, trim and released-byte telemetry. The policy cannot evict live arrays, alter world state, lower the population or trigger a CPU fallback.

The next operational gate is completion of the fixed D3-M horizon with post-trim cached bytes within the configured bound. Demographic regime and selection-validity gates remain unchanged.

## Current demographic interpretation

The D3-K three-seed aggregate does not show a settled post-bottleneck source at tick 3000. All runs rebound strongly after their troughs, but their last three 100-tick observations still have normalized positive slopes of about 0.105–0.126 per window and span changes of about 0.210–0.253.

The runs nevertheless show substantial turnover and broad recent reproduction:

- final alive: 6,056–7,339;
- living descendants: 92.4%–93.6%;
- mean generation: 2.63–2.98;
- effective successful parents in the final window: about 897–1,090;
- largest parent contribution: below 0.3%.

Founder-lineage inverse-Simpson counts are only about 23–47, while final strategy effective dimensions are about 20–33. These are different measurements and are no longer collapsed into a single diversity claim.

## Current execution and scientific chain

```text
role-free four-channel resources
→ conservative storage/recycling/renewal
→ costed spatial processing and matched controls
→ GPU-first large-population execution with target-device parity
→ bottleneck and death-cause audit
→ active rebound versus settled-platform classification
→ founder-lineage and current heritable-variation audit
→ fixed burn-in rule tested on new independent seeds
→ only then replicated evolutionary-selection inference
```

## Current gates

1. Do not treat the D3-K tick-3000 endpoint as settled.
2. Run the fixed D3-L horizon without outcome-conditioned stopping or seed replacement.
3. Require low recent slope and low cross-window population change before proposing a burn-in.
4. Keep founder-lineage concentration separate from current genotype/policy variation.
5. Preserve every insufficient run and window.
6. Keep migration, specialization, coexistence and ecotype gates closed.

## Still incomplete

- a replicated settled post-bottleneck regime;
- a preregistered burn-in validated on new independent seeds;
- causal decomposition of founder-lineage contraction;
- replicated selection effects after demographic stabilization;
- device-resident action settlement, lifecycle and graph updates;
- positive replicated processing-response evidence.

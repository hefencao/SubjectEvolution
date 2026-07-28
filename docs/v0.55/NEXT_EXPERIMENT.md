# Next experiment: D3-C

Run the external recycling substrate with three independent seeds:

```bash
se-d3-external-recycling \
  --config configs/mvp_short_d3c_external_recycling_longrun.json \
  --seeds 55001,55002,55003 \
  --output analyses/d3c_external_recycling_1500 \
  --backend gpu \
  --until-tick 1500
```

Interpretation order:

1. both source and external residue ledgers must remain closed;
2. store-decay deposits and residue release should occur in every seed;
3. death-carried raw-store deposition is interpreted only in seeds where such death loss occurs;
4. residual material should remain finite and spatially non-trivial rather than being instantly released;
5. population and external-resource endpoints remain descriptive because D3-B and D3-C use different independent seeds;
6. if the substrate remains closed, the next stage should create spatially distinct collection and processing opportunities before entity consumption or named trophic roles.

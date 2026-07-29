# SE v0.62

SE is a deterministic artificial-life and subject-structure research platform. The current main line retains four role-free resource channels, conservative delayed storage and processing, identity-preserving external recycling, persistent abiotic renewal, costed spatial processing support, matched support neutralization, and shared-checkpoint acute-response measurement.

## Why v0.62

The supplied v0.61 D3-H 1.5× run completed all 12 preregistered seed/checkpoint quartets. Every quartet met the acute sample-support gate, every interval resource and recycling ledger closed, and no checkpoint met the evolutionary-turnover gate.

The four-arm design now identifies original and reversed active-minus-neutral effects under matched observation orientations. The remaining problem is statistical interpretation: four checkpoints inside one seed are repeated panels, not four independent experiments, and tens of thousands of movement events do not increase the independent seed count.

v0.62 adds D3-I nested matched-effect inference. It changes no world mechanism, sensor, reward, controller, reproduction rule, population support, diversity rule, or ecological label.

## D3-I nested effect audit

`se-d3-response-scale-audit` now performs three levels of accounting:

```text
movement events and 30-tick windows
        ↓ repeated measurements only
checkpoint matched active-neutral effect
        ↓ equal checkpoint weight
seed-level effect
        ↓ equal seed weight
scale-level effect and replication gate
```

For every metric and support orientation it reports:

- matched panel effects;
- fixed-window matched effects;
- equal-checkpoint seed means;
- checkpoint and window sign fractions;
- leave-one-checkpoint-out sensitivity;
- equal-seed scale means;
- leave-one-seed-out sensitivity;
- an exact seed-level sign-flip diagnostic;
- a directional replication gate that never feeds back into the world.

Default interpretation requirements are eight independent seeds per scale, at least 75% positive seed means in each orientation, and at least 75% of seeds positive under both orientations. These are analysis gates only. They do not rescue populations, retry runs, select checkpoints, or alter behavior.

## Supplied 1.5× result

Equal-weight seed aggregation gives:

```text
original active-neutral mean support gain:  6.47752786474193e-08
reversed active-neutral mean support gain: -7.434496869115597e-06
independent seeds: 3
seeds positive in both orientations: 0
```

The original effect changes sign under leave-one-seed-out analysis. All three reversed seed means are negative, but three seeds are still insufficient for the preregistered replication gate. The supplied result therefore remains valid acute causal measurement but does not justify a processing-support sensor, movement reward, migration controller, or ecological interpretation.

## Run the fixed v2 panel

The next scientific run should preserve the same four-arm protocol and checkpoint list while adding independent seeds at both 1.5× and 2× scales.

```bash
se-d3-processing-response-panel \
  --config configs/mvp_short_d3g_spatial_processing_scale1p5_longrun.json \
  --seeds 62001,62002,62003,62004,62005,62006,62007,62008 \
  --output analyses/d3i_response_panel_1p5_replication \
  --checkpoint-ticks 300,600,900,1200 \
  --response-window 120 \
  --observation-period 30 \
  --backend gpu
```

Analyze without treating checkpoints as independent seeds:

```bash
se-d3-response-scale-audit \
  --result scale1p5=analyses/d3i_response_panel_1p5_replication/d3_processing_response_panel_results.json \
  --result scale2=analyses/d3i_response_panel_2_replication/d3_processing_response_panel_results.json \
  --output analyses/d3i_response_effect_audit
```

## Workflow

After metadata, entry-point, dependency, or package-layout changes:

```bash
make conda-sync
```

Daily validation:

```bash
make test
make conda-check
```

Artifact audit:

```bash
make release-check
```

## Current version documents

- [Supplied 1.5× four-arm result](docs/v0.62/D3H_SUPPLIED_1P5_RESULTS.md)
- [Nested matched-effect audit](docs/v0.62/D3I_SUPPLIED_EFFECT_AUDIT.md)
- [Implementation report](docs/v0.62/IMPLEMENTATION_REPORT.md)

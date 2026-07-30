# D3-B conservative intake run plan

- Schema: `d3-conservative-intake-plan-v1`
- Seeds: `54001, 54002, 54003`
- Horizon: `1500` ticks
- Functional schema: `expression-gated-regulatory-resource-metabolism-v6`
- Physiology schema: `transport-metabolism-messenger-tissue-resource-v5`
- Intake contract: `storage-room-constrained-preharvest-v2`

## Fixed conditions

- One active population per seed.
- Raw requests are capped before environmental commit.
- Capacity-rejected resource remains external.
- Conversion is delayed by at least one tick.
- Store-room constraints are visible to functional operators.
- Resource-v4 replay is preserved.
- No named metabolism, role label, diversity protection or module-copy change.

## Interpretation

The run checks whether conservative capacity-aware intake remains active with delayed conversion. It is not a pass/fail test of ecological differentiation.

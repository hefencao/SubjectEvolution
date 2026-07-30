# v0.52 implementation report

## Implemented

- Added conservative physiology schema `transport-metabolism-messenger-tissue-v3`.
- Retained v2 unchanged for historical replay.
- Added non-negative proportional substrate limiting.
- Prevented negative energy from generating negative messenger synthesis or repair flows.
- Preserved computation-created energy debt until world starvation settlement.
- Added per-tick finite/non-negative physiology-flow ledger validation.
- Upgraded D2-L plan/result schemas to v2 and recorded conservation semantics.
- Added `se-d2-regulatory-physiology-assess` for cumulative flow-ledger assessment.
- Added legacy v2 replay configs and promoted canonical D2-L configs to v3.
- Upgraded protocol audit to v20.

## Scientific decision

The supplied v0.51 D2-L result is retained as evidence that regulatory outputs and genetic physiology were active, but its messenger and precursor totals are invalid because their signs violate the declared flow semantics. No additional biological mechanism is introduced in response. The exact same experiment should be rerun under v3.

## Compatibility boundary

- v1–v4 functional/physiology paths are unchanged.
- v5 with physiology v2 is unchanged and replayable.
- The correction is activated only by physiology v3.

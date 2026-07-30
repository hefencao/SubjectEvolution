# v0.75 implementation report

## Supplied result

D3-Q confirms disablement of the complete knowledge-policy residual in all eight eligible seeds. Seven seed effects reduce total harvest, but the equal-seed median reduction remains below the preregistered practical threshold. The candidate is terminal and does not enter replication.

## Candidate-family ledger

The candidate ledger is upgraded to `paired-exploration-candidate-ledger-v3`.

New non-feedback portfolio fields include:

- mechanism family;
- family revision;
- family role;
- whether a manipulation-confirmed terminal negative closes the family revision;
- explicit rationale for a higher family revision.

A closed family cannot be silently reopened by a child candidate. A higher revision without a rationale is rejected before plan generation.

## Self-contained regulatory-output manipulation checks

Periodic and final summaries now expose the most recent fixed-evaluation values for:

- `functional_physiology_output_changed_entity_fraction`;
- `functional_physiology_output_effective_dimensions`.

These are diagnostics only and do not feed back into world state. They allow fixed-checkpoint result bundles to prove that regulatory output was active in baseline and neutralized in the intervention branch.

## Next bounded experiment

D3-R uses the existing eight tick-480 checkpoints and a 120-tick paired response window. It does not rerun shared prehistory or authorize large long confirmation.

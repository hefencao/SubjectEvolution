# Lightweight project governance check

Run this check once per iteration before selecting the next experiment or implementation task.

## 1. Data versus expectation

Determine whether an unexpected result comes from invalid support, failed manipulation, stale reporting, numerical inconsistency, or a genuine small/negative effect. Adjust the current task only from the identified cause; do not compensate by lowering thresholds, replacing failed seeds, extending horizons post hoc, or adding a reward.

## 2. Long-term principles

Identify any new durable constraint or any change to an existing constraint. A durable principle must be written into a stable project document and, where mechanically enforceable, into validation code and tests.

## 3. Chat-only principles

Check whether any active project rule still exists only in conversation. Move it into the repository before relying on it in later iterations.

## 4. Candidate-portfolio boundary

A closed or exhausted candidate portfolio does not authorize automatic selection of the nearest available mechanism. Another paired experiment requires a preregistered candidate with a distinct scientific basis. Reopening a closed family requires a higher revision, an explicit rationale, and a named directly measurable interface.

## v0.77 check

- D3-S support and manipulation are valid; the practical effect is genuinely below threshold.
- The task is adjusted from another same-architecture component screen to scientific revision design.
- The previously documented “new directly measurable interface” requirement is now enforced by code and tests.
- The recurring governance check and the prohibition on automatic replacement-candidate selection are now repository principles rather than chat-only instructions.
## 5. Decision-history continuity

Terminal candidate and family decisions are release state, not disposable analysis output. Every clean package must carry an immutable decision baseline. Workspace ledgers are append-only overlays: they may add compatible later assessments but may not erase or override baseline history.

## 6. Iteration delivery

Run the required validation every iteration. When validation succeeds, the delivery response may omit a detailed validation report. Every iteration must still provide the recommended next commands.

## v0.78 check

- The supplied audit mismatch is traced to incomplete workspace history rather than new scientific evidence.
- D3-P and D3-Q remain terminal; the scientific task is not changed to rerun them.
- Immutable decision history, conflict rejection and explicit workspace hydration are enforced by code and tests.
- The new delivery rules about concise successful-validation reporting and suggested commands are now repository principles rather than chat-only instructions.


## 7. Exposure-qualified manipulation evidence

An intervention-state flag is not sufficient target engagement when the affected interface can receive zero or effectively neutral exposure. When a direct exposure-weighted measure is available, the candidate must preregister it and distinguish:

- the interface being enabled or disabled;
- material exposure to that interface;
- the downstream effect used for promotion.

Exposure diagnostics remain read-only and cannot substitute for the practical-effect gate.

## v0.79 check

- The supplied portfolio audit is valid and does not require another history repair.
- D3-T is a distinct conserved material-flow interface, not a child of the closed policy or functional-module families.
- The direct support-exposure metric is report-only and is required by candidate-spec validation for this intervention.
- No threshold, horizon, seed, source checkpoint, reward or world rule is changed.

## 8. Inferential replication protocol lock

A stage called replication must repeat the same inferential source protocol on a disjoint independent seed set. The protocol fingerprint excludes only `run.seed`; it includes world scale, population limits, horizon, cadence, environment, mechanisms and every other configuration field.

Changing scale, horizon, checkpoint cadence, source-population construction or mechanism settings is a robustness or confirmation question, not replication. Such a change requires its own preregistration and cannot inherit a screen promotion automatically.

## v0.80 check

- The supplied D3-T screen passes its preregistered manipulation, direction and practical-effect gates; the task advances to replication rather than another candidate search.
- The positive intervention effect is retained as evidence that active support is acutely suppressive on the screen estimand; no beneficial interpretation is imposed.
- The prior replication configuration mixed new seeds with a larger world, larger population and longer source run. This is corrected as a protocol-design issue, not as an empirical failure.
- Exact source-protocol locking and the distinction between replication and scale robustness are enforced by code, configuration and tests rather than remaining chat-only rules.
- No reward, threshold, response horizon, checkpoint tick or world mechanism is changed.

## 9. Workspace and frozen-result boundary

Executable runtime, derived analysis, mutable state, and immutable scientific evidence are distinct artifact classes:

- all source and intervention runtime, including checkpoints, belongs under `runs/`;
- `analyses/` contains only derived reports and assessments;
- mutable overlays belong under `state/`;
- a completed stage is frozen under its owning `studies/<study>/frozen/<stage>/` with content hashes and a complete chain manifest.

Cross-version identity is content-addressed. A legacy candidate label or machine path cannot authorize a later stage by itself. Source-plan hashes, candidate signatures, protocol fingerprints, assessment hashes, decision hashes, and disjoint seed sets must form one verified chain. Legacy runtime may be relocated only by matching the frozen content hashes.

README files are descriptive navigation. Exact commands belong in one numerically ordered command file per step and must not be duplicated across unrelated documentation.

## v0.81 check

- The supplied D3-T replication is valid and independently retains the screen direction and practical effect; the task advances to exact-protocol confirmation.
- The previous directory layout mixed source runs, interventions, checkpoints, derived analyses, and mutable ledgers. This is corrected as an artifact-governance root cause rather than handled with another one-off candidate binding.
- Screen and replication are frozen as one portable study chain. The legacy generic screen candidate ID is accepted only through the original paired-plan source hash, not through a rewritten historical plan.
- D3-O through D3-S now have decision-only legacy study bundles. Their missing raw evidence is explicit, and no plan, assessment, result, or checkpoint identity is fabricated.
- Legacy stage migration verifies compact evidence and all checkpoint anchors before splitting source runtime, intervention runtime, and analyses; checkpoint-only relocation also completes hash preflight before writing and is safe to resume idempotently.
- Study-specific configs and candidate specs are colocated with design and ordered commands; project-level configs remain reusable presets.
- `.vscode/` is excluded from version control.
- No reward, world mechanism, cost, threshold, checkpoint tick, response horizon, or seed result is changed.

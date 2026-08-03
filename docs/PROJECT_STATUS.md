# SE project status

Version: **0.141.0**

## Current scientific task

Version 0.141 implements **Subject VM Stage 3C-27: visible-token trajectory kinematics audit**.

Stage 3A remains the authoritative long-term internal-history boundary: the unified graph emits a fixed-width continuous token and a bounded event ring stores that token with objective post-commit facts. Historical node IDs, edge IDs, activation masks and complete execution paths are not persisted.

Stage 3B-1 remains the micro-level bridge. Executed node output and actual bandwidth-bounded edge transmission may leave short-lived local eligibility values selected by graph flags and gates. Their signs remain local computational directions, not event value.

Stage 3B-2 and Stage 3C-1 remain explicit bootstrap biases: normalized continuous-token similarity defaults to one historical event candidate, while Stage 3C-18 permits an explicit at-most-two-candidate research override; the largest still-valid pre-activation local eligibility carrier still chooses at most one target per parameter family. These mechanisms shorten early graph shaping; they are not universal attention claims.

Stage 3B-3 forms a graph-controlled six-dimensional parameter-family proposal. Stage 3C-1 binds nonzero components to exact stable node or edge targets. Stage 3C-2 revalidates those targets and forms bounded candidate deltas. Stage 3C-3 verifies exact float32 compare-and-swap, event-level all-or-none semantics and rollback in a private shadow vector. Stage 3C-4 allows an explicitly opted-in live write only inside a fixed short rollback window and records it in a bounded applied ledger. Stage 3C-5 records the same 21-dimensional score-free evidence contract for guarded-live and read-only control windows.

Stage 3C-6 remains outside the runtime learning path. A plan binds one trusted quiescent checkpoint, its file/state/config hashes, exact source tick, common final tick and two explicit branch identities. The only authorized branch configuration difference is `subject_vm.live_write.enabled`. The branch runner preserves shared checkpoint state and stable-ID keyed randomness, persists branch identity in checkpoint lineage, and writes separate final checkpoints.

The exporter accepts only the planned guarded-live and read-only-control checkpoints, verifies their branch identities and final configuration hashes, extracts completed rollback-verified windows, and pairs them by stable subject, source event, window and exact target/update contract. It emits component-wise objective differences and preserves all unpaired windows. It does not produce a scalar score, fixed value weights, automatic keep/revert decision, permanent write authorization or automatic causal conclusion.

Stage 3C-7 remains outside the runtime and consumes one or more Stage-3C-6 exports plus their referenced final checkpoints. It verifies export/checkpoint hashes, reports independent source-state count, paired-window coverage and structured unpaired reasons, inspects rollback failures, pending writes, locked rows, fact clipping and count-only evaluation-cost matching, and records component-wise entity/environment branch divergence. Its default thresholds are explicit engineering screening parameters, not universal scientific sufficiency or subjective value.

Stage 3C-8 remains outside the runtime and consumes checksum-valid Stage-3C-7 assessments that passed their engineering screen. It resolves the referenced Stage-3C-6 exports, treats independent source checkpoints as the highest replicate unit, averages windows within stable subjects, then balances subjects within each source before cross-source comparison. It reports per-coordinate sign, dispersion and central-interval stability for objective facts, absolute activity and count differences. Duplicate source states do not become additional replicates, and conflicting duplicate data are rejected.

Stage 3C-9 adds a reproducible short-study runner and a frozen fixed bootstrap graph so the existing Stage-3C chain can produce infrastructure data without waiting for topology evolution. The bootstrap is explicitly recorded as fixed cognition and not as an evolved result. Read-only control now reserves the same pending target, ledger and window budgets as guarded-live while remaining parameter-read-only and cost-free at the live-write layer. At the export boundary, remaining temporary writes are restored and control reservations released without executing new semantic ticks; incomplete windows are excluded from paired evidence.

The default three-seed pilot produced 38 completed paired windows with full pairing coverage, zero rollback failures, zero fact clipping and matched evaluation costs. The Stage 3C-8 report found no coordinate passing its descriptive sign-and-interval stability screen: most branch differences were exactly or nearly zero, while the few nonzero differences appeared in only one of three sources. This is an engineering pipeline result only; it does not establish beneficial updates, causal credit, attention optimality, learning or subjecthood.

Stage 3C-10 keeps the v0.123 study factors unchanged and adds external diagnostics plus two bounded trace facts. Across the same three sources, all fixed-bootstrap subjects emit tokens and enter the association/update chain. The dominant bottleneck is later: assigned candidates collapse to delay `1` and similarity `1.0`, all safe proposals and all 45 temporary commits target only `node_bias`, and each commit affects one subsequent semantic activation tick. Live parameters change action potentials and sampled probabilities in all three sources, but only two subject-events in one source cross the sampled discrete-action boundary. Exact parameter restoration, control reservation symmetry, counted evaluation cost matching and export-boundary clearing hold in all sources. One source retains non-parameter path dependence after rollback because the changed action already altered objective state.

These diagnostics support an observability conclusion, not a learning conclusion: the data chain is active, the paired contract is intact, and the short fixed bootstrap produces parameter-level effects that are usually too narrow or too brief to become objective-event differences across independent sources. No mechanism parameter was changed in v0.124.

Stage 3C-11 changes only the independent source count. It preserves 32 initial entities, 16 fixed-bootstrap subjects, source tick 2, branch horizon 5, CPU execution, rollback/evaluation contracts and disabled permanent retention, while extending the predeclared source panel from seeds `12301..12303` to `12301..12309`. The first three sources remain the pilot prefix; zero and nonzero outcomes from the additional six sources are retained without filtering.

The nine-source panel produced 111 completed paired windows with pairing coverage 1.0, zero rollback failures, zero fact clipping and matched evaluation costs. Discrete-action and trace-level objective-event divergence appeared in 2/9 sources; only 1/9 sources had a nonzero completed-window objective vector. No objective coordinate passed the descriptive sign-and-interval stability screen. The 32 entities, 16 subjects and 111 windows improve within-source coverage but do not become 111 independent replicates.

Stage 3C-11 also corrects one diagnostic boundary exposed by the expanded seeds. Paired admission/evaluation symmetry remained valid in 9/9 sources, while later shadow-transaction preparation counts differed in four sources after live parameters had already changed those branches' future internal paths. That later path difference is not itself a paired-admission contract failure. Stage 3C-10 now also reports retained tick coverage; divergence counts from horizons longer than the trace ring are explicitly lower bounds rather than false complete zeros.

Repeated runs preserve identical source checkpoint state hashes, Stage-3C-10 diagnostics and Stage-3C-11 semantic results. Exact checkpoint/plan/export file hashes remain per-run artifact identities because checkpoint metadata includes creation time; Stage 3C-11 therefore reports a separate semantic-result hash that excludes paths, creation time and ZIP-container byte metadata without weakening within-run integrity verification.

Stage 3C-12 changes only `branch_horizon_ticks`, comparing the v0.125 five-tick arm with an eight-tick arm on the identical nine source-state hashes and bootstrap lineage. Eight is the maximum horizon that remains completely visible under the existing bounded trace retention. The comparison adds no runtime field, trace capacity, checkpoint schema, random stream, branch owner or persistent path record.

Before interpreting the extra tail, Stage 3C-12 compares every event-shaped Subject-VM trace array keyed by stable subject and event tick before the five-tick stopping boundary. All live and control prefixes are exactly identical across both arms. Both Stage-3C-7 screens pass with pairing coverage 1.0, zero rollback failures, zero fact clipping, matched evaluation costs and complete divergence-trace coverage.

The eight-tick arm completes 143 paired windows versus 111 at five ticks, while live commits rise only from 141 to 144. Both arms contain the same three discrete-action difference events in the same two of nine sources, and both retain 0/21 stable objective coordinates. The added tail contains no new discrete-action crossing; it only records later objective-state differences continuing from an action path that had already diverged before the five-tick boundary. This makes branch horizon a weaker explanation for the sparse discrete signal under the current rollback/exposure contract, without proving that five ticks are universally sufficient.

Stage 3C-13 changes only temporary exposure duration on the same nine-source, 32-entity, eight-tick CPU panel. `rollback_after_ticks` changes from 2 to 3 and the read-only `control_horizon_ticks` changes with it because Stage 3C-5 requires those horizons to match. The paired plan applies this common override after loading the same source checkpoint, so both arms retain identical source state/config hashes and bootstrap lineage; live versus control within each arm still differs only by `subject_vm.live_write.enabled`.

Before comparing outcomes, Stage 3C-13 verifies that only the two synchronized exposure fields are overridden and that read-only control thought tokens, action potentials, sampled probabilities, actions, resolutions and objective events are identical across arms. Both Stage-3C-7 screens pass with nine independent source pairs, pairing coverage 1.0, zero rollback failures, zero fact clipping, matched evaluation costs and complete divergence-trace coverage.

The longer exposure increases mean effective semantic ticks per commit from 1.000 to 1.993. Action-potential difference events rise from 371 to 423 and sampled-probability differences from 377 to 426, confirming that the temporary parameter change remains behaviorally visible for longer. Discrete-action differences do not rise: they change from three events in two sources to two events in one source. Both arms retain one of nine sources with a nonzero completed-window objective vector and 0/21 stable objective coordinates. Two fewer completed windows in the extended arm are incomplete boundary windows finalized without additional semantic ticks; they are preserved as finalization facts and excluded from evidence rather than treated as rollback failures.

This result does not classify longer exposure as beneficial or harmful. It shows that greater continuous influence does not monotonically become more sampled discrete-action crossings under the current fixed bootstrap. With horizon and exposure visibility now separately audited, the next minimal boundary is fixed-bootstrap parameter-family reachability, because proposals and commits remain concentrated in `node_bias`; no permanent retention, scalar value or general-attention claim is authorized.

The current result classifies the original three-source run as an engineering pipeline pilot, not a scientifically sufficient sample for stable direction claims. The nine-source expansion reduces uncertainty about rarity but still does not establish mechanism efficacy, delayed-effect sufficiency, entity-count adequacy, stable learning or causal credit.

The v0.110 single-owner rule remains unchanged. Subject VM is the sole optional action-potential residual owner when enabled; legacy knowledge/latent/working-memory routes remain fixed-cognition comparison baselines and cannot coexecute on the primary path.


Stage 3C-14 changes only the fixed-bootstrap one-hot modulation target route. The baseline writes the graph-produced target coordinate to token port 23 and therefore proposes `node_bias`; the alternative writes the same activation to token port 25 and therefore proposes `node_output_gate`. Both coordinates are excluded from association similarity, both families bind the same locally eligible node, and the nine-source panel, 32 entities, 16 bootstrap subjects, source tick 2, eight-tick branch horizon, exposure duration 3, bounded delta, rollback and score-free aggregation remain fixed.

The assessment anchors both arms before bootstrap. For every seed, pre-bootstrap checkpoint state/config hashes and selected stable subjects are identical. The two bootstrap profiles differ only in the authorized target-family route. Read-only control action potentials, sampled probabilities, actions, resolutions and objective facts are identical across arms; thought tokens differ only by relocating the same target weight from port 23 to port 25. The control-side token/association/eligibility funnel is also identical, so target-family role rather than source or addressing drift is isolated.

The nine-source comparison reaches both families: each arm produces 722 family proposals and 144 temporary commits, 141 completed paired windows, pairing coverage 1.0, zero rollback failures, zero fact clipping, matched evaluation costs and exact parameter restoration in 9/9 sources. `node_output_gate` produces 287 action-potential and 291 probability-difference events versus 423 and 426 for `node_bias`; discrete-action differences are 1 versus 2, but both arms diverge in only 1/9 source and both remain 0/21 stable objective coordinates. Parameter role therefore changes short-term continuous visibility, but opening a second reachable family does not create cross-source objective stability.

A preliminary `node_bias -> node_input_gate` comparison was rejected before becoming a scientific arm: node 0 reads the `constant-one` input port, so a bias delta and an input-gate delta are algebraically equivalent in this fixed bootstrap. This is recorded as an experiment-design diagnostic, not as evidence that the two parameter families are generally equivalent. Stage 3C-14 does not rank families by value, authorize permanent retention, validate causal credit or establish learning.

Stage 3C-15 does not open another live-write target. It replays bounded external `±0.05` finite-difference probes for all six generic parameter families from the same nine quiescent source checkpoints. Probe branches are transient, are not written back to source checkpoints, consume no new runtime state and retain the Stage 3C-7/8/10 baseline as engineering context.

Two operating contexts are required. The first activation after bootstrap diagnoses immediate node/output/token effects; a second context after one unperturbed activation permits the one-tick delayed edge to contribute. Across nine sources, `node_bias` and `node_input_gate` are numerically equivalent within `5.96e-8`, as expected from the constant-one input. `node_trace_gate` changes only the internal target token at the one-step probe horizon. `edge_forward_gate` is action-potential sensitive only in the warmed delayed-edge context, while `edge_bandwidth` remains locally zero because the current raw contribution never reaches the clamp boundary.

The diagnostic also separates local sensitivity from eligibility reachability. `node_bias`, `node_input_gate` and `node_output_gate` are currently reachable through node-0 local eligibility. `node_trace_gate` and `edge_forward_gate` are mechanically sensitive at the inspected operating points but are not reachable through the current fixed bootstrap eligibility carriers. This is an engineering shaping fact only; it does not assign value, validate credit, authorize eligibility expansion, retention, learning or a preferred parameter family.

Stage 3C-16 holds the frozen nine-source panel, 32 entities, 16 bootstrap subjects, source tick 2, eight-tick branch horizon, exposure duration 3, bounded update scale, nearest-token association and automatic rollback fixed. Both arms route the same one-hot target coordinate to `edge_forward_gate` on token port 27. The only bootstrap difference is whether edge 0 owns the existing bounded local-eligibility flag and gate.

The carrier-off arm preserves token generation, delayed association and modulation proposals but produces zero exact target bindings, zero safe updates, zero commits and zero completed windows. It is therefore an intentionally unreachable funnel baseline, not a Stage-3C-8 scientific replicate. The carrier-on arm produces 688 target bindings, 646 safe updates, 144 temporary commits and 129 completed paired windows across nine independent sources. Pairing coverage is 1.0, rollback failure and fact clipping are zero, evaluation cost matches, discrete-action/objective divergence appears in 3/9 sources, and the Stage-3C-8 screen remains 0/21 stable objective coordinates.

Pre-bootstrap state/config hashes, selected stable subjects, read-only control event arrays and the read-only token/association/modulation funnel are identical across arms. The result establishes that a local carrier is necessary for the current exact-target binding chain and that `edge_forward_gate` becomes mechanically writable once exposed. It does not establish credit quality, beneficial direction, learning, value or permission for permanent retention.

## Engineering status

Implemented and tested:

- Stage-1 fixed-capacity unified graph storage and lifecycle/checkpoint ownership;
- Stage-2 deterministic bounded CPU-reference activation and action-potential integration;
- v0.110 routing-ownership registry and policy/configuration conflict guards;
- Stage-3A continuous graph-produced token and bounded objective-event ring;
- Stage-3B-1 local node/edge eligibility with deterministic decay and expiry;
- Stage-3B-2 bounded delayed association candidates with explicit unassigned outcomes;
- Stage-3B-3 graph-requested parameter-family proposals without fixed event value;
- Stage-3C-1 pre-activation exact target binding under a replaceable bootstrap selector;
- Stage-3C-2 bounded candidate deltas with target revalidation, clips, L1 budget and parameter projection;
- Stage-3C-3 exact all-or-none shadow CAS, apply and rollback evidence;
- Stage-3C-4 explicit opt-in guarded live commits, bounded applied ledger and deterministic pre-activation rollback;
- Stage-3C-5 guarded-live/read-only objective evaluation windows with identical evidence shape;
- Stage-3C-6 source-checkpoint quiescence checks and deterministic plan identity;
- Stage-3C-7 repeated paired-export checksum verification, coverage/unpaired diagnostics and integrity assessment;
- Stage-3C-8 hierarchical source/subject/window aggregation and coordinate-wise sign, dispersion and interval assessment;
- Stage-3C-9 fixed-bootstrap short paired runner, symmetric control admission and export-boundary transient finalization;
- Stage-3C-10 source/subject funnel, update magnitude and exposure, association/eligibility quality, branch divergence, trace-retention coverage and aggregation-sensitivity diagnostics;
- Stage-3C-11 independent-source prefix sensitivity, source-level divergence incidence and sample-adequacy assessment without pseudoreplication;
- Stage-3C-12 horizon-only comparison with identical source states, exact semantic prefix identity and complete bounded-trace coverage;
- Stage-3C-13 exposure-only comparison with identical source checkpoints, synchronized control reservation and read-only behavior identity;
- Stage-3C-14 fixed-bootstrap target-family reachability comparison with pre-bootstrap identity, authorized token relocation and rejected-degeneracy recording;
- Stage-3C-15 external six-family finite-difference audit with delayed-edge warm context, algebraic-degeneracy detection and sensitivity-versus-eligibility separation;
- Stage-3C-16 isolated edge-forward eligibility-carrier toggle with unreachable-baseline handling, read-only control identity and carrier-on Stage-3C-7/8 evidence;
- Stage-3C-17 equal-similarity latest/oldest temporal tie-break audit with event-reuse concentration diagnostics;
- Stage-3C-18 top-1/top-2 bounded candidate-allocation audit with one-proposal budget, fixed-capacity secondary-reference diagnostics and trace-schema v9 compatibility;
- Stage-3C-19 external association-visible token variance, rank and normalized-dot score-separability diagnostic;
- Stage-3C-20 isolated node-0 graph-state readout comparison with pre-bootstrap identity, read-only objective-behavior identity and temporal-versus-subject geometry decomposition;
- v0.123 trace/checkpoint compatibility for the new bounded diagnostic fields;
- explicit guarded-live/read-only branch identities bound to source state, branch config and final tick;
- branch identity persistence in final checkpoint lineage;
- completed-window extraction and component-wise paired export without scalarization;
- explicit preservation of unpaired windows and failed pairing visibility;
- fixed 21-dimensional fact sums, absolute sums, maximum absolute values and event counts without a scalar score;
- birth/death/compaction/clone/checkpoint handling through the existing stable-owner lifecycle;
- exact disabled/default normalization preserving frozen legacy configuration identities;
- no engine-defined event value, automatic keep/revert choice, permanent retention or additional runtime random-number consumption.

D1-X/Y and the latent/working-memory policy family remain:

```text
rejected-as-primary-subject-model
retained-as-fixed-cognition-baseline
```

They retain engineering and comparison value but own neither Subject VM state nor the primary optional action route.

## Epoch milestones

- `epoch-0-ecological-carriers`: current era. Stage 3C-27 separates source-boundary forcing, exact latest-on-tie behavior and strict local token geometry without changing addressing or authorizing retention, learned attention or Epoch 1.
- `epoch-1-entity-subject-prototype`: not started. It still requires delayed parameter use, controlled intervention, baseline exceedance, cost compensation and independent replication.
- `epoch-2-group-subject-prototype`: not started. Candidate/group graphs remain observational and own no rules or Subject VM state.

No supplied checkpoint qualifies either later epoch.

## Not implemented or authorized

- interpreting delayed token similarity as causal credit;
- using objective event coordinates as fixed positive or negative value;
- scalarizing Stage 3C-5/3C-6 fact vectors;
- automatic causal attribution from a paired export;
- automatic keep/revert or permanent parameter retention;
- semantic acceptance of a committed update as beneficial or causally correct;
- recovery from rollback CAS failure beyond locking the subject write path;
- an unbounded or cross-generation applied-update/evaluation ledger;
- physical plasticity cost debit or health-compensated cost experiments;
- content-provenance references actually consumed by the graph;
- automatic conversion of legacy router genes/state into Subject VM nodes or edges;
- topology mutation, developmental expression, token/proposal-readout mutation, node migration or region-capacity evolution;
- a complete general attention allocator, candidate budget competition or lazy payload execution;
- fixed reward, trust, knowledge value, interest formula or group bonus;
- relation/group replacement;
- GPU packed Stage-2/3 execution;
- Epoch 1 panel, paired selection, gene persistence, candidate ledger or subjecthood score.

Stage 3C-27 establishes that source-boundary forcing contributes to total age-one coverage, but 386 of 387 multi-candidate age-one selections are strict normalized-dot geometry wins and only one requires latest tie-break. Strict age-one queries have about 200-fold smaller local visible-token steps than older-winner queries, and selected age tracks first-readout state persistence and recurrence. The next authorized boundary remains read-only diagnosis of shared sampling phase and recurrent geometry before any normalization, addressing or retention change.


## Stage 3C-17 retained result

Stage 3C-17 preserves the Stage-3C-16 carrier-on `edge_forward_gate` baseline and changes only exact-similarity temporal tie resolution from latest to oldest. The override is recorded in the paired plan and applied symmetrically to guarded-live and read-only-control branches. It is not part of persistent configuration or checkpoint state.

Across nine independent sources, both arms assign 1008 candidates with similarity 1.0. Latest selects delay 1 exclusively and uses 112 unique historical events per source once each. Oldest produces delays 1–6 but uses only 32 unique events per source, with one event reused up to six times. Latest produces 942 modulation proposals and 129 completed windows; oldest produces 801 proposals and 105 windows. Objective divergence occurs in 3/9 versus 2/9 sources, while both arms remain 0/21 stable objective coordinates.

This identifies the temporal tie-break as a material fixed-bootstrap bias. It does not establish that latest is better, that oldest is harmful, that recency or age has value, or that the credit assignment is scientifically valid. The next authorized boundary is a bounded multi-candidate allocation diagnostic with total update budget held fixed.

## Stage 3C-18 current result

Stage 3C-18 preserves the Stage-3C-16 carrier-on `edge_forward_gate` baseline and the Stage-3C-17 latest-on-tie rule. The only experimental factor is association candidate limit 1 versus 2. The top-2 arm forms one equal-weight historical objective-fact mean and still emits at most one modulation proposal under the original event delta budget. The override is checksum-bound in the paired plan, applied symmetrically to live/control, and is not a persistent configuration field.

Across nine independent sources, both arms assign 1008 current events. Top-2 adds 864 secondary delay-2 references and raises modulation proposals from 942 to 970 and completed paired windows from 129 to 137. Guarded-live commits remain 144 in both arms. Unique selected historical events remain 112 per source; top-2 instead makes 96 events per source reusable twice. Discrete action differences change from 4 to 2, objective-event divergence incidence from 3/9 to 2/9 sources, and both arms remain 0/21 stable objective coordinates.

This establishes candidate cardinality as a material fixed-bootstrap allocation factor but does not show improved historical coverage, causal credit, learning or value. The next authorized boundary is diagnostic rather than another allocator expansion: measure token-coordinate variance, effective rank and score separability while holding all runtime mechanisms fixed.

## Stage 3C-19 current result

The frozen nine-source read-only-control traces contain 1,152 association-visible tokens. Control and modulation ports 0-28 are excluded from similarity, leaving ports 29-31; every visible vector is exactly `[0, 0, 1]`. Per-source centered covariance rank and effective rank are zero, while uncentered direction rank is one. All 3,888 delay-eligible query/candidate pairs are exact vector duplicates with normalized-dot score 1.0, constant threshold margin 0.2 and zero best-versus-second spread.

This explains why temporal tie-break and candidate cardinality, rather than content score, determined allocation in Stages 3C-17/18. It does not prove the general token mechanism incapable, does not validate or invalidate credit, and authorizes no runtime change, retention, learned weight, scalar objective or universal-attention claim.


## Stage 3C-20 current result

Stage 3C-20 preserves the nine-source, 32-entity, carrier-on `edge_forward_gate` top-1/latest baseline. The only experimental factor is whether action-producing node 0 also emits its current scalar state through trace gate 1.0 to association-visible token port 29. Pre-bootstrap state/config hashes, selected stable subjects and read-only objective behavior are identical across arms; thought tokens differ only on port 29.

The baseline retains one visible vector and centered rank zero. The readout arm produces seven visible vectors and centered rank one in every source. Normalized-dot scores span approximately `-0.5073..1.0`, best-versus-second spreads become positive and exact score ties disappear. However, all 16 bootstrap subjects have the same port-29 value within each tick, and all nine sources share the same tick-mean trajectory. The readout is therefore a fixed shared temporal-phase coordinate, not subject or event identity.

Selected associations change from 1,008 delay-1 assignments to 864 delay-2 assignments. Modulation proposals change from 942 to 535, temporary commits from 144 to 143, completed paired windows from 129 to 100, and objective-event divergence incidence from 3/9 to 2/9 sources. Both arms retain pairing coverage 1.0, zero rollback failures, zero fact clipping, matched evaluation costs and 0/21 stable objective coordinates.

This establishes visible-geometry and score-separation reachability under one replaceable fixed readout. It does not establish event-specific content, causal credit, beneficial direction, learned attention, stable learning, subjecthood or permission for permanent parameter retention.


## Stage 3C-21 current result

Stage 3C-21 uses a common nine-node fixed bootstrap graph in both arms. Node 8 is a readout-only linear node with no action output, no local eligibility and trace port 29. The only experimental factor is its objective input port: constant-one port 0 versus uncertainty-mean port 11. The additional node capacity is common support in both arms and does not change the contrast.

The constant arm reproduces rank-zero geometry, 1,008 delay-1 assignments, 942 modulation proposals, 144 temporary commits, 129 completed windows, objective divergence in 3/9 sources and 0/21 stable coordinates. The uncertainty arm has centered rank one in every source, between-subject variance at every retained tick, temporal variation in 143/144 subjects, source-specific subject/event matrices and selected similarity range approximately `0.9445..1.0`. Its 1,008 assignments spread over delays 1–6, but unique associated events fall to 85–94 per source and maximum event reuse rises to three. It produces 846 proposals, 144 commits, 125 completed windows, objective divergence in 2/9 sources and 0/21 stable coordinates.

This establishes that subject- and event-specific association-visible geometry is reachable through an existing objective input without changing action output. It does not establish that uncertainty is valuable, that historical selection is more diverse, that causal credit is correct, or that learning has formed. The next authorized boundary is a read-only audit of selected-event diversity and reuse under the fixed Stage 3C-21 readout before changing addressing, top-k, update scale or retention.
## Stage 3C-22 current result

Stage 3C-22 makes no runtime intervention. It reconstructs every current-event query and every same-subject historical event inside the frozen delay bounds from the Stage 3C-21 read-only control checkpoints. The reconstruction uses the exact excluded control ports, normalized-dot similarity, threshold, latest tie-break and top-1 selector, and verifies every stored assignment with zero mismatch.

Both arms retain the same candidate opportunity in all nine sources: 112 unique delay-valid, nonzero and above-threshold historical events per source, 432 above-threshold query/candidate references and 112 assigned current events. The constant-one arm selects all 112 identities once each. The uncertainty arm selects only 85–94 identities, leaving 18–27 eligible identities unused per source and reusing some selected events up to three times. Unique identity coverage is 75.9%–83.9%; eligible-union selection Gini is approximately 0.272–0.381; inverse-Simpson effective selected-event count is 72.1–83.6, or 64.4%–74.7% of the eligible union.

The uncertainty selected set is a strict subset of the constant-arm selected set in every source and introduces no new event identity outside it. Exact same-query selection remains only 52.7%–71.4%, so the readout materially changes ranking while the threshold opportunity remains fixed. The centered rank of selected objective-fact vectors remains equal to the eligible-set rank in every source, showing that reduced event-identity coverage does not imply complete factual-span collapse.

This result does not rank coverage or reuse as good or bad, validate causal credit, establish learning, assign value to uncertainty, or authorize permanent retention. Constant-arm full identity coverage is itself a consequence of latest-on-tie selecting the immediately preceding event once; it is an engineering reference, not a scientific optimum.



## Stage 3C-23 current result

Stage 3C-23 uses a common ten-node fixed bootstrap in both arms. Node 8 keeps uncertainty-mean on association-visible port 29. Node 9 is readout-only, has no action output or local eligibility, and writes port 30. The only arm difference is node 9 input: duplicated uncertainty-mean port 11 versus data-screened local-resource-ratio-3 port 7.

The screen examines all approved objective inputs except constant-one and the primary uncertainty coordinate. A candidate must reach centered rank two in every source, show subject variance at every tick and temporal variance for every subject, and preserve at least one threshold-eligible historical candidate for every query. Port 7 maximizes the cross-source minimum residual variance after regression on uncertainty among qualifying ports. This geometry-only rule assigns no value to the resource channel.

The duplicate-coordinate arm remains rank one with 3–7 unique visible vectors per source. The selected-coordinate arm reaches rank two in 9/9 sources and has 128 unique vectors per source. Both assign 1,008 associations and execute 144 temporary commits. Proposals change from 846 to 833, completed windows from 125 to 121, objective-divergent sources from 2/9 to 1/9, and both remain 0/21 stable objective coordinates.

This establishes mechanical rank-two reachability only. It does not validate causal credit, rank token spaces by value, establish learning, authorize permanent retention or convert normalized-dot addressing into a universal attention claim.

## Stage 3C-24 current result

Stage 3C-24 reruns the frozen Stage 3C-23 rank-one duplicate-coordinate and rank-two selected-coordinate arms. It reconstructs every query/candidate score from read-only control checkpoints under the unchanged normalized-dot, threshold 0.8, latest/top-1 contract. Stored winner event IDs and similarities must match the reconstruction exactly.

Both arms retain 112 unique eligible historical events and 432 above-threshold references per source. Rank one selects 85–94 unique identities per source and still contains exact best-score ties. Rank two selects 80–88 identities, eliminates exact ties in all nine sources, and increases Gini concentration while reducing inverse-Simpson effective coverage. Every rank-two selected set is a strict subset of the corresponding rank-one set; no new event identity is introduced.

This result distinguishes score-order determinacy from evidence diversity. Higher geometric rank and positive winner margins do not establish better causal credit, beneficial updates, learning, value or subjecthood. Runtime and checkpoint schemas are unchanged and permanent retention remains disabled.

## Stage 3C-25 current result

Stage 3C-25 makes no runtime intervention. It reuses the frozen Stage 3C-23 rank-two read-only control checkpoints and reconstructs every above-threshold candidate under the unchanged normalized-dot, threshold 0.8, latest/top-1 contract. Stored winner event IDs and similarities match the reconstruction exactly.

Each source contains 112 assigned queries, of which 96 have more than one eligible candidate. The rank-two arm selects 80–88 unique winners per source; 21–27 winners are selected more than once, accounting for 41.1%–52.7% of assignments. A majority of multi-candidate queries have absolute best-versus-second margin at or below `1e-3`, so small numerical margins remain common.

However, winner reuse is not concentrated in the weakest normalized margins. In all nine sources, the median best-versus-second margin normalized by the full eligible score spread is larger for assignments to reused winners than for assignments to single-use winners. The reused-winner median ranges from approximately 0.059 to 0.798, while the single-use median ranges from approximately 0.000395 to 0.0191. The fraction at or below absolute margin `1e-6` is also lower for reused-winner assignments in every source.

Every reused winner is selected by distinct query events and distinct exact visible query vectors. Reused winners have a median of six eligibility opportunities in every source, compared with three to four for single-use winners, and span one to five query ticks. Query pairs selecting the same winner are not more mutually similar by median cosine than same-subject query pairs selecting different winners.

The supported interpretation is therefore opportunity-conditioned deterministic candidate-basin reuse, not exact query duplication and not reuse driven solely by the smallest margins. This does not validate causal credit, assign value to reuse or margin, establish learning, authorize permanent retention, or convert the fixed bootstrap into universal attention.


## Stage 3C-26 current result

Stage 3C-26 makes no runtime intervention. It reuses the frozen Stage 3C-23 rank-two read-only control checkpoints and reconstructs every candidate under the unchanged normalized-dot, threshold 0.8, latest/top-1 contract. Stored winner event IDs and similarities match exactly.

Each source has 128 association requests: 16 have no historical candidate, 112 are assigned, and the first 16 assigned queries have exactly one eligible candidate. These forced assignments account for 1/7 of all assignments and guarantee that all phase-zero events are selected once.

After removing the forced queries, age-one selection rate is 0.375–0.5625 and is highest or tied in all nine sources, strictly highest in eight. Reused winners have historical-phase median 0–1, single-use winners 3–4, and unselected eligible events 4–5. Opportunity-normalized reused-winner selection-rate median is at least the single-use median in all sources and strictly higher in eight.

The evidence therefore separates boundary forcing, raw opportunity and persistent near-age basin occupancy. It does not assign value to recency or age, validate causal credit, establish learning, or authorize permanent retention.


## Stage 3C-27 current result

Stage 3C-27 makes no runtime intervention. It reuses the frozen Stage 3C-23 rank-two read-only control checkpoints and checksum-bound Stage 3C-26 assessment, reconstructs every candidate under the unchanged normalized-dot/threshold/latest/top-1 contract, and verifies stored winners exactly.

Across nine independent source checkpoints, 864 multi-candidate queries contain 387 age-one selections. Of these, 386 are strict score wins and one is an exact tie resolved by latest. The source-balanced median local normalized-token step is about `3.78e-4` for strict age-one queries and `7.57e-2` for older-winner queries. First-readout-coordinate persistence predicts age-one selection at 0.902–0.966 per source; coordinate changes predict older selection at 0.841–0.929.

The engineering baseline remains pairing coverage 1.0, zero rollback failure, zero fact clipping, matched evaluation cost and 0/21 stable objective coordinates. The result diagnoses fixed-bootstrap trajectory geometry only and authorizes no value assignment, causal-credit claim, learning claim, automatic keep/revert or permanent retention.

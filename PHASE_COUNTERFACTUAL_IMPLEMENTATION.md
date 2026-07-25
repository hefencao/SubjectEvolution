# Phase-aware checkpoint counterfactuals (v0.17.0)

## Purpose

Long-run correlations can be dominated by shared ecological time trends. v0.17 adds a phase-aware runner that selects observational rise, peak, decline and trough states, maps them to trusted `.sechk` snapshots, and executes paired scientific branches with keyed randomness.

The runner does not label phases as causal mechanisms. A complete trough→peak→trough cycle must be detected before execution by default. Descriptive fallback labels require the explicit `--allow-incomplete-cycle` smoke-test flag.

## New scientific interventions

### `neutralize-resource-affinity`

- Replaces effective four-channel affinity with the uniform fixed-budget vector `[4096, 4096, 4096, 4096]`.
- Does not modify genotype coordinates, mutation, inheritance, knowledge, or environment fields.
- Applies consistently to policy resource utility, resource gradients, CPU harvest assimilation and hybrid GPU preparation.

### `disable-knowledge-policy`

- Publishes no knowledge residual to policy.
- Retains knowledge copies, local outcome learning, working-memory updates, storage costs and future transfer unless separately disabled.

### `disable-knowledge-transfer`

- Prevents future copy-transfer planning and commits.
- Keeps all existing copies and their local learning state.

Existing `ablate-working-memory` and `bypass-sparse-selection` interventions remain available.

All runtime ablation flags are cloned and stored in full checkpoints. Old checkpoints restore them as disabled.

## Phase selection

`phase_counterfactual.py` smooths the alive series with a three-window moving average and searches after a warm-up cutoff for the latest complete:

```text
trough -> peak -> trough
```

Within that cycle:

- rise is the maximum net-growth window before the peak;
- peak is the local population peak;
- decline is the minimum net-growth window between peak and trough;
- trough is the following local population trough.

Target ticks are mapped to the nearest unused full checkpoint, preferring an earlier checkpoint on equal distance.

## Usage

Plan only:

```bash
python -m subject_evolution.phase_counterfactual \
  --run-dir runs/heterogeneous_multiseed/seed_10001 \
  --output analyses/seed10001_phase_plan \
  --horizon 120
```

Execute:

```bash
python -m subject_evolution.phase_counterfactual \
  --run-dir runs/heterogeneous_multiseed/seed_10001 \
  --output analyses/seed10001_phase_counterfactual \
  --horizon 120 \
  --execute \
  --backend cpu
```

The default interventions are affinity neutralization, working-memory ablation, selector bypass, knowledge-policy disable and knowledge-transfer disable.

## Scientific boundary

Each delta is local to one checkpoint state and one post-intervention horizon. Replication across seeds and multiple cycles is required before claiming necessity or a general causal mechanism. Real CUDA execution remains unvalidated; scientific GPU requests should retain strict-reference semantics.

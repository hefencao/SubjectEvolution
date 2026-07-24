# Latent Routing Compute Cost — v0.12.0

## Purpose

v0.10.0/L1 and v0.11.0/L2 gave carriers increasingly expressive knowledge routers, but router execution was physically free. v0.12.0 introduces an optional world-internal energy cost so L1/L2 comparisons can be made under explicit computation budgets.

The feature is disabled by default. With `routing_cost_enabled=false`, v0.12.0 reproduces v0.11.0 L1/L2 semantics on all common state and log fields tested.

## Public boundary

The routing sequence is:

1. Build an immutable latent knowledge policy proposal from the pre-charge observation.
2. Compute an exact per-entity cost request from proposal diagnostics.
3. Apply `all-or-none-per-entity-v1` budget arbitration using pre-charge entity energy.
4. Deduct committed energy from authoritative world state.
5. Publish only affordable action-logit residuals.
6. Sample policy actions from the same pre-charge observation.
7. Resolve intents using the post-charge physical energy state.

This prevents routing cost from silently changing the current observation, while ensuring the cost is physically present before actions are resolved.

## Cost formula

For each entity that has at least one non-zero latent residual proposal:

```text
requested_energy =
    base_energy
  + latent_dimension_count × energy_per_latent_dimension
  + integer_mac_count × energy_per_mac
  + active_hidden_unit_count × energy_per_active_hidden_unit
  + emitted_action_count × energy_per_emitted_action
  + saturation_count × energy_per_saturation
  + clipped_output_count × energy_per_clipped_output
```

All terms are explicit config fields. Zero-valued terms are allowed.

### MAC accounting

Shared work:

- variable-length latent projection;
- five-dimensional local-outcome injection;
- reliability-weighted copy/action aggregation.

L1 additionally counts the linear action router.

L2 additionally counts both MLP layers. Bias additions and integer divisions are covered by the base invocation term instead of being mislabeled as multiply-accumulate operations.

## Budget arbitration

`all-or-none-per-entity-v1` accepts all residual cells for one entity if its pre-charge energy can pay the complete request. Otherwise all of that entity's knowledge residual cells are rejected and no routing energy is charged.

This rule avoids backend-dependent partial scaling near action boundaries. Rejected entities retain the genetic policy and any non-latent policy mechanisms.

A diagnostic cost-free action is computed with the same counter-based random draw whenever a proposal is rejected. The engine records how often budget rejection changes the sampled action.

## Audit outputs

New output:

```text
knowledge_routing_costs.csv
```

Per requested entity it records:

- requested and committed energy;
- accepted/rejected status;
- latent dimensions;
- MAC estimate;
- active hidden units;
- hard-tanh saturation count;
- output clipping count;
- emitted action count.

Metrics add step and cumulative requested/committed/rejected energy, entity counts, action-cell counts, work-unit totals and cost-induced action changes.

## K4 attribution

K4 candidate tracking adds `routing_cost` as a separate host-cost component. A committed entity charge is distributed across matching content IDs by encoded bytes. Attribution sums to the world routing charge within floating-point accounting tolerance.

The routing cost is also represented as `routing_cost_attributed_to` candidate graph edges.

## Checkpoint and replay

Routing totals are part of `KnowledgeStepStats`, which is included in trusted full-world checkpoint state. Costed continuous and restored branches match exactly in the short validation.

No persistent hidden budget state is required: each tick's budget is the carrier's current physical energy.

## CPU/GPU semantics

Cost requests are computed from CPU-host immutable plan diagnostics. The accepted sparse plan is then used by either CPU or device policy execution.

In hybrid preparation, device policy features still use pre-charge device energy. After policy evaluation, the committed host charge is synchronized to the device mirror. This keeps observation semantics aligned while preserving the physical world deduction.

Real CUDA multi-tick validation is still pending because the development container has no accessible CUDA GPU.

## Known limits

- The current cost is an explicit model unit, not calibrated to joules or real hardware power.
- All-or-none arbitration may be replaced by a separately versioned partial-budget rule later, but must not silently change this schema.
- Router planning itself is computed by the engine even when the simulated carrier rejects the proposal; that host computation is diagnostic implementation work, not free simulated computation.
- Short runs do not establish long-term adaptive superiority for L1 or L2.

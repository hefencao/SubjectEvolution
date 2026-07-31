from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunConfig:
    seed: int
    ticks: int
    metrics_period: int
    checkpoint_period: int
    # Complete action/trajectory records are opt-in.  Keeping the list empty
    # preserves the small, aggregate-only output of the reference runner.
    trajectory_subject_ids: tuple[int, ...] = ()
    # Device harvest planning keeps the same resolution/commit contract.
    # It is enabled for the GPU hybrid path after fixed-seed plan and
    # 100k-entity profiling checks; set false to profile the CPU key builder
    # while retaining the device allocation/commit stages.
    gpu_harvest_conflict_planner: bool = True
    # Scientific mode forbids direct action replacement and opt-in heuristic
    # controllers.  Entertainment mode keeps those mechanisms available for
    # demos without allowing their output to masquerade as scientific data.
    experiment_mode: str = "scientific"
    evolution_evaluation_period: int = 500
    validation_mode: bool = False
    # GPU-capable runs use the hybrid accelerator by default.  CPU remains the
    # deterministic fallback when CUDA/CuPy is unavailable.  The explicit
    # strict-reference mode is retained for diagnostics and historical replay;
    # CPU/GPU semantic validation belongs to the parity suite rather than the
    # production run path.
    gpu_semantics_mode: str = "hybrid-accelerated"
    # CuPy retains freed blocks in its default allocator cache.  A population
    # whose active batch grows every tick can otherwise leave a staircase of
    # obsolete block sizes resident.  The bounded policy releases only unused
    # blocks at end-of-step boundaries; live arrays and world semantics are
    # unaffected.
    gpu_memory_pool_policy: str = "bounded-cache-v1"
    gpu_memory_pool_cache_limit_bytes: int = 536870912
    gpu_memory_pool_trim_period: int = 1
    # Full-world bundles are opt-in because they are larger than the legacy
    # analysis-only NPZ snapshots.  When enabled they use checkpoint_period.
    full_checkpoint_enabled: bool = False
    # Optional exact checkpoint ticks. These complement checkpoint_period and
    # are especially useful for phase-matched multi-seed experiments.
    checkpoint_ticks: tuple[int, ...] = ()
    # Optional observational diagnostics for long multi-seed runs.  These
    # fields never feed back into policy or world state and are disabled by
    # default so archived evolution_progress JSONL remains unchanged.
    long_run_diagnostics_enabled: bool = False
    long_run_diagnostics_schema: str = "disabled"
    # Optional local analysis grid.  This remains purely observational and is
    # disabled by default so archived long-run schemas remain byte-compatible.
    spatial_stress_diagnostics_enabled: bool = False
    spatial_stress_diagnostics_schema: str = "disabled"
    spatial_stress_regions_x: int = 4
    spatial_stress_regions_y: int = 4
    # Analysis-only spatial partition. v1 keeps a fixed region count over
    # normalized world coordinates; scale consequences are published in
    # provenance rather than silently treated as invariant.
    spatial_stress_region_schema: str = "normalized-fixed-count-grid-v1"
    # Optional observational subject-succession diagnostics. The tracker uses
    # stable entity IDs to compare social-group memberships across refreshes;
    # it never changes group labels or candidate-subject graph state.
    subject_structure_diagnostics_enabled: bool = False
    subject_structure_diagnostics_schema: str = "disabled"
    # Optional multiscale environment/subject exposure atlas. Each scale is a
    # normalized fixed-count partition expressed as [regions_x, regions_y].
    # Empty scales keep archived configurations and outputs unchanged.
    environment_atlas_diagnostics_enabled: bool = False
    environment_atlas_diagnostics_schema: str = "disabled"
    environment_atlas_scales: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class WorldConfig:
    width: float
    height: float
    grid_x: int
    grid_y: int
    initial_entities: int
    max_entities: int
    periodic: bool


@dataclass(frozen=True)
class EnvironmentConfig:
    resource_regeneration: tuple[float, float, float, float]
    resource_capacity: tuple[float, float, float, float]
    season_period: int
    season_amplitude: float
    signal_decay: float
    signal_diffusion: float
    # Legacy runs retain the original globally synchronized four-channel
    # resource field.  The heterogeneous schema adds spatial phase offsets
    # without changing the action vocabulary or hard-coding a preferred niche.
    schema: str = "legacy-four-channel-v1"
    resource_temporal_phase_offsets: tuple[float, float, float, float] = (
        0.0, 1.3, 2.6, 3.9
    )
    # Number of additional seasonal cycles across the world in x/y.
    resource_spatial_phase_x: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    resource_spatial_phase_y: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    # D0 orthogonal-resource schema. These fields are inert for legacy and v1
    # heterogeneous environments. Wave vectors are expressed in normalized
    # world cycles, while each channel has its own temporal period, amplitude,
    # and diffusion scale.
    resource_cycle_periods: tuple[int, int, int, int] = (120, 173, 229, 307)
    resource_cycle_amplitudes: tuple[float, float, float, float] = (
        0.55, 0.50, 0.45, 0.40
    )
    resource_primary_wave_vectors: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ] = ((1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, -1.0))
    resource_secondary_wave_vectors: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ] = ((2.0, 1.0), (1.0, 2.0), (2.0, -1.0), (1.0, -2.0))
    resource_primary_wave_amplitudes: tuple[float, float, float, float] = (
        0.24, 0.22, 0.20, 0.18
    )
    resource_secondary_wave_amplitudes: tuple[float, float, float, float] = (
        0.14, 0.13, 0.12, 0.11
    )
    resource_diffusion_rates: tuple[float, float, float, float] = (
        0.002, 0.006, 0.012, 0.020
    )
    # D3-E opt-in abiotic processing support.  The field reuses the same
    # role-free four-channel wave basis as persistent renewal but is shifted by
    # a quarter cycle.  It carries no material and has no entity, lineage, or
    # group feedback.  A zero amplitude keeps archived configurations inert.
    resource_processing_schema: str = "disabled"
    resource_processing_support_amplitude: float = 0.0
    harvest_channel_multipliers: tuple[float, float, float, float] = (
        1.0, 0.45, 0.25, 0.18
    )
    # Per raw-resource channel effects on: energy, integrity, material,
    # information, fertility.  The matrix is used only by the heterogeneous
    # schema; the legacy branch preserves its historical direct mapping.
    resource_effect_matrix: tuple[
        tuple[float, float, float, float, float],
        tuple[float, float, float, float, float],
        tuple[float, float, float, float, float],
        tuple[float, float, float, float, float],
    ] = (
        (1.0, 0.0, 0.0, 0.0, 0.0),
        (0.0, 0.05, 0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 0.0, 1.0),
    )
    hazard_spatial_phase_x: float = 0.0
    hazard_spatial_phase_y: float = 0.0
    hazard_temporal_multiplier: float = 1.0
    hazard_secondary_amplitude: float = 0.0
    # Optional local, decaying physical trace deposited by death events.  It
    # is not a global death oracle: only the local field and its gradient can
    # enter the existing danger observation boundary.
    mortality_trace_schema: str = "disabled"
    mortality_trace_decay: float = 0.0
    mortality_trace_diffusion: float = 0.0
    mortality_trace_deposit: float = 0.0
    mortality_trace_max: float = 1.0
    mortality_trace_observation_weight: float = 0.0
    # Optional low-coupling additive field process. The core passes only a
    # normalized grid and tick and accepts only a scalar hazard contribution;
    # no entity, policy, relation, lineage or knowledge state crosses this
    # boundary. External implementations are registered as trusted plugins.
    environment_process_schema: str = "disabled"
    environment_process_parameters: dict[str, Any] | None = None
    # v0.22 compatibility adapter for the former in-core synthetic moving
    # Gaussian field. New configurations should use environment_process_*.
    moving_hazard_schema: str = "disabled"
    moving_hazard_source_count: int = 0
    moving_hazard_amplitude: float = 0.0
    moving_hazard_radius: float = 0.12
    moving_hazard_speed: float = 0.0
    moving_hazard_phase_offset: float = 0.0
    # Optional non-biological physiological environment.  This adds three
    # independent fields without changing resource identity: local oxygen
    # availability, terrain resistance, and mechanical wear.  The fields are
    # inert unless the explicit schema is enabled.
    physiology_environment_schema: str = "disabled"
    oxygen_floor: float = 1.0
    oxygen_amplitude: float = 0.0
    oxygen_period: int = 311
    oxygen_wave_x: float = 1.0
    oxygen_wave_y: float = -0.5
    oxygen_phase_offset: float = 0.0
    terrain_floor: float = 0.0
    terrain_amplitude: float = 0.0
    terrain_wave_x: float = 0.5
    terrain_wave_y: float = 1.5
    terrain_phase_offset: float = 0.0
    wear_floor: float = 0.0
    wear_amplitude: float = 0.0
    wear_period: int = 419
    wear_wave_x: float = -1.5
    wear_wave_y: float = 0.75
    wear_phase_offset: float = 0.0


@dataclass(frozen=True)
class EntityConfig:
    relation_slots: int
    maintenance_cost: float
    movement_cost: float
    signal_cost: float
    share_amount: float
    harvest_rate: float
    reproduction_threshold: float
    reproduction_cost: float
    initial_energy: float
    max_energy: float
    max_age: int
    # Capacity contention is a model rule, not an execution optimization.
    # Missing fields retain the historical stable-ID ordering so archived
    # configs remain replayable; bundled current configs opt into the neutral
    # stateless rule explicitly.
    reproduction_capacity_arbitration: str = "stable-id-v1"
    # Existing morphology genes 1..4 are activated only by this explicit
    # schema.  Their normalized total budget prevents an all-positive free
    # advantage and turns resource specialization into a genuine trade-off.
    resource_affinity_schema: str = "disabled"
    resource_affinity_strength: float = 0.0
    resource_affinity_min_efficiency: float = 0.25
    resource_affinity_max_efficiency: float = 1.75
    # Harvest requests historically extract every channel at a fixed rate.
    # The explicit selective schema instead spends the same total extraction
    # budget on one locally available channel chosen through inherited affinity.
    harvest_allocation_schema: str = "uniform-channel-rates-v1"
    # Morphology gene 6 can allocate a fixed evidence budget between direct
    # physical hazard and the delayed mortality trace.  It is inert unless the
    # explicit schema is enabled.
    danger_evidence_schema: str = "disabled"
    danger_evidence_strength: float = 0.0
    danger_evidence_min_efficiency: float = 0.25
    danger_evidence_max_efficiency: float = 1.75
    # Morphology gene 7 can select the spatial scale of the existing resource
    # utility gradient. Disabled configs retain the historical radius-one
    # central difference. Larger radii provide broader but less local spatial
    # information and pay separate structure, use, and development costs.
    resource_sensing_schema: str = "disabled"
    resource_sensing_radius_levels: tuple[int, ...] = (1,)
    resource_sensing_maintenance_energy_per_radius: float = 0.0
    resource_sensing_use_energy_per_radius: float = 0.0
    resource_sensing_development_energy_per_radius: float = 0.0


@dataclass(frozen=True)
class InformationConfig:
    channel_loss: float
    receiver_noise: float
    classification_error: float
    memory_decay: float
    max_signal_delay: int
    direct_message_capacity: int = 16
    source_noise: float = 0.0
    # Field-emission delivery cadence for the current resource/danger/social
    # channels.  A period greater than one is an explicit aggregation delay:
    # events queue until that channel's next flush, while field propagation
    # itself continues at the simulation tick cadence.
    signal_flush_periods: tuple[int, ...] = (1, 1, 1)


@dataclass(frozen=True)
class KnowledgeConfig:
    """Dynamic knowledge-copy settings for K1/K2/K3/K4.

    K3 is separately gated and never changes the meaning of the legacy 128
    inherited linear-policy genes.  K4 is a diagnostic-only candidate-subject
    graph and cannot affect policy or world commits.
    """

    enabled: bool = False
    schema: str = "dynamic-knowledge-k1-v1"
    initial_content_count: int = 0
    initial_holders_fraction: float = 0.0
    holder_capacity_bytes: int = 0
    encoded_bytes_per_copy: int = 64
    maintenance_energy_per_byte: float = 0.0
    transfer_period: int = 1
    transfer_probability: float = 0.0
    attention_slots_per_tick: int = 1
    transfer_base_energy_cost: float = 0.0
    transfer_energy_per_byte: float = 0.0
    receive_energy_per_byte: float = 0.0
    forget_probability: float = 0.0
    capacity_eviction: str = "oldest-copy-v1"
    log_transfer_events: bool = False

    # K2 local consequence learning.  These fields are inert when disabled.
    learning_enabled: bool = False
    outcome_schema: str = "local-outcome-v1"
    experience_creation_enabled: bool = True
    experience_creation_requires_free_capacity: bool = True
    verification_energy_cost: float = 0.0
    confidence_learning_rate: float = 0.25
    confidence_decay_per_tick: float = 0.0
    initial_experience_confidence: float = 0.25
    max_updates_per_outcome: int = 1
    log_outcome_updates: bool = False

    # K3 sparse local-outcome residuals.  All fields are inert unless the
    # separately versioned policy and knowledge schemas are enabled.
    policy_influence_enabled: bool = False
    policy_residual_schema: str = "sparse-local-outcome-residual-v1"
    policy_min_confidence: float = 0.0
    policy_min_local_samples: int = 1
    policy_sample_saturation: float = 4.0
    policy_unverified_transfer_weight: float = 0.25
    policy_outcome_scales: tuple[float, float, float, float, float] = (1.0, 1.0, 1.0, 1.0, 1.0)
    policy_outcome_clip: float = 1.0
    policy_max_abs_logit_residual: float = 1.0
    log_policy_contributions: bool = False

    # High-extensibility latent knowledge.  Variable-length content payloads
    # are routed through separately versioned inherited quantized L1/L2
    # parameters and publish only to the action-logit residual boundary.
    latent_policy_enabled: bool = False
    latent_schema: str = "variable-latent-knowledge-v1"
    latent_router_schema: str = "quantized-linear-latent-router-v1"
    latent_length_levels: tuple[int, ...] = (4, 8, 16, 32)
    # Width of the deterministic latent projection shared by L1 and L2.
    latent_router_hidden_width: int = 8
    # L2-only inherited MLP width.  The activation is an exact integer hard-tanh.
    latent_router_mlp_hidden_width: int = 8
    latent_router_activation_clip: float = 1.0
    latent_value_quantization_scale: int = 4096
    latent_router_weight_quantization_scale: int = 2048
    latent_outcome_injection: float = 0.5
    latent_base_encoded_bytes: int = 32
    latent_bytes_per_value: int = 2
    latent_length_mutation_probability: float = 0.125
    latent_max_abs_logit_residual: float = 1.0

    # Optional physical cost for executing the latent router.  The engine may
    # build a diagnostic plan for any carrier, but only carriers that can pay
    # the deterministic preflight cost publish their residuals to policy.
    routing_cost_enabled: bool = False
    routing_cost_schema: str = "latent-routing-compute-cost-v1"
    routing_budget_mode: str = "all-or-none-per-entity-v1"
    routing_base_energy_cost: float = 0.0
    routing_energy_per_latent_dimension: float = 0.0
    routing_energy_per_mac: float = 0.0
    routing_energy_per_active_hidden_unit: float = 0.0
    routing_energy_per_emitted_action: float = 0.0
    routing_energy_per_saturation: float = 0.0
    routing_energy_per_clipped_output: float = 0.0
    # Dense per-entity audit publication is observational and can be disabled
    # independently of the authoritative cost mechanism and aggregate counters.
    log_routing_costs: bool = True

    # Optional quantized recurrent working memory.  The legacy float32 EMA
    # remains the default when this separately versioned schema is disabled.
    working_memory_enabled: bool = False
    working_memory_schema: str = "quantized-working-memory-v1"
    working_memory_width: int = 4
    working_memory_quantization_scale: int = 4096
    working_memory_activation_clip: float = 1.0
    working_memory_base_energy_cost: float = 0.0
    working_memory_energy_per_dimension: float = 0.0
    working_memory_energy_per_saturation: float = 0.0
    log_working_memory_updates: bool = True

    # Optional sparse Query-Key selection.  Full dynamic knowledge remains in
    # the variable-length SoA; Top-k is an ephemeral per-tick device workset.
    sparse_selection_enabled: bool = False
    sparse_selection_schema: str = "sparse-query-key-topk-router-v1"
    sparse_selection_top_k: int = 4
    # Capacity can remain a fixed config value (legacy semantics) or become an
    # inherited discrete trait.  The levels are ordered capacity/cost options;
    # no category semantics are attached to them.
    sparse_selection_capacity_schema: str = "fixed-config-topk-v1"
    sparse_selection_capacity_levels: tuple[int, ...] = (0, 1, 2, 4, 8)
    sparse_selection_score_clip: int = 1_000_000_000
    sparse_selection_base_energy_cost: float = 0.0
    sparse_selection_energy_per_candidate: float = 0.0
    sparse_selection_energy_per_selected_copy: float = 0.0
    log_sparse_selection_events: bool = True

    # K4 candidate knowledge-subject diagnostics.  This layer is observational
    # and is inert unless explicitly enabled.
    candidate_tracking_enabled: bool = False
    candidate_schema: str = "knowledge-subject-candidate-v1"
    candidate_graph_schema: str = "candidate-subject-graph-v1"
    candidate_update_period: int = 10
    candidate_region_grid_x: int = 8
    candidate_region_grid_y: int = 8


@dataclass(frozen=True)
class DifferentiationConfig:
    """D1 inherited effective capacities over fixed physical maxima."""

    enabled: bool = False
    schema: str = "disabled"
    working_memory_min_dimensions: int = 0
    working_memory_max_dimensions: int = 4
    knowledge_min_bytes: int = 0
    knowledge_max_bytes: int = 512
    knowledge_quantum_bytes: int = 32
    relation_min_slots: int = 0
    relation_max_slots: int = 8
    attention_min_slots: int = 0
    attention_max_slots: int = 4
    mutation_probability: float = 0.02
    mutation_std: float = 0.12
    maintenance_energy_per_working_memory_dimension: float = 0.0
    maintenance_energy_per_knowledge_byte: float = 0.0
    maintenance_energy_per_relation_slot: float = 0.0
    maintenance_energy_per_attention_slot: float = 0.0
    development_energy_per_working_memory_dimension: float = 0.0
    development_energy_per_knowledge_byte: float = 0.0
    development_energy_per_relation_slot: float = 0.0
    development_energy_per_attention_slot: float = 0.0


@dataclass(frozen=True)
class FunctionalModuleConfig:
    """Bounded inherited modules over existing harvest ports.

    The v1 schema is the archived additive D2-A architecture.  The v2 schema
    adds a fixed acyclic signal bus between the same four slots.  The v3 schema
    retains that hierarchy and adds versioned locomotion, field-signal, and
    material-to-integrity repair output primitives.
    """

    enabled: bool = False
    schema: str = "disabled"
    module_count: int = 4
    input_schema: str = "internal-needs-local-resources-v1"
    output_schema: str = "harvest-channel-zero-sum-residual-v1"
    coupling_schema: str = "disabled"
    expression_threshold: float = 0.25
    max_residual_fraction: float = 0.5
    mutation_probability: float = 0.03
    mutation_std: float = 0.16
    maintenance_energy_per_expression: float = 0.0
    development_energy_per_expression: float = 0.0
    maintenance_energy_per_coupling_weight: float = 0.0
    development_energy_per_coupling_weight: float = 0.0
    maintenance_energy_per_embodied_weight: float = 0.0
    development_energy_per_embodied_weight: float = 0.0
    max_movement_speed_fraction: float = 0.0
    max_signal_strength_fraction: float = 0.0
    repair_material_per_tick: float = 0.0
    repair_integrity_per_material: float = 0.0
    repair_energy_per_material: float = 0.0
    maintenance_energy_per_physiology_weight: float = 0.0
    development_energy_per_physiology_weight: float = 0.0


@dataclass(frozen=True)
class PhysiologyConfig:
    """Opt-in lower-level body substrates for versioned functional modules.

    The archived v4 schema exposes four coarse body drives.  The v5 schema
    adds inherited transport/metabolism parameters, fatigue, finite messenger
    precursor, and two decaying regulatory buses.  Functional modules publish
    neural/regulatory drives; actual execution remains limited by body state,
    inherited capacities, environmental supply, and conserved use costs.
    """

    enabled: bool = False
    schema: str = "disabled"
    initial_oxygenation: float = 1.0
    initial_tissue_condition: float = 1.0
    initial_structure_condition: float = 1.0
    oxygen_uptake_per_tick: float = 0.0
    basal_oxygen_use_per_tick: float = 0.0
    movement_oxygen_use_per_tick: float = 0.0
    signal_oxygen_use_per_tick: float = 0.0
    repair_oxygen_use_per_material: float = 0.0
    perfusion_energy_per_tick: float = 0.0
    hypoxia_threshold: float = 0.0
    hypoxia_tissue_damage_per_tick: float = 0.0
    terrain_speed_penalty_fraction: float = 0.0
    terrain_energy_cost_fraction: float = 0.0
    wear_tissue_damage_per_tick: float = 0.0
    wear_structure_damage_per_tick: float = 0.0
    tissue_damage_integrity_fraction: float = 0.0
    structure_damage_integrity_fraction: float = 0.0
    repair_material_per_tick: float = 0.0
    repair_energy_per_material: float = 0.0
    repair_tissue_per_material: float = 0.0
    repair_structure_per_material: float = 0.0
    max_movement_speed_fraction: float = 0.0
    max_signal_strength_fraction: float = 0.0
    oxygen_gradient_weight: float = 0.0

    # v5 bounded regulatory physiology.  These remain inert for the archived
    # oxygen-tissue-structure-v1 schema.
    initial_metabolic_fatigue: float = 0.0
    initial_mobilization_messenger: float = 0.0
    initial_maintenance_messenger: float = 0.0
    initial_messenger_precursor: float = 1.0
    messenger_synthesis_per_tick: float = 0.0
    messenger_decay_per_tick: float = 0.0
    messenger_precursor_use_per_unit: float = 0.0
    messenger_precursor_recovery_per_tick: float = 0.0
    messenger_precursor_material_per_unit: float = 0.0
    messenger_energy_per_unit: float = 0.0
    computation_energy_per_load: float = 0.0
    computation_oxygen_per_load: float = 0.0
    fatigue_gain_per_work: float = 0.0
    fatigue_gain_per_hypoxia: float = 0.0
    fatigue_clearance_per_tick: float = 0.0
    mobilization_speed_gain: float = 0.0
    mobilization_signal_gain: float = 0.0
    mobilization_oxygen_cost_gain: float = 0.0
    maintenance_repair_gain: float = 0.0
    maintenance_clearance_gain: float = 0.0
    maintenance_speed_penalty: float = 0.0
    gene_mutation_probability: float = 0.0
    gene_mutation_std: float = 0.0
    maintenance_energy_per_capacity: float = 0.0
    development_energy_per_capacity: float = 0.0

    # v6 resource buffering and delayed conversion. These arrays remain inert
    # unless the explicit resource-metabolism physiology schema is selected.
    resource_store_base_capacity: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    resource_conversion_per_tick: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    resource_store_decay_per_tick: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    # D3-E per-unit execution cost for actual raw-store conversion.  The cost
    # is charged before body outcomes are realized and is preserved by the
    # spatial-support ablation.
    resource_processing_energy_per_unit: tuple[float, float, float, float] = (
        0.0, 0.0, 0.0, 0.0
    )


@dataclass(frozen=True)
class PolicyConfig:
    temperature: float
    partner_samples: int
    mutation_std: float
    # Per-gene mutation incidence.  Mutation magnitude is conditional on this
    # gate; separating incidence from magnitude prevents a 128-gene strategy
    # from receiving 128 independent perturbations at every birth.
    mutation_probability: float = 0.01
    schema: str = "inherited-linear-policy-v1"


@dataclass(frozen=True)
class SocialConfig:
    group_update_period: int
    trust_group_threshold: float
    group_min_members: int
    relation_decay: float
    trust_gain_share: float
    trust_loss_failed: float
    # Legacy configs keep fixed periodic recomputation.  The adaptive schema
    # refreshes only after a topology-relevant relation change, a predicted
    # trust-threshold decay crossing, or a bounded maximum staleness interval.
    group_update_mode: str = "periodic-v1"
    group_update_min_period: int = 1
    group_update_max_period: int = 0
    # Candidate-group labels are a measurement rule, not an ontological fact.
    group_label_schema: str = "trusted-directed-fixed-round-min-label-v1"
    group_label_propagation_rounds: int = 8


@dataclass(frozen=True)
class ControlConfig:
    """Entertainment controller settings; all heuristic behaviour is opt-in."""

    heuristic_social_guidance: bool = False
    heuristic_social_guidance_weight: float = 0.25
    # The recovery intervention deterministically selects this fraction of
    # the living cohort.  It only affects the entertainment-only
    # ``independent-foraging-override`` action-replacement intervention.
    autonomy_recovery_fraction: float = 0.25
    autonomy_activation_energy_fraction: float = 0.35
    autonomy_harvest_threshold: float = 0.05


@dataclass(frozen=True)
class SimulationConfig:
    run: RunConfig
    world: WorldConfig
    environment: EnvironmentConfig
    entities: EntityConfig
    information: InformationConfig
    knowledge: KnowledgeConfig
    differentiation: DifferentiationConfig
    functional_modules: FunctionalModuleConfig
    physiology: PhysiologyConfig
    policy: PolicyConfig
    social: SocialConfig
    control: ControlConfig

    @property
    def cell_width(self) -> float:
        return self.world.width / self.world.grid_x

    @property
    def cell_height(self) -> float:
        return self.world.height / self.world.grid_y


def _require(mapping: dict[str, Any], key: str) -> Any:
    if key not in mapping:
        raise ValueError(f"Missing configuration section: {key}")
    return mapping[key]


def _probability(name: str, value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")
    return value


def load_config(path: str | Path) -> SimulationConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    information_raw = _require(raw, "information")
    policy_raw = dict(_require(raw, "policy"))
    # Accepted for old run files, but no longer used: action preferences are
    # inherited genome data rather than a global hand-authored group weight.
    policy_raw.pop("group_influence", None)
    cfg = SimulationConfig(
        run=RunConfig(
            **{
                **_require(raw, "run"),
                "trajectory_subject_ids": tuple(_require(raw, "run").get("trajectory_subject_ids", ())),
                "gpu_harvest_conflict_planner": _require(raw, "run").get(
                    "gpu_harvest_conflict_planner", True
                ),
                "checkpoint_ticks": tuple(
                    int(value) for value in _require(raw, "run").get("checkpoint_ticks", ())
                ),
                "environment_atlas_scales": tuple(
                    tuple(int(value) for value in scale)
                    for scale in _require(raw, "run").get(
                        "environment_atlas_scales", ()
                    )
                ),
            }
        ),
        world=WorldConfig(**_require(raw, "world")),
        environment=EnvironmentConfig(
            resource_regeneration=tuple(_require(raw, "environment")["resource_regeneration"]),
            resource_capacity=tuple(_require(raw, "environment")["resource_capacity"]),
            season_period=_require(raw, "environment")["season_period"],
            season_amplitude=_require(raw, "environment")["season_amplitude"],
            signal_decay=_require(raw, "environment")["signal_decay"],
            signal_diffusion=_require(raw, "environment")["signal_diffusion"],
            schema=_require(raw, "environment").get(
                "schema", "legacy-four-channel-v1"
            ),
            resource_temporal_phase_offsets=tuple(
                _require(raw, "environment").get(
                    "resource_temporal_phase_offsets", (0.0, 1.3, 2.6, 3.9)
                )
            ),
            resource_spatial_phase_x=tuple(
                _require(raw, "environment").get(
                    "resource_spatial_phase_x", (0.0, 0.0, 0.0, 0.0)
                )
            ),
            resource_spatial_phase_y=tuple(
                _require(raw, "environment").get(
                    "resource_spatial_phase_y", (0.0, 0.0, 0.0, 0.0)
                )
            ),
            resource_cycle_periods=tuple(
                int(value)
                for value in _require(raw, "environment").get(
                    "resource_cycle_periods", (120, 173, 229, 307)
                )
            ),
            resource_cycle_amplitudes=tuple(
                float(value)
                for value in _require(raw, "environment").get(
                    "resource_cycle_amplitudes", (0.55, 0.50, 0.45, 0.40)
                )
            ),
            resource_primary_wave_vectors=tuple(
                tuple(float(component) for component in vector)
                for vector in _require(raw, "environment").get(
                    "resource_primary_wave_vectors",
                    ((1.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, -1.0)),
                )
            ),
            resource_secondary_wave_vectors=tuple(
                tuple(float(component) for component in vector)
                for vector in _require(raw, "environment").get(
                    "resource_secondary_wave_vectors",
                    ((2.0, 1.0), (1.0, 2.0), (2.0, -1.0), (1.0, -2.0)),
                )
            ),
            resource_primary_wave_amplitudes=tuple(
                float(value)
                for value in _require(raw, "environment").get(
                    "resource_primary_wave_amplitudes", (0.24, 0.22, 0.20, 0.18)
                )
            ),
            resource_secondary_wave_amplitudes=tuple(
                float(value)
                for value in _require(raw, "environment").get(
                    "resource_secondary_wave_amplitudes", (0.14, 0.13, 0.12, 0.11)
                )
            ),
            resource_diffusion_rates=tuple(
                float(value)
                for value in _require(raw, "environment").get(
                    "resource_diffusion_rates", (0.002, 0.006, 0.012, 0.020)
                )
            ),
            resource_processing_schema=str(
                _require(raw, "environment").get(
                    "resource_processing_schema", "disabled"
                )
            ),
            resource_processing_support_amplitude=float(
                _require(raw, "environment").get(
                    "resource_processing_support_amplitude", 0.0
                )
            ),
            harvest_channel_multipliers=tuple(
                _require(raw, "environment").get(
                    "harvest_channel_multipliers", (1.0, 0.45, 0.25, 0.18)
                )
            ),
            resource_effect_matrix=tuple(
                tuple(row)
                for row in _require(raw, "environment").get(
                    "resource_effect_matrix",
                    (
                        (1.0, 0.0, 0.0, 0.0, 0.0),
                        (0.0, 0.05, 0.0, 0.0, 0.0),
                        (0.0, 0.0, 0.0, 1.0, 0.0),
                        (0.0, 0.0, 0.0, 0.0, 1.0),
                    ),
                )
            ),
            hazard_spatial_phase_x=float(
                _require(raw, "environment").get("hazard_spatial_phase_x", 0.0)
            ),
            hazard_spatial_phase_y=float(
                _require(raw, "environment").get("hazard_spatial_phase_y", 0.0)
            ),
            hazard_temporal_multiplier=float(
                _require(raw, "environment").get("hazard_temporal_multiplier", 1.0)
            ),
            hazard_secondary_amplitude=float(
                _require(raw, "environment").get("hazard_secondary_amplitude", 0.0)
            ),
            mortality_trace_schema=str(
                _require(raw, "environment").get("mortality_trace_schema", "disabled")
            ),
            mortality_trace_decay=float(
                _require(raw, "environment").get("mortality_trace_decay", 0.0)
            ),
            mortality_trace_diffusion=float(
                _require(raw, "environment").get("mortality_trace_diffusion", 0.0)
            ),
            mortality_trace_deposit=float(
                _require(raw, "environment").get("mortality_trace_deposit", 0.0)
            ),
            mortality_trace_max=float(
                _require(raw, "environment").get("mortality_trace_max", 1.0)
            ),
            mortality_trace_observation_weight=float(
                _require(raw, "environment").get(
                    "mortality_trace_observation_weight", 0.0
                )
            ),
            environment_process_schema=str(
                _require(raw, "environment").get(
                    "environment_process_schema", "disabled"
                )
            ),
            environment_process_parameters=dict(
                _require(raw, "environment").get(
                    "environment_process_parameters", {}
                )
            ),
            moving_hazard_schema=str(
                _require(raw, "environment").get("moving_hazard_schema", "disabled")
            ),
            moving_hazard_source_count=int(
                _require(raw, "environment").get("moving_hazard_source_count", 0)
            ),
            moving_hazard_amplitude=float(
                _require(raw, "environment").get("moving_hazard_amplitude", 0.0)
            ),
            moving_hazard_radius=float(
                _require(raw, "environment").get("moving_hazard_radius", 0.12)
            ),
            moving_hazard_speed=float(
                _require(raw, "environment").get("moving_hazard_speed", 0.0)
            ),
            moving_hazard_phase_offset=float(
                _require(raw, "environment").get("moving_hazard_phase_offset", 0.0)
            ),
            physiology_environment_schema=str(
                _require(raw, "environment").get(
                    "physiology_environment_schema", "disabled"
                )
            ),
            oxygen_floor=float(
                _require(raw, "environment").get("oxygen_floor", 1.0)
            ),
            oxygen_amplitude=float(
                _require(raw, "environment").get("oxygen_amplitude", 0.0)
            ),
            oxygen_period=int(
                _require(raw, "environment").get("oxygen_period", 311)
            ),
            oxygen_wave_x=float(
                _require(raw, "environment").get("oxygen_wave_x", 1.0)
            ),
            oxygen_wave_y=float(
                _require(raw, "environment").get("oxygen_wave_y", -0.5)
            ),
            oxygen_phase_offset=float(
                _require(raw, "environment").get("oxygen_phase_offset", 0.0)
            ),
            terrain_floor=float(
                _require(raw, "environment").get("terrain_floor", 0.0)
            ),
            terrain_amplitude=float(
                _require(raw, "environment").get("terrain_amplitude", 0.0)
            ),
            terrain_wave_x=float(
                _require(raw, "environment").get("terrain_wave_x", 0.5)
            ),
            terrain_wave_y=float(
                _require(raw, "environment").get("terrain_wave_y", 1.5)
            ),
            terrain_phase_offset=float(
                _require(raw, "environment").get("terrain_phase_offset", 0.0)
            ),
            wear_floor=float(
                _require(raw, "environment").get("wear_floor", 0.0)
            ),
            wear_amplitude=float(
                _require(raw, "environment").get("wear_amplitude", 0.0)
            ),
            wear_period=int(
                _require(raw, "environment").get("wear_period", 419)
            ),
            wear_wave_x=float(
                _require(raw, "environment").get("wear_wave_x", -1.5)
            ),
            wear_wave_y=float(
                _require(raw, "environment").get("wear_wave_y", 0.75)
            ),
            wear_phase_offset=float(
                _require(raw, "environment").get("wear_phase_offset", 0.0)
            ),
        ),
        entities=EntityConfig(
            **{
                **_require(raw, "entities"),
                "resource_sensing_radius_levels": tuple(
                    int(value)
                    for value in _require(raw, "entities").get(
                        "resource_sensing_radius_levels", (1,)
                    )
                ),
            }
        ),
        information=InformationConfig(
            **{
                **information_raw,
                "signal_flush_periods": tuple(information_raw.get("signal_flush_periods", (1, 1, 1))),
            }
        ),
        knowledge=KnowledgeConfig(
            **{
                **raw.get("knowledge", {}),
                "policy_outcome_scales": tuple(
                    raw.get("knowledge", {}).get(
                        "policy_outcome_scales", (1.0, 1.0, 1.0, 1.0, 1.0)
                    )
                ),
                "latent_length_levels": tuple(
                    raw.get("knowledge", {}).get(
                        "latent_length_levels", (4, 8, 16, 32)
                    )
                ),
                "sparse_selection_capacity_levels": tuple(
                    raw.get("knowledge", {}).get(
                        "sparse_selection_capacity_levels", (0, 1, 2, 4, 8)
                    )
                ),
            }
        ),
        differentiation=DifferentiationConfig(**raw.get("differentiation", {})),
        functional_modules=FunctionalModuleConfig(**raw.get("functional_modules", {})),
        physiology=PhysiologyConfig(
            **{
                **raw.get("physiology", {}),
                "resource_store_base_capacity": tuple(
                    raw.get("physiology", {}).get(
                        "resource_store_base_capacity", (0.0, 0.0, 0.0, 0.0)
                    )
                ),
                "resource_conversion_per_tick": tuple(
                    raw.get("physiology", {}).get(
                        "resource_conversion_per_tick", (0.0, 0.0, 0.0, 0.0)
                    )
                ),
                "resource_store_decay_per_tick": tuple(
                    raw.get("physiology", {}).get(
                        "resource_store_decay_per_tick", (0.0, 0.0, 0.0, 0.0)
                    )
                ),
                "resource_processing_energy_per_unit": tuple(
                    raw.get("physiology", {}).get(
                        "resource_processing_energy_per_unit",
                        (0.0, 0.0, 0.0, 0.0),
                    )
                ),
            }
        ),
        policy=PolicyConfig(**policy_raw),
        social=SocialConfig(**_require(raw, "social")),
        control=ControlConfig(**raw.get("control", {})),
    )
    validate_config(cfg)
    return cfg


def validate_config(cfg: SimulationConfig) -> None:
    if cfg.world.initial_entities <= 0:
        raise ValueError("initial_entities must be positive")
    if cfg.world.max_entities < cfg.world.initial_entities:
        raise ValueError("max_entities must be >= initial_entities")
    if cfg.world.grid_x <= 0 or cfg.world.grid_y <= 0:
        raise ValueError("grid dimensions must be positive")
    sensing_schema = cfg.entities.resource_sensing_schema
    if sensing_schema not in {
        "disabled",
        "inherited-discrete-gradient-radius-v1",
        "inherited-affinity-routed-gradient-radius-v2",
        "inherited-affinity-budgeted-gradient-radius-v3",
    }:
        raise ValueError(
            "entities.resource_sensing_schema must be 'disabled', "
            "'inherited-discrete-gradient-radius-v1', "
            "'inherited-affinity-routed-gradient-radius-v2', or "
            "'inherited-affinity-budgeted-gradient-radius-v3'"
        )
    sensing_levels = tuple(int(value) for value in cfg.entities.resource_sensing_radius_levels)
    if not sensing_levels or any(value <= 0 for value in sensing_levels):
        raise ValueError("resource sensing radius levels must be positive")
    if tuple(sorted(set(sensing_levels))) != sensing_levels:
        raise ValueError("resource sensing radius levels must be strictly increasing")
    max_periodic_radius = min(cfg.world.grid_x, cfg.world.grid_y) // 2
    if max(sensing_levels) > max_periodic_radius:
        raise ValueError("resource sensing radius exceeds half the smallest grid dimension")
    sensing_costs = (
        cfg.entities.resource_sensing_maintenance_energy_per_radius,
        cfg.entities.resource_sensing_use_energy_per_radius,
        cfg.entities.resource_sensing_development_energy_per_radius,
    )
    if any(not math.isfinite(value) or value < 0.0 for value in sensing_costs):
        raise ValueError("resource sensing costs must be finite and non-negative")
    if sensing_schema == "disabled":
        if sensing_levels != (1,) or any(value != 0.0 for value in sensing_costs):
            raise ValueError(
                "disabled resource sensing requires radius level (1,) and zero costs"
            )
    elif not all(value > 0.0 for value in sensing_costs):
        raise ValueError(
            "inherited resource sensing requires positive maintenance, use, and development costs"
        )
    if (
        sensing_schema in {
            "inherited-affinity-routed-gradient-radius-v2",
            "inherited-affinity-budgeted-gradient-radius-v3",
        }
        and cfg.entities.resource_affinity_schema
        != "normalized-four-resource-affinity-v1"
    ):
        raise ValueError(
            "channel-routed resource sensing requires normalized four-resource affinity"
        )
    if (
        not math.isfinite(cfg.world.width)
        or not math.isfinite(cfg.world.height)
        or cfg.world.width <= 0.0
        or cfg.world.height <= 0.0
    ):
        raise ValueError("world width and height must be finite and positive")
    if cfg.run.ticks <= 0:
        raise ValueError("ticks must be positive")
    if any(int(value) < 0 for value in cfg.run.checkpoint_ticks):
        raise ValueError("run.checkpoint_ticks must be non-negative")
    if tuple(sorted(set(int(value) for value in cfg.run.checkpoint_ticks))) != tuple(
        int(value) for value in cfg.run.checkpoint_ticks
    ):
        raise ValueError("run.checkpoint_ticks must be sorted and unique")
    if not isinstance(cfg.run.gpu_harvest_conflict_planner, bool):
        raise ValueError("run.gpu_harvest_conflict_planner must be a boolean")
    if cfg.run.experiment_mode not in {"scientific", "entertainment"}:
        raise ValueError("run.experiment_mode must be 'scientific' or 'entertainment'")
    if cfg.run.evolution_evaluation_period <= 0:
        raise ValueError("run.evolution_evaluation_period must be positive")
    if cfg.run.long_run_diagnostics_schema not in {
        "disabled",
        "long-run-evolution-diagnostics-v1",
    }:
        raise ValueError(
            "run.long_run_diagnostics_schema must be 'disabled' or "
            "'long-run-evolution-diagnostics-v1'"
        )
    if cfg.run.long_run_diagnostics_enabled != (
        cfg.run.long_run_diagnostics_schema == "long-run-evolution-diagnostics-v1"
    ):
        raise ValueError(
            "long-run diagnostics enabled/schema fields must agree"
        )
    if cfg.run.spatial_stress_diagnostics_schema not in {
        "disabled",
        "spatial-local-stress-diagnostics-v1",
        "spatial-local-stress-culture-diagnostics-v2",
    }:
        raise ValueError(
            "run.spatial_stress_diagnostics_schema must be 'disabled' or "
            "'spatial-local-stress-diagnostics-v1' or 'spatial-local-stress-culture-diagnostics-v2'"
        )
    if cfg.run.spatial_stress_diagnostics_enabled != (
        cfg.run.spatial_stress_diagnostics_schema
        in {
            "spatial-local-stress-diagnostics-v1",
            "spatial-local-stress-culture-diagnostics-v2",
        }
    ):
        raise ValueError(
            "spatial stress diagnostics enabled/schema fields must agree"
        )
    if cfg.run.spatial_stress_regions_x <= 0 or cfg.run.spatial_stress_regions_y <= 0:
        raise ValueError("spatial stress diagnostic region dimensions must be positive")
    if cfg.run.spatial_stress_region_schema != "normalized-fixed-count-grid-v1":
        raise ValueError(
            "run.spatial_stress_region_schema must be "
            "'normalized-fixed-count-grid-v1'"
        )
    if (
        cfg.run.spatial_stress_regions_x > cfg.world.grid_x
        or cfg.run.spatial_stress_regions_y > cfg.world.grid_y
    ):
        raise ValueError(
            "spatial stress diagnostic grid cannot exceed the physical world grid"
        )
    if cfg.run.subject_structure_diagnostics_schema not in {
        "disabled",
        "stable-membership-subject-succession-v1",
    }:
        raise ValueError(
            "run.subject_structure_diagnostics_schema must be 'disabled' or "
            "'stable-membership-subject-succession-v1'"
        )
    if cfg.run.subject_structure_diagnostics_enabled != (
        cfg.run.subject_structure_diagnostics_schema
        == "stable-membership-subject-succession-v1"
    ):
        raise ValueError(
            "subject structure diagnostics enabled/schema fields must agree"
        )
    if cfg.run.environment_atlas_diagnostics_schema not in {
        "disabled",
        "multiscale-subject-environment-atlas-v1",
        "multiscale-subject-environment-atlas-v2",
    }:
        raise ValueError(
            "run.environment_atlas_diagnostics_schema must be 'disabled', "
            "'multiscale-subject-environment-atlas-v1', or "
            "'multiscale-subject-environment-atlas-v2'"
        )
    if cfg.run.environment_atlas_diagnostics_enabled != (
        cfg.run.environment_atlas_diagnostics_schema
        in {
            "multiscale-subject-environment-atlas-v1",
            "multiscale-subject-environment-atlas-v2",
        }
    ):
        raise ValueError(
            "environment atlas diagnostics enabled/schema fields must agree"
        )
    if cfg.run.environment_atlas_diagnostics_enabled and not cfg.run.environment_atlas_scales:
        raise ValueError(
            "enabled environment atlas diagnostics require at least one scale"
        )
    seen_atlas_scales: set[tuple[int, int]] = set()
    for scale in cfg.run.environment_atlas_scales:
        if len(scale) != 2:
            raise ValueError("each environment atlas scale must contain [x, y]")
        regions_x, regions_y = (int(scale[0]), int(scale[1]))
        if regions_x <= 0 or regions_y <= 0:
            raise ValueError("environment atlas scale dimensions must be positive")
        if regions_x > cfg.world.grid_x or regions_y > cfg.world.grid_y:
            raise ValueError(
                "environment atlas scales cannot exceed the physical world grid"
            )
        normalized_scale = (regions_x, regions_y)
        if normalized_scale in seen_atlas_scales:
            raise ValueError("environment atlas scales must be unique")
        seen_atlas_scales.add(normalized_scale)
    if not cfg.run.environment_atlas_diagnostics_enabled and cfg.run.environment_atlas_scales:
        raise ValueError(
            "disabled environment atlas diagnostics require an empty scale list"
        )
    if not isinstance(cfg.run.full_checkpoint_enabled, bool):
        raise ValueError("run.full_checkpoint_enabled must be a boolean")
    if not isinstance(cfg.run.validation_mode, bool):
        raise ValueError("run.validation_mode must be a boolean")
    if cfg.run.gpu_semantics_mode not in {"strict-reference", "hybrid-accelerated"}:
        raise ValueError(
            "run.gpu_semantics_mode must be one of: "
            "'strict-reference', 'hybrid-accelerated'"
        )
    if cfg.run.gpu_memory_pool_policy not in {
        "bounded-cache-v1",
        "unbounded-default-v1",
    }:
        raise ValueError(
            "run.gpu_memory_pool_policy must be one of: "
            "'bounded-cache-v1', 'unbounded-default-v1'"
        )
    if (
        not isinstance(cfg.run.gpu_memory_pool_cache_limit_bytes, int)
        or isinstance(cfg.run.gpu_memory_pool_cache_limit_bytes, bool)
        or cfg.run.gpu_memory_pool_cache_limit_bytes < 0
    ):
        raise ValueError(
            "run.gpu_memory_pool_cache_limit_bytes must be a non-negative integer"
        )
    if (
        not isinstance(cfg.run.gpu_memory_pool_trim_period, int)
        or isinstance(cfg.run.gpu_memory_pool_trim_period, bool)
        or cfg.run.gpu_memory_pool_trim_period <= 0
    ):
        raise ValueError(
            "run.gpu_memory_pool_trim_period must be a positive integer"
        )
    if len(cfg.environment.resource_regeneration) != 4 or len(cfg.environment.resource_capacity) != 4:
        raise ValueError("MVP requires exactly four resource channels")
    if any(v < 0 for v in cfg.environment.resource_regeneration):
        raise ValueError("resource regeneration cannot be negative")
    if any(v <= 0 for v in cfg.environment.resource_capacity):
        raise ValueError("resource capacities must be positive")
    if cfg.environment.schema not in {
        "legacy-four-channel-v1",
        "spatially-asynchronous-multiniche-v1",
        "orthogonal-four-resource-niche-v1",
        "orthogonal-four-resource-renewal-v2",
        "persistent-multiscale-four-resource-renewal-v3",
    }:
        raise ValueError(
            "environment.schema must be 'legacy-four-channel-v1', "
            "'spatially-asynchronous-multiniche-v1', or "
            "'orthogonal-four-resource-niche-v1', or "
            "'orthogonal-four-resource-renewal-v2', or "
            "'persistent-multiscale-four-resource-renewal-v3'"
        )
    for name, values in (
        ("resource_temporal_phase_offsets", cfg.environment.resource_temporal_phase_offsets),
        ("resource_spatial_phase_x", cfg.environment.resource_spatial_phase_x),
        ("resource_spatial_phase_y", cfg.environment.resource_spatial_phase_y),
        ("harvest_channel_multipliers", cfg.environment.harvest_channel_multipliers),
    ):
        if len(values) != 4 or any(not math.isfinite(float(value)) for value in values):
            raise ValueError(f"environment.{name} must contain four finite values")
    if any(value < 0.0 for value in cfg.environment.harvest_channel_multipliers):
        raise ValueError("environment.harvest_channel_multipliers cannot be negative")
    for name, values in (
        ("resource_cycle_periods", cfg.environment.resource_cycle_periods),
        ("resource_cycle_amplitudes", cfg.environment.resource_cycle_amplitudes),
        (
            "resource_primary_wave_amplitudes",
            cfg.environment.resource_primary_wave_amplitudes,
        ),
        (
            "resource_secondary_wave_amplitudes",
            cfg.environment.resource_secondary_wave_amplitudes,
        ),
        ("resource_diffusion_rates", cfg.environment.resource_diffusion_rates),
    ):
        if len(values) != 4 or any(not math.isfinite(float(value)) for value in values):
            raise ValueError(f"environment.{name} must contain four finite values")
    for name, vectors in (
        ("resource_primary_wave_vectors", cfg.environment.resource_primary_wave_vectors),
        ("resource_secondary_wave_vectors", cfg.environment.resource_secondary_wave_vectors),
    ):
        if len(vectors) != 4 or any(
            len(vector) != 2
            or any(not math.isfinite(float(component)) for component in vector)
            for vector in vectors
        ):
            raise ValueError(f"environment.{name} must be shaped [4, 2] with finite values")
    if cfg.environment.schema in {
        "orthogonal-four-resource-niche-v1",
        "orthogonal-four-resource-renewal-v2",
        "persistent-multiscale-four-resource-renewal-v3",
    }:
        if any(int(value) <= 0 for value in cfg.environment.resource_cycle_periods):
            raise ValueError("orthogonal resource cycle periods must be positive")
        if any(
            value < 0.0 or value >= 1.0
            for value in cfg.environment.resource_cycle_amplitudes
        ):
            raise ValueError("orthogonal resource cycle amplitudes must be in [0, 1)")
        if any(
            value < 0.0 or value > 0.45
            for value in cfg.environment.resource_primary_wave_amplitudes
        ) or any(
            value < 0.0 or value > 0.45
            for value in cfg.environment.resource_secondary_wave_amplitudes
        ):
            raise ValueError("orthogonal resource wave amplitudes must be in [0, 0.45]")
        if any(
            primary + secondary > 0.45 + 1e-12
            for primary, secondary in zip(
                cfg.environment.resource_primary_wave_amplitudes,
                cfg.environment.resource_secondary_wave_amplitudes,
                strict=True,
            )
        ):
            raise ValueError("orthogonal resource wave amplitude sums cannot exceed 0.45")
        if any(
            value < 0.0 or value > 0.25
            for value in cfg.environment.resource_diffusion_rates
        ):
            raise ValueError("orthogonal resource diffusion rates must be in [0, 0.25]")
        primary_vectors = tuple(
            (float(vector[0]), float(vector[1]))
            for vector in cfg.environment.resource_primary_wave_vectors
        )
        if len(set(primary_vectors)) != 4 or any(
            abs(x) + abs(y) <= 1e-12 for x, y in primary_vectors
        ):
            raise ValueError(
                "orthogonal resource primary wave vectors must be four distinct non-zero modes"
            )
        if cfg.environment.schema == "persistent-multiscale-four-resource-renewal-v3":
            primary_scale_keys = {
                round(float(x) * float(x) + float(y) * float(y), 12)
                for x, y in primary_vectors
            }
            if len(primary_scale_keys) != 4:
                raise ValueError(
                    "multiscale resource renewal requires four distinct primary spatial scales"
                )
            secondary_vectors = tuple(
                (float(vector[0]), float(vector[1]))
                for vector in cfg.environment.resource_secondary_wave_vectors
            )
            if any(abs(x) + abs(y) <= 1e-12 for x, y in secondary_vectors):
                raise ValueError(
                    "multiscale resource secondary wave vectors must be non-zero"
                )
    if cfg.environment.resource_processing_schema not in {
        "disabled",
        "phase-shifted-channel-processing-support-v1",
    }:
        raise ValueError(
            "environment.resource_processing_schema must be 'disabled' or "
            "'phase-shifted-channel-processing-support-v1'"
        )
    processing_amplitude = float(
        cfg.environment.resource_processing_support_amplitude
    )
    if not math.isfinite(processing_amplitude) or not 0.0 <= processing_amplitude < 1.0:
        raise ValueError(
            "environment.resource_processing_support_amplitude must be in [0, 1)"
        )
    if cfg.environment.resource_processing_schema == "disabled":
        if processing_amplitude != 0.0:
            raise ValueError(
                "disabled resource processing support requires zero amplitude"
            )
    elif (
        cfg.environment.schema not in {
            "orthogonal-four-resource-renewal-v2",
            "persistent-multiscale-four-resource-renewal-v3",
        }
        or processing_amplitude <= 0.0
    ):
        raise ValueError(
            "phase-shifted processing support requires persistent orthogonal renewal "
            "and positive amplitude"
        )
    if len(cfg.environment.resource_effect_matrix) != 4 or any(
        len(row) != 5 for row in cfg.environment.resource_effect_matrix
    ):
        raise ValueError("environment.resource_effect_matrix must be shaped [4, 5]")
    if any(
        not math.isfinite(float(value)) or value < 0.0
        for row in cfg.environment.resource_effect_matrix
        for value in row
    ):
        raise ValueError("environment.resource_effect_matrix must be finite and non-negative")
    for name, value in (
        ("hazard_spatial_phase_x", cfg.environment.hazard_spatial_phase_x),
        ("hazard_spatial_phase_y", cfg.environment.hazard_spatial_phase_y),
        ("hazard_temporal_multiplier", cfg.environment.hazard_temporal_multiplier),
        ("hazard_secondary_amplitude", cfg.environment.hazard_secondary_amplitude),
    ):
        if not math.isfinite(float(value)):
            raise ValueError(f"environment.{name} must be finite")
    if cfg.environment.hazard_temporal_multiplier <= 0.0:
        raise ValueError("environment.hazard_temporal_multiplier must be positive")
    if not 0.0 <= cfg.environment.hazard_secondary_amplitude <= 0.5:
        raise ValueError("environment.hazard_secondary_amplitude must be in [0, 0.5]")
    if cfg.environment.mortality_trace_schema not in {
        "disabled",
        "local-decaying-mortality-trace-v1",
    }:
        raise ValueError(
            "environment.mortality_trace_schema must be 'disabled' or "
            "'local-decaying-mortality-trace-v1'"
        )
    for name, value in (
        ("mortality_trace_decay", cfg.environment.mortality_trace_decay),
        ("mortality_trace_diffusion", cfg.environment.mortality_trace_diffusion),
        ("mortality_trace_deposit", cfg.environment.mortality_trace_deposit),
        ("mortality_trace_max", cfg.environment.mortality_trace_max),
        (
            "mortality_trace_observation_weight",
            cfg.environment.mortality_trace_observation_weight,
        ),
    ):
        if not math.isfinite(float(value)):
            raise ValueError(f"environment.{name} must be finite")
    if not 0.0 <= cfg.environment.mortality_trace_decay <= 1.0:
        raise ValueError("environment.mortality_trace_decay must be in [0, 1]")
    if not 0.0 <= cfg.environment.mortality_trace_diffusion <= 0.25:
        raise ValueError("environment.mortality_trace_diffusion must be in [0, 0.25]")
    if cfg.environment.mortality_trace_deposit < 0.0:
        raise ValueError("environment.mortality_trace_deposit cannot be negative")
    if cfg.environment.mortality_trace_max <= 0.0:
        raise ValueError("environment.mortality_trace_max must be positive")
    if cfg.environment.mortality_trace_observation_weight < 0.0:
        raise ValueError(
            "environment.mortality_trace_observation_weight cannot be negative"
        )
    if cfg.environment.physiology_environment_schema not in {
        "disabled",
        "oxygen-terrain-wear-mosaic-v1",
    }:
        raise ValueError(
            "environment.physiology_environment_schema must be 'disabled' or "
            "'oxygen-terrain-wear-mosaic-v1'"
        )
    physiology_environment_values = (
        cfg.environment.oxygen_floor,
        cfg.environment.oxygen_amplitude,
        cfg.environment.oxygen_wave_x,
        cfg.environment.oxygen_wave_y,
        cfg.environment.oxygen_phase_offset,
        cfg.environment.terrain_floor,
        cfg.environment.terrain_amplitude,
        cfg.environment.terrain_wave_x,
        cfg.environment.terrain_wave_y,
        cfg.environment.terrain_phase_offset,
        cfg.environment.wear_floor,
        cfg.environment.wear_amplitude,
        cfg.environment.wear_wave_x,
        cfg.environment.wear_wave_y,
        cfg.environment.wear_phase_offset,
    )
    if any(not math.isfinite(float(value)) for value in physiology_environment_values):
        raise ValueError("physiological environment fields must be finite")
    if cfg.environment.oxygen_period <= 0 or cfg.environment.wear_period <= 0:
        raise ValueError("physiological environment periods must be positive")
    for name, floor, amplitude in (
        ("oxygen", cfg.environment.oxygen_floor, cfg.environment.oxygen_amplitude),
        ("terrain", cfg.environment.terrain_floor, cfg.environment.terrain_amplitude),
        ("wear", cfg.environment.wear_floor, cfg.environment.wear_amplitude),
    ):
        if floor < 0.0 or floor > 1.0 or amplitude < 0.0 or amplitude > 1.0:
            raise ValueError(
                f"environment {name} floor/amplitude must each be in [0, 1]"
            )
        if floor + amplitude > 1.0 + 1.0e-12:
            raise ValueError(
                f"environment {name} floor plus amplitude cannot exceed 1"
            )
    if (
        cfg.environment.physiology_environment_schema == "disabled"
        and (
            cfg.environment.oxygen_floor != 1.0
            or cfg.environment.oxygen_amplitude != 0.0
            or cfg.environment.terrain_floor != 0.0
            or cfg.environment.terrain_amplitude != 0.0
            or cfg.environment.wear_floor != 0.0
            or cfg.environment.wear_amplitude != 0.0
        )
    ):
        raise ValueError(
            "disabled physiological environment requires neutral oxygen/terrain/wear fields"
        )
    if (
        cfg.environment.mortality_trace_schema != "disabled"
        and (
            cfg.environment.mortality_trace_deposit <= 0.0
            or cfg.environment.mortality_trace_observation_weight <= 0.0
        )
    ):
        raise ValueError(
            "enabled mortality trace requires positive deposit and observation weight"
        )
    if cfg.environment.moving_hazard_schema not in {
        "disabled",
        "moving-gaussian-hazard-sources-v1",
    }:
        raise ValueError(
            "environment.moving_hazard_schema must be 'disabled' or "
            "'moving-gaussian-hazard-sources-v1'"
        )
    if cfg.environment.moving_hazard_source_count < 0:
        raise ValueError("environment.moving_hazard_source_count cannot be negative")
    for name, value in (
        ("moving_hazard_amplitude", cfg.environment.moving_hazard_amplitude),
        ("moving_hazard_radius", cfg.environment.moving_hazard_radius),
        ("moving_hazard_speed", cfg.environment.moving_hazard_speed),
        ("moving_hazard_phase_offset", cfg.environment.moving_hazard_phase_offset),
    ):
        if not math.isfinite(float(value)):
            raise ValueError(f"environment.{name} must be finite")
    if cfg.environment.moving_hazard_amplitude < 0.0:
        raise ValueError("environment.moving_hazard_amplitude cannot be negative")
    if cfg.environment.moving_hazard_radius <= 0.0 or cfg.environment.moving_hazard_radius > 0.5:
        raise ValueError("environment.moving_hazard_radius must be in (0, 0.5]")
    if cfg.environment.moving_hazard_speed < 0.0:
        raise ValueError("environment.moving_hazard_speed cannot be negative")
    if cfg.environment.moving_hazard_schema != "disabled" and (
        cfg.environment.moving_hazard_source_count <= 0
        or cfg.environment.moving_hazard_amplitude <= 0.0
    ):
        raise ValueError(
            "enabled moving hazards require positive source count and amplitude"
        )
    # Generic extension validation is registry-backed and intentionally lives
    # behind a local import so configuration types do not depend on concrete
    # plugin implementations.
    from se.env.process import validate_environment_process_config

    validate_environment_process_config(cfg.environment)
    if cfg.entities.resource_affinity_schema not in {
        "disabled",
        "normalized-four-resource-affinity-v1",
    }:
        raise ValueError(
            "entities.resource_affinity_schema must be 'disabled' or "
            "'normalized-four-resource-affinity-v1'"
        )
    if cfg.entities.resource_affinity_strength < 0.0:
        raise ValueError("entities.resource_affinity_strength cannot be negative")
    if cfg.entities.harvest_allocation_schema not in {
        "uniform-channel-rates-v1",
        "affinity-sampled-exclusive-harvest-v1",
    }:
        raise ValueError(
            "entities.harvest_allocation_schema must be "
            "'uniform-channel-rates-v1' or "
            "'affinity-sampled-exclusive-harvest-v1'"
        )
    if (
        cfg.entities.harvest_allocation_schema
        == "affinity-sampled-exclusive-harvest-v1"
        and cfg.entities.resource_affinity_schema
        != "normalized-four-resource-affinity-v1"
    ):
        raise ValueError("selective harvest requires inherited resource affinity")
    if (
        cfg.entities.harvest_allocation_schema
        == "affinity-sampled-exclusive-harvest-v1"
        and not any(
            value > 0.0 for value in cfg.environment.harvest_channel_multipliers
        )
    ):
        raise ValueError("selective harvest requires a positive extraction budget")
    if (
        cfg.entities.resource_affinity_min_efficiency <= 0.0
        or cfg.entities.resource_affinity_max_efficiency
        < cfg.entities.resource_affinity_min_efficiency
    ):
        raise ValueError("resource affinity efficiency bounds are invalid")
    if (
        cfg.entities.resource_affinity_schema != "disabled"
        and cfg.environment.schema not in {
            "spatially-asynchronous-multiniche-v1",
            "orthogonal-four-resource-niche-v1",
            "orthogonal-four-resource-renewal-v2",
            "persistent-multiscale-four-resource-renewal-v3",
        }
    ):
        raise ValueError("resource affinity requires a heterogeneous environment schema")
    if cfg.entities.danger_evidence_schema not in {
        "disabled",
        "inherited-direct-trace-mixture-v1",
    }:
        raise ValueError(
            "entities.danger_evidence_schema must be 'disabled' or "
            "'inherited-direct-trace-mixture-v1'"
        )
    if not math.isfinite(float(cfg.entities.danger_evidence_strength)) or not 0.0 <= cfg.entities.danger_evidence_strength <= 1.0:
        raise ValueError("entities.danger_evidence_strength must be in [0, 1]")
    if (
        cfg.entities.danger_evidence_min_efficiency <= 0.0
        or cfg.entities.danger_evidence_max_efficiency
        < cfg.entities.danger_evidence_min_efficiency
        or cfg.entities.danger_evidence_max_efficiency >= 2.0
    ):
        raise ValueError("danger evidence efficiency bounds are invalid")
    if (
        cfg.entities.danger_evidence_schema != "disabled"
        and cfg.environment.mortality_trace_schema == "disabled"
    ):
        raise ValueError("inherited danger evidence mixing requires mortality trace")
    _probability("channel_loss", cfg.information.channel_loss)
    _probability("classification_error", cfg.information.classification_error)
    if cfg.information.receiver_noise < 0:
        raise ValueError("receiver_noise cannot be negative")
    if cfg.information.source_noise < 0:
        raise ValueError("source_noise cannot be negative")
    if cfg.information.max_signal_delay < 0:
        raise ValueError("max_signal_delay cannot be negative")
    if cfg.information.direct_message_capacity < 0:
        raise ValueError("direct_message_capacity cannot be negative")
    if len(cfg.information.signal_flush_periods) != 3 or any(
        not isinstance(period, int) or isinstance(period, bool) or period <= 0
        for period in cfg.information.signal_flush_periods
    ):
        raise ValueError("information.signal_flush_periods must contain three positive integers")

    if cfg.social.group_update_period <= 0:
        raise ValueError("social.group_update_period must be positive")
    if cfg.social.group_update_mode not in {
        "periodic-v1",
        "adaptive-topology-v1",
    }:
        raise ValueError(
            "social.group_update_mode must be 'periodic-v1' or "
            "'adaptive-topology-v1'"
        )
    if cfg.social.group_label_schema != "trusted-directed-fixed-round-min-label-v1":
        raise ValueError(
            "social.group_label_schema must be "
            "'trusted-directed-fixed-round-min-label-v1'"
        )
    if cfg.social.group_label_propagation_rounds < 0:
        raise ValueError("social.group_label_propagation_rounds cannot be negative")
    if cfg.social.group_update_min_period <= 0:
        raise ValueError("social.group_update_min_period must be positive")
    if cfg.social.group_update_max_period < 0:
        raise ValueError("social.group_update_max_period cannot be negative")
    if (
        cfg.social.group_update_mode == "adaptive-topology-v1"
        and cfg.social.group_update_max_period
        and cfg.social.group_update_max_period
        < cfg.social.group_update_min_period
    ):
        raise ValueError(
            "social.group_update_max_period cannot be below the minimum period"
        )

    if not isinstance(cfg.knowledge.enabled, bool):
        raise ValueError("knowledge.enabled must be a boolean")
    if cfg.knowledge.schema not in {
        "dynamic-knowledge-k1-v1",
        "dynamic-knowledge-k2-v1",
        "dynamic-knowledge-k3-v1",
        "dynamic-knowledge-k4-v1",
        "dynamic-knowledge-latent-v1",
    }:
        raise ValueError(
            "knowledge.schema must be one of: 'dynamic-knowledge-k1-v1', "
            "'dynamic-knowledge-k2-v1', 'dynamic-knowledge-k3-v1', "
            "'dynamic-knowledge-k4-v1', 'dynamic-knowledge-latent-v1'"
        )
    if cfg.knowledge.initial_content_count < 0:
        raise ValueError("knowledge.initial_content_count cannot be negative")
    _probability("knowledge.initial_holders_fraction", cfg.knowledge.initial_holders_fraction)
    if cfg.knowledge.holder_capacity_bytes < 0:
        raise ValueError("knowledge.holder_capacity_bytes cannot be negative")
    if cfg.knowledge.encoded_bytes_per_copy <= 0:
        raise ValueError("knowledge.encoded_bytes_per_copy must be positive")
    if cfg.knowledge.transfer_period <= 0:
        raise ValueError("knowledge.transfer_period must be positive")
    _probability("knowledge.transfer_probability", cfg.knowledge.transfer_probability)
    _probability("knowledge.forget_probability", cfg.knowledge.forget_probability)
    if cfg.knowledge.attention_slots_per_tick < 0:
        raise ValueError("knowledge.attention_slots_per_tick cannot be negative")
    if any(
        value < 0.0
        for value in (
            cfg.knowledge.maintenance_energy_per_byte,
            cfg.knowledge.transfer_base_energy_cost,
            cfg.knowledge.transfer_energy_per_byte,
            cfg.knowledge.receive_energy_per_byte,
        )
    ):
        raise ValueError("knowledge energy costs cannot be negative")
    if cfg.knowledge.capacity_eviction != "oldest-copy-v1":
        raise ValueError("knowledge.capacity_eviction must be 'oldest-copy-v1'")
    if not isinstance(cfg.knowledge.log_transfer_events, bool):
        raise ValueError("knowledge.log_transfer_events must be a boolean")
    if not isinstance(cfg.knowledge.learning_enabled, bool):
        raise ValueError("knowledge.learning_enabled must be a boolean")
    if cfg.knowledge.outcome_schema != "local-outcome-v1":
        raise ValueError("knowledge.outcome_schema must be 'local-outcome-v1'")
    if not isinstance(cfg.knowledge.experience_creation_enabled, bool):
        raise ValueError("knowledge.experience_creation_enabled must be a boolean")
    if not isinstance(cfg.knowledge.experience_creation_requires_free_capacity, bool):
        raise ValueError(
            "knowledge.experience_creation_requires_free_capacity must be a boolean"
        )
    if cfg.knowledge.verification_energy_cost < 0.0:
        raise ValueError("knowledge.verification_energy_cost cannot be negative")
    _probability(
        "knowledge.confidence_learning_rate",
        cfg.knowledge.confidence_learning_rate,
    )
    _probability(
        "knowledge.confidence_decay_per_tick",
        cfg.knowledge.confidence_decay_per_tick,
    )
    _probability(
        "knowledge.initial_experience_confidence",
        cfg.knowledge.initial_experience_confidence,
    )
    if cfg.knowledge.max_updates_per_outcome <= 0:
        raise ValueError("knowledge.max_updates_per_outcome must be positive")
    if not isinstance(cfg.knowledge.log_outcome_updates, bool):
        raise ValueError("knowledge.log_outcome_updates must be a boolean")
    if cfg.knowledge.learning_enabled and cfg.knowledge.schema not in {
        "dynamic-knowledge-k2-v1",
        "dynamic-knowledge-k3-v1",
        "dynamic-knowledge-k4-v1",
        "dynamic-knowledge-latent-v1",
    }:
        raise ValueError(
            "knowledge.learning_enabled requires K2 or K3 knowledge schema"
        )
    if cfg.knowledge.learning_enabled and not cfg.knowledge.enabled:
        raise ValueError("knowledge.learning_enabled requires knowledge.enabled")
    if cfg.knowledge.enabled and cfg.knowledge.holder_capacity_bytes <= 0:
        raise ValueError("enabled knowledge requires a positive holder_capacity_bytes")
    if not isinstance(cfg.knowledge.policy_influence_enabled, bool):
        raise ValueError("knowledge.policy_influence_enabled must be a boolean")
    if cfg.knowledge.policy_residual_schema not in {
        "sparse-local-outcome-residual-v1",
        "quantized-variable-latent-residual-v1",
        "quantized-variable-latent-mlp-residual-v1",
    }:
        raise ValueError("unknown knowledge.policy_residual_schema")
    _probability("knowledge.policy_min_confidence", cfg.knowledge.policy_min_confidence)
    if cfg.knowledge.policy_min_local_samples < 0:
        raise ValueError("knowledge.policy_min_local_samples cannot be negative")
    if cfg.knowledge.policy_sample_saturation <= 0.0:
        raise ValueError("knowledge.policy_sample_saturation must be positive")
    _probability(
        "knowledge.policy_unverified_transfer_weight",
        cfg.knowledge.policy_unverified_transfer_weight,
    )
    if (
        len(cfg.knowledge.policy_outcome_scales) != 5
        or any(not math.isfinite(v) or v <= 0.0 for v in cfg.knowledge.policy_outcome_scales)
    ):
        raise ValueError("knowledge.policy_outcome_scales must contain five positive finite values")
    if not math.isfinite(cfg.knowledge.policy_outcome_clip) or cfg.knowledge.policy_outcome_clip <= 0.0:
        raise ValueError("knowledge.policy_outcome_clip must be positive and finite")
    if (
        not math.isfinite(cfg.knowledge.policy_max_abs_logit_residual)
        or cfg.knowledge.policy_max_abs_logit_residual <= 0.0
    ):
        raise ValueError("knowledge.policy_max_abs_logit_residual must be positive and finite")
    if not isinstance(cfg.knowledge.log_policy_contributions, bool):
        raise ValueError("knowledge.log_policy_contributions must be a boolean")
    if not isinstance(cfg.knowledge.latent_policy_enabled, bool):
        raise ValueError("knowledge.latent_policy_enabled must be a boolean")
    if cfg.knowledge.latent_schema != "variable-latent-knowledge-v1":
        raise ValueError("unknown knowledge.latent_schema")
    if cfg.knowledge.latent_router_schema not in {
        "quantized-linear-latent-router-v1",
        "quantized-mlp-latent-router-v1",
    }:
        raise ValueError("unknown knowledge.latent_router_schema")
    levels = cfg.knowledge.latent_length_levels
    if (
        not levels
        or tuple(sorted(set(levels))) != tuple(levels)
        or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 or value > 256 for value in levels)
    ):
        raise ValueError("knowledge.latent_length_levels must be unique ascending integers in [1, 256]")
    if cfg.knowledge.latent_router_hidden_width <= 0 or cfg.knowledge.latent_router_hidden_width > 32:
        raise ValueError("knowledge.latent_router_hidden_width must be in [1, 32]")
    if (
        cfg.knowledge.latent_router_mlp_hidden_width <= 0
        or cfg.knowledge.latent_router_mlp_hidden_width > 32
    ):
        raise ValueError("knowledge.latent_router_mlp_hidden_width must be in [1, 32]")
    if (
        not math.isfinite(cfg.knowledge.latent_router_activation_clip)
        or cfg.knowledge.latent_router_activation_clip <= 0.0
        or cfg.knowledge.latent_router_activation_clip > 8.0
    ):
        raise ValueError(
            "knowledge.latent_router_activation_clip must be finite and in (0, 8]"
        )
    if cfg.knowledge.latent_value_quantization_scale <= 0:
        raise ValueError("knowledge.latent_value_quantization_scale must be positive")
    if cfg.knowledge.latent_router_weight_quantization_scale <= 0:
        raise ValueError("knowledge.latent_router_weight_quantization_scale must be positive")
    if not math.isfinite(cfg.knowledge.latent_outcome_injection) or cfg.knowledge.latent_outcome_injection < 0.0:
        raise ValueError("knowledge.latent_outcome_injection must be finite and non-negative")
    if cfg.knowledge.latent_base_encoded_bytes <= 0 or cfg.knowledge.latent_bytes_per_value <= 0:
        raise ValueError("latent encoded byte parameters must be positive")
    _probability(
        "knowledge.latent_length_mutation_probability",
        cfg.knowledge.latent_length_mutation_probability,
    )
    if (
        not math.isfinite(cfg.knowledge.latent_max_abs_logit_residual)
        or cfg.knowledge.latent_max_abs_logit_residual <= 0.0
    ):
        raise ValueError("knowledge.latent_max_abs_logit_residual must be positive and finite")
    if not isinstance(cfg.knowledge.routing_cost_enabled, bool):
        raise ValueError("knowledge.routing_cost_enabled must be a boolean")
    if not isinstance(cfg.knowledge.log_routing_costs, bool):
        raise ValueError("knowledge.log_routing_costs must be a boolean")
    if cfg.knowledge.routing_cost_schema != "latent-routing-compute-cost-v1":
        raise ValueError("unknown knowledge.routing_cost_schema")
    if cfg.knowledge.routing_budget_mode != "all-or-none-per-entity-v1":
        raise ValueError("unknown knowledge.routing_budget_mode")
    for name, value in (
        ("routing_base_energy_cost", cfg.knowledge.routing_base_energy_cost),
        ("routing_energy_per_latent_dimension", cfg.knowledge.routing_energy_per_latent_dimension),
        ("routing_energy_per_mac", cfg.knowledge.routing_energy_per_mac),
        ("routing_energy_per_active_hidden_unit", cfg.knowledge.routing_energy_per_active_hidden_unit),
        ("routing_energy_per_emitted_action", cfg.knowledge.routing_energy_per_emitted_action),
        ("routing_energy_per_saturation", cfg.knowledge.routing_energy_per_saturation),
        ("routing_energy_per_clipped_output", cfg.knowledge.routing_energy_per_clipped_output),
    ):
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"knowledge.{name} must be finite and non-negative")
    if cfg.knowledge.routing_cost_enabled and not cfg.knowledge.latent_policy_enabled:
        raise ValueError("knowledge.routing_cost_enabled requires latent policy")
    if not isinstance(cfg.knowledge.working_memory_enabled, bool):
        raise ValueError("knowledge.working_memory_enabled must be a boolean")
    if not isinstance(cfg.knowledge.log_working_memory_updates, bool):
        raise ValueError(
            "knowledge.log_working_memory_updates must be a boolean"
        )
    if cfg.knowledge.working_memory_schema != "quantized-working-memory-v1":
        raise ValueError("unknown knowledge.working_memory_schema")
    if cfg.knowledge.working_memory_width != 4:
        raise ValueError("knowledge.working_memory_width must currently be exactly 4")
    if cfg.knowledge.working_memory_quantization_scale <= 0:
        raise ValueError("knowledge.working_memory_quantization_scale must be positive")
    if (
        not math.isfinite(cfg.knowledge.working_memory_activation_clip)
        or cfg.knowledge.working_memory_activation_clip <= 0.0
        or cfg.knowledge.working_memory_activation_clip > 8.0
    ):
        raise ValueError("knowledge.working_memory_activation_clip must be in (0, 8]")
    for name, value in (
        ("working_memory_base_energy_cost", cfg.knowledge.working_memory_base_energy_cost),
        ("working_memory_energy_per_dimension", cfg.knowledge.working_memory_energy_per_dimension),
        ("working_memory_energy_per_saturation", cfg.knowledge.working_memory_energy_per_saturation),
        ("sparse_selection_base_energy_cost", cfg.knowledge.sparse_selection_base_energy_cost),
        ("sparse_selection_energy_per_candidate", cfg.knowledge.sparse_selection_energy_per_candidate),
        ("sparse_selection_energy_per_selected_copy", cfg.knowledge.sparse_selection_energy_per_selected_copy),
    ):
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f"knowledge.{name} must be finite and non-negative")
    if not isinstance(cfg.knowledge.sparse_selection_enabled, bool):
        raise ValueError("knowledge.sparse_selection_enabled must be a boolean")
    if not isinstance(cfg.knowledge.log_sparse_selection_events, bool):
        raise ValueError(
            "knowledge.log_sparse_selection_events must be a boolean"
        )
    if cfg.knowledge.sparse_selection_schema != "sparse-query-key-topk-router-v1":
        raise ValueError("unknown knowledge.sparse_selection_schema")
    if cfg.knowledge.sparse_selection_top_k < 0 or cfg.knowledge.sparse_selection_top_k > 64:
        raise ValueError("knowledge.sparse_selection_top_k must be in [0, 64]")
    if cfg.knowledge.sparse_selection_capacity_schema not in {
        "fixed-config-topk-v1", "inherited-discrete-topk-v1"
    }:
        raise ValueError("unknown knowledge.sparse_selection_capacity_schema")
    capacity_levels = cfg.knowledge.sparse_selection_capacity_levels
    if (
        not capacity_levels
        or tuple(sorted(set(capacity_levels))) != tuple(capacity_levels)
        or any(
            not isinstance(value, int) or isinstance(value, bool)
            or value < 0 or value > 64
            for value in capacity_levels
        )
    ):
        raise ValueError(
            "knowledge.sparse_selection_capacity_levels must be unique ascending integers in [0, 64]"
        )
    if (
        cfg.knowledge.sparse_selection_capacity_schema == "inherited-discrete-topk-v1"
        and not cfg.knowledge.sparse_selection_enabled
    ):
        raise ValueError("inherited sparse-selection capacity requires sparse selection")
    if cfg.knowledge.sparse_selection_score_clip <= 0:
        raise ValueError("knowledge.sparse_selection_score_clip must be positive")
    if cfg.knowledge.working_memory_enabled and not cfg.knowledge.latent_policy_enabled:
        raise ValueError("working memory requires latent policy")
    if cfg.knowledge.sparse_selection_enabled and not cfg.knowledge.latent_policy_enabled:
        raise ValueError("sparse selection requires latent policy")

    if not isinstance(cfg.knowledge.candidate_tracking_enabled, bool):
        raise ValueError("knowledge.candidate_tracking_enabled must be a boolean")
    if cfg.knowledge.candidate_schema != "knowledge-subject-candidate-v1":
        raise ValueError("knowledge.candidate_schema must be 'knowledge-subject-candidate-v1'")
    if cfg.knowledge.candidate_graph_schema != "candidate-subject-graph-v1":
        raise ValueError("knowledge.candidate_graph_schema must be 'candidate-subject-graph-v1'")
    if cfg.knowledge.candidate_update_period <= 0:
        raise ValueError("knowledge.candidate_update_period must be positive")
    if cfg.knowledge.candidate_region_grid_x <= 0 or cfg.knowledge.candidate_region_grid_y <= 0:
        raise ValueError("knowledge candidate region grid dimensions must be positive")
    if cfg.knowledge.candidate_tracking_enabled:
        if not cfg.knowledge.enabled or not cfg.knowledge.learning_enabled:
            raise ValueError("K4 candidate tracking requires enabled K2 learning")
        if cfg.knowledge.schema not in {"dynamic-knowledge-k4-v1", "dynamic-knowledge-latent-v1"}:
            raise ValueError("K4 candidate tracking requires K4 or latent knowledge schema")
        if not cfg.knowledge.policy_influence_enabled:
            raise ValueError("K4 candidate tracking requires K3 policy influence")
    if cfg.policy.schema not in {
        "inherited-linear-policy-v1",
        "inherited-linear-policy-knowledge-residual-v1",
        "inherited-variable-latent-router-v1",
        "inherited-variable-latent-router-mlp-v1",
    }:
        raise ValueError("unknown policy.schema")
    if cfg.knowledge.policy_influence_enabled:
        if not cfg.knowledge.enabled or not cfg.knowledge.learning_enabled:
            raise ValueError("knowledge policy influence requires enabled local learning")
        if cfg.knowledge.latent_policy_enabled:
            if cfg.knowledge.schema != "dynamic-knowledge-latent-v1":
                raise ValueError("latent policy requires dynamic-knowledge-latent-v1")
            if cfg.knowledge.latent_router_schema == "quantized-linear-latent-router-v1":
                if cfg.knowledge.policy_residual_schema != "quantized-variable-latent-residual-v1":
                    raise ValueError("linear latent policy requires its residual schema")
                if cfg.policy.schema != "inherited-variable-latent-router-v1":
                    raise ValueError("linear latent policy requires inherited-variable-latent-router-v1")
            else:
                if cfg.knowledge.policy_residual_schema != "quantized-variable-latent-mlp-residual-v1":
                    raise ValueError("MLP latent policy requires its residual schema")
                if cfg.policy.schema != "inherited-variable-latent-router-mlp-v1":
                    raise ValueError(
                        "MLP latent policy requires inherited-variable-latent-router-mlp-v1"
                    )
        else:
            if cfg.knowledge.schema not in {"dynamic-knowledge-k3-v1", "dynamic-knowledge-k4-v1"}:
                raise ValueError("K3 policy influence requires dynamic-knowledge-k3-v1 or dynamic-knowledge-k4-v1")
            if cfg.knowledge.policy_residual_schema != "sparse-local-outcome-residual-v1":
                raise ValueError("K3 policy influence requires sparse-local-outcome-residual-v1")
            if cfg.policy.schema != "inherited-linear-policy-knowledge-residual-v1":
                raise ValueError("K3 policy influence requires the K3 policy schema")
    elif cfg.policy.schema != "inherited-linear-policy-v1":
        raise ValueError("knowledge policy schema requires policy influence")
    if cfg.knowledge.latent_policy_enabled and not cfg.knowledge.policy_influence_enabled:
        raise ValueError("knowledge.latent_policy_enabled requires policy influence")
    _probability("trust_group_threshold", cfg.social.trust_group_threshold)
    if not isinstance(cfg.control.heuristic_social_guidance, bool):
        raise ValueError("control.heuristic_social_guidance must be a boolean")
    _probability("control.heuristic_social_guidance_weight", cfg.control.heuristic_social_guidance_weight)
    _probability("control.autonomy_recovery_fraction", cfg.control.autonomy_recovery_fraction)
    _probability(
        "control.autonomy_activation_energy_fraction",
        cfg.control.autonomy_activation_energy_fraction,
    )
    if cfg.control.autonomy_harvest_threshold < 0:
        raise ValueError("control.autonomy_harvest_threshold cannot be negative")
    dcfg = cfg.differentiation
    if dcfg.schema not in {"disabled", "inherited-elastic-capacities-v1"}:
        raise ValueError(
            "differentiation.schema must be 'disabled' or "
            "'inherited-elastic-capacities-v1'"
        )
    if dcfg.enabled != (dcfg.schema == "inherited-elastic-capacities-v1"):
        raise ValueError("differentiation enabled/schema fields must agree")
    capacity_bounds = (
        ("working_memory", dcfg.working_memory_min_dimensions, dcfg.working_memory_max_dimensions),
        ("knowledge", dcfg.knowledge_min_bytes, dcfg.knowledge_max_bytes),
        ("relation", dcfg.relation_min_slots, dcfg.relation_max_slots),
        ("attention", dcfg.attention_min_slots, dcfg.attention_max_slots),
    )
    for name, minimum, maximum in capacity_bounds:
        if minimum < 0 or maximum < minimum:
            raise ValueError(f"invalid differentiation {name} capacity bounds")
    if dcfg.knowledge_quantum_bytes <= 0:
        raise ValueError("differentiation.knowledge_quantum_bytes must be positive")
    if (dcfg.knowledge_max_bytes - dcfg.knowledge_min_bytes) % dcfg.knowledge_quantum_bytes:
        raise ValueError("knowledge capacity range must be divisible by its quantum")
    _probability("differentiation.mutation_probability", dcfg.mutation_probability)
    if not math.isfinite(dcfg.mutation_std) or dcfg.mutation_std < 0.0:
        raise ValueError("differentiation.mutation_std must be finite and non-negative")
    d1_costs = (
        dcfg.maintenance_energy_per_working_memory_dimension,
        dcfg.maintenance_energy_per_knowledge_byte,
        dcfg.maintenance_energy_per_relation_slot,
        dcfg.maintenance_energy_per_attention_slot,
        dcfg.development_energy_per_working_memory_dimension,
        dcfg.development_energy_per_knowledge_byte,
        dcfg.development_energy_per_relation_slot,
        dcfg.development_energy_per_attention_slot,
    )
    if any((not math.isfinite(value) or value < 0.0) for value in d1_costs):
        raise ValueError("differentiation capacity costs must be finite and non-negative")
    if dcfg.enabled:
        if not cfg.knowledge.enabled or not cfg.knowledge.working_memory_enabled:
            raise ValueError("D1 requires enabled knowledge and working memory")
        if cfg.entities.relation_slots <= 0:
            raise ValueError("D1 requires positive physical relation capacity")
        if dcfg.working_memory_max_dimensions > cfg.knowledge.working_memory_width:
            raise ValueError("D1 working-memory maximum exceeds physical working_memory_width")
        if dcfg.knowledge_max_bytes > cfg.knowledge.holder_capacity_bytes:
            raise ValueError("D1 knowledge maximum exceeds physical holder_capacity_bytes")
        if dcfg.relation_max_slots > cfg.entities.relation_slots:
            raise ValueError("D1 relation maximum exceeds physical relation_slots")
        if dcfg.attention_max_slots > cfg.knowledge.attention_slots_per_tick:
            raise ValueError("D1 attention maximum exceeds physical attention_slots_per_tick")

    fcfg = cfg.functional_modules
    additive_schema = "expression-gated-contextual-harvest-v1"
    compositional_schema = "expression-gated-compositional-harvest-v2"
    embodied_schema = "expression-gated-compositional-embodied-v3"
    physiological_schema = "expression-gated-compositional-physiological-v4"
    regulatory_schema = "expression-gated-regulatory-physiology-v5"
    resource_metabolism_schema = "expression-gated-regulatory-resource-metabolism-v6"
    if fcfg.schema not in {
        "disabled", additive_schema, compositional_schema, embodied_schema,
        physiological_schema, regulatory_schema, resource_metabolism_schema,
    }:
        raise ValueError(
            "functional_modules.schema must be 'disabled', "
            "'expression-gated-contextual-harvest-v1', "
            "'expression-gated-compositional-harvest-v2', or "
            "'expression-gated-compositional-embodied-v3', "
            "'expression-gated-compositional-physiological-v4', "
            "'expression-gated-regulatory-physiology-v5', or "
            "'expression-gated-regulatory-resource-metabolism-v6'"
        )
    if fcfg.enabled != (fcfg.schema != "disabled"):
        raise ValueError("functional_modules enabled/schema fields must agree")
    if fcfg.module_count != 4:
        raise ValueError("functional_modules.module_count must be exactly 4")
    expected_input = (
        "internal-homeostasis-local-resources-abiotic-stores-feedforward-v5"
        if fcfg.schema == resource_metabolism_schema
        else "internal-homeostasis-local-resources-abiotic-feedforward-v4"
        if fcfg.schema == regulatory_schema
        else "internal-physiology-local-resources-abiotic-feedforward-v3"
        if fcfg.schema == physiological_schema
        else "internal-needs-local-resources-feedforward-v2"
        if fcfg.schema in {compositional_schema, embodied_schema}
        else "internal-needs-local-resources-v1"
    )
    if fcfg.input_schema != expected_input:
        raise ValueError(
            f"functional_modules.input_schema must be {expected_input!r} "
            f"for schema {fcfg.schema!r}"
        )
    expected_coupling = (
        "lower-slot-signal-modulation-v1"
        if fcfg.schema in {
            compositional_schema, embodied_schema, physiological_schema,
            regulatory_schema, resource_metabolism_schema
        }
        else "disabled"
    )
    if fcfg.coupling_schema != expected_coupling:
        raise ValueError(
            f"functional_modules.coupling_schema must be {expected_coupling!r} "
            f"for schema {fcfg.schema!r}"
        )
    expected_output = (
        "harvest-locomotion-signal-repair-v1"
        if fcfg.schema == embodied_schema
        else "harvest-physiology-drive-v1"
        if fcfg.schema == physiological_schema
        else "harvest-regulatory-drive-v2"
        if fcfg.schema in {regulatory_schema, resource_metabolism_schema}
        else "harvest-channel-zero-sum-residual-v1"
    )
    if fcfg.output_schema != expected_output:
        raise ValueError(
            f"functional_modules.output_schema must be {expected_output!r} "
            f"for schema {fcfg.schema!r}"
        )
    if (
        not math.isfinite(fcfg.expression_threshold)
        or fcfg.expression_threshold < 0.0
        or fcfg.expression_threshold >= 1.0
    ):
        raise ValueError("functional_modules.expression_threshold must be in [0, 1)")
    if (
        not math.isfinite(fcfg.max_residual_fraction)
        or fcfg.max_residual_fraction <= 0.0
        or fcfg.max_residual_fraction > 1.0
    ):
        raise ValueError("functional_modules.max_residual_fraction must be in (0, 1]")
    _probability("functional_modules.mutation_probability", fcfg.mutation_probability)
    if not math.isfinite(fcfg.mutation_std) or fcfg.mutation_std < 0.0:
        raise ValueError("functional_modules.mutation_std must be finite and non-negative")
    functional_costs = (
        fcfg.maintenance_energy_per_expression,
        fcfg.development_energy_per_expression,
        fcfg.maintenance_energy_per_coupling_weight,
        fcfg.development_energy_per_coupling_weight,
        fcfg.maintenance_energy_per_embodied_weight,
        fcfg.development_energy_per_embodied_weight,
        fcfg.maintenance_energy_per_physiology_weight,
        fcfg.development_energy_per_physiology_weight,
        fcfg.max_movement_speed_fraction,
        fcfg.max_signal_strength_fraction,
        fcfg.repair_material_per_tick,
        fcfg.repair_integrity_per_material,
        fcfg.repair_energy_per_material,
    )
    if any((not math.isfinite(value) or value < 0.0) for value in functional_costs):
        raise ValueError(
            "functional module costs and embodied limits must be finite and non-negative"
        )
    if fcfg.max_movement_speed_fraction > 0.75:
        raise ValueError(
            "functional_modules.max_movement_speed_fraction cannot exceed 0.75"
        )
    if fcfg.max_signal_strength_fraction > 1.0:
        raise ValueError(
            "functional_modules.max_signal_strength_fraction cannot exceed 1.0"
        )
    embodied_values = (
        fcfg.max_movement_speed_fraction,
        fcfg.max_signal_strength_fraction,
        fcfg.repair_material_per_tick,
        fcfg.repair_integrity_per_material,
        fcfg.repair_energy_per_material,
        fcfg.maintenance_energy_per_embodied_weight,
        fcfg.development_energy_per_embodied_weight,
    )
    if fcfg.schema not in {embodied_schema, physiological_schema} and any(
        value != 0.0 for value in embodied_values
    ):
        raise ValueError(
            "embodied functional-module settings require the v3 embodied schema"
        )
    if fcfg.schema == embodied_schema and (
        fcfg.max_movement_speed_fraction <= 0.0
        or fcfg.max_signal_strength_fraction <= 0.0
        or fcfg.repair_material_per_tick <= 0.0
        or fcfg.repair_integrity_per_material <= 0.0
        or fcfg.repair_energy_per_material <= 0.0
    ):
        raise ValueError(
            "v3 embodied modules require positive movement, signal, and repair semantics"
        )
    physiology_weight_values = (
        fcfg.maintenance_energy_per_physiology_weight,
        fcfg.development_energy_per_physiology_weight,
    )
    if fcfg.schema not in {
        physiological_schema, regulatory_schema, resource_metabolism_schema
    } and any(
        value != 0.0 for value in physiology_weight_values
    ):
        raise ValueError(
            "physiology router costs require a physiological functional schema"
        )
    pcfg = cfg.physiology
    if pcfg.schema not in {
        "disabled",
        "oxygen-tissue-structure-v1",
        "transport-metabolism-messenger-tissue-v2",
        "transport-metabolism-messenger-tissue-v3",
        "transport-metabolism-messenger-tissue-resource-v4",
        "transport-metabolism-messenger-tissue-resource-v5",
        "transport-metabolism-messenger-tissue-resource-v6",
        "transport-metabolism-messenger-tissue-resource-v7",
    }:
        raise ValueError(
            "physiology.schema must be 'disabled', 'oxygen-tissue-structure-v1', "
            "'transport-metabolism-messenger-tissue-v2', "
            "'transport-metabolism-messenger-tissue-v3', or "
            "'transport-metabolism-messenger-tissue-resource-v4', or "
            "'transport-metabolism-messenger-tissue-resource-v5', or "
            "'transport-metabolism-messenger-tissue-resource-v6', or "
            "'transport-metabolism-messenger-tissue-resource-v7'"
        )
    if pcfg.enabled != (pcfg.schema != "disabled"):
        raise ValueError("physiology enabled/schema fields must agree")
    physiology_values: list[float] = []
    for name in PhysiologyConfig.__dataclass_fields__:
        if name in {"enabled", "schema"}:
            continue
        raw_value = getattr(pcfg, name)
        if isinstance(raw_value, tuple):
            physiology_values.extend(float(value) for value in raw_value)
        else:
            physiology_values.append(float(raw_value))
    if any(not math.isfinite(value) or value < 0.0 for value in physiology_values):
        raise ValueError("physiology parameters must be finite and non-negative")
    for name in (
        "resource_store_base_capacity",
        "resource_conversion_per_tick",
        "resource_store_decay_per_tick",
        "resource_processing_energy_per_unit",
    ):
        values = tuple(float(value) for value in getattr(pcfg, name))
        if len(values) != 4:
            raise ValueError(f"physiology.{name} must contain four channels")
    if any(value > 1.0 for value in pcfg.resource_store_decay_per_tick):
        raise ValueError("physiology.resource_store_decay_per_tick values cannot exceed 1")
    for name in (
        "initial_oxygenation",
        "initial_tissue_condition",
        "initial_structure_condition",
        "hypoxia_threshold",
        "terrain_speed_penalty_fraction",
        "terrain_energy_cost_fraction",
        "tissue_damage_integrity_fraction",
        "structure_damage_integrity_fraction",
        "max_movement_speed_fraction",
        "max_signal_strength_fraction",
        "initial_metabolic_fatigue",
        "initial_mobilization_messenger",
        "initial_maintenance_messenger",
        "initial_messenger_precursor",
        "mobilization_speed_gain",
        "mobilization_signal_gain",
        "maintenance_speed_penalty",
    ):
        if float(getattr(pcfg, name)) > 1.0:
            raise ValueError(f"physiology.{name} cannot exceed 1")
    if fcfg.schema in {
        physiological_schema, regulatory_schema, resource_metabolism_schema
    }:
        expected_physiology_schemas = (
            {
                "transport-metabolism-messenger-tissue-resource-v4",
                "transport-metabolism-messenger-tissue-resource-v5",
                "transport-metabolism-messenger-tissue-resource-v6",
                "transport-metabolism-messenger-tissue-resource-v7",
            }
            if fcfg.schema == resource_metabolism_schema
            else {
                "transport-metabolism-messenger-tissue-v2",
                "transport-metabolism-messenger-tissue-v3",
            }
            if fcfg.schema == regulatory_schema
            else {"oxygen-tissue-structure-v1"}
        )
        if not pcfg.enabled or pcfg.schema not in expected_physiology_schemas:
            raise ValueError(
                f"{fcfg.schema} requires physiology schema in "
                f"{sorted(expected_physiology_schemas)!r}"
            )
        if (
            cfg.environment.physiology_environment_schema
            != "oxygen-terrain-wear-mosaic-v1"
        ):
            raise ValueError(
                "physiological modules require the oxygen-terrain-wear environment"
            )
        required_positive = [
            pcfg.oxygen_uptake_per_tick,
            pcfg.basal_oxygen_use_per_tick,
            pcfg.repair_material_per_tick,
            pcfg.repair_energy_per_material,
            pcfg.repair_tissue_per_material,
            pcfg.repair_structure_per_material,
            pcfg.max_movement_speed_fraction,
            pcfg.max_signal_strength_fraction,
        ]
        if fcfg.schema in {regulatory_schema, resource_metabolism_schema}:
            required_positive.extend(
                [
                    pcfg.messenger_synthesis_per_tick,
                    pcfg.messenger_decay_per_tick,
                    pcfg.messenger_precursor_use_per_unit,
                    pcfg.messenger_precursor_recovery_per_tick,
                    pcfg.messenger_energy_per_unit,
                    pcfg.computation_energy_per_load,
                    pcfg.computation_oxygen_per_load,
                    pcfg.fatigue_gain_per_work,
                    pcfg.fatigue_clearance_per_tick,
                    pcfg.maintenance_energy_per_capacity,
                    pcfg.development_energy_per_capacity,
                ]
            )
            _probability(
                "physiology.gene_mutation_probability",
                pcfg.gene_mutation_probability,
            )
            if pcfg.gene_mutation_std <= 0.0:
                raise ValueError("v5 physiology requires positive gene_mutation_std")
            if pcfg.schema in {
                "transport-metabolism-messenger-tissue-resource-v4",
                "transport-metabolism-messenger-tissue-resource-v5",
                "transport-metabolism-messenger-tissue-resource-v6",
                "transport-metabolism-messenger-tissue-resource-v7",
            }:
                required_positive.extend(pcfg.resource_store_base_capacity)
                required_positive.extend(pcfg.resource_conversion_per_tick)
                if pcfg.schema == "transport-metabolism-messenger-tissue-resource-v7":
                    required_positive.extend(
                        pcfg.resource_processing_energy_per_unit
                    )
        if any(value <= 0.0 for value in required_positive):
            raise ValueError(
                "physiological modules require positive transport, use, repair, and execution semantics"
            )
    elif pcfg.enabled:
        raise ValueError(
            "enabled physiology requires a matching physiological functional schema"
        )
    if pcfg.schema not in {
        "transport-metabolism-messenger-tissue-resource-v4",
        "transport-metabolism-messenger-tissue-resource-v5",
        "transport-metabolism-messenger-tissue-resource-v6",
        "transport-metabolism-messenger-tissue-resource-v7",
    } and any(
        value != 0.0
        for values in (
            pcfg.resource_store_base_capacity,
            pcfg.resource_conversion_per_tick,
            pcfg.resource_store_decay_per_tick,
            pcfg.resource_processing_energy_per_unit,
        )
        for value in values
    ):
        raise ValueError(
            "resource storage and conversion settings require physiology resource-v4/v5/v6/v7"
        )
    if pcfg.schema == "transport-metabolism-messenger-tissue-resource-v7":
        if (
            cfg.environment.resource_processing_schema
            != "phase-shifted-channel-processing-support-v1"
        ):
            raise ValueError(
                "physiology resource-v7 requires phase-shifted channel processing support"
            )
    elif any(value != 0.0 for value in pcfg.resource_processing_energy_per_unit):
        raise ValueError(
            "resource processing execution costs require physiology resource-v7"
        )
    if fcfg.enabled:
        if cfg.entities.resource_affinity_schema != "normalized-four-resource-affinity-v1":
            raise ValueError("D2-A functional modules require inherited resource affinity")
        if cfg.entities.harvest_allocation_schema != "affinity-sampled-exclusive-harvest-v1":
            raise ValueError("D2-A functional modules require selective harvest allocation")

    if cfg.policy.temperature <= 0:
        raise ValueError("policy.temperature must be positive")
    _probability("policy.mutation_probability", cfg.policy.mutation_probability)
    if cfg.entities.relation_slots <= 0:
        raise ValueError("relation_slots must be positive")
    if cfg.entities.reproduction_capacity_arbitration not in {
        "stable-id-v1",
        "stateless-random-v1",
    }:
        raise ValueError(
            "entities.reproduction_capacity_arbitration must be one of: "
            "'stable-id-v1', 'stateless-random-v1'"
        )

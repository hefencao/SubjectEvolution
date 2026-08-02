from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np

from se.analysis.subject_vm_paired_evaluation import (
    PAIRED_EVALUATION_BRANCH_SCHEMA,
    _branch_config,
    _set_branch_mode,
    build_plan,
    export_pair,
)
from se.analysis.subject_vm_paired_evidence import (
    PAIRED_EVIDENCE_ASSESSMENT_SCHEMA,
    PairedEvidenceScreeningThresholds,
    assess_exports,
)
from se.cfg import load_config
from se.runtime.sim import Simulation
from se.subject_vm import (
    EVALUATION_MODE_GUARDED_LIVE,
    EVALUATION_MODE_READ_ONLY_CONTROL,
    EVALUATION_STATUS_COMPLETE_CONTROL,
    EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK,
    EVALUATION_STATUS_ROLLBACK_FAILED,
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_ASSOCIATION_SCHEMA,
    SUBJECT_VM_ELIGIBILITY_SCHEMA,
    SUBJECT_VM_EVALUATION_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_LIVE_WRITE_SCHEMA,
    SUBJECT_VM_MODULATION_SCHEMA,
    SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE3C5_SCHEMA,
    SUBJECT_VM_TARGET_BINDING_SCHEMA,
    SUBJECT_VM_TRACE_SCHEMA,
    SUBJECT_VM_TRANSACTION_SCHEMA,
    SUBJECT_VM_UPDATE_SAFETY_SCHEMA,
    TARGET_KIND_NODE,
    SubjectVMActivationConfig,
    SubjectVMAssociationConfig,
    SubjectVMConfig,
    SubjectVMEligibilityConfig,
    SubjectVMEvaluationConfig,
    SubjectVMLiveWriteConfig,
    SubjectVMModulationConfig,
    SubjectVMRegionConfig,
    SubjectVMTargetBindingConfig,
    SubjectVMTraceConfig,
    SubjectVMTransactionConfig,
    SubjectVMUpdateSafetyConfig,
)


def _canonical_sha256(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _subject_vm(*, live_enabled: bool) -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE3C5_SCHEMA,
        node_state_width=3,
        regions=tuple(
            SubjectVMRegionConfig(
                name=name, node_capacity=2, edge_capacity=1, update_period=1
            )
            for name in SUBJECT_VM_REGION_NAMES
        ),
        activation=SubjectVMActivationConfig(
            schema=SUBJECT_VM_ACTIVATION_SCHEMA,
            input_port_schema=SUBJECT_VM_INPUT_PORT_SCHEMA,
            output_port_schema=SUBJECT_VM_OUTPUT_PORT_SCHEMA,
            activation_clip=8.0,
            output_clip=8.0,
        ),
        trace=SubjectVMTraceConfig(
            schema=SUBJECT_VM_TRACE_SCHEMA,
            event_schema=SUBJECT_VM_OBJECTIVE_EVENT_SCHEMA,
            token_width=32,
            token_clip=8.0,
            capacity_per_subject=5,
            retention_ticks=5,
        ),
        eligibility=SubjectVMEligibilityConfig(
            schema=SUBJECT_VM_ELIGIBILITY_SCHEMA,
            decay=0.5,
            clip=2.0,
            max_age_ticks=4,
        ),
        association=SubjectVMAssociationConfig(
            schema=SUBJECT_VM_ASSOCIATION_SCHEMA,
            request_token_port=0,
            request_threshold=0.5,
            similarity_threshold=0.8,
            min_delay_ticks=1,
            max_delay_ticks=4,
        ),
        modulation=SubjectVMModulationConfig(
            schema=SUBJECT_VM_MODULATION_SCHEMA,
            request_token_port=1,
            request_threshold=0.5,
            fact_weight_start_port=2,
            target_weight_start_port=23,
            proposal_clip=1.0,
        ),
        target_binding=SubjectVMTargetBindingConfig(
            schema=SUBJECT_VM_TARGET_BINDING_SCHEMA,
            min_abs_eligibility=0.1,
        ),
        update_safety=SubjectVMUpdateSafetyConfig(
            schema=SUBJECT_VM_UPDATE_SAFETY_SCHEMA,
            step_scale=0.5,
            min_abs_delta=0.01,
            family_delta_clip=(0.2,) * 6,
            event_l1_budget=0.3,
            parameter_lower_bounds=(-2.0, -2.0, -2.0, -2.0, -2.0, 0.0),
            parameter_upper_bounds=(2.0,) * 6,
        ),
        transaction=SubjectVMTransactionConfig(
            schema=SUBJECT_VM_TRANSACTION_SCHEMA,
            max_targets_per_event=6,
            base_cost_units=3,
            per_target_cost_units=2,
        ),
        live_write=SubjectVMLiveWriteConfig(
            schema=SUBJECT_VM_LIVE_WRITE_SCHEMA,
            enabled=live_enabled,
            ledger_capacity_per_subject=4,
            rollback_after_ticks=2,
            window_ticks=8,
            max_pending_transactions=2,
            max_applied_targets_per_window=2,
            max_abs_delta_per_window=0.3,
            commit_base_cost_units=5,
            commit_per_target_cost_units=2,
            rollback_base_cost_units=3,
            rollback_per_target_cost_units=1,
        ),
        evaluation=SubjectVMEvaluationConfig(
            schema=SUBJECT_VM_EVALUATION_SCHEMA,
            enabled=True,
            capacity_per_subject=4,
            observation_ticks=1,
            control_horizon_ticks=2,
            fact_clip=8.0,
            registration_cost_units=2,
            per_observation_cost_units=1,
        ),
    )


def _config(*, live_enabled: bool):
    base = load_config("configs/mvp_small.json")
    return replace(
        base,
        subject_vm=_subject_vm(live_enabled=live_enabled),
        world=replace(
            base.world,
            initial_entities=8,
            max_entities=16,
            width=16.0,
            height=16.0,
            grid_x=4,
            grid_y=4,
        ),
        run=replace(
            base.run,
            ticks=3,
            metrics_period=99,
            checkpoint_period=99,
            full_checkpoint_enabled=False,
            checkpoint_ticks=(),
        ),
    )


def _close(sim: Simulation) -> None:
    sim.metrics.close()
    sim.evolution_progress.close()
    sim.knowledge.close()


def _complete(sim: Simulation, *, role: str, energy: float, rollback_failure=False) -> None:
    ledger = sim.subject_vm.evaluation_ledger
    assert ledger is not None
    mode = (
        EVALUATION_MODE_GUARDED_LIVE
        if role == "guarded-live"
        else EVALUATION_MODE_READ_ONLY_CONTROL
    )
    status = (
        EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK
        if role == "guarded-live"
        else EVALUATION_STATUS_COMPLETE_CONTROL
    )
    ledger.entry_valid[0, 0] = True
    ledger.mode[0, 0] = mode
    ledger.status[0, 0] = status
    ledger.source_event_id[0, 0] = np.uint64(700)
    ledger.start_tick[0, 0] = 1
    ledger.end_tick[0, 0] = 2
    ledger.rollback_due_tick[0, 0] = 3
    ledger.family_observed[0, 0, 0] = True
    ledger.target_kind[0, 0, 0] = TARGET_KIND_NODE
    ledger.target_index[0, 0, 0] = 0
    ledger.target_id[0, 0, 0] = 1
    ledger.pre_value[0, 0, 0] = np.float32(0.25)
    ledger.projected_value[0, 0, 0] = np.float32(0.45)
    ledger.bounded_delta[0, 0, 0] = np.float32(0.20)
    ledger.observation_count[0, 0] = 1
    ledger.success_count[0, 0] = 1
    ledger.fact_sum[0, 0, 0] = np.float32(energy)
    ledger.fact_abs_sum[0, 0, 0] = np.float32(abs(energy))
    ledger.fact_max_abs[0, 0, 0] = np.float32(abs(energy))
    ledger.rollback_verified[0, 0] = True
    ledger.counted_cost_units[0, 0] = 3
    if rollback_failure:
        ledger.entry_valid[0, 1] = True
        ledger.mode[0, 1] = EVALUATION_MODE_GUARDED_LIVE
        ledger.status[0, 1] = EVALUATION_STATUS_ROLLBACK_FAILED
        ledger.source_event_id[0, 1] = np.uint64(701)


def _paired_export(tmp_path: Path, *, rollback_failure=False) -> Path:
    source_cfg = _config(live_enabled=False)
    source_sim = Simulation(source_cfg, tmp_path / "source_run", backend="cpu")
    source = source_sim.save_full_checkpoint(tmp_path / "source.sechk")
    _close(source_sim)
    plan = build_plan(source, horizon_ticks=3)
    checkpoints = {}
    for role, energy in (("guarded-live", -1.5), ("read-only-control", -0.5)):
        sim = Simulation.from_checkpoint(
            source, tmp_path / role, backend="cpu", until_tick=3
        )
        _set_branch_mode(sim, role=role, final_tick=3)
        sim.tick = 3
        _complete(
            sim,
            role=role,
            energy=energy,
            rollback_failure=rollback_failure and role == "guarded-live",
        )
        branch = next(item for item in plan["branches"] if item["role"] == role)
        sim.checkpoint_lineage.append(
            {
                "schema": PAIRED_EVALUATION_BRANCH_SCHEMA,
                "branch_id": branch["branch_id"],
                "branch_role": role,
                "source_checkpoint_state_sha256": plan["source"][
                    "checkpoint_state_sha256"
                ],
                "paired_evaluation_plan_sha256": plan["plan_sha256"],
            }
        )
        checkpoints[role] = sim.save_full_checkpoint(tmp_path / f"{role}.sechk")
        _close(sim)
    payload = export_pair(
        plan,
        guarded_live_checkpoint=checkpoints["guarded-live"],
        read_only_control_checkpoint=checkpoints["read-only-control"],
    )
    path = tmp_path / "paired_export.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _one_pair_thresholds() -> PairedEvidenceScreeningThresholds:
    return PairedEvidenceScreeningThresholds(
        min_independent_source_pairs=1,
        min_total_paired_windows=1,
        min_pooled_pairing_coverage=1.0,
        max_fact_clip_fraction=0.0,
        max_rollback_failures=0,
        min_paired_evaluation_cost_match_fraction=1.0,
    )


def test_stage3c7_reports_integrity_without_scalarizing_objective_facts(
    tmp_path: Path,
) -> None:
    export = _paired_export(tmp_path)
    report = assess_exports([export], thresholds=_one_pair_thresholds())
    assert report["schema"] == PAIRED_EVIDENCE_ASSESSMENT_SCHEMA
    assert report["adequacy_screen"]["passed"] is True
    assert report["aggregate"]["independent_source_pair_count"] == 1
    assert report["aggregate"]["total_paired_window_count"] == 1
    assert report["aggregate"]["pooled_pairing_coverage"] == 1.0
    run = report["runs"][0]
    assert run["hard_integrity_pass"] is True
    assert run["branch_divergence"]["entity_divergence"][
        "alive_entity_identity_jaccard"
    ] == 1.0
    assert run["count_only_cost_matching"][
        "exact_evaluation_cost_match_fraction"
    ] == 1.0
    assert report["objective_coordinate_weighting"] is None
    assert report["scalar_score"] is False
    assert report["automatic_keep_or_revert_decision"] is False
    assert report["causal_effect_authorized"] is False


def test_stage3c7_does_not_count_duplicate_source_checkpoint_as_independent(
    tmp_path: Path,
) -> None:
    export = _paired_export(tmp_path)
    thresholds = replace(_one_pair_thresholds(), min_independent_source_pairs=2)
    report = assess_exports([export, export], thresholds=thresholds)
    assert report["aggregate"]["export_count"] == 2
    assert report["aggregate"]["independent_source_pair_count"] == 1
    assert report["aggregate"]["duplicate_source_state_hash_counts"]
    assert report["adequacy_screen"]["criteria"]["independent_source_pairs"] is False
    assert report["adequacy_screen"]["passed"] is False


def test_stage3c7_exposes_unpaired_contract_divergence(tmp_path: Path) -> None:
    export = _paired_export(tmp_path)
    payload = json.loads(export.read_text(encoding="utf-8"))
    pair = payload["window_evidence"]["pairs"].pop()
    live = pair["guarded_live"]
    control = pair["read_only_control"]
    control["target_id"][0] = 99
    control["pair_key"] = "control-mismatch"
    payload["window_evidence"]["unpaired_guarded_live"] = [live]
    payload["window_evidence"]["unpaired_read_only_control"] = [control]
    payload["window_evidence"]["paired_window_count"] = 0
    unsigned = dict(payload)
    unsigned.pop("export_sha256", None)
    payload["export_sha256"] = _canonical_sha256(unsigned)
    export.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    thresholds = replace(
        _one_pair_thresholds(),
        min_total_paired_windows=0,
        min_pooled_pairing_coverage=0.0,
        min_paired_evaluation_cost_match_fraction=0.0,
    )
    report = assess_exports([export], thresholds=thresholds)
    pairing = report["runs"][0]["pairing"]
    assert pairing["paired_window_count"] == 0
    assert pairing["unpaired_guarded_live_reason_counts"] == {
        "target-or-update-contract-divergence": 1
    }
    assert pairing["unpaired_read_only_control_reason_counts"] == {
        "target-or-update-contract-divergence": 1
    }


def test_stage3c7_rollback_failure_fails_hard_integrity(tmp_path: Path) -> None:
    export = _paired_export(tmp_path, rollback_failure=True)
    report = assess_exports([export], thresholds=_one_pair_thresholds())
    run = report["runs"][0]
    assert run["rollback_and_ledger_integrity"]["rollback_failure_count"] == 1
    assert run["hard_integrity_checks"]["no_rollback_failures"] is False
    assert run["hard_integrity_pass"] is False
    assert report["adequacy_screen"]["passed"] is False

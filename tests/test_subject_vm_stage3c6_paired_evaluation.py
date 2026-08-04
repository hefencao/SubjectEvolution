from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from se.cfg import load_config
from se.checkpointing import read_checkpoint_bundle, write_checkpoint_bundle
from se.analysis.subject_vm_paired_evaluation import (
    PAIRED_EVALUATION_BRANCH_SCHEMA,
    _branch_config,
    build_plan,
    export_pair,
    run_plan,
)
from se.subject_vm import (
    EVALUATION_MODE_GUARDED_LIVE,
    EVALUATION_MODE_READ_ONLY_CONTROL,
    EVALUATION_STATUS_COMPLETE_CONTROL,
    EVALUATION_STATUS_COMPLETE_LIVE_ROLLED_BACK,
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
    SubjectVMRuntime,
    SubjectVMTargetBindingConfig,
    SubjectVMTraceConfig,
    SubjectVMTransactionConfig,
    SubjectVMUpdateSafetyConfig,
)
from se.runtime.sim import Simulation
from se.subject_vm.evaluation_export import (
    PAIRED_WINDOW_EXPORT_SCHEMA,
    extract_completed_windows,
    pair_completed_windows,
)


def _subject_vm(*, live_enabled: bool) -> SubjectVMConfig:
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE3C5_SCHEMA,
        node_state_width=3,
        regions=tuple(
            SubjectVMRegionConfig(name=name, node_capacity=2, edge_capacity=1, update_period=1)
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
    return replace(base, subject_vm=_subject_vm(live_enabled=live_enabled))


def _runtime(cfg) -> SubjectVMRuntime:
    return SubjectVMRuntime.initialize(
        cfg.subject_vm,
        entity_capacity=1,
        active_rows=np.array([0], dtype=np.int32),
        entity_ids=np.array([11], dtype=np.uint64),
        subject_ids=np.array([101], dtype=np.uint64),
    )


def _write_checkpoint(path: Path, cfg, runtime: SubjectVMRuntime, *, tick: int, lineage=()):
    return write_checkpoint_bundle(
        path,
        config=cfg,
        tick=tick,
        state={
            "config": cfg,
            "simulation": {"tick": tick, "subject_vm": runtime.snapshot_state()},
            "checkpoint_lineage": list(lineage),
        },
        execution_backend="cpu-reference",
        requested_backend="cpu",
    )


def _complete(runtime: SubjectVMRuntime, *, role: str, energy: float) -> None:
    assert runtime.evaluation_ledger is not None
    ledger = runtime.evaluation_ledger
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
    ledger.start_tick[0, 0] = 2
    ledger.end_tick[0, 0] = 3
    ledger.rollback_due_tick[0, 0] = 4
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


def test_plan_freezes_shared_checkpoint_and_only_live_write_mode(tmp_path: Path) -> None:
    cfg = _config(live_enabled=False)
    source = _write_checkpoint(tmp_path / "source.sechk", cfg, _runtime(cfg), tick=0)
    plan = build_plan(source, horizon_ticks=3)
    assert plan["shared_checkpoint_required"] is True
    assert plan["scalar_score"] is False
    assert [item["role"] for item in plan["branches"]] == [
        "guarded-live", "read-only-control"
    ]
    assert plan["branches"][0]["config_sha256"] != plan["branches"][1]["config_sha256"]
    assert all(
        item["only_authorized_config_difference"] == "subject_vm.live_write.enabled"
        for item in plan["branches"]
    )
    assert plan == build_plan(source, horizon_ticks=3)
    finalized = build_plan(
        source, horizon_ticks=3, finalize_pending_transients_at_export=True
    )
    assert finalized["finalize_pending_transients_at_export"] is True
    assert finalized["plan_sha256"] != plan["plan_sha256"]


def test_plan_rejects_nonempty_source_ledgers(tmp_path: Path) -> None:
    cfg = _config(live_enabled=False)
    runtime = _runtime(cfg)
    assert runtime.evaluation_ledger is not None
    runtime.evaluation_ledger.entry_valid[0, 0] = True
    runtime.evaluation_ledger.status[0, 0] = EVALUATION_STATUS_COMPLETE_CONTROL
    source = _write_checkpoint(tmp_path / "source.sechk", cfg, runtime, tick=0)
    with pytest.raises(ValueError, match="empty Stage-3C-5 ledgers"):
        build_plan(source, horizon_ticks=3)


def test_export_pairs_componentwise_evidence_without_score(tmp_path: Path) -> None:
    source_cfg = _config(live_enabled=False)
    source = _write_checkpoint(
        tmp_path / "source.sechk", source_cfg, _runtime(source_cfg), tick=0
    )
    plan = build_plan(source, horizon_ticks=3)
    records = {}
    for role, energy in (("guarded-live", -1.5), ("read-only-control", -0.5)):
        cfg = _branch_config(source_cfg, role=role, final_tick=3)
        runtime = _runtime(cfg)
        _complete(runtime, role=role, energy=energy)
        branch = next(item for item in plan["branches"] if item["role"] == role)
        lineage = ({
            "schema": PAIRED_EVALUATION_BRANCH_SCHEMA,
            "branch_id": branch["branch_id"],
            "branch_role": role,
            "source_checkpoint_state_sha256": plan["source"]["checkpoint_state_sha256"],
            "paired_evaluation_plan_sha256": plan["plan_sha256"],
        },)
        path = _write_checkpoint(
            tmp_path / f"{role}.sechk", cfg, runtime, tick=3, lineage=lineage
        )
        records[role] = path
    payload = export_pair(
        plan,
        guarded_live_checkpoint=records["guarded-live"],
        read_only_control_checkpoint=records["read-only-control"],
    )
    assert payload["shared_checkpoint_verified"] is True
    assert payload["scalar_score"] is False
    evidence = payload["window_evidence"]
    assert evidence["schema"] == PAIRED_WINDOW_EXPORT_SCHEMA
    assert evidence["paired_window_count"] == 1
    pair = evidence["pairs"][0]
    assert pair["objective_fact_sum_difference_live_minus_control"][0] == pytest.approx(-1.0)
    assert pair["scalar_score"] is None
    assert pair["keep_or_revert_decision"] is None
    assert pair["causal_effect_authorized"] is False


def test_window_extraction_rejects_unverified_completion() -> None:
    cfg = _config(live_enabled=True)
    runtime = _runtime(cfg)
    _complete(runtime, role="guarded-live", energy=1.0)
    assert runtime.evaluation_ledger is not None
    runtime.evaluation_ledger.rollback_verified[0, 0] = False
    with pytest.raises(ValueError, match="rollback verification"):
        extract_completed_windows(runtime.snapshot_state(), branch_role="guarded-live")


def test_pair_export_keeps_unpaired_records_visible() -> None:
    cfg = _config(live_enabled=True)
    runtime = _runtime(cfg)
    _complete(runtime, role="guarded-live", energy=1.0)
    live = extract_completed_windows(runtime.snapshot_state(), branch_role="guarded-live")
    payload = pair_completed_windows(live, [])
    assert payload["paired_window_count"] == 0
    assert len(payload["unpaired_guarded_live"]) == 1
    assert payload["causal_effect_authorized"] is False


def test_run_plan_creates_shared_checkpoint_branches_and_export(tmp_path: Path) -> None:
    cfg = _config(live_enabled=False)
    cfg = replace(
        cfg,
        world=replace(
            cfg.world,
            initial_entities=16,
            max_entities=32,
            width=16.0,
            height=16.0,
            grid_x=4,
            grid_y=4,
        ),
        run=replace(
            cfg.run,
            ticks=3,
            metrics_period=99,
            checkpoint_period=99,
            full_checkpoint_enabled=False,
            checkpoint_ticks=(),
        ),
    )
    source_sim = Simulation(cfg, tmp_path / "source_run", backend="cpu")
    source = source_sim.save_full_checkpoint(tmp_path / "source.sechk")
    source_sim.metrics.close()
    source_sim.evolution_progress.close()
    source_sim.knowledge.close()
    plan = build_plan(source, horizon_ticks=3)
    result = run_plan(
        plan, source_checkpoint=source, output_dir=tmp_path / "paired", backend="cpu"
    )
    assert Path(result["guarded_live_checkpoint"]).is_file()
    assert Path(result["read_only_control_checkpoint"]).is_file()
    export = json.loads(Path(result["export"]).read_text(encoding="utf-8"))
    assert export["shared_checkpoint_verified"] is True
    assert export["branch_identity_verified"] is True
    assert export["scalar_score"] is False
    assert export["window_evidence"]["paired_window_count"] == 0
    assert (tmp_path / "paired/guarded_live/branch_identity.json").is_file()
    assert (tmp_path / "paired/read_only_control/branch_identity.json").is_file()


def test_plan_records_only_authorized_association_tie_break_runtime_override(
    tmp_path: Path,
) -> None:
    cfg = _config(live_enabled=False)
    source = _write_checkpoint(tmp_path / "source_tie.sechk", cfg, _runtime(cfg), tick=0)
    baseline = build_plan(source, horizon_ticks=3)
    oldest = build_plan(
        source, horizon_ticks=3, association_tie_break_override="oldest"
    )
    assert "branch_runtime_overrides" not in baseline
    assert oldest["branch_runtime_overrides"] == {
        "subject_vm.association.tie_break": "oldest"
    }
    assert oldest["plan_sha256"] != baseline["plan_sha256"]
    assert [item["branch_id"] for item in oldest["branches"]] != [
        item["branch_id"] for item in baseline["branches"]
    ]
    with pytest.raises(ValueError, match="latest or oldest"):
        build_plan(
            source,
            horizon_ticks=3,
            association_tie_break_override="random",
        )


def test_plan_records_only_authorized_association_candidate_limit_runtime_override(
    tmp_path: Path,
) -> None:
    cfg = _config(live_enabled=False)
    source = _write_checkpoint(tmp_path / "source_limit.sechk", cfg, _runtime(cfg), tick=0)
    baseline = build_plan(source, horizon_ticks=3)
    top2 = build_plan(
        source, horizon_ticks=3, association_candidate_limit_override=2
    )
    assert "branch_runtime_overrides" not in baseline
    assert top2["branch_runtime_overrides"] == {
        "subject_vm.association.candidate_limit": 2
    }
    assert top2["plan_sha256"] != baseline["plan_sha256"]
    with pytest.raises(ValueError, match="one or two"):
        build_plan(
            source,
            horizon_ticks=3,
            association_candidate_limit_override=3,
        )


def test_categorical_sampling_trace_preserves_paired_branch_identity_and_state(
    tmp_path: Path,
) -> None:
    cfg = _config(live_enabled=False)
    cfg = replace(
        cfg,
        world=replace(
            cfg.world,
            initial_entities=16,
            max_entities=32,
            width=16.0,
            height=16.0,
            grid_x=4,
            grid_y=4,
        ),
        run=replace(
            cfg.run,
            ticks=3,
            metrics_period=99,
            checkpoint_period=99,
            full_checkpoint_enabled=False,
            checkpoint_ticks=(),
        ),
    )
    source_sim = Simulation(cfg, tmp_path / "trace_source_run", backend="cpu")
    source = source_sim.save_full_checkpoint(tmp_path / "trace_source.sechk")
    source_sim.metrics.close()
    source_sim.evolution_progress.close()
    source_sim.knowledge.close()
    plan = build_plan(source, horizon_ticks=3)

    baseline = run_plan(
        plan,
        source_checkpoint=source,
        output_dir=tmp_path / "paired_baseline",
        backend="cpu",
    )
    traced = run_plan(
        plan,
        source_checkpoint=source,
        output_dir=tmp_path / "paired_traced",
        backend="cpu",
        categorical_sampling_trace=True,
    )

    for role, checkpoint_key, directory in (
        ("guarded_live", "guarded_live_checkpoint", "guarded_live"),
        ("read_only_control", "read_only_control_checkpoint", "read_only_control"),
    ):
        baseline_meta, _ = read_checkpoint_bundle(baseline[checkpoint_key])
        traced_meta, _ = read_checkpoint_bundle(traced[checkpoint_key])
        assert baseline_meta["config_sha256"] == traced_meta["config_sha256"]
        assert baseline_meta["state_sha256"] == traced_meta["state_sha256"]
        baseline_identity = (
            tmp_path / "paired_baseline" / directory / "branch_identity.json"
        ).read_bytes()
        traced_identity = (
            tmp_path / "paired_traced" / directory / "branch_identity.json"
        ).read_bytes()
        assert baseline_identity == traced_identity

    manifests = traced["categorical_sampling_trace_manifests"]
    assert manifests is not None
    assert set(manifests) == {"guarded-live", "read-only-control"}
    for role, manifest_path in manifests.items():
        assert manifest_path is not None
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        assert manifest["event_count"] > 0
        assert manifest["metadata"]["branch_role"] == role
        assert manifest["checkpoint_state_member"] is False
        assert manifest["semantic_feedback"] is False

from __future__ import annotations

from pathlib import Path

import numpy as np

from se.analysis.protocol_audit import build_protocol_audit
from se.subjects.social import (
    GROUP_LABEL_SCHEMA,
    DeterministicGroupLabelPlanner,
    GroupDetectionSnapshot,
)
from se.env.partition import SpatialRegionPartition


ROOT = Path(__file__).resolve().parents[1]


def _snapshot(rounds: int) -> GroupDetectionSnapshot:
    alive = np.ones(3, dtype=bool)
    stable_ids = np.asarray([101, 102, 103], dtype=np.uint64)
    return GroupDetectionSnapshot(
        active_indices=np.asarray([0, 1, 2], dtype=np.int32),
        active_entity_ids=stable_ids.copy(),
        alive=alive,
        stable_ids=stable_ids,
        energy=np.ones(3, dtype=np.float32),
        relation_targets=np.asarray([[-1], [0], [1]], dtype=np.int32),
        relation_trust=np.ones((3, 1), dtype=np.float32),
        resource_grad_x=np.ones(3, dtype=np.float32),
        resource_grad_y=np.zeros(3, dtype=np.float32),
        trust_threshold=0.5,
        min_members=1,
        label_schema=GROUP_LABEL_SCHEMA,
        propagation_rounds=rounds,
        tick=10,
    )


def test_group_label_fixed_round_horizon_is_explicit() -> None:
    planner = DeterministicGroupLabelPlanner()
    one_round = planner.plan(_snapshot(1))
    two_rounds = planner.plan(_snapshot(2))
    assert one_round.entity_group_ids.tolist() == [101, 101, 102]
    assert two_rounds.entity_group_ids.tolist() == [101, 101, 101]


def test_normalized_partition_changes_physical_scale_not_topology() -> None:
    small = SpatialRegionPartition(128.0, 128.0, 32, 32, 4, 4)
    large = SpatialRegionPartition(256.0, 256.0, 64, 64, 4, 4)
    small_meta = small.metadata()
    large_meta = large.metadata()
    assert small.normalized_topology()["topology_sha256"] == large.normalized_topology()[
        "topology_sha256"
    ]
    assert small_meta["partition_sha256"] != large_meta["partition_sha256"]
    assert small_meta["physical_region_width"] == 32.0
    assert large_meta["physical_region_width"] == 64.0
    assert small.region_ids(np.asarray([0.0, 127.9]), np.asarray([0.0, 127.9])).tolist() == [0, 15]
    assert large.region_ids(np.asarray([0.0, 255.9]), np.asarray([0.0, 255.9])).tolist() == [0, 15]


def test_protocol_audit_publishes_current_structural_rules() -> None:
    payload = build_protocol_audit(
        ROOT
        / "configs"
        / "mvp_short_latent_l2_memory_topk_inherited_heterogeneous_budget_matched_costed_transfer_mortality_trace_adaptive_groups_longrun.json"
    )
    group = payload["group_label_protocol"]
    region = payload["spatial_region_protocol"]
    assert group["label_schema"] == GROUP_LABEL_SCHEMA
    assert group["propagation_rounds"] == 8
    assert group["trust_threshold"] == 0.12
    assert group["minimum_members"] == 6
    assert region["regions_x"] == 4
    assert region["regions_y"] == 4
    assert region["physical_region_width"] == 32.0
    assert region["world_cells_per_region_x"] == 8.0
    assert len(payload["audit_sha256"]) == 64


def test_protocol_audit_publishes_gpu_first_parity_boundary() -> None:
    from se.analysis.protocol_audit import build_protocol_audit, render_markdown

    report = build_protocol_audit(ROOT / "configs" / "mvp_short_k1_compat.json")
    execution = report["execution_backend_protocol"]
    assert execution["cli_default_backend"] == "auto"
    assert execution["configured_gpu_semantics_mode"] == "hybrid-accelerated"
    assert execution["parity_schema"] == "cpu-gpu-parity-v2"
    assert execution["semantic_validation_boundary"] == "tests/test_parity.py"
    markdown = render_markdown(report)
    assert "## Execution backend" in markdown
    preference = execution["gpu_preference"].lower()
    assert "gpu-hybrid" in preference or "hybrid gpu" in preference

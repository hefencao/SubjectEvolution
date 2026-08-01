from __future__ import annotations

import csv
import json
from pathlib import Path

from se.analysis.multichannel_interest_debug import summarize
from se.experiments.d1_multichannel_interest import prepare

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies" / "d1y_multichannel_interest_feedback_v1"


def test_multichannel_config_changes_only_relation_semantics(tmp_path: Path) -> None:
    output = tmp_path / "multichannel.json"
    report = prepare(
        template=STUDY / "frozen/d1x/source_config.json",
        output=output,
        ticks=12,
        material_window_ticks=4,
        material_learning_rate=0.08,
        minimum_material=0.5,
        knowledge_window_ticks=8,
        knowledge_learning_rate=0.04,
        minimum_knowledge_evidence=0.5,
    )
    assert report["fixed_share_trust_enabled"] is False
    assert report["genetic_coordinates_changed"] == 0
    assert report["environment_or_movement_changed"] is False
    assert set(report["changed_paths"]) == {
        "run.ticks",
        "run.checkpoint_period",
        "social.relation_update_schema",
        "social.interest_feedback_window_ticks",
        "social.knowledge_interest_window_ticks",
        "social.knowledge_interest_learning_rate",
        "social.knowledge_interest_min_evidence",
    }
    payload = json.loads(output.read_text())
    assert payload["social"]["relation_update_schema"] == "delayed-multichannel-interest-v2"
    assert payload["social"]["knowledge_interest_window_ticks"] == 8
    assert payload["social"]["trust_gain_share"] == 0.0
    assert payload["social"]["trust_loss_failed"] == 0.0


def test_multichannel_debug_requires_both_material_and_knowledge_evidence(tmp_path: Path) -> None:
    root = tmp_path / "run" / "seed_1"
    root.mkdir(parents=True)
    (root / "run_manifest.json").write_text(json.dumps({
        "seed": 1,
        "requested_backend": "cpu",
        "execution_backend": "cpu",
        "config_sha256": "abc",
    }))
    (root / "resolved_config.json").write_text(json.dumps({
        "social": {"trust_gain_share": 0.0, "trust_loss_failed": 0.0}
    }))
    fields = [
        "tick", "alive", "groups", "relation_update_schema", "relation_edge_count",
        "relation_trust_mean", "relation_trust_std",
        "relation_partner_differentiation_mean_std",
        "interest_feedback_material_settlements_total",
        "interest_feedback_knowledge_events_total",
        "interest_feedback_knowledge_settlements_total",
        "interest_feedback_knowledge_evidence_total",
        "interest_feedback_knowledge_signed_value_total",
        "interest_feedback_knowledge_mean_delay_ticks",
        "interest_feedback_knowledge_orphaned_total",
        "knowledge_transfer_committed_total",
        "knowledge_transferred_copies_verified_total",
    ]
    with (root / "metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "tick": 360,
            "alive": 100,
            "groups": 0,
            "relation_update_schema": "delayed-multichannel-interest-v2",
            "relation_edge_count": 10,
            "relation_trust_mean": 0.1,
            "relation_trust_std": 0.03,
            "relation_partner_differentiation_mean_std": 0.02,
            "interest_feedback_material_settlements_total": 20,
            "interest_feedback_knowledge_events_total": 4,
            "interest_feedback_knowledge_settlements_total": 2,
            "interest_feedback_knowledge_evidence_total": 2.0,
            "interest_feedback_knowledge_signed_value_total": 1.0,
            "interest_feedback_knowledge_mean_delay_ticks": 180,
            "interest_feedback_knowledge_orphaned_total": 1,
            "knowledge_transfer_committed_total": 5,
            "knowledge_transferred_copies_verified_total": 4,
        })
    report = summarize(source_root=root.parent, output=tmp_path / "summary.json")
    assert report["semantics_ready"] is True
    assert report["epoch_1_ready"] is False
    assert report["authorization"]["epoch_1_base_checkpoint"] is False

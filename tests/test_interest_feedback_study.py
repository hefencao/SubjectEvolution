from __future__ import annotations

import csv
import json
from pathlib import Path

from se.analysis.interest_feedback_debug import summarize
from se.experiments.d1_interest_feedback import prepare

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies" / "d1x_interest_feedback_network_v1"


def test_interest_feedback_config_changes_only_relation_semantics(tmp_path: Path) -> None:
    output = tmp_path / "interest.json"
    report = prepare(
        template=STUDY / "frozen/d1v/source_config.json",
        output=output,
        ticks=12,
        window_ticks=4,
        learning_rate=0.08,
        minimum_material=0.5,
    )
    assert report["fixed_share_trust_enabled"] is False
    assert report["genetic_coordinates_changed"] == 0
    assert report["environment_or_movement_changed"] is False
    assert set(report["changed_paths"]) == {
        "run.ticks",
        "run.checkpoint_period",
        "social.relation_update_schema",
        "social.interest_feedback_window_ticks",
        "social.interest_feedback_learning_rate",
        "social.interest_feedback_min_material",
        "social.trust_gain_share",
        "social.trust_loss_failed",
    }
    payload = json.loads(output.read_text())
    assert payload["social"]["relation_update_schema"] == "delayed-material-interest-v1"
    assert payload["social"]["trust_gain_share"] == 0.0
    assert payload["social"]["trust_loss_failed"] == 0.0


def test_interest_feedback_debug_never_claims_epoch_one(tmp_path: Path) -> None:
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
        "tick", "alive", "relation_update_schema", "relation_edge_count",
        "relation_trust_mean", "relation_trust_std",
        "relation_partner_differentiation_mean_std",
        "interest_feedback_settlements_total", "interest_feedback_positive_total",
        "interest_feedback_negative_total", "interest_feedback_neutral_total",
        "interest_feedback_material_total",
    ]
    with (root / "metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "tick": 120,
            "alive": 100,
            "relation_update_schema": "delayed-material-interest-v1",
            "relation_edge_count": 10,
            "relation_trust_mean": 0.1,
            "relation_trust_std": 0.03,
            "relation_partner_differentiation_mean_std": 0.02,
            "interest_feedback_settlements_total": 20,
            "interest_feedback_positive_total": 9,
            "interest_feedback_negative_total": 8,
            "interest_feedback_neutral_total": 3,
            "interest_feedback_material_total": 12.0,
        })
    report = summarize(source_root=root.parent, output=tmp_path / "summary.json")
    assert report["semantics_ready"] is True
    assert report["epoch_1_ready"] is False
    assert report["authorization"]["epoch_1_base_checkpoint"] is False


def test_epoch_one_contract_remains_unqualified() -> None:
    contract = json.loads((ROOT / "protocols/epochs/interest_feedback_network_qualification_v1.json").read_text())
    assert contract["target_epoch"] == "epoch-1-entity-subject-prototype"
    assert contract["status"] == "not-yet-qualified"
    assert len(contract["required_stages"]) == 5

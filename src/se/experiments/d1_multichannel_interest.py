"""Prepare D1-Y multi-timescale material and knowledge relationship feedback."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ..cfg import load_config

SCHEMA = "d1-multichannel-interest-config-v1"


def _sha(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def prepare(
    *,
    template: str | Path,
    output: str | Path,
    ticks: int,
    material_window_ticks: int,
    material_learning_rate: float,
    minimum_material: float,
    knowledge_window_ticks: int,
    knowledge_learning_rate: float,
    minimum_knowledge_evidence: float,
) -> dict[str, Any]:
    source = Path(template)
    before = json.loads(source.read_text(encoding="utf-8"))
    after = json.loads(json.dumps(before))
    changes: dict[str, dict[str, Any]] = {}

    def change(section: str, key: str, value: Any) -> None:
        old = after[section].get(key)
        if old != value:
            after[section][key] = value
            changes[f"{section}.{key}"] = {"before": old, "after": value}

    change("run", "ticks", int(ticks))
    change("run", "metrics_period", 60)
    change("run", "checkpoint_period", int(ticks))
    change("run", "checkpoint_ticks", [])
    change("run", "full_checkpoint_enabled", False)
    change("social", "relation_update_schema", "delayed-multichannel-interest-v2")
    change("social", "interest_feedback_window_ticks", int(material_window_ticks))
    change("social", "interest_feedback_learning_rate", float(material_learning_rate))
    change("social", "interest_feedback_min_material", float(minimum_material))
    change("social", "knowledge_interest_window_ticks", int(knowledge_window_ticks))
    change("social", "knowledge_interest_learning_rate", float(knowledge_learning_rate))
    change("social", "knowledge_interest_min_evidence", float(minimum_knowledge_evidence))
    change("social", "trust_gain_share", 0.0)
    change("social", "trust_loss_failed", 0.0)

    allowed = {
        "run.ticks", "run.metrics_period", "run.checkpoint_period",
        "run.checkpoint_ticks", "run.full_checkpoint_enabled",
        "social.relation_update_schema", "social.interest_feedback_window_ticks",
        "social.interest_feedback_learning_rate", "social.interest_feedback_min_material",
        "social.knowledge_interest_window_ticks",
        "social.knowledge_interest_learning_rate",
        "social.knowledge_interest_min_evidence",
        "social.trust_gain_share", "social.trust_loss_failed",
    }
    unexpected = sorted(set(changes) - allowed)
    if unexpected:
        raise RuntimeError(f"D1-Y drifted outside its allow-list: {unexpected}")

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    cfg = load_config(destination)
    report = {
        "schema": SCHEMA,
        "source": str(source),
        "output": str(destination),
        "source_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output_file_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source_canonical_sha256": _sha(before),
        "output_canonical_sha256": _sha(after),
        "changed_paths": sorted(changes),
        "changes": changes,
        "genetic_coordinates_changed": 0,
        "environment_or_movement_changed": False,
        "direct_conflict_enabled": False,
        "fixed_share_trust_enabled": False,
        "relation_semantics": {
            "schema": cfg.social.relation_update_schema,
            "material_window_ticks": cfg.social.interest_feedback_window_ticks,
            "knowledge_window_ticks": cfg.social.knowledge_interest_window_ticks,
            "material_channel": (
                "realized bilateral material return remains one short-horizon channel; "
                "it no longer defines the complete partner value"
            ),
            "knowledge_channel": (
                "a transferred copy is credited only when later local verification "
                "compares its five-dimensional prediction with a realized outcome; "
                "signed prediction quality and confidence remain separately auditable"
            ),
            "aggregation": (
                "material and knowledge channels settle independently on different "
                "timescales; no single received/(given+received) formula represents all interest"
            ),
        },
        "authorization": {
            "single_seed_multichannel_semantics_debug": True,
            "epoch_1_entry": False,
            "formal_multi_seed_panel": False,
            "group_rule_implementation": False,
            "gene_audit": False,
            "subjecthood_claim": False,
        },
        "interpretation_boundary": (
            "D1-Y adds long-horizon non-material knowledge verification to the relation "
            "ledger. It does not prove causal knowledge benefit, stable partner prediction, "
            "population qualification, or Epoch 1 entry. Historical sources that are no "
            "longer living remain diagnostic orphaned evidence under the current row-addressed relation store."
        ),
    }
    Path(f"{destination}.manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ticks", type=int, default=900)
    parser.add_argument("--material-window-ticks", type=int, default=120)
    parser.add_argument("--material-learning-rate", type=float, default=0.08)
    parser.add_argument("--minimum-material", type=float, default=0.5)
    parser.add_argument("--knowledge-window-ticks", type=int, default=360)
    parser.add_argument("--knowledge-learning-rate", type=float, default=0.04)
    parser.add_argument("--minimum-knowledge-evidence", type=float, default=0.5)
    args = parser.parse_args(argv)
    print(json.dumps(prepare(
        template=args.template,
        output=args.output,
        ticks=args.ticks,
        material_window_ticks=args.material_window_ticks,
        material_learning_rate=args.material_learning_rate,
        minimum_material=args.minimum_material,
        knowledge_window_ticks=args.knowledge_window_ticks,
        knowledge_learning_rate=args.knowledge_learning_rate,
        minimum_knowledge_evidence=args.minimum_knowledge_evidence,
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

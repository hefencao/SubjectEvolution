"""Prepare D1-X delayed material-interest relationship configuration."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from se.cfg import load_config

SCHEMA = "delayed-material-interest-config-v1"


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def prepare(
    *,
    template: str | Path,
    output: str | Path,
    ticks: int = 900,
    window_ticks: int = 120,
    learning_rate: float = 0.08,
    minimum_material: float = 0.5,
) -> dict[str, Any]:
    source = Path(template)
    before = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(before, dict):
        raise ValueError("D1-X template must be a JSON object")
    if before.get("environment", {}).get("signal_medium_schema") != (
        "independent-openness-mosaic-v1"
    ):
        raise ValueError("D1-X requires the D1-V independent signal medium")
    if int(ticks) <= 0 or int(window_ticks) <= 0:
        raise ValueError("ticks and feedback window must be positive")
    if not 0.0 < float(learning_rate) <= 1.0:
        raise ValueError("learning rate must be in (0, 1]")
    if float(minimum_material) <= 0.0:
        raise ValueError("minimum material must be positive")

    after = deepcopy(before)
    changes: dict[str, dict[str, Any]] = {}

    def change(section: str, key: str, value: Any) -> None:
        old = deepcopy(after[section].get(key))
        after[section][key] = value
        if old != value:
            changes[f"{section}.{key}"] = {"before": old, "after": deepcopy(value)}

    change("run", "ticks", int(ticks))
    change("run", "metrics_period", 60)
    change("run", "checkpoint_period", int(ticks))
    change("run", "checkpoint_ticks", [])
    change("run", "full_checkpoint_enabled", False)
    change("social", "relation_update_schema", "delayed-material-interest-v1")
    change("social", "interest_feedback_window_ticks", int(window_ticks))
    change("social", "interest_feedback_learning_rate", float(learning_rate))
    change("social", "interest_feedback_min_material", float(minimum_material))
    # Fixed increments remain explicit zeroes so the generated protocol cannot
    # be misread as mixing designer trust bonuses with material feedback.
    change("social", "trust_gain_share", 0.0)
    change("social", "trust_loss_failed", 0.0)

    allowed = {
        "run.ticks",
        "run.metrics_period",
        "run.checkpoint_period",
        "run.checkpoint_ticks",
        "run.full_checkpoint_enabled",
        "social.relation_update_schema",
        "social.interest_feedback_window_ticks",
        "social.interest_feedback_learning_rate",
        "social.interest_feedback_min_material",
        "social.trust_gain_share",
        "social.trust_loss_failed",
    }
    unexpected = sorted(set(changes) - allowed)
    if unexpected:
        raise RuntimeError(f"D1-X drifted outside its allow-list: {unexpected}")

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
            "window_ticks": cfg.social.interest_feedback_window_ticks,
            "learning_rate": cfg.social.interest_feedback_learning_rate,
            "minimum_material": cfg.social.interest_feedback_min_material,
            "material_basis": (
                "realized energy/raw transfers normalized by configured per-action "
                "transfer amounts; directed realized receiving share within total bilateral material evidence"
            ),
        },
        "authorization": {
            "single_seed_relation_semantics_debug": True,
            "epoch_1_entry": False,
            "group_rule_implementation": False,
            "formal_multi_seed_panel": False,
            "gene_audit": False,
            "subjecthood_claim": False,
        },
        "interpretation_boundary": (
            "D1-X removes fixed SHARE trust increments and tests a delayed material "
            "balance ledger. It does not establish predictive partner models, broader "
            "non-material consequences, multi-seed persistence, or Epoch 1 entry."
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
    parser.add_argument("--window-ticks", type=int, default=120)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--minimum-material", type=float, default=0.5)
    args = parser.parse_args(argv)
    print(json.dumps(prepare(
        template=args.template,
        output=args.output,
        ticks=args.ticks,
        window_ticks=args.window_ticks,
        learning_rate=args.learning_rate,
        minimum_material=args.minimum_material,
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

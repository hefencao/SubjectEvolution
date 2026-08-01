"""Summarize D1-V independent signal-medium debug runs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize(*, source_root: str | Path, output: str | Path) -> dict[str, Any]:
    root = Path(source_root)
    seed_dirs = sorted(path for path in root.glob("seed_*") if path.is_dir())
    if not seed_dirs and (root / "summary.json").is_file():
        seed_dirs = [root]
    runs: list[dict[str, Any]] = []
    for seed_dir in seed_dirs:
        summary = _json(seed_dir / "summary.json")
        manifest = _json(seed_dir / "run_manifest.json")
        config = _json(seed_dir / "resolved_config.json")
        runs.append(
            {
                "run": seed_dir.name,
                "seed": manifest.get("seed"),
                "requested_backend": manifest.get("requested_backend"),
                "execution_backend": manifest.get("execution_backend"),
                "config_sha256": manifest.get("config_sha256"),
                "alive": summary.get("alive"),
                "signal_medium_schema": summary.get("signal_medium_schema"),
                "field_signal_transport": summary.get("signal_propagation_schema"),
                "direct_message_transport": summary.get(
                    "direct_message_propagation_schema"
                ),
                "signal_openness_mean": summary.get("signal_openness_mean"),
                "signal_openness_std": summary.get("signal_openness_std"),
                "movement_resistance_std": summary.get(
                    "movement_resistance_std"
                ),
                "movement_signal_correlation": summary.get(
                    "movement_signal_correlation"
                ),
                "config_field_transport": config.get("environment", {}).get(
                    "signal_propagation_schema"
                ),
                "config_direct_transport": config.get("information", {}).get(
                    "direct_message_propagation_schema"
                ),
            }
        )
    semantics_ready = bool(
        runs
        and all(
            run["signal_medium_schema"] == "independent-openness-mosaic-v1"
            and run["field_signal_transport"]
            == "independent-openness-diffusion-v2"
            and run["direct_message_transport"]
            == "openness-distance-attenuated-v2"
            and float(run.get("signal_openness_std") or 0.0) > 0.0
            and float(run.get("movement_resistance_std") or 0.0) > 0.0
            for run in runs
        )
    )
    report = {
        "schema": "independent-signal-medium-debug-summary-v1",
        "source_root": str(root),
        "runs": runs,
        "run_count": len(runs),
        "semantics_ready": semantics_ready,
        "fixed_direction_coupling": False,
        "authorization": {
            "continue_environment_debugging": True,
            "direct_conflict_implementation": False,
            "formal_environment_panel": False,
            "gene_audit": False,
            "social_role_claim": False,
        },
        "interpretation_boundary": (
            "The report verifies that movement resistance and signal transport are "
            "separate fields. Their observed correlation is a configured map property, "
            "not a universal law or evidence of information benefit."
        ),
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            summarize(source_root=args.source_root, output=args.output),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

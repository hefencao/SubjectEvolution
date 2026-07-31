"""Execution termination metadata shared by runtime entry points."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_run_termination(
    output_dir: str | Path,
    *,
    requested_tick: int,
    completed_tick: int,
    reason: str | None,
) -> dict[str, Any]:
    payload = {
        "schema": "run-termination-v1",
        "requested_tick": int(requested_tick),
        "completed_tick": int(completed_tick),
        "terminated_early": bool(completed_tick < requested_tick),
        "reason": reason,
        "scientific_effect_interpretation_authorized": (
            False if reason else None
        ),
    }
    path = Path(output_dir) / "run_termination.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload

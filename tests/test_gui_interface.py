from __future__ import annotations

import json
from pathlib import Path

from subject_evolution.gui_interface.run_simulation import run


def test_gui_runner_publishes_a_stream_and_preserves_config(tmp_path: Path) -> None:
    raw = json.loads(Path("configs/mvp_small.json").read_text(encoding="utf-8"))
    raw["run"].update(ticks=1, metrics_period=1, checkpoint_period=99)
    raw["world"].update(initial_entities=16, max_entities=24)
    config = tmp_path / "small.json"
    config.write_text(json.dumps(raw), encoding="utf-8")
    output = tmp_path / "output"
    stream = output / "eco_live.bin"

    run(config, output, stream, publish_every=1)

    assert stream.is_file()
    assert stream.stat().st_size > 0
    effective = json.loads((output / "config.json").read_text(encoding="utf-8"))
    assert effective["run"]["ticks"] == 1

from __future__ import annotations

from pathlib import Path
import sys

sys.dont_write_bytecode = True

root = Path(__file__).resolve().parents[1]
src = root / "src"

for forbidden in src.rglob("*"):
    if forbidden.is_dir() and forbidden.name == "__pycache__":
        raise AssertionError(f"bytecode cache must not be packaged: {forbidden}")
    if forbidden.is_file() and forbidden.suffix == ".pyc":
        raise AssertionError(f"compiled Python file must not be packaged: {forbidden}")

sys.path.insert(0, str(src))

import subject_evolution  # noqa: E402
from subject_evolution.gui_interface.run_simulation import build_parser as single_parser  # noqa: E402
from subject_evolution.multi_seed import build_parser as multi_parser  # noqa: E402

assert subject_evolution.__version__ == "0.30.0"

single = single_parser().parse_args(
    [
        "--config", "config.json",
        "--output", "runs/single",
        "--stream", "runs/single/eco_live.bin",
        "--backend", "auto",
    ]
)
assert single.backend == "auto"
assert single.stream.endswith("eco_live.bin")

multi = multi_parser().parse_args(
    [
        "--config", "config.json",
        "--seeds", "10001,10002,10003",
        "--output", "runs/multi",
        "--backend", "gpu",
        "--until-tick", "1500",
        "--overwrite-partial",
    ]
)
assert multi.backend == "gpu"
assert multi.until_tick == 1500
assert multi.overwrite_partial is True

single_help = single_parser().format_help()
multi_help = multi_parser().format_help()
for option in ("--config", "--output", "--stream", "--backend"):
    assert option in single_help
for option in ("--config", "--seeds", "--output", "--backend", "--until-tick", "--overwrite-partial"):
    assert option in multi_help

print("subject_evolution 0.30.0 GUI command compatibility: ok")

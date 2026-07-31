from __future__ import annotations

from pathlib import Path
import subprocess


def test_all_study_command_scripts_have_valid_bash_syntax() -> None:
    scripts = sorted(Path("studies").glob("*/commands/*.sh"))
    assert scripts
    for script in scripts:
        subprocess.run(["bash", "-n", str(script)], check=True)

from __future__ import annotations

import json
from pathlib import Path

from se.analysis.integrated_baseline import inspect_baseline, prepare


TEMPLATE = Path("studies/d1p_integrated_ecological_subject_v1/frozen/source/source_config.json")


def test_integrated_baseline_recognizes_plural_subject_and_environment() -> None:
    report = inspect_baseline(TEMPLATE)
    assert report["schema"] == "integrated-ecological-subject-baseline-v1"
    assert report["genome"]["total_coordinates"] == 704
    assert report["genome"]["functional_module_coordinates"] == 142
    assert report["environment"]["resource_channels"] == 4
    assert all(report["checks"].values())
    assert report["causal_effect_claim_authorized"] is False


def test_prepare_integrated_baseline_is_byte_identical(tmp_path: Path) -> None:
    output = tmp_path / "integrated.json"
    manifest = prepare(template=TEMPLATE, output=output)
    assert output.read_bytes() == TEMPLATE.read_bytes()
    assert manifest["source_file_sha256"] == manifest["output_file_sha256"]
    sidecar = json.loads(Path(f"{output}.manifest.json").read_text(encoding="utf-8"))
    assert sidecar["schema"] == "integrated-ecological-subject-baseline-v1"

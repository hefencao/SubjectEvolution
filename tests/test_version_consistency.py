from pathlib import Path
from scripts.check_version_consistency import check

ROOT = Path(__file__).resolve().parents[1]

def test_version_sources_agree_without_inspecting_local_iteration_history() -> None:
    report = check(ROOT)
    assert report["passed"]
    assert report["version"] == "0.100.0"
    assert report["package_version"] == "0.100.0"
    assert report["status_version"] == "0.100.0"
    assert report["iteration_docs_checked"] is False

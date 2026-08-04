from pathlib import Path
from scripts.check_version_consistency import check

ROOT = Path(__file__).resolve().parents[1]

def test_version_sources_agree_without_inspecting_local_iteration_history() -> None:
    report = check(ROOT)
    assert report["passed"]
    assert report["version"] == "0.161.0"
    assert report["package_version"] == "0.161.0"
    assert report["status_version"] == "0.161.0"
    assert report["iteration_docs_checked"] is False


def test_status_version_accepts_chinese_and_legacy_english_labels(tmp_path: Path) -> None:
    from scripts.check_version_consistency import status_version

    chinese = tmp_path / "status-cn.md"
    chinese.write_text("版本：**1.2.3**\n", encoding="utf-8")
    assert status_version(chinese) == "1.2.3"

    english = tmp_path / "status-en.md"
    english.write_text("Version: **1.2.3**\n", encoding="utf-8")
    assert status_version(english) == "1.2.3"

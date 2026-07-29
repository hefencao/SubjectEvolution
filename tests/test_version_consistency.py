from pathlib import Path
from scripts.check_version_consistency import check

ROOT=Path(__file__).resolve().parents[1]

def test_version_sources_and_makefile_docs_agree() -> None:
    report=check(ROOT)
    assert report['passed']
    assert report['version']=='0.60.0'

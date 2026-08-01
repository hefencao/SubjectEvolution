from __future__ import annotations

from pathlib import Path

import se.backend as backend
from se.analysis import long_run
from se.cmd import multi_seed as multi_seed_command
from se.cmd import run as run_command
from se.env import diversity, world
from se.evolution import progress
from se.knowledge import system as knowledge_system
from se.subjects import graph
from se.experiments import natural_event_execution
from se.runtime import sim as runtime_sim


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/se"


def test_short_package_layout_is_canonical() -> None:
    assert PACKAGE.is_dir()
    assert not (ROOT / "src/subject_evolution").exists()
    assert (PACKAGE / "env").is_dir()
    assert (PACKAGE / "evolution").is_dir()
    assert (PACKAGE / "knowledge").is_dir()
    assert (PACKAGE / "subjects").is_dir()
    assert (PACKAGE / "subject_vm").is_dir()
    assert (PACKAGE / "gui").is_dir()
    assert (PACKAGE / "cmd").is_dir()
    assert not (PACKAGE / "domains").exists()
    assert not (PACKAGE / "interfaces").exists()
    assert not (PACKAGE / "simulation.py").exists()
    assert not (PACKAGE / "config.py").exists()


def test_canonical_modules_import_directly() -> None:
    assert runtime_sim.Simulation.__name__ == "Simulation"
    assert knowledge_system.KnowledgeSystem.__name__ == "KnowledgeSystem"
    assert world.Environment.__name__ == "Environment"
    assert progress.EvolutionProgressTracker.__name__ == "EvolutionProgressTracker"
    assert graph.CandidateSubjectGraph.__name__ == "CandidateSubjectGraph"
    assert callable(long_run.load_progress)
    assert callable(natural_event_execution.execute_plan)
    assert callable(diversity.resource_field_diversity_metrics)


def test_large_modules_remain_split() -> None:
    assert len((PACKAGE / "runtime/sim.py").read_text().splitlines()) < 2500
    assert len((PACKAGE / "knowledge/system.py").read_text().splitlines()) < 1500


def test_project_charter_has_stable_name() -> None:
    assert (ROOT / "docs/PROJECT_CHARTER.md").is_file()
    assert not (ROOT / "docs/PROJECT_CHARTER_V0.3.md").exists()


def test_optional_cupy_import_is_cached() -> None:
    assert hasattr(backend._load_cupy, "cache_info")
    before = backend._load_cupy.cache_info()
    backend._load_cupy()
    backend._load_cupy()
    after = backend._load_cupy.cache_info()
    assert after.misses - before.misses <= 1
    assert after.hits - before.hits >= 1


def test_command_implementations_are_canonical() -> None:
    assert callable(run_command.main)
    assert callable(multi_seed_command.main)
    assert len((PACKAGE / "__main__.py").read_text().splitlines()) < 15


def test_gui_is_external_to_runtime_and_science_domains() -> None:
    runtime_sources = list((PACKAGE / "runtime").glob("*.py"))
    domain_sources = []
    for dirname in ("env", "evolution", "knowledge", "subjects", "subject_vm"):
        domain_sources.extend((PACKAGE / dirname).rglob("*.py"))
    for path in runtime_sources + domain_sources:
        text = path.read_text(encoding="utf-8")
        assert "se.gui" not in text

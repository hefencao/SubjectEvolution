from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from se.analysis.gene_persistence import build_report
from se.cfg import load_config
from se.policy import ParametricPolicy


CONFIG = Path("studies/d1p_integrated_ecological_subject_v1/frozen/source/source_config.json")


def _checkpoint(path: Path, *, tick: int, genotype: np.ndarray) -> None:
    generation = np.arange(genotype.shape[0], dtype=np.uint32) % 3
    np.savez_compressed(
        path,
        tick=np.asarray([tick], dtype=np.uint64),
        genotype=genotype.astype(np.float32),
        generation=generation,
    )


def test_gene_persistence_uses_cross_seed_quorum_and_is_not_causal(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    width = ParametricPolicy.genome_size_for_config(cfg)
    root = tmp_path / "panel"
    rng = np.random.default_rng(1234)
    for seed in (1, 2, 3):
        seed_dir = root / f"seed_{seed}"
        seed_dir.mkdir(parents=True)
        reference = rng.normal(0.0, 0.25, size=(24, width)).clip(-0.8, 0.8)
        final = reference.copy()
        final[:, 0] = 0.0  # cross-seed loss
        final[:, 1] = 0.5  # active but concentrated
        _checkpoint(seed_dir / "checkpoint_00000240.npz", tick=240, genotype=reference)
        _checkpoint(seed_dir / "checkpoint_00001200.npz", tick=1200, genotype=final)
        (seed_dir / "summary.json").write_text(
            json.dumps({"mean_generation": 1.5}), encoding="utf-8"
        )
    health = tmp_path / "health.json"
    health.write_text(json.dumps({"ready": True}), encoding="utf-8")
    report = build_report(source_root=root, config=CONFIG, health_report=health)
    assert report["sample_eligible"] is True
    assert report["genes"][0]["status"] == "lost"
    assert report["genes"][1]["status"] == "concentrated"
    assert report["causal_effect_claim_authorized"] is False
    assert report["interpretation"] == "retention-screen-only-no-causal-effect-claim"


def test_gene_persistence_without_health_report_is_diagnostic_only(tmp_path: Path) -> None:
    cfg = load_config(CONFIG)
    width = ParametricPolicy.genome_size_for_config(cfg)
    root = tmp_path / "panel"
    seed_dir = root / "seed_1"
    seed_dir.mkdir(parents=True)
    genotype = np.full((8, width), 0.25, dtype=np.float32)
    _checkpoint(seed_dir / "checkpoint_00000001.npz", tick=1, genotype=genotype)
    _checkpoint(seed_dir / "checkpoint_00000002.npz", tick=2, genotype=genotype)
    (seed_dir / "summary.json").write_text(json.dumps({"mean_generation": 0.0}), encoding="utf-8")

    report = build_report(source_root=root, config=CONFIG)
    assert report["sample_eligible"] is False
    assert report["interpretation"] == "sample-ineligible-for-gene-persistence-interpretation"
    assert report["causal_effect_claim_authorized"] is False

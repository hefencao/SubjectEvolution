from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from se.cfg import load_config, validate_config
from se.knowledge import (
    ACQUISITION_TRANSFER,
    KnowledgeOutcomePlan,
    KnowledgeSystem,
    OUTCOME_STATUS_SUCCESS,
)
from se.runtime.interest_feedback import commit_knowledge_verification_interest
from se.subjects.social import SocialSystem

ROOT = Path(__file__).resolve().parents[1]


def _config():
    cfg = load_config(
        ROOT / "studies" / "d1x_interest_feedback_network_v1" / "frozen" / "d1v" / "source_config.json"
    )
    cfg = replace(
        cfg,
        social=replace(
            cfg.social,
            relation_update_schema="delayed-multichannel-interest-v2",
            trust_gain_share=0.0,
            trust_loss_failed=0.0,
            interest_feedback_window_ticks=4,
            interest_feedback_learning_rate=0.1,
            interest_feedback_min_material=0.5,
            knowledge_interest_window_ticks=8,
            knowledge_interest_learning_rate=0.1,
            knowledge_interest_min_evidence=0.25,
        ),
    )
    validate_config(cfg)
    return cfg


def test_verified_transferred_copy_publishes_long_horizon_partner_credit(tmp_path: Path) -> None:
    cfg = _config()
    system = KnowledgeSystem(
        cfg,
        tmp_path / "knowledge",
        initial_entity_ids=np.asarray([1, 2], dtype=np.uint64),
        initial_subject_ids=np.asarray([101, 202], dtype=np.uint64),
        initial_knowledge_capacities=np.asarray([4096, 4096], dtype=np.int64),
    )
    outcome = np.zeros(5, dtype=np.float32)
    content_id = system.catalog.append(
        parent_content_id=0,
        context_key=1,
        action_id=0,
        outcome_vector=outcome,
        encoded_bytes=64,
        created_tick=1,
        source_subject_id=202,
    )
    system.arena.append(
        holder_subject_id=101,
        content_id=content_id,
        source_subject_id=202,
        confidence=0.8,
        sample_count=0,
        created_tick=1,
        last_verified_tick=0,
        encoded_bytes=64,
        outcome_mean=outcome,
        acquisition_kind=ACQUISITION_TRANSFER,
    )
    plan = KnowledgeOutcomePlan(
        tick=20,
        carrier_indices=np.asarray([0], dtype=np.int32),
        entity_ids=np.asarray([1], dtype=np.uint64),
        holder_subject_ids=np.asarray([101], dtype=np.uint64),
        context_keys=np.asarray([1], dtype=np.uint64),
        action_ids=np.asarray([0], dtype=np.int16),
        statuses=np.asarray([OUTCOME_STATUS_SUCCESS], dtype=np.uint8),
        failure_reasons=np.asarray([0], dtype=np.uint8),
        outcome_vectors=np.zeros((1, 5), dtype=np.float32),
    )
    system.commit_outcomes(
        plan,
        energy=np.asarray([10.0, 10.0], dtype=np.float32),
        alive=np.asarray([True, True]),
        knowledge_capacities=np.asarray([4096, 4096], dtype=np.int64),
    )
    audit = system.last_verification_credit_audit
    assert audit.size == 1
    assert int(audit.source_subject_ids[0]) == 202
    assert float(audit.signed_quality[0]) == 1.0
    assert int(audit.delay_ticks[0]) == 19

    social = SocialSystem(cfg, 2)
    social.set_effective_capacities(
        np.asarray([0, 1], dtype=np.int32), np.asarray([4, 4], dtype=np.int32)
    )
    committed = commit_knowledge_verification_interest(
        social,
        audit,
        alive=np.asarray([True, True]),
        primary_subject_ids=np.asarray([101, 202], dtype=np.uint64),
        tick=20,
    )
    assert committed == 1
    slot = social._relation_slot(0, 1)
    assert slot >= 0
    assert float(social.interest_knowledge_evidence[0, slot]) > 0.0

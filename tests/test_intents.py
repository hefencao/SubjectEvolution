import numpy as np

from subject_evolution.intents import build_intents
from subject_evolution.policy import PolicyDecision


def test_intent_ids_keep_scalar_tick_and_stable_id_encoding() -> None:
    active = np.asarray([3, 1], dtype=np.int32)
    stable_ids = np.asarray([11, 22, 33, 44], dtype=np.uint64)
    decision = PolicyDecision(
        action=np.asarray([0, 4], dtype=np.int16),
        probability=np.asarray([0.4, 0.6], dtype=np.float32),
        entropy=np.zeros(2, dtype=np.float32),
        direction_x=np.zeros(2, dtype=np.float32),
        direction_y=np.zeros(2, dtype=np.float32),
        selected_partner=np.asarray([-1, 0], dtype=np.int32),
        logits=np.zeros((2, 8), dtype=np.float32),
    )
    tick = (1 << 32) + 17

    proposer_subject_id = np.asarray([1001, 1002], dtype=np.uint64)
    controller_kind = np.asarray([0, 1], dtype=np.uint8)
    intents = build_intents(
        active,
        stable_ids,
        decision,
        tick,
        proposer_subject_id=proposer_subject_id,
        controller_kind=controller_kind,
    )

    expected = np.asarray(
        [((tick << 32) ^ int(entity_id)) & 0xFFFFFFFFFFFFFFFF for entity_id in stable_ids[active]],
        dtype=np.uint64,
    )
    np.testing.assert_array_equal(intents.carrier_id, stable_ids[active])
    np.testing.assert_array_equal(intents.intent_id, expected)
    np.testing.assert_array_equal(intents.proposer_subject_id, proposer_subject_id)
    np.testing.assert_array_equal(intents.controller_kind, controller_kind)

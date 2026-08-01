from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from se.cfg import load_config, validate_config
from se.subject_vm import (
    LEGACY_COMPONENT_DISPOSITIONS,
    PRIMARY_OPTIONAL_ACTION_ROUTE_OWNER,
    ROUTING_OWNERSHIP_SCHEMA,
    routing_ownership_manifest,
)
from se.subject_vm import (
    SUBJECT_VM_ACTIVATION_SCHEMA,
    SUBJECT_VM_INPUT_PORT_SCHEMA,
    SUBJECT_VM_OUTPUT_PORT_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE2_SCHEMA,
    SubjectVMActivationConfig,
    SubjectVMConfig,
    SubjectVMRegionConfig,
)


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_VM = ROOT / "src/se/subject_vm"


def _stage2_config() -> SubjectVMConfig:
    periods = (1, 2, 4, 8)
    return SubjectVMConfig(
        enabled=True,
        schema=SUBJECT_VM_STAGE2_SCHEMA,
        node_state_width=3,
        regions=tuple(
            SubjectVMRegionConfig(
                name=name, node_capacity=4, edge_capacity=4, update_period=period
            )
            for name, period in zip(SUBJECT_VM_REGION_NAMES, periods, strict=True)
        ),
        activation=SubjectVMActivationConfig(
            schema=SUBJECT_VM_ACTIVATION_SCHEMA,
            input_port_schema=SUBJECT_VM_INPUT_PORT_SCHEMA,
            output_port_schema=SUBJECT_VM_OUTPUT_PORT_SCHEMA,
            activation_clip=8.0,
            output_clip=8.0,
        ),
    )


def _base_with_stage2():
    cfg = load_config(ROOT / "configs/mvp_small.json")
    return replace(cfg, subject_vm=_stage2_config())


def test_legacy_component_disposition_is_explicit_and_machine_readable() -> None:
    manifest = routing_ownership_manifest()
    assert manifest["schema"] == ROUTING_OWNERSHIP_SCHEMA
    assert manifest["primary_optional_action_route_owner"] == PRIMARY_OPTIONAL_ACTION_ROUTE_OWNER
    by_name = {item.component: item for item in LEGACY_COMPONENT_DISPOSITIONS}
    assert by_name["latent-router"].disposition == "retained-fixed-cognition-baseline"
    assert by_name["latent-router"].may_coexecute_with_stage2 is False
    assert by_name["working-memory-router"].may_coexecute_with_stage2 is False
    assert by_name["knowledge-provenance-store"].may_coexecute_with_stage2 is True
    assert by_name["functional-modules"].may_coexecute_with_stage2 is True


@pytest.mark.parametrize(
    ("changes", "component"),
    [
        ({"policy_influence_enabled": True}, "knowledge-policy-residual"),
        (
            {
                "policy_influence_enabled": True,
                "latent_policy_enabled": True,
                "schema": "dynamic-knowledge-latent-v1",
                "policy_residual_schema": "quantized-variable-latent-residual-v1",
            },
            "latent-router",
        ),
        (
            {
                "policy_influence_enabled": True,
                "latent_policy_enabled": True,
                "working_memory_enabled": True,
                "schema": "dynamic-knowledge-latent-v1",
                "policy_residual_schema": "quantized-variable-latent-residual-v1",
            },
            "working-memory-router",
        ),
        (
            {
                "policy_influence_enabled": True,
                "latent_policy_enabled": True,
                "sparse_selection_enabled": True,
                "schema": "dynamic-knowledge-latent-v1",
                "policy_residual_schema": "quantized-variable-latent-residual-v1",
            },
            "sparse-selection-router",
        ),
    ],
)
def test_stage2_rejects_parallel_legacy_action_routes(changes: dict[str, object], component: str) -> None:
    cfg = _base_with_stage2()
    knowledge = replace(cfg.knowledge, **changes)
    with pytest.raises(ValueError, match=component):
        validate_config(replace(cfg, knowledge=knowledge))


def test_stage2_allows_objective_knowledge_store_without_policy_residual() -> None:
    cfg = _base_with_stage2()
    knowledge = replace(
        cfg.knowledge,
        enabled=True,
        schema="dynamic-knowledge-k1-v1",
        initial_content_count=0,
        holder_capacity_bytes=64,
        policy_influence_enabled=False,
    )
    validate_config(replace(cfg, knowledge=knowledge))


def test_subject_vm_does_not_import_legacy_domain_implementations() -> None:
    forbidden = (
        "se.knowledge",
        "..knowledge",
        "se.differentiation",
        "..differentiation",
        "se.subjects",
        "..subjects",
        "se.social",
        "..social",
    )
    for path in SUBJECT_VM.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} imports forbidden legacy domain {token}"

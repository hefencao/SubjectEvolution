"""Partitioned unified Subject Graph VM Stage-1 public boundary."""
from .config import (
    SUBJECT_VM_DISABLED_SCHEMA,
    SUBJECT_VM_REGION_NAMES,
    SUBJECT_VM_STAGE1_SCHEMA,
    SubjectVMConfig,
    SubjectVMRegionConfig,
    load_subject_vm_config,
    strip_disabled_subject_vm_section,
    validate_subject_vm_config,
)
from .lifecycle import SubjectVMMutationPlan, compact_rows
from .runtime import (
    STAGE1_DEVICE_CONTRACT,
    SubjectVMDeviceContract,
    SubjectVMRuntime,
)
from .storage import SubjectVMRegionUsage, SubjectVMStorage

__all__ = [
    "STAGE1_DEVICE_CONTRACT",
    "SUBJECT_VM_DISABLED_SCHEMA",
    "SUBJECT_VM_REGION_NAMES",
    "SUBJECT_VM_STAGE1_SCHEMA",
    "SubjectVMConfig",
    "SubjectVMDeviceContract",
    "SubjectVMMutationPlan",
    "SubjectVMRegionConfig",
    "SubjectVMRegionUsage",
    "SubjectVMRuntime",
    "SubjectVMStorage",
    "compact_rows",
    "load_subject_vm_config",
    "strip_disabled_subject_vm_section",
    "validate_subject_vm_config",
]

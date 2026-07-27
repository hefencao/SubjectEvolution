"""Native GUI interface: protocol, publisher, reader, and runner."""

from .attachment import (
    RealtimePublisherAttachment,
    attach_realtime_publisher,
    realtime_publisher_session,
)
from .protocol import (
    BridgeLayout,
    ENTITY_DTYPE,
    MANIFEST_SCHEMA,
    PROTOCOL_SCHEMA,
    default_manifest_path,
)
from .publisher import SharedFramePublisher
from .reader import FrameSnapshot, SharedFrameError, SharedFrameReader

__all__ = [
    "BridgeLayout",
    "ENTITY_DTYPE",
    "FrameSnapshot",
    "MANIFEST_SCHEMA",
    "PROTOCOL_SCHEMA",
    "RealtimePublisherAttachment",
    "SharedFrameError",
    "SharedFramePublisher",
    "SharedFrameReader",
    "attach_realtime_publisher",
    "default_manifest_path",
    "realtime_publisher_session",
]

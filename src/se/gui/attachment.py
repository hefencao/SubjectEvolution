"""Lifecycle-safe attachment of a frame publisher to one Simulation instance."""

from __future__ import annotations

from contextlib import contextmanager
from types import MethodType
from typing import Any, Callable, Iterator

from .publisher import SharedFramePublisher


_ATTACHMENT_ATTRIBUTE = "_se_gui_attachment"


class RealtimePublisherAttachment:
    """Attach a publisher without changing the Simulation class definition."""

    def __init__(
        self,
        simulation: Any,
        publisher: SharedFramePublisher,
        *,
        publish_initial: bool = True,
    ) -> None:
        existing = getattr(simulation, _ATTACHMENT_ATTRIBUTE, None)
        if existing is not None and getattr(existing, "active", False):
            raise RuntimeError("a realtime GUI publisher is already attached")
        self.simulation = simulation
        self.publisher = publisher
        self.original_step = simulation.step
        self.active = True

        if publish_initial:
            publisher.publish(simulation)

        attachment = self

        def wrapped_step(instance: Any) -> Any:
            stats = attachment.original_step()
            attachment.publisher.maybe_publish(instance)
            return stats

        self.wrapped_step = MethodType(wrapped_step, simulation)
        simulation.step = self.wrapped_step
        setattr(simulation, _ATTACHMENT_ATTRIBUTE, self)

    def detach(self) -> None:
        if not self.active:
            return
        self.active = False
        if self.simulation.step is self.wrapped_step:
            self.simulation.step = self.original_step
        if getattr(self.simulation, _ATTACHMENT_ATTRIBUTE, None) is self:
            delattr(self.simulation, _ATTACHMENT_ATTRIBUTE)

    def close(self) -> None:
        self.detach()
        self.publisher.close()

    def __enter__(self) -> "RealtimePublisherAttachment":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def attach_realtime_publisher(
    simulation: Any,
    publisher: SharedFramePublisher,
    *,
    publish_initial: bool = True,
) -> Callable[[], None]:
    """Backward-compatible helper returning a detach callback."""
    attachment = RealtimePublisherAttachment(
        simulation, publisher, publish_initial=publish_initial
    )
    return attachment.detach


@contextmanager
def realtime_publisher_session(
    simulation: Any,
    publisher: SharedFramePublisher,
    *,
    publish_initial: bool = True,
) -> Iterator[RealtimePublisherAttachment]:
    attachment = RealtimePublisherAttachment(
        simulation, publisher, publish_initial=publish_initial
    )
    try:
        yield attachment
    finally:
        attachment.close()


__all__ = [
    "RealtimePublisherAttachment",
    "attach_realtime_publisher",
    "realtime_publisher_session",
]

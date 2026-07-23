"""Copy the relevant lines into the existing subject_evolution main path."""

from pathlib import Path

from .eco_shm_bridge import (
    SharedFramePublisher,
    attach_realtime_publisher,
)


def enable_realtime_view(simulation):
    # subject_evolution.py and eco_shm_bridge.py are in the same directory.
    stream_path = Path(__file__).with_name("eco_live.bin")

    publisher = SharedFramePublisher.from_simulation(
        simulation,
        path=stream_path,
        every_ticks=2,
    )

    detach = attach_realtime_publisher(
        simulation,
        publisher,
        publish_initial=True,
    )

    return publisher, detach


# Example:
#
# simulation = Simulation(cfg, output, backend=args.backend)
# publisher, detach = enable_realtime_view(simulation)
# try:
#     simulation.run()
# finally:
#     detach()
#     publisher.close()

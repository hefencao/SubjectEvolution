from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import tempfile

import numpy as np


BRIDGE_PATH = (
    Path(__file__).resolve().parents[1]
    / "python"
    / "eco_shm_bridge.py"
)

spec = importlib.util.spec_from_file_location(
    "eco_shm_bridge",
    BRIDGE_PATH,
)
assert spec is not None
assert spec.loader is not None

bridge = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = bridge
spec.loader.exec_module(bridge)


def main() -> None:
    assert bridge.HEADER.size == 256
    assert bridge.SLOT_HEADER.size == 64
    assert bridge.ENTITY_DTYPE.itemsize == 72
    assert bridge.PUBLISHED_META_OFFSET == 72

    layout = bridge.BridgeLayout(
        grid_x=8,
        grid_y=4,
        max_entities=16,
        world_width=100.0,
        world_height=50.0,
        max_energy=10.0,
    )

    assert layout.resource_bytes == 4 * 8 * 4 * 4
    assert layout.hazard_bytes == 8 * 4 * 4
    assert layout.slot_size % 64 == 0

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "eco_live.bin"
        publisher = bridge.SharedFramePublisher(
            layout,
            path=path,
            every_ticks=1,
        )

        raw = path.read_bytes()[:256]
        fields = bridge.HEADER.unpack(raw)

        assert fields[0] == bridge.MAGIC
        assert fields[1] == bridge.VERSION
        assert fields[3] == bridge.SLOT_COUNT
        assert fields[4] == 16
        assert fields[5] == 8
        assert fields[6] == 4
        assert fields[10] == 72
        assert fields[11] == layout.slot_size

        published_slot, sequence, tick = struct.unpack_from(
            "<IIQ",
            raw,
            bridge.PUBLISHED_META_OFFSET,
        )
        assert published_slot == 0
        assert sequence == 0
        assert tick == 0

        publisher.close()

    print("python protocol layout: ok")


if __name__ == "__main__":
    main()

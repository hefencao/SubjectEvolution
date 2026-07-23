#include "eco/protocol.hpp"

#include <cassert>
#include <cstddef>
#include <cstdint>

int main() {
    static_assert(sizeof(eco::FileHeader) == 256);
    static_assert(sizeof(eco::SlotHeader) == 64);
    static_assert(sizeof(eco::EntitySample) == 72);

    assert(
        offsetof(
            eco::FileHeader,
            published_slot
        ) == 72
    );
    assert(
        offsetof(
            eco::FileHeader,
            published_sequence
        ) == 76
    );
    assert(
        offsetof(
            eco::FileHeader,
            last_tick
        ) == 80
    );

    return 0;
}

#pragma once

#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace eco {

inline constexpr std::array<char, 8> kProtocolMagic{
    'E', 'C', 'O', 'G', 'A', 'M', 'E', '1'
};

inline constexpr std::uint32_t kProtocolVersion = 1;
inline constexpr std::uint32_t kHeaderSize = 256;
inline constexpr std::uint32_t kSlotHeaderSize = 64;
inline constexpr std::uint32_t kDefaultSlotCount = 3;
inline constexpr std::uint8_t kNoAction = 255;

enum class Action : std::uint8_t {
    Rest = 0,
    MoveResource = 1,
    MoveSocial = 2,
    Harvest = 3,
    Share = 4,
    Signal = 5,
    Reproduce = 6,
    Flee = 7,
    None = kNoAction
};

#pragma pack(push, 1)

struct FileHeader {
    char magic[8];
    std::uint32_t version;
    std::uint32_t header_size;
    std::uint32_t slot_count;
    std::uint32_t max_entities;
    std::uint32_t grid_x;
    std::uint32_t grid_y;
    float world_width;
    float world_height;
    float max_energy;
    std::uint32_t entity_stride;
    std::uint64_t slot_size;
    std::uint64_t resource_bytes;
    std::uint64_t hazard_bytes;
    std::uint32_t published_slot;
    std::uint32_t published_sequence;
    std::uint64_t last_tick;
    std::uint8_t reserved[168];
};

struct SlotHeader {
    std::uint32_t sequence_begin;
    std::uint32_t sequence_end;
    std::uint64_t tick;
    std::uint32_t entity_count;
    std::uint32_t flags;
    std::uint64_t monotonic_ns;
    std::uint8_t reserved[32];
};

struct EntitySample {
    std::uint64_t entity_id;
    std::uint64_t group_id;
    std::uint64_t lineage_id;
    std::uint64_t target_id;

    float x;
    float y;
    float vx;
    float vy;
    float energy;
    float integrity;
    float fertility;
    float age_fraction;

    std::uint32_t generation;
    std::uint8_t action;
    std::uint8_t action_success;
    std::uint16_t flags;
};

#pragma pack(pop)

static_assert(sizeof(FileHeader) == kHeaderSize);
static_assert(sizeof(SlotHeader) == kSlotHeaderSize);
static_assert(sizeof(EntitySample) == 72);

struct Frame {
    FileHeader layout{};
    std::uint64_t tick = 0;
    std::uint64_t monotonic_ns = 0;
    std::vector<float> resources;
    std::vector<float> hazard;
    std::vector<EntitySample> entities;

    [[nodiscard]] std::size_t cell_count() const noexcept {
        return static_cast<std::size_t>(layout.grid_x) *
               static_cast<std::size_t>(layout.grid_y);
    }

    void clear() {
        tick = 0;
        monotonic_ns = 0;
        resources.clear();
        hazard.clear();
        entities.clear();
    }
};

inline bool has_valid_magic(const FileHeader& header) noexcept {
    return std::memcmp(
        header.magic,
        kProtocolMagic.data(),
        kProtocolMagic.size()
    ) == 0;
}

inline void require_little_endian() {
    if constexpr (std::endian::native != std::endian::little) {
        throw std::runtime_error(
            "eco shared-memory protocol currently requires little-endian"
        );
    }
}

}  // namespace eco

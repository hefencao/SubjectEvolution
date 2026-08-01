#include "eco/shared_reader.hpp"

#include <atomic>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace eco {
namespace {

template <typename T>
T copy_object(const std::byte* source) {
    T value{};
    std::memcpy(&value, source, sizeof(T));
    return value;
}

bool same_publication(
    const FileHeader& left,
    const FileHeader& right
) noexcept {
    return left.published_slot == right.published_slot &&
           left.published_sequence == right.published_sequence &&
           left.last_tick == right.last_tick;
}

}  // namespace

SharedFrameReader::SharedFrameReader(std::filesystem::path path)
    : path_(std::move(path)) {
    require_little_endian();
}

void SharedFrameReader::invalidate(std::string message) {
    last_error_ = std::move(message);
    mapping_.close();
    last_sequence_ = 0;
}

bool SharedFrameReader::ensure_open() {
    if (mapping_.is_open()) {
        return true;
    }

    if (!mapping_.open_read_only(path_)) {
        last_error_ = "waiting for shared-memory file: " + path_.string();
        return false;
    }

    if (mapping_.size() < sizeof(FileHeader)) {
        invalidate("shared-memory file is smaller than FileHeader");
        return false;
    }

    const FileHeader header =
        copy_object<FileHeader>(mapping_.data());

    if (!validate_layout(header)) {
        mapping_.close();
        return false;
    }

    last_error_.clear();
    return true;
}

bool SharedFrameReader::validate_layout(const FileHeader& header) {
    if (!has_valid_magic(header)) {
        last_error_ = "shared-memory magic does not match ECOGAME1";
        return false;
    }

    if (header.version != kProtocolVersion) {
        last_error_ = "unsupported shared-memory protocol version";
        return false;
    }

    if (header.header_size != sizeof(FileHeader) ||
        header.entity_stride != sizeof(EntitySample)) {
        last_error_ = "shared-memory structure layout mismatch";
        return false;
    }

    if (header.slot_count < 2 ||
        header.slot_count > 16 ||
        header.grid_x == 0 ||
        header.grid_y == 0 ||
        header.max_entities == 0 ||
        header.slot_size < sizeof(SlotHeader)) {
        last_error_ = "shared-memory header contains invalid dimensions";
        return false;
    }

    const std::uint64_t required =
        static_cast<std::uint64_t>(header.header_size) +
        static_cast<std::uint64_t>(header.slot_count) *
            header.slot_size;

    if (required > mapping_.size()) {
        last_error_ = "shared-memory file is truncated";
        return false;
    }

    const std::uint64_t cell_count =
        static_cast<std::uint64_t>(header.grid_x) *
        static_cast<std::uint64_t>(header.grid_y);

    if (header.resource_bytes !=
            cell_count * 4ULL * sizeof(float) ||
        header.hazard_bytes !=
            cell_count * sizeof(float)) {
        last_error_ = "shared-memory resource layout mismatch";
        return false;
    }

    const std::uint64_t minimum_slot =
        sizeof(SlotHeader) +
        header.resource_bytes +
        header.hazard_bytes +
        static_cast<std::uint64_t>(header.max_entities) *
            sizeof(EntitySample);

    if (minimum_slot > header.slot_size) {
        last_error_ = "shared-memory slot does not fit declared payload";
        return false;
    }

    return true;
}

bool SharedFrameReader::read_latest(Frame& output) {
    if (!ensure_open()) {
        return false;
    }

    for (int attempt = 0; attempt < 4; ++attempt) {
        const FileHeader before =
            copy_object<FileHeader>(mapping_.data());

        if (!validate_layout(before)) {
            mapping_.close();
            return false;
        }

        const std::uint32_t sequence =
            before.published_sequence;
        const std::uint32_t slot_index =
            before.published_slot;

        if (sequence == 0 ||
            sequence == last_sequence_ ||
            slot_index >= before.slot_count) {
            return false;
        }

        const std::uint64_t slot_offset_u64 =
            static_cast<std::uint64_t>(before.header_size) +
            static_cast<std::uint64_t>(slot_index) *
                before.slot_size;

        if (slot_offset_u64 >
            std::numeric_limits<std::size_t>::max()) {
            invalidate("slot offset exceeds addressable size");
            return false;
        }

        const std::size_t slot_offset =
            static_cast<std::size_t>(slot_offset_u64);

        const std::byte* slot_base =
            mapping_.data() + slot_offset;

        const SlotHeader slot_before =
            copy_object<SlotHeader>(slot_base);

        if (slot_before.sequence_begin != sequence ||
            slot_before.sequence_end != sequence ||
            (slot_before.flags & 1U) == 0U ||
            slot_before.entity_count > before.max_entities) {
            continue;
        }

        const std::size_t cell_count =
            static_cast<std::size_t>(before.grid_x) *
            static_cast<std::size_t>(before.grid_y);

        output.resources.resize(cell_count * 4U);
        output.hazard.resize(cell_count);
        output.entities.resize(slot_before.entity_count);

        const std::byte* resource_source =
            slot_base + sizeof(SlotHeader);
        const std::byte* hazard_source =
            resource_source + before.resource_bytes;
        const std::byte* entity_source =
            hazard_source + before.hazard_bytes;

        std::memcpy(
            output.resources.data(),
            resource_source,
            static_cast<std::size_t>(before.resource_bytes)
        );

        std::memcpy(
            output.hazard.data(),
            hazard_source,
            static_cast<std::size_t>(before.hazard_bytes)
        );

        std::memcpy(
            output.entities.data(),
            entity_source,
            output.entities.size() * sizeof(EntitySample)
        );

        std::atomic_thread_fence(std::memory_order_acquire);

        const SlotHeader slot_after =
            copy_object<SlotHeader>(slot_base);
        const FileHeader after =
            copy_object<FileHeader>(mapping_.data());

        if (slot_after.sequence_begin != sequence ||
            slot_after.sequence_end != sequence ||
            slot_before.tick != slot_after.tick ||
            slot_before.entity_count != slot_after.entity_count ||
            !same_publication(before, after)) {
            continue;
        }

        output.layout = after;
        output.tick = slot_after.tick;
        output.monotonic_ns = slot_after.monotonic_ns;

        last_sequence_ = sequence;
        last_error_.clear();
        return true;
    }

    return false;
}

}  // namespace eco

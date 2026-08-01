#pragma once

#include "eco/mapped_file.hpp"
#include "eco/protocol.hpp"

#include <cstdint>
#include <filesystem>
#include <string>

namespace eco {

class SharedFrameReader {
public:
    explicit SharedFrameReader(std::filesystem::path path);

    [[nodiscard]] const std::string& last_error() const noexcept {
        return last_error_;
    }

    bool read_latest(Frame& output);

private:
    bool ensure_open();
    bool validate_layout(const FileHeader& header);
    void invalidate(std::string message);

    std::filesystem::path path_;
    MappedFile mapping_;
    std::uint32_t last_sequence_ = 0;
    std::string last_error_;
};

}  // namespace eco

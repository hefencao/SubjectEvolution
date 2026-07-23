#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>

namespace eco {

class MappedFile {
public:
    MappedFile() = default;
    ~MappedFile();

    MappedFile(const MappedFile&) = delete;
    MappedFile& operator=(const MappedFile&) = delete;

    MappedFile(MappedFile&& other) noexcept;
    MappedFile& operator=(MappedFile&& other) noexcept;

    bool open_read_only(const std::filesystem::path& path);
    void close() noexcept;

    [[nodiscard]] bool is_open() const noexcept {
        return data_ != nullptr;
    }

    [[nodiscard]] const std::byte* data() const noexcept {
        return data_;
    }

    [[nodiscard]] std::size_t size() const noexcept {
        return size_;
    }

private:
    std::byte* data_ = nullptr;
    std::size_t size_ = 0;

#ifdef _WIN32
    void* file_handle_ = nullptr;
    void* mapping_handle_ = nullptr;
#else
    int file_descriptor_ = -1;
#endif
};

}  // namespace eco

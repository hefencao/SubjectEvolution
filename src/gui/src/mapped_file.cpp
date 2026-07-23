#include "eco/mapped_file.hpp"

#include <utility>

#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#else
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace eco {

MappedFile::~MappedFile() {
    close();
}

MappedFile::MappedFile(MappedFile&& other) noexcept {
    *this = std::move(other);
}

MappedFile& MappedFile::operator=(MappedFile&& other) noexcept {
    if (this == &other) {
        return *this;
    }

    close();

    data_ = other.data_;
    size_ = other.size_;
    other.data_ = nullptr;
    other.size_ = 0;

#ifdef _WIN32
    file_handle_ = other.file_handle_;
    mapping_handle_ = other.mapping_handle_;
    other.file_handle_ = nullptr;
    other.mapping_handle_ = nullptr;
#else
    file_descriptor_ = other.file_descriptor_;
    other.file_descriptor_ = -1;
#endif

    return *this;
}

bool MappedFile::open_read_only(const std::filesystem::path& path) {
    close();

#ifdef _WIN32
    const std::wstring wide_path = path.wstring();

    HANDLE file = CreateFileW(
        wide_path.c_str(),
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        nullptr,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        nullptr
    );

    if (file == INVALID_HANDLE_VALUE) {
        return false;
    }

    LARGE_INTEGER length{};
    if (!GetFileSizeEx(file, &length) || length.QuadPart <= 0) {
        CloseHandle(file);
        return false;
    }

    HANDLE mapping = CreateFileMappingW(
        file,
        nullptr,
        PAGE_READONLY,
        0,
        0,
        nullptr
    );

    if (mapping == nullptr) {
        CloseHandle(file);
        return false;
    }

    void* view = MapViewOfFile(
        mapping,
        FILE_MAP_READ,
        0,
        0,
        0
    );

    if (view == nullptr) {
        CloseHandle(mapping);
        CloseHandle(file);
        return false;
    }

    file_handle_ = file;
    mapping_handle_ = mapping;
    data_ = static_cast<std::byte*>(view);
    size_ = static_cast<std::size_t>(length.QuadPart);
    return true;
#else
    const int descriptor = ::open(path.c_str(), O_RDONLY);
    if (descriptor < 0) {
        return false;
    }

    struct stat status {};
    if (fstat(descriptor, &status) != 0 || status.st_size <= 0) {
        ::close(descriptor);
        return false;
    }

    void* view = mmap(
        nullptr,
        static_cast<std::size_t>(status.st_size),
        PROT_READ,
        MAP_SHARED,
        descriptor,
        0
    );

    if (view == MAP_FAILED) {
        ::close(descriptor);
        return false;
    }

    file_descriptor_ = descriptor;
    data_ = static_cast<std::byte*>(view);
    size_ = static_cast<std::size_t>(status.st_size);
    return true;
#endif
}

void MappedFile::close() noexcept {
#ifdef _WIN32
    if (data_ != nullptr) {
        UnmapViewOfFile(data_);
    }

    if (mapping_handle_ != nullptr) {
        CloseHandle(static_cast<HANDLE>(mapping_handle_));
    }

    if (file_handle_ != nullptr) {
        CloseHandle(static_cast<HANDLE>(file_handle_));
    }

    file_handle_ = nullptr;
    mapping_handle_ = nullptr;
#else
    if (data_ != nullptr && size_ > 0) {
        munmap(data_, size_);
    }

    if (file_descriptor_ >= 0) {
        ::close(file_descriptor_);
    }

    file_descriptor_ = -1;
#endif

    data_ = nullptr;
    size_ = 0;
}

}  // namespace eco

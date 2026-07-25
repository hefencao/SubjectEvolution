#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace eco::multi_seed {

enum class SeedStatus : std::uint8_t {
    Waiting,
    Current,
    Completed,
    SkippedCompleted,
    Failed,
};

struct SeedProgress {
    std::int64_t seed = 0;
    SeedStatus status = SeedStatus::Waiting;
    std::uint64_t tick = 0;
    std::uint64_t target_tick = 0;
    std::uint64_t alive = 0;
    std::filesystem::path output;
    std::string detail;
};

struct ProgressSnapshot {
    std::vector<SeedProgress> seeds;
    std::optional<std::size_t> current_index;
    std::size_t completed_count = 0;
    std::uint64_t aggregate_tick = 0;
    std::uint64_t aggregate_target = 0;
    bool analysis_ready = false;
    bool process_finished = false;
    int exit_code = -1;
    std::string warning;
};

class Monitor {
public:
    Monitor(
        std::filesystem::path output,
        std::vector<std::int64_t> seeds,
        std::uint64_t target_tick
    );

    ProgressSnapshot poll(bool process_finished = false, int exit_code = -1) const;

private:
    std::filesystem::path output_;
    std::vector<std::int64_t> seeds_;
    std::uint64_t target_tick_ = 0;
};

const char* status_name(SeedStatus status);

}  // namespace eco::multi_seed

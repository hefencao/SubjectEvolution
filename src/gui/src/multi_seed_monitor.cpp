#include "eco/multi_seed_monitor.hpp"

#include <algorithm>
#include <fstream>
#include <map>
#include <regex>
#include <sstream>
#include <system_error>

namespace eco::multi_seed {
namespace {

std::string read_text(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) return {};
    std::ostringstream out;
    out << input.rdbuf();
    return out.str();
}

std::optional<std::int64_t> integer_field(const std::string& text, const std::string& key) {
    const std::regex pattern("\\\"" + key + "\\\"\\s*:\\s*(-?[0-9]+)");
    std::smatch match;
    if (!std::regex_search(text, match, pattern)) return std::nullopt;
    try { return std::stoll(match[1].str()); } catch (...) { return std::nullopt; }
}

std::optional<std::string> string_field(const std::string& text, const std::string& key) {
    const std::regex pattern("\\\"" + key + "\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"");
    std::smatch match;
    if (!std::regex_search(text, match, pattern)) return std::nullopt;
    return match[1].str();
}

struct IndexedRecord {
    SeedStatus status = SeedStatus::Completed;
    std::uint64_t tick = 0;
    std::uint64_t alive = 0;
    std::filesystem::path output;
};

std::map<std::int64_t, IndexedRecord> read_index(const std::filesystem::path& path) {
    std::map<std::int64_t, IndexedRecord> records;
    const std::string text = read_text(path);
    if (text.empty()) return records;
    const std::regex object_pattern("\\{[^\\{\\}]*\\}");
    for (std::sregex_iterator it(text.begin(), text.end(), object_pattern), end; it != end; ++it) {
        const std::string object = it->str();
        const auto seed = integer_field(object, "seed");
        if (!seed) continue;
        IndexedRecord record;
        if (const auto tick = integer_field(object, "final_tick")) record.tick = static_cast<std::uint64_t>(std::max<std::int64_t>(0, *tick));
        if (const auto alive = integer_field(object, "alive")) record.alive = static_cast<std::uint64_t>(std::max<std::int64_t>(0, *alive));
        if (const auto output = string_field(object, "output")) record.output = *output;
        if (const auto status = string_field(object, "status"); status && *status == "skipped-completed") {
            record.status = SeedStatus::SkippedCompleted;
        } else {
            record.status = SeedStatus::Completed;
        }
        records[*seed] = std::move(record);
    }
    return records;
}

void read_last_jsonl(
    const std::filesystem::path& path,
    std::uint64_t& tick,
    std::uint64_t& alive
) {
    std::ifstream input(path);
    if (!input) return;
    std::string line;
    std::string last;
    while (std::getline(input, line)) {
        if (!line.empty()) last = line;
    }
    if (last.empty()) return;
    if (const auto value = integer_field(last, "tick")) tick = static_cast<std::uint64_t>(std::max<std::int64_t>(0, *value));
    if (const auto value = integer_field(last, "alive")) alive = static_cast<std::uint64_t>(std::max<std::int64_t>(0, *value));
}

void read_summary(
    const std::filesystem::path& path,
    std::uint64_t& tick,
    std::uint64_t& alive
) {
    const std::string text = read_text(path);
    if (text.empty()) return;
    for (const char* key : {"tick", "final_tick", "ticks"}) {
        if (const auto value = integer_field(text, key)) {
            tick = static_cast<std::uint64_t>(std::max<std::int64_t>(0, *value));
            break;
        }
    }
    if (const auto value = integer_field(text, "alive")) alive = static_cast<std::uint64_t>(std::max<std::int64_t>(0, *value));
}

bool directory_nonempty(const std::filesystem::path& path) {
    std::error_code error;
    if (!std::filesystem::is_directory(path, error) || error) return false;
    return std::filesystem::directory_iterator(path, error) != std::filesystem::directory_iterator{};
}

}  // namespace

Monitor::Monitor(
    std::filesystem::path output,
    std::vector<std::int64_t> seeds,
    std::uint64_t target_tick
) : output_(std::move(output)), seeds_(std::move(seeds)), target_tick_(target_tick) {}

ProgressSnapshot Monitor::poll(bool process_finished, int exit_code) const {
    ProgressSnapshot snapshot;
    snapshot.process_finished = process_finished;
    snapshot.exit_code = exit_code;
    snapshot.aggregate_target = target_tick_ * static_cast<std::uint64_t>(seeds_.size());
    const auto indexed = read_index(output_ / "multi_seed_index.json");
    snapshot.analysis_ready = std::filesystem::exists(output_ / "long_run_analysis.json") ||
                              std::filesystem::exists(output_ / "long_run_analysis.md");

    snapshot.seeds.reserve(seeds_.size());
    bool current_assigned = false;
    for (const auto seed : seeds_) {
        SeedProgress progress;
        progress.seed = seed;
        progress.target_tick = target_tick_;
        progress.output = output_ / ("seed_" + std::to_string(seed));

        if (const auto found = indexed.find(seed); found != indexed.end()) {
            progress.status = found->second.status;
            progress.tick = found->second.tick;
            progress.alive = found->second.alive;
            if (!found->second.output.empty()) progress.output = found->second.output;
            ++snapshot.completed_count;
        } else {
            read_summary(progress.output / "summary.json", progress.tick, progress.alive);
            read_last_jsonl(progress.output / "evolution_progress.jsonl", progress.tick, progress.alive);
            const bool has_output = directory_nonempty(progress.output);
            if (!current_assigned && has_output && !process_finished) {
                progress.status = SeedStatus::Current;
                current_assigned = true;
                snapshot.current_index = snapshot.seeds.size();
            } else if (process_finished && has_output) {
                progress.status = exit_code == 0 && progress.tick >= target_tick_
                    ? SeedStatus::Completed
                    : SeedStatus::Failed;
                if (progress.status == SeedStatus::Completed) ++snapshot.completed_count;
            } else {
                progress.status = SeedStatus::Waiting;
            }
        }
        snapshot.aggregate_tick += std::min(progress.tick, target_tick_);
        snapshot.seeds.push_back(std::move(progress));
    }

    if (!snapshot.current_index && !process_finished) {
        for (std::size_t index = 0; index < snapshot.seeds.size(); ++index) {
            if (snapshot.seeds[index].status == SeedStatus::Waiting) {
                snapshot.seeds[index].status = SeedStatus::Current;
                snapshot.current_index = index;
                break;
            }
        }
    }
    if (process_finished && exit_code != 0) {
        for (auto& progress : snapshot.seeds) {
            if (progress.status == SeedStatus::Current || progress.status == SeedStatus::Waiting) {
                progress.status = SeedStatus::Failed;
                break;
            }
        }
    }
    return snapshot;
}

const char* status_name(SeedStatus status) {
    switch (status) {
    case SeedStatus::Waiting: return "waiting";
    case SeedStatus::Current: return "current";
    case SeedStatus::Completed: return "completed";
    case SeedStatus::SkippedCompleted: return "skipped-completed";
    case SeedStatus::Failed: return "failed";
    }
    return "waiting";
}

}  // namespace eco::multi_seed

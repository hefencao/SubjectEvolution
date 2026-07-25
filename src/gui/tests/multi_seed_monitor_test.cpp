#include "eco/multi_seed_monitor.hpp"

#include <cassert>
#include <filesystem>
#include <fstream>

int main() {
    namespace fs = std::filesystem;
    using namespace eco::multi_seed;
    const fs::path root = fs::temp_directory_path() / "eco_multi_seed_monitor_v22";
    std::error_code error;
    fs::remove_all(root, error);
    fs::create_directories(root / "seed_10001", error);
    {
        std::ofstream progress(root / "seed_10001/evolution_progress.jsonl");
        progress << "{\"tick\": 20, \"alive\": 900}\n";
        progress << "{\"tick\": 45, \"alive\": 880}\n";
    }
    Monitor monitor(root, {10001, 10002, 10003}, 100);
    auto snapshot = monitor.poll(false, -1);
    assert(snapshot.current_index.has_value());
    assert(snapshot.seeds[*snapshot.current_index].seed == 10001);
    assert(snapshot.seeds[0].tick == 45);
    assert(snapshot.seeds[1].status == SeedStatus::Waiting);

    {
        std::ofstream index(root / "multi_seed_index.json");
        index << "[{\"seed\":10001,\"final_tick\":100,\"alive\":850,"
                 "\"output\":\"" << (root / "seed_10001").string() << "\","
                 "\"status\":\"completed\"}]";
    }
    fs::create_directories(root / "seed_10002", error);
    { std::ofstream progress(root / "seed_10002/evolution_progress.jsonl"); progress << "{\"tick\":33,\"alive\":700}\n"; }
    snapshot = monitor.poll(false, -1);
    assert(snapshot.completed_count == 1U);
    assert(snapshot.seeds[0].status == SeedStatus::Completed);
    assert(snapshot.current_index && snapshot.seeds[*snapshot.current_index].seed == 10002);
    assert(snapshot.aggregate_tick == 133U);

    snapshot = monitor.poll(true, 1);
    assert(snapshot.process_finished);
    bool failed = false;
    for (const auto& seed : snapshot.seeds) failed = failed || seed.status == SeedStatus::Failed;
    assert(failed);

    fs::remove_all(root, error);
    return 0;
}

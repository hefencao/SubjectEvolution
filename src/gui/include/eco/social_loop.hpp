#pragma once

#include "eco/protocol.hpp"

#include <cstddef>
#include <cstdint>
#include <deque>
#include <string>
#include <unordered_map>
#include <vector>

namespace eco {

struct SocialEvent {
    std::uint64_t tick = 0;
    std::string text;
};

struct SocialStats {
    std::size_t active_agents = 0;
    std::size_t active_groups = 0;
    std::size_t relationship_edges = 0;
    std::size_t active_rumors = 0;
    float mean_trust = 0.0F;
    float mean_reputation = 0.0F;
    float mean_stress = 0.0F;
};

class SocialLoop {
public:
    void update(const Frame& frame);

    [[nodiscard]] const SocialStats& stats() const noexcept {
        return stats_;
    }

    [[nodiscard]] const std::deque<SocialEvent>& recent_events() const noexcept {
        return recent_events_;
    }

private:
    struct AgentState {
        std::uint64_t group_id = 0;
        std::uint64_t last_seen_tick = 0;
        float reputation = 0.0F;
        float stress = 0.0F;
        float belonging = 0.0F;
        bool present = false;
    };

    struct PairKey {
        std::uint64_t low = 0;
        std::uint64_t high = 0;

        bool operator==(const PairKey&) const noexcept = default;
    };

    struct PairHash {
        std::size_t operator()(const PairKey& key) const noexcept;
    };

    struct Relationship {
        float trust = 0.0F;
        float familiarity = 0.0F;
        std::uint64_t last_tick = 0;
    };

    struct Rumor {
        std::uint64_t source_id = 0;
        std::uint64_t group_id = 0;
        std::uint64_t born_tick = 0;
        float strength = 1.0F;
    };

    static PairKey make_pair_key(
        std::uint64_t first,
        std::uint64_t second
    ) noexcept;

    Relationship& touch_relationship(
        std::uint64_t first,
        std::uint64_t second,
        std::uint64_t tick,
        float trust_delta,
        float familiarity_delta
    );

    void push_event(std::uint64_t tick, std::string text);
    void update_actions(const Frame& frame);
    void update_encounters(const Frame& frame);
    void decay_and_prune(std::uint64_t tick);
    void rebuild_stats(const Frame& frame);

    std::unordered_map<std::uint64_t, AgentState> agents_;
    std::unordered_map<PairKey, Relationship, PairHash> relationships_;
    std::vector<Rumor> rumors_;
    std::deque<SocialEvent> recent_events_;
    SocialStats stats_{};

    std::uint64_t last_tick_ = 0;
};

}  // namespace eco

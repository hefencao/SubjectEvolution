#include "eco/social_loop.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <sstream>
#include <unordered_set>

#include <random>

namespace eco {
namespace {

float clamp_unit(float value) {
    return std::clamp(value, -1.0F, 1.0F);
}

float clamp_positive_unit(float value) {
    return std::clamp(value, 0.0F, 1.0F);
}

constexpr std::size_t kMaximumRelationships = 750000;
constexpr std::size_t kMaximumEncounterCandidates = 4;

std::uint64_t mix64(std::uint64_t value) {
    value ^= value >> 30U;
    value *= 0xbf58476d1ce4e5b9ULL;
    value ^= value >> 27U;
    value *= 0x94d049bb133111ebULL;
    value ^= value >> 31U;
    return value;
}

std::uint64_t spatial_key(int x, int y) {
    return
        (static_cast<std::uint64_t>(
            static_cast<std::uint32_t>(x)
        ) << 32U) |
        static_cast<std::uint32_t>(y);
}

std::string id_text(std::uint64_t id) {
    return std::to_string(
        static_cast<unsigned long long>(id)
    );
}

}  // namespace

std::size_t SocialLoop::PairHash::operator()(
    const PairKey& key
) const noexcept {
    std::uint64_t value = key.low;
    value ^= key.high +
        0x9e3779b97f4a7c15ULL +
        (value << 6U) +
        (value >> 2U);

    value ^= value >> 30U;
    value *= 0xbf58476d1ce4e5b9ULL;
    value ^= value >> 27U;
    value *= 0x94d049bb133111ebULL;
    value ^= value >> 31U;

    return static_cast<std::size_t>(value);
}

SocialLoop::PairKey SocialLoop::make_pair_key(
    std::uint64_t first,
    std::uint64_t second
) noexcept {
    if (first <= second) {
        return PairKey{first, second};
    }
    return PairKey{second, first};
}

SocialLoop::Relationship& SocialLoop::touch_relationship(
    std::uint64_t first,
    std::uint64_t second,
    std::uint64_t tick,
    float trust_delta,
    float familiarity_delta
) {
    const PairKey key = make_pair_key(first, second);
    auto iterator = relationships_.find(key);

    if (iterator == relationships_.end()) {
        if (relationships_.size() >= kMaximumRelationships) {
            // Do not let visual/gameplay acquaintance tracking consume tens
            // of millions of persistent edges.  Meaningful action edges that
            // already exist continue to update; new ambient encounters are
            // dropped when the bounded store is full.
            static thread_local Relationship overflow_sink{};
            overflow_sink = Relationship{};
            overflow_sink.last_tick = tick;
            return overflow_sink;
        }

        iterator = relationships_.try_emplace(key).first;
    }

    Relationship& relationship = iterator->second;
    relationship.trust =
        clamp_unit(relationship.trust + trust_delta);
    relationship.familiarity =
        clamp_positive_unit(
            relationship.familiarity + familiarity_delta
        );
    relationship.last_tick = tick;

    return relationship;
}


void SocialLoop::push_event(
    std::uint64_t tick,
    std::string text
) {
    recent_events_.push_front(
        SocialEvent{tick, std::move(text)}
    );

    while (recent_events_.size() > 64) {
        recent_events_.pop_back();
    }
}

void SocialLoop::update(const Frame& frame) {
    if (frame.tick == last_tick_) {
        return;
    }

    for (auto& [id, state] : agents_) {
        static_cast<void>(id);
        state.present = false;
    }

    for (const EntitySample& entity : frame.entities) {
        const auto [iterator, inserted] =
            agents_.try_emplace(entity.entity_id);

        AgentState& state = iterator->second;

        if (inserted) {
            state.group_id = entity.group_id;
            state.reputation = 0.0F;
            state.stress = 0.0F;
            state.belonging =
                entity.group_id == 0 ? 0.0F : 0.25F;

            push_event(
                frame.tick,
                "Agent " + id_text(entity.entity_id) +
                " entered the world"
            );
        } else if (state.group_id != entity.group_id) {
            std::ostringstream stream;
            stream
                << "Agent " << entity.entity_id
                << " changed group "
                << state.group_id << " → "
                << entity.group_id;
            push_event(frame.tick, stream.str());

            state.group_id = entity.group_id;
            state.belonging *= 0.5F;
        }

        state.present = true;
        state.last_seen_tick = frame.tick;

        state.reputation *= 0.9995F;
        state.stress *= 0.997F;

        if (entity.group_id != 0) {
            state.belonging = std::min(
                1.0F,
                state.belonging + 0.002F
            );
        } else {
            state.belonging *= 0.995F;
        }
    }

    for (auto& [id, state] : agents_) {
        if (!state.present &&
            state.last_seen_tick == last_tick_) {
            push_event(
                frame.tick,
                "Agent " + id_text(id) + " left the world"
            );
        }
    }

    update_actions(frame);
    update_encounters(frame);
    decay_and_prune(frame.tick);
    rebuild_stats(frame);

    last_tick_ = frame.tick;
}

void SocialLoop::update_actions(const Frame& frame) {
    for (const EntitySample& entity : frame.entities) {
        AgentState& actor = agents_[entity.entity_id];

        const Action action =
            static_cast<Action>(entity.action);
        const bool success = entity.action_success != 0;

        switch (action) {
        case Action::Share:
            if (success && entity.target_id != 0) {
                touch_relationship(
                    entity.entity_id,
                    entity.target_id,
                    frame.tick,
                    0.075F,
                    0.055F
                );

                actor.reputation =
                    std::min(1.0F, actor.reputation + 0.012F);

                auto target = agents_.find(entity.target_id);
                if (target != agents_.end()) {
                    target->second.reputation =
                        std::min(
                            1.0F,
                            target->second.reputation + 0.004F
                        );
                }

                push_event(
                    frame.tick,
                    "Agent " + id_text(entity.entity_id) +
                    " shared energy with " + id_text(entity.target_id)
                );
            } else if (!success) {
                actor.stress =
                    std::min(1.0F, actor.stress + 0.015F);
            }
            break;

        case Action::Signal:
            if (success) {
                rumors_.push_back(
                    Rumor{
                        entity.entity_id,
                        entity.group_id,
                        frame.tick,
                        1.0F
                    }
                );

                actor.reputation =
                    std::min(1.0F, actor.reputation + 0.002F);

                if (entity.target_id != 0) {
                    touch_relationship(
                        entity.entity_id,
                        entity.target_id,
                        frame.tick,
                        0.005F,
                        0.012F
                    );
                }
            }
            break;

        case Action::Reproduce:
            if (success) {
                actor.reputation =
                    std::min(1.0F, actor.reputation + 0.006F);

                push_event(
                    frame.tick,
                    "Agent " + id_text(entity.entity_id) +
                    " reproduced"
                );
            }
            break;

        case Action::Flee:
            actor.stress =
                std::min(
                    1.0F,
                    actor.stress + (success ? 0.020F : 0.035F)
                );
            break;

        case Action::Harvest:
            if (success) {
                actor.stress =
                    std::max(0.0F, actor.stress - 0.004F);
            }
            break;

        case Action::MoveSocial:
            if (success) {
                actor.belonging =
                    std::min(1.0F, actor.belonging + 0.001F);
            }
            break;

        default:
            break;
        }
    }
}

void SocialLoop::update_encounters(const Frame& frame) {
    constexpr float encounter_radius = 1.5F;
    constexpr float radius_squared =
        encounter_radius * encounter_radius;
    constexpr std::size_t max_bucket_entities = 16;
    constexpr std::size_t max_new_events = 8;

    std::unordered_map<
        std::uint64_t,
        std::vector<const EntitySample*>
    > buckets;

    buckets.reserve(frame.entities.size() / 4 + 1);

    for (const EntitySample& entity : frame.entities) {
        const int cell_x = static_cast<int>(
            std::floor(entity.x / encounter_radius)
        );
        const int cell_y = static_cast<int>(
            std::floor(entity.y / encounter_radius)
        );

        auto& bucket = buckets[spatial_key(cell_x, cell_y)];
        if (bucket.size() < max_bucket_entities) {
            bucket.push_back(&entity);
        }
    }

    std::size_t event_count = 0;

    const int neighbor_offsets[5][2] = {
        {0, 0},
        {1, 0},
        {0, 1},
        {1, 1},
        {-1, 1},
    };

    for (const auto& [key, first_bucket] : buckets) {
        const int cell_x = static_cast<int>(
            static_cast<std::uint32_t>(key >> 32U)
        );
        const int cell_y = static_cast<int>(
            static_cast<std::uint32_t>(key)
        );

        for (const auto& offset : neighbor_offsets) {
            const auto second_iterator = buckets.find(
                spatial_key(
                    cell_x + offset[0],
                    cell_y + offset[1]
                )
            );

            if (second_iterator == buckets.end()) {
                continue;
            }

            const auto& second_bucket =
                second_iterator->second;
            const bool same_bucket =
                offset[0] == 0 && offset[1] == 0;

            for (std::size_t first_index = 0;
                 first_index < first_bucket.size();
                 ++first_index) {
                const EntitySample& first =
                    *first_bucket[first_index];

                if (second_bucket.empty()) {
                    continue;
                }

                const std::size_t candidate_count =
                    std::min(
                        second_bucket.size(),
                        kMaximumEncounterCandidates
                    );
                const std::size_t start_index =
                    static_cast<std::size_t>(
                        mix64(
                            first.entity_id ^
                            frame.tick ^
                            key
                        ) % second_bucket.size()
                    );

                for (std::size_t sample = 0;
                     sample < candidate_count;
                     ++sample) {
                    const std::size_t second_index =
                        (start_index + sample) %
                        second_bucket.size();

                    if (same_bucket &&
                        second_index <= first_index) {
                        continue;
                    }

                    const EntitySample& second =
                        *second_bucket[second_index];

                    if (first.entity_id == second.entity_id) {
                        continue;
                    }

                    const float dx = first.x - second.x;
                    const float dy = first.y - second.y;

                    if (dx * dx + dy * dy > radius_squared) {
                        continue;
                    }

                    const PairKey pair = make_pair_key(
                        first.entity_id,
                        second.entity_id
                    );

                    const auto old = relationships_.find(pair);
                    if (old == relationships_.end() &&
                        relationships_.size() >=
                            kMaximumRelationships) {
                        continue;
                    }

                    const float old_familiarity =
                        old == relationships_.end()
                            ? 0.0F
                            : old->second.familiarity;

                    const bool same_group =
                        first.group_id != 0 &&
                        first.group_id == second.group_id;

                    Relationship& relationship =
                        touch_relationship(
                            first.entity_id,
                            second.entity_id,
                            frame.tick,
                            same_group ? 0.0008F : 0.0001F,
                            0.0025F
                        );

                    if (old_familiarity < 0.10F &&
                        relationship.familiarity >= 0.10F &&
                        event_count < max_new_events) {
                        push_event(
                            frame.tick,
                            "Agents " + id_text(first.entity_id) +
                            " and " + id_text(second.entity_id) +
                            " became familiar"
                        );
                        ++event_count;
                    }
                }
            }
        }
    }
}

void SocialLoop::decay_and_prune(std::uint64_t tick) {
    for (Rumor& rumor : rumors_) {
        rumor.strength *= 0.965F;
    }

    std::erase_if(
        rumors_,
        [tick](const Rumor& rumor) {
            return rumor.strength < 0.04F ||
                   tick - rumor.born_tick > 180;
        }
    );

    if (tick % 64 != 0) {
        return;
    }

    std::erase_if(
        relationships_,
        [tick](const auto& item) {
            const Relationship& relationship =
                item.second;

            return tick - relationship.last_tick > 512 &&
                   relationship.familiarity < 0.12F &&
                   std::abs(relationship.trust) < 0.12F;
        }
    );

    std::erase_if(
        agents_,
        [tick](const auto& item) {
            const AgentState& state = item.second;
            return !state.present &&
                   tick - state.last_seen_tick > 2048;
        }
    );
}

void SocialLoop::rebuild_stats(const Frame& frame) {
    SocialStats next{};
    next.active_agents = frame.entities.size();
    next.relationship_edges = relationships_.size();
    next.active_rumors = rumors_.size();

    std::unordered_set<std::uint64_t> groups;
    groups.reserve(frame.entities.size() / 8 + 1);

    double reputation_sum = 0.0;
    double stress_sum = 0.0;

    for (const EntitySample& entity : frame.entities) {
        if (entity.group_id != 0) {
            groups.insert(entity.group_id);
        }

        const auto iterator = agents_.find(entity.entity_id);
        if (iterator != agents_.end()) {
            reputation_sum += iterator->second.reputation;
            stress_sum += iterator->second.stress;
        }
    }

    next.active_groups = groups.size();

    double trust_sum = 0.0;
    for (const auto& [pair, relationship] : relationships_) {
        static_cast<void>(pair);
        trust_sum += relationship.trust;
    }

    if (!relationships_.empty()) {
        next.mean_trust = static_cast<float>(
            trust_sum /
            static_cast<double>(relationships_.size())
        );
    }

    if (!frame.entities.empty()) {
        const double divisor =
            static_cast<double>(frame.entities.size());

        next.mean_reputation =
            static_cast<float>(reputation_sum / divisor);
        next.mean_stress =
            static_cast<float>(stress_sum / divisor);
    }

    stats_ = next;
}

}  // namespace eco

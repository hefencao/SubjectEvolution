#include "eco/social_loop.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <sstream>
#include <unordered_set>

namespace eco {
namespace {

constexpr std::size_t kMinimumRelationships = 30000;
constexpr std::size_t kMaximumRelationships = 250000;
constexpr std::size_t kMinimumRumors = 512;
constexpr std::size_t kMaximumRumors = 4096;
constexpr std::size_t kMaximumEncounterSources = 12000;
constexpr std::size_t kMaximumBucketEntities = 12;

float clamp_unit(float value) {
    return std::clamp(value, -1.0F, 1.0F);
}

float clamp_positive_unit(float value) {
    return std::clamp(value, 0.0F, 1.0F);
}

std::uint64_t spatial_key(int x, int y) {
    return
        (static_cast<std::uint64_t>(
            static_cast<std::uint32_t>(x)
        ) << 32U) |
        static_cast<std::uint32_t>(y);
}

std::uint64_t mix_value(std::uint64_t value) {
    value ^= value >> 30U;
    value *= 0xbf58476d1ce4e5b9ULL;
    value ^= value >> 27U;
    value *= 0x94d049bb133111ebULL;
    value ^= value >> 31U;
    return value;
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

    return static_cast<std::size_t>(mix_value(value));
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
        if (relationships_.size() >= relationship_capacity_) {
            ++suppressed_relationships_;
            static thread_local Relationship discarded{};
            discarded.trust = 0.0F;
            discarded.familiarity = 0.0F;
            discarded.last_tick = tick;
            return discarded;
        }

        iterator = relationships_.emplace(
            key,
            Relationship{}
        ).first;
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

    while (recent_events_.size() > 32) {
        recent_events_.pop_back();
    }
}

void SocialLoop::update(const Frame& frame) {
    if (frame.tick == last_tick_) {
        return;
    }

    relationship_capacity_ = std::clamp<std::size_t>(
        frame.entities.size() * 3U,
        kMinimumRelationships,
        kMaximumRelationships
    );
    rumor_capacity_ = std::clamp<std::size_t>(
        frame.entities.size() / 20U,
        kMinimumRumors,
        kMaximumRumors
    );

    const bool first_observation = agents_.empty();
    std::size_t births = 0;
    std::size_t deaths = 0;
    std::size_t group_changes = 0;

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
            if (!first_observation) {
                ++births;
            }
        } else if (state.group_id != entity.group_id) {
            state.group_id = entity.group_id;
            state.belonging *= 0.5F;
            ++group_changes;
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
        static_cast<void>(id);
        if (!state.present &&
            state.last_seen_tick == last_tick_) {
            ++deaths;
        }
    }

    if (births > 0 || deaths > 0 || group_changes > 0) {
        std::ostringstream stream;
        stream
            << "Lifecycle: +" << births
            << " births, -" << deaths
            << " deaths, " << group_changes
            << " group changes";
        push_event(frame.tick, stream.str());
    }

    update_actions(frame);
    update_encounters(frame);
    decay_and_prune(frame.tick);
    rebuild_stats(frame);

    if (frame.tick % 128 == 0) {
        std::ostringstream stream;
        stream
            << "Trend: population " << stats_.active_agents
            << ", groups " << stats_.active_groups
            << ", edges " << stats_.relationship_edges
            << "/" << stats_.relationship_capacity
            << ", rumors " << stats_.active_rumors
            << "/" << stats_.rumor_capacity
            << ", trust " << stats_.mean_trust
            << ", stress " << stats_.mean_stress;
        push_event(frame.tick, stream.str());
    }

    last_tick_ = frame.tick;
}

void SocialLoop::update_actions(const Frame& frame) {
    std::size_t shares = 0;
    std::size_t signals = 0;
    std::size_t reproductions = 0;
    std::size_t flees = 0;
    std::size_t failures = 0;

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
                ++shares;
            } else if (!success) {
                actor.stress =
                    std::min(1.0F, actor.stress + 0.015F);
                ++failures;
            }
            break;

        case Action::Signal:
            if (success) {
                // Signals are extremely frequent.  The entertainment layer keeps
                // a representative rumor sample rather than one persistent
                // object per emission.
                const std::uint64_t sample_hash = mix_value(
                    entity.entity_id ^
                    (frame.tick * 0x9e3779b97f4a7c15ULL)
                );
                if ((sample_hash & 15U) == 0U &&
                    rumors_.size() < rumor_capacity_) {
                    rumors_.push_back(
                        Rumor{
                            entity.entity_id,
                            entity.group_id,
                            frame.tick,
                            1.0F
                        }
                    );
                }

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
                ++signals;
            } else {
                ++failures;
            }
            break;

        case Action::Reproduce:
            if (success) {
                actor.reputation =
                    std::min(1.0F, actor.reputation + 0.006F);
                ++reproductions;
            } else {
                ++failures;
            }
            break;

        case Action::Flee:
            actor.stress =
                std::min(
                    1.0F,
                    actor.stress + (success ? 0.020F : 0.035F)
                );
            ++flees;
            if (!success) {
                ++failures;
            }
            break;

        case Action::Harvest:
            if (success) {
                actor.stress =
                    std::max(0.0F, actor.stress - 0.004F);
            } else {
                ++failures;
            }
            break;

        case Action::MoveSocial:
            if (success) {
                actor.belonging =
                    std::min(1.0F, actor.belonging + 0.001F);
            } else {
                ++failures;
            }
            break;

        default:
            break;
        }
    }

    if ((shares + signals + reproductions + flees) > 0 &&
        (frame.tick % 32 == 0 || reproductions > 0)) {
        std::ostringstream stream;
        stream
            << "Actions: share " << shares
            << ", signal " << signals
            << ", reproduce " << reproductions
            << ", flee " << flees
            << ", failed " << failures;
        push_event(frame.tick, stream.str());
    }
}

void SocialLoop::update_encounters(const Frame& frame) {
    constexpr float encounter_radius = 1.5F;
    constexpr float radius_squared =
        encounter_radius * encounter_radius;

    std::unordered_map<
        std::uint64_t,
        std::vector<const EntitySample*>
    > buckets;

    buckets.reserve(frame.entities.size() / 8 + 1);

    for (const EntitySample& entity : frame.entities) {
        const int cell_x = static_cast<int>(
            std::floor(entity.x / encounter_radius)
        );
        const int cell_y = static_cast<int>(
            std::floor(entity.y / encounter_radius)
        );

        auto& bucket = buckets[spatial_key(cell_x, cell_y)];
        if (bucket.size() < kMaximumBucketEntities) {
            bucket.push_back(&entity);
        }
    }

    const std::size_t source_stride =
        std::max<std::size_t>(
            1,
            (frame.entities.size() +
             kMaximumEncounterSources - 1) /
                kMaximumEncounterSources
        );
    const std::size_t maximum_new_edges = std::clamp<std::size_t>(
        frame.entities.size() / 128,
        128,
        1024
    );

    std::size_t new_edges = 0;

    constexpr int neighbor_offsets[9][2] = {
        {-1, -1}, {0, -1}, {1, -1},
        {-1,  0}, {0,  0}, {1,  0},
        {-1,  1}, {0,  1}, {1,  1},
    };

    for (const EntitySample& source : frame.entities) {
        const std::uint64_t source_hash = mix_value(
            source.entity_id ^
            (frame.tick * 0x9e3779b97f4a7c15ULL)
        );
        if (source_stride > 1 &&
            source_hash % source_stride != 0) {
            continue;
        }

        const int source_x = static_cast<int>(
            std::floor(source.x / encounter_radius)
        );
        const int source_y = static_cast<int>(
            std::floor(source.y / encounter_radius)
        );

        int accepted = 0;
        for (int attempt = 0;
             attempt < 7 && accepted < 1;
             ++attempt) {
            const int offset_index = static_cast<int>(
                (source_hash + static_cast<std::uint64_t>(attempt * 5)) % 9U
            );
            const auto& offset = neighbor_offsets[offset_index];

            const auto bucket_iterator = buckets.find(
                spatial_key(
                    source_x + offset[0],
                    source_y + offset[1]
                )
            );
            if (bucket_iterator == buckets.end() ||
                bucket_iterator->second.empty()) {
                continue;
            }

            const auto& bucket = bucket_iterator->second;
            const std::size_t candidate_index =
                static_cast<std::size_t>(
                    mix_value(
                        source_hash +
                        static_cast<std::uint64_t>(attempt + 1)
                    ) % bucket.size()
                );
            const EntitySample& candidate =
                *bucket[candidate_index];

            if (candidate.entity_id == source.entity_id) {
                continue;
            }

            const float dx = source.x - candidate.x;
            const float dy = source.y - candidate.y;
            if (dx * dx + dy * dy > radius_squared) {
                continue;
            }

            const PairKey pair = make_pair_key(
                source.entity_id,
                candidate.entity_id
            );
            const auto old = relationships_.find(pair);
            const bool existing = old != relationships_.end();

            const bool same_group =
                source.group_id != 0 &&
                source.group_id == candidate.group_id;

            if (!existing) {
                if (new_edges >= maximum_new_edges ||
                    relationships_.size() >= relationship_capacity_) {
                    continue;
                }

                // Incidental cross-group proximity is not automatically a durable
                // social edge.  Meaningful actions still create edges directly.
                const std::uint64_t contact_hash = mix_value(
                    source_hash ^ candidate.entity_id
                );
                if (!same_group && (contact_hash % 16U) != 0U) {
                    continue;
                }
                if (same_group && (contact_hash % 3U) != 0U) {
                    continue;
                }
                ++new_edges;
            }

            touch_relationship(
                source.entity_id,
                candidate.entity_id,
                frame.tick,
                same_group ? 0.0009F : 0.0001F,
                existing ? 0.0011F : 0.0022F
            );
            ++accepted;
        }
    }
}

void SocialLoop::decay_and_prune(std::uint64_t tick) {
    const std::uint64_t elapsed_ticks =
        last_tick_ == 0
            ? 1
            : std::max<std::uint64_t>(1, tick - last_tick_);
    const float rumor_decay = std::pow(
        0.970F,
        static_cast<float>(elapsed_ticks)
    );

    for (Rumor& rumor : rumors_) {
        rumor.strength *= rumor_decay;
    }

    std::erase_if(
        rumors_,
        [tick](const Rumor& rumor) {
            return rumor.strength < 0.05F ||
                   tick - rumor.born_tick > 96;
        }
    );

    if (rumors_.size() > rumor_capacity_) {
        std::partial_sort(
            rumors_.begin(),
            rumors_.begin() + static_cast<std::ptrdiff_t>(rumor_capacity_),
            rumors_.end(),
            [](const Rumor& left, const Rumor& right) {
                return left.strength > right.strength;
            }
        );
        rumors_.resize(rumor_capacity_);
    }

    if (tick % 32 != 0) {
        return;
    }

    std::erase_if(
        relationships_,
        [tick](const auto& item) {
            const Relationship& relationship =
                item.second;
            const std::uint64_t age =
                tick - relationship.last_tick;

            return
                (age > 256 &&
                 relationship.familiarity < 0.08F &&
                 std::abs(relationship.trust) < 0.08F) ||
                (age > 1024 &&
                 relationship.familiarity < 0.30F) ||
                age > 4096;
        }
    );

    // If a previously larger population left a graph above the current dynamic
    // cap, discard the weakest and oldest edges first.
    if (relationships_.size() > relationship_capacity_) {
        std::vector<std::pair<PairKey, float>> ranking;
        ranking.reserve(relationships_.size());
        for (const auto& [key, relationship] : relationships_) {
            const float recency = 1.0F /
                (1.0F + static_cast<float>(tick - relationship.last_tick) * 0.01F);
            const float score =
                std::abs(relationship.trust) * 0.45F +
                relationship.familiarity * 0.45F +
                recency * 0.10F;
            ranking.emplace_back(key, score);
        }

        const std::size_t remove_count =
            relationships_.size() - relationship_capacity_;
        std::nth_element(
            ranking.begin(),
            ranking.begin() + static_cast<std::ptrdiff_t>(remove_count),
            ranking.end(),
            [](const auto& left, const auto& right) {
                return left.second < right.second;
            }
        );
        for (std::size_t index = 0; index < remove_count; ++index) {
            relationships_.erase(ranking[index].first);
        }
    }

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
    next.relationship_capacity = relationship_capacity_;
    next.active_rumors = rumors_.size();
    next.rumor_capacity = rumor_capacity_;
    next.suppressed_relationships = suppressed_relationships_;

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

std::vector<SocialNeighbor> SocialLoop::strongest_neighbors(
    std::uint64_t entity_id,
    std::size_t limit
) const {
    std::vector<SocialNeighbor> result;
    if (entity_id == 0 || limit == 0) {
        return result;
    }

    result.reserve(std::min<std::size_t>(limit * 4U, 128U));

    for (const auto& [key, relationship] : relationships_) {
        std::uint64_t neighbor_id = 0;
        if (key.low == entity_id) {
            neighbor_id = key.high;
        } else if (key.high == entity_id) {
            neighbor_id = key.low;
        } else {
            continue;
        }

        result.push_back(SocialNeighbor{
            neighbor_id,
            relationship.trust,
            relationship.familiarity,
            relationship.last_tick
        });
    }

    const auto score = [this](const SocialNeighbor& neighbor) {
        const float age = last_tick_ >= neighbor.last_tick
            ? static_cast<float>(last_tick_ - neighbor.last_tick)
            : 0.0F;
        const float recency = 1.0F / (1.0F + age * 0.02F);
        return std::abs(neighbor.trust) * 0.45F +
            neighbor.familiarity * 0.45F +
            recency * 0.10F;
    };

    const std::size_t keep = std::min(limit, result.size());
    std::partial_sort(
        result.begin(),
        result.begin() + static_cast<std::ptrdiff_t>(keep),
        result.end(),
        [&score](const SocialNeighbor& left, const SocialNeighbor& right) {
            return score(left) > score(right);
        }
    );
    result.resize(keep);
    return result;
}

}  // namespace eco

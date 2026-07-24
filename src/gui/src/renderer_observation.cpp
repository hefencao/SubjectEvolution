#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"
#include "render/renderer_state.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <chrono>
#include <deque>
#include <limits>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace eco {
using namespace render_internal;

namespace {

float wrap_coordinate(float value, float extent) {
    if (!(extent > 0.0F) || !finite_value(value)) {
        return value;
    }
    value = std::fmod(value, extent);
    if (value < 0.0F) {
        value += extent;
    }
    return value;
}

float blend_periodic_angle(float previous, float current, float alpha, float period) {
    if (!(period > 0.0F)) {
        return lerp_value(previous, current, alpha);
    }
    float delta = std::remainder(current - previous, period);
    return previous + delta * alpha;
}

void blend_group_summary(
    GroupBehaviorSummary& target,
    const GroupBehaviorSummary& sample,
    float alpha,
    float action_switch_margin,
    float world_width,
    float world_height
) {
    if (target.visual_key == 0 || target.members == 0) {
        target = sample;
        return;
    }

    const Action previous_action = target.dominant_action;
    // Spatial centers should remain selectable and visually attached to the
    // cohort even when direction/action signals use a long observation window.
    // sqrt(alpha) tracks position faster while retaining stable motion vectors.
    const float position_alpha = clamp01(std::sqrt(std::max(alpha, 0.0F)));
    target.group_id = sample.group_id;
    target.visual_key = sample.visual_key;
    target.x = wrap_coordinate(
        target.x + wrapped_delta(sample.x - target.x, world_width) * position_alpha,
        world_width
    );
    target.y = wrap_coordinate(
        target.y + wrapped_delta(sample.y - target.y, world_height) * position_alpha,
        world_height
    );
    target.mean_vx = lerp_value(target.mean_vx, sample.mean_vx, alpha);
    target.mean_vy = lerp_value(target.mean_vy, sample.mean_vy, alpha);
    target.coherence = lerp_value(target.coherence, sample.coherence, alpha);
    target.spread = lerp_value(target.spread, sample.spread, position_alpha);
    target.spread_major = lerp_value(target.spread_major, sample.spread_major, position_alpha);
    target.spread_minor = lerp_value(target.spread_minor, sample.spread_minor, position_alpha);
    target.orientation = blend_periodic_angle(
        target.orientation,
        sample.orientation,
        position_alpha,
        3.14159265358979323846F
    );
    target.active_fraction = lerp_value(
        target.active_fraction,
        sample.active_fraction,
        alpha
    );
    target.members = static_cast<std::size_t>(std::max(
        1.0F,
        std::round(lerp_value(
            static_cast<float>(target.members),
            static_cast<float>(sample.members),
            position_alpha
        ))
    ));

    for (std::size_t index = 0; index < target.action_fractions.size(); ++index) {
        target.action_fractions[index] = lerp_value(
            target.action_fractions[index],
            sample.action_fractions[index],
            alpha
        );
    }

    int best_index = 0;
    for (int index = 1; index < 8; ++index) {
        if (target.action_fractions[static_cast<std::size_t>(index)] >
            target.action_fractions[static_cast<std::size_t>(best_index)]) {
            best_index = index;
        }
    }
    int previous_index = action_index(previous_action);
    if (previous_index < 0) {
        previous_index = 0;
    }
    const float previous_fraction =
        target.action_fractions[static_cast<std::size_t>(previous_index)];
    const float best_fraction =
        target.action_fractions[static_cast<std::size_t>(best_index)];
    if (best_index != previous_index &&
        best_fraction < previous_fraction + action_switch_margin) {
        best_index = previous_index;
    }
    target.dominant_action = static_cast<Action>(best_index);
    target.dominant_action_fraction = clamp01(
        target.action_fractions[static_cast<std::size_t>(best_index)]
    );
}

void blend_action_cell(
    ActionActivityCell& target,
    const ActionActivityCell& sample,
    float alpha
) {
    for (std::size_t index = 0; index < target.weights.size(); ++index) {
        target.weights[index] = lerp_value(target.weights[index], sample.weights[index], alpha);
        target.sum_x[index] = lerp_value(target.sum_x[index], sample.sum_x[index], alpha);
        target.sum_y[index] = lerp_value(target.sum_y[index], sample.sum_y[index], alpha);
        target.sum_vx[index] = lerp_value(target.sum_vx[index], sample.sum_vx[index], alpha);
        target.sum_vy[index] = lerp_value(target.sum_vy[index], sample.sum_vy[index], alpha);
        target.sum_speed[index] = lerp_value(
            target.sum_speed[index], sample.sum_speed[index], alpha
        );
        target.samples[index] = lerp_value(target.samples[index], sample.samples[index], alpha);
    }
}

}  // namespace

void WorldRenderer::observe_frame(const Frame& frame) {
    const auto timing_start = std::chrono::steady_clock::now();

    const auto layout_changed = [this, &frame]() {
        const StreamSignature& stream = state_->stream;
        return stream.initialized && (
            frame.tick < stream.last_tick ||
            frame.layout.grid_x != stream.grid_x ||
            frame.layout.grid_y != stream.grid_y ||
            frame.layout.max_entities != stream.max_entities ||
            frame.layout.world_width != stream.world_width ||
            frame.layout.world_height != stream.world_height
        );
    };
    if (layout_changed()) {
        reset_stream_state();
    }

    state_->stream.initialized = true;
    state_->stream.last_tick = frame.tick;
    state_->stream.grid_x = frame.layout.grid_x;
    state_->stream.grid_y = frame.layout.grid_y;
    state_->stream.max_entities = frame.layout.max_entities;
    state_->stream.world_width = frame.layout.world_width;
    state_->stream.world_height = frame.layout.world_height;

    state_->observation.diagnostics = FrameDiagnostics{};

    const bool first_observation = !state_->observation.has_observed_frame;

    state_->observation.previous_positions.clear();
    state_->observation.previous_positions.swap(state_->observation.current_positions);
    state_->observation.current_positions.clear();
    state_->observation.current_positions.reserve(frame.entities.size() * 5 / 4 + 1);

    struct Candidate {
        std::uint64_t entity_id;
        float x;
        float y;
    };

    std::vector<Candidate> births;
    std::vector<Candidate> deaths;
    std::vector<Candidate> harvests;
    std::vector<Candidate> reproductions;

    births.reserve(512);
    deaths.reserve(512);
    harvests.reserve(1024);
    reproductions.reserve(512);

    struct GroupAccumulator {
        std::size_t members = 0;
        double sum_cos_x = 0.0;
        double sum_sin_x = 0.0;
        double sum_cos_y = 0.0;
        double sum_sin_y = 0.0;
        double sum_vx = 0.0;
        double sum_vy = 0.0;
        double sum_speed = 0.0;
        std::size_t active = 0;
        std::array<double, 8> action_weights{};
        double total_action_weight = 0.0;
    };

    std::unordered_map<std::uint64_t, GroupAccumulator> group_accumulators;
    group_accumulators.reserve(frame.entities.size() / 32U + 1U);
    std::array<ActionActivityCell, kActionFieldCellCount> raw_action_cells{};

    const double two_pi = 6.28318530717958647692;
    const double world_width = std::max<double>(frame.layout.world_width, 1.0);
    const double world_height = std::max<double>(frame.layout.world_height, 1.0);
    double speed_sum = 0.0;

    for (const EntitySample& entity : frame.entities) {
        if (!valid_entity_sample(entity)) {
            continue;
        }

        state_->observation.current_positions.emplace(
            entity.entity_id,
            PositionSample{entity.x, entity.y, entity.vx, entity.vy}
        );

        const float speed = std::sqrt(entity.vx * entity.vx + entity.vy * entity.vy);
        speed_sum += speed;
        if (speed > 0.01F) {
            ++state_->observation.diagnostics.moving_entities;
        }

        const Action action = static_cast<Action>(entity.action);
        switch (action) {
        case Action::Rest:
            ++state_->observation.diagnostics.rests;
            break;
        case Action::MoveResource:
            ++state_->observation.diagnostics.move_resource;
            break;
        case Action::MoveSocial:
            ++state_->observation.diagnostics.move_social;
            break;
        case Action::Flee:
            ++state_->observation.diagnostics.flees;
            break;
        default:
            break;
        }
        if (entity.action_success != 0) {
            ++state_->observation.diagnostics.successful_actions;
        }

        const int action_slot_index = action_index(action);
        if (action_slot_index >= 0 && action != Action::Rest) {
            const int column = std::clamp(
                static_cast<int>(entity.x / static_cast<float>(world_width) *
                    kActionFieldColumns),
                0,
                kActionFieldColumns - 1
            );
            const int row = std::clamp(
                static_cast<int>(entity.y / static_cast<float>(world_height) *
                    kActionFieldRows),
                0,
                kActionFieldRows - 1
            );
            ActionActivityCell& activity = raw_action_cells[
                static_cast<std::size_t>(row * kActionFieldColumns + column)
            ];
            const bool movement = action_uses_direction(action);
            const float sample_weight = entity.action_success != 0
                ? 2.4F
                : movement ? 0.58F : 0.22F;
            const std::size_t slot = static_cast<std::size_t>(action_slot_index);
            activity.weights[slot] += sample_weight;
            activity.sum_x[slot] += entity.x * sample_weight;
            activity.sum_y[slot] += entity.y * sample_weight;
            activity.samples[slot] += 1.0F;
            if (movement && speed > 1.0e-5F) {
                activity.sum_vx[slot] += entity.vx * sample_weight;
                activity.sum_vy[slot] += entity.vy * sample_weight;
                activity.sum_speed[slot] += speed * sample_weight;
            }
        }

        if (entity.group_id != 0) {
            GroupAccumulator& group = group_accumulators[entity.group_id];
            ++group.members;
            const double angle_x = two_pi * static_cast<double>(entity.x) / world_width;
            const double angle_y = two_pi * static_cast<double>(entity.y) / world_height;
            group.sum_cos_x += std::cos(angle_x);
            group.sum_sin_x += std::sin(angle_x);
            group.sum_cos_y += std::cos(angle_y);
            group.sum_sin_y += std::sin(angle_y);
            group.sum_vx += entity.vx;
            group.sum_vy += entity.vy;
            group.sum_speed += speed;
            if (action != Action::Rest && action != Action::None) {
                ++group.active;
            }
            const int index = action_index(action);
            if (index >= 0) {
                const double action_weight = entity.action_success != 0 ? 2.5 :
                    (action == Action::MoveResource || action == Action::MoveSocial ||
                     action == Action::Flee ? 0.72 : 0.30);
                group.action_weights[static_cast<std::size_t>(index)] += action_weight;
                group.total_action_weight += action_weight;
            }
        }

        if (!first_observation &&
            state_->observation.previous_positions.find(entity.entity_id) == state_->observation.previous_positions.end()) {
            ++state_->observation.diagnostics.births;
            births.push_back(Candidate{entity.entity_id, entity.x, entity.y});
        }

        if (entity.action_success != 0) {
            switch (action) {
            case Action::Harvest:
                ++state_->observation.diagnostics.harvests;
                harvests.push_back(Candidate{entity.entity_id, entity.x, entity.y});
                break;
            case Action::Reproduce:
                ++state_->observation.diagnostics.reproductions;
                reproductions.push_back(Candidate{entity.entity_id, entity.x, entity.y});
                break;
            case Action::Share:
                ++state_->observation.diagnostics.shares;
                break;
            case Action::Signal:
                ++state_->observation.diagnostics.signals;
                break;
            default:
                break;
            }
        }
    }

    state_->action_field.raw = raw_action_cells;
    const std::uint64_t action_elapsed = state_->action_field.last_tick == 0 ||
        frame.tick <= state_->action_field.last_tick
            ? 1U
            : frame.tick - state_->action_field.last_tick;
    if (!state_->action_field.initialized) {
        state_->action_field.responsive = raw_action_cells;
        state_->action_field.stable = raw_action_cells;
        state_->action_field.initialized = true;
    } else {
        const float responsive_alpha = temporal_alpha_for_half_life(4.0F, action_elapsed);
        const float stable_alpha = temporal_alpha_for_half_life(18.0F, action_elapsed);
        for (std::size_t index = 0; index < raw_action_cells.size(); ++index) {
            blend_action_cell(
                state_->action_field.responsive[index],
                raw_action_cells[index],
                responsive_alpha
            );
            blend_action_cell(
                state_->action_field.stable[index],
                raw_action_cells[index],
                stable_alpha
            );
        }
    }
    state_->action_field.last_tick = frame.tick;

    if (!frame.entities.empty()) {
        state_->observation.diagnostics.mean_speed = static_cast<float>(
            speed_sum / static_cast<double>(frame.entities.size())
        );
    }

    state_->groups.behaviors.clear();
    state_->groups.behaviors.reserve(group_accumulators.size());
    for (const auto& [group_id, aggregate] : group_accumulators) {
        if (aggregate.members == 0) {
            continue;
        }
        auto circular_position = [two_pi](double sine, double cosine, double extent) {
            double angle = std::atan2(sine, cosine);
            if (angle < 0.0) {
                angle += two_pi;
            }
            return static_cast<float>(angle / two_pi * extent);
        };

        int dominant_index = 0;
        for (int index = 1; index < 8; ++index) {
            if (aggregate.action_weights[static_cast<std::size_t>(index)] >
                aggregate.action_weights[static_cast<std::size_t>(dominant_index)]) {
                dominant_index = index;
            }
        }
        const double resultant_speed = std::sqrt(
            aggregate.sum_vx * aggregate.sum_vx +
            aggregate.sum_vy * aggregate.sum_vy
        );
        const float coherence = aggregate.sum_speed > 1.0e-8
            ? static_cast<float>(resultant_speed / aggregate.sum_speed)
            : 0.0F;
        const float dominant_fraction = aggregate.total_action_weight > 1.0e-8
            ? static_cast<float>(
                aggregate.action_weights[static_cast<std::size_t>(dominant_index)] /
                aggregate.total_action_weight
            )
            : 0.0F;

        GroupBehaviorSummary summary{};
        summary.group_id = group_id;
        summary.members = aggregate.members;
        summary.x = circular_position(
            aggregate.sum_sin_x, aggregate.sum_cos_x, world_width
        );
        summary.y = circular_position(
            aggregate.sum_sin_y, aggregate.sum_cos_y, world_height
        );
        summary.mean_vx = static_cast<float>(
            aggregate.sum_vx / static_cast<double>(aggregate.members)
        );
        summary.mean_vy = static_cast<float>(
            aggregate.sum_vy / static_cast<double>(aggregate.members)
        );
        summary.coherence = clamp01(coherence);
        summary.active_fraction = static_cast<float>(aggregate.active) /
            static_cast<float>(aggregate.members);
        summary.dominant_action = static_cast<Action>(dominant_index);
        summary.dominant_action_fraction = clamp01(dominant_fraction);
        if (aggregate.total_action_weight > 1.0e-8) {
            for (std::size_t action_index_value = 0;
                 action_index_value < summary.action_fractions.size();
                 ++action_index_value) {
                summary.action_fractions[action_index_value] = clamp01(
                    static_cast<float>(
                        aggregate.action_weights[action_index_value] /
                        aggregate.total_action_weight
                    )
                );
            }
        }
        state_->groups.behaviors.push_back(summary);
    }

    std::sort(state_->groups.behaviors.begin(), state_->groups.behaviors.end(),
        [](const GroupBehaviorSummary& left, const GroupBehaviorSummary& right) {
            if (left.members != right.members) {
                return left.members > right.members;
            }
            return left.group_id < right.group_id;
        });

    std::unordered_map<std::uint64_t, std::size_t> group_indices;
    group_indices.reserve(state_->groups.behaviors.size() * 5U / 4U + 1U);
    std::vector<double> covariance_xx(state_->groups.behaviors.size(), 0.0);
    std::vector<double> covariance_yy(state_->groups.behaviors.size(), 0.0);
    std::vector<double> covariance_xy(state_->groups.behaviors.size(), 0.0);
    for (std::size_t index = 0; index < state_->groups.behaviors.size(); ++index) {
        group_indices.emplace(state_->groups.behaviors[index].group_id, index);
    }
    for (const EntitySample& entity : frame.entities) {
        if (!valid_entity_sample(entity) || entity.group_id == 0) {
            continue;
        }
        const auto iterator = group_indices.find(entity.group_id);
        if (iterator == group_indices.end()) {
            continue;
        }
        const GroupBehaviorSummary& group = state_->groups.behaviors[iterator->second];
        const double dx = wrapped_delta(entity.x - group.x, frame.layout.world_width);
        const double dy = wrapped_delta(entity.y - group.y, frame.layout.world_height);
        covariance_xx[iterator->second] += dx * dx;
        covariance_yy[iterator->second] += dy * dy;
        covariance_xy[iterator->second] += dx * dy;
    }
    for (std::size_t index = 0; index < state_->groups.behaviors.size(); ++index) {
        GroupBehaviorSummary& group = state_->groups.behaviors[index];
        const double members = static_cast<double>(
            std::max<std::size_t>(group.members, 1U)
        );
        const double xx = covariance_xx[index] / members;
        const double yy = covariance_yy[index] / members;
        const double xy = covariance_xy[index] / members;
        const double trace = xx + yy;
        const double discriminant = std::sqrt(
            std::max(0.0, (xx - yy) * (xx - yy) + 4.0 * xy * xy)
        );
        const double lambda_major = std::max(0.0, 0.5 * (trace + discriminant));
        const double lambda_minor = std::max(0.0, 0.5 * (trace - discriminant));
        group.spread = static_cast<float>(std::sqrt(std::max(trace, 0.0)));
        group.spread_major = static_cast<float>(std::sqrt(lambda_major));
        group.spread_minor = static_cast<float>(std::sqrt(lambda_minor));
        group.orientation = static_cast<float>(0.5 * std::atan2(2.0 * xy, xx - yy));
    }


    // Preserve visual identity independently from transient simulation group ids.
    // Exact id matches win. Remaining groups are matched to the previous frame
    // by wrapped spatial distance, member count, velocity and dominant action.
    // This prevents large color jumps when a clustering pass replaces a group
    // id while the same spatial cohort continues to exist.
    const std::vector<GroupVisualAnchor> previous_visuals =
        state_->groups.previous_visuals;
    std::vector<bool> previous_used(previous_visuals.size(), false);
    std::unordered_map<std::uint64_t, std::size_t> previous_by_id;
    previous_by_id.reserve(previous_visuals.size() * 5U / 4U + 1U);
    for (std::size_t index = 0; index < previous_visuals.size(); ++index) {
        previous_by_id.emplace(previous_visuals[index].group_id, index);
    }

    state_->groups.visual_keys.clear();
    state_->groups.visual_keys.reserve(
        state_->groups.behaviors.size() * 5U / 4U + 1U
    );

    for (GroupBehaviorSummary& group : state_->groups.behaviors) {
        const auto exact = previous_by_id.find(group.group_id);
        if (exact == previous_by_id.end()) {
            continue;
        }
        const GroupVisualAnchor& previous = previous_visuals[exact->second];
        group.visual_key = previous.visual_key != 0
            ? previous.visual_key
            : group.group_id;
        previous_used[exact->second] = true;
        state_->groups.visual_keys.emplace(group.group_id, group.visual_key);
    }

    for (GroupBehaviorSummary& group : state_->groups.behaviors) {
        if (group.visual_key != 0) {
            continue;
        }

        std::size_t best_index = previous_visuals.size();
        double best_score = std::numeric_limits<double>::infinity();
        for (std::size_t index = 0; index < previous_visuals.size(); ++index) {
            if (previous_used[index]) {
                continue;
            }
            const GroupVisualAnchor& previous = previous_visuals[index];
            const double dx = wrapped_delta(
                group.x - previous.x,
                frame.layout.world_width
            );
            const double dy = wrapped_delta(
                group.y - previous.y,
                frame.layout.world_height
            );
            const double distance = std::sqrt(dx * dx + dy * dy);
            const double distance_limit = std::max(
                14.0,
                7.0 + 1.65 * static_cast<double>(
                    group.spread + previous.spread
                )
            );
            if (distance > distance_limit) {
                continue;
            }

            const double member_ratio = std::abs(std::log(
                (static_cast<double>(group.members) + 1.0) /
                (static_cast<double>(previous.members) + 1.0)
            ));
            if (member_ratio > 1.10) {
                continue;
            }

            const double velocity_delta = std::sqrt(
                std::pow(static_cast<double>(group.mean_vx - previous.mean_vx), 2.0) +
                std::pow(static_cast<double>(group.mean_vy - previous.mean_vy), 2.0)
            );
            const double action_penalty =
                group.dominant_action == previous.dominant_action ? 0.0 : 0.22;
            const double score = distance / distance_limit +
                0.62 * member_ratio +
                0.16 * std::min(velocity_delta / 0.20, 2.0) +
                action_penalty;
            if (score < best_score) {
                best_score = score;
                best_index = index;
            }
        }

        if (best_index < previous_visuals.size() && best_score < 1.58) {
            const GroupVisualAnchor& previous = previous_visuals[best_index];
            group.visual_key = previous.visual_key != 0
                ? previous.visual_key
                : previous.group_id;
            previous_used[best_index] = true;

            if (previous.group_id != group.group_id) {
                const auto old_trail = state_->groups.trails.find(previous.group_id);
                if (old_trail != state_->groups.trails.end() &&
                    state_->groups.trails.find(group.group_id) ==
                        state_->groups.trails.end()) {
                    auto node = state_->groups.trails.extract(old_trail);
                    node.key() = group.group_id;
                    state_->groups.trails.insert(std::move(node));
                }
            }
        } else {
            group.visual_key = group.group_id;
        }
        state_->groups.visual_keys.emplace(group.group_id, group.visual_key);
    }

    state_->groups.responsive_behaviors.clear();
    state_->groups.stable_behaviors.clear();
    state_->groups.responsive_behaviors.reserve(state_->groups.behaviors.size());
    state_->groups.stable_behaviors.reserve(state_->groups.behaviors.size());
    std::unordered_set<std::uint64_t> observed_visual_keys;
    observed_visual_keys.reserve(state_->groups.behaviors.size() * 5U / 4U + 1U);
    for (const GroupBehaviorSummary& group : state_->groups.behaviors) {
        const std::uint64_t temporal_key = group.visual_key != 0
            ? group.visual_key
            : group.group_id;
        observed_visual_keys.insert(temporal_key);
        GroupTemporalState& temporal = state_->groups.temporal[temporal_key];
        const std::uint64_t elapsed = temporal.last_tick == 0 ||
            frame.tick <= temporal.last_tick
                ? 1U
                : frame.tick - temporal.last_tick;
        if (temporal.last_tick == 0) {
            temporal.responsive = group;
            temporal.stable = group;
        } else {
            blend_group_summary(
                temporal.responsive,
                group,
                temporal_alpha_for_half_life(4.5F, elapsed),
                0.055F,
                frame.layout.world_width,
                frame.layout.world_height
            );
            blend_group_summary(
                temporal.stable,
                group,
                temporal_alpha_for_half_life(22.0F, elapsed),
                0.12F,
                frame.layout.world_width,
                frame.layout.world_height
            );
        }
        temporal.last_tick = frame.tick;
        state_->groups.responsive_behaviors.push_back(temporal.responsive);
        state_->groups.stable_behaviors.push_back(temporal.stable);
    }
    std::erase_if(state_->groups.temporal, [&frame, &observed_visual_keys](const auto& item) {
        return observed_visual_keys.find(item.first) == observed_visual_keys.end() &&
            frame.tick > item.second.last_tick + 256U;
    });

    state_->groups.previous_visuals.clear();
    const std::size_t visual_history_limit = std::min<std::size_t>(
        state_->groups.behaviors.size(),
        4096U
    );
    state_->groups.previous_visuals.reserve(visual_history_limit);
    for (std::size_t index = 0; index < visual_history_limit; ++index) {
        const GroupBehaviorSummary& group = state_->groups.behaviors[index];
        state_->groups.previous_visuals.push_back(GroupVisualAnchor{
            group.group_id,
            group.visual_key,
            group.x,
            group.y,
            group.spread,
            group.mean_vx,
            group.mean_vy,
            group.members,
            group.dominant_action
        });
    }

    const std::uint64_t trail_period = frame.entities.size() > 100000U ? 8U : 4U;
    if (state_->groups.last_trail_tick == 0 ||
        frame.tick >= state_->groups.last_trail_tick + trail_period) {
        const std::size_t tracked_groups = std::min<std::size_t>(
            state_->groups.stable_behaviors.size(), 2048U
        );
        std::unordered_set<std::uint64_t> observed_groups;
        observed_groups.reserve(tracked_groups * 5U / 4U + 1U);
        for (std::size_t index = 0; index < tracked_groups; ++index) {
            const GroupBehaviorSummary& group = state_->groups.stable_behaviors[index];
            observed_groups.insert(group.group_id);
            auto& trail = state_->groups.trails[group.group_id];
            if (trail.empty() ||
                frame.tick > trail.back().tick) {
                trail.push_back(GroupTrailPoint{
                    frame.tick,
                    group.x,
                    group.y,
                    group.members,
                    group.coherence,
                    group.dominant_action
                });
            }
            while (trail.size() > 56U) {
                trail.pop_front();
            }
        }
        std::erase_if(state_->groups.trails, [&frame, &observed_groups](const auto& item) {
            const auto& trail = item.second;
            return trail.empty() ||
                (observed_groups.find(item.first) == observed_groups.end() &&
                 frame.tick > trail.back().tick + 512U);
        });
        state_->groups.last_trail_tick = frame.tick;
    }

    if (!first_observation) {
        for (const auto& [entity_id, position] : state_->observation.previous_positions) {
            if (state_->observation.current_positions.find(entity_id) == state_->observation.current_positions.end()) {
                ++state_->observation.diagnostics.deaths;
                deaths.push_back(Candidate{entity_id, position.x, position.y});
            }
        }
    }

    std::erase_if(
        state_->observation.event_markers,
        [&frame](const EventMarker& marker) {
            return frame.tick < marker.tick ||
                frame.tick - marker.tick > event_ttl(marker.kind);
        }
    );

    auto append_sampled = [this, &frame](
        const std::vector<Candidate>& candidates,
        EventKind kind,
        std::size_t budget
    ) {
        if (candidates.empty() || budget == 0) {
            return;
        }

        const std::size_t stride = std::max<std::size_t>(
            1,
            (candidates.size() + budget - 1) / budget
        );
        std::size_t added = 0;

        for (const Candidate& candidate : candidates) {
            if (stride > 1 &&
                mix_id(candidate.entity_id ^ (frame.tick * 0x9e3779b97f4a7c15ULL)) % stride != 0) {
                continue;
            }

            state_->observation.event_markers.push_back(EventMarker{
                candidate.entity_id,
                frame.tick,
                candidate.x,
                candidate.y,
                kind
            });
            if (++added >= budget) {
                break;
            }
        }
    };

    append_sampled(births, EventKind::Birth, 320);
    append_sampled(deaths, EventKind::Death, 320);
    append_sampled(harvests, EventKind::Harvest, 480);
    append_sampled(reproductions, EventKind::Reproduce, 240);

    constexpr std::size_t maximum_markers = 4096;
    if (state_->observation.event_markers.size() > maximum_markers) {
        const std::size_t excess = state_->observation.event_markers.size() - maximum_markers;
        state_->observation.event_markers.erase(state_->observation.event_markers.begin(), state_->observation.event_markers.begin() + excess);
    }

    state_->observation.last_observed_tick = frame.tick;
    state_->observation.has_observed_frame = true;
    state_->performance.tick = frame.tick;
    const double elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - timing_start
    ).count();
    record_timing(
        elapsed_ms,
        state_->performance.observe_ms,
        state_->performance.observe_ema_ms
    );
}

}  // namespace eco

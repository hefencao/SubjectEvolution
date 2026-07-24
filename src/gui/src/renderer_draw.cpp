#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"
#include "render/renderer_state.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <chrono>
#include <limits>
#include <unordered_map>
#include <vector>

#include <rlgl.h>

namespace eco {
using namespace render_internal;

void WorldRenderer::draw(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    const RenderOptions& options,
    const std::vector<SocialNeighbor>& selected_neighbors
) const {
    const auto timing_start = std::chrono::steady_clock::now();
    state_->overlay_usage = OverlayUsage{};
    state_->performance.agent_instances = 0;
    state_->performance.agent_gpu_active = false;
    state_->performance.agent_gpu_available = state_->gpu_agents.available;
    state_->performance.agent_gpu_capacity = state_->gpu_agents.capacity;
    state_->performance.agent_upload_ms = 0.0;
    state_->performance.agent_draw_ms = 0.0;

    if (state_->environment.heatmap.id == 0) {
        record_timing(
            0.0,
            state_->performance.draw_ms,
            state_->performance.draw_ema_ms
        );
        return;
    }

    const RenderContext context = build_render_context(
        frame,
        camera,
        viewport,
        options,
        selected_neighbors.size()
    );
    state_->overlay_budget = context.budget;
    const float world_width = context.world_width;
    const float world_height = context.world_height;
    const RenderDetail& detail = context.detail;
    const float micro_detail = clamp01(detail.micro_weight);
    const BehaviorWeights& behavior = context.behavior;
    const auto& display_groups = select_group_behaviors(
        state_->groups, options.overlay_temporal
    );
    const auto& display_action_field = select_action_field(
        state_->action_field, options.overlay_temporal
    );
    const EntitySample* selected_entity = context.selected_entity;
    const std::uint64_t selected_group_id = context.selected_group_id;

    DrawTexturePro(
        state_->environment.heatmap,
        Rectangle{0.0F, 0.0F,
            static_cast<float>(state_->environment.heatmap.width),
            static_cast<float>(state_->environment.heatmap.height)},
        Rectangle{0.0F, 0.0F, world_width, world_height},
        Vector2{0.0F, 0.0F},
        0.0F,
        WHITE
    );

    if (options.show_grid &&
        frame.layout.grid_x <= 512 &&
        frame.layout.grid_y <= 512 &&
        camera.zoom > 2.5F) {
        const float cell_width = world_width /
            static_cast<float>(frame.layout.grid_x);
        const float cell_height = world_height /
            static_cast<float>(frame.layout.grid_y);
        const Color grid_color = Fade(BLACK, 0.22F);

        rlSetTexture(0);
        rlBegin(RL_LINES);
        rlColor4ub(grid_color.r, grid_color.g, grid_color.b, grid_color.a);
        for (std::uint32_t x = 1; x < frame.layout.grid_x; ++x) {
            const float position = static_cast<float>(x) * cell_width;
            rlVertex2f(position, 0.0F);
            rlVertex2f(position, world_height);
        }
        for (std::uint32_t y = 1; y < frame.layout.grid_y; ++y) {
            const float position = static_cast<float>(y) * cell_height;
            rlVertex2f(0.0F, position);
            rlVertex2f(world_width, position);
        }
        rlEnd();
    }

    // The raw per-frame flow field is an explicit diagnostic layer. Group
    // migration presets use temporally smoothed group vectors instead; drawing
    // the raw field implicitly made F3/F5 shimmer even with stable overlays.
    if (options.show_velocity && detail.flow_weight > 0.04F) {
        draw_flow_field(
            frame,
            camera,
            std::max(detail.flow_weight, 0.42F)
        );
    }

    if (options.show_group_landmarks) {
        draw_group_landmarks_overlay(
            frame,
            camera,
            viewport,
            detail,
            options,
            selected_group_id,
            context.budget,
            std::clamp(
                0.34F + 0.56F * detail.density_weight +
                    0.18F * detail.agent_weight,
                0.0F,
                1.0F
            )
        );
    }

    if (behavior.groups > 0.035F) {
        draw_group_history_overlay(
            frame,
            camera,
            viewport,
            detail,
            options,
            selected_group_id,
            context.budget,
            behavior.groups
        );
        state_->overlay_usage.group_markers += draw_group_behavior_overlay(
            display_groups,
            camera,
            context.budget.group_markers > state_->overlay_usage.group_markers
                ? context.budget.group_markers - state_->overlay_usage.group_markers
                : 0U,
            behavior.groups * (options.show_group_trails ? 0.42F : 0.78F),
            options.action_filter
        );
    } else if (selected_group_id != 0) {
        RenderOptions selected_group_options = options;
        selected_group_options.show_group_trails = false;
        selected_group_options.focus_selected_group = true;
        draw_group_history_overlay(
            frame,
            camera,
            viewport,
            detail,
            selected_group_options,
            selected_group_id,
            context.budget,
            0.92F
        );
    }

    const float aggregate_action_weight = behavior.actions *
        (1.0F - 0.78F * detail.micro_weight);
    if (aggregate_action_weight > 0.05F) {
        state_->overlay_usage.action_glyphs += draw_action_activity_field(
            display_action_field,
            frame.layout,
            camera,
            context.budget.action_glyphs,
            aggregate_action_weight,
            options.action_filter
        );
    }

    const float left = context.left;
    const float right = context.right;
    const float top = context.top;
    const float bottom = context.bottom;

    // Overview gets a small spatial lifecycle summary at macro/medium scales.
    // It uses compact signed ticks instead of the old city-like event circles:
    // cyan points toward net births and red toward net deaths.
    if (options.show_group_landmarks && options.show_event_markers &&
        detail.density_weight > 0.22F &&
        context.budget.event_markers > state_->overlay_usage.event_markers) {
        constexpr int columns = 18;
        constexpr int rows = 11;
        constexpr int cell_count = columns * rows;
        struct LifecycleCell {
            float births = 0.0F;
            float deaths = 0.0F;
            float sum_x = 0.0F;
            float sum_y = 0.0F;
            float total = 0.0F;
        };
        static thread_local std::array<LifecycleCell, cell_count> cells{};
        cells.fill(LifecycleCell{});

        for (const EventMarker& marker : state_->observation.event_markers) {
            if (marker.kind != EventKind::Birth && marker.kind != EventKind::Death) {
                continue;
            }
            const float age = frame.tick >= marker.tick
                ? static_cast<float>(frame.tick - marker.tick)
                : 0.0F;
            const float recency = 1.0F - clamp01(age / 72.0F);
            if (recency <= 0.02F) {
                continue;
            }
            const int column = std::clamp(
                static_cast<int>(marker.x / std::max(world_width, 1.0F) * columns),
                0,
                columns - 1
            );
            const int row = std::clamp(
                static_cast<int>(marker.y / std::max(world_height, 1.0F) * rows),
                0,
                rows - 1
            );
            LifecycleCell& cell = cells[static_cast<std::size_t>(row * columns + column)];
            if (marker.kind == EventKind::Birth) {
                cell.births += recency;
            } else {
                cell.deaths += recency;
            }
            cell.sum_x += marker.x * recency;
            cell.sum_y += marker.y * recency;
            cell.total += recency;
        }

        struct LifecycleCandidate {
            int index = 0;
            float score = 0.0F;
        };
        std::vector<LifecycleCandidate> candidates;
        candidates.reserve(cell_count);
        for (int index = 0; index < cell_count; ++index) {
            const LifecycleCell& cell = cells[static_cast<std::size_t>(index)];
            const float activity = cell.births + cell.deaths;
            if (activity < 1.4F) {
                continue;
            }
            const float imbalance = std::abs(cell.births - cell.deaths) /
                std::max(activity, 1.0e-5F);
            candidates.push_back(LifecycleCandidate{
                index,
                std::log1p(activity) * (0.45F + 0.55F * imbalance)
            });
        }
        std::sort(candidates.begin(), candidates.end(),
            [](const LifecycleCandidate& lhs, const LifecycleCandidate& rhs) {
                return lhs.score > rhs.score;
            });

        const std::size_t remaining = context.budget.event_markers -
            state_->overlay_usage.event_markers;
        const std::size_t limit = std::min<std::size_t>(
            remaining,
            std::min<std::size_t>(candidates.size(), 10U)
        );
        const float inverse_zoom = context.inverse_zoom;
        for (std::size_t candidate_index = 0; candidate_index < limit; ++candidate_index) {
            const LifecycleCell& cell = cells[
                static_cast<std::size_t>(candidates[candidate_index].index)
            ];
            if (cell.total <= 1.0e-5F) {
                continue;
            }
            const Vector2 center{
                cell.sum_x / cell.total,
                cell.sum_y / cell.total
            };
            const bool net_birth = cell.births >= cell.deaths;
            const float activity = cell.births + cell.deaths;
            const float length = std::clamp(
                5.0F + 2.1F * std::log1p(activity),
                6.0F,
                13.0F
            ) * inverse_zoom;
            const Color color = net_birth
                ? Fade(Color{74, 232, 255, 255}, 0.50F)
                : Fade(Color{255, 91, 91, 255}, 0.50F);
            const Vector2 start{
                center.x,
                center.y + (net_birth ? length * 0.48F : -length * 0.48F)
            };
            const Vector2 end{
                center.x,
                center.y + (net_birth ? -length * 0.52F : length * 0.52F)
            };
            DrawLineEx(start, end, 1.35F * inverse_zoom, color);
            const float cap = 2.5F * inverse_zoom;
            DrawLineEx(
                Vector2{end.x - cap, end.y},
                Vector2{end.x + cap, end.y},
                1.0F * inverse_zoom,
                color
            );
            ++state_->overlay_usage.event_markers;
        }
    }

    // Selected-agent relationship topology is deliberately local and bounded.
    const auto selected_position = state_->observation.current_positions.find(options.selected_entity_id);
    if (selected_position != state_->observation.current_positions.end()) {
        const Vector2 source{selected_position->second.x, selected_position->second.y};
        std::size_t relationship_count = 0;
        for (const SocialNeighbor& neighbor : selected_neighbors) {
            if (relationship_count >= context.budget.relationship_lines) {
                break;
            }
            const auto target_iterator = state_->observation.current_positions.find(neighbor.entity_id);
            if (target_iterator == state_->observation.current_positions.end()) {
                continue;
            }

            Vector2 target{target_iterator->second.x, target_iterator->second.y};
            const float dx = wrapped_delta(target.x - source.x, world_width);
            const float dy = wrapped_delta(target.y - source.y, world_height);
            target = Vector2{source.x + dx, source.y + dy};

            const Color relationship_color = neighbor.trust >= 0.0F
                ? Fade(Color{95, 230, 190, 255}, 0.28F + 0.50F * neighbor.familiarity)
                : Fade(Color{255, 92, 92, 255}, 0.28F + 0.50F * neighbor.familiarity);
            const float width = (0.7F + 1.6F * neighbor.familiarity) /
                std::max(camera.zoom, 0.001F);
            DrawLineEx(source, target, width, relationship_color);
            ++relationship_count;
        }
        state_->overlay_usage.relationship_lines = relationship_count;
    }

    if (options.show_event_markers) {
        const float event_detail = clamp01(detail.agent_weight + 0.35F * detail.micro_weight);
        // At macro scale the trend panel and density field already carry the
        // aggregate event signal. Drawing cluster circles there created false
        // "cities" and obscured resources, so spatial glyphs enter only when
        // agents themselves have become readable.
        if (event_detail >= 0.18F) {
            const std::size_t marker_budget =
                context.budget.event_markers > state_->overlay_usage.event_markers
                    ? context.budget.event_markers - state_->overlay_usage.event_markers
                    : 0U;
            std::size_t drawn = 0;

            for (auto iterator = state_->observation.event_markers.rbegin();
                 iterator != state_->observation.event_markers.rend() && drawn < marker_budget;
                 ++iterator) {
                const EventMarker& marker = *iterator;
                if (marker.x < left || marker.x > right || marker.y < top || marker.y > bottom) {
                    continue;
                }

                bool event_matches_filter = true;
                switch (options.action_filter) {
                case ActionFilterMode::All:
                    break;
                case ActionFilterMode::Movement:
                case ActionFilterMode::Social:
                    event_matches_filter = false;
                    break;
                case ActionFilterMode::Resource:
                    event_matches_filter = marker.kind == EventKind::Harvest;
                    break;
                case ActionFilterMode::Reproduction:
                    event_matches_filter = marker.kind == EventKind::Birth ||
                        marker.kind == EventKind::Reproduce;
                    break;
                case ActionFilterMode::Survival:
                    event_matches_filter = marker.kind == EventKind::Death;
                    break;
                }
                if (!event_matches_filter) {
                    continue;
                }

                const bool action_marker = marker.kind == EventKind::Harvest ||
                    marker.kind == EventKind::Reproduce;
                if (action_marker &&
                    options.behavior_overlay != BehaviorOverlayMode::Off &&
                    detail.micro_weight < 0.72F) {
                    continue;
                }

                const float age = frame.tick >= marker.tick
                    ? static_cast<float>(frame.tick - marker.tick)
                    : 0.0F;
                const float life = 1.0F - clamp01(age /
                    static_cast<float>(event_ttl(marker.kind)));
                const float radius_pixels = lerp_value(1.8F, 4.8F, micro_detail);
                const float radius = (radius_pixels + 2.0F * life) /
                    std::max(camera.zoom, 0.001F);
                const float width = lerp_value(0.8F, 1.25F, micro_detail) /
                    std::max(camera.zoom, 0.001F);
                const Vector2 center{marker.x, marker.y};
                const Color color = Fade(
                    event_color(marker.kind),
                    (0.10F + 0.48F * life) * event_detail
                );

                switch (marker.kind) {
                case EventKind::Birth:
                    DrawCircleLines(static_cast<int>(marker.x), static_cast<int>(marker.y),
                        radius, color);
                    break;
                case EventKind::Death:
                    DrawLineEx(
                        Vector2{marker.x - radius, marker.y - radius},
                        Vector2{marker.x + radius, marker.y + radius},
                        width, color
                    );
                    DrawLineEx(
                        Vector2{marker.x - radius, marker.y + radius},
                        Vector2{marker.x + radius, marker.y - radius},
                        width, color
                    );
                    break;
                case EventKind::Harvest:
                    DrawLineEx(
                        Vector2{marker.x - radius, marker.y},
                        Vector2{marker.x + radius, marker.y},
                        width, color
                    );
                    DrawLineEx(
                        Vector2{marker.x, marker.y - radius},
                        Vector2{marker.x, marker.y + radius},
                        width, color
                    );
                    break;
                case EventKind::Reproduce:
                    DrawLineEx(Vector2{center.x, center.y - radius},
                        Vector2{center.x + radius, center.y}, width, color);
                    DrawLineEx(Vector2{center.x + radius, center.y},
                        Vector2{center.x, center.y + radius}, width, color);
                    DrawLineEx(Vector2{center.x, center.y + radius},
                        Vector2{center.x - radius, center.y}, width, color);
                    DrawLineEx(Vector2{center.x - radius, center.y},
                        Vector2{center.x, center.y - radius}, width, color);
                    break;
                }
                ++drawn;
            }
            state_->overlay_usage.event_markers += drawn;
        }
    }

    static thread_local std::vector<const EntitySample*> render_entities;
    static thread_local std::vector<const EntitySample*> tile_representatives;
    static thread_local std::vector<std::uint16_t> tile_priorities;
    render_entities.clear();

    if (detail.agent_weight > 0.025F) {
        const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);
        const float padding = 12.0F * inverse_zoom;
        const float sample_detail = clamp01(
            detail.agent_weight * (0.72F + 0.28F * detail.micro_weight)
        );
        const int tile_pixels = std::clamp(
            static_cast<int>(std::lround(lerp_value(30.0F, 5.0F, sample_detail))),
            5,
            30
        );
        const std::size_t entity_budget = context.budget.agent_markers;
        const int tile_columns = std::max(
            1,
            static_cast<int>(std::ceil(viewport.width / tile_pixels))
        );
        const int tile_rows = std::max(
            1,
            static_cast<int>(std::ceil(viewport.height / tile_pixels))
        );
        const std::size_t tile_count =
            static_cast<std::size_t>(tile_columns) *
            static_cast<std::size_t>(tile_rows);
        tile_representatives.assign(tile_count, nullptr);
        tile_priorities.assign(tile_count, 0U);

        const std::size_t candidate_stride = std::max<std::size_t>(
            1,
            frame.entities.size() / std::max<std::size_t>(entity_budget * 5U, 1U)
        );

        for (const EntitySample& entity : frame.entities) {
            if (!valid_entity_sample(entity) ||
                !is_visible(entity, left, top, right, bottom, padding)) {
                continue;
            }
            const bool previously_rendered =
                state_->observation.previous_rendered_entities.find(entity.entity_id) !=
                state_->observation.previous_rendered_entities.end();
            if (candidate_stride > 1 &&
                entity.entity_id != options.selected_entity_id &&
                entity.action_success == 0 &&
                !previously_rendered &&
                mix_id(entity.entity_id) % candidate_stride != 0) {
                continue;
            }

            const Vector2 screen = GetWorldToScreen2D(
                Vector2{entity.x, entity.y},
                camera
            );
            const int tile_x = static_cast<int>(
                (screen.x - viewport.x) / static_cast<float>(tile_pixels)
            );
            const int tile_y = static_cast<int>(
                (screen.y - viewport.y) / static_cast<float>(tile_pixels)
            );
            if (tile_x < 0 || tile_x >= tile_columns ||
                tile_y < 0 || tile_y >= tile_rows) {
                continue;
            }

            const std::size_t tile_index =
                static_cast<std::size_t>(tile_y) *
                    static_cast<std::size_t>(tile_columns) +
                static_cast<std::size_t>(tile_x);
            const Action entity_action = static_cast<Action>(entity.action);
            const bool filter_match = action_matches_filter(
                entity_action, options.action_filter);
            const std::uint16_t base_priority =
                entity.entity_id == options.selected_entity_id ? 7U :
                (options.focus_selected_group && selected_group_id != 0 &&
                 entity.group_id == selected_group_id) ? 6U :
                (options.action_filter != ActionFilterMode::All && filter_match) ? 5U :
                entity.action_success != 0 ? 4U :
                entity.group_id != 0 ? 2U : 1U;
            // Preserve the previous frame's representative when semantic
            // priority is equal. This removes the apparent group-color flicker
            // caused by a different member winning the same screen tile.
            const std::uint16_t priority = static_cast<std::uint16_t>(
                base_priority * 2U + (previously_rendered ? 1U : 0U)
            );
            if (tile_priorities[tile_index] > priority) {
                continue;
            }
            if (tile_priorities[tile_index] == priority &&
                tile_representatives[tile_index] != nullptr &&
                mix_id(tile_representatives[tile_index]->entity_id) < mix_id(entity.entity_id)) {
                continue;
            }
            tile_priorities[tile_index] = priority;
            tile_representatives[tile_index] = &entity;
        }

        render_entities.reserve(std::min(tile_count, entity_budget));
        for (const EntitySample* entity : tile_representatives) {
            if (entity != nullptr) {
                render_entities.push_back(entity);
                if (render_entities.size() >= entity_budget) {
                    break;
                }
            }
        }
        state_->overlay_usage.agent_markers = render_entities.size();
        state_->observation.previous_rendered_entities.clear();
        state_->observation.previous_rendered_entities.reserve(
            render_entities.size() * 5U / 4U + 1U
        );
        for (const EntitySample* entity : render_entities) {
            state_->observation.previous_rendered_entities.insert(entity->entity_id);
        }

        const float trail_weight = options.show_velocity
            ? std::max(detail.agent_weight, 0.48F)
            : detail.micro_weight * 0.26F;
        if (trail_weight > 0.035F && !render_entities.empty()) {
            const std::size_t trail_budget = context.budget.agent_trails;
            const std::size_t trail_stride = std::max<std::size_t>(
                1,
                render_entities.size() / std::max<std::size_t>(trail_budget, 1U)
            );
            for (std::size_t index = 0; index < render_entities.size(); index += trail_stride) {
                const EntitySample* entity = render_entities[index];
                const auto previous = state_->observation.previous_positions.find(entity->entity_id);
                if (previous == state_->observation.previous_positions.end()) {
                    continue;
                }
                const float speed = std::sqrt(
                    entity->vx * entity->vx + entity->vy * entity->vy
                );
                if (!finite_value(speed) || speed < 0.025F) {
                    continue;
                }
                const Vector2 current{entity->x, entity->y};
                const Vector2 old = previous_endpoint(
                    current,
                    Vector2{previous->second.x, previous->second.y},
                    world_width,
                    world_height
                );
                if (!valid_world_position(old.x, old.y)) {
                    continue;
                }
                DrawLineEx(
                    old,
                    current,
                    lerp_value(0.55F, 1.05F, detail.micro_weight) * inverse_zoom,
                    Fade(Color{108, 229, 255, 255}, 0.30F * trail_weight)
                );
                ++state_->overlay_usage.agent_trails;
            }
        }

        const float body_radius_pixels = lerp_value(
            0.92F,
            2.65F,
            std::pow(sample_detail, 0.78F)
        );
        const float outline_radius_pixels = body_radius_pixels +
            lerp_value(0.22F, 0.92F, detail.micro_weight);
        const float body_radius = body_radius_pixels * inverse_zoom;
        const float outline_radius = outline_radius_pixels * inverse_zoom;
        const unsigned char outline_alpha = static_cast<unsigned char>(
            std::clamp(45.0F + 185.0F * detail.agent_weight, 0.0F, 230.0F)
        );
        const unsigned char body_alpha = static_cast<unsigned char>(
            std::clamp(54.0F + 191.0F * detail.agent_weight, 0.0F, 245.0F)
        );

        const float core_radius_pixels = detail.micro_weight > 0.16F
            ? lerp_value(0.28F, 0.82F, detail.micro_weight)
            : 0.0F;

        const bool gpu_markers_drawn = draw_gpu_agent_markers(
            *state_,
            frame,
            camera,
            detail,
            options,
            selected_group_id,
            render_entities,
            body_radius_pixels,
            outline_radius_pixels,
            core_radius_pixels,
            body_alpha
        );

        if (!gpu_markers_drawn) {
            const auto agent_draw_start = std::chrono::steady_clock::now();
            state_->performance.agent_gpu_active = false;
            state_->performance.agent_instances = render_entities.size();
            state_->performance.agent_gpu_capacity = state_->gpu_agents.capacity;
            state_->performance.agent_gpu_available = state_->gpu_agents.available;
            record_timing(
                0.0,
                state_->performance.agent_upload_ms,
                state_->performance.agent_upload_ema_ms
            );

            const SolidQuadBatch outline_batch = begin_solid_quad_batch();
            for (const EntitySample* entity : render_entities) {
                emit_solid_quad(
                    outline_batch,
                    entity->x - outline_radius,
                    entity->y - outline_radius,
                    entity->x + outline_radius,
                    entity->y + outline_radius,
                    Color{1, 5, 7, outline_alpha}
                );
            }
            end_solid_quad_batch();

            const SolidQuadBatch body_batch = begin_solid_quad_batch();
            for (const EntitySample* entity : render_entities) {
                const auto visual_key_iterator =
                    state_->groups.visual_keys.find(entity->group_id);
                const std::uint64_t visual_key = visual_key_iterator !=
                    state_->groups.visual_keys.end()
                        ? visual_key_iterator->second
                        : entity->group_id;
                Color color = color_for_entity_visual(
                    *entity,
                    frame.layout.max_energy,
                    visual_key
                );
                color.a = static_cast<unsigned char>(std::min<int>(color.a, body_alpha));
                if (options.focus_selected_group && selected_group_id != 0 &&
                    entity->group_id != selected_group_id &&
                    entity->entity_id != options.selected_entity_id) {
                    color.a = static_cast<unsigned char>(
                        std::min<int>(
                            color.a,
                            10 + static_cast<int>(28.0F * detail.micro_weight)
                        )
                    );
                }
                if (options.action_filter != ActionFilterMode::All &&
                    entity->entity_id != options.selected_entity_id &&
                    !action_matches_filter(
                        static_cast<Action>(entity->action),
                        options.action_filter
                    )) {
                    color.a = static_cast<unsigned char>(
                        std::min<int>(
                            color.a,
                            10 + static_cast<int>(24.0F * detail.agent_weight)
                        )
                    );
                }

                emit_solid_quad(
                    body_batch,
                    entity->x - body_radius,
                    entity->y - body_radius,
                    entity->x + body_radius,
                    entity->y + body_radius,
                    color
                );
            }
            end_solid_quad_batch();

            if (detail.micro_weight > 0.16F) {
                const float core_radius = core_radius_pixels * inverse_zoom;
                const unsigned char core_alpha = static_cast<unsigned char>(
                    210.0F * detail.micro_weight
                );
                const SolidQuadBatch core_batch = begin_solid_quad_batch();
                for (const EntitySample* entity : render_entities) {
                    unsigned char alpha = core_alpha;
                    if (options.focus_selected_group && selected_group_id != 0 &&
                        entity->group_id != selected_group_id &&
                        entity->entity_id != options.selected_entity_id) {
                        alpha = static_cast<unsigned char>(
                            std::min<int>(
                                alpha,
                                6 + static_cast<int>(12.0F * detail.micro_weight)
                            )
                        );
                    }
                    if (options.action_filter != ActionFilterMode::All &&
                        entity->entity_id != options.selected_entity_id &&
                        !action_matches_filter(
                            static_cast<Action>(entity->action),
                            options.action_filter
                        )) {
                        alpha = static_cast<unsigned char>(std::min<int>(alpha, 8));
                    }
                    emit_solid_quad(
                        core_batch,
                        entity->x - core_radius,
                        entity->y - core_radius,
                        entity->x + core_radius,
                        entity->y + core_radius,
                        Color{242, 250, 255, alpha}
                    );
                }
                end_solid_quad_batch();
            }

            const auto agent_draw_end = std::chrono::steady_clock::now();
            const double agent_draw_ms = std::chrono::duration<double, std::milli>(
                agent_draw_end - agent_draw_start
            ).count();
            record_timing(
                agent_draw_ms,
                state_->performance.agent_draw_ms,
                state_->performance.agent_draw_ema_ms
            );
        }

        const float individual_action_weight = behavior.actions *
            smooth_range(0.28F, 0.78F, detail.micro_weight);
        if (individual_action_weight > 0.05F && !render_entities.empty()) {
            const std::size_t action_budget =
                context.budget.action_glyphs > state_->overlay_usage.action_glyphs
                    ? context.budget.action_glyphs - state_->overlay_usage.action_glyphs
                    : 0U;
            std::size_t drawn_actions = 0;
            for (const EntitySample* entity : render_entities) {
                if (options.focus_selected_group && selected_group_id != 0 &&
                    entity->group_id != selected_group_id) {
                    continue;
                }
                const Action action = static_cast<Action>(entity->action);
                const bool movement = action == Action::MoveResource ||
                    action == Action::MoveSocial || action == Action::Flee;
                if (action == Action::Rest || action == Action::None ||
                    !action_matches_filter(action, options.action_filter) ||
                    (entity->action_success == 0 && !movement)) {
                    continue;
                }
                Vector2 direction{entity->vx, entity->vy};
                const auto previous =
                    state_->observation.previous_positions.find(entity->entity_id);
                if (previous != state_->observation.previous_positions.end()) {
                    direction = resolve_motion_vector(
                        direction,
                        Vector2{entity->x, entity->y},
                        Vector2{previous->second.x, previous->second.y},
                        world_width,
                        world_height
                    );
                }
                if (draw_action_glyph(
                    action,
                    Vector2{entity->x, entity->y},
                    lerp_value(3.6F, 6.2F, detail.micro_weight),
                    camera,
                    individual_action_weight *
                        (entity->action_success != 0 ? 0.90F : 0.48F),
                    direction
                )) {
                    if (++drawn_actions >= action_budget) {
                        break;
                    }
                }
            }
            state_->overlay_usage.action_glyphs += drawn_actions;
        }
    }

    DrawRectangleLinesEx(
        Rectangle{0.0F, 0.0F, world_width, world_height},
        1.5F / std::max(camera.zoom, 0.001F),
        RAYWHITE
    );

    // Selected agents are always drawn, even when macro LOD suppresses all other
    // individuals or medium sampling would otherwise discard this ID.
    if (selected_entity != nullptr) {
        const EntitySample* selected = selected_entity;
        draw_selected_environment_probe(frame, camera, options, *selected);
        {
            const float selected_radius = 10.0F /
                std::max(camera.zoom, 0.001F);
            const Vector2 center{selected->x, selected->y};

            if (selected->target_id != 0) {
                const auto target = state_->observation.current_positions.find(selected->target_id);
                if (target != state_->observation.current_positions.end()) {
                    Vector2 target_position{target->second.x, target->second.y};
                    target_position.x = center.x + wrapped_delta(
                        target_position.x - center.x,
                        world_width
                    );
                    target_position.y = center.y + wrapped_delta(
                        target_position.y - center.y,
                        world_height
                    );
                    DrawLineEx(
                        center,
                        target_position,
                        1.25F / std::max(camera.zoom, 0.001F),
                        Fade(YELLOW, 0.48F)
                    );
                }
            }

            const float body_radius = 5.5F / std::max(camera.zoom, 0.001F);
            DrawCircleV(center, body_radius * 1.45F, BLACK);
            DrawCircleV(center, body_radius, Color{255, 248, 185, 255});
            DrawCircleLines(
                static_cast<int>(center.x),
                static_cast<int>(center.y),
                selected_radius,
                YELLOW
            );
            DrawCircleLines(
                static_cast<int>(center.x),
                static_cast<int>(center.y),
                selected_radius * 1.45F,
                Fade(YELLOW, 0.52F)
            );

            const float selected_speed = std::sqrt(
                selected->vx * selected->vx + selected->vy * selected->vy
            );
            if (finite_value(selected_speed) && selected_speed > 0.001F) {
                const float dx = selected->vx / selected_speed;
                const float dy = selected->vy / selected_speed;
                const float side_x = -dy;
                const float side_y = dx;
                const float length = 13.0F / std::max(camera.zoom, 0.001F);
                const float half_width = 4.2F / std::max(camera.zoom, 0.001F);
                DrawTriangle(
                    Vector2{center.x + dx * length, center.y + dy * length},
                    Vector2{center.x - dx * length * 0.45F + side_x * half_width,
                        center.y - dy * length * 0.45F + side_y * half_width},
                    Vector2{center.x - dx * length * 0.45F - side_x * half_width,
                        center.y - dy * length * 0.45F - side_y * half_width},
                    YELLOW
                );
            }
        }
    }

    state_->performance.tick = frame.tick;
    const double elapsed_ms = std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - timing_start
    ).count();
    record_timing(
        elapsed_ms,
        state_->performance.draw_ms,
        state_->performance.draw_ema_ms
    );
}

std::uint64_t WorldRenderer::pick_entity(
    const Frame& frame,
    const Camera2D& camera,
    Vector2 screen_position,
    float radius_pixels
) const {
    float best_distance = radius_pixels * radius_pixels;
    std::uint64_t selected = 0;

    for (const EntitySample& entity : frame.entities) {
        if (!valid_entity_sample(entity)) {
            continue;
        }
        const Vector2 screen = GetWorldToScreen2D(
            Vector2{entity.x, entity.y},
            camera
        );
        const float dx = screen.x - screen_position.x;
        const float dy = screen.y - screen_position.y;
        const float distance = dx * dx + dy * dy;
        if (distance < best_distance) {
            best_distance = distance;
            selected = entity.entity_id;
        }
    }

    return selected;
}

}  // namespace eco

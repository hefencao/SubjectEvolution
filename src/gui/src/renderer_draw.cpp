#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
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
    if (heatmap_.id == 0) {
        return;
    }

    const float world_width = frame.layout.world_width;
    const float world_height = frame.layout.world_height;
    const RenderDetail detail = resolve_render_detail(
        frame,
        camera,
        viewport,
        options.lod_mode
    );
    const float micro_detail = clamp01(detail.micro_weight);
    const BehaviorWeights behavior = resolve_behavior_weights(
        options.behavior_overlay,
        detail
    );
    const EntitySample* selected_entity = nullptr;
    std::uint64_t selected_group_id = options.selected_group_id;
    if (options.selected_entity_id != 0) {
        for (const EntitySample& entity : frame.entities) {
            if (entity.entity_id == options.selected_entity_id) {
                selected_entity = &entity;
                if (entity.group_id != 0) {
                    selected_group_id = entity.group_id;
                }
                break;
            }
        }
    }

    DrawTexturePro(
        heatmap_,
        Rectangle{0.0F, 0.0F,
            static_cast<float>(heatmap_.width),
            static_cast<float>(heatmap_.height)},
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

    const float flow_weight = options.show_velocity
        ? std::max(detail.flow_weight, 0.42F)
        : detail.flow_weight;
    if (flow_weight > 0.04F) {
        draw_flow_field(frame, camera, flow_weight);
    }

    if (behavior.groups > 0.035F) {
        draw_group_history_overlay(
            frame,
            camera,
            viewport,
            detail,
            options,
            selected_group_id,
            behavior.groups
        );
        draw_group_behavior_overlay(
            group_behaviors_,
            camera,
            behavior.groups * (options.show_group_trails ? 0.42F : 0.78F)
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
            0.92F
        );
    }

    const float aggregate_action_weight = behavior.actions *
        (1.0F - 0.78F * detail.micro_weight);
    if (aggregate_action_weight > 0.05F) {
        draw_action_activity_field(
            frame,
            camera,
            aggregate_action_weight
        );
    }

    const Vector2 top_left = GetScreenToWorld2D(
        Vector2{viewport.x, viewport.y},
        camera
    );
    const Vector2 bottom_right = GetScreenToWorld2D(
        Vector2{viewport.x + viewport.width, viewport.y + viewport.height},
        camera
    );
    const float left = std::min(top_left.x, bottom_right.x);
    const float right = std::max(top_left.x, bottom_right.x);
    const float top = std::min(top_left.y, bottom_right.y);
    const float bottom = std::max(top_left.y, bottom_right.y);

    // Selected-agent relationship topology is deliberately local and bounded.
    const auto selected_position = current_positions_.find(options.selected_entity_id);
    if (selected_position != current_positions_.end()) {
        const Vector2 source{selected_position->second.x, selected_position->second.y};
        for (const SocialNeighbor& neighbor : selected_neighbors) {
            const auto target_iterator = current_positions_.find(neighbor.entity_id);
            if (target_iterator == current_positions_.end()) {
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
        }
    }

    if (options.show_event_markers) {
        const float event_detail = clamp01(detail.agent_weight + 0.35F * detail.micro_weight);
        // At macro scale the trend panel and density field already carry the
        // aggregate event signal. Drawing cluster circles there created false
        // "cities" and obscured resources, so spatial glyphs enter only when
        // agents themselves have become readable.
        if (event_detail >= 0.18F) {
            const std::size_t marker_budget = static_cast<std::size_t>(
                lerp_value(36.0F, 320.0F, event_detail)
            );
            std::size_t drawn = 0;

            for (auto iterator = event_markers_.rbegin();
                 iterator != event_markers_.rend() && drawn < marker_budget;
                 ++iterator) {
                const EventMarker& marker = *iterator;
                if (marker.x < left || marker.x > right || marker.y < top || marker.y > bottom) {
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
                }
    }

    static thread_local std::vector<const EntitySample*> render_entities;
    static thread_local std::vector<const EntitySample*> tile_representatives;
    static thread_local std::vector<std::uint8_t> tile_priorities;
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
        const std::size_t entity_budget = static_cast<std::size_t>(
            lerp_value(
                420.0F,
                28000.0F,
                std::pow(sample_detail, 1.58F)
            )
        );
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
            if (candidate_stride > 1 &&
                entity.entity_id != options.selected_entity_id &&
                entity.action_success == 0 &&
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
            std::uint8_t priority = entity.entity_id == options.selected_entity_id ? 6U :
                (options.focus_selected_group && selected_group_id != 0 &&
                 entity.group_id == selected_group_id) ? 5U :
                entity.action_success != 0 ? 4U :
                entity.group_id != 0 ? 2U : 1U;
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

        const float trail_weight = options.show_velocity
            ? std::max(detail.agent_weight, 0.48F)
            : detail.micro_weight * 0.26F;
        if (trail_weight > 0.035F && !render_entities.empty()) {
            const std::size_t trail_budget = static_cast<std::size_t>(
                lerp_value(180.0F, 4200.0F, trail_weight)
            );
            const std::size_t trail_stride = std::max<std::size_t>(
                1,
                render_entities.size() / std::max<std::size_t>(trail_budget, 1U)
            );
            for (std::size_t index = 0; index < render_entities.size(); index += trail_stride) {
                const EntitySample* entity = render_entities[index];
                const auto previous = previous_positions_.find(entity->entity_id);
                if (previous == previous_positions_.end()) {
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
            Color color = color_for_entity(*entity, frame.layout.max_energy);
            color.a = static_cast<unsigned char>(std::min<int>(color.a, body_alpha));
            if (options.focus_selected_group && selected_group_id != 0 &&
                entity->group_id != selected_group_id &&
                entity->entity_id != options.selected_entity_id) {
                color.a = static_cast<unsigned char>(
                    std::min<int>(color.a, 10 + static_cast<int>(28.0F * detail.micro_weight))
                );
            }

            // Body color always represents group identity. Actions use
            // shape-coded overlays, so harvest no longer disappears into the
            // green resource palette and group patterns remain readable.
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
            const float core_radius = lerp_value(
                0.28F,
                0.82F,
                detail.micro_weight
            ) * inverse_zoom;
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
                        std::min<int>(alpha, 6 + static_cast<int>(12.0F * detail.micro_weight))
                    );
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

        const float individual_action_weight = behavior.actions *
            smooth_range(0.28F, 0.78F, detail.micro_weight);
        if (individual_action_weight > 0.05F && !render_entities.empty()) {
            const std::size_t action_budget = static_cast<std::size_t>(
                lerp_value(80.0F, 320.0F, individual_action_weight)
            );
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
                    (entity->action_success == 0 && !movement)) {
                    continue;
                }
                draw_action_glyph(
                    action,
                    Vector2{entity->x, entity->y},
                    lerp_value(3.6F, 6.2F, detail.micro_weight),
                    camera,
                    individual_action_weight *
                        (entity->action_success != 0 ? 0.90F : 0.48F)
                );
                if (++drawn_actions >= action_budget) {
                    break;
                }
            }
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
                const auto target = current_positions_.find(selected->target_id);
                if (target != current_positions_.end()) {
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

#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace eco {
using namespace render_internal;

EnvironmentProbe WorldRenderer::probe_environment(
    const Frame& frame,
    float world_x,
    float world_y,
    int resource_channel
) const noexcept {
    EnvironmentProbe probe{};
    if (!finite_value(world_x) || !finite_value(world_y) ||
        frame.layout.grid_x == 0 || frame.layout.grid_y == 0) {
        return probe;
    }

    const std::size_t cell_count = frame.cell_count();
    if (frame.resources.size() < cell_count * 4U ||
        frame.hazard.size() < cell_count) {
        return probe;
    }

    const float world_width = std::max(frame.layout.world_width, 1.0F);
    const float world_height = std::max(frame.layout.world_height, 1.0F);
    const float wrapped_x = std::fmod(std::fmod(world_x, world_width) + world_width, world_width);
    const float wrapped_y = std::fmod(std::fmod(world_y, world_height) + world_height, world_height);
    const std::uint32_t cell_x = std::min<std::uint32_t>(
        static_cast<std::uint32_t>(wrapped_x / world_width * frame.layout.grid_x),
        frame.layout.grid_x - 1U
    );
    const std::uint32_t cell_y = std::min<std::uint32_t>(
        static_cast<std::uint32_t>(wrapped_y / world_height * frame.layout.grid_y),
        frame.layout.grid_y - 1U
    );
    const auto index_of = [&frame](std::uint32_t x, std::uint32_t y) {
        return static_cast<std::size_t>(y) * frame.layout.grid_x + x;
    };
    const std::size_t index = index_of(cell_x, cell_y);
    probe.valid = true;
    probe.cell_x = cell_x;
    probe.cell_y = cell_y;
    for (std::size_t channel = 0; channel < 4U; ++channel) {
        probe.resources[channel] = frame.resources[channel * cell_count + index];
    }
    probe.hazard = frame.hazard[index];

    const int channel = std::clamp(resource_channel, 0, 3);
    const std::uint32_t left = cell_x == 0 ? frame.layout.grid_x - 1U : cell_x - 1U;
    const std::uint32_t right = cell_x + 1U == frame.layout.grid_x ? 0U : cell_x + 1U;
    const std::uint32_t up = cell_y == 0 ? frame.layout.grid_y - 1U : cell_y - 1U;
    const std::uint32_t down = cell_y + 1U == frame.layout.grid_y ? 0U : cell_y + 1U;
    const std::size_t offset = static_cast<std::size_t>(channel) * cell_count;
    probe.gradient_x = 0.5F * (
        frame.resources[offset + index_of(right, cell_y)] -
        frame.resources[offset + index_of(left, cell_y)]
    );
    probe.gradient_y = 0.5F * (
        frame.resources[offset + index_of(cell_x, down)] -
        frame.resources[offset + index_of(cell_x, up)]
    );
    probe.gradient_magnitude = std::sqrt(
        probe.gradient_x * probe.gradient_x +
        probe.gradient_y * probe.gradient_y
    );
    return probe;
}

void WorldRenderer::ensure_texture(std::uint32_t grid_x, std::uint32_t grid_y) {
    if (heatmap_.id != 0 && grid_x_ == grid_x && grid_y_ == grid_y) {
        return;
    }

    if (heatmap_.id != 0) {
        UnloadTexture(heatmap_);
        heatmap_ = Texture2D{};
    }

    grid_x_ = grid_x;
    grid_y_ = grid_y;
    pixels_.assign(
        static_cast<std::size_t>(grid_x_) * static_cast<std::size_t>(grid_y_),
        BLACK
    );

    for (auto& resource : filtered_resources_) {
        resource.clear();
    }
    filtered_hazard_.clear();
    for (auto& resource : previous_resources_) {
        resource.clear();
    }
    previous_hazard_.clear();
    resource_scale_initialized_.fill(false);
    resource_adaptive_initialized_.fill(false);
    last_heatmap_tick_ = 0;

    Image image = GenImageColor(
        static_cast<int>(grid_x_),
        static_cast<int>(grid_y_),
        BLACK
    );
    heatmap_ = LoadTextureFromImage(image);
    UnloadImage(image);
    SetTextureFilter(heatmap_, TEXTURE_FILTER_POINT);
    texture_filter_ = TEXTURE_FILTER_POINT;
}

void WorldRenderer::update_heatmap(
    const Frame& frame,
    const RenderDetail& detail,
    const RenderOptions& options
) {
    ensure_texture(frame.layout.grid_x, frame.layout.grid_y);

    const std::size_t cell_count = frame.cell_count();
    if (frame.resources.size() < cell_count * 4U ||
        frame.hazard.size() < cell_count) {
        return;
    }

    const int channel = std::clamp(options.resource_channel, 0, 3);
    const std::size_t offset = static_cast<std::size_t>(channel) * cell_count;

    if (!resource_scale_initialized_[channel]) {
        std::vector<float> scratch;
        scratch.reserve(cell_count);
        for (std::size_t index = 0; index < cell_count; ++index) {
            const float value = frame.resources[offset + index];
            if (finite_value(value)) {
                scratch.push_back(value);
            }
        }
        std::vector<float> low_scratch = scratch;
        resource_low_[channel] = quantile(low_scratch, 0.02F);
        resource_high_[channel] = quantile(scratch, 0.98F);
        if (resource_high_[channel] - resource_low_[channel] < 1.0e-5F) {
            resource_high_[channel] = resource_low_[channel] + 1.0F;
        }
        resource_scale_initialized_[channel] = true;
    }

    const float scale_low = resource_low_[channel];
    const float scale_span = std::max(
        resource_high_[channel] - resource_low_[channel],
        1.0e-5F
    );
    const std::uint64_t elapsed_ticks =
        last_heatmap_tick_ == 0 || frame.tick <= last_heatmap_tick_
            ? 1
            : frame.tick - last_heatmap_tick_;
    const FilterParameters parameters = filter_parameters(options.environment_filter);
    const float resource_alpha = effective_alpha(
        parameters.resource_alpha_per_tick,
        elapsed_ticks
    );
    const float hazard_alpha = effective_alpha(
        parameters.hazard_alpha_per_tick,
        elapsed_ticks
    );
    const float resource_max_step = std::max(
        scale_span * parameters.resource_max_step_fraction *
            static_cast<float>(std::clamp<std::uint64_t>(elapsed_ticks, 1, 16)),
        1.0e-6F
    );
    const float hazard_max_step = parameters.hazard_max_step *
        static_cast<float>(std::clamp<std::uint64_t>(elapsed_ticks, 1, 16));

    std::vector<float>& filtered_resource = filtered_resources_[channel];
    const bool resource_filter_initialized = filtered_resource.size() == cell_count;
    const bool hazard_filter_initialized = filtered_hazard_.size() == cell_count;
    if (!resource_filter_initialized) {
        filtered_resource.resize(cell_count);
    }
    if (!hazard_filter_initialized) {
        filtered_hazard_.resize(cell_count);
    }

    for (std::size_t index = 0; index < cell_count; ++index) {
        const float raw_resource = finite_value(frame.resources[offset + index])
            ? frame.resources[offset + index]
            : scale_low;
        const float raw_hazard = finite_value(frame.hazard[index])
            ? clamp01(frame.hazard[index])
            : 0.0F;

        if (!resource_filter_initialized ||
            options.environment_filter == EnvironmentFilterMode::Instant) {
            filtered_resource[index] = raw_resource;
        } else {
            filtered_resource[index] = filtered_step(
                filtered_resource[index],
                raw_resource,
                resource_alpha,
                resource_max_step
            );
        }

        if (!hazard_filter_initialized ||
            options.environment_filter == EnvironmentFilterMode::Instant) {
            filtered_hazard_[index] = raw_hazard;
        } else {
            filtered_hazard_[index] = filtered_step(
                filtered_hazard_[index],
                raw_hazard,
                hazard_alpha,
                hazard_max_step
            );
        }
    }

    static thread_local std::vector<float> density;
    static thread_local std::vector<float> density_coarse;
    static thread_local std::vector<float> density_medium;
    static thread_local std::vector<float> resource_coarse;
    static thread_local std::vector<float> resource_medium;
    static thread_local std::vector<float> hazard_coarse;
    static thread_local std::vector<float> hazard_medium;
    static thread_local std::vector<float> display_resource;
    static thread_local std::vector<float> display_hazard;
    static thread_local std::vector<float> display_density;
    static thread_local std::vector<float> scratch;
    static thread_local std::vector<float> scale_scratch;

    // Keep the initial scale as the absolute ecological reference, but also
    // maintain a slowly adapting local scale. The local scale reveals spatial
    // structure after global depletion without pretending that depleted cells
    // are fully replenished.
    scale_scratch.clear();
    scale_scratch.reserve(cell_count);
    for (const float value : filtered_resource) {
        if (finite_value(value)) {
            scale_scratch.push_back(value);
        }
    }
    std::vector<float> adaptive_low_scratch = scale_scratch;
    const float current_adaptive_low = quantile(adaptive_low_scratch, 0.06F);
    const float current_adaptive_high = quantile(scale_scratch, 0.94F);
    const float current_adaptive_span = std::max(
        current_adaptive_high - current_adaptive_low,
        0.0F
    );
    const float minimum_adaptive_span = std::max(
        current_adaptive_span * 0.55F,
        std::max(scale_span * 1.0e-5F, 1.0e-8F)
    );
    if (!resource_adaptive_initialized_[channel]) {
        resource_adaptive_low_[channel] = current_adaptive_low;
        resource_adaptive_high_[channel] = std::max(
            current_adaptive_high,
            current_adaptive_low + minimum_adaptive_span
        );
        resource_adaptive_initialized_[channel] = true;
    } else {
        const float adaptive_alpha = effective_alpha(0.012F, elapsed_ticks);
        resource_adaptive_low_[channel] = lerp_value(
            resource_adaptive_low_[channel],
            current_adaptive_low,
            adaptive_alpha
        );
        resource_adaptive_high_[channel] = lerp_value(
            resource_adaptive_high_[channel],
            std::max(current_adaptive_high, current_adaptive_low + minimum_adaptive_span),
            adaptive_alpha
        );
    }

    density.assign(cell_count, 0.0F);
    density_coarse.assign(cell_count, 0.0F);
    density_medium.assign(cell_count, 0.0F);
    display_density.assign(cell_count, 0.0F);

    const float world_width = std::max(frame.layout.world_width, 1.0F);
    const float world_height = std::max(frame.layout.world_height, 1.0F);
    const bool density_required = options.show_population_density ||
        options.environment_view == EnvironmentViewMode::PopulationDensity;

    if (density_required) {
        for (const EntitySample& entity : frame.entities) {
            if (!valid_entity_sample(entity)) {
                continue;
            }
            const int x = std::clamp(
                static_cast<int>(entity.x / world_width * frame.layout.grid_x),
                0,
                static_cast<int>(frame.layout.grid_x) - 1
            );
            const int y = std::clamp(
                static_cast<int>(entity.y / world_height * frame.layout.grid_y),
                0,
                static_cast<int>(frame.layout.grid_y) - 1
            );
            density[static_cast<std::size_t>(y) * frame.layout.grid_x + x] += 1.0F;
        }
        blur_grid(
            density,
            density_coarse,
            scratch,
            frame.layout.grid_x,
            frame.layout.grid_y,
            4
        );
        blur_grid(
            density,
            density_medium,
            scratch,
            frame.layout.grid_x,
            frame.layout.grid_y,
            2
        );
        const float density_fine_weight = smooth_range(
            0.18F,
            0.82F,
            detail.environment_detail
        );
        for (std::size_t index = 0; index < cell_count; ++index) {
            display_density[index] = lerp_value(
                density_coarse[index],
                density_medium[index],
                density_fine_weight
            );
        }
    }

    blur_grid(
        filtered_resource,
        resource_coarse,
        scratch,
        frame.layout.grid_x,
        frame.layout.grid_y,
        2
    );
    blur_grid(
        filtered_resource,
        resource_medium,
        scratch,
        frame.layout.grid_x,
        frame.layout.grid_y,
        1
    );
    blur_grid(
        filtered_hazard_,
        hazard_coarse,
        scratch,
        frame.layout.grid_x,
        frame.layout.grid_y,
        2
    );
    blur_grid(
        filtered_hazard_,
        hazard_medium,
        scratch,
        frame.layout.grid_x,
        frame.layout.grid_y,
        1
    );

    display_resource.resize(cell_count);
    display_hazard.resize(cell_count);
    const float medium_weight = smooth_range(
        0.05F,
        0.66F,
        detail.environment_detail
    );
    const float fine_weight = smooth_range(
        0.58F,
        0.96F,
        detail.environment_detail
    );
    for (std::size_t index = 0; index < cell_count; ++index) {
        const float medium_resource = lerp_value(
            resource_coarse[index],
            resource_medium[index],
            medium_weight
        );
        const float medium_hazard = lerp_value(
            hazard_coarse[index],
            hazard_medium[index],
            medium_weight
        );
        display_resource[index] = lerp_value(
            medium_resource,
            filtered_resource[index],
            fine_weight
        );
        display_hazard[index] = lerp_value(
            medium_hazard,
            filtered_hazard_[index],
            fine_weight
        );
    }

    const float adaptive_low = resource_adaptive_low_[channel];
    const float adaptive_span = std::max(
        resource_adaptive_high_[channel] - resource_adaptive_low_[channel],
        minimum_adaptive_span
    );
    double absolute_presence_sum = 0.0;
    for (const float value : display_resource) {
        absolute_presence_sum += clamp01((value - scale_low) / scale_span);
    }
    const float absolute_presence = cell_count > 0
        ? static_cast<float>(absolute_presence_sum / static_cast<double>(cell_count))
        : 0.0F;
    const float depletion = 1.0F - smooth_range(0.035F, 0.32F, absolute_presence);
    float local_contrast_strength = lerp_value(0.13F, 0.48F, depletion);
    if (options.environment_view == EnvironmentViewMode::ResourceAbsolute) {
        local_contrast_strength = std::min(0.68F, local_contrast_strength + 0.18F);
    }

    float density_max = 1.0F;
    for (const float value : display_density) {
        density_max = std::max(density_max, value);
    }
    const float density_divisor = std::log1p(density_max);

    const bool has_previous_resource =
        previous_resources_[channel].size() == cell_count;
    const bool has_previous_hazard = previous_hazard_.size() == cell_count;

    double resource_sum = 0.0;
    double hazard_sum = 0.0;
    double change_sum = 0.0;
    const int width = static_cast<int>(frame.layout.grid_x);
    const int height = static_cast<int>(frame.layout.grid_y);

    for (int y = 0; y < height; ++y) {
        const int up = std::max(y - 1, 0);
        const int down = std::min(y + 1, height - 1);
        for (int x = 0; x < width; ++x) {
            const int left = std::max(x - 1, 0);
            const int right = std::min(x + 1, width - 1);
            const std::size_t index = static_cast<std::size_t>(y) * frame.layout.grid_x +
                static_cast<std::size_t>(x);
            const std::size_t left_index = static_cast<std::size_t>(y) * frame.layout.grid_x +
                static_cast<std::size_t>(left);
            const std::size_t right_index = static_cast<std::size_t>(y) * frame.layout.grid_x +
                static_cast<std::size_t>(right);
            const std::size_t up_index = static_cast<std::size_t>(up) * frame.layout.grid_x +
                static_cast<std::size_t>(x);
            const std::size_t down_index = static_cast<std::size_t>(down) * frame.layout.grid_x +
                static_cast<std::size_t>(x);

            const float resource_value = display_resource[index];
            const float hazard_value = clamp01(display_hazard[index]);
            const float absolute_resource = clamp01(
                (resource_value - scale_low) / scale_span
            );
            const float local_resource = clamp01(
                (resource_value - adaptive_low) / adaptive_span
            );
            // Absolute abundance remains authoritative. Local contrast only
            // fills part of the unused perceptual range, so depleted worlds stay
            // visibly depleted while their remaining patches are still legible.
            const float normalized_resource = clamp01(
                absolute_resource +
                (1.0F - absolute_resource) *
                    smoothstep01(local_resource) * local_contrast_strength
            );
            const float population_density = density_divisor > 0.0F
                ? std::log1p(display_density[index]) / density_divisor
                : 0.0F;

            float resource_change = 0.0F;
            float hazard_change = 0.0F;
            if (has_previous_resource) {
                const float difference = filtered_resource[index] -
                    previous_resources_[channel][index];
                const float deadzone = scale_span * 0.0015F;
                if (std::abs(difference) > deadzone) {
                    resource_change = difference /
                        std::max(scale_span * 0.022F, 1.0e-5F);
                }
            }
            if (has_previous_hazard) {
                const float difference = clamp01(filtered_hazard_[index]) -
                    previous_hazard_[index];
                if (std::abs(difference) > 0.0015F) {
                    hazard_change = difference / 0.035F;
                }
            }

            // Gradients use the coarse resource field and adaptive span. This
            // suppresses single-cell direction noise and avoids the checkerboard
            // appearance seen in v8's HSV gradient view.
            const float gradient_x =
                (resource_coarse[right_index] - resource_coarse[left_index]) /
                adaptive_span * 1.65F;
            const float gradient_y =
                (resource_coarse[down_index] - resource_coarse[up_index]) /
                adaptive_span * 1.65F;
            const float hazard_edge = std::sqrt(
                std::pow(display_hazard[right_index] - display_hazard[left_index], 2.0F) +
                std::pow(display_hazard[down_index] - display_hazard[up_index], 2.0F)
            ) * 2.5F;

            pixels_[index] = heat_color(
                channel,
                normalized_resource,
                hazard_value,
                population_density,
                resource_change,
                hazard_change,
                gradient_x,
                gradient_y,
                hazard_edge,
                detail,
                options
            );

            resource_sum += absolute_resource;
            hazard_sum += hazard_value;
            change_sum += std::abs(std::clamp(resource_change, -1.0F, 1.0F)) +
                0.25 * std::abs(std::clamp(hazard_change, -1.0F, 1.0F));
        }
    }

    if (cell_count > 0) {
        diagnostics_.mean_resource = static_cast<float>(
            resource_sum / static_cast<double>(cell_count)
        );
        diagnostics_.mean_hazard = static_cast<float>(
            hazard_sum / static_cast<double>(cell_count)
        );
        diagnostics_.mean_environment_change = static_cast<float>(
            change_sum / static_cast<double>(cell_count)
        );
    }

    previous_resources_[channel] = filtered_resource;
    previous_hazard_ = filtered_hazard_;
    last_heatmap_tick_ = frame.tick;

    UpdateTexture(heatmap_, pixels_.data());
    const bool analytical_view =
        options.environment_view == EnvironmentViewMode::ResourceGradient ||
        options.environment_view == EnvironmentViewMode::Hazard ||
        options.environment_view == EnvironmentViewMode::PopulationDensity ||
        options.environment_view == EnvironmentViewMode::ResourceDelta;
    const int requested_filter = !analytical_view && detail.environment_detail >= 0.92F
        ? TEXTURE_FILTER_POINT
        : TEXTURE_FILTER_BILINEAR;
    if (texture_filter_ != requested_filter) {
        SetTextureFilter(heatmap_, requested_filter);
        texture_filter_ = requested_filter;
    }
}

void WorldRenderer::draw_selected_environment_probe(
    const Frame& frame,
    const Camera2D& camera,
    const RenderOptions& options,
    const EntitySample& selected
) const {
    const EnvironmentProbe probe = probe_environment(
        frame, selected.x, selected.y, options.resource_channel
    );
    if (!probe.valid || frame.layout.grid_x == 0 || frame.layout.grid_y == 0) {
        return;
    }
    const float cell_width = frame.layout.world_width /
        static_cast<float>(frame.layout.grid_x);
    const float cell_height = frame.layout.world_height /
        static_cast<float>(frame.layout.grid_y);
    if (cell_width * camera.zoom < 2.0F || cell_height * camera.zoom < 2.0F) {
        return;
    }
    const Rectangle cell{
        static_cast<float>(probe.cell_x) * cell_width,
        static_cast<float>(probe.cell_y) * cell_height,
        cell_width,
        cell_height
    };
    const float inverse_zoom = 1.0F / std::max(camera.zoom, 0.001F);
    DrawRectangleLinesEx(cell, 1.5F * inverse_zoom, Fade(YELLOW, 0.88F));
    const Rectangle neighborhood{
        cell.x - cell_width,
        cell.y - cell_height,
        cell_width * 3.0F,
        cell_height * 3.0F
    };
    DrawRectangleLinesEx(neighborhood, 0.8F * inverse_zoom, Fade(SKYBLUE, 0.32F));

    if (probe.gradient_magnitude > 1.0e-9F) {
        const float inverse_magnitude = 1.0F / probe.gradient_magnitude;
        const Vector2 center{
            cell.x + cell.width * 0.5F,
            cell.y + cell.height * 0.5F
        };
        const float length = 20.0F * inverse_zoom;
        const Vector2 end{
            center.x + probe.gradient_x * inverse_magnitude * length,
            center.y + probe.gradient_y * inverse_magnitude * length
        };
        DrawLineEx(center, end, 1.4F * inverse_zoom, Fade(Color{102, 220, 255, 255}, 0.88F));
        const float dx = (end.x - center.x) / std::max(length, 1.0e-6F);
        const float dy = (end.y - center.y) / std::max(length, 1.0e-6F);
        const float side_x = -dy;
        const float side_y = dx;
        DrawTriangle(
            end,
            Vector2{end.x - dx * 5.0F * inverse_zoom + side_x * 2.7F * inverse_zoom,
                    end.y - dy * 5.0F * inverse_zoom + side_y * 2.7F * inverse_zoom},
            Vector2{end.x - dx * 5.0F * inverse_zoom - side_x * 2.7F * inverse_zoom,
                    end.y - dy * 5.0F * inverse_zoom - side_y * 2.7F * inverse_zoom},
            Fade(Color{102, 220, 255, 255}, 0.88F)
        );
    }
}

}  // namespace eco

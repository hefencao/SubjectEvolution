#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"
#include "render/renderer_state.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace eco {
using namespace render_internal;

RenderDetail resolve_render_detail(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    LodMode mode
) {
    RenderDetail detail{};
    detail.estimated_visible = estimate_visible_entities(frame, camera, viewport);
    const double screen_area = std::max(
        static_cast<double>(viewport.width) * static_cast<double>(viewport.height),
        1.0
    );
    detail.projected_spacing = static_cast<float>(std::sqrt(
        screen_area / std::max(detail.estimated_visible, 1.0)
    ));

    if (mode == LodMode::ForceMacro) {
        detail.density_weight = 1.0F;
        detail.agent_weight = 0.08F;
        detail.micro_weight = 0.0F;
        detail.flow_weight = 1.0F;
        detail.environment_detail = 0.0F;
        detail.dominant = RenderLod::Macro;
        return detail;
    }
    if (mode == LodMode::ForceMedium) {
        detail.density_weight = 0.28F;
        detail.agent_weight = 1.0F;
        detail.micro_weight = 0.12F;
        detail.flow_weight = 0.38F;
        detail.environment_detail = 0.52F;
        detail.dominant = RenderLod::Medium;
        return detail;
    }
    if (mode == LodMode::ForceMicro) {
        detail.density_weight = 0.0F;
        detail.agent_weight = 1.0F;
        detail.micro_weight = 1.0F;
        detail.flow_weight = 0.0F;
        detail.environment_detail = 1.0F;
        detail.dominant = RenderLod::Micro;
        return detail;
    }

    // Screen-space spacing is continuous as the camera zoom changes. Each
    // visual layer derives its own weight from it, avoiding a hard 1.0/1.1
    // mode boundary while keeping the familiar Macro/Medium/Micro label.
    const float spacing = detail.projected_spacing;
    // v9 keeps the density layer dominant for longer. Real agents enter only
    // when a representative can occupy roughly a 7+ pixel footprint, which
    // prevents the 0.9--1.1 zoom range from becoming a full-screen confetti
    // field. All curves overlap, so this remains a natural screen-density
    // response rather than a timed cross-fade.
    detail.density_weight = 1.0F - smooth_range(4.0F, 17.0F, spacing);
    detail.agent_weight = smooth_range(5.2F, 14.5F, spacing);
    detail.micro_weight = smooth_range(18.0F, 42.0F, spacing);
    detail.flow_weight = 1.0F - smooth_range(10.0F, 31.0F, spacing);
    detail.environment_detail = smooth_range(6.0F, 30.0F, spacing);

    if (detail.micro_weight >= 0.55F) {
        detail.dominant = RenderLod::Micro;
    } else if (detail.agent_weight >= 0.36F) {
        detail.dominant = RenderLod::Medium;
    } else {
        detail.dominant = RenderLod::Macro;
    }
    return detail;
}

RenderLod resolve_render_lod(
    const Frame& frame,
    const Camera2D& camera,
    Rectangle viewport,
    LodMode mode
) {
    return resolve_render_detail(frame, camera, viewport, mode).dominant;
}

const char* render_lod_name(RenderLod lod) noexcept {
    switch (lod) {
    case RenderLod::Macro:
        return "macro resources + group behavior";
    case RenderLod::Medium:
        return "medium agents + activity";
    case RenderLod::Micro:
        return "micro individual agents";
    }
    return "unknown";
}

const char* lod_mode_name(LodMode mode) noexcept {
    switch (mode) {
    case LodMode::Auto:
        return "auto";
    case LodMode::ForceMacro:
        return "forced macro";
    case LodMode::ForceMedium:
        return "forced medium";
    case LodMode::ForceMicro:
        return "forced micro";
    }
    return "unknown";
}

const char* environment_filter_name(EnvironmentFilterMode mode) noexcept {
    switch (mode) {
    case EnvironmentFilterMode::Instant:
        return "instant";
    case EnvironmentFilterMode::Responsive:
        return "responsive";
    case EnvironmentFilterMode::Stable:
        return "stable";
    }
    return "unknown";
}

const char* environment_view_name(EnvironmentViewMode mode) noexcept {
    switch (mode) {
    case EnvironmentViewMode::Composite:
        return "composite";
    case EnvironmentViewMode::ResourceAbsolute:
        return "resource";
    case EnvironmentViewMode::ResourceGradient:
        return "gradient";
    case EnvironmentViewMode::Hazard:
        return "hazard";
    case EnvironmentViewMode::PopulationDensity:
        return "population";
    case EnvironmentViewMode::ResourceDelta:
        return "resource-delta";
    }
    return "unknown";
}

const char* behavior_overlay_name(BehaviorOverlayMode mode) noexcept {
    switch (mode) {
    case BehaviorOverlayMode::Auto:
        return "auto";
    case BehaviorOverlayMode::Off:
        return "off";
    case BehaviorOverlayMode::Actions:
        return "actions";
    case BehaviorOverlayMode::Groups:
        return "groups";
    case BehaviorOverlayMode::Combined:
        return "combined";
    }
    return "unknown";
}

const char* overlay_temporal_name(OverlayTemporalMode mode) noexcept {
    switch (mode) {
    case OverlayTemporalMode::Instant:
        return "instant";
    case OverlayTemporalMode::Responsive:
        return "responsive";
    case OverlayTemporalMode::Stable:
        return "stable";
    }
    return "stable";
}

const char* entity_render_backend_name(EntityRenderBackend mode) noexcept {
    switch (mode) {
    case EntityRenderBackend::Auto:
        return "auto";
    case EntityRenderBackend::CpuBatch:
        return "cpu";
    case EntityRenderBackend::GpuInstanced:
        return "gpu";
    }
    return "auto";
}

const char* action_filter_name(ActionFilterMode mode) noexcept {
    switch (mode) {
    case ActionFilterMode::All:
        return "all";
    case ActionFilterMode::Movement:
        return "movement";
    case ActionFilterMode::Resource:
        return "resource";
    case ActionFilterMode::Social:
        return "social";
    case ActionFilterMode::Reproduction:
        return "reproduction";
    case ActionFilterMode::Survival:
        return "survival";
    }
    return "all";
}

bool action_matches_filter(Action action, ActionFilterMode mode) noexcept {
    switch (mode) {
    case ActionFilterMode::All:
        return true;
    case ActionFilterMode::Movement:
        return action == Action::MoveResource ||
               action == Action::MoveSocial ||
               action == Action::Flee;
    case ActionFilterMode::Resource:
        return action == Action::MoveResource ||
               action == Action::Harvest;
    case ActionFilterMode::Social:
        return action == Action::MoveSocial ||
               action == Action::Share ||
               action == Action::Signal;
    case ActionFilterMode::Reproduction:
        return action == Action::Reproduce;
    case ActionFilterMode::Survival:
        return action == Action::Flee ||
               action == Action::Rest;
    }
    return true;
}

Color render_internal::color_for_entity_visual(
    const EntitySample& entity,
    float max_energy,
    std::uint64_t visual_key
) {
    const float energy = clamp01(
        entity.energy / std::max(max_energy, 1.0e-6F)
    );
    const float integrity = clamp01(entity.integrity);

    if (entity.group_id == 0 || visual_key == 0) {
        return Color{
            static_cast<unsigned char>(92.0F + 42.0F * energy),
            static_cast<unsigned char>(154.0F + 58.0F * integrity),
            static_cast<unsigned char>(188.0F + 54.0F * energy),
            230
        };
    }

    const std::uint64_t hash = mix_id(visual_key);
    // Use more than the low 16 bits so nearby/reissued group ids do not form
    // visibly correlated hues. The key itself is renderer-stable across frames.
    const std::uint32_t hue_bits = static_cast<std::uint32_t>(
        (hash ^ (hash >> 29U) ^ (hash >> 47U)) & 0xFFFFFFU
    );
    const float hue = static_cast<float>(hue_bits) / 16777215.0F;
    const float saturation = 0.72F + 0.20F * integrity;
    const float value = 0.86F + 0.14F * energy;
    return hsv_color(hue, saturation, value, 255);
}

Color color_for_entity(const EntitySample& entity, float max_energy) {
    return render_internal::color_for_entity_visual(entity, max_energy, entity.group_id);
}

WorldRenderer::WorldRenderer()
    : state_(std::make_unique<RendererState>()) {}

WorldRenderer::~WorldRenderer() {
    if (state_ != nullptr) {
        unload_gpu_agent_renderer(state_->gpu_agents);
        if (state_->environment.heatmap.id != 0 && IsWindowReady()) {
            UnloadTexture(state_->environment.heatmap);
        }
    }
}

WorldRenderer::WorldRenderer(WorldRenderer&&) noexcept = default;
WorldRenderer& WorldRenderer::operator=(WorldRenderer&&) noexcept = default;

void WorldRenderer::reset_stream_state() {
    std::uint64_t next_epoch = 1;
    if (state_ != nullptr) {
        next_epoch = state_->stream_epoch + 1;
        unload_gpu_agent_renderer(state_->gpu_agents);
        if (state_->environment.heatmap.id != 0 && IsWindowReady()) {
            UnloadTexture(state_->environment.heatmap);
        }
    }
    state_ = std::make_unique<RendererState>();
    state_->stream_epoch = next_epoch;
}

const FrameDiagnostics& WorldRenderer::diagnostics() const noexcept {
    return state_->observation.diagnostics;
}

const std::vector<GroupBehaviorSummary>& WorldRenderer::group_behaviors(
    OverlayTemporalMode mode
) const noexcept {
    return select_group_behaviors(state_->groups, mode);
}

const OverlayBudget& WorldRenderer::overlay_budget() const noexcept {
    return state_->overlay_budget;
}

const OverlayUsage& WorldRenderer::overlay_usage() const noexcept {
    return state_->overlay_usage;
}

const RenderPerformance& WorldRenderer::performance() const noexcept {
    return state_->performance;
}

std::uint64_t WorldRenderer::stream_epoch() const noexcept {
    return state_->stream_epoch;
}

const GroupBehaviorSummary* WorldRenderer::group_behavior(
    std::uint64_t group_id,
    OverlayTemporalMode mode
) const noexcept {
    if (group_id == 0) {
        return nullptr;
    }
    const auto& groups = select_group_behaviors(state_->groups, mode);
    const auto iterator = std::find_if(
        groups.begin(),
        groups.end(),
        [group_id](const GroupBehaviorSummary& group) {
            return group.group_id == group_id;
        }
    );
    return iterator == groups.end() ? nullptr : &*iterator;
}

}  // namespace eco

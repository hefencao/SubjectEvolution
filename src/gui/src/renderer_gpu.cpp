#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"
#include "render/renderer_state.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>

#include <rlgl.h>

namespace eco::render_internal {
namespace {

constexpr const char* kAgentVertexShader = R"GLSL(
#version 330
layout(location = 0) in vec2 vertexPosition;
layout(location = 1) in vec2 instanceCenter;
layout(location = 2) in vec4 instanceColor;

uniform vec2 screenSize;
uniform float halfSize;

out vec2 localPosition;
out vec4 markerColor;

void main() {
    vec2 pixel = instanceCenter + vertexPosition * halfSize;
    vec2 ndc = vec2(
        pixel.x / max(screenSize.x, 1.0) * 2.0 - 1.0,
        1.0 - pixel.y / max(screenSize.y, 1.0) * 2.0
    );
    gl_Position = vec4(ndc, 0.0, 1.0);
    localPosition = vertexPosition;
    markerColor = instanceColor;
}
)GLSL";

constexpr const char* kAgentFragmentShader = R"GLSL(
#version 330
in vec2 localPosition;
in vec4 markerColor;

uniform float bodyScale;
uniform float coreScale;
uniform float coreWeight;

out vec4 finalColor;

void main() {
    float edge = max(abs(localPosition.x), abs(localPosition.y));
    vec4 color = markerColor;

    if (edge > bodyScale) {
        color.rgb = vec3(0.004, 0.018, 0.026);
    }

    if (coreWeight > 0.001 && edge < coreScale) {
        color.rgb = mix(color.rgb, vec3(0.95, 0.98, 1.0), coreWeight);
    }

    finalColor = color;
}
)GLSL";

bool desktop_instancing_supported() noexcept {
    const int version = rlGetVersion();
    return version == RL_OPENGL_33 || version == RL_OPENGL_43;
}

void reset_handles(GpuAgentCache& gpu) noexcept {
    gpu.shader = Shader{};
    gpu.screen_size_location = -1;
    gpu.half_size_location = -1;
    gpu.body_scale_location = -1;
    gpu.core_scale_location = -1;
    gpu.core_weight_location = -1;
    gpu.vertex_array = 0;
    gpu.quad_vertex_buffer = 0;
    gpu.instance_vertex_buffer = 0;
    gpu.capacity = 0;
    gpu.available = false;
}

bool configure_instance_buffer(GpuAgentCache& gpu, std::size_t capacity) {
    if (gpu.vertex_array == 0 || capacity == 0 ||
        capacity > static_cast<std::size_t>(std::numeric_limits<int>::max()) /
            sizeof(GpuAgentInstance)) {
        return false;
    }

    if (gpu.instance_vertex_buffer != 0) {
        rlUnloadVertexBuffer(gpu.instance_vertex_buffer);
        gpu.instance_vertex_buffer = 0;
    }

    if (!rlEnableVertexArray(gpu.vertex_array)) {
        return false;
    }

    gpu.instance_vertex_buffer = rlLoadVertexBuffer(
        nullptr,
        static_cast<int>(capacity * sizeof(GpuAgentInstance)),
        true
    );
    if (gpu.instance_vertex_buffer == 0) {
        rlDisableVertexArray();
        return false;
    }

    rlEnableVertexBuffer(gpu.instance_vertex_buffer);
    rlSetVertexAttribute(
        1,
        2,
        RL_FLOAT,
        false,
        static_cast<int>(sizeof(GpuAgentInstance)),
        static_cast<int>(offsetof(GpuAgentInstance, screen_x))
    );
    rlEnableVertexAttribute(1);
    rlSetVertexAttributeDivisor(1, 1);

    rlSetVertexAttribute(
        2,
        4,
        RL_FLOAT,
        false,
        static_cast<int>(sizeof(GpuAgentInstance)),
        static_cast<int>(offsetof(GpuAgentInstance, red))
    );
    rlEnableVertexAttribute(2);
    rlSetVertexAttributeDivisor(2, 1);

    rlDisableVertexBuffer();
    rlDisableVertexArray();
    gpu.capacity = capacity;
    return true;
}

bool initialize_gpu_agent_renderer(GpuAgentCache& gpu) {
    if (gpu.initialization_attempted) {
        return gpu.available;
    }
    gpu.initialization_attempted = true;

    if (!IsWindowReady() || !desktop_instancing_supported()) {
        return false;
    }

    gpu.shader = LoadShaderFromMemory(kAgentVertexShader, kAgentFragmentShader);
    if (gpu.shader.id == 0) {
        reset_handles(gpu);
        gpu.initialization_attempted = true;
        return false;
    }

    gpu.screen_size_location = GetShaderLocation(gpu.shader, "screenSize");
    gpu.half_size_location = GetShaderLocation(gpu.shader, "halfSize");
    gpu.body_scale_location = GetShaderLocation(gpu.shader, "bodyScale");
    gpu.core_scale_location = GetShaderLocation(gpu.shader, "coreScale");
    gpu.core_weight_location = GetShaderLocation(gpu.shader, "coreWeight");
    if (gpu.screen_size_location < 0 || gpu.half_size_location < 0 ||
        gpu.body_scale_location < 0 || gpu.core_scale_location < 0 ||
        gpu.core_weight_location < 0) {
        UnloadShader(gpu.shader);
        reset_handles(gpu);
        gpu.initialization_attempted = true;
        return false;
    }

    gpu.vertex_array = rlLoadVertexArray();
    if (gpu.vertex_array == 0 || !rlEnableVertexArray(gpu.vertex_array)) {
        UnloadShader(gpu.shader);
        reset_handles(gpu);
        gpu.initialization_attempted = true;
        return false;
    }

    // TL -> BL -> BR, TL -> BR -> TR. The shader converts screen-space Y to
    // NDC, so this order remains front-facing after the vertical flip.
    constexpr float vertices[] = {
        -1.0F, -1.0F,
        -1.0F,  1.0F,
         1.0F,  1.0F,
        -1.0F, -1.0F,
         1.0F,  1.0F,
         1.0F, -1.0F,
    };
    gpu.quad_vertex_buffer = rlLoadVertexBuffer(
        vertices,
        static_cast<int>(sizeof(vertices)),
        false
    );
    if (gpu.quad_vertex_buffer == 0) {
        rlDisableVertexArray();
        UnloadShader(gpu.shader);
        reset_handles(gpu);
        gpu.initialization_attempted = true;
        return false;
    }

    rlEnableVertexBuffer(gpu.quad_vertex_buffer);
    rlSetVertexAttribute(0, 2, RL_FLOAT, false, 2 * sizeof(float), 0);
    rlEnableVertexAttribute(0);
    rlSetVertexAttributeDivisor(0, 0);
    rlDisableVertexBuffer();
    rlDisableVertexArray();

    if (!configure_instance_buffer(gpu, 4096U)) {
        unload_gpu_agent_renderer(gpu);
        gpu.initialization_attempted = true;
        return false;
    }

    gpu.instances.reserve(gpu.capacity);
    gpu.available = true;
    return true;
}

bool ensure_instance_capacity(GpuAgentCache& gpu, std::size_t required) {
    if (required <= gpu.capacity) {
        return true;
    }
    std::size_t capacity = std::max<std::size_t>(gpu.capacity, 4096U);
    while (capacity < required) {
        if (capacity > std::numeric_limits<std::size_t>::max() / 2U) {
            return false;
        }
        capacity *= 2U;
    }
    if (!configure_instance_buffer(gpu, capacity)) {
        gpu.available = false;
        return false;
    }
    gpu.instances.reserve(capacity);
    return true;
}

Color display_color(
    const RendererState& state,
    const Frame& frame,
    const RenderDetail& detail,
    const RenderOptions& options,
    std::uint64_t selected_group_id,
    const EntitySample& entity,
    unsigned char body_alpha
) {
    const auto visual_key_iterator = state.groups.visual_keys.find(entity.group_id);
    const std::uint64_t visual_key = visual_key_iterator !=
        state.groups.visual_keys.end()
            ? visual_key_iterator->second
            : entity.group_id;
    Color color = color_for_entity_visual(entity, frame.layout.max_energy, visual_key);
    color.a = static_cast<unsigned char>(std::min<int>(color.a, body_alpha));

    if (options.focus_selected_group && selected_group_id != 0 &&
        entity.group_id != selected_group_id &&
        entity.entity_id != options.selected_entity_id) {
        color.a = static_cast<unsigned char>(
            std::min<int>(color.a, 10 + static_cast<int>(28.0F * detail.micro_weight))
        );
    }
    if (options.action_filter != ActionFilterMode::All &&
        entity.entity_id != options.selected_entity_id &&
        !action_matches_filter(static_cast<Action>(entity.action), options.action_filter)) {
        color.a = static_cast<unsigned char>(
            std::min<int>(color.a, 10 + static_cast<int>(24.0F * detail.agent_weight))
        );
    }
    return color;
}

}  // namespace

void unload_gpu_agent_renderer(GpuAgentCache& gpu) noexcept {
    if (IsWindowReady()) {
        if (gpu.instance_vertex_buffer != 0) {
            rlUnloadVertexBuffer(gpu.instance_vertex_buffer);
        }
        if (gpu.quad_vertex_buffer != 0) {
            rlUnloadVertexBuffer(gpu.quad_vertex_buffer);
        }
        if (gpu.vertex_array != 0) {
            rlUnloadVertexArray(gpu.vertex_array);
        }
        if (gpu.shader.id != 0) {
            UnloadShader(gpu.shader);
        }
    }
    const bool attempted = gpu.initialization_attempted;
    gpu = GpuAgentCache{};
    gpu.initialization_attempted = attempted;
}

bool draw_gpu_agent_markers(
    RendererState& state,
    const Frame& frame,
    const Camera2D& camera,
    const RenderDetail& detail,
    const RenderOptions& options,
    std::uint64_t selected_group_id,
    const std::vector<const EntitySample*>& entities,
    float body_radius_pixels,
    float outline_radius_pixels,
    float core_radius_pixels,
    unsigned char body_alpha
) {
    state.performance.agent_instances = entities.size();
    state.performance.agent_gpu_active = false;

    if (options.entity_backend == EntityRenderBackend::CpuBatch) {
        state.performance.agent_gpu_available = state.gpu_agents.available;
        return false;
    }

    // For very small batches the existing immediate batch is cheaper than
    // shader/VBO state changes. An explicitly forced GPU backend bypasses this
    // threshold for diagnostics and benchmarking.
    if (options.entity_backend == EntityRenderBackend::Auto && entities.size() < 384U) {
        state.performance.agent_gpu_available = state.gpu_agents.available;
        return false;
    }

    GpuAgentCache& gpu = state.gpu_agents;
    if (!initialize_gpu_agent_renderer(gpu)) {
        state.performance.agent_gpu_available = false;
        return false;
    }
    state.performance.agent_gpu_available = true;

    if (!ensure_instance_capacity(gpu, entities.size())) {
        state.performance.agent_gpu_available = false;
        return false;
    }

    const auto upload_start = std::chrono::steady_clock::now();
    gpu.instances.clear();
    gpu.instances.reserve(entities.size());
    for (const EntitySample* entity : entities) {
        if (entity == nullptr) {
            continue;
        }
        const Vector2 screen = GetWorldToScreen2D(
            Vector2{entity->x, entity->y},
            camera
        );
        const Color color = display_color(
            state,
            frame,
            detail,
            options,
            selected_group_id,
            *entity,
            body_alpha
        );
        gpu.instances.push_back(GpuAgentInstance{
            screen.x,
            screen.y,
            static_cast<float>(color.r) / 255.0F,
            static_cast<float>(color.g) / 255.0F,
            static_cast<float>(color.b) / 255.0F,
            static_cast<float>(color.a) / 255.0F,
        });
    }

    rlDrawRenderBatchActive();
    if (!gpu.instances.empty()) {
        rlUpdateVertexBuffer(
            gpu.instance_vertex_buffer,
            gpu.instances.data(),
            static_cast<int>(gpu.instances.size() * sizeof(GpuAgentInstance)),
            0
        );
    }
    const auto upload_end = std::chrono::steady_clock::now();
    const double upload_ms = std::chrono::duration<double, std::milli>(
        upload_end - upload_start
    ).count();
    record_timing(
        upload_ms,
        state.performance.agent_upload_ms,
        state.performance.agent_upload_ema_ms
    );

    const auto draw_start = std::chrono::steady_clock::now();
    if (!gpu.instances.empty()) {
        const float screen_size[2] = {
            static_cast<float>(std::max(GetScreenWidth(), 1)),
            static_cast<float>(std::max(GetScreenHeight(), 1)),
        };
        const float half_size = std::max(outline_radius_pixels, 0.5F);
        const float body_scale = std::clamp(
            body_radius_pixels / std::max(outline_radius_pixels, 0.001F),
            0.05F,
            1.0F
        );
        const float core_scale = detail.micro_weight > 0.16F
            ? std::clamp(
                core_radius_pixels / std::max(outline_radius_pixels, 0.001F),
                0.01F,
                body_scale
            )
            : 0.0F;
        const float core_weight = detail.micro_weight > 0.16F
            ? std::clamp(0.28F + 0.72F * detail.micro_weight, 0.0F, 1.0F)
            : 0.0F;

        BeginShaderMode(gpu.shader);
        SetShaderValue(
            gpu.shader,
            gpu.screen_size_location,
            screen_size,
            SHADER_UNIFORM_VEC2
        );
        SetShaderValue(
            gpu.shader,
            gpu.half_size_location,
            &half_size,
            SHADER_UNIFORM_FLOAT
        );
        SetShaderValue(
            gpu.shader,
            gpu.body_scale_location,
            &body_scale,
            SHADER_UNIFORM_FLOAT
        );
        SetShaderValue(
            gpu.shader,
            gpu.core_scale_location,
            &core_scale,
            SHADER_UNIFORM_FLOAT
        );
        SetShaderValue(
            gpu.shader,
            gpu.core_weight_location,
            &core_weight,
            SHADER_UNIFORM_FLOAT
        );

        if (rlEnableVertexArray(gpu.vertex_array)) {
            rlDrawVertexArrayInstanced(
                0,
                6,
                static_cast<int>(gpu.instances.size())
            );
            rlDisableVertexArray();
        } else {
            EndShaderMode();
            gpu.available = false;
            state.performance.agent_gpu_available = false;
            return false;
        }
        EndShaderMode();
    }
    const auto draw_end = std::chrono::steady_clock::now();
    const double draw_ms = std::chrono::duration<double, std::milli>(
        draw_end - draw_start
    ).count();
    record_timing(
        draw_ms,
        state.performance.agent_draw_ms,
        state.performance.agent_draw_ema_ms
    );

    state.performance.agent_instances = gpu.instances.size();
    state.performance.agent_gpu_capacity = gpu.capacity;
    state.performance.agent_gpu_active = true;
    return true;
}

}  // namespace eco::render_internal

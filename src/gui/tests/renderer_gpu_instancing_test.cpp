#include "eco/renderer.hpp"
#include <rlgl.h>

#include <cassert>
#include <cstddef>

int rlGetVersion() { return RL_OPENGL_33; }

namespace {
int instanced_draw_calls = 0;
int last_instance_count = 0;
int upload_calls = 0;
}

void rlDrawVertexArrayInstanced(int, int count, int instances) {
    assert(count == 6);
    ++instanced_draw_calls;
    last_instance_count = instances;
}

void rlUpdateVertexBuffer(unsigned int, const void*, int size, int) {
    assert(size > 0);
    ++upload_calls;
}

int main() {
    eco::Frame frame;
    frame.tick = 1;
    frame.layout.grid_x = 32;
    frame.layout.grid_y = 32;
    frame.layout.world_width = 100.0F;
    frame.layout.world_height = 100.0F;
    frame.layout.max_energy = 5.0F;
    frame.resources.resize(4U * 32U * 32U, 0.5F);
    frame.hazard.resize(32U * 32U, 0.1F);

    constexpr int columns = 25;
    constexpr int rows = 20;
    frame.entities.reserve(columns * rows);
    for (int y = 0; y < rows; ++y) {
        for (int x = 0; x < columns; ++x) {
            eco::EntitySample entity{};
            entity.entity_id = static_cast<std::uint64_t>(y * columns + x + 1);
            entity.group_id = static_cast<std::uint64_t>((x / 5) + 1);
            entity.x = 4.0F + static_cast<float>(x) * 3.7F;
            entity.y = 4.0F + static_cast<float>(y) * 4.6F;
            entity.energy = 4.0F;
            entity.integrity = 1.0F;
            frame.entities.push_back(entity);
        }
    }

    eco::WorldRenderer renderer;
    eco::RenderOptions options;
    options.lod_mode = eco::LodMode::ForceMicro;
    options.entity_backend = eco::EntityRenderBackend::GpuInstanced;
    Camera2D camera{{400.0F, 300.0F}, {50.0F, 50.0F}, 0.0F, 6.0F};
    Rectangle viewport{0.0F, 0.0F, 800.0F, 600.0F};

    renderer.observe_frame(frame);
    const eco::RenderDetail detail = eco::resolve_render_detail(
        frame, camera, viewport, options.lod_mode
    );
    renderer.update_heatmap(frame, detail, options);
    renderer.draw(frame, camera, viewport, options, {});

    const eco::RenderPerformance& performance = renderer.performance();
    assert(performance.agent_gpu_available);
    assert(performance.agent_gpu_active);
    assert(performance.agent_instances >= 384U);
    assert(performance.agent_gpu_capacity >= performance.agent_instances);
    assert(upload_calls == 1);
    assert(instanced_draw_calls == 1);
    assert(last_instance_count == static_cast<int>(performance.agent_instances));

    options.entity_backend = eco::EntityRenderBackend::CpuBatch;
    renderer.draw(frame, camera, viewport, options, {});
    assert(!renderer.performance().agent_gpu_active);
    return 0;
}

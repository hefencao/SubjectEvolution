#include "eco/renderer.hpp"
#include <rlgl.h>

#include <algorithm>
#include <cassert>
#include <cmath>
#include <vector>

Vector2 GetScreenToWorld2D(Vector2 p, Camera2D c) {
    return {(p.x-c.offset.x)/c.zoom+c.target.x,(p.y-c.offset.y)/c.zoom+c.target.y};
}
Vector2 GetWorldToScreen2D(Vector2 p, Camera2D c) {
    return {(p.x-c.target.x)*c.zoom+c.offset.x,(p.y-c.target.y)*c.zoom+c.offset.y};
}
void DrawLineEx(Vector2,Vector2,float,Color) {}
void DrawCircleV(Vector2,float,Color) {}
void DrawCircleLines(int,int,float,Color) {}
void DrawRectangleLinesEx(Rectangle,float,Color) {}
void DrawTexturePro(Texture2D,Rectangle,Rectangle,Vector2,float,Color) {}
void DrawTriangle(Vector2,Vector2,Vector2,Color) {}
Color Fade(Color c,float a) { c.a=(unsigned char)(c.a*std::clamp(a,0.0F,1.0F)); return c; }
Image GenImageColor(int w,int h,Color) { return {nullptr,w,h,1,0}; }
Texture2D LoadTextureFromImage(Image i) { return {1u,i.width,i.height,1,0}; }
void UnloadImage(Image) {}
void UnloadTexture(Texture2D) {}
void UpdateTexture(Texture2D,const void*) {}
void SetTextureFilter(Texture2D,int) {}
Texture2D GetShapesTexture() { return {7u,1,1,1,0}; }
Rectangle GetShapesTextureRectangle() { return {0.0F,0.0F,1.0F,1.0F}; }
void rlSetTexture(unsigned int) {}
void rlBegin(int) {}
void rlEnd() {}
void rlNormal3f(float,float,float) {}
void rlColor4ub(unsigned char,unsigned char,unsigned char,unsigned char) {}
void rlTexCoord2f(float,float) {}
void rlVertex2f(float,float) {}

static eco::Frame make_frame(std::uint64_t tick, std::uint64_t group_id) {
    eco::Frame frame;
    frame.tick = tick;
    frame.layout.grid_x = 32;
    frame.layout.grid_y = 32;
    frame.layout.max_entities = 4096;
    frame.layout.world_width = 256.0F;
    frame.layout.world_height = 256.0F;
    frame.layout.max_energy = 5.0F;
    frame.resources.resize(4U * 32U * 32U, 0.5F);
    frame.hazard.resize(32U * 32U, 0.1F);
    frame.entities.resize(1200);
    for (std::size_t index = 0; index < frame.entities.size(); ++index) {
        auto& entity = frame.entities[index];
        entity.entity_id = index + 1U;
        entity.group_id = group_id;
        entity.x = static_cast<float>((index * 17U) % 256U);
        entity.y = static_cast<float>((index * 31U) % 256U);
        entity.vx = 0.08F;
        entity.vy = 0.03F;
        entity.energy = 3.5F;
        entity.integrity = 0.9F;
        entity.action = static_cast<std::uint8_t>(eco::Action::MoveResource);
        entity.action_success = 1;
    }
    return frame;
}

int main() {
    eco::WorldRenderer renderer;
    const std::uint64_t initial_epoch = renderer.stream_epoch();
    eco::Frame frame = make_frame(100, 11);
    eco::RenderOptions options;
    options.lod_mode = eco::LodMode::ForceMedium;
    Camera2D camera{{400.0F,300.0F},{128.0F,128.0F},0.0F,2.0F};
    Rectangle viewport{0.0F,0.0F,800.0F,600.0F};

    renderer.observe_frame(frame);
    const eco::RenderDetail detail = eco::resolve_render_detail(
        frame, camera, viewport, options.lod_mode);
    renderer.update_heatmap(frame, detail, options);
    renderer.draw(frame, camera, viewport, options, {});

    assert(renderer.stream_epoch() == initial_epoch);
    assert(renderer.performance().tick == frame.tick);
    assert(renderer.performance().observe_ema_ms >= 0.0);
    assert(renderer.performance().heatmap_ema_ms >= 0.0);
    assert(renderer.performance().draw_ema_ms >= 0.0);
    assert(renderer.overlay_budget().agent_markers > 0U);
    assert(renderer.overlay_usage().agent_markers <=
        renderer.overlay_budget().agent_markers);
    assert(renderer.overlay_usage().action_glyphs <=
        renderer.overlay_budget().action_glyphs);
    assert(renderer.overlay_usage().group_markers <=
        renderer.overlay_budget().group_markers + 1U);

    // A tick rollback represents a restarted/replaced stream. Derived event,
    // group-trail and filter state must be discarded before the new frame is
    // observed, and the first frame of the new stream must not report births.
    eco::Frame restarted = make_frame(3, 77);
    renderer.observe_frame(restarted);
    assert(renderer.stream_epoch() == initial_epoch + 1U);
    assert(renderer.diagnostics().births == 0U);
    assert(renderer.group_behavior(11) == nullptr);
    assert(renderer.group_behavior(77) != nullptr);
    return 0;
}

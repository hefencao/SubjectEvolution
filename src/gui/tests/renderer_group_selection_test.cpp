#include "eco/renderer.hpp"
#include <rlgl.h>

#include <algorithm>
#include <cassert>
#include <cstddef>

namespace {
std::size_t line_calls = 0;
std::size_t circle_calls = 0;
std::size_t triangle_calls = 0;
}

Vector2 GetScreenToWorld2D(Vector2 p, Camera2D c) {
    return {(p.x-c.offset.x)/c.zoom+c.target.x,(p.y-c.offset.y)/c.zoom+c.target.y};
}
Vector2 GetWorldToScreen2D(Vector2 p, Camera2D c) {
    return {(p.x-c.target.x)*c.zoom+c.offset.x,(p.y-c.target.y)*c.zoom+c.offset.y};
}
void DrawLineEx(Vector2,Vector2,float,Color) { ++line_calls; }
void DrawCircleV(Vector2,float,Color) { ++circle_calls; }
void DrawCircleLines(int,int,float,Color) { ++circle_calls; }
void DrawRectangleLinesEx(Rectangle,float,Color) { ++line_calls; }
void DrawTexturePro(Texture2D,Rectangle,Rectangle,Vector2,float,Color) {}
void DrawTriangle(Vector2,Vector2,Vector2,Color) { ++triangle_calls; }
Color Fade(Color c,float a) { c.a=(unsigned char)(c.a*std::clamp(a,0.0F,1.0F)); return c; }
Image GenImageColor(int w,int h,Color) { return {nullptr,w,h,1,0}; }
Texture2D LoadTextureFromImage(Image i) { return {1u,i.width,i.height,1,0}; }
void UnloadImage(Image) {}
void UnloadTexture(Texture2D) {}
void UpdateTexture(Texture2D,const void*) {}
void SetTextureFilter(Texture2D,int) {}
Texture2D GetShapesTexture() { return {7u,1,1,1,0}; }
Rectangle GetShapesTextureRectangle() { return {0,0,1,1}; }
void rlSetTexture(unsigned int) {}
void rlBegin(int) {}
void rlEnd() {}
void rlNormal3f(float,float,float) {}
void rlColor4ub(unsigned char,unsigned char,unsigned char,unsigned char) {}
void rlTexCoord2f(float,float) {}
void rlVertex2f(float,float) {}

static eco::Frame make_frame(std::uint64_t tick, float shift) {
    eco::Frame frame;
    frame.tick = tick;
    frame.layout.grid_x = 8;
    frame.layout.grid_y = 8;
    frame.layout.world_width = 80.0F;
    frame.layout.world_height = 80.0F;
    frame.layout.max_energy = 5.0F;
    frame.resources.resize(4U * 64U);
    frame.hazard.assign(64U, 0.1F);
    for (int channel = 0; channel < 4; ++channel) {
        for (int y = 0; y < 8; ++y) {
            for (int x = 0; x < 8; ++x) {
                frame.resources[static_cast<std::size_t>(channel) * 64U +
                    static_cast<std::size_t>(y) * 8U + static_cast<std::size_t>(x)] =
                    float(channel + 1) * 0.1F + float(x) * 0.05F;
            }
        }
    }
    for (std::size_t i = 0; i < 120; ++i) {
        eco::EntitySample e{};
        e.entity_id = i + 1;
        e.group_id = 77;
        e.x = 18.0F + shift + float(i % 20) * 0.7F;
        e.y = 30.0F + float(i / 20) * 0.18F;
        e.vx = 0.22F;
        e.vy = 0.015F;
        e.energy = 4.0F;
        e.integrity = 1.0F;
        e.action = static_cast<std::uint8_t>(eco::Action::MoveResource);
        e.action_success = 1;
        frame.entities.push_back(e);
    }
    for (std::size_t i = 0; i < 70; ++i) {
        eco::EntitySample e{};
        e.entity_id = 1000 + i;
        e.group_id = 88;
        e.x = 55.0F + float(i % 10) * 0.3F;
        e.y = 50.0F + float(i / 10) * 0.3F;
        e.vx = (i & 1U) ? 0.05F : -0.05F;
        e.energy = 2.0F;
        e.integrity = 1.0F;
        e.action = static_cast<std::uint8_t>(eco::Action::Rest);
        frame.entities.push_back(e);
    }
    return frame;
}

int main() {
    eco::WorldRenderer renderer;
    eco::Frame frame = make_frame(1, 0.0F);
    renderer.observe_frame(frame);
    frame = make_frame(5, 1.5F);
    renderer.observe_frame(frame);
    frame = make_frame(9, 3.0F);
    renderer.observe_frame(frame);

    const auto* group = renderer.group_behavior(77);
    assert(group != nullptr);
    assert(group->spread_major > group->spread_minor);
    assert(group->coherence > 0.9F);
    float fraction_sum = 0.0F;
    for (float fraction : group->action_fractions) {
        fraction_sum += fraction;
    }
    assert(fraction_sum > 0.99F && fraction_sum < 1.01F);
    assert(group->action_fractions[static_cast<std::size_t>(eco::Action::MoveResource)] > 0.95F);

    const eco::EnvironmentProbe probe = renderer.probe_environment(frame, 15.0F, 25.0F, 0);
    assert(probe.valid);
    assert(probe.cell_x == 1U);
    assert(probe.cell_y == 2U);
    assert(probe.resources[1] > probe.resources[0]);
    assert(probe.gradient_x > 0.0F);

    Camera2D camera{{400,400},{40,40},0,5.0F};
    Rectangle viewport{0,0,800,800};
    eco::RenderOptions options;
    options.lod_mode = eco::LodMode::ForceMacro;
    options.behavior_overlay = eco::BehaviorOverlayMode::Groups;
    options.show_population_density = false;
    options.show_event_markers = false;
    options.selected_entity_id = 1;
    renderer.update_heatmap(frame, eco::resolve_render_detail(frame,camera,viewport,options.lod_mode), options);

    const Vector2 group_screen = GetWorldToScreen2D(Vector2{group->x, group->y}, camera);
    const std::uint64_t picked_group = renderer.pick_group(frame, camera, group_screen);
    assert(picked_group == 77);

    options.selected_entity_id = 0;
    options.selected_group_id = 77;
    options.behavior_overlay = eco::BehaviorOverlayMode::Off;
    options.show_group_trails = false;
    line_calls = circle_calls = triangle_calls = 0;
    renderer.draw(frame,camera,viewport,options,{});
    const std::size_t selected_only = line_calls + circle_calls + triangle_calls;
    assert(selected_only > 0);

    options.behavior_overlay = eco::BehaviorOverlayMode::Groups;
    options.show_group_trails = true;
    options.focus_selected_group = true;
    line_calls = circle_calls = triangle_calls = 0;
    renderer.draw(frame,camera,viewport,options,{});
    const std::size_t with_trails = line_calls + circle_calls + triangle_calls;
    assert(with_trails > selected_only);
    return 0;
}

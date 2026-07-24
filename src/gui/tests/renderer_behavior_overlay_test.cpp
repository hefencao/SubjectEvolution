#include "eco/renderer.hpp"
#include <rlgl.h>

#include <algorithm>
#include <cassert>
#include <cstddef>
#include <string>

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

int main() {
    eco::Frame frame;
    frame.tick=10;
    frame.layout.grid_x=32;
    frame.layout.grid_y=32;
    frame.layout.world_width=320.0F;
    frame.layout.world_height=320.0F;
    frame.layout.max_energy=5.0F;
    frame.resources.assign(4U*32U*32U,0.4F);
    frame.hazard.assign(32U*32U,0.0F);

    for (std::size_t i=0;i<160;++i) {
        eco::EntitySample e{};
        e.entity_id=i+1;
        e.group_id=77;
        e.x=120.0F+float(i%16)*0.4F;
        e.y=130.0F+float(i/16)*0.4F;
        e.vx=0.18F;
        e.vy=0.02F;
        e.energy=3.0F;
        e.integrity=1.0F;
        e.action=static_cast<std::uint8_t>(eco::Action::Harvest);
        e.action_success=1;
        frame.entities.push_back(e);
    }
    for (std::size_t i=0;i<80;++i) {
        eco::EntitySample e{};
        e.entity_id=1000+i;
        e.group_id=88;
        e.x=220.0F+float(i%10);
        e.y=220.0F+float(i/10);
        e.vx=(i&1)?0.1F:-0.1F;
        e.vy=0.0F;
        e.energy=2.0F;
        e.integrity=1.0F;
        e.action=static_cast<std::uint8_t>(eco::Action::Rest);
        frame.entities.push_back(e);
    }

    eco::WorldRenderer renderer;
    renderer.observe_frame(frame);
    const auto* group=renderer.group_behavior(77);
    assert(group != nullptr);
    assert(group->members == 160);
    assert(group->coherence > 0.95F);
    assert(group->dominant_action == eco::Action::Harvest);
    assert(group->dominant_action_fraction > 0.95F);
    assert(renderer.diagnostics().harvests == 160);
    assert(renderer.diagnostics().successful_actions == 160);

    Camera2D camera{{450,450},{160,160},0,2.0F};
    Rectangle viewport{0,0,900,900};
    eco::RenderOptions options;
    options.lod_mode=eco::LodMode::ForceMacro;
    options.show_event_markers=false;
    options.show_population_density=false;
    options.show_velocity=false;
    renderer.update_heatmap(frame,eco::resolve_render_detail(frame,camera,viewport,options.lod_mode),options);

    options.behavior_overlay=eco::BehaviorOverlayMode::Off;
    line_calls=circle_calls=triangle_calls=0;
    renderer.draw(frame,camera,viewport,options,{});
    const std::size_t baseline=line_calls+circle_calls+triangle_calls;

    options.behavior_overlay=eco::BehaviorOverlayMode::Actions;
    line_calls=circle_calls=triangle_calls=0;
    renderer.draw(frame,camera,viewport,options,{});
    const std::size_t actions=line_calls+circle_calls+triangle_calls;
    assert(actions > baseline);

    options.behavior_overlay=eco::BehaviorOverlayMode::Groups;
    line_calls=circle_calls=triangle_calls=0;
    renderer.draw(frame,camera,viewport,options,{});
    const std::size_t groups=line_calls+circle_calls+triangle_calls;
    assert(groups > baseline);
    assert(std::string(eco::behavior_overlay_name(eco::BehaviorOverlayMode::Combined)) == "combined");
    return 0;
}

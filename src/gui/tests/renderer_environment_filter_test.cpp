#include "eco/renderer.hpp"
#include <rlgl.h>

#include <cassert>
#include <vector>

namespace {
std::vector<Color> uploaded;
std::size_t expected_pixels = 0;
}

Vector2 GetScreenToWorld2D(Vector2 p, Camera2D c) { return {(p.x-c.offset.x)/c.zoom+c.target.x,(p.y-c.offset.y)/c.zoom+c.target.y}; }
Vector2 GetWorldToScreen2D(Vector2 p, Camera2D c) { return {(p.x-c.target.x)*c.zoom+c.offset.x,(p.y-c.target.y)*c.zoom+c.offset.y}; }
void DrawLineEx(Vector2,Vector2,float,Color) {}
void DrawCircleV(Vector2,float,Color) {}
void DrawCircleLines(int,int,float,Color) {}
void DrawRectangleRec(Rectangle,Color) {}
void DrawRectangleLinesEx(Rectangle,float,Color) {}
void DrawTexturePro(Texture2D,Rectangle,Rectangle,Vector2,float,Color) {}
void DrawTriangle(Vector2,Vector2,Vector2,Color) {}
Color Fade(Color c,float a) { c.a=(unsigned char)(c.a*(a<0?0:a>1?1:a)); return c; }
Image GenImageColor(int w,int h,Color) { return {nullptr,w,h,1,0}; }
Texture2D LoadTextureFromImage(Image i) { return {1u,i.width,i.height,1,0}; }
void UnloadImage(Image) {}
void UnloadTexture(Texture2D) {}
void UpdateTexture(Texture2D,const void* data) {
    const auto* colors = static_cast<const Color*>(data);
    uploaded.assign(colors, colors + expected_pixels);
}
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

static eco::Frame make_frame(float hazard, std::uint64_t tick) {
    eco::Frame frame;
    frame.tick = tick;
    frame.layout.grid_x = 4;
    frame.layout.grid_y = 4;
    frame.layout.world_width = 4.0F;
    frame.layout.world_height = 4.0F;
    frame.layout.max_energy = 5.0F;
    frame.resources.resize(4U * 16U, 0.5F);
    frame.hazard.resize(16U, hazard);
    return frame;
}

int main() {
    expected_pixels = 16;
    eco::RenderOptions stable_options;
    stable_options.show_population_density = false;
    stable_options.environment_filter = eco::EnvironmentFilterMode::Stable;
    eco::WorldRenderer stable_renderer;

    eco::Frame frame = make_frame(0.0F, 1);
    stable_renderer.observe_frame(frame);
    stable_renderer.update_heatmap(frame, eco::RenderDetail{0.0,7.0F,0.3F,1.0F,0.1F,0.3F,0.5F,eco::RenderLod::Medium}, stable_options);
    const Color stable_baseline = uploaded.front();

    frame = make_frame(1.0F, 2);
    stable_renderer.observe_frame(frame);
    stable_renderer.update_heatmap(frame, eco::RenderDetail{0.0,7.0F,0.3F,1.0F,0.1F,0.3F,0.5F,eco::RenderLod::Medium}, stable_options);
    const Color stable_color = uploaded.front();

    eco::RenderOptions instant_options = stable_options;
    instant_options.environment_filter = eco::EnvironmentFilterMode::Instant;
    eco::WorldRenderer instant_renderer;
    frame = make_frame(0.0F, 1);
    instant_renderer.observe_frame(frame);
    instant_renderer.update_heatmap(frame, eco::RenderDetail{0.0,7.0F,0.3F,1.0F,0.1F,0.3F,0.5F,eco::RenderLod::Medium}, instant_options);
    const Color instant_baseline = uploaded.front();
    frame = make_frame(1.0F, 2);
    instant_renderer.observe_frame(frame);
    instant_renderer.update_heatmap(frame, eco::RenderDetail{0.0,7.0F,0.3F,1.0F,0.1F,0.3F,0.5F,eco::RenderLod::Medium}, instant_options);
    const Color instant_color = uploaded.front();

    // Stable mode must change substantially less than the instant view.
    const int stable_delta =
        std::abs(int(stable_color.r) - int(stable_baseline.r)) +
        std::abs(int(stable_color.g) - int(stable_baseline.g)) +
        std::abs(int(stable_color.b) - int(stable_baseline.b));
    const int instant_delta =
        std::abs(int(instant_color.r) - int(instant_baseline.r)) +
        std::abs(int(instant_color.g) - int(instant_baseline.g)) +
        std::abs(int(instant_color.b) - int(instant_baseline.b));
    assert(stable_delta < instant_delta);

    eco::Frame lod_frame;
    lod_frame.layout.world_width = 1024.0F;
    lod_frame.layout.world_height = 1024.0F;
    lod_frame.entities.resize(80000);
    Rectangle viewport{510.0F, 0.0F, 900.0F, 900.0F};
    Camera2D camera{{960.0F,450.0F},{512.0F,512.0F},0.0F,0.88F};
    assert(eco::resolve_render_lod(lod_frame,camera,viewport) == eco::RenderLod::Macro);
    camera.zoom = 3.0F;
    assert(eco::resolve_render_lod(lod_frame,camera,viewport) == eco::RenderLod::Medium);
    camera.zoom = 10.0F;
    assert(eco::resolve_render_lod(lod_frame,camera,viewport) == eco::RenderLod::Micro);
    return 0;
}

#include "eco/renderer.hpp"
#include <rlgl.h>

#include <algorithm>
#include <cassert>
#include <cmath>
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
void DrawRectangleLinesEx(Rectangle,float,Color) {}
void DrawTexturePro(Texture2D,Rectangle,Rectangle,Vector2,float,Color) {}
void DrawTriangle(Vector2,Vector2,Vector2,Color) {}
Color Fade(Color c,float a) { c.a=(unsigned char)(c.a*std::clamp(a,0.0F,1.0F)); return c; }
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

static eco::Frame make_frame(std::uint64_t tick, float resource_offset = 0.0F) {
    eco::Frame frame;
    frame.tick = tick;
    frame.layout.grid_x = 8;
    frame.layout.grid_y = 8;
    frame.layout.world_width = 80.0F;
    frame.layout.world_height = 80.0F;
    frame.layout.max_energy = 5.0F;
    frame.resources.resize(4U * 64U, 0.0F);
    frame.hazard.resize(64U, 0.0F);
    for (int y = 0; y < 8; ++y) {
        for (int x = 0; x < 8; ++x) {
            const std::size_t index = static_cast<std::size_t>(y * 8 + x);
            frame.resources[index] = 0.05F + 0.10F * float(x) + resource_offset;
            frame.hazard[index] = x >= 5 ? 0.85F : 0.05F;
        }
    }
    // Concentrate population in the upper-left quarter.
    for (std::uint64_t id = 1; id <= 200; ++id) {
        eco::EntitySample entity{};
        entity.entity_id = id;
        entity.x = float((id * 3) % 25);
        entity.y = float((id * 7) % 25);
        entity.energy = 3.0F;
        entity.integrity = 1.0F;
        frame.entities.push_back(entity);
    }
    return frame;
}


static bool same_colors(const std::vector<Color>& left, const std::vector<Color>& right) {
    if (left.size() != right.size()) return false;
    for (std::size_t index = 0; index < left.size(); ++index) {
        const Color a = left[index];
        const Color b = right[index];
        if (a.r != b.r || a.g != b.g || a.b != b.b || a.a != b.a) return false;
    }
    return true;
}

static std::vector<Color> render_view(
    eco::EnvironmentViewMode view,
    const eco::Frame& frame
) {
    eco::WorldRenderer renderer;
    eco::RenderOptions options;
    options.environment_filter = eco::EnvironmentFilterMode::Instant;
    options.environment_view = view;
    options.show_population_density = true;
    options.show_hazard = true;
    eco::RenderDetail detail{200.0, 5.0F, 0.75F, 0.55F, 0.0F, 0.65F, 0.25F, eco::RenderLod::Macro};
    renderer.observe_frame(frame);
    renderer.update_heatmap(frame, detail, options);
    return uploaded;
}

int main() {
    expected_pixels = 64;
    const eco::Frame frame = make_frame(1);
    const auto composite = render_view(eco::EnvironmentViewMode::Composite, frame);
    const auto resource = render_view(eco::EnvironmentViewMode::ResourceAbsolute, frame);
    const auto gradient = render_view(eco::EnvironmentViewMode::ResourceGradient, frame);
    const auto hazard = render_view(eco::EnvironmentViewMode::Hazard, frame);
    const auto population = render_view(eco::EnvironmentViewMode::PopulationDensity, frame);

    assert(!same_colors(composite, resource));
    assert(!same_colors(resource, gradient));
    assert(!same_colors(gradient, hazard));
    assert(!same_colors(hazard, population));

    // Hazard-only mode should make a high-hazard cell more red-dominant than
    // the composite resource-first mode.
    const std::size_t high_hazard = 6;
    assert(int(hazard[high_hazard].r) - int(hazard[high_hazard].g) >
           int(composite[high_hazard].r) - int(composite[high_hazard].g));

    // Population-only mode must distinguish the occupied and empty regions.
    const int occupied_brightness = int(population[0].g) + int(population[0].b);
    const int empty_brightness = int(population[63].g) + int(population[63].b);
    assert(occupied_brightness > empty_brightness);

    eco::WorldRenderer delta_renderer;
    eco::RenderOptions delta_options;
    delta_options.environment_filter = eco::EnvironmentFilterMode::Instant;
    delta_options.environment_view = eco::EnvironmentViewMode::ResourceDelta;
    delta_options.show_population_density = false;
    eco::RenderDetail detail{0.0, 8.0F, 0.2F, 0.9F, 0.2F, 0.2F, 0.65F, eco::RenderLod::Medium};
    eco::Frame first = make_frame(1);
    delta_renderer.observe_frame(first);
    delta_renderer.update_heatmap(first, detail, delta_options);
    eco::Frame second = make_frame(2, 0.12F);
    delta_renderer.observe_frame(second);
    delta_renderer.update_heatmap(second, detail, delta_options);
    bool saw_positive = false;
    for (const Color color : uploaded) {
        if (color.g > color.r && color.g > color.b) {
            saw_positive = true;
            break;
        }
    }
    assert(saw_positive);
    return 0;
}

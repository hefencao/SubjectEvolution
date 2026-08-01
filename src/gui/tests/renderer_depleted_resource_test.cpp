#include "eco/renderer.hpp"
#include <rlgl.h>

#include <algorithm>
#include <cassert>
#include <vector>

namespace { std::vector<Color> uploaded; std::size_t expected_pixels = 0; }
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
void UpdateTexture(Texture2D,const void* data) { const auto* p=static_cast<const Color*>(data); uploaded.assign(p,p+expected_pixels); }
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

static eco::Frame make_frame(std::uint64_t tick, float scale) {
    eco::Frame frame;
    frame.tick=tick;
    frame.layout.grid_x=16; frame.layout.grid_y=16;
    frame.layout.world_width=160; frame.layout.world_height=160;
    frame.layout.max_energy=5;
    frame.resources.assign(4U*256U,0.0F);
    frame.hazard.assign(256U,0.0F);
    for(int y=0;y<16;++y) for(int x=0;x<16;++x) {
        const auto i=static_cast<std::size_t>(y*16+x);
        const float pattern=0.10F+0.90F*float(x+y)/30.0F;
        frame.resources[i]=pattern*scale;
    }
    return frame;
}

int main(){
    expected_pixels=256;
    eco::WorldRenderer renderer;
    eco::RenderOptions options;
    options.environment_filter=eco::EnvironmentFilterMode::Instant;
    options.environment_view=eco::EnvironmentViewMode::ResourceAbsolute;
    options.show_population_density=false;
    options.show_hazard=false;
    eco::RenderDetail detail{0.0,3.0F,1.0F,0.0F,0.0F,1.0F,0.0F,eco::RenderLod::Macro};

    auto initial=make_frame(1,1.0F);
    renderer.observe_frame(initial);
    renderer.update_heatmap(initial,detail,options);

    for(std::uint64_t tick=65;tick<=641;tick+=64){
        auto depleted=make_frame(tick,0.001F);
        renderer.observe_frame(depleted);
        renderer.update_heatmap(depleted,detail,options);
    }

    int min_brightness=100000, max_brightness=0;
    for(const auto c:uploaded){
        const int b=int(c.r)+int(c.g)+int(c.b);
        min_brightness=std::min(min_brightness,b);
        max_brightness=std::max(max_brightness,b);
    }
    // Absolute abundance stays depleted, but adaptive contrast preserves the
    // remaining spatial structure instead of turning the entire field black.
    assert(renderer.diagnostics().mean_resource < 0.01F);
    assert(max_brightness-min_brightness > 35);
    return 0;
}

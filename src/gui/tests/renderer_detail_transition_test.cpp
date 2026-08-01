#include "eco/renderer.hpp"
#include <rlgl.h>

#include <algorithm>
#include <cassert>
#include <cmath>

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

int main() {
    eco::Frame frame;
    frame.layout.world_width = 1024.0F;
    frame.layout.world_height = 1024.0F;
    frame.entities.resize(130000);
    Rectangle viewport{540.0F, 0.0F, 900.0F, 900.0F};
    Camera2D camera{{990.0F,450.0F},{512.0F,512.0F},0.0F,1.0F};

    const eco::RenderDetail at_one = eco::resolve_render_detail(
        frame, camera, viewport, eco::LodMode::Auto
    );
    camera.zoom = 1.1F;
    const eco::RenderDetail at_one_one = eco::resolve_render_detail(
        frame, camera, viewport, eco::LodMode::Auto
    );

    // The historically abrupt 1.0 -> 1.1 step must now remain a small,
    // monotonic screen-space change rather than changing the entire layer set.
    assert(at_one_one.projected_spacing > at_one.projected_spacing);
    assert(at_one_one.agent_weight >= at_one.agent_weight);
    assert(std::abs(at_one_one.agent_weight - at_one.agent_weight) < 0.08F);
    assert(std::abs(at_one_one.density_weight - at_one.density_weight) < 0.08F);
    assert(at_one.dominant == at_one_one.dominant);

    camera.zoom = 4.0F;
    const eco::RenderDetail medium = eco::resolve_render_detail(
        frame, camera, viewport, eco::LodMode::Auto
    );
    assert(medium.agent_weight > 0.45F);
    assert(medium.dominant == eco::RenderLod::Medium);

    camera.zoom = 15.0F;
    const eco::RenderDetail micro = eco::resolve_render_detail(
        frame, camera, viewport, eco::LodMode::Auto
    );
    assert(micro.micro_weight > 0.75F);
    assert(micro.dominant == eco::RenderLod::Micro);

    const eco::RenderDetail forced_macro = eco::resolve_render_detail(
        frame, camera, viewport, eco::LodMode::ForceMacro
    );
    assert(forced_macro.dominant == eco::RenderLod::Macro);
    assert(forced_macro.density_weight == 1.0F);
    return 0;
}

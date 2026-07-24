#include "eco/renderer.hpp"
#include <rlgl.h>

#include <cassert>
#include <cmath>
#include <vector>

namespace {
std::vector<Vector2> vertices;
std::vector<Vector2> texcoords;
unsigned int current_texture = 0;
unsigned int nonzero_texture_sets = 0;
int current_mode = 0;
}

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
Color Fade(Color c,float a) { c.a=(unsigned char)(c.a*(a<0?0:a>1?1:a)); return c; }
Image GenImageColor(int w,int h,Color) { return {nullptr,w,h,1,0}; }
Texture2D LoadTextureFromImage(Image i) { return {1u,i.width,i.height,1,0}; }
void UnloadImage(Image) {}
void UnloadTexture(Texture2D) {}
void UpdateTexture(Texture2D,const void*) {}
void SetTextureFilter(Texture2D,int) {}
Texture2D GetShapesTexture() { return {7u,1,1,1,0}; }
Rectangle GetShapesTextureRectangle() { return {0.0F,0.0F,1.0F,1.0F}; }
void rlSetTexture(unsigned int id) {
    current_texture=id;
    if (id != 0) ++nonzero_texture_sets;
}
void rlBegin(int mode) { current_mode=mode; }
void rlEnd() { current_mode=0; }
void rlNormal3f(float,float,float) {}
void rlColor4ub(unsigned char,unsigned char,unsigned char,unsigned char) {}
void rlTexCoord2f(float u,float v) { if (current_mode == RL_QUADS) texcoords.push_back({u,v}); }
void rlVertex2f(float x,float y) { if (current_mode == RL_QUADS) vertices.push_back({x,y}); }

int main() {
    eco::WorldRenderer renderer;
    eco::Frame frame;
    frame.tick=1;
    frame.layout.grid_x=16;
    frame.layout.grid_y=16;
    frame.layout.world_width=100.0F;
    frame.layout.world_height=100.0F;
    frame.layout.max_energy=5.0F;
    frame.resources.resize(4u*16u*16u,0.5F);
    frame.hazard.resize(16u*16u,0.1F);
    frame.entities.resize(1);
    auto& entity=frame.entities.front();
    entity.entity_id=42;
    entity.group_id=3;
    entity.x=50.0F;
    entity.y=50.0F;
    entity.energy=4.0F;
    entity.integrity=1.0F;

    eco::RenderOptions options;
    options.lod_mode=eco::LodMode::ForceMicro;
    Camera2D camera{{400.0F,300.0F},{50.0F,50.0F},0.0F,2.0F};
    Rectangle viewport{0.0F,0.0F,800.0F,600.0F};

    renderer.observe_frame(frame);
    renderer.update_heatmap(frame,eco::RenderDetail{0.0,20.0F,0.0F,1.0F,1.0F,0.0F,1.0F,eco::RenderLod::Micro},options);
    renderer.draw(frame,camera,viewport,options,{});

    // Outline, body and bright core: one textured solid quad each.
    assert(nonzero_texture_sets >= 3);
    assert(vertices.size() >= 12);
    assert(texcoords.size() == vertices.size());

    // The first quad must match raylib DrawRectanglePro winding: TL, BL, BR, TR.
    const Vector2 tl=vertices[0];
    const Vector2 bl=vertices[1];
    const Vector2 br=vertices[2];
    const Vector2 tr=vertices[3];
    assert(std::abs(tl.x-bl.x) < 1.0e-5F);
    assert(std::abs(bl.y-br.y) < 1.0e-5F);
    assert(std::abs(br.x-tr.x) < 1.0e-5F);
    assert(std::abs(tr.y-tl.y) < 1.0e-5F);
    assert(tl.x < tr.x);
    assert(tl.y < bl.y);
    assert(current_texture == 0);

    // Medium uses the same validated rlgl shape-texture path.
    vertices.clear();
    texcoords.clear();
    nonzero_texture_sets = 0;
    options.lod_mode = eco::LodMode::ForceMedium;
    renderer.update_heatmap(frame, eco::RenderDetail{0.0,7.0F,0.3F,1.0F,0.1F,0.3F,0.5F,eco::RenderLod::Medium}, options);
    renderer.draw(frame, camera, viewport, options, {});
    assert(nonzero_texture_sets >= 2);
    assert(vertices.size() >= 8);
    assert(texcoords.size() == vertices.size());
    assert(current_texture == 0);
    return 0;
}

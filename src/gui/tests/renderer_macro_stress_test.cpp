#include "eco/renderer.hpp"
#include <cassert>
#include <algorithm>
#include <cmath>
#include <cstdarg>
#include <limits>

Vector2 GetScreenToWorld2D(Vector2 p, Camera2D c) { return {(p.x-c.offset.x)/c.zoom+c.target.x,(p.y-c.offset.y)/c.zoom+c.target.y}; }
Vector2 GetWorldToScreen2D(Vector2 p, Camera2D c) { return {(p.x-c.target.x)*c.zoom+c.offset.x,(p.y-c.target.y)*c.zoom+c.offset.y}; }
void DrawLineEx(Vector2,Vector2,float,Color) {}
void DrawCircleV(Vector2,float,Color) {}
void DrawCircleLines(int,int,float,Color) {}
void DrawRectangleRec(Rectangle,Color) {}
void DrawRectangleLinesEx(Rectangle,float,Color) {}
void DrawTexturePro(Texture2D,Rectangle,Rectangle,Vector2,float,Color) {}
void DrawTriangle(Vector2,Vector2,Vector2,Color) {}
Color Fade(Color c,float a) { c.a=(unsigned char)(c.a*std::clamp(a,0.0f,1.0f)); return c; }
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
    eco::WorldRenderer renderer;
    eco::Frame frame;
    frame.layout.grid_x=128; frame.layout.grid_y=128;
    frame.layout.world_width=256.0f; frame.layout.world_height=256.0f; frame.layout.max_energy=5.0f;
    frame.resources.resize(4u*128u*128u,0.5f);
    frame.hazard.resize(128u*128u,0.2f);
    frame.entities.resize(70000);
    for (std::size_t i=0;i<frame.entities.size();++i) {
        auto &e=frame.entities[i];
        e.entity_id=i+1; e.group_id=(i%1500)+1;
        e.x=float((i*37)%25600)/100.0f; e.y=float((i*73)%25600)/100.0f;
        e.vx=float(int(i%7)-3)*0.04f; e.vy=float(int(i%5)-2)*0.05f;
        e.energy=2.5f; e.integrity=1.0f; e.action=(std::uint8_t)eco::Action::Harvest; e.action_success=(i%11==0);
    }
    // Invalid samples must be ignored, not sent to indexing or rlgl.
    frame.entities[17].x=std::numeric_limits<float>::quiet_NaN();
    frame.entities[29].vx=std::numeric_limits<float>::infinity();

    eco::RenderOptions options; options.lod_mode=eco::LodMode::ForceMacro;
    Camera2D camera{{960,540},{128,128},0,3.0f};
    Rectangle viewport{512,0,1408,1080};
    std::vector<eco::SocialNeighbor> neighbors;
    for (std::uint64_t tick=1;tick<=96;++tick) {
        frame.tick=tick;
        // Force births/deaths over time and enough event markers to exercise cap.
        for (std::size_t i=0;i<512;++i) {
            const std::size_t idx=(i+tick*31)%frame.entities.size();
            frame.entities[idx].entity_id=1000000+tick*1000+i;
            frame.entities[idx].action=(std::uint8_t)((i&1)?eco::Action::Harvest:eco::Action::Reproduce);
            frame.entities[idx].action_success=1;
        }
        renderer.observe_frame(frame);
        renderer.update_heatmap(frame,eco::RenderDetail{0.0,2.0F,1.0F,0.05F,0.0F,1.0F,0.0F,eco::RenderLod::Macro},options);
        renderer.draw(frame,camera,viewport,options,neighbors);
    }
    assert(renderer.diagnostics().harvests>0);
}

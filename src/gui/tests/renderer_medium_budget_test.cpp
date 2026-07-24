#include "eco/renderer.hpp"
#include <rlgl.h>

#include <cassert>
#include <cmath>
#include <cstddef>

namespace { std::size_t quad_vertices=0; int current_mode=0; }
Vector2 GetScreenToWorld2D(Vector2 p, Camera2D c){return{(p.x-c.offset.x)/c.zoom+c.target.x,(p.y-c.offset.y)/c.zoom+c.target.y};}
Vector2 GetWorldToScreen2D(Vector2 p, Camera2D c){return{(p.x-c.target.x)*c.zoom+c.offset.x,(p.y-c.target.y)*c.zoom+c.offset.y};}
void DrawLineEx(Vector2,Vector2,float,Color){}
void DrawCircleV(Vector2,float,Color){}
void DrawCircleLines(int,int,float,Color){}
void DrawRectangleLinesEx(Rectangle,float,Color){}
void DrawTexturePro(Texture2D,Rectangle,Rectangle,Vector2,float,Color){}
void DrawTriangle(Vector2,Vector2,Vector2,Color){}
Color Fade(Color c,float a){c.a=(unsigned char)(c.a*(a<0?0:a>1?1:a));return c;}
Image GenImageColor(int w,int h,Color){return{nullptr,w,h,1,0};}
Texture2D LoadTextureFromImage(Image i){return{1u,i.width,i.height,1,0};}
void UnloadImage(Image){}
void UnloadTexture(Texture2D){}
void UpdateTexture(Texture2D,const void*){}
void SetTextureFilter(Texture2D,int){}
Texture2D GetShapesTexture(){return{7u,1,1,1,0};}
Rectangle GetShapesTextureRectangle(){return{0,0,1,1};}
void rlSetTexture(unsigned int){}
void rlBegin(int mode){current_mode=mode;}
void rlEnd(){current_mode=0;}
void rlNormal3f(float,float,float){}
void rlColor4ub(unsigned char,unsigned char,unsigned char,unsigned char){}
void rlTexCoord2f(float,float){}
void rlVertex2f(float,float){if(current_mode==RL_QUADS)++quad_vertices;}

int main(){
    eco::Frame frame;
    frame.tick=1;
    frame.layout.grid_x=32; frame.layout.grid_y=32;
    frame.layout.world_width=1950.0F; frame.layout.world_height=1950.0F;
    frame.layout.max_energy=5.0F;
    frame.resources.assign(4U*1024U,0.4F);
    frame.hazard.assign(1024U,0.0F);
    frame.entities.resize(80000);
    for(std::size_t i=0;i<frame.entities.size();++i){
        auto& e=frame.entities[i];
        e.entity_id=i+1;
        e.x=float((i*37)%1950);
        e.y=float((i*91)%1950);
        e.energy=3.0F; e.integrity=1.0F;
    }
    eco::WorldRenderer renderer;
    eco::RenderOptions options;
    options.lod_mode=eco::LodMode::Auto;
    options.show_event_markers=false;
    options.show_population_density=true;
    Rectangle viewport{540,0,900,900};
    Camera2D camera{{990,450},{975,975},0,1.0F};
    renderer.observe_frame(frame);
    const auto detail=eco::resolve_render_detail(frame,camera,viewport,options.lod_mode);
    assert(detail.projected_spacing>6.0F && detail.projected_spacing<8.0F);
    assert(detail.agent_weight<0.20F);
    renderer.update_heatmap(frame,detail,options);
    renderer.draw(frame,camera,viewport,options,{});
    // At this historically noisy scale, v9 should select roughly one stable
    // representative per ~28px tile rather than tens of thousands of agents.
    const std::size_t quads=quad_vertices/4U;
    assert(quads>0);
    assert(quads<5000);
    return 0;
}

#include "eco/renderer.hpp"
#include <rlgl.h>
#include <algorithm>
#include <cassert>

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
Rectangle GetShapesTextureRectangle() { return {0,0,1,1}; }
void rlSetTexture(unsigned int) {}
void rlBegin(int) {}
void rlEnd() {}
void rlNormal3f(float,float,float) {}
void rlColor4ub(unsigned char,unsigned char,unsigned char,unsigned char) {}
void rlTexCoord2f(float,float) {}
void rlVertex2f(float,float) {}

int main() {
    using eco::Action;
    using eco::ActionFilterMode;
    using eco::action_matches_filter;

    assert(action_matches_filter(Action::Harvest, ActionFilterMode::All));
    assert(action_matches_filter(Action::MoveResource, ActionFilterMode::Movement));
    assert(action_matches_filter(Action::Flee, ActionFilterMode::Movement));
    assert(!action_matches_filter(Action::Harvest, ActionFilterMode::Movement));
    assert(action_matches_filter(Action::Harvest, ActionFilterMode::Resource));
    assert(action_matches_filter(Action::MoveResource, ActionFilterMode::Resource));
    assert(action_matches_filter(Action::Share, ActionFilterMode::Social));
    assert(action_matches_filter(Action::Signal, ActionFilterMode::Social));
    assert(!action_matches_filter(Action::Flee, ActionFilterMode::Social));
    assert(action_matches_filter(Action::Reproduce, ActionFilterMode::Reproduction));
    assert(!action_matches_filter(Action::Share, ActionFilterMode::Reproduction));
    assert(action_matches_filter(Action::Flee, ActionFilterMode::Survival));
    assert(action_matches_filter(Action::Rest, ActionFilterMode::Survival));
    return 0;
}

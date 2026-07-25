#include <raylib.h>
#include <rlgl.h>
#include <cstdarg>
#define WEAK __attribute__((weak))
WEAK Vector2 GetScreenToWorld2D(Vector2 p, Camera2D c){return {(p.x-c.offset.x)/c.zoom+c.target.x,(p.y-c.offset.y)/c.zoom+c.target.y};}
WEAK Vector2 GetWorldToScreen2D(Vector2 p, Camera2D c){return {(p.x-c.target.x)*c.zoom+c.offset.x,(p.y-c.target.y)*c.zoom+c.offset.y};}
WEAK Vector2 GetMousePosition(){return {};}
WEAK Vector2 GetMouseDelta(){return {};}
WEAK float GetMouseWheelMove(){return 0;}
WEAK int GetCharPressed(){return 0;}
WEAK double GetTime(){return 0.0;}
WEAK int GetScreenWidth(){return 1280;}
WEAK int GetScreenHeight(){return 720;}
WEAK int GetFPS(){return 60;}
WEAK bool CheckCollisionPointRec(Vector2,Rectangle){return false;}
WEAK bool IsKeyPressed(int){return false;}
WEAK bool IsMouseButtonDown(int){return false;}
WEAK bool IsMouseButtonPressed(int){return false;}
WEAK bool WindowShouldClose(){return true;}
WEAK void SetConfigFlags(unsigned int){}
WEAK void InitWindow(int,int,const char*){}
WEAK void CloseWindow(){}
WEAK void SetTargetFPS(int){}
WEAK void SetWindowTitle(const char*){}
WEAK void SetWindowMinSize(int,int){}
WEAK void SetWindowSize(int,int){}
WEAK int MeasureText(const char* text,int size){int n=0; if(text){while(text[n]) ++n;} return n*size/2;}
WEAK Vector2 MeasureTextEx(Font,const char* text,float size,float){int n=0; if(text){while(text[n]) ++n;} return {n*size*0.6f,size};}
WEAK Font GetFontDefault(){return {16,96,0,Texture2D{1u,1,1,1,0},nullptr,nullptr};}
WEAK Font LoadFontEx(const char*,int size,int*,int){return {size,96,0,Texture2D{1u,1,1,1,0},nullptr,nullptr};}
WEAK void UnloadFont(Font){}
WEAK void DrawTextEx(Font,const char*,Vector2,float,float,Color){}
WEAK void SetClipboardText(const char*){}
WEAK void BeginDrawing(){}
WEAK void EndDrawing(){}
WEAK void ClearBackground(Color){}
WEAK void BeginMode2D(Camera2D){}
WEAK void EndMode2D(){}
WEAK void BeginScissorMode(int,int,int,int){}
WEAK void EndScissorMode(){}
WEAK void DrawText(const char*,int,int,int,Color){}
WEAK void DrawRectangle(int,int,int,int,Color){}
WEAK void DrawRectangleRec(Rectangle,Color){}
WEAK void DrawRectangleLinesEx(Rectangle,float,Color){}
WEAK void DrawLine(int,int,int,int,Color){}
WEAK void DrawLineV(Vector2,Vector2,Color){}
WEAK void DrawLineEx(Vector2,Vector2,float,Color){}
WEAK void DrawCircleV(Vector2,float,Color){}
WEAK void DrawCircleLines(int,int,float,Color){}
WEAK void DrawTriangle(Vector2,Vector2,Vector2,Color){}
WEAK void DrawTexturePro(Texture2D,Rectangle,Rectangle,Vector2,float,Color){}
WEAK Color Fade(Color c,float a){c.a=(unsigned char)(c.a*a);return c;}
WEAK Image GenImageColor(int w,int h,Color){return {nullptr,w,h,1,0};}
WEAK Texture2D LoadTextureFromImage(Image i){return {1u,i.width,i.height,1,0};}
WEAK void UnloadImage(Image){}
WEAK void UnloadTexture(Texture2D){}
WEAK void UpdateTexture(Texture2D,const void*){}
WEAK void SetTextureFilter(Texture2D,int){}
WEAK Texture2D GetShapesTexture(){return {7u,1,1,1,0};}
WEAK Rectangle GetShapesTextureRectangle(){return {0,0,1,1};}
WEAK const char* TextFormat(const char* fmt,...){return fmt;}
WEAK void rlSetTexture(unsigned int){}
WEAK void rlBegin(int){}
WEAK void rlEnd(){}
WEAK void rlNormal3f(float,float,float){}
WEAK void rlColor4ub(unsigned char,unsigned char,unsigned char,unsigned char){}
WEAK void rlTexCoord2f(float,float){}
WEAK void rlVertex2f(float,float){}
WEAK bool IsWindowReady(){return true;}
WEAK Shader LoadShaderFromMemory(const char*,const char*){static int locs[32]{};return {11u,locs};}
WEAK void UnloadShader(Shader){}
WEAK int GetShaderLocation(Shader,const char*){return 1;}
WEAK void SetShaderValue(Shader,int,const void*,int){}
WEAK void BeginShaderMode(Shader){}
WEAK void EndShaderMode(){}
WEAK int rlGetVersion(){return RL_OPENGL_21;}
WEAK unsigned int rlLoadVertexArray(){return 21u;}
WEAK bool rlEnableVertexArray(unsigned int){return true;}
WEAK void rlDisableVertexArray(){}
WEAK unsigned int rlLoadVertexBuffer(const void*,int,bool){static unsigned int next=30u;return next++;}
WEAK void rlUpdateVertexBuffer(unsigned int,const void*,int,int){}
WEAK void rlEnableVertexBuffer(unsigned int){}
WEAK void rlDisableVertexBuffer(){}
WEAK void rlEnableVertexAttribute(unsigned int){}
WEAK void rlSetVertexAttribute(unsigned int,int,int,bool,int,int){}
WEAK void rlSetVertexAttributeDivisor(unsigned int,int){}
WEAK void rlDrawVertexArrayInstanced(int,int,int){}
WEAK void rlUnloadVertexArray(unsigned int){}
WEAK void rlUnloadVertexBuffer(unsigned int){}
WEAK void rlDrawRenderBatchActive(){}

#include "eco/renderer.hpp"

#include <cassert>
#include <cstdarg>

// Link-only raylib/rlgl stubs.  The test exercises frame observation, not GPU IO.
void SetConfigFlags(unsigned int) {}
void InitWindow(int, int, const char*) {}
void CloseWindow() {}
bool WindowShouldClose() { return true; }
void SetTargetFPS(int) {}
int GetScreenWidth() { return 1280; }
int GetScreenHeight() { return 720; }
int GetFPS() { return 60; }
Vector2 GetMousePosition() { return {}; }
Vector2 GetMouseDelta() { return {}; }
float GetMouseWheelMove() { return 0.0F; }
bool IsMouseButtonPressed(int) { return false; }
bool IsMouseButtonDown(int) { return false; }
bool IsKeyPressed(int) { return false; }
bool CheckCollisionPointRec(Vector2, Rectangle) { return false; }
Vector2 GetScreenToWorld2D(Vector2 point, Camera2D) { return point; }
Vector2 GetWorldToScreen2D(Vector2 point, Camera2D) { return point; }
void BeginDrawing() {}
void EndDrawing() {}
void BeginMode2D(Camera2D) {}
void EndMode2D() {}
void BeginScissorMode(int, int, int, int) {}
void EndScissorMode() {}
void ClearBackground(Color) {}
void DrawText(const char*, int, int, int, Color) {}
const char* TextFormat(const char* text, ...) { return text; }
void DrawRectangle(int, int, int, int, Color) {}
void DrawRectangleRec(Rectangle, Color) {}
void DrawRectangleLinesEx(Rectangle, float, Color) {}
void DrawLine(int, int, int, int, Color) {}
void DrawLineV(Vector2, Vector2, Color) {}
void DrawLineEx(Vector2, Vector2, float, Color) {}
void DrawCircleV(Vector2, float, Color) {}
void DrawCircleLines(int, int, float, Color) {}
void DrawTriangle(Vector2, Vector2, Vector2, Color) {}
void DrawTexturePro(Texture2D, Rectangle, Rectangle, Vector2, float, Color) {}
Color Fade(Color color, float) { return color; }
Image GenImageColor(int width, int height, Color) { return Image{nullptr, width, height, 1, 0}; }
Texture2D LoadTextureFromImage(Image image) { return Texture2D{0, image.width, image.height, 1, 0}; }
void UnloadImage(Image) {}
void UnloadTexture(Texture2D) {}
void UpdateTexture(Texture2D, const void*) {}
void SetTextureFilter(Texture2D, int) {}
Texture2D GetShapesTexture() { return {7u,1,1,1,0}; }
Rectangle GetShapesTextureRectangle() { return {0.0F,0.0F,1.0F,1.0F}; }
void rlSetTexture(unsigned int) {}
void rlBegin(int) {}
void rlEnd() {}
void rlNormal3f(float,float,float) {}
void rlColor4ub(unsigned char, unsigned char, unsigned char, unsigned char) {}
void rlTexCoord2f(float, float) {}
void rlVertex2f(float, float) {}

int main() {
    eco::WorldRenderer renderer;

    eco::Frame first;
    first.tick = 1;
    first.layout.world_width = 100.0F;
    first.layout.world_height = 100.0F;
    first.layout.max_energy = 10.0F;
    first.entities.resize(2);
    first.entities[0].entity_id = 1;
    first.entities[0].x = 10.0F;
    first.entities[0].y = 10.0F;
    first.entities[1].entity_id = 2;
    first.entities[1].x = 20.0F;
    first.entities[1].y = 20.0F;

    renderer.observe_frame(first);
    assert(renderer.diagnostics().births == 0);
    assert(renderer.diagnostics().deaths == 0);

    eco::Frame second = first;
    second.tick = 2;
    second.entities.clear();
    second.entities.resize(2);
    second.entities[0].entity_id = 2;
    second.entities[0].x = 21.0F;
    second.entities[0].y = 20.0F;
    second.entities[0].vx = 0.2F;
    second.entities[0].action = static_cast<std::uint8_t>(eco::Action::Harvest);
    second.entities[0].action_success = 1;
    second.entities[1].entity_id = 3;
    second.entities[1].x = 30.0F;
    second.entities[1].y = 30.0F;
    second.entities[1].action = static_cast<std::uint8_t>(eco::Action::Reproduce);
    second.entities[1].action_success = 1;

    renderer.observe_frame(second);
    const eco::FrameDiagnostics& diagnostics = renderer.diagnostics();
    assert(diagnostics.births == 1);
    assert(diagnostics.deaths == 1);
    assert(diagnostics.harvests == 1);
    assert(diagnostics.reproductions == 1);
    assert(diagnostics.moving_entities == 1);

    return 0;
}

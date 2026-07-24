#include "eco/renderer.hpp"

#include <cassert>
#include <cmath>
#include <cstdarg>

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
Image GenImageColor(int width, int height, Color) { return {nullptr, width, height, 1, 0}; }
Texture2D LoadTextureFromImage(Image image) { return {1u, image.width, image.height, 1, 0}; }
void UnloadImage(Image) {}
void UnloadTexture(Texture2D) {}
void UpdateTexture(Texture2D, const void*) {}
void SetTextureFilter(Texture2D, int) {}
Texture2D GetShapesTexture() { return {7u, 1, 1, 1, 0}; }
Rectangle GetShapesTextureRectangle() { return {0.0F, 0.0F, 1.0F, 1.0F}; }
void rlSetTexture(unsigned int) {}
void rlBegin(int) {}
void rlEnd() {}
void rlNormal3f(float, float, float) {}
void rlColor4ub(unsigned char, unsigned char, unsigned char, unsigned char) {}
void rlTexCoord2f(float, float) {}
void rlVertex2f(float, float) {}

int main() {
    eco::WorldRenderer renderer;
    eco::Frame frame;
    frame.tick = 1;
    frame.layout.world_width = 100.0F;
    frame.layout.world_height = 100.0F;
    frame.layout.max_energy = 5.0F;
    frame.entities.resize(4);

    const float xs[4] = {99.0F, 1.0F, 98.0F, 2.0F};
    for (int index = 0; index < 4; ++index) {
        auto& entity = frame.entities[static_cast<std::size_t>(index)];
        entity.entity_id = static_cast<std::uint64_t>(index + 1);
        entity.group_id = 42;
        entity.x = xs[index];
        entity.y = 50.0F + static_cast<float>(index % 2);
        entity.vx = 0.1F;
        entity.energy = 2.0F;
        entity.integrity = 1.0F;
        entity.action = static_cast<std::uint8_t>(eco::Action::MoveResource);
    }

    renderer.observe_frame(frame);
    const eco::GroupBehaviorSummary* group = renderer.group_behavior(
        42, eco::OverlayTemporalMode::Instant
    );
    assert(group != nullptr);
    assert(group->x < 4.0F || group->x > 96.0F);
    assert(group->spread_major < 4.0F);
    assert(group->spread_minor < 2.0F);
    assert(std::abs(group->mean_vx - 0.1F) < 1.0e-4F);

    const eco::RenderPerformance& performance = renderer.performance();
    assert(performance.observe_ms >= performance.observe_scan_ms);
    assert(performance.observe_scan_ms >= 0.0);
    assert(performance.observe_groups_ms >= 0.0);
    return 0;
}

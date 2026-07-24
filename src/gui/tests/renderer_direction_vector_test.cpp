#include "eco/renderer.hpp"
#include "render/renderer_internal.hpp"

#include <cassert>
#include <cmath>
#include <vector>

namespace {
struct Segment { Vector2 start; Vector2 end; };
std::vector<Segment> segments;
}

void DrawLineEx(Vector2 start, Vector2 end, float, Color) {
    segments.push_back(Segment{start, end});
}

int main() {
    Camera2D camera{{0.0F, 0.0F}, {0.0F, 0.0F}, 0.0F, 1.0F};

    segments.clear();
    const bool drew_up = eco::render_internal::draw_action_glyph(
        eco::Action::MoveResource,
        Vector2{50.0F, 50.0F},
        8.0F,
        camera,
        1.0F,
        Vector2{0.0F, -2.0F}
    );
    assert(drew_up);
    assert(segments.size() >= 6U);  // shadow + color layers
    // The main shaft must be vertical and point upward in raylib screen/world
    // coordinates, not fall back to the template's right-facing direction.
    assert(std::abs(segments[0].start.x - segments[0].end.x) < 1.0e-4F);
    assert(segments[0].end.y < segments[0].start.y);

    segments.clear();
    const bool drew_zero = eco::render_internal::draw_action_glyph(
        eco::Action::Flee,
        Vector2{10.0F, 10.0F},
        7.0F,
        camera,
        1.0F,
        Vector2{0.0F, 0.0F}
    );
    assert(!drew_zero);
    assert(segments.empty());

    segments.clear();
    const bool drew_left = eco::render_internal::draw_action_glyph(
        eco::Action::Flee,
        Vector2{30.0F, 30.0F},
        7.0F,
        camera,
        1.0F,
        Vector2{-1.0F, 0.0F}
    );
    assert(drew_left);
    assert(!segments.empty());
    // The first chevron tail is to the right of its left-facing apex.
    assert(segments[0].start.x > segments[0].end.x);

    const Vector2 wrapped = eco::render_internal::resolve_motion_vector(
        Vector2{0.0F, 0.0F},
        Vector2{1.0F, 50.0F},
        Vector2{99.0F, 50.0F},
        100.0F,
        100.0F
    );
    assert(std::abs(wrapped.x - 2.0F) < 1.0e-4F);
    assert(std::abs(wrapped.y) < 1.0e-4F);

    return 0;
}

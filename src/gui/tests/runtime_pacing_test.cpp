#include "eco/runtime_pacing.hpp"

#include <cassert>
#include <chrono>

int main() {
    using namespace std::chrono_literals;
    using eco::runtime::PollBackoff;

    static_assert(eco::runtime::kLauncherTargetFps == 30);
    static_assert(eco::runtime::kRuntimeTargetFps == 60);
    static_assert(eco::runtime::kMonitorPollInterval == 250ms);
    static_assert(eco::runtime::kFinishedMonitorPollInterval == 1000ms);

    PollBackoff backoff{4ms, 32ms};
    assert(backoff.after_activity() == 4ms);
    assert(backoff.after_idle() == 4ms);
    assert(backoff.after_idle() == 8ms);
    assert(backoff.after_idle() == 16ms);
    assert(backoff.after_idle() == 32ms);
    assert(backoff.after_idle() == 32ms);
    assert(backoff.after_activity() == 4ms);
    assert(backoff.current() == 4ms);
    return 0;
}

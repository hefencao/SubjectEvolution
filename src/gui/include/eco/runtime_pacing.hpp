#pragma once

#include <algorithm>
#include <chrono>

namespace eco::runtime {

inline constexpr int kLauncherTargetFps = 30;
inline constexpr int kRuntimeTargetFps = 60;
inline constexpr std::chrono::milliseconds kMonitorPollInterval{250};
inline constexpr std::chrono::milliseconds kFinishedMonitorPollInterval{1000};

class PollBackoff {
public:
    using Duration = std::chrono::milliseconds;

    explicit PollBackoff(Duration minimum = Duration{4}, Duration maximum = Duration{64})
        : minimum_(std::max(Duration{1}, minimum)),
          maximum_(std::max(minimum_, maximum)),
          current_(minimum_) {}

    [[nodiscard]] Duration after_activity() noexcept {
        current_ = minimum_;
        return minimum_;
    }

    [[nodiscard]] Duration after_idle() noexcept {
        const Duration delay = current_;
        current_ = std::min(maximum_, current_ * 2);
        return delay;
    }

    void reset() noexcept { current_ = minimum_; }

    [[nodiscard]] Duration current() const noexcept { return current_; }
    [[nodiscard]] Duration minimum() const noexcept { return minimum_; }
    [[nodiscard]] Duration maximum() const noexcept { return maximum_; }

private:
    Duration minimum_;
    Duration maximum_;
    Duration current_;
};

}  // namespace eco::runtime

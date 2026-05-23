"""System state management module.

This module will maintain runtime mode transitions (OFF, ACTIVE,
APP_SWITCH) and enforce gesture priority rules.
"""

from __future__ import annotations


class StateManager:
    """Manage runtime system activation state and toggle debounce."""

    def __init__(self, hold_frames: int, cooldown_seconds: float) -> None:
        self._active = False
        self._fist_frame_streak = 0
        self._hold_frames = max(1, hold_frames)
        self._cooldown_seconds = cooldown_seconds
        self._last_toggle_time = -1e9

    @property
    def is_active(self) -> bool:
        return self._active

    def update_toggle(self, closed_fist_detected: bool, now_seconds: float) -> bool:
        """Update activation state using closed-fist hold gesture.

        Returns True when state toggles in the current frame.
        """
        if closed_fist_detected:
            self._fist_frame_streak += 1
        else:
            self._fist_frame_streak = 0

        if now_seconds - self._last_toggle_time < self._cooldown_seconds:
            return False

        if self._fist_frame_streak < self._hold_frames:
            return False

        self._active = not self._active
        self._last_toggle_time = now_seconds
        self._fist_frame_streak = 0
        return True

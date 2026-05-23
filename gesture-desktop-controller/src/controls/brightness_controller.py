"""Brightness control module.

This module will map gesture-driven vertical motion to display brightness
adjustments with safe update logic.
"""

from __future__ import annotations

import screen_brightness_control as sbc


class BrightnessController:
    """Adjust display brightness based on normalized vertical gesture motion."""

    def __init__(
        self,
        step_percent: int = 4,
        motion_threshold: float = 0.025,
        cooldown_seconds: float = 0.08,
    ) -> None:
        self._step_percent = max(1, int(step_percent))
        self._motion_threshold = max(0.005, float(motion_threshold))
        self._cooldown_seconds = max(0.0, float(cooldown_seconds))
        self._last_y = None
        self._last_update_time = -1e9
        self._last_known_brightness = self._get_current_brightness()

    def reset(self) -> None:
        """Reset gesture-tracking memory when brightness gesture is inactive."""
        self._last_y = None

    def update(self, y_norm: float, now_seconds: float, active: bool) -> tuple[bool, int | None]:
        """Update brightness from two-finger vertical movement.

        Returns:
            (changed, level) where level is the latest known brightness.
        """
        if not active:
            self.reset()
            return False, self._last_known_brightness

        y_norm = min(max(y_norm, 0.0), 1.0)
        if self._last_y is None:
            self._last_y = y_norm
            return False, self._last_known_brightness

        delta = self._last_y - y_norm  # positive when hand moves upward
        if abs(delta) < self._motion_threshold:
            return False, self._last_known_brightness

        if now_seconds - self._last_update_time < self._cooldown_seconds:
            return False, self._last_known_brightness

        direction = 1 if delta > 0 else -1
        steps = max(1, int(abs(delta) / self._motion_threshold))
        current = self._get_current_brightness()
        target = int(min(max(current + (direction * steps * self._step_percent), 0), 100))
        changed = self._set_brightness(target)
        self._last_y = y_norm
        self._last_update_time = now_seconds
        return changed, self._last_known_brightness

    def _get_current_brightness(self) -> int:
        try:
            value = sbc.get_brightness()
            if isinstance(value, list):
                value = value[0]
            self._last_known_brightness = int(min(max(value, 0), 100))
        except Exception:
            pass
        return self._last_known_brightness

    def _set_brightness(self, value: int) -> bool:
        value = int(min(max(value, 0), 100))
        try:
            sbc.set_brightness(value)
            self._last_known_brightness = value
            return True
        except Exception:
            return False

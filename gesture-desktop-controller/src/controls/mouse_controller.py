"""Mouse control module.

This module will handle cursor movement and click execution based on
validated gesture events.
"""

from __future__ import annotations

import math

import pyautogui


class MouseController:
    """Map normalized fingertip position to full-screen cursor position."""

    def __init__(
        self,
        smoothing_alpha: float = 0.35,
        active_margin_x: float = 0.08,
        active_margin_y: float = 0.12,
        click_cooldown_seconds: float = 0.35,
    ) -> None:
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        pyautogui.MINIMUM_DURATION = 0
        pyautogui.MINIMUM_SLEEP = 0
        self._screen_width, self._screen_height = pyautogui.size()
        self._alpha = min(max(smoothing_alpha, 0.0), 1.0)
        self._margin_x = min(max(active_margin_x, 0.0), 0.3)
        self._margin_y = min(max(active_margin_y, 0.0), 0.3)
        self._edge_snap_threshold = 0.04
        self._fast_move_threshold_px = 35.0
        self._click_cooldown_seconds = max(0.0, click_cooldown_seconds)
        self._last_click_time = -1e9
        self._pinch_latched = False
        self._smoothed_x = None
        self._smoothed_y = None

    def move_from_normalized(self, x_norm: float, y_norm: float) -> None:
        """Move cursor by direct position mapping from camera to screen."""
        x_norm = min(max(x_norm, 0.0), 1.0)
        y_norm = min(max(y_norm, 0.0), 1.0)

        # Map a smaller interaction box to full screen for better reachability.
        min_x = self._margin_x
        max_x = 1.0 - self._margin_x
        min_y = self._margin_y
        max_y = 1.0 - self._margin_y

        if max_x <= min_x:
            mapped_x = x_norm
        else:
            mapped_x = (x_norm - min_x) / (max_x - min_x)
        if max_y <= min_y:
            mapped_y = y_norm
        else:
            mapped_y = (y_norm - min_y) / (max_y - min_y)

        mapped_x = min(max(mapped_x, 0.0), 1.0)
        mapped_y = min(max(mapped_y, 0.0), 1.0)

        target_x = mapped_x * (self._screen_width - 1)
        target_y = mapped_y * (self._screen_height - 1)

        if self._smoothed_x is None or self._smoothed_y is None:
            self._smoothed_x = target_x
            self._smoothed_y = target_y
        else:
            alpha = self._adaptive_alpha(
                mapped_x=mapped_x,
                mapped_y=mapped_y,
                target_x=target_x,
                target_y=target_y,
            )
            self._smoothed_x = (alpha * target_x) + ((1.0 - alpha) * self._smoothed_x)
            self._smoothed_y = (alpha * target_y) + ((1.0 - alpha) * self._smoothed_y)

        pyautogui.moveTo(int(self._smoothed_x), int(self._smoothed_y))

    def reset(self) -> None:
        """Clear internal smoothing state when tracking is inactive."""
        self._smoothed_x = None
        self._smoothed_y = None

    def maybe_left_click(
        self,
        pinch_distance_ratio: float,
        click_ready: bool,
        pinch_press_threshold: float,
        pinch_release_threshold: float,
        now_seconds: float,
    ) -> bool:
        """Trigger click using pinch hysteresis and one-click-per-close cycle."""
        if not click_ready:
            self._pinch_latched = False
            return False

        if self._pinch_latched:
            if pinch_distance_ratio > pinch_release_threshold:
                self._pinch_latched = False
            return False

        if pinch_distance_ratio >= pinch_press_threshold:
            return False

        if (now_seconds - self._last_click_time) < self._click_cooldown_seconds:
            return False

        pyautogui.click(button="left")
        self._last_click_time = now_seconds
        self._pinch_latched = True
        return True

    def _adaptive_alpha(self, mapped_x: float, mapped_y: float, target_x: float, target_y: float) -> float:
        """Increase responsiveness near edges and during faster hand motion."""
        near_edge = (
            mapped_x < self._edge_snap_threshold
            or mapped_x > (1.0 - self._edge_snap_threshold)
            or mapped_y < self._edge_snap_threshold
            or mapped_y > (1.0 - self._edge_snap_threshold)
        )
        if near_edge:
            return 0.95

        delta = math.hypot(target_x - self._smoothed_x, target_y - self._smoothed_y)
        if delta > self._fast_move_threshold_px:
            return min(0.75, self._alpha + 0.30)

        return self._alpha

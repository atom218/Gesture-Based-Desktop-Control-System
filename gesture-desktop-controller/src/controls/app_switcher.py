"""Application switcher module.

This module will orchestrate app-switch mode actions, including cycling
through windows and confirming selection events.
"""

from __future__ import annotations

import pyautogui


class AppSwitcher:
    """Manage Alt+Tab mode using gesture-driven navigation and selection."""

    def __init__(
        self,
        hold_seconds: float = 1.0,
        timeout_seconds: float = 6.0,
        move_threshold: float = 0.06,
        cycle_cooldown_seconds: float = 0.14,
        enter_cooldown_seconds: float = 1.0,
    ) -> None:
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        self._hold_seconds = max(0.2, hold_seconds)
        self._timeout_seconds = max(1.0, timeout_seconds)
        self._move_threshold = max(0.01, move_threshold)
        self._cycle_cooldown_seconds = max(0.03, cycle_cooldown_seconds)
        self._enter_cooldown_seconds = max(0.0, enter_cooldown_seconds)

        self._in_mode = False
        self._alt_held = False
        self._open_palm_start_time = None
        self._mode_start_time = 0.0
        self._last_activity_time = 0.0
        self._last_cycle_time = -1e9
        self._last_enter_time = -1e9
        self._previous_x = None
        self._pinch_latched = False

    @property
    def in_mode(self) -> bool:
        return self._in_mode

    def update_entry(self, open_palm: bool, now_seconds: float) -> bool:
        """Enter app switch mode after sustained open-palm hold."""
        if self._in_mode:
            return False

        if now_seconds - self._last_enter_time < self._enter_cooldown_seconds:
            self._open_palm_start_time = None if not open_palm else self._open_palm_start_time
            return False

        if not open_palm:
            self._open_palm_start_time = None
            return False

        if self._open_palm_start_time is None:
            self._open_palm_start_time = now_seconds
            return False

        if (now_seconds - self._open_palm_start_time) < self._hold_seconds:
            return False

        self._enter_mode(now_seconds)
        return True

    def update_mode(self, hand_x_norm: float, pinch_active: bool, now_seconds: float) -> tuple[bool, bool, bool]:
        """Update mode navigation and selection.

        Returns:
            (navigated, selected, timed_out)
        """
        if not self._in_mode:
            return False, False, False

        timed_out = (now_seconds - self._last_activity_time) > self._timeout_seconds
        if timed_out:
            self.exit_mode()
            return False, False, True

        navigated = self._navigate(hand_x_norm=hand_x_norm, now_seconds=now_seconds)
        selected = self._select_if_pinch(pinch_active=pinch_active)
        return navigated, selected, False

    def exit_mode(self) -> None:
        """Exit app switch mode and release held modifier keys."""
        if self._alt_held:
            try:
                pyautogui.keyUp("alt")
            except Exception:
                pass
        self._alt_held = False
        self._in_mode = False
        self._open_palm_start_time = None
        self._previous_x = None
        self._pinch_latched = False

    def _enter_mode(self, now_seconds: float) -> None:
        self._open_palm_start_time = None
        self._mode_start_time = now_seconds
        self._last_activity_time = now_seconds
        self._last_cycle_time = -1e9
        self._last_enter_time = now_seconds
        self._previous_x = None
        self._pinch_latched = False
        self._in_mode = True

        try:
            pyautogui.keyDown("alt")
            self._alt_held = True
            pyautogui.press("tab")
        except Exception:
            self.exit_mode()

    def _navigate(self, hand_x_norm: float, now_seconds: float) -> bool:
        if self._previous_x is None:
            self._previous_x = hand_x_norm
            return False

        if (now_seconds - self._last_cycle_time) < self._cycle_cooldown_seconds:
            return False

        delta_x = hand_x_norm - self._previous_x
        if abs(delta_x) < self._move_threshold:
            return False

        forward = delta_x > 0
        steps = max(1, min(3, int(abs(delta_x) / self._move_threshold)))
        for _ in range(steps):
            if forward:
                pyautogui.press("tab")
            else:
                pyautogui.keyDown("shift")
                pyautogui.press("tab")
                pyautogui.keyUp("shift")

        self._previous_x = hand_x_norm
        self._last_cycle_time = now_seconds
        self._last_activity_time = now_seconds
        return True

    def _select_if_pinch(self, pinch_active: bool) -> bool:
        if pinch_active and not self._pinch_latched:
            self._pinch_latched = True
            self.exit_mode()
            return True

        if not pinch_active:
            self._pinch_latched = False
        return False

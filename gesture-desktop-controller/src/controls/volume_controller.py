"""Volume control module.

This module will convert recognized volume gestures into system audio
adjustment actions.
"""

from __future__ import annotations

import math

import pyautogui

try:
    from ctypes import POINTER, cast

    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
except Exception:  # pragma: no cover - runtime fallback path
    AudioUtilities = None
    IAudioEndpointVolume = None
    CLSCTX_ALL = None
    POINTER = None
    cast = None


class VolumeController:
    """Adjust system volume from rotational hand motion."""

    def __init__(
        self,
        rotation_step_rad: float = 0.32,
        step_scalar: float = 0.04,
        cooldown_seconds: float = 0.10,
        clockwise_increases: bool = True,
    ) -> None:
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        self._rotation_step_rad = max(0.08, rotation_step_rad)
        self._step_scalar = min(max(step_scalar, 0.005), 0.25)
        self._cooldown_seconds = max(0.0, cooldown_seconds)
        self._clockwise_increases = clockwise_increases

        self._previous_angle = None
        self._accumulated_rotation = 0.0
        self._last_update_time = -1e9
        self._last_direction = "idle"
        self._endpoint = self._create_endpoint()
        self._last_volume_percent = 50
        self._last_volume_percent = self._get_volume_percent()

    def reset(self) -> None:
        """Reset temporal rotation memory when gesture is inactive."""
        self._previous_angle = None
        self._accumulated_rotation = 0.0
        self._last_direction = "idle"

    def update(self, landmarks, now_seconds: float, active: bool) -> tuple[bool, str, int | None]:
        """Update volume using rotational movement around palm center.

        Returns:
            (changed, direction, volume_percent)
        """
        if not active:
            self.reset()
            return False, "idle", self._last_volume_percent

        angle = self._compute_rotation_angle(landmarks)
        if angle is None:
            return False, "idle", self._last_volume_percent

        if self._previous_angle is None:
            self._previous_angle = angle
            return False, "idle", self._last_volume_percent

        delta = self._normalize_angle(angle - self._previous_angle)
        self._previous_angle = angle
        self._accumulated_rotation += delta

        if (now_seconds - self._last_update_time) < self._cooldown_seconds:
            return False, self._last_direction, self._last_volume_percent

        if abs(self._accumulated_rotation) < self._rotation_step_rad:
            return False, self._last_direction, self._last_volume_percent

        steps = max(1, int(abs(self._accumulated_rotation) / self._rotation_step_rad))
        clockwise = self._accumulated_rotation < 0
        increase = clockwise if self._clockwise_increases else not clockwise

        changed = self._apply_steps(steps=steps, increase=increase)
        self._accumulated_rotation = 0.0
        self._last_update_time = now_seconds
        self._last_direction = "up" if increase else "down"
        return changed, self._last_direction, self._last_volume_percent

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        while angle > math.pi:
            angle -= (2.0 * math.pi)
        while angle < -math.pi:
            angle += (2.0 * math.pi)
        return angle

    def _compute_rotation_angle(self, landmarks) -> float | None:
        # HandLandmarker indices.
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        wrist = landmarks[0]
        index_mcp = landmarks[5]
        pinky_mcp = landmarks[17]

        center_x = (thumb_tip.x + index_tip.x + middle_tip.x) / 3.0
        center_y = (thumb_tip.y + index_tip.y + middle_tip.y) / 3.0
        anchor_x = (wrist.x + index_mcp.x + pinky_mcp.x) / 3.0
        anchor_y = (wrist.y + index_mcp.y + pinky_mcp.y) / 3.0

        dx = center_x - anchor_x
        dy = -(center_y - anchor_y)  # invert Y to use standard Cartesian rotation
        radius = math.hypot(dx, dy)
        if radius < 1e-3:
            return None
        return math.atan2(dy, dx)

    def _create_endpoint(self):
        if AudioUtilities is None:
            return None
        try:
            device = AudioUtilities.GetSpeakers()
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception:
            return None

    def _get_volume_percent(self) -> int | None:
        if self._endpoint is None:
            return self._last_volume_percent
        try:
            level = float(self._endpoint.GetMasterVolumeLevelScalar())
            self._last_volume_percent = int(min(max(level * 100.0, 0.0), 100.0))
        except Exception:
            pass
        return self._last_volume_percent

    def _set_volume_scalar(self, value: float) -> bool:
        if self._endpoint is None:
            return False
        try:
            value = min(max(value, 0.0), 1.0)
            self._endpoint.SetMasterVolumeLevelScalar(value, None)
            self._last_volume_percent = int(value * 100.0)
            return True
        except Exception:
            return False

    def _apply_steps(self, steps: int, increase: bool) -> bool:
        if self._endpoint is not None:
            current_scalar = (self._get_volume_percent() or 0) / 100.0
            delta = steps * self._step_scalar
            target = current_scalar + delta if increase else current_scalar - delta
            changed = self._set_volume_scalar(target)
            return changed

        # Fallback for systems where pycaw endpoint is unavailable.
        key = "volumeup" if increase else "volumedown"
        for _ in range(steps):
            pyautogui.press(key)
        if self._last_volume_percent is not None:
            approx = self._last_volume_percent + (steps * int(self._step_scalar * 100.0) * (1 if increase else -1))
            self._last_volume_percent = int(min(max(approx, 0), 100))
        return True

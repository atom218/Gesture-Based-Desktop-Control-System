"""Gesture recognition module.

This module will translate finger states and landmark motion into
high-level gesture labels with priority-aware detection.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")
LANDMARK_INDEX = {
    "wrist": 0,
    "thumb_cmc": 1,
    "thumb_tip": 4,
    "thumb_ip": 3,
    "thumb_mcp": 2,
    "index_mcp": 5,
    "index_tip": 8,
    "index_pip": 6,
    "pinky_mcp": 17,
    "middle_tip": 12,
    "middle_pip": 10,
    "ring_tip": 16,
    "ring_pip": 14,
    "pinky_tip": 20,
    "pinky_pip": 18,
}


@dataclass
class GestureResult:
    """Output produced for one detected hand."""

    finger_states: dict[str, bool]
    fingers_up_count: int
    fingers_up_names: list[str]
    gesture_label: str
    pinch_distance_ratio: float
    pinch_active: bool


class GestureDetector:
    """Infer finger-up states and a basic gesture label."""

    def __init__(self, pinch_threshold_ratio: float = 0.32) -> None:
        self._pinch_threshold_ratio = max(0.05, pinch_threshold_ratio)

    def detect(self, landmarks, handedness: str) -> GestureResult:
        """Return per-finger states and a simple gesture classification."""
        finger_states = self._get_finger_states(landmarks, handedness)
        fingers_up_names = [name for name in FINGER_NAMES if finger_states[name]]
        gesture_label = self._classify_gesture(finger_states)
        pinch_distance_ratio = self._get_pinch_distance_ratio(landmarks)
        pinch_active = pinch_distance_ratio < self._pinch_threshold_ratio
        return GestureResult(
            finger_states=finger_states,
            fingers_up_count=len(fingers_up_names),
            fingers_up_names=fingers_up_names,
            gesture_label=gesture_label,
            pinch_distance_ratio=pinch_distance_ratio,
            pinch_active=pinch_active,
        )

    def _get_finger_states(self, landmarks, handedness: str) -> dict[str, bool]:
        thumb_up = self._is_thumb_extended(landmarks)

        states = {
            "thumb": thumb_up,
            "index": self._is_finger_up(
                landmarks,
                LANDMARK_INDEX["index_tip"],
                LANDMARK_INDEX["index_pip"],
            ),
            "middle": self._is_finger_up(
                landmarks,
                LANDMARK_INDEX["middle_tip"],
                LANDMARK_INDEX["middle_pip"],
            ),
            "ring": self._is_finger_up(
                landmarks,
                LANDMARK_INDEX["ring_tip"],
                LANDMARK_INDEX["ring_pip"],
            ),
            "pinky": self._is_finger_up(
                landmarks,
                LANDMARK_INDEX["pinky_tip"],
                LANDMARK_INDEX["pinky_pip"],
            ),
        }
        return states

    @staticmethod
    def _is_finger_up(landmarks, tip_id, pip_id) -> bool:
        return landmarks[tip_id].y < landmarks[pip_id].y

    @staticmethod
    def _is_thumb_extended(landmarks) -> bool:
        """Estimate thumb extension using conservative palm-relative cues."""
        wrist = landmarks[LANDMARK_INDEX["wrist"]]
        thumb_tip = landmarks[LANDMARK_INDEX["thumb_tip"]]
        thumb_ip = landmarks[LANDMARK_INDEX["thumb_ip"]]
        thumb_mcp = landmarks[LANDMARK_INDEX["thumb_mcp"]]
        index_mcp = landmarks[LANDMARK_INDEX["index_mcp"]]
        pinky_mcp = landmarks[LANDMARK_INDEX["pinky_mcp"]]

        palm_width = math.hypot(index_mcp.x - pinky_mcp.x, index_mcp.y - pinky_mcp.y)
        if palm_width < 1e-6:
            return False

        # 1) Straightness at IP joint (folded thumb is usually bent).
        v1x = thumb_mcp.x - thumb_ip.x
        v1y = thumb_mcp.y - thumb_ip.y
        v2x = thumb_tip.x - thumb_ip.x
        v2y = thumb_tip.y - thumb_ip.y

        mag1 = math.hypot(v1x, v1y)
        mag2 = math.hypot(v2x, v2y)
        if mag1 < 1e-6 or mag2 < 1e-6:
            return False

        cos_angle = (v1x * v2x + v1y * v2y) / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        angle_deg = math.degrees(math.acos(cos_angle))

        # 2) Thumb direction must point away from palm center.
        palm_center_x = (wrist.x + index_mcp.x + pinky_mcp.x) / 3.0
        palm_center_y = (wrist.y + index_mcp.y + pinky_mcp.y) / 3.0
        thumb_vec_x = thumb_tip.x - thumb_mcp.x
        thumb_vec_y = thumb_tip.y - thumb_mcp.y
        to_palm_vec_x = palm_center_x - thumb_mcp.x
        to_palm_vec_y = palm_center_y - thumb_mcp.y
        thumb_vec_mag = math.hypot(thumb_vec_x, thumb_vec_y)
        to_palm_vec_mag = math.hypot(to_palm_vec_x, to_palm_vec_y)
        if thumb_vec_mag < 1e-6 or to_palm_vec_mag < 1e-6:
            return False
        dir_cos = (thumb_vec_x * to_palm_vec_x + thumb_vec_y * to_palm_vec_y) / (
            thumb_vec_mag * to_palm_vec_mag
        )
        points_away_from_palm = dir_cos < -0.10

        # 3) Spread from index base (reduces false positives in index-only pose).
        tip_to_index_base = math.hypot(thumb_tip.x - index_mcp.x, thumb_tip.y - index_mcp.y)

        is_straight = angle_deg > 150.0
        has_lateral_spread = tip_to_index_base > 0.55 * palm_width
        return points_away_from_palm and is_straight and has_lateral_spread

    @staticmethod
    def _get_pinch_distance_ratio(landmarks) -> float:
        thumb_tip = landmarks[LANDMARK_INDEX["thumb_tip"]]
        index_tip = landmarks[LANDMARK_INDEX["index_tip"]]
        index_mcp = landmarks[LANDMARK_INDEX["index_mcp"]]
        pinky_mcp = landmarks[LANDMARK_INDEX["pinky_mcp"]]

        palm_width = math.hypot(index_mcp.x - pinky_mcp.x, index_mcp.y - pinky_mcp.y)
        if palm_width < 1e-6:
            return 1.0

        pinch_distance = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
        return pinch_distance / palm_width

    @staticmethod
    def _classify_gesture(finger_states: dict[str, bool]) -> str:
        active = {name for name, is_up in finger_states.items() if is_up}

        if not active:
            return "Closed Fist (System Toggle Candidate)"
        if active == {"thumb", "index", "middle", "ring", "pinky"}:
            return "Open Palm (App Switch Candidate)"
        if active == {"index"}:
            return "Index Point (Cursor Candidate)"
        if active == {"thumb", "index"}:
            return "Thumb + Index (Click Candidate)"
        if active == {"index", "middle"}:
            return "Index + Middle (Brightness Candidate)"
        if active == {"thumb", "index", "middle"}:
            return "Thumb + Index + Middle (Volume Candidate)"

        # Fallback for all other combinations while building intuition.
        return "Custom Finger Combination"

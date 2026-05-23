"""Hand tracking module.

This module will encapsulate webcam frame processing and MediaPipe hand
landmark extraction for downstream gesture and control pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Optional
from urllib.request import urlretrieve

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from system import config


@dataclass
class TrackedHand:
    """Container for single-hand tracking output."""

    landmarks: list
    handedness: str


class HandTracker:
    """Wrapper around MediaPipe Tasks HandLandmarker for one-hand tracking."""

    def __init__(self) -> None:
        self._connections = vision.HandLandmarksConnections.HAND_CONNECTIONS
        model_path = self._ensure_model()
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=config.MAX_NUM_HANDS,
            min_hand_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
        )
        self._hands = vision.HandLandmarker.create_from_options(options)

    @staticmethod
    def _ensure_model() -> Path:
        model_path = Path(config.HAND_LANDMARKER_MODEL_PATH)
        if model_path.exists():
            return model_path

        model_path.parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(config.HAND_LANDMARKER_MODEL_URL, model_path)
        return model_path

    def process(self, frame_bgr: np.ndarray, timestamp_ms: int):
        """Run hand landmark inference on a BGR frame."""
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        return self._hands.detect_for_video(image, timestamp_ms)

    def get_primary_hand(self, results: Any) -> Optional[TrackedHand]:
        """Return first detected hand with handedness metadata."""
        if not results or not results.hand_landmarks:
            return None

        hand_landmarks = results.hand_landmarks[0]
        handedness = "Unknown"
        if results.handedness and results.handedness[0]:
            handedness = results.handedness[0][0].category_name

        return TrackedHand(landmarks=hand_landmarks, handedness=handedness)

    def draw_landmarks(self, frame_bgr: np.ndarray, results: Any) -> None:
        """Draw detected hand landmarks for visual debugging."""
        if not results or not results.hand_landmarks:
            return

        height, width = frame_bgr.shape[:2]
        for hand_landmarks in results.hand_landmarks:
            points = []
            for landmark in hand_landmarks:
                x = int(landmark.x * width)
                y = int(landmark.y * height)
                points.append((x, y))
                cv2.circle(frame_bgr, (x, y), 3, (80, 220, 80), -1)

            for connection in self._connections:
                start = points[connection.start]
                end = points[connection.end]
                cv2.line(frame_bgr, start, end, (255, 120, 0), 2)

    def close(self) -> None:
        """Release MediaPipe resources."""
        self._hands.close()

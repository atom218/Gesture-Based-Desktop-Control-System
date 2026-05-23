"""Project configuration module.

This module will store tunable constants, thresholds, and runtime options
shared across tracking, gesture, and control components.
"""

CAMERA_INDEX = 0
WINDOW_NAME = "Gesture Desktop Controller - Finger Recognition Demo"

# MediaPipe Hands parameters
MAX_NUM_HANDS = 1
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.6

# Optional camera capture setup (ignored when unsupported by the webcam)
FRAME_WIDTH = 960
FRAME_HEIGHT = 540

# MediaPipe Tasks model settings
HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
HAND_LANDMARKER_MODEL_PATH = "assets/models/hand_landmarker.task"

# State and gesture timing
TOGGLE_FIST_HOLD_FRAMES = 12
TOGGLE_COOLDOWN_SECONDS = 1.0

# Cursor control tuning
CURSOR_SMOOTHING_ALPHA = 0.35
CURSOR_ACTIVE_MARGIN_X = 0.08
CURSOR_ACTIVE_MARGIN_Y = 0.12

# Click gesture tuning (thumb-index pinch)
CLICK_PINCH_THRESHOLD_RATIO = 0.45
CLICK_COOLDOWN_SECONDS = 0.35
CLICK_ARM_THRESHOLD_RATIO = 0.52
CLICK_RELEASE_THRESHOLD_RATIO = 0.54

# Brightness gesture tuning (index + middle vertical slide)
BRIGHTNESS_STEP_PERCENT = 4
BRIGHTNESS_MOTION_THRESHOLD = 0.025
BRIGHTNESS_COOLDOWN_SECONDS = 0.08

# App switcher tuning (open palm hold -> alt+tab mode)
APP_SWITCH_HOLD_SECONDS = 1.0
APP_SWITCH_TIMEOUT_SECONDS = 6.0
APP_SWITCH_MOVE_THRESHOLD = 0.06
APP_SWITCH_CYCLE_COOLDOWN_SECONDS = 0.14
APP_SWITCH_ENTER_COOLDOWN_SECONDS = 1.0

# Volume gesture tuning (thumb + index + middle rotation)
VOLUME_ROTATION_STEP_RAD = 0.32
VOLUME_STEP_SCALAR = 0.04
VOLUME_COOLDOWN_SECONDS = 0.10
VOLUME_CLOCKWISE_INCREASES = True
VOLUME_THUMB_RELAXED_SPREAD_RATIO = 0.46

"""Main application entry point.

This file will coordinate pipeline initialization and real-time loop
execution for gesture-based desktop interaction.
"""

from __future__ import annotations

import time

import cv2

from controls.app_switcher import AppSwitcher
from controls.brightness_controller import BrightnessController
from controls.mouse_controller import MouseController
from controls.volume_controller import VolumeController
from gestures.gesture_detector import GestureDetector
from system import config
from system.state_manager import StateManager
from tracking.hand_tracker import HandTracker
from ui.overlay import draw_overlay

INDEX_TIP_ID = 8
MIDDLE_TIP_ID = 12


def _open_camera() -> cv2.VideoCapture:
    """Open the preferred camera, prioritizing external webcams."""
    camera_indices = (
        (config.CAMERA_INDEX,)
        if config.CAMERA_INDEX is not None
        else config.CAMERA_PRIORITY
    )

    for camera_index in camera_indices:
        capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        ok, _ = capture.read()
        if capture.isOpened() and ok:
            print(f"Using camera index {camera_index}")
            return capture

        capture.release()

    raise RuntimeError(
        "Unable to open webcam. Check camera permissions/device index."
    )


def run() -> None:
    """Run the basic finger-recognition demo loop."""
    capture = _open_camera()
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    tracker = HandTracker()
    detector = GestureDetector(pinch_threshold_ratio=config.CLICK_PINCH_THRESHOLD_RATIO)
    state_manager = StateManager(
        hold_frames=config.TOGGLE_FIST_HOLD_FRAMES,
        cooldown_seconds=config.TOGGLE_COOLDOWN_SECONDS,
    )
    mouse_controller = MouseController(
        smoothing_alpha=config.CURSOR_SMOOTHING_ALPHA,
        active_margin_x=config.CURSOR_ACTIVE_MARGIN_X,
        active_margin_y=config.CURSOR_ACTIVE_MARGIN_Y,
        click_cooldown_seconds=config.CLICK_COOLDOWN_SECONDS,
    )
    brightness_controller = BrightnessController(
        step_percent=config.BRIGHTNESS_STEP_PERCENT,
        motion_threshold=config.BRIGHTNESS_MOTION_THRESHOLD,
        cooldown_seconds=config.BRIGHTNESS_COOLDOWN_SECONDS,
    )
    app_switcher = AppSwitcher(
        hold_seconds=config.APP_SWITCH_HOLD_SECONDS,
        timeout_seconds=config.APP_SWITCH_TIMEOUT_SECONDS,
        move_threshold=config.APP_SWITCH_MOVE_THRESHOLD,
        cycle_cooldown_seconds=config.APP_SWITCH_CYCLE_COOLDOWN_SECONDS,
        enter_cooldown_seconds=config.APP_SWITCH_ENTER_COOLDOWN_SECONDS,
    )
    volume_controller = VolumeController(
        rotation_step_rad=config.VOLUME_ROTATION_STEP_RAD,
        step_scalar=config.VOLUME_STEP_SCALAR,
        cooldown_seconds=config.VOLUME_COOLDOWN_SECONDS,
        clockwise_increases=config.VOLUME_CLOCKWISE_INCREASES,
    )
    previous_time = time.perf_counter()
    click_aim_lock = False
    invisible_frame_count = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            now = time.perf_counter()
            fps = 1.0 / max(now - previous_time, 1e-6)
            previous_time = now

            timestamp_ms = int(now * 1000)
            results = tracker.process(frame, timestamp_ms)
            tracker.draw_landmarks(frame, results)
            tracked_hand = tracker.get_primary_hand(results)
            cursor_tracking_active = False
            pinch_active = False
            click_triggered = False
            brightness_mode_active = False
            brightness_changed = False
            brightness_level = None
            volume_mode_active = False
            volume_changed = False
            volume_direction = "idle"
            volume_level = None
            app_switch_message = "idle"

            if tracked_hand is None:
                click_aim_lock = False
                mouse_controller.reset()
                brightness_controller.reset()
                volume_controller.reset()
                if app_switcher.in_mode:
                    _, _, timed_out = app_switcher.update_mode(
                        hand_x_norm=0.5,
                        pinch_active=False,
                        now_seconds=now,
                    )
                    if timed_out:
                        app_switch_message = "timeout exit"
                else:
                    app_switch_message = "waiting open palm"
                mouse_controller.maybe_left_click(
                    pinch_distance_ratio=1.0,
                    click_ready=False,
                    pinch_press_threshold=config.CLICK_PINCH_THRESHOLD_RATIO,
                    pinch_release_threshold=config.CLICK_RELEASE_THRESHOLD_RATIO,
                    now_seconds=now,
                )
                draw_overlay(
                    frame_bgr=frame,
                    fps=fps,
                    handedness="N/A",
                    gesture_result=None,
                    system_active=state_manager.is_active,
                    cursor_tracking_active=False,
                    pinch_active=False,
                    click_triggered=False,
                    click_aim_lock=False,
                    brightness_mode_active=False,
                    brightness_changed=False,
                    brightness_level=None,
                    volume_mode_active=False,
                    volume_changed=False,
                    volume_direction="idle",
                    volume_level=None,
                    app_switch_mode_active=app_switcher.in_mode,
                    app_switch_message=app_switch_message,
                )
            else:
                gesture_result = detector.detect(
                    landmarks=tracked_hand.landmarks,
                    handedness=tracked_hand.handedness,
                )
                pinch_ratio = gesture_result.pinch_distance_ratio
                index_extended = gesture_result.finger_states.get("index", False)
                pinch_raw_active = pinch_ratio < config.CLICK_PINCH_THRESHOLD_RATIO
                # Display/use pinch only when index is part of the gesture intent.
                pinch_active = pinch_raw_active and index_extended
                toggled = state_manager.update_toggle(
                    closed_fist_detected=(gesture_result.fingers_up_count == 0),
                    now_seconds=now,
                )
                if toggled and not state_manager.is_active:
                    app_switcher.exit_mode()
                    app_switch_message = "system off"

                open_palm_active = (
                    state_manager.is_active
                    and gesture_result.finger_states.get("index", False)
                    and gesture_result.finger_states.get("middle", False)
                    and gesture_result.finger_states.get("thumb", False)
                    and gesture_result.finger_states.get("ring", False)
                    and gesture_result.finger_states.get("pinky", False)
                )
                if app_switcher.update_entry(open_palm=open_palm_active, now_seconds=now):
                    app_switch_message = "entered mode"

                if app_switcher.in_mode:
                    hand_x = tracked_hand.landmarks[INDEX_TIP_ID].x
                    navigated, selected, timed_out = app_switcher.update_mode(
                        hand_x_norm=hand_x,
                        pinch_active=pinch_raw_active,
                        now_seconds=now,
                    )
                    if selected:
                        app_switch_message = "selected app"
                    elif timed_out:
                        app_switch_message = "timeout exit"
                    elif navigated:
                        app_switch_message = "cycling apps"
                    else:
                        app_switch_message = "move hand to cycle"

                    click_aim_lock = False
                    mouse_controller.reset()
                    brightness_controller.reset()
                    volume_controller.reset()
                    mouse_controller.maybe_left_click(
                        pinch_distance_ratio=1.0,
                        click_ready=False,
                        pinch_press_threshold=config.CLICK_PINCH_THRESHOLD_RATIO,
                        pinch_release_threshold=config.CLICK_RELEASE_THRESHOLD_RATIO,
                        now_seconds=now,
                    )
                    draw_overlay(
                        frame_bgr=frame,
                        fps=fps,
                        handedness=tracked_hand.handedness,
                        gesture_result=gesture_result,
                        system_active=state_manager.is_active,
                        cursor_tracking_active=False,
                        pinch_active=pinch_active,
                        click_triggered=False,
                        click_aim_lock=False,
                        brightness_mode_active=False,
                        brightness_changed=False,
                        brightness_level=None,
                        volume_mode_active=False,
                        volume_changed=False,
                        volume_direction="idle",
                        volume_level=None,
                        app_switch_mode_active=True,
                        app_switch_message=app_switch_message,
                    )
                    cv2.imshow(config.WINDOW_NAME, frame)
                    try:
                        visible_flag = cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE)
                        if visible_flag < 1 and not app_switcher.in_mode:
                            invisible_frame_count += 1
                        else:
                            invisible_frame_count = 0
                        if invisible_frame_count >= 15:
                            break
                    except cv2.error:
                        invisible_frame_count += 1
                        if invisible_frame_count >= 15:
                            break
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                click_ready_hand_shape = (
                    state_manager.is_active
                    and index_extended
                    and not gesture_result.finger_states.get("middle", False)
                    and not gesture_result.finger_states.get("ring", False)
                    and not gesture_result.finger_states.get("pinky", False)
                )
                if click_ready_hand_shape and (
                    pinch_ratio < config.CLICK_ARM_THRESHOLD_RATIO
                ):
                    click_aim_lock = True
                elif (
                    not click_ready_hand_shape
                    or pinch_ratio > config.CLICK_RELEASE_THRESHOLD_RATIO
                ):
                    click_aim_lock = False

                brightness_mode_active = (
                    state_manager.is_active
                    and gesture_result.finger_states.get("index", False)
                    and gesture_result.finger_states.get("middle", False)
                    and not gesture_result.finger_states.get("thumb", False)
                    and not gesture_result.finger_states.get("ring", False)
                    and not gesture_result.finger_states.get("pinky", False)
                )

                palm_width = (
                    ((tracked_hand.landmarks[5].x - tracked_hand.landmarks[17].x) ** 2)
                    + ((tracked_hand.landmarks[5].y - tracked_hand.landmarks[17].y) ** 2)
                ) ** 0.5
                thumb_extension = (
                    ((tracked_hand.landmarks[4].x - tracked_hand.landmarks[2].x) ** 2)
                    + ((tracked_hand.landmarks[4].y - tracked_hand.landmarks[2].y) ** 2)
                ) ** 0.5
                thumb_extension_ready = (
                    palm_width > 1e-6
                    and thumb_extension > (config.VOLUME_THUMB_EXTENSION_RATIO * palm_width)
                )
                volume_thumb_ready = (
                    gesture_result.finger_states.get("thumb", False)
                    or (
                        pinch_ratio
                        > config.VOLUME_THUMB_RELAXED_SPREAD_RATIO
                        and thumb_extension_ready
                    )
                )
                volume_mode_active = (
                    state_manager.is_active
                    and volume_thumb_ready
                    and gesture_result.finger_states.get("index", False)
                    and gesture_result.finger_states.get("middle", False)
                    and not gesture_result.finger_states.get("ring", False)
                    and not gesture_result.finger_states.get("pinky", False)
                    and not brightness_mode_active
                )
                if volume_mode_active:
                    volume_changed, volume_direction, volume_level = volume_controller.update(
                        landmarks=tracked_hand.landmarks,
                        now_seconds=now,
                        active=True,
                    )
                    mouse_controller.reset()
                    brightness_controller.reset()
                    mouse_controller.maybe_left_click(
                        pinch_distance_ratio=1.0,
                        click_ready=False,
                        pinch_press_threshold=config.CLICK_PINCH_THRESHOLD_RATIO,
                        pinch_release_threshold=config.CLICK_RELEASE_THRESHOLD_RATIO,
                        now_seconds=now,
                    )
                    click_aim_lock = False
                    app_switch_message = "volume mode active"
                else:
                    volume_changed, volume_direction, volume_level = volume_controller.update(
                        landmarks=tracked_hand.landmarks,
                        now_seconds=now,
                        active=False,
                    )

                if brightness_mode_active and not volume_mode_active:
                    middle_tip = tracked_hand.landmarks[MIDDLE_TIP_ID]
                    brightness_changed, brightness_level = brightness_controller.update(
                        y_norm=middle_tip.y,
                        now_seconds=now,
                        active=True,
                    )
                    mouse_controller.reset()
                    click_aim_lock = False
                    app_switch_message = "brightness mode active"
                else:
                    brightness_changed, brightness_level = brightness_controller.update(
                        y_norm=0.0,
                        now_seconds=now,
                        active=False,
                    )
                    if state_manager.is_active and not volume_mode_active:
                        app_switch_message = "show open palm to enter"
                    else:
                        if not state_manager.is_active:
                            app_switch_message = "system off"

                index_only_active = (
                    state_manager.is_active
                    and index_extended
                    and not gesture_result.finger_states.get("thumb", False)
                    and not gesture_result.finger_states.get("middle", False)
                    and not gesture_result.finger_states.get("ring", False)
                    and not gesture_result.finger_states.get("pinky", False)
                )
                # Pre-lock cursor before full pinch to reduce pre-click drift.
                if index_only_active and pinch_ratio < config.CLICK_PRELOCK_RATIO:
                    click_aim_lock = True
                thumb_far_from_index = (
                    pinch_ratio > (config.CLICK_ARM_THRESHOLD_RATIO + 0.03)
                )
                if (
                    index_only_active
                    and thumb_far_from_index
                    and not click_aim_lock
                    and not brightness_mode_active
                    and not volume_mode_active
                ):
                    index_tip = tracked_hand.landmarks[INDEX_TIP_ID]
                    mouse_controller.move_from_normalized(
                        x_norm=index_tip.x,
                        y_norm=index_tip.y,
                    )
                    cursor_tracking_active = True
                elif not click_aim_lock:
                    mouse_controller.reset()

                click_triggered = mouse_controller.maybe_left_click(
                    pinch_distance_ratio=pinch_ratio,
                    click_ready=(click_ready_hand_shape and not brightness_mode_active and not volume_mode_active),
                    pinch_press_threshold=config.CLICK_PINCH_THRESHOLD_RATIO,
                    pinch_release_threshold=config.CLICK_RELEASE_THRESHOLD_RATIO,
                    now_seconds=now,
                )

                draw_overlay(
                    frame_bgr=frame,
                    fps=fps,
                    handedness=tracked_hand.handedness,
                    gesture_result=gesture_result,
                    system_active=state_manager.is_active,
                    cursor_tracking_active=cursor_tracking_active,
                    pinch_active=pinch_active,
                    click_triggered=click_triggered,
                    click_aim_lock=click_aim_lock,
                    brightness_mode_active=brightness_mode_active,
                    brightness_changed=brightness_changed,
                    brightness_level=brightness_level,
                    volume_mode_active=volume_mode_active,
                    volume_changed=volume_changed,
                    volume_direction=volume_direction,
                    volume_level=volume_level,
                    app_switch_mode_active=False,
                    app_switch_message=app_switch_message,
                )

            cv2.imshow(config.WINDOW_NAME, frame)
            try:
                visible_flag = cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE)
                if visible_flag < 1 and not app_switcher.in_mode:
                    invisible_frame_count += 1
                else:
                    invisible_frame_count = 0
                if invisible_frame_count >= 15:
                    break
            except cv2.error:
                invisible_frame_count += 1
                if invisible_frame_count >= 15:
                    break
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        app_switcher.exit_mode()
        tracker.close()
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run()

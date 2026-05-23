"""UI overlay module.

This module will render debug and status overlays such as FPS, active
gesture label, system state, and landmark visualization.
"""

from __future__ import annotations

import cv2


def draw_overlay(
    frame_bgr,
    fps: float,
    handedness: str,
    gesture_result,
    system_active: bool,
    cursor_tracking_active: bool,
    pinch_active: bool,
    click_triggered: bool,
    click_aim_lock: bool,
    brightness_mode_active: bool,
    brightness_changed: bool,
    brightness_level: int | None,
    volume_mode_active: bool,
    volume_changed: bool,
    volume_direction: str,
    volume_level: int | None,
    app_switch_mode_active: bool,
    app_switch_message: str,
) -> None:
    """Render on-screen diagnostics for the current frame."""
    status_text = "SYSTEM: ACTIVE" if system_active else "SYSTEM: OFF"
    status_color = (80, 255, 80) if system_active else (60, 60, 255)
    cv2.putText(
        frame_bgr,
        status_text,
        (20, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        status_color,
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame_bgr,
        f"FPS: {fps:.1f}",
        (20, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )

    if gesture_result is None:
        cv2.putText(
            frame_bgr,
            "No hand detected",
            (20, 92),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
        return

    cv2.putText(
        frame_bgr,
        f"Hand: {handedness}",
        (20, 92),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame_bgr,
        f"Gesture: {gesture_result.gesture_label}",
        (20, 127),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (80, 255, 80),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame_bgr,
        f"Fingers Up: {gesture_result.fingers_up_count}",
        (20, 162),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 220, 80),
        2,
        cv2.LINE_AA,
    )

    names = ", ".join(gesture_result.fingers_up_names) if gesture_result.fingers_up_names else "none"
    cv2.putText(
        frame_bgr,
        f"Active: {names}",
        (20, 197),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    cursor_text = "Cursor Tracking: ON" if cursor_tracking_active else "Cursor Tracking: OFF"
    cursor_color = (80, 255, 80) if cursor_tracking_active else (180, 180, 180)
    cv2.putText(
        frame_bgr,
        cursor_text,
        (20, 232),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        cursor_color,
        2,
        cv2.LINE_AA,
    )

    pinch_text = (
        f"Pinch: {'ON' if pinch_active else 'OFF'} "
        f"(ratio {gesture_result.pinch_distance_ratio:.2f})"
    )
    pinch_color = (80, 255, 80) if pinch_active else (180, 180, 180)
    cv2.putText(
        frame_bgr,
        pinch_text,
        (20, 267),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        pinch_color,
        2,
        cv2.LINE_AA,
    )

    click_text = "Left Click: TRIGGERED" if click_triggered else "Left Click: waiting"
    click_color = (60, 220, 255) if click_triggered else (180, 180, 180)
    cv2.putText(
        frame_bgr,
        click_text,
        (20, 302),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        click_color,
        2,
        cv2.LINE_AA,
    )

    lock_text = "Click Aim Lock: ON" if click_aim_lock else "Click Aim Lock: OFF"
    lock_color = (60, 220, 255) if click_aim_lock else (180, 180, 180)
    cv2.putText(
        frame_bgr,
        lock_text,
        (20, 337),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        lock_color,
        2,
        cv2.LINE_AA,
    )

    brightness_text = "Brightness Mode: ON" if brightness_mode_active else "Brightness Mode: OFF"
    brightness_color = (120, 255, 120) if brightness_mode_active else (180, 180, 180)
    cv2.putText(
        frame_bgr,
        brightness_text,
        (20, 372),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        brightness_color,
        2,
        cv2.LINE_AA,
    )

    if brightness_level is None:
        level_text = "Brightness: unknown"
    else:
        level_text = f"Brightness: {brightness_level}%"
    if brightness_changed:
        level_text += " (updated)"
    level_color = (120, 255, 120) if brightness_changed else (180, 180, 180)
    cv2.putText(
        frame_bgr,
        level_text,
        (20, 407),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        level_color,
        2,
        cv2.LINE_AA,
    )

    app_mode_text = "App Switch Mode: ON" if app_switch_mode_active else "App Switch Mode: OFF"
    app_mode_color = (120, 255, 120) if app_switch_mode_active else (180, 180, 180)
    cv2.putText(
        frame_bgr,
        app_mode_text,
        (20, 442),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        app_mode_color,
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame_bgr,
        f"App Switch: {app_switch_message}",
        (20, 512),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        app_mode_color,
        2,
        cv2.LINE_AA,
    )

    volume_mode_text = "Volume Mode: ON" if volume_mode_active else "Volume Mode: OFF"
    volume_mode_color = (120, 255, 120) if volume_mode_active else (180, 180, 180)
    cv2.putText(
        frame_bgr,
        volume_mode_text,
        (20, 477),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        volume_mode_color,
        2,
        cv2.LINE_AA,
    )

    if volume_level is None:
        volume_text = f"Volume: unknown ({volume_direction})"
    else:
        volume_text = f"Volume: {volume_level}% ({volume_direction})"
    if volume_changed:
        volume_text += " updated"
    cv2.putText(
        frame_bgr,
        volume_text,
        (20, 547),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        volume_mode_color,
        2,
        cv2.LINE_AA,
    )

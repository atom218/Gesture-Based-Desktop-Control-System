# Gesture-Based Desktop Control System Using Real-Time Hand Tracking

## Final Technical Project Report

**Author context:** Master's-level computer vision and human–computer interaction project  
**Repository:** gesture-desktop-controller  
**Document type:** Comprehensive system design, implementation, and analysis report  
**Version:** As implemented at project completion  

---

\newpage

## Table of Contents

1. Executive Summary  
2. Introduction and Problem Statement  
3. Project Objectives and Success Criteria  
4. Theoretical Foundations  
5. System Architecture Overview  
6. Technology Stack and Runtime Environment  
7. Project Structure and Module Responsibilities  
8. Perception Layer: Camera Capture and Hand Tracking  
9. Finger State Extraction and Geometric Reasoning  
10. High-Level Gesture Classification  
11. System Activation and State Management  
12. Cursor Control: Mapping, Smoothing, and Latency  
13. Left-Click Interaction via Pinch Detection  
14. Brightness Control via Vertical Gesture Motion  
15. Application Switching via Open Palm and Alt+Tab Semantics  
16. Volume Control via Rotational Gesture Analysis  
17. Main Loop Orchestration and Gesture Priority Arbitration  
18. User Interface and Debug Overlay  
19. Configuration Management and Tunable Parameters  
20. Development History and Design Iterations  
21. Performance, Reliability, and Known Limitations  
22. Testing Methodology and Validation Scenarios  
23. Research Contributions and Academic Positioning  
24. Future Work and Recommended Refactoring  
25. Conclusion  
26. Appendix: Landmark Index Reference and Parameter Tables  

---

\newpage

## 1. Executive Summary

This report documents the complete design, implementation, and evolution of a **Gesture-Based Desktop Control System** that uses a standard laptop webcam and real-time computer vision to translate hand poses and motions into desktop control actions. The system is intentionally architected as a modular, research-oriented human–computer interaction (HCI) application rather than a monolithic proof-of-concept script. It supports six primary interaction capabilities: system activation and deactivation via a closed-fist hold gesture; cursor movement via an extended index finger; left mouse click via a thumb–index pinch; display brightness adjustment via vertical two-finger motion; application switching via an open-palm hold followed by horizontal navigation and pinch selection; and system volume adjustment via rotational motion of a three-finger pose (thumb, index, and middle extended).

The pipeline follows a strict separation of concerns: raw video acquisition, hand landmark inference, per-finger state extraction, gesture labeling, runtime state management, action execution through OS-level control libraries, and visual feedback through an on-screen diagnostic overlay. The project was built incrementally across multiple development phases, with extensive user-driven tuning particularly around thumb detection reliability, cursor stability near screen edges, click registration consistency, and mutual exclusivity between brightness and volume modes that share overlapping finger configurations.

The implementation targets the Windows desktop environment and relies on MediaPipe Hand Landmarker (Tasks API), OpenCV for capture and visualization, PyAutoGUI for mouse and keyboard synthesis, pycaw for audio endpoint volume control, and screen-brightness-control for display luminance adjustment. Performance is suitable for interactive use at approximately twenty to thirty frames per second on typical hardware, with perceptual latency kept low through disabled automation delays, adaptive cursor smoothing, and debounced discrete actions.

This document explains every major concept, formula, control policy, and module interaction in detail so that a reader without access to the source repository can fully understand how the system works from first principles through to final behavior.

---

\newpage

## 2. Introduction and Problem Statement

Traditional desktop interaction depends on physical input devices—principally the mouse and keyboard—which assume a flat surface, fine motor precision, and continuous contact with hardware. For many contexts including presentations, sterile environments, accessibility scenarios, and hands-busy workflows, **contactless control** offers meaningful advantages. Vision-based hand tracking enables users to control a computer by moving and posing their hand in front of a camera, but naive implementations often suffer from jitter, false activations, ambiguous gestures, and poor mapping between camera space and screen space.

The problem addressed by this project is therefore not merely "detect a hand," but **design a stable, intentional, on-demand control system** that:

- Activates only when the user explicitly enables it, avoiding passive surveillance behavior.
- Maps hand motion to screen actions with predictable, low-latency response.
- Distinguishes multiple gestures that share partial finger overlap (for example, index-only versus index-plus-middle).
- Prevents action cross-talk (cursor drift during click approach, brightness stealing volume mode, and similar conflicts).
- Remains maintainable as features are added incrementally.

The project's academic framing emphasizes **real-time interactive vision system design**, with cursor stabilization identified as a primary technical contribution area, alongside temporal gesture recognition for rotation-based volume control and debounced discrete event handling for clicks and mode transitions.

---

\newpage

## 3. Project Objectives and Success Criteria

### 3.1 Primary Objectives

The project aimed to deliver a working desktop control system with the following functional capabilities, each mapped to an explicit hand gesture:

| Capability | Intended Gesture | Intended System Response |
|------------|------------------|---------------------------|
| System toggle | Closed fist held approximately one second | Toggle global ON/OFF; when OFF, ignore control gestures except re-activation |
| Cursor control | Index finger extended alone | Move mouse cursor across full screen |
| Left click | Thumb and index pinch | Single left click with debounce |
| Brightness | Index and middle extended; vertical motion | Increase brightness upward, decrease downward |
| App switcher | Open palm held; then horizontal motion; pinch to confirm | Enter Alt+Tab-like mode; cycle applications; select |
| Volume | Thumb, index, middle extended; rotational motion | Clockwise increases volume; counterclockwise decreases |

### 3.2 Non-Functional Objectives

Beyond feature completeness, the design pursued:

- **Modularity:** Each pipeline stage isolated in its own Python module.
- **Scalability of development:** New gestures added without rewriting the entire application.
- **Demo and debug friendliness:** Live overlay showing system state, active gesture, and sub-feature status.
- **Maintainability:** Centralized configuration constants for threshold tuning.
- **Research credibility:** Decisions documented and justified (smoothing, hysteresis, hold-to-activate, priority rules).

### 3.3 Performance Targets

The original specification targeted approximately twenty to thirty frames per second, cursor jitter minimization, end-to-end perceived latency under one hundred milliseconds where feasible, high gesture classification accuracy under consistent lighting, and minimal false activations when the system is OFF or when non-target finger combinations are shown.

---

\newpage

## 4. Theoretical Foundations

### 4.1 Hand Landmarks as a Low-Dimensional Representation

Modern hand tracking systems do not typically output a full 3D skeletal model estimated from first principles. Instead, they infer a fixed set of **normalized 2D landmarks** in image space, augmented with relative depth proxies. MediaPipe Hand Landmarker provides twenty-one points per hand, indexed from wrist through each finger's metacarpophalangeal (MCP), proximal interphalangeal (PIP), distal interphalangeal (DIP) where applicable, and tip (TIP).

Each landmark is expressed in normalized image coordinates where horizontal position x and vertical position y typically lie in the closed interval from zero to one relative to frame width and height, with the origin conventionally at the upper-left of the image. This representation is **scale-normalized to the frame** but not automatically normalized to physical hand size; therefore, many project decisions use **hand-relative metrics** such as palm width rather than absolute pixel distances.

### 4.2 Geometric Finger State Logic

For four fingers (index, middle, ring, pinky), a classical heuristic compares the vertical position of the fingertip against the PIP joint: if the tip lies above the PIP in image coordinates (smaller y value), the finger is classified as extended. This exploits the observation that, in an upright camera view with the palm facing the camera, extension correlates with the tip being higher in the image than the middle joint.

The thumb does not share the same kinematic axis as the other fingers. Its extension is ambiguous under simple vertical comparisons, especially under horizontal mirroring of the preview feed. The project therefore uses **multi-cue thumb extension estimation** based on joint angle, direction relative to palm center, and lateral separation from the index finger base.

### 4.3 Temporal Processing and Debouncing

Single-frame classification is insufficient for reliable HCI. The system applies:

- **Hold counters** for mode entry (closed fist for system toggle, open palm for app switch).
- **Cooldown timers** preventing repeated toggles or rapid-fire OS commands.
- **Hysteresis** for pinch-based clicking (separate press and release thresholds).
- **Accumulated motion buffers** for rotation-based volume and stepwise brightness changes.

These mechanisms convert noisy continuous signals into **intentional discrete actions**.

### 4.4 Coordinate Mapping from Camera to Screen

Cursor control uses **absolute mapping** from normalized finger position to screen coordinates, optionally preceded by margin compression so that a comfortable central region of the camera frame maps to the full display area. Smoothing is applied as exponential moving average in screen space, with adaptive increase of responsiveness near screen edges and during rapid movements.

### 4.5 Rotational Gesture Analysis

Volume control interprets the change in orientation angle of a three-fingertip cluster relative to a palm anchor. Angular deltas are wrapped to the principal interval minus pi to pi radians to avoid discontinuities at the branch cut. Clockwise or counterclockwise classification depends on the sign of accumulated wrapped delta and a configurable polarity flag.

---

\newpage

## 5. System Architecture Overview

The architecture implements a linear pipeline with a branching action layer orchestrated by a central runtime loop:

**Camera Feed → Hand Landmark Detection → Finger State Extraction → Gesture Recognition → State Management → Action Execution → UI Overlay**

### 5.1 Layer Responsibilities

**Tracking layer** acquires frames, mirrors them for ergonomic interaction, invokes MediaPipe Hand Landmarker in VIDEO running mode with monotonically increasing millisecond timestamps, and renders skeleton connections for debugging.

**Gesture layer** converts landmarks into boolean finger states, pinch distance ratio, symbolic gesture labels, and auxiliary fields consumed by the main loop.

**System layer** maintains global ON/OFF through StateManager and centralizes numeric configuration.

**Controls layer** contains four action executors: MouseController, BrightnessController, VolumeController, and AppSwitcher. Each encapsulates OS interaction logic and internal temporal state.

**UI layer** draws diagnostic text on the preview frame.

**Main orchestration** implements priority rules deciding which control path executes each frame.

### 5.2 Design Pattern: Incremental Feature Slices

The project deliberately avoided implementing all gestures simultaneously. Early milestones validated finger recognition only; subsequent milestones added toggle, cursor, click, brightness, app switching, and volume in sequence. This reduced debugging complexity and allowed regression isolation when later features interfered with earlier thresholds—notably thumb classification shared across click, volume, and brightness gating.

### 5.3 Planned but Unintegrated Components

A dedicated cursor_smoother module exists as a placeholder describing future reusable smoothing strategies, but smoothing is currently implemented inside MouseController. README documentation at project root remains minimal relative to implementation depth.

---

\newpage

## 6. Technology Stack and Runtime Environment

### 6.1 Core Libraries

**OpenCV** provides VideoCapture from a configurable camera index, frame flipping, window display via imshow, and drawing operations for landmarks and overlay text.

**MediaPipe Tasks (Hand Landmarker)** performs inference using a downloaded hand_landmarker.task model file stored under assets/models. The legacy mediapipe.solutions API is not used because recent MediaPipe distributions expose the Tasks API as the supported interface on Windows.

**NumPy** supports array-oriented frame handling where needed.

**PyAutoGUI** synthesizes mouse movement, mouse click, key down/up, and key press events. FAILSAFE is disabled and PAUSE set to zero to minimize inserted delays between commands.

**pycaw with comtypes** accesses the Windows audio endpoint volume interface (IAudioEndpointVolume) for scalar volume adjustment when available.

**screen-brightness-control** queries and sets display brightness percentage on supported hardware.

**keyboard and mouse** packages are listed as dependencies for potential extended control but are not central to the described main loop implementation.

### 6.2 Platform Assumptions

The control semantics (Alt+Tab app switching, pycaw endpoint volume, WMI-related brightness backends) assume **Microsoft Windows**. Linux or macOS would require alternate OS integration paths.

### 6.3 Model Acquisition

On first run, if the hand landmarker model file is absent locally, the tracker downloads it from a Google-hosted MediaPipe model URL defined in configuration. This ensures reproducible setup across machines at the cost of a one-time network dependency.

---

\newpage

## 7. Project Structure and Module Responsibilities

The repository root gesture-desktop-controller contains:

- **src/main.py** — Application entry point and real-time loop.
- **src/tracking/hand_tracker.py** — MediaPipe wrapper and landmark visualization.
- **src/gestures/gesture_detector.py** — Finger states, pinch metric, gesture labels.
- **src/system/config.py** — All tunable constants.
- **src/system/state_manager.py** — Global active/inactive toggle logic.
- **src/controls/mouse_controller.py** — Cursor mapping, smoothing, click hysteresis.
- **src/controls/brightness_controller.py** — Vertical motion to brightness percent.
- **src/controls/volume_controller.py** — Rotational motion to volume scalar.
- **src/controls/app_switcher.py** — Open palm entry, Alt+Tab navigation, pinch select.
- **src/ui/overlay.py** — Diagnostic text rendering.
- **src/smoothing/cursor_smoother.py** — Placeholder only.
- **experiments/, docs/, assets/** — Supporting directories.
- **requirements.txt** — Python dependencies.
- **summary.md** — Development conversation log (separate from this report).

This separation allows academic discussion of each concern in isolation and mirrors professional software engineering practice.

---

\newpage

## 8. Perception Layer: Camera Capture and Hand Tracking

### 8.1 Frame Acquisition

The main loop opens a VideoCapture on camera index zero by default, requesting frame width 960 and height 540 pixels. These dimensions balance field of view and processing cost; webcams may ignore requested properties and deliver native resolutions.

Each successful read returns a BGR color frame. The frame is **horizontally flipped** before processing so that users experience mirror-like interaction: moving the hand right in physical space moves the on-screen representation right, aligning with cursor mapping intuition.

### 8.2 FPS Measurement

Frame rate displayed in the overlay is computed as the reciprocal of delta time between consecutive loop iterations: FPS equals one divided by the maximum of (current time minus previous time) and a tiny epsilon to avoid division by zero. This measures **loop iteration rate** inclusive of inference and OS control overhead, not isolated camera hardware FPS.

### 8.3 Hand Landmarker Configuration

HandLandmarkerOptions specify:

- BaseOptions with local model asset path.
- RunningMode.VIDEO requiring monotonically increasing timestamp in milliseconds per frame.
- num_hands equal to one (single-hand interaction simplifies gesture logic).
- min_hand_detection_confidence 0.7.
- min_tracking_confidence 0.6.

VIDEO mode leverages temporal tracking stability across frames compared to independent per-image detection.

### 8.4 Inference and Primary Hand Selection

Each frame converts BGR to RGB, wraps bytes in a MediaPipe Image with SRGB format, and calls detect_for_video. Results may contain zero or one hand landmarks lists. The tracker selects the first detected hand as primary and reads handedness category label when present (Left, Right, or Unknown).

### 8.5 Landmark Visualization

For debugging, each landmark projects to pixel coordinates by multiplying normalized x by frame width and y by frame height. Small circles mark joints; line segments connect anatomical pairs defined by HandLandmarksConnections.HAND_CONNECTIONS. This visualization is essential for tuning thresholds during development.

### 8.6 Resource Lifecycle

On shutdown, the tracker closes the HandLandmarker instance, releases the camera, and destroys OpenCV windows. The finally block in main also forces app switcher exit to release any held Alt key.

---

\newpage

## 9. Finger State Extraction and Geometric Reasoning

This section details the mathematical and logical criteria used in gesture_detector.py.

### 9.1 Non-Thumb Finger Extension

For a generic finger with tip landmark index tip_id and pip landmark index pip_id, the finger is **up** if:

**tip.y < pip.y**

In normalized image coordinates, smaller y is nearer the top of the frame. This rule is applied to index (tip 8, pip 6), middle (12, 10), ring (16, 14), and pinky (20, 18).

### 9.2 Palm Width Normalization

Many ratios normalize distances by **palm width**, defined as the Euclidean distance between index MCP (landmark 5) and pinky MCP (landmark 17):

**palm_width = sqrt((x5 - x17)² + (y5 - y17)²)**

If palm_width is below a tiny epsilon, ratio calculations abort to safe defaults to avoid division instability.

### 9.3 Thumb Extension: Three Conjunctive Criteria

Thumb state requires all of the following:

**Criterion A — IP joint straightness:** Form vectors from thumb MCP (2) to IP (3) and from IP (3) to TIP (4). Let θ be the angle between these vectors in degrees, computed via dot product cosine law with cosine clamped to [-1, 1]. Require **θ > 150°**.

**Criterion B — Direction away from palm center:** Compute palm center as average of wrist (0), index MCP (5), and pinky MCP (17) positions. Vector from thumb MCP toward thumb tip defines thumb direction; vector from thumb MCP toward palm center defines inward direction. Let dir_cos be normalized dot product. Require **dir_cos < -0.10** (thumb points away from palm center beyond a small tolerance).

**Criterion C — Lateral spread from index base:** Euclidean distance from thumb tip to index MCP must exceed **0.55 × palm_width**.

Only if all three hold is thumb classified as extended. This conservative policy reduced false thumb positives when only index or index-middle were raised, at the cost of occasional false negatives during extreme rotations—addressed later in volume mode via relaxed fallback in main.py.

### 9.4 Pinch Distance Ratio

Pinch strength uses thumb tip (4) and index tip (8):

**pinch_distance = sqrt((x4 - x8)² + (y4 - y8)²)**

**pinch_distance_ratio = pinch_distance / palm_width**

If palm width is negligible, ratio defaults to 1.0 (non-pinched). Lower ratios indicate stronger pinch. The gesture detector also defines pinch_active when ratio falls below CLICK_PINCH_THRESHOLD_RATIO (0.45 by default), though main.py further gates displayed pinch state on index extension for click intent clarity.

---

\newpage

## 10. High-Level Gesture Classification

Given boolean finger states, classification uses **exact set matching** on the active finger set:

| Active finger set | Label assigned |
|-------------------|----------------|
| Empty set | Closed Fist (System Toggle Candidate) |
| {thumb, index, middle, ring, pinky} | Open Palm (App Switch Candidate) |
| {index} | Index Point (Cursor Candidate) |
| {thumb, index} | Thumb + Index (Click Candidate) |
| {index, middle} | Index + Middle (Brightness Candidate) |
| {thumb, index, middle} | Thumb + Index + Middle (Volume Candidate) |
| Any other combination | Custom Finger Combination |

This label is informational for the overlay; actual control activation applies additional gates in main.py (system must be active, mode priority, thumb relaxed rules for volume, etc.).

The GestureResult dataclass bundles finger_states dictionary, fingers_up_count, fingers_up_names list, gesture_label string, pinch_distance_ratio float, and pinch_active boolean for downstream consumption.

---

\newpage

## 11. System Activation and State Management

### 11.1 Semantic States

The original specification described three conceptual states: OFF, ACTIVE, and APP_SWITCH. Implementation-wise:

- **OFF / ACTIVE** is tracked by StateManager.is_active boolean.
- **APP_SWITCH** is tracked separately by AppSwitcher.in_mode boolean.

Full unification into a single state machine enum was deferred; behavior nonetheless enforces that app switch mode exits when system toggles OFF.

### 11.2 Closed Fist Toggle Logic

When fingers_up_count equals zero (no finger classified as extended), the frame counts as closed fist detected. StateManager maintains fist_frame_streak counter incremented each qualifying frame and reset to zero otherwise.

Toggle occurs only if:

1. Current time minus last_toggle_time exceeds TOGGLE_COOLDOWN_SECONDS (1.0 second default).
2. fist_frame_streak is at least TOGGLE_FIST_HOLD_FRAMES (12 frames default).

At approximately thirty FPS, twelve frames is roughly four tenths of a second of consistent closed fist—shorter than the one-second holds used for app switch entry but sufficient to prevent accidental toggles from brief closures.

Upon toggle, is_active flips, last_toggle_time updates, and streak resets to zero. Method returns True on the frame a toggle occurs.

### 11.3 Interaction with App Switcher

If toggle turns system OFF while app switcher active, main explicitly calls app_switcher.exit_mode() to release Alt key and prevent stuck modifier state.

---

\newpage

## 12. Cursor Control: Mapping, Smoothing, and Latency

MouseController implements cursor positioning when main.py enables index-only tracking under appropriate guards.

### 12.1 Normalization and Margin Mapping

Input fingertip provides normalized coordinates (x_norm, y_norm) clamped to [0, 1]. Margins margin_x and margin_y (defaults 0.08 and 0.12) define an inner interaction box:

- min_x = margin_x, max_x = 1 - margin_x
- min_y = margin_y, max_y = 1 - margin_y

Mapped coordinates:

**mapped_x = (x_norm - min_x) / (max_x - min_x)** with clamp to [0, 1]  
**mapped_y = (y_norm - min_y) / (max_y - min_y)** with clamp to [0, 1]

Screen target pixel positions:

**target_x = mapped_x × (screen_width - 1)**  
**target_y = mapped_y × (screen_height - 1)**

Margin mapping allows users to reach screen edges without physically touching the extreme borders of the camera frame, trading off linearity for ergonomics.

### 12.2 Exponential Smoothing

Let alpha be smoothing factor (default 0.35). If no prior smoothed position exists, initialize smoothed position to target. Otherwise:

**smoothed_x = alpha × target_x + (1 - alpha) × previous_smoothed_x**  
**smoothed_y = alpha × target_y + (1 - alpha) × previous_smoothed_y**

Final cursor command uses integer-rounded smoothed coordinates via PyAutoGUI moveTo.

Lower alpha yields heavier smoothing and more lag; higher alpha yields snappier motion and more jitter.

### 12.3 Adaptive Alpha for Edge and Fast Motion

Adaptive_alpha modifies alpha per frame:

- If mapped position lies near any screen edge (within edge_snap_threshold 0.04 normalized units from 0 or 1), return **0.95** for near-instant tracking at borders.
- Else compute pixel delta between target and previous smoothed position. If delta exceeds fast_move_threshold_px (35 pixels), return **min(0.75, alpha + 0.30)**.
- Else return base alpha.

This addresses user-reported latency buildup near top-right and bottom screen regions where heavy smoothing prevented timely cursor arrival.

### 12.4 PyAutoGUI Latency Mitigation

PyAutoGUI global PAUSE, MINIMUM_DURATION, and MINIMUM_SLEEP are set to zero to avoid artificial sleeps between consecutive automation calls during rapid cursor updates.

### 12.5 Activation Guards in Main Loop

Cursor tracking requires simultaneously:

- System active.
- Index extended, thumb/middle/ring/pinky not extended (strict index-only pose).
- Thumb-index pinch ratio greater than CLICK_ARM_THRESHOLD_RATIO + 0.03 (thumb sufficiently far from index).
- click_aim_lock false (cursor frozen during pinch approach).
- brightness_mode_active false.
- volume_mode_active false.

When tracking inactive but not in aim lock, MouseController.reset clears smoothed state to avoid stale jumps on re-entry.

---

\newpage

## 13. Left-Click Interaction via Pinch Detection

### 13.1 Click-Ready Hand Shape

Clicking is armed only when system active, index extended, and middle, ring, pinky not extended. This approximates a pinch-without-extra-fingers pose.

### 13.2 Click Aim Lock

To reduce pre-click cursor drift, two mechanisms apply:

**Arm lock:** If click-ready and pinch_ratio < CLICK_ARM_THRESHOLD_RATIO (0.52), click_aim_lock becomes true—cursor movement stops even before full pinch closure.

**Pre-lock:** If index-only active and pinch_ratio < CLICK_PRELOCK_RATIO (0.65), click_aim_lock also engages earlier in the approach trajectory.

While click_aim_lock true, cursor tracking disabled.

### 13.3 Pinch Hysteresis and Click Execution

MouseController.maybe_left_click implements debounced clicking:

If not click_ready, pinch latch resets and no click.

If pinch latch already true (post-click), wait until pinch_distance_ratio exceeds CLICK_RELEASE_THRESHOLD_RATIO (0.50) to clear latch—fingers must open before another click arms.

If ratio still at or above CLICK_PINCH_THRESHOLD_RATIO (0.45), no new click—closure not deep enough.

If within CLICK_COOLDOWN_SECONDS (0.35) of last click, suppress.

Otherwise execute left click, record time, set latch true, return triggered flag.

**Hysteresis** means press threshold (0.45) lower than release threshold (0.50) in ratio terms—actually press triggers below 0.45 and release clears above 0.50, creating a stable band preventing oscillation when ratio hovers near boundary.

### 13.4 Displayed Pinch vs Raw Pinch

Overlay pinch ON state uses pinch_active = pinch_raw_active AND index_extended, preventing misleading pinch indication when middle finger alone brings landmarks into proximity. App switch selection uses pinch_raw_active without index requirement so pinch can confirm app choice even if finger state noisy.

### 13.5 Documented User Issues and Mitigations

Users reported cursor drift during pinch approach and low click registration rate (one of three attempts). Mitigations included aim lock bands, hysteresis, index-gated display pinch, and separation from volume/brightness modes. Residual sensitivity may still require per-user calibration of thresholds.

---

\newpage

## 14. Brightness Control via Vertical Gesture Motion

BrightnessController activates when main sets brightness_mode_active: system active, index and middle up, thumb/ring/pinky down, and volume mode not active.

### 14.1 Vertical Delta Computation

Uses middle fingertip normalized vertical coordinate y_norm each frame. On first active frame, stores baseline last_y without change.

Subsequent frames compute:

**delta = last_y - y_norm**

Positive delta means hand moved upward in image coordinates (smaller y), mapped to brightness increase direction.

If absolute delta below BRIGHTNESS_MOTION_THRESHOLD (0.025), ignore as noise.

If within BRIGHTNESS_COOLDOWN_SECONDS (0.08) of last update, ignore.

### 14.2 Step Quantization

Direction sign = +1 for upward, -1 for downward.

Steps = max(1, floor(abs(delta) / motion_threshold)).

Read current brightness percent (0–100) via screen-brightness-control library, clamp to valid range.

Target brightness = current + direction × steps × BRIGHTNESS_STEP_PERCENT (4 percent per step default).

Apply via set_brightness; update last_y and timestamp on success path.

### 14.3 Mutual Exclusivity with Volume

Because index+middle configuration overlaps volume finger set minus thumb, brightness explicitly requires thumb not extended and volume_mode_active false. Volume mode uses separate thumb readiness heuristic (next section) to avoid brightness hijacking during rotation.

---

\newpage

## 15. Application Switching via Open Palm and Alt+Tab Semantics

AppSwitcher emulates Windows Alt+Tab task switching using keyboard synthesis.

### 15.1 Entry Condition: Open Palm Hold

Open palm detected when system active and all five fingers classified up. update_entry tracks open_palm_start_time on first qualifying frame. Entry requires continuous open palm for APP_SWITCH_HOLD_SECONDS (1.0 second) while not already in mode and respecting APP_SWITCH_ENTER_COOLDOWN_SECONDS (1.0) since last entry.

Upon entry, _enter_mode sets in_mode true, records timestamps, presses and holds Alt, presses Tab once to open switcher UI.

### 15.2 Navigation by Horizontal Hand Motion

While in mode, horizontal position uses index tip normalized x. On first frame, store baseline previous_x.

Each update computes delta_x = hand_x_norm - previous_x. If absolute delta below APP_SWITCH_MOVE_THRESHOLD (0.06), no navigation.

If within APP_SWITCH_CYCLE_COOLDOWN_SECONDS (0.14), suppress cycling.

Otherwise determine forward = delta_x > 0. Steps = clamp between 1 and 3 based on magnitude relative to threshold. For each step: if forward, press Tab; else hold Shift, press Tab, release Shift (reverse direction).

Update previous_x, refresh activity timer.

### 15.3 Selection and Timeout

If pinch_active (raw pinch in app switch branch) and not yet latched, latch and exit_mode releasing Alt—confirms selection.

If inactivity exceeds APP_SWITCH_TIMEOUT_SECONDS (6.0), exit_mode without explicit selection.

exit_mode always attempts keyUp Alt if held.

### 15.4 Main Loop Isolation

When app_switcher.in_mode, main executes dedicated branch drawing overlay and continues loop early—skipping cursor, brightness, volume, and click paths. Resets mouse, brightness, volume controllers; disables click_ready.

### 15.5 Window Visibility Bug and Fix

Alt+Tab causes OpenCV preview window to lose visibility. Original logic treated invisible window as user close, terminating application. Fix uses multi-frame invisible counter (fifteen frames) and ignores visibility loss while in app switch mode. Also changed interpretation to require sustained invisible state rather than single-frame glitch.

---

\newpage

## 16. Volume Control via Rotational Gesture Analysis

VolumeController is the most mathematically involved control module.

### 16.1 Activation Conditions in Main

Volume mode requires system active; index and middle extended; ring and pinky down; not brightness_mode_active; and volume_thumb_ready.

volume_thumb_ready = strict thumb extended OR (pinch_ratio > VOLUME_THUMB_RELAXED_SPREAD_RATIO AND thumb_extension > VOLUME_THUMB_EXTENSION_RATIO × palm_width).

Thumb extension distance uses Euclidean distance between thumb tip (4) and thumb MCP (2). Relaxed fallback allows volume continuity when strict thumb classifier fails during anticlockwise rotation orientations.

### 16.2 Rotation Angle Definition

Compute cluster center as average of thumb tip, index tip, middle tip positions.

Compute anchor as average of wrist, index MCP, pinky MCP.

Vector from anchor to center:

**dx = center_x - anchor_x**  
**dy = -(center_y - anchor_y)**  (invert y for Cartesian consistency)

If hypot(dx, dy) < 0.001, return no angle.

**angle = atan2(dy, dx)** in radians.

### 16.3 Wrapped Angular Delta

Given previous angle, compute raw delta = angle - previous_angle. Normalize to (-π, π] by subtracting or adding 2π until within range. Accumulate into accumulated_rotation buffer.

### 16.4 Triggering Volume Steps

If cooldown elapsed and absolute accumulated_rotation exceeds VOLUME_ROTATION_STEP_RAD (0.32 rad default):

steps = max(1, floor(abs(accumulated_rotation) / rotation_step))

Clockwise determination: accumulated_rotation < 0 treated as clockwise in implementation (due to y-inversion and coordinate conventions). increase = clockwise if VOLUME_CLOCKWISE_INCREASES true else inverted.

Apply steps, reset accumulated buffer, update direction label up or down.

### 16.5 Volume Application Paths

**Primary path (pycaw):** Obtain IAudioEndpointVolume interface for default speakers. Read current scalar in [0,1]. Adjust by steps × VOLUME_STEP_SCALAR (0.04 default). Write via SetMasterVolumeLevelScalar.

**Fallback path:** If endpoint unavailable, press volumeup or volumedown keys steps times via PyAutoGUI; approximate percent tracking internally.

### 16.6 Interaction Suppression

When volume active, main resets mouse and brightness controllers, disables click_ready, clears click_aim_lock, sets app_switch_message accordingly.

---

\newpage

## 17. Main Loop Orchestration and Gesture Priority Arbitration

The runtime loop in main.py is the **authoritative policy engine**. Approximate evaluation order when hand present:

1. Run gesture detection; compute pinch_ratio, index_extended, pinch display flags.
2. Update system toggle via closed fist; handle OFF transition exiting app switch.
3. Evaluate open palm for app switch entry.
4. If app_switcher.in_mode → handle navigation/select/timeout only; skip other controls; continue.
5. Compute click_ready shape and click_aim_lock (arm + prelock rules).
6. Compute brightness_mode_active (index+middle, thumb down).
7. Compute palm metrics; volume_thumb_ready; volume_mode_active (excludes brightness).
8. If volume active → update volume; suppress other actions.
9. Else if brightness active → update brightness.
10. Compute index_only_active; apply prelock; if safe, move cursor.
11. Maybe left click if click_ready and not brightness/volume active.
12. Draw overlay; show frame; handle quit keys and window visibility.

This ordering implements specification priority **with app switch consuming entire frames while active** and volume taking precedence over brightness when both finger sets might appear similar under noisy thumb logic.

### 17.1 No-Hand Behavior

When tracking lost, controllers reset, click latch cleared, app switch may timeout if was active, overlay shows waiting state.

### 17.2 Shutdown Guarantees

finally block calls app_switcher.exit_mode(), tracker.close(), capture.release(), destroyAllWindows—critical for releasing Alt modifier state.

---

\newpage

## 18. User Interface and Debug Overlay

The overlay module renders textual diagnostics directly on the BGR frame using OpenCV putText with anti-aliased fonts.

Displayed fields include:

- System ACTIVE/OFF banner (color coded green vs red tint).
- FPS numeric estimate.
- Handedness label or no-hand warning.
- Gesture label from classifier.
- Count and names of fingers up.
- Cursor tracking on/off.
- Pinch on/off with live ratio value.
- Left click triggered vs waiting.
- Click aim lock on/off.
- Brightness mode and level with updated marker.
- App switch mode and textual status message (entered, cycling, selected, timeout, etc.).
- Volume mode, percent level, direction, updated marker.

Early return when gesture_result None prevents accessing fields on missing hand—only system and FPS show plus no-hand message.

This overlay was essential for iterative threshold tuning without external plotting tools.

---

\newpage

## 19. Configuration Management and Tunable Parameters

All constants live in system/config.py for single-point tuning.

### 19.1 Camera and MediaPipe

CAMERA_INDEX=0, FRAME_WIDTH=960, FRAME_HEIGHT=540, MAX_NUM_HANDS=1, MIN_DETECTION_CONFIDENCE=0.7, MIN_TRACKING_CONFIDENCE=0.6, model URL and local path for hand landmarker task file.

### 19.2 Toggle

TOGGLE_FIST_HOLD_FRAMES=12, TOGGLE_COOLDOWN_SECONDS=1.0.

### 19.3 Cursor and Click

CURSOR_SMOOTHING_ALPHA=0.35, CURSOR_ACTIVE_MARGIN_X=0.08, CURSOR_ACTIVE_MARGIN_Y=0.12, CLICK_PINCH_THRESHOLD_RATIO=0.45, CLICK_COOLDOWN_SECONDS=0.35, CLICK_ARM_THRESHOLD_RATIO=0.52, CLICK_RELEASE_THRESHOLD_RATIO=0.50, CLICK_PRELOCK_RATIO=0.65.

### 19.4 Brightness

BRIGHTNESS_STEP_PERCENT=4, BRIGHTNESS_MOTION_THRESHOLD=0.025, BRIGHTNESS_COOLDOWN_SECONDS=0.08.

### 19.5 App Switch

APP_SWITCH_HOLD_SECONDS=1.0, APP_SWITCH_TIMEOUT_SECONDS=6.0, APP_SWITCH_MOVE_THRESHOLD=0.06, APP_SWITCH_CYCLE_COOLDOWN_SECONDS=0.14, APP_SWITCH_ENTER_COOLDOWN_SECONDS=1.0.

### 19.6 Volume

VOLUME_ROTATION_STEP_RAD=0.32, VOLUME_STEP_SCALAR=0.04, VOLUME_COOLDOWN_SECONDS=0.10, VOLUME_CLOCKWISE_INCREASES=True, VOLUME_THUMB_RELAXED_SPREAD_RATIO=0.46, VOLUME_THUMB_EXTENSION_RATIO=0.35.

Tuning guide conceptually: lower pinch thresholds increase click sensitivity; higher arm/prelock thresholds lock cursor earlier; smaller rotation step rad increases volume sensitivity; larger motion threshold reduces brightness noise.

---

\newpage

## 20. Development History and Design Iterations

### 20.1 Phase 0 — Scaffolding

Established modular directory tree and placeholder docstrings without logic. Set dependency list anticipating Windows control requirements.

### 20.2 Phase 1 — Recognition Demo

Implemented webcam loop, landmark inference, finger states, overlay. Migrated from deprecated MediaPipe solutions API to Tasks HandLandmarker after environment error. Added automatic model download.

### 20.3 Thumb Detection Iterations

Progression from handedness-dependent horizontal rule (failed under mirror) to angle-based thumb, to overly permissive multi-cue with temporal voting (sticky false positives), to conservative three-criterion AND logic (user acceptance), to volume-specific relaxed fallback causing brightness conflicts, to extension-ratio augmented fallback with mutual exclusion rules.

### 20.4 Cursor Mapping Iterations

Explored absolute mapping with margins, brief relative delta mapping per user request for full-screen reach, reverted to absolute per user preference, added adaptive smoothing and zero PyAutoGUI pause for edge latency.

### 20.5 Click Iterations

Added pinch ratio metric, aim lock, hysteresis press/release, index-gated pinch display, prelock ratio, interaction guards against volume and brightness.

### 20.6 Feature Additions

Brightness vertical control, app switcher with Alt+Tab semantics and window visibility fixes, volume rotation with pycaw and init-order bugfix for endpoint attribute.

### 20.7 Regression Cycles

Late-stage issues included click drift return, brightness/volume dual activation, middle-only false pinch display, app closing on open palm, volume init crash. Each addressed through policy tweaks rather than architectural rewrite.

---

\newpage

## 21. Performance, Reliability, and Known Limitations

### 21.1 Performance

Achievable loop rates depend on CPU, camera driver, and MediaPipe inference cost. Typical development sessions reported usable interactive FPS in the twenty to thirty range. TensorFlow Lite delegate messages indicate XNNPACK acceleration on CPU.

### 21.2 Reliability Strengths

Modular boundaries enabled isolated testing per feature. Hold-to-activate and cooldown patterns reduced accidental toggles. Hysteresis improved click repeatability. App switch cleanup in finally reduces stuck modifier risk.

### 21.3 Limitations

**Thumb classification** remains context-sensitive; shared metrics create coupling between features.

**Single-hand only** — no two-hand gestures.

**Lighting sensitivity** — extreme shadows or backlighting degrade landmark stability (not extensively compensated).

**Platform coupling** — Windows-specific control paths.

**Main loop complexity** — priority logic centralized in one large function, increasing regression risk.

**cursor_smoother unused** — architectural debt.

**No automated test suite** — validation manual.

**README minimal** — onboarding relies on mentor or external docs.

**Occlusion and motion blur** — not modeled explicitly.

**Kalman / One Euro filtering** — mentioned in roadmap but not implemented.

---

\newpage

## 22. Testing Methodology and Validation Scenarios

Recommended manual test matrix:

| Scenario | Expected outcome |
|----------|------------------|
| Closed fist hold ~0.4s+ | System toggles ACTIVE/OFF |
| Index only, thumb far | Cursor tracks; mapped edges reachable |
| Approach pinch slowly | Aim lock engages; minimal cursor drift |
| Complete pinch | Single left click; must release to re-click |
| Index+middle vertical slide | Brightness changes; volume mode off |
| Thumb+index+middle rotate CW/CCW | Volume changes; brightness off |
| Open palm hold 1s | App switch mode enters |
| Horizontal motion in switcher | Tabs cycle forward/back |
| Pinch in switcher | Selection confirmed; Alt released |
| System OFF | No cursor/click/brightness/volume |
| Press q or close window | Clean exit |

Regression focus areas from user feedback: click registration rate, brightness-volume exclusivity, app window closing unexpectedly, thumb false negatives during rotation.

---

\newpage

## 23. Research Contributions and Academic Positioning

### 23.1 Low-Latency Stabilized Cursor Interaction

The project contributes a practical combination of margin-expanded absolute mapping, exponential smoothing with edge-aware adaptive alpha, and pre-click aim locking—each addressing distinct failure modes (reach, edge lag, pinch drift). While individual techniques are known, their integration for webcam-only HCI with explicit hold-to-activate policy forms a coherent systems narrative.

### 23.2 Gesture Arbitration Under Overlapping Finger Sets

Brightness and volume poses share index and middle extension; disambiguation via thumb strict vs relaxed policies illustrates real-world combinatorial gesture design challenges.

### 23.3 Temporal Rotation for Continuous Control

Volume uses wrapped angular deltas with accumulation thresholding—closer to continuous analog control than discrete static poses—aligning with "temporal gesture recognition" emphasis in project specification.

### 23.4 Engineering for Demonstrability

Live diagnostic overlay transforms opaque classification into explainable feedback valuable in academic demonstration and user calibration.

---

\newpage

## 24. Future Work and Recommended Refactoring

### 24.1 GestureArbiter Class

Extract priority policy from main into dedicated arbitration module with explicit enum states OFF, ACTIVE, APP_SWITCH, BRIGHTNESS, VOLUME, CURSOR, CLICK_ARMED. Reduces coupling and enables unit tests per transition.

### 24.2 Per-Mode Thumb Estimator

Provide mode parameter adjusting thumb strictness without duplicating logic in main.

### 24.3 Integrate or Remove cursor_smoother

Either move smoothing strategies into dedicated module consumed by MouseController or delete placeholder to avoid confusion.

### 24.4 Documentation

Expand README with install prerequisites, gesture cheat sheet, troubleshooting MediaPipe warnings, tuning tables mirroring Section 19.

### 24.5 Filtering Research

Implement Kalman or One Euro filter on cursor target coordinates for comparative evaluation in thesis experiments.

### 24.6 Cross-Platform Adapters

Abstract OS control behind interface with Windows, Linux, macOS implementations.

### 24.7 Automated Testing

Synthetic landmark sequences injected into gesture_detector and controllers to regression-test thresholds without live camera.

### 24.8 Latency Instrumentation

Log segment timings (capture, inference, control, draw) for quantitative latency chapter.

---

\newpage

## 25. Conclusion

The Gesture-Based Desktop Control System successfully demonstrates a modular, real-time vision pipeline that converts hand poses and motions into meaningful desktop actions. From initial scaffolding through finger recognition, MediaPipe Tasks migration, and incremental feature delivery, the project evolved into a multi-modal contactless controller supporting system toggle, cursor movement, clicking, brightness adjustment, application switching, and volume rotation.

Core technical ideas include palm-width-normalized geometric ratios, conservative multi-cue thumb classification with context-specific relaxed fallback, margin-based absolute cursor mapping with adaptive exponential smoothing, pinch hysteresis for debounced clicking, vertical delta step control for brightness, Alt+Tab semantic app switching with temporal holds and timeouts, and wrapped angular accumulation for rotational volume adjustment. The main runtime loop enforces priority among overlapping gestures, while the overlay provides transparency for tuning and demonstration.

Remaining challenges—click drift sensitivity, thumb false negatives under rotation, and overlapping finger-set ambiguity—reflect fundamental HCI tradeoffs rather than implementation oversight. Future architectural refactoring toward explicit state machines and per-gesture thumb policies would improve maintainability and testability for research continuation.

The system is suitable for portfolio demonstration, supervised laboratory evaluation, and as a foundation for master's thesis chapters on real-time vision-based human–computer interaction, provided rigorous user studies and quantitative latency measurements are added in subsequent work.

---

\newpage

## 26. Appendix: Landmark Index Reference and Parameter Tables

### 26.1 MediaPipe Hand Landmark Indices Used

| Index | Anatomical role |
|-------|-----------------|
| 0 | Wrist |
| 1 | Thumb CMC |
| 2 | Thumb MCP |
| 3 | Thumb IP |
| 4 | Thumb tip |
| 5 | Index MCP |
| 6 | Index PIP |
| 8 | Index tip |
| 10 | Middle PIP |
| 12 | Middle tip |
| 14 | Ring PIP |
| 16 | Ring tip |
| 17 | Pinky MCP |
| 18 | Pinky PIP |
| 20 | Pinky tip |

### 26.2 Complete Configuration Constant Table

| Constant | Value | Role |
|----------|-------|------|
| CAMERA_INDEX | 0 | Webcam device selection |
| FRAME_WIDTH / HEIGHT | 960 / 540 | Capture resolution request |
| MAX_NUM_HANDS | 1 | Single-hand tracking |
| MIN_DETECTION_CONFIDENCE | 0.7 | Detection threshold |
| MIN_TRACKING_CONFIDENCE | 0.6 | Tracking threshold |
| TOGGLE_FIST_HOLD_FRAMES | 12 | Frames to confirm fist toggle |
| TOGGLE_COOLDOWN_SECONDS | 1.0 | Toggle debounce |
| CURSOR_SMOOTHING_ALPHA | 0.35 | Base EMA smoothing |
| CURSOR_ACTIVE_MARGIN_X | 0.08 | Horizontal margin map |
| CURSOR_ACTIVE_MARGIN_Y | 0.12 | Vertical margin map |
| CLICK_PINCH_THRESHOLD_RATIO | 0.45 | Pinch press trigger |
| CLICK_COOLDOWN_SECONDS | 0.35 | Between clicks |
| CLICK_ARM_THRESHOLD_RATIO | 0.52 | Aim lock arm distance |
| CLICK_RELEASE_THRESHOLD_RATIO | 0.50 | Pinch release for re-arm |
| CLICK_PRELOCK_RATIO | 0.65 | Early aim lock distance |
| BRIGHTNESS_STEP_PERCENT | 4 | Per step brightness change |
| BRIGHTNESS_MOTION_THRESHOLD | 0.025 | Min vertical motion |
| BRIGHTNESS_COOLDOWN_SECONDS | 0.08 | Brightness update rate limit |
| APP_SWITCH_HOLD_SECONDS | 1.0 | Open palm hold to enter |
| APP_SWITCH_TIMEOUT_SECONDS | 6.0 | Inactivity exit |
| APP_SWITCH_MOVE_THRESHOLD | 0.06 | Horizontal navigate delta |
| APP_SWITCH_CYCLE_COOLDOWN_SECONDS | 0.14 | Tab cycle rate limit |
| APP_SWITCH_ENTER_COOLDOWN_SECONDS | 1.0 | Re-entry debounce |
| VOLUME_ROTATION_STEP_RAD | 0.32 | Rotation per volume step |
| VOLUME_STEP_SCALAR | 0.04 | Scalar delta per step |
| VOLUME_COOLDOWN_SECONDS | 0.10 | Volume update rate limit |
| VOLUME_CLOCKWISE_INCREASES | True | Rotation polarity |
| VOLUME_THUMB_RELAXED_SPREAD_RATIO | 0.46 | Volume thumb fallback spread |
| VOLUME_THUMB_EXTENSION_RATIO | 0.35 | Volume thumb fallback extension |

### 26.3 Dependency Package List

opencv-python, mediapipe, numpy, pyautogui, keyboard, mouse, pycaw, screen-brightness-control, comtypes.

---

**End of Final Project Report**

*Document generated from full repository analysis and complete development conversation history. For operational quick-start instructions, see project README and summary.md development log.*

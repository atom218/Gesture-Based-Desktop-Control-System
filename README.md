# Gesture-Based Desktop Control System

A real-time, webcam-driven desktop control system that uses hand tracking and gesture recognition to operate your computer without a mouse or keyboard for common tasks. Built for a master's-level computer vision / HCI project with a modular architecture suitable for demos, portfolio use, and further research.

The system is **on-demand only**: it stays inactive until you explicitly enable it, then interprets hand poses and motions to control the cursor, click, brightness, volume, and application switching.

---

## Features

| Gesture | Action |
|--------|--------|
| **Closed fist** (hold ~0.4s) | Toggle system **ON** / **OFF** |
| **Index finger only** | Move mouse cursor (full-screen mapping) |
| **Thumb + index pinch** | Left mouse click (debounced) |
| **Index + middle** (vertical slide) | Increase / decrease display brightness |
| **Thumb + index + middle** (rotate) | Increase / decrease system volume |
| **Open palm** (hold 1s) | Enter app-switch mode (Alt+Tab style) |
| **In app-switch mode** | Move hand left/right to cycle apps; pinch to select |

While active, a live debug overlay shows system state, detected gesture, finger status, and per-feature modes.

---

## Demo

```
Webcam → Hand landmarks (MediaPipe) → Finger states → Gesture logic → Desktop actions
```

**Pipeline**

1. Capture and mirror webcam frames  
2. Detect 21 hand landmarks per frame  
3. Classify which fingers are extended  
4. Arbitrate gestures by priority  
5. Execute OS controls (mouse, keys, brightness, volume)  
6. Render status overlay on the preview window  

---

## Requirements

- **OS:** Windows (primary target; uses `pycaw`, Alt+Tab, and `screen-brightness-control`)
- **Python:** 3.10+ recommended (tested with 3.13)
- **Hardware:** Webcam, adequate lighting, single hand in frame

---

## Installation

Clone the repository and install dependencies from the project root:

```bash
cd gesture-desktop-controller
python -m pip install -r requirements.txt
```

On first run, the hand landmark model is downloaded automatically to `assets/models/hand_landmarker.task` if it is not already present.

---

## Usage

From the `gesture-desktop-controller` directory:

```bash
python src/main.py
```

| Input | Effect |
|-------|--------|
| **Closed fist** (hold) | Turn control system on or off |
| **q** | Quit application |
| **Close window** | Quit application |

### Quick start workflow

1. Run the app and allow camera access if prompted.  
2. Show a **closed fist** until the overlay reads `SYSTEM: ACTIVE`.  
3. Point with your **index finger** to move the cursor.  
4. **Pinch** thumb and index to click.  
5. Use **index + middle** and slide up/down for brightness.  
6. Use **thumb + index + middle** and rotate clockwise/counterclockwise for volume.  
7. Show an **open palm** for one second to enter app switching; move horizontally to cycle; pinch to confirm.  
8. **Closed fist** again to deactivate when finished.

---

## Gesture priority

When multiple conditions could apply, the system resolves them in this order:

1. System toggle (closed fist)  
2. App switch mode (when active, blocks other controls)  
3. Volume control  
4. Brightness control  
5. Left click  
6. Cursor tracking  

This reduces accidental cross-triggering between similar hand poses.

---

## Project structure

```
gesture-desktop-controller/
├── src/
│   ├── main.py                 # Application entry point and main loop
│   ├── tracking/
│   │   └── hand_tracker.py     # Webcam + MediaPipe Hand Landmarker
│   ├── gestures/
│   │   └── gesture_detector.py # Finger states, pinch metric, labels
│   ├── controls/
│   │   ├── mouse_controller.py       # Cursor + click
│   │   ├── brightness_controller.py  # Vertical brightness gesture
│   │   ├── volume_controller.py      # Rotational volume gesture
│   │   └── app_switcher.py           # Alt+Tab app switching
│   ├── system/
│   │   ├── config.py           # Tunable thresholds and constants
│   │   └── state_manager.py    # ON/OFF toggle logic
│   ├── ui/
│   │   └── overlay.py          # Debug HUD on preview frame
│   └── smoothing/
│       └── cursor_smoother.py  # Placeholder for future smoothing module
├── assets/models/               # Hand landmarker model (auto-downloaded)
├── docs/                       # Technical documentation
├── experiments/                # Future experiments
├── requirements.txt
├── summary.md                  # Development conversation log
└── README.md
```

---

## Configuration

All tunable parameters live in `src/system/config.py`, including:

- Camera index and resolution  
- MediaPipe detection / tracking confidence  
- Cursor smoothing and screen margin mapping  
- Pinch thresholds for click and aim-lock  
- Brightness step size and motion sensitivity  
- App-switch hold time, timeout, and navigation threshold  
- Volume rotation sensitivity and thumb fallback rules  

Adjust these values if gestures feel too sensitive or unresponsive for your camera, hand size, or lighting.

---

## Technical stack

| Library | Role |
|---------|------|
| [OpenCV](https://opencv.org/) | Webcam capture, display, landmark drawing |
| [MediaPipe](https://developers.google.com/mediapipe) | Hand landmark detection (Tasks API) |
| [NumPy](https://numpy.org/) | Numerical operations |
| [PyAutoGUI](https://pyautogui.readthedocs.io/) | Mouse and keyboard synthesis |
| [pycaw](https://github.com/AndreMiras/pycaw) | Windows master volume control |
| [screen-brightness-control](https://github.com/Crozzers/screen-brightness-control) | Display brightness |

---

## Troubleshooting

**`src/main.py` not found**  
Run commands from inside `gesture-desktop-controller`, not the parent repo folder.

**TensorFlow / MediaPipe warnings in terminal**  
Messages such as `oneDNN`, `XNNPACK`, or `inference_feedback_manager` are usually informational and can be ignored.

**Camera does not open**  
Check permissions, close other apps using the webcam, or change `CAMERA_INDEX` in `config.py`.

**Cursor drifts before clicking**  
The system uses click aim-lock when thumb and index approach each other; tune `CLICK_ARM_THRESHOLD_RATIO` and `CLICK_PRELOCK_RATIO` in config.

**Clicks register inconsistently**  
Ensure index is up and other fingers are down; release pinch fully between clicks. Adjust `CLICK_PINCH_THRESHOLD_RATIO` and `CLICK_RELEASE_THRESHOLD_RATIO`.

**Brightness and volume conflict**  
Brightness requires thumb down; volume requires thumb + index + middle. If both modes appear active, thumb detection may need tuning—see `VOLUME_THUMB_RELAXED_SPREAD_RATIO` and related settings.

**App window closes during app switch**  
The app ignores brief window hide events during Alt+Tab; update to the latest code if this persists.

**Volume init error on older runs**  
Ensure `volume_controller.py` initializes the audio endpoint before reading volume level (fixed in current version).

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/FINAL_PROJECT_REPORT.md](docs/FINAL_PROJECT_REPORT.md) | Full technical report: architecture, formulas, and implementation detail |
| [summary.md](summary.md) | Step-by-step development history and iteration notes |

---

## Research focus

This project emphasizes **real-time interactive vision system design**, with particular attention to:

- Low-latency, stabilized webcam-to-screen cursor mapping  
- Robust finger-state and thumb classification under mirrored video  
- Temporal gestures (rotation, vertical slide) with debouncing  
- Modular, maintainable control pipelines for HCI experimentation  

---

## Limitations

- Single-hand tracking only  
- Windows-oriented OS integration  
- Performance and accuracy depend on lighting and camera quality  
- Thresholds may require per-user calibration  
- `cursor_smoother.py` is reserved for future work; smoothing is implemented in `mouse_controller.py`

---

## License

Add your license here if publishing the repository publicly.

---

## Acknowledgments

Hand tracking powered by Google's MediaPipe Hand Landmarker. Developed as an academic gesture-based desktop control system using Python and OpenCV.

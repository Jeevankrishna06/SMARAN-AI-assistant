# Vision Mode v1.0

Control your mouse cursor with hand gestures using your webcam.

## Install

```bash
pip install opencv-python mediapipe pyautogui
```

> **macOS users** – also run:
> ```bash
> pip install pyobjc-framework-Quartz pyobjc-core
> ```
> and grant your terminal **Accessibility** + **Screen Recording** permission
> in *System Settings → Privacy & Security*.

## Run

```bash
python vision_mode.py
```

Use a different camera:
```bash
python vision_mode.py --camera 1
```

## Gestures

| Gesture | Action |
|---|---|
| Index finger extended | Move cursor |
| Thumb + Index pinch | Left click |
| Thumb + Middle pinch | Right click |
| Closed fist held 2 s | Exit Vision Mode |

Press **Q** or **Escape** to quit at any time.

## Safety

- Your physical keyboard and mouse always keep working.
- PyAutoGUI FAILSAFE is ON: move the mouse to any screen corner to abort.
- Press **Q** / **Escape** to quit without any gestures.

## File Structure

```
vision_mode/
├── vision_mode.py        # Entry point, main loop
├── hand_tracker.py       # MediaPipe wrapper
├── gesture_recognizer.py # Landmark → gesture classifier
├── cursor_controller.py  # Gesture → OS mouse actions
├── overlay.py            # Debug HUD drawing
├── requirements.txt
└── README.md
```

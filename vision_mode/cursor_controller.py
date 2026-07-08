"""
cursor_controller.py
Maps gesture recognition to PyAutoGUI OS mouse control actions with dynamic smoothing and safety overrides.

Gesture → Action mapping:
  pointing       → move cursor (index finger)
  open_app       → Enter key (thumb + index)
  close_app      → Alt+F4 (thumb + middle)
  left_click     → left click (thumb + ring)
  right_click    → right click (thumb + pinky)
  select         → left click (thumb + index + middle)
  drag           → mouseDown + move + mouseUp (thumb + index + middle hold)
"""

import time
import math
import pyautogui
from .hand_tracker import HandTracker
from .gesture_recognizer import (
    GestureRecognizer,
    GESTURE_LEFT_CLICK, GESTURE_RIGHT_CLICK,
    GESTURE_SELECT, GESTURE_NONE,
    GESTURE_POINT, GESTURE_FIST, GESTURE_DRAG,
    GESTURE_OPEN_APP, GESTURE_CLOSE_APP,
)

pyautogui.PAUSE    = 0.0
pyautogui.FAILSAFE = True


class CursorController:
    # Normalized active zone boundaries
    ZONE_L = 0.25;  ZONE_R = 0.75 
    ZONE_T = 0.30;  ZONE_B = 0.70

    # Smoothing parameters — optimized for 60 FPS real-time tracking with high jitter suppression
    MIN_ALPHA       = 0.005   # near-zero smoothing at rest to kill jitter
    MAX_ALPHA       = 0.080   # increased max alpha for fast, real-time responsive tracking
    SPEED_THRESHOLD = 0.04    # lower speed threshold to transition to fast tracking sooner

    CLICK_COOLDOWN  = 0.20    # seconds between click actions

    def __init__(self):
        self._sw, self._sh = pyautogui.size()
        self._sx = self._sw / 2
        self._sy = self._sh / 2

        self._prev_nx = None
        self._prev_ny = None

        self._last_left  = 0.0
        self._last_right = 0.0
        self._last_select = 0.0
        self._paused_until = 0.0

        self._dragging   = False

        # Edge-detection flags for single-fire gestures
        self._left_click_active   = False
        self._right_click_active  = False
        self._select_click_active = False
        self._open_logged  = False
        self._close_logged = False

        # Safety override tracking
        self._expected_x = int(self._sx)
        self._expected_y = int(self._sy)
        self._moved_last_frame = False

    def update(self, tracker: HandTracker, recognizer: GestureRecognizer):
        now = time.monotonic()
        g = recognizer.gesture

        is_paused = now < self._paused_until

        # ── 1. Update Cursor Coordinate Baseline & Smoothing ────────────────
        if tracker.landmarks:
            rx, ry = tracker.tip(HandTracker.INDEX_TIP)
            
            # Map normalized index finger coordinate to active zone bounds
            nx = max(0.0, min(1.0, (rx - self.ZONE_L) / (self.ZONE_R - self.ZONE_L)))
            ny = max(0.0, min(1.0, (ry - self.ZONE_T) / (self.ZONE_B - self.ZONE_T)))

            # Always update EMA position (for smooth cursor)
            if self._dragging:
                # Extra smooth constant alpha during window drag
                alpha = 0.04
            elif self._prev_nx is not None:
                # Dynamic speed-based EMA alpha computation
                dist = math.hypot(nx - self._prev_nx, ny - self._prev_ny)
                factor = min(1.0, dist / self.SPEED_THRESHOLD)
                alpha = self.MIN_ALPHA + (self.MAX_ALPHA - self.MIN_ALPHA) * factor
            else:
                alpha = 1.0

            self._prev_nx = nx
            self._prev_ny = ny

            self._sx = alpha * (nx * self._sw) + (1 - alpha) * self._sx
            self._sy = alpha * (ny * self._sh) + (1 - alpha) * self._sy

            # Move cursor only if gesture control is not paused
            # Move on: pointing, drag, open_app, close_app
            if not is_paused and g in (GESTURE_POINT, GESTURE_DRAG,
                                       GESTURE_OPEN_APP, GESTURE_CLOSE_APP):
                target_x = int(self._sx)
                target_y = int(self._sy)
                pyautogui.moveTo(target_x, target_y)
                self._expected_x = target_x
                self._expected_y = target_y
                self._moved_last_frame = True

        # ── 2. Click / Drag Control (Only when not paused) ──────────────────
        if not is_paused:
            # ── Left Click (thumb + ring) — single fire on transition ────
            if g == GESTURE_LEFT_CLICK:
                if not self._left_click_active:
                    self._left_click_active = True
                    if now - self._last_left > self.CLICK_COOLDOWN:
                        pyautogui.click(button="left")
                        self._last_left = now
                        print("[CursorController] Left Click")
            else:
                self._left_click_active = False

            # ── Right Click (thumb + pinky) — single fire on transition ──
            if g == GESTURE_RIGHT_CLICK:
                if not self._right_click_active:
                    self._right_click_active = True
                    if now - self._last_right > self.CLICK_COOLDOWN:
                        pyautogui.click(button="right")
                        self._last_right = now
                        print("[CursorController] Right Click")
            else:
                self._right_click_active = False

            # ── Select (thumb + index + middle pinch) ────────────────────
            if g == GESTURE_SELECT:
                if not self._select_click_active:
                    self._select_click_active = True
                    if now - self._last_select > self.CLICK_COOLDOWN:
                        pyautogui.click(button="left")
                        self._last_select = now
                        print("[CursorController] Select Action")
            else:
                self._select_click_active = False

            # ── Drag (thumb + index + middle held) ───────────────────────
            if g == GESTURE_DRAG:
                if not self._dragging:
                    pyautogui.mouseDown(button="left")
                    self._dragging = True
                    print("[CursorController] Drag START")
            else:
                if self._dragging:
                    pyautogui.mouseUp(button="left")
                    self._dragging = False
                    print("[CursorController] Drag END")

        else:
            # If paused, update coordinates to match current mouse position to prevent jump
            curr_x, curr_y = pyautogui.position()
            self._expected_x = curr_x
            self._expected_y = curr_y
            self._moved_last_frame = False

        # ── 3. Open / Close App Controls ────────────────────────────────────
        if g == GESTURE_OPEN_APP:
            if not self._open_logged:
                self._open_logged = True
                print("[VISION]\nOPEN DETECTED")
                # Double-click at cursor position to open items (icons, files, etc.)
                pyautogui.doubleClick()
        else:
            self._open_logged = False

        if g == GESTURE_CLOSE_APP:
            if not self._close_logged:
                self._close_logged = True
                print("[VISION]\nCLOSE DETECTED")
                # Safely close only real app windows, never the desktop/shell
                self._safe_close_foreground()
        else:
            self._close_logged = False

        # ── 4. Check Safety Override (User moved physical mouse) ───────────
        actual_x, actual_y = pyautogui.position()
        if self._moved_last_frame and not is_paused:
            dx = actual_x - self._expected_x
            dy = actual_y - self._expected_y
            d_offset = math.hypot(dx, dy)
            if d_offset > 15:
                self._paused_until = now + 1.5
                print(f"[CursorController] Safety override: user moved physical mouse. Pausing control for 1.5s.")
                # Release dragging if active
                if self._dragging:
                    pyautogui.mouseUp(button="left")
                    self._dragging = False

    def _safe_close_foreground(self):
        """Close the foreground window using win32gui, but skip desktop/shell windows."""
        try:
            import win32gui
            import win32con

            SKIP_CLASSES = {
                "Shell_TrayWnd", "Progman", "WorkerW",
                "Shell_SecondaryTrayWnd", "DV2ControlHost",
                "Windows.UI.Core.CoreWindow",
                "MultitaskingViewFrame", "ForegroundStaging",
                "NotifyIconOverflowWindow",
            }

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                print("[CursorController] No foreground window found.")
                return

            class_name = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)

            # Don't close the Vision Mode camera window itself
            if title == "Vision Mode  |  Q to quit":
                print("[CursorController] Skipping close: Vision Mode window.")
                return

            # Don't close desktop/shell/system windows
            if class_name in SKIP_CLASSES:
                print(f"[CursorController] Skipping close: system window ({class_name}).")
                return

            # Safe to close
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            print(f"[CursorController] Closed: '{title}' ({class_name})")

        except ImportError:
            # Fallback if win32gui not available — still avoid desktop
            print("[CursorController] win32gui not available, skipping close.")
        except Exception as e:
            print(f"[CursorController] Close error: {e}")

    @property
    def is_paused(self) -> bool:
        return time.monotonic() < self._paused_until

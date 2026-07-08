"""
overlay.py
Full debug overlay HUD drawn onto the webcam frame containing FPS, states, legend, and timers.
"""

import cv2
import time
from .gesture_recognizer import (
    GESTURE_NONE, GESTURE_POINT,
    GESTURE_LEFT_CLICK, GESTURE_RIGHT_CLICK,
    GESTURE_SELECT, GESTURE_FIST, GESTURE_DRAG,
    GESTURE_OPEN_APP, GESTURE_CLOSE_APP,
)

# BGR colours
C_WHITE  = (255, 255, 255)
C_BLACK  = (0,   0,   0)
C_GREEN  = (50,  220,  50)
C_YELLOW = (30,  220, 220)
C_ORANGE = (30,  140, 255)
C_RED    = (50,   50, 220)
C_BLUE   = (220, 140,  50)
C_CYAN   = (200, 200,  50)
C_GRAY   = (140, 140, 140)

_GESTURE_META = {
    GESTURE_NONE:        ("No hand",              C_GRAY),
    GESTURE_POINT:       ("Pointing (cursor)",    C_GREEN),
    GESTURE_LEFT_CLICK:  ("L-Click (Thumb+Ring)", C_YELLOW),
    GESTURE_RIGHT_CLICK: ("R-Click (Thumb+Pinky)",C_ORANGE),
    GESTURE_SELECT:      ("Select (Th+Idx+Mid)",  C_CYAN),
    GESTURE_FIST:        ("Closed Fist",          C_RED),
    GESTURE_DRAG:        ("Drag (Th+Idx+Mid)",    C_BLUE),
    GESTURE_OPEN_APP:    ("Open (Thumb+Index)",   C_GREEN),
    GESTURE_CLOSE_APP:   ("Close (Thumb+Mid)",    C_RED),
}

_FONT  = cv2.FONT_HERSHEY_SIMPLEX


class Overlay:
    def __init__(self, w, h):
        self._w = w
        self._h = h
        self._ticks = []          # for FPS tracking
        self._flash_until = 0.0
        self._flash_g = GESTURE_NONE

    def draw(self, frame, recognizer, controller, hand_found, confidence=0.0):
        g     = recognizer.gesture
        now   = time.monotonic()

        self._fps_counter(frame)
        self._debug_panel(frame, g, recognizer, controller, hand_found, confidence, now)
        self._legend(frame)

        # Handle fist exit progress bar
        if g == GESTURE_FIST and recognizer.fist_progress > 0:
            self._exit_bar(frame, recognizer.fist_progress)

        # Trigger flash banner on Zoom gestures
        if g in (GESTURE_OPEN_APP, GESTURE_CLOSE_APP):
            self._flash_until = now + 1.5
            self._flash_g = g
        if now < self._flash_until:
            self._flash_label(frame, self._flash_g)

    def _fps_counter(self, frame):
        now = time.monotonic()
        self._ticks.append(now)
        self._ticks = [t for t in self._ticks if now - t < 1.0]
        fps = len(self._ticks)
        self._put(frame, f"FPS: {fps}", (self._w - 105, 24), scale=0.60,
                  colour=C_GREEN, thickness=1)

    def _debug_panel(self, frame, g, recognizer, controller, hand_found, confidence, now):
        panel_h = 215
        bg = frame.copy()
        cv2.rectangle(bg, (8, 8), (340, 8 + panel_h), C_BLACK, -1)
        cv2.addWeighted(bg, 0.45, frame, 0.55, 0, frame)
        cv2.rectangle(frame, (8, 8), (340, 8 + panel_h), C_GRAY, 1)

        label, colour = _GESTURE_META.get(g, ("...", C_GRAY))
        if not hand_found and len(recognizer._history) == 0:
            label, colour = "No hand", C_GRAY

        # Dynamic Cursor Mode
        if controller.is_paused:
            cursor_mode = "PAUSED (Override)"
            mode_color = C_RED
        elif controller._dragging:
            cursor_mode = "DRAGGING"
            mode_color = C_BLUE
        else:
            cursor_mode = "NORMAL"
            mode_color = C_GREEN

        rows = [
            (f"Cursor Active: {'YES' if not controller.is_paused else 'NO'}", C_GREEN if not controller.is_paused else C_RED),
            (f"Gesture      : {label}", colour),
            (f"Drag Active  : {'ACTIVE' if controller._dragging else 'inactive'}", C_BLUE if controller._dragging else C_GRAY),
            (f"Left Click   : {'ACTIVE' if g == GESTURE_LEFT_CLICK else 'inactive'}", C_YELLOW if g == GESTURE_LEFT_CLICK else C_GRAY),
            (f"Right Click  : {'ACTIVE' if g == GESTURE_RIGHT_CLICK else 'inactive'}", C_ORANGE if g == GESTURE_RIGHT_CLICK else C_GRAY),
            (f"Select       : {'ACTIVE' if g == GESTURE_SELECT else 'inactive'}", C_CYAN if g == GESTURE_SELECT else C_GRAY),
            (f"Open App     : {'DETECTED' if g == GESTURE_OPEN_APP or recognizer.open_detected else 'no'}", C_GREEN if (g == GESTURE_OPEN_APP or recognizer.open_detected) else C_GRAY),
            (f"Close App    : {'DETECTED' if g == GESTURE_CLOSE_APP or recognizer.close_detected else 'no'}", C_RED if (g == GESTURE_CLOSE_APP or recognizer.close_detected) else C_GRAY),
        ]

        for i, (txt, col) in enumerate(rows):
            y = 32 + i * 22
            self._put(frame, txt, (16, y), scale=0.55, colour=col, thickness=1)

    def _legend(self, frame):
        hints = [
            ("Index finger    -> move cursor",  C_GREEN),
            ("Thumb+Index     -> open app",     C_GREEN),
            ("Thumb+Middle    -> close app",    C_RED),
            ("Thumb+Ring      -> left click",   C_YELLOW),
            ("Thumb+Pinky     -> right click",  C_ORANGE),
            ("Thumb+Idx+Mid   -> select",       C_CYAN),
            ("Thumb+Idx+Mid H -> drag mode",    C_BLUE),
            ("Closed Fist (2s)-> EXIT",         C_RED),
        ]
        y0 = self._h - len(hints) * 18 - 10
        for i, (txt, col) in enumerate(hints):
            y = y0 + i * 18
            self._put(frame, txt, (10, y), scale=0.38, colour=col, thickness=1, shadow=True)

    def _exit_bar(self, frame, p):
        bw = self._w - 40
        y  = self._h - 24
        cv2.rectangle(frame, (20, y), (20 + bw, y + 16), C_BLACK, -1)
        cv2.rectangle(frame, (20, y), (20 + int(bw * p), y + 16), C_RED, -1)
        cv2.rectangle(frame, (20, y), (20 + bw, y + 16), C_WHITE, 1)
        
        txt = "VISION MODE EXITING" if p >= 0.95 else f"Exiting {int(p*100)}%"
        self._put(frame, txt, (24, y + 13), scale=0.45, colour=C_WHITE, thickness=1)

    def _flash_label(self, frame, g):
        if g == GESTURE_OPEN_APP:
            label, colour = "OPEN APPLICATION DETECTED", C_GREEN
        elif g == GESTURE_CLOSE_APP:
            label, colour = "CLOSE APPLICATION DETECTED", C_RED
        else:
            return

        tw, th = 400, 50
        x = (self._w - tw) // 2
        y = self._h // 2 - 60
        bg = frame.copy()
        cv2.rectangle(bg, (x - 10, y - 36), (x + tw + 20, y + 14), C_BLACK, -1)
        cv2.addWeighted(bg, 0.5, frame, 0.5, 0, frame)
        self._put(frame, label, (x, y), scale=0.8, colour=colour, thickness=2)

    def _put(self, frame, text, pos, scale=0.55, colour=C_WHITE,
             thickness=1, shadow=True):
        if shadow:
            cv2.putText(frame, text, (pos[0]+1, pos[1]+1), _FONT,
                        scale, C_BLACK, thickness + 1, cv2.LINE_AA)
        cv2.putText(frame, text, pos, _FONT,
                    scale, colour, thickness, cv2.LINE_AA)

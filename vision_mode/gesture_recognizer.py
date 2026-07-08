"""
gesture_recognizer.py
Redesigned gesture classifier with stability filtering and fist exit timing.

Gesture Mapping (single-hand):
  Index finger only        → cursor movement (pointing)
  Thumb + Index pinch      → open (system)
  Thumb + Middle pinch     → close (system)
  Thumb + Ring pinch       → left click
  Thumb + Pinky pinch      → right click
  Thumb + Index + Middle   → select  (hold to enter drag)
  Fist (hold 2s)           → exit vision mode
"""

import math
import time
from .hand_tracker import HandTracker

# ── Labels ────────────────────────────────────────────────────────────
GESTURE_NONE        = "none"
GESTURE_POINT       = "pointing"
GESTURE_LEFT_CLICK  = "left_click"
GESTURE_RIGHT_CLICK = "right_click"
GESTURE_SELECT      = "select"
GESTURE_FIST        = "fist"
GESTURE_DRAG        = "drag"
GESTURE_OPEN_APP    = "open_app"
GESTURE_CLOSE_APP   = "close_app"


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _finger_up(lm, tip, pip, mcp):
    """
    True when fingertip is extended.
    Checks vertical coordinate (tip above PIP) and distance knuckle relation.
    """
    vertical_check = lm[tip][1] < lm[pip][1]  # y is 0 at top
    dist_check = _dist(lm[tip], lm[mcp]) > _dist(lm[pip], lm[mcp])
    return vertical_check or dist_check


def _fingers_up_mask(lm):
    """Return (index_up, middle_up, ring_up, pinky_up)."""
    return (
        _finger_up(lm, HandTracker.INDEX_TIP, 6, HandTracker.INDEX_MCP),
        _finger_up(lm, HandTracker.MIDDLE_TIP, 10, HandTracker.MIDDLE_MCP),
        _finger_up(lm, HandTracker.RING_TIP, 14, HandTracker.RING_MCP),
        _finger_up(lm, HandTracker.PINKY_TIP, 18, HandTracker.PINKY_MCP),
    )


class GestureRecognizer:
    PINCH_THRESH   = 0.038   # tighter threshold to prevent accidental pinches (down from 0.045)
    FIST_HOLD_SEC  = 2.0     # hold duration to trigger exit
    DRAG_HOLD_SEC  = 0.5     # hold duration to enter drag from select
    STABLE_FRAMES  = 5       # more frames to commit gesture (up from 4) for stability

    def __init__(self):
        # Public state
        self.gesture        = GESTURE_NONE
        self.fist_progress  = 0.0
        self.drag_active    = False
        self.open_detected  = False
        self.close_detected = False
        self.zoom_ready     = False   # kept for API compat, not used now

        # Internal single-hand states
        self._fist_start   = 0.0
        self._select_start = 0.0     # timer for select → drag transition
        self._history      = []
        self._stable_raw   = GESTURE_NONE

        # Edge-detection flags for open/close (fire once per gesture)
        self._open_fired   = False
        self._close_fired  = False

    def update(self, tracker: HandTracker) -> str:
        now = time.monotonic()
        self.open_detected = False
        self.close_detected = False

        # ── Single-Hand Gesture Classification ──────────────────────────
        lm = tracker.landmarks
        if not lm:
            self._reset_single_hand()
            self.gesture = GESTURE_NONE
            return self.gesture

        iu, mu, ru, pu = _fingers_up_mask(lm)

        raw = self._classify(tracker, lm, iu, mu, ru, pu)

        # ── Stability filter ──────────────────────────────────────────
        self._history.append(raw)
        if len(self._history) > self.STABLE_FRAMES:
            self._history.pop(0)

        if len(self._history) == self.STABLE_FRAMES and \
                all(g == raw for g in self._history):
            self._stable_raw = raw

        old_gesture = self.gesture
        self.gesture = self._stable_raw

        # ── Edge-detect open / close triggers (fire once per gesture) ──
        if self.gesture == GESTURE_OPEN_APP:
            if not self._open_fired:
                self._open_fired = True
                self.open_detected = True
                print("[VISION] OPEN DETECTED")
        else:
            self._open_fired = False

        if self.gesture == GESTURE_CLOSE_APP:
            if not self._close_fired:
                self._close_fired = True
                self.close_detected = True
                print("[VISION] CLOSE DETECTED")
        else:
            self._close_fired = False

        return self.gesture

    @property
    def exit_triggered(self) -> bool:
        return self.fist_progress >= 1.0

    def _classify(self, tracker, lm, iu, mu, ru, pu) -> str:
        now    = time.monotonic()
        thumb  = tracker.tip(HandTracker.THUMB_TIP)
        index  = tracker.tip(HandTracker.INDEX_TIP)
        middle = tracker.tip(HandTracker.MIDDLE_TIP)
        ring   = tracker.tip(HandTracker.RING_TIP)
        pinky  = tracker.tip(HandTracker.PINKY_TIP)

        pinch_ti = _dist(thumb, index)  < self.PINCH_THRESH   # thumb-index
        pinch_tm = _dist(thumb, middle) < self.PINCH_THRESH   # thumb-middle
        pinch_tr = _dist(thumb, ring)   < self.PINCH_THRESH   # thumb-ring
        pinch_tp = _dist(thumb, pinky)  < self.PINCH_THRESH   # thumb-pinky

        any_pinch = pinch_ti or pinch_tm or pinch_tr or pinch_tp

        # ── Fist exit (only when NO pinch is active) ──────────────────
        #    A true fist has all fingers curled and no thumb contact.
        is_fist = (not iu and not mu and not ru and not pu and not any_pinch)
        if is_fist:
            if self._fist_start == 0.0:
                self._fist_start = now
            self.fist_progress = min(
                (now - self._fist_start) / self.FIST_HOLD_SEC, 1.0
            )
            self._select_start = 0.0
            self.drag_active   = False
            return GESTURE_FIST

        self._fist_start   = 0.0
        self.fist_progress = 0.0

        # ── Select / Drag (thumb + index + middle pinch) ───────────────
        #    Priority: three-finger pinch first, then two-finger pinches
        if pinch_ti and pinch_tm:
            if self._select_start == 0.0:
                self._select_start = now
            if now - self._select_start >= self.DRAG_HOLD_SEC:
                self.drag_active = True
                return GESTURE_DRAG
            self.drag_active = False
            return GESTURE_SELECT

        self._select_start = 0.0
        self.drag_active = False

        # ── Open App (thumb + index pinch only) ────────────────────────
        if pinch_ti and not pinch_tm and not pinch_tr and not pinch_tp:
            return GESTURE_OPEN_APP

        # ── Close App (thumb + middle pinch only) ──────────────────────
        if pinch_tm and not pinch_ti and not pinch_tr and not pinch_tp:
            return GESTURE_CLOSE_APP

        # ── Left Click (thumb + ring pinch) ────────────────────────────
        if pinch_tr and not pinch_ti and not pinch_tm and not pinch_tp:
            return GESTURE_LEFT_CLICK

        # ── Right Click (thumb + pinky pinch) ──────────────────────────
        if pinch_tp and not pinch_ti and not pinch_tm and not pinch_tr:
            return GESTURE_RIGHT_CLICK

        # ── Default: pointing (index finger up) ───────────────────────
        if iu:
            return GESTURE_POINT

        return GESTURE_NONE

    def _reset_single_hand(self):
        self._fist_start   = 0.0
        self.fist_progress = 0.0
        self._select_start = 0.0
        self.drag_active   = False
        self._history      = []
        self._stable_raw   = GESTURE_NONE
        self._open_fired   = False
        self._close_fired  = False
        self.zoom_ready    = False

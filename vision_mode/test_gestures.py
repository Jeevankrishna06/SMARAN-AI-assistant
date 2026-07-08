"""
test_gestures.py
Unit tests for the redesigned GestureRecognizer with new gesture mappings.
No webcam required.

Gesture Mapping Under Test:
  Index finger only        → cursor movement (pointing)
  Thumb + Index pinch      → open app
  Thumb + Middle pinch     → close app
  Thumb + Ring pinch       → left click
  Thumb + Pinky pinch      → right click
  Thumb + Index + Middle   → select (hold → drag)
  Fist (hold 2s)           → exit vision mode
"""

import sys
import time
import os

# Ensure package modules can be imported correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision_mode.gesture_recognizer import (
    GestureRecognizer,
    GESTURE_NONE, GESTURE_POINT,
    GESTURE_LEFT_CLICK, GESTURE_RIGHT_CLICK,
    GESTURE_SELECT, GESTURE_FIST, GESTURE_DRAG,
    GESTURE_OPEN_APP, GESTURE_CLOSE_APP,
)
from vision_mode.hand_tracker import HandTracker

# Joint coordinate constants
MCP_Y  = 0.45
PIP_UP = 0.35
PIP_DN = 0.40
TIP_UP = 0.20
TIP_DN = 0.48


def _lm(thumb_tip=(0.65, 0.50),
        index="folded",
        middle="folded",
        ring="folded",
        pinky="folded"):
    """
    Build a 21-element mock landmark list.
    """
    lm = [(0.50, 0.50, 0.0)] * 21
    
    # Wrist
    lm[HandTracker.WRIST] = (0.50, 0.70, 0.0)
    
    # Thumb
    lm[HandTracker.THUMB_TIP] = (*thumb_tip, 0.0)

    # Fingers configuration
    fingers = {
        "index":  (5, 6, 8),
        "middle": (9, 10, 12),
        "ring":   (13, 14, 16),
        "pinky":  (17, 18, 20),
    }

    states = {
        "index": index,
        "middle": middle,
        "ring": ring,
        "pinky": pinky,
    }

    for name, (mcp, pip, tip) in fingers.items():
        state = states[name]
        if state == "extended":
            lm[mcp] = (0.50, MCP_Y, 0.0)
            lm[pip] = (0.50, PIP_UP, 0.0)
            lm[tip] = (0.50, TIP_UP, 0.0)
        else: # folded
            lm[mcp] = (0.50, MCP_Y, 0.0)
            lm[pip] = (0.50, PIP_DN, 0.0)
            lm[tip] = (0.50, TIP_DN, 0.0)

    return lm


# ── Preset Poses ──────────────────────────────────────────────────────

# All fingers folded, thumb curled to side (not touching any fingertip)
POSE_FIST = _lm(
    thumb_tip=(0.40, TIP_DN),
    index="folded", middle="folded", ring="folded", pinky="folded"
)

# Index finger up only → pointing / cursor movement
POSE_POINT = _lm(
    thumb_tip=(0.65, 0.50),
    index="extended", middle="folded", ring="folded", pinky="folded"
)

# Thumb + Index pinch ONLY → open app
POSE_OPEN_APP = _lm(
    thumb_tip=(0.50, 0.42),
    index="folded", middle="folded", ring="folded", pinky="folded"
)
POSE_OPEN_APP[HandTracker.INDEX_TIP] = (0.52, 0.42, 0.0)

# Thumb + Middle pinch ONLY → close app
POSE_CLOSE_APP = _lm(
    thumb_tip=(0.50, 0.42),
    index="folded", middle="folded", ring="folded", pinky="folded"
)
POSE_CLOSE_APP[HandTracker.MIDDLE_TIP] = (0.51, 0.43, 0.0)

# Thumb + Ring pinch ONLY → left click
POSE_LEFT_CLICK = _lm(
    thumb_tip=(0.50, 0.42),
    index="folded", middle="folded", ring="folded", pinky="folded"
)
POSE_LEFT_CLICK[HandTracker.RING_TIP] = (0.51, 0.43, 0.0)

# Thumb + Pinky pinch ONLY → right click
POSE_RIGHT_CLICK = _lm(
    thumb_tip=(0.50, 0.42),
    index="folded", middle="folded", ring="folded", pinky="folded"
)
POSE_RIGHT_CLICK[HandTracker.PINKY_TIP] = (0.51, 0.43, 0.0)

# Thumb + Index + Middle pinch → select / drag
POSE_SELECT = _lm(
    thumb_tip=(0.50, 0.42),
    index="folded", middle="folded", ring="folded", pinky="folded"
)
POSE_SELECT[HandTracker.INDEX_TIP]  = (0.52, 0.42, 0.0)
POSE_SELECT[HandTracker.MIDDLE_TIP] = (0.51, 0.43, 0.0)


class FakeTracker:
    def __init__(self, landmarks_list):
        self.multi_landmarks = landmarks_list
        self.landmarks = landmarks_list[0] if landmarks_list else []
        self._last_result = None

    def tip(self, lid):
        if not self.landmarks or lid >= len(self.landmarks):
            return (0.5, 0.5)
        return (self.landmarks[lid][0], self.landmarks[lid][1])

    def hand_tip(self, hand_idx, lid):
        if hand_idx >= len(self.multi_landmarks):
            return (0.5, 0.5)
        lms = self.multi_landmarks[hand_idx]
        if lid >= len(lms):
            return (0.5, 0.5)
        return (lms[lid][0], lms[lid][1])


def pump(rec, tracker, n=6):
    """Run updates n times so stability buffer commits gesture."""
    g = GESTURE_NONE
    for _ in range(n):
        g = rec.update(tracker)
    return g


# Test Harness
PASS = FAIL = 0

def check(label, got, expected):
    global PASS, FAIL
    if got == expected:
        print(f"  [PASS]  {label}")
        PASS += 1
    else:
        print(f"  [FAIL]  {label}  ->  expected={expected!r}  got={got!r}")
        FAIL += 1


# ── Test Cases ────────────────────────────────────────────────────────

def test_no_hand():
    print("\n[1] No hand")
    rec = GestureRecognizer()
    tr  = FakeTracker([])
    g   = pump(rec, tr)
    check("Empty landmarks -> none", g, GESTURE_NONE)


def test_pointing():
    print("\n[2] Pointing (cursor movement)")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_POINT])
    g   = pump(rec, tr)
    check("Index extended only -> pointing", g, GESTURE_POINT)


def test_open_app():
    print("\n[3] Open App (Thumb + Index)")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_OPEN_APP])
    g   = pump(rec, tr)
    check("Thumb+Index pinch -> open_app", g, GESTURE_OPEN_APP)


def test_close_app():
    print("\n[4] Close App (Thumb + Middle)")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_CLOSE_APP])
    g   = pump(rec, tr)
    check("Thumb+Middle pinch -> close_app", g, GESTURE_CLOSE_APP)


def test_left_click():
    print("\n[5] Left Click (Thumb + Ring)")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_LEFT_CLICK])
    g   = pump(rec, tr)
    check("Thumb+Ring pinch -> left_click", g, GESTURE_LEFT_CLICK)


def test_right_click():
    print("\n[6] Right Click (Thumb + Pinky)")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_RIGHT_CLICK])
    g   = pump(rec, tr)
    check("Thumb+Pinky pinch -> right_click", g, GESTURE_RIGHT_CLICK)


def test_select():
    print("\n[7] Select (Thumb + Index + Middle)")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_SELECT])
    g   = pump(rec, tr)
    check("Thumb+Index+Middle pinch -> select", g, GESTURE_SELECT)


def test_drag():
    print("\n[8] Drag Mode (Thumb + Index + Middle held)")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_SELECT])
    pump(rec, tr, n=8)

    # Fast-forward select → drag timer
    rec._select_start = time.monotonic() - 0.6
    for _ in range(6):
        g = rec.update(tr)
    check("Select held >=0.5s -> drag", g, GESTURE_DRAG)


def test_fist_exit():
    print("\n[9] Closed Fist Exit")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_FIST])
    g   = pump(rec, tr)
    check("Closed fist -> fist", g, GESTURE_FIST)
    check("Exit not triggered yet", rec.exit_triggered, False)

    # Fast-forward exit timer
    rec._fist_start = time.monotonic() - 2.1
    rec.update(tr)
    check("Exit triggered after 2 seconds", rec.exit_triggered, True)


def test_open_fires_once():
    print("\n[10] Open App fires open_detected only once")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_OPEN_APP])
    pump(rec, tr)
    # open_detected should have been True on the first stable frame
    # Now pump again — should NOT re-fire
    rec.update(tr)
    check("open_detected is False on subsequent frames", rec.open_detected, False)


def test_close_fires_once():
    print("\n[11] Close App fires close_detected only once")
    rec = GestureRecognizer()
    tr  = FakeTracker([POSE_CLOSE_APP])
    pump(rec, tr)
    rec.update(tr)
    check("close_detected is False on subsequent frames", rec.close_detected, False)


if __name__ == "__main__":
    print("=" * 60)
    print("  Vision Mode - Gesture Recognizer Unit Tests")
    print("  New Mapping: Index=cursor, Th+Idx=open, Th+Mid=close,")
    print("  Th+Ring=L-click, Th+Pinky=R-click, Th+Idx+Mid=select/drag")
    print("=" * 60)

    test_no_hand()
    test_pointing()
    test_open_app()
    test_close_app()
    test_left_click()
    test_right_click()
    test_select()
    test_drag()
    test_fist_exit()
    test_open_fires_once()
    test_close_fires_once()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"  {PASS}/{total} passed   {FAIL} failed")
    print("=" * 60)
    sys.exit(0 if FAIL == 0 else 1)

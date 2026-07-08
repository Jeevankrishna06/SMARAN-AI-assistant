"""
hand_tracker.py
MediaPipe hand detection wrapper.
"""

import cv2
import mediapipe as mp


class HandTracker:
    WRIST      = 0
    THUMB_TIP  = 4
    INDEX_TIP  = 8
    INDEX_MCP  = 5
    MIDDLE_TIP = 12
    MIDDLE_MCP = 9
    RING_TIP   = 16
    RING_MCP   = 13
    PINKY_TIP  = 20
    PINKY_MCP  = 17

    def __init__(self, detection_confidence=0.50, tracking_confidence=0.50, model_complexity=0):
        mp_hands = mp.solutions.hands
        self._hands = mp_hands.Hands(
            max_num_hands=2,
            model_complexity=model_complexity,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._draw_utils  = mp.solutions.drawing_utils
        self._draw_styles = mp.solutions.drawing_styles
        self._connections = mp_hands.HAND_CONNECTIONS
        self.landmarks    = []
        self.multi_landmarks = []
        self._last_result = None

    def process(self, frame_bgr) -> bool:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        self._last_result  = self._hands.process(rgb)
        rgb.flags.writeable = True

        self.landmarks = []
        self.multi_landmarks = []

        if self._last_result.multi_hand_landmarks:
            for lms in self._last_result.multi_hand_landmarks:
                pts = [(l.x, l.y, l.z) for l in lms.landmark]
                self.multi_landmarks.append(pts)
            
            # Maintain self.landmarks as first hand for backwards compatibility
            self.landmarks = self.multi_landmarks[0]
            return True

        return False

    def draw(self, frame_bgr):
        if self._last_result and self._last_result.multi_hand_landmarks:
            for lm in self._last_result.multi_hand_landmarks:
                self._draw_utils.draw_landmarks(
                    frame_bgr, lm, self._connections,
                    self._draw_styles.get_default_hand_landmarks_style(),
                    self._draw_styles.get_default_hand_connections_style(),
                )

    def tip(self, lid: int) -> tuple:
        if not self.landmarks or lid >= len(self.landmarks):
            return (0.5, 0.5)
        return (self.landmarks[lid][0], self.landmarks[lid][1])

    def hand_tip(self, hand_idx: int, lid: int) -> tuple:
        if hand_idx >= len(self.multi_landmarks):
            return (0.5, 0.5)
        lms = self.multi_landmarks[hand_idx]
        if lid >= len(lms):
            return (0.5, 0.5)
        return (lms[lid][0], lms[lid][1])

    def release(self):
        self._hands.close()

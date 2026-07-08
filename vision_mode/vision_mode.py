"""
vision_mode.py
Main entry point and execution loop for gesture-based touchless desktop controls.
"""

import threading
import cv2
import time

from .hand_tracker       import HandTracker
from .gesture_recognizer import GestureRecognizer
from .cursor_controller  import CursorController
from .overlay            import Overlay


class VisionMode:
    """
    Gesture-based mouse controller.
    """

    WINDOW = "Vision Mode  |  Q to quit"
    W, H   = 640, 480

    def __init__(self, camera_index: int = 0):
        self._cam_idx = camera_index
        self._running = False
        self._thread  = None

    # ── Public API ────────────────────────────────────────────────────

    def start(self):
        """Blocking start — returns when Vision Mode exits."""
        self._running = True
        self._run()

    def start_async(self):
        """Non-blocking start — returns immediately."""
        if self._thread and self._thread.is_alive():
            print("[VisionMode] Already running.")
            return
        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal Vision Mode to shut down and wait for cleanup."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=4)

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Internal ──────────────────────────────────────────────────────

    def _run(self):
        cap = cv2.VideoCapture(self._cam_idx)
        if not cap.isOpened():
            print(f"[VisionMode] ERROR: Cannot open camera {self._cam_idx}")
            self._running = False
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.H)
        cap.set(cv2.CAP_PROP_FPS, 60)

        tracker    = HandTracker(model_complexity=0)
        recognizer = GestureRecognizer()
        controller = CursorController()
        overlay    = Overlay(self.W, self.H)

        # Threading state variables for async inference
        latest_frame = None
        frame_lock = threading.Lock()

        landmarks_result = []
        multi_landmarks_result = []
        last_result_result = None
        hand_found_result = False
        result_lock = threading.Lock()

        # Background thread to run HandTracker process asynchronously
        def inference_worker():
            worker_tracker = HandTracker(model_complexity=0)
            while self._running:
                frame_to_process = None
                with frame_lock:
                    if latest_frame is not None:
                        frame_to_process = latest_frame.copy()
                
                if frame_to_process is None:
                    time.sleep(0.002)
                    continue

                found = worker_tracker.process(frame_to_process)

                with result_lock:
                    nonlocal hand_found_result, landmarks_result, multi_landmarks_result, last_result_result
                    hand_found_result = found
                    landmarks_result = list(worker_tracker.landmarks) if worker_tracker.landmarks else []
                    multi_landmarks_result = list(worker_tracker.multi_landmarks) if worker_tracker.multi_landmarks else []
                    last_result_result = worker_tracker._last_result

                # Prevent CPU lock
                time.sleep(0.001)

            worker_tracker.release()

        worker_thread = threading.Thread(target=inference_worker, daemon=True)
        worker_thread.start()

        print("[VisionMode] Started — show your hand(s) to the camera.")
        cv2.namedWindow(self.WINDOW, cv2.WINDOW_NORMAL)
        
        # Scaling & Repositioning: Top-right corner, 480x360
        import pyautogui
        screen_w, screen_h = pyautogui.size()
        win_w, win_h = 480, 360
        cv2.resizeWindow(self.WINDOW, win_w, win_h)
        cv2.moveWindow(self.WINDOW, screen_w - win_w - 20, 40)

        # Auto-minimize all other windows to focus on Vision Mode
        try:
            import win32gui
            import win32con
            # Give the OS time to register the OpenCV window
            time.sleep(0.5)
            vision_hwnd = win32gui.FindWindow(None, self.WINDOW)

            # System/shell window classes that must not be minimized
            SKIP_CLASSES = {
                "Shell_TrayWnd", "Progman", "WorkerW",
                "Shell_SecondaryTrayWnd", "DV2ControlHost",
                "Windows.UI.Core.CoreWindow", "ApplicationFrameWindow",
                "MultitaskingViewFrame", "ForegroundStaging",
                "TaskManagerWindow", "NotifyIconOverflowWindow",
            }

            minimized_count = 0

            def enum_handler(hwnd, _):
                nonlocal minimized_count
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return
                    if hwnd == vision_hwnd:
                        return
                    title = win32gui.GetWindowText(hwnd)
                    if not title:
                        return
                    class_name = win32gui.GetClassName(hwnd)
                    if class_name in SKIP_CLASSES:
                        return
                    if win32gui.IsIconic(hwnd):
                        return
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    minimized_count += 1
                except Exception:
                    pass  # Skip windows that refuse to be minimized

            win32gui.EnumWindows(enum_handler, None)
            print(f"[VisionMode] Minimized {minimized_count} windows.")
        except Exception as e:
            print(f"[VisionMode] Error minimizing windows: {e}")

        try:
            while self._running:
                ok, frame = cap.read()
                if not ok:
                    continue

                # Mirror webcam feed naturally
                frame = cv2.flip(frame, 1)

                # Feed new frame to background worker
                with frame_lock:
                    latest_frame = frame

                # Read tracking results from background thread safely
                with result_lock:
                    tracker.landmarks = landmarks_result
                    tracker.multi_landmarks = multi_landmarks_result
                    tracker._last_result = last_result_result
                    hand_found = hand_found_result

                # ── Core pipeline ──────────────────────────────────────
                recognizer.update(tracker)

                # Read hand confidence if available
                confidence = 0.0
                if (hand_found
                        and tracker._last_result
                        and tracker._last_result.multi_handedness):
                    try:
                        confidence = tracker._last_result \
                            .multi_handedness[0].classification[0].score
                    except (IndexError, AttributeError):
                        confidence = 0.0

                if hand_found:
                    tracker.draw(frame)
                    controller.update(tracker, recognizer)

                # ── HUD ────────────────────────────────────────────────
                overlay.draw(frame, recognizer, controller, hand_found, confidence)

                cv2.imshow(self.WINDOW, frame)
                
                # Prevent CPU lock and main thread starvation
                time.sleep(0.001)

                # ── Exit conditions ────────────────────────────────────
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27) or recognizer.exit_triggered:
                    if recognizer.exit_triggered:
                        print("[VISION]\nEXITING")
                        # Allow 1 frame to draw the final banner/progress
                        overlay.draw(frame, recognizer, controller, hand_found, confidence)
                        cv2.imshow(self.WINDOW, frame)
                        cv2.waitKey(100)
                    break

        finally:
            # Ensure drag is released cleanly on exit
            if controller._dragging:
                import pyautogui
                pyautogui.mouseUp(button="left")

            cap.release()
            tracker.release()
            cv2.destroyWindow(self.WINDOW)
            self._running = False
            print("[VisionMode] Stopped cleanly.")

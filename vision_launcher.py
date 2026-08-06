import sys
import time
from vision_mode import VisionMode

def main():
    print("[VISION_LAUNCHER] Initializing Vision Mode...")
    try:
        vm = VisionMode()
        vm.start()
    except Exception as e:
        print(f"[VISION_LAUNCHER] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
#explain how vision mode works- Vision Mode is a feature that allows a system to process and interpret visual data from cameras or other imaging devices. It typically involves several key components:
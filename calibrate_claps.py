import time
import clap_detector
import speech_recognition as sr

def main():
    print("========================================")
    print("  CLAP CALIBRATION MODE  ")
    print("========================================")
    print("Instructions:")
    print("1. Clap near your microphone.")
    print("2. Observe the printed metrics.")
    print("3. Try coughing, typing, or speaking loudly to see their metrics.")
    print("4. Press Ctrl+C to exit.")
    print("----------------------------------------")
    
    # Enable calibration printouts inside the module
    clap_detector.CALIBRATION_MODE = True
    
    # We will use BufferedMicSource just to run the background loop and print stats
    r = sr.Recognizer()
    try:
        with clap_detector.BufferedMicSource() as source:
            print("Microphone active. Listening...")
            # Just keep the main thread alive while the background thread does the work
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting calibration mode.")

if __name__ == "__main__":
    main()

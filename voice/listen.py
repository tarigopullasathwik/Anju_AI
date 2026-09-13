# pyrefly: ignore [missing-import]
import speech_recognition as sr
import time

# ==========================================
# GLOBAL SPEAKING STATE
# ==========================================

# This prevents Anju from hearing itself
is_speaking = False


def set_speaking(state: bool):
    """
    Update speaking state from TTS engine.
    True  = Anju is speaking
    False = Anju finished speaking
    """
    global is_speaking
    is_speaking = state


# ==========================================
# SHARED RECOGNIZER
# ==========================================

_recognizer = sr.Recognizer()

# Voice sensitivity tuning
_recognizer.energy_threshold = 500
_recognizer.dynamic_energy_threshold = True

# Faster response timing
_recognizer.pause_threshold = 0.5
_recognizer.non_speaking_duration = 0.4


# ==========================================
# LISTEN FUNCTION
# ==========================================

def listen() -> str:
    """
    Fast microphone listener with:
    - self-loop prevention
    - noise handling
    - fast response
    """

    global is_speaking

    # ======================================
    # PREVENT SELF LISTENING
    # ======================================

    if is_speaking:
        return ""

    try:
        microphone = sr.Microphone()
    except (AttributeError, OSError) as e:
        print(f"[Mic] Microphone unavailable: {e}")
        return ""

    try:
        with microphone as source:
            # Small ambient calibration
            _recognizer.adjust_for_ambient_noise(
                source,
                duration=0.2
            )

            print("[Mic] Listening...")

            # Capture audio
            audio = _recognizer.listen(
                source,
                timeout=2,
                phrase_time_limit=10
            )

            print("[Mic] Processing...")

            # Google Speech Recognition
            text = _recognizer.recognize_google(audio)

            if text:

                cleaned_text = text.strip()

                print(f"[Mic] Captured: {cleaned_text}")

                # Ignore tiny accidental sounds
                if len(cleaned_text) < 2:
                    return ""

                return cleaned_text

            return ""

    # ----------------------------------
    # Speech not understood
    # ----------------------------------

    except sr.UnknownValueError:
        return ""

    # ----------------------------------
    # API / internet issue
    # ----------------------------------

    except sr.RequestError as e:
        print(f"[Mic] API Service Error: {e}")

        # Prevent rapid retries
        time.sleep(2)

        return ""

    # ----------------------------------
    # No speech detected
    # ----------------------------------

    except sr.WaitTimeoutError:
        return ""

    # ----------------------------------
    # Any other issue
    # ----------------------------------

    except Exception as e:
        print(f"[Mic] Error: {e}")

        time.sleep(1)

        return ""

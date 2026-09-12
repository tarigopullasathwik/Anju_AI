"""
Anju AI — Wake Word Detector
Listens in the background for "hey anju" and fires a callback when detected.
Connect to main.py if you want hands-free voice activation.
"""
# pyrefly: ignore [missing-import]
import speech_recognition as sr
import time

# Import the listen module itself so we read is_speaking as a live attribute,
# not as a snapshot boolean captured at import time.
try:
    import voice.listen as _listen_mod
except ImportError:
    import listen as _listen_mod  # fallback when running the file directly


class WakeWordDetector:

    def __init__(self, wake_word="hey anju", on_wake=None):
        self.wake_word = wake_word.lower()
        self.on_wake = on_wake
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.stop_listening = None
        self.last_trigger_time = 0
        self.cooldown = 3  # seconds between triggers

        # Tuned thresholds for background listening
        self.recognizer.energy_threshold = 500
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.5

    def _callback(self, recognizer, audio):
        # Read is_speaking live from the module — not a stale import-time snapshot
        if _listen_mod.is_speaking:
            return

        try:
            text = recognizer.recognize_google(audio).lower().strip()
            if not text:
                return

            print(f"[WakeWord] Heard: {text}")

            if self.wake_word in text:
                now = time.time()
                if now - self.last_trigger_time < self.cooldown:
                    return  # still in cooldown
                self.last_trigger_time = now
                print(f"[WakeWord] Triggered: '{text}'")
                if self.on_wake:
                    self.on_wake()

        except sr.UnknownValueError:
            pass  # audio not understood — normal background noise
        except sr.RequestError as e:
            print(f"[WakeWord] STT API error: {e}")
        except Exception as e:
            print(f"[WakeWord] Error: {e}")

    def start(self):
        """Start background wake-word listening."""
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        self.stop_listening = self.recognizer.listen_in_background(
            self.microphone, self._callback
        )
        print(f"[WakeWord] Listening for '{self.wake_word}'...")

    def stop(self):
        """Stop background wake-word listening."""
        if self.stop_listening:
            self.stop_listening(wait_for_stop=False)
            print("[WakeWord] Stopped.")


def listen_for_wake_word(wake_word: str = "hey anju") -> bool:
    """Legacy compatibility stub — always returns False."""
    return False

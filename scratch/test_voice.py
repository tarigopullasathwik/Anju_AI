import sys
import os

# Resolve paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.tts import generate_tts_base64

def test_tts():
    print("Testing OpenAI TTS generation...")
    try:
        audio_b64 = generate_tts_base64("Yes, Sathwik... I am fully operational and upgraded.", "neutral")
        if audio_b64:
            print("SUCCESS: Base64 audio generated successfully!")
            print(f"Base64 length: {len(audio_b64)} characters.")
            print(f"Preview: {audio_b64[:60]}...")
        else:
            print("WARNING: Base64 audio returned None. Falling back to browser TTS.")
    except Exception as e:
        print(f"ERROR: Exception occurred: {e}")

if __name__ == "__main__":
    test_tts()

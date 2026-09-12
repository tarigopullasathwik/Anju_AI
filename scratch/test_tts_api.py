"""Test OpenAI TTS API to find what works."""
import os
import sys
import base64

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.helpers import get_api_key

api_key = get_api_key("OPENAI_API_KEY")
if not api_key:
    print("FAIL: No API key found")
    sys.exit(1)

print(f"API Key found: {api_key[:20]}...")
print(f"API Key length: {len(api_key)}")

from openai import OpenAI
import httpx

client = OpenAI(api_key=api_key, http_client=httpx.Client(timeout=30.0))

test_text = "Hello Sathwik. I am Anju, your personal AI companion. How are you feeling today?"

models_to_test = [
    "tts-1-hd",
    "gpt-4o-mini-tts",
    "tts-1",
]

voices_to_test = ["alloy", "nova", "shimmer", "ash", "echo", "fable"]

# Test each model with alloy voice
for model in models_to_test:
    print(f"\n--- Testing model: {model} ---")
    try:
        response = client.audio.speech.create(
            model=model,
            voice="alloy",
            input=test_text,
            speed=0.92
        )
        audio_len = len(response.content)
        print(f"  SUCCESS: audio size = {audio_len} bytes")

        # Try with instructions if it's gpt-4o-mini-tts
        if "gpt-4o" in model:
            try:
                response2 = client.audio.speech.create(
                    model=model,
                    voice="alloy",
                    input=test_text,
                    instructions="Speak in a warm, calm, and peaceful tone.",
                    speed=0.92
                )
                print(f"  With instructions: SUCCESS, audio = {len(response2.content)} bytes")
            except Exception as e:
                print(f"  With instructions: FAILED - {e}")
    except Exception as e:
        print(f"  FAILED: {e}")

# Test different voices with tts-1-hd
print(f"\n--- Voice comparison with tts-1-hd ---")
for voice in voices_to_test:
    try:
        response = client.audio.speech.create(
            model="tts-1-hd",
            voice=voice,
            input="Hello, I am testing this voice for clarity and warmth.",
            speed=0.92
        )
        print(f"  Voice '{voice}': OK ({len(response.content)} bytes)")
    except Exception as e:
        print(f"  Voice '{voice}': FAILED - {e}")

print("\n--- Test complete ---")

import sys
import os

# Resolve paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.helpers import get_api_key
from google import genai

def test_gemini():
    print("Testing Gemini API validation...")
    gemini_key = get_api_key("GEMINI_API_KEY")
    print(f"Loaded key: {gemini_key[:12]}...")

    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'System online!'"
        )
        print(f"SUCCESS: Gemini response: {response.text.strip()}")
    except Exception as e:
        print(f"ERROR: Gemini verification failed: {e}")

if __name__ == "__main__":
    test_gemini()

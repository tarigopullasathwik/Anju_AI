import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    print("Available Models:")
    # The new SDK might have a different way to list models
    # Let's try to list models if possible, or just test a few
    for model in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.0-pro-exp-02-05"]:
        try:
            print(f"Testing {model}...")
            res = client.models.generate_content(model=model, contents="Hi")
            print(f"  {model} OK: {res.text[:20]}...")
        except Exception as e:
            print(f"  {model} ERROR: {e}")
except Exception as e:
    print(f"Global Error: {e}")

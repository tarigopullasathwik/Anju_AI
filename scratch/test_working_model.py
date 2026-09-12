import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    for model in ["gemini-flash-latest", "gemini-2.0-flash", "gemini-3-flash-preview"]:
        try:
            print(f"Testing {model}...")
            res = client.models.generate_content(model=model, contents="Hi")
            print(f"  {model} OK: {res.text[:20]}...")
            break
        except Exception as e:
            print(f"  {model} ERROR: {e}")
except Exception as e:
    print(f"Global Error: {e}")

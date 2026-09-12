import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    print("Listing Models...")
    # List models to see what's actually available
    models = client.models.list()
    for m in models:
        print(f"Model: {m.name} (DisplayName: {m.display_name})")
except Exception as e:
    print(f"Error listing models: {e}")

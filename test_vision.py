import os, requests, base64
import dotenv
dotenv.load_dotenv()

openrouter_key = os.getenv("OPENROUTER_API_KEY")
url = "https://openrouter.ai/api/v1/chat/completions"
headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}

img_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="

payload = {
    "model": "google/gemini-2.5-flash",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is this image?"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
            ]
        }
    ]
}

try:
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    print("Status:", r.status_code)
    print("Response:", r.text[:300])
except Exception as e:
    print("Error:", e)

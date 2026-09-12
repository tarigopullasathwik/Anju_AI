import os
import base64
import requests

def analyze_image_with_vision(image_path: str, prompt: str = "Analyze this image in detail.") -> str:
    """
    Takes an image file path and uses OpenRouter (Gemini-2.5-Flash) to analyze the contents.
    Provides powerful multimodal vision capabilities to Anju AI.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return "Error: OPENROUTER_API_KEY is not configured in the environment."

    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path):
        return f"Error: Image file does not exist at '{abs_path}'."

    try:
        # Load and encode image to base64 string
        with open(abs_path, 'rb') as f:
            image_data = f.read()

        # Extract extension to identify mime type
        ext = os.path.splitext(abs_path)[1].lower().replace(".", "")
        mime_type = f"image/{ext}"
        if ext in ("jpg", "jpeg"):
            mime_type = "image/jpeg"
        elif ext == "png":
            mime_type = "image/png"
        elif ext == "webp":
            mime_type = "image/webp"
        elif ext == "gif":
            mime_type = "image/gif"
        
        b64_string = base64.b64encode(image_data).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{b64_string}"

        print(f"[Vision] Triggering multimodal vision analysis on {abs_path}...")
        
        openrouter_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "google/gemini-2.5-flash",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}}
                    ]
                }
            ]
        }

        resp = requests.post(f"{openrouter_url.rstrip('/')}/chat/completions", json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        
        result_json = resp.json()
        return result_json.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

    except Exception as e:
        return f"Error performing vision analysis: {e}"

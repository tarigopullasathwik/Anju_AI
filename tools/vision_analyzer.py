import os
import base64
from google import genai

def analyze_image_with_vision(image_path: str, prompt: str = "Analyze this image in detail.") -> str:
    """
    Takes an image file path and uses Gemini-2.0-Flash to analyze the contents.
    Provides powerful multimodal vision capabilities to Anju AI.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return "Error: GEMINI_API_KEY is not configured in the environment."

    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path):
        return f"Error: Image file does not exist at '{abs_path}'."

    try:
        # Load and encode image to inline data bytes
        with open(abs_path, 'rb') as f:
            image_data = f.read()

        # Extract extension to identify mime type
        ext = os.path.splitext(abs_path)[1].lower().replace(".", "")
        mime_type = f"image/{ext}"
        if ext == "jpg" or ext == "jpeg":
            mime_type = "image/jpeg"
        elif ext == "png":
            mime_type = "image/png"
        elif ext == "webp":
            mime_type = "image/webp"
        elif ext == "gif":
            mime_type = "image/gif"

        client = genai.Client(api_key=api_key)

        # Prepare contents using standard google-genai schema:
        # Pass a list containing the prompt string and the base64 part dictionary
        contents = [
            prompt,
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(image_data).decode('utf-8')
                }
            }
        ]

        print(f"[Vision] Triggering multimodal vision analysis on {abs_path}...")
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=contents
        )
        return response.text

    except Exception as e:
        return f"Error performing vision analysis: {e}"

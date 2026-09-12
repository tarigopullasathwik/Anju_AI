import os
import urllib.request
import urllib.parse
import time
import random

# All generated images land in output/ instead of the project root
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

def generate_image(prompt: str, output_filename: str = None) -> str:
    """
    Generate an image using a free high-quality AI image generation API
    (Pollinations.ai / Flux model, no API key required).
    Saves to output/ and returns the relative path.
    """
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 1. Sanitize prompt
        if not prompt or len(prompt.strip()) < 2:
            prompt = "A beautiful AI generated 8k masterpiece"
        safe_prompt = urllib.parse.quote(prompt.strip())

        # 2. Setup Filename — always saved inside output/
        if not output_filename:
            timestamp = int(time.time())
            output_filename = f"generated_image_{timestamp}_{random.randint(1000, 9999)}.png"
        output_path = os.path.join(OUTPUT_DIR, os.path.basename(output_filename))

        # 3. Generate Seed and Model URL
        seed = random.randint(1, 1000000000)
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true&model=flux&seed={seed}"

        # 4. Request with User-Agent
        req = urllib.request.Request(
            image_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )

        # 5. Download
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
            with open(output_path, 'wb') as out_file:
                out_file.write(data)

        # Return a URL-friendly relative path for the dashboard to serve
        return f"output/{os.path.basename(output_path)}"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error generating image: {str(e)}"

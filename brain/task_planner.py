import os
import re
import json

from tools.pdf_generator import generate_pdf
from tools.image_generator import generate_image
from tools.web_search import search_web
from automation.app_control import open_application
from automation.system_tasks import shutdown_system
from memory.memory import remember_fact, get_memory
from tools.cyber_tools import port_scanner, url_detector
from tools.camera import take_picture
from utils.api_handler import APIHandler


# ─────────────────────────────────────────────────────────────────────────────
# KEYWORD FALLBACK: catches commands even when Gemini is unavailable or
# returns an uncertain result. Patterns are intentionally broad.
# ─────────────────────────────────────────────────────────────────────────────
_PATTERNS = [
    # Open / launch / start / run an app
    {
        "action": "open_app",
        "regex": re.compile(
            r"\b(open|launch|start|run|load|execute|fire up|bring up|switch to|go to)\b.+",
            re.IGNORECASE
        ),
        "extract": lambda m: {"app_name": re.sub(
            r"^(open|launch|start|run|load|execute|fire up|bring up|switch to|go to)\s+(the\s+|an?\s+)?",
            "", m, flags=re.IGNORECASE
        ).strip()}
    },
    # Web search
    {
        "action": "web_search",
        "regex": re.compile(
            r"\b(search|look up|google|find|browse|lookup|tell me about|what is|who is|where is|when is|how (to|do|does|did|can|much|many))\b",
            re.IGNORECASE
        ),
        "extract": lambda m: {"query": m.strip()}
    },
    # Generate PDF / document / report
    {
        "action": "generate_pdf",
        "regex": re.compile(
            r"\b(create|generate|make|write|produce|draft)\b.*(pdf|document|report|file|letter|essay|note)",
            re.IGNORECASE
        ),
        "extract": lambda m: {"title": "Generated Document", "content": m, "filename": "document.pdf"}
    },
    # Generate image / picture / photo / art
    {
        "action": "generate_image",
        "regex": re.compile(
            r"\b(generate|create|make|draw|design|produce|paint)\b.*(image|picture|photo|art|illustration|graphic|wallpaper)",
            re.IGNORECASE
        ),
        "extract": lambda m: {"prompt": m.strip()}
    },
    # Take picture / capture / screenshot
    {
        "action": "take_picture",
        "regex": re.compile(
            r"\b(take|capture|snap|shoot|click|grab)\b.*(picture|photo|selfie|screenshot|image|pic)",
            re.IGNORECASE
        ),
        "extract": lambda m: {}
    },
    # Remember / save / store / note
    {
        "action": "remember",
        "regex": re.compile(
            r"\b(remember|note|save|store|keep in mind|note down|don't forget|keep note)\b",
            re.IGNORECASE
        ),
        "extract": lambda m: {}
    },
    # Recall / what do you know / do you remember
    {
        "action": "knowledge_retrieval",
        "regex": re.compile(
            r"\b(recall|what do you know|do you remember|retrieve|tell me what you know|what did i tell you|give me info)\b",
            re.IGNORECASE
        ),
        "extract": lambda m: {"subject": m.strip()}
    },
    # Port scan
    {
        "action": "port_scan",
        "regex": re.compile(
            r"\b(scan|check)\b.*(port|ports|open services|network)\b",
            re.IGNORECASE
        ),
        "extract": lambda m: {"host": _extract_host(m)}
    },
    # URL check / phishing check
    {
        "action": "url_check",
        "regex": re.compile(
            r"\b(check|verify|scan|analyse|analyze|is it safe|is this safe)\b.*(url|link|website|site|domain)",
            re.IGNORECASE
        ),
        "extract": lambda m: {"url": _extract_url(m)}
    },
    # Shutdown / power off / turn off computer
    {
        "action": "shutdown",
        "regex": re.compile(
            r"\b(shutdown|shut down|power off|turn off|restart)\b.*(computer|pc|system|laptop|machine)?",
            re.IGNORECASE
        ),
        "extract": lambda m: {"delay": _extract_delay(m)}
    },
]

def _extract_host(text: str) -> str:
    match = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3}|localhost|[\w.-]+\.\w{2,})\b", text)
    return match.group(1) if match else "localhost"

def _extract_url(text: str) -> str:
    match = re.search(r"https?://\S+|www\.\S+|[\w-]+\.\w{2,}\S*", text)
    return match.group(0) if match else text.strip()

def _extract_delay(text: str) -> int:
    match = re.search(r"\b(\d+)\s*(second|minute|min|sec|s|m)\b", text, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        unit = match.group(2).lower()
        return val * 60 if "min" in unit or unit == "m" else val
    return 60

def _keyword_fallback(user_input: str) -> list[dict]:
    """Try to match user input against keyword patterns. Returns a list of plan dicts."""
    text = user_input.strip()

    # Split by " and " or " then " but be careful not to split inside quotes if any
    # For simplicity, we just split by " and " and " then "
    sub_tasks = re.split(r'\b(?:and|then)\b', text, flags=re.IGNORECASE)

    plans = []
    for task in sub_tasks:
        task = task.strip()
        if not task:
            continue

        matched = False
        for pattern in _PATTERNS:
            if pattern["regex"].search(task):
                plans.append({
                    "action": pattern["action"],
                    "params": pattern["extract"](task)
                })
                matched = True
                break

    return plans if plans else [{"action": "chat", "params": {}}]


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTE TASK
# ─────────────────────────────────────────────────────────────────────────────
def execute_task(user_prompt: str, action: str, params: dict) -> str:
    """
    Executes a specific tool or automation based on the planner's output.
    """
    if action == "generate_pdf":
        title    = params.get("title", "Generated Document")
        content  = params.get("content", "This is an auto-generated PDF from your request.")
        filename = params.get("filename", "generated_doc.pdf")
        path = generate_pdf(title, content, filename)
        return f"I have generated the PDF document and saved it as {path}."

    elif action == "generate_image":
        prompt = params.get("prompt", "A beautiful AI generated image")
        path = generate_image(prompt)
        if path.startswith("Error"):
            return path
        return f"I have created the image. It is saved at {path}."

    elif action == "take_picture":
        path = take_picture()
        if path.startswith("Error"):
            return path
        return f"I have taken a picture and saved it to {path}."

    elif action == "web_search":
        query = params.get("query", user_prompt)
        if not query:
            return "What would you like me to search for?"

        # Automatically open browser to show visual results
        import urllib.parse
        import webbrowser
        safe_query = urllib.parse.quote(query)
        webbrowser.open(f"https://www.google.com/search?q={safe_query}")

        results = search_web(query)
        if "Error" in results or "No results" in results:
            return f"I have opened a web search for: {query}"

        return f"I have opened a web search for '{query}'. Quick summary: {results[:500]}..."

    elif action == "open_app":
        app_name = params.get("app_name", "")
        # If Gemini returned empty app_name, try to extract it ourselves
        if not app_name:
            app_name = re.sub(
                r"^(open|launch|start|run|load|execute|fire up|bring up|switch to|go to)\s+(the\s+|an?\s+)?",
                "", user_prompt, flags=re.IGNORECASE
            ).strip()
        return open_application(app_name)

    elif action == "remember":
        return remember_fact(user_prompt)

    elif action == "knowledge_retrieval":
        subject = params.get("subject", user_prompt)
        return get_memory(subject)

    elif action == "port_scan":
        host = params.get("host", "localhost")
        return port_scanner(host)

    elif action == "url_check":
        url = params.get("url", "")
        return url_detector(url)

    elif action == "shutdown":
        delay = params.get("delay", 60)
        return shutdown_system(int(delay))

    elif action == "chat":
        return ""

    return "I am not sure how to perform that action yet."


# ─────────────────────────────────────────────────────────────────────────────
# PLAN TASK — Gemini first, keyword fallback second
# ─────────────────────────────────────────────────────────────────────────────
def plan_task(user_input: str) -> list[dict]:
    """
    Uses Gemini to determine the required actions, with a robust keyword-based
    fallback so commands still work even when Gemini is unclear or unavailable.
    Returns a list of task objects (even for single tasks).
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        # No API key → use keyword fallback only
        return _keyword_fallback(user_input)

    from google import genai  # lazy import — only needed when API key is present
    client = genai.Client(api_key=api_key)

    # Escape user input for the prompt to avoid JSON issues
    safe_user_input = user_input.replace('"', '\\"')

    prompt = """
You are the Task Planner for an AI assistant named Anju running on Windows.
Analyze the user's input and determine the required actions. The user might ask for multiple things at once.
Return ONLY a raw JSON array of objects — no markdown, no extra text.

Structure:
[
    {
        "action": "<action>",
        "params": {}
    },
    ...
]

Available actions and when to use them:
- "open_app"            → user wants to open, launch, start, run, or switch to any application, browser, software, or website. Set params: {"app_name": "<extracted app or site name>"}
- "web_search"          → user asks for REAL-TIME or EXTERNAL information REQUIRED (e.g. news, weather).
- "generate_pdf"        → user wants to create a document or report.
- "generate_image"      → user wants an image, art, or picture.
  IMPORTANT: You MUST expand the user's simple request into a highly detailed, professional, and cinematic prompt.
  Focus on: lighting (volumetric), textures (hyper-realistic, 8k), and style (photorealistic, digital art, oil painting).
  Example: If user says "a dragon", you set params: {"prompt": "A majestic gold-scaled dragon perched on a snowy mountain peak at sunset, fiery breath illuminating the falling snow, volumetric lighting, hyper-realistic textures, 8k resolution, cinematic composition."}
- "chat"                → Default for general conversation, questions, greetings, or when no other tool is relevant. Be witty, helpful, and charming!
- "take_picture"        → user wants to take a photo or capture a camera frame.
- "remember"            → user says to remember something.
- "knowledge_retrieval" → user asks what you know or recalls a fact.
- "port_scan"           → user wants to scan a host.
- "url_check"           → user wants to verify a link safety.
- "shutdown"            → user wants to shut down or restart.

Important rules:
- NEVER use web_search for personal questions ("who am I").
- Extract exact app/website names.
- For image generation, always be highly descriptive and creative in the 'prompt' parameter.

User Input: "{{USER_INPUT}}"
""".replace("{{USER_INPUT}}", safe_user_input)

    # 1. Try Cache First for planning (short TTL)
    cache_key = f"task_plan_{user_input}"
    cached = APIHandler.get_cache(cache_key, ttl_hours=2)
    if cached:
        try:
            print(f"[Planner] From Cache: {user_input[:20]}")
            return json.loads(cached)
        except: pass

    try:
        # 2. Use APIHandler for robust calling with backoff
        content, err = APIHandler.call_gemini_with_backoff(
            client, "gemini-2.0-flash", prompt
        )

        if err:
            print(f"Task Planning Error: {err} — falling back to keyword matching")
            return _keyword_fallback(user_input)

        # Strip any accidental markdown fences
        content = re.sub(r"```[a-z]*\n?", "", content).replace("```", "").strip()
        data = json.loads(content)

        # Ensure it's a list
        if isinstance(data, dict):
            tasks = [data]
        elif isinstance(data, list):
            tasks = data
        else:
            tasks = [{"action": "chat", "params": {}}]

        # Sanity check: if Gemini says open_app but gave no app_name, recover it
        for task in tasks:
            action = task.get("action", "chat")
            params = task.get("params", {})
            if action == "open_app" and not params.get("app_name"):
                params["app_name"] = re.sub(
                    r"^(open|launch|start|run|load|fire up|bring up|switch to|go to)\s+(the\s+|an?\s+)?",
                    "", user_input, flags=re.IGNORECASE
                ).strip()

        # Cache the valid plan
        APIHandler.set_cache(cache_key, json.dumps(tasks))
        return tasks

    except Exception as e:
        print(f"Task Planning Logic Error: {e} — falling back to keyword matching")
        return _keyword_fallback(user_input)

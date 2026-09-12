"""
Anju AI — Local Intelligence Engine
Provides offline-capable intelligence for simple queries, pattern matching,
and smart routing between local and cloud processing.
"""
import os
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional


# ── Local Knowledge Base ────────────────────────────────────────────────────
# These are high-accuracy patterns that can be answered without any API call.

_KNOWLEDGE_BASE = {
    # Technical Facts
    (r"(what|tell me about)\s+(python|py)", "tech"): (
        "Python is a high-level, interpreted programming language created by Guido van Rossum. "
        "It emphasizes readability and simplicity. You use it extensively for Anju AI, Sathwik."
    ),
    (r"(what is|explain)\s+(ai|artificial intelligence)", "tech"): (
        "Artificial Intelligence is the simulation of human intelligence by machines. "
        "I'm an example of AI in action, Sathwik — I use natural language processing "
        "and machine learning to understand and help you."
    ),
    (r"(what is|explain)\s+(machine learning|ml)", "tech"): (
        "Machine Learning is a subset of AI where systems learn from data patterns "
        "without being explicitly programmed for every scenario. It powers how I understand you better over time."
    ),
    (r"(what is|explain)\s+(deep learning|neural network)", "tech"): (
        "Deep Learning uses multi-layered neural networks inspired by the human brain "
        "to process complex patterns in data. Models like Gemini use deep learning "
        "to have natural conversations."
    ),

    # Anju-specific Knowledge
    (r"what (can|does) anju (do|know)", "anju"): (
        "I can do so much, Sathwik! I can search the web, generate images and PDFs, "
        "control apps on your PC, take webcam photos, analyze images, run code, "
        "remember facts, manage tasks and projects, control your Android phone, "
        "execute multi-step workflows, and adapt my personality to your mood. "
        "And I'm always learning new capabilities through my plugin system."
    ),
    (r"(how were you|how are you )? (built|made|created|programmed)", "anju"): (
        "I was built by you, Sathwik — using Python, with Google Gemini as my brain, "
        "Flask for my web interface, SQLite for my memory, and a lot of thoughtful engineering. "
        "My architecture includes a local sentry layer, emotion engine, memory system, "
        "and now a full plugin ecosystem."
    ),

    # Programming Help
    (r"(how to|how do i)\s+(code|program|write)\s+(in\s+)?python", "coding"): (
        "To write Python, Sathwik: start with `print('Hello World')`. Use variables without declaring types, "
        "functions with `def`, and import modules with `import`. For Anju-level projects, "
        "organize code into modules, use classes for state, and always handle exceptions gracefully."
    ),
    (r"what('s| is) (a )?(variable|function|class|loop|list|dict)", "coding"): (
        "In Python: a **variable** stores data, a **function** (`def`) groups reusable code, "
        "a **class** is a blueprint for objects, a **loop** (`for`/`while`) repeats operations, "
        "a **list** is an ordered collection `[1, 2, 3]`, and a **dict** maps keys to values `{'key': 'value'}`."
    ),
}

# ── Response Templates ──────────────────────────────────────────────────────

_GREETING_VARIANTS = [
    "Right here, Sathwik. Fully synced and ready.",
    "I'm here, Sathwik. What do you need?",
    "Present and accounted for, Sathwik. How can I help?",
    "At your service, Sathwik. I've been waiting.",
]

_FAREWELL_VARIANTS = [
    "Goodbye, Sathwik. I'll be here when you return.",
    "Take care, Sathwik. Powering down until you need me.",
    "Signing off. Don't forget — I'm always here.",
]

_THANKS_RESPONSES = [
    "Always, Sathwik. That's what I'm here for.",
    "You don't need to thank me. Helping you is my purpose.",
    "Anytime, Sathwik. That's what partners do.",
    "My pleasure. What else can I help with?",
]

# ── Intent Classification (Local) ──────────────────────────────────────────

_INTENT_PATTERNS = {
    "greeting": [
        r"^(hi|hello|hey|yo|sup|good morning|good evening|good afternoon)",
        r"^(what's up|howdy|greetings|namaste)",
    ],
    "farewell": [
        r"^(bye|goodbye|see you|take care|talk later|peace out)",
        r"(signing off|power down|shutdown|good night)",
    ],
    "thanks": [
        r"(thank|thanks|ty|appreciate it|grateful)",
        r"(you're the best|you are amazing|thanks a lot)",
    ],
    "identity": [
        r"(who (are you|made you|built you|created you))",
        r"(your (creator|master|owner))",
    ],
    "capabilities": [
        r"(what can you do|capabilities|features|help me)",
        r"(what are you capable of|how can you help|your skills)",
    ],
    "joke": [
        r"(tell|say|crack|make).*(joke|funny|humor)",
        r"(make me laugh|tell me something funny)",
    ],
    "time": [
        r"(what time|current time|tell me the time)",
    ],
    "date": [
        r"(what date|what day|today's date)",
    ],
    "weather": [
        r"(weather|temperature|how.*cold|how.*hot)",
        r"(rain|sunny|cloudy|forecast)",
    ],
}

# ══════════════════════════════════════════════════════════════════════════
#  LOCAL INTELLIGENCE API
# ══════════════════════════════════════════════════════════════════════════

def classify_intent(query: str) -> Optional[str]:
    """
    Classify the intent of a query using local pattern matching.
    Returns intent name or None if not matched.
    """
    q = query.lower().strip()

    for intent, patterns in _INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, q, re.IGNORECASE):
                return intent

    return None


def answer_local(query: str) -> Optional[str]:
    """
    Try to answer a query using the local knowledge base.
    Returns a response string or None if not found in local KB.
    """
    q = query.lower().strip()

    for (pattern, category), response in _KNOWLEDGE_BASE.items():
        if re.search(pattern, q, re.IGNORECASE):
            return response

    return None


def get_local_response(query: str, emotion: str = "neutral") -> Optional[str]:
    """
    Get a response for common intents entirely locally (no API call needed).
    Returns None if the query requires cloud processing.
    """
    import random
    q = query.lower().strip()

    intent = classify_intent(q)

    if intent == "greeting":
        return random.choice(_GREETING_VARIANTS)

    if intent == "farewell":
        return random.choice(_FAREWELL_VARIANTS)

    if intent == "thanks":
        return random.choice(_THANKS_RESPONSES)

    if intent == "time":
        return f"It's {datetime.now().strftime('%I:%M %p')} right now, Sathwik."

    if intent == "date":
        return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}, Sathwik."

    if intent == "capabilities":
        from tools.plugin_manager import plugins_help
        base = ("I'm your personal AI companion with evolving capabilities, Sathwik. "
                "Here's what I can do right now:\n\n")
        return base + plugins_help()

    # Try knowledge base
    kb_answer = answer_local(query)
    if kb_answer:
        return kb_answer

    return None


# ══════════════════════════════════════════════════════════════════════════
#  SMART ROUTING — Local vs Cloud
# ══════════════════════════════════════════════════════════════════════════

def should_use_local(query: str) -> bool:
    """
    Determine if a query should be handled locally or sent to the cloud.
    Local for: greetings, simple facts, identity questions, time/date, thanks.
    Cloud for: complex questions, web search, code generation, multi-step tasks.
    """
    intent = classify_intent(query)

    # These are always local
    if intent in ["greeting", "farewell", "thanks", "time", "date"]:
        return True

    # Simple identity questions can be local
    if intent == "identity":
        return True

    # Knowledge base lookups
    if answer_local(query):
        return True

    # Everything else goes to cloud
    return False


def assess_complexity(query: str) -> str:
    """
    Assess the complexity of a query for model routing.
    Returns: "simple", "medium", or "complex"
    """
    q = query.lower()
    length = len(q)

    # Simple: short queries, greetings, basic questions
    if length < 15:
        return "simple"

    # Complex: code generation, analysis, multi-part requests
    complex_indicators = [
        "code", "script", "function", "algorithm", "explain", "analyze",
        "compare", "difference", "why", "how does", "create a", "design",
        "architecture", "optimize", "debug", "refactor", "write a",
        "generate", "calculate", "build", "implement", "deploy",
        "multi-step", "workflow", "plan", "autonomous",
    ]

    complexity_score = 0
    for indicator in complex_indicators:
        if indicator in q:
            complexity_score += 1

    # Adjust for length
    if length > 100:
        complexity_score += 2
    elif length > 50:
        complexity_score += 1

    # Check for technical keywords
    tech_keywords = ["python", "javascript", "api", "database", "server",
                     "frontend", "backend", "algorithm", "data structure",
                     "neural", "machine learning", "deep learning"]
    for kw in tech_keywords:
        if kw in q:
            complexity_score += 1
            break

    if complexity_score >= 3:
        return "complex"
    elif complexity_score >= 1:
        return "medium"
    else:
        return "simple"


def select_model(query: str, preferred_models: list = None) -> list:
    """
    Select the appropriate model(s) based on query complexity.
    Returns a prioritized list of model names.

    Simple queries → fastest/cheapest model
    Medium queries → balanced model
    Complex queries → most capable model
    """
    complexity = assess_complexity(query)

    model_tiers = {
        "simple": ["gemini-flash-latest", "gemini-2.0-flash"],
        "medium": ["gemini-2.0-flash", "gemini-flash-latest"],
        "complex": ["gemini-2.0-flash", "gemini-flash-latest"],
    }

    # If user has preferred models, use those instead
    if preferred_models:
        return preferred_models

    return model_tiers.get(complexity, model_tiers["medium"])


def local_cache_key(query: str, context: str = "") -> str:
    """Generate a deterministic cache key from a query."""
    key = f"{context}:{query.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def should_speak_response(response: str) -> bool:
    """Determine if a response should be spoken based on its content."""
    # Code blocks are handled by the TTS layer (it strips markdown), so still speak them
    if "```" in response or "code" in response.lower():
        return True

    # Skip TTS for very long responses — reading a wall of text aloud is unhelpful
    if len(response) > 500:
        return False

    return True


# ══════════════════════════════════════════════════════════════════════════
#  STATUS
# ══════════════════════════════════════════════════════════════════════════

def get_intelligence_status() -> dict:
    """Get status of the local intelligence system."""
    return {
        "local_patterns": len(_INTENT_PATTERNS),
        "knowledge_base_entries": len(_KNOWLEDGE_BASE),
        "online_capable": bool(os.getenv("GEMINI_API_KEY")),
        "intents_supported": list(_INTENT_PATTERNS.keys()),
    }

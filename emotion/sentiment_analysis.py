import re

def analyze_emotion(text: str) -> dict:
    """
    Analyzes the sentiment and emotional tone of the given text.
    Detects complex states like loneliness, stress, and excitement.
    """
    if not text.strip():
        return {"sentiment": "neutral", "tone": "calm", "intensity": 0.0}

    q = text.lower()
    positive_words = {"happy", "great", "amazing", "wonderful", "good", "love", "awesome"}
    negative_words = {"sad", "unhappy", "bad", "hate", "awful", "terrible", "angry"}
    words = set(re.findall(r"[a-z']+", q))
    polarity = (len(words & positive_words) - len(words & negative_words)) / max(1, len(words))
    subjectivity = min(1.0, (len(words & (positive_words | negative_words)) + 1) / max(2, len(words)))

    # 1. Advanced Keyword Mapping for Nuance
    emotion = "neutral"
    if any(w in q for w in ["alone", "lonely", "missing", "miss you", "sad", "unhappy"]):
        emotion = "lonely"
    elif any(w in q for w in ["stress", "tired", "worried", "anxious", "overwhelmed", "hard day"]):
        emotion = "stressed"
    elif any(w in q for w in ["happy", "great", "amazing", "wonderful", "good news"]):
        emotion = "happy"
    elif any(w in q for w in ["yay", "excited", "awesome", "can't wait", "wow"]):
        emotion = "excited"
    elif polarity < -0.4:
        emotion = "upset"
    elif polarity > 0.4:
        emotion = "happy"

    # Tone logic
    tone = "personal" if subjectivity > 0.5 or emotion != "neutral" else "objective"

    return {
        "sentiment": emotion,
        "tone": tone,
        "intensity": abs(polarity),
        "subjectivity": subjectivity
    }

def analyze_sentiment(text: str) -> str:
    """
    Returns only the sentiment string label (e.g., 'neutral', 'lonely', 'happy').
    """
    return analyze_emotion(text).get("sentiment", "neutral")

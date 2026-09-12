from textblob import TextBlob
import re

def analyze_emotion(text: str) -> dict:
    """
    Analyzes the sentiment and emotional tone of the given text.
    Detects complex states like loneliness, stress, and excitement.
    """
    if not text.strip():
        return {"sentiment": "neutral", "tone": "calm", "intensity": 0.0}

    q = text.lower()
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

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

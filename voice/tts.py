"""
Anju AI — CLEAN VOICE ENGINE
Single source: Microsoft Edge Neural TTS (edge-tts)
Completely free — no API key required, no browser speech fallback.
"""

from voice.free_tts import generate_tts_base64 as free_tts

# ==========================================
# GENERATE TTS AUDIO
# ==========================================

def generate_tts_base64(
    text: str,
    emotion: str = "default"
) -> str | None:
    """
    Generate neural TTS audio using Microsoft Edge Neural TTS.
    Returns base64 encoded MP3 audio or None if it fails.

    - 100% free, no API key required
    - 47+ English neural voices available
    - 7-second timeout before giving up
    - No fallback to browser speech — clean single voice pipeline
    """

    if not text or not text.strip():
        return None

    print("[TTS] Generating neural voice (edge-tts)...")
    result = free_tts(text, emotion)

    if result:
        print("[TTS] Neural voice generated successfully")
        return result

    print("[TTS] Neural voice generation failed — no voice for this message")
    return None

"""
Anju AI — Free TTS Module
Uses Microsoft Edge's online TTS (edge-tts) for high-quality neural speech.
Completely free — no API key required.
"""

import asyncio
import base64
import io
import re
import threading
from typing import Optional

# ── Timeout ─────────────────────────────────────────────────────────────────
# If edge-tts takes longer than this, we abort and let the browser handle it
TTS_TIMEOUT_SECONDS = 7

# ── Voice Configuration ─────────────────────────────────────────────────────

VOICE_MAP = {
    "default":     "en-US-AriaNeural",
    "happy":       "en-US-JennyNeural",
    "excited":     "en-US-AnaNeural",
    "energetic":   "en-US-AnaNeural",
    "sad":         "en-US-AriaNeural",
    "lonely":      "en-US-JennyNeural",
    "stressed":    "en-US-AriaNeural",
    "motivational":"en-US-GuyNeural",
    "professional":"en-US-DavisNeural",
    "technical":   "en-US-DavisNeural",
}

RATE_MAP = {
    "default":      "+0%",
    "happy":        "+8%",
    "excited":      "+12%",
    "energetic":    "+10%",
    "sad":          "-8%",
    "lonely":       "-10%",
    "stressed":     "-12%",
    "motivational": "+5%",
    "professional": "+0%",
    "technical":    "-5%",
}


def clean_text(text: str) -> str:
    """Minimal cleaning — preserve word shapes for natural pronunciation."""
    if not text:
        return ""
    text = re.sub(r"```[\s\S]*?```", " [Code shown on screen] ", text)
    text = re.sub(r"\*\*|__", "", text)
    text = re.sub(r"\*|_", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"#+\s+", "", text)
    text = re.sub(r"<[^>]*>", " ", text)
    text = re.sub(r"https?://\S+", "link", text)
    text = text.replace("&amp;", " and ")
    text = text.replace("&lt;", " less than ")
    text = text.replace("&gt;", " greater than ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def _generate_async(text: str, voice: str, rate: str) -> Optional[bytes]:
    """Generate TTS with timeout. Returns MP3 bytes or None."""
    try:
        from edge_tts import Communicate

        communicate = Communicate(text, voice=voice, rate=rate)
        audio_buffer = io.BytesIO()

        async def stream_audio():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

        # Apply timeout
        await asyncio.wait_for(stream_audio(), timeout=TTS_TIMEOUT_SECONDS)

        audio_bytes = audio_buffer.getvalue()
        if len(audio_bytes) > 100:
            return audio_bytes
        return None

    except asyncio.TimeoutError:
        print(f"[FreeTTS] Timed out after {TTS_TIMEOUT_SECONDS}s")
        return None
    except Exception as e:
        print(f"[FreeTTS] Error: {e}")
        return None


def generate_tts_base64(
    text: str,
    emotion: str = "default"
) -> Optional[str]:
    """Generate free TTS audio. Returns base64 MP3 or None."""
    clean = clean_text(text)
    if not clean:
        return None

    emotion = emotion.lower()
    voice = VOICE_MAP.get(emotion, VOICE_MAP["default"])
    rate = RATE_MAP.get(emotion, RATE_MAP["default"])

    print(f"[FreeTTS] Voice={voice} Rate={rate} Emotion={emotion}")

    try:
        audio_bytes = asyncio.run(_generate_async(clean, voice, rate))
    except RuntimeError:
        def run_in_thread():
            nonlocal audio_bytes
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_bytes = loop.run_until_complete(
                _generate_async(clean, voice, rate)
            )
            loop.close()
        audio_bytes = None
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        thread.join(timeout=TTS_TIMEOUT_SECONDS + 3)

    if audio_bytes and len(audio_bytes) > 100:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        print(f"[FreeTTS] Success: {len(audio_bytes)} bytes")
        return audio_b64

    print("[FreeTTS] Failed to generate audio")
    return None

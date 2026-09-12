"""Test edge-tts and list available voices."""
import asyncio
import edge_tts

async def main():
    # List all English voices
    voices = await edge_tts.list_voices()
    en_voices = [v for v in voices if v['Locale'].startswith('en')]

    print(f"Found {len(en_voices)} English voices:\n")
    for v in en_voices[:20]:
        name = v.get('FriendlyName', v.get('ShortName', 'unknown'))
        gender = v.get('Gender', '?')
        locale = v.get('Locale', '?')
        status = v.get('Status', '?')
        print(f"  {v['ShortName']:<35s} | {gender:<6s} | {locale:<10s} | {status}")

    print("\n--- Testing TTS generation ---\n")

    # Test with Microsoft's best English voice
    voice = "en-US-AriaNeural"
    communicate = edge_tts.Communicate(
        "Hello Sathwik, I am Anju, your personal AI companion. I am testing my new voice right now.",
        voice
    )

    # Generate and save
    await communicate.save("scratch/test_voice_edge.mp3")
    print(f"Audio generated with {voice} and saved to scratch/test_voice_edge.mp3")

asyncio.run(main())

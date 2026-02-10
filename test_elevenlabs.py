"""Standalone test: ElevenLabs TTS with LiveKit plugin."""

import asyncio
import aiohttp
from livekit.plugins import elevenlabs
from config import config


async def test_elevenlabs_tts():
    print("=== ElevenLabs TTS Test ===\n")

    # Check API key
    api_key = config.elevenlabs.api_key
    if not api_key or api_key == "your_elevenlabs_key":
        print("ERROR: ELEVENLABS_API_KEY not set in .env")
        return

    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"Voice ID: {config.elevenlabs.voice_id}")
    print(f"Model: {config.elevenlabs.model_id}")

    # Provide our own aiohttp session since we're outside LiveKit job context
    async with aiohttp.ClientSession() as session:
        tts = elevenlabs.TTS(
            api_key=api_key,
            voice_id=config.elevenlabs.voice_id,
            model=config.elevenlabs.model_id,
            http_session=session,
        )
        print(f"\nTTS instance created: {tts}")

        # Synthesize a test phrase
        text = "Hello, this is a test of ElevenLabs text to speech."
        print(f"\nSynthesizing: '{text}'")
        try:
            stream = tts.synthesize(text)
            total_frames = 0
            async for event in stream:
                if hasattr(event, 'frame') and event.frame:
                    total_frames += 1

            print(f"SUCCESS: Received {total_frames} audio frame(s)")
        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_elevenlabs_tts())

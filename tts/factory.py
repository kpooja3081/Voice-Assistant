"""Factory function for creating TTS instances using LiveKit plugins."""

import logging
from typing import TYPE_CHECKING

from livekit.plugins import deepgram, elevenlabs
from livekit.plugins.elevenlabs import VoiceSettings

if TYPE_CHECKING:
    from config import Config

logger = logging.getLogger("patient-support-agent")


def get_tts(config: "Config"):
    """Create a TTS instance based on configuration.

    Args:
        config: Application configuration

    Returns:
        Configured TTS instance from appropriate LiveKit plugin

    Supported providers:
        - elevenlabs: ElevenLabs (default, high quality)
        - deepgram: Deepgram Aura (low latency)
        - openai: OpenAI TTS
        - google: Google Cloud TTS
        - azure: Azure AI Speech
        - cartesia: Cartesia (ultra low latency)
    """
    from config import TTSProvider

    provider = config.tts_provider

    match provider:
        case TTSProvider.ELEVENLABS:
            logger.info(
                f"Using ElevenLabs TTS (model={config.elevenlabs.model_id}, "
                f"voice={config.elevenlabs.voice_id})"
            )
            return elevenlabs.TTS(
                api_key=config.elevenlabs.api_key,
                voice_id=config.elevenlabs.voice_id,
                model=config.elevenlabs.model_id,
                voice_settings=VoiceSettings(
                    stability=0.4,           # Lower = more expressive/emotional range
                    similarity_boost=0.75,    # Keep close to original voice character
                    style=0.35,              # Moderate style exaggeration for warmth
                    use_speaker_boost=True,  # Clearer voice on phone audio
                ),
            )

        case TTSProvider.DEEPGRAM:
            logger.info("Using Deepgram Aura TTS")
            return deepgram.TTS(
                api_key=config.deepgram.api_key,
            )

        case TTSProvider.OPENAI:
            from livekit.plugins import openai
            logger.info("Using OpenAI TTS")
            return openai.TTS(
                api_key=config.openai.api_key,
            )

        case TTSProvider.GOOGLE:
            from livekit.plugins import google
            logger.info("Using Google Cloud TTS")
            return google.TTS(
                credentials_info=config.google.credentials_info,
            )

        case TTSProvider.AZURE:
            from livekit.plugins import azure
            logger.info("Using Azure AI Speech TTS")
            return azure.TTS(
                speech_key=config.azure_speech.speech_key,
                speech_region=config.azure_speech.speech_region,
            )

        case TTSProvider.CARTESIA:
            from livekit.plugins import cartesia
            logger.info("Using Cartesia TTS (ultra low latency)")
            return cartesia.TTS(
                api_key=config.cartesia.api_key,
            )

        case _:
            logger.warning(f"Unknown TTS provider '{provider}', falling back to Deepgram")
            return deepgram.TTS(
                api_key=config.deepgram.api_key,
            )

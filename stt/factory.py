"""Factory function for creating STT instances using LiveKit plugins."""

import logging
from typing import TYPE_CHECKING

from livekit.plugins import deepgram

if TYPE_CHECKING:
    from config import Config

logger = logging.getLogger("patient-support-agent")


def get_stt(config: "Config"):
    """Create an STT instance based on configuration.

    Args:
        config: Application configuration

    Returns:
        Configured STT instance from appropriate LiveKit plugin

    Supported providers:
        - deepgram: Deepgram Nova-2 (default)
        - openai: OpenAI Whisper
        - google: Google Cloud Speech-to-Text
        - azure: Azure AI Speech
        - assemblyai: AssemblyAI
    """
    from config import STTProvider

    provider = config.stt_provider

    match provider:
        case STTProvider.DEEPGRAM:
            logger.info(f"Using Deepgram STT (model={config.deepgram.model})")
            return deepgram.STT(
                api_key=config.deepgram.api_key,
                model=config.deepgram.model,
                language=config.deepgram.language,
            )

        case STTProvider.OPENAI:
            from livekit.plugins import openai
            logger.info("Using OpenAI Whisper STT")
            return openai.STT(
                api_key=config.openai.api_key,
            )

        case STTProvider.GOOGLE:
            from livekit.plugins import google
            logger.info("Using Google Cloud STT")
            return google.STT(
                credentials_info=config.google.credentials_info,
            )

        case STTProvider.AZURE:
            from livekit.plugins import azure
            logger.info("Using Azure AI Speech STT")
            return azure.STT(
                speech_key=config.azure_speech.speech_key,
                speech_region=config.azure_speech.speech_region,
            )

        case STTProvider.ASSEMBLYAI:
            from livekit.plugins import assemblyai
            logger.info("Using AssemblyAI STT")
            return assemblyai.STT(
                api_key=config.assemblyai.api_key,
            )

        case STTProvider.SARVAM:
            from livekit.plugins.sarvam import STT as SarvamSTT
            # Use saarika:v2.5 model - language is optional and auto-detected
            model = config.sarvam.model
            lang = config.sarvam.language_code
            logger.info(f"Using Sarvam STT (model={model}, lang={lang})")
            return SarvamSTT(
                api_key=config.sarvam.api_key,
                model=model,
                language=lang,
            )

        case _:
            logger.warning(f"Unknown STT provider '{provider}', falling back to Deepgram")
            return deepgram.STT(
                api_key=config.deepgram.api_key,
                model=config.deepgram.model,
            )

"""Configuration management for the Patient Support Voice Agent."""

import os
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(Enum):
    AZURE = "azure"
    GEMINI = "gemini"


class TTSProvider(Enum):
    DEEPGRAM = "deepgram"
    ELEVENLABS = "elevenlabs"
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    CARTESIA = "cartesia"


class STTProvider(Enum):
    DEEPGRAM = "deepgram"
    OPENAI = "openai"
    GOOGLE = "google"
    AZURE = "azure"
    ASSEMBLYAI = "assemblyai"
    SARVAM = "sarvam"


@dataclass
class LiveKitConfig:
    url: str
    api_key: str
    api_secret: str


@dataclass
class ElevenLabsConfig:
    api_key: str
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel - warm, professional voice
    model_id: str = "eleven_turbo_v2"  # Low latency model


@dataclass
class DeepgramConfig:
    api_key: str
    model: str = "nova-2"
    language: str = "en-US"


@dataclass
class AzureOpenAIConfig:
    endpoint: str
    api_key: str
    deployment: str
    api_version: str = "2024-02-15-preview"


@dataclass
class GeminiConfig:
    api_key: str
    model: str = "gemini-1.5-flash"


@dataclass
class OpenAIConfig:
    api_key: str


@dataclass
class AzureSpeechConfig:
    speech_key: str
    speech_region: str = "eastus"


@dataclass
class CartesiaConfig:
    api_key: str


@dataclass
class AssemblyAIConfig:
    api_key: str


@dataclass
class SarvamConfig:
    api_key: str
    model: str = "saarika:v2.5"  # Sarvam's STT model (v2.5 is default)
    language_code: str = "en-IN"  # Default to Indian English, or "unknown" for auto-detect


@dataclass
class GoogleConfig:
    credentials_info: dict | None = None


@dataclass
class Config:
    livekit: LiveKitConfig
    elevenlabs: ElevenLabsConfig
    deepgram: DeepgramConfig
    azure_openai: AzureOpenAIConfig
    gemini: GeminiConfig
    openai: OpenAIConfig
    azure_speech: AzureSpeechConfig
    cartesia: CartesiaConfig
    assemblyai: AssemblyAIConfig
    sarvam: SarvamConfig
    google: GoogleConfig
    llm_provider: LLMProvider
    tts_provider: TTSProvider
    stt_provider: STTProvider

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        provider_str = os.getenv("LLM_PROVIDER", "azure").lower()
        llm_provider = LLMProvider.AZURE if provider_str == "azure" else LLMProvider.GEMINI

        # Parse TTS provider
        tts_str = os.getenv("TTS_PROVIDER", "deepgram").lower()
        tts_provider = TTSProvider(tts_str) if tts_str in [p.value for p in TTSProvider] else TTSProvider.DEEPGRAM

        # Parse STT provider
        stt_str = os.getenv("STT_PROVIDER", "deepgram").lower()
        stt_provider = STTProvider(stt_str) if stt_str in [p.value for p in STTProvider] else STTProvider.DEEPGRAM

        return cls(
            livekit=LiveKitConfig(
                url=os.getenv("LIVEKIT_URL", ""),
                api_key=os.getenv("LIVEKIT_API_KEY", ""),
                api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
            ),
            elevenlabs=ElevenLabsConfig(
                api_key=os.getenv("ELEVENLABS_API_KEY", ""),
                voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            ),
            deepgram=DeepgramConfig(
                api_key=os.getenv("DEEPGRAM_API_KEY", ""),
            ),
            azure_openai=AzureOpenAIConfig(
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
                api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
                deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            ),
            gemini=GeminiConfig(
                api_key=os.getenv("GOOGLE_API_KEY", ""),
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            ),
            openai=OpenAIConfig(
                api_key=os.getenv("OPENAI_API_KEY", ""),
            ),
            azure_speech=AzureSpeechConfig(
                speech_key=os.getenv("AZURE_SPEECH_KEY", ""),
                speech_region=os.getenv("AZURE_SPEECH_REGION", "eastus"),
            ),
            cartesia=CartesiaConfig(
                api_key=os.getenv("CARTESIA_API_KEY", ""),
            ),
            assemblyai=AssemblyAIConfig(
                api_key=os.getenv("ASSEMBLYAI_API_KEY", ""),
            ),
            sarvam=SarvamConfig(
                api_key=os.getenv("SARVAM_API_KEY", ""),
                model=os.getenv("SARVAM_MODEL", "saarika:v2"),
                language_code=os.getenv("SARVAM_LANGUAGE", "en-IN"),
            ),
            google=GoogleConfig(
                credentials_info=None,  # Load from file if needed
            ),
            llm_provider=llm_provider,
            tts_provider=tts_provider,
            stt_provider=stt_provider,
        )


# Global config instance
config = Config.from_env()

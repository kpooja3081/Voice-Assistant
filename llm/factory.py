"""Factory function for creating LLM instances."""

from config import Config, LLMProvider
from .base import BaseLLM
from .azure_openai import AzureOpenAILLM
from .gemini import GeminiLLM


def get_llm(config: Config) -> BaseLLM:
    """Create an LLM instance based on configuration.

    Args:
        config: Application configuration

    Returns:
        Configured LLM instance (Azure OpenAI or Gemini)
    """
    if config.llm_provider == LLMProvider.AZURE:
        return AzureOpenAILLM(config.azure_openai)
    else:
        return GeminiLLM(config.gemini)

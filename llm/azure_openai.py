"""Azure OpenAI LLM implementation for the Patient Support Voice Agent."""

from typing import AsyncIterator
from openai import AsyncAzureOpenAI

from .base import BaseLLM
from config import AzureOpenAIConfig


class AzureOpenAILLM(BaseLLM):
    """Azure OpenAI GPT implementation with low-latency settings."""

    def __init__(self, config: AzureOpenAIConfig):
        self.config = config
        self.client = AsyncAzureOpenAI(
            azure_endpoint=config.endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
        )
        self.deployment = config.deployment

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 150,
    ) -> str:
        """Send a chat request to Azure OpenAI."""
        response = await self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 150,
    ) -> AsyncIterator[str]:
        """Stream a chat response from Azure OpenAI."""
        stream = await self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

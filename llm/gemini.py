"""Google Gemini LLM implementation for the Patient Support Voice Agent."""

from typing import AsyncIterator
import google.generativeai as genai

from .base import BaseLLM
from config import GeminiConfig


class GeminiLLM(BaseLLM):
    """Google Gemini Flash implementation for low-latency responses."""

    def __init__(self, config: GeminiConfig):
        self.config = config
        genai.configure(api_key=config.api_key)
        self.model = genai.GenerativeModel(config.model)

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """Convert OpenAI-style messages to Gemini format."""
        gemini_messages = []
        system_prompt = ""

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_prompt = content
            elif role == "user":
                gemini_messages.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                gemini_messages.append({"role": "model", "parts": [content]})

        # Prepend system prompt to first user message if exists
        if system_prompt and gemini_messages:
            first_content = gemini_messages[0]["parts"][0]
            gemini_messages[0]["parts"][0] = f"{system_prompt}\n\n{first_content}"

        return gemini_messages

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 150,
    ) -> str:
        """Send a chat request to Gemini."""
        gemini_messages = self._convert_messages(messages)

        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        chat = self.model.start_chat(history=gemini_messages[:-1])
        response = await chat.send_message_async(
            gemini_messages[-1]["parts"][0],
            generation_config=generation_config,
        )
        return response.text

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 150,
    ) -> AsyncIterator[str]:
        """Stream a chat response from Gemini."""
        gemini_messages = self._convert_messages(messages)

        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        chat = self.model.start_chat(history=gemini_messages[:-1])
        response = await chat.send_message_async(
            gemini_messages[-1]["parts"][0],
            generation_config=generation_config,
            stream=True,
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text

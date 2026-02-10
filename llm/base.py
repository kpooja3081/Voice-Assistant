"""Base LLM interface for the Patient Support Voice Agent."""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 150,
    ) -> str:
        """Send a chat request and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response

        Returns:
            The assistant's response text
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 150,
    ) -> AsyncIterator[str]:
        """Send a chat request and stream the response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response

        Yields:
            Response text chunks as they arrive
        """
        pass

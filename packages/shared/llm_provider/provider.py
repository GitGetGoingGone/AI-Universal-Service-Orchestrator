"""Provider interface: chat completion and optional health check."""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Interface for an LLM backend (OSS or OpenAI)."""

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> str:
        """
        Send chat messages and return the assistant reply text.
        Raises on failure (timeout, 5xx, 429); caller or facade handles fallback.
        """
        ...

    def health_check(self) -> bool:
        """Optional: return True if the provider is reachable."""
        ...

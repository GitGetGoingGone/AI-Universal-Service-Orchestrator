"""OpenAI API fallback provider."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OpenAIFallbackProvider:
    """LLM provider using OpenAI API (fallback when OSS is down or rate-limited)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        timeout_sec: int = 30,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_sec = timeout_sec
        self._client: Any = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> str:
        client = self._get_client()
        resp = client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=self.timeout_sec,
        )
        if not resp.choices:
            return ""
        return (resp.choices[0].message.content or "").strip()

    def health_check(self) -> bool:
        try:
            client = self._get_client()
            client.models.list()
            return True
        except Exception as e:
            logger.debug("OpenAI health_check failed: %s", e)
            return False

    def get_client(self):
        """Return the underlying OpenAI client for tool calls etc."""
        return self._get_client()

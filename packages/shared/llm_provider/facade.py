"""Facade: try primary (OSS), on failure or 429 fallback to OpenAI."""

import logging
from typing import Any, Dict, List, Optional

from .config import get_llm_provider_config
from .oss import OSSProvider
from .openai_fallback import OpenAIFallbackProvider

logger = logging.getLogger(__name__)


class LLMProviderFacade:
    """
    Single entry point: tries primary provider (OSS or OpenAI), then fallback on
    failure, timeout, or 429. Uses config from get_llm_provider_config().
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config or get_llm_provider_config()
        self._primary = self._build_provider(self._config["LLM_PRIMARY"])
        self._fallback = None
        if self._config.get("LLM_FALLBACK"):
            self._fallback = self._build_provider(self._config["LLM_FALLBACK"])
        # If no primary (e.g. LLM_PRIMARY=oss but OSS_ENDPOINT not set), use fallback as primary
        if not self._primary and self._config.get("OPENAI_API_KEY"):
            self._primary = self._build_provider("openai")
        if not self._primary and self._fallback:
            self._primary, self._fallback = self._fallback, None
        self._max_retries = self._config.get("LLM_MAX_RETRIES", 1)

    def _build_provider(self, kind: str):
        if kind == "oss":
            endpoint = self._config.get("OSS_ENDPOINT")
            if not endpoint:
                return None
            return OSSProvider(
                endpoint=endpoint,
                api_key=self._config.get("OSS_API_KEY"),
                model=self._config.get("OSS_MODEL") or "openai/gpt-oss-20b",
                timeout_sec=self._config.get("LLM_TIMEOUT_SEC", 30),
            )
        if kind == "openai":
            key = self._config.get("OPENAI_API_KEY")
            if not key:
                return None
            return OpenAIFallbackProvider(
                api_key=key,
                model=self._config.get("OPENAI_MODEL") or "gpt-4o",
                timeout_sec=self._config.get("LLM_TIMEOUT_SEC", 30),
            )
        return None

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 500,
    ) -> str:
        """Try primary then fallback; raise if both fail."""
        last_error = None
        for attempt in range(self._max_retries + 1):
            if self._primary:
                try:
                    out = self._primary.chat_completion(
                        messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    return out
                except Exception as e:
                    last_error = e
                    is_429 = "429" in str(e) or "rate" in str(e).lower()
                    if is_429 or attempt >= self._max_retries:
                        logger.info("Primary LLM failed (%s), trying fallback", e)
                        break
                    continue

        if self._fallback:
            try:
                return self._fallback.chat_completion(
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.warning("Fallback LLM also failed: %s", e)
                last_error = e

        if last_error:
            raise last_error
        raise RuntimeError("No LLM provider configured (set OSS_ENDPOINT or OPENAI_API_KEY)")

    def get_client(self):
        """Return the underlying OpenAI-compatible client (primary or fallback) for tool calls. Prefer primary."""
        if self._primary:
            try:
                return self._primary.get_client()
            except Exception:
                pass
        if self._fallback:
            return self._fallback.get_client()
        raise RuntimeError("No LLM provider configured (set OSS_ENDPOINT or OPENAI_API_KEY)")

    def health_check(self) -> Dict[str, bool]:
        """Check primary and optionally fallback."""
        out = {"primary": False, "fallback": False}
        if self._primary:
            out["primary"] = self._primary.health_check()
        if self._fallback:
            out["fallback"] = self._fallback.health_check()
        return out


def get_llm_provider(config: Optional[Dict[str, Any]] = None) -> LLMProviderFacade:
    """Return the shared LLM facade (primary + fallback)."""
    return LLMProviderFacade(config=config)

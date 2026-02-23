"""
LLM abstraction for the new platform: self-hosted OSS primary, OpenAI API fallback.
Single provider interface for intent resolution, planning, and engagement response.
"""

from .config import get_llm_provider_config
from .facade import get_llm_provider, LLMProviderFacade

__all__ = [
    "get_llm_provider_config",
    "get_llm_provider",
    "LLMProviderFacade",
]

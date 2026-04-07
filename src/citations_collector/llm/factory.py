"""Factory for creating LLM backends."""

from __future__ import annotations

from typing import Any, Literal

from .base import LLMBackend
from .ollama_backend import OllamaBackend
from .openai_backend import OpenAIBackend
from .openrouter import OpenRouterBackend

BackendType = Literal["openrouter", "ollama", "openai", "dartmouth"]


def create_backend(
    backend_type: BackendType,
    **kwargs: Any,
) -> LLMBackend:
    """Factory for creating LLM backends.

    Args:
        backend_type: Type of backend to create
        **kwargs: Backend-specific arguments (model, api_key, base_url, etc.)

    Returns:
        LLMBackend instance

    Examples:
        >>> # Create OpenRouter backend
        >>> backend = create_backend("openrouter", model="openai/gpt-4.1-nano")

        >>> # Create local Ollama backend
        >>> backend = create_backend("ollama", model="qwen2:7b")

        >>> # Create Dartmouth chat backend
        >>> backend = create_backend(
        ...     "dartmouth",
        ...     model="gpt-4",
        ...     base_url="https://chat.dartmouth.edu",
        ... )
    """
    if backend_type == "openrouter":
        return OpenRouterBackend(**kwargs)
    elif backend_type == "ollama":
        return OllamaBackend(**kwargs)
    elif backend_type == "openai":
        return OpenAIBackend(**kwargs)
    elif backend_type == "dartmouth":
        # Dartmouth uses OpenAI-compatible interface
        # Default base_url for Dartmouth unless overridden
        if "base_url" not in kwargs:
            kwargs["base_url"] = "https://chat.dartmouth.edu/api"
        return OpenAIBackend(**kwargs)
    else:
        raise ValueError(
            f"Unknown backend type: {backend_type}. "
            f"Must be one of: openrouter, ollama, openai, dartmouth"
        )

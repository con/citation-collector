"""LLM backends for citation relationship classification."""

from .base import ClassificationResult, LLMBackend
from .factory import BackendType, create_backend

__all__ = [
    "LLMBackend",
    "ClassificationResult",
    "BackendType",
    "create_backend",
]

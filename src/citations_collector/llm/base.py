"""Base classes for LLM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    """Result from LLM classification."""

    relationship_type: str  # CitationRelationship enum value
    confidence: float  # 0.0-1.0
    reasoning: str  # LLM's explanation
    context_used: list[str]  # Which paragraph contexts were analyzed


class LLMBackend(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    def classify_citation(
        self,
        contexts: list[str],  # Paragraph-level contexts mentioning dataset
        paper_metadata: dict,  # Title, journal, year, etc.
        dataset_id: str,
    ) -> ClassificationResult:
        """Classify citation relationship type based on context.

        Args:
            contexts: List of paragraph-level contexts where dataset is mentioned
            paper_metadata: Dictionary with title, journal, year, etc.
            dataset_id: Dataset identifier (e.g., "dandi:000003")

        Returns:
            ClassificationResult with relationship type, confidence, reasoning
        """
        pass

    @abstractmethod
    def batch_classify(
        self,
        citations: list[tuple[list[str], dict, str]],
    ) -> list[ClassificationResult]:
        """Batch classification for efficiency.

        Args:
            citations: List of (contexts, paper_metadata, dataset_id) tuples

        Returns:
            List of ClassificationResult objects
        """
        pass

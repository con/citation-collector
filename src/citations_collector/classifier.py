"""Citation relationship classifier using LLM backends."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from citations_collector.llm.base import ClassificationResult, LLMBackend
from citations_collector.llm.factory import create_backend

logger = logging.getLogger(__name__)


class CitationClassifier:
    """Classify citation relationships using LLM."""

    def __init__(
        self,
        backend: LLMBackend,
        confidence_threshold: float = 0.7,
    ):
        """Initialize classifier.

        Args:
            backend: LLM backend to use for classification
            confidence_threshold: Minimum confidence to accept (0.0-1.0)
        """
        self.backend = backend
        self.confidence_threshold = confidence_threshold

    @classmethod
    def from_config(
        cls,
        backend_type: str,
        model: str | None = None,
        confidence_threshold: float = 0.7,
        **backend_kwargs: Any,
    ) -> CitationClassifier:
        """Create classifier from configuration.

        Args:
            backend_type: Backend type (ollama, dartmouth, openrouter, openai)
            model: Model name (backend-specific)
            confidence_threshold: Minimum confidence threshold
            **backend_kwargs: Additional backend arguments

        Returns:
            CitationClassifier instance
        """
        if model:
            backend_kwargs["model"] = model

        # backend_type comes from CLI as str, validated by click.Choice
        backend = create_backend(backend_type, **backend_kwargs)  # type: ignore[arg-type]
        return cls(backend, confidence_threshold)

    def classify_citation(
        self,
        contexts: list[str],
        paper_metadata: dict[str, Any],
        dataset_id: str,
    ) -> ClassificationResult:
        """Classify a single citation.

        Args:
            contexts: List of context strings where dataset is mentioned
            paper_metadata: Paper metadata (title, journal, year, etc.)
            dataset_id: Dataset identifier (e.g., "dandi:000003")

        Returns:
            ClassificationResult with relationship type and confidence
        """
        if not contexts:
            logger.warning(
                f"No contexts found for {dataset_id} in "
                f"{paper_metadata.get('title', 'unknown paper')}"
            )
            return ClassificationResult(
                relationship_type="Cites",  # Default fallback
                confidence=0.0,
                reasoning="No context available for classification",
                context_used=[],
            )

        logger.debug(
            f"Classifying {dataset_id} with {len(contexts)} contexts "
            f"for paper: {paper_metadata.get('title', 'unknown')[:50]}..."
        )

        result = self.backend.classify_citation(
            contexts=contexts,
            paper_metadata=paper_metadata,
            dataset_id=dataset_id,
        )

        logger.info(
            f"Classification: {result.relationship_type} (confidence: {result.confidence:.2f})"
        )

        return result

    def classify_from_full_text(
        self,
        pdf_or_html_path: Path,
        dataset_ids: list[str],
        paper_metadata: dict[str, Any],
    ) -> list[tuple[str, ClassificationResult]]:
        """Classify citations using full paper text.

        Args:
            pdf_or_html_path: Path to PDF or HTML file
            dataset_ids: List of dataset IDs to classify
            paper_metadata: Paper metadata dict

        Returns:
            List of (dataset_id, ClassificationResult) tuples
        """
        from citations_collector.context_extractor import ContextExtractor

        extractor = ContextExtractor()

        # Extract full text
        if pdf_or_html_path.suffix == ".pdf":
            full_text = extractor.extract_full_text_from_pdf(pdf_or_html_path, max_chars=50000)
        elif pdf_or_html_path.suffix == ".html":
            full_text = extractor.extract_full_text_from_html(pdf_or_html_path, max_chars=50000)
        else:
            logger.error(f"Unsupported file type: {pdf_or_html_path.suffix}")
            return []

        logger.info(
            f"Classifying with full text ({len(full_text)} chars) for {len(dataset_ids)} datasets"
        )

        results = []

        # Classify each dataset using the full paper text as context
        for dataset_id in dataset_ids:
            result = self.classify_citation(
                contexts=[full_text],  # Use full text as single context
                paper_metadata=paper_metadata,
                dataset_id=dataset_id,
            )
            results.append((dataset_id, result))

        return results

    def classify_from_extracted_file(
        self,
        extracted_file: Path,
    ) -> list[tuple[str, ClassificationResult]]:
        """Classify all citations in an extracted_citations.json file.

        Args:
            extracted_file: Path to extracted_citations.json

        Returns:
            List of (dataset_id, ClassificationResult) tuples
        """
        if not extracted_file.exists():
            logger.warning(f"Extracted file not found: {extracted_file}")
            return []

        with open(extracted_file) as f:
            data = json.load(f)

        paper_metadata = {
            "title": data.get("paper_title", "Unknown"),
            "journal": data.get("paper_journal"),
            "year": data.get("paper_year"),
            "doi": data.get("paper_doi"),
            "oa_status": data.get("oa_status"),
        }

        results = []

        for citation in data.get("citations", []):
            dataset_id = citation["dataset_id"]

            # Collect all context strings
            contexts = [mention["context"] for mention in citation.get("dataset_mentions", [])]

            result = self.classify_citation(
                contexts=contexts,
                paper_metadata=paper_metadata,
                dataset_id=dataset_id,
            )

            results.append((dataset_id, result))

        return results

    def should_review(self, result: ClassificationResult) -> bool:
        """Check if classification result should be reviewed.

        Args:
            result: Classification result

        Returns:
            True if confidence is below threshold
        """
        return result.confidence < self.confidence_threshold

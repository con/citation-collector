"""Tests for citations_collector.classifier module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from citations_collector.classifier import CitationClassifier
from citations_collector.llm.base import ClassificationResult, LLMBackend


@pytest.mark.ai_generated
class TestCitationClassifierInit:
    """Test CitationClassifier creation."""

    def test_init_with_backend_and_defaults(self) -> None:
        """Constructor stores backend and default confidence threshold."""
        backend = MagicMock(spec=LLMBackend)
        classifier = CitationClassifier(backend)
        assert classifier.backend is backend
        assert classifier.confidence_threshold == 0.7

    def test_init_with_custom_threshold(self) -> None:
        """Constructor stores custom confidence threshold."""
        backend = MagicMock(spec=LLMBackend)
        classifier = CitationClassifier(backend, confidence_threshold=0.5)
        assert classifier.confidence_threshold == 0.5


@pytest.mark.ai_generated
class TestCitationClassifierFromConfig:
    """Test CitationClassifier.from_config factory."""

    @patch("citations_collector.classifier.create_backend")
    def test_from_config_creates_backend(self, mock_create: MagicMock) -> None:
        """from_config delegates to create_backend with the right args."""
        mock_backend = MagicMock(spec=LLMBackend)
        mock_create.return_value = mock_backend

        classifier = CitationClassifier.from_config(
            backend_type="ollama",
            model="qwen2:7b",
            confidence_threshold=0.8,
        )

        mock_create.assert_called_once_with("ollama", model="qwen2:7b")
        assert classifier.backend is mock_backend
        assert classifier.confidence_threshold == 0.8

    @patch("citations_collector.classifier.create_backend")
    def test_from_config_without_model(self, mock_create: MagicMock) -> None:
        """from_config works when model is None."""
        mock_create.return_value = MagicMock(spec=LLMBackend)
        CitationClassifier.from_config(backend_type="ollama")
        mock_create.assert_called_once_with("ollama")


@pytest.mark.ai_generated
class TestClassifyCitation:
    """Test CitationClassifier.classify_citation."""

    def _make_classifier(self) -> tuple[CitationClassifier, MagicMock]:
        backend = MagicMock(spec=LLMBackend)
        classifier = CitationClassifier(backend, confidence_threshold=0.7)
        return classifier, backend

    def test_classify_with_contexts(self) -> None:
        """classify_citation delegates to backend and returns result."""
        classifier, backend = self._make_classifier()
        expected = ClassificationResult(
            relationship_type="Uses",
            confidence=0.9,
            reasoning="Paper analyses the dataset",
            context_used=["We used DANDI:000003"],
        )
        backend.classify_citation.return_value = expected

        result = classifier.classify_citation(
            contexts=["We used DANDI:000003"],
            paper_metadata={"title": "Test Paper"},
            dataset_id="dandi:000003",
        )

        assert result is expected
        backend.classify_citation.assert_called_once_with(
            contexts=["We used DANDI:000003"],
            paper_metadata={"title": "Test Paper"},
            dataset_id="dandi:000003",
        )

    def test_classify_with_empty_contexts_returns_fallback(self) -> None:
        """classify_citation returns fallback when no contexts provided."""
        classifier, backend = self._make_classifier()

        result = classifier.classify_citation(
            contexts=[],
            paper_metadata={"title": "Test Paper"},
            dataset_id="dandi:000003",
        )

        assert result.relationship_type == "Cites"
        assert result.confidence == 0.0
        assert result.context_used == []
        backend.classify_citation.assert_not_called()


@pytest.mark.ai_generated
class TestShouldReview:
    """Test CitationClassifier.should_review threshold logic."""

    def test_below_threshold_needs_review(self) -> None:
        backend = MagicMock(spec=LLMBackend)
        classifier = CitationClassifier(backend, confidence_threshold=0.7)
        result = ClassificationResult(
            relationship_type="Uses",
            confidence=0.5,
            reasoning="low confidence",
            context_used=[],
        )
        assert classifier.should_review(result) is True

    def test_above_threshold_no_review(self) -> None:
        backend = MagicMock(spec=LLMBackend)
        classifier = CitationClassifier(backend, confidence_threshold=0.7)
        result = ClassificationResult(
            relationship_type="Uses",
            confidence=0.9,
            reasoning="high confidence",
            context_used=[],
        )
        assert classifier.should_review(result) is False

    def test_at_threshold_no_review(self) -> None:
        backend = MagicMock(spec=LLMBackend)
        classifier = CitationClassifier(backend, confidence_threshold=0.7)
        result = ClassificationResult(
            relationship_type="Uses",
            confidence=0.7,
            reasoning="exact threshold",
            context_used=[],
        )
        assert classifier.should_review(result) is False


@pytest.mark.ai_generated
class TestClassifyFromExtractedFile:
    """Test CitationClassifier.classify_from_extracted_file."""

    def test_classify_from_extracted_file(self, tmp_path: Path) -> None:
        """classify_from_extracted_file reads JSON and classifies each citation."""
        extracted_data = {
            "paper_title": "A Great Paper",
            "paper_journal": "Nature",
            "paper_year": 2024,
            "paper_doi": "10.1234/test",
            "oa_status": "gold",
            "citations": [
                {
                    "dataset_id": "dandi:000003",
                    "dataset_mentions": [
                        {"context": "We analysed DANDI:000003 recordings"},
                    ],
                },
            ],
        }
        extracted_file = tmp_path / "extracted_citations.json"
        extracted_file.write_text(json.dumps(extracted_data))

        backend = MagicMock(spec=LLMBackend)
        backend.classify_citation.return_value = ClassificationResult(
            relationship_type="Uses",
            confidence=0.9,
            reasoning="ok",
            context_used=["We analysed DANDI:000003 recordings"],
        )
        classifier = CitationClassifier(backend)

        results = classifier.classify_from_extracted_file(extracted_file)

        assert len(results) == 1
        dataset_id, result = results[0]
        assert dataset_id == "dandi:000003"
        assert result.relationship_type == "Uses"

    def test_classify_from_nonexistent_file(self, tmp_path: Path) -> None:
        """Returns empty list for nonexistent file."""
        backend = MagicMock(spec=LLMBackend)
        classifier = CitationClassifier(backend)
        results = classifier.classify_from_extracted_file(tmp_path / "missing.json")
        assert results == []

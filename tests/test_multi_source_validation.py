"""Tests for multi-source citation tracking validation."""

from __future__ import annotations

import json

import pytest

from citations_collector.models import CitationRecord


@pytest.mark.ai_generated
def test_citation_sources_dates_coherence_valid() -> None:
    """Verify that coherent citation_sources and discovered_dates pass validation."""
    citation = CitationRecord(
        item_id="test:001",
        item_flavor="v1.0",
        citation_relationship="Cites",
        citation_source="crossref",  # Backward compatibility field
        citation_sources=["crossref", "openalex"],
        discovered_dates=json.dumps({"crossref": "2025-01-15", "openalex": "2025-01-20"}),
    )

    # Should not raise
    assert citation.citation_sources == ["crossref", "openalex"]
    assert json.loads(citation.discovered_dates) == {
        "crossref": "2025-01-15",
        "openalex": "2025-01-20",
    }


@pytest.mark.ai_generated
def test_citation_sources_dates_coherence_missing_in_dates() -> None:
    """Verify that sources without corresponding dates raise validation error."""
    with pytest.raises(ValueError, match="citation_sources and discovered_dates must be coherent"):
        CitationRecord(
            item_id="test:001",
            item_flavor="v1.0",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_sources=["crossref", "openalex", "datacite"],
            discovered_dates=json.dumps({"crossref": "2025-01-15"}),  # Missing openalex, datacite
        )


@pytest.mark.ai_generated
def test_citation_sources_dates_coherence_missing_in_sources() -> None:
    """Verify that dates without corresponding sources raise validation error."""
    with pytest.raises(ValueError, match="citation_sources and discovered_dates must be coherent"):
        CitationRecord(
            item_id="test:001",
            item_flavor="v1.0",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_sources=["crossref"],
            discovered_dates=json.dumps(
                {
                    "crossref": "2025-01-15",
                    "openalex": "2025-01-20",
                    "datacite": "2025-01-22",
                }
            ),  # Extra keys
        )


@pytest.mark.ai_generated
def test_citation_sources_dates_both_empty() -> None:
    """Verify that citation_sources auto-populates from citation_source when empty."""
    citation = CitationRecord(
        item_id="test:001",
        item_flavor="v1.0",
        citation_relationship="Cites",
        citation_source="crossref",  # Legacy field still required
        citation_sources=[],  # Empty - should be auto-populated
        discovered_dates=None,  # None
    )

    # citation_sources should auto-populate from citation_source (backward compat)
    assert citation.citation_sources == ["crossref"]
    assert citation.discovered_dates is None


@pytest.mark.ai_generated
def test_citation_sources_dates_invalid_json() -> None:
    """Verify that invalid JSON in discovered_dates raises validation error."""
    with pytest.raises(ValueError, match="Invalid JSON in discovered_dates"):
        CitationRecord(
            item_id="test:001",
            item_flavor="v1.0",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_sources=["crossref"],
            discovered_dates="{invalid json}",
        )


@pytest.mark.ai_generated
def test_citation_sources_dates_not_dict() -> None:
    """Verify that non-dict JSON in discovered_dates raises validation error."""
    with pytest.raises(ValueError, match="discovered_dates must be a JSON object"):
        CitationRecord(
            item_id="test:001",
            item_flavor="v1.0",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_sources=["crossref"],
            discovered_dates='["crossref"]',  # Valid JSON but not an object
        )

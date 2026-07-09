"""Tests for core CitationCollector orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest
import responses

from citations_collector.core import CitationCollector


@pytest.mark.ai_generated
def test_from_yaml(collections_dir: Path) -> None:
    """Test loading collection from YAML."""
    collector = CitationCollector.from_yaml(collections_dir / "simple.yaml")

    assert collector.collection.name == "Simple Test Collection"
    assert len(collector.collection.items) == 1
    assert len(collector.citations) == 0  # No citations loaded yet


@pytest.mark.ai_generated
@responses.activate
def test_discover_all_with_mocks(collections_dir: Path) -> None:
    """Test discover_all with mocked APIs."""
    # Mock CrossRef data-citations API
    responses.add(
        responses.GET,
        "https://api.crossref.org/beta/datacitations",
        json={
            "message": {
                "total-results": 1,
                "items-per-page": 1000,
                "next-page": None,
                "items": [
                    {
                        "timestamp": "2024-01-01T00:00:00Z",
                        "relation": "references",
                        "subject": {
                            "id": "10.1234/citing.paper",
                            "type": "journal-article",
                            "member": "1234",
                            "registration-agency": "Crossref",
                        },
                        "object": {
                            "id": "10.1234/test.dataset",
                            "type": "dataset",
                            "registration-agency": "DataCite",
                        },
                    }
                ],
            }
        },
        status=200,
    )

    # Mock DOI metadata endpoint
    responses.add(
        responses.GET,
        "https://doi.org/10.1234/citing.paper",
        json={
            "title": "Test citation",
            "author": [{"given": "John", "family": "Doe"}],
            "published": {"date-parts": [[2024]]},
        },
        status=200,
    )

    # Load collection and discover
    collector = CitationCollector.from_yaml(collections_dir / "simple.yaml")
    collector.discover_all(sources=["crossref"])

    # Verify citations discovered
    assert len(collector.citations) == 1
    assert collector.citations[0].citation_doi == "10.1234/citing.paper"
    assert collector.citations[0].item_id == "test-item"
    assert collector.citations[0].item_flavor == "1.0.0"


@pytest.mark.ai_generated
def test_load_existing_citations(tsv_dir: Path, collections_dir: Path) -> None:
    """Test loading existing citations from TSV."""
    collector = CitationCollector.from_yaml(collections_dir / "simple.yaml")
    collector.load_existing_citations(tsv_dir / "simple.tsv")

    assert len(collector.citations) == 1
    assert collector.citations[0].citation_status == "active"


@pytest.mark.ai_generated
def test_merge_citations_preserve_curation(collections_dir: Path) -> None:
    """Test merging new citations preserves existing curation."""
    from citations_collector.models import CitationRecord

    collector = CitationCollector.from_yaml(collections_dir / "simple.yaml")

    # Add existing citation with curation
    existing = CitationRecord(
        item_id="test-item",
        item_flavor="1.0.0",
        citation_doi="10.1234/paper",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="ignored",
        citation_comment="False positive",
    )
    collector.citations = [existing]

    # Try to merge same citation from new discovery
    new_citations = [
        CitationRecord(
            item_id="test-item",
            item_flavor="1.0.0",
            citation_doi="10.1234/paper",
            citation_relationship="Cites",
            citation_source="opencitations",
            citation_status="active",
        )
    ]

    collector.merge_citations(new_citations)

    # Should preserve existing curation status
    assert len(collector.citations) == 1
    assert collector.citations[0].citation_status == "ignored"
    assert collector.citations[0].citation_comment == "False positive"


@pytest.mark.ai_generated
def test_save_workflow(tmp_path: Path, collections_dir: Path) -> None:
    """Test saving collection and citations."""
    from citations_collector.models import CitationRecord

    collector = CitationCollector.from_yaml(collections_dir / "simple.yaml")

    # Add a citation
    collector.citations = [
        CitationRecord(
            item_id="test-item",
            item_flavor="1.0.0",
            citation_doi="10.1234/paper",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_status="active",
        )
    ]

    # Save
    yaml_path = tmp_path / "collection.yaml"
    tsv_path = tmp_path / "citations.tsv"
    collector.save(yaml_path, tsv_path)

    # Verify files created
    assert yaml_path.exists()
    assert tsv_path.exists()

    # Reload and verify
    reloaded = CitationCollector.from_yaml(yaml_path)
    reloaded.load_existing_citations(tsv_path)
    assert len(reloaded.citations) == 1

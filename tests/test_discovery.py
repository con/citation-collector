"""Tests for citation discovery APIs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
import responses

from citations_collector.discovery import (
    CrossRefDiscoverer,
    DataCiteDiscoverer,
    OpenCitationsDiscoverer,
)
from citations_collector.discovery.utils import deduplicate_citations
from citations_collector.models import ItemRef


@pytest.mark.ai_generated
@responses.activate
def test_crossref_success(responses_dir: Path) -> None:
    """Test successful citation discovery from the CrossRef data-citations API."""
    # Load mock response
    with open(responses_dir / "crossref_success.json") as f:
        mock_data = json.load(f)

    # Mock CrossRef data-citations API
    responses.add(
        responses.GET,
        "https://api.crossref.org/beta/datacitations",
        json=mock_data,
        status=200,
    )

    # Mock DOI metadata endpoint for each citing DOI
    responses.add(
        responses.GET,
        "https://doi.org/10.1234/citing.paper1",
        json={
            "title": "First paper citing our dataset",
            "author": [{"given": "John", "family": "Smith"}],
            "published": {"date-parts": [[2024, 1, 15]]},
            "container-title": ["Journal of Test Research"],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://doi.org/10.1234/citing.paper2",
        json={
            "title": "Second paper citing our dataset",
            "author": [{"given": "Bob", "family": "Wilson"}],
            "published": {"date-parts": [[2023, 6, 10]]},
            "container-title": ["Test Science"],
        },
        status=200,
    )

    # Create discoverer and item ref
    discoverer = CrossRefDiscoverer(email="test@example.org")
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Discover citations
    citations = discoverer.discover(item_ref)

    # Verify results
    assert len(citations) == 2
    assert citations[0].citation_doi == "10.1234/citing.paper1"
    assert citations[0].citation_source == "crossref"
    assert citations[0].citation_title == "First paper citing our dataset"
    assert citations[0].citation_year == 2024
    assert citations[1].citation_doi == "10.1234/citing.paper2"


@pytest.mark.ai_generated
@responses.activate
def test_crossref_empty_results(responses_dir: Path) -> None:
    """Test CrossRef data-citations API with no citations."""
    # Load mock response
    with open(responses_dir / "crossref_empty.json") as f:
        mock_data = json.load(f)

    # Mock CrossRef data-citations API
    responses.add(
        responses.GET,
        "https://api.crossref.org/beta/datacitations",
        json=mock_data,
        status=200,
    )

    # The empty-results fallback also hits the works metadata endpoint
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/test.dataset",
        json={"message": {"is-referenced-by-count": 0}},
        status=200,
    )

    # Create discoverer
    discoverer = CrossRefDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Discover citations
    citations = discoverer.discover(item_ref)

    # Should return empty list, not error
    assert citations == []


@pytest.mark.ai_generated
@responses.activate
def test_crossref_network_error() -> None:
    """Test CrossRef graceful degradation on network error."""
    # Mock network error
    responses.add(
        responses.GET,
        "https://api.crossref.org/beta/datacitations",
        status=500,
    )

    # Create discoverer
    discoverer = CrossRefDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Should return empty list, not raise
    citations = discoverer.discover(item_ref)
    assert citations == []


@pytest.mark.ai_generated
@responses.activate
def test_opencitations_discovery(responses_dir: Path) -> None:
    """Test OpenCitations COCI citation discovery."""
    # Load mock response
    with open(responses_dir / "opencitations_success.json") as f:
        mock_data = json.load(f)

    # Mock OpenCitations COCI API (v1)
    responses.add(
        responses.GET,
        "https://opencitations.net/index/coci/api/v1/citations/10.1234/test.dataset",
        json=mock_data,
        status=200,
    )

    # Mock DOI metadata endpoint for citing DOI
    responses.add(
        responses.GET,
        "https://doi.org/10.1234/citing.paper3",
        json={
            "title": "Third paper citing our dataset",
            "author": [{"given": "Jane", "family": "Doe"}],
            "published": {"date-parts": [[2024, 2, 1]]},
            "container-title": ["Citation Journal"],
        },
        status=200,
    )

    # Create discoverer
    discoverer = OpenCitationsDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Discover citations
    citations = discoverer.discover(item_ref)

    # Verify results
    assert len(citations) == 1
    assert citations[0].citation_doi == "10.1234/citing.paper3"
    assert citations[0].citation_source == "opencitations"


@pytest.mark.ai_generated
@responses.activate
def test_incremental_date_filtering() -> None:
    """Test incremental discovery using date filters."""
    # Mock CrossRef data-citations API with date filter
    responses.add(
        responses.GET,
        "https://api.crossref.org/beta/datacitations",
        json={
            "message": {
                "total-results": 0,
                "items-per-page": 1000,
                "next-page": None,
                "items": [],
            }
        },
        status=200,
    )

    # Mock CrossRef Metadata API (called when data-citations returns 0)
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/test.dataset",
        json={"message": {"is-referenced-by-count": 0}},
        status=200,
    )

    # Create discoverer
    discoverer = CrossRefDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Discover with since parameter
    since = datetime(2024, 1, 1)
    discoverer.discover(item_ref, since=since)

    # Beta API uses from-created-date (indexing timestamp), not from-updated-date.
    assert len(responses.calls) == 2  # data-citations + metadata
    assert "from-created-date=2024-01-01" in responses.calls[0].request.url
    assert "object-id=" in responses.calls[0].request.url
    assert "10.1234" in responses.calls[0].request.url


@pytest.mark.ai_generated
def test_deduplication_across_sources() -> None:
    """Test deduplication of citations from multiple sources."""
    from citations_collector.models import CitationRecord

    # Create duplicate citations (same item+flavor+doi)
    citations = [
        CitationRecord(
            item_id="test",
            item_flavor="1.0",
            citation_doi="10.1234/paper",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_status="active",
        ),
        CitationRecord(
            item_id="test",
            item_flavor="1.0",
            citation_doi="10.1234/paper",
            citation_relationship="Cites",
            citation_source="opencitations",
            citation_status="active",
        ),
        CitationRecord(
            item_id="test",
            item_flavor="1.0",
            citation_doi="10.1234/different",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_status="active",
        ),
    ]

    # Deduplicate
    unique = deduplicate_citations(citations)

    # Should keep only unique (item_id, item_flavor, citation_doi)
    assert len(unique) == 2
    dois = {c.citation_doi for c in unique}
    assert dois == {"10.1234/paper", "10.1234/different"}


@pytest.mark.ai_generated
@responses.activate
def test_datacite_success(responses_dir: Path) -> None:
    """Test successful citation discovery from DataCite Event Data."""
    # Load mock response
    with open(responses_dir / "datacite_success.json") as f:
        mock_data = json.load(f)

    # Mock DataCite Event Data API
    responses.add(
        responses.GET,
        "https://api.datacite.org/events",
        json=mock_data,
        status=200,
    )

    # Create discoverer and item ref
    discoverer = DataCiteDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.48324/dandi.000003/0.210812.1448")

    # Discover citations
    citations = discoverer.discover(item_ref)

    # Verify results
    assert len(citations) == 2
    assert citations[0].citation_doi == "10.1016/j.neuron.2022.01.001"
    assert citations[0].citation_source == "datacite"
    assert citations[0].citation_title == "Hippocampal replay of extended experience"
    assert citations[0].citation_year == 2022
    assert citations[1].citation_doi == "10.1038/s41593-023-01234-5"


@pytest.mark.ai_generated
@responses.activate
def test_datacite_empty_results(responses_dir: Path) -> None:
    """Test DataCite with no citations."""
    # Load mock response
    with open(responses_dir / "datacite_empty.json") as f:
        mock_data = json.load(f)

    # Mock DataCite Event Data API
    responses.add(
        responses.GET,
        "https://api.datacite.org/events",
        json=mock_data,
        status=200,
    )

    # Create discoverer
    discoverer = DataCiteDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.48324/dandi.000005/0.210812.1500")

    # Discover citations
    citations = discoverer.discover(item_ref)

    # Should return empty list, not error
    assert citations == []


@pytest.mark.ai_generated
@responses.activate
def test_datacite_network_error() -> None:
    """Test DataCite graceful degradation on network error."""
    # Mock network error
    responses.add(
        responses.GET,
        "https://api.datacite.org/events",
        status=500,
    )

    # Create discoverer
    discoverer = DataCiteDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.48324/dandi.000003/0.210812.1448")

    # Should return empty list, not raise
    citations = discoverer.discover(item_ref)
    assert citations == []


@pytest.mark.ai_generated
def test_datacite_non_doi_ref() -> None:
    """Test DataCite with non-DOI reference type."""
    discoverer = DataCiteDiscoverer()
    item_ref = ItemRef(ref_type="github", ref_value="dandi/dandi-cli")

    # Should return empty list and log warning
    citations = discoverer.discover(item_ref)
    assert citations == []

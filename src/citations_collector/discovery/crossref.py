"""CrossRef data-citations API discovery.

Uses the ``/beta/datacitations`` endpoint on ``api.crossref.org``. This
replaces the retired ``api.eventdata.crossref.org`` Event Data service,
which CrossRef permanently shut down on 2026-04-23. See issue #7 and
https://www.crossref.org/blog/strengthening-support-for-data-citations-and-saying-goodbye-to-event-data/
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, cast

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from citations_collector.discovery.base import AbstractDiscoverer
from citations_collector.models import CitationRecord, CitationSource, ItemRef

logger = logging.getLogger(__name__)


def _sanitize_text(text: str | None) -> str | None:
    """Sanitize text for TSV output - normalize whitespace, remove control chars."""
    if text is None:
        return None
    # Replace newlines, tabs, carriage returns with spaces
    text = re.sub(r"[\n\r\t]+", " ", text)
    # Collapse multiple spaces
    text = re.sub(r" +", " ", text)
    # Strip leading/trailing whitespace
    return text.strip() or None


class CrossRefDiscoverer(AbstractDiscoverer):
    """Discover citations via the CrossRef data-citations API."""

    BASE_URL = "https://api.crossref.org/beta/datacitations"
    DOI_API = "https://doi.org"

    def __init__(self, email: str | None = None) -> None:
        """
        Initialize CrossRef data-citations discoverer.

        Args:
            email: Email for polite pool (better rate limits)
        """
        self.email = email
        self.session = requests.Session()
        if email:
            self.session.headers["User-Agent"] = f"citations-collector (mailto:{email})"

        # Add retry logic for timeouts and server errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,  # 2s, 4s, 8s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def discover(self, item_ref: ItemRef, since: datetime | None = None) -> list[CitationRecord]:
        """
        Discover citations from the CrossRef data-citations API.

        Args:
            item_ref: DOI reference to query
            since: Optional date for incremental updates (from-created-date filter)

        Returns:
            List of citation records
        """
        if item_ref.ref_type != "doi":
            logger.warning(f"CrossRef only supports DOI refs, got {item_ref.ref_type}")
            return []

        doi = item_ref.ref_value
        logger.debug(f"CrossRef querying for DOI: {doi}")

        # object-id filters citations whose *object* (cited work) is this DOI;
        # rows=1000 is the API maximum.
        params: dict[str, Any] = {"object-id": doi, "rows": 1000}
        if self.email:
            params["mailto"] = self.email

        # Beta API takes YYYY-MM-DD for from-created-date (indexing timestamp).
        if since:
            params["from-created-date"] = since.strftime("%Y-%m-%d")

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
        except requests.Timeout:
            logger.warning(f"CrossRef data-citations API timeout for {doi} (query took >60s)")
            return []
        except requests.RequestException as e:
            logger.warning(f"CrossRef data-citations API error for {doi}: {e}")
            return []

        # Parse citations from the items array
        citations = []
        items = data.get("message", {}).get("items", [])

        for item in items:
            # subject.id is the citing DOI (bare, no URL prefix)
            citing_doi = item.get("subject", {}).get("id", "")

            if not citing_doi or not citing_doi.startswith("10."):
                continue

            # Fetch metadata for the citing DOI via DOI content negotiation
            metadata = self._fetch_doi_metadata(citing_doi)

            # Create citation record with metadata
            citation = CitationRecord(
                item_id="",  # Will be filled by caller
                item_flavor="",  # Will be filled by caller
                citation_doi=citing_doi,
                citation_title=cast(str | None, metadata.get("title")),
                citation_authors=cast(str | None, metadata.get("authors")),
                citation_year=cast(int | None, metadata.get("year")),
                citation_journal=cast(str | None, metadata.get("journal")),
                citation_relationship="Cites",  # type: ignore[arg-type]
                citation_source=CitationSource("crossref"),
                citation_status="active",  # type: ignore[arg-type]
            )
            citations.append(citation)

        # Warn if the API returned items but none were valid DOI-based citations
        if len(items) > 0 and len(citations) == 0:
            logger.info(
                f"CrossRef data-citations returned {len(items)} items for {doi} "
                f"but none had valid subject DOIs"
            )

        # Also check metadata API if we got 0 citations total
        if len(citations) == 0:
            try:
                meta_resp = self.session.get(f"https://api.crossref.org/works/{doi}", timeout=10)
                if meta_resp.status_code == 200:
                    meta_data = meta_resp.json()
                    cited_by_count = meta_data.get("message", {}).get("is-referenced-by-count", 0)
                    if cited_by_count > 0:
                        logger.warning(
                            f"CrossRef metadata shows {cited_by_count} citations for {doi}, "
                            f"but data-citations API has 0 valid citations. "
                            f"Full cited-by data requires CrossRef membership: "
                            f"https://www.crossref.org/services/cited-by/"
                        )
            except Exception as e:
                logger.debug(f"Failed to check cited-by count for {doi}: {e}")

        return citations

    def _fetch_doi_metadata(self, doi: str) -> dict[str, str | int | None]:
        """
        Fetch metadata for a DOI via content negotiation.

        Args:
            doi: The DOI to fetch metadata for

        Returns:
            Dictionary with title, authors, year, journal
        """
        metadata: dict[str, str | int | None] = {
            "title": None,
            "authors": None,
            "year": None,
            "journal": None,
        }

        try:
            response = self.session.get(
                f"{self.DOI_API}/{doi}",
                headers={"Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            # Extract title (sanitize for TSV)
            metadata["title"] = _sanitize_text(data.get("title"))

            # Extract authors
            authors = data.get("author", [])
            if authors:
                author_names = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors
                ]
                metadata["authors"] = _sanitize_text("; ".join(author_names))

            # Extract year
            published = data.get("published", {})
            date_parts = published.get("date-parts", [[]])
            if date_parts and len(date_parts[0]) > 0:
                metadata["year"] = date_parts[0][0]

            # Extract journal (may be string or list, sanitize for TSV)
            container = data.get("container-title")
            if isinstance(container, list):
                metadata["journal"] = _sanitize_text(container[0]) if container else None
            else:
                metadata["journal"] = _sanitize_text(container)

        except requests.RequestException as e:
            logger.debug(f"Failed to fetch metadata for DOI {doi}: {e}")

        return metadata

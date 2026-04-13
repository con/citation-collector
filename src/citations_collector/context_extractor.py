"""Extract citation contexts from PDFs and HTML files."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ContextExtractor:
    """Extract citation contexts from PDFs and HTMLs."""

    def __init__(self, dataset_patterns: dict[str, list[str]] | None = None):
        r"""Initialize context extractor.

        Args:
            dataset_patterns: Mapping of dataset namespace to regex patterns
                Example: {"dandi": [r"DANDI:\s*(\d+)", r"dandiarchive\.org/dandiset/(\d+)"]}
        """
        self.dataset_patterns = dataset_patterns or self._default_patterns()

    @staticmethod
    def _default_patterns() -> dict[str, list[str]]:
        """Default dataset ID patterns."""
        return {
            "dandi": [
                r"DANDI[:\s]+(\d{6})",  # DANDI:000003 or DANDI 000003
                r"dandiarchive\.org/dandiset/(\d{6})",  # URL form
                r"doi\.org/10\.48324/dandi\.(\d{6})",  # DOI form
            ],
        }

    def extract_full_text_from_pdf(
        self,
        pdf_path: Path,
        max_chars: int = 50000,
    ) -> str:
        """Extract full text from PDF (up to max_chars).

        Args:
            pdf_path: Path to PDF file
            max_chars: Maximum characters to extract (default: 50000)

        Returns:
            Full text string (or first max_chars)
        """
        try:
            import pdfplumber
        except ImportError as e:
            raise ImportError(
                "pdfplumber required for PDF extraction. Install with: pip install pdfplumber"
            ) from e

        logger.info(f"Extracting full text from PDF: {pdf_path}")

        full_text_parts = []
        total_chars = 0

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if total_chars + len(text) > max_chars:
                    # Truncate to max_chars
                    remaining = max_chars - total_chars
                    full_text_parts.append(text[:remaining])
                    break
                full_text_parts.append(text)
                total_chars += len(text)

        full_text = "\n\n".join(full_text_parts)
        logger.debug(f"Extracted {len(full_text)} chars from {pdf_path}")
        return full_text

    def extract_from_pdf(
        self,
        pdf_path: Path,
        target_datasets: list[str] | None = None,
    ) -> dict[str, Any]:
        """Extract citation contexts from PDF.

        Args:
            pdf_path: Path to PDF file
            target_datasets: List of dataset IDs to search for (e.g., ["dandi:000003"])
                            If None, search for all known patterns

        Returns:
            extracted_citations.json structure
        """
        try:
            import pdfplumber
        except ImportError as e:
            raise ImportError(
                "pdfplumber required for PDF extraction. Install with: pip install pdfplumber"
            ) from e

        logger.info(f"Extracting contexts from PDF: {pdf_path}")

        with pdfplumber.open(pdf_path) as pdf:
            # Extract metadata
            metadata = pdf.metadata or {}

            # Extract text by page
            citations_by_dataset: dict[str, dict] = {}

            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""

                # Search for dataset mentions
                for dataset_id in target_datasets or []:
                    matches = self._find_dataset_mentions(text, dataset_id)

                    for match in matches:
                        if dataset_id not in citations_by_dataset:
                            citations_by_dataset[dataset_id] = {
                                "dataset_id": dataset_id,
                                "dataset_mentions": [],
                            }

                        # Extract paragraph containing mention
                        context = self._extract_paragraph(text, match.start())

                        # Avoid duplicates (same context on same page)
                        if not self._is_duplicate_context(
                            citations_by_dataset[dataset_id]["dataset_mentions"],
                            context,
                            page_num,
                        ):
                            citations_by_dataset[dataset_id]["dataset_mentions"].append(
                                {
                                    "context": context,
                                    "page": page_num,
                                    "section": None,  # TODO: extract section headers
                                    "source": "pdf",
                                }
                            )

            return {
                "paper_doi": None,  # Set externally
                "paper_title": metadata.get("Title", "Unknown"),
                "paper_journal": None,  # Set externally
                "paper_year": None,  # Set externally
                "oa_status": None,  # Set externally
                "extraction_date": datetime.now().isoformat(),
                "extraction_method": "pdfplumber",
                "citations": list(citations_by_dataset.values()),
            }

    def extract_full_text_from_html(
        self,
        html_path: Path,
        max_chars: int = 50000,
    ) -> str:
        """Extract full text from HTML (up to max_chars).

        Args:
            html_path: Path to HTML file
            max_chars: Maximum characters to extract (default: 50000)

        Returns:
            Full text string (or first max_chars)
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError as e:
            raise ImportError(
                "beautifulsoup4 required for HTML extraction. "
                "Install with: pip install beautifulsoup4"
            ) from e

        logger.info(f"Extracting full text from HTML: {html_path}")

        with open(html_path, encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Remove script/style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get all text
        full_text = soup.get_text(separator="\n", strip=True)

        # Truncate if needed
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars]
            logger.debug(f"Truncated HTML text to {max_chars} chars")

        logger.debug(f"Extracted {len(full_text)} chars from {html_path}")
        return full_text

    def extract_from_html(
        self,
        html_path: Path,
        target_datasets: list[str],
    ) -> dict[str, Any]:
        """Extract citation contexts from HTML.

        Args:
            html_path: Path to HTML file
            target_datasets: List of dataset IDs to search for

        Returns:
            extracted_citations.json structure
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError as e:
            raise ImportError(
                "beautifulsoup4 required for HTML extraction. "
                "Install with: pip install beautifulsoup4"
            ) from e

        logger.info(f"Extracting contexts from HTML: {html_path}")

        with open(html_path, encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Remove script/style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract by paragraph
        citations_by_dataset: dict[str, dict] = {}

        for p in soup.find_all("p"):
            text = p.get_text()

            for dataset_id in target_datasets:
                if self._contains_dataset_id(text, dataset_id):
                    if dataset_id not in citations_by_dataset:
                        citations_by_dataset[dataset_id] = {
                            "dataset_id": dataset_id,
                            "dataset_mentions": [],
                        }

                    # Try to find section header
                    section = self._find_section_header(p)

                    # Avoid duplicates
                    context = text.strip()
                    if not self._is_duplicate_context(
                        citations_by_dataset[dataset_id]["dataset_mentions"],
                        context,
                        None,
                    ):
                        citations_by_dataset[dataset_id]["dataset_mentions"].append(
                            {
                                "context": context,
                                "page": None,
                                "section": section,
                                "source": "html",
                            }
                        )

        return {
            "paper_doi": None,
            "paper_title": None,
            "paper_journal": None,
            "paper_year": None,
            "oa_status": None,
            "extraction_date": datetime.now().isoformat(),
            "extraction_method": "beautifulsoup",
            "citations": list(citations_by_dataset.values()),
        }

    def _find_dataset_mentions(self, text: str, dataset_id: str) -> list[re.Match]:
        """Find all mentions of dataset ID in text.

        Args:
            text: Text to search
            dataset_id: Dataset identifier (e.g., "dandi:000003")

        Returns:
            List of regex matches
        """
        # Extract namespace and ID
        if ":" in dataset_id:
            namespace, dataset_num = dataset_id.split(":", 1)
        else:
            # Try to infer namespace
            namespace = "dandi" if dataset_id.startswith("00") else "unknown"
            dataset_num = dataset_id

        matches = []

        # Try patterns for this namespace
        patterns = self.dataset_patterns.get(namespace.lower(), [])
        for pattern in patterns:
            # Replace capture group with specific dataset number
            specific_pattern = pattern.replace(r"(\d{6})", dataset_num)
            specific_pattern = specific_pattern.replace(r"(\d+)", dataset_num)

            for match in re.finditer(specific_pattern, text, re.IGNORECASE):
                matches.append(match)

        # Also try literal dataset ID
        for match in re.finditer(re.escape(dataset_id), text, re.IGNORECASE):
            matches.append(match)

        return matches

    def _contains_dataset_id(self, text: str, dataset_id: str) -> bool:
        """Check if text contains dataset ID.

        Args:
            text: Text to search
            dataset_id: Dataset identifier

        Returns:
            True if dataset ID found
        """
        return len(self._find_dataset_mentions(text, dataset_id)) > 0

    def _extract_paragraph(self, text: str, position: int, window_size: int = 800) -> str:
        """Extract paragraph containing the position.

        Extracts context around the dataset mention. Prefers natural paragraph
        boundaries (double newlines) but expands to window_size if needed.

        Args:
            text: Full text
            position: Position of dataset mention
            window_size: Target context window size in characters (default: 800)

        Returns:
            Paragraph text
        """
        # First try to find paragraph boundaries (double newlines)
        para_start = text.rfind("\n\n", 0, position)
        para_end = text.find("\n\n", position)

        # If we found both boundaries, use them (but enforce minimum size)
        if para_start != -1 and para_end != -1:
            paragraph = text[para_start:para_end].strip()

            # If paragraph is too short, expand to window_size
            if len(paragraph) < window_size // 2:
                para_start = max(0, position - window_size // 2)
                para_end = min(len(text), position + window_size // 2)
        else:
            # No clear paragraph boundaries, use fixed window
            para_start = max(0, position - window_size // 2)
            para_end = min(len(text), position + window_size // 2)

        paragraph = text[para_start:para_end].strip()

        # Clean up whitespace (collapse multiple spaces/newlines to single space)
        paragraph = re.sub(r"\s+", " ", paragraph)

        # Truncate if still too long (keep context centered on mention)
        max_length = 1000
        if len(paragraph) > max_length:
            mention_in_para = position - para_start
            # Keep max_length/2 chars before and after
            context_start = max(0, mention_in_para - max_length // 2)
            context_end = min(len(paragraph), mention_in_para + max_length // 2)
            paragraph = "..." + paragraph[context_start:context_end] + "..."

        return paragraph

    def _find_section_header(self, element: Any) -> str | None:
        """Find nearest section header before element.

        Args:
            element: BeautifulSoup element

        Returns:
            Section header text or None
        """
        # Look backwards for h1, h2, h3, h4
        for sibling in element.find_previous_siblings():
            if sibling.name in ["h1", "h2", "h3", "h4"]:
                return str(sibling.get_text().strip())
        return None

    def _is_duplicate_context(
        self,
        existing_mentions: list[dict],
        new_context: str,
        page: int | None,
    ) -> bool:
        """Check if context is duplicate of existing mention.

        Args:
            existing_mentions: List of existing mention dicts
            new_context: New context text
            page: Page number (for PDFs)

        Returns:
            True if duplicate
        """
        for mention in existing_mentions:
            # Same context text
            if mention["context"] == new_context:
                return True

            # Very similar context (90% overlap)
            similarity = self._text_similarity(mention["context"], new_context)
            if similarity > 0.9:
                return True

        return False

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simple word overlap).

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score 0-1
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def save_extracted_citations(
        self,
        extracted: dict[str, Any],
        output_path: Path,
    ) -> None:
        """Save extracted citations to JSON file.

        Args:
            extracted: Extracted citations dictionary
            output_path: Path to save JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(extracted, f, indent=2)

        logger.info(f"Saved extracted citations to {output_path}")

    def load_extracted_citations(self, json_path: Path) -> dict[str, Any]:
        """Load extracted citations from JSON file.

        Args:
            json_path: Path to JSON file

        Returns:
            Extracted citations dictionary
        """
        with open(json_path) as f:
            return dict(json.load(f))

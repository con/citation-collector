"""Tests for citations_collector.context_extractor module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citations_collector.context_extractor import ContextExtractor


@pytest.mark.ai_generated
class TestContextExtractorInit:
    """Test ContextExtractor initialization."""

    def test_default_patterns(self) -> None:
        """Default patterns include dandi namespace."""
        extractor = ContextExtractor()
        assert "dandi" in extractor.dataset_patterns
        assert len(extractor.dataset_patterns["dandi"]) > 0

    def test_custom_patterns(self) -> None:
        """Custom patterns override defaults."""
        custom = {"myns": [r"MYNS[:\s]+(\d+)"]}
        extractor = ContextExtractor(dataset_patterns=custom)
        assert extractor.dataset_patterns == custom


@pytest.mark.ai_generated
class TestFindDatasetMentions:
    """Test _find_dataset_mentions pattern matching."""

    def test_finds_dandi_colon_format(self) -> None:
        extractor = ContextExtractor()
        text = "We used DANDI:000003 for analysis."
        matches = extractor._find_dataset_mentions(text, "dandi:000003")
        assert len(matches) > 0

    def test_finds_dandi_url_format(self) -> None:
        extractor = ContextExtractor()
        text = "Data from dandiarchive.org/dandiset/000003 was used."
        matches = extractor._find_dataset_mentions(text, "dandi:000003")
        assert len(matches) > 0

    def test_no_match_for_wrong_dataset(self) -> None:
        extractor = ContextExtractor()
        text = "We used DANDI:000003 for analysis."
        matches = extractor._find_dataset_mentions(text, "dandi:000999")
        assert len(matches) == 0

    def test_literal_dataset_id_match(self) -> None:
        extractor = ContextExtractor()
        text = "Referenced dandi:000020 here."
        matches = extractor._find_dataset_mentions(text, "dandi:000020")
        assert len(matches) > 0


@pytest.mark.ai_generated
class TestContainsDatasetId:
    """Test _contains_dataset_id helper."""

    def test_contains_returns_true(self) -> None:
        extractor = ContextExtractor()
        assert extractor._contains_dataset_id("See DANDI:000003", "dandi:000003")

    def test_contains_returns_false(self) -> None:
        extractor = ContextExtractor()
        assert not extractor._contains_dataset_id("No dataset here", "dandi:000003")


@pytest.mark.ai_generated
class TestExtractParagraph:
    """Test _extract_paragraph context windowing."""

    def test_extracts_around_position(self) -> None:
        extractor = ContextExtractor()
        text = "A" * 200 + "\n\n" + "B" * 50 + "DANDI:000003" + "C" * 50 + "\n\n" + "D" * 200
        position = text.index("DANDI:000003")
        paragraph = extractor._extract_paragraph(text, position)
        assert "DANDI:000003" in paragraph

    def test_handles_no_paragraph_boundaries(self) -> None:
        extractor = ContextExtractor()
        text = "Some text with DANDI:000003 mentioned in it."
        position = text.index("DANDI:000003")
        paragraph = extractor._extract_paragraph(text, position)
        assert "DANDI:000003" in paragraph


@pytest.mark.ai_generated
class TestTextSimilarity:
    """Test _text_similarity static method."""

    def test_identical_texts(self) -> None:
        assert ContextExtractor._text_similarity("hello world", "hello world") == 1.0

    def test_completely_different(self) -> None:
        assert ContextExtractor._text_similarity("hello world", "foo bar") == 0.0

    def test_partial_overlap(self) -> None:
        sim = ContextExtractor._text_similarity("hello world foo", "hello world bar")
        assert 0.0 < sim < 1.0

    def test_empty_texts(self) -> None:
        assert ContextExtractor._text_similarity("", "") == 0.0

    def test_one_empty(self) -> None:
        assert ContextExtractor._text_similarity("hello", "") == 0.0


@pytest.mark.ai_generated
class TestIsDuplicateContext:
    """Test _is_duplicate_context deduplication."""

    def test_exact_duplicate(self) -> None:
        extractor = ContextExtractor()
        existing = [{"context": "We used DANDI:000003", "page": 1}]
        assert extractor._is_duplicate_context(existing, "We used DANDI:000003", 2) is True

    def test_not_duplicate(self) -> None:
        extractor = ContextExtractor()
        existing = [{"context": "We used DANDI:000003", "page": 1}]
        assert (
            extractor._is_duplicate_context(existing, "A completely different paragraph", 2)
            is False
        )

    def test_empty_existing(self) -> None:
        extractor = ContextExtractor()
        assert extractor._is_duplicate_context([], "anything", 1) is False


@pytest.mark.ai_generated
class TestExtractFullTextFromHtml:
    """Test extract_full_text_from_html."""

    def test_extracts_text_from_html(self, tmp_path: Path) -> None:
        html_content = """<html>
<head><title>Test Paper</title></head>
<body>
<h1>Introduction</h1>
<p>We analysed data from DANDI:000003 in this study.</p>
<script>var x = 1;</script>
<style>.foo { color: red; }</style>
<p>More text here.</p>
</body>
</html>"""
        html_file = tmp_path / "paper.html"
        html_file.write_text(html_content)

        extractor = ContextExtractor()
        text = extractor.extract_full_text_from_html(html_file)

        assert "DANDI:000003" in text
        assert "More text here" in text
        # Script and style should be removed
        assert "var x = 1" not in text
        assert ".foo" not in text

    def test_truncates_at_max_chars(self, tmp_path: Path) -> None:
        html_content = "<html><body><p>" + "A" * 500 + "</p></body></html>"
        html_file = tmp_path / "big.html"
        html_file.write_text(html_content)

        extractor = ContextExtractor()
        text = extractor.extract_full_text_from_html(html_file, max_chars=100)
        assert len(text) <= 100


@pytest.mark.ai_generated
class TestExtractFromHtml:
    """Test extract_from_html structured extraction."""

    def test_extracts_citations_from_html(self, tmp_path: Path) -> None:
        html_content = """<html><body>
<h2>Methods</h2>
<p>We downloaded recordings from DANDI:000003 for analysis.</p>
<p>No dataset mention here.</p>
</body></html>"""
        html_file = tmp_path / "paper.html"
        html_file.write_text(html_content)

        extractor = ContextExtractor()
        result = extractor.extract_from_html(html_file, target_datasets=["dandi:000003"])

        assert result["extraction_method"] == "beautifulsoup"
        assert len(result["citations"]) == 1
        citation = result["citations"][0]
        assert citation["dataset_id"] == "dandi:000003"
        assert len(citation["dataset_mentions"]) >= 1
        assert "DANDI:000003" in citation["dataset_mentions"][0]["context"]

    def test_no_match_returns_empty_citations(self, tmp_path: Path) -> None:
        html_content = "<html><body><p>Nothing here.</p></body></html>"
        html_file = tmp_path / "empty.html"
        html_file.write_text(html_content)

        extractor = ContextExtractor()
        result = extractor.extract_from_html(html_file, target_datasets=["dandi:000003"])
        assert result["citations"] == []


@pytest.mark.ai_generated
class TestSaveAndLoadExtractedCitations:
    """Test save_extracted_citations and load_extracted_citations round-trip."""

    def test_round_trip(self, tmp_path: Path) -> None:
        extractor = ContextExtractor()
        data = {
            "paper_doi": "10.1234/test",
            "paper_title": "Test",
            "citations": [
                {
                    "dataset_id": "dandi:000003",
                    "dataset_mentions": [{"context": "text", "page": 1}],
                }
            ],
        }
        output = tmp_path / "sub" / "extracted.json"
        extractor.save_extracted_citations(data, output)

        loaded = extractor.load_extracted_citations(output)
        assert loaded == data

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        extractor = ContextExtractor()
        output = tmp_path / "a" / "b" / "c" / "out.json"
        extractor.save_extracted_citations({"test": True}, output)
        assert output.exists()
        with open(output) as f:
            assert json.load(f) == {"test": True}

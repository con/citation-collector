#!/usr/bin/env python3
"""Test context extraction from PDFs and HTMLs."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from citations_collector.context_extractor import ContextExtractor


def test_html_extraction():
    """Test HTML context extraction."""
    print("=" * 70)
    print("Testing HTML Context Extraction")
    print("=" * 70)

    # Create sample HTML
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Paper</title></head>
    <body>
        <h1>Introduction</h1>
        <p>Neuroscience research requires large-scale datasets.</p>

        <h2>Methods</h2>
        <p>We analyzed neural recordings from the Allen Institute Neuropixels
        dataset (DANDI:000003) using custom spike sorting algorithms. The dataset
        contains high-quality electrophysiological recordings from mouse visual cortex.</p>

        <p>Additionally, we validated our approach on the Patch-seq dataset
        (DANDI:000020) which includes simultaneous electrophysiology and transcriptomics.</p>

        <h2>Results</h2>
        <p>Our analysis of DANDI:000003 revealed novel patterns in neural activity.</p>

        <h2>Discussion</h2>
        <p>These results demonstrate the value of open datasets like DANDI:000003.</p>
    </body>
    </html>
    """

    # Save to temp file
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write(html_content)
        html_path = Path(f.name)

    try:
        extractor = ContextExtractor()

        # Extract contexts for DANDI:000003 and DANDI:000020
        extracted = extractor.extract_from_html(
            html_path,
            target_datasets=["dandi:000003", "dandi:000020"],
        )

        print(f"\nExtraction method: {extracted['extraction_method']}")
        print(f"Found {len(extracted['citations'])} datasets with mentions")

        for citation in extracted["citations"]:
            dataset_id = citation["dataset_id"]
            mentions = citation["dataset_mentions"]

            print(f"\n{dataset_id}:")
            print(f"  Mentions: {len(mentions)}")

            for i, mention in enumerate(mentions, 1):
                print(f"\n  [{i}] Section: {mention['section']}")
                print(f"      Context: {mention['context'][:100]}...")

        # Verify we found both datasets
        dataset_ids = [c["dataset_id"] for c in extracted["citations"]]
        assert "dandi:000003" in dataset_ids, "Should find DANDI:000003"
        assert "dandi:000020" in dataset_ids, "Should find DANDI:000020"

        # Verify DANDI:000003 has multiple mentions
        dandi_003 = next(c for c in extracted["citations"] if c["dataset_id"] == "dandi:000003")
        assert len(dandi_003["dataset_mentions"]) >= 3, "Should find at least 3 mentions"

        print("\n✓ HTML extraction test passed!")
        return True

    finally:
        html_path.unlink()


def test_pdf_extraction():
    """Test PDF context extraction."""
    print("\n" + "=" * 70)
    print("Testing PDF Context Extraction")
    print("=" * 70)

    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        print("⊘ pdfplumber not installed, skipping PDF test")
        print("  Install with: pip install pdfplumber")
        return False

    # Create sample PDF with text
    try:
        import tempfile

        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            pdf_path = Path(f.name)

        # Create simple PDF
        c = canvas.Canvas(str(pdf_path), pagesize=letter)

        # Page 1
        c.drawString(100, 750, "Test Research Paper")
        c.drawString(100, 700, "Methods")
        c.drawString(
            100,
            650,
            "We analyzed neural data from DANDI:000003 using spike sorting.",
        )
        c.drawString(100, 630, "The DANDI:000003 dataset contains electrophysiology data.")
        c.showPage()

        # Page 2
        c.drawString(100, 750, "Results")
        c.drawString(100, 700, "Analysis of DANDI:000003 revealed novel patterns.")
        c.showPage()

        c.save()

    except ImportError:
        print("⊘ reportlab not installed, creating mock PDF test")
        print("  Install with: pip install reportlab")
        return False

    try:
        extractor = ContextExtractor()

        extracted = extractor.extract_from_pdf(
            pdf_path,
            target_datasets=["dandi:000003"],
        )

        print(f"\nExtraction method: {extracted['extraction_method']}")
        print(f"Found {len(extracted['citations'])} datasets with mentions")

        for citation in extracted["citations"]:
            dataset_id = citation["dataset_id"]
            mentions = citation["dataset_mentions"]

            print(f"\n{dataset_id}:")
            print(f"  Mentions: {len(mentions)}")

            for i, mention in enumerate(mentions, 1):
                print(f"\n  [{i}] Page: {mention['page']}")
                print(f"      Context: {mention['context'][:100]}...")

        print("\n✓ PDF extraction test passed!")
        return True

    finally:
        if pdf_path.exists():
            pdf_path.unlink()


def test_dataset_pattern_matching():
    """Test dataset ID pattern matching."""
    print("\n" + "=" * 70)
    print("Testing Dataset Pattern Matching")
    print("=" * 70)

    extractor = ContextExtractor()

    test_cases = [
        ("DANDI:000003", "dandi:000003", True),
        ("DANDI 000003", "dandi:000003", True),
        ("dandiarchive.org/dandiset/000003", "dandi:000003", True),
        ("doi.org/10.48324/dandi.000003", "dandi:000003", True),
        ("other dataset", "dandi:000003", False),
    ]

    for text, dataset_id, should_match in test_cases:
        matches = extractor._find_dataset_mentions(text, dataset_id)
        found = len(matches) > 0

        status = "✓" if found == should_match else "✗"
        print(f"{status} '{text}' -> {dataset_id}: {found}")

        assert found == should_match, f"Pattern matching failed for: {text}"

    print("\n✓ Pattern matching test passed!")
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("Context Extraction Tests")
    print("=" * 70)

    results = {
        "Pattern matching": test_dataset_pattern_matching(),
        "HTML extraction": test_html_extraction(),
        "PDF extraction": test_pdf_extraction(),
    }

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20s}: {status}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()

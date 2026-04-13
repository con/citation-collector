#!/usr/bin/env python3
"""Quick test of classify command on dandi-bib extracts."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from citations_collector.classifier import CitationClassifier


def test_classify_real_extracts():
    """Test classification on real extracted contexts from dandi-bib."""
    print("Testing classify on real dandi-bib extracts...\n")

    # Path to dandi-bib extracts
    dandi_bib_path = Path("/home/yoh/proj/dandi/dandi-bib/citations/pdfs")

    if not dandi_bib_path.exists():
        print(f"⊘ dandi-bib path not found: {dandi_bib_path}")
        print("  Run extract-contexts in dandi-bib first")
        return False

    # Find extracted files (recursively)
    extracted_files = list(dandi_bib_path.glob("**/extracted_citations.json"))

    if not extracted_files:
        print(f"⊘ No extracted_citations.json files found in {dandi_bib_path}")
        return False

    print(f"Found {len(extracted_files)} extracted files\n")

    # Test with first 3 files
    test_files = extracted_files[:3]

    try:
        # Create classifier (Ollama backend)
        print("Creating classifier with Ollama backend...")
        classifier = CitationClassifier.from_config(
            backend_type="ollama",
            model="qwen2:7b",
            confidence_threshold=0.7,
        )
        print("✓ Classifier created\n")

    except Exception as e:
        print(f"✗ Failed to create classifier: {e}")
        print("\nTroubleshooting:")
        print("  - Check Ollama is running or SSH tunnel active")
        print("  - Test with: curl http://localhost:11434/api/tags")
        return False

    # Test classification
    success_count = 0
    for json_path in test_files:
        print(f"Testing: {json_path.parent.name}")

        # Load and check contents
        with open(json_path) as f:
            data = json.load(f)

        if not data.get("citations"):
            print("  ⊘ No citations in file, skipping\n")
            continue

        print(f"  Paper: {data.get('paper_title', 'Unknown')[:60]}...")
        print(f"  Citations: {len(data['citations'])}")

        # Classify
        try:
            results = classifier.classify_from_extracted_file(json_path)

            for dataset_id, result in results:
                print(
                    f"    • {dataset_id}: {result.relationship_type} "
                    f"(confidence: {result.confidence:.2f})"
                )
                if result.confidence < 0.7:
                    print(f"      Reasoning: {result.reasoning[:100]}...")

                # Show first context
                if result.context_used:
                    ctx = result.context_used[0]
                    print(f"      Context: {ctx[:150]}...")

            success_count += 1
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}\n")

    # Summary
    print("=" * 60)
    print(f"Successfully classified: {success_count}/{len(test_files)}")
    return success_count > 0


if __name__ == "__main__":
    success = test_classify_real_extracts()
    sys.exit(0 if success else 1)

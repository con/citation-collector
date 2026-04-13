#!/usr/bin/env python
"""Test script for LLM backends."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from citations_collector.llm import create_backend


def test_ollama():
    """Test Ollama backend."""
    print("Testing Ollama backend...")

    try:
        backend = create_backend("ollama", model="qwen2:7b")

        # Test classification
        contexts = [
            (
                "We analyzed neural recordings from the Allen Institute dataset "
                "(DANDI:000003) using custom spike sorting algorithms."
            ),
            (
                "The DANDI:000003 dataset contains high-quality electrophysiological "
                "recordings from mouse visual cortex."
            ),
        ]

        metadata = {
            "title": "Advanced spike sorting methods for neural data",
            "journal": "Nature Neuroscience",
            "year": 2024,
        }

        result = backend.classify_citation(
            contexts=contexts,
            paper_metadata=metadata,
            dataset_id="dandi:000003",
        )

        print("✓ Ollama classification successful!")
        print(f"  Relationship: {result.relationship_type}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")
        return True

    except Exception as e:
        print(f"✗ Ollama test failed: {e}")
        return False


def test_dartmouth():
    """Test Dartmouth chat backend."""
    print("\nTesting Dartmouth chat backend...")

    try:
        backend = create_backend(
            "dartmouth",
            model="gpt-4",
            # base_url defaults to https://chat.dartmouth.edu/api
        )

        contexts = [
            (
                "We describe a comprehensive dataset of neural recordings "
                "(DANDI:000108) collected from mouse visual cortex."
            ),
        ]

        metadata = {
            "title": "A comprehensive dataset of neural recordings",
            "journal": "Scientific Data",
            "year": 2024,
        }

        result = backend.classify_citation(
            contexts=contexts,
            paper_metadata=metadata,
            dataset_id="dandi:000108",
        )

        print("✓ Dartmouth classification successful!")
        print(f"  Relationship: {result.relationship_type}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Reasoning: {result.reasoning}")
        return True

    except Exception as e:
        print(f"✗ Dartmouth test failed: {e}")
        return False


def main():
    """Run all backend tests."""
    print("=" * 60)
    print("LLM Backend Tests")
    print("=" * 60)

    # Load secrets
    # Try both possible locations
    secrets_paths = [
        Path("/home/yoh/proj/dandi/citations-collector/.git/secrets"),
        Path(__file__).parent.parent / ".git" / "secrets",
    ]

    for secrets_file in secrets_paths:
        if secrets_file.exists():
            print(f"Loading secrets from {secrets_file}")
            import os

            with open(secrets_file) as f:
                for line in f:
                    if line.strip() and line.startswith("export "):
                        # Parse export statements
                        try:
                            line = line.strip()[7:]  # Remove "export "
                            if "=" in line:
                                key, value = line.split("=", 1)
                                os.environ[key] = value
                        except Exception:  # noqa: S110
                            pass
            break

    results = {}

    # Test Ollama
    results["ollama"] = test_ollama()

    # Test Dartmouth
    results["dartmouth"] = test_dartmouth()

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for backend, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{backend:15s}: {status}")

    # Exit with error if any failed
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()

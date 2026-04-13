#!/usr/bin/env python3
"""Systematic comparison of LLM models for citation classification.

Runs multiple models (both Ollama and Dartmouth) on both short contexts
and full text, stores results, and generates comparison report.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from citations_collector.classifier import CitationClassifier
from citations_collector.persistence import tsv_io, yaml_io


def get_available_ollama_models():
    """Get list of available Ollama models."""
    import subprocess

    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return [model["name"] for model in data.get("models", [])]
    except Exception as e:
        print(f"Warning: Could not get Ollama models: {e}")
    return []


def classify_with_model(
    classifier,
    papers_to_classify,
    citation_lookup,
    mode="short",
):
    """Run classification with a model and return results.

    Returns:
        dict: {(doi, dataset_id): (relationship, confidence, reasoning)}
    """
    results = {}

    for item in papers_to_classify:
        if mode == "full":
            doi, file_path, file_type = item
            # Get datasets for this DOI
            datasets_for_doi = [dataset_id for (d, dataset_id) in citation_lookup if d == doi]

            # Get paper metadata
            citation = next((c for c in citation_lookup.values() if c.citation_doi == doi), None)
            if not citation:
                continue

            paper_metadata = {
                "title": citation.citation_title,
                "journal": citation.citation_journal,
                "year": citation.citation_year,
                "doi": doi,
            }

            try:
                model_results = classifier.classify_from_full_text(
                    file_path, datasets_for_doi, paper_metadata
                )
            except Exception as e:
                print(f"  Error on {doi}: {e}")
                continue

        else:  # short context mode
            doi, json_path, _ = item
            try:
                model_results = classifier.classify_from_extracted_file(json_path)
            except Exception as e:
                print(f"  Error on {doi}: {e}")
                continue

        # Store results
        for dataset_id, result in model_results:
            results[(doi, dataset_id)] = (
                result.relationship_type,
                result.confidence,
                result.reasoning[:200],  # Truncate reasoning
            )

    return results


def run_comparison(collection_path: Path, output_dir: Path):
    """Run systematic comparison across models."""
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("LLM Model Comparison for Citation Classification")
    print("=" * 80)
    print()

    # Load collection and citations
    print(f"Loading collection from {collection_path}")
    coll = yaml_io.load_collection(collection_path)

    tsv_path = Path(coll.output_tsv) if coll.output_tsv else Path("citations.tsv")
    citations = tsv_io.load_citations(tsv_path)

    pdfs_dir = Path(coll.pdfs.output_dir) if coll.pdfs else Path("pdfs")

    # Build citation lookup
    citation_lookup = {(c.citation_doi, c.item_id): c for c in citations if c.citation_doi}

    print(f"Loaded {len(citations)} citations")
    print()

    # Find papers with extracted contexts
    papers_short_context = []
    papers_full_text = []

    for doi in {c.citation_doi for c in citations if c.citation_doi}:
        doi_path = pdfs_dir / doi
        json_path = doi_path / "extracted_citations.json"
        pdf_path = doi_path / "article.pdf"
        html_path = doi_path / "article.html"

        if json_path.exists():
            papers_short_context.append((doi, json_path, "json"))

        if pdf_path.exists():
            papers_full_text.append((doi, pdf_path, "pdf"))
        elif html_path.exists():
            papers_full_text.append((doi, html_path, "html"))

    print(f"Papers with extracted contexts: {len(papers_short_context)}")
    print(f"Papers with full text: {len(papers_full_text)}")
    print()

    # Define models to test
    ollama_models = get_available_ollama_models()
    print(f"Available Ollama models: {ollama_models}")

    # Filter to models we want to test (fast ones)
    test_ollama_models = [
        m for m in ollama_models if any(x in m for x in ["qwen2", "llama", "phi"])
    ][:3]  # Limit to 3 fastest

    print(f"Testing Ollama models: {test_ollama_models}")
    print()

    # Dartmouth models to test
    # Free (local at Dartmouth) - good for testing
    dartmouth_free = [
        "openai.gpt-oss-120b",  # GPT-OSS 120b (Reasoning)
        "google.gemma-3-27b-it",  # Gemma 3 27b
        "meta.llama-3.2-11b-vision-instruct",  # Llama 3.2 11b
    ]

    # Budget ($) - fast and cheap
    dartmouth_budget = [
        "anthropic.claude-haiku-4-5-20251001",  # Claude Haiku 4.5
        "openai.gpt-4.1-mini-2025-04-14",  # GPT 4.1 mini
        "vertex_ai.gemini-2.0-flash-001",  # Gemini 2.0 Flash
    ]

    # Premium ($$$) - best quality
    dartmouth_premium = [
        "anthropic.claude-sonnet-4-5-20250929",  # Claude Sonnet 4.5 (tested)
        "openai_responses.gpt-5-2025-08-07",  # GPT-5
        "vertex_ai.gemini-2.5-pro",  # Gemini 2.5 Pro
    ]

    # Select models based on priority
    # Start with free + 1-2 budget + 1 premium for comprehensive comparison
    dartmouth_models = (
        dartmouth_free[:2]  # 2 free models
        + dartmouth_budget[:2]  # 2 budget models
        + dartmouth_premium[:1]  # 1 premium model
    )

    # Check if Dartmouth is available
    # Dartmouth uses OPENAI_API_KEY for authentication
    dartmouth_available = False

    # Check environment variable first
    if os.getenv("OPENAI_API_KEY"):
        dartmouth_available = True
    else:
        # Try to load from secrets file
        try:
            secrets_path = Path.home() / "proj/dandi/citations-collector/.git/secrets"
            if secrets_path.exists():
                with open(secrets_path) as f:
                    for line in f:
                        if "OPENAI_API_KEY" in line and "=" in line:
                            # Set environment variable for backends
                            key, value = line.split("=", 1)
                            os.environ["OPENAI_API_KEY"] = value.strip()
                            dartmouth_available = True
                            break
        except Exception as e:
            print(f"Warning: Could not load secrets: {e}")

    if not dartmouth_available:
        print("Dartmouth API not configured (no OPENAI_API_KEY), skipping")
        dartmouth_models = []
    else:
        print(f"Dartmouth API configured, testing {len(dartmouth_models)} models")

    # Storage for all results
    all_results = {}

    # Run each model on both short and full context
    modes = [
        ("short", papers_short_context),
        ("full", papers_full_text),
    ]

    for backend_type in ["ollama", "dartmouth"]:
        models = test_ollama_models if backend_type == "ollama" else dartmouth_models

        for model in models:
            for mode_name, papers in modes:
                model_key = f"{backend_type}_{model}_{mode_name}"
                print(f"\n{'=' * 60}")
                print(f"Testing: {model_key}")
                print(f"{'=' * 60}")

                try:
                    # Create classifier
                    classifier = CitationClassifier.from_config(
                        backend_type=backend_type,
                        model=model,
                        confidence_threshold=0.7,
                    )

                    # Run classification
                    results = classify_with_model(
                        classifier, papers, citation_lookup, mode=mode_name
                    )

                    all_results[model_key] = {
                        "backend": backend_type,
                        "model": model,
                        "mode": mode_name,
                        "timestamp": datetime.now().isoformat(),
                        "num_classifications": len(results),
                        "results": {
                            f"{doi}|{dataset_id}": {
                                "relationship": rel,
                                "confidence": conf,
                                "reasoning": reason,
                            }
                            for (doi, dataset_id), (rel, conf, reason) in results.items()
                        },
                    }

                    print(f"✓ Classified {len(results)} citations")

                    # Save intermediate results
                    result_file = output_dir / f"{model_key}.json"
                    with open(result_file, "w") as f:
                        json.dump(all_results[model_key], f, indent=2)
                    print(f"  Saved to {result_file}")

                except Exception as e:
                    print(f"✗ Error: {e}")
                    all_results[model_key] = {
                        "backend": backend_type,
                        "model": model,
                        "mode": mode_name,
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e),
                    }

    # Save combined results
    combined_file = output_dir / "all_results.json"
    with open(combined_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'=' * 80}")
    print(f"✓ All results saved to {output_dir}")
    print(f"{'=' * 80}")

    return all_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compare LLM models for citation classification")
    parser.add_argument("collection", type=Path, help="Path to collection YAML file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("model_comparison_results"),
        help="Output directory for results",
    )

    args = parser.parse_args()

    results = run_comparison(args.collection, args.output_dir)

    print("\nRun analyze_model_comparison.py to generate comparison report")

#!/usr/bin/env python3
"""Analyze and compare LLM model classification results.

Generates report showing:
- Agreement rates between models
- Confidence distributions
- Which models agree/disagree
- Short context vs full text comparison
"""

import json
import sys
from collections import defaultdict
from pathlib import Path


def load_results(results_dir: Path):
    """Load all model results."""
    all_results = {}

    # Load combined file if exists
    combined = results_dir / "all_results.json"
    if combined.exists():
        with open(combined) as f:
            all_results = json.load(f)
    else:
        # Load individual files
        for result_file in results_dir.glob("*.json"):
            if result_file.name == "all_results.json":
                continue
            with open(result_file) as f:
                data = json.load(f)
                model_key = result_file.stem
                all_results[model_key] = data

    return all_results


def create_comparison_matrix(all_results):
    """Create matrix of classifications by model."""
    # Get all citation keys
    all_citations = set()
    for model_data in all_results.values():
        if "results" in model_data:
            all_citations.update(model_data["results"].keys())

    # Build matrix: {citation_key: {model: (relationship, confidence)}}
    matrix = defaultdict(dict)

    for model_key, model_data in all_results.items():
        if "results" not in model_data:
            continue

        for citation_key, result in model_data["results"].items():
            matrix[citation_key][model_key] = (
                result["relationship"],
                result["confidence"],
            )

    return matrix


def calculate_agreement(matrix):
    """Calculate pairwise agreement between models."""
    models = set()
    for citation_data in matrix.values():
        models.update(citation_data.keys())

    models = sorted(models)

    # Pairwise agreement matrix
    agreement = {}

    for model1 in models:
        for model2 in models:
            if model1 >= model2:
                continue

            # Find citations classified by both
            common_citations = [
                key for key, data in matrix.items() if model1 in data and model2 in data
            ]

            if not common_citations:
                continue

            # Calculate agreement
            agree_count = sum(
                1 for key in common_citations if matrix[key][model1][0] == matrix[key][model2][0]
            )

            agreement_rate = agree_count / len(common_citations)
            agreement[(model1, model2)] = {
                "agree": agree_count,
                "total": len(common_citations),
                "rate": agreement_rate,
            }

    return agreement


def generate_report(results_dir: Path, output_file: Path):
    """Generate comprehensive comparison report."""
    print("Loading results...")
    all_results = load_results(results_dir)

    if not all_results:
        print(f"No results found in {results_dir}")
        return

    print(f"Loaded {len(all_results)} model runs")

    report_lines = []

    report_lines.append("=" * 80)
    report_lines.append("LLM MODEL COMPARISON REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    # 1. Model Summary
    report_lines.append("## Models Tested")
    report_lines.append("")

    for model_key, model_data in sorted(all_results.items()):
        backend = model_data.get("backend", "unknown")
        model = model_data.get("model", "unknown")
        mode = model_data.get("mode", "unknown")
        n_classifications = model_data.get("num_classifications", 0)

        if "error" in model_data:
            status = f"ERROR: {model_data['error']}"
        else:
            status = f"{n_classifications} classifications"

        report_lines.append(f"  {model_key:50s} {backend:12s} {model:20s} {mode:6s} {status}")

    report_lines.append("")

    # 2. Classification Matrix
    report_lines.append("## Classification Comparison Matrix")
    report_lines.append("")

    matrix = create_comparison_matrix(all_results)

    # Get relationship type distributions per model
    report_lines.append("### Relationship Type Distributions")
    report_lines.append("")

    for model_key in sorted(all_results.keys()):
        if "results" not in all_results[model_key]:
            continue

        rel_counts = defaultdict(int)
        for result in all_results[model_key]["results"].values():
            rel_counts[result["relationship"]] += 1

        total = sum(rel_counts.values())

        report_lines.append(f"**{model_key}** ({total} classifications):")
        for rel, count in sorted(rel_counts.items(), key=lambda x: -x[1]):
            pct = 100 * count / total if total > 0 else 0
            report_lines.append(f"  {rel:30s} {count:3d} ({pct:5.1f}%)")
        report_lines.append("")

    # 3. Agreement Analysis
    report_lines.append("## Model Agreement Analysis")
    report_lines.append("")

    agreement = calculate_agreement(matrix)

    if agreement:
        report_lines.append("### Pairwise Agreement Rates")
        report_lines.append("")
        report_lines.append("Models are sorted by agreement rate.")
        report_lines.append("")

        for (model1, model2), data in sorted(agreement.items(), key=lambda x: -x[1]["rate"]):
            rate = data["rate"]
            agree = data["agree"]
            total = data["total"]

            report_lines.append(
                f"  {model1:40s} <-> {model2:40s}: " f"{rate:5.1%} ({agree}/{total})"
            )
        report_lines.append("")

    # 4. Short vs Full Text Comparison
    report_lines.append("## Short Context vs Full Text Comparison")
    report_lines.append("")

    # Group by base model (backend_model)
    short_vs_full = defaultdict(lambda: {"short": None, "full": None})

    for model_key, model_data in all_results.items():
        if "results" not in model_data:
            continue

        backend = model_data["backend"]
        model = model_data["model"]
        mode = model_data["mode"]

        base_key = f"{backend}_{model}"
        short_vs_full[base_key][mode] = model_key

    for base_key, modes in sorted(short_vs_full.items()):
        short_key = modes["short"]
        full_key = modes["full"]

        if not short_key or not full_key:
            continue

        # Find common citations
        common = set(all_results[short_key]["results"].keys()) & set(
            all_results[full_key]["results"].keys()
        )

        if not common:
            continue

        # Calculate agreement
        agree_count = sum(
            1
            for key in common
            if all_results[short_key]["results"][key]["relationship"]
            == all_results[full_key]["results"][key]["relationship"]
        )

        agreement_rate = agree_count / len(common)

        report_lines.append(f"**{base_key}**:")
        report_lines.append(f"  Common citations: {len(common)}")
        report_lines.append(f"  Agreement: {agreement_rate:.1%} ({agree_count}/{len(common)})")

        # Show disagreements
        disagreements = [
            key
            for key in common
            if all_results[short_key]["results"][key]["relationship"]
            != all_results[full_key]["results"][key]["relationship"]
        ]

        if disagreements[:5]:  # Show first 5
            report_lines.append("  Sample disagreements:")
            for key in disagreements[:5]:
                doi, dataset = key.split("|")
                short_rel = all_results[short_key]["results"][key]["relationship"]
                full_rel = all_results[full_key]["results"][key]["relationship"]
                report_lines.append(f"    {dataset:20s} short={short_rel:20s} full={full_rel:20s}")

        report_lines.append("")

    # 5. Confidence Analysis
    report_lines.append("## Confidence Score Analysis")
    report_lines.append("")

    for model_key in sorted(all_results.keys()):
        if "results" not in all_results[model_key]:
            continue

        confidences = [
            result["confidence"] for result in all_results[model_key]["results"].values()
        ]

        if confidences:
            avg_conf = sum(confidences) / len(confidences)
            min_conf = min(confidences)
            max_conf = max(confidences)

            report_lines.append(
                f"  {model_key:50s} " f"avg={avg_conf:.2f} min={min_conf:.2f} max={max_conf:.2f}"
            )

    report_lines.append("")

    # 6. Problematic Classifications (low agreement)
    report_lines.append("## Citations with Low Model Agreement")
    report_lines.append("")

    # Find citations where models disagree most
    disagreement_scores = {}

    for citation_key, models in matrix.items():
        if len(models) < 2:
            continue

        relationships = [rel for rel, conf in models.values()]
        unique_rels = set(relationships)

        if len(unique_rels) > 1:
            # Disagreement score: number of unique relationships
            disagreement_scores[citation_key] = len(unique_rels)

    if disagreement_scores:
        report_lines.append("Citations with most disagreement:")
        report_lines.append("")

        for citation_key in sorted(disagreement_scores, key=disagreement_scores.get, reverse=True)[
            :10
        ]:
            doi, dataset = citation_key.split("|")

            report_lines.append(f"**{dataset}** (DOI: {doi[:40]}...)")

            for model_key, (rel, conf) in matrix[citation_key].items():
                report_lines.append(f"  {model_key:40s} {rel:20s} ({conf:.2f})")

            report_lines.append("")

    # Write report
    report_text = "\n".join(report_lines)

    with open(output_file, "w") as f:
        f.write(report_text)

    print(f"\n✓ Report saved to {output_file}")
    print("\nReport preview:")
    print("=" * 80)
    print("\n".join(report_lines[:50]))
    print("...")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze model comparison results")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("model_comparison_results"),
        help="Directory containing model results",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("model_comparison_report.md"),
        help="Output report file",
    )

    args = parser.parse_args()

    if not args.results_dir.exists():
        print(f"Error: Results directory not found: {args.results_dir}")
        sys.exit(1)

    generate_report(args.results_dir, args.output)

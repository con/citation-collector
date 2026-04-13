# LLM Model Comparison Guide

This guide explains how to systematically compare different LLM models for citation classification.

## Quick Start

```bash
# 1. Run comparison across all available models (both short and full text)
cd /home/yoh/proj/dandi/dandi-bib/citations
/home/yoh/proj/dandi/citations-collector-enh-zotero/.venv/bin/python \
  /home/yoh/proj/dandi/citations-collector-enh-zotero/scripts/compare_models.py \
  dandi-full.yaml --output-dir model_comparison_results

# 2. Generate comparison report
/home/yoh/proj/dandi/citations-collector-enh-zotero/.venv/bin/python \
  /home/yoh/proj/dandi/citations-collector-enh-zotero/scripts/analyze_model_comparison.py \
  --results-dir model_comparison_results \
  --output model_comparison_report.md

# 3. View report
less model_comparison_report.md
```

## What Gets Compared

### Models Tested

**Ollama (local):**
- Automatically detects available models
- Tests fast models: qwen2, llama, phi
- Limited to 3 fastest for efficiency

**Dartmouth (if configured):**
- claude-sonnet-4-5
- Add others as needed

### Modes

Each model is tested in two modes:

1. **Short context** - Uses extracted paragraph contexts (current approach)
2. **Full text** - Uses up to 50K chars of full paper text

## Results Structure

### Individual Model Results

Each model run produces a JSON file:

```
model_comparison_results/
├── ollama_qwen2:7b_short.json
├── ollama_qwen2:7b_full.json
├── ollama_llama3.1:8b_short.json
├── ollama_llama3.1:8b_full.json
├── dartmouth_claude-sonnet-4-5_short.json
├── dartmouth_claude-sonnet-4-5_full.json
└── all_results.json
```

Format:
```json
{
  "backend": "ollama",
  "model": "qwen2:7b",
  "mode": "short",
  "timestamp": "2026-02-03T...",
  "num_classifications": 47,
  "results": {
    "10.1038/s41597-025-06285-x|dandi.001349": {
      "relationship": "Uses",
      "confidence": 0.95,
      "reasoning": "The paper analyzes neural recordings from..."
    }
  }
}
```

## Comparison Report

The analysis script generates a markdown report with:

### 1. Model Summary

Shows which models were tested and how many classifications each produced.

### 2. Relationship Type Distributions

Shows what types each model classified and their frequencies:

```
ollama_qwen2:7b_short (47 classifications):
  Uses                26 (55.3%)
  CitesAsDataSource   15 (31.9%)
  IsDocumentedBy       5 (10.6%)
  Compiles             1 ( 2.1%)
```

### 3. Model Agreement Analysis

Pairwise comparison showing which models agree:

```
ollama_qwen2:7b_short <-> ollama_llama3.1:8b_short:  85.1% (40/47)
```

### 4. Short vs Full Text Comparison

For each model, compares short context vs full text:

```
ollama_qwen2:7b:
  Common citations: 47
  Agreement: 68.1% (32/47)
  Sample disagreements:
    dandi.000402    short=Uses               full=Citation
    dandi.001349    short=CitesAsDataSource  full=cited
```

### 5. Confidence Score Analysis

Average, min, max confidence per model:

```
ollama_qwen2:7b_short       avg=0.92 min=0.80 max=0.95
ollama_qwen2:7b_full        avg=0.94 min=0.75 max=1.00
```

### 6. Problematic Classifications

Citations where models disagree most - these need manual review.

## Interpreting Results

### High Agreement (>90%)

Models are confident and consistent. These classifications are likely correct.

### Medium Agreement (70-90%)

Some variation, but reasonable. May indicate:
- Ambiguous cases (paper both Uses and Reviews dataset)
- Different but valid interpretations

### Low Agreement (<70%)

Significant disagreement. Either:
- Classification is genuinely ambiguous
- Some models are performing poorly
- Need manual expert review

### Short vs Full Text

**If short context performs better:**
- Models get confused with too much information
- Paragraph-level contexts are sufficient

**If full text performs better:**
- More context helps disambiguate
- Should reconsider extraction strategy

## Adding More Models

### Ollama

Install model locally:
```bash
ollama pull llama3.1:8b
ollama pull phi3:mini
```

The script automatically detects available models.

### Dartmouth

Edit `compare_models.py` and add to `dartmouth_models` list:

```python
dartmouth_models = [
    "claude-sonnet-4-5",
    "gpt-4-turbo",  # if available
    "claude-opus-4-5",  # if available
]
```

## Example Workflow

```bash
# 1. Ensure Ollama is running with desired models
ollama list

# 2. Ensure SSH tunnel to typhon (if using remote Ollama)
ssh -L 0.0.0.0:11434:localhost:11434 typhon -N &

# 3. Run comparison (takes ~10-30 min depending on # models)
cd /home/yoh/proj/dandi/dandi-bib/citations
python3 /path/to/compare_models.py dandi-full.yaml

# 4. Generate report
python3 /path/to/analyze_model_comparison.py

# 5. Review results
cat model_comparison_report.md

# 6. If one model clearly performs best, use it for production:
citations-collector classify dandi-full.yaml \
  --backend ollama --model llama3.1:8b \
  --confidence-threshold 0.7
```

## Notes

- **Time**: Each model takes ~5-10 minutes for 47 papers
- **Ollama models**: Only tests models already installed locally
- **Full text mode**: Uses first 50K chars (truncates longer papers)
- **Results are cached**: Individual model JSONs can be reused for analysis
- **Manual review**: High-disagreement cases should be manually reviewed

## Troubleshooting

**"No Ollama models found"**
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- If using SSH tunnel, ensure it's bound to 0.0.0.0

**"Dartmouth API not configured"**
- Check `~/.git/secrets` has DARTMOUTH_API_TOKEN

**Models returning invalid types**
- Full text mode sometimes confuses models
- This is expected and part of evaluation
- Report shows which models follow instructions better

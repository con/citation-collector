# Documentation Overview

## Quick Start

1. **[SETUP-LLM.md](SETUP-LLM.md)** - Set up LLM backends (Ollama, Dartmouth, OpenRouter, OpenAI)
2. **[CLASSIFICATION-WORKFLOW.md](CLASSIFICATION-WORKFLOW.md)** - Complete workflow from extraction to classification

## Reference Guides

### Core Functionality
- **[CLASSIFICATION-METADATA.md](CLASSIFICATION-METADATA.md)** - Schema, architecture, and metadata fields
- **[CONTEXT-EXTRACTION.md](CONTEXT-EXTRACTION.md)** - How context extraction works from PDFs/HTMLs
- **[AVAILABLE-MODELS.md](AVAILABLE-MODELS.md)** - Catalog of 31+ available models across Dartmouth tiers

### Advanced Topics
- **[MODEL-COMPARISON.md](MODEL-COMPARISON.md)** - Compare multiple models for quality assessment

## Typical Workflow

```bash
# 1. Set up LLM backend (see SETUP-LLM.md)
source /path/to/secrets
# or: ssh -L 11434:localhost:11434 server -N

# 2. Extract contexts from PDFs
citations-collector extract-contexts collection.yaml

# 3. Classify with LLM
citations-collector classify collection.yaml \
  --backend dartmouth \
  --model google.gemma-3-27b-it \
  --confidence-threshold 0.7

# 4. (Optional) Compare multiple models
python scripts/compare_models.py collection.yaml
python scripts/analyze_model_comparison.py
```

## Example Deployment

For a complete production example, see [dandi-bib](https://github.com/dandi/dandi-bib) which uses citations-collector for DANDI Archive citation tracking with automated workflows.

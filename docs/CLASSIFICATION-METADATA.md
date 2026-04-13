# Classification Metadata

## Overview

The schema includes **minimal metadata fields** in the main citations table for quick filtering, while full classification details are stored per-paper in `classifications.json` files. This enables:

- **Reproducibility**: Track which model classified each relationship
- **Quality control**: Filter by confidence, identify classifications needing review
- **Model comparison**: Store results from multiple models, compare them
- **Audit trail**: Full provenance from classification through human review
- **Incremental updates**: Skip already-classified citations
- **Clean main table**: Only 4 metadata columns, full details stored separately

## Architecture

### Two-Level Storage

**Level 1: Main citations table (citations.tsv)**
- Minimal metadata (4 fields) for quick filtering
- Points to detailed results in per-paper files

**Level 2: Per-paper classifications (pdfs/{doi}/classifications.json)**
- All classification attempts from all models
- Full reasoning, contexts, timestamps
- Enables model comparison and ensemble voting

```
pdfs/10.1234/example/
├── article.pdf
├── article.bib
├── extracted_citations.json      # Contexts per dataset
└── classifications.json           # All model results per dataset
```

## Schema Fields (Main Table)

### `classification_method` (enum)
How the citation relationship was determined.

**Values:**
- `manual` - Manually classified by human curator
- `llm` - Classified by Large Language Model

### `classification_model` (string, optional)
LLM model identifier if `classification_method` is `llm`.

**Empty for manual classifications.**

**Examples:**
- `google.gemma-3-27b-it` (Dartmouth)
- `anthropic.claude-haiku-4-5-20251001` (Dartmouth)
- `qwen2:7b` (Ollama)

### `classification_confidence` (float, 0.0-1.0, optional)
Confidence score from LLM classification.

**Empty for manual classifications.**

**Usage:**
- Filter low-confidence: `< 0.7`
- Identify high-confidence: `>= 0.9`
- Track model calibration

### `classification_reviewed` (boolean, default: false)
Has a human reviewed and approved this classification?

**Workflow:**
1. LLM classifies → `classification_reviewed=false`
2. Human reviews → Update to `classification_reviewed=true`
3. Filter unreviewed: `WHERE classification_reviewed=false AND classification_confidence<0.8`

## Per-Paper Classifications Storage

### classifications.json Format

Stored in `pdfs/{doi}/classifications.json`:

```json
[
  {
    "item_id": "dandi.000020",
    "item_flavor": "0.210913.1639",
    "model": "google.gemma-3-27b-it",
    "backend": "dartmouth",
    "relationship_type": "Uses",
    "confidence": 0.92,
    "reasoning": "Paper analyzes neural recordings from the dataset...",
    "timestamp": "2026-02-04T14:30:00",
    "mode": "short_context"
  },
  {
    "item_id": "dandi.000020",
    "item_flavor": "0.210913.1639",
    "model": "anthropic.claude-haiku-4-5",
    "backend": "dartmouth",
    "relationship_type": "CitesAsDataSource",
    "confidence": 0.85,
    "reasoning": "Work explicitly cites dataset as data source...",
    "timestamp": "2026-02-04T14:32:00",
    "mode": "short_context"
  }
]
```

**Benefits:**
- Store results from multiple models
- Compare model agreement
- Full reasoning preserved (not truncated)
- Timestamps for audit trail
- Co-located with paper data

## TSV Column Order

Only 4 new columns added between `curated_date` and `oa_status`:

```
...
curated_by
curated_date
classification_method          ← NEW (manual, llm)
classification_model           ← NEW (model ID or empty)
classification_confidence      ← NEW (0.0-1.0 or empty)
classification_reviewed        ← NEW (true/false)
oa_status
pdf_url
pdf_path
```

## Example TSV Rows

```tsv
item_id       item_flavor      citation_doi  citation_relationship  classification_method  classification_model     classification_confidence  classification_reviewed
dandi.000020  0.210913.1639   10.1234/x     Uses                  llm                    google.gemma-3-27b-it   0.92                          false
dandi.000037  0.220126.1903   10.5678/y     IsDocumentedBy        manual                                                                       true
dandi.000053  0.230601.2018   10.9012/z     CitesAsDataSource     llm                    anthropic.claude-haiku  0.78                          true
```

## Backward Compatibility

- **Old TSVs** without these columns load fine (fields are optional)
- **Empty values** in TSV are treated as `None`/`null`
- **Default values**:
  - `classification_reviewed` defaults to `false`
  - All other fields default to `None`

## Usage Examples

### Filter by confidence threshold
```python
from citations_collector.persistence import tsv_io

citations = tsv_io.load_citations("citations.tsv")

# Find low-confidence classifications needing review
needs_review = [
    c for c in citations
    if c.classification_method == "llm"
    and c.classification_confidence
    and c.classification_confidence < 0.7
    and not c.classification_reviewed
]

print(f"{len(needs_review)} citations need review")
```

### Compare models (from main table)
```python
from collections import defaultdict

by_model = defaultdict(list)
for c in citations:
    if c.classification_model:
        by_model[c.classification_model].append(c.classification_confidence)

for model, confidences in by_model.items():
    avg_conf = sum(confidences) / len(confidences)
    print(f"{model}: {avg_conf:.2f} avg confidence ({len(confidences)} classifications)")
```

### Compare models for a specific paper (from classifications.json)
```python
from pathlib import Path
from citations_collector.classifications_storage import ClassificationsStorage

storage = ClassificationsStorage(Path("pdfs"))

# Get all classifications for a paper
doi = "10.1234/example"
item_id = "dandi.000020"
item_flavor = "0.210913.1639"

classifications = storage.get_classifications_for_item(doi, item_id, item_flavor)

print(f"Model results for {doi} citing {item_id}:")
for c in classifications:
    print(f"  {c.model}: {c.relationship_type} (confidence: {c.confidence:.2f})")
    print(f"    {c.reasoning[:100]}...")
```

### Track review progress
```python
llm_classified = [c for c in citations if c.classification_method == "llm"]
reviewed = [c for c in llm_classified if c.classification_reviewed]

print(f"Review progress: {len(reviewed)}/{len(llm_classified)} ({len(reviewed)/len(llm_classified)*100:.1f}%)")
```

## CLI Integration

### Single Model Classification

```bash
# Classify with a single model
citations-collector classify collection.yaml \
  --backend dartmouth \
  --model google.gemma-3-27b-it \
  --confidence-threshold 0.7

# This will:
# 1. Store full results in pdfs/{doi}/classifications.json
# 2. Update citations.tsv with:
#    - classification_method: "llm"
#    - classification_model: "google.gemma-3-27b-it"
#    - classification_confidence: from LLM (0.0-1.0)
#    - classification_reviewed: false
```

### Multiple Model Comparison

```bash
# Run multiple models and save all results
citations-collector classify collection.yaml \
  --models google.gemma-3-27b-it,anthropic.claude-haiku-4-5,openai.gpt-oss-120b \
  --save-all

# This creates classifications.json with results from all models
# Then select best classification for main table:

# Option 1: Highest confidence
citations-collector select-best collection.yaml --strategy highest_confidence

# Option 2: Majority vote (requires at least 2 models to agree)
citations-collector select-best collection.yaml --strategy majority_vote --min-agreement 2

# Option 3: Specific model priority
citations-collector select-best collection.yaml --preferred-model google.gemma-3-27b-it
```

### Manual Review Workflow

```bash
# Review low-confidence LLM classifications
citations-collector classify collection.yaml --review --confidence-threshold 0.8

# Interactive:
# - Shows LLM classification and reasoning
# - Lets human approve, reject, or change
# - Sets classification_reviewed=true after approval
# - Updates classification_method="manual" if changed
```

## Model Comparison Results

Based on systematic testing (see `docs/MODEL-COMPARISON.md`):

| Model | Backend | Avg Confidence | Performance |
|-------|---------|----------------|-------------|
| **google.gemma-3-27b-it** | Dartmouth (FREE) | 0.84 | ✓ Best |
| anthropic.claude-haiku-4-5 | Dartmouth ($) | 0.82 | Good |
| openai.gpt-oss-120b | Dartmouth (FREE) | 0.78 | Fair (short), Poor (full) |
| qwen2:7b | Ollama | 0.92 | Good (short only) |

**Recommendation:** Use `google.gemma-3-27b-it` with `short_context` mode for production classification.

## Migration

### Existing TSVs
No migration needed - old TSVs load fine with new schema. New fields will be `None` for existing records.

### Adding metadata to existing classifications
If you have citations already classified but without metadata:

```python
from citations_collector.persistence import tsv_io
from citations_collector.models import ClassificationMethod

citations = tsv_io.load_citations("citations.tsv")

for c in citations:
    if c.citation_relationship and not c.classification_method:
        # Assume manual classification if no metadata
        c.classification_method = ClassificationMethod.manual
        c.classification_reviewed = True  # Assume already reviewed

tsv_io.save_citations(citations, "citations.tsv")
```

## Future Enhancements

### In classifications.json
Potential additions to per-paper storage:
- `prompt_version` - Track prompt template versions
- `api_cost` - API cost per classification
- `latency_ms` - Response time in milliseconds
- `context_tokens` - Number of input tokens
- `contexts_hash` - Verify same contexts were used across models
- `top_n_predictions` - Store alternative predictions with scores

### In main table
- Could add `classification_consensus` (0.0-1.0) for multi-model agreement score

# Classification Workflow

This document demonstrates the complete classification workflow with the new metadata architecture.

## Quick Start

```bash
# 1. Classify citations using LLM
citations-collector classify collection.yaml \
  --backend dartmouth \
  --model google.gemma-3-27b-it \
  --confidence-threshold 0.7

# 2. Review low-confidence classifications
citations-collector classify collection.yaml \
  --backend dartmouth \
  --model google.gemma-3-27b-it \
  --review \
  --confidence-threshold 0.8
```

## Complete Example

### Setup

```bash
cd /home/yoh/proj/dandi/dandi-bib/citations

# Collection structure:
# - dandi-full.yaml (collection config)
# - dandi-full-citations.tsv (citations with metadata)
# - pdfs/{doi}/extracted_citations.json (contexts)
```

### Run Classification

```bash
# Set API key (if using Dartmouth)
export OPENAI_API_KEY="your-key-here"

# Classify all papers with extracted contexts
citations-collector classify dandi-full.yaml \
  --backend dartmouth \
  --model google.gemma-3-27b-it \
  --confidence-threshold 0.7
```

### What Happens

**For each paper with `extracted_citations.json`:**

1. **Load contexts** from `pdfs/{doi}/extracted_citations.json`
   ```json
   {
     "paper_doi": "10.64898/2026.01.08.698522",
     "citations": [
       {
         "dataset_id": "dandi.000020",
         "dataset_mentions": [
           {
             "context": "Allen Institute ... Patch-seq recordings ...",
             "page": 16
           }
         ]
       }
     ]
   }
   ```

2. **Send to LLM** for classification
   - Model: `google.gemma-3-27b-it`
   - Input: Paper metadata + contexts
   - Output: Relationship type + confidence + reasoning

3. **Save detailed result** to `pdfs/{doi}/classifications.json`
   ```json
   [
     {
       "item_id": "dandi.000020",
       "item_flavor": "0.210913.1639",
       "model": "google.gemma-3-27b-it",
       "backend": "dartmouth",
       "relationship_type": "Uses",
       "confidence": 0.92,
       "reasoning": "Paper analyzes neural recordings...",
       "timestamp": "2026-02-05T10:03:01.932777",
       "mode": "short_context"
     }
   ]
   ```

4. **Update citations TSV** with metadata
   | Field | Value |
   |-------|-------|
   | `citation_relationships` | `Uses` |
   | `classification_method` | `llm` |
   | `classification_model` | `google.gemma-3-27b-it` |
   | `classification_confidence` | `0.92` |
   | `classification_reviewed` | `false` |

### Output

```
================================================================================
Loading collection from dandi-full.yaml
Loaded 94 citations from dandi-full-citations.tsv
Using dartmouth backend for classification
Model: google.gemma-3-27b-it
Confidence threshold: 0.70
Output directory: pdfs
Mode: Extracted contexts

Found 44 papers to classify

Classifying: 10.64898/2026.01.08.698522
  ✓ dandi.000020: Uses (confidence: 0.92)

Classifying: 10.1038/s41597-025-06285-x
  ✓ dandi.000563: Uses (confidence: 0.88)
  ✓ dandi.000617: Uses (confidence: 0.90)
  ⚠ dandi.000690: Uses (confidence: 0.65)
    Reasoning: Paper mentions analyzing data but relationship unclear...

...

================================================================================
Classified: 47
Low confidence: 8
Errors: 0

Saving detailed results to classifications.json files...
Updating dandi-full-citations.tsv...
✓ Saved detailed results for 47 citations
✓ Updated 47 citations in dandi-full-citations.tsv
```

## Multi-Model Comparison

### Run Multiple Models

```bash
# Option 1: Run models sequentially, save all results
for model in google.gemma-3-27b-it anthropic.claude-haiku-4-5 openai.gpt-oss-120b; do
  citations-collector classify dandi-full.yaml \
    --backend dartmouth \
    --model "$model" \
    --confidence-threshold 0.7
done
```

After running multiple models, `classifications.json` contains all results:

```json
[
  {
    "item_id": "dandi.000020",
    "item_flavor": "0.210913.1639",
    "model": "google.gemma-3-27b-it",
    "relationship_type": "Uses",
    "confidence": 0.92,
    ...
  },
  {
    "item_id": "dandi.000020",
    "item_flavor": "0.210913.1639",
    "model": "anthropic.claude-haiku-4-5",
    "relationship_type": "CitesAsDataSource",
    "confidence": 0.85,
    ...
  },
  {
    "item_id": "dandi.000020",
    "item_flavor": "0.210913.1639",
    "model": "openai.gpt-oss-120b",
    "relationship_type": "Uses",
    "confidence": 0.78,
    ...
  }
]
```

### Compare Results

```python
from pathlib import Path
from citations_collector.classifications_storage import ClassificationsStorage

storage = ClassificationsStorage(Path("pdfs"))

# Get all classifications for a citation
doi = "10.64898/2026.01.08.698522"
item_id = "dandi.000020"
item_flavor = "0.210913.1639"

classifications = storage.get_classifications_for_item(doi, item_id, item_flavor)

print(f"Models tested: {len(classifications)}")
for c in classifications:
    print(f"  {c.model:35} → {c.relationship_type:20} (conf: {c.confidence:.2f})")

# Output:
# Models tested: 3
#   google.gemma-3-27b-it               → Uses                 (conf: 0.92)
#   anthropic.claude-haiku-4-5          → CitesAsDataSource    (conf: 0.85)
#   openai.gpt-oss-120b                 → Uses                 (conf: 0.78)
```

### Select Best Classification

**Strategy 1: Highest Confidence**
```python
best = max(classifications, key=lambda x: x.confidence)
# → google.gemma-3-27b-it: Uses (0.92)
```

**Strategy 2: Majority Vote**
```python
from collections import Counter

votes = Counter(c.relationship_type for c in classifications)
winner = votes.most_common(1)[0][0]
# → Uses (2 votes vs 1 for CitesAsDataSource)
```

**Strategy 3: Model Priority**
```python
# Prefer specific model
preferred = next(
    (c for c in classifications if c.model == "google.gemma-3-27b-it"),
    classifications[0]
)
```

## Review Workflow

### Interactive Review

```bash
# Review only low-confidence classifications
citations-collector classify dandi-full.yaml \
  --backend dartmouth \
  --model google.gemma-3-27b-it \
  --review \
  --confidence-threshold 0.8
```

For each low-confidence classification:
```
Classifying: 10.1038/s41597-025-06285-x
  ⚠ dandi.000690: Uses (confidence: 0.65)
    Reasoning: Paper mentions analyzing data but relationship unclear...

    Context:
      [1] We analyzed neural recordings from dataset dandi.000690 to...
      [2] Data was obtained from the DANDI archive (dandi.000690)...

    Suggested: Uses (0.65)
    Accept/Edit/Skip? (a/e/s): e
    Enter relationship type [Uses]: CitesAsDataSource
    ✓ Updated to: CitesAsDataSource (manual review)
```

### Result

When human reviews/edits a classification:
- TSV updated with:
  - `classification_method`: `llm` (still LLM-classified)
  - `classification_reviewed`: `true` (human verified)
- `classifications.json` retains original LLM result
- Can track which classifications were human-verified

## Query and Filter

### Find Unreviewed LLM Classifications

```python
from citations_collector.persistence import tsv_io

citations = tsv_io.load_citations("dandi-full-citations.tsv")

# Find low-confidence, unreviewed
needs_review = [
    c for c in citations
    if c.classification_method == "llm"
    and c.classification_confidence
    and c.classification_confidence < 0.8
    and not c.classification_reviewed
]

print(f"{len(needs_review)} citations need review")
```

### Compare Model Performance

```python
from collections import defaultdict

by_model = defaultdict(list)
for c in citations:
    if c.classification_model:
        by_model[c.classification_model].append(c.classification_confidence)

for model, confidences in sorted(by_model.items()):
    avg_conf = sum(confidences) / len(confidences)
    count = len(confidences)
    print(f"{model:35} {avg_conf:.2f} avg ({count} citations)")

# Output:
# anthropic.claude-haiku-4-5          0.82 avg (15 citations)
# google.gemma-3-27b-it               0.84 avg (32 citations)
```

## File Structure

```
pdfs/
├── 10.64898/
│   └── 2026.01.08.698522/
│       ├── article.pdf
│       ├── article.bib
│       ├── extracted_citations.json      # Input: contexts
│       └── classifications.json          # Output: all model results
├── 10.1038/
│   └── s41597-025-06285-x/
│       ├── article.pdf
│       ├── extracted_citations.json
│       └── classifications.json
...

dandi-full-citations.tsv                  # Main table with 4 metadata columns
```

## Benefits

1. **Clean main table** - Only 4 classification columns
2. **Full provenance** - Complete history in classifications.json
3. **Model comparison** - Store and compare multiple models
4. **Ensemble voting** - Combine models for better accuracy
5. **Incremental** - Add new model results without losing old ones
6. **Audit trail** - Timestamp + reasoning for every classification
7. **Co-located** - Classification data lives with paper PDFs

## Next Steps

### Automated Ensemble

Create a script to automatically select best classification:

```bash
# Run 3 models
for model in gemma claude gpt; do
  citations-collector classify collection.yaml --model $model
done

# Select best via majority vote
python scripts/select_best_classifications.py \
  --strategy majority_vote \
  --min-agreement 2
```

### Quality Metrics

Track classification quality over time:

```python
# Generate report
python scripts/classification_report.py dandi-full.yaml

# Output:
# Classification Quality Report
# =============================
# Total citations: 94
# LLM classified: 47 (50%)
# Human reviewed: 12 (26% of LLM)
# Avg confidence: 0.84
# Low confidence (<0.7): 8 (17%)
# Model breakdown:
#   google.gemma-3-27b-it: 32 (avg: 0.84)
#   anthropic.claude-haiku: 15 (avg: 0.82)
```

# Context Extraction Guide

## Overview

The context extraction system finds dataset mentions in PDFs and HTML files, extracts paragraph-level contexts around those mentions, and saves them as `extracted_citations.json` alongside each paper. These contexts are then used by the LLM classifier to determine citation relationship types.

## Quick Start

### 1. Ensure PDFs are Available

The extract-contexts command expects PDFs in this structure:
```
pdfs/
├── 10.1038/
│   └── s41597-023-02214-y/
│       └── article.pdf
├── 10.1101/
│   └── 2024.01.15.575901/
│       └── article.pdf
```

### 2. Run Context Extraction

```bash
citations-collector extract-contexts collection.yaml
```

This will:
1. Read citations from the TSV file
2. Group by paper DOI
3. Find PDFs/HTMLs for each paper
4. Extract dataset mentions and contexts
5. Save `extracted_citations.json` for each paper
6. Optionally add to git-annex with OA status metadata

### 3. Review Output

```bash
cat pdfs/10.1038/s41597-023-02214-y/extracted_citations.json
```

Example output:
```json
{
  "paper_doi": "10.1038/s41597-023-02214-y",
  "paper_title": "A comprehensive dataset of...",
  "paper_journal": "Scientific Data",
  "paper_year": 2024,
  "oa_status": "gold",
  "extraction_date": "2026-02-01T12:00:00",
  "extraction_method": "pdfplumber",
  "citations": [
    {
      "dataset_id": "dandi:000003",
      "dataset_mentions": [
        {
          "context": "We analyzed neural recordings from DANDI:000003...",
          "page": 3,
          "section": null,
          "source": "pdf"
        },
        {
          "context": "The DANDI:000003 dataset contains high-quality...",
          "page": 8,
          "section": null,
          "source": "pdf"
        }
      ]
    }
  ]
}
```

## CLI Usage

### Basic Command

```bash
citations-collector extract-contexts collection.yaml
```

### Options

```bash
citations-collector extract-contexts collection.yaml \
    --output-dir pdfs/ \          # Override pdfs.output_dir from YAML
    --git-annex \                  # Add to git-annex with metadata
    --overwrite \                  # Re-extract even if exists
    --dry-run                      # Show what would be done
```

### Configuration via YAML

```yaml
# collection.yaml

output_tsv: citations.tsv

pdfs:
  output_dir: pdfs/
  git_annex: true  # Automatically add extracted files to git-annex
```

## Git-Annex Integration

When `--git-annex` is enabled, extracted_citations.json files are added to git-annex with metadata tags based on the paper's open access status.

### Metadata Tags

```bash
# For open access papers (gold/green/hybrid)
git annex metadata pdfs/10.1038/.../extracted_citations.json
# Output:
#   oa_status=gold
#   url=https://example.com/paper.pdf

# For closed access papers
git annex metadata pdfs/10.1101/.../extracted_citations.json
# Output:
#   oa_status=closed
#   tag: distribution-restricted
```

### Query by Metadata

```bash
# Find all gold OA extracted contexts
git annex find --metadata oa_status=gold

# Find all distribution-restricted files
git annex find --metadata tag=distribution-restricted
```

## How It Works

### 1. Dataset Pattern Matching

The extractor finds dataset IDs using regex patterns:

```python
patterns = {
    "dandi": [
        r"DANDI[:\s]+(\d{6})",           # DANDI:000003 or DANDI 000003
        r"dandiarchive\.org/dandiset/(\d{6})",  # URL form
        r"doi\.org/10.48324/dandi\.(\d{6})",    # DOI form
    ],
}
```

Matches:
- `DANDI:000003`
- `DANDI 000003`
- `dandiarchive.org/dandiset/000003`
- `doi.org/10.48324/dandi.000003`

### 2. Context Extraction

For each dataset mention found:

1. **Locate position** in text
2. **Find paragraph boundaries** (double newlines or ±250 chars)
3. **Clean whitespace** (normalize to single spaces)
4. **Deduplicate** (avoid same context appearing multiple times)

**PDF-specific**:
- Extracts page numbers
- TODO: Extract section headers

**HTML-specific**:
- Extracts section headers from `<h1>`, `<h2>`, `<h3>`, `<h4>` tags
- Preserves paragraph structure

### 3. Output Format

Each paper gets one `extracted_citations.json` file containing:

- **Paper metadata**: DOI, title, journal, year, OA status
- **Extraction metadata**: Date, method (pdfplumber/beautifulsoup)
- **Citations**: List of datasets mentioned
  - **dataset_id**: e.g., "dandi:000003"
  - **dataset_mentions**: List of contexts
    - **context**: Paragraph text (~500 chars max)
    - **page**: Page number (PDFs only)
    - **section**: Section header (HTMLs only)
    - **source**: "pdf" or "html"

## Examples

### Example 1: Extract from Specific Directory

```bash
citations-collector extract-contexts collection.yaml \
    --output-dir /path/to/pdfs
```

### Example 2: Dry Run to Preview

```bash
citations-collector extract-contexts collection.yaml --dry-run
```

Output:
```
Loading collection from collection.yaml
Found 150 papers citing 300 datasets
Output directory: pdfs/

[DRY RUN] Would extract: 10.1038/s41597-023-02214-y
  Datasets: dandi:000003, dandi:000020
  Source: PDF

[DRY RUN] Would extract: 10.1101/2024.01.15.575901
  Datasets: dandi:000108
  Source: PDF

...

Extracted: 150
Skipped: 0
Errors: 0
```

### Example 3: Re-extract Everything

```bash
citations-collector extract-contexts collection.yaml --overwrite
```

### Example 4: Extract with Git-Annex

```bash
citations-collector extract-contexts collection.yaml \
    --git-annex \
    --output-dir /mnt/storage/pdfs
```

## Troubleshooting

### "No PDF/HTML found"

**Problem**: PDFs not in expected directory structure

**Solution**: Ensure PDFs are organized as `output_dir/DOI/article.pdf`

```bash
# Example structure
pdfs/
├── 10.1038/
│   └── s41597-023-02214-y/
│       └── article.pdf  # ✓ Correct
```

### "Already extracted" (skipping papers)

**Problem**: extracted_citations.json already exists

**Solution**: Use `--overwrite` to force re-extraction

```bash
citations-collector extract-contexts collection.yaml --overwrite
```

### No dataset mentions found

**Problem**: Dataset IDs not in expected format

**Solution**: Check if IDs match patterns:
- PDFs: May have OCR errors (e.g., "DAND1:000003")
- Custom patterns needed for other repositories

Add custom patterns:
```python
from citations_collector.context_extractor import ContextExtractor

extractor = ContextExtractor(dataset_patterns={
    "dandi": [r"DANDI[:\s]+(\d{6})", ...],
    "openneuro": [r"OpenNeuro[:\s]+ds(\d+)"],  # Custom
})
```

## Dependencies

Required packages (installed with `[extraction]` extra):

```bash
pip install "citations-collector[extraction]"
```

Includes:
- `pdfplumber>=0.10.0` - PDF text extraction
- `beautifulsoup4>=4.12.0` - HTML parsing
- `lxml>=4.9.0` - Fast HTML parser

## Next Steps

After extracting contexts:

1. **Classify citations** using LLM:
   ```bash
   citations-collector classify collection.yaml
   ```

2. **Review low-confidence classifications**:
   ```bash
   citations-collector classify collection.yaml --review
   ```

See [LLM Integration Guide](SETUP-LLM.md) for classification details.

## Advanced Usage

### Custom Dataset Patterns

```python
from citations_collector.context_extractor import ContextExtractor

# Add patterns for new repository
extractor = ContextExtractor(dataset_patterns={
    "dandi": [r"DANDI[:\s]+(\d{6})", ...],
    "zenodo": [r"zenodo\.org/record/(\d+)"],
    "figshare": [r"figshare\.com/articles/(\d+)"],
})
```

### Programmatic Usage

```python
from pathlib import Path
from citations_collector.context_extractor import ContextExtractor

extractor = ContextExtractor()

# Extract from single PDF
extracted = extractor.extract_from_pdf(
    pdf_path=Path("article.pdf"),
    target_datasets=["dandi:000003", "dandi:000020"],
)

# Save
extractor.save_extracted_citations(
    extracted,
    output_path=Path("extracted_citations.json"),
)
```

### Load and Analyze

```python
import json
from pathlib import Path

# Load extracted contexts
with open("pdfs/10.1038/.../extracted_citations.json") as f:
    data = json.load(f)

# Count total mentions
total_mentions = sum(
    len(c["dataset_mentions"]) for c in data["citations"]
)

print(f"Found {total_mentions} mentions of {len(data['citations'])} datasets")

# Get all contexts for a specific dataset
for citation in data["citations"]:
    if citation["dataset_id"] == "dandi:000003":
        for mention in citation["dataset_mentions"]:
            print(f"Page {mention['page']}: {mention['context']}")
```

## Performance

**Extraction speed:**
- PDF: ~2-5 seconds per paper (depends on length)
- HTML: ~0.5-1 second per paper

**For 1000 papers:**
- Estimated time: ~30-60 minutes
- Can run in background with progress tracking

**Storage:**
- extracted_citations.json: ~1-10 KB per paper
- 1000 papers: ~1-10 MB total

## See Also

- [LLM Setup Guide](SETUP-LLM.md) - Configure LLM backends
- [Classification Guide](CLASSIFICATION.md) - Classify relationship types
- [Git-Annex Guide](GIT-ANNEX.md) - Manage large files with metadata

# GROBID: Future Enhancement for Citation Extraction

## What is GROBID?

**GROBID** (GeneRation Of BIbliographic Data) is a machine learning library that extracts structured data from scientific PDFs.

**Key capabilities:**
- Bibliographic reference extraction
- Citation context recognition (linking in-text citations to references)
- Full-text structuring (sections, tables, figures)
- Author/affiliation parsing
- High accuracy: 0.87-0.90 F1-score

## How It Could Enhance Our System

### Current Approach (pdfplumber + regex)

1. Extract text with pdfplumber
2. Search for patterns like "DANDI:000003" or "10.48324/dandi.000020"
3. Extract ~400 chars around match
4. Use context for LLM classification

**Limitations:**
- No understanding of document structure
- May miss references that don't use exact patterns
- Can't distinguish between bibliography entry vs. actual usage in text
- No citation-reference linking

### GROBID Approach

GROBID provides structured XML/TEI output with:
- Full bibliography with parsed references
- Citation callouts linked to bibliography entries
- Section structure (Methods, Results, Discussion)
- Coordinates for each element

**Benefits:**
- Better context extraction (actual paragraphs, not arbitrary char windows)
- Citation-reference linking (know which mention links to which dataset)
- Section awareness (e.g., prioritize Methods/Results over Introduction)
- Works even when datasets mentioned without exact ID patterns

## Integration Scenarios

### Scenario 1: Full Replacement

Replace `context_extractor.py` with GROBID-based extraction. Send PDF to GROBID service, parse TEI XML, find references matching dataset patterns, extract citation callouts and surrounding context.

### Scenario 2: Hybrid Approach (Recommended)

Use pdfplumber for simple cases, GROBID for complex:
- Try simple pattern matching first
- If too few contexts found, fall back to GROBID for deeper analysis
- Keeps dependencies minimal for common cases

### Scenario 3: Bibliography Parsing Only

Use GROBID to extract full bibliography, find dataset references even when the dataset ID only appears in the reference list (not in the body text). This lets us find citations like "We analyzed data from [23]" where [23] links to a DANDI dataset.

## Performance Considerations

| Metric | pdfplumber | GROBID |
|--------|-----------|--------|
| Speed | ~10-20 PDFs/sec | ~2.5 PDFs/sec (full) |
| CPU usage | Light | Higher (ML models) |
| Dependencies | Python package | Java service (Docker) |
| Accuracy | Pattern-dependent | 0.87-0.90 F1 |

## Deployment Options

1. **Docker (easiest):** `docker run -p 8070:8070 lfoppiano/grobid:0.8.0`
2. **Self-hosted service:** Java application with RESTful API
3. **Batch processing:** Local Java library, no network overhead

## Recommendation

Start with hybrid approach - use pdfplumber as default, add optional GROBID support for papers where deeper analysis is needed. Make GROBID an optional dependency that degrades gracefully when unavailable.

## References

- [GROBID documentation](https://grobid.readthedocs.io/)
- Suggested by @tekrajchhetri in [PR #4](https://github.com/con/citations-collector/pull/4)

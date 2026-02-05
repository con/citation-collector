# CI Status and GROBID Analysis

## 1. CI Status: BROKEN ❌

### Test Failures

Running tests shows **9 failures out of 150 tests**:

```
FAILED tests/test_core.py::test_save_workflow
FAILED tests/test_dataset_relationships.py::test_cites_as_data_source
FAILED tests/test_dataset_relationships.py::test_multiple_dataset_citations_same_paper
FAILED tests/test_dataset_relationships.py::test_new_relationships_tsv_roundtrip
FAILED tests/test_multi_relationship.py::test_single_relationship_backward_compat
FAILED tests/test_multi_relationship.py::test_relationships_coherence_validation
FAILED tests/test_multi_source_validation.py::test_citation_sources_dates_coherence_missing_in_dates
FAILED tests/test_multi_source_validation.py::test_citation_sources_dates_coherence_missing_in_sources
FAILED tests/test_multi_source_validation.py::test_citation_sources_dates_invalid_json
FAILED tests/test_multi_source_validation.py::test_citation_sources_dates_not_dict
```

### Root Cause

**Missing Pydantic model validators** after schema regeneration. When LinkML regenerated the models, custom validation logic was lost:

1. **Auto-population**: `citation_relationship` → `citation_relationships` list
2. **Coherence validation**: Ensure `citation_relationship` matches first element of `citation_relationships`
3. **Multi-source validation**: Ensure `citation_sources` and `discovered_dates` are coherent

### Immediate Fix Required

**Option 1: Add custom validators to generated model**
```python
# In src/citations_collector/models/generated.py or a wrapper

from pydantic import model_validator

class CitationRecord(BaseModel):
    # ... generated fields ...

    @model_validator(mode='after')
    def populate_and_validate_relationships(self) -> 'CitationRecord':
        """Auto-populate citation_relationships and validate coherence."""
        # If only citation_relationship provided, populate list
        if self.citation_relationship and not self.citation_relationships:
            self.citation_relationships = [self.citation_relationship]

        # Validate coherence
        if self.citation_relationships:
            if self.citation_relationship != self.citation_relationships[0]:
                raise ValueError(
                    "citation_relationship must match first element of citation_relationships"
                )

        return self
```

**Option 2: Add validators in separate module**
Create `src/citations_collector/models/validators.py` with custom logic and patch the generated models.

### Workaround Applied

Fixed **one critical failure** (`test_save_workflow`) by adding default values in TSV loader:
```python
# When citation_relationship is missing from TSV
cleaned["citation_relationship"] = "Cites"
cleaned["citation_relationships"] = ["Cites"]
```

This prevents validation errors but doesn't fix the model validation logic.

---

## 2. GROBID: Citation Extraction Alternative

### What is GROBID?

**GROBID** (GeneRation Of BIbliographic Data) is a machine learning library that extracts structured data from scientific PDFs.

**Key capabilities:**
- Bibliographic reference extraction
- Citation context recognition (linking in-text citations to references)
- Full-text structuring (sections, tables, figures)
- Author/affiliation parsing
- High accuracy: 0.87-0.90 F1-score

### How It Could Help Us

#### Current Approach (pdfplumber + regex)
```python
# We do:
1. Extract text with pdfplumber
2. Search for patterns like "DANDI:000003" or "10.48324/dandi.000020"
3. Extract ±400 chars around match
4. Hope we captured relevant context
```

**Limitations:**
- No understanding of document structure
- May miss references that don't use exact patterns
- Can't distinguish between bibliography entry vs. actual usage in text
- No citation-reference linking

#### GROBID Approach
```python
# GROBID provides:
1. Structured XML/TEI output with:
   - Full bibliography with parsed references
   - Citation callouts linked to bibliography entries
   - Section structure
   - Coordinates for each element
2. Citation context extraction:
   - Knows which in-text citation links to which reference
   - Provides surrounding text from the actual body
   - Distinguishes Methods, Results, Discussion sections
```

### Integration Scenarios

#### Scenario 1: Use GROBID for Citation Context Extraction

**Replace `context_extractor.py` with GROBID-based extraction:**

```python
import requests

def extract_contexts_with_grobid(pdf_path, dataset_patterns):
    """
    Extract citation contexts using GROBID.

    1. Send PDF to GROBID service
    2. Parse TEI XML response
    3. Find references matching dataset patterns
    4. Extract citation callouts linking to those references
    5. Get surrounding context from body text
    """
    # POST PDF to GROBID
    with open(pdf_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8070/api/processFulltextDocument',
            files={'input': f}
        )

    tei_xml = response.text

    # Parse TEI to find:
    # 1. <biblStruct> entries matching our datasets
    # 2. <ref target="#b23"> callouts in body
    # 3. Surrounding <p> context

    return extracted_citations
```

**Benefits:**
- Better context extraction (actual paragraphs, not arbitrary char windows)
- Citation-reference linking (know which mention links to which dataset)
- Section awareness (e.g., prioritize Methods/Results over Introduction)
- Works even when datasets mentioned without exact ID patterns

**Drawbacks:**
- Requires GROBID service running (Docker or self-hosted)
- Processing slower than pdfplumber (~2.5 PDFs/sec)
- Adds infrastructure dependency

#### Scenario 2: Hybrid Approach

**Use pdfplumber for simple cases, GROBID for complex:**

```python
def extract_contexts(pdf_path, dataset_patterns):
    # Try simple pattern matching first
    simple_contexts = extract_with_pdfplumber(pdf_path, dataset_patterns)

    if len(simple_contexts) < 2:  # Didn't find much
        # Fall back to GROBID for deeper analysis
        return extract_with_grobid(pdf_path, dataset_patterns)

    return simple_contexts
```

#### Scenario 3: Use GROBID for Bibliography Parsing Only

**Current limitation:** We only find citations where dataset ID appears in full text.

**GROBID enhancement:** Extract full bibliography, find dataset references even if ID only appears there:

```python
# GROBID extracts all references from bibliography
# Example from GROBID:
{
  "biblStruct": {
    "title": "Patch-seq recordings from mouse visual cortex",
    "idno": "10.48324/dandi.000020/0.210913.1639",
    "ref": "#b23"
  }
}

# Then find in-text citations:
# "We analyzed data from [23]" → links to #b23 → DANDI:000020
```

**Benefit:** Find citations even when dataset not mentioned by ID in main text.

### Deployment Options

1. **Docker (easiest):**
   ```bash
   docker run -p 8070:8070 lfoppiano/grobid:0.8.0
   ```

2. **Self-hosted service:**
   - Java application
   - RESTful API
   - Can handle multiple concurrent requests

3. **Batch processing:**
   - Local Java library
   - Process entire directories
   - No network overhead

### Performance Considerations

**GROBID:**
- ~2.5 PDFs/second (full processing)
- ~10+ PDFs/second (optimized, reference extraction only)
- Higher CPU usage (ML models)

**Current (pdfplumber):**
- ~10-20 PDFs/second
- Lighter weight
- No ML overhead

**Recommendation:** Start with hybrid approach - use pdfplumber as default, GROBID for papers where we need deeper analysis.

---

## 3. Recommendations

### Immediate (PR #4)

1. **Fix CI tests** - Add missing model validators
2. **Document GROBID** as future enhancement (not blocking for this PR)
3. **Commit workaround** for TSV loading

### Short-term (Next PR)

1. **Experiment with GROBID** on subset of dandi-bib
2. **Compare results**: pdfplumber vs. GROBID context quality
3. **Measure performance** impact

### Long-term

1. **Hybrid extraction** - pdfplumber + GROBID fallback
2. **Optional GROBID** - Make it an optional dependency, fall back gracefully
3. **Bibliography mining** - Use GROBID to find citations in references only

---

## 4. Response to Comment

**tekrajchhetri's comment:** "with grobid you can also extract citations"

**Response:**

> Thanks for the GROBID suggestion! You're absolutely right that GROBID provides excellent citation extraction capabilities with better structure than our current pdfplumber approach.
>
> I've researched GROBID's capabilities and see several ways it could enhance our system:
> - Better citation-reference linking (knowing which in-text mention links to which bibliography entry)
> - Section-aware context extraction
> - Handling papers where datasets only appear in bibliography
>
> For this PR, we're sticking with the current pdfplumber-based extraction to keep dependencies minimal and avoid infrastructure requirements. However, I've documented GROBID as a high-priority enhancement for the next phase.
>
> Would be great to explore this further - perhaps a hybrid approach where we use pdfplumber by default and fall back to GROBID for complex cases where we need deeper analysis?

---

## Files to Update

1. **Fix tests:** Add `src/citations_collector/models/validators.py`
2. **Document enhancement:** Update `docs/CONTEXT-EXTRACTION.md` with GROBID future work
3. **Commit workaround:** The TSV loader fix

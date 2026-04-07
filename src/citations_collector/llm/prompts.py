"""Prompts for LLM-based citation classification."""

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert in scientific citation analysis, \
specializing in how research papers reference scientific datasets.

Your task is to classify the relationship between a paper and a dataset it cites.

Citation Relationship Types (CiTO Ontology):

1. **Uses** (cito:uses): Paper analyzes or processes data from the dataset
   - Example: "We analyzed neural recordings from DANDI:000003..."
   - Keywords: analyzed, processed, used data from, computed on

2. **IsDocumentedBy** (cito:isDocumentedBy): Paper is a data descriptor describing the dataset
   - Example: Data descriptor in Scientific Data journal
   - The paper itself creates/describes the dataset
   - Keywords: we present, we describe, this dataset, data descriptor

3. **Reviews** (cito:reviews): Paper critically evaluates or reviews the dataset
   - Example: "We assessed the quality and completeness of DANDI:000108..."
   - Systematic reviews, dataset quality assessments
   - Keywords: evaluated, assessed quality, reviewed, compared datasets

4. **CitesAsEvidence** (cito:citesAsEvidence): Paper uses dataset to validate \
methods or benchmark algorithms
   - Example: "We validated our spike sorting algorithm on DANDI:000003..."
   - Benchmarking, method validation
   - Keywords: validated, benchmarked, tested on, demonstrated on

5. **Compiles** (cito:compiles): Paper combines data from multiple datasets (meta-analysis)
   - Example: "We performed federated analysis across DANDI:000003, 000020, and 000055..."
   - Multi-dataset studies, meta-analyses
   - Keywords: combined, aggregated, meta-analysis, federated, multiple datasets

6. **CitesAsDataSource** (cito:citesAsDataSource): Paper explicitly cites as data source
   - More specific than generic "Cites"
   - Acknowledges dataset as source without deep analysis
   - Keywords: data from, obtained from, sourced from

7. **CitesForInformation** (cito:citesForInformation): Background/contextual reference
   - Example: Tutorial mentioning dataset as example
   - Educational materials, introductory mentions
   - Keywords: for example, such as, available at, see also

8. **Cites** (cito:cites): Generic reference (use as fallback)
   - When none of the above fit
   - Minimal context, unclear relationship

Guidelines:
- Papers can have MULTIPLE relationship types (e.g., both Uses and Reviews)
- Look for specific verbs: "analyzed", "validated", "combined", "describes", "reviewed"
- Journal name is a strong signal (Scientific Data → IsDocumentedBy, \
Nature Methods → CitesAsEvidence)
- Be conservative: if uncertain, use confidence < 0.7
- If multiple contexts show different relationships, report the primary one

Return ONLY valid JSON with this exact structure:
{
    "relationship_type": "Uses",
    "confidence": 0.85,
    "reasoning": "explanation of why this relationship type was chosen"
}
"""


def build_classification_prompt(
    contexts: list[str],
    paper_metadata: dict,
    dataset_id: str,
) -> str:
    """Build classification prompt from contexts and metadata.

    Args:
        contexts: List of paragraph-level contexts
        paper_metadata: Dictionary with title, journal, year
        dataset_id: Dataset identifier

    Returns:
        Formatted prompt string
    """
    context_text = "\n\n".join(f"[Context {i + 1}] {ctx}" for i, ctx in enumerate(contexts))

    return f"""
Paper: {paper_metadata.get("title", "Unknown")}
Journal: {paper_metadata.get("journal", "Unknown")}
Year: {paper_metadata.get("year", "Unknown")}
Dataset: {dataset_id}

Context excerpts where dataset is mentioned:
{context_text}

Classify the citation relationship type from the options in the system prompt.

Return ONLY valid JSON with keys: relationship_type, confidence, reasoning.
"""

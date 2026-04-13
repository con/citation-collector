# LLM Backends for Citation Classification

This module provides LLM-based classification of citation relationships using multiple backends.

## Supported Backends

### 1. Ollama (Local, Recommended for Development)

**Setup:**
```bash
# On remote server (typhon)
ollama pull qwen2:7b
ollama pull gemma:2b

# Create SSH tunnel from local machine
ssh -L 11434:localhost:11434 typhon -N
```

**Usage:**
```python
from citations_collector.llm import create_backend

backend = create_backend("ollama", model="qwen2:7b")
result = backend.classify_citation(
    contexts=["We analyzed data from DANDI:000003..."],
    paper_metadata={"title": "...", "journal": "...", "year": 2024},
    dataset_id="dandi:000003",
)
```

### 2. Dartmouth Chat (OpenAI-compatible)

**Setup:**
```bash
# Get JWT token from https://chat.dartmouth.edu
# Settings > Account > Copy API Key
export OPENAI_API_KEY="your-jwt-token"
```

**Usage:**
```python
backend = create_backend(
    "dartmouth",
    model="gpt-4",
    base_url="https://chat.dartmouth.edu",
)
```

### 3. OpenRouter

**Setup:**
```bash
export OPENROUTER_API_KEY="your-key"
```

**Usage:**
```python
backend = create_backend("openrouter", model="openai/gpt-4.1-nano")
```

### 4. OpenAI

**Setup:**
```bash
export OPENAI_API_KEY="your-key"
```

**Usage:**
```python
backend = create_backend("openai", model="gpt-4")
```

## Testing

```bash
# Source secrets
source .git/secrets

# Run test script
python scripts/test_llm_backends.py
```

## Classification Result

All backends return a `ClassificationResult`:

```python
@dataclass
class ClassificationResult:
    relationship_type: str  # "Uses", "IsDocumentedBy", etc.
    confidence: float       # 0.0-1.0
    reasoning: str          # LLM explanation
    context_used: list[str] # Original contexts
```

## Relationship Types

Based on CiTO ontology:

- **Uses**: Analyzes/processes data
- **IsDocumentedBy**: Data descriptor paper
- **Reviews**: Critical evaluation
- **CitesAsEvidence**: Method validation/benchmarking
- **Compiles**: Meta-analysis combining datasets
- **CitesAsDataSource**: Explicit data source citation
- **CitesForInformation**: Background/context reference
- **Cites**: Generic (fallback)

## Cost Comparison

| Backend | Model | Cost (per 1000 citations) |
|---------|-------|---------------------------|
| Ollama | qwen2:7b | $0 (after setup) |
| Dartmouth | gpt-4 | $0 (institutional) |
| OpenRouter | gpt-4.1-nano | ~$0.05 |
| OpenAI | gpt-4 | ~$5-10 |

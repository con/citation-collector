# Available LLM Models for Citation Classification

## Dartmouth (chat.dartmouth.edu)

**Access:** Via OPENAI_API_KEY in secrets file
**Total:** 31 chat models
**API:** OpenAI-compatible

### Free Tier (Local at Dartmouth)

No cost, runs on Dartmouth infrastructure:

- **GPT-OSS 120b** (`openai.gpt-oss-120b`)
  - Tags: Reasoning, Tool Calling
  - Good for: Complex reasoning tasks

- **Gemma 3 27b** (`google.gemma-3-27b-it`)
  - Fast and efficient

- **Llama 3.2 11b** (`meta.llama-3.2-11b-vision-instruct`)
  - Vision capable

- **Llama 3.2 3b** (`meta.llama-3-2-3b-instruct`)
  - Very fast, smaller model

- **Qwen3-VL 32b** (`qwen.qwen3-vl-32b-instruct-fp8`)
  - Vision + Tool Calling

- **CodeLlama 13b** (`meta.codellama-13b-instruct-hf`)
  - Optimized for code

### Budget Tier ($)

Low cost per token:

- **Claude Haiku 4.5** (`anthropic.claude-haiku-4-5-20251001`)
  - Tags: Hybrid Reasoning, Tool Calling
  - Fast Claude model

- **GPT 4.1 mini** (`openai.gpt-4.1-mini-2025-04-14`)
  - Latest small GPT model

- **Gemini 2.0 Flash** (`vertex_ai.gemini-2.0-flash-001`)
  - Fast Google model

- **Gemini 2.5 Flash** (`vertex_ai.gemini-2.5-flash`)
  - Tags: Reasoning
  - Newer version

- **Claude 3.5 Haiku** (`anthropic.claude-3-5-haiku-20241022`)
  - Previous generation

- **GPT-5.1 Codex Mini** (`openai_responses.gpt-5.1-codex-mini`)
  - Code-optimized, adaptive reasoning

### Standard Tier ($$)

- **Mistral Large 3** (`mistral.mistral-large-2512`)
- **Mistral Medium 2508** (`mistral.mistral-medium-2508`)

### Premium Tier ($$$)

Highest quality, highest cost:

#### Claude Models (Anthropic)

- **Claude Sonnet 4.5** (`anthropic.claude-sonnet-4-5-20250929`) ✓ **TESTED**
  - Tags: Hybrid Reasoning, Tool Calling
  - Excellent instruction following
  - **95% confidence on short contexts**

- **Claude Opus 4.5** (`anthropic.claude-opus-4-5-20251101`)
  - Highest capability Claude

- **Claude Sonnet 4** (`anthropic.claude-sonnet-4-20250514`)
  - Previous version

- **Claude 3.7 Sonnet** (`anthropic.claude-3-7-sonnet-20250219`)
  - Older generation

#### GPT Models (OpenAI)

- **GPT-5** (`openai_responses.gpt-5-2025-08-07`)
  - Tags: Reasoning, Tool Calling
  - Latest reasoning model

- **GPT-5.1 Thinking** (`openai_responses.gpt-5.1-2025-11-13`)
  - Hybrid reasoning

- **GPT-5.2 Thinking** (`openai_responses.gpt-5.2-2025-12-11`)
  - Latest version

- **GPT-5.1 Codex** (`openai_responses.gpt-5.1-codex`)
  - Code-optimized

- **GPT-5.1 Instant** (`openai_responses.gpt-5.1-chat-latest`)
  - Fast inference

- **GPT-5.2 Instant** (`openai_responses.gpt-5.2-chat-latest`)
  - Latest fast version

- **GPT 4.1** (`openai.gpt-4.1-2025-04-14`)
  - Vision capable

#### Google Models

- **Gemini 2.5 Pro** (`vertex_ai.gemini-2.5-pro`)
  - Tags: Reasoning, Tool Calling
  - Latest Gemini

- **Pixtral Large** (`mistral.pixtral-large-2411`)
  - Mistral vision model

## Ollama (Local or Remote via SSH Tunnel)

**Access:** Via SSH tunnel to typhon or local installation
**Models:** Auto-detected from `ollama list`

### Tested

- **qwen2:7b** ✓ **TESTED**
  - Short context: 26 Uses, 15 CitesAsDataSource, 5 IsDocumentedBy, 1 Compiles
  - All valid types, 0.80-0.95 confidence
  - Full text: Confused, generated invalid types

### Recommended for Testing

Fast models available on Ollama:

- **llama3.1:8b** - Latest Llama model
- **llama3.2:3b** - Smaller, faster
- **phi3:mini** - Very fast Microsoft model
- **mistral:7b** - Good general purpose
- **qwen2.5:7b** - Latest Qwen (if available)

## Comparison Strategy

### Recommended Test Set

For comprehensive comparison with reasonable cost/time:

1. **Free tier (2 models):**
   - GPT-OSS 120b (Dartmouth)
   - qwen2:7b (Ollama - already tested)

2. **Budget tier (2 models):**
   - Claude Haiku 4.5 (Dartmouth)
   - Gemini 2.0 Flash (Dartmouth)

3. **Premium tier (2 models):**
   - Claude Sonnet 4.5 (Dartmouth - already tested)
   - GPT-5 (Dartmouth)

This gives 6 models × 2 modes (short/full) = **12 comparisons**

### Full Test Set

For exhaustive evaluation:

- All 6 free Dartmouth models
- 3-4 Ollama models
- 2-3 budget models
- 2-3 premium models

Total: ~15 models × 2 modes = **30 comparisons**

## Usage

### Quick Test (Recommended Set)

```bash
# Edit scripts/compare_models.py to select models
# Then run:
python scripts/compare_models.py dandi-full.yaml
```

### Select Specific Models

Edit `scripts/compare_models.py`:

```python
# Test only specific Dartmouth models
dartmouth_models = [
    "anthropic.claude-sonnet-4-5-20250929",  # Best Claude
    "openai_responses.gpt-5-2025-08-07",     # Best GPT
    "vertex_ai.gemini-2.5-pro",              # Best Gemini
]

# Test only specific Ollama models
test_ollama_models = ["qwen2:7b", "llama3.1:8b"]
```

## Cost Estimates

Based on typical pricing (check current rates):

### Per 47 Papers (dandi-full.yaml)

Approximate token counts:
- Short context: ~10K input tokens/paper
- Full text: ~50K input tokens/paper
- Output: ~500 tokens/classification

**Free tier:** $0
**Budget tier:** ~$0.50-1.00 for full comparison
**Premium tier:** ~$5-10 for full comparison

## Model Selection Guide

### For Development/Testing
- Use **free tier** (GPT-OSS 120b, local Ollama)
- Fast iteration, no cost

### For Production
Based on comparison results:
- **Best accuracy:** Likely Claude Sonnet 4.5 or GPT-5
- **Best value:** Likely Claude Haiku 4.5 or Gemini Flash
- **Best speed:** Local Ollama models

### Special Cases

- **Code-heavy papers:** GPT-5.1 Codex
- **Vision needed:** Qwen3-VL, Gemini Pro
- **Reasoning tasks:** GPT-5, Claude Opus, GPT-OSS 120b

## Notes

- All models support Tool Calling (structured output)
- Hybrid Reasoning models "think" before responding
- Vision models can process images (useful for figure understanding)
- Free/Local models run on Dartmouth infrastructure (no external API calls)

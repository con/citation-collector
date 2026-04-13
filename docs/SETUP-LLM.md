# LLM Backend Setup Guide

## Quick Start

### 1. Start SSH Tunnel for Ollama

**IMPORTANT**: The tunnel must bind to `0.0.0.0` to be accessible from the podman container.

In a **separate terminal** on your host machine:

```bash
ssh -L 0.0.0.0:11434:localhost:11434 typhon -N
```

Keep this terminal running!

**Why `0.0.0.0`?**
- Default `ssh -L 11434:...` binds only to `127.0.0.1` (localhost)
- Podman containers can't reach host's `127.0.0.1`
- Binding to `0.0.0.0` makes the port accessible from the container via `host.containers.internal`

### 2. Test Connection

From inside the container (where Claude Code runs):

```bash
cd /home/yoh/proj/dandi/citations-collector-enh-zotero

# This automatically detects container environment and uses host.containers.internal
uv run scripts/test_ollama_connection.py
```

Expected output:
```
Detected podman container - using host.containers.internal
Testing Ollama connection at http://host.containers.internal:11434...

1. Checking Ollama version...
   ✓ Ollama version: 0.x.x

2. Listing available models...
   ✓ Found 3 model(s):
      - qwen2:7b (4.2 GB)
      - gemma:2b (1.5 GB)
      - mistral:7b (4.1 GB)

3. Testing text generation...
   Using model: qwen2:7b
   ✓ Generation successful

✓ All tests passed!
```

### 3. Test Classification

Quick test of citation classification:

```bash
uv run python3 << 'EOF'
import sys
sys.path.insert(0, 'src')

from citations_collector.llm import create_backend

# Auto-detects container and uses host.containers.internal
backend = create_backend('ollama', model='qwen2:7b')

result = backend.classify_citation(
    contexts=[
        'We analyzed neural recordings from DANDI:000003 using spike sorting.',
        'The DANDI:000003 dataset contains high-quality electrophysiology data.'
    ],
    paper_metadata={
        'title': 'Advanced spike sorting methods',
        'journal': 'Nature Neuroscience',
        'year': 2024
    },
    dataset_id='dandi:000003',
)

print(f'Relationship Type: {result.relationship_type}')
print(f'Confidence: {result.confidence:.2f}')
print(f'Reasoning: {result.reasoning}')
EOF
```

---

## Backends Available

### 1. Ollama (Recommended - $0 cost)

**Setup**: SSH tunnel (see above)

**Models on typhon**:
```bash
ssh typhon
ollama list
```

**Usage in code**:
```python
from citations_collector.llm import create_backend

# Auto-detects container vs host environment
backend = create_backend('ollama', model='qwen2:7b')
```

### 2. Dartmouth Chat

**API Token**: Already configured in `/home/yoh/proj/dandi/citations-collector/.git/secrets`

**Base URL**: `https://chat.dartmouth.edu/api`

**Usage**:
```python
backend = create_backend('dartmouth', model='gpt-4')
# Automatically uses OPENAI_API_KEY from environment
```

**Note**: Currently getting "Internal Server Error" - may need to verify:
- Token is valid and not expired
- Correct model names available
- API path is correct for your instance

### 3. OpenRouter (Optional)

**Cost**: ~$0.05 per 1000 citations (with gpt-4.1-nano)

**Setup**:
```bash
export OPENROUTER_API_KEY="your-key"
```

**Usage**:
```python
backend = create_backend('openrouter', model='openai/gpt-4.1-nano')
```

---

## Troubleshooting

### "Connection refused" when testing Ollama

**Check 1**: Is the SSH tunnel running?
```bash
# On your host, check if port is listening
netstat -tln | grep 11434
# or
ss -tln | grep 11434
```

**Check 2**: Is it bound to 0.0.0.0 (not just 127.0.0.1)?
```bash
# Should show 0.0.0.0:11434, not 127.0.0.1:11434
```

**Check 3**: Restart tunnel with correct binding:
```bash
# Stop old tunnel (Ctrl+C)
# Start with 0.0.0.0 binding:
ssh -L 0.0.0.0:11434:localhost:11434 typhon -N
```

### Dartmouth API returns "Internal Server Error"

**Possible causes**:
1. Token expired - Get new JWT from Settings > Account
2. Wrong API path - Try different endpoints
3. Model name incorrect

**Debug**:
```bash
source /home/yoh/proj/dandi/citations-collector/.git/secrets

# Test if API is reachable
curl -v https://chat.dartmouth.edu/api/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Try chat completions
curl -X POST https://chat.dartmouth.edu/api/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": false
  }'
```

---

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Host Machine                                                │
│                                                             │
│  SSH Tunnel: 0.0.0.0:11434 ←→ typhon:11434 (Ollama)       │
│                    ↑                                        │
│                    │                                        │
│  ┌─────────────────┴──────────────────────────────────┐   │
│  │ Podman Container                                    │   │
│  │                                                     │   │
│  │  Claude Code → host.containers.internal:11434      │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key points**:
- Container sees host as `host.containers.internal` (169.254.1.2)
- Tunnel must bind to `0.0.0.0` to be reachable from container IP
- Auto-detection in code uses `/run/.containerenv` to detect container

---

## Files Updated

1. `src/citations_collector/llm/ollama_backend.py` - Auto-detects container environment
2. `src/citations_collector/llm/factory.py` - Dartmouth base URL to /api
3. `scripts/test_ollama_connection.py` - Auto-detects container, better error messages
4. `scripts/test_llm_backends.py` - Loads secrets from correct path
5. `scripts/setup-ollama-tunnel.sh` - Helper script with instructions

---

## Next Steps

Once Ollama test passes:

1. **Implement context extraction** from PDFs/HTMLs
2. **Build classification pipeline**
3. **Add CLI commands** (`extract-contexts`, `classify`)
4. **Test on real dandi-bib citations**

#!/usr/bin/env python3
"""Simple test for Ollama connection (no dependencies)."""

import sys

try:
    import requests
except ImportError:
    print("✗ requests module not found. Install with: pip install requests")
    sys.exit(1)


def test_ollama_connection(base_url=None):
    """Test if Ollama is reachable."""
    import os

    # Auto-detect container vs host
    if base_url is None:
        if os.path.exists("/run/.containerenv"):
            base_url = "http://host.containers.internal:11434"
            print("Detected podman container - using host.containers.internal")
        else:
            base_url = "http://localhost:11434"

    print(f"Testing Ollama connection at {base_url}...")

    try:
        # Test 1: Check version
        print("\n1. Checking Ollama version...")
        response = requests.get(f"{base_url}/api/version", timeout=5)
        if response.status_code == 200:
            version = response.json()
            print(f"   ✓ Ollama version: {version.get('version', 'unknown')}")
        else:
            print(f"   ✗ Unexpected status: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("   ✗ Connection refused. Is SSH tunnel running?")
        if "host.containers.internal" in base_url:
            print("   → From host, run: ssh -L 0.0.0.0:11434:localhost:11434 typhon -N")
            print("   → (Must bind to 0.0.0.0 to be accessible from container)")
        else:
            print("   → Run: ssh -L 11434:localhost:11434 typhon -N")
        return False
    except requests.exceptions.Timeout:
        print("   ✗ Connection timeout")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    try:
        # Test 2: List models
        print("\n2. Listing available models...")
        response = requests.get(f"{base_url}/api/tags", timeout=10)
        response.raise_for_status()

        data = response.json()
        models = data.get("models", [])

        if not models:
            print("   ✗ No models found. Pull models with:")
            print("      ssh typhon")
            print("      ollama pull qwen2:7b")
            return False

        print(f"   ✓ Found {len(models)} model(s):")
        for model in models:
            name = model.get("name", "unknown")
            size_gb = model.get("size", 0) / (1024**3)
            print(f"      - {name} ({size_gb:.1f} GB)")

    except Exception as e:
        print(f"   ✗ Error listing models: {e}")
        return False

    try:
        # Test 3: Simple generation
        print("\n3. Testing text generation...")

        # Use first available model
        model_name = models[0]["name"]
        print(f"   Using model: {model_name}")

        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model_name,
                "messages": [
                    {"role": "user", "content": "Say 'hello' in JSON format with a greeting key."}
                ],
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=60,
        )
        response.raise_for_status()

        result = response.json()
        message = result.get("message", {}).get("content", "")
        print("   ✓ Generation successful")
        print(f"   Response: {message[:100]}...")

    except Exception as e:
        print(f"   ✗ Generation error: {e}")
        return False

    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    success = test_ollama_connection()
    sys.exit(0 if success else 1)

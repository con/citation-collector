"""Ollama backend for local LLM inference."""

from __future__ import annotations

import json
import logging

import requests

from .base import ClassificationResult, LLMBackend
from .prompts import CLASSIFICATION_SYSTEM_PROMPT, build_classification_prompt

logger = logging.getLogger(__name__)


class OllamaBackend(LLMBackend):
    """Local Ollama backend for LLM inference."""

    def __init__(
        self,
        model: str = "qwen2:7b",
        base_url: str | None = None,
        timeout: int = 120,
    ):
        """Initialize Ollama backend.

        Args:
            model: Model name (e.g., "qwen2:7b", "gemma:2b", "mistral:7b")
            base_url: Ollama API base URL (auto-detects container vs host)
            timeout: Request timeout in seconds
        """
        self.model = model

        # Auto-detect if running in container
        if base_url is None:
            # Check if host.containers.internal exists (podman/docker container)
            import os

            if os.path.exists("/run/.containerenv"):
                # Running in podman container
                base_url = "http://host.containers.internal:11434"
            else:
                # Running on host
                base_url = "http://localhost:11434"

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def classify_citation(
        self,
        contexts: list[str],
        paper_metadata: dict,
        dataset_id: str,
    ) -> ClassificationResult:
        """Classify using local Ollama.

        Args:
            contexts: List of paragraph contexts
            paper_metadata: Paper title, journal, year
            dataset_id: Dataset identifier

        Returns:
            ClassificationResult
        """
        prompt = build_classification_prompt(contexts, paper_metadata, dataset_id)

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": CLASSIFICATION_SYSTEM_PROMPT,
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low for consistency
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()

            return self._parse_response(response.json(), contexts)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API error: {e}")
            # Return fallback
            return ClassificationResult(
                relationship_type="Cites",
                confidence=0.0,
                reasoning=f"API error: {e}",
                context_used=contexts,
            )

    def batch_classify(
        self,
        citations: list[tuple[list[str], dict, str]],
    ) -> list[ClassificationResult]:
        """Batch classification (processes sequentially for Ollama).

        Args:
            citations: List of (contexts, metadata, dataset_id) tuples

        Returns:
            List of ClassificationResult objects
        """
        results = []
        for contexts, metadata, dataset_id in citations:
            result = self.classify_citation(contexts, metadata, dataset_id)
            results.append(result)
        return results

    def _parse_response(self, response_json: dict, contexts: list[str]) -> ClassificationResult:
        """Parse Ollama response.

        Args:
            response_json: Response from Ollama API
            contexts: Original contexts for context_used field

        Returns:
            ClassificationResult
        """
        try:
            # Extract message content
            content = response_json["message"]["content"]

            # Parse JSON from content
            # Sometimes LLMs wrap JSON in ```json code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            return ClassificationResult(
                relationship_type=result["relationship_type"],
                confidence=float(result["confidence"]),
                reasoning=result["reasoning"],
                context_used=contexts,
            )

        except (KeyError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Ollama response: {e}")
            logger.debug(f"Response: {response_json}")

            # Return fallback
            return ClassificationResult(
                relationship_type="Cites",
                confidence=0.0,
                reasoning=f"Parse error: {e}",
                context_used=contexts,
            )

"""OpenRouter API backend."""

from __future__ import annotations

import json
import logging
import os

import requests

from .base import ClassificationResult, LLMBackend
from .prompts import CLASSIFICATION_SYSTEM_PROMPT, build_classification_prompt

logger = logging.getLogger(__name__)


class OpenRouterBackend(LLMBackend):
    """OpenRouter API backend."""

    def __init__(
        self,
        model: str = "openai/gpt-4.1-nano",
        api_key: str | None = None,
        timeout: int = 60,
    ):
        """Initialize OpenRouter backend.

        Args:
            model: Model name (e.g., "openai/gpt-4.1-nano", "anthropic/claude-3.5-sonnet")
            api_key: API key (defaults to OPENROUTER_API_KEY env var)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.timeout = timeout

        if not self.api_key:
            raise ValueError(
                "API key required. Set OPENROUTER_API_KEY environment variable "
                "or pass api_key parameter."
            )

    def classify_citation(
        self,
        contexts: list[str],
        paper_metadata: dict,
        dataset_id: str,
    ) -> ClassificationResult:
        """Classify using OpenRouter API.

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
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": CLASSIFICATION_SYSTEM_PROMPT,
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()

            return self._parse_response(response.json(), contexts)

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API error: {e}")
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
        """Batch classification (processes sequentially).

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
        """Parse OpenRouter response.

        Args:
            response_json: Response from OpenRouter API
            contexts: Original contexts for context_used field

        Returns:
            ClassificationResult
        """
        try:
            # Extract message content
            content = response_json["choices"][0]["message"]["content"]

            # Parse JSON from content
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
            logger.error(f"Failed to parse OpenRouter response: {e}")
            logger.debug(f"Response: {response_json}")

            # Return fallback
            return ClassificationResult(
                relationship_type="Cites",
                confidence=0.0,
                reasoning=f"Parse error: {e}",
                context_used=contexts,
            )

"""OpenAI-compatible backend (OpenAI, Dartmouth chat.dartmouth.edu, etc.)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from .base import ClassificationResult, LLMBackend
from .prompts import CLASSIFICATION_SYSTEM_PROMPT, build_classification_prompt

logger = logging.getLogger(__name__)


class OpenAIBackend(LLMBackend):
    """OpenAI-compatible backend."""

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 60,
    ):
        """Initialize OpenAI-compatible backend.

        Args:
            model: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
            api_key: API key (defaults to OPENAI_API_KEY env var)
            base_url: Base URL (for Dartmouth: https://chat.dartmouth.edu)
            timeout: Request timeout in seconds
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout = timeout

        if not self.api_key:
            raise ValueError(
                "API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        # Import OpenAI client
        try:
            from openai import OpenAI
        except ImportError as err:
            raise ImportError("openai package required. Install with: pip install openai") from err

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            timeout=self.timeout,
        )

    def classify_citation(
        self,
        contexts: list[str],
        paper_metadata: dict,
        dataset_id: str,
    ) -> ClassificationResult:
        """Classify using OpenAI-compatible API.

        Args:
            contexts: List of paragraph contexts
            paper_metadata: Paper title, journal, year
            dataset_id: Dataset identifier

        Returns:
            ClassificationResult
        """
        prompt = build_classification_prompt(contexts, paper_metadata, dataset_id)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": CLASSIFICATION_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )

            return self._parse_response(response, contexts)

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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

    def _parse_response(self, response: Any, contexts: list[str]) -> ClassificationResult:
        """Parse OpenAI response.

        Args:
            response: Response from OpenAI API
            contexts: Original contexts for context_used field

        Returns:
            ClassificationResult
        """
        try:
            # Extract message content
            content = response.choices[0].message.content

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

        except (KeyError, json.JSONDecodeError, ValueError, AttributeError) as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            logger.debug(f"Response: {response}")

            # Return fallback
            return ClassificationResult(
                relationship_type="Cites",
                confidence=0.0,
                reasoning=f"Parse error: {e}",
                context_used=contexts,
            )

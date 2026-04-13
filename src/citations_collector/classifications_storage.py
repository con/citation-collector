"""Storage for per-paper classification results.

Each paper's directory (pdfs/{doi}/) contains a classifications.json file
with results from all models that have classified citations for that paper.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from citations_collector.llm.base import ClassificationResult


@dataclass
class StoredClassification:
    """A stored classification result for a specific item+flavor."""

    item_id: str
    item_flavor: str
    model: str
    backend: str
    relationship_type: str
    confidence: float
    reasoning: str
    timestamp: str  # ISO 8601
    mode: str  # "short_context" or "full_text"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "item_id": self.item_id,
            "item_flavor": self.item_flavor,
            "model": self.model,
            "backend": self.backend,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StoredClassification:
        """Load from dictionary."""
        return cls(
            item_id=data["item_id"],
            item_flavor=data["item_flavor"],
            model=data["model"],
            backend=data["backend"],
            relationship_type=data["relationship_type"],
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            timestamp=data["timestamp"],
            mode=data["mode"],
        )


class ClassificationsStorage:
    """Manages per-paper classifications.json files."""

    def __init__(self, pdfs_dir: Path):
        """Initialize storage.

        Args:
            pdfs_dir: Root directory containing paper subdirectories
        """
        self.pdfs_dir = pdfs_dir

    def get_paper_dir(self, doi: str) -> Path:
        """Get directory for a paper by DOI.

        Args:
            doi: Paper DOI (e.g., "10.1234/example")

        Returns:
            Path to paper directory (pdfs/{doi}/)
        """
        return self.pdfs_dir / doi

    def get_classifications_file(self, doi: str) -> Path:
        """Get path to classifications.json for a paper.

        Args:
            doi: Paper DOI

        Returns:
            Path to classifications.json file
        """
        return self.get_paper_dir(doi) / "classifications.json"

    def load_classifications(self, doi: str) -> list[StoredClassification]:
        """Load all classifications for a paper.

        Args:
            doi: Paper DOI

        Returns:
            List of stored classifications (empty if file doesn't exist)
        """
        classifications_file = self.get_classifications_file(doi)
        if not classifications_file.exists():
            return []

        with open(classifications_file) as f:
            data = json.load(f)

        return [StoredClassification.from_dict(item) for item in data]

    def save_classifications(self, doi: str, classifications: list[StoredClassification]) -> None:
        """Save classifications for a paper.

        Args:
            doi: Paper DOI
            classifications: List of classifications to save
        """
        classifications_file = self.get_classifications_file(doi)
        classifications_file.parent.mkdir(parents=True, exist_ok=True)

        data = [c.to_dict() for c in classifications]

        with open(classifications_file, "w") as f:
            json.dump(data, f, indent=2)

    def add_classification(
        self,
        doi: str,
        item_id: str,
        item_flavor: str,
        result: ClassificationResult,
        model: str,
        backend: str,
        mode: str = "short_context",
    ) -> None:
        """Add a new classification result.

        If a classification for this (item_id, item_flavor, model) already exists,
        it will be replaced.

        Args:
            doi: Paper DOI
            item_id: Item identifier (e.g., "dandi.000020")
            item_flavor: Item version (e.g., "0.210913.1639")
            result: Classification result from LLM
            model: Model identifier (e.g., "google.gemma-3-27b-it")
            backend: Backend name (e.g., "dartmouth", "ollama")
            mode: Classification mode ("short_context" or "full_text")
        """
        # Load existing classifications
        classifications = self.load_classifications(doi)

        # Create new classification
        new_classification = StoredClassification(
            item_id=item_id,
            item_flavor=item_flavor,
            model=model,
            backend=backend,
            relationship_type=result.relationship_type,
            confidence=result.confidence,
            reasoning=result.reasoning,
            timestamp=datetime.now().isoformat(),
            mode=mode,
        )

        # Remove any existing classification for same (item_id, item_flavor, model)
        classifications = [
            c
            for c in classifications
            if not (c.item_id == item_id and c.item_flavor == item_flavor and c.model == model)
        ]

        # Add new classification
        classifications.append(new_classification)

        # Save
        self.save_classifications(doi, classifications)

    def get_classification(
        self, doi: str, item_id: str, item_flavor: str, model: str
    ) -> StoredClassification | None:
        """Get a specific classification.

        Args:
            doi: Paper DOI
            item_id: Item identifier
            item_flavor: Item version
            model: Model identifier

        Returns:
            StoredClassification if found, None otherwise
        """
        classifications = self.load_classifications(doi)
        for c in classifications:
            if c.item_id == item_id and c.item_flavor == item_flavor and c.model == model:
                return c
        return None

    def get_classifications_for_item(
        self, doi: str, item_id: str, item_flavor: str
    ) -> list[StoredClassification]:
        """Get all classifications for a specific item+flavor.

        Useful for comparing multiple models' results.

        Args:
            doi: Paper DOI
            item_id: Item identifier
            item_flavor: Item version

        Returns:
            List of classifications (possibly from different models)
        """
        classifications = self.load_classifications(doi)
        return [c for c in classifications if c.item_id == item_id and c.item_flavor == item_flavor]

    def has_classification(self, doi: str, item_id: str, item_flavor: str, model: str) -> bool:
        """Check if a classification exists.

        Args:
            doi: Paper DOI
            item_id: Item identifier
            item_flavor: Item version
            model: Model identifier

        Returns:
            True if classification exists, False otherwise
        """
        return self.get_classification(doi, item_id, item_flavor, model) is not None

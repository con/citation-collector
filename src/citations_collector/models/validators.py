"""Custom validators for CitationRecord model.

These validators provide automatic population and coherence checking
for backward compatibility fields and multi-value fields.
"""

from __future__ import annotations

import json

from pydantic import model_validator


def create_citation_record_with_validators(base_class: type) -> type:
    """Create CitationRecord subclass with validators.

    Args:
        base_class: The generated CitationRecord class

    Returns:
        Subclass with validators added
    """

    class CitationRecordWithValidators(base_class):  # type: ignore[misc,valid-type,has-type]
        """CitationRecord with custom validation logic."""

        @model_validator(mode="after")
        def populate_and_validate(self) -> CitationRecordWithValidators:
            """Auto-populate lists and validate coherence."""
            # Citation relationships handling
            if self.citation_relationship and not self.citation_relationships:  # type: ignore[has-type]
                # Auto-populate list from singular
                self.citation_relationships = [self.citation_relationship]
            elif (
                self.citation_relationships
                and self.citation_relationship
                and self.citation_relationship != self.citation_relationships[0]
            ):
                # Validate coherence: first element must match singular
                raise ValueError(
                    f"citation_relationship ({self.citation_relationship}) "
                    f"must match first element of citation_relationships "
                    f"({self.citation_relationships[0]})"
                )

            # Citation sources handling
            if self.citation_source and not self.citation_sources:  # type: ignore[has-type]
                # Auto-populate list from singular
                self.citation_sources = [self.citation_source]
            elif (
                self.citation_sources
                and self.citation_source
                and self.citation_source not in self.citation_sources
            ):
                # Validate coherence: must contain singular
                raise ValueError(
                    f"citation_source ({self.citation_source}) must be present "
                    f"in citation_sources ({self.citation_sources})"
                )

            # Validate citation_sources and discovered_dates coherence
            if self.citation_sources and self.discovered_dates:
                # Parse discovered_dates if string
                if isinstance(self.discovered_dates, str):
                    try:
                        dates_dict = json.loads(self.discovered_dates)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"Invalid JSON in discovered_dates: {self.discovered_dates}"
                        ) from e

                    if not isinstance(dates_dict, dict):
                        raise ValueError(
                            f"discovered_dates must be a JSON object, got: {type(dates_dict)}"
                        )
                else:
                    dates_dict = self.discovered_dates or {}

                # Check all sources have dates
                for source in self.citation_sources:
                    if source not in dates_dict:
                        raise ValueError(
                            f"citation_sources and discovered_dates must be coherent: "
                            f"source '{source}' missing in discovered_dates"
                        )

                # Check all dates have sources
                for source in dates_dict:
                    if source not in self.citation_sources:
                        raise ValueError(
                            f"citation_sources and discovered_dates must be coherent: "
                            f"source '{source}' in discovered_dates but not "
                            f"in citation_sources"
                        )

            return self

    # Preserve the original class name
    CitationRecordWithValidators.__name__ = base_class.__name__
    CitationRecordWithValidators.__qualname__ = base_class.__qualname__

    return CitationRecordWithValidators

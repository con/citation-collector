"""Data models for citations-collector.

Generated from LinkML schema at schema/citations.yaml.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # For static type checking, use the generated class directly
    # so mypy can resolve all attributes
    from citations_collector.models.generated import CitationRecord as CitationRecord
else:
    # At runtime, wrap with validators for auto-population and coherence checks
    from citations_collector.models.generated import CitationRecord as _CitationRecord
    from citations_collector.models.validators import (
        create_citation_record_with_validators,
    )

    CitationRecord = create_citation_record_with_validators(_CitationRecord)

from citations_collector.models.generated import (
    CitationRelationship,
    CitationSource,
    CitationStatus,
    CitationType,
    ClassificationMethod,
    Collection,
    CurationConfig,
    CurationRule,
    DiscoverConfig,
    Item,
    ItemFlavor,
    ItemRef,
    PdfsConfig,
    RefType,
    SourceConfig,
    ZoteroConfig,
)

__all__ = [
    "CitationRecord",
    "CitationRelationship",
    "CitationSource",
    "CitationStatus",
    "CitationType",
    "ClassificationMethod",
    "Collection",
    "CurationConfig",
    "CurationRule",
    "DiscoverConfig",
    "Item",
    "ItemFlavor",
    "ItemRef",
    "PdfsConfig",
    "RefType",
    "SourceConfig",
    "ZoteroConfig",
]

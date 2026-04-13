from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "None"
version = "0.2.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )

    @model_serializer(mode='wrap', when_used='unless-none')
    def treat_empty_lists_as_none(
            self, handler: SerializerFunctionWrapHandler,
            info: SerializationInfo) -> dict[str, Any]:
        if info.exclude_none:
            _instance = self.model_copy()
            for field, field_info in type(_instance).model_fields.items():
                if getattr(_instance, field) == [] and not(
                        field_info.is_required()):
                    setattr(_instance, field, None)
        else:
            _instance = self
        return handler(_instance, info)



class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'citations',
     'default_range': 'string',
     'description': 'Schema for tracking scholarly citations of digital products '
                    '(datasets, software, tools) identified by DOIs, RRIDs, or '
                    'other identifiers. Supports flexible hierarchical collections '
                    'and curation workflows.',
     'id': 'https://w3id.org/dandi/citations-collector',
     'imports': ['linkml:types'],
     'license': 'MIT',
     'name': 'citations-collector',
     'prefixes': {'citations': {'prefix_prefix': 'citations',
                                'prefix_reference': 'https://w3id.org/dandi/citations-collector/'},
                  'cito': {'prefix_prefix': 'cito',
                           'prefix_reference': 'http://purl.org/spar/cito/'},
                  'datacite': {'prefix_prefix': 'datacite',
                               'prefix_reference': 'https://purl.org/datacite/v4.4/'},
                  'dcterms': {'prefix_prefix': 'dcterms',
                              'prefix_reference': 'http://purl.org/dc/terms/'},
                  'fabio': {'prefix_prefix': 'fabio',
                            'prefix_reference': 'http://purl.org/spar/fabio/'},
                  'foaf': {'prefix_prefix': 'foaf',
                           'prefix_reference': 'http://xmlns.com/foaf/0.1/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'schema': {'prefix_prefix': 'schema',
                             'prefix_reference': 'http://schema.org/'}},
     'source_file': 'schema/citations.yaml',
     'title': 'Citations Collector Schema'} )

class RefType(str, Enum):
    """
    Type of identifier reference.
    """
    doi = "doi"
    """
    Digital Object Identifier (version-specific).
    """
    rrid = "rrid"
    """
    Research Resource Identifier (SciCrunch).
    """
    arxiv = "arxiv"
    """
    arXiv preprint identifier.
    """
    pmid = "pmid"
    """
    PubMed identifier.
    """
    pmcid = "pmcid"
    """
    PubMed Central identifier.
    """
    url = "url"
    """
    Generic URL (fallback when no persistent ID available).
    """
    zenodo_concept = "zenodo_concept"
    """
    Zenodo concept DOI or parent.id representing ALL versions. Example: "10.5281/zenodo.1012598" or just "1012598". System will auto-discover all version DOIs via Zenodo API (query: parent.id:1012598&f=allversions:true).
    """
    zenodo_version = "zenodo_version"
    """
    Zenodo version-specific record ID (resolves to DOI).
    """
    github = "github"
    """
    GitHub repository (owner/repo format).
    """


class CitationRelationship(str, Enum):
    """
    The relationship between a citing work and the cited item. Aligned with CiTO (Citation Typing Ontology) and DataCite relationship types.
    """
    Cites = "Cites"
    """
    The work explicitly cites the item in its references.
    """
    IsDocumentedBy = "IsDocumentedBy"
    """
    The item is documented by this work (e.g., a data descriptor).
    """
    Describes = "Describes"
    """
    The work describes the item or its creation methodology.
    """
    IsSupplementedBy = "IsSupplementedBy"
    """
    The item is supplemented by this work.
    """
    References = "References"
    """
    The work references the item without formal citation.
    """
    Uses = "Uses"
    """
    The work uses data/code from the item.
    """
    IsDerivedFrom = "IsDerivedFrom"
    """
    The work is derived from the item.
    """
    CitesAsDataSource = "CitesAsDataSource"
    """
    The work explicitly cites the item as a source of data. More specific than generic Cites for data reuse scenarios.
    """
    Reviews = "Reviews"
    """
    The work reviews, evaluates, or critically assesses the cited item.
    """
    CitesAsEvidence = "CitesAsEvidence"
    """
    The work uses the cited item as evidence to support claims or validate methods.
    """
    Compiles = "Compiles"
    """
    The work compiles or aggregates data from multiple datasets including this one.
    """
    CitesForInformation = "CitesForInformation"
    """
    The work cites the item as background information or context.
    """


class CitationType(str, Enum):
    """
    The type of citing work. Aligned with FaBiO (FRBR-aligned Bibliographic Ontology) and schema.org types.
    """
    Publication = "Publication"
    """
    Peer-reviewed journal article or conference paper.
    """
    Preprint = "Preprint"
    """
    Non-peer-reviewed preprint (bioRxiv, arXiv, etc.).
    """
    Protocol = "Protocol"
    """
    Published protocol (protocols.io, etc.).
    """
    Thesis = "Thesis"
    """
    Doctoral or master's thesis.
    """
    Book = "Book"
    """
    Book or book chapter.
    """
    Software = "Software"
    """
    Software package or tool.
    """
    Dataset = "Dataset"
    """
    Another dataset that cites this one.
    """
    Other = "Other"
    """
    Other type of work.
    """


class CitationSource(str, Enum):
    """
    The source from which the citation was discovered.
    """
    crossref = "crossref"
    """
    Discovered via CrossRef cited-by API.
    """
    opencitations = "opencitations"
    """
    Discovered via OpenCitations (OCI) API.
    """
    datacite = "datacite"
    """
    Discovered via DataCite API.
    """
    openalex = "openalex"
    """
    Discovered via OpenAlex API.
    """
    europepmc = "europepmc"
    """
    Discovered via Europe PMC API.
    """
    semantic_scholar = "semantic_scholar"
    """
    Discovered via Semantic Scholar API.
    """
    scicrunch = "scicrunch"
    """
    Discovered via SciCrunch/RRID API.
    """
    manual = "manual"
    """
    Manually added by curator.
    """


class CitationStatus(str, Enum):
    """
    Curation status of the citation.
    """
    active = "active"
    """
    Citation is valid and should be included.
    """
    ignored = "ignored"
    """
    Citation is a false positive and should be excluded.
    """
    merged = "merged"
    """
    Citation has been merged into another (e.g., preprint → published).
    """
    pending = "pending"
    """
    Citation needs review by curator.
    """


class ClassificationMethod(str, Enum):
    """
    How the citation relationship was determined.
    """
    manual = "manual"
    """
    Manually classified by a human curator.
    """
    llm = "llm"
    """
    Classified by a Large Language Model.
    """



class ItemRef(ConfiguredBaseModel):
    """
    A resolvable identifier for an item (DOI, RRID, URL, etc.). An item may have multiple refs (e.g., both RRID and Zenodo DOI).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dandi/citations-collector'})

    ref_type: RefType = Field(default=..., description="""Type of identifier.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemRef', 'SourceConfig']} })
    ref_value: str = Field(default=..., description="""The identifier value. Format depends on ref_type: - doi: \"10.1234/example\" (without doi: prefix) - rrid: \"SCR_016216\" (without RRID: prefix) - arxiv: \"2301.12345\" - pmid: \"12345678\" - url: full URL - zenodo: record ID like \"852659\" - github: \"owner/repo\"""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemRef']} })
    ref_url: Optional[str] = Field(default=None, description="""Resolved URL for this reference (auto-populated).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemRef']} })


class ItemFlavor(ConfiguredBaseModel):
    """
    A specific version or variant of an item. For versioned resources (software releases, dataset versions), each version is a flavor. For unversioned resources, use a single flavor (e.g., \"latest\" or \"main\").
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dandi/citations-collector'})

    flavor_id: str = Field(default=..., description="""Identifier for this flavor (e.g., \"0.210812.1448\", \"23.1.0\", \"latest\"). Use \"main\" or omit for unversioned items.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemFlavor']} })
    name: Optional[str] = Field(default=None, description="""Human-readable name for this flavor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemFlavor', 'Item', 'Collection']} })
    release_date: Optional[date] = Field(default=None, description="""When this flavor was released (ISO 8601).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemFlavor']} })
    refs: list[ItemRef] = Field(default=..., description="""Resolvable identifiers for this flavor. Multiple refs allowed (e.g., both DOI and RRID for the same version).""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemFlavor']} })
    citations: Optional[list[CitationRecord]] = Field(default=[], description="""Citations discovered for this flavor.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemFlavor']} })


class Item(ConfiguredBaseModel):
    """
    A tracked resource with one or more flavors (versions). The item_id can encode hierarchy using \":\" separator (e.g., \"dandi:000003\", \"repronim:fmriprep\", or just \"my-tool\").
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'schema:CreativeWork',
         'exact_mappings': ['dcterms:Resource'],
         'from_schema': 'https://w3id.org/dandi/citations-collector'})

    item_id: str = Field(default=..., description="""Unique identifier for this item within the collection. May include namespace prefix with \":\" (e.g., \"dandi:000003\"). The part before \":\" indicates the source/project.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Item', 'CitationRecord'],
         'exact_mappings': ['dcterms:identifier', 'schema:identifier']} })
    name: Optional[str] = Field(default=None, description="""Human-readable name.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemFlavor', 'Item', 'Collection'],
         'exact_mappings': ['schema:name', 'dcterms:title']} })
    description: Optional[str] = Field(default=None, description="""Description of the item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Item', 'Collection'],
         'exact_mappings': ['schema:description', 'dcterms:description']} })
    homepage: Optional[str] = Field(default=None, description="""URL to the item's homepage or landing page.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Item', 'Collection'],
         'exact_mappings': ['schema:url', 'foaf:homepage']} })
    flavors: list[ItemFlavor] = Field(default=..., description="""Versions/variants of this item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Item']} })


class CitationRecord(ConfiguredBaseModel):
    """
    A record representing a citation relationship between a citing work and a tracked item. Each row in the citations TSV.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'cito:CitationAct',
         'comments': ['Represents a citation relationship aligned with CiTO (Citation '
                      'Typing Ontology) and DataCite relationTypes.'],
         'exact_mappings': ['datacite:Relation'],
         'from_schema': 'https://w3id.org/dandi/citations-collector',
         'unique_keys': {'citation_item_key': {'description': 'Unique key: each citing '
                                                              'work (by DOI or URL) is '
                                                              'unique per item+flavor.',
                                               'unique_key_name': 'citation_item_key',
                                               'unique_key_slots': ['item_id',
                                                                    'item_flavor',
                                                                    'citation_doi']}}})

    item_id: str = Field(default=..., description="""ID of the tracked item being cited.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Item', 'CitationRecord']} })
    item_flavor: str = Field(default=..., description="""Flavor (version) of the item being cited.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    item_ref_type: Optional[RefType] = Field(default=None, description="""Which ref type was matched for this citation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    item_ref_value: Optional[str] = Field(default=None, description="""Which ref value was matched for this citation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    item_name: Optional[str] = Field(default=None, description="""Human-readable name of the item (for display).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    citation_doi: Optional[str] = Field(default=None, description="""DOI of the citing work (primary identifier).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'],
         'exact_mappings': ['datacite:doi', 'schema:identifier']} })
    citation_pmid: Optional[str] = Field(default=None, description="""PubMed ID of the citing work.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'], 'exact_mappings': ['schema:identifier']} })
    citation_arxiv: Optional[str] = Field(default=None, description="""arXiv ID of the citing work.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'], 'exact_mappings': ['schema:identifier']} })
    citation_url: Optional[str] = Field(default=None, description="""URL to the citing work (fallback if no DOI).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'], 'exact_mappings': ['schema:url']} })
    citation_title: Optional[str] = Field(default=None, description="""Title of the citing work.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'],
         'exact_mappings': ['dcterms:title', 'schema:name']} })
    citation_authors: Optional[str] = Field(default=None, description="""Authors of the citing work (semicolon-separated).""", json_schema_extra = { "linkml_meta": {'comments': ['Consider migrating to structured Person list for better '
                      'semantic alignment.'],
         'domain_of': ['CitationRecord'],
         'exact_mappings': ['dcterms:creator', 'schema:author']} })
    citation_year: Optional[int] = Field(default=None, description="""Publication year of the citing work.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'],
         'exact_mappings': ['dcterms:issued', 'schema:datePublished']} })
    citation_journal: Optional[str] = Field(default=None, description="""Journal or venue of the citing work.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'], 'exact_mappings': ['schema:isPartOf']} })
    citation_relationship: CitationRelationship = Field(default=..., description="""DEPRECATED: Use citation_relationships instead. Primary relationship type (kept for backward compatibility).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    citation_relationships: Optional[list[CitationRelationship]] = Field(default=[], description="""How the citing work relates to the item. Can have multiple relationship types. Example: [\"Cites\", \"Uses\"] for a paper that both cites and uses data from a dataset. Must be coherent with citation_relationship (first value).""", json_schema_extra = { "linkml_meta": {'comments': ['In CiTO terms, a citation can have multiple characterizations.',
                      'Common combinations: Cites+Uses, IsDocumentedBy+Extends, '
                      'References+IsDerivedFrom.'],
         'domain_of': ['CitationRecord'],
         'slot_uri': 'cito:hasCitationCharacterization'} })
    citation_type: Optional[CitationType] = Field(default=None, description="""Type of the citing work.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'],
         'exact_mappings': ['dcterms:type', 'schema:additionalType']} })
    citation_source: CitationSource = Field(default=..., description="""DEPRECATED: Use citation_sources instead. Primary discovery source (kept for backward compatibility).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    discovered_date: Optional[date] = Field(default=None, description="""DEPRECATED: Use discovered_dates instead. When this citation was first discovered (ISO 8601).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    citation_sources: Optional[list[str]] = Field(default=[], description="""All discovery sources that found this citation. Must be coherent with discovered_dates keys. Example: [\"crossref\", \"openalex\", \"datacite\"]""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    discovered_dates: Optional[str] = Field(default=None, description="""Map of source name to discovery date (ISO 8601). Must be coherent with citation_sources list. Stored as JSON string in TSV. Example: {\"crossref\": \"2025-01-15\", \"openalex\": \"2025-01-20\"}""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    citation_status: CitationStatus = Field(default=CitationStatus.active, description="""Curation status.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'], 'ifabsent': 'string(active)'} })
    citation_merged_into: Optional[str] = Field(default=None, description="""If status is 'merged', the DOI of the canonical version (e.g., published paper DOI when this is a preprint).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    citation_comment: Optional[str] = Field(default=None, description="""Curator notes about this citation.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    curated_by: Optional[str] = Field(default=None, description="""Who made the curation decision.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    curated_date: Optional[date] = Field(default=None, description="""When the curation decision was made (ISO 8601).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    classification_method: Optional[ClassificationMethod] = Field(default=None, description="""How the citation_relationship was determined. \"manual\" for human curation, \"llm\" for LLM classification. Empty/null indicates unspecified (treat as manual).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    classification_model: Optional[str] = Field(default=None, description="""LLM model identifier if classification_method is \"llm\". Empty for manual classifications. Examples: \"google.gemma-3-27b-it\", \"anthropic.claude-sonnet-4-5\", \"qwen2:7b\" (Ollama).""", json_schema_extra = { "linkml_meta": {'comments': ['Full classification details stored in '
                      'pdfs/{doi}/classifications.json',
                      'This field enables quick filtering without joining to external '
                      'file.'],
         'domain_of': ['CitationRecord']} })
    classification_confidence: Optional[float] = Field(default=None, description="""Confidence score from LLM classification (0.0-1.0). Empty for manual classifications.""", ge=0.0, le=1.0, json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    classification_reviewed: Optional[bool] = Field(default=False, description="""Has a human reviewed and approved this classification? Use for tracking which LLM classifications need manual verification. Defaults to false for new LLM classifications.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord'], 'ifabsent': 'false'} })
    oa_status: Optional[str] = Field(default=None, description="""Open access status from Unpaywall: gold, green, bronze, hybrid, or closed.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    pdf_url: Optional[str] = Field(default=None, description="""Best open access PDF URL from Unpaywall.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })
    pdf_path: Optional[str] = Field(default=None, description="""Relative path to locally stored PDF file.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CitationRecord']} })

    @field_validator('citation_doi')
    def pattern_citation_doi(cls, v):
        pattern=re.compile(r"^10\..+/.+$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid citation_doi format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid citation_doi format: {v}"
            raise ValueError(err_msg)
        return v

    @field_validator('citation_merged_into')
    def pattern_citation_merged_into(cls, v):
        pattern=re.compile(r"^10\..+/.+$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid citation_merged_into format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid citation_merged_into format: {v}"
            raise ValueError(err_msg)
        return v


class SourceConfig(ConfiguredBaseModel):
    """
    Configuration for the item source (e.g., DANDI, Zenodo).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dandi/citations-collector'})

    type: Optional[str] = Field(default=None, description="""Source type: \"dandi\", \"bibtex\", \"zenodo_org\", \"zenodo_collection\", \"github_org\", \"yaml\", etc.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig']} })
    update_items: Optional[str] = Field(default=None, description="""How to handle items during import: \"add\" (only add new items) or \"sync\" (add new and update existing).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig']} })
    include_draft: Optional[bool] = Field(default=False, description="""Include draft/unpublished items.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig'], 'ifabsent': 'false'} })
    group_id: Optional[int] = Field(default=None, description="""Numeric group/org ID (if applicable).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig', 'ZoteroConfig']} })
    collection_key: Optional[str] = Field(default=None, description="""Collection key within the source (if applicable).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig', 'ZoteroConfig']} })
    dandiset_ids: Optional[list[str]] = Field(default=[], description="""List of specific DANDI dandiset identifiers to import (e.g., [\"000003\", \"000402\"]). If not specified, imports all dandisets.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig']} })
    bibtex_file: Optional[str] = Field(default=None, description="""Path to BibTeX file (relative to collection YAML or absolute).""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig']} })
    bib_field: Optional[str] = Field(default=None, description="""BibTeX field to extract reference from (e.g., 'doi', 'url').""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig']} })
    ref_type: Optional[RefType] = Field(default=None, description="""Type of reference extracted from bib_field.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemRef', 'SourceConfig']} })
    ref_regex: Optional[str] = Field(default=None, description="""Regex pattern with named groups (?P<item_id>...) and optionally (?P<flavor_id>...) to parse reference into components. If flavor_id not captured, uses 'main'.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig']} })


class DiscoverConfig(ConfiguredBaseModel):
    """
    Configuration for citation discovery.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dandi/citations-collector'})

    sources: Optional[list[str]] = Field(default=[], description="""List of discovery source names to query (e.g., crossref, opencitations, datacite).""", json_schema_extra = { "linkml_meta": {'domain_of': ['DiscoverConfig']} })
    email: Optional[str] = Field(default=None, description="""Contact email for API polite pools.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DiscoverConfig']} })


class PdfsConfig(ConfiguredBaseModel):
    """
    Configuration for PDF retrieval.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dandi/citations-collector'})

    output_dir: Optional[str] = Field(default="pdfs/", description="""Directory to store downloaded PDFs.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PdfsConfig'], 'ifabsent': 'string(pdfs/)'} })
    unpaywall_email: Optional[str] = Field(default="site-unpaywall@oneukrainian.com", description="""Email for Unpaywall API.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PdfsConfig'],
         'ifabsent': 'string(site-unpaywall@oneukrainian.com)'} })
    git_annex: Optional[bool] = Field(default=False, description="""Store PDFs in git-annex instead of git.""", json_schema_extra = { "linkml_meta": {'domain_of': ['PdfsConfig'], 'ifabsent': 'false'} })


class ZoteroConfig(ConfiguredBaseModel):
    """
    Configuration for Zotero integration.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dandi/citations-collector'})

    group_id: Optional[int] = Field(default=None, description="""Zotero group library ID.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig', 'ZoteroConfig']} })
    collection_key: Optional[str] = Field(default=None, description="""Zotero collection key to sync into.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SourceConfig', 'ZoteroConfig']} })


class Collection(ConfiguredBaseModel):
    """
    A collection of tracked items. This is the root object that gets serialized to collection.yaml.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'schema:Collection',
         'exact_mappings': ['dcterms:Collection'],
         'from_schema': 'https://w3id.org/dandi/citations-collector',
         'tree_root': True})

    name: str = Field(default=..., description="""Name of the collection (e.g., \"DANDI\", \"ReproNim Tools\").""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemFlavor', 'Item', 'Collection'],
         'exact_mappings': ['schema:name', 'dcterms:title']} })
    description: Optional[str] = Field(default=None, description="""Description of the collection.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Item', 'Collection'],
         'exact_mappings': ['schema:description', 'dcterms:description']} })
    homepage: Optional[str] = Field(default=None, description="""URL to the collection homepage.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Item', 'Collection'],
         'exact_mappings': ['schema:url', 'foaf:homepage']} })
    maintainers: Optional[list[str]] = Field(default=[], description="""List of maintainer names or emails.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    source_type: Optional[str] = Field(default=None, description="""DEPRECATED: Use source.type instead. Hint for auto-import: \"dandi\", \"zenodo_org\", \"zenodo_collection\", \"github_org\", \"yaml\", etc.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    source_config: Optional[str] = Field(default=None, description="""DEPRECATED: Use source block instead. Configuration for auto-import (JSON string or nested object).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    output_tsv: Optional[str] = Field(default=None, description="""Path to the output TSV file for citations.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    source: Optional[SourceConfig] = Field(default=None, description="""Source configuration block.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    discover: Optional[DiscoverConfig] = Field(default=None, description="""Citation discovery configuration block.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    pdfs: Optional[PdfsConfig] = Field(default=None, description="""PDF retrieval configuration block.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    zotero: Optional[ZoteroConfig] = Field(default=None, description="""Zotero integration configuration block.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    zotero_group_id: Optional[int] = Field(default=None, description="""DEPRECATED: Use zotero.group_id instead. Zotero group ID for syncing.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    zotero_collection_key: Optional[str] = Field(default=None, description="""DEPRECATED: Use zotero.collection_key instead. Zotero parent collection key.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })
    items: Optional[list[Item]] = Field(default=[], description="""Items in this collection.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Collection']} })


class CurationRule(ConfiguredBaseModel):
    """
    A rule for automatic curation.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dandi/citations-collector'})

    rule_id: str = Field(default=..., description="""Unique identifier for this rule.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationRule']} })
    rule_type: str = Field(default=..., description="""Type of rule: \"ignore_doi_prefix\", \"ignore_doi\", \"merge_preprint\", \"auto_merge_preprint\", \"flag_for_review\".""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationRule']} })
    pattern: str = Field(default=..., description="""Pattern to match (DOI prefix, regex, etc.).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationRule']} })
    action: str = Field(default=..., description="""Action to take (ignore, merge, flag).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationRule']} })
    target: Optional[str] = Field(default=None, description="""Target for merge actions.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationRule']} })
    comment: Optional[str] = Field(default=None, description="""Explanation of why this rule exists.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationRule']} })
    created_by: Optional[str] = Field(default=None, description="""Who created this rule.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationRule']} })
    created_date: Optional[date] = Field(default=None, description="""When this rule was created.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationRule']} })


class CurationConfig(ConfiguredBaseModel):
    """
    Configuration for automatic curation.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dandi/citations-collector'})

    rules: Optional[list[CurationRule]] = Field(default=[], description="""Curation rules to apply automatically.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationConfig']} })
    preprint_doi_prefixes: Optional[list[str]] = Field(default=[], description="""DOI prefixes that indicate preprints. Default: 10.1101 (bioRxiv), 10.21203 (Research Square), 10.2139 (SSRN).""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationConfig']} })
    ignored_doi_prefixes: Optional[list[str]] = Field(default=[], description="""DOI prefixes to always ignore.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationConfig']} })
    auto_merge_preprints: Optional[bool] = Field(default=None, description="""If true, automatically merge preprints when published version is found citing the same item.""", json_schema_extra = { "linkml_meta": {'domain_of': ['CurationConfig']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
ItemRef.model_rebuild()
ItemFlavor.model_rebuild()
Item.model_rebuild()
CitationRecord.model_rebuild()
SourceConfig.model_rebuild()
DiscoverConfig.model_rebuild()
PdfsConfig.model_rebuild()
ZoteroConfig.model_rebuild()
Collection.model_rebuild()
CurationRule.model_rebuild()
CurationConfig.model_rebuild()

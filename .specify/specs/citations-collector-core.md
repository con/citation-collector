# Feature Specification: Citations Collector

**Feature Branch**: `001-citations-collector-core`
**Created**: 2026-01-17
**Status**: Draft
**Input**: A helper to discover, consolidate, and curate scholarly papers that cite digital products (datasets, software) identified by DOIs/RRIDs. Supports hierarchical collections (e.g., DANDI dandisets with versions) and syncs to Zotero.

## Prior Art

**[SciCrunch/SPARC-Citations](https://github.com/SciCrunch/SPARC-Citations)** - Reference for SPARC datasets:
- Uses TSV format (`dataset_data_citations.tsv`) for git-friendly curation
- Queries multiple sources: CrossRef, OpenCitations (OCI), DataCite, manual curation
- Tracks `citation_source` (provenance) and `citation_relationship` (IsDocumentedBy, Describes, Cites)
- Python scripts + shell orchestration, runs via cron

**License**: UC Copyright (non-commercial only) - **cannot reuse code**.

We take **inspiration** from their approach (TSV schema concept, multi-source pattern, relationship tracking) but must implement everything from scratch under MIT license.

## Overview

This tool answers: "What papers cite my dataset/software?" It:
1. Takes a hierarchical structure of DOIs (e.g., dandisets → versions → DOI)
2. Discovers papers citing each DOI via CrossRef, OpenCitations, DataCite
3. Supports curation: ignore bogus citations, merge preprint→published
4. Syncs the hierarchical citation collection to Zotero
5. Stores everything in a git repository for version control and CI automation

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover Citing Papers for a DOI (Priority: P1)

As a dataset maintainer, I want to find all papers that cite my dataset's DOI so that I can track the impact of my data.

**Why this priority**: This is the core capability. Without discovering citations, nothing else works.

**Independent Test**: Provide a known DOI with citations and verify papers are returned.

**Acceptance Scenarios**:

1. **Given** a DOI with known citations (e.g., "10.48324/dandi.000003/0.210812.1448"), **When** I call `discover_citations("10.48324/dandi.000003/0.210812.1448")`, **Then** I receive a list of Citation objects representing papers that cite this DOI.
2. **Given** the same DOI, **When** citations are fetched from both CrossRef and OpenCitations, **Then** results are merged and deduplicated by DOI.
3. **Given** a DOI with no citations, **When** I call `discover_citations(doi)`, **Then** I receive an empty list (not an error).

---

### User Story 2 - Load Hierarchical Collection from YAML (Priority: P1)

As a project maintainer, I want to define my collection hierarchy in a YAML file so that citations are organized by project/version.

**Why this priority**: The hierarchical structure is central to organizing citations for multi-version datasets.

**Independent Test**: Load a YAML file and verify the hierarchy is parsed correctly.

**Acceptance Scenarios**:

1. **Given** a YAML file defining items with flavors and refs:
   ```yaml
   name: DANDI Archive
   items:
     - item_id: "dandi:000003"
       name: "Hippocampal Granule Cells"
       flavors:
         - flavor_id: "0.210812.1448"
           refs:
             - ref_type: doi
               ref_value: "10.48324/dandi.000003/0.210812.1448"
         - flavor_id: "0.220126.1853"
           refs:
             - ref_type: doi
               ref_value: "10.48324/dandi.000003/0.220126.1853"
   ```
   **When** I load this file, **Then** a `Collection` object is created with the correct hierarchy.

2. **Given** a collection with items having multiple ref types (DOI + RRID):
   ```yaml
   items:
     - item_id: datalad
       flavors:
         - flavor_id: latest
           refs:
             - ref_type: rrid
               ref_value: SCR_003931
             - ref_type: doi
               ref_value: "10.5281/zenodo.808846"
   ```
   **When** I call `collection.discover_all_citations()`, **Then** citations are discovered by querying ALL refs for each flavor.

---

### User Story 3 - Import from External Sources (Priority: P2)

As a user, I want to import DOIs from sources like Zenodo collections or DANDI API so I don't have to manually maintain YAML files.

**Why this priority**: Automation reduces maintenance burden for large collections.

**Independent Test**: Query DANDI API and verify dandisets/versions are discovered.

**Acceptance Scenarios**:

1. **Given** the DANDI API, **When** I call `import_from_dandi()`, **Then** all dandisets and their version DOIs are discovered and returned as a hierarchy.
2. **Given** a Zenodo collection URL, **When** I call `import_from_zenodo(collection_url)`, **Then** all items in the collection are returned with their DOIs.
3. **Given** a GitHub organization on Zenodo, **When** I call `import_from_zenodo_org("dandi")`, **Then** all Zenodo deposits for that org are returned.

---

### User Story 4 - Curate Citations: Ignore Bogus (Priority: P1)

As a curator, I want to mark certain citations as "bogus" so they are permanently ignored in future runs.

**Why this priority**: False positives from citation APIs need to be filtered out.

**Independent Test**: Mark a citation as ignored, re-run discovery, verify it's excluded.

**Acceptance Scenarios**:

1. **Given** a citation that is a false positive, **When** I mark it with `curation.ignore(doi="10.1234/bogus", reason="Not actually citing our work")`, **Then** it is recorded in the curation file.
2. **Given** a curation file with ignored DOIs, **When** citations are discovered, **Then** ignored DOIs are filtered out of results.
3. **Given** an ignored citation, **When** I call `curation.unignore(doi)`, **Then** it is removed from the ignore list.

---

### User Story 5 - Curate Citations: Merge Preprint with Published (Priority: P2)

As a curator, I want to merge a preprint citation with its published version so they appear as one entry.

**Why this priority**: Common scenario where both preprint and published paper cite the same dataset.

**Independent Test**: Define a merge rule, verify only the published version appears.

**Acceptance Scenarios**:

1. **Given** a preprint DOI and its published DOI, **When** I call `curation.merge(preprint="10.1101/preprint", published="10.1234/published")`, **Then** the merge is recorded.
2. **Given** a merge rule exists, **When** citations are processed, **Then** the preprint is replaced by the published version.
3. **Given** a merge rule, **When** I export citations, **Then** only the published DOI appears with a note about the preprint.

---

### User Story 6 - Persist Collection State as TSV (Priority: P1)

As a maintainer, I want all citation data stored in a TSV file (like SPARC-Citations) so it's git-friendly and manually editable.

**Why this priority**: Version control is essential for curation decisions and CI automation. TSV is easy to diff and edit.

**Independent Test**: Save collection, verify TSV is created with correct columns, load and verify round-trip.

**Acceptance Scenarios**:

1. **Given** a collection with discovered citations, **When** I call `collection.save()`, **Then** a TSV file is written with columns:
   ```
   dataset_id  dataset_doi  dataset_name  citation_doi  citation_relationship  citation_type  citation_source  citation_status  citation_merged_into  citation_comment  citation_title  citation_authors  citation_year
   ```
2. **Given** a TSV with `citation_status=ignored`, **When** loaded, **Then** those citations are filtered from active results.
3. **Given** a TSV with `citation_merged_into=10.1234/published`, **When** loaded, **Then** the preprint is replaced by the published version.
4. **Given** the collection is in a git repo, **When** citations change, **Then** diffs show exactly which rows changed.

---

### User Story 7 - Sync to Zotero (Priority: P2)

As a project maintainer, I want to sync my citation collection to Zotero so it's browsable and shareable.

**Why this priority**: Zotero provides a collaborative interface for exploring citations.

**Independent Test**: Sync a collection, verify Zotero structure matches hierarchy.

**Acceptance Scenarios**:

1. **Given** a collection hierarchy and Zotero API credentials, **When** I call `sync_to_zotero(collection, group_id, parent_collection)`, **Then** sub-collections are created matching the hierarchy.
2. **Given** the hierarchy `dandi/000003/0.210812.1448`, **When** synced, **Then** Zotero has:
   - Collection "000003" under parent
   - Sub-collection "0.210812.1448" under "000003"
   - Citation items in the version sub-collection
3. **Given** an existing Zotero structure, **When** synced again, **Then** only new/changed items are updated (incremental sync).

---

### User Story 8 - CLI for Common Operations (Priority: P2)

As a user, I want CLI commands for discovery and sync so I can run them manually or in CI.

**Why this priority**: CLI enables automation via cron jobs and CI pipelines.

**Acceptance Scenarios**:

1. `citations-collector discover collection.yaml` - discover citations for all DOIs
2. `citations-collector sync-zotero collection.yaml --group 5774211` - sync to Zotero
3. `citations-collector import-dandi --output dandi-collection.yaml` - import from DANDI API
4. `citations-collector curate ignore 10.1234/bogus --reason "False positive"` - add ignore rule

---

### User Story 9 - CI Automation (Priority: P3)

As a maintainer, I want a GitHub Actions workflow that periodically updates citations.

**Why this priority**: Automated updates ensure the collection stays current.

**Reference**: See `examples/github-ci-workflow.yaml` for a complete workflow example.

**Acceptance Scenarios**:

1. **Given** a cron schedule (e.g., weekly), **When** the workflow runs, **Then** it:
   - Discovers new citations (incrementally, using `last_updated`)
   - Commits changes if any
   - Optionally syncs to Zotero
2. **Given** new citations are found, **When** committed, **Then** the commit message lists what changed.
3. **Given** `workflow_dispatch` with `full_refresh=true`, **When** triggered manually, **Then** it bypasses incremental mode.
4. **Given** secrets `CROSSREF_EMAIL` and `ZOTERO_API_KEY` are configured, **When** workflow runs, **Then** it uses polite pool and syncs to Zotero.

---

### Edge Cases

- CrossRef data-citations API requires Polite pool (email in User-Agent, plus `mailto` query parameter for the `/beta/datacitations` endpoint) for better rate limits
- OpenCitations may have delayed indexing (weeks behind CrossRef)
- Zotero API rate limits: 6 requests/second for single-key auth
- Large collections: batch API calls, implement progress reporting
- Network failures: retry with backoff, save partial progress
- Preprint detection: use DOI prefixes (10.1101 for bioRxiv, 10.21203 for Research Square)

### Incremental Updates (Efficiency)

APIs support date-based filtering for efficient incremental queries:

- **CrossRef** (`/beta/datacitations`): `from-created-date` query parameter (date only, `YYYY-MM-DD`)
  - Example: `?object-id=<DOI>&from-created-date=2024-01-15`
  - Filters by ingestion timestamp into CrossRef's data-citations database (~5 day lag from member deposit)
- **OpenCitations**: `filter=date:>YYYY-MM-DD` parameter
  - Example: `?filter=date:>2024-01-15`
- **DataCite**: `registered` filter supports date ranges

The system should:
1. Store `last_updated` timestamp per collection
2. On subsequent runs, only query for citations since last update
3. Merge new citations with existing, preserving curation status
4. Support `--full-refresh` flag to bypass incremental mode

## Requirements *(mandatory)*

### Functional Requirements

**Citation Discovery:**
- **FR-001**: System MUST discover papers citing a DOI via the CrossRef data-citations API (`api.crossref.org/beta/datacitations`)
- **FR-002**: System MUST discover papers citing a DOI via OpenCitations (OCI) API
- **FR-003**: System MUST discover papers citing a DOI via DataCite API
- **FR-004**: System MUST merge and deduplicate results from multiple sources
- **FR-005**: System MUST track `citation_source` provenance for each discovered citation

**Collection Management:**
- **FR-006**: System MUST support hierarchical collection definitions via YAML
- **FR-007**: System MUST persist all data in TSV format (git-friendly, manually editable)
- **FR-008**: System MUST track `citation_relationship` (Cites, IsDocumentedBy, Describes, etc.)

**Curation:**
- **FR-009**: System MUST support `citation_status` column (active, ignored)
- **FR-010**: System MUST support `citation_merged_into` column for preprint→published
- **FR-011**: System MUST filter ignored citations from active results
- **FR-012**: System MUST replace preprints with published versions per merge rules

**Zotero Integration:**
- **FR-013**: System MUST sync discovered citations TO Zotero as nested collections
- **FR-014**: System MUST support incremental Zotero sync (only update changes)
- **FR-015**: System MAY import items FROM a Zotero collection as a source of DOIs to track
- **FR-016**: Zotero sync should use `pyzotero` library (see [dandi-bib reference](https://github.com/dandi/dandi-bib/blob/master/code/update-zotero-collection))

**Incremental Updates (Efficiency):**
- **FR-017**: System MUST support incremental citation discovery using API date filters
- **FR-018**: System MUST store `last_updated` timestamp and use it for subsequent queries
- **FR-019**: System MUST merge new citations with existing, preserving curation status
- **FR-020**: CLI MUST support `--full-refresh` flag to bypass incremental mode

**Zenodo Version Discovery:**
- **FR-021**: System MUST support `zenodo_concept` ref type (concept DOI or parent.id)
- **FR-022**: Given a concept DOI (e.g., `10.5281/zenodo.1012598`) or parent.id (`1012598`), system MUST auto-discover all version DOIs via Zenodo API (`parent.id:X&f=allversions:true`)
- **FR-023**: System MUST query citations for BOTH concept DOI AND all version DOIs

**Importers & CLI:**
- **FR-024**: System MUST provide importers for DANDI API, Zenodo collections/orgs
- **FR-025**: CLI MUST support discover, sync, import, and curate commands

### Key Entities

**Defined in LinkML schema**: `schema/citations.yaml` (v0.2.0)

Generated outputs:
- Pydantic models: `src/citations_collector/models/generated.py`
- JSON Schema: `schema/citations.schema.json`

**Enums:**
- `RefType`: doi, rrid, arxiv, pmid, pmcid, url, zenodo, github
- `CitationRelationship`: Cites, IsDocumentedBy, Describes, IsSupplementedBy, References, Uses, IsDerivedFrom
- `CitationType`: Publication, Preprint, Protocol, Thesis, Book, Software, Dataset, Other
- `CitationSource`: crossref, opencitations, datacite, europepmc, semantic_scholar, scicrunch, manual
- `CitationStatus`: active, ignored, merged, pending

**Classes:**
- **Collection** (tree root): Container for tracked items
  - Attributes: name, description, homepage, maintainers, source_type, source_config, zotero_group_id, zotero_collection_key, items
  - Persistence: `collection.yaml`

- **Item**: A tracked resource (dataset, tool, software)
  - Attributes: item_id (can use `:` for namespacing, e.g., "dandi:000003"), name, description, homepage, flavors
  - The `item_id` encodes optional hierarchy via `:` separator

- **ItemFlavor**: A version/variant of an item
  - Attributes: flavor_id (e.g., "0.210812.1448", "23.1.0", "latest"), name, release_date, refs, citations
  - Use "main" or "latest" for unversioned items

- **ItemRef**: A resolvable identifier
  - Attributes: ref_type, ref_value, ref_url
  - Multiple refs per flavor allowed (DOI + RRID + GitHub)

- **CitationRecord**: A citation relationship (row in TSV)
  - Item fields: item_id, item_flavor, item_ref_type, item_ref_value, item_name
  - Citation fields: citation_doi, citation_pmid, citation_arxiv, citation_url, citation_title, citation_authors, citation_year, citation_journal
  - Relationship: citation_relationship, citation_type
  - Provenance: citation_source, discovered_date
  - Curation: citation_status, citation_merged_into, citation_comment, curated_by, curated_date
  - Unique key: (item_id, item_flavor, citation_doi)
  - Persistence: `citations.tsv`

- **CurationRule** / **CurationConfig**: Automatic curation rules
  - Attributes: preprint_doi_prefixes, ignored_doi_prefixes, auto_merge_preprints

**Non-schema classes (implementation):**
- **CitationDiscoverer**: Queries external APIs for citing papers
  - Sources: CrossRef (data-citations), OpenCitations (OCI), DataCite, OpenAlex, SciCrunch (RRID)
  - Supports incremental queries via date filters (`from-created-date` on CrossRef, `filter=date:>` on OpenCitations, etc.)
- **ZoteroSync**: Handles Zotero API interaction via `pyzotero` library
  - Primary: Push discovered citations TO Zotero as nested collections
  - Optional: Import items FROM Zotero collection as source of DOIs to track
  - Reference: [dandi-bib/update-zotero-collection](https://github.com/dandi/dandi-bib/blob/master/code/update-zotero-collection)
- **Importer** (abstract): Import items from external sources
  - DANDIImporter: Query DANDI API for dandisets and versions
  - ZenodoImporter: Query Zenodo for org/collection DOIs
  - ZoteroImporter: Import from existing Zotero collection
  - YAMLImporter: Load from local YAML file

## Future Considerations (TODOs)

- **PDF Storage**: Use git-annex to store PDFs of citing papers
- **Additional Importers**: GitHub releases, PyPI packages, npm packages
- **Citation Metrics**: Track citation counts over time
- **Notification**: Alert when new citations are discovered
- **Web UI**: Simple dashboard for viewing collection status

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Discover 95%+ of citations findable via CrossRef/OpenCitations
- **SC-002**: Zotero sync creates correct hierarchy matching input structure
- **SC-003**: Curation rules correctly filter/merge citations on subsequent runs
- **SC-004**: CI workflow successfully runs on schedule without manual intervention
- **SC-005**: Collection state survives git clone and load() recovers full state
- **SC-006**: Incremental operations (discover, sync) complete in reasonable time for 1000+ citations

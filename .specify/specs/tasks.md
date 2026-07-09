---
description: "Implementation tasks for citations-collector project"
---

# Tasks: Citations Collector

**Input**: Implementation plan at `~/.claude/plans/adaptive-cooking-lemur.md`, feature spec at `.specify/specs/citations-collector-core.md`
**Prerequisites**: LinkML schema (schema/citations.yaml), Constitution (CONSTITUTION.md), Examples (examples/)

**Tests**: Tests are MANDATORY per constitution - all code paths must be tested with pytest

**Organization**: Tasks grouped by implementation phases from the plan, with clear dependencies

## Format: `[ID] [P?] [Phase] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Phase]**: Which phase this task belongs to (Setup, P1, P2, P3, P4, P5, P6)

## Phase 0: Setup (Foundation - No Code Yet)

**Purpose**: Bootstrap project structure and build system
**Checkpoint**: Can install package, run `tox`, all checks pass

- [ ] T001 Create `pyproject.toml` with hatch-vcs, layered extras (test, devel, ci, linkml)
- [ ] T002 Create `tox.ini` with default envlist=py3{10,11,12},lint,type
- [ ] T003 [P] Create `.github/workflows/ci.yaml` invoking tox
- [ ] T004 [P] Create `README.md` with installation, quick start, LinkML regeneration instructions
- [ ] T005 Create `src/citations_collector/__init__.py` (empty, will export public API later)
- [ ] T006 [P] Create `src/citations_collector/py.typed` (PEP 561 marker)
- [ ] T007 Create `tests/__init__.py` and `tests/conftest.py` with basic fixtures
- [ ] T008 Install linkml with `uv pip install linkml` (in separate step, not in pyproject.toml runtime deps)
- [ ] T009 Generate Pydantic models: `gen-pydantic schema/citations.yaml > src/citations_collector/models/generated.py`
- [ ] T010 [P] Generate JSON Schema: `gen-json-schema schema/citations.yaml > schema/citations.schema.json`
- [ ] T011 Create `src/citations_collector/models/__init__.py` re-exporting generated models
- [ ] T012 Validate: `uv venv && source .venv/bin/activate && uv pip install -e ".[devel]" && tox -e lint,type` passes

**Checkpoint**: Project structure ready, `tox -e lint,type` passes, models importable

---

## Phase 1: Persistence Layer (P1 - Core Infrastructure)

**Purpose**: Load/save YAML collections and TSV citations with full round-trip fidelity
**Dependencies**: Phase 0 complete
**Checkpoint**: Can load examples/, save, reload, byte-identical output

### Tests for Persistence (Write First, Ensure Fail)

- [ ] T013 [P] [P1] Create `tests/fixtures/collections/simple.yaml` - minimal test collection
- [ ] T014 [P] [P1] Create `tests/fixtures/tsv/simple.tsv` - minimal test citations
- [ ] T015 [P] [P1] Copy examples/repronim-tools.yaml to tests/fixtures/collections/
- [ ] T016 [P] [P1] Copy examples/citations-example.tsv to tests/fixtures/tsv/
- [ ] T017 [P1] Create `tests/test_persistence.py` with test_load_yaml_round_trip (SHOULD FAIL)
- [ ] T018 [P1] Add test_load_tsv_round_trip to tests/test_persistence.py (SHOULD FAIL)
- [ ] T019 [P1] Add test_missing_optional_fields to tests/test_persistence.py (SHOULD FAIL)
- [ ] T020 [P1] Add test_validation_errors to tests/test_persistence.py (SHOULD FAIL)
- [ ] T021 Mark all tests in test_persistence.py with @pytest.mark.ai_generated

### Implementation for Persistence

- [ ] T022 [P] [P1] Create `src/citations_collector/persistence/__init__.py` with exports
- [ ] T023 [P1] Implement `load_collection()` in `src/citations_collector/persistence/yaml_io.py`
- [ ] T024 [P1] Implement `save_collection()` in `src/citations_collector/persistence/yaml_io.py`
- [ ] T025 [P1] Implement `load_citations()` in `src/citations_collector/persistence/tsv_io.py`
- [ ] T026 [P1] Implement `save_citations()` in `src/citations_collector/persistence/tsv_io.py`
- [ ] T027 Validate: All tests in test_persistence.py pass, `tox -e py312` passes

**Checkpoint**: Can load examples/repronim-tools.yaml, verify Item/ItemFlavor structure, save/reload

---

## Phase 2: Citation Discovery (P1 - Core Feature)

**Purpose**: Discover citations via CrossRef, OpenCitations, DataCite APIs
**Dependencies**: Phase 1 complete (need models and persistence)
**Checkpoint**: Can query real DOI, get citations, handle errors gracefully

### Tests for Discovery (Write First, Ensure Fail)

- [ ] T028 [P] [P2] Create `tests/fixtures/responses/crossref_success.json` - mock API response
- [ ] T029 [P] [P2] Create `tests/fixtures/responses/crossref_empty.json` - no citations
- [ ] T030 [P] [P2] Create `tests/fixtures/responses/opencitations_success.json` - mock response
- [ ] T031 [P2] Create `tests/test_discovery.py` with test_crossref_success (SHOULD FAIL)
- [ ] T032 [P2] Add test_crossref_empty_results to tests/test_discovery.py (SHOULD FAIL)
- [ ] T033 [P2] Add test_crossref_network_error to tests/test_discovery.py (SHOULD FAIL)
- [ ] T034 [P2] Add test_opencitations_discovery to tests/test_discovery.py (SHOULD FAIL)
- [ ] T035 [P2] Add test_incremental_date_filtering to tests/test_discovery.py (SHOULD FAIL)
- [ ] T036 [P2] Add test_deduplication_across_sources to tests/test_discovery.py (SHOULD FAIL)
- [ ] T037 Mark all tests in test_discovery.py with @pytest.mark.ai_generated

### Implementation for Discovery

- [ ] T038 [P] [P2] Create `src/citations_collector/discovery/__init__.py` with exports
- [ ] T039 [P2] Implement AbstractDiscoverer in `src/citations_collector/discovery/base.py`
- [ ] T040 [P2] Implement CrossRefDiscoverer in `src/citations_collector/discovery/crossref.py`
  - Support email for polite pool (User-Agent header)
  - Support `since` parameter for incremental (from-created-date filter on /beta/datacitations)
  - Graceful degradation on 404/network errors (return empty list)
- [ ] T041 [P2] Implement OpenCitationsDiscoverer in `src/citations_collector/discovery/opencitations.py`
  - Support `since` parameter (filter=date:>YYYY-MM-DD)
  - Graceful degradation on errors
- [ ] T042 [P] [P2] Implement DataCiteDiscoverer in `src/citations_collector/discovery/datacite.py`
- [ ] T043 [P] [P2] Implement utility functions in `src/citations_collector/discovery/utils.py`
  - `build_doi_url(doi: str) -> str`
  - `deduplicate_citations(citations: list[CitationRecord]) -> list[CitationRecord]`
- [ ] T044 Validate: All tests in test_discovery.py pass with mocked responses, `tox -e py312` passes

**Checkpoint**: Can discover citations for DOI 10.48324/dandi.000003/0.210812.1448 (test with real API)

---

## Phase 3: Core Orchestration (P1 - Main Library API)

**Purpose**: CitationCollector class as primary library entry point
**Dependencies**: Phase 1 + Phase 2 complete (need persistence + discovery)
**Checkpoint**: End-to-end workflow works programmatically

### Tests for Core (Write First, Ensure Fail)

- [ ] T045 [P] [P3] Create `tests/test_core.py` with test_from_yaml (SHOULD FAIL)
- [ ] T046 [P3] Add test_discover_all_with_mocks to tests/test_core.py (SHOULD FAIL)
- [ ] T047 [P3] Add test_incremental_vs_full_refresh to tests/test_core.py (SHOULD FAIL)
- [ ] T048 [P3] Add test_merge_citations_preserve_curation to tests/test_core.py (SHOULD FAIL)
- [ ] T049 [P3] Add test_save_workflow to tests/test_core.py (SHOULD FAIL)
- [ ] T050 Mark all tests in test_core.py with @pytest.mark.ai_generated

### Implementation for Core

- [ ] T051 [P3] Create `src/citations_collector/core.py` with CitationCollector class
- [ ] T052 [P3] Implement `__init__(collection: Collection)` method
- [ ] T053 [P3] Implement `from_yaml(path: Path) -> CitationCollector` classmethod
- [ ] T054 [P3] Implement `discover_all(sources, incremental, email)` method
  - Initialize CrossRefDiscoverer, OpenCitationsDiscoverer
  - Iterate over collection.items → flavors → refs
  - Call discoverers, merge/deduplicate results
  - Update collection.last_updated
- [ ] T055 [P3] Implement `load_existing_citations(path: Path)` method
- [ ] T056 [P3] Implement `merge_citations(new_citations)` method
  - Use unique key (item_id, item_flavor, citation_doi)
  - Preserve existing citation_status, citation_comment
- [ ] T057 [P3] Implement `save(yaml_path: Path, tsv_path: Path)` method
- [ ] T058 Update `src/citations_collector/__init__.py` to export CitationCollector, Collection
- [ ] T059 Validate: All tests in test_core.py pass, `tox -e py312` passes

**Checkpoint**: Can load repronim-tools.yaml, mock discover, verify citations populated, save TSV

---

## Phase 4: CLI (P2 - User Interface)

**Purpose**: Click-based CLI as thin wrapper around core library
**Dependencies**: Phase 3 complete (need CitationCollector)
**Checkpoint**: CLI works end-to-end, DANDI integration test passes

### Tests for CLI (Write First, Ensure Fail)

- [ ] T060 [P] [P4] Create `tests/test_cli.py` with test_discover_command (SHOULD FAIL)
- [ ] T061 [P4] Add test_discover_full_refresh_flag to tests/test_cli.py (SHOULD FAIL)
- [ ] T062 [P4] Add test_discover_email_env_var to tests/test_cli.py (SHOULD FAIL)
- [ ] T063 [P4] Add test_sync_zotero_placeholder to tests/test_cli.py (SHOULD FAIL)
- [ ] T064 [P4] Create `tests/test_dandi_integration.py` with test_dandi_full_workflow (SHOULD FAIL)
  - Load examples/dandi-collection.yaml
  - Mock discover for dandi:000003 and dandi:000005 DOIs
  - Verify TSV has hierarchical item_id (dandi:000003 format)
  - Run discover twice (incremental), verify no duplicates, last_updated changes
- [ ] T065 Mark all CLI tests with @pytest.mark.ai_generated

### Implementation for CLI

- [ ] T066 [P4] Create `src/citations_collector/cli.py` with main Click group
- [ ] T067 [P4] Implement `discover` command
  - Arguments: collection (Path)
  - Options: --output, --full-refresh, --email (with envvar=CROSSREF_EMAIL)
  - Logic: Load collection, load existing TSV if exists, discover, save
  - Progress output with click.echo
- [ ] T068 [P4] Implement `sync-zotero` command placeholder (click.echo "Not yet implemented")
- [ ] T069 [P4] Add `@click.version_option()` to main group
- [ ] T070 Validate: All CLI tests pass, `citations-collector discover examples/repronim-tools.yaml --output /tmp/test.tsv` works

**Checkpoint**: Can run `citations-collector discover collection.yaml`, TSV created with correct schema

---

## Phase 5: DANDI Integration Validation (Success Criteria)

**Purpose**: Validate full workflow with real DANDI dandisets
**Dependencies**: Phase 4 complete
**Checkpoint**: All success criteria met, ready for v0.1.0 release

- [ ] T071 [P5] Run `tox` (no arguments) - all environments must pass
- [ ] T072 [P5] Load examples/dandi-collection.yaml successfully
- [ ] T073 [P5] Discover citations for DOI 10.48324/dandi.000003/0.210812.1448 (real API call)
- [ ] T074 [P5] Verify TSV output matches examples/citations-example.tsv schema
- [ ] T075 [P5] Run test_dandi_integration.py with mock responses - verify passes
- [ ] T076 [P5] Test incremental discovery workflow:
  - Run discover on dandi-collection.yaml
  - Note last_updated timestamp
  - Run discover again (incremental=True)
  - Verify no duplicate citations
  - Verify last_updated changed
- [ ] T077 [P5] Validate CLI end-to-end: `citations-collector discover examples/dandi-collection.yaml`

**Checkpoint**: MVP complete! All Phase 1-5 success criteria met, ready to tag v0.1.0

---

## Phase 6: Advanced Features (Post-MVP - P2/P3)

**Purpose**: Importers, Zotero sync, curation, additional discoverers
**Dependencies**: Phase 5 complete (MVP released)

### Importers

- [ ] T078 [P] [P6] Create `src/citations_collector/importers/__init__.py`
- [ ] T079 [P] [P6] Implement AbstractImporter in `src/citations_collector/importers/base.py`
- [ ] T080 [P6] Implement DANDIImporter in `src/citations_collector/importers/dandi.py`
  - Query DANDI API for all dandisets
  - Extract versions and version DOIs
  - Return Collection object
- [ ] T081 [P6] Implement ZenodoImporter in `src/citations_collector/importers/zenodo.py`
  - Support zenodo_concept expansion (parent.id:X&f=allversions:true)
  - Return all version DOIs for a concept DOI
- [ ] T082 [P6] Add CLI command `import-dandi --output collection.yaml`
- [ ] T083 [P6] Add CLI command `import-zenodo CONCEPT_DOI --output collection.yaml`
- [ ] T084 [P6] Tests for importers in `tests/test_importers.py` (@pytest.mark.ai_generated)

### Zotero Sync

- [ ] T085 [P] [P6] Create `src/citations_collector/zotero/__init__.py`
- [ ] T086 [P6] Implement ZoteroSync in `src/citations_collector/zotero/sync.py`
  - Use pyzotero library
  - Create nested collections matching hierarchy
  - Incremental sync (check existing items)
  - Reference: https://github.com/dandi/dandi-bib/blob/master/code/update-zotero-collection
- [ ] T087 [P6] Implement `sync_to_zotero()` method in CitationCollector
- [ ] T088 [P6] Update CLI `sync-zotero` command with real implementation
  - Options: --api-key (envvar=ZOTERO_API_KEY), --group-id
- [ ] T089 [P6] Tests for Zotero sync in `tests/test_zotero.py` (@pytest.mark.ai_generated)

### Curation

- [ ] T090 [P] [P6] Create `src/citations_collector/curation/__init__.py`
- [ ] T091 [P6] Implement curation logic in `src/citations_collector/curation/rules.py`
  - Apply ignore rules from TSV citation_status
  - Merge preprints into published versions
  - Detect preprints by DOI prefix (10.1101, 10.21203, 10.2139)
- [ ] T092 [P6] Add CLI command `curate ignore DOI --reason "text"`
- [ ] T093 [P6] Add CLI command `curate merge PREPRINT_DOI PUBLISHED_DOI`
- [ ] T094 [P6] Tests for curation in `tests/test_curation.py` (@pytest.mark.ai_generated)

### Additional Discoverers

- [ ] T095 [P] [P6] Implement EuropePMCDiscoverer in `src/citations_collector/discovery/europepmc.py`
- [ ] T096 [P] [P6] Implement SemanticScholarDiscoverer in `src/citations_collector/discovery/semantic_scholar.py`
- [ ] T097 [P] [P6] Implement SciCrunchDiscoverer in `src/citations_collector/discovery/scicrunch.py`
- [ ] T098 [P6] Update discover_all() to support all discoverers
- [ ] T099 [P6] Tests for new discoverers in tests/test_discovery.py

### Zenodo Synchronization (Ultimate Success Criterion)

- [ ] T100 [P6] Implement bidirectional Zenodo sync
  - Import: zenodo_concept expansion to all version DOIs
  - Export: Update Zenodo records with discovered citations metadata
  - Incremental: Only update changed records
- [ ] T101 [P6] Add CLI command `sync-zenodo --api-key XXX --mode {import|export|both}`
- [ ] T102 [P6] Integration test for Zenodo sync in `tests/test_zenodo_integration.py`

**Checkpoint**: All advanced features complete, ultimate success criteria met

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0 (Setup)**: No dependencies - START HERE
- **Phase 1 (Persistence)**: Requires Phase 0 complete
- **Phase 2 (Discovery)**: Requires Phase 1 complete (needs models)
- **Phase 3 (Core)**: Requires Phase 1 + Phase 2 complete
- **Phase 4 (CLI)**: Requires Phase 3 complete
- **Phase 5 (Validation)**: Requires Phase 4 complete
- **Phase 6 (Advanced)**: Requires Phase 5 complete (post-MVP)

### Critical Path for MVP (v0.1.0)

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 (Release!)
```

### Parallel Opportunities

**Within Phase 0**:
- T003, T004, T006 can run in parallel
- T010 can run in parallel with T009

**Within Phase 1**:
- T013-T016 (create fixtures) all parallel
- T021 (mark tests) after T017-T020
- T022-T026 (implementation files) parallel after tests written

**Within Phase 2**:
- T028-T030 (create fixtures) all parallel
- T042, T043 can run in parallel with T040-T041
- T031-T037 tests before implementation

**Within Phase 6**:
- All importer tasks (T078-T084) can run in parallel
- All Zotero tasks (T085-T089) can run in parallel
- All curation tasks (T090-T094) can run in parallel
- All new discoverer tasks (T095-T099) can run in parallel

### Within Each Phase

1. Write tests FIRST (ensure they FAIL)
2. Implement code to make tests pass
3. Run `tox` to validate
4. Checkpoint validation before next phase

---

## Implementation Strategy

### MVP First (Phases 0-5)

1. Complete Phase 0: Setup → Foundation ready
2. Complete Phase 1: Persistence → Can load/save
3. Complete Phase 2: Discovery → Can query APIs
4. Complete Phase 3: Core → Library API works
5. Complete Phase 4: CLI → User can run commands
6. Complete Phase 5: Validation → All success criteria met
7. **Tag v0.1.0 and release!**

### Post-MVP (Phase 6)

8. Add importers (DANDI, Zenodo concept expansion)
9. Add Zotero sync
10. Add curation features
11. Add additional discoverers
12. Implement Zenodo bidirectional sync (ultimate goal)
13. **Tag v0.2.0 with advanced features**

---

## Validation Checkpoints

After each phase, validate before proceeding:

- **Phase 0**: `tox -e lint,type` passes, models importable
- **Phase 1**: Load examples/repronim-tools.yaml, save/reload works
- **Phase 2**: Query real DOI, get citations
- **Phase 3**: End-to-end library workflow works
- **Phase 4**: CLI command works, DANDI integration test passes
- **Phase 5**: `tox` (all envs) passes, all success criteria met
- **Phase 6**: Advanced features validated individually

---

## Notes

- **[P]** = Can run in parallel (different files, no dependencies)
- **[Phase]** = Maps task to implementation phase
- **Tests FIRST**: Write failing tests before implementation (TDD)
- **@pytest.mark.ai_generated**: Mark all AI-written tests
- **Commit**: After each task or logical group
- **tox**: Run frequently to catch issues early
- **Checkpoint**: Validate phase completion before moving on
- **MVP Focus**: Complete Phases 0-5 before starting Phase 6

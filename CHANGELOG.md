# 0.2.4 (Mon Feb 02 2026)

#### 🐛 Bug Fix

- **CRITICAL: Fix bioRxiv/Cloudflare 403 errors** - Remove custom User-Agent that triggered bot detection [#3](https://github.com/con/citations-collector/pull/3) ([@yarikoptic](https://github.com/yarikoptic))
- Improve integration tests to detect User-Agent/Cloudflare issues - Tests now fail on 403 instead of skipping ([@yarikoptic](https://github.com/yarikoptic))
- Improve robustness: increase API timeouts, better error handling - Event Data APIs now 60s timeout, smarter 404/403 handling ([@yarikoptic](https://github.com/yarikoptic))
- Fix ruff formatting in openalex.py ([@yarikoptic](https://github.com/yarikoptic))

#### 🚀 Enhancement

- Add 5 dataset-specific citation relationship types (Phase 1) - Supports, Describes, Derives, Cites, References ([@yarikoptic](https://github.com/yarikoptic))
- Add ontology alignment to established vocabularies (Phase 1) - Maps to CiTO, DataCite, BIBO ontologies ([@yarikoptic](https://github.com/yarikoptic))
- Support multiple citation relationships per citation ([@yarikoptic](https://github.com/yarikoptic))

#### 🏠 Internal

- Add comprehensive ontology alignment documentation ([@yarikoptic](https://github.com/yarikoptic))
- Add comprehensive tooling and integration plan ([@yarikoptic](https://github.com/yarikoptic))
- Restore multi-source validation after schema regeneration ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# 0.2.3 (Fri Jan 31 2026)

#### 🚀 Enhancement

- BibTeX source type - Import items from external BibTeX files with regex-based parsing for item_id/flavor_id extraction
- Multi-source citation deduplication - Merge citations found by multiple discoverers into single TSV rows with comma-separated sources
- PDF download improvements - Retry logic with Retry-After header support and exponential backoff for bioRxiv rate limiting
- Progress bars - Real-time progress monitoring with tqdm for long-running discovery tasks
- HTML detection - Automatically detect and save HTML responses with correct extension when servers return HTML instead of PDF

#### 🐛 Bug Fix

- **CRITICAL: Fix bioRxiv/Cloudflare 403 errors** - Remove custom User-Agent that triggered bot detection, use default python-requests User-Agent
- Rename TSV column from citation_source to citation_sources (plural) for clarity
- Fix re-download prevention - Check both .pdf and .html extensions before downloading
- Fix TSV backward compatibility - Support both old citation_source and new citation_sources columns
- Add default citation_source value - Use "manual" for TSV files missing source field
- Improve logging with tqdm - Use logging_redirect_tqdm() for better real-time output

#### 📝 Documentation

- Update README with BibTeX source type examples and configuration
- Add real-world use case documentation - DANDI Archive (850+ dandisets), MICrONS, StudyForrest, ReproNim
- Document multi-source tracking - Explain comma-separated citation_sources format
- Add reference to dandi-bib complete pipeline for DANDI production setup
- Document PDF acquisition features - Retry logic, HTML detection, rate limiting

#### 🏠 Internal

- Add comprehensive tests for PDF retry logic - Unit tests with mocks and integration tests with real bioRxiv downloads
- Add cross-field validation - Pydantic model validator for citation_sources/discovered_dates coherence
- Improve rate limiting - 2-second delay between downloads, configurable download_delay parameter
- Fix test compatibility - Handle missing citation_source field in TSV files gracefully

#### ⚠️ Pushed to `master`

- Add reference to dandi-bib complete pipeline in README ([@yarikoptic](https://github.com/yarikoptic))
- Update README with BibTeX source, multi-source tracking, real examples ([@yarikoptic](https://github.com/yarikoptic))
- Add comprehensive tests for PDF retry logic and bioRxiv downloads ([@yarikoptic](https://github.com/yarikoptic))
- Improve PDF download retry logic and rate limiting for bioRxiv ([@yarikoptic](https://github.com/yarikoptic))
- Rename TSV column from citation_source to citation_sources ([@yarikoptic](https://github.com/yarikoptic))
- Simplify tqdm logging with logging_redirect_tqdm ([@yarikoptic](https://github.com/yarikoptic))
- Fix tqdm progress bar to show logging in real-time ([@yarikoptic](https://github.com/yarikoptic))
- Fix multi-source citation handling and PDF/HTML detection ([@yarikoptic](https://github.com/yarikoptic))
- Store multi-source citations as single TSV row ([@yarikoptic](https://github.com/yarikoptic))
- Improve reporting: group by DOI and show all discovery sources ([@yarikoptic](https://github.com/yarikoptic))
- Centralize citation count reporting and fix progress bar ([@yarikoptic](https://github.com/yarikoptic))
- Fix BibTeX source to not save items to YAML when update_items is omitted ([@yarikoptic](https://github.com/yarikoptic))
- Document per-source incremental discovery TODO ([@yarikoptic](https://github.com/yarikoptic))
- Add tqdm progress bar, improve logging, and add retry logic ([@yarikoptic](https://github.com/yarikoptic))
- Add debug logging and fix Makefile to use --full-refresh ([@yarikoptic](https://github.com/yarikoptic))
- Fix BibTeX importer to properly group flavors by item_id ([@yarikoptic](https://github.com/yarikoptic))
- Add BibTeX source type for external item management ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# 0.2.2 (Fri Jan 30 2026)

#### 🐛 Bug Fix

- Add auto-release automation [#1](https://github.com/con/citation-collector/pull/1) ([@yarikoptic](https://github.com/yarikoptic) [@yarikoptic-gitmate](https://github.com/yarikoptic-gitmate))

#### ⚠️ Pushed to `master`

- Add auto-release integration plan ([@yarikoptic](https://github.com/yarikoptic))
- Comment out sources in examples - default uses all available sources ([@yarikoptic](https://github.com/yarikoptic))
- Fix mypy type errors in DANDI and OpenAlex discoverers ([@yarikoptic](https://github.com/yarikoptic))
- Remove last_updated from Collection schema - derive from TSV instead ([@yarikoptic](https://github.com/yarikoptic))
- Add tox environment for updating example citations ([@yarikoptic](https://github.com/yarikoptic))
- Fix test: account for CrossRef metadata API call ([@yarikoptic](https://github.com/yarikoptic))
- Merge enh-zotero branch: Add OpenAlex support and multi-source tracking ([@yarikoptic](https://github.com/yarikoptic))
- Enable OpenAlex by default and fix example YAML structure ([@yarikoptic](https://github.com/yarikoptic))
- Fix OpenAlex discoverer to use OpenAlex IDs instead of DOIs in filter ([@yarikoptic](https://github.com/yarikoptic))
- Fix DataCite Event Data API query parameters ([@yarikoptic](https://github.com/yarikoptic))
- Add OpenAlex as a citation discovery source ([@yarikoptic](https://github.com/yarikoptic))
- Add multi-source citation tracking with coherence validation ([@yarikoptic](https://github.com/yarikoptic))
- Add CrossRef metadata coverage check and warnings ([@yarikoptic](https://github.com/yarikoptic))
- Add dynamic source population for DANDI dandisets ([@yarikoptic](https://github.com/yarikoptic))
- Add support for importing specific DANDI dandisets ([@yarikoptic](https://github.com/yarikoptic))
- Merge branch 'enh-zotero' into master ([@yarikoptic](https://github.com/yarikoptic))
- Add Zotero Related Items links between merged and published versions ([@yarikoptic](https://github.com/yarikoptic))
- Add tests for Zotero preprint vs journal article field mapping ([@yarikoptic](https://github.com/yarikoptic))
- Fix preprint field mapping in Zotero sync ([@yarikoptic](https://github.com/yarikoptic))
- Fix mypy type errors in merge_detection.py ([@yarikoptic](https://github.com/yarikoptic))
- Fix detect-merges CLI command configuration loading ([@yarikoptic](https://github.com/yarikoptic))
- Update documentation for PDF acquisition, merge detection, and Zotero sync ([@yarikoptic](https://github.com/yarikoptic))
- Handle previously-synced items transitioning to merged status ([@yarikoptic](https://github.com/yarikoptic))
- Add preprint/published version merge detection ([@yarikoptic](https://github.com/yarikoptic))
- Fix mypy type errors in CLI and Zotero sync ([@yarikoptic](https://github.com/yarikoptic))
- Dual-assign active citations to item + flavor Zotero collections ([@yarikoptic](https://github.com/yarikoptic))
- Use bare item ID for Zotero collection names, not item_name ([@yarikoptic](https://github.com/yarikoptic))
- Fix Zotero sync idempotency: recurse subcollections for existing items ([@yarikoptic](https://github.com/yarikoptic))
- Add Zotero sync, PDF acquisition, and unified YAML config ([@yarikoptic](https://github.com/yarikoptic))
- Add coverage reporting to py312 tox run ([@yarikoptic](https://github.com/yarikoptic))
- Fix CLI tests modifying simple.yaml fixture ([@yarikoptic](https://github.com/yarikoptic))
- Include datacite in default discovery sources ([@yarikoptic](https://github.com/yarikoptic))
- Stop tracking auto-generated _version.py ([@yarikoptic](https://github.com/yarikoptic))
- Fix typing issues across discovery and importer modules ([@yarikoptic](https://github.com/yarikoptic))
- rename dandi example collection ([@yarikoptic](https://github.com/yarikoptic))
- fixup and extend examples/dandi-collection.yaml ([@yarikoptic](https://github.com/yarikoptic))
- Add DANDI and Zotero importers with CLI commands ([@yarikoptic](https://github.com/yarikoptic))
- Sanitize metadata text and enhance DataCite discoverer ([@yarikoptic](https://github.com/yarikoptic))
- added one more sample dandiset for which there must be a citation ([@yarikoptic](https://github.com/yarikoptic))
- MAJOR FIX: Correct citation discovery - was backwards! ([@yarikoptic](https://github.com/yarikoptic))
- Fix API authentication and date filter bugs ([@yarikoptic](https://github.com/yarikoptic))
- Handle Zenodo API 403 errors gracefully in integration tests ([@yarikoptic](https://github.com/yarikoptic))
- Set up pre-commit with ruff and add usage documentation ([@yarikoptic](https://github.com/yarikoptic))
- Add integration tests with live external API calls ([@yarikoptic](https://github.com/yarikoptic))
- Phase 6 Part 2: Reference importers for non-DOI refs expansion ([@yarikoptic](https://github.com/yarikoptic))
- Phase 6 Part 1: Implement DataCite discoverer for DANDI citations ([@yarikoptic](https://github.com/yarikoptic))
- Phase 5: Validation & Assessment - All tox environments passing ([@yarikoptic](https://github.com/yarikoptic))
- Phase 4: Implement Click-based CLI ([@yarikoptic](https://github.com/yarikoptic))
- Phase 3: Implement core CitationCollector orchestration ([@yarikoptic](https://github.com/yarikoptic))
- Phase 2: Implement citation discovery APIs ([@yarikoptic](https://github.com/yarikoptic))
- Phase 1: Implement YAML/TSV persistence layer ([@yarikoptic](https://github.com/yarikoptic))
- Phase 0: Bootstrap project structure and build system ([@yarikoptic](https://github.com/yarikoptic))
- Add feature specification, LinkML schema, and examples ([@yarikoptic](https://github.com/yarikoptic))
- [DATALAD RUNCMD] yolo '/speckit.constitution A simple FO... ([@yarikoptic](https://github.com/yarikoptic))
- [DATALAD RUNCMD] specify init --ai claude --script sh --h... ([@yarikoptic](https://github.com/yarikoptic))
- [DATALAD] new dataset ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- GitMate for @yarikoptic ([@yarikoptic-gitmate](https://github.com/yarikoptic-gitmate))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# CHANGELOG

This changelog is automatically generated using [auto](https://github.com/intuit/auto).

## 0.2.1 (Fri Jan 30 2026)

#### 🚀 Enhancement

- Add OpenAlex as a citation discovery source - Fourth discovery source for broader citation coverage
- Add dynamic source population for DANDI dandisets - Fetch items from DANDI API automatically
- Add multi-source citation tracking with coherence validation - Track which sources found each citation
- Add tox environment for updating example citations - Automated script to update all examples

#### 🐛 Bug Fix

- Fix DataCite Event Data API query parameters - Use correct relation type and DOI format
- Fix CrossRef metadata API call handling - Account for metadata checks in tests

#### 🏠 Internal

- Remove last_updated from Collection schema - Derive 'since' date from TSV instead, clean git history
- Comment out sources in examples - Default uses all available sources, clearer documentation
- Merge enh-zotero branch - OpenAlex support and multi-source tracking
- Fix mypy type errors in DANDI and OpenAlex discoverers

#### 📝 Documentation

- Add auto-release integration plan - Comprehensive guide for CI/CD automation

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

## 0.2.0 (Wed Jan 29 2026)

Initial tagged release with:

#### 🚀 Enhancement

- Zotero sync with merge detection - Sync citations to Zotero groups with preprint/published tracking
- PDF acquisition via Unpaywall - Automated PDF download with git-annex support
- DANDI and Zotero importers - Auto-generate collections from external sources
- Citation discovery from CrossRef, OpenCitations, and DataCite

#### 🏠 Internal

- Unified YAML configuration - Single source config for all features
- Coverage reporting in tox - 78% test coverage
- Comprehensive test suite - 101 tests across Python 3.10, 3.11, 3.12

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

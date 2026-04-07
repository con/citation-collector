"""Click-based CLI for citations-collector."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from citations_collector.models import CitationRecord

import click

from citations_collector.core import CitationCollector
from citations_collector.importers.dandi import DANDIImporter
from citations_collector.importers.zotero import ZoteroImporter
from citations_collector.persistence import yaml_io

logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool) -> None:
    """Discover and curate scholarly citations of datasets and software."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


@main.command()
@click.argument("collection", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output TSV file (overrides collection YAML output_tsv)",
)
@click.option(
    "--full-refresh",
    is_flag=True,
    help="Ignore incremental mode (discover all citations)",
)
@click.option(
    "--since",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Only discover citations since this date (YYYY-MM-DD). Overrides incremental mode.",
)
@click.option(
    "--email",
    envvar="CROSSREF_EMAIL",
    help="Email for CrossRef polite pool (overrides discover.email in YAML)",
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(["crossref", "opencitations", "datacite", "openalex"]),
    help="Which sources to query (overrides discover.sources in YAML)",
)
@click.option(
    "--expand-refs",
    is_flag=True,
    help="Expand non-DOI refs (zenodo_concept, github) to DOIs before discovery",
)
def discover(
    collection: Path,
    output: Path | None,
    full_refresh: bool,
    since: datetime | None,
    email: str | None,
    sources: tuple[str, ...],
    expand_refs: bool,
) -> None:
    """Discover citations for all items in COLLECTION."""
    click.echo(f"Loading collection from {collection}")

    # Load collection
    collector = CitationCollector.from_yaml(collection)
    cfg = collector.collection

    # Populate items dynamically from source config (e.g., DANDI API)
    if cfg.source and cfg.source.type:
        click.echo(f"Populating items from {cfg.source.type} source...")
        collector.populate_from_source()

    # Resolve config: CLI overrides > YAML config > defaults
    discover_cfg = cfg.discover
    if not output:
        output = Path(cfg.output_tsv) if cfg.output_tsv else Path("citations.tsv")
    if not email and discover_cfg:
        email = discover_cfg.email
    if not sources and discover_cfg and discover_cfg.sources:
        sources = tuple(discover_cfg.sources)

    # Expand non-DOI refs if requested
    if expand_refs:
        click.echo("Expanding non-DOI references (zenodo_concept, github) to DOIs...")
        collector.expand_refs()

    # Load existing citations if TSV exists
    if output.exists():
        click.echo(f"Loading existing citations from {output}")
        collector.load_existing_citations(output)
        existing_count = len(collector.citations)
    else:
        existing_count = 0

    # Discover citations
    click.echo(f"Discovering citations for {cfg.name}...")
    if email:
        click.echo(f"Using CrossRef polite pool with email: {email}")

    sources_list = list(sources) if sources else None
    collector.discover_all(
        sources=sources_list,
        incremental=not full_refresh,
        since_date=since,
        email=email,
    )

    # Report results
    new_count = len(collector.citations) - existing_count
    click.echo(f"Found {new_count} new citations ({len(collector.citations)} total)")

    # Save results
    collector.save(collection, output)
    click.echo(f"Saved to {output}")


@main.command("import-dandi")
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output YAML file for collection",
)
@click.option(
    "--include-draft",
    is_flag=True,
    help="Include draft versions (no DOI)",
)
@click.option(
    "--limit",
    type=int,
    help="Limit number of dandisets to import (only for --all)",
)
@click.option(
    "--dandiset-id",
    "-d",
    "dandiset_ids",
    multiple=True,
    help="Import specific dandiset(s) by ID (e.g., -d 000402 -d 000003)",
)
@click.option(
    "--all",
    "import_all",
    is_flag=True,
    help="Import all dandisets (default if no --dandiset-id specified)",
)
def import_dandi(
    output: Path,
    include_draft: bool,
    limit: int | None,
    dandiset_ids: tuple[str, ...],
    import_all: bool,
) -> None:
    """Import dandisets from DANDI Archive.

    Examples:

      # Import specific dandisets
      citations-collector import-dandi -o microns.yaml -d 000402

      # Import multiple specific dandisets
      citations-collector import-dandi -o multi.yaml -d 000003 -d 000402

      # Import all dandisets (with limit)
      citations-collector import-dandi -o all.yaml --all --limit 10
    """
    importer = DANDIImporter()

    # Determine what to import
    if dandiset_ids:
        # Import specific dandisets
        click.echo(f"Importing {len(dandiset_ids)} specific dandiset(s)...")

        with click.progressbar(length=len(dandiset_ids), label="Importing") as bar:  # type: ignore[var-annotated]

            def progress(current: int, total: int | None) -> None:
                bar.update(1)

            collection = importer.import_specific(
                dandiset_ids=list(dandiset_ids),
                include_draft=include_draft,
                progress_callback=progress,
            )
    else:
        # Import all dandisets
        if not import_all:
            click.echo(
                "No --dandiset-id specified, importing all dandisets "
                "(use --all to suppress this message)"
            )
        else:
            click.echo("Importing all dandisets from DANDI Archive...")

        with click.progressbar(length=limit or 0, label="Importing") as bar:  # type: ignore[var-annotated]

            def progress(current: int, total: int | None) -> None:
                bar.update(1)

            collection = importer.import_all(
                include_draft=include_draft,
                limit=limit,
                progress_callback=progress if limit else None,
            )

    yaml_io.save_collection(collection, output)
    click.echo(f"Imported {len(collection.items or [])} dandisets to {output}")


@main.command("import-zotero")
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output YAML file for collection",
)
@click.option(
    "--group-id",
    required=True,
    type=int,
    help="Zotero group ID",
)
@click.option(
    "--collection-key",
    help="Specific collection within group",
)
@click.option(
    "--api-key",
    envvar="ZOTERO_API_KEY",
    help="Zotero API key (optional for public groups)",
)
@click.option(
    "--limit",
    type=int,
    help="Limit number of items to import",
)
def import_zotero(
    output: Path,
    group_id: int,
    collection_key: str | None,
    api_key: str | None,
    limit: int | None,
) -> None:
    """Import items from a Zotero group."""
    click.echo(f"Importing items from Zotero group {group_id}...")

    importer = ZoteroImporter(api_key=api_key)
    collection = importer.import_group(
        group_id=group_id,
        collection_key=collection_key,
        limit=limit,
    )

    yaml_io.save_collection(collection, output)
    click.echo(f"Imported {len(collection.items or [])} items to {output}")


@main.command("sync-zotero")
@click.argument("collection", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--tsv",
    type=click.Path(exists=True, path_type=Path),
    help="Citations TSV file (overrides collection YAML output_tsv)",
)
@click.option(
    "--api-key",
    envvar="ZOTERO_API_KEY",
    help="Zotero API key",
)
@click.option(
    "--group-id",
    type=int,
    help="Zotero group ID (overrides zotero.group_id in YAML)",
)
@click.option(
    "--collection-key",
    help="Zotero collection key (overrides zotero.collection_key in YAML)",
)
@click.option("--dry-run", is_flag=True, help="Show what would be synced without writing")
def sync_zotero(
    collection: Path,
    tsv: Path | None,
    api_key: str | None,
    group_id: int | None,
    collection_key: str | None,
    dry_run: bool,
) -> None:
    """Sync citations to Zotero as hierarchical collections."""
    from citations_collector.persistence import tsv_io
    from citations_collector.zotero_sync import ZoteroSyncer

    collector = CitationCollector.from_yaml(collection)
    cfg = collector.collection
    zotero_cfg = cfg.zotero

    # Resolve config
    if not tsv:
        tsv_path = Path(cfg.output_tsv) if cfg.output_tsv else Path("citations.tsv")
    else:
        tsv_path = tsv
    if not group_id and zotero_cfg:
        group_id = zotero_cfg.group_id
    if not collection_key and zotero_cfg:
        collection_key = zotero_cfg.collection_key
    if not api_key:
        raise click.UsageError("Zotero API key required (--api-key or ZOTERO_API_KEY)")
    if not group_id:
        raise click.UsageError("Zotero group ID required (--group-id or zotero.group_id in YAML)")
    if not collection_key:
        raise click.UsageError(
            "Zotero collection key required (--collection-key or zotero.collection_key in YAML)"
        )

    citations = tsv_io.load_citations(tsv_path)
    click.echo(f"Loaded {len(citations)} citations from {tsv_path}")

    syncer = ZoteroSyncer(api_key=api_key, group_id=group_id, collection_key=collection_key)
    report = syncer.sync(cfg, citations, dry_run=dry_run)

    prefix = "[DRY RUN] " if dry_run else ""
    click.echo(f"{prefix}Collections created: {report.collections_created}")
    click.echo(f"{prefix}Items created: {report.items_created}")
    click.echo(f"{prefix}Items skipped: {report.items_skipped}")
    click.echo(f"{prefix}Attachments created: {report.attachments_created}")
    if report.errors:
        click.echo(f"Errors: {len(report.errors)}")
        for err in report.errors[:10]:
            click.echo(f"  {err}")


@main.command("fetch-pdfs")
@click.argument("collection", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--tsv",
    type=click.Path(path_type=Path),
    help="Citations TSV file (overrides collection YAML output_tsv)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="PDF output directory (overrides pdfs.output_dir in YAML)",
)
@click.option(
    "--email",
    envvar="UNPAYWALL_EMAIL",
    help="Email for Unpaywall API (overrides pdfs.unpaywall_email in YAML)",
)
@click.option("--git-annex/--no-git-annex", default=None, help="Use git-annex for PDFs")
@click.option("--dry-run", is_flag=True, help="Report OA status without downloading")
def fetch_pdfs(
    collection: Path,
    tsv: Path | None,
    output_dir: Path | None,
    email: str | None,
    git_annex: bool | None,
    dry_run: bool,
) -> None:
    """Fetch open-access PDFs for citations in COLLECTION."""
    from citations_collector.pdf import PDFAcquirer
    from citations_collector.persistence import tsv_io

    collector = CitationCollector.from_yaml(collection)
    cfg = collector.collection
    pdfs_cfg = cfg.pdfs

    # Resolve config
    if not tsv:
        tsv_path = Path(cfg.output_tsv) if cfg.output_tsv else Path("citations.tsv")
    else:
        tsv_path = tsv
    if not output_dir:
        output_dir = Path((pdfs_cfg.output_dir if pdfs_cfg else None) or "pdfs/")

    # Resolve with fallbacks (ensure non-None types for PDFAcquirer)
    email_resolved: str = (
        email
        or (pdfs_cfg.unpaywall_email if pdfs_cfg else None)
        or "site-unpaywall@oneukrainian.com"
    )
    git_annex_resolved: bool = (
        git_annex
        if git_annex is not None
        else ((pdfs_cfg.git_annex if pdfs_cfg else None) or False)
    )

    citations = tsv_io.load_citations(tsv_path)
    click.echo(f"Loaded {len(citations)} citations from {tsv_path}")

    acquirer = PDFAcquirer(
        output_dir=output_dir, email=email_resolved, git_annex=git_annex_resolved
    )
    counts = acquirer.acquire_all(citations, dry_run=dry_run)

    prefix = "[DRY RUN] " if dry_run else ""
    click.echo(f"{prefix}Downloaded: {counts['downloaded']}")
    click.echo(f"{prefix}Skipped (existing): {counts['skipped']}")
    click.echo(f"{prefix}No OA available: {counts['no_oa']}")
    click.echo(f"{prefix}No DOI: {counts['no_doi']}")
    if counts["error"]:
        click.echo(f"Errors: {counts['error']}")

    if not dry_run:
        tsv_io.save_citations(citations, tsv_path)
        click.echo(f"Updated {tsv_path}")


@main.command(name="detect-merges")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to collection YAML config",
)
@click.option(
    "--tsv",
    type=click.Path(exists=True, path_type=Path),
    help="Override: path to TSV file (default: from config)",
)
@click.option(
    "--email",
    help="Email for CrossRef API (default: from config or fallback)",
)
@click.option(
    "--fuzzy-match",
    is_flag=True,
    help="Also perform fuzzy title matching (heuristic, use with caution)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be marked without saving",
)
def detect_merges(
    config: Path | None,
    tsv: Path | None,
    email: str | None,
    fuzzy_match: bool,
    dry_run: bool,
) -> None:
    """Detect and mark preprints that have published versions.

    Uses CrossRef API to find "is-preprint-of" relationships and marks
    preprints as merged with citation_status=merged.
    """
    from citations_collector.core import CitationCollector
    from citations_collector.merge_detection import MergeDetector
    from citations_collector.persistence import tsv_io

    # Load config if provided
    pdfs_cfg = None
    if config:
        collector = CitationCollector.from_yaml(config)
        cfg = collector.collection
        pdfs_cfg = cfg.pdfs
        if not tsv:
            tsv_path = Path(cfg.output_tsv) if cfg.output_tsv else Path("citations.tsv")
        else:
            tsv_path = tsv
    elif tsv:
        tsv_path = tsv
    else:
        raise click.UsageError("Must provide either --config or --tsv")

    # Resolve email
    email_resolved: str = (
        email
        or (pdfs_cfg.unpaywall_email if pdfs_cfg else None)
        or "site-unpaywall@oneukrainian.com"
    )

    citations = tsv_io.load_citations(tsv_path)
    click.echo(f"Loaded {len(citations)} citations from {tsv_path}")

    detector = MergeDetector(email=email_resolved)

    # Detect merges via CrossRef relationships
    merged_pairs = detector.detect_merged_pairs(citations)
    click.echo(f"Found {len(merged_pairs)} merged pairs via CrossRef API")

    # Optionally add fuzzy matching
    if fuzzy_match:
        click.echo("Running fuzzy title matching...")
        fuzzy_pairs = detector.fuzzy_match_by_title(citations)
        click.echo(f"Found {len(fuzzy_pairs)} potential pairs via fuzzy matching")

        # Show fuzzy matches for manual review
        if fuzzy_pairs:
            click.echo("\nFuzzy matches (review before accepting):")
            for preprint_doi, pub_doi in fuzzy_pairs.items():
                click.echo(f"  {preprint_doi} -> {pub_doi}")

        # Don't auto-merge fuzzy matches - require manual review
        click.echo(
            "\nFuzzy matches not applied automatically. "
            "Review and add to CrossRef metadata if valid."
        )

    # Mark merged citations
    if merged_pairs:
        prefix = "[DRY RUN] " if dry_run else ""
        marked = detector.mark_merged_citations(citations, merged_pairs)
        click.echo(f"{prefix}Marked {marked} citations as merged")

        if not dry_run:
            tsv_io.save_citations(citations, tsv_path)
            click.echo(f"Updated {tsv_path}")
    else:
        click.echo("No merges detected")


@main.command()
@click.argument("collection", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Directory containing PDFs (overrides pdfs.output_dir in YAML)",
)
@click.option(
    "--git-annex/--no-git-annex",
    default=None,
    help="Add extracted_citations.json to git-annex with metadata",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Re-extract even if extracted_citations.json exists",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be extracted without creating files",
)
def extract_contexts(
    collection: Path,
    output_dir: Path | None,
    git_annex: bool | None,
    overwrite: bool,
    dry_run: bool,
) -> None:
    """Extract citation contexts from PDFs/HTMLs for classification.

    Finds dataset mentions in PDFs and HTMLs, extracts paragraph-level
    contexts around mentions, and saves as extracted_citations.json
    alongside each paper.

    If --git-annex is enabled, files are added to git-annex with
    oa_status metadata tags based on the citation's open access status.
    """
    from citations_collector.context_extractor import ContextExtractor
    from citations_collector.git_annex import GitAnnexHelper
    from citations_collector.persistence import tsv_io

    click.echo(f"Loading collection from {collection}")

    # Load collection
    coll = yaml_io.load_collection(collection)

    # Resolve output_dir
    if not output_dir:
        if coll.pdfs and coll.pdfs.output_dir:
            output_dir = Path(coll.pdfs.output_dir)
        else:
            output_dir = Path("pdfs")

    # Resolve git-annex setting
    if git_annex is None:
        git_annex = (
            coll.pdfs.git_annex if (coll.pdfs and coll.pdfs.git_annex is not None) else False
        )

    # Load citations TSV
    tsv_path = Path(coll.output_tsv) if coll.output_tsv else Path("citations.tsv")
    if not tsv_path.exists():
        click.echo(f"Error: Citations TSV not found: {tsv_path}", err=True)
        click.echo("Run 'citations-collector discover' first", err=True)
        raise click.Abort()

    citations = tsv_io.load_citations(tsv_path)

    # Group citations by DOI
    papers: dict[str, list[str]] = {}
    paper_metadata: dict[str, dict] = {}

    for citation in citations:
        if citation.citation_doi:
            doi = citation.citation_doi

            if doi not in papers:
                papers[doi] = []
                paper_metadata[doi] = {
                    "title": citation.citation_title,
                    "journal": citation.citation_journal,
                    "year": citation.citation_year,
                    "oa_status": citation.oa_status,
                    "pdf_url": citation.pdf_url,
                }

            papers[doi].append(citation.item_id)

    click.echo(f"Found {len(papers)} papers citing {len(citations)} datasets")
    click.echo(f"Output directory: {output_dir}")

    # Check git-annex
    if git_annex and not dry_run and not GitAnnexHelper.is_git_annex_repo():
        click.echo(
            "Warning: git-annex requested but not initialized in this repo",
            err=True,
        )
        git_annex = False

    # Extract contexts
    extractor = ContextExtractor()

    extracted_count = 0
    skipped_count = 0
    error_count = 0

    for doi, dataset_ids in papers.items():
        # Normalize DOI to path (preserve slashes)
        doi_path = output_dir / doi
        json_path = doi_path / "extracted_citations.json"

        # Check if already extracted
        if json_path.exists() and not overwrite:
            click.echo(f"⊘ {doi} (already extracted)")
            skipped_count += 1
            continue

        # Find PDF or HTML
        pdf_path = doi_path / "article.pdf"
        html_path = doi_path / "article.html"

        if not pdf_path.exists() and not html_path.exists():
            click.echo(f"✗ {doi} (no PDF/HTML found)")
            error_count += 1
            continue

        if dry_run:
            click.echo(f"[DRY RUN] Would extract: {doi}")
            click.echo(f"  Datasets: {', '.join(dataset_ids)}")
            click.echo(f"  Source: {'PDF' if pdf_path.exists() else 'HTML'}")
            extracted_count += 1
            continue

        # Extract
        try:
            if pdf_path.exists():
                extracted = extractor.extract_from_pdf(pdf_path, dataset_ids)
            else:
                extracted = extractor.extract_from_html(html_path, dataset_ids)

            # Add metadata from citation record
            metadata = paper_metadata[doi]
            extracted["paper_doi"] = doi
            extracted["paper_title"] = metadata["title"]
            extracted["paper_journal"] = metadata["journal"]
            extracted["paper_year"] = metadata["year"]
            extracted["oa_status"] = metadata["oa_status"]

            # Save
            extractor.save_extracted_citations(extracted, json_path)

            # Git-annex
            if git_annex:
                oa_status = metadata["oa_status"] or "closed"
                GitAnnexHelper.add_with_metadata(
                    json_path,
                    oa_status=oa_status,
                    url=metadata["pdf_url"],
                )

            # Report
            mention_count = sum(len(c["dataset_mentions"]) for c in extracted["citations"])
            click.echo(
                f"✓ {doi} ({len(extracted['citations'])} datasets, {mention_count} mentions)"
            )
            extracted_count += 1

        except Exception as e:
            click.echo(f"✗ {doi}: {e}", err=True)
            error_count += 1

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo(f"Extracted: {extracted_count}")
    click.echo(f"Skipped: {skipped_count}")
    click.echo(f"Errors: {error_count}")

    if git_annex and extracted_count > 0 and not dry_run:
        click.echo(f"\n✓ Added {extracted_count} files to git-annex with metadata")


@main.command()
@click.argument("collection", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--backend",
    type=click.Choice(["ollama", "dartmouth", "openrouter", "openai"]),
    default="ollama",
    help="LLM backend to use for classification",
)
@click.option(
    "--model",
    type=str,
    help="Model name (backend-specific, e.g., qwen2:7b for Ollama)",
)
@click.option(
    "--confidence-threshold",
    type=float,
    default=0.7,
    help="Minimum confidence to accept classification (0.0-1.0)",
)
@click.option(
    "--review",
    is_flag=True,
    help="Enable interactive review mode for low-confidence classifications",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="Directory containing extracted_citations.json files",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be classified without updating TSV",
)
@click.option(
    "--full-text",
    is_flag=True,
    help="Use full paper text instead of extracted contexts (experimental)",
)
def classify(
    collection: Path,
    backend: str,
    model: str | None,
    confidence_threshold: float,
    review: bool,
    output_dir: Path | None,
    dry_run: bool,
    full_text: bool,
) -> None:
    """Classify citation relationships using LLM.

    Reads extracted_citations.json files created by extract-contexts,
    sends contexts to LLM for classification, and updates the citations
    TSV with relationship types and confidence scores.

    Full classification details (reasoning, timestamp, mode) are saved to
    pdfs/{doi}/classifications.json for each paper.

    Requires extracted_citations.json files created by extract-contexts.
    """

    from citations_collector.classifications_storage import ClassificationsStorage
    from citations_collector.classifier import CitationClassifier
    from citations_collector.models import ClassificationMethod
    from citations_collector.persistence import tsv_io

    click.echo(f"Loading collection from {collection}")

    # Load collection
    coll = yaml_io.load_collection(collection)

    # Resolve output_dir
    if not output_dir:
        if coll.pdfs and coll.pdfs.output_dir:
            output_dir = Path(coll.pdfs.output_dir)
        else:
            output_dir = Path("pdfs")

    # Load citations TSV
    tsv_path = Path(coll.output_tsv) if coll.output_tsv else Path("citations.tsv")
    if not tsv_path.exists():
        click.echo(f"Error: Citations TSV not found: {tsv_path}", err=True)
        click.echo("Run 'citations-collector discover' first", err=True)
        raise click.Abort()

    citations = tsv_io.load_citations(tsv_path)

    # Build citation lookup by (doi, item_id)
    citation_lookup = {(c.citation_doi, c.item_id): c for c in citations if c.citation_doi}

    click.echo(f"Loaded {len(citations)} citations from {tsv_path}")
    click.echo(f"Using {backend} backend for classification")
    if model:
        click.echo(f"Model: {model}")

    # Create classifier
    try:
        classifier = CitationClassifier.from_config(
            backend_type=backend,
            model=model,
            confidence_threshold=confidence_threshold,
        )
    except Exception as e:
        click.echo(f"Error creating classifier: {e}", err=True)
        click.echo("\nTroubleshooting:", err=True)
        if backend == "ollama":
            click.echo("  - Check Ollama is running (or SSH tunnel active)", err=True)
            click.echo("  - Test with: curl http://localhost:11434/api/tags", err=True)
        elif backend == "dartmouth":
            click.echo(
                "  - Check DARTMOUTH_API_TOKEN is set in environment or secrets",
                err=True,
            )
        raise click.Abort() from e

    click.echo(f"Confidence threshold: {confidence_threshold:.2f}")
    click.echo(f"Output directory: {output_dir}")

    # Determine mode and model identifier
    classification_mode = "full_text" if full_text else "short_context"
    # Get model identifier from classifier
    if hasattr(classifier.backend, "model"):
        model_id = classifier.backend.model
    else:
        model_id = model or "unknown"

    click.echo(f"Model: {model_id}")
    if full_text:
        click.echo("Mode: Full text classification (experimental)\n")
    else:
        click.echo("Mode: Extracted contexts\n")

    # Create classifications storage
    storage = ClassificationsStorage(output_dir)

    # Find papers to classify
    papers_to_classify = []
    if full_text:
        # Full text mode: find PDF/HTML files
        for doi in {c.citation_doi for c in citations if c.citation_doi}:
            doi_path = output_dir / doi
            pdf_path = doi_path / "article.pdf"
            html_path = doi_path / "article.html"

            if pdf_path.exists():
                papers_to_classify.append((doi, pdf_path, "pdf"))
            elif html_path.exists():
                papers_to_classify.append((doi, html_path, "html"))
    else:
        # Extracted contexts mode: find extracted_citations.json
        for doi in {c.citation_doi for c in citations if c.citation_doi}:
            doi_path = output_dir / doi
            json_path = doi_path / "extracted_citations.json"

            if json_path.exists():
                papers_to_classify.append((doi, json_path, "json"))

    if not papers_to_classify:
        if full_text:
            click.echo(
                "No PDF/HTML files found. Run 'citations-collector fetch-pdfs' first.",
                err=True,
            )
        else:
            click.echo(
                "No extracted_citations.json files found. "
                "Run 'citations-collector extract-contexts' first.",
                err=True,
            )
        raise click.Abort()

    click.echo(f"Found {len(papers_to_classify)} papers to classify\n")

    # Classify
    classified_count = 0
    low_confidence_count = 0
    error_count = 0
    updates: list[tuple[str, str, str, Any, bool]] = []

    for item in papers_to_classify:
        if full_text:
            doi, file_path, file_type = item
        else:
            doi, file_path, _ = item

        click.echo(f"Classifying: {doi}")

        try:
            if full_text:
                # Full text mode: get dataset IDs for this DOI
                datasets_for_doi = [c.item_id for c in citations if c.citation_doi == doi]

                # Get paper metadata
                paper_metadata = {
                    "title": next(
                        (c.citation_title for c in citations if c.citation_doi == doi),
                        "Unknown",
                    ),
                    "journal": next(
                        (c.citation_journal for c in citations if c.citation_doi == doi),
                        None,
                    ),
                    "year": next(
                        (c.citation_year for c in citations if c.citation_doi == doi),
                        None,
                    ),
                    "doi": doi,
                }

                results = classifier.classify_from_full_text(
                    file_path, datasets_for_doi, paper_metadata
                )
            else:
                # Extracted contexts mode
                results = classifier.classify_from_extracted_file(file_path)

            for dataset_id, result in results:
                # Look up citation record
                citation = citation_lookup.get((doi, dataset_id))
                if not citation:
                    click.echo(
                        f"  Warning: No citation record for {dataset_id}",
                        err=True,
                    )
                    continue

                # Check if needs review
                needs_review = classifier.should_review(result)
                confidence_marker = "⚠" if needs_review else "✓"

                click.echo(
                    f"  {confidence_marker} {dataset_id}: "
                    f"{result.relationship_type} "
                    f"(confidence: {result.confidence:.2f})"
                )

                # Track if this was reviewed/edited by human
                was_reviewed = False

                if needs_review:
                    low_confidence_count += 1
                    click.echo(f"    Reasoning: {result.reasoning}")

                    if review and not dry_run:
                        # Interactive review
                        click.echo("\n    Context:")
                        for i, ctx in enumerate(result.context_used[:2], 1):
                            click.echo(f"      [{i}] {ctx[:200]}...")

                        click.echo(
                            f"\n    Suggested: {result.relationship_type} ({result.confidence:.2f})"
                        )
                        response = click.prompt(
                            "    Accept/Edit/Skip? (a/e/s)",
                            type=str,
                            default="a",
                        )

                        if response.lower() == "s":
                            click.echo("    Skipped")
                            continue
                        elif response.lower() == "e":
                            new_type = click.prompt(
                                "    Enter relationship type",
                                type=str,
                                default=result.relationship_type,
                            )
                            result.relationship_type = new_type
                            result.confidence = 1.0  # Manual override
                            was_reviewed = True  # Human edited
                        elif response.lower() == "a":
                            was_reviewed = True  # Human reviewed and accepted

                # Store update (include item_flavor for unique identification)
                updates.append(
                    (
                        doi,
                        dataset_id,
                        citation.item_flavor,  # Need this for classifications.json
                        result,
                        was_reviewed,
                    )
                )

                classified_count += 1

        except Exception as e:
            click.echo(f"  ✗ Error: {e}", err=True)
            error_count += 1

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo(f"Classified: {classified_count}")
    click.echo(f"Low confidence: {low_confidence_count}")
    click.echo(f"Errors: {error_count}")

    if dry_run:
        click.echo("\n[DRY RUN] TSV not updated")
        return

    # Update TSV and save detailed results
    if updates:
        click.echo("\nSaving detailed results to classifications.json files...")
        click.echo(f"Updating {tsv_path}...")

        # Update citation records
        from citations_collector.models.generated import CitationRelationship

        updated_citations: list[tuple[str, str, CitationRecord]] = []
        for doi, item_id, item_flavor, result, was_reviewed in updates:
            citation = citation_lookup.get((doi, item_id))
            if citation:
                # Update relationship (use enum value)
                try:
                    rel_enum = CitationRelationship(result.relationship_type)

                    # Save detailed result to classifications.json
                    if not dry_run:
                        storage.add_classification(
                            doi=doi,
                            item_id=item_id,
                            item_flavor=item_flavor,
                            result=result,
                            model=model_id,
                            backend=backend,
                            mode=classification_mode,
                        )

                    # Update citation with classification metadata
                    updated = citation.model_copy(
                        update={
                            "citation_relationship": rel_enum,
                            "citation_relationships": [rel_enum],
                            "classification_method": ClassificationMethod.llm,
                            "classification_model": model_id,
                            "classification_confidence": result.confidence,
                            "classification_reviewed": was_reviewed,
                        }
                    )
                    updated_citations.append((doi, item_id, updated))

                except (ValueError, Exception) as e:
                    click.echo(
                        f"Warning: Failed to update relationship '{result.relationship_type}' "
                        f"for {item_id}: {e}",
                        err=True,
                    )
                    continue

        # Replace updated citations in the list
        for doi, item_id, updated_citation in updated_citations:
            citation = citation_lookup.get((doi, item_id))
            if citation:
                # Replace in citations list
                idx = citations.index(citation)
                citations[idx] = updated_citation

        # Save TSV
        tsv_io.save_citations(citations, tsv_path)
        click.echo(f"✓ Saved detailed results for {len(updates)} citations")
        click.echo(f"✓ Updated {len(updates)} citations in {tsv_path}")


if __name__ == "__main__":
    main()

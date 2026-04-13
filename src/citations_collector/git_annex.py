"""Git-annex integration for managing extracted citations with metadata."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitAnnexHelper:
    """Helper for git-annex operations."""

    @staticmethod
    def is_git_annex_repo(path: Path | None = None) -> bool:
        """Check if current directory is a git-annex repository.

        Args:
            path: Path to check (defaults to current directory)

        Returns:
            True if git-annex initialized
        """
        if path is None:
            path = Path.cwd()
        try:
            result = subprocess.run(
                ["git", "annex", "version"],
                cwd=path,
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    @staticmethod
    def add_with_metadata(
        file_path: Path,
        oa_status: str,
        url: str | None = None,
        dry_run: bool = False,
    ) -> bool:
        """Add file to git-annex with metadata tags.

        Args:
            file_path: Path to file (extracted_citations.json)
            oa_status: Open access status (gold/green/hybrid/closed)
            url: Original PDF URL for provenance
            dry_run: If True, only log what would be done

        Returns:
            True if successful
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        # Validate OA status
        valid_statuses = ["gold", "green", "hybrid", "closed"]
        if oa_status not in valid_statuses:
            logger.warning(f"Invalid oa_status '{oa_status}', must be one of: {valid_statuses}")
            oa_status = "closed"

        if dry_run:
            logger.info(f"[DRY RUN] Would add to git-annex: {file_path}")
            logger.info(f"[DRY RUN]   oa_status={oa_status}")
            if url:
                logger.info(f"[DRY RUN]   url={url}")
            if oa_status == "closed":
                logger.info("[DRY RUN]   tag: distribution-restricted")
            return True

        try:
            # Add file to git-annex
            logger.info(f"Adding to git-annex: {file_path}")
            result = subprocess.run(
                ["git", "annex", "add", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(f"git annex add failed: {result.stderr}")
                return False

            # Add metadata: oa_status
            logger.info(f"Setting metadata: oa_status={oa_status}")
            result = subprocess.run(
                [
                    "git",
                    "annex",
                    "metadata",
                    str(file_path),
                    "-s",
                    f"oa_status={oa_status}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.warning(f"Failed to set oa_status metadata: {result.stderr}")

            # Add distribution-restricted tag for closed access
            if oa_status == "closed":
                logger.info("Adding distribution-restricted tag")
                result = subprocess.run(
                    [
                        "git",
                        "annex",
                        "metadata",
                        str(file_path),
                        "-t",
                        "distribution-restricted",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.warning(f"Failed to add tag: {result.stderr}")

            # Add URL metadata for open access
            if url and oa_status in ["gold", "green", "hybrid"]:
                logger.info(f"Setting URL metadata: {url}")
                result = subprocess.run(
                    [
                        "git",
                        "annex",
                        "metadata",
                        str(file_path),
                        "-s",
                        f"url={url}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.warning(f"Failed to set URL metadata: {result.stderr}")

            return True

        except subprocess.TimeoutExpired:
            logger.error(f"git-annex operation timed out for {file_path}")
            return False
        except FileNotFoundError:
            logger.error("git-annex not found. Is it installed?")
            return False
        except Exception as e:
            logger.error(f"git-annex operation failed: {e}")
            return False

    @staticmethod
    def get_metadata(file_path: Path) -> dict[str, list[str]]:
        """Get git-annex metadata for a file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary of metadata fields to values
        """
        try:
            result = subprocess.run(
                ["git", "annex", "metadata", "--json", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                import json

                data = json.loads(result.stdout)
                return dict(data.get("fields", {}))

            return {}

        except Exception as e:
            logger.warning(f"Failed to get metadata: {e}")
            return {}

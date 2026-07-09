"""Tests for CLI commands."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import responses
from click.testing import CliRunner

from citations_collector.cli import main


def _copy_fixture(collections_dir: Path, tmp_path: Path) -> Path:
    """Copy simple.yaml fixture to tmp_path so tests don't modify the original."""
    src = collections_dir / "simple.yaml"
    dst = tmp_path / "simple.yaml"
    shutil.copy2(src, dst)
    return dst


@pytest.mark.ai_generated
@responses.activate
def test_discover_command(collections_dir: Path, tmp_path: Path) -> None:
    """Test discover command."""
    collection_file = _copy_fixture(collections_dir, tmp_path)

    # Mock CrossRef data-citations API
    responses.add(
        responses.GET,
        "https://api.crossref.org/beta/datacitations",
        json={
            "message": {
                "total-results": 0,
                "items-per-page": 1000,
                "next-page": None,
                "items": [],
            }
        },
        status=200,
    )
    # Mock DataCite Events API
    responses.add(
        responses.GET,
        "https://api.datacite.org/events",
        json={"data": []},
        status=200,
    )

    runner = CliRunner()
    output_file = tmp_path / "test.tsv"

    result = runner.invoke(
        main,
        [
            "discover",
            str(collection_file),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert "Discovering citations" in result.output
    assert output_file.exists()


@pytest.mark.ai_generated
@responses.activate
def test_discover_full_refresh_flag(collections_dir: Path, tmp_path: Path) -> None:
    """Test discover with --full-refresh flag."""
    collection_file = _copy_fixture(collections_dir, tmp_path)

    # Mock CrossRef data-citations API
    responses.add(
        responses.GET,
        "https://api.crossref.org/beta/datacitations",
        json={
            "message": {
                "total-results": 0,
                "items-per-page": 1000,
                "next-page": None,
                "items": [],
            }
        },
        status=200,
    )
    # Mock DataCite Events API
    responses.add(
        responses.GET,
        "https://api.datacite.org/events",
        json={"data": []},
        status=200,
    )

    runner = CliRunner()
    output_file = tmp_path / "test.tsv"

    result = runner.invoke(
        main,
        [
            "discover",
            str(collection_file),
            "--output",
            str(output_file),
            "--full-refresh",
        ],
    )

    assert result.exit_code == 0
    assert "Discovering citations" in result.output


@pytest.mark.ai_generated
def test_discover_email_env_var(
    collections_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test discover respects CROSSREF_EMAIL environment variable."""
    collection_file = _copy_fixture(collections_dir, tmp_path)
    monkeypatch.setenv("CROSSREF_EMAIL", "test@example.org")

    runner = CliRunner()
    output_file = tmp_path / "test.tsv"

    # Mock to avoid actual API call
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://api.crossref.org/beta/datacitations",
            json={
                "message": {
                    "total-results": 0,
                    "items-per-page": 1000,
                    "next-page": None,
                    "items": [],
                }
            },
            status=200,
        )
        rsps.add(
            responses.GET,
            "https://api.datacite.org/events",
            json={"data": []},
            status=200,
        )

        result = runner.invoke(
            main,
            [
                "discover",
                str(collection_file),
                "--output",
                str(output_file),
            ],
        )

    assert result.exit_code == 0
    assert "polite pool" in result.output


@pytest.mark.ai_generated
def test_sync_zotero_requires_config(collections_dir: Path) -> None:
    """Test sync-zotero requires group-id and collection-key."""
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "sync-zotero",
            str(collections_dir / "simple.yaml"),
            "--api-key",
            "test-key",
        ],
    )

    # Should fail: simple.yaml has no zotero config and no --group-id
    assert result.exit_code != 0

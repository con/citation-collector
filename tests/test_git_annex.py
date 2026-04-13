"""Tests for citations_collector.git_annex module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from citations_collector.git_annex import GitAnnexHelper


@pytest.mark.ai_generated
class TestIsGitAnnexRepo:
    """Test GitAnnexHelper.is_git_annex_repo."""

    @patch("citations_collector.git_annex.subprocess.run")
    def test_returns_true_when_annex_available(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0)
        assert GitAnnexHelper.is_git_annex_repo(Path("/some/repo")) is True
        mock_run.assert_called_once_with(
            ["git", "annex", "version"],
            cwd=Path("/some/repo"),
            capture_output=True,
            timeout=5,
        )

    @patch("citations_collector.git_annex.subprocess.run")
    def test_returns_false_on_nonzero_exit(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=128)
        assert GitAnnexHelper.is_git_annex_repo(Path("/not/annex")) is False

    @patch("citations_collector.git_annex.subprocess.run")
    def test_returns_false_on_file_not_found(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("git not found")
        assert GitAnnexHelper.is_git_annex_repo(Path("/no/git")) is False

    @patch("citations_collector.git_annex.subprocess.run")
    def test_returns_false_on_subprocess_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.SubprocessError("timeout")
        assert GitAnnexHelper.is_git_annex_repo(Path("/timeout")) is False

    @patch("citations_collector.git_annex.subprocess.run")
    @patch("citations_collector.git_annex.Path")
    def test_defaults_to_cwd(self, mock_path_cls: MagicMock, mock_run: MagicMock) -> None:
        """When path is None, uses Path.cwd()."""
        mock_cwd = Path("/fake/cwd")
        mock_path_cls.cwd.return_value = mock_cwd
        mock_run.return_value = MagicMock(returncode=0)

        GitAnnexHelper.is_git_annex_repo(None)

        mock_run.assert_called_once_with(
            ["git", "annex", "version"],
            cwd=mock_cwd,
            capture_output=True,
            timeout=5,
        )


@pytest.mark.ai_generated
class TestAddWithMetadata:
    """Test GitAnnexHelper.add_with_metadata."""

    def test_dry_run_does_not_run_subprocess(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        result = GitAnnexHelper.add_with_metadata(
            file_path=test_file,
            oa_status="gold",
            url="https://example.com/paper.pdf",
            dry_run=True,
        )
        assert result is True

    def test_nonexistent_file_returns_false(self, tmp_path: Path) -> None:
        result = GitAnnexHelper.add_with_metadata(
            file_path=tmp_path / "missing.json",
            oa_status="gold",
        )
        assert result is False

    def test_invalid_oa_status_defaults_to_closed(self, tmp_path: Path) -> None:
        """Invalid oa_status falls back to 'closed' and adds restricted tag."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        # dry_run so we don't need real git-annex
        result = GitAnnexHelper.add_with_metadata(
            file_path=test_file,
            oa_status="invalid_status",
            dry_run=True,
        )
        assert result is True

    @patch("citations_collector.git_annex.subprocess.run")
    def test_add_with_gold_status(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Successful add for gold OA includes URL metadata."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = GitAnnexHelper.add_with_metadata(
            file_path=test_file,
            oa_status="gold",
            url="https://example.com/paper.pdf",
        )

        assert result is True
        # Should call: git annex add, git annex metadata -s oa_status=gold,
        # git annex metadata -s url=...
        assert mock_run.call_count == 3

    @patch("citations_collector.git_annex.subprocess.run")
    def test_add_with_closed_status_adds_restricted_tag(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = GitAnnexHelper.add_with_metadata(
            file_path=test_file,
            oa_status="closed",
        )

        assert result is True
        # Should call: git annex add, metadata -s oa_status=closed, metadata -t restricted
        assert mock_run.call_count == 3

    @patch("citations_collector.git_annex.subprocess.run")
    def test_add_failure_returns_false(self, mock_run: MagicMock, tmp_path: Path) -> None:
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")
        mock_run.return_value = MagicMock(returncode=1, stderr="error")

        result = GitAnnexHelper.add_with_metadata(
            file_path=test_file,
            oa_status="gold",
        )
        assert result is False

    @patch("citations_collector.git_annex.subprocess.run")
    def test_timeout_returns_false(self, mock_run: MagicMock, tmp_path: Path) -> None:
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=30)

        result = GitAnnexHelper.add_with_metadata(
            file_path=test_file,
            oa_status="gold",
        )
        assert result is False

    @patch("citations_collector.git_annex.subprocess.run")
    def test_git_not_found_returns_false(self, mock_run: MagicMock, tmp_path: Path) -> None:
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")
        mock_run.side_effect = FileNotFoundError("git not found")

        result = GitAnnexHelper.add_with_metadata(
            file_path=test_file,
            oa_status="gold",
        )
        assert result is False


@pytest.mark.ai_generated
class TestGetMetadata:
    """Test GitAnnexHelper.get_metadata."""

    @patch("citations_collector.git_annex.subprocess.run")
    def test_returns_metadata_fields(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"fields": {"oa_status": ["gold"], "url": ["https://example.com"]}}',
        )

        result = GitAnnexHelper.get_metadata(tmp_path / "test.json")
        assert result == {"oa_status": ["gold"], "url": ["https://example.com"]}

    @patch("citations_collector.git_annex.subprocess.run")
    def test_returns_empty_on_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = GitAnnexHelper.get_metadata(tmp_path / "test.json")
        assert result == {}

    @patch("citations_collector.git_annex.subprocess.run")
    def test_returns_empty_on_exception(self, mock_run: MagicMock, tmp_path: Path) -> None:
        mock_run.side_effect = Exception("boom")
        result = GitAnnexHelper.get_metadata(tmp_path / "test.json")
        assert result == {}

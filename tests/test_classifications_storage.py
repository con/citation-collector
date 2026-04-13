"""Tests for citations_collector.classifications_storage module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citations_collector.classifications_storage import (
    ClassificationsStorage,
    StoredClassification,
)
from citations_collector.llm.base import ClassificationResult


@pytest.mark.ai_generated
class TestStoredClassification:
    """Test StoredClassification dataclass serialization."""

    def _sample(self) -> StoredClassification:
        return StoredClassification(
            item_id="dandi.000003",
            item_flavor="0.210913.1639",
            model="gpt-4",
            backend="openai",
            relationship_type="Uses",
            confidence=0.9,
            reasoning="Paper uses the dataset",
            timestamp="2024-01-01T00:00:00",
            mode="short_context",
        )

    def test_to_dict(self) -> None:
        sc = self._sample()
        d = sc.to_dict()
        assert d["item_id"] == "dandi.000003"
        assert d["confidence"] == 0.9
        assert d["mode"] == "short_context"

    def test_from_dict_round_trip(self) -> None:
        sc = self._sample()
        d = sc.to_dict()
        sc2 = StoredClassification.from_dict(d)
        assert sc == sc2


@pytest.mark.ai_generated
class TestClassificationsStorageInit:
    """Test ClassificationsStorage path helpers."""

    def test_get_paper_dir(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        assert storage.get_paper_dir("10.1234/test") == tmp_path / "10.1234/test"

    def test_get_classifications_file(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        assert (
            storage.get_classifications_file("10.1234/test")
            == tmp_path / "10.1234/test" / "classifications.json"
        )


@pytest.mark.ai_generated
class TestClassificationsStorageLoadSave:
    """Test load/save operations."""

    def test_load_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        result = storage.load_classifications("10.1234/missing")
        assert result == []

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        doi = "10.1234/test"

        sc = StoredClassification(
            item_id="dandi.000003",
            item_flavor="0.1",
            model="gpt-4",
            backend="openai",
            relationship_type="Uses",
            confidence=0.85,
            reasoning="The paper uses the dataset",
            timestamp="2024-06-01T12:00:00",
            mode="short_context",
        )

        storage.save_classifications(doi, [sc])
        loaded = storage.load_classifications(doi)

        assert len(loaded) == 1
        assert loaded[0].item_id == "dandi.000003"
        assert loaded[0].confidence == 0.85

    def test_save_creates_directories(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        doi = "10.9999/deeply/nested"
        storage.save_classifications(doi, [])

        assert (tmp_path / doi / "classifications.json").exists()

    def test_json_format_is_list_of_dicts(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        doi = "10.1234/fmt"

        sc = StoredClassification(
            item_id="dandi.000020",
            item_flavor="1.0",
            model="gemma",
            backend="dartmouth",
            relationship_type="Cites",
            confidence=0.5,
            reasoning="Generic citation",
            timestamp="2024-01-01T00:00:00",
            mode="full_text",
        )
        storage.save_classifications(doi, [sc])

        raw = json.loads((tmp_path / doi / "classifications.json").read_text())
        assert isinstance(raw, list)
        assert len(raw) == 1
        assert raw[0]["item_id"] == "dandi.000020"


@pytest.mark.ai_generated
class TestClassificationsStorageAddAndGet:
    """Test add_classification, get_classification, and helpers."""

    def _make_result(self, rtype: str = "Uses", confidence: float = 0.9) -> ClassificationResult:
        return ClassificationResult(
            relationship_type=rtype,
            confidence=confidence,
            reasoning="test reasoning",
            context_used=["ctx"],
        )

    def test_add_classification(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        doi = "10.1234/add"

        storage.add_classification(
            doi=doi,
            item_id="dandi.000003",
            item_flavor="0.1",
            result=self._make_result(),
            model="gpt-4",
            backend="openai",
        )

        loaded = storage.load_classifications(doi)
        assert len(loaded) == 1
        assert loaded[0].relationship_type == "Uses"

    def test_add_classification_replaces_same_key(self, tmp_path: Path) -> None:
        """Adding for same (item_id, item_flavor, model) replaces old entry."""
        storage = ClassificationsStorage(tmp_path)
        doi = "10.1234/replace"

        storage.add_classification(
            doi=doi,
            item_id="dandi.000003",
            item_flavor="0.1",
            result=self._make_result("Uses", 0.7),
            model="gpt-4",
            backend="openai",
        )
        storage.add_classification(
            doi=doi,
            item_id="dandi.000003",
            item_flavor="0.1",
            result=self._make_result("Reviews", 0.95),
            model="gpt-4",
            backend="openai",
        )

        loaded = storage.load_classifications(doi)
        assert len(loaded) == 1
        assert loaded[0].relationship_type == "Reviews"
        assert loaded[0].confidence == 0.95

    def test_add_classification_different_models_coexist(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        doi = "10.1234/multi"

        storage.add_classification(
            doi=doi,
            item_id="dandi.000003",
            item_flavor="0.1",
            result=self._make_result("Uses"),
            model="gpt-4",
            backend="openai",
        )
        storage.add_classification(
            doi=doi,
            item_id="dandi.000003",
            item_flavor="0.1",
            result=self._make_result("Reviews"),
            model="gemma",
            backend="dartmouth",
        )

        loaded = storage.load_classifications(doi)
        assert len(loaded) == 2

    def test_get_classification_found(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        doi = "10.1234/get"

        storage.add_classification(
            doi=doi,
            item_id="dandi.000003",
            item_flavor="0.1",
            result=self._make_result(),
            model="gpt-4",
            backend="openai",
        )

        c = storage.get_classification(doi, "dandi.000003", "0.1", "gpt-4")
        assert c is not None
        assert c.relationship_type == "Uses"

    def test_get_classification_not_found(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        assert storage.get_classification("10.1234/x", "a", "b", "c") is None

    def test_has_classification(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        doi = "10.1234/has"

        assert storage.has_classification(doi, "dandi.000003", "0.1", "gpt-4") is False

        storage.add_classification(
            doi=doi,
            item_id="dandi.000003",
            item_flavor="0.1",
            result=self._make_result(),
            model="gpt-4",
            backend="openai",
        )
        assert storage.has_classification(doi, "dandi.000003", "0.1", "gpt-4") is True

    def test_get_classifications_for_item(self, tmp_path: Path) -> None:
        storage = ClassificationsStorage(tmp_path)
        doi = "10.1234/foritem"

        storage.add_classification(
            doi=doi,
            item_id="dandi.000003",
            item_flavor="0.1",
            result=self._make_result("Uses"),
            model="gpt-4",
            backend="openai",
        )
        storage.add_classification(
            doi=doi,
            item_id="dandi.000003",
            item_flavor="0.1",
            result=self._make_result("Reviews"),
            model="gemma",
            backend="dartmouth",
        )
        storage.add_classification(
            doi=doi,
            item_id="dandi.000020",
            item_flavor="1.0",
            result=self._make_result("Cites"),
            model="gpt-4",
            backend="openai",
        )

        results = storage.get_classifications_for_item(doi, "dandi.000003", "0.1")
        assert len(results) == 2
        types = {r.relationship_type for r in results}
        assert types == {"Uses", "Reviews"}

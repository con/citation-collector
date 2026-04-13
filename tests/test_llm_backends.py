"""Tests for citations_collector.llm package (factory, prompts, backends)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from citations_collector.llm.base import LLMBackend
from citations_collector.llm.factory import create_backend
from citations_collector.llm.prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_classification_prompt,
)

# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestCreateBackend:
    """Test create_backend factory function."""

    @patch("citations_collector.llm.factory.OllamaBackend")
    def test_creates_ollama(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = MagicMock(spec=LLMBackend)
        backend = create_backend("ollama", model="qwen2:7b")
        mock_cls.assert_called_once_with(model="qwen2:7b")
        assert backend is mock_cls.return_value

    @patch("citations_collector.llm.factory.OpenAIBackend")
    def test_creates_openai(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = MagicMock(spec=LLMBackend)
        backend = create_backend("openai", model="gpt-4", api_key="sk-test")
        mock_cls.assert_called_once_with(model="gpt-4", api_key="sk-test")
        assert backend is mock_cls.return_value

    @patch("citations_collector.llm.factory.OpenRouterBackend")
    def test_creates_openrouter(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = MagicMock(spec=LLMBackend)
        backend = create_backend("openrouter", model="openai/gpt-4.1-nano", api_key="sk-or-test")
        mock_cls.assert_called_once_with(model="openai/gpt-4.1-nano", api_key="sk-or-test")
        assert backend is mock_cls.return_value

    @patch("citations_collector.llm.factory.OpenAIBackend")
    def test_creates_dartmouth_with_default_base_url(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = MagicMock(spec=LLMBackend)
        backend = create_backend("dartmouth", model="gpt-4", api_key="key")
        mock_cls.assert_called_once_with(
            model="gpt-4",
            api_key="key",
            base_url="https://chat.dartmouth.edu/api",
        )
        assert backend is mock_cls.return_value

    @patch("citations_collector.llm.factory.OpenAIBackend")
    def test_dartmouth_respects_custom_base_url(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = MagicMock(spec=LLMBackend)
        create_backend("dartmouth", model="gpt-4", api_key="key", base_url="https://custom.url")
        mock_cls.assert_called_once_with(
            model="gpt-4",
            api_key="key",
            base_url="https://custom.url",
        )

    def test_unknown_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown backend type"):
            create_backend("nonexistent")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Prompt tests
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestBuildClassificationPrompt:
    """Test build_classification_prompt."""

    def test_includes_metadata(self) -> None:
        prompt = build_classification_prompt(
            contexts=["We used DANDI:000003"],
            paper_metadata={"title": "My Paper", "journal": "Nature", "year": 2024},
            dataset_id="dandi:000003",
        )
        assert "My Paper" in prompt
        assert "Nature" in prompt
        assert "2024" in prompt
        assert "dandi:000003" in prompt

    def test_includes_all_contexts(self) -> None:
        prompt = build_classification_prompt(
            contexts=["First context", "Second context"],
            paper_metadata={"title": "T"},
            dataset_id="d",
        )
        assert "[Context 1] First context" in prompt
        assert "[Context 2] Second context" in prompt

    def test_missing_metadata_shows_unknown(self) -> None:
        prompt = build_classification_prompt(
            contexts=["ctx"],
            paper_metadata={},
            dataset_id="d",
        )
        assert "Unknown" in prompt

    def test_system_prompt_is_nonempty(self) -> None:
        assert len(CLASSIFICATION_SYSTEM_PROMPT) > 100
        assert "relationship_type" in CLASSIFICATION_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# OpenAI backend parse_response tests
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestOpenAIBackendParseResponse:
    """Test OpenAIBackend._parse_response with mocked responses."""

    def _make_backend(self) -> MagicMock:
        """Create a backend instance with mocked OpenAI client."""
        from citations_collector.llm.openai_backend import OpenAIBackend

        with patch("openai.OpenAI"):
            backend = OpenAIBackend(model="gpt-4", api_key="sk-test")
        backend.client = MagicMock()
        return backend

    def test_parses_plain_json(self) -> None:
        backend = self._make_backend()
        response = MagicMock()
        response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "relationship_type": "Uses",
                            "confidence": 0.9,
                            "reasoning": "Paper uses the dataset",
                        }
                    )
                )
            )
        ]

        result = backend._parse_response(response, ["ctx"])
        assert result.relationship_type == "Uses"
        assert result.confidence == 0.9
        assert result.context_used == ["ctx"]

    def test_parses_json_in_code_block(self) -> None:
        backend = self._make_backend()
        content = (
            '```json\n{"relationship_type": "Reviews", "confidence": 0.8, "reasoning": "rev"}\n```'
        )
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content=content))]

        result = backend._parse_response(response, [])
        assert result.relationship_type == "Reviews"

    def test_parses_json_in_plain_code_block(self) -> None:
        backend = self._make_backend()
        content = (
            '```\n{"relationship_type": "Cites", "confidence": 0.5, "reasoning": "generic"}\n```'
        )
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content=content))]

        result = backend._parse_response(response, [])
        assert result.relationship_type == "Cites"

    def test_returns_fallback_on_invalid_json(self) -> None:
        backend = self._make_backend()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content="not json at all"))]

        result = backend._parse_response(response, ["ctx"])
        assert result.relationship_type == "Cites"
        assert result.confidence == 0.0
        assert "Parse error" in result.reasoning

    def test_returns_fallback_on_missing_keys(self) -> None:
        backend = self._make_backend()
        response = MagicMock()
        response.choices = [MagicMock(message=MagicMock(content='{"relationship_type": "Uses"}'))]

        result = backend._parse_response(response, [])
        assert result.relationship_type == "Cites"
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# OpenAI backend classify_citation with mocked client
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestOpenAIBackendClassify:
    """Test OpenAIBackend.classify_citation with mocked API."""

    def test_classify_success(self) -> None:
        from citations_collector.llm.openai_backend import OpenAIBackend

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client

            backend = OpenAIBackend(model="gpt-4", api_key="sk-test")

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(
                            {
                                "relationship_type": "Uses",
                                "confidence": 0.92,
                                "reasoning": "Data was analysed",
                            }
                        )
                    )
                )
            ]
            mock_client.chat.completions.create.return_value = mock_response

            result = backend.classify_citation(
                contexts=["We analysed DANDI:000003"],
                paper_metadata={"title": "Test"},
                dataset_id="dandi:000003",
            )

            assert result.relationship_type == "Uses"
            assert result.confidence == 0.92

    def test_classify_api_error_returns_fallback(self) -> None:
        from citations_collector.llm.openai_backend import OpenAIBackend

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("API down")

            backend = OpenAIBackend(model="gpt-4", api_key="sk-test")

            result = backend.classify_citation(
                contexts=["ctx"],
                paper_metadata={"title": "T"},
                dataset_id="d",
            )

            assert result.relationship_type == "Cites"
            assert result.confidence == 0.0
            assert "API error" in result.reasoning


# ---------------------------------------------------------------------------
# Ollama backend parse_response tests
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestOllamaBackendParseResponse:
    """Test OllamaBackend._parse_response."""

    def test_parses_valid_response(self) -> None:
        from citations_collector.llm.ollama_backend import OllamaBackend

        backend = OllamaBackend.__new__(OllamaBackend)
        backend.model = "qwen2:7b"

        response_json = {
            "message": {
                "content": json.dumps(
                    {
                        "relationship_type": "CitesAsEvidence",
                        "confidence": 0.88,
                        "reasoning": "benchmarking",
                    }
                )
            }
        }

        result = backend._parse_response(response_json, ["ctx"])
        assert result.relationship_type == "CitesAsEvidence"
        assert result.confidence == 0.88

    def test_parse_failure_returns_fallback(self) -> None:
        from citations_collector.llm.ollama_backend import OllamaBackend

        backend = OllamaBackend.__new__(OllamaBackend)
        backend.model = "qwen2:7b"

        result = backend._parse_response({"message": {"content": "garbage"}}, [])
        assert result.relationship_type == "Cites"
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# OpenRouter backend parse_response tests
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestOpenRouterBackendParseResponse:
    """Test OpenRouterBackend._parse_response."""

    def test_parses_valid_response(self) -> None:
        from citations_collector.llm.openrouter import OpenRouterBackend

        backend = OpenRouterBackend.__new__(OpenRouterBackend)
        backend.model = "openai/gpt-4.1-nano"

        response_json = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "relationship_type": "Compiles",
                                "confidence": 0.75,
                                "reasoning": "meta-analysis",
                            }
                        )
                    }
                }
            ]
        }

        result = backend._parse_response(response_json, ["c1", "c2"])
        assert result.relationship_type == "Compiles"
        assert result.confidence == 0.75
        assert result.context_used == ["c1", "c2"]

    def test_parse_failure_returns_fallback(self) -> None:
        from citations_collector.llm.openrouter import OpenRouterBackend

        backend = OpenRouterBackend.__new__(OpenRouterBackend)
        backend.model = "m"

        result = backend._parse_response({"choices": [{"message": {"content": "bad"}}]}, [])
        assert result.relationship_type == "Cites"
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Backend batch_classify
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestBatchClassify:
    """Test batch_classify on OpenAI backend (representative for all)."""

    def test_batch_processes_sequentially(self) -> None:
        from citations_collector.llm.openai_backend import OpenAIBackend

        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client

            backend = OpenAIBackend(model="gpt-4", api_key="sk-test")

            good_json = json.dumps(
                {"relationship_type": "Uses", "confidence": 0.9, "reasoning": "ok"}
            )
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content=good_json))]
            mock_client.chat.completions.create.return_value = mock_response

            citations = [
                (["ctx1"], {"title": "P1"}, "d1"),
                (["ctx2"], {"title": "P2"}, "d2"),
            ]

            results = backend.batch_classify(citations)
            assert len(results) == 2
            assert all(r.relationship_type == "Uses" for r in results)
            assert mock_client.chat.completions.create.call_count == 2


# ---------------------------------------------------------------------------
# OpenAI backend init validation
# ---------------------------------------------------------------------------


@pytest.mark.ai_generated
class TestOpenAIBackendInit:
    """Test OpenAIBackend constructor validation."""

    def test_raises_without_api_key(self) -> None:
        from citations_collector.llm.openai_backend import OpenAIBackend

        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="API key required"),
        ):
            OpenAIBackend(model="gpt-4", api_key=None)

    def test_raises_without_openai_package(self) -> None:
        """When openai is not importable, raises ImportError."""
        import builtins

        from citations_collector.llm.openai_backend import OpenAIBackend

        real_import = builtins.__import__

        def mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "openai":
                raise ImportError("no openai")
            return real_import(name, *args, **kwargs)

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
            patch("builtins.__import__", side_effect=mock_import),
            pytest.raises(ImportError, match="openai package required"),
        ):
            OpenAIBackend(model="gpt-4", api_key="sk-test")


@pytest.mark.ai_generated
class TestOpenRouterBackendInit:
    """Test OpenRouterBackend constructor validation."""

    def test_raises_without_api_key(self) -> None:
        from citations_collector.llm.openrouter import OpenRouterBackend

        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="API key required"),
        ):
            OpenRouterBackend(model="m", api_key=None)

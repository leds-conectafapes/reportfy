"""Unit tests for MarkdownSummarizer (AI module) — mocks the Mistral API."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from reportfy.ai.prompts import PromptType


@pytest.fixture(scope="module")
def MarkdownSummarizer():
    """Import MarkdownSummarizer lazily so mistralai is loaded inside the test."""
    from reportfy.ai.summarizer import MarkdownSummarizer as _MS
    return _MS


class TestMarkdownSummarizer:
    """Tests for MarkdownSummarizer."""

    @pytest.fixture
    def sample_md_file(self, tmp_path):
        """Create a temporary markdown file for testing."""
        path = tmp_path / "report.md"
        path.write_text("# Test Report\n\nSome content here.")
        return str(path)

    def test_raises_if_no_api_key(self, MarkdownSummarizer, sample_md_file):
        """Constructor must raise ValueError when no API key is provided."""
        with pytest.raises(ValueError, match="API key"):
            MarkdownSummarizer(api_key="", filepaths=[sample_md_file])

    def test_raises_if_file_not_found(self, MarkdownSummarizer):
        """generate_summary() must raise FileNotFoundError for missing files."""
        summarizer = MarkdownSummarizer(
            api_key="test-key",
            filepaths=["/non/existent/path.md"],
        )
        with pytest.raises(FileNotFoundError):
            summarizer.generate_summary()

    def test_generate_summary_calls_mistral(self, MarkdownSummarizer, sample_md_file):
        """generate_summary() should call the Mistral client and return its text."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "  Generated summary  "

        with patch("reportfy.ai.summarizer.Mistral") as MockMistral:
            mock_client = MockMistral.return_value
            mock_client.chat.complete.return_value = mock_response

            summarizer = MarkdownSummarizer(
                api_key="test-key",
                filepaths=[sample_md_file],
                prompt_type=PromptType.PROJETO,
            )
            result = summarizer.generate_summary()

        assert result == "Generated summary"
        mock_client.chat.complete.assert_called_once()

    def test_uses_correct_model(self, MarkdownSummarizer, sample_md_file):
        """The model name must be forwarded to the Mistral API call."""
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"

        with patch("reportfy.ai.summarizer.Mistral") as MockMistral:
            mock_client = MockMistral.return_value
            mock_client.chat.complete.return_value = mock_response

            summarizer = MarkdownSummarizer(
                api_key="test-key",
                filepaths=[sample_md_file],
                model="mistral-small-latest",
            )
            summarizer.generate_summary()

        call_kwargs = mock_client.chat.complete.call_args
        passed_model = call_kwargs.kwargs.get("model") or (
            call_kwargs.args[0] if call_kwargs.args else None
        )
        assert passed_model == "mistral-small-latest"

    def test_week_range_returns_monday_and_friday(self, MarkdownSummarizer):
        """_current_week_range() must return Monday and Friday of the current week."""
        start, end = MarkdownSummarizer._current_week_range()
        from datetime import date
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
        assert start_d.weekday() == 0    # Monday
        assert end_d.weekday() == 4      # Friday
        assert (end_d - start_d).days == 4

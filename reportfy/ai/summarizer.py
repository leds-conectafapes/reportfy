"""MarkdownSummarizer — generates AI-powered summaries via the Mistral API."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Optional

from mistralai.client import Mistral

from reportfy.ai.prompts import PROMPTS, PromptType


class MarkdownSummarizer:
    """
    Reads one or more markdown files, concatenates them, and sends the
    content to Mistral to generate a structured summary.

    Supports five prompt types (see ``PromptType``):
      - PROJETO: Overall project status for leadership.
      - DESENVOLVEDOR: Individual developer performance feedback.
      - EQUIPE_SEMANAL: Weekly team summary.
      - COMPETENCIA: Developer competency assessment.
      - EQUIPES_GERAL_SEMANAL: Cross-team consolidated weekly report.

    Usage::

        summarizer = MarkdownSummarizer(
            api_key="...",
            filepaths=["./report/organization_stats.md"],
            prompt_type=PromptType.PROJETO,
        )
        summary = summarizer.generate_summary()
    """

    def __init__(
        self,
        api_key: str,
        filepaths: list[str],
        prompt_type: PromptType = PromptType.PROJETO,
        model: str = "mistral-large-latest",
    ):
        """
        Args:
            api_key: Mistral API key.
            filepaths: Paths to markdown files to summarise (concatenated).
            prompt_type: Which prompt template to use.
            model: Mistral model identifier (default: ``mistral-large-latest``).
        """
        if not api_key:
            raise ValueError("Mistral API key is required.")
        self.client = Mistral(api_key=api_key)
        self.filepaths = filepaths
        self.prompt_type = prompt_type
        self.model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_summary(self) -> str:
        """
        Read the markdown files and call the Mistral API.

        Returns:
            Generated summary text (stripped).

        Raises:
            FileNotFoundError: If any filepath does not exist.
        """
        content = self._read_markdown()
        prompt = self._build_prompt(content)
        response = self.client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_markdown(self) -> str:
        """Read and concatenate all markdown files."""
        parts: list[str] = []
        for filepath in self.filepaths:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Markdown file not found: {filepath}")
            with open(filepath, "r", encoding="utf-8") as f:
                parts.append(f.read())
        return "\n\n---\n\n".join(parts)

    def _build_prompt(self, content: str) -> str:
        """Combine the prompt template with the markdown content."""
        prompt_base = PROMPTS[self.prompt_type]
        start_date, end_date = self._current_week_range()
        prompt_base = (
            prompt_base
            .replace("**data_inicial**", f"**{start_date}**")
            .replace("**data_final**", f"**{end_date}**")
        )
        return prompt_base + content

    @staticmethod
    def _current_week_range() -> tuple[str, str]:
        """Return (Monday, Friday) of the current week as ISO strings."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)
        return monday.isoformat(), friday.isoformat()

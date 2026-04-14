"""BaseController — abstract base for all Reportfy domain controllers."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional

from reportfy.core.config import ReportConfig


class BaseController(ABC):
    """
    Abstract base class for domain controllers.

    A *controller* is responsible for:
      1. Receiving pre-fetched data and a ReportConfig.
      2. Instantiating the appropriate Model with that data.
      3. Instantiating the appropriate View with the Model.
      4. Calling ``view.render()`` and persisting the result to disk.

    Subclasses must implement ``run()``.
    """

    def __init__(self, config: ReportConfig):
        """
        Args:
            config: Shared runtime configuration.
        """
        self.config = config
        os.makedirs(config.output_dir, exist_ok=True)

    @abstractmethod
    def run(self) -> str:
        """
        Execute the full pipeline for this controller.

        Returns:
            Path to the primary output markdown file.
        """

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _save_report(self, content: str, filename: str) -> str:
        """
        Write *content* to ``{output_dir}/{filename}``.

        Args:
            content: Markdown string to write.
            filename: Relative filename inside output_dir.

        Returns:
            Absolute path to the written file.
        """
        path = os.path.join(self.config.output_dir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Report saved → {path}")
        return path

    def _generate_ai_summary(
        self,
        filepaths: list[str],
        prompt_type,
        section_title: str = "Análise por IA",
    ) -> str:
        """
        Generate an AI summary section using Mistral, if enabled.

        Silently returns an empty string when AI is disabled, the API key is
        missing, or an API error occurs — so callers never need a try/except.

        Args:
            filepaths: Markdown files to read and summarise.
            prompt_type: ``PromptType`` enum value selecting the prompt template.
            section_title: Heading for the generated markdown section.

        Returns:
            A markdown string with a section heading + AI-generated body,
            or ``""`` if AI is not available / an error occurred.
        """
        if not self.config.has_ai():
            return ""

        # Lazy import — avoids loading mistralai when AI is disabled
        try:
            from reportfy.ai.summarizer import MarkdownSummarizer

            summarizer = MarkdownSummarizer(
                api_key=self.config.mistral_api_key,
                filepaths=filepaths,
                prompt_type=prompt_type,
                model=self.config.mistral_model,
            )
            summary = summarizer.generate_summary()
            print(f"  [AI] {section_title} generated ({len(summary)} chars).")
            return f"\n\n---\n\n## {section_title}\n\n> _Gerado por IA (Mistral)_\n\n{summary}\n"
        except FileNotFoundError as exc:
            print(f"  [AI] Skipping — file not found: {exc}")
            return ""
        except Exception as exc:  # noqa: BLE001
            print(f"  [AI] Error generating summary: {exc}")
            return ""

    def _append_ai_to_file(
        self,
        filepath: str,
        prompt_type,
        section_title: str = "Análise por IA",
    ) -> None:
        """
        Append an AI-generated section to an already-written markdown file.

        A no-op when AI is disabled or an error occurs.

        Args:
            filepath: Path to the existing markdown file to read and append to.
            prompt_type: ``PromptType`` enum value selecting the prompt template.
            section_title: Heading for the appended markdown section.
        """
        ai_section = self._generate_ai_summary([filepath], prompt_type, section_title)
        if not ai_section:
            return
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(ai_section)

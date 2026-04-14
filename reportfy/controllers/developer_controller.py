"""DeveloperController — orchestrates the per-developer dashboard."""
from __future__ import annotations

import os

import pandas as pd

from reportfy.controllers.base import BaseController
from reportfy.core.config import ReportConfig
from reportfy.models.issue import IssueModel
from reportfy.models.developer import DeveloperModel
from reportfy.views.developer_view import DeveloperView


class DeveloperController(BaseController):
    """
    Drives the per-developer dashboard pipeline.

    Pipeline (three explicit phases):

    1. ``run()`` — generate all markdown files and charts from GitHub data.
    2. ``run_ai()`` — append Mistral AI analyses to each file already on disk.
    3. Notifications — handled externally by ``DeveloperMessageSender`` /
       ``CompetenceMessageSender`` after both phases complete.
    """

    def __init__(self, config: ReportConfig, issues_df: pd.DataFrame):
        """
        Args:
            config: Shared runtime configuration.
            issues_df: Raw issues DataFrame from GitHubFetcher.
        """
        super().__init__(config)
        self.issues_df = issues_df
        self._model: DeveloperModel | None = None

    # ------------------------------------------------------------------
    # Phase 1 — generate
    # ------------------------------------------------------------------

    def run(self) -> str:
        """
        Phase 1: generate all developer markdown files and the summary index.

        Writes one file per developer in ``{output_dir}/developers/`` and the
        index at ``{output_dir}/developer_stats.md``.  No AI calls are made
        here — call ``run_ai()`` afterwards.

        Returns:
            Path to the summary index file.
        """
        print("Running DeveloperController…")
        issues = [IssueModel.from_row(row) for row in self.issues_df.to_dict("records")]

        self._model = DeveloperModel(issues)
        view = DeveloperView(self._model, self.config.output_dir)

        view.save_all_developer_reports()

        summary = view.render()
        return self._save_report(summary, "developer_stats.md")

    # ------------------------------------------------------------------
    # Phase 2 — AI analysis
    # ------------------------------------------------------------------

    def run_ai(self) -> None:
        """
        Phase 2: append Mistral AI sections to every developer file on disk.

        Must be called **after** ``run()``.  Silently skips if AI is not
        configured (``config.has_ai() == False``).

        Appends two sections per developer:
          - **Análise de Desempenho** (``PromptType.DESENVOLVEDOR``) — productivity
            feedback: consistency, delivery impact, points of attention.
          - **Análise de Competências** (``PromptType.COMPETENCIA``) — competency
            profile: technical skills, soft skills, reliability, future allocation.
        """
        if not self.config.has_ai():
            return

        if self._model is None:
            print("[DeveloperController] run() must be called before run_ai().")
            return

        from reportfy.ai.prompts import PromptType

        dev_dir = os.path.join(self.config.output_dir, "developers")
        all_stats = self._model.all_stats()
        total = len(all_stats)
        print(f"  [AI] Gerando análises para {total} desenvolvedores…")

        for idx, stats in enumerate(all_stats, 1):
            dev_path = os.path.join(dev_dir, f"{stats.login}.md")
            if not os.path.exists(dev_path):
                continue
            print(f"  [AI] {idx}/{total} — {stats.login}")
            # Performance feedback
            self._append_ai_to_file(
                dev_path,
                PromptType.DESENVOLVEDOR,
                "Análise de Desempenho",
            )
            # Competency profile
            self._append_ai_to_file(
                dev_path,
                PromptType.COMPETENCIA,
                "Análise de Competências",
            )

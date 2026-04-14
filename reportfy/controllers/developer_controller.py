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
        Phase 2: generate Mistral AI feedback files for every developer.

        Must be called **after** ``run()``.  Silently skips if AI is not
        configured (``config.has_ai() == False``).

        Creates a separate ``{login}_feedback.md`` file per developer containing:
          - **Análise de Desempenho** (``PromptType.DESENVOLVEDOR``) — productivity
            feedback: consistency, delivery impact, points of attention.
          - **Análise de Competências** (``PromptType.COMPETENCIA``) — competency
            profile: technical skills, soft skills, reliability, future allocation.

        The main ``{login}.md`` stats file is left untouched.
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
            self._write_developer_feedback(dev_path, stats.login)

    def _write_developer_feedback(self, stats_path: str, login: str) -> None:
        """
        Generate and save ``{login}_feedback.md`` with both AI analyses.

        Args:
            stats_path: Path to the developer's stats markdown file (used as AI input).
            login: GitHub login used to name the output file.
        """
        from reportfy.ai.prompts import PromptType

        performance = self._generate_ai_summary(
            [stats_path], PromptType.DESENVOLVEDOR, "Análise de Desempenho", raw=True
        )
        competency = self._generate_ai_summary(
            [stats_path], PromptType.COMPETENCIA, "Perfil de Competências", raw=True
        )
        evolution = self._generate_ai_summary(
            [stats_path], PromptType.COMPETENCIA_EVOLUTIVA, "Evolução Mensal", raw=True
        )

        if not any([performance, competency, evolution]):
            return

        feedback_path = os.path.join(
            os.path.dirname(stats_path), f"{login}_feedback.md"
        )
        with open(feedback_path, "w", encoding="utf-8") as f:
            f.write(f"# Feedback — {login}\n\n")
            f.write(f"> _Gerado por IA (Mistral) — modelo: {self.config.mistral_model}_\n\n")
            if performance:
                f.write("---\n\n## Análise de Desempenho\n\n")
                f.write(performance)
                f.write("\n\n")
            if evolution:
                f.write("---\n\n")
                f.write(evolution)
                f.write("\n\n")
            if competency:
                f.write("---\n\n## Perfil de Competências\n\n")
                f.write(competency)
                f.write("\n")
        print(f"  [AI] Feedback salvo → {feedback_path}")

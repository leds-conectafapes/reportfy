"""OrganizationController — orchestrates the organisation-level dashboard."""
from __future__ import annotations

import pandas as pd

from reportfy.controllers.base import BaseController
from reportfy.core.config import ReportConfig
from reportfy.models.issue import IssueModel
from reportfy.models.organization import OrganizationModel
from reportfy.views.organization_view import OrganizationView


class OrganizationController(BaseController):
    """
    Drives the organisation dashboard pipeline:

    ``issues_df`` → ``OrganizationModel`` → ``OrganizationView`` → markdown file.
    """

    def __init__(self, config: ReportConfig, issues_df: pd.DataFrame):
        """
        Args:
            config: Shared runtime configuration.
            issues_df: Raw issues DataFrame from GitHubFetcher.
        """
        super().__init__(config)
        self.issues_df = issues_df

    def run(self) -> str:
        """
        Phase 1: generate ``{output_dir}/organization_stats.md`` with charts.

        No AI calls are made here — call ``run_ai()`` afterwards.

        Returns:
            Path to ``{output_dir}/organization_stats.md``.
        """
        print("Running OrganizationController…")
        issues = [IssueModel.from_row(row) for row in self.issues_df.to_dict("records")]

        self._model = OrganizationModel(issues, simulations=self.config.monte_carlo_simulations)
        view = OrganizationView(self._model, self.config.output_dir)

        markdown = view.render()
        self._report_path = self._save_report(markdown, "organization_stats.md")
        return self._report_path

    def run_ai(self) -> None:
        """
        Phase 2: append Mistral AI strategic analysis to the organization report.

        Must be called **after** ``run()``.  Silently skips if AI is not configured.

        Appends:
          - **Análise Estratégica por IA** (``PromptType.PROJETO``) — risk assessment,
            bottleneck identification, velocity trends, and strategic next steps.
        """
        if not self.config.has_ai():
            return
        if not getattr(self, "_report_path", ""):
            print("[OrganizationController] run() must be called before run_ai().")
            return
        from reportfy.ai.prompts import PromptType
        print("  [AI] Gerando análise estratégica da organização…")
        self._append_ai_to_file(
            self._report_path,
            PromptType.PROJETO,
            "Análise Estratégica por IA",
        )

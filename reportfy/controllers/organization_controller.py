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
        Execute the full organisation pipeline.

        Returns:
            Path to ``{output_dir}/organization_stats.md``.
        """
        print("Running OrganizationController…")
        issues = [IssueModel.from_row(row) for row in self.issues_df.to_dict("records")]

        model = OrganizationModel(issues, simulations=self.config.monte_carlo_simulations)
        view = OrganizationView(model, self.config.output_dir)

        markdown = view.render()
        return self._save_report(markdown, "organization_stats.md")

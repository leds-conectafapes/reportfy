"""RepositoryController — orchestrates the per-repository dashboard."""
from __future__ import annotations

import pandas as pd

from reportfy.controllers.base import BaseController
from reportfy.core.config import ReportConfig
from reportfy.models.issue import IssueModel
from reportfy.models.repository import RepositoryModel
from reportfy.views.repository_view import RepositoryView


class RepositoryController(BaseController):
    """
    Drives the per-repository dashboard pipeline:

    ``issues_df`` → ``RepositoryModel`` → ``RepositoryView`` → markdown file.
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
        Execute the full repository pipeline.

        Returns:
            Path to ``{output_dir}/repository_stats.md``.
        """
        print("Running RepositoryController…")
        issues = [IssueModel.from_row(row) for row in self.issues_df.to_dict("records")]

        model = RepositoryModel(issues, simulations=self.config.monte_carlo_simulations)
        view = RepositoryView(model, self.config.output_dir)

        markdown = view.render()
        return self._save_report(markdown, "repository_stats.md")

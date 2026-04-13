"""DeveloperController — orchestrates the per-developer dashboard."""
from __future__ import annotations

import pandas as pd

from reportfy.controllers.base import BaseController
from reportfy.core.config import ReportConfig
from reportfy.models.issue import IssueModel
from reportfy.models.developer import DeveloperModel
from reportfy.views.developer_view import DeveloperView


class DeveloperController(BaseController):
    """
    Drives the per-developer dashboard pipeline:

    ``issues_df`` → ``DeveloperModel`` → ``DeveloperView``
    → individual developer files + summary index.
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
        Execute the full developer pipeline.

        Writes one markdown file per developer in ``{output_dir}/developers/``
        and a summary index at ``{output_dir}/developer_stats.md``.

        Returns:
            Path to the summary index file.
        """
        print("Running DeveloperController…")
        issues = [IssueModel.from_row(row) for row in self.issues_df.to_dict("records")]

        model = DeveloperModel(issues)
        view = DeveloperView(model, self.config.output_dir)

        # Write individual developer files
        view.save_all_developer_reports()

        # Write and return the summary index
        summary = view.render()
        return self._save_report(summary, "developer_stats.md")

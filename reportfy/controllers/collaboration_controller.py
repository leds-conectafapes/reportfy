"""CollaborationController — orchestrates the collaboration graph dashboard."""
from __future__ import annotations

import pandas as pd

from reportfy.controllers.base import BaseController
from reportfy.core.config import ReportConfig
from reportfy.models.issue import IssueModel
from reportfy.models.collaboration import CollaborationModel
from reportfy.views.collaboration_view import CollaborationView


class CollaborationController(BaseController):
    """
    Drives the collaboration graph pipeline:

    ``issues_df`` → ``CollaborationModel`` → ``CollaborationView`` → markdown file.
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
        Execute the full collaboration pipeline.

        Returns:
            Path to ``{output_dir}/collaboration_report.md``.
        """
        print("Running CollaborationController…")
        issues = [IssueModel.from_row(row) for row in self.issues_df.to_dict("records")]

        model = CollaborationModel(issues)
        model.build_graph()
        view = CollaborationView(model, self.config.output_dir)

        markdown = view.render()
        return self._save_report(markdown, "collaboration_report.md")

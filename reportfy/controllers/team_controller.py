"""TeamController — orchestrates the per-team dashboard."""
from __future__ import annotations

import pandas as pd

from reportfy.controllers.base import BaseController
from reportfy.core.config import ReportConfig
from reportfy.models.issue import IssueModel
from reportfy.models.team import TeamModel
from reportfy.views.team_view import TeamView


class TeamController(BaseController):
    """
    Drives the per-team dashboard pipeline:

    ``issues_df`` + ``members_df`` → ``TeamModel`` → ``TeamView``
    → individual team files + summary index.
    """

    def __init__(
        self,
        config: ReportConfig,
        issues_df: pd.DataFrame,
        members_df: pd.DataFrame,
    ):
        """
        Args:
            config: Shared runtime configuration.
            issues_df: Raw issues DataFrame from GitHubFetcher.
            members_df: Raw team_members DataFrame from GitHubFetcher.
        """
        super().__init__(config)
        self.issues_df = issues_df
        self.members_df = members_df

    def run(self) -> str:
        """
        Execute the full team pipeline.

        Writes one markdown file per team in ``{output_dir}/teams/``
        and a summary index at ``{output_dir}/teams.md``.

        Returns:
            Path to the summary index file.
        """
        print("Running TeamController…")
        issues = [IssueModel.from_row(row) for row in self.issues_df.to_dict("records")]

        model = TeamModel(issues, self.members_df)
        view = TeamView(model, self.config.output_dir)

        view.save_all_team_reports()

        summary = view.render()
        return self._save_report(summary, "teams.md")

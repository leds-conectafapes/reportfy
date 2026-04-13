"""ReportController — main orchestrator that runs all domain controllers."""
from __future__ import annotations

import subprocess

from reportfy.controllers.base import BaseController
from reportfy.controllers.collaboration_controller import CollaborationController
from reportfy.controllers.developer_controller import DeveloperController
from reportfy.controllers.organization_controller import OrganizationController
from reportfy.controllers.repository_controller import RepositoryController
from reportfy.controllers.team_controller import TeamController
from reportfy.core.config import ReportConfig
from reportfy.core.fetcher import GitHubFetcher


class ReportController(BaseController):
    """
    Top-level controller that:

    1. Fetches all GitHub data once via ``GitHubFetcher``.
    2. Runs each enabled domain controller in sequence.
    3. Optionally commits the generated reports to git.
    """

    def __init__(self, config: ReportConfig):
        """
        Args:
            config: Shared runtime configuration with all feature flags.
        """
        super().__init__(config)
        self.fetcher = GitHubFetcher(config)

    def run(self) -> str:
        """
        Execute the full reporting pipeline.

        Returns:
            Path to the output directory.
        """
        print(f"\n{'='*60}")
        print(f"Reportfy — {self.config.repository}")
        print(f"{'='*60}\n")

        # Fetch all data once (shared cache via Airbyte DuckDB)
        data = self.fetcher.fetch_all()
        issues_df = data["issues"]
        members_df = data["team_members"]

        if issues_df.empty:
            print("No issues found. Exiting.")
            return self.config.output_dir

        output_paths: list[str] = []

        if self.config.enable_organization_report:
            path = OrganizationController(self.config, issues_df).run()
            output_paths.append(path)

        if self.config.enable_repository_report:
            path = RepositoryController(self.config, issues_df).run()
            output_paths.append(path)

        if self.config.enable_developer_report:
            path = DeveloperController(self.config, issues_df).run()
            output_paths.append(path)

        if self.config.enable_team_report:
            path = TeamController(self.config, issues_df, members_df).run()
            output_paths.append(path)

        if self.config.enable_collaboration_report:
            path = CollaborationController(self.config, issues_df).run()
            output_paths.append(path)

        print(f"\nGenerated {len(output_paths)} report(s).")

        if self.config.commit_reports:
            self._commit_reports()

        return self.config.output_dir

    # ------------------------------------------------------------------
    # Git commit
    # ------------------------------------------------------------------

    def _commit_reports(self) -> None:
        """Stage and commit all generated reports to the current git repository."""
        try:
            subprocess.run(["git", "config", "user.email", "reportfy-bot@github.com"], check=True)
            subprocess.run(["git", "config", "user.name", "Reportfy Bot"], check=True)
            subprocess.run(["git", "add", self.config.output_dir], check=True)
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                capture_output=True,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m", "chore(reports): auto-generate weekly reports [skip ci]"],
                    check=True,
                )
                print("Reports committed to git.")
            else:
                print("No changes to commit.")
        except subprocess.CalledProcessError as exc:
            print(f"Git commit failed: {exc}")

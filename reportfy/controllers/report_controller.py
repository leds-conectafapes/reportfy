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
        Execute the full reporting pipeline in three explicit phases:

        **Phase 1 — Generate:** all controllers write markdown files and charts
        from GitHub data.  No AI calls happen here.

        **Phase 2 — AI analysis:** each controller appends Mistral-generated
        sections to the files already on disk.  Only runs when
        ``config.has_ai()`` is True.

        **Phase 3 — Notifications:** Discord senders run last, after every file
        is complete.  Only runs when ``config.has_discord()`` is True.

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

        # ── Phase 1: Generate all reports ─────────────────────────────
        print("\n── Fase 1: Gerando relatórios ──")
        controllers: list = []

        if self.config.enable_organization_report:
            ctrl = OrganizationController(self.config, issues_df)
            ctrl.run()
            controllers.append(ctrl)

        if self.config.enable_repository_report:
            RepositoryController(self.config, issues_df).run()

        if self.config.enable_developer_report:
            ctrl = DeveloperController(self.config, issues_df)
            ctrl.run()
            controllers.append(ctrl)

        if self.config.enable_team_report:
            ctrl = TeamController(self.config, issues_df, members_df)
            ctrl.run()
            controllers.append(ctrl)

        if self.config.enable_collaboration_report:
            ctrl = CollaborationController(self.config, issues_df)
            ctrl.run()
            controllers.append(ctrl)

        print(f"\nFase 1 concluída — {len(controllers)} controller(s) executados.")

        # ── Phase 2: AI analysis (append to generated files) ──────────
        if self.config.has_ai():
            print("\n── Fase 2: Análises por IA (Mistral) ──")
            for ctrl in controllers:
                if hasattr(ctrl, "run_ai"):
                    ctrl.run_ai()
            print("\nFase 2 concluída.")
        else:
            print("\n[Fase 2 ignorada — ENABLE_AI_SUMMARIES=false ou MISTRAL_API_KEY ausente]")

        # ── Phase 3: Discord notifications ────────────────────────────
        if self.config.has_discord():
            print("\n── Fase 3: Enviando notificações Discord ──")
            self._send_notifications()
            print("\nFase 3 concluída.")
        else:
            print("\n[Fase 3 ignorada — ENABLE_DISCORD_NOTIFICATIONS=false ou token ausente]")

        if self.config.commit_reports:
            self._commit_reports()

        return self.config.output_dir

    # ------------------------------------------------------------------
    # Phase 3 — notifications
    # ------------------------------------------------------------------

    def _send_notifications(self) -> None:
        """Send all enabled Discord notifications (called from phase 3)."""
        from reportfy.notifications.senders import (
            DeveloperMessageSender,
            CompetenceMessageSender,
            TeamWeeklySender,
            TeamsGeneralSender,
            ProjectMessageSender,
        )
        # Individual developer DMs + competency
        if self.config.enable_developer_report:
            DeveloperMessageSender(self.config).send()
            CompetenceMessageSender(self.config).send()
        # Team weekly + executive summary
        if self.config.enable_team_report:
            TeamWeeklySender(self.config).send()
            TeamsGeneralSender(self.config).send()
        # Project status to leadership channel
        if self.config.enable_organization_report:
            ProjectMessageSender(self.config).send()

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

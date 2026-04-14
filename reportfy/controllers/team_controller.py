"""TeamController — orchestrates the per-team dashboard."""
from __future__ import annotations

import os

import pandas as pd

from reportfy.controllers.base import BaseController
from reportfy.core.config import ReportConfig
from reportfy.models.issue import IssueModel
from reportfy.models.team import TeamModel
from reportfy.views.team_view import TeamView


class TeamController(BaseController):
    """
    Drives the per-team dashboard pipeline.

    Pipeline (three explicit phases):

    1. ``run()`` — generate all markdown files and charts from GitHub data.
    2. ``run_ai()`` — append Mistral AI analyses to each file already on disk.
    3. Notifications — handled externally by ``TeamWeeklySender`` /
       ``TeamsGeneralSender`` after both phases complete.
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
        self._model: TeamModel | None = None
        self._teams_md_path: str = ""

    # ------------------------------------------------------------------
    # Phase 1 — generate
    # ------------------------------------------------------------------

    def run(self) -> str:
        """
        Phase 1: generate all team markdown files and the summary index.

        Writes one file per team in ``{output_dir}/teams/`` and the index
        at ``{output_dir}/teams.md``.  No AI calls are made here — call
        ``run_ai()`` afterwards.

        Returns:
            Path to ``{output_dir}/teams.md``.
        """
        print("Running TeamController…")
        issues = [IssueModel.from_row(row) for row in self.issues_df.to_dict("records")]

        self._model = TeamModel(issues, self.members_df)
        view = TeamView(self._model, self.config.output_dir)

        view.save_all_team_reports()

        summary = view.render()
        self._teams_md_path = self._save_report(summary, "teams.md")
        return self._teams_md_path

    # ------------------------------------------------------------------
    # Phase 2 — AI analysis
    # ------------------------------------------------------------------

    def run_ai(self) -> None:
        """
        Phase 2: append Mistral AI sections to every team file on disk.

        Must be called **after** ``run()``.  Silently skips if AI is not
        configured (``config.has_ai() == False``).

        Appends two types of analysis:
          - **Resumo Semanal por IA** (``PromptType.EQUIPE_SEMANAL``) — per-team
            weekly summary with highlights, deliveries, and comparative indicators.
          - **Resumo Executivo Semanal** (``PromptType.EQUIPES_GERAL_SEMANAL``) —
            appended to the consolidated ``teams.md``, synthesising all teams.
        """
        if not self.config.has_ai():
            return

        if self._model is None:
            print("[TeamController] run() must be called before run_ai().")
            return

        from reportfy.ai.prompts import PromptType

        teams_dir = os.path.join(self.config.output_dir, "teams")
        all_stats = self._model.all_stats()
        total = len(all_stats)
        print(f"  [AI] Gerando análises para {total} equipes…")

        # Per-team weekly summary
        for idx, stats in enumerate(all_stats, 1):
            team_path = os.path.join(teams_dir, f"{stats.team_slug}.md")
            if not os.path.exists(team_path):
                continue
            print(f"  [AI] {idx}/{total} — equipe {stats.team_slug}")
            self._append_ai_to_file(
                team_path,
                PromptType.EQUIPE_SEMANAL,
                f"Resumo Semanal por IA — {stats.team_slug}",
            )

        # Consolidated executive summary on the teams index
        if self._teams_md_path and os.path.exists(self._teams_md_path):
            print("  [AI] Gerando resumo executivo consolidado de todas as equipes…")
            self._append_ai_to_file(
                self._teams_md_path,
                PromptType.EQUIPES_GERAL_SEMANAL,
                "Resumo Executivo Semanal — Todas as Equipes",
            )

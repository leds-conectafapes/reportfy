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
        Phase 2: generate Mistral AI feedback files for every team.

        Must be called **after** ``run()``.  Silently skips if AI is not
        configured (``config.has_ai() == False``).

        Creates a separate ``{slug}_feedback.md`` per team containing:
          - **Resumo Semanal** (``PromptType.EQUIPE_SEMANAL``) — weekly highlights,
            deliveries, and comparative indicators.
          - **Maturidade e Competência** (``PromptType.EQUIPE_COMPETENCIA``) — team
            maturity assessment with monthly evolution table and development plan.

        Also appends a consolidated executive summary to ``teams.md``
        (``PromptType.EQUIPES_GERAL_SEMANAL``).

        The main ``{slug}.md`` stats files are left untouched.
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

        for idx, stats in enumerate(all_stats, 1):
            team_path = os.path.join(teams_dir, f"{stats.team_slug}.md")
            if not os.path.exists(team_path):
                continue
            print(f"  [AI] {idx}/{total} — equipe {stats.team_slug}")
            self._write_team_feedback(team_path, stats.team_slug)

        # Consolidated executive summary appended to teams index
        if self._teams_md_path and os.path.exists(self._teams_md_path):
            print("  [AI] Gerando resumo executivo consolidado de todas as equipes…")
            self._append_ai_to_file(
                self._teams_md_path,
                PromptType.EQUIPES_GERAL_SEMANAL,
                "Resumo Executivo Semanal — Todas as Equipes",
            )

    def _write_team_feedback(self, stats_path: str, team_slug: str) -> None:
        """
        Generate and save ``{slug}_feedback.md`` with both AI analyses.

        Args:
            stats_path: Path to the team's stats markdown file (used as AI input).
            team_slug: Team slug used to name the output file.
        """
        from reportfy.ai.prompts import PromptType

        weekly = self._generate_ai_summary(
            [stats_path], PromptType.EQUIPE_SEMANAL,
            f"Resumo Semanal — {team_slug}", raw=True
        )
        competency = self._generate_ai_summary(
            [stats_path], PromptType.EQUIPE_COMPETENCIA,
            f"Maturidade e Competência — {team_slug}", raw=True
        )

        if not weekly and not competency:
            return

        feedback_path = os.path.join(
            os.path.dirname(stats_path), f"{team_slug}_feedback.md"
        )
        with open(feedback_path, "w", encoding="utf-8") as f:
            f.write(f"# Feedback — Equipe {team_slug}\n\n")
            f.write(f"> _Gerado por IA (Mistral) — modelo: {self.config.mistral_model}_\n\n")
            if weekly:
                f.write("---\n\n## Resumo Semanal\n\n")
                f.write(weekly)
                f.write("\n\n")
            if competency:
                f.write("---\n\n")
                f.write(competency)
                f.write("\n")
        print(f"  [AI] Feedback salvo → {feedback_path}")

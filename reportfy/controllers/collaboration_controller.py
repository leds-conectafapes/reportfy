"""CollaborationController — orchestrates the collaboration graph dashboard."""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd

from reportfy.controllers.base import BaseController
from reportfy.core.config import ReportConfig
from reportfy.models.issue import IssueModel
from reportfy.models.collaboration import CollaborationModel
from reportfy.views.collaboration_view import CollaborationView

_MONTH_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}


class CollaborationController(BaseController):
    """
    Drives the collaboration graph pipeline.

    Generates:

    - ``{output_dir}/collaboration_report.md`` — overall (all-time) report.
    - ``{output_dir}/collaboration/YYYY-MM/monthly.md`` — one file per calendar
      month with a monthly consolidated analysis followed by a weekly breakdown.
    """

    def __init__(self, config: ReportConfig, issues_df: pd.DataFrame):
        """
        Args:
            config: Shared runtime configuration.
            issues_df: Raw issues DataFrame from GitHubFetcher.
        """
        super().__init__(config)
        self.issues_df = issues_df

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> str:
        """
        Phase 1: generate the overall and monthly collaboration markdown files.

        No AI calls are made here — call ``run_ai()`` afterwards.

        Returns:
            Path to ``{output_dir}/collaboration_report.md``.
        """
        print("Running CollaborationController…")
        self._issues = [IssueModel.from_row(row) for row in self.issues_df.to_dict("records")]

        # Overall report (all issues)
        overall_model = CollaborationModel(self._issues)
        overall_model.build_graph()
        overall_view = CollaborationView(overall_model, self.config.output_dir)
        overall_md = overall_view.render()
        self._overall_path = self._save_report(overall_md, "collaboration_report.md")

        # Monthly reports
        self._generate_monthly_reports(self._issues)

        return self._overall_path

    def run_ai(self) -> None:
        """
        Phase 2: append Mistral AI collaboration analysis to the overall report
        and to each monthly report already on disk.

        Must be called **after** ``run()``.  Silently skips if AI is not configured.

        Appends:
          - **Análise de Colaboração por IA** (``PromptType.COLABORACAO``) to:
              - ``collaboration_report.md`` (overall network)
              - Each ``collaboration/YYYY-MM/monthly.md``
        """
        if not self.config.has_ai():
            return
        if not getattr(self, "_overall_path", ""):
            print("[CollaborationController] run() must be called before run_ai().")
            return

        from reportfy.ai.prompts import PromptType

        # Analyse overall report
        print("  [AI] Gerando análise de colaboração geral…")
        self._append_ai_to_file(
            self._overall_path,
            PromptType.COLABORACAO,
            "Análise de Colaboração por IA",
        )

        # Analyse each monthly report
        collab_base = os.path.join(self.config.output_dir, "collaboration")
        if not os.path.isdir(collab_base):
            return

        monthly_files = sorted([
            os.path.join(collab_base, month_dir, "monthly.md")
            for month_dir in os.listdir(collab_base)
            if os.path.isdir(os.path.join(collab_base, month_dir))
        ])
        monthly_files = [f for f in monthly_files if os.path.exists(f)]
        total = len(monthly_files)
        print(f"  [AI] Analisando {total} relatórios mensais de colaboração…")

        for idx, monthly_path in enumerate(monthly_files, 1):
            month_label = os.path.basename(os.path.dirname(monthly_path))
            print(f"  [AI] {idx}/{total} — colaboração {month_label}")
            self._append_ai_to_file(
                monthly_path,
                PromptType.COLABORACAO,
                "Análise de Colaboração por IA",
            )

    # ------------------------------------------------------------------
    # Monthly breakdown
    # ------------------------------------------------------------------

    def _generate_monthly_reports(self, issues: list[IssueModel]) -> None:
        """Generate one ``monthly.md`` per calendar month inside collaboration/."""
        months = CollaborationModel.months_with_issues(issues)
        if not months:
            return

        print(f"Generating monthly collaboration reports for {len(months)} months…")
        collab_base = os.path.join(self.config.output_dir, "collaboration")
        os.makedirs(collab_base, exist_ok=True)

        for year, month in months:
            self._generate_month(issues, year, month, collab_base)

    def _generate_month(
        self,
        all_issues: list[IssueModel],
        year: int,
        month: int,
        collab_base: str,
    ) -> None:
        """Build and save monthly.md for a single (year, month) pair."""
        month_dir = os.path.join(collab_base, f"{year:04d}-{month:02d}")
        os.makedirs(month_dir, exist_ok=True)

        month_label = f"{_MONTH_PT[month]} {year}"
        slug = f"{year:04d}-{month:02d}"

        # Monthly consolidated model
        month_start, month_end = self._month_bounds(year, month)
        monthly_model = CollaborationModel.for_period(all_issues, month_start, month_end)
        monthly_model.build_graph()

        monthly_view = CollaborationView(
            monthly_model,
            month_dir,
            period_label=month_label,
            chart_filename="network_monthly.png",
        )

        md = f"# Relatório de Colaboração — {month_label}\n\n"
        md += f"> Período: {month_start.strftime('%d/%m/%Y')} a "
        md += f"{(month_end - pd.Timedelta(days=1)).strftime('%d/%m/%Y')}\n\n"
        md += "---\n\n"
        md += "## Análise Mensal Consolidada\n\n"
        md += monthly_view.render_section(heading_level=3)

        # Weekly breakdown
        weeks = CollaborationModel.weeks_in_month(year, month)
        md += "---\n\n## Análise Semanal\n\n"

        for week_start, week_end in weeks:
            week_label = f"Semana {week_start.strftime('%d/%m')} – {(week_end - pd.Timedelta(days=1)).strftime('%d/%m/%Y')}"
            weekly_model = CollaborationModel.for_period(all_issues, week_start, week_end)
            weekly_model.build_graph()

            net = weekly_model.network_metrics()
            if net.num_nodes == 0:
                md += f"### {week_label}\n\n_Sem atividade de colaboração nesta semana._\n\n"
                continue

            chart_name = f"network_week_{week_start.strftime('%Y-%m-%d')}.png"
            weekly_view = CollaborationView(
                weekly_model,
                month_dir,
                period_label=week_label,
                chart_filename=chart_name,
            )
            md += f"### {week_label}\n\n"
            md += weekly_view.render_section(heading_level=4)

        # Save
        report_path = os.path.join(month_dir, "monthly.md")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"  Saved {report_path}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
        """Return (first_day_of_month, first_day_of_next_month) as naive datetimes."""
        start = pd.Timestamp(year=year, month=month, day=1)
        end = start + pd.offsets.MonthEnd(1) + pd.Timedelta(days=1)
        return start.to_pydatetime(), end.normalize().to_pydatetime()

"""TeamView — renders per-team markdown reports and contribution/throughput charts."""
from __future__ import annotations

import os

import matplotlib.pyplot as plt
import pandas as pd

from reportfy.models.team import TeamModel, TeamStats
from reportfy.views.base import BaseView


class TeamView(BaseView):
    """
    Renders one markdown file per team plus a summary index.

    Charts generated per team:
      - Member contribution bar chart (created vs assigned)
      - Biweekly throughput line chart
      - Monthly throughput line chart

    Summary charts:
      - Delivery vs Done across all teams
      - Total throughput by team
    """

    def __init__(self, model: TeamModel, output_dir: str):
        """
        Args:
            model: Pre-computed TeamModel.
            output_dir: Base output directory.
        """
        super().__init__(output_dir)
        self.model = model
        self.teams_dir = os.path.join(output_dir, "teams")
        self.graphs_dir = os.path.join(self.teams_dir, "graphs")
        os.makedirs(self.graphs_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # BaseView implementation
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Build the teams summary index markdown."""
        all_stats = self.model.all_stats()
        md = "# Estatísticas por Equipe\n\n"
        md += "| Equipe | Membros | Issues Criadas | Issues Fechadas |\n"
        md += "|--------|---------|----------------|----------------|\n"
        for s in all_stats:
            md += (
                f"| [{s.team_slug}](teams/{s.team_slug}.md)"
                f" | {len(s.members)} | {s.issues_created} | {s.issues_closed} |\n"
            )
        return md

    def save_charts(self) -> dict[str, str]:
        """Generate all charts for all teams and return path mapping."""
        charts: dict[str, str] = {}
        for stats in self.model.all_stats():
            slug = stats.team_slug
            charts[f"{slug}_contrib"] = self._plot_contributions(stats)
            charts[f"{slug}_biweekly"] = self._plot_throughput(stats, "2W")
            charts[f"{slug}_monthly"] = self._plot_throughput(stats, "M")
        charts["summary_delivery"] = self._plot_summary_delivery()
        charts["summary_throughput"] = self._plot_summary_throughput()
        return charts

    def render_team(self, stats: TeamStats) -> str:
        """Build the full markdown report for a single team."""
        contrib_path = self._plot_contributions(stats)
        biweekly_path = self._plot_throughput(stats, "2W")
        monthly_path = self._plot_throughput(stats, "M")

        md = f"# Equipe: {stats.team_slug}\n\n"
        md += f"**Membros:** {', '.join(stats.members)}\n\n"
        md += "## Contribuições por Membro\n\n"
        if not stats.member_contributions.empty:
            md += "| Login | Criadas | Atribuídas |\n"
            md += "|-------|---------|------------|\n"
            for _, row in stats.member_contributions.iterrows():
                md += f"| {row['login']} | {int(row['created'])} | {int(row['assigned'])} |\n"
            md += "\n"
        if contrib_path:
            md += f"![Contribuições](graphs/{os.path.basename(contrib_path)})\n\n"

        md += "## Throughput Quinzenal\n\n"
        if not stats.biweekly_df.empty:
            md += "| Período | Entregue | Média Móvel |\n"
            md += "|---------|----------|-------------|\n"
            for _, row in stats.biweekly_df.iterrows():
                p_str = row["period"].strftime("%Y-%m-%d") if hasattr(row["period"], "strftime") else str(row["period"])
                md += f"| {p_str} | {int(row['delivered'])} | {row['moving_avg']} |\n"
            md += "\n"
        if biweekly_path:
            md += f"![Throughput quinzenal](graphs/{os.path.basename(biweekly_path)})\n\n"

        md += "## Throughput Mensal\n\n"
        if monthly_path:
            md += f"![Throughput mensal](graphs/{os.path.basename(monthly_path)})\n\n"

        md += "## Issues da Equipe\n\n"
        md += "| # | Título | Estado | Criado em | URL |\n"
        md += "|---|--------|--------|-----------|-----|\n"
        for issue in stats.issues[:50]:  # cap at 50 for readability
            created = issue.created_at.strftime("%Y-%m-%d") if issue.created_at else ""
            title = issue.title[:55] + "…" if len(issue.title) > 55 else issue.title
            md += f"| {issue.number} | {title} | {issue.state} | {created} | [link]({issue.html_url}) |\n"
        return md

    def save_all_team_reports(self) -> None:
        """Write individual markdown files for every team."""
        for stats in self.model.all_stats():
            content = self.render_team(stats)
            path = os.path.join(self.teams_dir, f"{stats.team_slug}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    # ------------------------------------------------------------------
    # Chart helpers
    # ------------------------------------------------------------------

    def _plot_contributions(self, stats: TeamStats) -> str:
        path = os.path.join(self.graphs_dir, f"{stats.team_slug}_contribuicao.png")
        df = stats.member_contributions
        if df.empty:
            return ""
        x = range(len(df))
        bar_w = 0.35
        plt.figure(figsize=(12, 5))
        plt.bar([i - bar_w / 2 for i in x], df["created"], width=bar_w, label="Criadas", color="steelblue")
        plt.bar([i + bar_w / 2 for i in x], df["assigned"], width=bar_w, label="Atribuídas", color="darkorange")
        plt.xticks(list(x), df["login"].tolist(), rotation=30, ha="right")
        plt.ylabel("Issues")
        plt.title(f"Contribuições — {stats.team_slug}")
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.4)
        return self._savefig(path)

    def _plot_throughput(self, stats: TeamStats, freq: str) -> str:
        suffix = "2W" if freq == "2W" else "M"
        path = os.path.join(self.graphs_dir, f"{stats.team_slug}_throughput_{suffix}.png")
        df = stats.biweekly_df if freq == "2W" else stats.monthly_df
        if df.empty:
            return ""
        x = range(len(df))
        labels = [
            r["period"].strftime("%Y-%m-%d") if hasattr(r["period"], "strftime") else str(r["period"])
            for _, r in df.iterrows()
        ]
        plt.figure(figsize=(12, 4))
        plt.bar(list(x), df["delivered"].tolist(), color="teal", alpha=0.7, label="Entregue")
        plt.plot(list(x), df["moving_avg"].tolist(), color="red", marker="o", linewidth=2, label="Média móvel")
        plt.xticks(list(x), labels, rotation=30, ha="right")
        plt.ylabel("Issues fechadas")
        plt.title(f"Throughput {'Quinzenal' if freq == '2W' else 'Mensal'} — {stats.team_slug}")
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.4)
        return self._savefig(path)

    def _plot_summary_delivery(self) -> str:
        path = os.path.join(self.teams_dir, "delivery_vs_done.png")
        all_stats = self.model.all_stats()
        if not all_stats:
            return ""
        slugs = [s.team_slug for s in all_stats]
        created = [s.issues_created for s in all_stats]
        closed = [s.issues_closed for s in all_stats]
        x = range(len(slugs))
        bar_w = 0.35
        plt.figure(figsize=(12, 5))
        plt.bar([i - bar_w / 2 for i in x], created, width=bar_w, label="Criadas", color="steelblue")
        plt.bar([i + bar_w / 2 for i in x], closed, width=bar_w, label="Fechadas", color="green")
        plt.xticks(list(x), slugs, rotation=30, ha="right")
        plt.ylabel("Issues")
        plt.title("Criadas vs Fechadas — Por Equipe")
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.4)
        return self._savefig(path)

    def _plot_summary_throughput(self) -> str:
        path = os.path.join(self.teams_dir, "throughput_summary.png")
        all_stats = self.model.all_stats()
        if not all_stats:
            return ""
        slugs = [s.team_slug for s in all_stats]
        totals = [s.biweekly_df["delivered"].sum() if not s.biweekly_df.empty else 0 for s in all_stats]
        plt.figure(figsize=(12, 5))
        plt.bar(slugs, totals, color="mediumseagreen")
        plt.xticks(rotation=30, ha="right")
        plt.ylabel("Total de issues fechadas")
        plt.title("Throughput Total por Equipe")
        plt.grid(axis="y", linestyle="--", alpha=0.4)
        return self._savefig(path)

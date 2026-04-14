"""DeveloperView — renders per-developer markdown files and charts."""
from __future__ import annotations

import os

import matplotlib.pyplot as plt
import pandas as pd

from reportfy.models.developer import DeveloperModel, DeveloperStats
from reportfy.views.base import BaseView


class DeveloperView(BaseView):
    """
    Renders one markdown file per developer plus a summary index.

    Charts generated per developer:
      - Prometido vs Realizado bar chart
      - Throughput line chart
    """

    def __init__(self, model: DeveloperModel, output_dir: str):
        """
        Args:
            model: Pre-computed DeveloperModel.
            output_dir: Base output directory.
        """
        super().__init__(output_dir)
        self.model = model
        self.dev_dir = os.path.join(output_dir, "developers")
        self.graphs_dir = os.path.join(self.dev_dir, "graphs")
        os.makedirs(self.graphs_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # BaseView implementation
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Build the developer index markdown (summary of all developers)."""
        all_stats = self.model.all_stats()
        md = "# Estatísticas por Desenvolvedor\n\n"
        md += "| Desenvolvedor | Total | Abertas | Fechadas | % Fechadas |\n"
        md += "|--------------|-------|---------|----------|------------|\n"
        for s in all_stats:
            md += (
                f"| [{s.login}](developers/{s.login}.md)"
                f" | {s.total} | {s.open_count} | {s.closed_count} | {s.closed_pct}% |\n"
            )
        return md

    def save_charts(self) -> dict[str, str]:
        """Generate charts for all developers and return path mapping."""
        charts: dict[str, str] = {}
        for stats in self.model.all_stats():
            p1, p2 = self._plot_developer_charts(stats)
            charts[f"{stats.login}_prometido"] = p1
            charts[f"{stats.login}_throughput"] = p2
        return charts

    def render_developer(self, stats: DeveloperStats) -> str:
        """Build the full markdown report for a single developer."""
        p1, p2 = self._plot_developer_charts(stats)
        md = f"# Estatísticas de {stats.login}\n\n"
        md += "## Resumo de Status\n\n"
        md += "| Total | Abertas | Fechadas | % Abertas | % Fechadas |\n"
        md += "|-------|---------|----------|-----------|------------|\n"
        md += f"| {stats.total} | {stats.open_count} | {stats.closed_count} | {stats.open_pct}% | {stats.closed_pct}% |\n\n"

        md += "## Prometido vs Realizado (quinzenal)\n\n"
        if not stats.throughput_df.empty:
            md += "| Período | Prometido | Realizado |\n"
            md += "|---------|-----------|----------|\n"
            for period, row in stats.throughput_df.iterrows():
                p_str = self._format_period(period)
                md += f"| {p_str} | {int(row['Prometido (Criadas)'])} | {int(row['Realizado (Fechadas)'])} |\n"
            md += "\n"
            if p1:
                md += f"![Prometido vs Realizado](graphs/{os.path.basename(p1)})\n\n"

        md += "## Throughput (Issues Fechadas)\n\n"
        closed_issues = [i for i in stats.issues if i.is_closed]
        if closed_issues and p2:
            md += f"![Throughput](graphs/{os.path.basename(p2)})\n\n"
        else:
            md += "_Nenhum dado de throughput disponível._\n\n"

        md += "## Issues\n\n"
        md += "| # | Título | Estado | Criado em | URL |\n"
        md += "|---|--------|--------|-----------|-----|\n"
        for issue in stats.issues:
            created = issue.created_at.strftime("%Y-%m-%d") if issue.created_at else ""
            title = issue.title[:60] + "…" if len(issue.title) > 60 else issue.title
            md += f"| {issue.number} | {title} | {issue.state} | {created} | [link]({issue.html_url}) |\n"
        return md

    def save_all_developer_reports(self) -> None:
        """Write individual markdown files for every developer."""
        for stats in self.model.all_stats():
            content = self.render_developer(stats)
            path = os.path.join(self.dev_dir, f"{stats.login}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    # ------------------------------------------------------------------
    # Chart helpers
    # ------------------------------------------------------------------

    def _plot_developer_charts(self, stats: DeveloperStats) -> tuple[str, str]:
        """Generate both charts for *stats* and return (path1, path2)."""
        p1 = self._plot_prometido_realizado(stats)
        p2 = self._plot_throughput(stats)
        return p1, p2

    def _plot_prometido_realizado(self, stats: DeveloperStats) -> str:
        path = os.path.join(self.graphs_dir, f"{stats.login}_prometido_realizado.png")
        df = stats.throughput_df
        if df.empty:
            return ""
        fig, ax = plt.subplots(figsize=(12, 4))
        df.plot(kind="bar", ax=ax)
        ax.set_title(f"Prometido vs Realizado — {stats.login}")
        ax.set_ylabel("Issues")
        ax.set_xticklabels(
            [self._format_period(d) for d in df.index],
            rotation=30,
            ha="right",
        )
        ax.grid(True, linestyle="--", alpha=0.5)
        return self._savefig(path)

    def _plot_throughput(self, stats: DeveloperStats) -> str:
        path = os.path.join(self.graphs_dir, f"{stats.login}_throughput.png")
        df = stats.throughput_df
        if df.empty or df["Realizado (Fechadas)"].sum() == 0:
            return ""
        throughput = df["Realizado (Fechadas)"]
        plt.figure(figsize=(12, 4))
        plt.plot(range(len(throughput)), throughput.values, marker="o", linestyle="-", color="blue")
        plt.title(f"Throughput Quinzenal — {stats.login}")
        plt.ylabel("Issues Fechadas")
        plt.xlabel("Período")
        plt.xticks(
            range(len(throughput)),
            [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in throughput.index],
            rotation=30,
            ha="right",
        )
        plt.grid(True, linestyle="--", alpha=0.5)
        return self._savefig(path)

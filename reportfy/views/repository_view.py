"""RepositoryView — renders per-repository charts and markdown report."""
from __future__ import annotations

import os

import matplotlib.pyplot as plt
import pandas as pd

from reportfy.models.repository import RepositoryModel
from reportfy.views.base import BaseView


class RepositoryView(BaseView):
    """
    Renders the per-repository dashboard.

    For each repository it generates biweekly, burn-up, Monte Carlo, and
    velocity distribution charts, then aggregates everything into a single
    markdown report.
    """

    def __init__(self, model: RepositoryModel, output_dir: str):
        """
        Args:
            model: Pre-computed RepositoryModel.
            output_dir: Base output directory.
        """
        super().__init__(output_dir)
        self.model = model
        self._weekly_dir = os.path.join(output_dir, "charts_weekly")
        self._burnup_dir = os.path.join(output_dir, "charts_burnup")
        self._mc_dir = os.path.join(output_dir, "charts_monte_carlo")
        for d in (self._weekly_dir, self._burnup_dir, self._mc_dir):
            os.makedirs(d, exist_ok=True)

    # ------------------------------------------------------------------
    # BaseView implementation
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Build the full per-repository markdown report."""
        repos = self.model.repository_names()
        all_stats = self.model.all_stats()

        md = "# Estatísticas GitHub — Por Repositório\n\n"
        md += "## Resumo Geral\n\n"
        md += "| Repositório | Abertas | Fechadas | Total | % Fechadas |\n"
        md += "|-------------|---------|----------|-------|------------|\n"
        for s in all_stats:
            md += f"| {s['repository']} | {s['open']} | {s['closed']} | {s['total']} | {s['percent_closed']}% |\n"
        md += "\n---\n\n"

        for repo in repos:
            md += self._repo_section(repo)

        return md

    def save_charts(self) -> dict[str, str]:
        """Generate all charts for every repository."""
        charts: dict[str, str] = {}
        for repo in self.model.repository_names():
            slug = repo.replace("/", "_")
            weekly = self.model.compute_biweekly_delivery(repo)
            mc = self.model.run_monte_carlo(repo)
            charts[f"{slug}_biweekly"] = self._plot_biweekly(repo, weekly)
            charts[f"{slug}_burnup"] = self._plot_burnup(repo, weekly)
            charts[f"{slug}_monte_carlo"] = self._plot_monte_carlo(repo, mc)
            charts[f"{slug}_velocity"] = self._plot_velocity(repo, mc)
        return charts

    # ------------------------------------------------------------------
    # Per-repo markdown
    # ------------------------------------------------------------------

    def _repo_section(self, repo: str) -> str:
        slug = repo.replace("/", "_")
        stats = self.model.compute_stats(repo)
        weekly = self.model.compute_biweekly_delivery(repo)
        mc = self.model.run_monte_carlo(repo)

        biweekly_path = self._plot_biweekly(repo, weekly)
        burnup_path = self._plot_burnup(repo, weekly)
        mc_path = self._plot_monte_carlo(repo, mc)
        vel_path = self._plot_velocity(repo, mc)

        md = f"## {repo}\n\n"
        md += f"| Abertas | Fechadas | Total | % Fechadas |\n"
        md += f"|---------|----------|-------|------------|\n"
        md += f"| {stats['open']} | {stats['closed']} | {stats['total']} | {stats['percent_closed']}% |\n\n"

        if biweekly_path:
            md += f"![Entregas quinzenais — {repo}]({biweekly_path})\n\n"
        if burnup_path:
            md += f"![Burn-up — {repo}]({burnup_path})\n\n"

        if not weekly.empty:
            md += "| Período | Prometido | Entregue | % Concluído |\n"
            md += "|---------|-----------|----------|-------------|\n"
            for _, row in weekly.iterrows():
                md += f"| {row['period'].strftime('%Y-%m-%d')} | {int(row['promised'])} | {int(row['delivered'])} | {round(row['percent_completed'], 1)}% |\n"
            md += "\n"

        if mc.simulation_data:
            if mc_path:
                md += f"![Monte Carlo — {repo}]({mc_path})\n\n"
            if vel_path:
                md += f"![Velocidade — {repo}]({vel_path})\n\n"
            md += "| Métrica | Valor |\n|--------|-------|\n"
            md += f"| Velocidade Média | {mc.velocity_mean:.2f} |\n"
            if mc.is_complete:
                md += "| Conclusão | Já concluído |\n"
            elif mc.completion_date_p50:
                md += f"| Conclusão P50 | {mc.completion_date_p50} |\n"
                md += f"| Conclusão P90 | {mc.completion_date_p90} |\n"
            md += "\n"
            md += self._monte_carlo_explanation()

        md += "---\n\n"
        return md

    # ------------------------------------------------------------------
    # Chart generators
    # ------------------------------------------------------------------

    def _plot_biweekly(self, repo: str, weekly: pd.DataFrame) -> str:
        slug = repo.replace("/", "_")
        path = os.path.join(self._weekly_dir, f"{slug}_weekly.png")
        if weekly.empty:
            return ""
        periods = weekly["period"].dt.strftime("%Y-%m-%d")
        x = range(len(periods))
        bar_w = 0.4
        fig, ax1 = plt.subplots(figsize=(12, 5))
        ax1.bar([i - bar_w / 2 for i in x], weekly["promised"], width=bar_w, label="Prometido", color="navy")
        ax1.bar([i + bar_w / 2 for i in x], weekly["delivered"], width=bar_w, label="Entregue", color="green")
        ax1.set_ylabel("Issues")
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(list(periods), rotation=45)
        ax1.legend(loc="upper left")
        ax2 = ax1.twinx()
        ax2.plot(list(x), weekly["percent_completed"].round(1).tolist(), color="darkred", marker="o", linewidth=2, label="% Concluído")
        ax2.set_ylabel("% Concluído")
        ax2.set_ylim(0, 110)
        ax2.legend(loc="upper right")
        plt.title(f"Entregas Quinzenais — {repo}")
        return self._savefig(path)

    def _plot_burnup(self, repo: str, weekly: pd.DataFrame) -> str:
        slug = repo.replace("/", "_")
        path = os.path.join(self._burnup_dir, f"{slug}_burnup.png")
        if weekly.empty:
            return ""
        w = weekly.copy().sort_values("period")
        w["cum_promised"] = w["promised"].cumsum()
        w["cum_delivered"] = w["delivered"].cumsum()
        x = range(len(w))
        periods = w["period"].dt.strftime("%Y-%m-%d").tolist()
        plt.figure(figsize=(12, 5))
        plt.plot(list(x), w["cum_promised"].tolist(), label="Prometido acumulado", color="blue", marker="o")
        plt.plot(list(x), w["cum_delivered"].tolist(), label="Entregue acumulado", color="green", marker="o")
        plt.fill_between(list(x), w["cum_delivered"].tolist(), w["cum_promised"].tolist(), color="lightgray", alpha=0.3)
        if len(w) >= 2:
            trend = pd.Series(w["cum_delivered"].values).rolling(2, min_periods=1).mean()
            plt.plot(list(x), trend.tolist(), linestyle="--", color="orange", label="Tendência")
        plt.xticks(list(x), periods, rotation=45)
        plt.xlabel("Período")
        plt.ylabel("Issues acumuladas")
        plt.title(f"Burn-up — {repo}")
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.3)
        return self._savefig(path)

    def _plot_monte_carlo(self, repo: str, mc) -> str:
        from reportfy.models.organization import MonteCarloResult
        slug = repo.replace("/", "_")
        path = os.path.join(self._mc_dir, f"{slug}_monte_carlo.png")
        if not mc.simulation_data:
            return ""
        dates = [s["completion_date"] for s in mc.simulation_data]
        min_d = min(dates)
        nums = [(d - min_d).days / 7 for d in dates]
        bins = min(20, max(1, len(set(int(n) for n in nums))))
        plt.figure(figsize=(12, 6))
        plt.hist(nums, bins=bins, alpha=0.7, color="steelblue", edgecolor="black")
        sorted_nums = sorted(nums)
        n = len(sorted_nums)
        for pct, color, label in ((0.10, "green", "P10"), (0.50, "orange", "P50"), (0.90, "red", "P90")):
            plt.axvline(x=sorted_nums[min(int(pct * n), n - 1)], color=color, linestyle="--", linewidth=2, label=label)
        plt.title(f"Monte Carlo — {repo}")
        plt.xlabel("Semanas até conclusão")
        plt.ylabel("Simulações")
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.3)
        return self._savefig(path)

    def _plot_velocity(self, repo: str, mc) -> str:
        slug = repo.replace("/", "_")
        path = os.path.join(self._mc_dir, f"{slug}_velocity_dist.png")
        if not mc.simulation_data:
            return ""
        velocities = [s["velocity"] for s in mc.simulation_data]
        plt.figure(figsize=(12, 5))
        plt.hist(velocities, bins=min(20, len(velocities) // 5 + 1), alpha=0.7, color="teal", edgecolor="black")
        for val, color, label in ((mc.velocity_p10, "green", "P10"), (mc.velocity_p50, "orange", "P50"), (mc.velocity_p90, "red", "P90")):
            plt.axvline(x=val, color=color, linestyle="--", linewidth=2, label=label)
        plt.title(f"Distribuição de Velocidade — {repo}")
        plt.xlabel("Velocidade (issues/quinzena)")
        plt.ylabel("Frequência")
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.3)
        return self._savefig(path)

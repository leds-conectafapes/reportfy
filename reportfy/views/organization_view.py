"""OrganizationView — renders org-level markdown report and charts."""
from __future__ import annotations

import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from reportfy.models.organization import MonteCarloResult, OrganizationModel
from reportfy.views.base import BaseView


class OrganizationView(BaseView):
    """
    Renders the organisation dashboard.

    Produces:
      - Biweekly delivery bar+line chart
      - Burn-up chart with trend projection
      - Monte Carlo completion histogram
      - Velocity distribution histogram
      - Full markdown report combining all of the above
    """

    def __init__(self, model: OrganizationModel, output_dir: str):
        """
        Args:
            model: Pre-computed OrganizationModel.
            output_dir: Base directory for saving charts and the report.
        """
        super().__init__(output_dir)
        self.model = model
        self.charts_dir = os.path.join(output_dir, "organization_charts")
        os.makedirs(self.charts_dir, exist_ok=True)

        # Cache model computations
        self._stats = model.compute_stats()
        self._weekly = model.compute_biweekly_delivery()
        self._mc: MonteCarloResult = model.run_monte_carlo()

    # ------------------------------------------------------------------
    # BaseView implementation
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Build and return the full organisation markdown report."""
        chart_paths = self.save_charts()
        md = self._header()
        md += self._biweekly_section(chart_paths.get("biweekly", ""))
        md += self._burnup_section(chart_paths.get("burnup", ""))
        md += self._monte_carlo_section(
            chart_paths.get("monte_carlo", ""),
            chart_paths.get("velocity_dist", ""),
        )
        return md

    def save_charts(self) -> dict[str, str]:
        """Generate and save all organisation charts."""
        return {
            "biweekly": self._plot_biweekly(),
            "burnup": self._plot_burnup(),
            "monte_carlo": self._plot_monte_carlo(),
            "velocity_dist": self._plot_velocity_dist(),
        }

    # ------------------------------------------------------------------
    # Markdown sections
    # ------------------------------------------------------------------

    def _header(self) -> str:
        s = self._stats
        md = "# Estatísticas GitHub — Organização\n\n"
        md += "| Abertas | Fechadas | Total | % Fechadas |\n"
        md += "|---------|----------|-------|------------|\n"
        md += f"| {s['open']} | {s['closed']} | {s['total']} | {s['percent_closed']}% |\n\n"
        return md

    def _biweekly_section(self, chart_path: str) -> str:
        w = self._weekly
        avg_velocity = round(w["delivered"].mean(), 2) if not w.empty else 0
        md = "## Entregas Quinzenais da Organização\n\n"
        if chart_path:
            md += f"![Entregas quinzenais]({chart_path})\n\n"
        md += f"**Velocidade média quinzenal:** {avg_velocity} issues/quinzena\n\n"
        md += "| Período | Prometido | Entregue | % Concluído |\n"
        md += "|---------|-----------|----------|-------------|\n"
        for _, row in w.iterrows():
            md += f"| {row['period'].strftime('%Y-%m-%d')} | {int(row['promised'])} | {int(row['delivered'])} | {round(row['percent_completed'], 1)}% |\n"
        md += "\n"
        return md

    def _burnup_section(self, chart_path: str) -> str:
        md = "## Burn-up Chart da Organização\n\n"
        if chart_path:
            md += f"![Burn-up]({chart_path})\n\n"
        return md

    def _monte_carlo_section(self, mc_path: str, vel_path: str) -> str:
        mc = self._mc
        if not mc.simulation_data:
            return ""
        md = "## Simulação Monte Carlo\n\n"
        if mc_path:
            md += f"![Monte Carlo]({mc_path})\n\n"
        if vel_path:
            md += f"![Distribuição de velocidade]({vel_path})\n\n"
        md += "### Previsões\n\n"
        md += "| Métrica | Valor |\n|--------|-------|\n"
        md += f"| Velocidade Média | {mc.velocity_mean:.2f} issues/quinzena |\n"
        md += f"| Velocidade P10 | {mc.velocity_p10:.2f} |\n"
        md += f"| Velocidade P50 | {mc.velocity_p50:.2f} |\n"
        md += f"| Velocidade P90 | {mc.velocity_p90:.2f} |\n"
        if mc.is_complete:
            md += "| Conclusão | Já concluído |\n"
        elif mc.completion_date_p50:
            md += f"| Conclusão P10 (Otimista) | {mc.completion_date_p10} |\n"
            md += f"| Conclusão P50 (Provável) | {mc.completion_date_p50} |\n"
            md += f"| Conclusão P90 (Conservador) | {mc.completion_date_p90} |\n"
        md += "\n"
        md += self._monte_carlo_explanation()
        return md

    # ------------------------------------------------------------------
    # Chart generators
    # ------------------------------------------------------------------

    def _plot_biweekly(self) -> str:
        path = os.path.join(self.charts_dir, "organization_biweekly.png")
        w = self._weekly
        if w.empty:
            return ""
        periods = w["period"].dt.strftime("%Y-%m-%d")
        x = range(len(periods))
        bar_w = 0.4
        fig, ax1 = plt.subplots(figsize=(12, 5))
        ax1.bar([i - bar_w / 2 for i in x], w["promised"], width=bar_w, label="Prometido", color="navy")
        ax1.bar([i + bar_w / 2 for i in x], w["delivered"], width=bar_w, label="Entregue", color="green")
        ax1.set_ylabel("Issues")
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(list(periods), rotation=45)
        ax1.legend(loc="upper left")
        ax2 = ax1.twinx()
        ax2.plot(list(x), w["percent_completed"].round(1).tolist(), color="darkred", marker="o", linewidth=2, label="% Concluído")
        ax2.set_ylabel("% Concluído")
        ax2.set_ylim(0, 110)
        ax2.legend(loc="upper right")
        plt.title("Entregas Quinzenais da Organização")
        return self._savefig(path)

    def _plot_burnup(self) -> str:
        path = os.path.join(self.charts_dir, "organization_burnup.png")
        w = self._weekly.copy().sort_values("period")
        if w.empty:
            return ""
        w["cum_promised"] = w["promised"].cumsum()
        w["cum_delivered"] = w["delivered"].cumsum()
        periods = w["period"].dt.strftime("%Y-%m-%d").tolist()
        x = range(len(periods))
        plt.figure(figsize=(12, 5))
        plt.plot(list(x), w["cum_promised"].tolist(), label="Prometido acumulado", color="blue", marker="o")
        plt.plot(list(x), w["cum_delivered"].tolist(), label="Entregue acumulado", color="green", marker="o")
        plt.fill_between(list(x), w["cum_delivered"].tolist(), w["cum_promised"].tolist(), color="lightgray", alpha=0.3)
        if len(w) >= 2:
            trend = pd.Series(w["cum_delivered"].values).rolling(2, min_periods=1).mean()
            plt.plot(list(x), trend.tolist(), linestyle="--", color="orange", label="Tendência")
            delta = trend.iloc[-1] - trend.iloc[-2]
            if delta > 0:
                total = w["cum_promised"].max()
                periods_left = (total - trend.iloc[-1]) / delta
                if 0 < periods_left < 20:
                    last_dt = pd.to_datetime(w["period"].iloc[-1])
                    pred = (last_dt + pd.Timedelta(days=int(periods_left * 14))).strftime("%Y-%m-%d")
                    future_x = len(periods) - 1 + periods_left
                    plt.axvline(x=future_x, linestyle=":", color="red", label=f"Previsão: {pred}")
        plt.xticks(list(x), periods, rotation=45)
        plt.xlabel("Período")
        plt.ylabel("Issues acumuladas")
        plt.title("Burn-up Chart da Organização")
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.3)
        return self._savefig(path)

    def _plot_monte_carlo(self) -> str:
        path = os.path.join(self.charts_dir, "organization_monte_carlo.png")
        mc = self._mc
        if not mc.simulation_data:
            return ""
        dates = [s["completion_date"] for s in mc.simulation_data]
        min_d = min(dates)
        nums = [(d - min_d).days / 7 for d in dates]
        bins = min(20, max(1, int((max(nums) - min(nums)) / 1) + 1))
        plt.figure(figsize=(12, 6))
        plt.hist(nums, bins=bins, alpha=0.7, color="blue", edgecolor="black")
        sorted_nums = sorted(nums)
        n = len(sorted_nums)
        for pct, color, label in ((0.10, "green", "P10"), (0.50, "orange", "P50"), (0.90, "red", "P90")):
            plt.axvline(x=sorted_nums[min(int(pct * n), n - 1)], color=color, linestyle="--", linewidth=2, label=label)
        plt.title("Simulação Monte Carlo — Previsão de Conclusão")
        plt.xlabel("Semanas até conclusão")
        plt.ylabel("Número de simulações")
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.3)
        return self._savefig(path)

    def _plot_velocity_dist(self) -> str:
        path = os.path.join(self.charts_dir, "organization_velocity_dist.png")
        mc = self._mc
        if not mc.simulation_data:
            return ""
        velocities = [s["velocity"] for s in mc.simulation_data]
        plt.figure(figsize=(12, 5))
        plt.hist(velocities, bins=min(20, len(velocities) // 5 + 1), alpha=0.7, color="green", edgecolor="black")
        for val, color, label in (
            (mc.velocity_p10, "green", "P10"),
            (mc.velocity_p50, "orange", "P50"),
            (mc.velocity_p90, "red", "P90"),
        ):
            plt.axvline(x=val, color=color, linestyle="--", linewidth=2, label=label)
        plt.title("Distribuição de Velocidade da Organização")
        plt.xlabel("Velocidade (issues/quinzena)")
        plt.ylabel("Frequência")
        plt.legend()
        plt.grid(axis="y", linestyle="--", alpha=0.3)
        return self._savefig(path)

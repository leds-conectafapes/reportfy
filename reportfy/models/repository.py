"""RepositoryModel — per-repository delivery stats and Monte Carlo."""
from __future__ import annotations

import random
from typing import Optional

import numpy as np
import pandas as pd

from reportfy.models.issue import IssueModel
from reportfy.models.organization import MonteCarloResult


class RepositoryModel:
    """Groups issues by repository and computes individual repo metrics."""

    def __init__(self, issues: list[IssueModel], simulations: int = 1000):
        """
        Args:
            issues: All parsed issues (multi-repo is supported).
            simulations: Monte Carlo iterations per repository.
        """
        self.issues = issues
        self.simulations = simulations

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def repository_names(self) -> list[str]:
        """Return sorted list of unique repository names."""
        return sorted({i.repository for i in self.issues})

    def issues_for(self, repo: str) -> list[IssueModel]:
        """Return only the issues belonging to *repo*."""
        return [i for i in self.issues if i.repository == repo]

    def compute_stats(self, repo: str) -> dict:
        """Return open/closed/total/pct_closed for a single repository."""
        repo_issues = self.issues_for(repo)
        closed = sum(1 for i in repo_issues if i.is_closed)
        total = len(repo_issues)
        return {
            "repository": repo,
            "open": total - closed,
            "closed": closed,
            "total": total,
            "percent_closed": round(closed / total * 100, 1) if total else 0.0,
        }

    def all_stats(self) -> list[dict]:
        """Return stats for every repository."""
        return [self.compute_stats(r) for r in self.repository_names()]

    def compute_biweekly_delivery(self, repo: str) -> pd.DataFrame:
        """
        Return biweekly promised/delivered DataFrame for *repo*.

        Mirrors OrganizationModel.compute_biweekly_delivery but scoped to one repo.
        """
        repo_issues = self.issues_for(repo)
        if not repo_issues:
            return pd.DataFrame(columns=["period", "promised", "delivered", "percent_completed"])

        rows = [{"state": i.state, "created_at": i.created_at} for i in repo_issues]
        df = pd.DataFrame(rows)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["period"] = df["created_at"].dt.to_period("2W").apply(lambda r: r.start_time)

        grouped = df.groupby(["period", "state"]).size().unstack(fill_value=0)
        for col in ("open", "closed"):
            if col not in grouped.columns:
                grouped[col] = 0

        grouped["promised"] = grouped["open"] + grouped["closed"]
        grouped["delivered"] = grouped["closed"]
        grouped["percent_completed"] = (
            grouped["closed"] / grouped["promised"]
        ).fillna(0) * 100

        return grouped.reset_index().sort_values("period")

    def run_monte_carlo(self, repo: str) -> MonteCarloResult:
        """Run Monte Carlo completion simulation for a single repository."""
        weekly = self.compute_biweekly_delivery(repo)
        if weekly.empty:
            return MonteCarloResult(
                velocity_mean=0.0, velocity_p10=0.0, velocity_p50=0.0,
                velocity_p90=0.0, completion_date_p10=None,
                completion_date_p50=None, completion_date_p90=None,
            )

        velocities = weekly["delivered"].tolist()
        weekly["cum_promised"] = weekly["promised"].cumsum()
        weekly["cum_delivered"] = weekly["delivered"].cumsum()
        remaining = weekly["cum_promised"].max() - weekly["cum_delivered"].max()
        last_date = pd.to_datetime(weekly["period"].max())

        if remaining <= 0:
            mean_v = float(np.mean(velocities)) if velocities else 0.0
            return MonteCarloResult(
                velocity_mean=mean_v,
                velocity_p10=float(np.percentile(velocities, 10)) if velocities else 0.0,
                velocity_p50=float(np.percentile(velocities, 50)) if velocities else 0.0,
                velocity_p90=float(np.percentile(velocities, 90)) if velocities else 0.0,
                completion_date_p10="Complete",
                completion_date_p50="Complete",
                completion_date_p90="Complete",
            )

        simulation_data: list[dict] = []
        for _ in range(self.simulations):
            sample = random.choices(velocities, k=len(velocities))
            mean_v = float(np.mean(sample)) * random.uniform(0.8, 1.2)
            if mean_v <= 0:
                continue
            periods = remaining / mean_v
            simulation_data.append({
                "velocity": mean_v,
                "periods_to_completion": periods,
                "completion_date": last_date + pd.Timedelta(days=int(periods * 14)),
            })

        if not simulation_data:
            return MonteCarloResult(
                velocity_mean=0.0, velocity_p10=0.0, velocity_p50=0.0,
                velocity_p90=0.0, completion_date_p10=None,
                completion_date_p50=None, completion_date_p90=None,
            )

        all_v = [s["velocity"] for s in simulation_data]
        all_dates = sorted(s["completion_date"] for s in simulation_data)
        n = len(all_dates)

        def _pct(p: float) -> str:
            return all_dates[min(int(p * n), n - 1)].strftime("%Y-%m-%d")

        return MonteCarloResult(
            velocity_mean=float(np.mean(all_v)),
            velocity_p10=float(np.percentile(all_v, 10)),
            velocity_p50=float(np.percentile(all_v, 50)),
            velocity_p90=float(np.percentile(all_v, 90)),
            completion_date_p10=_pct(0.10),
            completion_date_p50=_pct(0.50),
            completion_date_p90=_pct(0.90),
            simulation_data=simulation_data,
        )

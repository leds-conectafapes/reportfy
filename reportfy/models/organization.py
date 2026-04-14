"""OrganizationModel — computes org-level stats, biweekly delivery, and Monte Carlo."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from reportfy.models.issue import IssueModel
from reportfy.utils.periods import apply_half_month


@dataclass
class MonteCarloResult:
    """Holds percentile outputs of a Monte Carlo completion simulation."""

    velocity_mean: float
    velocity_p10: float
    velocity_p50: float
    velocity_p90: float
    completion_date_p10: Optional[str]
    completion_date_p50: Optional[str]
    completion_date_p90: Optional[str]
    simulation_data: list[dict] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Return True when all work is already delivered."""
        return self.completion_date_p50 == "Complete"


class OrganizationModel:
    """Aggregates all issues for an organisation and computes delivery metrics."""

    def __init__(self, issues: list[IssueModel], simulations: int = 1000):
        """
        Args:
            issues: Parsed list of IssueModel objects for the whole organisation.
            simulations: Number of Monte Carlo iterations to run.
        """
        self.issues = issues
        self.simulations = simulations
        self._df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_df(self) -> pd.DataFrame:
        """Convert the issue list to a pandas DataFrame (cached)."""
        if self._df is None:
            rows = [
                {
                    "state": i.state,
                    "created_at": i.created_at,
                    "closed_at": i.closed_at,
                    "repository": i.repository,
                }
                for i in self.issues
            ]
            self._df = pd.DataFrame(rows)
        return self._df

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_stats(self) -> dict:
        """Return overall open/closed counts and percentage closed."""
        df = self._to_df()
        if df.empty or "state" not in df.columns:
            return {"open": 0, "closed": 0, "total": 0, "percent_closed": 0.0}
        counts = df["state"].value_counts().to_dict()
        open_count = counts.get("open", 0)
        closed_count = counts.get("closed", 0)
        total = open_count + closed_count
        return {
            "open": open_count,
            "closed": closed_count,
            "total": total,
            "percent_closed": round(closed_count / total * 100, 1) if total else 0.0,
        }

    def compute_biweekly_delivery(self) -> pd.DataFrame:
        """
        Return a DataFrame with biweekly promised/delivered/pct columns.

        Columns: period, open, closed, promised, delivered, percent_completed.
        """
        df = self._to_df().copy()
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["period"] = apply_half_month(df["created_at"])

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

    def run_monte_carlo(self) -> MonteCarloResult:
        """
        Run Monte Carlo simulations to predict project completion date.

        Uses bootstrapped biweekly velocities with ±20 % random noise per
        iteration.  Returns P10/P50/P90 percentile completion dates.
        """
        weekly = self.compute_biweekly_delivery()
        velocities = weekly["delivered"].tolist()
        weekly["cumulative_promised"] = weekly["promised"].cumsum()
        weekly["cumulative_delivered"] = weekly["delivered"].cumsum()
        remaining = weekly["cumulative_promised"].max() - weekly["cumulative_delivered"].max()
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
        print(f"Running {self.simulations} Monte Carlo simulations…")
        for _ in range(self.simulations):
            sample = random.choices(velocities, k=len(velocities))
            mean_v = float(np.mean(sample)) * random.uniform(0.8, 1.2)
            if mean_v <= 0:
                continue
            periods_to_finish = remaining / mean_v
            completion_date = last_date + pd.Timedelta(days=int(periods_to_finish * 14))
            simulation_data.append(
                {
                    "velocity": mean_v,
                    "periods_to_completion": periods_to_finish,
                    "completion_date": completion_date,
                }
            )

        if not simulation_data:
            return MonteCarloResult(
                velocity_mean=0.0,
                velocity_p10=0.0,
                velocity_p50=0.0,
                velocity_p90=0.0,
                completion_date_p10=None,
                completion_date_p50=None,
                completion_date_p90=None,
            )

        all_v = [s["velocity"] for s in simulation_data]
        all_dates = sorted(s["completion_date"] for s in simulation_data)
        n = len(all_dates)

        def _date_pct(p: float) -> str:
            return all_dates[min(int(p * n), n - 1)].strftime("%Y-%m-%d")

        return MonteCarloResult(
            velocity_mean=float(np.mean(all_v)),
            velocity_p10=float(np.percentile(all_v, 10)),
            velocity_p50=float(np.percentile(all_v, 50)),
            velocity_p90=float(np.percentile(all_v, 90)),
            completion_date_p10=_date_pct(0.10),
            completion_date_p50=_date_pct(0.50),
            completion_date_p90=_date_pct(0.90),
            simulation_data=simulation_data,
        )

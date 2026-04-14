"""DeveloperModel — per-developer throughput and issue breakdown."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from reportfy.models.issue import IssueModel
from reportfy.utils.periods import apply_half_month


@dataclass
class DeveloperStats:
    """Aggregated statistics for a single developer."""

    login: str
    total: int
    open_count: int
    closed_count: int
    open_pct: float
    closed_pct: float
    throughput_df: pd.DataFrame   # index=period, cols=[Prometido, Realizado]
    issues: list[IssueModel] = field(default_factory=list)


class DeveloperModel:
    """
    Groups issues by author login and computes per-developer delivery metrics.

    Each developer gets:
      - Total / open / closed counts and percentages.
      - Biweekly promised-vs-realised throughput table.
      - Raw list of their issues for detailed rendering.
    """

    def __init__(self, issues: list[IssueModel]):
        """
        Args:
            issues: Full list of parsed IssueModel objects.
        """
        self.issues = issues

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def developer_logins(self) -> list[str]:
        """Return sorted list of unique developer logins."""
        return sorted({i.author_login for i in self.issues if i.author_login})

    def issues_for(self, login: str) -> list[IssueModel]:
        """Return all issues authored by *login*."""
        return [i for i in self.issues if i.author_login == login]

    def compute_stats(self, login: str) -> DeveloperStats:
        """
        Compute full stats for a single developer.

        Returns a DeveloperStats dataclass with counts, percentages, and
        a biweekly throughput DataFrame.
        """
        dev_issues = self.issues_for(login)
        total = len(dev_issues)
        closed = sum(1 for i in dev_issues if i.is_closed)
        open_count = total - closed

        throughput_df = self._build_throughput(dev_issues)

        return DeveloperStats(
            login=login,
            total=total,
            open_count=open_count,
            closed_count=closed,
            open_pct=round(open_count / total * 100, 1) if total else 0.0,
            closed_pct=round(closed / total * 100, 1) if total else 0.0,
            throughput_df=throughput_df,
            issues=dev_issues,
        )

    def all_stats(self) -> list[DeveloperStats]:
        """Return stats for every developer."""
        return [self.compute_stats(login) for login in self.developer_logins()]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_throughput(issues: list[IssueModel]) -> pd.DataFrame:
        """
        Build a biweekly Prometido vs Realizado DataFrame.

        Columns: Prometido (Criadas), Realizado (Fechadas).
        Index: period start datetime.
        """
        rows = [
            {
                "created_at": i.created_at,
                "closed_at": i.closed_at,
                "is_closed": i.is_closed,
            }
            for i in issues
            if i.created_at is not None
        ]
        if not rows:
            return pd.DataFrame(columns=["Prometido (Criadas)", "Realizado (Fechadas)"])

        df = pd.DataFrame(rows)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["closed_at"] = pd.to_datetime(df["closed_at"], errors="coerce")
        df["created_period"] = apply_half_month(df["created_at"])
        df["closed_period"] = apply_half_month(df["closed_at"])

        created_counts = df.groupby("created_period").size().rename("Prometido (Criadas)")
        closed_df = df.dropna(subset=["closed_period"])
        closed_counts = closed_df.groupby("closed_period").size().rename("Realizado (Fechadas)")

        result = pd.DataFrame({"Prometido (Criadas)": created_counts}).fillna(0)
        result["Realizado (Fechadas)"] = pd.Series(closed_counts).fillna(0)
        return result.fillna(0).astype(int).sort_index()

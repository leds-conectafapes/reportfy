"""TeamModel — per-team contribution and throughput metrics."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pandas as pd

from reportfy.models.issue import IssueModel


@dataclass
class TeamMember:
    """Represents a GitHub team member."""

    login: str
    team_slug: str


@dataclass
class TeamStats:
    """Aggregated statistics for a single team."""

    team_slug: str
    members: list[str]
    issues_created: int
    issues_closed: int
    member_contributions: pd.DataFrame   # cols=[login, created, assigned]
    biweekly_df: pd.DataFrame            # cols=[period, delivered]
    monthly_df: pd.DataFrame             # cols=[period, delivered]
    issues: list[IssueModel] = field(default_factory=list)


class TeamModel:
    """
    Groups issues by team membership and computes per-team metrics.

    Supports both single-assignee (assignee field) and multi-assignee
    (assignees field) GitHub issues.
    """

    def __init__(self, issues: list[IssueModel], members_df: pd.DataFrame):
        """
        Args:
            issues: Full parsed issue list.
            members_df: Raw Airbyte team_members DataFrame.
        """
        self.issues = issues
        self.members_df = members_df
        self._team_members: dict[str, list[str]] = {}  # slug → [logins]
        self._parse_members()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _parse_members(self) -> None:
        """Parse the raw members DataFrame into a slug→logins mapping."""
        if self.members_df.empty:
            return

        df = self.members_df.copy()

        # Normalise login column — Airbyte may nest it inside a 'user' JSON
        if "login" not in df.columns and "user" in df.columns:
            df["login"] = df["user"].apply(self._extract_login)

        # Normalise team slug column
        slug_col = next(
            (c for c in ("team_slug", "slug", "team") if c in df.columns), None
        )
        if slug_col is None:
            return

        for _, row in df.iterrows():
            slug = str(row[slug_col])
            login = str(row.get("login", ""))
            if login:
                self._team_members.setdefault(slug, []).append(login)

    @staticmethod
    def _extract_login(user_json) -> str:
        try:
            user = json.loads(user_json) if isinstance(user_json, str) else user_json
            if isinstance(user, dict):
                return user.get("login", "")
        except (json.JSONDecodeError, TypeError):
            pass
        return ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def team_slugs(self) -> list[str]:
        """Return sorted list of team slugs."""
        return sorted(self._team_members.keys())

    def members_of(self, slug: str) -> list[str]:
        """Return login list for a team slug."""
        return self._team_members.get(slug, [])

    def issues_for_team(self, slug: str) -> list[IssueModel]:
        """Return issues that have at least one team member as creator or assignee."""
        members = set(self.members_of(slug))
        return [
            i for i in self.issues
            if (i.author_login in members) or bool(members & set(i.all_assignees))
        ]

    def compute_stats(self, slug: str) -> TeamStats:
        """Compute contribution metrics for a single team."""
        members = self.members_of(slug)
        team_issues = self.issues_for_team(slug)

        created = sum(1 for i in team_issues if i.author_login in set(members))
        closed = sum(1 for i in team_issues if i.is_closed)

        contrib = self._member_contributions(members, team_issues)
        biweekly = self._throughput(team_issues, "2W")
        monthly = self._throughput(team_issues, "M")

        return TeamStats(
            team_slug=slug,
            members=members,
            issues_created=created,
            issues_closed=closed,
            member_contributions=contrib,
            biweekly_df=biweekly,
            monthly_df=monthly,
            issues=team_issues,
        )

    def all_stats(self) -> list[TeamStats]:
        """Return stats for every team."""
        return [self.compute_stats(slug) for slug in self.team_slugs()]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _member_contributions(
        members: list[str], issues: list[IssueModel]
    ) -> pd.DataFrame:
        """Build a per-member created/assigned contribution table."""
        data = {m: {"login": m, "created": 0, "assigned": 0} for m in members}
        for issue in issues:
            if issue.author_login in data:
                data[issue.author_login]["created"] += 1
            for assignee in issue.all_assignees:
                if assignee in data:
                    data[assignee]["assigned"] += 1
        return pd.DataFrame(list(data.values()))

    @staticmethod
    def _throughput(issues: list[IssueModel], freq: str) -> pd.DataFrame:
        """Build a throughput DataFrame (delivered issues per period)."""
        closed = [
            {"closed_at": i.closed_at}
            for i in issues
            if i.is_closed and i.closed_at is not None
        ]
        if not closed:
            return pd.DataFrame(columns=["period", "delivered"])

        df = pd.DataFrame(closed)
        df["closed_at"] = pd.to_datetime(df["closed_at"])
        df["period"] = df["closed_at"].dt.to_period(freq).dt.start_time
        result = df.groupby("period").size().reset_index(name="delivered")

        # 3-period rolling average for trend
        result["moving_avg"] = (
            result["delivered"].rolling(window=3, min_periods=1).mean().round(2)
        )
        return result.sort_values("period")

"""IssueModel — parses and normalises raw GitHub issue rows from the Airbyte DataFrame."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class IssueModel:
    """Represents a single GitHub issue with all relevant fields normalised."""

    number: int
    title: str
    state: str
    repository: str
    html_url: str
    created_at: datetime
    closed_at: Optional[datetime]
    author_login: str
    assignee_login: Optional[str]
    assignee_logins: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_row(cls, row: dict) -> "IssueModel":
        """Build an IssueModel from a raw Airbyte/pandas row dict."""
        return cls(
            number=int(row.get("number", 0)),
            title=str(row.get("title", "")),
            state=str(row.get("state", "open")),
            repository=str(row.get("repository", "")),
            html_url=str(row.get("html_url", "")),
            created_at=cls._parse_dt(row.get("created_at")),
            closed_at=cls._parse_dt(row.get("closed_at")),
            author_login=cls._extract_login(row.get("user")),
            assignee_login=cls._extract_login(row.get("assignee")),
            assignee_logins=cls._extract_logins(row.get("assignees")),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_dt(value) -> Optional[datetime]:
        """Parse a datetime value that may be a string, datetime, or None."""
        if value is None:
            return None
        import pandas as pd
        try:
            parsed = pd.to_datetime(value)
            return None if pd.isna(parsed) else parsed.to_pydatetime()
        except Exception:
            return None

    @staticmethod
    def _extract_login(user_json) -> Optional[str]:
        """Extract the login string from a raw GitHub user JSON field."""
        if user_json is None:
            return None
        try:
            user = json.loads(user_json) if isinstance(user_json, str) else user_json
            if isinstance(user, dict):
                return user.get("login")
        except (json.JSONDecodeError, TypeError):
            pass
        return None

    @staticmethod
    def _extract_logins(assignees_json) -> list[str]:
        """Extract all login strings from a GitHub assignees JSON field."""
        if assignees_json is None:
            return []
        try:
            data = json.loads(assignees_json) if isinstance(assignees_json, str) else assignees_json
            if isinstance(data, list):
                return [
                    item["login"]
                    for item in data
                    if isinstance(item, dict) and "login" in item
                ]
            if isinstance(data, dict) and "login" in data:
                return [data["login"]]
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_closed(self) -> bool:
        """Return True if the issue is closed."""
        return self.state == "closed"

    @property
    def all_assignees(self) -> list[str]:
        """Return the full list of assignee logins (merges single + multi)."""
        logins = set(self.assignee_logins)
        if self.assignee_login:
            logins.add(self.assignee_login)
        return list(logins)
